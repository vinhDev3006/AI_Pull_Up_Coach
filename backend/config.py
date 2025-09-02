import argparse
from pathlib import Path
from typing import Optional

class Config:
    """Application configuration"""
    
    def __init__(self):
        self.debug_mode: str = "debug"
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
        self.mode_descriptions = {
            "debug": "Debug Mode (with frame saving)",
            "debug_no_save": "Debug Mode (without frame saving)", 
            "non_debug": "Non-Debug Mode (minimal logging)"
        }
    
    def setup_from_args(self):
        """Parse command line arguments and setup configuration"""
        parser = argparse.ArgumentParser(description="AI Pull-Up Coach Backend")
        parser.add_argument(
            "--mode", 
            choices=["debug", "debug_no_save", "non_debug"],
            default="debug",
            help="Debug mode: 'debug' (save frames), 'debug_no_save' (no frame saving), 'non_debug' (minimal logging)"
        )
        args = parser.parse_args()
        
        self.debug_mode = args.mode
        self.save_frames = (self.debug_mode == "debug")
        
        # Create debug directory only if saving frames
        if self.save_frames:
            self.debug_dir = Path("debug_frames")
            self.debug_dir.mkdir(exist_ok=True)
    
    @property
    def mode_description(self) -> str:
        return self.mode_descriptions[self.debug_mode]

# Global config instance
config = Config()