## Project Overview

AI Pull-Up Coach is a real-time fitness application that uses computer vision to count pull-up repetitions. The system consists of:
- **Backend**: FastAPI server running YOLOv8 pose estimation model (Python)
- **Frontend**: Android app with camera feed and real-time analysis (Kotlin + Jetpack Compose)

The backend processes video frames from the Android camera, detects body keypoints, analyzes pull-up motion patterns, and returns rep counts.

## Architecture

### Backend (Python/FastAPI)

**Core Components:**
- `main.py`: FastAPI application with CORS, endpoints for frame analysis, session management, and status checks (709 lines)
- `config.py`: Configuration with three debug modes (debug with frame saving, debug without saving, non-debug)
- `run.py`: Uvicorn server launcher with command-line arguments

**Services:**
- `pose_service.py`: YOLO pose model wrapper that detects 17 body keypoints per frame
- `debug_service.py`: Debug frame saving with visual overlays (only when `save_frames=True`)
  - Saves frames with timestamp: `frame_{num}_diff_{val}_reps_{count}_{timestamp}.jpg`

**Models:**
- `pull_up_counter.py`: **PullUpCounter** - Stateful rep counting logic using direction change detection (502 lines)
  - Tracks wrist-to-shoulder vertical distance over time
  - Detects DOWN→UP motion patterns with hysteresis to prevent false positives
  - Uses configurable thresholds: movement_threshold (8px), min_movement_range (30px), rep_cooldown (2s)
  - Maintains position history (30 frames) and direction history (10 transitions)

**Utils:**
- `logging_utils.py`: Logging configuration for different debug modes
- `keypoint_utils.py`: **Critical utility** for keypoint extraction and processing
  - `extract_shoulder_wrist_keypoints()`: Extracts specific keypoints from YOLO output
  - `calculate_wrist_shoulder_diff()`: Calculates vertical distance metric for rep detection
  - Keypoint index constants: LEFT_SHOULDER=5, RIGHT_SHOULDER=6, LEFT_WRIST=9, RIGHT_WRIST=10

**Test:**
- `test/test_pose_service_visualization.py`: Educational test script (292 lines) demonstrating:
  - Webcam integration for testing pose detection
  - Real-time keypoint visualization
  - Pose skeleton drawing
  - Useful for learning and debugging the pose detection system

**Model File:**
- `yolov8n-pose.pt`: YOLOv8 nano pose estimation model (6.8 MB, must be present in backend/)

**Dependencies (requirements.txt):**
```
fastapi==0.116.1
uvicorn[standard]==0.35.0
opencv-python==4.12.0.88
numpy==2.2.6
ultralytics==8.3.191
requests==2.32.5
python-multipart==0.0.20
```

### Frontend (Kotlin/Android)

**Architecture Pattern:** MVVM with Jetpack Compose + Coroutines

**Main Entry Point:**
- `MainActivity.kt`: Main Android activity handling:
  - Landscape orientation enforcement
  - Fullscreen immersive mode
  - Camera lifecycle management
  - ViewModel initialization

**Configuration:**
- `config/AppConfig.kt`: Centralized configuration for backend URL
  - `backendUrl`: Configurable backend server address (default: `http://192.168.1.8:8000/`)
  - Automatically ensures URL ends with `/`

**ViewModels & State:**
- `ui/viewmodels/WorkoutViewModels.kt`: Manages workout state, frame analysis requests, network error handling (208 lines)
  - Frame throttling (5 FPS via CameraHelper)
  - Network resilience: max 5 consecutive failures before retry delay (5s)
  - Connection status tracking
  - Error message handling with dismissal
- `ui/viewmodels/WorkoutState.kt`: Immutable state data class with fields:
  - `repCount`: Current rep count
  - `status`: Current workout status (e.g., "ready", "pulling_up", "lowering_down")
  - `isWorkoutActive`: Whether workout session is active
  - `isConnected`: Backend connection status
  - `errorMessage`: Current error message (if any)
  - `framesSent`: Debug counter for frames sent
  - `lastRepTime`: Timestamp of last counted rep

**UI Components:**
- `ui/screens/WorkoutScreen.kt`: Main workout interface composable (107 lines)
  - Combined Start/Reset button (starts when idle, resets when active)
  - Connection status indicator
  - Rep counter display
  - Error message cards with dismissal
