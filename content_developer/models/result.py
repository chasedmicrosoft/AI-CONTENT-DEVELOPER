"""
Result model for AI Content Developer
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .content import ContentStrategy


@dataclass
class Result:
    """Result of content developer pipeline"""
    
    # Core fields from Phase 1
    working_directory: str
    justification: str
    confidence: float
    repo_url: str
    repo_path: str
    material_summaries: List[Dict]
    content_goal: str
    service_area: str
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Phase 1 status
    directory_ready: bool = False
    working_directory_full_path: Optional[str] = None
    setup_error: Optional[str] = None
    
    # Phase 2 results
    content_strategy: Optional[ContentStrategy] = None
    strategy_ready: bool = False
    
    # Phase 3 results
    generation_results: Optional[Dict] = None
    generation_ready: bool = False
    
    # Phase 4 results (remediation)
    remediation_results: Optional[Dict] = None
    remediation_ready: bool = False
    
    # Phase 5 results (TOC management)
    toc_results: Optional[Dict] = None
    toc_ready: bool = False 