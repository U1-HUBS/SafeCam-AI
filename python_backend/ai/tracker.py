"""
SAFECAM — Person Tracker Wrapper Component
==========================================
Wraps ByteTrack / LightweightTracker to assign persistent, stable track IDs (ID 1, ID 2...)
to person bounding boxes across consecutive camera frames.
"""

from typing import List, Dict
try:
    from tracking.tracker import LightweightTracker, TrackedPerson, Detection
except ImportError:
    from python_backend.tracking.tracker import LightweightTracker, TrackedPerson, Detection

from .person_detector import PersonDetection


class PersonTrackerWrapper:
    """
    Manages per-camera person trackers for stable ID assignment.
    """

    def __init__(self, iou_thresh: float = 0.30, max_missing: int = 5):
        self.iou_thresh = iou_thresh
        self.max_missing = max_missing
        self._trackers: Dict[str, LightweightTracker] = {}

    def get_tracker(self, camera_id: str) -> LightweightTracker:
        if camera_id not in self._trackers:
            self._trackers[camera_id] = LightweightTracker(
                iou_threshold=self.iou_thresh,
                max_missing_frames=self.max_missing,
                frame_width=1920,
                frame_height=1080
            )
        return self._trackers[camera_id]

    def update(self, camera_id: str, person_detections: List[PersonDetection]) -> List[TrackedPerson]:
        tracker = self.get_tracker(camera_id)

        # Convert PersonDetection to tracker Detection objects
        det_objects = [
            Detection(
                class_id=p.class_id,
                class_name="person",
                confidence=p.confidence,
                x1=p.x1, y1=p.y1, x2=p.x2, y2=p.y2
            )
            for p in person_detections
        ]

        return tracker.update(det_objects)

    def reset_camera(self, camera_id: str):
        if camera_id in self._trackers:
            self._trackers[camera_id].reset()
