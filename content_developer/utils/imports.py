"""
Dynamic imports handler for optional dependencies
"""
import sys
import logging
from typing import List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Import configuration
IMPORTS = [
    ('openai', ['OpenAI'], True, "OpenAI required. Install: pip install openai"),
    ('rich.console', ['Console'], False, None),
    ('rich.panel', ['Panel'], False, None),
    ('docx', ['Document'], False, "python-docx not available"),
    ('PyPDF2', ['PdfReader'], False, "PyPDF2 not available"),
    ('requests', None, False, "requests not available"),
    ('bs4', ['BeautifulSoup'], False, "beautifulsoup4 not available"),
    ('tenacity', ['retry', 'stop_after_attempt', 'wait_exponential', 'retry_if_exception_type'], False, "tenacity not available - retry logic disabled"),
    ('rich.progress', ['Progress', 'SpinnerColumn', 'TextColumn', 'BarColumn', 'TaskProgressColumn', 'TimeRemainingColumn'], False, "Rich progress not available")
]

# Global availability flags
HAS_OPENAI = False
HAS_RICH = False
HAS_DOCX = False
HAS_PDF = False
HAS_WEB = False
HAS_TENACITY = False
HAS_PROGRESS = False

# Store imported modules
imported_modules = {}


def safe_import(module: str, items: Optional[List[str]] = None, 
                required: bool = False, msg: Optional[str] = None) -> Any:
    """
    Safely import a module with optional items
    
    Args:
        module: Module name to import
        items: List of items to import from module
        required: Whether the import is required
        msg: Warning message if import fails
        
    Returns:
        Imported module or items, or None if failed
    """
    try:
        mod = __import__(module, fromlist=items or [])
        if items:
            return tuple(getattr(mod, item) for item in items)
        return mod
    except ImportError:
        if msg:
            logger.warning(msg)
        if required:
            sys.exit(1)
        if items:
            return tuple([None] * len(items))
        return None


def initialize_imports():
    """Initialize all dynamic imports and set availability flags"""
    global HAS_OPENAI, HAS_RICH, HAS_DOCX, HAS_PDF, HAS_WEB, HAS_TENACITY, HAS_PROGRESS
    
    for module, items, required, msg in IMPORTS:
        if items:
            result = safe_import(module, items, required, msg)
            if result:
                for i, item in enumerate(items):
                    imported_modules[item] = result[i]
        else:
            result = safe_import(module, None, required, msg)
            if result:
                imported_modules[module.split('.')[-1]] = result
    
    # Set availability flags
    HAS_OPENAI = 'OpenAI' in imported_modules
    HAS_RICH = 'Console' in imported_modules and 'Panel' in imported_modules
    HAS_DOCX = 'Document' in imported_modules
    HAS_PDF = 'PdfReader' in imported_modules
    HAS_WEB = 'requests' in imported_modules and 'BeautifulSoup' in imported_modules
    HAS_TENACITY = 'retry' in imported_modules
    HAS_PROGRESS = 'Progress' in imported_modules
    
    return imported_modules


def get_import(name: str) -> Any:
    """Get an imported module or item by name"""
    return imported_modules.get(name)


# Initialize imports when module is loaded
initialize_imports() 