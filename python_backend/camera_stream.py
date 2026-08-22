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
    from ai_engine import AIEngine
except ImportError:
    from python_backend.ai_engine import AIEngine

# Configure OpenCV FFmpeg low-delay options
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|max_delay;0|analyzeduration;100000|probesize;100000"
cv2.setNumThreads(1)

# Global shared AI Engine instance (models loaded once on CPU)
global_ai_engine = AIEngine(model_path="yolo11n.pt")


class SyntheticCameraSource:
    """
    High-resolution 1080p synthetic camera source generator.
    Used when no physical webcam or RTSP stream is accessible.
    """
    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height
        self.start_time = time.time()

    def read(self):
        t = time.time() - self.start_time
        frame = np.full((self.height, self.width, 3), (15, 23, 42), dtype=np.uint8)

        # Grid background
        for y in range(0, self.height, 100):
            cv2.line(frame, (0, y), (self.width, y), (30, 41, 59), 1)
        for x in range(0, self.width, 100):
            cv2.line(frame, (x, 0), (x, self.height), (30, 41, 59), 1)

        # Dynamic Person 1
        p1_x = int(400 + math.sin(t * 1.2) * 350)
        p1_y = int(500 + math.cos(t * 0.8) * 50)
        self._draw_synthetic_person(frame, p1_x, p1_y, color=(200, 200, 200))

        # Dynamic Person 2
        p2_x = int(1400 - math.sin(t * 1.2) * 350)
        p2_y = int(520 + math.sin(t * 0.8) * 40)
        self._draw_synthetic_person(frame, p2_x, p2_y, color=(180, 180, 220))

        # Banner
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"SYNTHETIC CCTV SOURCE | 1080P | {timestamp}", (40, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 212, 255), 2)

        return True, frame

    def _draw_synthetic_person(self, frame, x, y, color):
        cv2.circle(frame, (x, y - 120), 25, color, -1)
        cv2.rectangle(frame, (x - 30, y - 95), (x + 30, y + 20), color, -1)
        cv2.line(frame, (x - 30, y - 80), (x - 70, y - 20), color, 8)
        cv2.line(frame, (x + 30, y - 80), (x + 70, y - 20), color, 8)
        cv2.line(frame, (x - 15, y + 20), (x - 35, y + 110), color, 10)
        cv2.line(frame, (x + 15, y + 20), (x + 35, y + 110), color, 10)

    def release(self):
        pass


