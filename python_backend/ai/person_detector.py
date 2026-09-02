"""
SAFECAM — Person Detector Component
====================================
Detects ALL visible persons in frame independently of action predictions.
Uses COCO Person Class [0] from a lightweight YOLO model (yolo11n.pt or best_v1.pt fallback).
"""

import os
import numpy as np
from typing import List, NamedTuple

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


class PersonDetection(NamedTuple):
    class_id:   int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def cx(self) -> int:
        return (self.x1 + self.x2) // 2

    @property
    def cy(self) -> int:
        return (self.y1 + self.y2) // 2

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height


class PersonDetector:
    """
    Independent Person Detector.
    Ensures every visible person receives a bounding box regardless of action or posture.
    """

    def __init__(self, model_path: str = None, imgsz: int = 640, device: str = "cpu", conf_thresh: float = 0.30):
        self.imgsz = imgsz
        self.device = device
        self.conf_thresh = conf_thresh
        self.model = None
        self.api_available = False

        if ULTRALYTICS_AVAILABLE:
            try:
                # Primary lightweight person model: yolo11n.pt (COCO)
                root_coco = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "yolo11n.pt"))
                target_path = root_coco if os.path.exists(root_coco) else (model_path or "yolo11n.pt")
                if not os.path.exists(target_path) and model_path and os.path.exists(model_path):
                    target_path = model_path
                
                self.model = YOLO(target_path)
                self.api_available = True
                print(f"[PERSON DETECTOR] Loaded model: {target_path} | conf_thresh={self.conf_thresh}")
            except Exception as e:
                print(f"[PERSON DETECTOR WARNING] Could not load primary person model: {e}")
                if model_path and os.path.exists(model_path):
                    try:
                        self.model = YOLO(model_path)
                        self.api_available = True
                        print(f"[PERSON DETECTOR] Fallback loaded: {model_path}")
                    except Exception as e2:
                        print(f"[PERSON DETECTOR ERROR] Fallback failed: {e2}")

    def detect(self, frame_1080p: np.ndarray) -> List[PersonDetection]:
        """
        Runs person detection on frame and returns list of PersonDetection objects.
        """
        if frame_1080p is None or not self.api_available or self.model is None:
            return []

        detections: List[PersonDetection] = []
        try:
            # Check if model has COCO person class [0] or is a custom action model
            is_coco_person = False
            if hasattr(self.model, "names") and isinstance(self.model.names, dict):
                cls0_name = str(self.model.names.get(0, "")).lower()
                if "person" in cls0_name:
                    is_coco_person = True

            kwargs = {
                "imgsz": self.imgsz,
                "device": self.device,
                "conf": self.conf_thresh,
                "verbose": False
            }
            if is_coco_person:
                kwargs["classes"] = [0]

            results = self.model(frame_1080p, **kwargs)

            if results and len(results) > 0:
                r = results[0]
                boxes = r.boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        detections.append(PersonDetection(
                            class_id=cls_id,
                            class_name="person",
                            confidence=conf,
                            x1=x1, y1=y1,
                            x2=x2, y2=y2
                        ))

        except Exception as e:
            # If classes=[0] is not supported (custom model without class 0 as person), run standard inference
            try:
                results = self.model(
                    frame_1080p,
                    imgsz=self.imgsz,
                    device=self.device,
                    conf=self.conf_thresh,
                    verbose=False
                )
                if results and len(results) > 0:
                    r = results[0]
                    boxes = r.boxes
                    if boxes is not None and len(boxes) > 0:
                        for box in boxes:
                            cls_id = int(box.cls[0].item())
                            conf = float(box.conf[0].item())
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            cls_name = self.model.names.get(cls_id, "person")
                            detections.append(PersonDetection(
                                class_id=cls_id,
                                class_name=cls_name,
                                confidence=conf,
                                x1=x1, y1=y1,
                                x2=x2, y2=y2
                            ))
            except Exception as e2:
                print(f"[PERSON DETECTOR ERROR] Detection failed: {e2}")

        return detections
