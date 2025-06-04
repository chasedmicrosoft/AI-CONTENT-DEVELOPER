"""
Core utilities for AI Content Developer
"""
import hashlib
from functools import wraps
from typing import Callable
import logging
import re
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

def extract_from_markdown_block(content: str) -> str:
    """Extract content from markdown code blocks.
    
    Simply removes the most common markdown fence patterns.
    For complex cases, the LLM will handle it naturally.
    """
    if not content:
        return content
    
    content = content.strip()
    
    # Check for common fence patterns
    if content.startswith('```') and content.endswith('```'):
        # Find first newline after opening fence
        first_newline = content.find('\n')
        if first_newline > 0:
            # Remove opening fence and closing fence
            return content[first_newline + 1:-3].strip()
    
    # Return as-is if no fence found
    return content 