"""
Main orchestrator for AI Content Developer
"""
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

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
from ..utils import write, mkdir
from ..constants import MAX_PHASES
from ..utils.step_tracker import get_step_tracker

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
        
        self.repo_manager = RepositoryManager()
        self.dir_confirmator = DirectoryConfirmation(config, self.client)
        self.strategy_confirmator = StrategyConfirmation(config)
    
    def execute(self) -> Result:
        """Execute the content development workflow"""
        # Parse phases configuration
        max_phase = self._parse_max_phase()
        phase_display = self.config.phases if self.config.phases != "all" else f"1-{max_phase}"
        logger.info(f"=== Content Developer: Phase(s) {phase_display} ===")
        
        # Execute Phase 1 (always runs)
        result = self._execute_phase1()
        
        # Execute Phase 2 if requested
        if max_phase >= 2 and result.directory_ready:
            self._execute_phase2(result)
        
        # Execute Phase 3 if requested
        if max_phase >= 3 and result.strategy_ready:
            self._execute_phase3(result)
        
        # Execute Phase 4 if requested
        if max_phase >= 4 and result.generation_ready and not self.config.skip_toc:
            self._execute_phase4(result)
        elif max_phase >= 4 and self.config.skip_toc:
            if self.console_display:
                self.console_display.show_status("TOC management skipped (--skip-toc flag)", "info")
            logger.info("=== Phase 4: TOC Management (SKIPPED) ===")
            logger.info("TOC management skipped due to --skip-toc flag")
        
        return result
    
    def _parse_max_phase(self) -> int:
        """Parse the maximum phase to execute from config"""
        if self.config.phases == "all":
            max_phase = MAX_PHASES
        elif self.config.phases.isdigit():
            max_phase = int(self.config.phases)
        else:
            # Handle combinations like "123", "34", etc.
            max_phase = max(int(p) for p in self.config.phases if p.isdigit()) if any(p.isdigit() for p in self.config.phases) else 1
        
        logger.info(f"Phases parsing: config.phases='{self.config.phases}' -> max_phase={max_phase}")
        return max_phase
    
    def _execute_phase1(self) -> Result:
        """Execute Phase 1: Repository Analysis & Directory Selection"""
        logger.info("=== Phase 1: Repository Analysis ===")
        
        # Reset step counter for Phase 1
        step_tracker = get_step_tracker()
        step_tracker.reset_phase(1)
        
        if self.console_display:
            with self.console_display.phase_progress("1: Repository Analysis", 4) as progress:
                # Clone/update repository
                progress.update_func(description="Cloning repository")
                repo_path = self.repo_manager.clone_or_update(self.config.repo_url, self.config.work_dir)
                progress.update_func(1)
                
                # Process materials - Phase 1, Step 1
                progress.update_func(description="Processing materials")
                material_processor = MaterialProcessor(self.client, self.config, self.console_display)
                material_processor.set_phase_step(1, 1)
                materials = material_processor.process(
                    self.config.support_materials, repo_path
                )
                progress.update_func(1)
                
                # Get repository structure
                progress.update_func(description="Analyzing structure")
                structure = self.repo_manager.get_structure(repo_path, self.config.max_repo_depth)
                progress.update_func(1)
                
                # Detect working directory with LLM - Phase 1, Step 2
                progress.update_func(description="Selecting directory")
                llm_result, llm_failed, error = self._detect_directory(repo_path, structure, materials)
                progress.update_func(1)
        else:
            # Original flow without console display
            repo_path = self.repo_manager.clone_or_update(self.config.repo_url, self.config.work_dir)
            material_processor = MaterialProcessor(self.client, self.config)
            material_processor.set_phase_step(1, 1)
            materials = material_processor.process(
                self.config.support_materials, repo_path
            )
            structure = self.repo_manager.get_structure(repo_path, self.config.max_repo_depth)
            llm_result, llm_failed, error = self._detect_directory(repo_path, structure, materials)
        
        # In auto-confirm mode, check if the selection is valid
        if self.config.auto_confirm:
            if llm_failed:
                logger.error(f"Directory selection failed in auto-confirm mode: {error}")
                raise RuntimeError(f"Auto-confirm enabled but LLM failed: {error}")
            
            # Check if the result indicates a failure (empty directory, low confidence, or error)
            if not llm_result.get('working_directory'):
                error_msg = llm_result.get('error', 'LLM returned empty directory')
                logger.error(f"Directory selection failed in auto-confirm mode: {error_msg}")
                raise RuntimeError(f"Auto-confirm enabled but directory selection failed: {error_msg}")
            
            if llm_result.get('confidence', 0) < 0.7:
                logger.error(f"Directory selection confidence too low in auto-confirm mode: {llm_result.get('confidence', 0):.2f}")
                logger.error(f"Selected directory: {llm_result.get('working_directory')}")
                raise RuntimeError(f"Auto-confirm enabled but confidence too low: {llm_result.get('confidence', 0):.2f}")
        
        # Confirm directory selection (in auto-confirm mode, this will just pass through)
        confirmed = self.dir_confirmator.confirm(llm_result, structure, llm_failed, error)
        
        # Setup directory
        setup_result = self._setup_directory(repo_path, confirmed['working_directory'])
        
        # Show phase summary
        if self.console_display:
            self.console_display.show_phase_summary("1: Repository Analysis", {
                "Selected Directory": confirmed['working_directory'],
                "Confidence": f"{confirmed['confidence']:.1%}",
                "Materials Processed": len(materials),
                "Markdown Files": setup_result.get('markdown_count', 0)
            })
        
        # Create and return result
        return self._create_phase1_result(confirmed, setup_result, repo_path, materials)
    
    def _detect_directory(self, repo_path: Path, structure: str, 
                         materials: list) -> Tuple[Optional[Dict], bool, str]:
        """Detect working directory using LLM"""
        try:
            detector = DirectoryDetector(self.client, self.config, self.console_display)
            detector.set_phase_step(1, 1)
            llm_result = detector.process(
                repo_path, structure, materials
            )
            return llm_result, False, ""
        except Exception as e:
            logger.warning(f"LLM failed: {e}")
            return None, True, str(e)
    
    def _create_phase1_result(self, confirmed: Dict, setup_result: Dict, 
                             repo_path: Path, materials: list) -> Result:
        """Create Result object from Phase 1 outputs"""
        return Result(
            working_directory=confirmed['working_directory'],
            justification=confirmed['justification'],
            confidence=confirmed['confidence'],
            repo_url=self.config.repo_url,
            repo_path=str(repo_path),
            material_summaries=materials,
            content_goal=self.config.content_goal,
            service_area=self.config.service_area,
            directory_ready=setup_result['success'],
            working_directory_full_path=setup_result.get('full_path'),
            setup_error=setup_result.get('error')
        )
    
    def _execute_phase2(self, result: Result) -> None:
        """Execute Phase 2: Content Strategy Analysis"""
        logger.info("=== Phase 2: Content Strategy Analysis ===")
        
        # Reset step counter for Phase 2
        step_tracker = get_step_tracker()
        step_tracker.reset_phase(2)
        
        try:
            # Get working directory path
            working_dir_path = Path(result.working_directory_full_path)
            
            if self.console_display:
                with self.console_display.phase_progress("2: Content Strategy", 3) as progress:
                    # Discover content chunks - Phase 2, Step 1
                    progress.update_func(description="Discovering content")
                    discovery_processor = ContentDiscoveryProcessor(self.client, self.config, self.console_display)
                    discovery_processor.set_phase_step(2, 1)
                    chunks = discovery_processor.process(
                        working_dir_path,
                        self.repo_manager.extract_name(self.config.repo_url),
                        result.working_directory
                    )
                    progress.update_func(1)
                    
                    # Generate content strategy - Phase 2, Step 2
                    progress.update_func(description="Analyzing gaps")
                    strategy_processor = ContentStrategyProcessor(self.client, self.config, self.console_display)
                    strategy_processor.set_phase_step(2, 2)
                    strategy = strategy_processor.process(
                        chunks, result.material_summaries, self.config,
                        self.repo_manager.extract_name(self.config.repo_url),
                        result.working_directory
                    )
                    progress.update_func(1)
                    
                    # Confirm strategy
                    progress.update_func(description="Confirming strategy")
                    confirmed_strategy = self.strategy_confirmator.confirm(strategy)
                    progress.update_func(1)
                    
                    # Show decisions
                    self.console_display.show_status(f"Generated {len(confirmed_strategy.decisions)} content decisions", "success")
                    for decision in confirmed_strategy.decisions[:5]:  # Show first 5
                        self.console_display.show_decision(decision)
                    if len(confirmed_strategy.decisions) > 5:
                        self.console_display.show_status(f"... and {len(confirmed_strategy.decisions) - 5} more", "info")
            else:
                # Original flow
                chunks = self._discover_content(working_dir_path, result.working_directory)
                strategy = self._generate_strategy(chunks, result.material_summaries, result.working_directory)
                confirmed_strategy = self.strategy_confirmator.confirm(strategy)
            
            # Update result
            result.content_strategy = confirmed_strategy
            result.strategy_ready = confirmed_strategy.confidence > 0
            
            # Show phase summary
            if self.console_display:
                create_count = sum(1 for d in confirmed_strategy.decisions if d.get('action') == 'CREATE')
                update_count = sum(1 for d in confirmed_strategy.decisions if d.get('action') == 'UPDATE')
                self.console_display.show_phase_summary("2: Content Strategy", {
                    "Content Chunks Analyzed": len(chunks),
                    "Files to Create": create_count,
                    "Files to Update": update_count,
                    "Strategy Confidence": f"{confirmed_strategy.confidence:.1%}"
                })
            
            logger.info(f"Phase 2 completed: {confirmed_strategy.summary}")
            
        except Exception as e:
            self._handle_phase2_error(result, e)
    
    def _discover_content(self, working_dir_path: Path, working_directory: str) -> list:
        """Discover and chunk content in the working directory"""
        processor = ContentDiscoveryProcessor(self.client, self.config, self.console_display)
        processor.set_phase_step(2, 1)
        chunks = processor.process(
            working_dir_path,
            self.repo_manager.extract_name(self.config.repo_url),
            working_directory
        )
        logger.info(f"ContentDiscoveryProcessor returned {len(chunks)} chunks")
        return chunks
    
    def _generate_strategy(self, chunks: list, materials: list, 
                          working_directory: str) -> 'ContentStrategy':
        """Generate content strategy based on discovered chunks"""
        processor = ContentStrategyProcessor(self.client, self.config, self.console_display)
        processor.set_phase_step(2, 2)
        strategy = processor.process(
            chunks, materials, self.config,
            self.repo_manager.extract_name(self.config.repo_url),
            working_directory
        )
        logger.info(f"ContentStrategyProcessor returned strategy: {strategy.summary[:50]}...")
        return strategy
    
    def _handle_phase2_error(self, result: Result, error: Exception) -> None:
        """Handle Phase 2 execution errors"""
        import traceback
        logger.error(f"Phase 2 failed with exception: {type(error).__name__}: {error}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        if self.console_display:
            self.console_display.show_error(str(error), "Phase 2 Failed")
        
        error_strategy = self.strategy_confirmator.confirm(None, True, str(error))
        result.content_strategy = error_strategy
        result.strategy_ready = False
    
    def _execute_phase3(self, result: Result) -> None:
        """Execute Phase 3: Content Generation"""
        logger.info("=== Phase 3: Content Generation ===")
        
        # Reset step counter for Phase 3
        step_tracker = get_step_tracker()
        step_tracker.reset_phase(3)
        try:
            # Get working directory path
            working_dir_path = Path(result.working_directory_full_path)
            
            if self.console_display:
                total_actions = len(result.content_strategy.decisions)
                with self.console_display.phase_progress("3: Content Generation", total_actions) as progress:
                    # Generate content with progress updates
                    generator = ContentGenerator(self.client, self.config, self.console_display)
                    generator.set_phase_step(3, 1)  # Phase 3, Step 1: Main generation
                    
                    # Set up progress callback
                    def update_progress(action_name: str):
                        progress.update_func(1, description=f"Processing: {action_name}")
                    
                    generator.progress_callback = update_progress
                    
                    generation_results = generator.process(
                        result.content_strategy,
                        result.material_summaries,
                        working_dir_path,
                        self.repo_manager.extract_name(self.config.repo_url),
                        result.working_directory
                    )
            else:
                # Original flow
                generation_results = self._generate_content(
                    result, working_dir_path, result.working_directory
                )
            
            # Store results
            result.generation_results = generation_results
            result.generation_ready = True
            
            # Apply changes if requested
            if self.config.apply_changes:
                self._apply_generated_content(generation_results, working_dir_path)
                # Set applied flag to indicate changes were written to repository
                generation_results['applied'] = True
                if self.console_display:
                    self.console_display.show_status("Changes applied to repository", "success")
            else:
                # Set applied flag to false to indicate preview mode
                generation_results['applied'] = False
                if self.console_display:
                    self.console_display.show_status("Preview mode - changes not applied (use --apply-changes to apply)", "info")
            
            # Show phase summary
            if self.console_display:
                create_count = sum(1 for r in generation_results.get('create_results', []) if r.get('success'))
                update_count = sum(1 for r in generation_results.get('update_results', []) if r.get('success'))
                self.console_display.show_phase_summary("3: Content Generation", {
                    "Files Created": create_count,
                    "Files Updated": update_count,
                    "Applied to Repository": generation_results.get('applied', False)
                })
            
            # Log summary
            self._log_generation_summary(generation_results)
            
        except Exception as e:
            self._handle_phase3_error(result, e)
    
    def _generate_content(self, result: Result, working_dir_path: Path, 
                         working_directory: str) -> Dict:
        """Generate content using ContentGenerator"""
        generator = ContentGenerator(self.client, self.config, self.console_display)
        generator.set_phase_step(3, 1)  # Phase 3, Step 1: Main generation
        return generator.process(
            result.content_strategy,
            result.material_summaries,
            working_dir_path,
            self.repo_manager.extract_name(self.config.repo_url),
            working_directory
        )
    
    def _log_generation_summary(self, generation_results: Dict) -> None:
        """Log content generation summary"""
        create_count = sum(1 for result in generation_results.get('create_results', []) 
                          if result.get('success'))
        update_count = sum(1 for result in generation_results.get('update_results', []) 
                          if result.get('success'))
        
        logger.info(f"Phase 3 completed: Generated {create_count} new files, "
                   f"updated {update_count} files")
    
    def _handle_phase3_error(self, result: Result, error: Exception) -> None:
        """Handle Phase 3 execution errors"""
        logger.error(f"Phase 3 failed: {error}")
        
        if self.console_display:
            self.console_display.show_error(str(error), "Phase 3 Failed")
        
        result.generation_results = None
        result.generation_ready = False
    
    def _apply_generated_content(self, generation_results: Dict, working_dir_path: Path):
        """Apply generated content to the repository"""
        logger.info("Applying generated content to repository...")
        
        # Apply CREATE actions
        self._apply_create_actions(generation_results.get('create_results', []), 
                                  working_dir_path)
        
        # Apply UPDATE actions
        self._apply_update_actions(generation_results.get('update_results', []), 
                                  working_dir_path)
    
    def _apply_create_actions(self, create_results: list, working_dir_path: Path) -> None:
        """Apply CREATE actions to create new files"""
        for result in create_results:
            if result.get('success') and result.get('content'):
                self._create_file(result, working_dir_path)
    
    def _create_file(self, result: Dict, working_dir_path: Path) -> None:
        """Create a new file from generation result"""
        filename = result['action'].get('filename', '')
        file_path = working_dir_path / filename
        
        # Ensure directory exists
        mkdir(file_path.parent)
        
        # Write content
        write(file_path, result['content'])
        logger.info(f"Created: {filename}")
    
    def _apply_update_actions(self, update_results: list, working_dir_path: Path) -> None:
        """Apply UPDATE actions to modify existing files"""
        for result in update_results:
            if result.get('success') and result.get('updated_content'):
                self._update_file(result, working_dir_path)
    
    def _update_file(self, result: Dict, working_dir_path: Path) -> None:
        """Update an existing file from generation result"""
        filename = result['action'].get('filename', '')
        file_path = working_dir_path / filename
        
        # Write updated content
        write(file_path, result['updated_content'])
        logger.info(f"Updated: {filename}")
    
    def _setup_directory(self, repo_path: Path, working_dir: str) -> Dict:
        """Setup and validate working directory"""
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
    
    def _execute_phase4(self, result: Result) -> None:
        """Execute Phase 4: TOC Management"""
        logger.info("=== Phase 4: TOC Management ===")
        
        # Reset step counter for Phase 4
        step_tracker = get_step_tracker()
        step_tracker.reset_phase(4)
        
        try:
            # Get working directory path
            working_dir_path = Path(result.working_directory_full_path)
            
            if self.console_display:
                with self.console_display.phase_progress("4: TOC Management", 2) as progress:
                    # Run TOC management
                    progress.update_func(description="Analyzing TOC structure")
                    toc_processor = TOCProcessor(self.client, self.config, self.console_display)
                    toc_processor.set_phase_step(4, 1)  # Phase 4, Step 1: TOC processing
                    toc_results = toc_processor.process(
                        working_dir_path,
                        result.generation_results.get('created_files', []),
                        result.generation_results.get('updated_files', []),
                        {
                            'decisions': result.content_strategy.decisions if hasattr(result.content_strategy, 'decisions') else []
                        }
                    )
                    progress.update_func(1)
                    
                    # Apply if requested
                    progress.update_func(description="Updating TOC")
                    if self.config.apply_changes and toc_results.get('success') and toc_results.get('changes_made'):
                        self._apply_toc_changes(toc_results, working_dir_path)
                        toc_results['applied'] = True
                        self.console_display.show_status("TOC.yml updated", "success")
                    else:
                        toc_results['applied'] = False
                        if toc_results.get('success') and not toc_results.get('changes_made'):
                            self.console_display.show_status("No TOC changes needed", "info")
                        elif toc_results.get('success'):
                            self.console_display.show_status("TOC preview generated (use --apply-changes to apply)", "info")
                    progress.update_func(1)
            else:
                # Original flow
                toc_results = self._run_toc_phase(
                    working_dir_path,
                    result.generation_results.get('created_files', []),
                    result.generation_results.get('updated_files', []),
                    result.content_strategy
                )
                
                if self.config.apply_changes and toc_results.get('success') and toc_results.get('changes_made'):
                    self._apply_toc_changes(toc_results, working_dir_path)
                    toc_results['applied'] = True
                else:
                    toc_results['applied'] = False
            
            # Update result
            result.toc_results = toc_results
            result.toc_ready = True
            
            # Show phase summary
            if self.console_display:
                entries_added = len(toc_results.get('entries_added', []))
                self.console_display.show_phase_summary("4: TOC Management", {
                    "Entries Added": entries_added,
                    "Applied to Repository": toc_results.get('applied', False),
                    "Status": toc_results.get('message', 'Completed')
                })
            
            logger.info(f"Phase 4 completed: {toc_results.get('message', 'No message')}")
            
        except Exception as e:
            self._handle_phase4_error(result, e)
    
    def _run_toc_phase(self, working_dir_path: Path, created_files: list, updated_files: list, 
                      strategy: 'ContentStrategy') -> Dict:
        """Run TOC management phase"""
        toc_processor = TOCProcessor(self.client, self.config, self.console_display)
        toc_processor.set_phase_step(4, 1)  # Phase 4, Step 1: TOC processing
        return toc_processor.process(
            working_dir_path,
            created_files,
            updated_files,
            {
                'decisions': strategy.decisions if hasattr(strategy, 'decisions') else []
            }
        )
    
    def _apply_toc_changes(self, toc_results: Dict, working_dir_path: Path) -> None:
        """Apply TOC changes to the repository"""
        logger.info("Applying TOC changes to repository...")
        
        toc_path = working_dir_path / "TOC.yml"
        
        # The LLM should have returned the complete updated TOC content
        updated_content = toc_results.get('content', '')
        
        if not updated_content:
            logger.error("No TOC content to apply")
            return
        
        # Write the updated TOC
        write(toc_path, updated_content)
        logger.info(f"Updated: TOC.yml")
        
        # Log which entries were added
        entries_added = toc_results.get('entries_added', [])
        if entries_added:
            logger.info(f"Added {len(entries_added)} entries to TOC: {', '.join(entries_added)}")
    
    def _handle_phase4_error(self, result: Result, error: Exception) -> None:
        """Handle Phase 4 execution errors"""
        logger.error(f"Phase 4 failed: {error}")
        
        if self.console_display:
            self.console_display.show_error(str(error), "Phase 4 Failed")
        
        result.toc_results = None
        result.toc_ready = False 