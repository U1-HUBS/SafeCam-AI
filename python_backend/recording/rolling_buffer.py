"""
SAFECAM — Rolling Pre-Event Frame Buffer
=========================================
Maintains a JPEG-compressed ring buffer of recent camera frames so that
when a bullying event is confirmed, the 5 seconds BEFORE the event can be
prepended to the incident clip.

MEMORY DESIGN:
    1080p raw frame  ≈ 1920×1080×3 = ~6.2 MB per frame
    5s × 30 FPS      = 150 frames × 6.2 MB = ~930 MB  ← unacceptable on laptop

    With JPEG compression (quality=50):
    1080p JPEG       ≈ 50–150 KB per frame
    150 frames       ≈ 7–22 MB total ← acceptable

    Frames are decoded back to numpy arrays only when the clip is being saved,
    not while buffering.

THREAD SAFETY:
    push() is called from the capture thread.
    get_pre_event_frames() is called from the alarm/clip-save thread.
    A threading.Lock protects the ring buffer deque.
"""

import cv2
import time
import threading
import numpy as np
from collections import deque
from typing import List


class RollingBuffer:
    """
    JPEG-compressed ring buffer of recent camera frames.

    Parameters
    ----------
    pre_event_seconds : float  — How many seconds of pre-event footage to keep.
    camera_fps        : float  — Camera frame rate (used to size the ring buffer).
    jpeg_quality      : int    — JPEG compression quality 1–95. Lower = smaller RAM.
    """

    def __init__(
        self,
        pre_event_seconds: float = 5.0,
        camera_fps:        float = 30.0,
        jpeg_quality:      int   = 50,
    ):
        self.pre_event_seconds = pre_event_seconds
        self.camera_fps        = camera_fps
        self.jpeg_quality      = jpeg_quality

        # Ring buffer capacity in frames
        capacity = max(1, int(pre_event_seconds * camera_fps))

        self._buf:  deque  = deque(maxlen=capacity)   # deque of (timestamp, jpeg_bytes)
        self._lock: threading.Lock = threading.Lock()

        self._encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]

        print(
            f"[ROLLING BUFFER] Initialized: {pre_event_seconds}s × {camera_fps:.0f}FPS "
            f"= {capacity} frame capacity | JPEG quality={jpeg_quality}"
        )

    def push(self, frame: np.ndarray):
        """
        Add a new frame to the ring buffer.
        Called from the capture worker thread on every raw camera frame.
        Old frames are automatically evicted when capacity is reached.
        """
        if frame is None:
            return
        try:
            ok, buf = cv2.imencode(".jpg", frame, self._encode_params)
            if ok:
                with self._lock:
                    self._buf.append((time.time(), buf.tobytes()))
        except Exception:
            pass   # Never crash the capture thread

    def get_pre_event_frames(self) -> List[np.ndarray]:
        """
        Decode and return all buffered frames as numpy arrays in chronological order.
        Call this when bullying is confirmed to get the pre-event footage.
        Returns an empty list if the buffer is empty.
        """
        with self._lock:
            buffered = list(self._buf)   # snapshot

        frames = []
        for _ts, jpeg_bytes in buffered:
            try:
                arr   = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    frames.append(frame)
            except Exception:
                continue

        return frames

    def clear(self):
        """Clear all buffered frames."""
        with self._lock:
            self._buf.clear()

    @property
    def frame_count(self) -> int:
        with self._lock:
            return len(self._buf)

    @property
    def capacity(self) -> int:
        return self._buf.maxlen
