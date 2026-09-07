"""
SAFECAM AI Engine — LSTM Sequence Pipeline
=================================================
Replaces the old state-machine with a deep sequence model:
  1. YOLOv11 Pose Tracking (Bounding box + Keypoints)
  2. LSTM Sequence Buffer (Rolling 30 frames per track)
  3. LSTM Keras Model (Predicts PUNCH/KICK/NEUTRAL)
  4. Temporal Confirmation (Anti-flicker logic)
  5. Interaction Validator (Physical contact confirmation)
"""

import os
import cv2
import time
import numpy as np
from typing import Tuple, Dict, List, Optional
import tensorflow as tf
from ultralytics import YOLO

# Load config and manager
try:
    from alarm_config import alarm_config
except ImportError:
    from python_backend.alarm_config import alarm_config

try:
    from alarm_manager import alarm_manager
except ImportError:
    from python_backend.alarm_manager import alarm_manager

# AI Subcomponents
from ai.normalizer import normalize_frame
from ai.lstm_sequence_buffer import LSTMSequenceBuffer
from ai.temporal_confirmation import TemporalConfirmation
from ai.interaction_validator import InteractionValidator

# Drawing Colors
_WHITE = (255, 255, 255)
_GREEN = (0, 255, 0)
_RED   = (0, 0, 255)
_CYAN  = (255, 212, 0)

# YOLO Pose Indices for LSTM (12 landmarks)
# L Arm (5,7,9), R Arm (6,8,10), L Leg (11,13,15), R Leg (12,14,16)
YOLO_KP_INDICES = [5, 7, 9, 6, 8, 10, 11, 13, 15, 12, 14, 16]

LSTM_CLASSES = ['NEUTRAL', 'PUNCH', 'KICK']

