import os
import sys
import time
import cv2
import torch

# Add python_backend to search path
sys.path.append(os.path.join(os.path.dirname(__file__), "python_backend"))

from python_backend.ai_engine import AIEngine  # pyrefly: ignore [missing-import] # type: ignore
from python_backend.alarm_config import alarm_config  # pyrefly: ignore [missing-import] # type: ignore
from python_backend.alarm_manager import alarm_manager  # pyrefly: ignore [missing-import] # type: ignore

def run_benchmark_pass(video_path, imgsz):
    os.environ["YOLO_IMGSZ"] = str(imgsz)
    alarm_config.YOLO_IMGSZ = imgsz

    engine = AIEngine()
    cam_id = f"BENCH-{imgsz}-{os.path.basename(video_path)}"
    alarm_manager.camera_states[cam_id] = alarm_manager.get_default_state(cam_id)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {video_path}")
        return None

    frame_count = 0
    total_detections = 0
    punch_count = 0
    kick_count = 0
    people_count_sum = 0
    peak_yolo_conf = 0.0
    peak_fight_prob = 0.0
    confirming_hits = 0
    confirmed_attacks = 0
    false_alarms = 0
    yolo_ms_list = []
    total_ai_ms_list = []

    start_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        frame_count += 1
        t_f0 = time.time()
        annotated_frame, telemetry = engine.process_frame(frame, camera_id=cam_id)
        t_f1 = time.time()

        total_ai_ms = (t_f1 - t_f0) * 1000.0
        total_ai_ms_list.append(total_ai_ms)

        yolo_ms = telemetry.get("yolo_inference_ms", 0.0)
        yolo_ms_list.append(yolo_ms)

        det_conf = telemetry.get("detection_confidence", 0.0)
        if det_conf > peak_yolo_conf:
            peak_yolo_conf = det_conf

        fight_prob = telemetry.get("fight_probability", 0.0)
        if fight_prob > peak_fight_prob:
            peak_fight_prob = fight_prob

        punch_c = telemetry.get("punch_count", 0)
        kick_c = telemetry.get("kick_count", 0)
        people_c = telemetry.get("people_count", 0)

        punch_count += punch_c
        kick_count += kick_c
        people_count_sum += people_c
        total_detections += (punch_c + kick_c)

        st = telemetry.get("alarm_state", {})
        if st.get("state") == "CONFIRMING":
            confirming_hits += 1
        elif st.get("state") == "ALARM_ACTIVE":
            confirmed_attacks += 1

    cap.release()
    elapsed = time.time() - start_time
    fps = frame_count / max(0.1, elapsed)

    avg_yolo_ms = sum(yolo_ms_list) / max(1, len(yolo_ms_list))
    avg_total_ai_ms = sum(total_ai_ms_list) / max(1, len(total_ai_ms_list))

    return {
        "video": os.path.basename(video_path),
        "imgsz": imgsz,
        "frames": frame_count,
        "elapsed_sec": round(elapsed, 2),
        "fps": round(fps, 1),
        "avg_yolo_ms": round(avg_yolo_ms, 1),
        "avg_total_ai_ms": round(avg_total_ai_ms, 1),
        "total_detections": total_detections,
        "punch_count": punch_count,
        "kick_count": kick_count,
        "avg_people_detected": round(people_count_sum / max(1, frame_count), 1),
        "peak_yolo_conf": round(peak_yolo_conf * 100, 1),
        "peak_fight_prob": round(peak_fight_prob * 100, 1),
        "confirming_hits": confirming_hits,
        "confirmed_attacks": confirmed_attacks,
        "false_alarms": false_alarms
    }

def main():
    print("==================================================")
    print(" SAFECAM AI Intel Core i5-1235U Benchmark Suite")
    print(f" CUDA Available: {torch.cuda.is_available()}")
    print(f" Device Selected: {'0 (CUDA)' if torch.cuda.is_available() else 'cpu'}")
    print("==================================================\n")

    videos = ["fi034.mp4", "fi035.mp4"]
    resolutions = [640, 800, 1024]

    results = []

    for vid in videos:
        if not os.path.exists(vid):
            print(f"[WARN] Video {vid} not found, skipping...")
            continue
        for r in resolutions:
            print(f"[BENCHMARKING] Video: {vid} | imgsz: {r} ...")
            res = run_benchmark_pass(vid, r)
            if res:
                results.append(res)
                print(f"  -> {vid} @ {r}x{r}: FPS={res['fps']}, AvgYOLO={res['avg_yolo_ms']}ms, Detections={res['total_detections']} (PUNCH:{res['punch_count']}, KICK:{res['kick_count']}), PeakConf={res['peak_yolo_conf']}%, Hits={res['confirming_hits']}")

    print("\n\n==================================================")
    print(" SUMMARY BENCHMARK RESULTS")
    print("==================================================")
    for r in results:
        print(r)

if __name__ == "__main__":
    main()
