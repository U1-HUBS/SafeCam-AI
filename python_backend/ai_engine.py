import cv2
import numpy as np
import time
import math
from collections import defaultdict, deque
from ultralytics import YOLO
import mediapipe as mp

try:
    from real_person_verifier import RealPersonVerifier
except ImportError:
    from python_backend.real_person_verifier import RealPersonVerifier

try:
    from alarm_manager import alarm_manager
except ImportError:
    from python_backend.alarm_manager import alarm_manager

class AIEngine:
    """
    SAFEcam Python WebRTC AI Processing Engine
    - Runs YOLO11 person detection & tracking on 640x360 AI frame.
    - Runs RealPersonVerifier to filter photos, posters, TV screens & phone displays.
    - Runs MediaPipe Pose landmark extraction on 640x360 AI frame.
    - Associates MediaPipe landmarks to YOLO11 person track IDs.
    - Conducts temporal behavior analysis & aggressive action classification:
      * Roles: ATTACKER (RED), VICTIM (GREEN), NORMAL (GREEN), REJECTED SCREEN/PHOTO (GREY)
      * Actions: PUNCH_ATTACKER, KICK_ATTACKER, PUSH_ATTACKER, HIT_ATTACKER, AGGRESSIVE_CONTACT
    - Scales coordinates dynamically to 1080p (1920x1080).
    - Renders bounding boxes, joint circles, skeleton lines, IDs, and alert badges directly onto 1080p frames via OpenCV.
    """

    # Configurable Action & Temporal Detection Thresholds
    THRESHOLDS = {
        "proximity_dist_px": 140.0,          # Max distance (640p) between 2 persons for interaction
        "punch_wrist_speed": 150.0,          # Min wrist speed (px/s) directed towards target
        "punch_strike_dist": 55.0,           # Max distance from wrist to target bounding box
        "punch_arm_ext_ratio": 0.82,         # Min ratio: dist(shoulder, wrist) / (dist(shoulder, elbow) + dist(elbow, wrist))
        "kick_ankle_speed": 140.0,           # Min ankle speed (px/s) directed towards target
        "kick_strike_dist": 65.0,            # Max distance from ankle to target bounding box
        "kick_ankle_elevation_offset": 0.35, # Ankle y must be < hip_y + 0.35 * bbox_h
        "push_wrist_speed": 110.0,           # Min wrist speed for push candidate
        "push_dist_px": 85.0,                # Max distance for push interaction
        "sustained_contact_dist": 70.0,      # Max distance for aggressive contact candidate
        "temporal_confirm_frames": 3,        # Min consecutive frames to confirm ATTACKER status
        "temporal_decay_frames": 10,         # Frames to hold state before decaying back to normal
        "enter_attack_frames": 4,            # N_enter: consecutive high-violence frames to transition NORMAL -> ATTACK
        "exit_attack_frames": 6,             # N_exit: consecutive normal frames to transition ATTACK -> NORMAL
        "high_confidence_thresh": 0.65,      # Min confidence threshold to qualify as high-confidence violence
        "history_window_len": 25             # Rolling history length per track
    }

    def __init__(self, model_path="yolo11n.pt"):
        print(f"[AI ENGINE] Initializing YOLO11 model ({model_path})...")
        self.model = YOLO(model_path)
        
        print("[AI ENGINE] Initializing MediaPipe Pose solution...")
        self.mp_pose = mp.solutions.pose
        self.pose_detector = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.45,
            min_tracking_confidence=0.45
        )

        print("[AI ENGINE] Initializing RealPersonVerifier module...")
        self.real_person_verifier = RealPersonVerifier()

        # Per-camera tracking & temporal behavior state history
        # camera_id -> track_id -> deque of historical state snapshots
        self.camera_history = defaultdict(lambda: defaultdict(lambda: deque(maxlen=self.THRESHOLDS["history_window_len"])))
        
        # Per-camera temporal action accumulators
        # camera_id -> track_id -> action_name -> consecutive_hits count
        self.camera_action_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        # Per-camera confirmed roles state dictionary to maintain temporal persistence
        # camera_id -> track_id -> { "role": str, "action": str, "target_id": int, "decay": int }
        self.confirmed_roles = defaultdict(dict)

        # Per-camera last printed terminal status (to prevent duplicate spam prints)
        self.last_printed_status = defaultdict(dict)

        # Stream-level Temporal Hysteresis State Machine per camera_id
        # camera_id -> { "state": "NORMAL" | "ATTACK", "consecutive_high": int, "consecutive_low": int }
        self.stream_hysteresis_state = defaultdict(lambda: {
            "state": "NORMAL",
            "consecutive_high": 0,
            "consecutive_low": 0
        })

        # Initialize RWF-2000 3D CNN Violence Classifier
        print("[AI ENGINE] Initializing RWF-2000 Violence Classifier...")
        try:
            try:
                from python_backend.rwf_classifier import RWF2000Classifier
            except ImportError:
                from rwf_classifier import RWF2000Classifier
            self.rwf_classifier = RWF2000Classifier()
        except Exception as e:
            print(f"[AI ENGINE] Warning: RWF-2000 Classifier initialization deferred/failed: {e}")
            self.rwf_classifier = None

    def process_frame(self, frame_1080p, camera_id="default"):
        """
        Processes a 1080p input frame:
        1. Resizes to 640x360 for AI processing.
        2. Performs YOLO11 person tracking & MediaPipe Pose.
        3. Conducts multi-person behavior & aggressive action analysis.
        4. Scales coordinates back to 1080p.
        5. Draws OpenCV overlays directly on frame_1080p.
        Returns: (annotated_1080p_frame, ai_telemetry_dict)
        """
        if frame_1080p is None:
            return None, {}

        orig_h, orig_w = frame_1080p.shape[:2]
        ai_w, ai_h = 640, 360

        scale_x = orig_w / float(ai_w)
        scale_y = orig_h / float(ai_h)

        t_ai_start = time.time()

        # 1. Create 640x360 AI Frame
        ai_frame = cv2.resize(frame_1080p, (ai_w, ai_h), interpolation=cv2.INTER_LINEAR)

        # 2. YOLO11 Detection & Tracking
        t_yolo_start = time.time()
        yolo_results = self.model.track(ai_frame, persist=True, classes=[0], verbose=False)
        yolo_ms = (time.time() - t_yolo_start) * 1000.0

        tracked_persons = []
        if yolo_results and len(yolo_results) > 0:
            boxes = yolo_results[0].boxes
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    cls_id = int(box.cls[0].item()) if box.cls is not None else 0
                    if cls_id != 0:
                        continue # person class only

                    conf = float(box.conf[0].item()) if box.conf is not None else 0.0
                    if conf < 0.45:
                        continue # filter out low-confidence noise / false positives

                    track_id = int(box.id[0].item()) if box.id is not None else int(time.time() * 1000) % 10000

                    # 640px bounding box [x1, y1, x2, y2]
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])

                    # IoU deduplication check against already added valid tracks
                    is_duplicate = False
                    for existing in tracked_persons:
                        b1 = existing["bbox_640"]
                        xi1, yi1 = max(b1[0], x1), max(b1[1], y1)
                        xi2, yi2 = min(b1[2], x2), min(b1[3], y2)
                        inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
                        area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
                        area2 = (x2 - x1) * (y2 - y1)
                        union = area1 + area2 - inter
                        iou = inter / union if union > 0 else 0
                        if iou > 0.55:
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        tracked_persons.append({
                            "track_id": track_id,
                            "bbox_640": [x1, y1, x2, y2],
                            "conf": conf,
                            "pose_landmarks": None
                        })

        # 3. MediaPipe Pose Detection on 640px AI Frame
        t_mp_start = time.time()
        rgb_ai = cv2.cvtColor(ai_frame, cv2.COLOR_BGR2RGB)
        pose_res = self.pose_detector.process(rgb_ai)
        mediapipe_ms = (time.time() - t_mp_start) * 1000.0

        raw_pose_landmarks = []
        if pose_res and pose_res.pose_landmarks:
            lms = pose_res.pose_landmarks.landmark
            # Extract 12 key joint indices:
            # 11: left_shoulder, 12: right_shoulder, 13: left_elbow, 14: right_elbow, 15: left_wrist, 16: right_wrist
            # 23: left_hip, 24: right_hip, 25: left_knee, 26: right_knee, 27: left_ankle, 28: right_ankle
            joint_indices = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
            extracted_joints = {}

            for idx in joint_indices:
                lm = lms[idx]
                if lm.visibility > 0.35:
                    extracted_joints[idx] = {
                        "x": lm.x * ai_w,
                        "y": lm.y * ai_h,
                        "vis": lm.visibility
                    }

            if extracted_joints:
                raw_pose_landmarks.append(extracted_joints)

        # 4. Associate Pose Landmarks to YOLO Tracked Persons
        for person in tracked_persons:
            px1, py1, px2, py2 = person["bbox_640"]
            best_pose = None
            best_overlap = 0

            for pose in raw_pose_landmarks:
                contained_count = 0
                for idx, lm in pose.items():
                    if px1 - 15 <= lm["x"] <= px2 + 15 and py1 - 15 <= lm["y"] <= py2 + 15:
                        contained_count += 1
                if contained_count > best_overlap:
                    best_overlap = contained_count
                    best_pose = pose
            person["pose_landmarks"] = best_pose

        # 5. Temporal Snapshot Update
        history_map = self.camera_history[camera_id]
        current_time = time.time()

        for person in tracked_persons:
            tid = person["track_id"]
            bx1, by1, bx2, by2 = person["bbox_640"]
            center_x = (bx1 + bx2) / 2.0
            center_y = (by1 + by2) / 2.0

            pose = person["pose_landmarks"] or {}
            lwrist = pose.get(15)
            rwrist = pose.get(16)
            lankle = pose.get(27)
            rankle = pose.get(28)
            lhip = pose.get(23)
            rhip = pose.get(24)
            lshoulder = pose.get(11)
            rshoulder = pose.get(12)
            lelbow = pose.get(13)
            relbow = pose.get(14)

            snap = {
                "time": current_time,
                "center": (center_x, center_y),
                "bbox": [bx1, by1, bx2, by2],
                "lwrist": (lwrist["x"], lwrist["y"]) if lwrist else None,
                "rwrist": (rwrist["x"], rwrist["y"]) if rwrist else None,
                "lankle": (lankle["x"], lankle["y"]) if lankle else None,
                "rankle": (rankle["x"], rankle["y"]) if rankle else None,
                "lhip": (lhip["x"], lhip["y"]) if lhip else None,
                "rhip": (rhip["x"], rhip["y"]) if rhip else None,
                "lshoulder": (lshoulder["x"], lshoulder["y"]) if lshoulder else None,
                "rshoulder": (rshoulder["x"], rshoulder["y"]) if rshoulder else None,
                "lelbow": (lelbow["x"], lelbow["y"]) if lelbow else None,
                "relbow": (relbow["x"], relbow["y"]) if relbow else None
            }
            history_map[tid].append(snap)

        # 6. REAL-PERSON VERIFICATION LAYER
        tracked_persons = self.real_person_verifier.verify_tracks(tracked_persons, ai_frame, camera_id=camera_id)

        # Separate verified physical people vs rejected image/screen detections
        verified_persons = [p for p in tracked_persons if p.get("is_verified_real_person", False)]
        rejected_persons = [p for p in tracked_persons if not p.get("is_verified_real_person", False)]

        # 6. RWF-2000 / LSTM Violence Classifier
        t_rwf_start = time.time()
        rwf_res = {}
        if self.rwf_classifier is not None:
            temp_telemetry = {"people_count": len(verified_persons), "tracked_persons": verified_persons}
            rwf_res = self.rwf_classifier.predict_frame(frame_1080p, camera_id=camera_id, pose_telemetry=temp_telemetry)
        rwf_lstm_ms = (time.time() - t_rwf_start) * 1000.0
        total_ai_ms = (time.time() - t_ai_start) * 1000.0

        rwf_violence = rwf_res.get("violence_detected", False)
        rwf_prob = rwf_res.get("fight_probability", 0.0)

        # 7. Action & Role Analysis strictly across VERIFIED Real Persons
        current_candidates = {} # track_id -> { "action": str, "target_id": int, "conf": float }
        action_counts = self.camera_action_counts[camera_id]

        if len(verified_persons) >= 2:
            for i in range(len(verified_persons)):
                p1 = verified_persons[i]
                t1 = p1["track_id"]
                h1 = history_map[t1]

                for j in range(len(verified_persons)):
                    if i == j:
                        continue
                    p2 = verified_persons[j]
                    t2 = p2["track_id"]
                    h2 = history_map[t2]

                    c1_x = (p1["bbox_640"][0] + p1["bbox_640"][2]) / 2.0
                    c1_y = (p1["bbox_640"][1] + p1["bbox_640"][3]) / 2.0
                    c2_x = (p2["bbox_640"][0] + p2["bbox_640"][2]) / 2.0
                    c2_y = (p2["bbox_640"][1] + p2["bbox_640"][3]) / 2.0

                    dist_centers = math.hypot(c1_x - c2_x, c1_y - c2_y)
                    if dist_centers > self.THRESHOLDS["proximity_dist_px"]:
                        continue

                    # Evaluate action directed from p1 toward p2
                    detected_action, act_conf = self._evaluate_attack_action(p1, p2, h1, h2, rwf_prob)
                    if detected_action:
                        # Prioritize higher confidence / stronger action
                        if t1 not in current_candidates or act_conf > current_candidates[t1]["conf"]:
                            current_candidates[t1] = {
                                "action": detected_action,
                                "target_id": t2,
                                "conf": act_conf
                            }

        # 8. Temporal Persistence & State Accumulation across Verified Persons
        all_present_ids = {p["track_id"] for p in verified_persons}
        active_roles = self.confirmed_roles[camera_id]

        for p in verified_persons:
            tid = p["track_id"]
            if tid in current_candidates:
                cand = current_candidates[tid]
                act = cand["action"]
                action_counts[tid][act] += 1

                # Check if temporal persistence threshold passed (>= 3 frames)
                if action_counts[tid][act] >= self.THRESHOLDS["temporal_confirm_frames"]:
                    active_roles[tid] = {
                        "role": "attacker",
                        "action": act,
                        "target_id": cand["target_id"],
                        "confidence": cand["conf"],
                        "decay": self.THRESHOLDS["temporal_decay_frames"]
                    }
            else:
                # Decay action counters
                for act in list(action_counts[tid].keys()):
                    action_counts[tid][act] = max(0, action_counts[tid][act] - 1)

                # Decay confirmed role state
                if tid in active_roles:
                    active_roles[tid]["decay"] -= 1
                    if active_roles[tid]["decay"] <= 0:
                        del active_roles[tid]

        # Clean up stale track IDs
        for tid in list(active_roles.keys()):
            if tid not in all_present_ids:
                active_roles[tid]["decay"] -= 1
                if active_roles[tid]["decay"] <= 0:
                    del active_roles[tid]

        # Assign Victim Roles strictly based on confirmed Attackers
        confirmed_victim_ids = set()
        for tid, rdata in active_roles.items():
            if rdata["role"] == "attacker" and rdata["target_id"] in all_present_ids:
                confirmed_victim_ids.add(rdata["target_id"])

        # Mutual Fight vs One-Sided Bullying Resolution
        confirmed_attacker_ids = set()
        mutual_fight_ids = set()

        for tid, rdata in active_roles.items():
            if rdata["role"] == "attacker" and rdata["target_id"] in all_present_ids:
                target_id = rdata["target_id"]
                if target_id in active_roles and active_roles[target_id].get("target_id") == tid:
                    mutual_fight_ids.add(tid)
                    mutual_fight_ids.add(target_id)
                else:
                    confirmed_attacker_ids.add(tid)

        # Remove mutual fight participants from single-victim list
        for tid in mutual_fight_ids:
            confirmed_victim_ids.discard(tid)

        # Construct Final Role and Telemetry per Tracked Person
        overall_status = "NORMAL"
        threat_level = "normal"
        has_bullying_alert = False

        for p in verified_persons:
            tid = p["track_id"]
            if tid in mutual_fight_ids:
                p["role"] = "attacker"
                p["action"] = "MUTUAL_FIGHT"
                p["action_label"] = "MUTUAL FIGHT"
                p["box_color"] = "RED"
                p["target_id"] = None
                p["confidence"] = 0.95
                has_bullying_alert = True
                threat_level = "aggressive"
                overall_status = "MUTUAL FIGHT / TWO-WAY AGGRESSION"
            elif tid in confirmed_attacker_ids and tid not in confirmed_victim_ids:
                rdata = active_roles[tid]
                p["role"] = "attacker"
                p["action"] = rdata["action"]
                act_suffix = rdata["action"].replace("_ATTACKER", "").replace("_", " ")
                p["action_label"] = f"BULLY — {act_suffix}"
                p["box_color"] = "RED"
                p["target_id"] = rdata["target_id"]
                p["confidence"] = round(rdata["confidence"], 2)
                has_bullying_alert = True
                threat_level = "bullying"
                overall_status = f"BULLY — {act_suffix} DETECTED"
            elif tid in confirmed_victim_ids:
                p["role"] = "victim"
                p["action"] = None
                p["action_label"] = "VICTIM"
                p["box_color"] = "GREEN"
                p["target_id"] = None
                p["confidence"] = 1.0
            else:
                p["role"] = "normal"
                p["action"] = None
                p["action_label"] = "NORMAL"
                p["box_color"] = "GREEN"
                p["target_id"] = None
                p["confidence"] = 1.0

        # Mark Rejected Screen / Photo Detections (Strict Alert Protection)
        for p in rejected_persons:
            v_status = p.get("verification_status", "REJECTED (SCREEN/PHOTO)")
            p["role"] = "normal"
            p["action"] = None
            p["action_label"] = f"REJECTED ({v_status})"
            p["box_color"] = "GREY"
            p["target_id"] = None
            p["confidence"] = p.get("real_person_score", 0.0)

        # 8. Multimodal Evidence Gating & Stream-Level Hysteresis State Machine
        rwf_gated_reason = None
        total_kinetic_motion = self._calc_total_kinetic_motion(tracked_persons, history_map)
        all_sedentary = len(tracked_persons) > 0 and all(
            self._is_sedentary_computer_pose(p, history_map[p["track_id"]]) for p in tracked_persons
        )

        frame_is_violent = False
        if has_bullying_alert:
            frame_is_violent = True
        elif rwf_violence:
            if len(tracked_persons) <= 1:
                rwf_gated_reason = f"Solitary Person (people_count={len(tracked_persons)} <= 1)"
            elif all_sedentary:
                rwf_gated_reason = "Sedentary Computer/Desk Pose Filter"
            elif total_kinetic_motion < 65.0:
                rwf_gated_reason = f"Low Kinetic Motion ({total_kinetic_motion:.1f} px/s < 65.0 px/s)"
            else:
                frame_is_violent = True

        # Stream-Level Hysteresis State Machine Update
        h_state = self.stream_hysteresis_state[camera_id]
        enter_req = self.THRESHOLDS["enter_attack_frames"] # 4 frames
        exit_req = self.THRESHOLDS["exit_attack_frames"]   # 6 frames

        if frame_is_violent:
            h_state["consecutive_high"] += 1
            h_state["consecutive_low"] = 0
            if h_state["state"] == "NORMAL" and h_state["consecutive_high"] >= enter_req:
                h_state["state"] = "ATTACK"
                h_state["consecutive_high"] = 0
                print(f"[HYSTERESIS STATE CHANGE] Camera {camera_id}: NORMAL -> ATTACK (Confirmed after {enter_req} consecutive high-violence frames)")
        else:
            h_state["consecutive_low"] += 1
            h_state["consecutive_high"] = 0
            if h_state["state"] == "ATTACK" and h_state["consecutive_low"] >= exit_req:
                h_state["state"] = "NORMAL"
                h_state["consecutive_low"] = 0
                print(f"[HYSTERESIS STATE CHANGE] Camera {camera_id}: ATTACK -> NORMAL (Returned to NORMAL after {exit_req} consecutive low-violence frames)")

        # Overall Status & State Machine Derivation for UI Presentation
        if h_state["state"] == "ATTACK":
            if h_state["consecutive_low"] > 0:
                ui_state_label = "RECOVERING"
                banner_title = "SAFECAM AI - RECOVERING"
                banner_status_text = "RECOVERING"
                banner_status_color = (0, 212, 255) # AMBER
                banner_border_color = (0, 212, 255)
                threat_level = "suspicious"
                overall_status = "RECOVERING — RETURNING TO SAFE"
            else:
                ui_state_label = "ALERT"
                banner_title = "SAFECAM AI - ALERT"
                if has_bullying_alert:
                    active_attacker_p = next((p for p in tracked_persons if p.get("role") == "attacker"), None)
                    act_suffix = active_attacker_p.get("action_label", "PHYSICAL VIOLENCE") if active_attacker_p else "PHYSICAL VIOLENCE"
                    overall_status = f"{act_suffix} DETECTED"
                    banner_status_text = f"{act_suffix} DETECTED"
                else:
                    overall_status = "VIOLENCE DETECTED"
                    banner_status_text = "VIOLENCE DETECTED"
                    for p in tracked_persons:
                        if p["role"] == "normal":
                            p["action_label"] = "UNKNOWN"
                banner_status_color = (0, 0, 255) # RED
                banner_border_color = (0, 0, 255)
                threat_level = "bullying" if has_bullying_alert else "aggressive"
        else:
            if h_state["consecutive_high"] > 0 or (rwf_violence and rwf_gated_reason is None):
                ui_state_label = "VERIFYING"
                banner_title = "SAFECAM AI - VERIFYING ACTIVITY"
                banner_status_text = "VERIFYING ACTIVITY"
                banner_status_color = (0, 212, 255) # AMBER
                banner_border_color = (0, 212, 255)
                threat_level = "suspicious"
                overall_status = "VERIFYING SUSPICIOUS ACTIVITY"
            elif len(tracked_persons) >= 2 and any(p.get("role") == "victim" for p in tracked_persons):
                ui_state_label = "VERIFYING"
                banner_title = "SAFECAM AI - VERIFYING ACTIVITY"
                banner_status_text = "VERIFYING ACTIVITY"
                banner_status_color = (0, 212, 255) # AMBER
                banner_border_color = (0, 212, 255)
                threat_level = "suspicious"
                overall_status = "SUSPICIOUS ACTIVITY"
            else:
                ui_state_label = "SAFE"
                banner_title = "SAFECAM AI - MONITORING"
                banner_status_text = "SAFE"
                banner_status_color = (0, 255, 0) # GREEN
                banner_border_color = (0, 212, 255)
                threat_level = "normal"
                overall_status = "SAFE"

        # 9. Terminal Output Printing & Detailed AI Debug Logs
        printed_map = self.last_printed_status[camera_id]
        for p in tracked_persons:
            tid = p["track_id"]
            curr_str = f"{tid}:{p['role']}:{p['action_label']}:{rwf_gated_reason}:{ui_state_label}"
            if printed_map.get(tid) != curr_str:
                printed_map[tid] = curr_str
                if p["role"] == "attacker":
                    print(f"[AI DEBUG] Person ID {tid} → RED → {p['action_label']} | UI State: {ui_state_label} | Feature: Pose Strike Vector & Proximity Pass")
                elif p["role"] == "victim":
                    print(f"[AI DEBUG] Person ID {tid} → GREEN → VICTIM | UI State: {ui_state_label} | Feature: Target of Confirmed Attacker")
                else:
                    if rwf_gated_reason:
                        print(f"[AI DEBUG] Person ID {tid} → GREEN → {p['action_label']} | UI State: {ui_state_label} | Feature: RWF Raw {int(rwf_prob*100)}% GATED ({rwf_gated_reason})")
                    else:
                        print(f"[AI DEBUG] Person ID {tid} → GREEN → {p['action_label']} | UI State: {ui_state_label} | Feature: Normal Activity")

        # 10. Render OpenCV Overlays directly on 1080p Frame
        annotated_frame = frame_1080p.copy()

        arm_connections = [(11, 13), (13, 15), (12, 14), (14, 16)]
        leg_connections = [(23, 25), (25, 27), (24, 26), (26, 28)]

        for person in tracked_persons:
            tid = person["track_id"]
            role = person["role"]
            action_label = person["action_label"]
            box_color_str = person["box_color"]

            bx1, by1, bx2, by2 = person["bbox_640"]
            x1_1080 = int(bx1 * scale_x)
            y1_1080 = int(by1 * scale_y)
            x2_1080 = int(bx2 * scale_x)
            y2_1080 = int(by2 * scale_y)

            # BGR Colors: Attacker = RED (0,0,255), Victim & Normal = GREEN (0,255,0), Rejected = GREY (120,120,120)
            if box_color_str == "RED":
                bgr_color = (0, 0, 255)
                text_color = (255, 255, 255)
            elif box_color_str == "GREY":
                bgr_color = (120, 120, 120)
                text_color = (220, 220, 220)
            else:
                bgr_color = (0, 255, 0)
                text_color = (0, 0, 0)

            # Draw Bounding Box
            cv2.rectangle(annotated_frame, (x1_1080, y1_1080), (x2_1080, y2_1080), bgr_color, 3)

            # Draw Bounding Box Badge Label
            label_text = f"ID: {tid} | {action_label}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated_frame, (x1_1080, max(0, y1_1080 - 28)), (x1_1080 + tw + 12, y1_1080), bgr_color, -1)
            cv2.putText(annotated_frame, label_text, (x1_1080 + 6, max(18, y1_1080 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)

            # Draw Skeleton & Joints
            pose = person["pose_landmarks"]
            if pose:
                joints_1080 = {}
                for idx, lm in pose.items():
                    jx_1080 = int(lm["x"] * scale_x)
                    jy_1080 = int(lm["y"] * scale_y)
                    joints_1080[idx] = (jx_1080, jy_1080)

                for idx1, idx2 in arm_connections:
                    if idx1 in joints_1080 and idx2 in joints_1080:
                        cv2.line(annotated_frame, joints_1080[idx1], joints_1080[idx2], (0, 225, 255), 2)

                for idx1, idx2 in leg_connections:
                    if idx1 in joints_1080 and idx2 in joints_1080:
                        cv2.line(annotated_frame, joints_1080[idx1], joints_1080[idx2], (255, 0, 200), 2)

                for idx in [11, 12, 13, 14, 15, 16]:
                    if idx in joints_1080:
                        cv2.circle(annotated_frame, joints_1080[idx], 6, (0, 212, 255), -1)

                for idx in [23, 24, 25, 26, 27, 28]:
                    if idx in joints_1080:
                        cv2.circle(annotated_frame, joints_1080[idx], 6, (255, 0, 150), -1)

        # 11. Compact HUD Panel (Professional CCTV Security Overlay)
        # Derive ACTIVITY and THREAT LEVEL from ui_state_label
        if ui_state_label == "SAFE":
            activity_text = "NORMAL"
            threat_level_display = "LOW"
            if rwf_prob >= 0.50:
                conf_text = f"Violence: {int(rwf_prob * 100)}%"
            else:
                conf_text = f"Normal: {int((1.0 - rwf_prob) * 100)}%"
        elif ui_state_label == "VERIFYING":
            activity_text = "SUSPICIOUS MOVEMENT"
            threat_level_display = "ELEVATED"
            conf_text = f"Violence: {int(rwf_prob * 100)}%"
        elif ui_state_label == "ALERT":
            if has_bullying_alert:
                active_attacker_p = next((p for p in tracked_persons if p.get("role") == "attacker"), None)
                act_suffix = active_attacker_p.get("action_label", "PHYSICAL VIOLENCE") if active_attacker_p else "PHYSICAL VIOLENCE"
                activity_text = act_suffix.replace("BULLY — ", "")
            else:
                activity_text = "PHYSICAL ALTERCATION"
            threat_level_display = "HIGH"
            conf_text = f"Violence: {int(rwf_prob * 100)}%"
        elif ui_state_label == "RECOVERING":
            activity_text = "DE-ESCALATING"
            threat_level_display = "ELEVATED"
            if rwf_prob >= 0.50:
                conf_text = f"Violence: {int(rwf_prob * 100)}%"
            else:
                conf_text = f"Normal: {int((1.0 - rwf_prob) * 100)}%"
        else:
            activity_text = "UNKNOWN"
            threat_level_display = "LOW"
            conf_text = f"Normal: {int((1.0 - rwf_prob) * 100)}%"

        # Compact panel dimensions (~22% of 1920px width)
        px, py = 12, 10  # top-left margin from frame edge
        pw, ph = 390, 110  # panel width x height
        banner_bg = (11, 17, 32)

        # Semi-transparent background overlay
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (px, py), (px + pw, py + ph), banner_bg, -1)
        cv2.addWeighted(overlay, 0.85, annotated_frame, 0.15, 0, annotated_frame)

        # Thin border + left accent stripe
        cv2.rectangle(annotated_frame, (px, py), (px + pw, py + ph), banner_border_color, 1)
        cv2.rectangle(annotated_frame, (px, py), (px + 3, py + ph), banner_status_color, -1)

        lx = px + 10  # left text margin
        dim = (130, 145, 165)  # muted gray
        bright = (235, 240, 248)  # near-white

        # Use ASCII-only banner title (no Unicode bullet)
        banner_title_ascii = banner_title.replace(" \u2022 ", " - ").replace("\u2022", "-")

        # Row 1 (y=py+16): Title with status dot
        cv2.circle(annotated_frame, (lx + 3, py + 14), 4, banner_status_color, -1)
        cv2.putText(annotated_frame, banner_title_ascii, (lx + 12, py + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, bright, 1)

        # Row 2 (y=py+32): CAM + PEOPLE (two-column)
        cam_short = camera_id[-12:] if len(camera_id) > 12 else camera_id
        cv2.putText(annotated_frame, f"CAM: {cam_short}", (lx, py + 33), cv2.FONT_HERSHEY_SIMPLEX, 0.32, dim, 1)
        cv2.putText(annotated_frame, f"PEOPLE: {len(tracked_persons)}", (lx + 230, py + 33), cv2.FONT_HERSHEY_SIMPLEX, 0.32, dim, 1)

        # Row 3 (y=py+52): STATUS — most prominent (larger, bold, state-colored)
        cv2.putText(annotated_frame, f"STATUS: {banner_status_text}", (lx, py + 54), cv2.FONT_HERSHEY_SIMPLEX, 0.48, banner_status_color, 2)

        # Row 4 (y=py+70): ACTIVITY
        cv2.putText(annotated_frame, f"ACTIVITY: {activity_text}", (lx, py + 72), cv2.FONT_HERSHEY_SIMPLEX, 0.32, bright, 1)

        # Row 5 (y=py+88): Confidence + Threat Level (two-column)
        cv2.putText(annotated_frame, conf_text, (lx, py + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.32, dim, 1)

        if threat_level_display == "HIGH":
            tl_color = (0, 0, 255)
        elif threat_level_display == "ELEVATED":
            tl_color = (0, 212, 255)
        else:
            tl_color = (0, 255, 0)
        cv2.putText(annotated_frame, f"THREAT: {threat_level_display}", (lx + 230, py + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.32, tl_color, 1)

        # Store for telemetry JSON
        confidence_label = conf_text

        # Update Single Source of Truth Backend Alarm State Machine
        temp_telemetry_for_alarm = {
            "camera_id": camera_id,
            "people_count": len(tracked_persons),
            "tracked_persons": tracked_persons,
            "fight_probability": rwf_prob,
            "status": overall_status,
            "threat_level": threat_level
        }
        camera_alarm_state = alarm_manager.update_camera_state(camera_id, annotated_frame, temp_telemetry_for_alarm)

        ai_telemetry = {
            "camera_id": camera_id,
            "people_count": len(tracked_persons),
            "status": overall_status,
            "threat_level": threat_level,
            "threat_level_display": threat_level_display,
            "activity": activity_text,
            "tracked_persons": tracked_persons,
            "fight_probability": rwf_prob,
            "nonfight_probability": rwf_res.get("nonfight_probability", 1.0),
            "violence_detected": rwf_violence,
            "confidence": rwf_res.get("confidence", 1.0),
            "confidence_label": confidence_label,
            "rwf_class": rwf_res.get("class_name", "NonFight"),
            "epoch": rwf_res.get("epoch", "LSTM-v1"),
            "model_architecture": rwf_res.get("model_architecture", "RWF-LSTM"),
            "yolo_ms": round(yolo_ms, 1),
            "mediapipe_ms": round(mediapipe_ms, 1),
            "rwf_lstm_ms": round(rwf_lstm_ms, 1),
            "total_ai_ms": round(total_ai_ms, 1),
            "alarm_state": camera_alarm_state
        }

        return annotated_frame, ai_telemetry

    def _evaluate_attack_action(self, p1, p2, h1, h2, rwf_prob):
        """
        Evaluates limb vectors, velocity, extension, and proximity from p1 toward p2.
        Applies scale-invariant height normalization to prevent distance/perspective bias.
        Returns: (action_name, confidence_score) or (None, 0.0)
        """
        if len(h1) < 3:
            return None, 0.0

        target_bbox = p2["bbox_640"]
        target_center = ((target_bbox[0] + target_bbox[2]) / 2.0, (target_bbox[1] + target_bbox[3]) / 2.0)

        # Scale Normalization Factor based on person 1 bbox height (200px baseline in 640 space)
        p1_bbox_h = max(30.0, p1["bbox_640"][3] - p1["bbox_640"][1])
        scale_norm = max(0.35, min(2.5, p1_bbox_h / 200.0))

        # Dynamic Scale-Invariant Thresholds
        thresh_punch_dist = self.THRESHOLDS["punch_strike_dist"] * scale_norm
        thresh_punch_speed = self.THRESHOLDS["punch_wrist_speed"] * scale_norm
        thresh_kick_dist = self.THRESHOLDS["kick_strike_dist"] * scale_norm
        thresh_kick_speed = self.THRESHOLDS["kick_ankle_speed"] * scale_norm
        thresh_push_dist = self.THRESHOLDS["push_dist_px"] * scale_norm
        thresh_push_speed = self.THRESHOLDS["push_wrist_speed"] * scale_norm
        thresh_contact_dist = self.THRESHOLDS["sustained_contact_dist"] * scale_norm

        pose1 = p1["pose_landmarks"] or {}
        lshoulder, rshoulder = pose1.get(11), pose1.get(12)
        lelbow, relbow = pose1.get(13), pose1.get(14)
        lwrist, rwrist = pose1.get(15), pose1.get(16)
        lhip, rhip = pose1.get(23), pose1.get(24)
        lknee, rknee = pose1.get(25), pose1.get(26)
        lankle, rankle = pose1.get(27), pose1.get(28)

        # 1. PUNCH DETECTION EVALUATION
        for wrist_idx, wrist_pt, sh_pt, el_pt in [
            (15, lwrist, lshoulder, lelbow),
            (16, rwrist, rshoulder, relbow)
        ]:
            if wrist_pt and sh_pt and el_pt:
                # Arm extension ratio
                dist_sw = math.hypot(wrist_pt["x"] - sh_pt["x"], wrist_pt["y"] - sh_pt["y"])
                dist_se = math.hypot(el_pt["x"] - sh_pt["x"], el_pt["y"] - sh_pt["y"])
                dist_ew = math.hypot(wrist_pt["x"] - el_pt["x"], wrist_pt["y"] - el_pt["y"])
                arm_ext = dist_sw / (dist_se + dist_ew + 1e-5)

                # Wrist speed & direction
                w_speed, w_dir = self._calc_point_velocity(h1, "lwrist" if wrist_idx == 15 else "rwrist")

                # Distance to target rectangle
                dist_to_target = self._dist_point_to_rect((wrist_pt["x"], wrist_pt["y"]), target_bbox)

                # Direction vector toward target center
                v_to_target = (target_center[0] - wrist_pt["x"], target_center[1] - wrist_pt["y"])
                mag_t = math.hypot(v_to_target[0], v_to_target[1])
                dot_dir = 0.0
                if mag_t > 0 and w_dir is not None:
                    dot_dir = (w_dir[0] * v_to_target[0] + w_dir[1] * v_to_target[1]) / mag_t

                if (
                    arm_ext >= self.THRESHOLDS["punch_arm_ext_ratio"]
                    and w_speed >= thresh_punch_speed
                    and dot_dir > 0.40
                    and dist_to_target <= thresh_punch_dist
                ):
                    return "PUNCH_ATTACKER", min(0.99, 0.75 + (w_speed / (400.0 * scale_norm)))

        # 2. KICK DETECTION EVALUATION
        for ankle_idx, ankle_pt, hip_pt, knee_pt in [
            (27, lankle, lhip, lknee),
            (28, rankle, rhip, rknee)
        ]:
            if ankle_pt and hip_pt and knee_pt:
                dist_ha = math.hypot(ankle_pt["x"] - hip_pt["x"], ankle_pt["y"] - hip_pt["y"])
                dist_hk = math.hypot(knee_pt["x"] - hip_pt["x"], knee_pt["y"] - hip_pt["y"])
                dist_ka = math.hypot(ankle_pt["x"] - knee_pt["x"], ankle_pt["y"] - knee_pt["y"])
                leg_ext = dist_ha / (dist_hk + dist_ka + 1e-5)

                a_speed, a_dir = self._calc_point_velocity(h1, "lankle" if ankle_idx == 27 else "rankle")
                dist_to_target = self._dist_point_to_rect((ankle_pt["x"], ankle_pt["y"]), target_bbox)

                is_elevated = ankle_pt["y"] < (hip_pt["y"] + self.THRESHOLDS["kick_ankle_elevation_offset"] * p1_bbox_h)

                v_to_target = (target_center[0] - ankle_pt["x"], target_center[1] - ankle_pt["y"])
                mag_t = math.hypot(v_to_target[0], v_to_target[1])
                dot_dir = 0.0
                if mag_t > 0 and a_dir is not None:
                    dot_dir = (a_dir[0] * v_to_target[0] + a_dir[1] * v_to_target[1]) / mag_t

                if (
                    (is_elevated or leg_ext > 0.80)
                    and a_speed >= thresh_kick_speed
                    and dot_dir > 0.40
                    and dist_to_target <= thresh_kick_dist
                ):
                    return "KICK_ATTACKER", min(0.99, 0.75 + (a_speed / (400.0 * scale_norm)))

        # 3. PUSH DETECTION EVALUATION
        if lwrist and rwrist:
            dist_lw = self._dist_point_to_rect((lwrist["x"], lwrist["y"]), target_bbox)
            dist_rw = self._dist_point_to_rect((rwrist["x"], rwrist["y"]), target_bbox)
            lw_speed, _ = self._calc_point_velocity(h1, "lwrist")
            rw_speed, _ = self._calc_point_velocity(h1, "rwrist")

            if (
                dist_lw <= thresh_push_dist
                and dist_rw <= thresh_push_dist
                and (lw_speed >= thresh_push_speed or rw_speed >= thresh_push_speed)
            ):
                return "PUSH_ATTACKER", 0.85

        # 4. HIT FALLBACK DETECTION EVALUATION
        for wrist_key in ["lwrist", "rwrist"]:
            wpt = lwrist if wrist_key == "lwrist" else rwrist
            if wpt:
                w_speed, w_dir = self._calc_point_velocity(h1, wrist_key)
                dist_to_target = self._dist_point_to_rect((wpt["x"], wpt["y"]), target_bbox)
                if w_speed >= (130.0 * scale_norm) and dist_to_target <= (60.0 * scale_norm):
                    return "HIT_ATTACKER", 0.80

        # 5. AGGRESSIVE CONTACT EVALUATION
        dist_centers = math.hypot(
            (p1["bbox_640"][0] + p1["bbox_640"][2]) / 2.0 - target_center[0],
            (p1["bbox_640"][1] + p1["bbox_640"][3]) / 2.0 - target_center[1]
        )
        if dist_centers <= thresh_contact_dist and (rwf_prob > 0.65 or len(h1) >= 6):
            w_speed_1 = self._calc_wrist_speed(h1)
            if w_speed_1 > (120.0 * scale_norm):
                return "AGGRESSIVE_CONTACT", 0.78

        return None, 0.0

    def _calc_point_velocity(self, history_deque, point_key):
        """Calculates instantaneous velocity (px/s) and unit direction vector for a landmark key"""
        if len(history_deque) < 2:
            return 0.0, None

        h_list = list(history_deque)
        curr = h_list[-1][point_key]
        prev = h_list[-2][point_key]

        if curr is None or prev is None:
            return 0.0, None

        dt = h_list[-1]["time"] - h_list[-2]["time"]
        if dt <= 0:
            return 0.0, None

        dx = curr[0] - prev[0]
        dy = curr[1] - prev[1]
        dist = math.hypot(dx, dy)
        speed = dist / dt

        if dist > 0:
            dir_vec = (dx / dist, dy / dist)
        else:
            dir_vec = (0.0, 0.0)

        return speed, dir_vec

    def _dist_point_to_rect(self, point, rect):
        """Calculates minimum distance from a 2D point (px, py) to rectangle [x1, y1, x2, y2]"""
        px, py = point
        rx1, ry1, rx2, ry2 = rect
        dx = max(rx1 - px, 0, px - rx2)
        dy = max(ry1 - py, 0, py - ry2)
        return math.hypot(dx, dy)

    def _calc_wrist_speed(self, history_deque):
        """Calculates maximum wrist velocity over recent frames"""
        if len(history_deque) < 2:
            return 0.0

        max_speed = 0.0
        h_list = list(history_deque)
        for i in range(1, len(h_list)):
            dt = h_list[i]["time"] - h_list[i-1]["time"]
            if dt <= 0:
                continue

            for wrist_key in ["lwrist", "rwrist"]:
                w_curr = h_list[i][wrist_key]
                w_prev = h_list[i-1][wrist_key]
                if w_curr and w_prev:
                    dist = math.hypot(w_curr[0] - w_prev[0], w_curr[1] - w_prev[1])
                    speed = dist / dt
                    if speed > max_speed:
                        max_speed = speed

        return max_speed

    def _check_chasing(self, h1, h2):
        """Checks trajectory direction consistency indicating chasing/following"""
        if len(h1) < 8 or len(h2) < 8:
            return False

        h1_list = list(h1)
        h2_list = list(h2)

        v1_x = h1_list[-1]["center"][0] - h1_list[0]["center"][0]
        v1_y = h1_list[-1]["center"][1] - h1_list[0]["center"][1]

        v2_x = h2_list[-1]["center"][0] - h2_list[0]["center"][0]
        v2_y = h2_list[-1]["center"][1] - h2_list[0]["center"][1]

        mag1 = math.hypot(v1_x, v1_y)
        mag2 = math.hypot(v2_x, v2_y)

        if mag1 > 40 and mag2 > 40:
            dot = (v1_x * v2_x + v1_y * v2_y) / (mag1 * mag2)
            if dot > 0.85:
                return True

        return False

    def _is_sedentary_computer_pose(self, person, history):
        """
        Detects if a person is in a benign sedentary desk / computer-use pose.
        Criteria:
        - Low wrist velocity (< 60 px/s)
        - Arm extension ratio < 0.80
        """
        if not history or len(history) < 2:
            return True

        max_w_speed = self._calc_wrist_speed(history)
        if max_w_speed > 60.0:
            return False # High speed movement -> Not sedentary typing/sitting

        pose = person.get("pose_landmarks") or {}
        lsh, rsh = pose.get(11), pose.get(12)
        lel, rel = pose.get(13), pose.get(14)
        lwr, rwr = pose.get(15), pose.get(16)

        arm_ext_left, arm_ext_right = 0.0, 0.0
        if lsh and lel and lwr:
            dist_sw = math.hypot(lwr["x"] - lsh["x"], lwr["y"] - lsh["y"])
            dist_se = math.hypot(lel["x"] - lsh["x"], lel["y"] - lsh["y"])
            dist_ew = math.hypot(lwr["x"] - lel["x"], lwr["y"] - lel["y"])
            arm_ext_left = dist_sw / (dist_se + dist_ew + 1e-5)

        if rsh and rel and rwr:
            dist_sw = math.hypot(rwr["x"] - rsh["x"], rwr["y"] - rsh["y"])
            dist_se = math.hypot(rel["x"] - rsh["x"], rel["y"] - rsh["y"])
            dist_ew = math.hypot(rwr["x"] - rel["x"], rwr["y"] - rel["y"])
            arm_ext_right = dist_sw / (dist_se + dist_ew + 1e-5)

        if max(arm_ext_left, arm_ext_right) > 0.80:
            return False # Extended arm strike posture -> Not computer typing

        return True

    def _calc_total_kinetic_motion(self, tracked_persons, history_map):
        """Calculates combined multi-joint kinetic speed (px/s) across all persons in view."""
        total_kinetic = 0.0
        for p in tracked_persons:
            h = history_map[p["track_id"]]
            w_speed = self._calc_wrist_speed(h)
            total_kinetic += w_speed
        return total_kinetic

