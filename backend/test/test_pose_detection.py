#!/usr/bin/env python3
"""
Test script for pose detection functionality
Tests YOLO pose detection with webcam or dummy frames
"""

import cv2
import numpy as np
from ultralytics import YOLO
import time

def test_pose_detection():
    """Test pose detection with webcam or test image"""
    
    print("Loading YOLO model...")
    model = YOLO('yolov8n-pose.pt')
    
    # Try to open webcam first
    cap = cv2.VideoCapture(0)
    use_webcam = cap.isOpened()
    
    if not use_webcam:
        print("Webcam not available, using test image mode")
        cap.release()
    else:
        print("Webcam opened successfully")
    
    frame_count = 0
    
    try:
        while True:
            if use_webcam:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to grab frame")
                    break
            else:
                # Create a dummy frame for testing
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "No webcam - dummy frame", (50, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            frame_count += 1
            print(f"\n--- Frame {frame_count} ---")
            print(f"Frame shape: {frame.shape}")
            
            # Run YOLO detection
            results = model(frame, verbose=False, conf=0.3)
            
            # Analyze results
            if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
                keypoints = results[0].keypoints.data[0].cpu().numpy()
                print(f"✅ Person detected! Keypoints shape: {keypoints.shape}")
                
                # Check key points for pull-up detection
                if len(keypoints) >= 17:
                    left_shoulder = keypoints[5]   # [x, y, confidence]
                    right_shoulder = keypoints[6]
                    left_wrist = keypoints[9]
                    right_wrist = keypoints[10]
                    
                    print(f"Left Shoulder:  x={left_shoulder[0]:.1f}, y={left_shoulder[1]:.1f}, conf={left_shoulder[2]:.2f}")
                    print(f"Right Shoulder: x={right_shoulder[0]:.1f}, y={right_shoulder[1]:.1f}, conf={right_shoulder[2]:.2f}")
                    print(f"Left Wrist:     x={left_wrist[0]:.1f}, y={left_wrist[1]:.1f}, conf={left_wrist[2]:.2f}")
                    print(f"Right Wrist:    x={right_wrist[0]:.1f}, y={right_wrist[1]:.1f}, conf={right_wrist[2]:.2f}")
                    
                    # Calculate positions
                    shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
                    wrist_y = (left_wrist[1] + right_wrist[1]) / 2
                    wrist_shoulder_diff = wrist_y - shoulder_y
                    
                    print(f"Average shoulder Y: {shoulder_y:.1f}")
                    print(f"Average wrist Y: {wrist_y:.1f}")
                    print(f"Wrist-Shoulder diff: {wrist_shoulder_diff:.1f}")
                    
                    # Determine position
                    if wrist_shoulder_diff < -20:
                        position = "UP (wrists above shoulders)"
                    elif wrist_shoulder_diff > 40:
                        position = "DOWN (wrists below shoulders)"
                    else:
                        position = "TRANSITION"
                    
                    print(f"🎯 Position: {position}")
                    
                    # Draw keypoints on frame if using webcam
                    if use_webcam:
                        # Draw skeleton
                        annotated_frame = results[0].plot()
                        cv2.imshow('Pose Detection Test', annotated_frame)
                        
                        # ESC to quit
                        if cv2.waitKey(1) & 0xFF == 27:
                            break
                else:
                    print("❌ Not enough keypoints detected")
            else:
                print("❌ No person detected in frame")
            
            if not use_webcam:
                # In dummy mode, just run a few iterations
                if frame_count >= 3:
                    break
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    finally:
        if use_webcam:
            cap.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    print("🏋️ AI Pull-Up Coach - Pose Detection Test")
    print("=" * 50)
    
    try:
        test_pose_detection()
        print("\n✅ Pose detection test complete!")
        
    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")