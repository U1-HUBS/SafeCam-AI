import os

class AlarmConfig:
    """
    SAFECAM AI Bullying Alarm System Configuration.
    Single source of truth for alarm thresholds, temporal confirmation rules, and clip persistence settings.
    """
    # Temporal Confirmation Rules
    MIN_CONSECUTIVE_FRAMES = 4        # N_confirm: consecutive AI frames required above confidence threshold
    CONFIDENCE_THRESHOLD = 0.65       # Min fight / violence probability threshold (0.0 to 1.0)
    
    # Incident Cooldown / Debounce
    COOLDOWN_PERIOD_SEC = 15.0        # Seconds to wait after an incident ends before allowing a new incident ID
    
    # Real-Person Verification Requirements
    REQUIRE_REAL_PERSON = True         # Require RealPersonVerifier status == VERIFIED_REAL_PERSON
    REQUIRE_EXPERT_RULE_PASS = True   # Require active attacker role + strike vector pass
    
    # Incident Clip Persistence
    SAVE_CLIPS = True                 # Automatically save 1080p MP4 incident clips & JPEG snapshots
    MAX_CLIP_FRAMES = 90              # ~3 seconds of incident frames per clip
    INCIDENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "incidents"))

# Global singleton instance
alarm_config = AlarmConfig()
