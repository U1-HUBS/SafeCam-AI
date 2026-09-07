import math

INTERACTION_CONFIG = {
    "min_people": 2,               # Must have at least 2 people to form an interaction
    "confidence_threshold": 0.80,  # LSTM confidence needed to even check for interaction
    "min_contact_frames": 2,       # How many frames the limb must be in contact range
    "max_contact_distance_ratio": 0.25, # Distance relative to target's torso/bbox height
}

class InteractionValidator:
    def __init__(self):
        # We track interaction states per (striker_id, target_id) pair
        # dict: {(striker_id, target_id): consecutive_contact_frames}
        self.contact_history = {}
        # Keep track of previous endpoint distances to determine approach direction
        # dict: {(striker_id, target_id): prev_distance}
        self.distance_history = {}

    def _get_target_region(self, action, target_keypoints, target_bbox):
        """
        Determines the center of the target region based on the action type.
        PUNCH -> Upper Body / Head
        KICK -> Lower Body
        """
        if target_keypoints is not None and not (target_keypoints == 0).all():
            # target_keypoints is flat (24,)
            pts = target_keypoints.reshape((12, 2))
            if action == 'PUNCH':
                # Upper body: Average of shoulders (0, 3)
                shoulder_l, shoulder_r = pts[0], pts[3]
                return (shoulder_l + shoulder_r) / 2.0
            elif action == 'KICK':
                # Lower body: Average of hips (6, 9)
                hip_l, hip_r = pts[6], pts[9]
                return (hip_l + hip_r) / 2.0
        
        # Fallback to BBox if keypoints missing
        x1, y1, x2, y2 = target_bbox
        if action == 'PUNCH':
            return (x1 + x2) / 2.0, y1 + (y2 - y1) * 0.25 # Top quarter
        else:
            return (x1 + x2) / 2.0, y1 + (y2 - y1) * 0.75 # Bottom quarter

    def _get_striker_endpoint(self, action, striker_keypoints):
        """
        Determines the striking endpoint.
        PUNCH -> Wrists (15, 16)
        KICK -> Ankles (27, 28)
        """
        if striker_keypoints is None or (striker_keypoints == 0).all():
            return None
            
        pts = striker_keypoints.reshape((12, 2))
        
        if action == 'PUNCH':
            # Return both wrists (2, 5)
            return [pts[2], pts[5]]
        elif action == 'KICK':
            # Return both ankles (8, 11)
            return [pts[8], pts[11]]
        
        return None
        
    def _get_target_scale(self, target_bbox):
        """
        Returns a scale factor based on the target's bounding box height
        to make distance checking invariant to camera distance.
        """
        x1, y1, x2, y2 = target_bbox
        return max(1.0, float(y2 - y1))

    def validate(self, tracked_people):
        """
        Analyzes all people in the frame to validate any physical interactions.
        
        Args:
            tracked_people: List of dicts:
                {
                    'person_id': int,
                    'bbox': [x1, y1, x2, y2],
                    'keypoints': np.array(24), # Denormalized image-space keypoints (12 pairs)
                    'action': str,
                    'confidence': float
                }
                
        Returns:
            list of confirmed alert dicts:
            [{'striker_id': 1, 'target_id': 2, 'action': 'PUNCH', 'confidence': 0.85}]
        """
        confirmed_alerts = []
        current_pairs = set()
        
        if len(tracked_people) < INTERACTION_CONFIG["min_people"]:
            # Clean up history if not enough people
            self.contact_history.clear()
            self.distance_history.clear()
            return confirmed_alerts

        # Find all potential strikers
        for striker in tracked_people:
            action = striker.get('action')
            confidence = striker.get('confidence', 0.0)
            
            if action in ['PUNCH', 'KICK'] and confidence >= INTERACTION_CONFIG["confidence_threshold"]:
                striker_id = striker['person_id']
                endpoints = self._get_striker_endpoint(action, striker['keypoints'])
                
                if not endpoints:
                    continue
                    
                # Find the closest target
                best_target_id = None
                min_dist = float('inf')
                
                for target in tracked_people:
                    if target['person_id'] == striker_id:
                        continue
                        
                    target_region = self._get_target_region(action, target['keypoints'], target['bbox'])
                    
                    # Check distance from both endpoints (left/right limb)
                    for ep in endpoints:
                        # Skip if endpoint wasn't detected properly (0,0)
                        if ep[0] == 0 and ep[1] == 0:
                            continue
                            
                        dist = math.hypot(ep[0] - target_region[0], ep[1] - target_region[1])
                        
                        # Normalize distance by target's bounding box height
                        target_scale = self._get_target_scale(target['bbox'])
                        norm_dist = dist / target_scale
                        
                        if norm_dist < min_dist:
                            min_dist = norm_dist
                            best_target_id = target['person_id']
                            
                if best_target_id is not None:
                    pair_key = (striker_id, best_target_id)
                    current_pairs.add(pair_key)
                    
                    # 1. Is it within contact range?
                    if min_dist <= INTERACTION_CONFIG["max_contact_distance_ratio"]:
                        
                        # 2. Is it approaching or already very close?
                        prev_dist = self.distance_history.get(pair_key, float('inf'))
                        self.distance_history[pair_key] = min_dist
                        
                        # It is valid if it got closer OR if it's just maintaining very close contact
                        if min_dist <= prev_dist or min_dist < (INTERACTION_CONFIG["max_contact_distance_ratio"] / 2):
                            # Increment contact frames
                            self.contact_history[pair_key] = self.contact_history.get(pair_key, 0) + 1
                            
                            if self.contact_history[pair_key] >= INTERACTION_CONFIG["min_contact_frames"]:
                                confirmed_alerts.append({
                                    'striker_id': striker_id,
                                    'target_id': best_target_id,
                                    'action': action,
                                    'confidence': confidence,
                                    'distance_ratio': min_dist
                                })
                        else:
                            # Moving away, reset contact count
                            self.contact_history[pair_key] = 0
                    else:
                        self.distance_history[pair_key] = min_dist
                        self.contact_history[pair_key] = 0

        # Clean up old pairs that are no longer tracked or interacting
        stale_pairs = set(self.contact_history.keys()) - current_pairs
        for p in stale_pairs:
            del self.contact_history[p]
            if p in self.distance_history:
                del self.distance_history[p]

        return confirmed_alerts
