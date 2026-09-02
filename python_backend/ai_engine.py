"""
SAFECAM AI Engine — Rebuilt Modular Architecture
=================================================
Orchestrates the 7 clean AI sub-components:
  1. PersonDetector        — COCO Person Detector (yolo11n.pt, classes=[0])
  2. PersonTrackerWrapper  — ByteTrack / LightweightTracker
  3. ActionDetector        — Custom Action YOLO11n (best_v1.pt: PUNCH, KICK, NORMAL)
  4. InteractionDetector   — 2+ Person Pair Geometry & Motion Direction
  5. ContactDetector       — Contact Landing Evidence Calculation
  6. AttackEngine          — 5-State State Machine (NORMAL -> CONFIRMED_ATTACK)
  7. AlarmGate             — Single Authoritative Alarm Safety Gate
"""

import os
import cv2
import time
import numpy as np
from typing import Tuple, Dict, List, Optional

try:
    from alarm_config import alarm_config
except ImportError:
    from python_backend.alarm_config import alarm_config

try:
    from alarm_manager import alarm_manager
except ImportError:
    from python_backend.alarm_manager import alarm_manager

# Modular AI Package Imports
try:
    from ai.person_detector import PersonDetector
    from ai.tracker import PersonTrackerWrapper
    from ai.action_detector import ActionDetector
    from ai.interaction_detector import InteractionDetector
    from ai.contact_detector import ContactDetector
    from ai.attack_engine import AttackEngine, AttackEngineResult
    from ai.alarm_gate import AlarmGate, AlarmGateResult
except ImportError:
    from python_backend.ai.person_detector import PersonDetector
    from python_backend.ai.tracker import PersonTrackerWrapper
    from python_backend.ai.action_detector import ActionDetector
    from python_backend.ai.interaction_detector import InteractionDetector
    from python_backend.ai.contact_detector import ContactDetector
    from python_backend.ai.attack_engine import AttackEngine, AttackEngineResult
    from python_backend.ai.alarm_gate import AlarmGate, AlarmGateResult

# Drawing BGR Colors
_WHITE = (255, 255, 255)
_GREEN = (0, 255, 0)
_RED   = (0, 0, 255)
_CYAN  = (255, 212, 0)
_YELLOW= (0, 255, 255)


