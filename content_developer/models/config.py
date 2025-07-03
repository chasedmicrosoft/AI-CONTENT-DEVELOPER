"""
Configuration model for AI Content Developer
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import logging

# Load environment variables from .env file if it exists
from dotenv import load_dotenv
load_dotenv()

from ..utils import mkdir
from ..constants import DEFAULT_COMPLETION_MODEL, DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration for content development workflow"""
    # Repository settings
    repo_url: str
    content_goal: str
    service_area: str
    
    # Audience settings
    audience: str = "technical professionals"
    audience_level: str = "intermediate"  # beginner | intermediate | advanced
    
    # Optional settings
    support_materials: List[str] = field(default_factory=list)
    auto_confirm: bool = False
    work_dir: Path = Path.cwd() / "work" / "tmp"
    max_repo_depth: int = 3
    content_limit: int = 15000
    phases: str = "3"
    debug_similarity: bool = False
    apply_changes: bool = False
    skip_toc: bool = False
    check_material_sufficiency: bool = True
    
    # GitHub configuration (optional)
    github_token: Optional[str] = None
    
    # Azure OpenAI configuration
    azure_endpoint: str = ""
    api_version: str = "2024-08-01-preview"
    
    # Deployment names (instead of model names for Azure)
    completion_deployment: str = ""
    embedding_deployment: str = ""
    
    # Model names (for compatibility)
    completion_model: str = ""
    simple_model: str = ""
    embedding_model: str = ""
    
    # Temperature settings
    temperature: float = 0.3
    creative_temperature: float = 0.7
    
    def __post_init__(self):
        """Post-initialization setup"""
        self._validate_azure_config()
        self._load_deployment_config()
        self._load_github_config()
        self._create_output_directories()
    
    def _validate_azure_config(self):
        """Validate Azure OpenAI configuration"""
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        if not self.azure_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
        
        # API version can be overridden
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", self.api_version)
    
    def _load_deployment_config(self):
        """Load deployment configuration from environment variables"""
        # Primary deployments
        self.completion_deployment = os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT", "gpt-4")
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        
        # Set model names to deployment names for compatibility
        self.completion_model = self.completion_deployment
        self.simple_model = self.completion_deployment
        self.embedding_model = self.embedding_deployment
        
        # Temperature settings
        self.temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.3"))
        self.creative_temperature = float(os.getenv("AZURE_OPENAI_CREATIVE_TEMPERATURE", "0.7"))
    
    def _load_github_config(self):
        """Load optional GitHub configuration from environment"""
        # Load GitHub token if available
        self.github_token = os.getenv("GITHUB_TOKEN", "").strip()
        
        # Convert empty string to None for cleaner checks
        if not self.github_token:
            self.github_token = None
        
        # Log configuration status (without revealing token)
        if self.github_token:
            # Mask token for logging - show only first/last 4 chars
            if len(self.github_token) > 8:
                masked = f"{self.github_token[:4]}...{self.github_token[-4:]}"
            else:
                masked = "****"
            logger.info(f"GitHub token loaded: {masked}")
        else:
            logger.info("No GitHub token configured - only public repositories accessible")
    
    def _create_output_directories(self):
        """Create all necessary output directories"""
        base_dir = "./llm_outputs"
        
        # Define only required directories
        required_directories = [
            "embeddings",
            "preview",
            "preview/create",
            "preview/update",
            "preview/toc"
        ]
        
        # Create each directory
        for directory in required_directories:
            full_path = f"{base_dir}/{directory}"
            mkdir(full_path) 