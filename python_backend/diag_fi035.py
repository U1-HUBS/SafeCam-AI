"""
Standalone Diagnostic Script for fi035.mp4 Action Model Analysis
"""

import cv2
import numpy as np
from ultralytics import YOLO

model_path = "python_backend/Model/best_v1.pt"
coco_person_path = "yolo11n.pt"

action_model = YOLO(model_path)
person_model = YOLO(coco_person_path)

print(f"ACTION MODEL TASK: {action_model.task}")
print(f"ACTION MODEL NAMES: {action_model.names}")

video_path = "fi035.mp4"
cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"VIDEO: {video_path} | frames={total_frames} | fps={fps} | resolution={w}x{h}\n")

frames_to_test = [20, 24, 26, 27, 30, 35, 40, 44, 45, 46]

for target_frame in frames_to_test:
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = cap.read()
    if not ret:
        continue

    print(f"==================================================")
    print(f"--- TESTING FRAME {target_frame:04d} ---")
    print(f"==================================================")

    # 1. Test Full Frame across imgsz=640, 768, 1024 at conf=0.01
    for sz in [640, 768, 1024]:
        res = action_model(frame, imgsz=sz, conf=0.01, verbose=False)
        boxes = res[0].boxes
        box_count = len(boxes) if boxes is not None else 0
        print(f"FULL FRAME (imgsz={sz}, conf=0.01): {box_count} raw boxes detected")
        if boxes is not None and len(boxes) > 0:
            for b in boxes:
                cid = int(b.cls[0].item())
                cname = action_model.names.get(cid, str(cid))
                cnf = float(b.conf[0].item())
                xyxy = map(int, b.xyxy[0].tolist())
                print(f"   -> class_id={cid} ({cname}) conf={cnf:.4f} bbox={list(xyxy)}")

    # 2. Extract Person Crops using person_model
    p_res = person_model(frame, imgsz=640, conf=0.30, classes=[0], verbose=False)
    p_boxes = p_res[0].boxes
    p_count = len(p_boxes) if p_boxes is not None else 0
    print(f"\nPERSON DETECTOR (imgsz=640, conf=0.30): {p_count} persons detected")

    if p_boxes is not None and len(p_boxes) > 0:
        for idx, pb in enumerate(p_boxes):
            px1, py1, px2, py2 = map(int, pb.xyxy[0].tolist())
            pw, ph = px2 - px1, py2 - py1
            # Add 25% padding
            pad_x, pad_y = int(pw * 0.25), int(ph * 0.15)
            cx1, cy1 = max(0, px1 - pad_x), max(0, py1 - pad_y)
            cx2, cy2 = min(w, px2 + pad_x), min(h, py2 + pad_y)

            crop = frame[cy1:cy2, cx1:cx2]
            cw, ch = cx2 - cx1, cy2 - cy1

            print(f"   [Person Track #{idx+1}] bbox=({px1},{py1},{px2},{py2}) crop_size=({cw}x{ch})")

            for sz in [640, 768]:
                c_res = action_model(crop, imgsz=sz, conf=0.01, verbose=False)
                c_b = c_res[0].boxes
                c_cnt = len(c_b) if c_b is not None else 0
                print(f"      Crop Action Inference (imgsz={sz}, conf=0.01): {c_cnt} raw boxes")
                if c_b is not None and len(c_b) > 0:
                    for cb in c_b:
                        ccid = int(cb.cls[0].item())
                        ccname = action_model.names.get(ccid, str(ccid))
                        ccnf = float(cb.conf[0].item())
                        cxyxy = map(int, cb.xyxy[0].tolist())
                        print(f"         -> class_id={ccid} ({ccname}) conf={ccnf:.4f} crop_bbox={list(cxyxy)}")

cap.release()
