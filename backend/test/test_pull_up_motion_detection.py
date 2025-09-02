#!/usr/bin/env python3
"""
Motion-based script to continuously analyze pull-up movements
Uses direction change detection like the backend for better accuracy
"""

import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import deque

class MotionBasedPullUpAnalyzer:
    def __init__(self):
        self.count = 0
        self.position = "neutral"
        
        # Motion tracking
        self.position_history = deque(maxlen=30)
        self.direction_history = deque(maxlen=10)
        
        # Rep counting state
        self.last_rep_time = 0
        self.rep_cooldown = 2.0
        
        # Motion state tracking
        self.current_direction = "stable"
        self.consecutive_up_frames = 0
        self.consecutive_down_frames = 0
        self.min_consecutive_frames = 3
        
        self.frame_count = 0
        
        # Statistics
        self.all_measurements = []
        self.min_diff = float('inf')
        self.max_diff = float('-inf')
        
    def detect_direction_change(self, current_diff):
        """Detect clear direction changes with confirmation"""
        self.position_history.append(current_diff)
        self.all_measurements.append(current_diff)
        
        # Update min/max for range tracking
        self.min_diff = min(self.min_diff, current_diff)
        self.max_diff = max(self.max_diff, current_diff)
        
        if len(self.position_history) < 5:
            return "starting", 0, "🟡 STARTING", "↔"
        
        # Look at recent movement over 5 frames
        recent = list(self.position_history)[-5:]
        movement = recent[-1] - recent[0]  # Net change over 5 frames
        
        # Determine direction with hysteresis
        new_direction = "stable"
        if movement > 8:  # Moving up (less negative = wrists rising)
            new_direction = "up"
        elif movement < -8:  # Moving down (more negative = wrists lowering)
            new_direction = "down"
        
        # Update consecutive counters
        if new_direction == "up":
            self.consecutive_up_frames += 1
            self.consecutive_down_frames = 0
        elif new_direction == "down":
            self.consecutive_down_frames += 1
            self.consecutive_up_frames = 0
        else:
            # Gradual decay for stable periods
            if self.consecutive_up_frames > 0:
                self.consecutive_up_frames = max(0, self.consecutive_up_frames - 0.5)
            if self.consecutive_down_frames > 0:
                self.consecutive_down_frames = max(0, self.consecutive_down_frames - 0.5)
        
        # Determine confirmed direction
        confirmed_direction = self.current_direction
        if self.consecutive_up_frames >= self.min_consecutive_frames:
            confirmed_direction = "up"
        elif self.consecutive_down_frames >= self.min_consecutive_frames:
            confirmed_direction = "down"
        elif self.consecutive_up_frames == 0 and self.consecutive_down_frames == 0:
            confirmed_direction = "stable"
        
        # Track direction changes
        if confirmed_direction != self.current_direction:
            self.direction_history.append((confirmed_direction, time.time(), current_diff))
            self.current_direction = confirmed_direction
            print(f"🔄 Direction change: {self.current_direction.upper()} (diff: {current_diff:.1f})")
        
        # Create status display
        if confirmed_direction == "up":
            if self.consecutive_up_frames >= 6:
                status = "🔵 PULLING UP (Strong)"
                arrow = "⬆⬆"
            else:
                status = "🟦 PULLING UP (Weak)"
                arrow = "⬆"
        elif confirmed_direction == "down":
            if self.consecutive_down_frames >= 6:
                status = "🔴 LOWERING DOWN (Strong)"
                arrow = "⬇⬇"
            else:
                status = "🟥 LOWERING DOWN (Weak)"  
                arrow = "⬇"
        else:
            status = "🟡 STABLE/TRANSITION"
            arrow = "↔"
            
        return confirmed_direction, abs(movement), status, arrow
    
    def check_for_rep(self, current_diff):
        """Check if a complete rep has been performed"""
        current_time = time.time()
        
        if current_time - self.last_rep_time > self.rep_cooldown:
            if len(self.direction_history) >= 2:
                # Get last two direction changes
                recent_changes = list(self.direction_history)[-2:]
                
                # Look for DOWN -> UP pattern (complete pull-up)
                if (len(recent_changes) == 2 and 
                    recent_changes[0][0] == "down" and 
                    recent_changes[1][0] == "up"):
                    
                    # Additional validation: check the movement range
                    down_diff = recent_changes[0][2]
                    up_diff = recent_changes[1][2]
                    movement_range = abs(up_diff - down_diff)
                    
                    # Must have significant movement (at least 30 pixels)
                    if movement_range > 30:
                        self.count += 1
                        self.last_rep_time = current_time
                        
                        print(f"🎉 REP COMPLETED! Count: {self.count}")
                        print(f"   Movement: {down_diff:.1f} → {up_diff:.1f} (range: {movement_range:.1f})")
                        
                        # Clear history to prevent double counting
                        self.direction_history.clear()
                        return True
        return False
    
    def get_summary_stats(self):
        """Get current session statistics"""
        if not self.all_measurements:
            return None
            
        measurements = self.all_measurements
        return {
            'count': len(measurements),
            'min': min(measurements),
            'max': max(measurements),
            'avg': np.mean(measurements),
            'std': np.std(measurements),
            'range': max(measurements) - min(measurements)
        }

