import cv2
import numpy as np
import time
from config import config
from utils.logging_utils import logger

class DebugService:
    """Service for handling debug frame saving and visualization"""
    
    @staticmethod
    def save_debug_frame(img_bytes: bytes, frame_count: int, diff_value: float, 
                        position: str, rep_count: int):
        """Save debug frame - only if SAVE_FRAMES is True"""
        if not config.save_frames or not config.debug_dir:
            return
            
        try:
            # Decode the image from bytes
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error(f"Failed to decode image for frame {frame_count}")
                return
            
            # Add debug info overlay
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
                f"Position: {position}",
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