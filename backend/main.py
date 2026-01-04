"""
FastAPI backend server for AI Pull-Up Coach.

OVERVIEW:
=========
This module provides the REST API server for real-time pull-up detection and counting.
It receives video frames from Android clients, processes them using YOLOv8 pose estimation,
and returns rep counts with real-time feedback.

ARCHITECTURE:
=============
┌─────────────┐         ┌──────────────┐         ┌─────────────────┐
│   Android   │  JPEG   │   FastAPI    │  Numpy  │  YOLOv8 Pose    │
│   Camera    ├────────>│   Endpoint   ├────────>│    Detection    │
│             │<────────┤  /analyze    │<────────┤                 │
└─────────────┘  JSON   └──────────────┘ Keypts  └─────────────────┘
                                │
                                │ Keypoints (17 x 3)
                                v
                        ┌──────────────┐
                        │  Pull-Up     │
                        │  Counter     │
                        │  (Stateful)  │
                        └──────────────┘

ENDPOINTS:
==========
POST /analyze_frame
    - Primary endpoint for frame-by-frame analysis
    - Accepts: Multipart JPEG image from camera
    - Returns: {rep_count, status, timestamp, debug_info}
    - Stateful: Maintains session across frames for rep counting

POST /reset_session
    - Resets workout session (clears rep count and history)
    - Accepts: No parameters
    - Returns: {status, message, timestamp, session_id}

GET /status
    - Health check and server status
    - Returns: {status, model_loaded, mode, saving_frames, timestamp}

GET /debug
    - Detailed debug information (debug modes only)
    - Returns: Session state, frame counts, saved frame info

DATA FLOW:
==========
1. Android app captures camera frame (640x480 JPEG)
2. HTTP POST to /analyze_frame with multipart/form-data
3. Backend decodes JPEG → NumPy array → OpenCV BGR
4. YOLOv8 detects 17 body keypoints (shoulders, wrists, etc.)
5. PullUpCounter analyzes keypoint motion over time
6. Response sent back with rep count and status
7. Optional: Debug frame saved with pose overlay

SESSION MANAGEMENT:
===================
Sessions are stored in-memory with a simple dictionary:
- Key: session_id (currently "default" for single-user)
- Value: PullUpCounter instance (maintains state across frames)
- Lifetime: Until server restart or explicit reset
- Simple and easy to understand for learning purposes

DEBUG MODES:
============
Three operational modes (configured via --mode flag):
- DEBUG: Full logging + frame saving to debug_frames/ (best for learning/debugging)
- DEBUG_NO_SAVE: Full logging without frame saving (saves disk space)
- NON_DEBUG: Minimal logging (for testing performance without debug overhead)

PERFORMANCE NOTES:
==================
- Target: ~30 FPS frame processing (plenty fast for development/testing)
- YOLOv8n model: ~10-20ms inference on CPU
- Total latency: ~30-50ms per frame (including network)
- Good enough for real-time feedback during workouts

Usage:
    python run.py [--mode debug|debug_no_save|non_debug]
"""

import cv2
import numpy as np
import time
from typing import Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import config, DebugMode
from utils.logging_utils import logger
from utils.keypoint_utils import extract_shoulder_wrist_keypoints, calculate_wrist_shoulder_diff
from services.pose_service import pose_service
from services.debug_service import debug_service
from models.pull_up_counter import PullUpCounter

# ============================================================================
# CONFIGURATION AND CONSTANTS
# ============================================================================

# Initialize configuration from command-line arguments
config.setup_from_args()

# Log the selected operational mode
logger.info(f"🚀 Starting in: {config.mode_description}")

# Constants for clarity
DEFAULT_SESSION_ID = "default"  # Session identifier (single-user for now)
LATEST_FRAMES_COUNT = 5  # Number of recent frames to show in debug endpoint
DEFAULT_DIFF_VALUE = 0.0  # Default wrist-shoulder diff when keypoints unavailable

# HTTP status codes
HTTP_BAD_REQUEST = 400
HTTP_INTERNAL_ERROR = 500

