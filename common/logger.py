import logging
import sys
from .config import LOG_LEVEL, LOG_FORMAT

def get_logger(name):
    """Get a configured logger instance"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # File handler
        file_handler = logging.FileHandler('pcs.log')
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
        
        # Prevent duplicate logs
        logger.propagate = False
    
    return logger

def log_system_status(logger, message, level='info'):
    """Log system status with consistent formatting"""
    formatted_message = f"[SYSTEM] {message}"
    getattr(logger, level.lower())(formatted_message)