def print_measurements_continuously(video_source=0):
    """Print motion-based measurements in real-time"""
    
    print("🎯 Motion-Based Pull-Up Analyzer")
    print("=" * 60)
    print("This analyzes pull-up MOVEMENTS using direction changes")
    print("for more accurate rep counting and position detection.")
    print()
    print("Understanding the system:")
    print("📈 Tracks MOVEMENT PATTERNS over time (not just position)")
    print("🔄 Requires CONSISTENT direction for 3+ frames")
    print("🎯 Counts reps on complete DOWN → UP sequences")
    print("⏱️  2-second cooldown prevents double counting")
    print()
    print("Movement meanings:")
    print("⬆️  UP = Wrists rising relative to shoulders (pulling up)")
    print("⬇️  DOWN = Wrists lowering relative to shoulders (lowering down)")
    print("↔️  STABLE = Little movement (holding position)")
    print()
    print("Press 'Q' to quit, 'R' to reset counter")
    print("=" * 60)
    
    model = YOLO('yolov8n-pose.pt')
    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print("❌ Could not open video source")
        return
    
    analyzer = MotionBasedPullUpAnalyzer()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("End of video or camera disconnected")
                break
            
            analyzer.frame_count += 1
            
            # Run pose detection
            results = model(frame, verbose=False, conf=0.3)
            
            if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
                keypoints = results[0].keypoints.data[0].cpu().numpy()
                
                # Get key points
                left_shoulder = keypoints[5]   # [x, y, confidence]
                right_shoulder = keypoints[6]
                left_wrist = keypoints[9]
                right_wrist = keypoints[10]
                
                # Check if we have good confidence
                confidences = [left_shoulder[2], right_shoulder[2], left_wrist[2], right_wrist[2]]
                min_confidence = min(confidences)
                
                if min_confidence > 0.3:  # Good detection
                    # Calculate positions
                    shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
                    wrist_y = (left_wrist[1] + right_wrist[1]) / 2
                    diff = wrist_y - shoulder_y
                    
                    # Analyze motion
                    direction, movement_magnitude, status, arrow = analyzer.detect_direction_change(diff)
                    
                    # Check for completed reps
                    rep_completed = analyzer.check_for_rep(diff)
                    
                    # Print measurement every few frames
                    if analyzer.frame_count % 5 == 0:  # Every 5th frame
                        recent_avg = np.mean(list(analyzer.position_history)[-10:]) if len(analyzer.position_history) >= 10 else diff
                        
                        rep_indicator = "🆕 NEW REP! " if rep_completed else ""
                        print(f"{analyzer.frame_count:4d} | {diff:6.1f} | {arrow:2s} | {status:25s} | "
                              f"Move: {movement_magnitude:4.1f} | Reps: {analyzer.count:2d} | {rep_indicator}")
                    
                    # Show on video
                    cv2.putText(frame, f"Diff: {diff:.1f}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(frame, f"Direction: {direction.upper()}", (10, 70), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(frame, f"Reps: {analyzer.count}", (10, 110), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    cv2.putText(frame, f"Movement: {movement_magnitude:.1f}", (10, 150), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    cv2.putText(frame, f"Range: [{analyzer.min_diff:.0f}, {analyzer.max_diff:.0f}]", (10, 180), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    
                    # Draw pose skeleton
                    annotated_frame = results[0].plot()
                else:
                    # Low confidence detection
                    if analyzer.frame_count % 30 == 0:
                        print(f"{analyzer.frame_count:4d} | Low confidence detection (min: {min_confidence:.2f})")
                    annotated_frame = frame
                    cv2.putText(annotated_frame, f"Low Confidence: {min_confidence:.2f}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)
                    
            else:
                # No person detected
                if analyzer.frame_count % 30 == 0:
                    print(f"{analyzer.frame_count:4d} | No person detected")
                annotated_frame = frame
                cv2.putText(annotated_frame, "No Person Detected", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show video
            cv2.imshow('Motion-Based Pull-Up Analysis', annotated_frame)
            
            # Check for keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                print("🔄 Resetting counter...")
                analyzer = MotionBasedPullUpAnalyzer()
                print("Counter reset to 0")
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        # Print summary
        stats = analyzer.get_summary_stats()
        if stats and stats['count'] > 0:
            print("\n" + "=" * 60)
            print("📊 MOTION-BASED ANALYSIS SUMMARY")
            print("=" * 60)
            print(f"🏃‍♂️ Total REPS completed: {analyzer.count}")
            print(f"📏 Total measurements: {stats['count']}")
            print(f"📐 Difference range: {stats['min']:.1f} to {stats['max']:.1f}")
            print(f"📊 Average difference: {stats['avg']:.1f}")
            print(f"📈 Movement range: {stats['range']:.1f} pixels")
            print(f"🎯 Standard deviation: {stats['std']:.1f}")
            print()
            
            # Direction change analysis
            if len(analyzer.direction_history) > 0:
                print("🔄 MOVEMENT PATTERN ANALYSIS:")
                direction_changes = list(analyzer.direction_history)
                for i, (direction, timestamp, diff_val) in enumerate(direction_changes[-10:]):  # Last 10 changes
                    print(f"   {i+1:2d}. {direction.upper():6s} at diff {diff_val:6.1f}")
                print()
            
            # Motion-based thresholds (different from position-based)
            if len(analyzer.all_measurements) > 20:
                sorted_diffs = sorted(analyzer.all_measurements)
                percentile_10 = np.percentile(analyzer.all_measurements, 10)  # Lower position
                percentile_90 = np.percentile(analyzer.all_measurements, 90)  # Higher position
                
                print("🎯 MOTION ANALYSIS INSIGHTS:")
                print(f"📉 Lowest 10% positions (hanging): < {percentile_10:.0f}")
                print(f"📈 Highest 10% positions (pulled up): > {percentile_90:.0f}")
                print(f"🎚️  Main working range: {percentile_90:.0f} to {percentile_10:.0f}")
                print()
                print("⚙️  MOTION DETECTION SETTINGS:")
                print(f"   Movement threshold: ±8 pixels")
                print(f"   Confirmation frames: {analyzer.min_consecutive_frames}")
                print(f"   Rep validation range: 30+ pixels")
                print(f"   Rep cooldown: {analyzer.rep_cooldown} seconds")

if __name__ == "__main__":
    print("Choose video source:")
    print("1. Webcam")
    print("2. Video file")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        print_measurements_continuously(0)  # Webcam
    elif choice == "2":
        video_path = input("Enter video file path: ").strip()
        print_measurements_continuously(video_path)
    else:
        print("Invalid choice")