# Response keys (for consistency)
KEY_REP_COUNT = "rep_count"
KEY_STATUS = "status"
KEY_TIMESTAMP = "timestamp"
KEY_DEBUG = "debug"
KEY_FRAME_COUNT = "frame_count"
KEY_MODE = "mode"
KEY_SAVING_FRAMES = "saving_frames"
KEY_DEBUG_DIR = "debug_dir"
KEY_MESSAGE = "message"
KEY_SESSION_ID = "session_id"

# ============================================================================
# GLOBAL STATE
# ============================================================================

# Global workout sessions storage (in-memory)
# Maps session_id -> PullUpCounter instance
# Simple dictionary works great for single-user development/testing
workout_sessions: Dict[str, PullUpCounter] = {}

# ============================================================================
# APPLICATION SETUP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.

    STARTUP PHASE:
    - Load YOLOv8 pose estimation model into memory
    - Initialize pose detection service
    - Validate model file exists and loads correctly

    SHUTDOWN PHASE:
    - Currently no cleanup needed (model auto-releases)
    - Sessions are discarded on shutdown (development/testing only)

    Args:
        app: FastAPI application instance

    Yields:
        Control to the running application

    Raises:
        Exception if model fails to load (will prevent server startup)
    """
    # Startup: Initialize the pose service
    logger.info("Initializing pose detection service...")
    await pose_service.initialize()
    logger.info("Pose service initialized successfully")

    yield

    # Shutdown: Add cleanup code here if needed in the future
    logger.info("Shutting down server...")

# Create FastAPI application instance
app = FastAPI(
    title=f"AI Pull-Up Coach Backend - {config.mode_description}",
    description="Real-time pull-up detection and counting using YOLOv8 pose estimation",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS middleware for cross-origin requests
# This allows the Android app to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accept requests from any origin (Android app)
    allow_credentials=True,  # Allow cookies and authentication headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"]  # Allow all headers
)

# ============================================================================
# HELPER FUNCTIONS FOR FRAME ANALYSIS
# ============================================================================

def _decode_image_from_upload(contents: bytes) -> np.ndarray:
    """
    Decode uploaded JPEG bytes into OpenCV image format.

    The Android app sends JPEG-encoded frames via multipart/form-data.
    This function converts the raw bytes into a NumPy array suitable for OpenCV.

    Args:
        contents: Raw JPEG bytes from uploaded file

    Returns:
        np.ndarray: Decoded image in BGR format (OpenCV standard)

    Raises:
        HTTPException: If image decoding fails (corrupt/invalid JPEG)
    """
    # Convert bytes to NumPy array
    nparr = np.frombuffer(contents, np.uint8)

    # Decode JPEG into BGR image
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(
            status_code=HTTP_BAD_REQUEST,
            detail="Invalid image: Unable to decode JPEG data"
        )

    # Convert RGB to BGR for OpenCV compatibility
    # NOTE: Android JPEG may be in RGB format, but OpenCV expects BGR
    # This ensures correct color representation in debug frames
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    return img


def _get_or_create_session(session_id: str) -> PullUpCounter:
    """
    Retrieve existing workout session or create a new one.

    Sessions maintain state across frames (rep count, motion history, etc.).
    Each session is identified by a unique session_id.

    Args:
        session_id: Unique identifier for the workout session

    Returns:
        PullUpCounter: The session's counter instance
    """
    if session_id not in workout_sessions:
        logger.info(f"Creating new workout session: {session_id}")
        workout_sessions[session_id] = PullUpCounter()

    return workout_sessions[session_id]


def _calculate_debug_diff(keypoints: Optional[np.ndarray]) -> float:
    """
    Calculate wrist-shoulder difference for debug logging.

    This extracts the same metric used by the counter for debugging purposes.
    The value helps diagnose detection issues and threshold tuning.

    Args:
        keypoints: Detected body keypoints (or None if no person)

    Returns:
        float: Vertical wrist-shoulder difference, or 0.0 if unavailable
    """
    if keypoints is None:
        return DEFAULT_DIFF_VALUE

    # Extract shoulder and wrist keypoints
    left_shoulder, right_shoulder, left_wrist, right_wrist, min_conf = \
        extract_shoulder_wrist_keypoints(keypoints)

    if left_shoulder is None:
        return DEFAULT_DIFF_VALUE

    # Calculate the vertical difference metric
    diff = calculate_wrist_shoulder_diff(
        left_shoulder, right_shoulder, left_wrist, right_wrist
    )

    return diff


def _log_frame_analysis(counter: PullUpCounter, diff: float, status: str) -> None:
    """
    Log frame analysis details (debug modes only).

    Provides detailed per-frame logging for troubleshooting and monitoring.
    Only active in DEBUG and DEBUG_NO_SAVE modes.

    Args:
        counter: The workout session counter
        diff: Wrist-shoulder vertical difference
        status: Current motion status
    """
    if config.debug_mode != DebugMode.NON_DEBUG:
        logger.info(
            f"Frame {counter.frame_count}: Diff {diff:.1f} | "
            f"{status.upper()} | Reps: {counter.count} | "
            f"Direction: {counter.current_direction}"
        )


def _build_response_data(
    rep_count: int,
    status: str,
    counter: Optional[PullUpCounter] = None
) -> Dict[str, Any]:
    """
    Build the JSON response for the /analyze_frame endpoint.

    Constructs a standardized response with rep count, status, and optional debug info.

    Args:
        rep_count: Current rep count for this session
        status: Current motion status (pulling_up, lowering_down, etc.)
        counter: Optional counter instance for debug info

    Returns:
        Dict containing response data ready for JSON serialization

    Response structure:
        {
            "rep_count": int,
            "status": str,
            "timestamp": float,
            "debug": {  # Only in debug modes
                "frame_count": int,
                "mode": str,
                "saving_frames": bool,
                "debug_dir": str  # Only if saving frames
            }
        }
    """
    response_data = {
        KEY_REP_COUNT: rep_count,
        KEY_STATUS: status,
        KEY_TIMESTAMP: time.time()
    }

    # Add debug information in debug modes
    if config.debug_mode != DebugMode.NON_DEBUG and counter is not None:
        debug_info = {
            KEY_FRAME_COUNT: counter.frame_count,
            KEY_MODE: config.debug_mode,
            KEY_SAVING_FRAMES: config.save_frames
        }

        # Include debug directory path if saving frames
        if config.save_frames and config.debug_dir:
            debug_info[KEY_DEBUG_DIR] = str(config.debug_dir.absolute())

        response_data[KEY_DEBUG] = debug_info

    return response_data


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/analyze_frame")
async def analyze_frame(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Analyze a single video frame for pull-up detection.

    PRIMARY ENDPOINT for real-time pull-up counting. Receives a JPEG frame from
    the Android camera, processes it through the pose detection pipeline, and
    returns the current rep count with motion status.

    PROCESSING PIPELINE:
    1. Decode JPEG bytes to OpenCV image
    2. Get or create workout session (maintains state)
    3. Run YOLOv8 pose detection (detect 17 body keypoints)
    4. Analyze keypoints with PullUpCounter (direction detection + rep counting)
    5. Save debug frame with pose overlay (if enabled)
    6. Return rep count and status to client

    Args:
        file: Uploaded JPEG image (multipart/form-data)
              Expected size: ~640x480 pixels
              Expected format: JPEG compressed

    Returns:
        Dict containing:
            - rep_count (int): Total reps counted in this session
            - status (str): Current motion state
                Values: "pulling_up", "lowering_down", "stable",
                       "no_person", "low_confidence"
            - timestamp (float): Server timestamp
            - debug (dict, optional): Debug info if in debug mode

    Raises:
        HTTPException 400: Invalid image data (corrupt JPEG)
        HTTPException 500: Model not loaded or processing error

    Example response:
        {
            "rep_count": 5,
            "status": "pulling_up",
            "timestamp": 1609459200.0,
            "debug": {
                "frame_count": 150,
                "mode": "debug",
                "saving_frames": true,
                "debug_dir": "/path/to/debug_frames"
            }
        }
    """
    # Verify pose detection model is loaded
    if not pose_service.model:
        raise HTTPException(
            status_code=HTTP_INTERNAL_ERROR,
            detail="Pose detection model not loaded"
        )

    try:
        # Step 1: Decode uploaded JPEG into OpenCV format
        contents = await file.read()
        img = _decode_image_from_upload(contents)

        # Step 2: Get or create workout session for this user
        counter = _get_or_create_session(DEFAULT_SESSION_ID)
        counter.frame_count += 1

        # Step 3: Run pose detection on the frame
        keypoints = pose_service.detect_pose(img)

        # Step 4: Analyze pose and update rep count
        if keypoints is not None:
            # Person detected - analyze motion
            rep_count, status = counter.analyze_pose(keypoints)

            # Calculate wrist-shoulder diff for debugging
            diff = _calculate_debug_diff(keypoints)

            # Save debug frame with pose visualization (if enabled)
            debug_service.save_debug_frame(
                contents, counter.frame_count, diff, status, rep_count, keypoints
            )

            # Log frame details (debug modes only)
            _log_frame_analysis(counter, diff, status)

        else:
            # No person detected in frame
            rep_count = counter.count
            status = "no_person"

            # Save debug frame even when no person detected
            if config.save_frames:
                debug_service.save_debug_frame(
                    contents, counter.frame_count, DEFAULT_DIFF_VALUE,
                    status, rep_count, None
                )

        # Step 5: Build and return response
        return _build_response_data(rep_count, status, counter)

    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        raise

    except Exception as e:
        # Log unexpected errors and return 500
        logger.error(f"Error processing frame: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_ERROR,
            detail=f"Frame processing failed: {str(e)}"
        )

