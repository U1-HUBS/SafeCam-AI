"""
SAFECAM — Alarm Safety Gate Component
======================================
SINGLE AUTHORITATIVE ALARM SAFETY GATE:
  should_trigger_alarm()

Enforces that NO raw prediction, confidence threshold, isolated movement,
or single-person gesture can EVER create a bullying alarm.

An alarm is triggered ONLY when ALL 7 MANDATORY CONDITIONS are MET:
  1. tracked_people >= 2
  2. attack_engine_result.confirmed_attack == True
  3. attack_type in ("PUNCH", "KICK")
  4. attacker_track_id is valid (not None)
  5. victim_track_id is valid (not None)
  6. contact_evidence.contact_confirmed == True
  7. confirmation_frames >= 3
"""

from typing import NamedTuple, Optional
from .attack_engine import AttackEngineResult
from .contact_detector import ContactEvidence


class AlarmGateResult(NamedTuple):
    should_alarm:        bool
    reason:              str
    attack_type:         Optional[str]
    confidence:          float
    attacker_track_id:   Optional[int]
    victim_track_id:     Optional[int]


class AlarmGate:
    """
    Single Authoritative Alarm Gate.
    """

    def __init__(self, min_people: int = 2, min_confirm_frames: int = 3):
        self.min_people = min_people
        self.min_confirm_frames = min_confirm_frames

    def evaluate_gate(
        self,
        people_count: int,
        attack_result: AttackEngineResult,
        contact_evidence: Optional[ContactEvidence]
    ) -> AlarmGateResult:
        """
        Evaluates whether an alarm should be triggered for the current frame.
        """
        # Condition 1: Must have 2+ tracked people
        if people_count < self.min_people:
            return AlarmGateResult(
                should_alarm=False,
                reason="SINGLE PERSON — ALARM DISABLED",
                attack_type=None,
                confidence=0.0,
                attacker_track_id=None,
                victim_track_id=None
            )

        # Condition 2: AttackEngine state must be CONFIRMED_ATTACK
        if not attack_result or not attack_result.confirmed_attack:
            return AlarmGateResult(
                should_alarm=False,
                reason=f"NO CONFIRMED ATTACK (state={attack_result.state if attack_result else 'NORMAL'})",
                attack_type=None,
                confidence=0.0,
                attacker_track_id=None,
                victim_track_id=None
            )

        # Condition 3: Attack type must be PUNCH or KICK
        if attack_result.attack_type not in ("PUNCH", "KICK"):
            return AlarmGateResult(
                should_alarm=False,
                reason=f"INVALID ATTACK TYPE ({attack_result.attack_type})",
                attack_type=None,
                confidence=0.0,
                attacker_track_id=None,
                victim_track_id=None
            )

        # Condition 4 & 5: Attacker and Victim IDs must be valid and distinct
        if attack_result.attacker_track_id is None or attack_result.victim_track_id is None or attack_result.attacker_track_id == attack_result.victim_track_id:
            return AlarmGateResult(
                should_alarm=False,
                reason="INVALID ATTACKER/VICTIM ID ASSIGNMENT",
                attack_type=None,
                confidence=0.0,
                attacker_track_id=None,
                victim_track_id=None
            )

        # Condition 6: Contact evidence must be confirmed
        if not contact_evidence or not contact_evidence.contact_confirmed:
            return AlarmGateResult(
                should_alarm=False,
                reason="CONTACT LANDING EVIDENCE UNCONFIRMED",
                attack_type=None,
                confidence=0.0,
                attacker_track_id=None,
                victim_track_id=None
            )

        # Condition 7: Confirmation frames must meet threshold
        if attack_result.confirmation_frames < self.min_confirm_frames:
            return AlarmGateResult(
                should_alarm=False,
                reason=f"TEMPORAL CONFIRMATION INCOMPLETE ({attack_result.confirmation_frames}/{self.min_confirm_frames})",
                attack_type=None,
                confidence=0.0,
                attacker_track_id=None,
                victim_track_id=None
            )

        # ALL 7 CONDITIONS MET! CONFIRMED BULLYING ALARM!
        return AlarmGateResult(
            should_alarm=True,
            reason=f"CONFIRMED {attack_result.attack_type} ATTACK (Attacker ID:{attack_result.attacker_track_id} -> Victim ID:{attack_result.victim_track_id})",
            attack_type=attack_result.attack_type,
            confidence=attack_result.confidence,
            attacker_track_id=attack_result.attacker_track_id,
            victim_track_id=attack_result.victim_track_id
        )


def should_trigger_alarm(
    people_count: int,
    attack_result: AttackEngineResult,
    contact_evidence: Optional[ContactEvidence]
) -> bool:
    """Helper global gate check function."""
    gate = AlarmGate()
    return gate.evaluate_gate(people_count, attack_result, contact_evidence).should_alarm
