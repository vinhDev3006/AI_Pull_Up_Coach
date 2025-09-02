import logging
from config import config

def setup_logging():
    """Setup logging based on debug mode"""
    if config.debug_mode == "non_debug":
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)
    
    logger = logging.getLogger("pullup_coach")
    return logger

# Global logger instance
logger = setup_logging()