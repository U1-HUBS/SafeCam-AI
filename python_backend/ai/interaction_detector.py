"""
SAFECAM — Interaction & Multi-Factor Target Association Engine
================================================================
Architecture:
  1. Multi-Factor Target Scoring:
     - Distance Score (S_dist)
     - Direction / Vector Cosine Alignment (S_dir)
     - Frontal Aspect Check (S_frontal)
     - Bounding Box Overlap / Proximity (S_overlap)
     - Approach Velocity / Distance Decrease (S_approach)
     - Composite Score: T_score = 0.25*S_dist + 0.35*S_dir + 0.15*S_frontal + 0.15*S_overlap + 0.10*S_approach
  2. Hard Rejection Rules (attacker self-match, distance > 0.40, candidate behind attacker).
  3. Temporal Target Confirmation (3 frames) & Target Locking.
  4. Target Lock Release (action finish/recovery, target missing, attacker lost).
  5. Air Punch / Air Kick Handling (victim_tp = None, no victim, no alert).
  6. Configurable TARGET_DEBUG logging.
"""

import math
import time
import numpy as np
from typing import List, Tuple, Optional, Dict, NamedTuple

try:
    from tracking.tracker import TrackedPerson
except ImportError:
    from python_backend.tracking.tracker import TrackedPerson

try:
    from alarm_config import alarm_config
except ImportError:
    from python_backend.alarm_config import alarm_config


class PairInteraction(NamedTuple):
    attacker_tp:         TrackedPerson
    victim_tp:           Optional[TrackedPerson]
    attack_action:       str        # "PUNCH" or "KICK"
    action_confidence:   float
    dist_normalized:     float
    is_moving_toward:    bool
    is_dist_decreasing:  bool
    approach_speed:      float


class TargetState:
    """
    Per-attacker target selection state tracking candidate scores,
    confirmation frame counts, and locked target identity.
    """
    def __init__(self, attacker_id: int):
        self.attacker_id: int = attacker_id
        self.candidate_id: Optional[int] = None
        self.confirmation_count: int = 0
        self.locked_target_id: Optional[int] = None
        self.last_scores: Dict[int, float] = {}
        self.last_updated: float = time.time()
        self.missing_target_count: int = 0

    def reset_lock(self):
        self.candidate_id = None
        self.confirmation_count = 0
        self.locked_target_id = None
        self.missing_target_count = 0


