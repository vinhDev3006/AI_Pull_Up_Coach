import cv2
import numpy as np
import time
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import config
from utils.logging_utils import logger
from utils.motivation import get_motivation_text
from services.pose_service import pose_service
from services.debug_service import debug_service
from models.pull_up_counter import FixedPullUpCounter

# Initialize configuration
config.setup_from_args()

# Log the selected mode
logger.info(f"🚀 Starting in: {config.mode_description}")

app = FastAPI(title=f"AI Pull-Up Coach Backend - {config.mode_description}")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Global workout sessions storage
workout_sessions = {}

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    await pose_service.initialize()

@app.post("/analyze_frame")
async def analyze_frame(file: UploadFile = File(...)):
    """Analyze a single frame for pull-up detection"""
    
    if not pose_service.model:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    try:
        # Read raw bytes for debug saving (if enabled)
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        # Get or create session
        session_id = "default"
        if session_id not in workout_sessions:
            workout_sessions[session_id] = FixedPullUpCounter()
        
        counter = workout_sessions[session_id]
        counter.frame_count += 1
        
        # Detect pose
        keypoints = pose_service.detect_pose(img)
        
        if keypoints is not None:
            rep_count, position = counter.analyze_pose(keypoints)
            
            # Calculate diff for debugging
            left_shoulder = keypoints[5]
            right_shoulder = keypoints[6]
            left_wrist = keypoints[9]
            right_wrist = keypoints[10]
            shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
            wrist_y = (left_wrist[1] + right_wrist[1]) / 2
            diff = wrist_y - shoulder_y
            
            # Save debug frame (only if enabled)
            debug_service.save_debug_frame(contents, counter.frame_count, diff, position, rep_count)
            
            # Log frame info based on debug mode
            if config.debug_mode in ["debug", "debug_no_save"]:
                logger.info(f"Frame {counter.frame_count}: Diff {diff:.1f} | "
                           f"{position.upper()} | Reps: {rep_count} | Direction: {counter.current_direction}")
                       
        else:
            rep_count, position = counter.count, "no_person"
            # Save debug frame even when no person detected (if enabled)
            if config.save_frames:
                debug_service.save_debug_frame(contents, counter.frame_count, 0.0, position, rep_count)
        
        motivation = get_motivation_text(rep_count)
        
        response_data = {
            "rep_count": rep_count,
            "position": position,
            "motivation": motivation,
            "timestamp": time.time()
        }
        
        # Only add debug info in debug modes
        if config.debug_mode != "non_debug":
            response_data["debug"] = {
                "frame_count": counter.frame_count,
                "mode": config.debug_mode,
                "saving_frames": config.save_frames
            }
            
            if config.save_frames:
                response_data["debug"]["debug_dir"] = str(config.debug_dir.absolute())
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    """Get application status"""
    response_data = {
        "status": "online",
        "model_loaded": pose_service.model is not None,
        "mode": config.debug_mode,
        "mode_description": config.mode_description,
        "saving_frames": config.save_frames,
        "timestamp": time.time()
    }
    
    # Add debug frame count only if saving frames
    if config.save_frames and config.debug_dir:
        frame_count = len(list(config.debug_dir.glob("frame_*.jpg")))
        response_data.update({
            "debug_frames_saved": frame_count,
            "debug_directory": str(config.debug_dir.absolute())
        })
    
    return response_data

@app.post("/reset_session")
async def reset_session():
    """Reset the workout session - clears rep count and position history"""
    try:
        session_id = "default"
        
        # Create a fresh counter instance
        workout_sessions[session_id] = FixedPullUpCounter()
        
        logger.info(f"Session {session_id} reset successfully")
        
        return {
            "status": "success",
            "message": "Workout session reset successfully",
            "timestamp": time.time(),
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset session: {str(e)}")

@app.get("/debug")
async def debug():
    """Get debug information about the current session"""
    session_id = "default"
    if session_id in workout_sessions:
        counter = workout_sessions[session_id]
        
        response_data = {
            "count": counter.count,
            "position": counter.position,
            "current_direction": counter.current_direction,
            "frame_count": counter.frame_count,
            "mode": config.debug_mode,
            "saving_frames": config.save_frames
        }
        
        if config.save_frames and config.debug_dir:
            frame_files = list(config.debug_dir.glob("frame_*.jpg"))
            response_data.update({
                "debug_frames_saved": len(frame_files),
                "debug_directory": str(config.debug_dir.absolute()),
                "latest_frames": [f.name for f in sorted(frame_files)[-5:]]
            })
        
        return response_data
    
    return {"message": "No session found", "mode": config.debug_mode}