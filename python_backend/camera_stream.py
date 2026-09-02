"""
SAFECAM — Camera Pipeline with Rolling Buffer & Time-Based AI Throttle
=======================================================================
Architecture (per camera):

    RTSP / Webcam / File (30 FPS)
          ↓
    Capture Worker Thread
     ├─ latest_raw_frame (buffer size = 1, newest wins, stale dropped)
     └─ RollingBuffer.push(frame) ← every raw frame for pre-event recording
          ↓
    AI Worker Thread (time-throttled to TARGET_AI_FPS ≈ 10 FPS)
     ├─ Grab newest raw frame (skip if stale since last AI grab)
     ├─ AIEngine.process_frame() → YOLO + Tracker + Bullying → annotated frame
     └─ Post-event frame collection after alarm ends
          ↓
    WebRTC Display Thread (30 FPS)
     └─ latest_annotated_frame → CameraTrack → React frontend

Key design rules enforced here:
  - Buffer size = 1: NEVER a growing queue
  - Time-based AI throttle: exactly 1 AI call per (1/TARGET_AI_FPS) seconds
  - Stale frame detection: if raw frame hasn't changed since last AI grab, skip
  - RollingBuffer receives EVERY raw frame (not every AI frame) for 5s pre-event
  - Post-event collection: after alarm stops, collect POST_EVENT_SECONDS more frames
"""

import cv2
import numpy as np
import time
import os
import math
import asyncio
import threading
from av import VideoFrame
from aiortc import VideoStreamTrack

try:
    from ai_engine   import AIEngine
    from alarm_config import alarm_config
    from recording.rolling_buffer import RollingBuffer
except ImportError:
    from python_backend.ai_engine          import AIEngine
    from python_backend.alarm_config       import alarm_config
    from python_backend.recording.rolling_buffer import RollingBuffer


# OpenCV low-delay RTSP options
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay"
    "|max_delay;0|analyzeduration;100000|probesize;100000"
)
cv2.setNumThreads(1)   # Prevent OpenCV internal thread explosion on laptop

# ============================================================================
# Global Shared AI Engine — loaded ONCE, shared across all cameras
# Loading best_v1.pt at module import time.
# ============================================================================
global_ai_engine = AIEngine(model_path=alarm_config.MODEL_PATH)


# ============================================================================
# Synthetic Camera Source (fallback when no physical camera available)
# ============================================================================

class SyntheticCameraSource:
    """
    1080p synthetic CCTV source for testing without physical hardware.
    Generates two animated persons walking across the frame.
    """
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width      = width
        self.height     = height
        self.start_time = time.time()

    def read(self):
        t     = time.time() - self.start_time
        frame = np.full((self.height, self.width, 3), (15, 23, 42), dtype=np.uint8)

        # Grid background
        for y in range(0, self.height, 100):
            cv2.line(frame, (0, y), (self.width, y), (30, 41, 59), 1)
        for x in range(0, self.width, 100):
            cv2.line(frame, (x, 0), (x, self.height), (30, 41, 59), 1)

        # Two animated persons
        p1_x = int(400  + math.sin(t * 1.2) * 350)
        p1_y = int(500  + math.cos(t * 0.8) * 50)
        p2_x = int(1400 - math.sin(t * 1.2) * 350)
        p2_y = int(520  + math.sin(t * 0.8) * 40)
        self._draw_person(frame, p1_x, p1_y, color=(200, 200, 200))
        self._draw_person(frame, p2_x, p2_y, color=(180, 180, 220))

        # Banner
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"SYNTHETIC CCTV | 1080P | {ts}",
                    (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 212, 255), 2)

        return True, frame

    def _draw_person(self, frame, x, y, color):
        cv2.circle(frame, (x, y - 120), 25, color, -1)
        cv2.rectangle(frame, (x - 30, y - 95), (x + 30, y + 20), color, -1)
        cv2.line(frame, (x - 30, y - 80), (x - 70, y - 20), color, 8)
        cv2.line(frame, (x + 30, y - 80), (x + 70, y - 20), color, 8)
        cv2.line(frame, (x - 15, y + 20), (x - 35, y + 110), color, 10)
        cv2.line(frame, (x + 15, y + 20), (x + 35, y + 110), color, 10)

    def release(self):
        pass

    def isOpened(self):
        return True


# ============================================================================
# Single Camera Pipeline
# ============================================================================