@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get server status and configuration information.

    HEALTH CHECK ENDPOINT for monitoring server availability and configuration.
    Used by clients to verify the backend is running and ready to process frames.

    This endpoint is lightweight and can be called frequently without performance impact.
    It does not require any authentication or session state.

    Returns:
        Dict containing:
            - status (str): Server operational status (always "online" if responding)
            - model_loaded (bool): Whether YOLOv8 pose model is loaded and ready
            - mode (str): Current debug mode (debug/debug_no_save/non_debug)
            - mode_description (str): Human-readable mode description
            - saving_frames (bool): Whether debug frames are being saved to disk
            - timestamp (float): Server timestamp
            - debug_frames_saved (int, optional): Count of saved frames (if saving enabled)
            - debug_directory (str, optional): Path to debug frames (if saving enabled)

    Example response (debug mode with frame saving):
        {
            "status": "online",
            "model_loaded": true,
            "mode": "debug",
            "mode_description": "Debug Mode (with frame saving)",
            "saving_frames": true,
            "timestamp": 1609459200.0,
            "debug_frames_saved": 247,
            "debug_directory": "/path/to/backend/debug_frames"
        }

    Example response (non-debug mode):
        {
            "status": "online",
            "model_loaded": true,
            "mode": "non_debug",
            "mode_description": "Non-Debug Mode (minimal logging)",
            "saving_frames": false,
            "timestamp": 1609459200.0
        }
    """
    # Build basic status response
    response_data = {
        KEY_STATUS: "online",
        "model_loaded": pose_service.model is not None,
        KEY_MODE: config.debug_mode,
        "mode_description": config.mode_description,
        KEY_SAVING_FRAMES: config.save_frames,
        KEY_TIMESTAMP: time.time()
    }

    # Add debug frame statistics if saving frames
    if config.save_frames and config.debug_dir:
        # Count saved debug frames in the directory
        frame_files = list(config.debug_dir.glob("frame_*.jpg"))
        response_data.update({
            "debug_frames_saved": len(frame_files),
            "debug_directory": str(config.debug_dir.absolute())
        })

    return response_data

@app.post("/reset_session")
async def reset_session() -> Dict[str, Any]:
    """
    Reset the workout session to start a fresh workout.

    SESSION RESET ENDPOINT for clearing all workout state and starting over.
    Called by the Android app when the user wants to begin a new workout session.

    WHAT GETS RESET:
    - Rep count → 0
    - Motion status → neutral
    - Position history → cleared (30-frame sliding window)
    - Direction history → cleared (pattern detection memory)
    - Direction state → stable
    - Consecutive frame counters → 0
    - Rep cooldown timer → 0
    - Frame counter → 0

    This is equivalent to creating a fresh PullUpCounter instance.
    The old session data is discarded and garbage collected.

    NOTE: Debug frames saved to disk are NOT deleted. They persist until
    manually deleted or the debug_frames/ directory is cleared.

    Returns:
        Dict containing:
            - status (str): Always "success" if reset completes
            - message (str): Human-readable success message
            - timestamp (float): Server timestamp when reset occurred
            - session_id (str): The session that was reset (currently "default")

    Raises:
        HTTPException 500: If session reset fails (rare, indicates server issue)

    Example response:
        {
            "status": "success",
            "message": "Workout session reset successfully",
            "timestamp": 1609459200.0,
            "session_id": "default"
        }

    Example usage from Android:
        User taps "New Workout" button
        → POST /reset_session
        → Response confirms reset
        → UI displays 0 reps, neutral status
    """
    try:
        session_id = DEFAULT_SESSION_ID

        # Create a fresh counter instance (replaces existing session)
        # This discards all accumulated state from the previous workout
        workout_sessions[session_id] = PullUpCounter()

        logger.info(f"Session '{session_id}' reset successfully")

        return {
            KEY_STATUS: "success",
            KEY_MESSAGE: "Workout session reset successfully",
            KEY_TIMESTAMP: time.time(),
            KEY_SESSION_ID: session_id
        }

    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        raise HTTPException(
            status_code=HTTP_INTERNAL_ERROR,
            detail=f"Failed to reset session: {str(e)}"
        )

@app.get("/debug")
async def debug() -> Dict[str, Any]:
    """
    Get detailed debug information about the current workout session.

    DEBUG INSPECTION ENDPOINT for troubleshooting and monitoring session state.
    Provides detailed internal state of the PullUpCounter and debug configuration.

    This endpoint is useful for:
    - Verifying rep counting algorithm state
    - Checking frame processing progress
    - Inspecting saved debug frames
    - Diagnosing detection issues
    - Learning how the state machine works

    Returns:
        Dict containing session state and debug info:
            - count (int): Current rep count
            - status (str): Current motion status
            - current_direction (str): Direction state machine value (up/down/stable)
            - frame_count (int): Total frames processed in this session
            - mode (str): Debug mode configuration
            - saving_frames (bool): Whether frames are being saved
            - debug_frames_saved (int, optional): Count of saved frames
            - debug_directory (str, optional): Path to saved frames
            - latest_frames (list, optional): Names of 5 most recent saved frames

        If no session exists:
            - message (str): "No session found"
            - mode (str): Current debug mode

    Example response (with active session):
        {
            "count": 7,
            "status": "pulling_up",
            "current_direction": "up",
            "frame_count": 342,
            "mode": "debug",
            "saving_frames": true,
            "debug_frames_saved": 342,
            "debug_directory": "/path/to/backend/debug_frames",
            "latest_frames": [
                "frame_0338.jpg",
                "frame_0339.jpg",
                "frame_0340.jpg",
                "frame_0341.jpg",
                "frame_0342.jpg"
            ]
        }

    Example response (no session):
        {
            "message": "No session found",
            "mode": "debug"
        }

    Example usage:
        Use during development to verify:
        - Rep counting is working correctly
        - Frames are being saved as expected
        - Direction detection is responding to movement
    """
    session_id = DEFAULT_SESSION_ID

    # Check if a workout session exists
    if session_id in workout_sessions:
        counter = workout_sessions[session_id]

        # Build basic debug response with session state
        response_data = {
            "count": counter.count,
            KEY_STATUS: counter.status,
            "current_direction": counter.current_direction,
            KEY_FRAME_COUNT: counter.frame_count,
            KEY_MODE: config.debug_mode,
            KEY_SAVING_FRAMES: config.save_frames
        }

        # Add debug frame information if saving frames
        if config.save_frames and config.debug_dir:
            # Get all saved frame files
            frame_files = list(config.debug_dir.glob("frame_*.jpg"))

            # Sort by filename to get chronological order
            sorted_frames = sorted(frame_files)

            # Get the 5 most recent frames
            latest_frames = sorted_frames[-LATEST_FRAMES_COUNT:] if sorted_frames else []

            response_data.update({
                "debug_frames_saved": len(frame_files),
                "debug_directory": str(config.debug_dir.absolute()),
                "latest_frames": [f.name for f in latest_frames]
            })

        return response_data

    # No session found - return minimal info
    return {
        KEY_MESSAGE: "No session found",
        KEY_MODE: config.debug_mode
    }