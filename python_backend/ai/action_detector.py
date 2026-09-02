"""
SAFECAM — Action Detector Component (Rebuilt Per-Track Decision Engine)
========================================================================
Uses custom YOLO11n model (best_v1.pt) to classify actions (PUNCH, KICK, NORMAL).
Maintains an independent, persistent per-track temporal state machine for every ByteTrack ID:
  - Temporal frame confirmation (MIN_ACTION_FRAMES)
  - Confidence margin check over NORMAL / background
  - Dynamic motion velocity calculation to suppress static boxing stances & poses
  - Hysteresis to prevent PUNCH/KICK oscillation
  - Action recovery decay back to NORMAL
  - Strict ONE PERSON = ONE ACTION STATE guarantee
"""

import os
import time
import numpy as np
from typing import List, Dict, Tuple, NamedTuple, Optional

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

try:
    from tracking.tracker import TrackedPerson
except ImportError:
    from python_backend.tracking.tracker import TrackedPerson

try:
    from alarm_config import alarm_config
except ImportError:
    from python_backend.alarm_config import alarm_config


class ActionPrediction(NamedTuple):
    action_class: str     # "PUNCH", "KICK", "NORMAL"
    confidence:   float
    x1: int
    y1: int
    x2: int
    y2: int
    track_id:     Optional[int] = None   # Associated TrackedPerson ID


class TrackActionState:
    """
    Independent temporal action state per ByteTrack ID.
    """
    def __init__(self, track_id: int):
        self.track_id: int = track_id
        self.current_action: str = "NORMAL"        # Final confirmed action: "NORMAL", "PUNCH", "KICK"
        self.candidate_action: str = "NORMAL"      # Candidate action being evaluated over N frames
        self.candidate_count: int = 0              # Consecutive frames candidate observed above threshold
        self.action_confidence: float = 0.0        # Confidence score of confirmed current_action

        # Raw frame probabilities
        self.raw_punch_conf: float = 0.0
        self.raw_kick_conf: float = 0.0
        self.raw_normal_conf: float = 1.0
        self.last_raw_action: str = "NORMAL"
        self.last_raw_conf: float = 0.0

        # Motion & Bbox history for static pose / boxing stance suppression
        self.bbox_history: List[Tuple[float, float, float, float, float]] = []  # (cx, cy, w, h, ts)

        # Timing and state counters
        self.recovery_count: int = 0               # Frames spent decaying back to NORMAL
        self.cooldown_count: int = 0               # Cooldown frames post-action
        self.last_updated: float = time.time()
        self.target_id: Optional[int] = None
        self.role: str = "NORMAL"                  # "NORMAL", "ATTACKER", "VICTIM"
        self.debug_reason: str = "Below threshold"

    def update_bbox(self, cx: float, cy: float, w: float, h: float, ts: float):
        """Appends bounding box position and timestamp for temporal motion analysis."""
        self.bbox_history.append((cx, cy, w, h, ts))
        if len(self.bbox_history) > 10:
            self.bbox_history.pop(0)

    def compute_motion_velocity(self, frame_diag: float = 2200.0) -> float:
        """
        Calculates normalized motion speed & bbox dimension expansion rate over frame history.
        Distinguishes active punching/kicking motion from static boxing stances or standing poses.
        """
        if len(self.bbox_history) < 2:
            return 0.0

        prev_cx, prev_cy, prev_w, prev_h, _ = self.bbox_history[0]
        curr_cx, curr_cy, curr_w, curr_h, _ = self.bbox_history[-1]

        # Center displacement
        disp = ((curr_cx - prev_cx) ** 2 + (curr_cy - prev_cy) ** 2) ** 0.5
        disp_norm = disp / frame_diag

        # Dimension expansion/contraction velocity
        dim_change = (abs(curr_w - prev_w) + abs(curr_h - prev_h)) / frame_diag

        frames_diff = len(self.bbox_history) - 1
        motion_v = (disp_norm + dim_change) / max(1, frames_diff)
        return motion_v

    def __repr__(self) -> str:
        return (
            f"TrackState(ID={self.track_id}, action={self.current_action}, "
            f"cand={self.candidate_action}[{self.candidate_count}], "
            f"conf={self.action_confidence:.2f}, role={self.role})"
        )