class SingleCameraPipeline:
    """
    Isolated pipeline for ONE camera stream.

    Threads:
      capture_thread  — reads frames from source at camera FPS
      ai_thread       — processes frames at TARGET_AI_FPS (time-throttled)
      watchdog_thread — detects RTSP freezes and reconnects
      logger_thread   — prints performance stats every 3 seconds

    Frame flow:
      [Capture] → latest_raw_frame (size-1 buffer)
                → rolling_buffer.push(frame)   ← for pre-event recording
      [AI]      → reads latest_raw_frame
                → AIEngine.process_frame()
                → latest_annotated_frame
      [WebRTC]  → reads latest_annotated_frame OR latest_raw_frame
    """

    def __init__(self, camera_id: str = "CAM-001", stream_url: str = ""):
        self.camera_id  = camera_id
        self.stream_url = stream_url.strip() if stream_url else ""
        self.ai_engine  = global_ai_engine

        # Frame buffers (capacity = 1)
        self.latest_raw_frame:        np.ndarray = None
        self.latest_raw_timestamp:    float      = 0.0
        self.latest_annotated_frame:  np.ndarray = None
        self.latest_annotated_timestamp: float   = 0.0

        # Performance counters
        self.capture_count:   int   = 0
        self.ai_count:        int   = 0
        self.webrtc_count:    int   = 0
        self.total_ai_ms:     float = 0.0
        self.detected_persons_count: int = 0

        self.last_ai_grab_timestamp:        float = 0.0
        self.last_successful_read_timestamp: float = time.time()
        self.last_webrtc_emit_timestamp:     float = 0.0

        # Viewer tracking & state management
        self.active_viewers: int = 0
        self.cap                = None
        self.is_synthetic       = False
        self.source_label       = "RTSP"
        self.running            = False

        self.lock = threading.Lock()

        # Rolling pre-event buffer (push every raw frame)
        self.rolling_buffer = RollingBuffer(
            pre_event_seconds = alarm_config.PRE_EVENT_SECONDS,
            camera_fps        = alarm_config.CAMERA_FPS,
            jpeg_quality      = 50,
        )

        # Post-event recording state
        self._post_event_active:       bool  = False
        self._post_event_frames_left:  int   = 0
        self._post_event_clip_id:      str   = None
        self._post_event_frame_buffer: list  = []
        self._post_event_pre_frames:   list  = []

        # Was alarm active in previous AI frame?
        self._prev_alarm_active: bool = False

        # Threads
        self.capture_thread  = None
        self.watchdog_thread = None
        self.ai_thread       = None
        self.logger_thread   = None

    def add_viewer(self):
        """Called when a WebRTC peer connects to watch this camera."""
        with self.lock:
            self.active_viewers += 1
            count = self.active_viewers
            print(f"\n[MONITOR] Viewer connected")
            print(f"[MONITOR] Camera: {self.camera_id}")
            print(f"[MONITOR] Active viewers: {count}")

        if not self.running:
            print(f"[PIPELINE] Starting camera pipeline for {self.camera_id}")
            self.start_pipeline()

    def remove_viewer(self):
        """Called when a WebRTC peer disconnects from this camera."""
        with self.lock:
            self.active_viewers = max(0, self.active_viewers - 1)
            count = self.active_viewers
            print(f"\n[MONITOR] Viewer disconnected")
            print(f"[MONITOR] Camera: {self.camera_id}")
            print(f"[MONITOR] Active viewers: {count}")

        if count == 0:
            print(f"[PIPELINE] No active viewers")
            print(f"[PIPELINE] Stopping {self.camera_id}")
            self.stop()

    def start_pipeline(self):
        with self.lock:
            if self.running:
                return
            self.running = True

        self._open_capture_source()

        # Start pipeline threads
        self.capture_thread  = threading.Thread(target=self._capture_worker,  daemon=True, name=f"cap-{self.camera_id}")
        self.watchdog_thread = threading.Thread(target=self._watchdog_worker, daemon=True, name=f"wdg-{self.camera_id}")
        self.ai_thread       = threading.Thread(target=self._ai_worker,       daemon=True, name=f"ai-{self.camera_id}")
        self.logger_thread   = threading.Thread(target=self._logger_worker,   daemon=True, name=f"log-{self.camera_id}")

        self.capture_thread.start()
        self.watchdog_thread.start()
        self.ai_thread.start()
        self.logger_thread.start()

    # ---------------------------------------------------------------- setup

    def _open_capture_source(self):
        """Open OpenCV VideoCapture or synthetic fallback."""
        if self.stream_url:
            if self.stream_url.isdigit():
                self.cap          = cv2.VideoCapture(int(self.stream_url))
                self.source_label = f"WEBCAM_{self.stream_url}"
            else:
                self.cap          = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
                self.source_label = "RTSP_STREAM"
        else:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.source_label = "WEBCAM_0"
            else:
                self._use_synthetic()
                return

        if not self.is_synthetic and self.cap is not None:
            if not self.cap.isOpened():
                print(f"[CAMERA PIPELINE] Source unreadable for {self.camera_id}. Using synthetic.")
                self._use_synthetic()
            else:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _use_synthetic(self):
        self.is_synthetic = True
        self.source_label = "SYNTHETIC"
        self.cap          = SyntheticCameraSource(1920, 1080)

    # ---------------------------------------------------------------- threads

    def _capture_worker(self):
        """
        Reads frames from camera at native FPS.
        Overwrites latest_raw_frame on every read (buffer size = 1).
        Also pushes every frame into the rolling pre-event buffer.
        """
        is_file = self.stream_url.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))

        while self.running:
            try:
                if self.cap is not None:
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        now = time.time()
                        with self.lock:
                            self.latest_raw_frame        = frame
                            self.latest_raw_timestamp    = now
                            self.capture_count          += 1
                            self.last_successful_read_timestamp = now

                        # Push to rolling buffer OUTSIDE the lock for performance
                        self.rolling_buffer.push(frame)

                        if is_file:
                            time.sleep(0.033)   # pace file playback at ~30 FPS
                    else:
                        if is_file:
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)   # loop
                        time.sleep(0.002)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"[CAPTURE WORKER ERROR] {self.camera_id}: {e}")
                time.sleep(0.05)

    def _watchdog_worker(self):
        """Detects RTSP stream freezes and reconnects safely."""
        reconnect_delay = 1.0
        while self.running:
            time.sleep(1.5)
            if self.is_synthetic:
                continue

            now = time.time()
            with self.lock:
                stalled = now - self.last_successful_read_timestamp

            if stalled > 3.0:
                print(f"[RTSP WATCHDOG] {self.camera_id} frozen ({stalled:.1f}s). Reconnecting…")
                try:
                    if self.cap is not None:
                        self.cap.release()
                except Exception:
                    pass
                time.sleep(reconnect_delay)
                with self.lock:
                    self._open_capture_source()
                    self.last_successful_read_timestamp = time.time()
                reconnect_delay = min(10.0, reconnect_delay * 1.5)
            else:
                reconnect_delay = 1.0

    def _ai_worker(self):
        """
        Time-throttled AI worker: runs YOLO at exactly TARGET_AI_FPS (≈10 FPS).
        Always processes the NEWEST available frame.
        Drops any frame that hasn't changed since last AI grab (stale-frame skip).

        Post-event recording:
        When the alarm transitions from active→inactive, this thread collects
        POST_EVENT_SECONDS × camera_FPS more raw frames, then triggers clip save.
        """
        target_interval = 1.0 / max(1.0, alarm_config.TARGET_AI_FPS)   # 0.1s for 10 FPS
        min_interval    = 1.0 / max(1.0, alarm_config.MAX_AI_FPS)       # 0.067s for 15 FPS

        post_event_frames_needed = int(alarm_config.POST_EVENT_SECONDS * alarm_config.CAMERA_FPS)

        while self.running:
            loop_start = time.time()

            # ---- Grab newest raw frame (stale check) ----
            raw_frame    = None
            capture_ts   = 0.0

            with self.lock:
                if (self.latest_raw_frame is not None and
                        self.latest_raw_timestamp > self.last_ai_grab_timestamp):
                    raw_frame                 = self.latest_raw_frame.copy()
                    capture_ts                = self.latest_raw_timestamp
                    self.last_ai_grab_timestamp = capture_ts

            if raw_frame is not None:
                try:
                    annotated, telemetry = self.ai_engine.process_frame(raw_frame, self.camera_id)

                    with self.lock:
                        self.latest_annotated_frame      = annotated
                        self.latest_annotated_timestamp  = capture_ts
                        self.ai_count                   += 1
                        self.total_ai_ms                 = telemetry.get("total_ai_ms", 0.0)
                        self.detected_persons_count      = telemetry.get("people_count", 0)

                    # ---- Post-event recording logic ----
                    alarm_state  = telemetry.get("alarm_state", {})
                    alarm_active = alarm_state.get("alarm_active", False)
                    incident_id  = alarm_state.get("incident_id")

                    # Detect transition: alarm just went active → capture pre-event frames
                    if alarm_active and not self._prev_alarm_active:
                        self._post_event_pre_frames = self.rolling_buffer.get_pre_event_frames()
                        self._post_event_frame_buffer = []
                        self._post_event_clip_id      = incident_id
                        self._post_event_active       = False  # will collect after alarm ends
                        print(f"[AI WORKER] {self.camera_id}: Alarm STARTED — captured "
                              f"{len(self._post_event_pre_frames)} pre-event frames")

                    # While alarm is active — keep appending live frames
                    if alarm_active:
                        if len(self._post_event_frame_buffer) < alarm_config.MAX_CLIP_FRAMES:
                            self._post_event_frame_buffer.append(annotated.copy() if annotated is not None else raw_frame.copy())

                    # Detect transition: alarm just stopped → start post-event collection
                    if not alarm_active and self._prev_alarm_active:
                        self._post_event_active       = True
                        self._post_event_frames_left  = post_event_frames_needed
                        print(f"[AI WORKER] {self.camera_id}: Alarm STOPPED — collecting "
                              f"{self._post_event_frames_left} post-event frames…")

                    # Post-event frame collection
                    if self._post_event_active and self._post_event_frames_left > 0:
                        self._post_event_frame_buffer.append(annotated.copy() if annotated is not None else raw_frame.copy())
                        self._post_event_frames_left -= 1

                        if self._post_event_frames_left <= 0:
                            self._post_event_active = False
                            # Trigger clip save with pre + live + post frames
                            all_frames = (
                                self._post_event_pre_frames
                                + self._post_event_frame_buffer
                            )
                            self._trigger_clip_save(all_frames, alarm_state)
                            self._post_event_pre_frames   = []
                            self._post_event_frame_buffer = []

                    self._prev_alarm_active = alarm_active

                except Exception as e:
                    print(f"[AI WORKER ERROR] {self.camera_id}: {e}")

            # ---- Time-based throttle ----
            elapsed      = time.time() - loop_start
            sleep_needed = max(min_interval, target_interval - elapsed)
            time.sleep(sleep_needed)

    def _trigger_clip_save(self, all_frames: list, alarm_state: dict):
        """
        Save incident clip in a background thread so AI worker is not blocked.
        """
        if not all_frames:
            return

        try:
            from alarm_manager import alarm_manager
        except ImportError:
            from python_backend.alarm_manager import alarm_manager

        inc_id     = alarm_state.get("incident_id", "INC-UNKNOWN")
        action     = alarm_state.get("action", "UNKNOWN")

        # Clip filename: bullying_2026-08-31_19-45-32_PUNCH.mp4
        from datetime import datetime
        ts_str    = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        action_clean = (action or "UNKNOWN").replace("BULLY — ", "").replace(" ", "_").upper()
        # Use only PUNCH or KICK in the filename
        if "PUNCH" in action_clean:
            action_clean = "PUNCH"
        elif "KICK" in action_clean:
            action_clean = "KICK"

        clip_filename = f"bullying_{ts_str}_{action_clean}.mp4"
        clip_filepath = os.path.join(alarm_config.INCIDENTS_DIR, clip_filename)

        # Ensure uniqueness — never overwrite
        base, ext = os.path.splitext(clip_filepath)
        counter   = 1
        while os.path.exists(clip_filepath):
            clip_filepath = f"{base}_{counter}{ext}"
            counter      += 1

        clip_rel_path = f"/incidents/{os.path.basename(clip_filepath)}"

        def _save():
            try:
                h, w     = all_frames[0].shape[:2]
                fourcc   = cv2.VideoWriter_fourcc(*"mp4v")
                out_vid  = cv2.VideoWriter(clip_filepath, fourcc, 15.0, (w, h))
                for f in all_frames:
                    if f is not None:
                        frame_resized = f if f.shape[:2] == (h, w) else cv2.resize(f, (w, h))
                        out_vid.write(frame_resized)
                out_vid.release()
                print(f"[RECORDING] Saved incident clip: {clip_filepath} ({len(all_frames)} frames)")

                # Update AlarmManager with clip path
                alarm_manager.set_clip_path(inc_id, clip_rel_path)

            except Exception as e:
                print(f"[RECORDING ERROR] Failed to save clip: {e}")

        threading.Thread(target=_save, daemon=True, name=f"clip-save-{inc_id}").start()

    def _logger_worker(self):
        """Prints performance diagnostics every 3 seconds."""
        last_log = time.time()
        last_cap  = 0
        last_ai   = 0
        last_wrtc = 0

        while self.running:
            time.sleep(3.0)
            now = time.time()
            dt  = max(0.001, now - last_log)

            with self.lock:
                cap_c  = self.capture_count
                ai_c   = self.ai_count
                wrtc_c = self.webrtc_count
                raw_ts = self.latest_raw_timestamp
                ann_ts = self.latest_annotated_timestamp
                ai_ms  = self.total_ai_ms

            cap_fps  = (cap_c  - last_cap)  / dt
            ai_fps   = (ai_c   - last_ai)   / dt
            wrtc_fps = (wrtc_c - last_wrtc) / dt

            ai_age_ms   = int((now - ann_ts) * 1000) if ann_ts > 0 else 0
            raw_age_ms  = int((now - raw_ts) * 1000) if raw_ts > 0 else 0

            print(f"\n[SAFECAM PERF] {self.camera_id}")
            print(f"  Capture FPS:     {cap_fps:.1f}")
            print(f"  WebRTC FPS:      {wrtc_fps:.1f}")
            print(f"  AI FPS:          {ai_fps:.1f}  (target={alarm_config.TARGET_AI_FPS})")
            print(f"  YOLO ms:         {int(ai_ms)}")
            print(f"  AI frame age:    {ai_age_ms} ms")
            print(f"  PreBuf frames:   {self.rolling_buffer.frame_count}/{self.rolling_buffer.capacity}")
            print(f"  Source:          {self.source_label}")

            last_log  = now
            last_cap  = cap_c
            last_ai   = ai_c
            last_wrtc = wrtc_c

    # ---------------------------------------------------------------- display

    def get_display_frame(self):
        """
        Return the newest available frame for WebRTC display.
        Prefers annotated (AI-processed) frame; falls back to raw.
        Never blocks. Never waits for AI.
        """
        with self.lock:
            if self.latest_annotated_frame is not None:
                frame = self.latest_annotated_frame
                ts    = self.latest_annotated_timestamp
            elif self.latest_raw_frame is not None:
                frame = self.latest_raw_frame
                ts    = self.latest_raw_timestamp
            else:
                frame = None
                ts    = time.time()

            self.webrtc_count += 1
            self.last_webrtc_emit_timestamp = time.time()

        if frame is None:
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        if frame.shape[:2] != (1080, 1920):
            frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LINEAR)

        return frame, ts

    def stop(self):
        if not self.running:
            return
        print(f"[AI] Stopping AI worker for {self.camera_id}")
        print(f"[RTSP] Releasing capture for {self.camera_id}")
        print(f"[BUFFER] Clearing frame buffer for {self.camera_id}")
        self.running = False

        if not self.is_synthetic and self.cap is not None:
            try:
                self.cap.release()
                self.cap = None
            except Exception as e:
                print(f"[RTSP] Error releasing capture: {e}")

        with self.lock:
            self.latest_raw_frame       = None
            self.latest_annotated_frame = None
            if hasattr(self, 'rolling_buffer') and self.rolling_buffer:
                self.rolling_buffer.clear()

        print(f"[PIPELINE] {self.camera_id} stopped")


