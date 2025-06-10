"""
Core utilities for AI Content Developer
"""
import hashlib
from functools import wraps
from typing import Callable
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Hash generation for string content
get_hash = lambda content: hashlib.sha256(content.encode('utf-8')).hexdigest()

def error_handler(func: Callable) -> Callable:
    """
    Decorator to handle errors gracefully
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function that returns None on error
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            return None
    return wrapper

 