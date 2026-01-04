"""
Keypoint extraction utilities for YOLO pose detection.

Provides helper functions for extracting and validating specific keypoints
from YOLO pose estimation results.
"""

from typing import Optional, Tuple
import numpy as np

# YOLO pose keypoint indices (COCO format)
# 0: nose, 1: left eye, 2: right eye, 3: left ear, 4: right ear
# 5: left shoulder, 6: right shoulder, 7: left elbow, 8: right elbow
# 9: left wrist, 10: right wrist, 11: left hip, 12: right hip
# 13: left knee, 14: right knee, 15: left ankle, 16: right ankle

KEYPOINT_LEFT_SHOULDER = 5
KEYPOINT_RIGHT_SHOULDER = 6
KEYPOINT_LEFT_WRIST = 9
KEYPOINT_RIGHT_WRIST = 10


def extract_shoulder_wrist_keypoints(
    keypoints: np.ndarray,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[float]]:
    """Extract shoulder and wrist keypoints with confidence values.

    Args:
        keypoints: YOLO pose keypoints array of shape (17, 3) where each keypoint
                  has [x, y, confidence]

    Returns:
        Tuple of (left_shoulder, right_shoulder, left_wrist, right_wrist, min_confidence)
        where each keypoint is array [x, y, confidence], or (None, None, None, None, None)
        if keypoints array is invalid or has insufficient shape.

    Example:
        >>> keypoints = np.array([[x, y, conf], ...])  # 17 keypoints
        >>> ls, rs, lw, rw, min_conf = extract_shoulder_wrist_keypoints(keypoints)
        >>> if min_conf is not None and min_conf > 0.3:
        ...     # Use the keypoints
    """
    if keypoints is None or len(keypoints) < 17:
        return None, None, None, None, None

    try:
        left_shoulder = keypoints[KEYPOINT_LEFT_SHOULDER]
        right_shoulder = keypoints[KEYPOINT_RIGHT_SHOULDER]
        left_wrist = keypoints[KEYPOINT_LEFT_WRIST]
        right_wrist = keypoints[KEYPOINT_RIGHT_WRIST]

        # Calculate minimum confidence among these 4 keypoints
        min_confidence = min(
            left_shoulder[2],
            right_shoulder[2],
            left_wrist[2],
            right_wrist[2]
        )

        return left_shoulder, right_shoulder, left_wrist, right_wrist, min_confidence

    except (IndexError, TypeError):
        return None, None, None, None, None


def calculate_wrist_shoulder_diff(
    left_shoulder: np.ndarray,
    right_shoulder: np.ndarray,
    left_wrist: np.ndarray,
    right_wrist: np.ndarray,
) -> float:
    """Calculate vertical difference between average wrist and shoulder positions.

    This metric is used to determine if the person is at the top (wrists above shoulders)
    or bottom (wrists below shoulders) of a pull-up motion.

    Args:
        left_shoulder: Left shoulder keypoint [x, y, confidence]
        right_shoulder: Right shoulder keypoint [x, y, confidence]
        left_wrist: Left wrist keypoint [x, y, confidence]
        right_wrist: Right wrist keypoint [x, y, confidence]

    Returns:
        Vertical difference (wrist_y - shoulder_y) in pixels.
        Positive values indicate wrists are below shoulders (hanging position).
        Negative values indicate wrists are above shoulders (pulled up position).

    Example:
        >>> diff = calculate_wrist_shoulder_diff(ls, rs, lw, rw)
        >>> if diff > 30:
        ...     print("Person is in hanging position")
        >>> elif diff < -30:
        ...     print("Person is in pulled-up position")
    """
    shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
    wrist_y = (left_wrist[1] + right_wrist[1]) / 2
    return wrist_y - shoulder_y
