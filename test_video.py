import cv2
import sys
import os
import time
import argparse

# Add python_backend to module search path
sys.path.append(os.path.join(os.path.dirname(__file__), "python_backend"))

try:
    from python_backend.ai_engine import AIEngine  # pyrefly: ignore [missing-import] # type: ignore
    from python_backend.alarm_config import alarm_config  # pyrefly: ignore [missing-import] # type: ignore
except ImportError:
    from ai_engine import AIEngine  # pyrefly: ignore [missing-import] # type: ignore
    from alarm_config import alarm_config  # pyrefly: ignore [missing-import] # type: ignore

def run_video_test(video_path, save_output=False, display=True):
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file not found: {video_path}")
        return

    interval = getattr(alarm_config, "AI_FRAME_INTERVAL", getattr(alarm_config, "ROBOFLOW_FRAME_INTERVAL", 1))
    conf_thresh = getattr(alarm_config, "YOLO_CONF_THRESHOLD", 0.20)
    print(f"\n==================================================")
    print(f" SAFECAM Local YOLO11 Video Test")
    print(f" Video Source: {video_path}")
    print(f" Interval:     Every {interval}rd frame")
    print(f" Threshold:    {conf_thresh*100:.0f}%")
    print(f" Models:       yolo11n-pose.pt + safecam_lstm_24.keras")
    print(f"==================================================\n")

    print("[INFO] Initializing Local YOLO11 AIEngine...")
    engine = AIEngine()

    cam_id = f"VIDEO-{os.path.basename(video_path)}"
    # Reset alarm manager camera state for this video test run to avoid previous run's 15s cooldown blocking
    try:
        from python_backend.alarm_manager import alarm_manager  # pyrefly: ignore [missing-import] # type: ignore
    except ImportError:
        from alarm_manager import alarm_manager  # pyrefly: ignore [missing-import] # type: ignore

    alarm_manager.camera_states[cam_id] = alarm_manager.get_default_state(cam_id)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Unable to open video file: {video_path}")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    out = None
    if save_output:
        out_filename = f"output_{os.path.basename(video_path)}"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(out_filename, fourcc, fps, (1920, 1080))
        print(f"[INFO] Saving processed video to: {out_filename}")

    frame_count = 0
    start_time = time.time()
    last_annotated = None

    print("[INFO] Processing frames... Press 'q' or 'ESC' in the window to quit.\n")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                print("\n[INFO] End of video stream.")
                break

            frame_count += 1

            # Process frame with local YOLO11 AIEngine
            if frame_count % interval == 0 or last_annotated is None:
                annotated_frame, telemetry = engine.process_frame(frame, camera_id=cam_id)
                last_annotated = annotated_frame
                
                # Print structured diagnostic telemetry
                imgsz = telemetry.get("yolo_imgsz", 1024)
                y_conf = telemetry.get("yolo_conf_threshold", 0.10)
                det_cls = telemetry.get("detected_class") or "NONE"
                det_conf = telemetry.get("detection_confidence", 0.0)
                people_c = telemetry.get("people_count", 0)
                punch_c = telemetry.get("punch_count", 0)
                kick_c = telemetry.get("kick_count", 0)
                tracked_c = telemetry.get("tracked_persons_count", 0)
                fight_p = telemetry.get("fight_probability", 0.0)
                alarm_st = telemetry.get("alarm_state", {})
                st_name = alarm_st.get("state", "IDLE")
                hits = alarm_st.get("consecutive_hits", 0)

                print(f"[DIAGNOSTIC FRAME {frame_count:04d}] imgsz:{imgsz} | conf_thresh:{y_conf:.2f} | cls:{det_cls} ({det_conf*100:.1f}%) | "
                      f"people:{people_c} | PUNCH:{punch_c} | KICK:{kick_c} | tracked:{tracked_c} | "
                      f"FightProb:{fight_p*100:.1f}% | State:{st_name} (Hits:{hits})")
            else:
                annotated_frame = last_annotated if last_annotated is not None else frame

            if annotated_frame.shape[:2] != (1080, 1920):
                annotated_frame = cv2.resize(annotated_frame, (1920, 1080))

            if out is not None:
                out.write(annotated_frame)

            if display:
                cv2.imshow("SAFECAM Roboflow Cloud API Video Test", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27: # q or ESC
                    print("[INFO] Test manually stopped by user.")
                    break

    except Exception as e:
        print(f"[ERROR] Processing error: {e}")
    finally:
        cap.release()
        if out is not None:
            out.release()
        if display:
            cv2.destroyAllWindows()

        elapsed = time.time() - start_time
        print(f"\n==================================================")
        print(f" Test Completed!")
        print(f" Total Frames Processed: {frame_count}")
        print(f" Total Time Elapsed:     {elapsed:.2f}s ({frame_count/max(0.1, elapsed):.1f} FPS)")
        print(f"==================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SAFECAM Roboflow Cloud API Video Test Script")
    parser.add_argument("video", nargs="?", default="1.mp4", help="Path to video file (default: 1.mp4)")
    parser.add_argument("--save", action="store_true", help="Save output annotated MP4 video")
    parser.add_argument("--no-display", action="store_true", help="Run in headless mode without opening GUI window")

    args = parser.parse_args()
    run_video_test(args.video, save_output=args.save, display=not args.no_display)
