"""
Logging configuration and utilities.

This module sets up the application-wide logging configuration based on
the selected debug mode. It creates and configures the global logger
instance used throughout the application.

Logging levels by mode:
    - DEBUG/DEBUG_NO_SAVE: INFO level (detailed operation logs)
    - NON_DEBUG: WARNING level (errors and warnings only)
"""

import logging
from config import config, DebugMode

def setup_logging() -> logging.Logger:
    """Setup logging based on debug mode"""
    if config.debug_mode == DebugMode.NON_DEBUG:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)
    
    logger = logging.getLogger("pullup_coach")
    return logger

# Global logger instance
logger = setup_logging()