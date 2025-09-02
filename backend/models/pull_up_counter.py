import time
import numpy as np
from collections import deque
from config import config
from utils.logging_utils import logger

class FixedPullUpCounter:
    """Pull-up counter with fixed rep detection logic"""
    
    def __init__(self):
        self.count = 0
        self.position = "neutral"
        
        # Motion tracking
        self.position_history = deque(maxlen=30)
        self.direction_history = deque(maxlen=10)
        
        # Rep counting state
        self.last_rep_time = 0
        
        # Motion state tracking
        self.current_direction = "stable"
        self.consecutive_up_frames = 0
        self.consecutive_down_frames = 0
        
        self.frame_count = 0
    
    def detect_direction_change(self, current_diff):
        """Detect clear direction changes with confirmation"""
        self.position_history.append(current_diff)
        
        if len(self.position_history) < 5:
            return "starting", 0
        
        # Look at recent movement
        recent = list(self.position_history)[-5:]
        movement = recent[-1] - recent[0]
        
        # Determine direction with hysteresis
        new_direction = "stable"
        if movement > config.movement_threshold:  # Moving up (less negative)
            new_direction = "up"
        elif movement < -config.movement_threshold:  # Moving down (more negative)
            new_direction = "down"
        
        # Update consecutive counters
        if new_direction == "up":
            self.consecutive_up_frames += 1
            self.consecutive_down_frames = 0
        elif new_direction == "down":
            self.consecutive_down_frames += 1
            self.consecutive_up_frames = 0
        else:
            # Don't reset immediately for stable
            if self.consecutive_up_frames > 0:
                self.consecutive_up_frames = max(0, self.consecutive_up_frames - 0.5)
            if self.consecutive_down_frames > 0:
                self.consecutive_down_frames = max(0, self.consecutive_down_frames - 0.5)
        
        # Determine confirmed direction
        confirmed_direction = self.current_direction
        if self.consecutive_up_frames >= config.min_consecutive_frames:
            confirmed_direction = "up"
        elif self.consecutive_down_frames >= config.min_consecutive_frames:
            confirmed_direction = "down"
        elif self.consecutive_up_frames == 0 and self.consecutive_down_frames == 0:
            confirmed_direction = "stable"
        
        # Track direction changes
        if confirmed_direction != self.current_direction:
            self.direction_history.append((confirmed_direction, time.time(), current_diff))
            self.current_direction = confirmed_direction
            
            # Only log direction changes in debug modes
            if config.debug_mode != "non_debug":
                logger.info(f"Direction change: {self.current_direction.upper()} (diff: {current_diff:.1f})")
        
        return confirmed_direction, abs(movement)
    
    def analyze_pose(self, keypoints):
        """Fixed rep counting based on direction changes"""
        if keypoints is None or len(keypoints) == 0:
            return self.count, "no_person"
            
        try:
            # Get key points
            left_shoulder = keypoints[5]
            right_shoulder = keypoints[6] 
            left_wrist = keypoints[9]
            right_wrist = keypoints[10]
            
            # Check confidence
            min_confidence = min(left_shoulder[2], right_shoulder[2], left_wrist[2], right_wrist[2])
            if min_confidence < config.min_confidence:
                return self.count, "low_confidence"
            
            # Calculate position
            shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
            wrist_y = (left_wrist[1] + right_wrist[1]) / 2
            wrist_shoulder_diff = wrist_y - shoulder_y
            
            # Get direction
            direction, magnitude = self.detect_direction_change(wrist_shoulder_diff)
            
            # REP COUNTING - Look for DOWN -> UP sequences
            current_time = time.time()
            if current_time - self.last_rep_time > config.rep_cooldown:
                
                if len(self.direction_history) >= 2:
                    # Get last two direction changes
                    recent_changes = list(self.direction_history)[-2:]
                    
                    # Look for DOWN -> UP pattern
                    if (len(recent_changes) == 2 and 
                        recent_changes[0][0] == "down" and 
                        recent_changes[1][0] == "up"):
                        
                        # Additional validation: check the movement range
                        down_diff = recent_changes[0][2]
                        up_diff = recent_changes[1][2]
                        movement_range = abs(up_diff - down_diff)
                        
                        # Must have significant movement
                        if movement_range > config.min_movement_range:
                            self.count += 1
                            self.last_rep_time = current_time
                            
                            # Only log rep completion in debug modes
                            if config.debug_mode != "non_debug":
                                logger.info(f"REP COMPLETED! Count: {self.count}")
                                logger.info(f"   Movement: {down_diff:.1f} → {up_diff:.1f} (range: {movement_range:.1f})")
                            
                            # Clear history to prevent double counting
                            self.direction_history.clear()
            
            # Set display position
            if direction == "up":
                self.position = "pulling_up"
            elif direction == "down": 
                self.position = "lowering_down"
            else:
                self.position = "stable"
            
            return self.count, self.position
            
        except Exception as e:
            logger.error(f"Error in rep analysis: {e}")
            return self.count, "error"
    
    def reset(self):
        """Reset all counter state"""
        self.count = 0
        self.position = "neutral"
        self.position_history.clear()
        self.direction_history.clear()
        self.last_rep_time = 0
        self.current_direction = "stable"
        self.consecutive_up_frames = 0
        self.consecutive_down_frames = 0
        self.frame_count = 0
        
        logger.info("Pull-up counter reset to initial state")