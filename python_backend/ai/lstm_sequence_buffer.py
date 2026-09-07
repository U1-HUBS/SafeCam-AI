import numpy as np
from collections import deque

class LSTMSequenceBuffer:
    def __init__(self, sequence_length=30):
        self.sequence_length = sequence_length
        self.buffers = {} # track_id -> deque
        self.last_seen = {} # track_id -> int (frames since last update)

    def update(self, track_id, normalized_keypoints):
        """
        Add a new frame of keypoints (24,) for a tracked person.
        """
        if track_id not in self.buffers:
            self.buffers[track_id] = deque(maxlen=self.sequence_length)
        
        self.buffers[track_id].append(normalized_keypoints)
        self.last_seen[track_id] = 0

    def get_sequence(self, track_id):
        """
        Returns the sequence if it has reached sequence_length, else None.
        """
        if track_id in self.buffers and len(self.buffers[track_id]) == self.sequence_length:
            return np.array(self.buffers[track_id])
        return None

    def tick(self, active_track_ids):
        """
        Clean up stale tracks
        """
        stale_ids = []
        for tid in list(self.buffers.keys()):
            if tid not in active_track_ids:
                self.last_seen[tid] += 1
                if self.last_seen[tid] > 30: # Clean up after 1 second of missing (assuming 30fps)
                    stale_ids.append(tid)
        
        for tid in stale_ids:
            del self.buffers[tid]
            del self.last_seen[tid]
