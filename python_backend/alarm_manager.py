import os
import cv2
import json
import time
import threading
from datetime import datetime
from collections import defaultdict
try:
    from alarm_config import alarm_config
except ImportError:
    from python_backend.alarm_config import alarm_config


class AlarmManager:
    """
    SAFECAM AI Single Source of Truth Backend Alarm Manager.
    
    State Machine per Camera:
    IDLE → SUSPICIOUS → CONFIRMING → BULLYING_CONFIRMED / ALARM_ACTIVE → COOLDOWN → IDLE
    
    Rules & Features:
    - Requires MIN_CONSECUTIVE_FRAMES (default: 4) above threshold before triggering ALARM_ACTIVE.
    - Resets confirmation counter if evidence drops before threshold is met.
    - Manages single active incident per camera without duplicating alerts every frame.
    - Saves 1080p MP4 incident clips and JPEG snapshots to python_backend/incidents/.
    - Maintains persisted incidents.json history file.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.config = alarm_config
        os.makedirs(self.config.INCIDENTS_DIR, exist_ok=True)
        
        self.incidents_json_path = os.path.join(self.config.INCIDENTS_DIR, "incidents.json")
        self.lock = threading.Lock()
        
        # Camera ID -> State Dict
        self.camera_states = {}
        
        # Camera ID -> Incident Frame Buffer for MP4 saving
        self.clip_frame_buffers = defaultdict(list)
        
        # Loaded Incident History
        self.incidents_history = self._load_incidents_history()

    def _load_incidents_history(self):
        if os.path.exists(self.incidents_json_path):
            try:
                with open(self.incidents_json_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ALARM MANAGER] Warning: Could not read incidents.json: {e}")
        return []

    def _save_incidents_history(self):
        try:
            with open(self.incidents_json_path, "w") as f:
                json.dump(self.incidents_history, f, indent=2)
        except Exception as e:
            print(f"[ALARM MANAGER] Error saving incidents.json: {e}")

    def get_default_state(self, camera_id):
        return {
            "camera_id": camera_id,
            "alarm_active": False,
            "state": "IDLE",
            "incident_id": None,
            "event_type": "NORMAL",
            "action": None,
            "confidence": 0.0,
            "attacker_id": None,
            "victim_id": None,
            "started_at": None,
            "last_detected_at": None,
            "clip_path": None,
            "snapshot_path": None,
            "reason": "Normal Activity",
            "consecutive_hits": 0,
            "cooldown_remaining_sec": 0.0,
            "acknowledged": False
        }

    def update_camera_state(self, camera_id, frame_1080p, telemetry):
        """
        Updates single source of truth alarm state for camera_id based on AI telemetry.
        Returns: Current camera alarm state dict.
        """
        with self.lock:
            if camera_id not in self.camera_states:
                self.camera_states[camera_id] = self.get_default_state(camera_id)

            st = self.camera_states[camera_id]
            now_ts = time.time()
            now_iso = datetime.now().astimezone().isoformat()

            persons = telemetry.get("tracked_persons", [])
            fight_prob = telemetry.get("fight_probability", 0.0)
            overall_status = telemetry.get("status", "NORMAL")
            threat_level = telemetry.get("threat_level", "normal")

            # Check for active attacker in verified real persons
            verified_persons = [p for p in persons if p.get("is_verified_real_person", False)]
            attacker_p = next((p for p in verified_persons if p.get("role") == "attacker"), None)
            victim_p = next((p for p in verified_persons if p.get("role") == "victim"), None)

            # Require verified real persons present if REQUIRE_REAL_PERSON is True
            has_real_person = len(verified_persons) > 0 if self.config.REQUIRE_REAL_PERSON else True

            has_confirmed_threat = has_real_person and (
                attacker_p is not None
                or fight_prob >= self.config.CONFIDENCE_THRESHOLD
                or threat_level in ["aggressive", "bullying"]
            )

            # State Machine Transitions
            current_state = st["state"]

            if current_state == "COOLDOWN":
                # Check cooldown expiry
                cooldown_start = st.get("_cooldown_start", now_ts)
                elapsed = now_ts - cooldown_start
                rem = max(0.0, self.config.COOLDOWN_PERIOD_SEC - elapsed)
                st["cooldown_remaining_sec"] = round(rem, 1)

                # Keep alarm_active = True during cooldown unless acknowledged
                if not st.get("acknowledged", False):
                    st["alarm_active"] = True

                if rem <= 0:
                    print(f"[ALARM STATE] Camera {camera_id}: COOLDOWN -> IDLE (Ready for new incidents)")
                    st["state"] = "IDLE"
                    st["alarm_active"] = False
                    st["consecutive_hits"] = 0
                    st["incident_id"] = None
                    st["acknowledged"] = False

            elif has_confirmed_threat and current_state != "COOLDOWN":
                st["consecutive_hits"] += 1
                hit_count = st["consecutive_hits"]

                if hit_count < self.config.MIN_CONSECUTIVE_FRAMES:
                    st["state"] = "CONFIRMING"
                    st["alarm_active"] = False
                    st["confidence"] = round(fight_prob, 2)
                    st["reason"] = f"Confirming Threat ({hit_count}/{self.config.MIN_CONSECUTIVE_FRAMES} frames)"
                else:
                    # CONFIRMED BULLYING TRIGGER
                    if not st["alarm_active"]:
                        # First frame of ALARM_ACTIVE -> Create Incident Record
                        inc_num = len(self.incidents_history) + 1
                        inc_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{inc_num:03d}"
                        
                        st["state"] = "ALARM_ACTIVE"
                        st["alarm_active"] = True
                        st["incident_id"] = inc_id
                        st["event_type"] = "BULLYING_CONFIRMED"
                        st["started_at"] = now_iso
                        st["last_detected_at"] = now_iso
                        st["attacker_id"] = attacker_p.get("track_id") if attacker_p else None
                        st["victim_id"] = victim_p.get("track_id") if victim_p else None
                        st["action"] = attacker_p.get("action_label", "PHYSICAL VIOLENCE") if attacker_p else "PHYSICAL VIOLENCE"
                        st["confidence"] = round(max(fight_prob, 0.88), 2)
                        st["reason"] = f"Confirmed Violence ({int(st['confidence']*100)}% Confidence)"
                        st["acknowledged"] = False

                        # Save snapshot JPEG
                        if frame_1080p is not None:
                            snap_filename = f"{inc_id}_snap.jpg"
                            snap_filepath = os.path.join(self.config.INCIDENTS_DIR, snap_filename)
                            cv2.imwrite(snap_filepath, frame_1080p)
                            st["snapshot_path"] = f"/incidents/{snap_filename}"

                        print(f"\n==================================================")
                        print(f" *** [CONFIRMED BULLYING ALARM TRIGGERED] ***")
                        print(f" Camera:       {camera_id}")
                        print(f" Incident ID:  {inc_id}")
                        print(f" Action:       {st['action']}")
                        print(f" Attacker ID:  {st['attacker_id']}")
                        print(f" Victim ID:    {st['victim_id']}")
                        print(f" Confidence:   {st['confidence']*100:.1f}%")
                        print(f" Snapshot:     {st.get('snapshot_path')}")
                        print(f"==================================================\n")

                    else:
                        # Ongoing ALARM_ACTIVE -> Update last_detected_at without duplicating incident ID
                        st["last_detected_at"] = now_iso
                        st["confidence"] = round(max(fight_prob, st["confidence"]), 2)
                        if attacker_p:
                            st["attacker_id"] = attacker_p.get("track_id")
                        if victim_p:
                            st["victim_id"] = victim_p.get("track_id")

                    # Buffer frame for incident clip
                    if frame_1080p is not None and len(self.clip_frame_buffers[camera_id]) < self.config.MAX_CLIP_FRAMES:
                        self.clip_frame_buffers[camera_id].append(frame_1080p.copy())

            else:
                # Threat disappeared / Evidence dropped below threshold
                if current_state in ["CONFIRMING", "SUSPICIOUS"]:
                    print(f"[ALARM STATE] Camera {camera_id}: {current_state} -> IDLE (Evidence dropped)")
                    st["state"] = "IDLE"
                    st["consecutive_hits"] = 0
                    st["alarm_active"] = False

                elif current_state == "ALARM_ACTIVE":
                    # Incident ended -> Finalize Incident Record & Transition to COOLDOWN
                    print(f"\n[ALARM STATE] Camera {camera_id}: ALARM_ACTIVE -> COOLDOWN (Incident ended)")
                    st["state"] = "COOLDOWN"
                    st["alarm_active"] = True  # Keep alarm_active = True during cooldown for UI visibility
                    st["_cooldown_start"] = now_ts
                    st["cooldown_remaining_sec"] = self.config.COOLDOWN_PERIOD_SEC

                    # Finalize MP4 video clip saving in background thread
                    inc_id = st.get("incident_id", "INC-000")
                    frames_to_save = list(self.clip_frame_buffers[camera_id])
                    self.clip_frame_buffers[camera_id].clear()

                    if frames_to_save and self.config.SAVE_CLIPS:
                        clip_filename = f"{inc_id}_clip.mp4"
                        clip_filepath = os.path.join(self.config.INCIDENTS_DIR, clip_filename)
                        st["clip_path"] = f"/incidents/{clip_filename}"

                        # Save incident log record to history
                        inc_record = {
                            "incident_id": inc_id,
                            "camera_id": camera_id,
                            "event_type": st["event_type"],
                            "action": st["action"],
                            "confidence": st["confidence"],
                            "attacker_id": st["attacker_id"],
                            "victim_id": st["victim_id"],
                            "started_at": st["started_at"],
                            "ended_at": now_iso,
                            "reason": st["reason"],
                            "snapshot_path": st.get("snapshot_path"),
                            "clip_path": st.get("clip_path")
                        }
                        self.incidents_history.insert(0, inc_record)
                        self._save_incidents_history()

                        threading.Thread(
                            target=self._save_mp4_clip,
                            args=(clip_filepath, frames_to_save),
                            daemon=True
                        ).start()

            return dict(st)

    def _save_mp4_clip(self, filepath, frames):
        """Asynchronously writes buffered 1080p frames to an MP4 video clip."""
        if not frames:
            return
        try:
            h, w = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(filepath, fourcc, 15.0, (w, h))
            for f in frames:
                out.write(f)
            out.release()
            print(f"[ALARM MANAGER] Saved incident video clip: {filepath}")
        except Exception as e:
            print(f"[ALARM MANAGER] Error saving incident video clip: {e}")

    def acknowledge_alarm(self, camera_id):
        """Silence audio alert for camera_id without interrupting detection."""
        with self.lock:
            if camera_id in self.camera_states:
                self.camera_states[camera_id]["acknowledged"] = True
                print(f"[ALARM MANAGER] Camera {camera_id} audio alarm acknowledged/silenced by user.")
                return True
        return False

    def get_camera_state(self, camera_id):
        with self.lock:
            return self.camera_states.get(camera_id, self.get_default_state(camera_id))

    def get_all_states(self):
        with self.lock:
            return {cid: dict(st) for cid, st in self.camera_states.items()}

    def get_all_incidents(self):
        with self.lock:
            return list(self.incidents_history)

    def delete_incident(self, incident_id):
        """Permanently deletes incident matching incident_id from backend history and file storage."""
        with self.lock:
            initial_len = len(self.incidents_history)
            self.incidents_history = [inc for inc in self.incidents_history if inc.get("incident_id") != incident_id]

            # Also clear active camera state if it matches this incident_id
            for cid, st in self.camera_states.items():
                if st.get("incident_id") == incident_id:
                    st["alarm_active"] = False
                    st["state"] = "IDLE"
                    st["incident_id"] = None
                    st["consecutive_hits"] = 0

            self._save_incidents_history()
            print(f"[ALARM MANAGER] Deleted incident {incident_id}. History count: {initial_len} -> {len(self.incidents_history)}")
            return len(self.incidents_history) < initial_len


# Global singleton instance
alarm_manager = AlarmManager()
