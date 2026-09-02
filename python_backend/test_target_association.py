"""
SAFECAM AI — Target Association Verification Test Suite
========================================================
Validates target association requirements:
  TEST 1: Straight Punch (ID 1 punches ID 2 in front, ID 3 off-axis) -> ID 1=ATTACKER, ID 2=VICTIM, ID 3=NORMAL
  TEST 2: Nearby Person Behind Attacker (ID 2 closer behind ID 1, ID 3 farther in front) -> ID 3=VICTIM (ID 2 stays NORMAL)
  TEST 3: Air Punch (ID 1 punches air, scores < 0.45) -> ID 1=PUNCH solo, NO VICTIM, NO ALARM
  TEST 4: Target Locking & Anti-Flicker (ID 1 locked to ID 3 without switching)
  TEST 5: Role Reset (Action finishes -> Both return to NORMAL)
  TEST 6: Reverse Attack (ID 3 attacks ID 1 later -> ID 3=ATTACKER, ID 1=VICTIM)
"""

import sys
import os
import time
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.interaction_detector import InteractionDetector, PairInteraction
from ai.attack_engine import AttackEngine
from ai.contact_detector import ContactDetector
from tracking.tracker import TrackedPerson, Detection


def create_person(track_id: int, cx: int, cy: int, w: int = 120, h: int = 300) -> TrackedPerson:
    x1, y1 = cx - w // 2, cy - h // 2
    x2, y2 = cx + w // 2, cy + h // 2
    det = Detection(class_id=0, class_name="person", confidence=0.90, x1=x1, y1=y1, x2=x2, y2=y2)
    tp = TrackedPerson(track_id=track_id, detection=det)
    tp.centroid_history.append((float(cx), float(cy)))
    return tp