# ============================================================================
# Camera Manager (Singleton)
# ============================================================================

class CameraManager:
    """
    Ensures ONE SingleCameraPipeline per camera_id across all WebRTC clients.
    """
    _instance = None
    _lock     = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.pipelines = {}
        return cls._instance

    def get_or_create_pipeline(self, camera_id: str = "CAM-001", stream_url: str = "") -> SingleCameraPipeline:
        with self._lock:
            if camera_id not in self.pipelines or not self.pipelines[camera_id].running:
                print(f"[CAMERA MANAGER] Creating pipeline: camera_id='{camera_id}' stream='{stream_url}'")
                self.pipelines[camera_id] = SingleCameraPipeline(camera_id=camera_id, stream_url=stream_url)
            return self.pipelines[camera_id]

    def release_pipeline(self, camera_id: str):
        with self._lock:
            if camera_id in self.pipelines:
                p = self.pipelines[camera_id]
                if p.active_viewers <= 0 or not p.running:
                    p.stop()
                    del self.pipelines[camera_id]
                    print(f"[CAMERA MANAGER] Released pipeline for camera_id='{camera_id}'")


# ============================================================================
# WebRTC VideoStreamTrack
# ============================================================================

class CameraTrack(VideoStreamTrack):
    """
    Feeds SingleCameraPipeline frames into the WebRTC peer connection.
    Does NOT open its own RTSP connection or start its own AI worker.
    """

    def __init__(self, pipeline: SingleCameraPipeline):
        super().__init__()
        self.pipeline = pipeline

    async def recv(self):
        pts, time_base    = await self.next_timestamp()
        display_frame, ts = self.pipeline.get_display_frame()

        new_frame           = VideoFrame.from_ndarray(display_frame, format="bgr24")
        new_frame.pts       = pts
        new_frame.time_base = time_base
        return new_frame

    def stop(self):
        super().stop()
