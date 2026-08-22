#!/usr/bin/env python3
"""
SAFECAM AI - Unified AI Pipeline Test Client (test_py.py)
Evaluates the complete SAFECAM AI pipeline:
- YOLO11 Person Detection & Tracking
- MediaPipe Pose Joint & Limb Skeleton Overlay
- RWF-2000 3D CNN Temporal Violence / Fight Classification
Supports single video files or folder batch evaluation with optional video output saving.
"""

import sys
import os
import time
import argparse
import cv2

# Ensure python_backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from python_backend.ai_engine import AIEngine
except ImportError as err:
    print("\n[ERROR] Could not load existing AI backend.")
    print("[ERROR] Check the module/path instead of creating a duplicate AI implementation.")
    print(f"[ERROR] Import Error details: {err}\n")
    sys.exit(1)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="SAFECAM AI - Unified AI Pipeline Video & RWF-2000 Tester"
    )
    parser.add_argument(
        "positional_video",
        type=str,
        nargs="?",
        default=None,
        help="Path to single test video file (.mp4, .avi, .mov, .mkv)"
    )
    parser.add_argument(
        "--video", "-v",
        type=str,
        default=None,
        help="Path to input test video file (.mp4, .avi, .mov, .mkv)"
    )
    parser.add_argument(
        "--folder", "-f",
        type=str,
        default=None,
        help="Path to folder containing test videos for batch evaluation"
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="Save processed video with AI overlays to test_results/ directory"
    )
    parser.add_argument(
        "--camera_id", "-c",
        type=str,
        default="CAM-001",
        help="Camera ID to target for live dashboard alarm syncing (default: CAM-001)"
    )
    return parser.parse_args()


