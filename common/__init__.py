# Password Cracking Simulator - Common Package
# This file makes the common directory a Python package

__version__ = "1.0.0"
__author__ = "PCS Team"

# Import commonly used functions for easier access
from .logger import get_logger, log_system_status
from .config import *

__all__ = [
    'get_logger',
    'log_system_status',
    'MASTER_URL',
    'MASTER_HOST', 
    'MASTER_PORT',
    'TASK_FETCH_INTERVAL',
    'TASK_BATCH_SIZE',
    'TASK_TIMEOUT'
]