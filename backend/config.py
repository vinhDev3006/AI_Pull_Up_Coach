"""
Application configuration management.

This module handles all configuration for the AI Pull-Up Coach backend,
including debug modes, detection thresholds, and command-line argument parsing.
All configuration is centralized in the Config class.

Debug Modes:
    - DEBUG: Full debugging with frame saving to debug_frames/
    - DEBUG_NO_SAVE: Debugging logs without saving frames
    - NON_DEBUG: Minimal logging for production use
"""

import argparse
from pathlib import Path
from typing import Optional, Dict
from enum import Enum


class DebugMode(str, Enum):
    """Debug mode configuration options."""
    DEBUG = "debug"
    DEBUG_NO_SAVE = "debug_no_save"
    NON_DEBUG = "non_debug"


class Config:
    """Application configuration"""
    
    def __init__(self):
        self.debug_mode: DebugMode = DebugMode.DEBUG
        self.save_frames: bool = False
        self.debug_dir: Optional[Path] = None
        self.min_confidence: float = 0.3
        self.rep_cooldown: float = 2.0
        self.min_consecutive_frames: int = 3
        self.movement_threshold: int = 8
        self.min_movement_range: int = 30
        self.image_width_limit: int = 640
        self.model_conf_threshold: float = 0.4

        # Mode descriptions
        self.mode_descriptions: Dict[DebugMode, str] = {
            DebugMode.DEBUG: "Debug Mode (with frame saving)",
            DebugMode.DEBUG_NO_SAVE: "Debug Mode (without frame saving)",
            DebugMode.NON_DEBUG: "Non-Debug Mode (minimal logging)"
        }
    
    def setup_from_args(self) -> None:
        """Parse command line arguments and setup configuration"""
        parser = argparse.ArgumentParser(description="AI Pull-Up Coach Backend")
        parser.add_argument(
            "--mode", 
            choices=["debug", "debug_no_save", "non_debug"],
            default="debug",
            help="Debug mode: 'debug' (save frames), 'debug_no_save' (no frame saving), 'non_debug' (minimal logging)"
        )
        args = parser.parse_args()

        self.debug_mode = DebugMode(args.mode)
        self.save_frames = (self.debug_mode == DebugMode.DEBUG)
        
        # Create debug directory only if saving frames
        if self.save_frames:
            self.debug_dir = Path("debug_frames")
            self.debug_dir.mkdir(exist_ok=True)
    
    @property
    def mode_description(self) -> str:
        return self.mode_descriptions[self.debug_mode]

# Global config instance
config = Config()