def process_video_stream(video_path, ai_engine, save_output=False, display_window=True, target_camera_id="CAM-001"):
    """
    Processes a single video through the complete SAFECAM AI Pipeline (YOLO11 + MediaPipe + RWF-2000).
    """
    if not os.path.exists(video_path):
        print(f"\n[ERROR] Could not open video: File '{video_path}' does not exist.")
        return None

    valid_extensions = (".mp4", ".avi", ".mov", ".mkv")
    if not video_path.lower().endswith(valid_extensions):
        print(f"\n[ERROR] Unsupported video format: {video_path}")
        return None

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"\n[ERROR] OpenCV failed to open '{video_path}'.")
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or fps > 120:
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    base_filename = os.path.basename(video_path)
    print("\n--------------------------------------------------")
    print(f"[TEST] Loading video: {base_filename}")
    print(f"[TEST] Video resolution: {width}x{height}")
    print(f"[TEST] Video FPS: {fps:.1f}")
    print(f"[TEST] Total frames: {total_frames}")

    # Video Writer Setup if --save enabled
    video_writer = None
    output_save_path = None
    if save_output:
        output_dir = os.path.abspath("test_results")
        os.makedirs(output_dir, exist_ok=True)
        raw_name = os.path.splitext(base_filename)[0]
        output_save_path = os.path.join(output_dir, f"result_{raw_name}.mp4")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(output_save_path, fourcc, fps, (width, height))
        if not video_writer.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            output_save_path = os.path.join(output_dir, f"result_{raw_name}.avi")
            video_writer = cv2.VideoWriter(output_save_path, fourcc, fps, (width, height))

        print(f"[TEST] Video saving enabled -> Output: {output_save_path}")

    print("--------------------------------------------------\n")

    frame_idx = 0
    fight_frames_count = 0
    first_detection_frame = None
    max_people_detected = 0
    max_fight_prob = 0.0
    last_reported_status = None
    last_telemetry = {}

    start_time = time.time()
    processed_fps = 0.0
    camera_id = target_camera_id or "CAM-001"
    window_name = f"SAFECAM AI Unified Test - {base_filename}"

    if display_window:
        print("[TEST] Starting AI Inference playback. Press 'Q' or 'ESC' to exit...\n")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            loop_start = time.time()

            # Process frame through full AIEngine pipeline
            annotated_frame, telemetry = ai_engine.process_frame(frame, camera_id=camera_id)
            if annotated_frame is None:
                annotated_frame = frame

            last_telemetry = telemetry

            overall_status = telemetry.get("status", "NORMAL")
            threat_level = telemetry.get("threat_level", "normal")
            people_count = telemetry.get("people_count", 0)
            tracked_persons = telemetry.get("tracked_persons", [])
            fight_prob = telemetry.get("fight_probability", 0.0)
            nonfight_prob = telemetry.get("nonfight_probability", 1.0)
            violence_detected = telemetry.get("violence_detected", False)

            if fight_prob > max_fight_prob:
                max_fight_prob = fight_prob

            if people_count > max_people_detected:
                max_people_detected = people_count

            is_threat = (
                violence_detected
                or "BULLYING" in overall_status.upper()
                or "AGGRESSIVE" in overall_status.upper()
                or threat_level in ["aggressive", "bullying"]
            )

            if is_threat:
                fight_frames_count += 1
                if first_detection_frame is None:
                    first_detection_frame = frame_idx

            # Calculate live FPS
            loop_dt = time.time() - loop_start
            if loop_dt > 0:
                processed_fps = 0.9 * processed_fps + 0.1 * (1.0 / loop_dt) if processed_fps > 0 else (1.0 / loop_dt)

            # Draw top telemetry overlay on display window
            info_text = f"FRAME: {frame_idx}/{total_frames} | FPS: {processed_fps:.1f} | PEOPLE: {people_count} | FIGHT: {int(fight_prob*100)}%"
            cv2.putText(annotated_frame, info_text, (max(20, width - 620), 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 212, 255), 2)

            # Save frame to output video if --save enabled
            if video_writer is not None:
                if (annotated_frame.shape[1], annotated_frame.shape[0]) != (width, height):
                    save_frame = cv2.resize(annotated_frame, (width, height))
                else:
                    save_frame = annotated_frame
                video_writer.write(save_frame)

            # Display Window
            if display_window:
                cv2.imshow(window_name, annotated_frame)

            # Print Terminal Output when status changes or on periodic interval
            should_print = (
                frame_idx == 1
                or is_threat
                or overall_status != last_reported_status
                or (frame_idx % 30 == 0)
            )

            if should_print:
                print(f"[TEST] Frame {frame_idx}/{total_frames}")
                print(f"[AI] People detected: {people_count}")

                for person in tracked_persons:
                    tid = person.get("track_id", "N/A")
                    conf = person.get("conf", 0.0)
                    role = person.get("role", "normal")
                    action = person.get("action")
                    box_color = person.get("box_color", "GREEN")
                    bbox = [round(b, 1) for b in person.get("bbox_640", [])]
                    
                    if role == "attacker":
                        role_str = f"{box_color} → {action}"
                    elif role == "victim":
                        role_str = f"{box_color} → VICTIM"
                    else:
                        role_str = f"{box_color} → NORMAL"

                    print(f"Person ID {tid} → {role_str} (conf={conf:.2f}, bbox_640={bbox})")

                print(f"[AI] RWF-2000 Fight Prob: {fight_prob * 100:.1f}% | Non-Fight: {nonfight_prob * 100:.1f}%")
                print(f"[AI] Violence/Threat detected: {'TRUE (' + overall_status + ')' if is_threat else 'FALSE'}")
                print(f"[AI] Threat level: {threat_level}")
                print("-" * 50)
                last_reported_status = overall_status

            if display_window:
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == ord("Q") or key == 27:
                    print("\n[TEST] User requested exit ('Q' key pressed). Stopping test...")
                    break

    except KeyboardInterrupt:
        print("\n[TEST] Interrupted by user. Cleaning up...")
    finally:
        cap.release()
        if video_writer is not None:
            video_writer.release()
        if display_window:
            cv2.destroyAllWindows()

    total_time = time.time() - start_time
    avg_fps = (frame_idx / total_time) if total_time > 0 else 0.0

    summary_result = {
        "video": base_filename,
        "total_frames": total_frames,
        "processed_frames": frame_idx,
        "avg_fps": round(avg_fps, 1),
        "max_people": max_people_detected,
        "fight_detected": "YES" if fight_frames_count > 0 else "NO",
        "fight_frames": fight_frames_count,
        "first_detection_frame": first_detection_frame if first_detection_frame else "N/A",
        "peak_fight_prob": round(max_fight_prob * 100, 1),
        "output_save_path": output_save_path
    }

    # Print Summary Report
    print("\n==================================================")
    print("UNIFIED AI & RWF-2000 TEST SUMMARY")
    print("==================================================")
    print(f"Video: {base_filename}")
    print(f"Frames processed: {frame_idx} / {total_frames}")
    print(f"Average FPS: {avg_fps:.1f}")
    print(f"Max people detected: {max_people_detected}")
    print(f"Violence/Fight detected: {summary_result['fight_detected']}")
    print(f"Peak Fight Probability: {summary_result['peak_fight_prob']}%")
    print(f"Fight/Violence frames: {fight_frames_count}")
    print(f"First detection frame: {summary_result['first_detection_frame']}")
    if output_save_path:
        print(f"Processed video saved: {output_save_path}")
    print("==================================================\n")

    return summary_result


