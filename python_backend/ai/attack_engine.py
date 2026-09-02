"""
SAFECAM — 5-State Attack Engine Component
==========================================
State Machine States:
  1. NORMAL               — No attack evidence.
  2. POSSIBLE_ACTION      — PUNCH or KICK detected, 1 person or no target yet. (NO ALARM)
  3. POSSIBLE_INTERACTION — 2+ people present, action directed toward target. (NO ALARM)
  4. CONTACT_CANDIDATE    — Action + Target + Proximity & Overlap evidence. (NO ALARM YET)
  5. CONFIRMED_ATTACK     — Contact evidence sustained for 3 consecutive frames. (BULLYING ALARM)
"""

from typing import NamedTuple, Optional, List, Dict
try:
    from tracking.tracker import TrackedPerson
except ImportError:
    from python_backend.tracking.tracker import TrackedPerson

from .interaction_detector import PairInteraction
from .contact_detector import ContactEvidence


class AttackEngineResult(NamedTuple):
    state:               str        # "NORMAL", "POSSIBLE_ACTION", "POSSIBLE_INTERACTION", "CONTACT_CANDIDATE", "CONFIRMED_ATTACK"
    confirmed_attack:    bool       # True ONLY when state == "CONFIRMED_ATTACK"
    attack_type:         Optional[str]   # "PUNCH" or "KICK"
    confidence:          float
    attacker_track_id:   Optional[int]
    victim_track_id:     Optional[int]
    confirmation_frames: int
    reason:              str
    dist_normalized:     float
    contact_overlap:     float


def default_camera_attack_state() -> Dict:
    return {
        "state":               "NORMAL",
        "confirmed_attack":    False,
        "attack_type":         None,
        "confidence":          0.0,
        "attacker_track_id":   None,
        "victim_track_id":     None,
        "confirmation_frames": 0,
        "stop_frames":         0,
        "distance_history":    [],
        "prev_attack_cx":      None,
        "prev_attack_cy":      None,
        "prev_victim_cx":      None,
        "prev_victim_cy":      None,
        "prev_dist_norm":      None,
    }