- `ui/components/CameraComponents.kt`: CameraX integration for frame capture (148 lines)
- `ui/components/UIComponents.kt`: Reusable UI elements (243 lines)

**Theme:**
- `ui/theme/Color.kt`: App color palette
- `ui/theme/Theme.kt`: Material theme configuration
- `ui/theme/Type.kt`: Typography definitions

**Network & Camera:**
- `utils/ApiService.kt`: Retrofit interface for backend communication
  - Uses `AppConfig.backendUrl` for dynamic configuration
  - Endpoints: `/analyze_frame`, `/status`, `/reset_session`
- `utils/CameraHelper.kt`: **Core camera implementation** (163 lines)
  - CameraX integration with RGBA output format
  - Frame throttling: 5 FPS (200ms intervals)
  - JPEG conversion with 70% quality
  - Frame size validation (max 400KB)
  - Backpressure strategy for high-frequency capture

**Network Flow:**
1. CameraHelper captures frames at 5 FPS → converts to JPEG bytes (70% quality)
2. `WorkoutViewModels.analyzeFrame()` sends multipart request to `/analyze_frame`
3. Backend returns `{rep_count, position, timestamp}`
4. UI updates reactively via StateFlow
5. On connection failure: tracks consecutive failures, shows error message, implements retry delay

**Build Configuration:**
- compileSdk: 36
- minSdk: 28 (Android 9.0)
- targetSdk: 36
- Kotlin JVM target: 17
- Release build: Minification + ProGuard optimization enabled

**Permissions (AndroidManifest.xml):**
- `CAMERA`: Required for camera access (requested at runtime)
- `INTERNET`: Required for backend communication
- `ACCESS_NETWORK_STATE`: For connection status monitoring
- `usesCleartextTraffic="true"`: Allows HTTP connections (required for local development)

## Set up Guide

### Backend Development

```bash
# Setup virtual environment (first time)
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backend server (different modes)
python run.py --mode debug          # Debug with frame saving to debug_frames/
python run.py --mode debug_no_save  # Debug logging without saving frames
python run.py --mode non_debug      # Minimal logging (production)

# Default port: 8000
# Endpoints: /analyze_frame (POST), /status (GET), /reset_session (POST), /debug (GET)

# Run test visualization script (requires webcam)
cd backend
python test/test_pose_service_visualization.py
```

### Frontend Development

Download Android Studio and open the frontend folder, wait for the IDE to sync itself and then build the application.

## Development Notes

### Backend Configuration

The `config.py` file contains critical thresholds for pull-up detection:
- `min_confidence`: 0.3 - Minimum keypoint confidence to process frame
- `rep_cooldown`: 2.0 seconds - Prevents double-counting reps
- `min_consecutive_frames`: 3 - Frames required to confirm direction change
- `movement_threshold`: 8 pixels - Minimum movement to detect direction
- `min_movement_range`: 30 pixels - Total vertical range required for valid rep
- `model_conf_threshold`: 0.4 - YOLO detection confidence threshold
- `image_width_limit`: 640 - Frame resizing limit for performance

**When tuning rep detection**, modify these values in `config.py` and test with different body types/camera angles.

### Android Network Configuration

**CRITICAL**: Update backend URL in `frontend/app/src/main/java/vinh/nguyen/app/config/AppConfig.kt`:
```kotlin
object AppConfig {
    var backendUrl: String = "http://YOUR_LAPTOP_IP:8000/" # using ipconfig with ipv4
        set(value) {
            field = if (value.endsWith("/")) value else "$value/"
        }
}
```

The backend URL is centrally managed in `AppConfig.kt` and used by `ApiService.kt` dynamically. This allows runtime configuration changes if needed.

**Network Requirements:**
- Backend server and Android device must be on same WiFi network
- Backend server must be accessible via HTTP (cleartext traffic enabled in manifest)
- Connection resilience: App retries after 5 consecutive failures with 5-second delay

### Rep Counting Logic

The pull-up detection algorithm in `PullUpCounter`:
1. Uses `keypoint_utils.extract_shoulder_wrist_keypoints()` to get wrist/shoulder positions
2. Calculates `wrist_y - shoulder_y` for vertical position using `calculate_wrist_shoulder_diff()`
3. Maintains sliding window of positions to detect movement direction
4. Requires 3 consecutive frames to confirm direction change (reduces noise)
5. Counts a rep only when detecting DOWN→UP sequence with sufficient range (30px+)
6. Enforces 2-second cooldown between reps