def main():
    args = parse_arguments()

    # Determine input video or folder path
    video_target = args.video or args.positional_video

    if not video_target and not args.folder:
        print("\n==================================================")
        print("SAFECAM AI - UNIFIED PIPELINE TEST CLIENT")
        print("==================================================")
        print("Usage:")
        print("  python test_py.py <path_to_video.mp4> [--save]")
        print("  python test_py.py --video <path_to_video.mp4> [--save]")
        print("  python test_py.py --folder <path_to_video_dir> [--save]\n")
        print("Examples:")
        print("  python test_py.py test_video.mp4")
        print("  python test_py.py --video videos/fight_test.mp4 --save")
        print("  python test_py.py --folder ./test_videos --save")
        print("==================================================\n")
        sys.exit(0)

    print("\n[TEST] Initializing SAFECAM AI Engine (YOLO11 + MediaPipe + RWF-2000)...")
    try:
        ai_engine = AIEngine(model_path="yolo11n.pt")
    except Exception as e:
        print(f"[ERROR] Failed to initialize AIEngine: {e}")
        sys.exit(1)

    print("[TEST] AI Engine initialized successfully!")

    # Mode 1: Single Video File
    if video_target and not args.folder:
        process_video_stream(video_target, ai_engine, save_output=args.save, display_window=True, target_camera_id=args.camera_id)
        sys.exit(0)

    # Mode 2: Folder Batch Evaluation
    if args.folder:
        folder_path = args.folder
        if not os.path.exists(folder_path):
            print(f"\n[ERROR] Folder does not exist: {folder_path}")
            sys.exit(1)

        valid_exts = (".mp4", ".avi", ".mov", ".mkv")
        video_files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(valid_exts)
        ]

        if not video_files:
            print(f"\n[ERROR] No video files found in folder: {folder_path}")
            sys.exit(1)

        print(f"\n==================================================")
        print(f"BATCH EVALUATION: {len(video_files)} Videos in '{folder_path}'")
        print(f"==================================================")

        batch_results = []
        for v in video_files:
            res = process_video_stream(v, ai_engine, save_output=args.save, display_window=True)
            if res:
                batch_results.append(res)

        print("\n==================================================")
        print("BATCH EVALUATION SUMMARY REPORT")
        print("==================================================")
        for r in batch_results:
            print(f" - {r['video']}: Violence Detected = {r['fight_detected']} (Peak Fight: {r['peak_fight_prob']}%, Max People: {r['max_people']})")
        print("==================================================\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
