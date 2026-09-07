import numpy as np

def normalize_frame(keypoints):
    """
    Normalizes a single frame of keypoints (length 24 -> 12 pairs of X, Y).
    
    Normalization Method:
    1. Body-Centric Translation: The center of the hips is calculated. 
       This center is subtracted from all 12 X,Y coordinates.
    2. Torso-Based Scaling: The distance between the center of the hips and the center of the 
       shoulders is calculated (torso length). All coordinates are divided by this length.
       
    Args:
        keypoints (np.ndarray): Shape (24,) containing [X0, Y0, ... X11, Y11].
        
    Returns:
        np.ndarray: Shape (24,) normalized keypoints.
    """
    # If the frame is all zeros (no person detected), return it as-is
    if np.all(keypoints == 0):
        return keypoints.copy()
        
    # Reshape to (12, 2) for easier coordinate math
    pts = keypoints.reshape((12, 2))
    
    # New Indices:
    # 0: left_shoulder, 3: right_shoulder
    # 6: left_hip, 9: right_hip
    
    left_shoulder = pts[0]
    right_shoulder = pts[3]
    left_hip = pts[6]
    right_hip = pts[9]
    
    # 1. Translation: Center around the hips
    hip_center = (left_hip + right_hip) / 2.0
    pts_centered = pts - hip_center
    
    # 2. Scaling: Normalize by torso length
    shoulder_center = (left_shoulder + right_shoulder) / 2.0
    torso_length = np.linalg.norm(shoulder_center - hip_center)
    
    # Prevent division by zero
    if torso_length > 1e-6:
        pts_normalized = pts_centered / torso_length
    else:
        pts_normalized = pts_centered
        
    # Flatten back to (24,)
    return pts_normalized.flatten()

def normalize_sequence(sequence):
    """
    Normalizes a sequence of frames.
    
    Args:
        sequence (np.ndarray): Shape (num_frames, 24)
        
    Returns:
        np.ndarray: Normalized sequence.
    """
    normalized_seq = np.zeros_like(sequence)
    for i in range(len(sequence)):
        normalized_seq[i] = normalize_frame(sequence[i])
    return normalized_seq
