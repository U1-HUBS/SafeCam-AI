class TemporalConfirmation:
    """
    State machine that requires an action to be confidently predicted
    for a minimum number of consecutive frames before confirming it.
    """
    def __init__(self, confidence_threshold=0.80, min_consecutive_frames=3):
        self.confidence_threshold = confidence_threshold
        self.min_consecutive_frames = min_consecutive_frames
        
        self.current_action = "UNKNOWN"
        self.consecutive_count = 0
        self.last_confirmed_action = None
        
    def update(self, action_label, confidence):
        """
        Updates the internal state with a new prediction.
        
        Args:
            action_label (str): The predicted class (e.g., 'PUNCH', 'KICK', 'NEUTRAL')
            confidence (float): The probability of the prediction (0.0 to 1.0)
            
        Returns:
            str or None: The confirmed action label if it just crossed the threshold,
                         otherwise None.
        """
        if confidence < self.confidence_threshold:
            self.current_action = "UNKNOWN"
            self.consecutive_count = 0
            self.last_confirmed_action = None
            return None
            
        # Confidence is high enough. Is it the same action as the previous frame?
        if action_label == self.current_action:
            self.consecutive_count += 1
        else:
            self.current_action = action_label
            self.consecutive_count = 1
            self.last_confirmed_action = None
            
        # Have we reached the threshold?
        if self.consecutive_count >= self.min_consecutive_frames:
            # Only trigger once per sequence
            if self.last_confirmed_action != self.current_action:
                self.last_confirmed_action = self.current_action
                # Return the confirmed action so the caller can emit an alert
                return self.current_action
                
        return None

    def reset(self):
        self.current_action = "UNKNOWN"
        self.consecutive_count = 0
        self.last_confirmed_action = None
