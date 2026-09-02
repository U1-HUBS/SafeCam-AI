"""
SAFECAM — Archived Legacy Bullying Logic
=========================================
ARCHIVED MODULE: This module was superseded by the modular python_backend/ai/ package.
Maintained in _archive for reference only.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class BullyingResult:
    bullying_confirmed:  bool          = False
    state:               str           = "NORMAL"
    attack_type:         Optional[str] = None
    confidence:          float         = 0.0
    attacker_track_id:   Optional[int] = None
    victim_track_id:     Optional[int] = None
    reason:              str           = "Normal activity"
    distance_normalized: float         = 1.0
    contact_overlap:     float         = 0.0
    confirmation_frames: int           = 0
    stop_frames:         int           = 0