**Common issues:**
- False negatives: Decrease `min_movement_range` or `movement_threshold`
- False positives: Increase `rep_cooldown` or `min_consecutive_frames`

### Debug Mode Frame Saving

When running backend with `--mode debug`, frames are saved to `backend/debug_frames/` with overlay annotations showing:
- Frame number
- Wrist-shoulder diff value
- Current position (pulling_up/lowering_down/stable)
- Rep count
- Timestamp in filename: `frame_{num}_diff_{val}_reps_{count}_{timestamp}.jpg`

Use this to diagnose detection issues by reviewing saved frames.

### Camera Configuration

The camera capture in `CameraHelper.kt` is optimized for performance:
- **Frame Rate**: 5 FPS (200ms intervals) to reduce network load
- **Format**: RGBA from CameraX, converted to JPEG at 70% quality
- **Size Limit**: 400KB max per frame
- **Backpressure**: Drops frames if previous analysis hasn't completed

Adjust these values in `CameraHelper.kt` if you need different performance characteristics:
- Increase FPS for smoother detection (higher network load)
- Increase JPEG quality for better accuracy (larger frames)
- Decrease frame limit for faster networks

### Testing Network Connection

Test backend from Android device:
1. Start backend: `python run.py`
2. Note the IP address of your machine (use `ipconfig` on Windows or `ifconfig` on Linux/Mac)
3. Test with curl: `curl http://YOUR_IP:8000/status`
4. Update `backendUrl` in `AppConfig.kt` to match
5. In Android app, connection status indicator shows green when connected
6. If connection fails, check:
   - Both devices on same WiFi
   - Firewall allows port 8000
   - Backend server is running
   - IP address is correct in AppConfig.kt

### Educational Resources

For learning the codebase:
- **test_pose_service_visualization.py**: Interactive webcam script showing pose detection in real-time
- **LEARNING_ROADMAP.md**: Comprehensive 4-week learning guide with day-by-day activities
- **keypoint_utils.py**: Reference for YOLO keypoint indices and extraction logic

### Network Resilience Features

The app includes robust error handling:
- **Consecutive Failure Tracking**: Monitors up to 5 consecutive failures
- **Retry Delay**: 5-second delay after max failures reached
- **Connection Status**: Real-time indicator in UI
- **Error Messages**: Dismissible error cards for user feedback
- **Graceful Degradation**: App continues running even if backend disconnects

### File Structure Reference

```
AI_Pull_Up_Coach/
├── backend/
│   ├── main.py                     # FastAPI application (709 lines)
│   ├── config.py                   # Configuration & thresholds (73 lines)
│   ├── run.py                      # Server launcher (27 lines)
│   ├── requirements.txt            # Python dependencies
│   ├── yolov8n-pose.pt            # YOLO model (6.8 MB)
│   ├── models/
│   │   └── pull_up_counter.py     # Rep counting algorithm (502 lines)
│   ├── services/
│   │   ├── pose_service.py        # YOLO wrapper (70 lines)
│   │   └── debug_service.py       # Frame visualization (179 lines)
│   ├── utils/
│   │   ├── logging_utils.py       # Logging config (27 lines)
│   │   └── keypoint_utils.py      # Keypoint extraction (98 lines)
│   ├── test/
│   │   └── test_pose_service_visualization.py  # Educational webcam test (292 lines)
│   └── debug_frames/              # Created when --mode debug
│
└── frontend/app/src/main/java/vinh/nguyen/app/
    ├── MainActivity.kt             # App entry point (105 lines)
    ├── config/
    │   └── AppConfig.kt           # Backend URL configuration (31 lines)
    ├── ui/
    │   ├── screens/
    │   │   └── WorkoutScreen.kt   # Main UI (107 lines)
    │   ├── components/
    │   │   ├── CameraComponents.kt # Camera integration (148 lines)
    │   │   └── UIComponents.kt     # Reusable components (243 lines)
    │   ├── viewmodels/
    │   │   ├── WorkoutViewModels.kt # State management (208 lines)
    │   │   └── WorkoutState.kt      # State data class (14 lines)
    │   └── theme/
    │       ├── Color.kt            # Color palette
    │       ├── Theme.kt            # Theme config
    │       └── Type.kt             # Typography
    └── utils/
        ├── ApiService.kt           # Retrofit API (59 lines)
        └── CameraHelper.kt         # Camera implementation (163 lines)
```
