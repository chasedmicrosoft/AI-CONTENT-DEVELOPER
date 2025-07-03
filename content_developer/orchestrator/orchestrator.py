"""
Main orchestrator for AI Content Developer
"""
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from ..interactive.directory import DirectoryConfirmation
from ..interactive.strategy import StrategyConfirmation
from ..models import Config, Result
from ..processors import (
    ContentDiscoveryProcessor, ContentStrategyProcessor, DirectoryDetector,
    MaterialProcessor, TOCProcessor
)
from ..generation import ContentGenerator
from ..repository import RepositoryManager
from ..utils import write, mkdir, read
from ..constants import MAX_PHASES
from ..utils.step_tracker import get_step_tracker

# Import new refactored modules
from .phase_executor import PhaseExecutor
from .change_applier import ChangeApplier

logger = logging.getLogger(__name__)


class ContentDeveloperOrchestrator:
    """Main orchestrator for content development workflow"""
    
    def __init__(self, config: Config, console_display=None):
        self.config = config
        self.console_display = console_display
        
        # Initialize Azure OpenAI client with Entra ID authentication
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )
        
        self.client = AzureOpenAI(
            azure_endpoint=config.azure_endpoint,
            azure_ad_token_provider=token_provider,
            api_version=config.api_version,
        )
        
        # Initialize repository manager with GitHub token if available
        self.repo_manager = RepositoryManager(github_token=config.github_token)
        self.dir_confirmator = DirectoryConfirmation(config, self.client)
        self.strategy_confirmator = StrategyConfirmation(config)
        
        # Initialize phase executor
        self.phase_executor = PhaseExecutor(self)
    
    def execute(self) -> Result:
        """Execute the content development workflow"""
        # Parse phases configuration
        max_phase = self._parse_max_phase()
        phase_display = self.config.phases if self.config.phases != "all" else f"1-{max_phase}"
        logger.info(f"=== Content Developer: Phase(s) {phase_display} ===")
        
        # Execute Phase 1 (always runs)
        result = self.phase_executor.execute_phase1()
        
        # Execute Phase 2 if requested
        if max_phase >= 2 and result.directory_ready:
            self.phase_executor.execute_phase2(result)
        
        # Execute Phase 3 if requested
        if max_phase >= 3 and result.strategy_ready:
            self.phase_executor.execute_phase3(result)
        
        # Execute Phase 4 if requested (now remediation)
        if max_phase >= 4 and result.generation_ready:
            self.phase_executor.execute_phase4(result)
        
        # Execute Phase 5 if requested (now TOC management)
        if max_phase >= 5 and result.generation_ready and not self.config.skip_toc:
            self.phase_executor.execute_phase5(result)
        elif max_phase >= 5 and self.config.skip_toc:
            if self.console_display:
                self.console_display.show_status("TOC management skipped (--skip-toc flag)", "info")
            logger.info("=== Phase 5: TOC Management (SKIPPED) ===")
            logger.info("TOC management skipped due to --skip-toc flag")
        
        # Apply all changes at the end if requested
        if self.config.apply_changes and result.generation_ready:
            change_applier = ChangeApplier(self.console_display)
            change_applier.apply_all_changes(result)
        
        return result
    
    def _parse_max_phase(self) -> int:
        """Parse the maximum phase to execute from config"""
        if self.config.phases == "all":
            max_phase = MAX_PHASES
        elif self.config.phases.isdigit() and 1 <= int(self.config.phases) <= MAX_PHASES:
            max_phase = int(self.config.phases)
        else:
            # Invalid phase specification, default to all phases
            logger.warning(f"Invalid phases value '{self.config.phases}', defaulting to all phases")
            max_phase = MAX_PHASES
        
        logger.info(f"Phases parsing: config.phases='{self.config.phases}' -> max_phase={max_phase}")
        return max_phase
    
    def _confirm_strategy(self, strategy: 'ContentStrategy') -> bool:
        """Confirm strategy with user"""
        if not strategy or not strategy.decisions:
            return False
        
        # Show a confirmation prompt
        if self.console_display:
            self.console_display.show_separator()
            confirm = self.console_display.prompt_confirm("Proceed with this strategy?")
            return confirm
        
        # If no console display, just return true
        return True
    
    def _run_toc_phase(self, working_dir_path: Path, created_files: list, updated_files: list, 
                      strategy: 'ContentStrategy') -> Dict:
        """Run TOC management phase"""
        from ..processors.phase5 import TOCProcessor
        toc_processor = TOCProcessor(self.client, self.config, self.console_display)
        toc_processor.set_phase_step(5, 1)  # Phase 5, Step 1: TOC processing
        
        # Extract just the file paths if created_files/updated_files are dicts
        created_paths = []
        for item in created_files:
            if isinstance(item, dict):
                created_paths.append(item.get('path', ''))
            else:
                created_paths.append(item)
        
        updated_paths = []
        for item in updated_files:
            if isinstance(item, dict):
                updated_paths.append(item.get('path', ''))
            else:
                updated_paths.append(item)
        
        return toc_processor.process(
            working_dir_path,
            created_paths,  # Pass just the paths
            updated_paths,  # Pass just the paths
            {
                'decisions': strategy.decisions if hasattr(strategy, 'decisions') else []
            }
        )
    
    def _setup_directory(self, repo_path: Path, working_dir: str) -> Dict:
        """Setup and validate working directory"""
        # Handle empty string as repository root
        if working_dir == '':
            full_path = repo_path
            logger.info("Using repository root as working directory")
        else:
            # Strip repository name if included
            working_dir = self._normalize_working_directory(repo_path, working_dir)
            # Get full path
            full_path = repo_path / working_dir
        
        # Validate directory
        validation_result = self._validate_directory(full_path, working_dir)
        if validation_result:
            return validation_result
        
        # Check for markdown files
        md_count = self._count_markdown_files(full_path)
        
        return {
            'success': True,
            'full_path': str(full_path),
            'markdown_count': md_count
        }
    
    def _normalize_working_directory(self, repo_path: Path, working_dir: str) -> str:
        """Normalize working directory path by removing repo name if present"""
        repo_name = repo_path.name
        if working_dir.startswith(f"{repo_name}/"):
            working_dir = working_dir[len(repo_name)+1:]
            logger.info(f"Stripped repo name from working_dir: {repo_name}/ -> {working_dir}")
        return working_dir
    
    def _validate_directory(self, full_path: Path, working_dir: str) -> Optional[Dict]:
        """Validate that the directory exists and is a directory"""
        if not full_path.exists():
            return {
                'success': False,
                'error': f"Directory does not exist: {working_dir}",
                'full_path': str(full_path)
            }
        
        if not full_path.is_dir():
            return {
                'success': False,
                'error': f"Not a directory: {working_dir}",
                'full_path': str(full_path)
            }
        
        return None
    
    def _count_markdown_files(self, directory: Path) -> int:
        """Count markdown files in directory"""
        md_files = list(directory.rglob("*.md"))
        if not md_files:
            logger.warning(f"No markdown files found in {directory}")
            logger.info("This may indicate a non-content directory was selected (e.g., media/assets directory)")
            logger.info("Consider re-running with a different content goal or checking the selected directory")
        return len(md_files)