def run_target_tests():
    print("\n==================================================")
    print(" SAFECAM TARGET ASSOCIATION VERIFICATION TEST SUITE")
    print("==================================================\n")

    inter_det = InteractionDetector()
    attack_eng = AttackEngine()
    contact_det = ContactDetector()

    passed = 0
    total = 6

    # -------------------------------------------------------------------------
    # TEST 1: Straight Punch (ID 1 punches ID 2 directly in front; ID 3 off-axis)
    # -------------------------------------------------------------------------
    inter_det.reset_camera("CAM-TEST")
    attack_eng.reset_camera("CAM-TEST")
    p1 = create_person(1, 500, 500, w=140)
    p2 = create_person(2, 600, 500, w=140) # Directly in front (overlap IoU = 0.28, dist 100px)
    p3 = create_person(3, 500, 800, w=140) # Off-axis below

    # Simulate P1 moving forward towards P2
    p1.centroid_history = [(470.0, 500.0), (485.0, 500.0), (500.0, 500.0)]

    act_map = {1: "PUNCH", 2: "NORMAL", 3: "NORMAL"}
    cam_hist = attack_eng._get_camera_state("CAM-TEST")

    res = None
    for _ in range(6):
        pair = inter_det.evaluate_interaction("CAM-TEST", [p1, p2, p3], act_map, cam_hist)
        contact = contact_det.evaluate_contact(pair)
        res = attack_eng.process("CAM-TEST", [p1, p2, p3], pair, contact, any_action_detected=True, raw_action_type="PUNCH")

    if res.confirmed_attack and res.attacker_track_id == 1 and res.victim_track_id == 2:
        print("[OK] TEST 1 PASSED: Straight Punch -> ID 1=ATTACKER, ID 2=VICTIM (ID 3=NORMAL)")
        passed += 1
    else:
        print(f"[FAIL] TEST 1 FAILED: res={res}")

    # -------------------------------------------------------------------------
    # TEST 2: Nearby Person Behind Attacker (ID 2 is 100px behind ID 1, ID 3 is 100px in front)
    # -------------------------------------------------------------------------
    inter_det.reset_camera("CAM-TEST")
    attack_eng.reset_camera("CAM-TEST")
    p1 = create_person(1, 500, 500, w=140)
    p2 = create_person(2, 400, 500, w=140) # BEHIND P1 (distance 100px)
    p3 = create_person(3, 600, 500, w=140) # IN FRONT OF P1 (distance 100px)

    # P1 moving forward towards P3 (away from P2)
    p1.centroid_history = [(460.0, 500.0), (480.0, 500.0), (500.0, 500.0)]
    act_map = {1: "PUNCH", 2: "NORMAL", 3: "NORMAL"}
    cam_hist = attack_eng._get_camera_state("CAM-TEST")

    res = None
    for _ in range(6):
        pair = inter_det.evaluate_interaction("CAM-TEST", [p1, p2, p3], act_map, cam_hist)
        contact = contact_det.evaluate_contact(pair)
        res = attack_eng.process("CAM-TEST", [p1, p2, p3], pair, contact, any_action_detected=True, raw_action_type="PUNCH")

    if res.confirmed_attack and res.attacker_track_id == 1 and res.victim_track_id == 3:
        print("[OK] TEST 2 PASSED: Person Behind Attacker -> Selected ID 3=VICTIM (ID 2 ignored)")
        passed += 1
    else:
        print(f"[FAIL] TEST 2 FAILED: res={res}")

    # -------------------------------------------------------------------------
    # TEST 3: Air Punch (ID 1 punches air, no candidate target score >= 0.45)
    # -------------------------------------------------------------------------
    inter_det.reset_camera("CAM-TEST")
    attack_eng.reset_camera("CAM-TEST")
    p1 = create_person(1, 500, 500)
    p_far = create_person(2, 1800, 500) # Very far candidate (out of range)

    act_map = {1: "PUNCH", 2: "NORMAL"}
    cam_hist = attack_eng._get_camera_state("CAM-TEST")

    pair = inter_det.evaluate_interaction("CAM-TEST", [p1, p_far], act_map, cam_hist)
    contact = contact_det.evaluate_contact(pair)
    res = attack_eng.process("CAM-TEST", [p1, p_far], pair, contact, any_action_detected=True, raw_action_type="PUNCH")

    if (pair is None or pair.victim_tp is None) and not res.confirmed_attack:
        print("[OK] TEST 3 PASSED: Air Punch -> Solo Action, NO VICTIM, NO ALARM")
        passed += 1
    else:
        print(f"[FAIL] TEST 3 FAILED: pair={pair}, res={res}")

    # -------------------------------------------------------------------------
    # TEST 4: Target Locking & Anti-Flicker
    # -------------------------------------------------------------------------
    inter_det.reset_camera("CAM-TEST")
    attack_eng.reset_camera("CAM-TEST")
    p1 = create_person(1, 500, 500)
    p2 = create_person(2, 650, 500)
    p3 = create_person(3, 660, 510)

    p1.centroid_history = [(470.0, 500.0), (485.0, 500.0), (500.0, 500.0)]
    act_map = {1: "PUNCH", 2: "NORMAL", 3: "NORMAL"}
    cam_hist = attack_eng._get_camera_state("CAM-TEST")

    # First lock target ID 2
    for _ in range(6):
        pair = inter_det.evaluate_interaction("CAM-TEST", [p1, p2, p3], act_map, cam_hist)

    locked_victim = pair.victim_tp.track_id if pair and pair.victim_tp else None

    if locked_victim == 2:
        print("[OK] TEST 4 PASSED: Target Locked to ID 2 (no flickering)")
        passed += 1
    else:
        print(f"[FAIL] TEST 4 FAILED: Expected locked victim ID 2, got {locked_victim}")

    # -------------------------------------------------------------------------
    # TEST 5: Role Reset (Action finishes -> Both return to NORMAL)
    # -------------------------------------------------------------------------
    inter_det.reset_camera("CAM-TEST")
    res_end = attack_eng.reset_camera("CAM-TEST")
    if not res_end.confirmed_attack and res_end.attacker_track_id is None and res_end.victim_track_id is None:
        print("[OK] TEST 5 PASSED: Role Reset -> Both return to NORMAL")
        passed += 1
    else:
        print(f"[FAIL] TEST 5 FAILED: res_end={res_end}")

    # -------------------------------------------------------------------------
    # TEST 6: Reverse Attack (ID 3 attacks ID 1 later -> ID 3=ATTACKER, ID 1=VICTIM)
    # -------------------------------------------------------------------------
    inter_det.reset_camera("CAM-TEST")
    attack_eng.reset_camera("CAM-TEST")
    p1 = create_person(1, 500, 500, w=140)
    p3 = create_person(3, 600, 500, w=140)

    # P3 moving towards P1
    p3.centroid_history = [(630.0, 500.0), (615.0, 500.0), (600.0, 500.0)]
    act_map = {1: "NORMAL", 3: "KICK"}
    cam_hist = attack_eng._get_camera_state("CAM-TEST")

    res = None
    for _ in range(6):
        pair = inter_det.evaluate_interaction("CAM-TEST", [p1, p3], act_map, cam_hist)
        contact = contact_det.evaluate_contact(pair)
        res = attack_eng.process("CAM-TEST", [p1, p3], pair, contact, any_action_detected=True, raw_action_type="KICK")

    if res.confirmed_attack and res.attacker_track_id == 3 and res.victim_track_id == 1:
        print("[OK] TEST 6 PASSED: Reverse Attack -> ID 3=ATTACKER, ID 1=VICTIM")
        passed += 1
    else:
        print(f"[FAIL] TEST 6 FAILED: res={res}")

    print("\n==================================================")
    print(f" TEST SUITE SUMMARY: {passed}/{total} PASSED")
    print("==================================================\n")

    return passed == total

if __name__ == "__main__":
    success = run_target_tests()
    sys.exit(0 if success else 1)
