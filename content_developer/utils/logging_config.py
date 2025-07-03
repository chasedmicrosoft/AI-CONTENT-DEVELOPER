"""
Dual logging configuration for separating console and file output
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


# Global console instance for Rich output
console = Console()


class ConsoleFilter(logging.Filter):
    """Filter to only show WARNING and above on console"""
    def filter(self, record):
        # Only show warnings, errors, and critical messages on console
        # Plus any messages explicitly marked for console
        return (record.levelno >= logging.WARNING or 
                hasattr(record, 'console_only') and record.console_only)


class FileOnlyFilter(logging.Filter):
    """Filter to exclude console-only messages from file"""
    def filter(self, record):
        # Exclude messages marked as console-only from file
        return not (hasattr(record, 'console_only') and record.console_only)


def setup_dual_logging(log_file: Optional[str] = None, console_level: str = "WARNING") -> None:
    """
    Setup dual logging with different outputs for console and file
    
    Args:
        log_file: Path to log file. If None, uses timestamp-based name
        console_level: Minimum level for console output (default: WARNING)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # Generate log file name if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"ai_content_developer_{timestamp}.log"
    else:
        log_file = Path(log_file)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # File handler - detailed logging
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(FileOnlyFilter())
    root_logger.addHandler(file_handler)
    
    # Console handler - minimal output with Rich
    console_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_width=100,
        tracebacks_show_locals=False
    )
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_handler.addFilter(ConsoleFilter())
    root_logger.addHandler(console_handler)
    
    # Log the setup
    logging.info(f"Logging initialized. File: {log_file}, Console level: {console_level}")


def console_log(message: str, level: str = "INFO") -> None:
    """
    Log a message that should appear on console regardless of level
    
    Args:
        message: Message to log
        level: Logging level (default: INFO)
    """
    logger = logging.getLogger(__name__)
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper()),
        fn="console_log",
        lno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.console_only = True
    logger.handle(record)


# Convenience function for getting console
def get_console() -> Console:
    """Get the global Rich console instance"""
    return console 