"""
SAFECAM — Contact Detector Component
=====================================
Calculates physical contact/landing evidence using bounding-box overlap IoU, centroid proximity,
approach speed, and directional motion.
Contact evidence is required before a candidate can advance to temporal confirmation.
"""

from typing import NamedTuple
from .interaction_detector import PairInteraction


class ContactEvidence(NamedTuple):
    contact_score:      float
    contact_confirmed:  bool
    overlap_iou:        float
    dist_normalized:    float
    reason:             str


class ContactDetector:
    """
    Evaluates physical contact landing evidence between attacker and victim.
    """

    def __init__(
        self,
        min_contact_score: float = 0.50,
        contact_dist_thresh: float = 0.12,
        overlap_thresh: float = 0.05,
        min_approach_speed: float = 0.005
    ):
        self.min_contact_score = min_contact_score
        self.contact_dist_thresh = contact_dist_thresh
        self.overlap_thresh = overlap_thresh
        self.min_approach_speed = min_approach_speed

    def evaluate_contact(self, pair: PairInteraction) -> ContactEvidence:
        if not pair:
            return ContactEvidence(0.0, False, 0.0, 1.0, "No pair interaction")

        adet = pair.attacker_tp.detection
        vdet = pair.victim_tp.detection

        # Calculate bounding box IoU relative to victim area
        ix1 = max(adet.x1, vdet.x1)
        iy1 = max(adet.y1, vdet.y1)
        ix2 = min(adet.x2, vdet.x2)
        iy2 = min(adet.y2, vdet.y2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        v_area = max(1, vdet.area)
        overlap_iou = inter / v_area

        # Calculate composite contact score (0.0 to 1.0)
        prox_score = max(0.0, 1.0 - (pair.dist_normalized / max(0.01, self.contact_dist_thresh)))
        over_score = min(1.0, overlap_iou / max(0.001, self.overlap_thresh))
        appr_score = min(1.0, pair.approach_speed / max(0.001, self.min_approach_speed))
        towards_sc = 1.0 if pair.is_moving_toward else 0.0

        composite_score = (0.35 * prox_score) + (0.35 * over_score) + (0.15 * appr_score) + (0.15 * towards_sc)
        composite_score = round(composite_score, 4)

        # Contact landing condition: composite_score >= min_contact_score OR tight spatial proximity + overlap/approach
        contact_confirmed = (
            composite_score >= self.min_contact_score
            or (pair.dist_normalized <= self.contact_dist_thresh and (overlap_iou >= self.overlap_thresh or (pair.approach_speed >= self.min_approach_speed and pair.is_moving_toward)))
        )

        reason = (
            f"Contact score={composite_score:.2f} (dist={pair.dist_normalized:.2f}, overlap={overlap_iou:.2f})"
            if contact_confirmed else "Insufficient contact evidence"
        )

        return ContactEvidence(
            contact_score=composite_score,
            contact_confirmed=contact_confirmed,
            overlap_iou=round(overlap_iou, 4),
            dist_normalized=pair.dist_normalized,
            reason=reason
        )
