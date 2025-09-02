import cv2
import numpy as np
from ultralytics import YOLO
from utils.logging_utils import logger
from config import config

class PoseService:
    """Service for handling YOLO pose detection model"""
    
    def __init__(self):
        self.model = None
    
    async def initialize(self):
        """Initialize the YOLO pose model"""
        logger.info("Loading YOLO pose model...")
        self.model = YOLO('yolov8n-pose.pt')
        
        # Warm up the model
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        _ = self.model(dummy, verbose=False)
        
        startup_msg = f"Pose model loaded in {config.mode_description}!"
        if config.save_frames:
            startup_msg += f" Debug frames location: {config.debug_dir.absolute()}"
        
        logger.info(startup_msg)
    
    def detect_pose(self, img: np.ndarray):
        """Detect pose keypoints in an image"""
        if not self.model:
            raise RuntimeError("Model not initialized")
        
        # Resize for performance
        height, width = img.shape[:2]
        if width > config.image_width_limit:
            scale = config.image_width_limit / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))
        
        results = self.model(img, verbose=False, conf=config.model_conf_threshold)
        
        if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
            return results[0].keypoints.data[0].cpu().numpy()
        
        return None

# Global pose service instance
pose_service = PoseService()