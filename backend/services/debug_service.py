"""
Debug frame visualization and saving service.

This module handles saving annotated debug frames to disk when debug mode
is enabled. Frames are saved with overlay information showing:
    - Frame number
    - Wrist-shoulder difference value
    - Current exercise status
    - Rep count
    - Pose skeleton with keypoints (if detected)

Debug frames are only saved when running in DEBUG mode (not DEBUG_NO_SAVE
or NON_DEBUG). Frames are saved to the debug_frames/ directory.
"""

import cv2
import numpy as np
import time
from typing import Optional
from config import config
from utils.logging_utils import logger

# COCO pose skeleton connections
SKELETON_CONNECTIONS = [
    (5, 6),   # Left shoulder -> Right shoulder
    (5, 7),   # Left shoulder -> Left elbow
    (7, 9),   # Left elbow -> Left wrist
    (6, 8),   # Right shoulder -> Right elbow
    (8, 10),  # Right elbow -> Right wrist
    (5, 11),  # Left shoulder -> Left hip
    (6, 12),  # Right shoulder -> Right hip
    (11, 12), # Left hip -> Right hip
    (11, 13), # Left hip -> Left knee
    (13, 15), # Left knee -> Left ankle
    (12, 14), # Right hip -> Right knee
    (14, 16), # Right knee -> Right ankle
    (0, 1),   # Nose -> Left eye
    (0, 2),   # Nose -> Right eye
    (1, 3),   # Left eye -> Left ear
    (2, 4),   # Right eye -> Right ear
]

class DebugService:
    """Service for handling debug frame saving and visualization"""

    @staticmethod
    def draw_pose_on_frame(img: np.ndarray, keypoints: np.ndarray, min_confidence: float = 0.3) -> np.ndarray:
        """
        Draw pose skeleton and keypoints on the image

        Args:
            img: Image to draw on
            keypoints: Array of shape (17, 3) with [x, y, confidence] for each keypoint
            min_confidence: Minimum confidence to draw a keypoint

        Returns:
            Image with pose visualization
        """
        annotated = img.copy()

        # Draw skeleton connections (lines between keypoints)
        for start_idx, end_idx in SKELETON_CONNECTIONS:
            if start_idx < len(keypoints) and end_idx < len(keypoints):
                start_kp = keypoints[start_idx]
                end_kp = keypoints[end_idx]

                # Only draw if both keypoints have sufficient confidence
                if start_kp[2] > min_confidence and end_kp[2] > min_confidence:
                    start_point = (int(start_kp[0]), int(start_kp[1]))
                    end_point = (int(end_kp[0]), int(end_kp[1]))
                    cv2.line(annotated, start_point, end_point, (0, 255, 0), 2)

        # Draw keypoints (circles at each detected joint)
        for idx, kp in enumerate(keypoints):
            if kp[2] > min_confidence:
                x, y, conf = int(kp[0]), int(kp[1]), kp[2]

                # Color coding: shoulders and wrists in different colors for pull-up tracking
                if idx in [5, 6]:  # Shoulders
                    color = (255, 0, 0)  # Blue
                    radius = 6
                elif idx in [9, 10]:  # Wrists
                    color = (0, 0, 255)  # Red
                    radius = 6
                else:
                    color = (0, 255, 255)  # Yellow for other keypoints
                    radius = 4

                cv2.circle(annotated, (x, y), radius, color, -1)

                # Draw keypoint index for debugging
                cv2.putText(annotated, str(idx), (x + 8, y - 8),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        return annotated

    @staticmethod
    def save_debug_frame(img_bytes: bytes, frame_count: int, diff_value: float,
                        status: str, rep_count: int, keypoints: Optional[np.ndarray] = None) -> None:
        """
        Save debug frame with pose visualization

        Args:
            img_bytes: Image bytes from camera
            frame_count: Current frame number
            diff_value: Wrist-shoulder difference
            status: Current exercise status
            rep_count: Current rep count
            keypoints: Optional pose keypoints for visualization
        """
        if not config.save_frames or not config.debug_dir:
            return

        try:
            # Decode the image from bytes
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                logger.error(f"Failed to decode image for frame {frame_count}")
                return

            # Convert RGB to BGR (JPEG from Android is RGB, OpenCV expects BGR)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            # Draw pose skeleton if keypoints provided
            if keypoints is not None and len(keypoints) >= 17:
                debug_img = DebugService.draw_pose_on_frame(img, keypoints, config.min_confidence)
            else:
                debug_img = img.copy()
            
            # Add text overlay with background for better visibility
            overlay_color = (0, 255, 0)  # Green
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            thickness = 2
            
            # Add background rectangles for text
            texts = [
                f"Frame: {frame_count}",
                f"Diff: {diff_value:.1f}",
                f"Status: {status}",
                f"Reps: {rep_count}"
            ]
            
            y_offset = 40
            for i, text in enumerate(texts):
                y_pos = y_offset + (i * 35)
                
                # Get text size for background rectangle
                (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
                
                # Draw background rectangle
                cv2.rectangle(debug_img, (5, y_pos - text_height - 5), 
                             (15 + text_width, y_pos + baseline + 5), (0, 0, 0), -1)
                
                # Draw text
                cv2.putText(debug_img, text, (10, y_pos), font, font_scale, overlay_color, thickness)
            
            # Save frames
            save_frequency = 1
            if frame_count % save_frequency == 0:
                timestamp = int(time.time())
                filename = f"frame_{frame_count:04d}_diff_{diff_value:.1f}_reps_{rep_count}_{timestamp}.jpg"
                filepath = config.debug_dir / filename
                
                # Save the image
                success = cv2.imwrite(str(filepath), debug_img)
                
                if success:
                    logger.info(f"DEBUG FRAME SAVED: {filepath}")
                else:
                    logger.error(f"Failed to save debug frame: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving debug frame {frame_count}: {e}")

# Global debug service instance
debug_service = DebugService()