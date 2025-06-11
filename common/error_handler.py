import functools
import traceback
from common.logger import get_logger

logger = get_logger("ErrorHandler")

def handle_exceptions(func):
    """Decorator for consistent error handling"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    return wrapper

class PCSException(Exception):
    """Base exception for PCS application"""
    pass

class WorkerConnectionError(PCSException):
    """Raised when worker cannot connect to master"""
    pass

class TaskProcessingError(PCSException):
    """Raised when task processing fails"""
    pass

class MasterStartupError(PCSException):
    """Raised when master fails to start"""
    pass