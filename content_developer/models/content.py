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
    decisions: List['ContentDecision']  # List of ContentDecision objects
    confidence: float
    summary: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    debug_info: Optional[Dict[str, Any]] = None


@dataclass
class ContentDecision:
    """Represents a strategic decision about content to create or update"""
    action: str  # CREATE, UPDATE, or SKIP
    target_file: str  # Required for all actions - never null
    file_title: str
    content_type: str
    sections: List[str]
    rationale: str
    priority: str = "medium"
    aligns_with_goal: bool = True
    prerequisites: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    
    # Legacy fields for backward compatibility
    filename: Optional[str] = None
    reason: Optional[str] = None
    relevant_chunks: List[str] = field(default_factory=list)
    content_brief: Optional[Dict[str, Any]] = None
    ms_topic: Optional[str] = None
    
    # For UPDATE actions
    current_content_type: Optional[str] = None
    change_description: Optional[str] = None
    specific_sections: Optional[List[str]] = None
    
    def __post_init__(self):
        # Validate target_file
        if not self.target_file or self.target_file.strip() == "":
            raise ValueError(f"target_file is required for {self.action} action")
            
        # Map new fields to legacy fields for compatibility
        if self.target_file and not self.filename:
            self.filename = self.target_file
        if self.rationale and not self.reason:
            self.reason = self.rationale
        if self.content_type and not self.ms_topic:
            self.ms_topic = self.content_type


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