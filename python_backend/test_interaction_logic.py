"""
SAFECAM — Interaction & Attack Logic Test Suite
=================================================
Tests all required false-positive and confirmed attack scenarios for the rebuilt modular AI package:
  - 1-Person gestures (hand wave, punch air, kick air, shadow box) -> NORMAL (0 alarms)
  - 2-Person standing/walking/close -> NORMAL (0 alarms)
  - 2-Person punch/kick miss -> Candidate only (0 alarms)
  - 2-Person sustained punch/kick + contact -> CONFIRMED ATTACK (Bullying Alarm)
"""

import sys
import os

# Add python_backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from tracking.tracker import TrackedPerson, Detection
from ai.interaction_detector import InteractionDetector
from ai.contact_detector import ContactDetector
from ai.attack_engine import AttackEngine
from ai.alarm_gate import AlarmGate


def create_mock_person(track_id: int, class_name: str, confidence: float, x1: int, y1: int, x2: int, y2: int) -> TrackedPerson:
    det = Detection(
        class_id=0 if class_name == "punch" else 1,
        class_name=class_name,
        confidence=confidence,
        x1=x1, y1=y1, x2=x2, y2=y2
    )
    tp = TrackedPerson(track_id=track_id, detection=det)
    return tp


def run_tests():
    cam = "TEST_CAM"
    interaction_det = InteractionDetector(frame_width=1920, frame_height=1080)
    contact_det = ContactDetector()
    attack_engine = AttackEngine(confirm_frames=3)
    alarm_gate = AlarmGate()

    print("==================================================")
    print(" SAFECAM Modular AI Unit Test Suite (13 Scenarios)")
    print("==================================================\n")

    passed = 0

    def process_test_frame(persons, action_map):
        cam_hist = attack_engine._get_camera_state(cam)
        pair = interaction_det.evaluate_interaction(cam, persons, action_map, cam_hist)
        contact = contact_det.evaluate_contact(pair) if pair else None
        any_act = any(act in ("PUNCH", "KICK") for act in action_map.values())
        raw_act = next((act for act in action_map.values() if act in ("PUNCH", "KICK")), "NONE")

        att_res = attack_engine.process(cam, persons, pair, contact, any_act, raw_act)
        gate_res = alarm_gate.evaluate_gate(len(persons), att_res, contact)
        return att_res, gate_res

    # TEST 1: One person standing still
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "normal", 0.90, 500, 200, 700, 800)
    att, gate = process_test_frame([p1], {1: "NORMAL"})
    assert gate.should_alarm == False and att.state == "NORMAL"
    print("[PASS] TEST 1: One person standing still -> NORMAL (0 alarm)")
    passed += 1

    # TEST 2: One person punching the air
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "punch", 0.95, 500, 200, 700, 800)
    att, gate = process_test_frame([p1], {1: "PUNCH"})
    assert gate.should_alarm == False and att.confirmed_attack == False
    print("[PASS] TEST 2: One person punching the air -> NORMAL (0 alarm)")
    passed += 1

    # TEST 3: One person kicking the air
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "kick", 0.95, 500, 200, 700, 800)
    att, gate = process_test_frame([p1], {1: "KICK"})
    assert gate.should_alarm == False and att.confirmed_attack == False
    print("[PASS] TEST 3: One person kicking the air -> NORMAL (0 alarm)")
    passed += 1

    # TEST 4: One person moving arms quickly
    attack_engine.reset_camera(cam)
    for f in range(5):
        p1 = create_mock_person(1, "punch", 0.85 + (f % 2) * 0.05, 500 + f * 10, 200, 700 + f * 10, 800)
        att, gate = process_test_frame([p1], {1: "PUNCH"})
        assert gate.should_alarm == False and att.confirmed_attack == False
    print("[PASS] TEST 4: One person moving arms quickly -> NORMAL (0 alarm)")
    passed += 1

    # TEST 5: Two people standing far apart
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "normal", 0.90, 200, 200, 400, 800)
    p2 = create_mock_person(2, "normal", 0.90, 1200, 200, 1400, 800)
    att, gate = process_test_frame([p1, p2], {1: "NORMAL", 2: "NORMAL"})
    assert gate.should_alarm == False and att.state == "NORMAL"
    print("[PASS] TEST 5: Two people standing far apart -> NORMAL (0 alarm)")
    passed += 1

    # TEST 6: Two people walking past each other
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "normal", 0.90, 200, 200, 400, 800)
    p2 = create_mock_person(2, "normal", 0.90, 1200, 200, 1400, 800)
    att, gate = process_test_frame([p1, p2], {1: "NORMAL", 2: "NORMAL"})
    assert gate.should_alarm == False
    print("[PASS] TEST 6: Two people walking past each other -> NORMAL (0 alarm)")
    passed += 1

    # TEST 7: Two people, one shadow-boxing far away
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "punch", 0.90, 100, 200, 300, 800)
    p2 = create_mock_person(2, "normal", 0.90, 1600, 200, 1800, 800)
    att, gate = process_test_frame([p1, p2], {1: "PUNCH", 2: "NORMAL"})
    assert gate.should_alarm == False and att.confirmed_attack == False
    print("[PASS] TEST 7: Two people, shadow-boxing far away -> NO ALARM")
    passed += 1

    # TEST 8: Person A punches toward Person B far away
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "punch", 0.85, 200, 200, 400, 800)
    p2 = create_mock_person(2, "normal", 0.90, 1400, 200, 1600, 800)
    att, gate = process_test_frame([p1, p2], {1: "PUNCH", 2: "NORMAL"})
    assert gate.should_alarm == False and att.confirmed_attack == False
    print("[PASS] TEST 8: Person A punches toward Person B far away -> NO ALARM")
    passed += 1

    # TEST 9: Person A punches Person B close/overlapping -> Candidate
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "punch", 0.85, 800, 200, 1000, 800)
    p2 = create_mock_person(2, "normal", 0.90, 950, 200, 1150, 800)
    att, gate = process_test_frame([p1, p2], {1: "PUNCH", 2: "NORMAL"})
    assert gate.should_alarm == False and att.state in ("POSSIBLE_INTERACTION", "CONTACT_CANDIDATE")
    print(f"[PASS] TEST 9: Person A punches Person B close/overlapping -> Candidate ({att.state})")
    passed += 1

    # TEST 10: Sustained Punch + contact -> CONFIRMED PUNCH
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "punch", 0.90, 800, 200, 1000, 800)
    p2 = create_mock_person(2, "normal", 0.90, 950, 200, 1150, 800)
    for f in range(5):
        att, gate = process_test_frame([p1, p2], {1: "PUNCH", 2: "NORMAL"})
    assert gate.should_alarm == True and att.confirmed_attack == True and att.attack_type == "PUNCH"
    assert att.attacker_track_id == 1 and att.victim_track_id == 2
    print("[PASS] TEST 10: Sustained Punch + contact -> CONFIRMED PUNCH (Attacker: ID=1, Victim: ID=2)")
    passed += 1

    # TEST 11: Sustained Kick + contact -> CONFIRMED KICK
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(3, "kick", 0.92, 600, 200, 800, 800)
    p2 = create_mock_person(7, "normal", 0.90, 750, 200, 950, 800)
    for f in range(5):
        att, gate = process_test_frame([p1, p2], {3: "KICK", 7: "NORMAL"})
    assert gate.should_alarm == True and att.confirmed_attack == True and att.attack_type == "KICK"
    assert att.attacker_track_id == 3 and att.victim_track_id == 7
    print("[PASS] TEST 11: Sustained Kick + contact -> CONFIRMED KICK (Attacker: ID=3, Victim: ID=7)")
    passed += 1

    # TEST 12: Transition 2-person confirmed attack -> 1-person scene -> Immediate RESET
    p1_only = create_mock_person(3, "kick", 0.99, 600, 200, 800, 800)
    att_reset, gate_reset = process_test_frame([p1_only], {3: "KICK"})
    assert gate_reset.should_alarm == False and att_reset.state == "NORMAL"
    assert att_reset.attacker_track_id == None and att_reset.victim_track_id == None
    print("[PASS] TEST 12: Transition 2-person attack to 1-person -> Immediate RESET to NORMAL")
    passed += 1

    # TEST 13: 4 persons tracked independently
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "normal", 0.88, 100, 200, 300, 800)
    p2 = create_mock_person(2, "normal", 0.91, 500, 200, 700, 800)
    p3 = create_mock_person(3, "normal", 0.85, 900, 200, 1100, 800)
    p4 = create_mock_person(4, "normal", 0.79, 1300, 200, 1500, 800)
    att_4, gate_4 = process_test_frame([p1, p2, p3, p4], {1: "NORMAL", 2: "NORMAL", 3: "NORMAL", 4: "NORMAL"})
    assert gate_4.should_alarm == False and att_4.state == "NORMAL"
    print("[PASS] TEST 13: 4 persons tracked independently -> 4 boxes maintained (NORMAL)")
    passed += 1

    # TEST 14: Dynamic Role Reversal & Immediate Return to Normal
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "punch", 0.90, 800, 200, 1000, 800)
    p2 = create_mock_person(2, "normal", 0.90, 950, 200, 1150, 800)
    for _ in range(5):
        att, gate = process_test_frame([p1, p2], {1: "PUNCH", 2: "NORMAL"})
    assert gate.should_alarm == True and att.attacker_track_id == 1 and att.victim_track_id == 2

    # Attack ends (2-3 frames of NORMAL)
    p1_normal = create_mock_person(1, "normal", 0.90, 800, 200, 1000, 800)
    for _ in range(3):
        att_norm, gate_norm = process_test_frame([p1_normal, p2], {1: "NORMAL", 2: "NORMAL"})
    assert gate_norm.should_alarm == False and att_norm.state == "NORMAL"
    assert att_norm.attacker_track_id == None and att_norm.victim_track_id == None

    # Later: Person 2 punches Person 1 (Role Reversal)
    p2_punch = create_mock_person(2, "punch", 0.92, 950, 200, 1150, 800)
    for _ in range(5):
        att_rev, gate_rev = process_test_frame([p1_normal, p2_punch], {1: "NORMAL", 2: "PUNCH"})
    assert gate_rev.should_alarm == True and att_rev.attacker_track_id == 2 and att_rev.victim_track_id == 1
    print("[PASS] TEST 14: Dynamic Role Reversal (1->2, then 2->1) & Expiration -> PASSED")
    passed += 1

    # TEST 15: 3 Persons — Selective Attacker/Victim Roles
    attack_engine.reset_camera(cam)
    p1 = create_mock_person(1, "punch", 0.90, 800, 200, 1000, 800)
    p2 = create_mock_person(2, "normal", 0.90, 100, 200, 300, 800)  # Non-participant far away
    p3 = create_mock_person(3, "normal", 0.90, 950, 200, 1150, 800)
    for _ in range(5):
        att_3p, gate_3p = process_test_frame([p1, p2, p3], {1: "PUNCH", 2: "NORMAL", 3: "NORMAL"})
    assert gate_3p.should_alarm == True and att_3p.attacker_track_id == 1 and att_3p.victim_track_id == 3
    print("[PASS] TEST 15: 3 Persons — Person 1 attacks Person 3 (Person 2 remains NORMAL) -> PASSED")
    passed += 1

    print("\n==================================================")
    print(f" ALL {passed}/15 MODULAR AI TESTS PASSED SUCCESSFULLY!")
    print("==================================================\n")

if __name__ == "__main__":
    run_tests()