class InteractionDetector:
    """
    Evaluates 2+ person pair interactions and multi-factor target association.
    """

    def __init__(
        self,
        frame_width: int = 1920,
        frame_height: int = 1080,
        min_spatial_dist_norm: float = 0.04,
        max_interaction_dist_norm: float = 0.40
    ):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.min_spatial_dist_norm = min_spatial_dist_norm
        self.max_interaction_dist_norm = max_interaction_dist_norm

        # Load weights and thresholds from alarm_config
        self.w_dist     = getattr(alarm_config, "TARGET_DISTANCE_WEIGHT", 0.25)
        self.w_dir      = getattr(alarm_config, "TARGET_DIRECTION_WEIGHT", 0.35)
        self.w_frontal  = getattr(alarm_config, "TARGET_FRONTAL_WEIGHT", 0.15)
        self.w_overlap  = getattr(alarm_config, "TARGET_OVERLAP_WEIGHT", 0.15)
        self.w_approach = getattr(alarm_config, "TARGET_APPROACH_WEIGHT", 0.10)

        self.min_target_score           = getattr(alarm_config, "MIN_TARGET_SCORE", 0.45)
        self.target_confirmation_frames = getattr(alarm_config, "TARGET_CONFIRMATION_FRAMES", 3)
        self.target_debug               = getattr(alarm_config, "TARGET_DEBUG", False)

        # Per-camera target state history: camera_id -> {attacker_id: TargetState}
        self._camera_target_states: Dict[str, Dict[int, TargetState]] = {}

    def _get_target_state(self, camera_id: str, attacker_id: int) -> TargetState:
        if camera_id not in self._camera_target_states:
            self._camera_target_states[camera_id] = {}
        cam_dict = self._camera_target_states[camera_id]
        if attacker_id not in cam_dict:
            cam_dict[attacker_id] = TargetState(attacker_id)
        return cam_dict[attacker_id]

    def reset_camera(self, camera_id: str):
        """Clears all target locks and candidate states for a given camera."""
        if camera_id in self._camera_target_states:
            for st in self._camera_target_states[camera_id].values():
                st.reset_lock()
            self._camera_target_states[camera_id].clear()

    def evaluate_interaction(
        self,
        camera_id: str,
        tracked_persons: List[TrackedPerson],
        person_action_map: dict,
        camera_history: dict
    ) -> Optional[PairInteraction]:
        """
        Evaluates active interactions between tracked persons.
        Returns PairInteraction with confirmed victim_tp if a target is confirmed,
        or None / victim_tp=None if solo air-punch or insufficient target evidence.
        """
        if not tracked_persons or len(tracked_persons) < 2:
            self.reset_camera(camera_id)
            return None

        # Find attackers performing PUNCH or KICK
        attacker_candidates = [
            tp for tp in tracked_persons
            if person_action_map.get(tp.track_id) in ("PUNCH", "KICK")
        ]

        if not attacker_candidates:
            # Clean up target state locks for callers returning to NORMAL
            self.reset_camera(camera_id)
            return None

        # Select highest confidence attacker candidate
        attacker_tp = max(attacker_candidates, key=lambda tp: tp.detection.confidence)
        attacker_id = attacker_tp.track_id
        attack_action = person_action_map[attacker_id]
        action_conf = attacker_tp.detection.confidence

        tgt_state = self._get_target_state(camera_id, attacker_id)
        tgt_state.last_updated = time.time()

        # Build candidate list of all other tracked persons
        raw_candidates = [
            tp for tp in tracked_persons
            if tp.track_id != attacker_id
        ]

        if not raw_candidates:
            tgt_state.reset_lock()
            return None

        # ---------------------------------------------------------------------
        # 1. HARD REJECTION & MULTI-FACTOR TARGET SCORING
        # ---------------------------------------------------------------------
        scored_candidates: List[Tuple[TrackedPerson, float, dict]] = []

        for cand_tp in raw_candidates:
            dist_norm = self._calc_dist_norm(attacker_tp.detection, cand_tp.detection)

            # Hard Rejection Rule 1: Spatial distance too far (> max_interaction_dist_norm)
            if dist_norm > self.max_interaction_dist_norm:
                continue

            score, components = self.compute_target_score(attacker_tp, cand_tp, camera_history)

            # Hard Rejection Rule 2: Candidate clearly behind attacker with active motion
            if components.get("is_behind", False):
                continue

            scored_candidates.append((cand_tp, score, components))

        # ---------------------------------------------------------------------
        # 2. DEBUG LOGGING
        # ---------------------------------------------------------------------
        if self.target_debug or getattr(alarm_config, "DEBUG_ACTION_LOGGING", False):
            print(f"\n[TARGET DIAG] Attacker ID={attacker_id} ({attack_action})")
            for c_tp, c_score, c_comp in scored_candidates:
                print(
                    f"  Candidate ID={c_tp.track_id}: "
                    f"dist={c_comp['s_dist']:.2f} dir={c_comp['s_dir']:.2f} "
                    f"frontal={c_comp['s_frontal']:.2f} overlap={c_comp['s_overlap']:.2f} "
                    f"approach={c_comp['s_approach']:.2f} TOTAL={c_score:.3f}"
                )

        # ---------------------------------------------------------------------
        # 3. TEMPORAL TARGET CONFIRMATION & TARGET LOCKING
        # ---------------------------------------------------------------------
        confirmed_victim_tp: Optional[TrackedPerson] = None

        if scored_candidates:
            best_cand_tp, best_score, best_comp = max(scored_candidates, key=lambda x: x[1])

            # Check if locked target is still present in active candidates
            if tgt_state.locked_target_id is not None:
                locked_tp = next((tp for tp in raw_candidates if tp.track_id == tgt_state.locked_target_id), None)
                if locked_tp is not None:
                    # Target remains LOCKED
                    confirmed_victim_tp = locked_tp
                    tgt_state.missing_target_count = 0
                    if self.target_debug:
                        print(f"  BEST TARGET={locked_tp.track_id} SCORE={best_score:.3f} STATUS=LOCKED")
                else:
                    tgt_state.missing_target_count += 1
                    if tgt_state.missing_target_count > 5:
                        tgt_state.reset_lock()

            if confirmed_victim_tp is None:
                if best_score >= self.min_target_score:
                    if tgt_state.candidate_id == best_cand_tp.track_id:
                        tgt_state.confirmation_count += 1
                    else:
                        tgt_state.candidate_id = best_cand_tp.track_id
                        tgt_state.confirmation_count = 1

                    if self.target_debug:
                        print(
                            f"  BEST TARGET={best_cand_tp.track_id} SCORE={best_score:.3f} "
                            f"CONFIRMATION={tgt_state.confirmation_count}/{self.target_confirmation_frames}"
                        )

                    if tgt_state.confirmation_count >= self.target_confirmation_frames:
                        tgt_state.locked_target_id = best_cand_tp.track_id
                        confirmed_victim_tp = best_cand_tp
                        if self.target_debug:
                            print(f"  STATUS=LOCKED to ID={best_cand_tp.track_id}")
                else:
                    tgt_state.candidate_id = None
                    tgt_state.confirmation_count = 0
        else:
            if self.target_debug:
                print("  NO VALID CANDIDATES (AIR PUNCH / AIR KICK)")

        # ---------------------------------------------------------------------
        # 4. AIR PUNCH / AIR KICK HANDLING
        # If no target confirmed -> return None (No victim, no bullying alert)
        # ---------------------------------------------------------------------
        if confirmed_victim_tp is None:
            return None

        # Calculate final motion metrics for confirmed pair
        dist_norm = self._calc_dist_norm(attacker_tp.detection, confirmed_victim_tp.detection)
        moving_toward = self._is_moving_toward(camera_history, attacker_tp.detection, confirmed_victim_tp.detection)
        dist_decreasing = self._is_distance_decreasing(camera_history, dist_norm)
        approach_speed = self._compute_approach_speed(camera_history, dist_norm)

        return PairInteraction(
            attacker_tp=attacker_tp,
            victim_tp=confirmed_victim_tp,
            attack_action=attack_action,
            action_confidence=action_conf,
            dist_normalized=round(dist_norm, 4),
            is_moving_toward=moving_toward,
            is_dist_decreasing=dist_decreasing,
            approach_speed=round(approach_speed, 4)
        )

    def compute_target_score(
        self,
        attacker_tp: TrackedPerson,
        candidate_tp: TrackedPerson,
        camera_history: dict
    ) -> Tuple[float, dict]:
        """
        Calculates multi-factor target score (0.0 to 1.0) for a given attacker and candidate pair:
          S_dist, S_dir, S_frontal, S_overlap, S_approach
        """
        adet = attacker_tp.detection
        cdet = candidate_tp.detection

        # A. Distance Score (Normalized spatial proximity)
        dist_norm = self._calc_dist_norm(adet, cdet)
        s_dist = max(0.0, 1.0 - (dist_norm / max(0.01, self.max_interaction_dist_norm)))

        # B. Direction / Vector Cosine Alignment
        # Attacker velocity vector from centroid history or velocity method
        att_vel = attacker_tp.velocity()
        if att_vel is not None:
            v_ax, v_ay = att_vel
        else:
            prev_ax = camera_history.get("prev_attack_cx")
            prev_ay = camera_history.get("prev_attack_cy")
            if prev_ax is None:
                prev_ax = adet.cx
            if prev_ay is None:
                prev_ay = adet.cy
            v_ax, v_ay = adet.cx - prev_ax, adet.cy - prev_ay

        v_mag = (v_ax * v_ax + v_ay * v_ay) ** 0.5

        # Direction vector from attacker to candidate
        v_cx = cdet.cx - adet.cx
        v_cy = cdet.cy - adet.cy
        c_mag = (v_cx * v_cx + v_cy * v_cy) ** 0.5

        is_behind = False

        if v_mag < 1.5 or c_mag < 1.0:
            # Velocity magnitude too small to determine directional vector reliably -> neutral score
            cos_sim = 0.50
            s_dir = 0.50
            s_frontal = 0.50
        else:
            cos_sim = (v_ax * v_cx + v_ay * v_cy) / (v_mag * c_mag)

            if cos_sim < -0.30 and v_mag > 2.0:
                is_behind = True

            s_dir = max(0.0, cos_sim)

            # C. Frontal Aspect Check
            if cos_sim > 0.50:
                s_frontal = 1.0
            elif cos_sim > 0.0:
                s_frontal = cos_sim * 2.0
            else:
                s_frontal = 0.0

        # D. Bounding Box Overlap / Proximity
        ix1 = max(adet.x1, cdet.x1)
        iy1 = max(adet.y1, cdet.y1)
        ix2 = min(adet.x2, cdet.x2)
        iy2 = min(adet.y2, cdet.y2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        c_area = max(1, cdet.area)
        overlap_iou = inter / c_area
        s_overlap = min(1.0, overlap_iou / 0.05)

        # E. Approach Velocity / Distance Decrease
        prev_dist = camera_history.get("prev_dist_norm")
        if prev_dist is not None and prev_dist > dist_norm:
            dist_diff = prev_dist - dist_norm
            s_approach = min(1.0, dist_diff / 0.01)
        else:
            s_approach = 0.0

        # Composite Total Score
        total_score = (
            (self.w_dist * s_dist) +
            (self.w_dir * s_dir) +
            (self.w_frontal * s_frontal) +
            (self.w_overlap * s_overlap) +
            (self.w_approach * s_approach)
        )
        total_score = round(min(1.0, max(0.0, total_score)), 4)

        components = {
            "s_dist": round(s_dist, 4),
            "s_dir": round(s_dir, 4),
            "s_frontal": round(s_frontal, 4),
            "s_overlap": round(s_overlap, 4),
            "s_approach": round(s_approach, 4),
            "is_behind": is_behind,
            "cos_sim": round(cos_sim, 4)
        }

        return total_score, components

    def _calc_dist_norm(self, det_a, det_b) -> float:
        dx = det_a.cx - det_b.cx
        dy = det_a.cy - det_b.cy
        px_dist = (dx * dx + dy * dy) ** 0.5
        return px_dist / max(self.frame_width, 1)

    def _is_moving_toward(self, st: dict, attack_det, victim_det) -> bool:
        prev_ax = st.get("prev_attack_cx")
        prev_vx = st.get("prev_victim_cx")
        if prev_ax is None or prev_vx is None:
            return True
        prev_ay = st.get("prev_attack_cy", 0)
        prev_vy = st.get("prev_victim_cy", 0)
        prev_dist = ((prev_ax - prev_vx) ** 2 + (prev_ay - prev_vy) ** 2) ** 0.5
        curr_dist = ((attack_det.cx - victim_det.cx) ** 2 + (attack_det.cy - victim_det.cy) ** 2) ** 0.5
        return curr_dist < prev_dist

    def _is_distance_decreasing(self, st: dict, curr_dist_norm: float) -> bool:
        history = st.get("distance_history", [])
        if len(history) < 2:
            return True
        return curr_dist_norm <= (sum(history[-2:]) / 2)

    def _compute_approach_speed(self, st: dict, curr_dist_norm: float) -> float:
        prev_dist = st.get("prev_dist_norm")
        if prev_dist is None:
            return 0.0
        return max(0.0, prev_dist - curr_dist_norm)
