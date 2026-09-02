"""
Comprehensive Action Detector Diagnostic Script for BOTH PUNCH and KICK
"""

import cv2
import numpy as np
from ultralytics import YOLO

action_model = YOLO("python_backend/Model/best_v1.pt")
person_model = YOLO("yolo11n.pt")

print(f"ACTION MODEL PATH: python_backend/Model/best_v1.pt")
print(f"MODEL TASK: {action_model.task}")
print(f"MODEL NAMES: {action_model.names}")

for video_name in ["kicktest.mp4", "punchtest.mp4"]:
    print(f"\n==================================================")
    print(f" TEST VIDEO: {video_name}")
    print(f"==================================================")
    cap = cv2.VideoCapture(video_name)
    if not cap.isOpened():
        print(f"[ERROR] Could not open {video_name}")
        continue

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Sample key action frames
    sample_frames = list(range(10, min(35, total_frames), 5))

    for f_idx in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if not ret:
            continue

        print(f"\n--- Frame {f_idx:03d} ({video_name}) ---")

        # Full frame test across 640, 768, 1024
        for sz in [640, 768, 1024]:
            res = action_model(frame, imgsz=sz, conf=0.01, verbose=False)
            boxes = res[0].boxes
            b_cnt = len(boxes) if boxes is not None else 0
            raw_summary = []
            if boxes is not None and len(boxes) > 0:
                for b in boxes:
                    cid = int(b.cls[0].item())
                    cname = action_model.names.get(cid, str(cid))
                    cnf = float(b.conf[0].item())
                    raw_summary.append(f"{cname}:{cnf:.2f}")
            print(f"  FULL FRAME (imgsz={sz}): {b_cnt} boxes -> {', '.join(raw_summary) if raw_summary else 'NONE'}")

        # Person crop test
        p_res = person_model(frame, imgsz=640, conf=0.30, classes=[0], verbose=False)
        p_boxes = p_res[0].boxes
        if p_boxes is not None and len(p_boxes) > 0:
            for idx, pb in enumerate(p_boxes):
                px1, py1, px2, py2 = map(int, pb.xyxy[0].tolist())
                pw, ph = px2 - px1, py2 - py1
                pad_x, pad_y = int(pw * 0.25), int(ph * 0.15)
                cx1, cy1 = max(0, px1 - pad_x), max(0, py1 - pad_y)
                cx2, cy2 = min(w, px2 + pad_x), min(h, py2 + pad_y)
                crop = frame[cy1:cy2, cx1:cx2]

                for sz in [640, 768]:
                    c_res = action_model(crop, imgsz=sz, conf=0.01, verbose=False)
                    c_b = c_res[0].boxes
                    c_summary = []
                    if c_b is not None and len(c_b) > 0:
                        for cb in c_b:
                            ccid = int(cb.cls[0].item())
                            ccname = action_model.names.get(ccid, str(ccid))
                            ccnf = float(cb.conf[0].item())
                            c_summary.append(f"{ccname}:{ccnf:.2f}")
                    print(f"  CROP Person #{idx+1} ({cx2-cx1}x{cy2-cy1}, imgsz={sz}): {', '.join(c_summary) if c_summary else 'NONE'}")

    cap.release()