class AIEngine:
    def __init__(self, model_path: str = None):
        self.config = alarm_config
        self.device = self.config.YOLO_DEVICE
        
        print("\n========================================")
        print(" SAFECAM AI ENGINE (LSTM SEQUENCE MODE)")
        print("========================================")

        # 1. YOLO Pose Model
        self.yolo_model = YOLO("yolo11n-pose.pt")
        self.person_conf = getattr(self.config, "PERSON_CONFIDENCE", 0.30)
        self.imgsz = self.config.YOLO_IMGSZ

        # 2. LSTM Sequence Model
        model_file = os.path.join(os.path.dirname(__file__), 'ai', 'safecam_lstm_24.keras')
        self.lstm_model = tf.keras.models.load_model(model_file)
        
        # 3. Buffers and Validators
        self.sequence_buffers = {} # camera_id -> LSTMSequenceBuffer
        self.temporal_confirmations = {} # (camera_id, track_id) -> TemporalConfirmation
        self.interaction_validators = {} # camera_id -> InteractionValidator

        print(" SAFECAM AI Engine Rebuild Ready!\n========================================\n")

    def _get_camera_state(self, camera_id):
        if camera_id not in self.sequence_buffers:
            self.sequence_buffers[camera_id] = LSTMSequenceBuffer(sequence_length=30)
            self.interaction_validators[camera_id] = InteractionValidator()
        return self.sequence_buffers[camera_id], self.interaction_validators[camera_id]

    def _get_temporal(self, camera_id, track_id):
        key = (camera_id, track_id)
        if key not in self.temporal_confirmations:
            self.temporal_confirmations[key] = TemporalConfirmation(confidence_threshold=0.80, min_consecutive_frames=3)
        return self.temporal_confirmations[key]

    def process_frame(self, frame_1080p: np.ndarray, camera_id: str = "default") -> Tuple[np.ndarray, dict]:
        if frame_1080p is None:
            return None, {}

        t_start = time.time()
        orig_h, orig_w = frame_1080p.shape[:2]
        seq_buffer, inter_validator = self._get_camera_state(camera_id)

        # 1. YOLO Pose Tracking
        # persist=True enables ByteTrack under the hood
        results = self.yolo_model.track(
            frame_1080p, 
            classes=[0], # Person only
            conf=self.person_conf, 
            persist=True, 
            verbose=False,
            imgsz=self.imgsz,
            device=self.device
        )

        tracked_persons = []
        active_track_ids = []
        
        if results and len(results) > 0:
            result = results[0]
            if result.boxes is not None and result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                track_ids = result.boxes.id.cpu().numpy().astype(int)
                keypoints_all = result.keypoints.xy.cpu().numpy() # (N, 17, 2)
                
                for i in range(len(track_ids)):
                    tid = track_ids[i]
                    bbox = boxes[i]
                    kps = keypoints_all[i]
                    
                    active_track_ids.append(tid)
                    
                    # Extract 12 keypoints
                    target_kps = kps[YOLO_KP_INDICES] # (12, 2)
                    flat_kps = target_kps.flatten()
                    
                    # Convert absolute px to normalized (0-1) to match Mediapipe training
                    for j in range(12):
                        flat_kps[j*2] /= orig_w
                        flat_kps[j*2+1] /= orig_h
                        
                    norm_kps = normalize_frame(flat_kps)
                    seq_buffer.update(tid, norm_kps)
                    
                    tracked_persons.append({
                        'person_id': tid,
                        'bbox': bbox,
                        'keypoints': target_kps.flatten(), # absolute px for interaction validator
                        'norm_kps': norm_kps,
                        'action': 'NEUTRAL',
                        'confidence': 0.0
                    })

        # Tick buffer to remove stale tracks
        seq_buffer.tick(active_track_ids)

        # 2. LSTM Inference
        for person in tracked_persons:
            tid = person['person_id']
            seq = seq_buffer.get_sequence(tid)
            
            temporal = self._get_temporal(camera_id, tid)
            
            if seq is not None:
                # seq is (30, 24)
                X = np.expand_dims(seq, axis=0) # (1, 30, 24)
                preds = self.lstm_model.predict(X, verbose=0)[0]
                
                class_idx = np.argmax(preds)
                conf = float(preds[class_idx])
                raw_action = LSTM_CLASSES[class_idx]
                
                confirmed_action = temporal.update(raw_action, conf)
                
                person['action'] = temporal.last_confirmed_action if temporal.last_confirmed_action else "NEUTRAL"
                person['confidence'] = conf

            else:
                temporal.reset()

        # 3. Physical Interaction Validation
        confirmed_alerts = inter_validator.validate(tracked_persons)
        
        # Determine Alarm State
        should_alarm = len(confirmed_alerts) > 0
        attack_type = confirmed_alerts[0]['action'] if should_alarm else "NONE"
        attacker_id = confirmed_alerts[0]['striker_id'] if should_alarm else None
        victim_id = confirmed_alerts[0]['target_id'] if should_alarm else None

        # Build Telemetry
        tracked_persons_payload = []
        punch_count = sum(1 for p in tracked_persons if p['action'] == 'PUNCH')
        kick_count = sum(1 for p in tracked_persons if p['action'] == 'KICK')

        for p in tracked_persons:
            role = "normal"
            if should_alarm:
                if p['person_id'] == attacker_id: role = "attacker"
                elif p['person_id'] == victim_id: role = "victim"
                
            x1, y1, x2, y2 = p['bbox']
            tracked_persons_payload.append({
                "track_id": p['person_id'],
                "role": role,
                "action": p['action'],
                "confidence": round(p['confidence'], 4),
                "bbox_1080": [float(x1), float(y1), float(x2), float(y2)],
                "bbox_640": [
                    float(x1 * (640.0 / orig_w)),
                    float(y1 * (640.0 / orig_h)),
                    float(x2 * (640.0 / orig_w)),
                    float(y2 * (640.0 / orig_h)),
                ],
            })

        telemetry_for_alarm = {
            "camera_id": camera_id,
            "people_count": len(tracked_persons),
            "tracked_persons": tracked_persons_payload,
            "attack_state": "ALARM_ACTIVE" if should_alarm else "NORMAL",
            "confirmed_attack": should_alarm,
            "should_alarm": should_alarm,
            "bullying_confirmed": should_alarm,
            "attacker_id": attacker_id,
            "victim_id": victim_id,
            "attack_type": attack_type,
            "confidence": confirmed_alerts[0]['confidence'] if should_alarm else 0.0,
            "reason": f"Physical {attack_type} contact confirmed" if should_alarm else "",
            "timestamp": time.time()
        }

        # Render HUD
        annotated_frame = self._render_frame(frame_1080p, tracked_persons, confirmed_alerts, should_alarm)
        alarm_manager.update_camera_state(camera_id, annotated_frame, telemetry_for_alarm)

        total_ms = (time.time() - t_start) * 1000.0

        ai_telemetry = {
            "camera_id": camera_id,
            "people_count": len(tracked_persons),
            "punch_count": punch_count,
            "kick_count": kick_count,
            "yolo_imgsz": self.imgsz,
            "tracked_persons_count": len(tracked_persons),
            "confirmed_attack": should_alarm,
            "should_alarm": should_alarm,
            "total_ai_ms": round(total_ms, 2),
            "alarm_state": alarm_manager.get_camera_state(camera_id)
        }

        return annotated_frame, ai_telemetry

    def _render_frame(self, frame, tracked_persons, confirmed_alerts, should_alarm):
        out = frame.copy()
        
        attacker_id = confirmed_alerts[0]['striker_id'] if should_alarm else None
        victim_id = confirmed_alerts[0]['target_id'] if should_alarm else None

        for p in tracked_persons:
            tid = p['person_id']
            act = p['action']
            conf_pct = int(p['confidence'] * 100)
            x1, y1, x2, y2 = map(int, p['bbox'])

            if should_alarm and tid == attacker_id:
                color = _RED
                label = f"ID:{tid} {act} {conf_pct}% - ATTACKER"
            elif should_alarm and tid == victim_id:
                color = _GREEN
                label = f"ID:{tid} {act} {conf_pct}% - VICTIM"
            else:
                if act in ("PUNCH", "KICK"):
                    color = _CYAN
                    label = f"ID:{tid} {act} {conf_pct}%"
                else:
                    color = _WHITE
                    label = f"ID:{tid} NORMAL {conf_pct}%"

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 3)
            
            # Draw label banner
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(out, (x1, y1 - th - 10), (x1 + tw + 10, y1), color, -1)
            cv2.putText(out, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, _WHITE if color == _RED else (0, 0, 0), 2)
            
            # Optional: Draw Pose skeleton points
            kps = p['keypoints'].reshape((12, 2))
            for pt in kps:
                if pt[0] > 0 and pt[1] > 0:
                    cv2.circle(out, (int(pt[0]), int(pt[1])), 4, color, -1)

        # Draw HUD status header badge
        if should_alarm:
            hud_bg = _RED
            attack_type = confirmed_alerts[0]['action']
            hud_txt = f"CONFIRMED BULLYING | {attack_type}"
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
        cv2.rectangle(out, (bx1, by1), (bx2, by2), _WHITE if should_alarm else (60, 60, 60), 2)
        cv2.putText(out, hud_txt, (bx1 + 10, by1 + th + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.65, _WHITE, 2)

        return out