class AIEngine:
    """
    Top-level SAFECAM AI Orchestrator.
    Cleanly connects all modular sub-components.
    """

    def __init__(self, model_path: str = None):
        self.config     = alarm_config
        self.model_path = model_path or self.config.MODEL_PATH
        self.imgsz      = self.config.YOLO_IMGSZ
        self.device     = self.config.YOLO_DEVICE

        print("\n================================")
        print(" SAFECAM AI ENGINE REBUILD")
        print("================================")

        # 1. Person Detector (COCO Person Class [0])
        person_conf = getattr(self.config, "PERSON_CONFIDENCE", 0.30)
        self.person_detector = PersonDetector(
            model_path=self.model_path,
            imgsz=self.imgsz,
            device=self.device,
            conf_thresh=person_conf
        )

        # 2. Person Tracker (ByteTrack / LightweightTracker)
        self.tracker_wrapper = PersonTrackerWrapper(
            iou_thresh=getattr(self.config, "TRACKER_IOU_THRESHOLD", 0.30),
            max_missing=getattr(self.config, "TRACKER_MAX_MISSING_FRAMES", 5)
        )

        # 3. Action Detector (Custom YOLO11n best_v1.pt, conf_thresh=0.05 for raw candidate intake)
        self.action_detector = ActionDetector(
            model_path=self.model_path,
            imgsz=self.imgsz,
            device=self.device,
            conf_thresh=0.05
        )

        # 4. Interaction Detector (Pair geometry & direction)
        self.interaction_detector = InteractionDetector(frame_width=1920, frame_height=1080)

        # 5. Contact Detector (Contact landing evidence)
        self.contact_detector = ContactDetector(
            min_contact_score=getattr(self.config, "MIN_CONTACT_SCORE", 0.50),
            contact_dist_thresh=getattr(self.config, "CONTACT_DISTANCE_THRESHOLD", 0.12),
            overlap_thresh=getattr(self.config, "CONTACT_OVERLAP_THRESHOLD", 0.05)
        )

        # 6. Attack Engine (5-State State Machine)
        confirm_frames = getattr(self.config, "BULLYING_CONFIRMATION_FRAMES", 3)
        stop_frames = getattr(self.config, "BULLYING_STOP_FRAMES", 10)
        self.attack_engine = AttackEngine(confirm_frames=confirm_frames, stop_frames=stop_frames)

        # 7. Alarm Safety Gate (Single Authoritative Alarm Gate)
        self.alarm_gate = AlarmGate(min_people=2, min_confirm_frames=confirm_frames)

        self.last_yolo_inference_ms: float = 0.0
        print(" SAFECAM AI Engine Rebuild Ready!\n================================\n")

    def process_frame(self, frame_1080p: np.ndarray, camera_id: str = "default") -> Tuple[np.ndarray, dict]:
        """
        Processes one 1080p frame through the clean 7-component modular pipeline.
        Returns: (annotated_frame, telemetry_dict)
        """
        if frame_1080p is None:
            return None, {}

        t_start = time.time()
        orig_h, orig_w = frame_1080p.shape[:2]

        # ---------------------------------------------------------------------
        # STEP 1: Person Detection (Every visible person gets a box)
        # ---------------------------------------------------------------------
        person_detections = self.person_detector.detect(frame_1080p)

        # ---------------------------------------------------------------------
        # STEP 2: Tracker Update (Stable ByteTrack / LightweightTracker IDs)
        # ---------------------------------------------------------------------
        tracked_persons = self.tracker_wrapper.update(camera_id, person_detections)
        people_count = len(tracked_persons)

        # ---------------------------------------------------------------------
        # STEP 3: Action Classification (Custom best_v1.pt) & Association
        # ---------------------------------------------------------------------
        action_preds, person_action_map = self.action_detector.detect_and_associate(frame_1080p, tracked_persons)
        any_action = any(act in ("PUNCH", "KICK") for act in person_action_map.values())
        raw_act_type = next((act for act in person_action_map.values() if act in ("PUNCH", "KICK")), "NONE")

        # ---------------------------------------------------------------------
        # STEP 4: Interaction Detection (Evaluated ONLY when tracked_people >= 2)
        # ---------------------------------------------------------------------
        cam_history = getattr(self.attack_engine, "_get_camera_state")(camera_id)
        pair_interaction = self.interaction_detector.evaluate_interaction(
            camera_id=camera_id,
            tracked_persons=tracked_persons,
            person_action_map=person_action_map,
            camera_history=cam_history
        )

        # ---------------------------------------------------------------------
        # STEP 5: Contact Landing Validation
        # ---------------------------------------------------------------------
        contact_evidence = self.contact_detector.evaluate_contact(pair_interaction) if pair_interaction else None

        # ---------------------------------------------------------------------
        # STEP 6: 5-State Attack Engine Process
        # ---------------------------------------------------------------------
        attack_result: AttackEngineResult = self.attack_engine.process(
            camera_id=camera_id,
            tracked_persons=tracked_persons,
            pair_interaction=pair_interaction,
            contact_evidence=contact_evidence,
            any_action_detected=any_action,
            raw_action_type=raw_act_type
        )

        # ---------------------------------------------------------------------
        # STEP 7: Single Authoritative Alarm Safety Gate
        # ---------------------------------------------------------------------
        gate_result: AlarmGateResult = self.alarm_gate.evaluate_gate(
            people_count=people_count,
            attack_result=attack_result,
            contact_evidence=contact_evidence
        )

        # Clean Structured Console Diagnostic Print per User Specification
        print(f"\n--- [FRAME DIAGNOSTIC TRACE | Camera: {camera_id}] ---")
        print(f"[YOLO DETECTIONS] Count: {people_count} | Boxes: {[ [det.x1, det.y1, det.x2, det.y2] for det in person_detections ]}")
        print(f"[BYTETRACK] Active Track IDs: {[tp.track_id for tp in tracked_persons]}")

        for tp in tracked_persons:
            st = self.action_detector.get_track_state(tp.track_id)
            pred_act = person_action_map.get(tp.track_id, "NORMAL")
            act_conf = st.action_confidence if pred_act in ("PUNCH", "KICK") else st.last_raw_conf
            print(f"\n[ACTION DEBUG]")
            print(f"Track={tp.track_id}")
            print(f"PUNCH={st.raw_punch_conf:.2f}")
            print(f"KICK={st.raw_kick_conf:.2f}")
            print(f"NORMAL={st.raw_normal_conf:.2f}")
            print(f"Predicted={pred_act}")
            print(f"Confidence={act_conf:.2f}")
            print(f"SuppressionInfo={st.debug_reason}")

        attacker_id = pair_interaction.attacker_tp.track_id if pair_interaction else (attack_result.attacker_track_id if attack_result else None)
        victim_id = pair_interaction.victim_tp.track_id if (pair_interaction and pair_interaction.victim_tp) else (attack_result.victim_track_id if attack_result else None)
        assoc_reason = "Success" if (attacker_id and victim_id) else ("No pair interaction" if not pair_interaction else ("Air punch/kick (no victim confirmed)" if pair_interaction.victim_tp is None else "Association failed"))

        print(f"\n[ASSOCIATION DEBUG]")
        print(f"Attacker={'Track ' + str(attacker_id) if attacker_id is not None else 'None'}")
        print(f"Victim={'Track ' + str(victim_id) if victim_id is not None else 'None'}")
        print(f"Reason={assoc_reason}")

        print(f"\n[TEMPORAL DEBUG]")
        print(f"CandidateFrames={max([st.candidate_count for st in self.action_detector.track_states.values()], default=0)}/{self.action_detector.min_action_frames}")
        print(f"Confirmed={attack_result.confirmation_frames}/{self.attack_engine.confirm_frames}")
        print(f"State={attack_result.state}")

        print(f"\n[FINAL DEBUG]")
        print(f"Result={'ATTACK' if gate_result.should_alarm else 'NORMAL'}")
        print(f"Reason={gate_result.reason}\n")

        # Build tracked persons payload for API / Telemetry
        tracked_persons_payload = []
        punch_count = 0
        kick_count = 0

        for tp in tracked_persons:
            det = tp.detection
            st = self.action_detector.get_track_state(tp.track_id)
            # Display action suppresses PUNCH/KICK for single person
            action_label = person_action_map.get(tp.track_id, "NORMAL") if (person_action_map and people_count >= 2) else "NORMAL"
            
            if action_label == "PUNCH":
                punch_count += 1
            elif action_label == "KICK":
                kick_count += 1

            role = "normal"
            if attack_result.confirmed_attack:
                if attack_result.attacker_track_id == tp.track_id:
                    role = "attacker"
                elif attack_result.victim_track_id == tp.track_id:
                    role = "victim"

            act_conf = st.action_confidence if action_label in ("PUNCH", "KICK") else det.confidence

            tracked_persons_payload.append({
                "track_id": tp.track_id,
                "role": role,
                "action": action_label,
                "confidence": round(act_conf, 4),
                "bbox_1080": [det.x1, det.y1, det.x2, det.y2],
                "bbox_640": [
                    det.x1 * (640.0 / orig_w),
                    det.y1 * (640.0 / orig_h),
                    det.x2 * (640.0 / orig_w),
                    det.y2 * (640.0 / orig_h),
                ],
            })

        telemetry_for_alarm = {
            "camera_id": camera_id,
            "people_count": people_count,
            "tracked_persons": tracked_persons_payload,
            "attack_state": attack_result.state,
            "confirmed_attack": attack_result.confirmed_attack,
            "should_alarm": gate_result.should_alarm,
            "bullying_confirmed": gate_result.should_alarm,
            "attacker_id": gate_result.attacker_track_id,
            "victim_id": gate_result.victim_track_id,
            "attack_type": gate_result.attack_type,
            "confidence": gate_result.confidence,
            "reason": gate_result.reason,
            "timestamp": time.time()
        }

        # Update AlarmManager singleton
        annotated_frame = self._render_frame(frame_1080p, tracked_persons, attack_result, gate_result, person_action_map)
        alarm_manager.update_camera_state(camera_id, annotated_frame, telemetry_for_alarm)

        total_ms = (time.time() - t_start) * 1000.0

        ai_telemetry = {
            "camera_id": camera_id,
            "people_count": people_count,
            "punch_count": punch_count,
            "kick_count": kick_count,
            "yolo_imgsz": self.imgsz,
            "yolo_conf_threshold": getattr(self.config, "YOLO_CONF_THRESHOLD", 0.10),
            "tracked_persons_count": len(tracked_persons),
            "attack_state": attack_result.state,
            "confirmed_attack": attack_result.confirmed_attack,
            "should_alarm": gate_result.should_alarm,
            "total_ai_ms": round(total_ms, 2),
            "alarm_state": alarm_manager.get_camera_state(camera_id)
        }

        return annotated_frame, ai_telemetry

    def _render_frame(
        self,
        frame: np.ndarray,
        tracked_persons: List,
        attack_result: AttackEngineResult,
        gate_result: AlarmGateResult,
        person_action_map: Optional[Dict[int, str]] = None
    ) -> np.ndarray:
        """
        Renders bounding boxes and status HUD according to strict clean label rules:
          - Confirmed Attacker -> RED with "ID:X PUNCH 91% - ATTACKER"
          - Confirmed Victim   -> GREEN with "ID:X NORMAL 87% - VICTIM"
          - Candidate Action   -> YELLOW/CYAN with "ID:X PUNCH 91%"
          - Normal             -> WHITE with "ID:X NORMAL 85%"
        """
        out = frame.copy()
        people_count = len(tracked_persons)

        for tp in tracked_persons:
            det = tp.detection
            st = self.action_detector.get_track_state(tp.track_id)
            act = person_action_map.get(tp.track_id, "NORMAL") if (person_action_map and people_count >= 2) else "NORMAL"
            act_conf = st.action_confidence if act in ("PUNCH", "KICK") else det.confidence
            conf_pct = int(act_conf * 100)

            if gate_result.should_alarm and gate_result.attacker_track_id == tp.track_id:
                color = _RED
                label = f"ID:{tp.track_id} {act} {conf_pct}% - ATTACKER"
            elif gate_result.should_alarm and gate_result.victim_track_id == tp.track_id:
                color = _GREEN
                label = f"ID:{tp.track_id} {act} {int(det.confidence * 100)}% - VICTIM"
            else:
                if act in ("PUNCH", "KICK"):
                    color = (0, 255, 255)  # Yellow/Cyan highlight for action candidate
                    label = f"ID:{tp.track_id} {act} {conf_pct}%"
                else:
                    color = _WHITE
                    label = f"ID:{tp.track_id} NORMAL {conf_pct}%"

            x1, y1, x2, y2 = det.x1, det.y1, det.x2, det.y2
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 3)

            # Draw label banner
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(out, (x1, y1 - th - 10), (x1 + tw + 10, y1), color, -1)
            cv2.putText(out, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, _WHITE if color == _RED else (0, 0, 0), 2)

        # Draw HUD status header badge at top-right
        if gate_result.should_alarm:
            hud_bg = _RED
            hud_txt = f"CONFIRMED BULLYING | {gate_result.attack_type}"
        else:
            hud_bg = (20, 20, 20)
            hud_txt = f"MONITORING ACTIVE | {len(tracked_persons)} PERSONS"

        frame_w = out.shape[1]
        (tw, th), _ = cv2.getTextSize(hud_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        bx1 = frame_w - tw - 30
        by1 = 10
        bx2 = frame_w - 10
        by2 = by1 + th + 16

        cv2.rectangle(out, (bx1, by1), (bx2, by2), hud_bg, -1)
        cv2.rectangle(out, (bx1, by1), (bx2, by2), _WHITE if gate_result.should_alarm else (60, 60, 60), 2)
        cv2.putText(out, hud_txt, (bx1 + 10, by1 + th + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.65, _WHITE, 2)

        return out