class SingleCameraPipeline:
    """
    Isolated Camera Pipeline for ONE camera stream.
    Architecture:
    RTSP Camera
        |
    ONE Capture Worker Thread (Buffer size = 1, latest raw frame)
        |
        +---> RTSP Watchdog (Detects freezes & reconnects safely)
        |
        +---> WebRTC Stream Track (Path 1: 1080p @ 30 FPS target, latest frame wins)
        |
        +---> AI Worker Thread (Path 2: 640x360 @ 8-12 FPS target, stale frame dropping)
              YOLOv11 + ByteTrack + MediaPipe Pose + RWF-LSTM
    """
    def __init__(self, camera_id="CAM-001", stream_url=""):
        self.camera_id = camera_id
        self.stream_url = stream_url.strip() if stream_url else ""
        self.ai_engine = global_ai_engine

        self.cap = None
        self.is_synthetic = False
        self.source_label = "RTSP"
        self.lock = threading.Lock()
        self.running = True

        # Frame Buffers (Capacity = 1)
        self.latest_raw_frame = None
        self.latest_raw_timestamp = 0.0

        self.latest_annotated_frame = None
        self.latest_annotated_timestamp = 0.0

        # Performance & Timing Counters
        self.capture_count = 0
        self.ai_count = 0
        self.ai_dropped_count = 0
        self.webrtc_count = 0

        self.last_ai_grab_timestamp = 0.0
        self.last_successful_read_timestamp = time.time()
        self.last_webrtc_emit_timestamp = 0.0

        # Measured Component Times (ms)
        self.yolo_ms = 0.0
        self.mediapipe_ms = 0.0
        self.rwf_lstm_ms = 0.0
        self.detected_persons_count = 0

        self._open_capture_source()

        # Start Pipeline Threads
        self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.watchdog_thread = threading.Thread(target=self._watchdog_worker, daemon=True)
        self.ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self.logger_thread = threading.Thread(target=self._logger_worker, daemon=True)

        self.capture_thread.start()
        self.watchdog_thread.start()
        self.ai_thread.start()
        self.logger_thread.start()

    def _open_capture_source(self):
        """Initializes OpenCV VideoCapture or synthetic fallback."""
        if self.stream_url:
            if self.stream_url.isdigit():
                self.cap = cv2.VideoCapture(int(self.stream_url))
                self.source_label = f"WEBCAM_{self.stream_url}"
            else:
                self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
                self.source_label = "RTSP_STREAM"
        else:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.source_label = "WEBCAM_0"
            else:
                self.is_synthetic = True
                self.source_label = "SYNTHETIC"
                self.cap = SyntheticCameraSource(1920, 1080)

        if not self.is_synthetic and self.cap is not None:
            if not self.cap.isOpened():
                print(f"[CAMERA PIPELINE] Physical RTSP/Webcam unreadable for {self.camera_id}. Switching to Synthetic Source.")
                self.is_synthetic = True
                self.source_label = "SYNTHETIC"
                self.cap = SyntheticCameraSource(1920, 1080)
            else:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _capture_worker(self):
        """ONE capture worker thread per camera. Overwrites latest_raw_frame on every read."""
        is_file_source = self.stream_url.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
        while self.running:
            try:
                if self.cap is not None:
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        now = time.time()
                        with self.lock:
                            self.latest_raw_frame = frame
                            self.latest_raw_timestamp = now
                            self.capture_count += 1
                            self.last_successful_read_timestamp = now
                        if is_file_source:
                            time.sleep(0.033)  # Pace video file playback at ~30 FPS
                    else:
                        if is_file_source:
                            # Loop video file continuously
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        time.sleep(0.002)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"[CAPTURE WORKER ERROR] {self.camera_id}: {e}")
                time.sleep(0.05)

    def _watchdog_worker(self):
        """RTSP Watchdog: Detects stream freezes and reconnects safely."""
        reconnect_delay = 1.0
        while self.running:
            time.sleep(1.5)
            if self.is_synthetic:
                continue

            now = time.time()
            with self.lock:
                stalled_sec = now - self.last_successful_read_timestamp

            if stalled_sec > 3.0:
                print(f"\n[RTSP WATCHDOG ALERT] Camera {self.camera_id} capture frozen ({stalled_sec:.1f}s without frame). Attempting safe reconnect...")
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
        Independent AI Worker:
        Runs YOLO11 + MediaPipe Pose + RWF-LSTM at target 8-12 FPS.
        Grabs newest raw frame, drops intermediate stale frames. Never blocks WebRTC or capture.
        """
        target_interval = 0.09 # ~11 FPS target cadence
        while self.running:
            loop_start = time.time()
            raw_frame = None
            capture_ts = 0.0

            with self.lock:
                if self.latest_raw_frame is not None:
                    if self.latest_raw_timestamp > self.last_ai_grab_timestamp:
                        raw_frame = self.latest_raw_frame.copy()
                        capture_ts = self.latest_raw_timestamp

                        # Calculate dropped AI frames count
                        if self.last_ai_grab_timestamp > 0:
                            skipped = max(0, self.capture_count - self.ai_count - 1)
                            self.ai_dropped_count += skipped
                        self.last_ai_grab_timestamp = capture_ts

            if raw_frame is not None:
                try:
                    # Run AI Pipeline on 640x360 resized copy
                    annotated, telemetry = self.ai_engine.process_frame(raw_frame, self.camera_id)

                    with self.lock:
                        self.latest_annotated_frame = annotated
                        self.latest_annotated_timestamp = capture_ts
                        self.ai_count += 1
                        self.yolo_ms = telemetry.get("yolo_ms", 0.0)
                        self.mediapipe_ms = telemetry.get("mediapipe_ms", 0.0)
                        self.rwf_lstm_ms = telemetry.get("rwf_lstm_ms", 0.0)
                        self.detected_persons_count = telemetry.get("people_count", 0)
                        persons = telemetry.get("tracked_persons", [])
                        self.verified_persons_count = len([p for p in persons if p.get("is_verified_real_person", False)])
                        self.rejected_persons_count = len([p for p in persons if not p.get("is_verified_real_person", False)])

                except Exception as e:
                    print(f"[AI WORKER ERROR] {self.camera_id}: {e}")

            # Dynamic sleep to maintain target 8-12 FPS cadence
            elapsed = time.time() - loop_start
            sleep_needed = max(0.005, target_interval - elapsed)
            time.sleep(sleep_needed)

    def _logger_worker(self):
        """
        Performance logging thread. Prints measured diagnostics block every 3 seconds.
        Matches exact required formatting.
        """
        last_log_time = time.time()
        last_cap = 0
        last_ai = 0
        last_wrtc = 0

        while self.running:
            time.sleep(3.0)
            now = time.time()
            dt = now - last_log_time if last_log_time > 0 else 3.0

            with self.lock:
                cap_c = self.capture_count
                ai_c = self.ai_count
                wrtc_c = self.webrtc_count
                raw_ts = self.latest_raw_timestamp
                ann_ts = self.latest_annotated_timestamp
                dropped_ai = self.ai_dropped_count
                yolo_t = self.yolo_ms
                mp_t = self.mediapipe_ms
                rwf_t = self.rwf_lstm_ms
                v_count = getattr(self, "verified_persons_count", 0)
                r_count = getattr(self, "rejected_persons_count", 0)

            cap_fps = (cap_c - last_cap) / dt
            ai_fps = (ai_c - last_ai) / dt
            wrtc_fps = (wrtc_c - last_wrtc) / dt

            ai_frame_age_ms = int((now - ann_ts) * 1000.0) if ann_ts > 0 else 0
            webrtc_frame_age_ms = int((now - raw_ts) * 1000.0) if raw_ts > 0 else 0
            end_to_end_latency_ms = max(webrtc_frame_age_ms, ai_frame_age_ms)

            print(f"\n[PERFORMANCE]")
            print(f"Capture FPS: {cap_fps:.1f}")
            print(f"WebRTC FPS: {wrtc_fps:.1f}")
            print(f"AI FPS: {ai_fps:.1f}")
            print(f"YOLO: {int(yolo_t)} ms")
            print(f"MediaPipe: {int(mp_t)} ms")
            print(f"RWF-LSTM: {int(rwf_t)} ms")
            print(f"AI Frame Age: {ai_frame_age_ms} ms")
            print(f"AI Dropped Frames: {dropped_ai}")
            print(f"WebRTC Frame Age: {webrtc_frame_age_ms} ms")
            print(f"End-to-End Display Latency: {end_to_end_latency_ms} ms")
            print(f"Verified Real Persons: {v_count} | Rejected Photos/Screens: {r_count}\n")

            last_log_time = now
            last_cap = cap_c
            last_ai = ai_c
            last_wrtc = wrtc_c

    def get_display_frame(self):
        """
        Retrieves newest available 1080p frame for WebRTC display.
        Serves latest_annotated_frame if available; falls back to latest_raw_frame.
        Never blocks, never waits for AI.
        """
        with self.lock:
            if self.latest_annotated_frame is not None:
                frame = self.latest_annotated_frame
                ts = self.latest_annotated_timestamp
            elif self.latest_raw_frame is not None:
                frame = self.latest_raw_frame
                ts = self.latest_raw_timestamp
            else:
                frame = None
                ts = time.time()

            self.webrtc_count += 1
            self.last_webrtc_emit_timestamp = time.time()

        if frame is None:
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        if frame.shape[:2] != (1080, 1920):
            frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LINEAR)

        return frame, ts

    def stop(self):
        self.running = False
        if not self.is_synthetic and self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass


class CameraManager:
    """
    Singleton Manager: Ensures ONE SingleCameraPipeline per camera_id / RTSP URL across all WebRTC clients.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.pipelines = {}
        return cls._instance

    def get_or_create_pipeline(self, camera_id="CAM-001", stream_url=""):
        with self._lock:
            if camera_id not in self.pipelines or not self.pipelines[camera_id].running:
                print(f"[CAMERA MANAGER] Creating SingleCameraPipeline for camera_id='{camera_id}' stream='{stream_url}'")
                pipeline = SingleCameraPipeline(camera_id=camera_id, stream_url=stream_url)
                self.pipelines[camera_id] = pipeline
            return self.pipelines[camera_id]


class CameraTrack(VideoStreamTrack):
    """
    WebRTC VideoStreamTrack feeding off SingleCameraPipeline at 30 FPS target.
    Does NOT open separate RTSP connections or start separate AI workers.
    """
    def __init__(self, pipeline: SingleCameraPipeline):
        super().__init__()
        self.pipeline = pipeline

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        display_frame, ts = self.pipeline.get_display_frame()

        new_frame = VideoFrame.from_ndarray(display_frame, format="bgr24")
        new_frame.pts = pts
        new_frame.time_base = time_base
        return new_frame

    def stop(self):
        super().stop()
