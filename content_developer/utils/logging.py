"""
Logging configuration for AI Content Developer
"""
import logging
import sys
from pathlib import Path


def setup_logging(log_dir: str = "./logs") -> logging.Logger:
    """
    Setup logging configuration
    
    Note: This is deprecated. Use logging_config.py for dual console/file logging.
    
    Args:
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Configure logging - now just returns the logger without file handler
    # since logging_config.py handles the actual logging setup
    return logging.getLogger('ContentDeveloper') 