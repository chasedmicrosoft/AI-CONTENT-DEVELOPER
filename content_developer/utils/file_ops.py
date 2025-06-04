"""
File operations utilities
"""
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional


def read(path: Path, limit: Optional[int] = None) -> str:
    """Read text file with optional limit
    
    Args:
        path: Path to file to read
        limit: Maximum characters to read. None means read entire file.
    """
    path = Path(path)
    content = path.read_text()
    return content[:limit] if limit else content


def write(path: Path, content: str) -> None:
    """Write text to file"""
    Path(path).write_text(content)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    """Save data as JSON"""
    Path(path).write_text(json.dumps(data, indent=2))


def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file"""
    path = Path(path)
    if not path.exists():
        return {}
    
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def get_hash(path: Path) -> str:
    """Get file hash"""
    path = Path(path)
    if not path.exists():
        return ""
    
    with open(path, 'rb') as file_handle:
        file_content = file_handle.read()
        return hashlib.sha256(file_content).hexdigest()


def mkdir(path: Path) -> None:
    """Create directory with parents"""
    Path(path).mkdir(parents=True, exist_ok=True) 