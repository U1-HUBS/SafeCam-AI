import os

class AlarmConfig:
    """
    SAFECAM AI Bullying Alarm System Configuration.
    Single source of truth for all alarm thresholds, AI performance settings,
    temporal confirmation rules, contact estimation parameters, and clip persistence.

    All values are environment-variable overridable for easy tuning after
    real-world CCTV testing without changing source code.
    """

    # =========================================================================
    # MODEL CONFIGURATION
    # =========================================================================
    # Primary model: YOLO11n trained on Punch / Kick / Normal classes.
    # DO NOT use best_v2.pt. DO NOT use a second YOLO person model.
    MODEL_PATH = os.environ.get(
        "YOLO_MODEL_PATH",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "Model", "best_v1.pt"))
    )

    # =========================================================================
    # LAPTOP PERFORMANCE SETTINGS (Intel i5-1235U / Intel Iris Xe / 16 GB RAM)
    # =========================================================================
    # Image size fed to YOLO: 640 is the optimal laptop trade-off (speed vs accuracy)
    YOLO_IMGSZ = int(os.environ.get("YOLO_IMGSZ", 640))

    # Device: always CPU for this laptop (no NVIDIA GPU)
    YOLO_DEVICE = os.environ.get("YOLO_DEVICE", "cpu")

    # Minimum confidence for any raw YOLO detection to be considered
    YOLO_CONF_THRESHOLD = float(os.environ.get("YOLO_CONF_THRESHOLD", 0.10))

    # Configurable person detection confidence threshold (0.25–0.35 optimal)
    PERSON_CONFIDENCE = float(os.environ.get("PERSON_CONFIDENCE", 0.30))

    # Visual debug mode toggle for troubleshooting person detection IDs
    VISUAL_DEBUG_MODE = bool(int(os.environ.get("VISUAL_DEBUG_MODE", 0)))

    # Confidence above which a detection becomes a candidate for bullying analysis
    CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", 0.50))

    # Action Classifier Configuration
    ACTION_CONFIDENCE_THRESHOLD = float(os.environ.get("ACTION_CONFIDENCE_THRESHOLD", 0.20))
    ACTION_MARGIN_THRESHOLD     = float(os.environ.get("ACTION_MARGIN_THRESHOLD", 0.05))
    MIN_ACTION_FRAMES           = int(os.environ.get("MIN_ACTION_FRAMES", 2))
    ACTION_CONFIRMATION_WINDOW  = int(os.environ.get("ACTION_CONFIRMATION_WINDOW", 5))
    ACTION_COOLDOWN_FRAMES      = int(os.environ.get("ACTION_COOLDOWN_FRAMES", 5))
    ACTION_RECOVERY_FRAMES      = int(os.environ.get("ACTION_RECOVERY_FRAMES", 4))
    MIN_MOTION_VELOCITY_NORM    = float(os.environ.get("MIN_MOTION_VELOCITY_NORM", 0.0005))
    DEBUG_ACTION_LOGGING        = bool(int(os.environ.get("DEBUG_ACTION_LOGGING", 0)))

    # Target Association Configuration
    TARGET_DISTANCE_WEIGHT     = float(os.environ.get("TARGET_DISTANCE_WEIGHT", 0.25))
    TARGET_DIRECTION_WEIGHT    = float(os.environ.get("TARGET_DIRECTION_WEIGHT", 0.35))
    TARGET_FRONTAL_WEIGHT      = float(os.environ.get("TARGET_FRONTAL_WEIGHT", 0.15))
    TARGET_OVERLAP_WEIGHT      = float(os.environ.get("TARGET_OVERLAP_WEIGHT", 0.15))
    TARGET_APPROACH_WEIGHT     = float(os.environ.get("TARGET_APPROACH_WEIGHT", 0.10))

    MIN_TARGET_SCORE           = float(os.environ.get("MIN_TARGET_SCORE", 0.45))
    TARGET_CONFIRMATION_FRAMES = int(os.environ.get("TARGET_CONFIRMATION_FRAMES", 3))
    TARGET_DEBUG               = bool(int(os.environ.get("TARGET_DEBUG", 0)))

    # Target AI inference rate (YOLO runs at this rate, not every camera frame)
    TARGET_AI_FPS = float(os.environ.get("TARGET_AI_FPS", 10.0))
    MAX_AI_FPS    = float(os.environ.get("MAX_AI_FPS", 15.0))

    # Frame buffer capacity = 1 (always drop stale frames, always process newest)
    FRAME_BUFFER_SIZE = 1

    # =========================================================================
    # BULLYING INTERACTION & CONTACT ESTIMATION THRESHOLDS
    # All distance values are normalized (0.0–1.0) relative to frame width.
    # =========================================================================

    # Enable interaction validation layer (hard rule: 2+ persons required)
    INTERACTION_ENABLED = bool(int(os.environ.get("INTERACTION_ENABLED", 1)))

    # Minimum number of distinct persons detected for bullying analysis to proceed.
    # Isolated movement (< 2 persons) will NEVER trigger an alarm.
    MIN_PERSONS_FOR_BULLYING = int(os.environ.get("MIN_PERSONS_FOR_BULLYING", 2))
    MIN_PEOPLE_FOR_ATTACK    = MIN_PERSONS_FOR_BULLYING

    # Max normalized distance between attack region center and victim body center (0.15 = 15% frame width)
    CONTACT_DISTANCE_THRESHOLD = float(os.environ.get("CONTACT_DISTANCE_THRESHOLD", 0.15))

    # Max normalized distance between two persons' centroids to consider them in proximity
    PERSON_PROXIMITY_THRESHOLD = float(os.environ.get("PERSON_PROXIMITY_THRESHOLD", 0.50))

    # Fraction of victim bbox that attack bbox must overlap
    CONTACT_OVERLAP_THRESHOLD = float(os.environ.get("CONTACT_OVERLAP_THRESHOLD", 0.05))

    # Minimum normalized approach speed (fraction of frame width per AI frame)
    MIN_APPROACH_SPEED = float(os.environ.get("MIN_APPROACH_SPEED", 0.005))

    # Composite contact score threshold (0.0 to 1.0) combining proximity, overlap, approach & direction
    MIN_CONTACT_SCORE = float(os.environ.get("MIN_CONTACT_SCORE", 0.50))

    # Number of consecutive AI frames where all contact signals must be positive
    # before BULLYING_CONFIRMED is declared.
    BULLYING_CONFIRMATION_FRAMES = int(os.environ.get("BULLYING_CONFIRMATION_FRAMES", 3))
    MIN_CONSECUTIVE_ATTACK_FRAMES = BULLYING_CONFIRMATION_FRAMES

    # Number of consecutive AI frames WITHOUT confirmed bullying before the alarm turns off
    BULLYING_STOP_FRAMES = int(os.environ.get("BULLYING_STOP_FRAMES", 10))

    # =========================================================================
    # INCIDENT CLIP RECORDING
    # =========================================================================
    # Rolling buffer duration BEFORE the bullying event starts (seconds)
    PRE_EVENT_SECONDS  = float(os.environ.get("PRE_EVENT_SECONDS", 5.0))

    # Extra recording AFTER confirmed bullying stops (seconds)
    POST_EVENT_SECONDS = float(os.environ.get("POST_EVENT_SECONDS", 3.0))

    # Camera FPS for rolling buffer capacity estimation
    CAMERA_FPS = float(os.environ.get("CAMERA_FPS", 30.0))

    # Whether to write incident clips to disk
    SAVE_CLIPS = True

    # Maximum raw frames to buffer per active incident clip (safety cap)
    MAX_CLIP_FRAMES = int(os.environ.get("MAX_CLIP_FRAMES", 300))

    # Absolute path where incident MP4 clips and JSON are stored
    INCIDENTS_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "incidents")
    )

    # =========================================================================
    # ALARM COOLDOWN
    # =========================================================================
    # After an incident ends, wait this many seconds before allowing a new
    # incident ID to be created (prevents duplicate incident records for the
    # same continuous event).
    COOLDOWN_PERIOD_SEC = float(os.environ.get("COOLDOWN_PERIOD_SEC", 15.0))

    # =========================================================================
    # TRACKER CONFIGURATION
    # =========================================================================
    # Frames a tracked person can be absent before their track is dropped
    TRACKER_MAX_MISSING_FRAMES = int(os.environ.get("TRACKER_MAX_MISSING_FRAMES", 5))

    # IoU threshold for matching new detections to existing tracks
    TRACKER_IOU_THRESHOLD = float(os.environ.get("TRACKER_IOU_THRESHOLD", 0.30))

    # ByteTrack / LightweightTracker settings
    BYTETRACK_ENABLED = True


# Global singleton instance
alarm_config = AlarmConfig()