class AttackEngine:
    """
    5-State State Machine Engine per camera.
    """

    def __init__(self, confirm_frames: int = 3, stop_frames: int = 2):
        self.confirm_frames = confirm_frames
        self.stop_frames = stop_frames
        self._states: Dict[str, dict] = {}

    def _get_camera_state(self, camera_id: str) -> dict:
        if camera_id not in self._states:
            self._states[camera_id] = default_camera_attack_state()
        return self._states[camera_id]

    def reset_camera(self, camera_id: str, reason: str = "Reset to NORMAL") -> AttackEngineResult:
        st = self._get_camera_state(camera_id)
        st.update(default_camera_attack_state())
        return AttackEngineResult(
            state="NORMAL",
            confirmed_attack=False,
            attack_type=None,
            confidence=0.0,
            attacker_track_id=None,
            victim_track_id=None,
            confirmation_frames=0,
            reason=reason,
            dist_normalized=1.0,
            contact_overlap=0.0
        )

    def process(
        self,
        camera_id: str,
        tracked_persons: List[TrackedPerson],
        pair_interaction: Optional[PairInteraction],
        contact_evidence: Optional[ContactEvidence],
        any_action_detected: bool = False,
        raw_action_type: Optional[str] = None
    ) -> AttackEngineResult:
        """
        Processes frame evidence through the 5-state state machine.
        """
        st = self._get_camera_state(camera_id)

        # ====================================================================
        # ABSOLUTE ONE-PERSON RULE
        # If tracked_people < 2, force reset immediately to NORMAL
        # ====================================================================
        if not tracked_persons or len(tracked_persons) < 2:
            return self.reset_camera(camera_id, reason="SINGLE PERSON - ATTACK DISABLED")

        # ====================================================================
        # STATE MACHINE TRANSITIONS
        # ====================================================================
        current_state = st["state"]

        if not pair_interaction or pair_interaction.victim_tp is None:
            # 2+ people present, but no directional pair interaction or no confirmed victim
            if any_action_detected:
                st["state"] = "POSSIBLE_ACTION"
                st["reason"] = f"Raw {raw_action_type} detected without pair target"
            else:
                return self.reset_camera(camera_id, reason="No action or pair interaction")

            return AttackEngineResult(
                state=st["state"],
                confirmed_attack=False,
                attack_type=None,
                confidence=0.0,
                attacker_track_id=None,
                victim_track_id=None,
                confirmation_frames=0,
                reason=st["reason"],
                dist_normalized=1.0,
                contact_overlap=0.0
            )

        # We have a valid 2-person pair interaction!
        attacker_id = pair_interaction.attacker_tp.track_id
        victim_id = pair_interaction.victim_tp.track_id
        attack_type = pair_interaction.attack_action
        action_conf = pair_interaction.action_confidence
        contact_ok = contact_evidence.contact_confirmed if contact_evidence else False

        # Update history
        st["prev_attack_cx"] = pair_interaction.attacker_tp.detection.cx
        st["prev_attack_cy"] = pair_interaction.attacker_tp.detection.cy
        st["prev_victim_cx"] = pair_interaction.victim_tp.detection.cx
        st["prev_victim_cy"] = pair_interaction.victim_tp.detection.cy
        st["prev_dist_norm"] = pair_interaction.dist_normalized
        st["distance_history"].append(pair_interaction.dist_normalized)
        if len(st["distance_history"]) > 15:
            st["distance_history"].pop(0)

        # Handle dynamic role change (e.g., Person 2 attacks Person 1 after Person 1 attacked Person 2)
        if st.get("attacker_track_id") is not None and st.get("attacker_track_id") != attacker_id:
            st["attacker_track_id"] = attacker_id
            st["victim_track_id"] = victim_id
            st["attack_type"] = attack_type
            st["confidence"] = action_conf
            st["confirmation_frames"] = 1 if contact_ok else 0

        # Transition rules
        if current_state in ("NORMAL", "POSSIBLE_ACTION"):
            st["state"] = "POSSIBLE_INTERACTION"
            st["attacker_track_id"] = attacker_id
            st["victim_track_id"] = victim_id
            st["attack_type"] = attack_type
            st["confidence"] = action_conf
            st["confirmation_frames"] = 0

        elif current_state == "POSSIBLE_INTERACTION":
            st["attacker_track_id"] = attacker_id
            st["victim_track_id"] = victim_id
            st["attack_type"] = attack_type
            if contact_ok:
                st["state"] = "CONTACT_CANDIDATE"
                st["confirmation_frames"] = 1
            else:
                st["state"] = "POSSIBLE_INTERACTION"

        elif current_state == "CONTACT_CANDIDATE":
            if contact_ok and st.get("attacker_track_id") == attacker_id:
                st["confirmation_frames"] += 1
                st["confidence"] = max(st["confidence"], action_conf)
                if st["confirmation_frames"] >= self.confirm_frames:
                    st["state"] = "CONFIRMED_ATTACK"
                    st["confirmed_attack"] = True
            else:
                st["confirmation_frames"] = 0
                st["state"] = "POSSIBLE_INTERACTION"

        elif current_state == "CONFIRMED_ATTACK":
            if contact_ok and st.get("attacker_track_id") == attacker_id:
                st["stop_frames"] = 0
                st["confidence"] = max(st["confidence"], action_conf)
            else:
                st["stop_frames"] += 1
                if st["stop_frames"] >= self.stop_frames:
                    return self.reset_camera(camera_id, reason="Attack ended — back to NORMAL")

        confirmed_attack = (st["state"] == "CONFIRMED_ATTACK")
        reason = f"{st['state']}: {attack_type} conf={action_conf:.2f}"

        return AttackEngineResult(
            state=st["state"],
            confirmed_attack=confirmed_attack,
            attack_type=st.get("attack_type"),
            confidence=st.get("confidence", 0.0),
            attacker_track_id=st.get("attacker_track_id") if confirmed_attack else None,
            victim_track_id=st.get("victim_track_id") if confirmed_attack else None,
            confirmation_frames=st.get("confirmation_frames", 0),
            reason=reason,
            dist_normalized=pair_interaction.dist_normalized,
            contact_overlap=contact_evidence.overlap_iou if contact_evidence else 0.0
        )
