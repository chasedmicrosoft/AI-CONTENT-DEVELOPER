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