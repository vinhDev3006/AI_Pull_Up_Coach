#!/usr/bin/env python3
"""
Test script for pose_service visualization
Demonstrates how the PoseService detects and visualizes human poses

Educational script for students to understand:
- How to use the PoseService
- What keypoints are detected (17 body landmarks)
- How to visualize the skeleton on camera frames
- Frame sizes match what the tablet sends (640px width max, typically 640x360)
"""

import cv2
import numpy as np
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.append(str(Path(__file__).parent.parent))

from services.pose_service import pose_service
from config import config

# COCO pose skeleton connections (which keypoints connect to form the skeleton)
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

def draw_pose_on_frame(frame: np.ndarray, keypoints: np.ndarray, min_confidence: float = 0.3) -> np.ndarray:
    """
    Draw detected pose keypoints and skeleton on the frame

    Args:
        frame: Image to draw on
        keypoints: Array of shape (17, 3) with [x, y, confidence] for each keypoint
        min_confidence: Minimum confidence to draw a keypoint

    Returns:
        Frame with pose visualization drawn on it
    """
    annotated = frame.copy()

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
        if kp[2] > min_confidence:  # Check confidence
            x, y, conf = int(kp[0]), int(kp[1]), kp[2]

            # Color coding: shoulders and wrists in different colors for pull-up tracking
            if idx in [5, 6]:  # Shoulders
                color = (255, 0, 0)  # Blue
                radius = 8
            elif idx in [9, 10]:  # Wrists
                color = (0, 0, 255)  # Red
                radius = 8
            else:
                color = (0, 255, 255)  # Yellow for other keypoints
                radius = 5

            cv2.circle(annotated, (x, y), radius, color, -1)

            # Draw keypoint index for educational purposes
            cv2.putText(annotated, str(idx), (x + 10, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    return annotated


def print_keypoint_info(keypoints: np.ndarray) -> None:
    """Print detailed information about detected keypoints (for educational purposes)"""

    keypoint_names = [
        "Nose", "Left Eye", "Right Eye", "Left Ear", "Right Ear",
        "Left Shoulder", "Right Shoulder", "Left Elbow", "Right Elbow",
        "Left Wrist", "Right Wrist", "Left Hip", "Right Hip",
        "Left Knee", "Right Knee", "Left Ankle", "Right Ankle"
    ]

    print("\n📍 Detected Keypoints (COCO format):")
    print("-" * 70)

    for idx, kp in enumerate(keypoints):
        name = keypoint_names[idx] if idx < len(keypoint_names) else f"Point {idx}"
        x, y, conf = kp[0], kp[1], kp[2]

        # Highlight important keypoints for pull-up detection
        marker = ""
        if idx in [5, 6]:  # Shoulders
            marker = "  🔵 SHOULDER"
        elif idx in [9, 10]:  # Wrists
            marker = "  🔴 WRIST"

        print(f"  [{idx:2d}] {name:15s} → x={x:6.1f}, y={y:6.1f}, conf={conf:.2f}{marker}")

    # Calculate pull-up relevant metrics
    if len(keypoints) >= 11:
        left_shoulder = keypoints[5]
        right_shoulder = keypoints[6]
        left_wrist = keypoints[9]
        right_wrist = keypoints[10]

        if all(kp[2] > 0.3 for kp in [left_shoulder, right_shoulder, left_wrist, right_wrist]):
            shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
            wrist_y = (left_wrist[1] + right_wrist[1]) / 2
            wrist_shoulder_diff = wrist_y - shoulder_y

            print("\n🎯 Pull-Up Tracking Metrics:")
            print(f"  Average Shoulder Y: {shoulder_y:.1f}")
            print(f"  Average Wrist Y:    {wrist_y:.1f}")
            print(f"  Wrist-Shoulder Diff: {wrist_shoulder_diff:.1f}")

            if wrist_shoulder_diff < -20:
                status = "UP (wrists above shoulders) ⬆️"
            elif wrist_shoulder_diff > 40:
                status = "DOWN (wrists below shoulders) ⬇️"
            else:
                status = "TRANSITION ↔️"

            print(f"  Status: {status}")


async def test_pose_service_visualization():
    """Main test function demonstrating pose_service usage"""

    print("🏋️ Pose Service Visualization Test")
    print("=" * 70)

    # Step 1: Initialize the pose service
    print("\n[1/3] Initializing pose_service...")
    await pose_service.initialize()
    print(f"✅ Model loaded successfully!")
    print(f"   Config mode: {config.mode_description}")
    print(f"   Min confidence: {config.min_confidence}")
    print(f"   Image width limit: {config.image_width_limit}px (matches tablet processing)")

    # Step 2: Try to open webcam
    print("\n[2/3] Opening video source...")
    cap = cv2.VideoCapture(0)
    use_webcam = cap.isOpened()

    if not use_webcam:
        print("⚠️  Webcam not available - using dummy frames for demonstration")
        cap.release()
    else:
        print("✅ Webcam opened successfully")
        print("   Press ESC to quit, SPACE to pause/print keypoint details")
        print(f"   Note: Frames will be resized to {config.image_width_limit}px width (same as tablet)")

    # Step 3: Process frames
    print("\n[3/3] Processing frames...")
    print("-" * 70)

    frame_count = 0
    paused = False

    try:
        while True:
            if not paused:
                if use_webcam:
                    ret, frame = cap.read()
                    if not ret:
                        print("❌ Failed to grab frame")
                        break

                    # Resize to match tablet processing (640px width max)
                    # This matches what pose_service.detect_pose() does internally
                    height, width = frame.shape[:2]
                    original_size = f"{width}x{height}"
                    if width > config.image_width_limit:
                        scale = config.image_width_limit / width
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                        print(f"📐 Resized from {original_size} to {new_width}x{new_height}")
                else:
                    # Create dummy frame matching typical tablet aspect ratio (16:9)
                    # Resized to 640px width = 640x360
                    frame = np.zeros((360, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "No webcam - dummy frame", (50, 180),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(frame, "640x360 (tablet size)", (50, 220),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

                frame_count += 1
                print(f"\n🎬 Frame {frame_count} | Shape: {frame.shape}")

                # Use pose_service to detect keypoints
                keypoints = pose_service.detect_pose(frame)

                if keypoints is not None and len(keypoints) >= 17:
                    print(f"✅ Person detected! Keypoints shape: {keypoints.shape}")

                    # Visualize the pose
                    annotated_frame = draw_pose_on_frame(frame, keypoints,
                                                         min_confidence=config.min_confidence)

                    # Add frame info overlay
                    h, w = annotated_frame.shape[:2]
                    cv2.putText(annotated_frame, f"Frame: {frame_count} | {w}x{h} (tablet size)", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(annotated_frame, "Blue=Shoulders, Red=Wrists", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    cv2.putText(annotated_frame, "SPACE=Pause/Details, ESC=Quit", (10, 85),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

                    if use_webcam:
                        cv2.imshow('Pose Service Visualization', annotated_frame)
                else:
                    print("❌ No person detected in frame")
                    if use_webcam:
                        cv2.putText(frame, "No person detected", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        cv2.imshow('Pose Service Visualization', frame)

            # Handle keyboard input
            if use_webcam:
                key = cv2.waitKey(1) & 0xFF

                if key == 27:  # ESC
                    print("\n👋 Quitting...")
                    break
                elif key == 32:  # SPACE
                    paused = not paused
                    if paused and keypoints is not None:
                        print("\n⏸️  PAUSED - Detailed keypoint information:")
                        print_keypoint_info(keypoints)
                        print("\nPress SPACE to resume...")
                    else:
                        print("\n▶️  Resumed")
            else:
                # In dummy mode, just run a few iterations
                if frame_count >= 3:
                    print("\n✅ Dummy mode test complete!")
                    break
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user (Ctrl+C)")

    finally:
        if use_webcam:
            cap.release()
            cv2.destroyAllWindows()
        print("\n" + "=" * 70)
        print(f"📊 Test Summary: Processed {frame_count} frames")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  POSE SERVICE VISUALIZATION TEST")
    print("  Educational demonstration of pose detection and skeleton drawing")
    print("=" * 70)

    try:
        asyncio.run(test_pose_service_visualization())
        print("\n✅ Test completed successfully!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
