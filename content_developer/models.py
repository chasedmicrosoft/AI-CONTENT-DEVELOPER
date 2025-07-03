"""
Data models for content developer
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum

@dataclass
class Result:
    """Final result of content development"""
    # Phase 1 results
    working_directory: str
    justification: str
    confidence: float
    repo_url: str
    repo_path: str
    material_summaries: List[MaterialSummary]
    content_goal: str
    service_area: str
    directory_ready: bool
    working_directory_full_path: Optional[str] = None
    setup_error: Optional[str] = None
    
    # Phase 2 results
    content_strategy: Optional['ContentStrategy'] = None
    strategy_ready: bool = False
    
    # Phase 3 results
    generation_results: Optional[Dict] = None
    generation_ready: bool = False
    
    # Phase 4 results
    toc_results: Optional[Dict] = None
    toc_ready: bool = False

@dataclass
class ContentDecision:
    """Represents a strategic decision about content to create or update"""
    action: str  # CREATE, UPDATE, or SKIP
    target_file: Optional[str]  # Can be None for SKIP actions
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
        # Map new fields to legacy fields for compatibility
        if self.target_file and not self.filename:
            self.filename = self.target_file
        if self.rationale and not self.reason:
            self.reason = self.rationale
        if self.content_type and not self.ms_topic:
            self.ms_topic = self.content_type 