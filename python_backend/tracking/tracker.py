"""
SAFECAM — Lightweight Bounding-Box Temporal Tracker
====================================================
Architecture Design:
    BaseTracker (abstract interface)
        └── LightweightTracker  ← used now (no external dependencies)
        └── ByteTrackTracker    ← future drop-in replacement

The LightweightTracker assigns stable track_ids to persons across consecutive
AI frames using IoU + centroid distance matching, with no external libraries.

This module is intentionally free of ByteTrack, MediaPipe, and CUDA dependencies.

HOW TO ADD BYTETRACK LATER:
    1. Install bytetracker: pip install bytetracker
    2. Implement ByteTrackTracker(BaseTracker) in this file
    3. Set BYTETRACK_ENABLED=True in alarm_config.py
    4. BullyingStateMachine and AIEngine will auto-use it via get_tracker()
    No other files need changing.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    """
    Raw detection from YOLO for a single bounding box in one frame.

    Fields
    ------
    class_id    : int   — YOLO class index (e.g. 0=Punch, 1=Kick, 2=Normal)
    class_name  : str   — Human-readable class name from model.names
    confidence  : float — Detection confidence 0.0–1.0
    x1,y1,x2,y2: int   — Absolute pixel coordinates in the original frame
    """
    class_id:   int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2.0

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    def iou(self, other: "Detection") -> float:
        """Intersection over Union with another detection."""
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0


@dataclass
class TrackedPerson:
    """
    A person tracked across multiple AI frames with a stable track_id.

    Fields
    ------
    track_id         : int   — Stable cross-frame identity
    detection        : Detection — Latest detection for this person
    centroid_history : list  — Last N (cx, cy) centroids for movement analysis
    bbox_history     : list  — Last N [x1,y1,x2,y2] bboxes
    missing_frames   : int   — Consecutive frames this track had no matching detection
    last_seen        : float — time.time() of last match
    role             : str   — "attacker", "victim", or "normal" (set by bullying logic)
    """
    track_id:         int
    detection:        Detection
    centroid_history: List[tuple] = field(default_factory=list)
    bbox_history:     List[list]  = field(default_factory=list)
    missing_frames:   int         = 0
    last_seen:        float       = field(default_factory=time.time)
    role:             str         = "normal"

    # Maximum history entries kept per track
    MAX_HISTORY: int = field(default=15, init=False, repr=False)

    def update(self, det: Detection):
        """Apply a new matched detection to this track."""
        self.detection      = det
        self.missing_frames = 0
        self.last_seen      = time.time()

        self.centroid_history.append((det.cx, det.cy))
        self.bbox_history.append([det.x1, det.y1, det.x2, det.y2])

        if len(self.centroid_history) > self.MAX_HISTORY:
            self.centroid_history.pop(0)
        if len(self.bbox_history) > self.MAX_HISTORY:
            self.bbox_history.pop(0)

    def velocity(self) -> Optional[tuple]:
        """
        Returns (dx, dy) average velocity in pixels/frame over last N centroids.
        Returns None if fewer than 2 history entries exist.
        """
        h = self.centroid_history
        if len(h) < 2:
            return None
        dx = h[-1][0] - h[0][0]
        dy = h[-1][1] - h[0][1]
        n  = len(h) - 1
        return (dx / n, dy / n)


# ---------------------------------------------------------------------------
# Abstract Base Tracker (ByteTrack-compatible interface)
# ---------------------------------------------------------------------------

class BaseTracker(ABC):
    """
    Abstract interface for all SafeCam trackers.
    Concrete implementations:
        LightweightTracker — bounding-box IoU/centroid matching (no deps)
        ByteTrackTracker   — future drop-in when ByteTrack is enabled
    """

    @abstractmethod
    def update(self, detections: List[Detection]) -> List[TrackedPerson]:
        """
        Accept a list of raw YOLO detections for the current frame.
        Returns a list of TrackedPerson objects with stable track_ids.
        """
        ...

    @abstractmethod
    def reset(self):
        """Clear all active tracks (e.g., when camera disconnects)."""
        ...


# ---------------------------------------------------------------------------
# Lightweight Tracker Implementation
# ---------------------------------------------------------------------------

class LightweightTracker(BaseTracker):
    """
    Pure-Python, zero-dependency bounding-box temporal association tracker.

    Matching strategy (in priority order):
    1. IoU overlap ≥ iou_threshold  → strong spatial match
    2. Centroid distance < max_centroid_dist_px → positional proximity match

    Unmatched existing tracks increment their missing_frames counter.
    Tracks missing for > max_missing_frames are removed.
    Unmatched new detections spawn new TrackedPerson entries.

    Thread safety: NOT thread-safe by itself. The caller (AIEngine) must
    ensure update() is called from a single thread.
    """

    def __init__(
        self,
        iou_threshold:          float = 0.30,
        max_centroid_dist_norm: float = 0.25,   # normalised to frame width
        max_missing_frames:     int   = 5,
        max_history:            int   = 15,
        frame_width:            int   = 1920,
        frame_height:           int   = 1080,
    ):
        self.iou_threshold          = iou_threshold
        self.max_centroid_dist_norm = max_centroid_dist_norm
        self.max_missing_frames     = max_missing_frames
        self.max_history            = max_history
        self.frame_width            = frame_width
        self.frame_height           = frame_height

        self._tracks:   List[TrackedPerson] = []
        self._next_id:  int                 = 1

    # ------------------------------------------------------------------ public

    def update(self, detections: List[Detection]) -> List[TrackedPerson]:
        """
        Main update method called once per AI frame.
        Returns all currently active TrackedPerson objects.
        """
        # Compute max centroid distance in pixels from normalised threshold
        max_dist_px = self.max_centroid_dist_norm * self.frame_width

        matched_track_ids   = set()
        matched_det_indices = set()

        # ---- Phase 1: Match by IoU first (strongest signal) ----
        for track in self._tracks:
            if not detections:
                break
            best_iou   = self.iou_threshold
            best_idx   = -1
            track_det  = track.detection

            for i, det in enumerate(detections):
                if i in matched_det_indices:
                    continue
                iou = _det_iou(track_det, det)
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i

            if best_idx >= 0:
                track.update(detections[best_idx])
                track.MAX_HISTORY = self.max_history
                matched_track_ids.add(track.track_id)
                matched_det_indices.add(best_idx)

        # ---- Phase 2: Match remaining by centroid distance ----
        for track in self._tracks:
            if track.track_id in matched_track_ids:
                continue
            if not detections:
                break
            best_dist = max_dist_px
            best_idx  = -1

            for i, det in enumerate(detections):
                if i in matched_det_indices:
                    continue
                dist = _centroid_dist(track.detection, det)
                if dist < best_dist:
                    best_dist = dist
                    best_idx  = i

            if best_idx >= 0:
                track.update(detections[best_idx])
                track.MAX_HISTORY = self.max_history
                matched_track_ids.add(track.track_id)
                matched_det_indices.add(best_idx)

        # ---- Phase 3: Increment missing counter for unmatched tracks ----
        for track in self._tracks:
            if track.track_id not in matched_track_ids:
                track.missing_frames += 1

        # ---- Phase 4: Remove stale tracks ----
        self._tracks = [
            t for t in self._tracks
            if t.missing_frames <= self.max_missing_frames
        ]

        # ---- Phase 5: Create new tracks for unmatched detections ----
        # Suppress duplicate sub-body part detections (extended arm/hand/shadow) of the same human
        min_spatial_sep_px = 0.06 * self.frame_width
        for i, det in enumerate(detections):
            if i not in matched_det_indices:
                is_sub_body_dup = False
                for existing_track in self._tracks:
                    dist_px = _centroid_dist(existing_track.detection, det)
                    iou_val = _det_iou(existing_track.detection, det)
                    if dist_px <= min_spatial_sep_px or iou_val >= 0.20:
                        is_sub_body_dup = True
                        break

                if not is_sub_body_dup:
                    new_track = TrackedPerson(
                        track_id=self._next_id,
                        detection=det,
                    )
                    new_track.MAX_HISTORY = self.max_history
                    new_track.centroid_history.append((det.cx, det.cy))
                    new_track.bbox_history.append([det.x1, det.y1, det.x2, det.y2])
                    self._tracks.append(new_track)
                    self._next_id += 1

        return list(self._tracks)

    def reset(self):
        """Clear all tracks (call when stream restarts)."""
        self._tracks  = []
        self._next_id = 1

    @property
    def active_tracks(self) -> List[TrackedPerson]:
        return list(self._tracks)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _det_iou(a: Detection, b: Detection) -> float:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = max(0, a.x2 - a.x1) * max(0, a.y2 - a.y1)
    area_b = max(0, b.x2 - b.x1) * max(0, b.y2 - b.y1)
    union  = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _centroid_dist(a: Detection, b: Detection) -> float:
    dx = a.cx - b.cx
    dy = a.cy - b.cy
    return (dx * dx + dy * dy) ** 0.5


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_tracker(config) -> BaseTracker:
    """
    Returns the appropriate tracker based on alarm_config.
    When BYTETRACK_ENABLED is set True in config, swap to ByteTrackTracker here.
    All callers use this factory — zero code changes needed elsewhere.
    """
    if getattr(config, "BYTETRACK_ENABLED", False):
        # Future: return ByteTrackTracker(config)
        raise NotImplementedError(
            "ByteTrack is not yet enabled. Set BYTETRACK_ENABLED=False or "
            "implement ByteTrackTracker in tracking/tracker.py first."
        )
    return LightweightTracker(
        iou_threshold          = getattr(config, "TRACKER_IOU_THRESHOLD",      0.30),
        max_centroid_dist_norm = 0.25,
        max_missing_frames     = getattr(config, "TRACKER_MAX_MISSING_FRAMES",  5),
        max_history            = 15,
    )