class ActionDetector:
    """
    Action Classification Engine with Per-Track Temporal Decision Logic.
    Executes inference using custom best_v1.pt and manages per-track temporal state.
    """

    def __init__(self, model_path: str = None, imgsz: int = 640, device: str = "cpu", conf_thresh: float = 0.05):
        self.model_path = model_path or alarm_config.MODEL_PATH
        self.imgsz = imgsz or alarm_config.YOLO_IMGSZ
        self.device = device or alarm_config.YOLO_DEVICE
        self.conf_thresh = conf_thresh
        self.model = None
        self.api_available = False
        self.class_map = {}

        # Configurable decision thresholds
        self.action_conf_thresh  = getattr(alarm_config, "ACTION_CONFIDENCE_THRESHOLD", 0.65)
        self.margin_thresh        = getattr(alarm_config, "ACTION_MARGIN_THRESHOLD", 0.15)
        self.min_action_frames   = getattr(alarm_config, "MIN_ACTION_FRAMES", 3)
        self.recovery_frames     = getattr(alarm_config, "ACTION_RECOVERY_FRAMES", 4)
        self.cooldown_frames     = getattr(alarm_config, "ACTION_COOLDOWN_FRAMES", 5)
        self.min_motion_velocity = getattr(alarm_config, "MIN_MOTION_VELOCITY_NORM", 0.003)
        self.debug_logging       = getattr(alarm_config, "DEBUG_ACTION_LOGGING", False)

        # Per-track persistent states {track_id -> TrackActionState}
        self.track_states: Dict[int, TrackActionState] = {}

        if ULTRALYTICS_AVAILABLE and os.path.exists(self.model_path):
            try:
                self.model = YOLO(self.model_path)
                self.api_available = True

                raw_names = self.model.names
                print(f"[ACTION DETECTOR] Model loaded OK: {self.model_path}")
                print(f"[ACTION DETECTOR] model.names = {raw_names}")

                for cls_id, name in raw_names.items():
                    n_lower = name.lower()
                    if "punch" in n_lower:
                        self.class_map[cls_id] = "PUNCH"
                    elif "kick" in n_lower:
                        self.class_map[cls_id] = "KICK"
                    elif "normal" in n_lower:
                        self.class_map[cls_id] = "NORMAL"
                    else:
                        self.class_map[cls_id] = name.upper()

                print(f"[ACTION DETECTOR] Class mapping built: {self.class_map}")
            except Exception as e:
                print(f"[ACTION DETECTOR ERROR] Failed to load action model: {e}")

    def get_track_state(self, track_id: int) -> TrackActionState:
        """Returns or initializes the TrackActionState for a given track_id."""
        if track_id not in self.track_states:
            self.track_states[track_id] = TrackActionState(track_id)
        return self.track_states[track_id]

    def _purge_stale_tracks(self, active_track_ids: List[int]):
        """Cleans up state for tracks no longer visible."""
        active_set = set(active_track_ids)
        stale_ids = [tid for tid in self.track_states if tid not in active_set]
        for tid in stale_ids:
            if time.time() - self.track_states[tid].last_updated > 10.0:
                del self.track_states[tid]

    def detect_and_associate(
        self,
        frame_1080p: np.ndarray,
        tracked_persons: List[TrackedPerson]
    ) -> Tuple[List[ActionPrediction], Dict[int, str]]:
        """
        Runs action inference and updates per-track temporal decision state.
        Guarantees STRICT ONE PERSON = ONE ACTION STATE (NORMAL, PUNCH, or KICK).
        Returns:
          - predictions: List of ActionPrediction (exactly 1 per tracked person)
          - person_action_map: Dict[track_id -> "NORMAL" | "PUNCH" | "KICK"]
        """
        if frame_1080p is None or not self.api_available or self.model is None or not tracked_persons:
            return [], {tp.track_id: "NORMAL" for tp in tracked_persons}

        active_ids = [tp.track_id for tp in tracked_persons]
        self._purge_stale_tracks(active_ids)

        fh, fw = frame_1080p.shape[:2]
        frame_diag = (fw * fw + fh * fh) ** 0.5
        predictions: List[ActionPrediction] = []
        now_ts = time.time()

        # Update per-track bbox history first
        for tp in tracked_persons:
            st = self.get_track_state(tp.track_id)
            det = tp.detection
            st.update_bbox(float(det.cx), float(det.cy), float(det.width), float(det.height), now_ts)

        # Dict to store raw max detections per person for current frame: track_id -> {action: conf}
        raw_person_detections: Dict[int, Dict[str, float]] = {
            tp.track_id: {"PUNCH": 0.0, "KICK": 0.0, "NORMAL": 0.0}
            for tp in tracked_persons
        }

        try:
            # 1. Full Frame Inference (Pre-filtering with conf=0.05)
            results = self.model(
                frame_1080p,
                imgsz=self.imgsz,
                device=self.device,
                conf=self.conf_thresh,
                verbose=False
            )

            if results and len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        action_label = self.class_map.get(cls_id, "NORMAL")

                        matched_tp = self._find_matching_person(x1, y1, x2, y2, tracked_persons)
                        if matched_tp is not None:
                            curr_conf = raw_person_detections[matched_tp.track_id].get(action_label, 0.0)
                            raw_person_detections[matched_tp.track_id][action_label] = max(curr_conf, conf)

            # 2. Person Crop ROI Inference (Padded by 25% horizontally / 15% vertically)
            for tp in tracked_persons:
                pdet = tp.detection
                pw, ph = pdet.width, pdet.height
                pad_x, pad_y = int(pw * 0.25), int(ph * 0.15)

                cx1 = max(0, pdet.x1 - pad_x)
                cy1 = max(0, pdet.y1 - pad_y)
                cx2 = min(fw, pdet.x2 + pad_x)
                cy2 = min(fh, pdet.y2 + pad_y)

                if (cx2 - cx1) < 40 or (cy2 - cy1) < 40:
                    continue

                crop = frame_1080p[cy1:cy2, cx1:cx2]
                c_results = self.model(crop, imgsz=self.imgsz, device=self.device, conf=self.conf_thresh, verbose=False)

                if c_results and len(c_results) > 0:
                    c_boxes = c_results[0].boxes
                    if c_boxes is not None and len(c_boxes) > 0:
                        for c_box in c_boxes:
                            c_cls_id = int(c_box.cls[0].item())
                            c_conf = float(c_box.conf[0].item())
                            c_label = self.class_map.get(c_cls_id, "NORMAL")
                            curr_conf = raw_person_detections[tp.track_id].get(c_label, 0.0)
                            raw_person_detections[tp.track_id][c_label] = max(curr_conf, c_conf)

        except Exception as e:
            print(f"[ACTION DETECTOR ERROR] Inference error: {e}")

        # ---------------------------------------------------------------------
        # 3. TEMPORAL STATE MACHINE, MOTION CHECK & HYSTERESIS PER TRACK
        # ---------------------------------------------------------------------
        person_action_map: Dict[int, str] = {}

        for tp in tracked_persons:
            tid = tp.track_id
            st = self.get_track_state(tid)
            st.last_updated = now_ts

            raw_scores = raw_person_detections[tid]
            st.raw_punch_conf = raw_scores.get("PUNCH", 0.0)
            st.raw_kick_conf  = raw_scores.get("KICK", 0.0)
            st.raw_normal_conf = raw_scores.get("NORMAL", 0.0)

            # Compute motion velocity over frame history
            motion_v = st.compute_motion_velocity(frame_diag=frame_diag)

            # Determine best raw action candidate for this frame
            raw_cand = "NORMAL"
            raw_conf = 0.0

            best_attack_act = "PUNCH" if st.raw_punch_conf >= st.raw_kick_conf else "KICK"
            best_attack_conf = max(st.raw_punch_conf, st.raw_kick_conf)
            second_conf = st.raw_kick_conf if best_attack_act == "PUNCH" else st.raw_punch_conf

            # Require confidence threshold AND margin over NORMAL and secondary action
            if best_attack_conf < self.action_conf_thresh:
                st.debug_reason = f"Raw conf {best_attack_conf:.2f} < thresh {self.action_conf_thresh:.2f}"
            elif (best_attack_conf - st.raw_normal_conf) < self.margin_thresh:
                st.debug_reason = f"Margin over NORMAL ({best_attack_conf - st.raw_normal_conf:.2f}) < {self.margin_thresh:.2f}"
            elif (best_attack_conf - second_conf) < self.margin_thresh:
                st.debug_reason = f"Margin over secondary action ({best_attack_conf - second_conf:.2f}) < {self.margin_thresh:.2f}"
            else:
                # PREVENT BOXING STANCE & STATIC POSE HALLUCINATION:
                # If motion velocity is near 0 (static pose / standing in stance / raised arm/leg)
                # and raw conf is not overwhelming (>0.92), override raw candidate to NORMAL.
                if motion_v < self.min_motion_velocity and best_attack_conf < 0.92:
                    raw_cand = "NORMAL"
                    raw_conf = 0.0
                    st.debug_reason = f"Motion velocity ({motion_v:.4f}) < {self.min_motion_velocity} with conf {best_attack_conf:.2f} < 0.92"
                else:
                    raw_cand = best_attack_act
                    raw_conf = best_attack_conf
                    st.debug_reason = f"Candidate {raw_cand} accepted (conf={raw_conf:.2f}, motion={motion_v:.4f})"

            st.last_raw_action = raw_cand
            st.last_raw_conf   = raw_conf

            # Maintain cooldown if active
            if st.cooldown_count > 0:
                st.cooldown_count -= 1
                raw_cand = "NORMAL"

            # Temporal Accumulation & State Transitions
            if raw_cand in ("PUNCH", "KICK"):
                if raw_cand == st.candidate_action:
                    st.candidate_count += 1
                else:
                    st.candidate_action = raw_cand
                    st.candidate_count = 1

                # Check transition to current_action
                if st.current_action == "NORMAL":
                    if st.candidate_count >= self.min_action_frames:
                        st.current_action = raw_cand
                        st.action_confidence = raw_conf
                        st.recovery_count = 0
                elif st.current_action in ("PUNCH", "KICK"):
                    if raw_cand == st.current_action:
                        st.action_confidence = max(st.action_confidence, raw_conf)
                        st.recovery_count = 0
                    else:
                        # Prevent flip-flop / oscillation between PUNCH and KICK:
                        # Require candidate_count >= min_action_frames for the new candidate
                        if st.candidate_count >= self.min_action_frames:
                            st.current_action = raw_cand
                            st.action_confidence = raw_conf
                            st.recovery_count = 0
            else:
                # Raw candidate is NORMAL: decay candidate count gradually to tolerate 1-frame detection flickers
                if st.candidate_count > 0:
                    st.candidate_count -= 1
                    if st.candidate_count == 0:
                        st.candidate_action = "NORMAL"

                if st.current_action in ("PUNCH", "KICK"):
                    # Enter RECOVERY phase before returning to NORMAL
                    st.recovery_count += 1
                    if st.recovery_count >= self.recovery_frames:
                        st.current_action = "NORMAL"
                        st.action_confidence = 0.0
                        st.recovery_count = 0
                        st.cooldown_count = self.cooldown_frames

            # Guarantee ONE PERSON = ONE ACTION STATE
            person_action_map[tid] = st.current_action

            # Construct ActionPrediction payload (strictly 1 prediction per person)
            pdet = tp.detection
            predictions.append(ActionPrediction(
                action_class=st.current_action,
                confidence=st.action_confidence if st.current_action != "NORMAL" else pdet.confidence,
                x1=pdet.x1, y1=pdet.y1, x2=pdet.x2, y2=pdet.y2,
                track_id=tid
            ))

            # Configurable debug logging per track
            if self.debug_logging:
                print(
                    f"ID={tid} raw={st.last_raw_action}:{st.last_raw_conf:.2f} "
                    f"(P:{st.raw_punch_conf:.2f} K:{st.raw_kick_conf:.2f} N:{st.raw_normal_conf:.2f}) "
                    f"smoothed={st.current_action}:{st.action_confidence:.2f} "
                    f"candidate={st.candidate_action}[{st.candidate_count}/{self.min_action_frames}] "
                    f"target={st.target_id} state={st.role}"
                )

        return predictions, person_action_map

    def _find_matching_person(
        self,
        ax1: int, ay1: int, ax2: int, ay2: int,
        persons: List[TrackedPerson]
    ) -> Optional[TrackedPerson]:
        """Matches action bounding box to the best overlapping tracked person."""
        best_tp = None
        best_score = -1.0
        acx, acy = (ax1 + ax2) // 2, (ay1 + ay2) // 2

        for tp in persons:
            pdet = tp.detection
            ix1, iy1 = max(ax1, pdet.x1), max(ay1, pdet.y1)
            ix2, iy2 = min(ax2, pdet.x2), min(ay2, pdet.y2)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            p_area = max(1, pdet.area)
            iou = inter / p_area

            dist = ((acx - pdet.cx) ** 2 + (acy - pdet.cy) ** 2) ** 0.5
            score = (iou * 2.0) - (dist / 1000.0)

            if score > best_score:
                best_score = score
                best_tp = tp

        return best_tp
