"""
SAFECAM — Alarm Manager (Single Source of Truth)
=================================================
Manages alarm state, incident records, and persistence for all cameras.

State Machine per camera:
  IDLE → CONFIRMING → ALARM_ACTIVE → BULLYING_STOPPING → COOLDOWN → IDLE

Key design rules:
  - Alarm turns ON only when BullyingResult.bullying_confirmed == True
  - Alarm stays ON while bullying continues (never restarts per frame)
  - Alarm turns OFF only after BULLYING_STOP_FRAMES consecutive non-bullying frames
    (but this is managed by BullyingStateMachine → result.state == "SAVE_CLIP")
  - Clip path is set later by camera_stream after the post-event recording finishes
  - Never overwrite an existing clip
  - Incident JSON is saved to incidents/incidents.json
"""

import os
import cv2
import json
import time
import threading
from datetime   import datetime
from collections import defaultdict

try:
    from alarm_config import alarm_config
except ImportError:
    from python_backend.alarm_config import alarm_config


class AlarmManager:
    """
    SAFECAM AI Single Source of Truth Backend Alarm Manager.

    Singleton — one instance shared across the entire process.
    """

    _instance = None
    _cls_lock = threading.Lock()

    def __new__(cls):
        with cls._cls_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.config = alarm_config
        os.makedirs(self.config.INCIDENTS_DIR, exist_ok=True)

        self.incidents_json_path = os.path.join(self.config.INCIDENTS_DIR, "incidents.json")
        self.lock = threading.Lock()

        # camera_id → state dict
        self.camera_states: dict = {}

        # Loaded incident history
        self.incidents_history: list = self._load_incidents()

    # ---------------------------------------------------------------- persist

    def _load_incidents(self) -> list:
        if os.path.exists(self.incidents_json_path):
            try:
                with open(self.incidents_json_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ALARM MANAGER] Warning: Could not read incidents.json: {e}")
        return []

    def _save_incidents(self):
        try:
            with open(self.incidents_json_path, "w") as f:
                json.dump(self.incidents_history, f, indent=2)
        except Exception as e:
            print(f"[ALARM MANAGER] Error saving incidents.json: {e}")

    # ---------------------------------------------------------------- state

    def _default_state(self, camera_id: str) -> dict:
        return {
            "camera_id":             camera_id,
            "alarm_active":          False,
            "state":                 "IDLE",
            "incident_id":           None,
            "event_type":            "NORMAL",
            "action":                None,
            "attack_type":           None,
            "confidence":            0.0,
            "attacker_id":           None,
            "victim_id":             None,
            "started_at":            None,
            "last_detected_at":      None,
            "clip_path":             None,
            "snapshot_path":         None,
            "reason":                "Normal Activity",
            "consecutive_hits":      0,
            "cooldown_remaining_sec":0.0,
            "acknowledged":          False,
            "bullying_state":        "NORMAL",
            "distance_normalized":   1.0,
            "contact_overlap":       0.0,
        }

    def get_default_state(self, camera_id: str) -> dict:
        return self._default_state(camera_id)

    def get_camera_state(self, camera_id: str) -> dict:
        with self.lock:
            return dict(self.camera_states.get(camera_id, self._default_state(camera_id)))

    def get_all_states(self) -> dict:
        with self.lock:
            return {cid: dict(st) for cid, st in self.camera_states.items()}

    def get_all_incidents(self) -> list:
        with self.lock:
            return list(self.incidents_history)

    # ---------------------------------------------------------------- update

    def update_camera_state(
        self,
        camera_id:    str,
        frame_1080p,
        telemetry:    dict,
        bullying_result=None,
        bullying_sm=None,
    ) -> dict:
        """
        Main update method called once per AI frame by AIEngine.

        Parameters
        ----------
        camera_id       : str  — camera identifier
        frame_1080p     : np.ndarray — annotated frame (for snapshot)
        telemetry       : dict — full AI telemetry including BullyingResult fields
        bullying_result : BullyingResult (optional) — direct access to result object
        bullying_sm     : BullyingStateMachine (optional) — to notify on clip save

        Returns: current camera alarm state dict
        """
        with self.lock:
            if camera_id not in self.camera_states:
                self.camera_states[camera_id] = self._default_state(camera_id)

            st        = self.camera_states[camera_id]
            now_ts    = time.time()
            now_iso   = datetime.now().astimezone().isoformat()

            # Extract key fields from telemetry
            bullying_confirmed = telemetry.get("bullying_confirmed", False)
            people_count       = telemetry.get("people_count", 0)

            # ====================================================================
            # ABSOLUTE SINGLE-PERSON RULE
            # Hard guard: Alarm system & attack state MUST IMMEDIATELY RESET when tracked_people < 2
            # ====================================================================
            min_people = getattr(self.config, "MIN_PEOPLE_FOR_ATTACK", getattr(self.config, "MIN_PERSONS_FOR_BULLYING", 2))
            if people_count < min_people:
                bullying_confirmed = False
                bullying_state_sm  = "NORMAL"
                attack_type        = None
                confidence         = 0.0
                attacker_id        = None
                victim_id          = None
                confirmation_frames= 0
                st["consecutive_hits"] = 0
                st["alarm_active"]     = False
                st["current_attack_type"] = None
                st["current_attacker_id"] = None
                st["current_victim_id"] = None
                st["state"]            = "IDLE"

            else:
                bullying_state_sm  = telemetry.get("bullying_state", "NORMAL")  # from BullyingStateMachine
                attack_type        = telemetry.get("attack_type")
                confidence         = telemetry.get("confidence", 0.0)
                attacker_id        = telemetry.get("attacker_track_id")
                victim_id          = telemetry.get("victim_track_id")

            reason             = telemetry.get("reason", "")
            distance_norm      = telemetry.get("distance_normalized", 1.0)
            contact_overlap    = telemetry.get("contact_overlap", 0.0)
            confirmation_frames= telemetry.get("confirmation_frames", 0)

            # Update passthrough telemetry fields
            st["bullying_state"]      = bullying_state_sm
            st["distance_normalized"] = distance_norm
            st["contact_overlap"]     = contact_overlap

            current = st["state"]

            # ================================================================
            # COOLDOWN: waiting between incidents
            # ================================================================
            if current == "COOLDOWN":
                cooldown_start = st.get("_cooldown_start", now_ts)
                elapsed        = now_ts - cooldown_start
                rem            = max(0.0, self.config.COOLDOWN_PERIOD_SEC - elapsed)
                st["cooldown_remaining_sec"] = round(rem, 1)
                st["alarm_active"]           = False
                st["consecutive_hits"]       = 0

                if rem <= 0:
                    print(f"[ALARM MANAGER] {camera_id}: COOLDOWN → IDLE")
                    st["state"]       = "IDLE"
                    st["incident_id"] = None
                    st["acknowledged"]= False

                return dict(st)

            # ================================================================
            # BullyingStateMachine says SAVE_CLIP → finalize incident
            # ================================================================
            if bullying_state_sm == "SAVE_CLIP" and current == "ALARM_ACTIVE":
                print(f"\n[ALARM MANAGER] {camera_id}: ALARM_ACTIVE → COOLDOWN (clip will be saved)")
                st["state"]        = "COOLDOWN"
                st["alarm_active"] = False
                st["consecutive_hits"] = 0
                st["_cooldown_start"]  = now_ts
                st["cooldown_remaining_sec"] = self.config.COOLDOWN_PERIOD_SEC

                # Save incident record (clip_path will be updated later by camera_stream)
                inc_id = st.get("incident_id", "INC-UNKNOWN")
                now_dt = datetime.now()
                inc_record = {
                    "incident_id":  inc_id,
                    "camera_id":    camera_id,
                    "date":         now_dt.strftime("%Y-%m-%d"),
                    "time":         now_dt.strftime("%H:%M:%S"),
                    "event_type":   "BULLYING_CONFIRMED",
                    "type":         st.get("attack_type") or "UNKNOWN",
                    "action":       st.get("action") or "UNKNOWN",
                    "confidence":   round(st.get("confidence", 0.0), 4),
                    "status":       "BULLYING_CONFIRMED",
                    "attacker_id":  st.get("attacker_id"),
                    "victim_id":    st.get("victim_id"),
                    "started_at":   st.get("started_at"),
                    "ended_at":     now_iso,
                    "reason":       st.get("reason", ""),
                    "snapshot_path":st.get("snapshot_path"),
                    "clip_path":    None,   # will be filled by set_clip_path()
                    "timestamp":    now_iso,
                }
                self.incidents_history.insert(0, inc_record)
                self._save_incidents()

                # Notify BullyingStateMachine to reset to NORMAL
                if bullying_sm is not None:
                    bullying_sm.notify_clip_saved(camera_id)

                return dict(st)

            # ================================================================
            # ALARM ACTIVE: bullying confirmed and ongoing
            # ================================================================
            if bullying_confirmed:
                st["consecutive_hits"] += 1

                if not st["alarm_active"]:
                    # ---- First frame of confirmed bullying: create incident ----
                    inc_num = len(self.incidents_history) + 1
                    inc_id  = f"INC-{datetime.now().strftime('%Y%m%d')}-{inc_num:03d}"

                    action_label = f"BULLY — {attack_type}" if attack_type else "PHYSICAL VIOLENCE"

                    st["state"]        = "ALARM_ACTIVE"
                    st["alarm_active"] = True
                    st["incident_id"]  = inc_id
                    st["event_type"]   = "BULLYING_CONFIRMED"
                    st["attack_type"]  = attack_type
                    st["action"]       = action_label
                    st["confidence"]   = round(confidence, 4)
                    st["attacker_id"]  = attacker_id
                    st["victim_id"]    = victim_id
                    st["started_at"]   = now_iso
                    st["last_detected_at"] = now_iso
                    st["reason"]       = reason
                    st["acknowledged"] = False

                    # Save snapshot JPEG
                    if frame_1080p is not None:
                        snap_name = f"{inc_id}_snap.jpg"
                        snap_path = os.path.join(self.config.INCIDENTS_DIR, snap_name)
                        try:
                            cv2.imwrite(snap_path, frame_1080p)
                            st["snapshot_path"] = f"/incidents/{snap_name}"
                        except Exception as e:
                            print(f"[ALARM MANAGER] Snapshot save error: {e}")

                    print(f"\n{'='*50}")
                    print(f" *** BULLYING ALARM TRIGGERED ***")
                    print(f" Camera:     {camera_id}")
                    print(f" Incident:   {inc_id}")
                    print(f" Type:       {attack_type}")
                    print(f" Attacker:   Track ID {attacker_id}")
                    print(f" Victim:     Track ID {victim_id}")
                    print(f" Confidence: {int(confidence*100)}%")
                    print(f" Reason:     {reason}")
                    print(f"{'='*50}\n")

                else:
                    # ---- Ongoing alarm: update fields dynamically ----
                    st["last_detected_at"] = now_iso
                    st["confidence"]       = round(max(confidence, st["confidence"]), 4)
                    if attacker_id is not None:
                        st["attacker_id"] = attacker_id
                    if victim_id is not None:
                        st["victim_id"]   = victim_id

                return dict(st)

            # ================================================================
            # NO BULLYING: evidence absent or state machine not confirmed
            # ================================================================
            if current == "ALARM_ACTIVE":
                # Alarm was running but bullying_confirmed just dropped to False.
                # The BullyingStateMachine is counting stop_frames internally.
                # We keep alarm_active True until SM signals SAVE_CLIP.
                # (Do nothing here — SM will transition to SAVE_CLIP when ready)
                return dict(st)

            elif current in ("CONFIRMING",):
                st["state"]            = "IDLE"
                st["consecutive_hits"] = 0
                st["alarm_active"]     = False

            elif current == "IDLE":
                pass   # Normal, nothing to do

            return dict(st)

    # ---------------------------------------------------------------- clip path

    def set_clip_path(self, incident_id: str, clip_rel_path: str):
        """
        Called by camera_stream after the clip file has been saved to disk.
        Updates both the in-memory incident record and incidents.json.
        """
        with self.lock:
            # Update in-memory history
            for inc in self.incidents_history:
                if inc.get("incident_id") == incident_id:
                    inc["clip_path"] = clip_rel_path
                    break

            # Update active camera state if it matches
            for cid, st in self.camera_states.items():
                if st.get("incident_id") == incident_id:
                    st["clip_path"] = clip_rel_path

            self._save_incidents()
            print(f"[ALARM MANAGER] Clip path updated for {incident_id}: {clip_rel_path}")

    # ---------------------------------------------------------------- actions

    def acknowledge_alarm(self, camera_id: str) -> bool:
        """Silence audio alarm for camera_id."""
        with self.lock:
            if camera_id in self.camera_states:
                self.camera_states[camera_id]["acknowledged"] = True
                print(f"[ALARM MANAGER] {camera_id}: alarm acknowledged")
                return True
        return False

    def delete_incident(self, incident_id: str) -> bool:
        """Permanently delete an incident from history and reset active state if matched."""
        with self.lock:
            before = len(self.incidents_history)
            self.incidents_history = [
                inc for inc in self.incidents_history
                if inc.get("incident_id") != incident_id
            ]
            for cid, st in self.camera_states.items():
                if st.get("incident_id") == incident_id:
                    st.update(self._default_state(cid))
            self._save_incidents()
            deleted = len(self.incidents_history) < before
            print(f"[ALARM MANAGER] Deleted incident {incident_id}: {before}→{len(self.incidents_history)}")
            return deleted


# Global singleton
alarm_manager = AlarmManager()
