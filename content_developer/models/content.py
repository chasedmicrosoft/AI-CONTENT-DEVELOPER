"""
Content models for AI Content Developer
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ContentStrategy:
    """Content strategy with CREATE/UPDATE actions"""
    thinking: str
    decisions: List[Dict]  # CREATE and UPDATE actions
    confidence: float
    summary: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DocumentChunk:
    """Represents a chunk of document content with metadata"""
    content: str
    file_path: str
    heading_path: List[str]
    section_level: int
    chunk_index: int
    frontmatter: Dict[str, Any]
    embedding_content: str
    embedding: Optional[List[float]] = None
    content_hash: Optional[str] = None
    file_id: str = ""
    chunk_id: str = ""
    prev_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    parent_heading_chunk_id: Optional[str] = None
    total_chunks_in_file: int = 0 