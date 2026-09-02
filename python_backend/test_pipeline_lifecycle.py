"""
SAFECAM — Camera Pipeline Lifecycle Integration Test
=====================================================
Tests viewer connect/disconnect, active_viewers count tracking,
and clean pipeline start/stop behavior.
"""

import sys
import os
import time

# Add python_backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from camera_stream import CameraManager

def run_lifecycle_tests():
    print("==================================================")
    print(" SAFECAM Pipeline Lifecycle Test Suite")
    print("==================================================\n")

    cm = CameraManager()
    cam_id = "test_cam_lifecycle_01"

    # -------------------------------------------------------------------------
    # TEST 1: Initial state (No active pipelines for test_cam_lifecycle_01)
    # -------------------------------------------------------------------------
    assert cam_id not in cm.pipelines
    print("[PASS] TEST 1: Initial state — No active pipelines")

    # -------------------------------------------------------------------------
    # TEST 2: First viewer connects
    # -------------------------------------------------------------------------
    p = cm.get_or_create_pipeline(camera_id=cam_id, stream_url="")
    p.add_viewer()
    assert p.active_viewers == 1
    assert p.running == True
    print("[PASS] TEST 2: First viewer connected -> active_viewers = 1, running = True")

    # -------------------------------------------------------------------------
    # TEST 3: Second viewer connects to same camera
    # -------------------------------------------------------------------------
    p_again = cm.get_or_create_pipeline(camera_id=cam_id, stream_url="")
    assert p_again is p  # Shared pipeline instance
    p.add_viewer()
    assert p.active_viewers == 2
    assert p.running == True
    print("[PASS] TEST 3: Second viewer connected -> active_viewers = 2, running = True")

    # -------------------------------------------------------------------------
    # TEST 4: First viewer disconnects
    # -------------------------------------------------------------------------
    p.remove_viewer()
    assert p.active_viewers == 1
    assert p.running == True
    print("[PASS] TEST 4: One viewer disconnected -> active_viewers = 1, running = True (Pipeline kept active)")

    # -------------------------------------------------------------------------
    # TEST 5: Last viewer disconnects
    # -------------------------------------------------------------------------
    p.remove_viewer()
    assert p.active_viewers == 0
    assert p.running == False
    cm.release_pipeline(cam_id)
    assert cam_id not in cm.pipelines
    print("[PASS] TEST 5: Last viewer disconnected -> active_viewers = 0, running = False (Pipeline stopped & released)")

    # -------------------------------------------------------------------------
    # TEST 6: Re-connect viewer after shutdown
    # -------------------------------------------------------------------------
    p2 = cm.get_or_create_pipeline(camera_id=cam_id, stream_url="")
    p2.add_viewer()
    assert p2.active_viewers == 1
    assert p2.running == True
    print("[PASS] TEST 6: Re-connect viewer -> Fresh pipeline created & running = True")

    # -------------------------------------------------------------------------
    # TEST 7: Cleanup test camera
    # -------------------------------------------------------------------------
    p2.remove_viewer()
    cm.release_pipeline(cam_id)
    assert cam_id not in cm.pipelines
    assert p2.running == False
    print("[PASS] TEST 7: Final cleanup -> Pipeline released cleanly")

    print("\n==================================================")
    print(" ALL PIPELINE LIFECYCLE TESTS PASSED SUCCESSFULLY!")
    print("==================================================\n")

if __name__ == "__main__":
    run_lifecycle_tests()
