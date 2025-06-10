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
        
        # Execute Phase 4 if requested (now remediation)
        if max_phase >= 4 and result.generation_ready:
            self._execute_phase4(result)
        
        # Execute Phase 5 if requested (now TOC management)
        if max_phase >= 5 and result.generation_ready and not self.config.skip_toc:
            self._execute_phase5(result)
        elif max_phase >= 5 and self.config.skip_toc:
            if self.console_display:
                self.console_display.show_status("TOC management skipped (--skip-toc flag)", "info")
            logger.info("=== Phase 5: TOC Management (SKIPPED) ===")
            logger.info("TOC management skipped due to --skip-toc flag")
        
        # Apply all changes at the end if requested
        if self.config.apply_changes and result.generation_ready:
            self._apply_all_changes(result)
        
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
                
                # Check repository size to decide which structure method to use
                total_items = sum(1 for _ in repo_path.rglob("*") if not str(_).startswith('.'))
                is_large_repo = total_items > 5000  # Threshold for large repo
                
                if is_large_repo:
                    logger.info(f"Large repository detected ({total_items} items), using directory-only structure")
                    # Use directory-only structure for large repos to avoid rate limits
                    structure = self.repo_manager.get_directory_structure(repo_path, self.config.max_repo_depth)
                else:
                    # For smaller repos, we can use the full structure (which now defaults to directory-only anyway)
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
            else:
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
                    
                    # Display strategy decisions
                    for decision in strategy.decisions:
                        self.console_display.show_strategy_decision(decision)
                    
                    self.console_display.show_separator()
                    
                    # Show confidence
                    self.console_display.show_metric("Strategy Confidence", f"{strategy.confidence:.0%}")
                    
                    # Ask for confirmation
                    if not self.config.auto_confirm:
                        if not self._confirm_strategy(strategy):
                            self.console_display.show_warning("Strategy rejected by user")
                            result.success = False
                            result.error = "User rejected the strategy"
                            return
            else:
                # Original flow
                # Discover content chunks
                discovery_processor = ContentDiscoveryProcessor(self.client, self.config, self.console_display)
                discovery_processor.set_phase_step(2, 1)
                chunks = discovery_processor.process(
                    working_dir_path,
                    self.repo_manager.extract_name(self.config.repo_url),
                    result.working_directory
                )
                logger.info(f"ContentDiscoveryProcessor returned {len(chunks)} chunks")
                
                # Generate content strategy
                strategy_processor = ContentStrategyProcessor(self.client, self.config, self.console_display)
                strategy_processor.set_phase_step(2, 2)
                strategy = strategy_processor.process(
                    chunks, result.material_summaries, self.config,
                    self.repo_manager.extract_name(self.config.repo_url),
                    result.working_directory
                )
                logger.info(f"ContentStrategyProcessor returned strategy: {strategy.summary[:50]}...")
            
            # Update result
            result.content_strategy = strategy
            result.strategy_ready = strategy.confidence > 0
            
            # Show phase summary
            if self.console_display:
                create_count = sum(1 for d in strategy.decisions if d.action == 'CREATE')
                update_count = sum(1 for d in strategy.decisions if d.action == 'UPDATE')
                skip_count = sum(1 for d in strategy.decisions if d.action == 'SKIP')
                self.console_display.show_phase_summary("2: Content Strategy", {
                    "Files Analyzed": len(chunks),
                    "Files to Create": create_count,
                    "Files to Update": update_count,
                    "Files to Skip": skip_count,
                    "Strategy Confidence": f"{strategy.confidence:.1%}"
                })
            
            logger.info(f"Phase 2 completed: {strategy.summary}")
            
        except Exception as e:
            self._handle_phase2_error(result, e)
    

    
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
            
            # Filter out SKIP decisions
            active_decisions = [d for d in result.content_strategy.decisions if d.action != 'SKIP']
            
            if self.console_display:
                total_actions = len(active_decisions)
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
                generator = ContentGenerator(self.client, self.config, self.console_display)
                generator.set_phase_step(3, 1)  # Phase 3, Step 1: Main generation
                generation_results = generator.process(
                    result.content_strategy,
                    result.material_summaries,
                    working_dir_path,
                    self.repo_manager.extract_name(self.config.repo_url),
                    result.working_directory
                )
            
            # Store results
            result.generation_results = generation_results
            result.generation_ready = True
            
            # Note: Apply changes moved to phase 4 after remediation
            if self.console_display:
                self.console_display.show_status("Content generated - proceed to remediation phase", "info")
            
            # Show phase summary
            if self.console_display:
                create_count = sum(1 for r in generation_results.get('create_results', []) if r.get('success'))
                update_count = sum(1 for r in generation_results.get('update_results', []) if r.get('success'))
                skip_count = sum(1 for r in generation_results.get('skip_results', []))
                self.console_display.show_phase_summary("3: Content Generation", {
                    "Files Created (Preview)": create_count,
                    "Files Updated (Preview)": update_count,
                    "Files Skipped": skip_count,
                    "Status": "All content saved to preview directory"
                })
            
            # Log summary
            self._log_generation_summary(generation_results)
            
        except Exception as e:
            self._handle_phase3_error(result, e)
    

    
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
    
    def _execute_phase4(self, result: Result) -> None:
        """Execute Phase 4: Content Remediation"""
        logger.info("=== Phase 4: Content Remediation ===")
        
        # Reset step counter for Phase 4
        step_tracker = get_step_tracker()
        step_tracker.reset_phase(4)
        
        try:
            # Get working directory path
            working_dir_path = Path(result.working_directory_full_path)
            
            if self.console_display:
                # Count files to process
                files_to_process = (
                    sum(1 for r in result.generation_results.get('create_results', []) if r.get('success')) +
                    sum(1 for r in result.generation_results.get('update_results', []) if r.get('success'))
                )
                
                with self.console_display.phase_progress("4: Content Remediation", files_to_process * 3) as progress:
                    # Import here to avoid circular imports
                    from ..processors.phase4 import ContentRemediationProcessor
                    
                    # Create progress callback
                    def update_progress(step_name: str = None):
                        if step_name:
                            progress.update_func(1, description=step_name)
                        else:
                            progress.update_func(1)
                    
                    # Run remediation
                    processor = ContentRemediationProcessor(self.client, self.config, self.console_display)
                    processor.set_phase_step(4, 1)  # Phase 4, Step 1
                    processor.progress_callback = update_progress
                    
                    remediation_results = processor.process(
                        result.generation_results,
                        result.material_summaries,
                        self.config,
                        working_dir_path
                    )
            else:
                # Original flow without display
                from ..processors.phase4 import ContentRemediationProcessor
                processor = ContentRemediationProcessor(self.client, self.config, self.console_display)
                processor.set_phase_step(4, 1)
                
                remediation_results = processor.process(
                    result.generation_results,
                    result.material_summaries,
                    self.config,
                    working_dir_path
                )
            
            # Update result
            result.remediation_results = remediation_results
            result.remediation_ready = True
            
            # Always set to preview mode - actual application happens at the end
            result.generation_results['applied'] = False
            if self.console_display:
                self.console_display.show_status("Preview files updated with remediated content", "success")
            
            # Show phase summary
            if self.console_display:
                summary = remediation_results.get('summary', {})
                self.console_display.show_phase_summary("4: Content Remediation", {
                    "Files Processed": summary.get('total_files', 0),
                    "SEO Optimized": f"{summary.get('success_rate', {}).get('seo', 0) * 100:.0f}%",
                    "Security Checked": f"{summary.get('success_rate', {}).get('security', 0) * 100:.0f}%",
                    "Accuracy Validated": f"{summary.get('success_rate', {}).get('accuracy', 0) * 100:.0f}%",
                    "All Steps Complete": summary.get('all_steps_completed', 0)
                })
            
            logger.info(f"Phase 4 completed: {remediation_results.get('total_processed', 0)} files processed")
            
        except Exception as e:
            self._handle_phase4_error(result, e)
    
    def _apply_all_changes(self, result: Result) -> None:
        """Apply all changes from preview directories to the repository"""
        logger.info("=== Applying All Changes to Repository ===")
        
        if not result.generation_ready:
            logger.warning("No generated content to apply")
            return
            
        working_dir_path = Path(result.working_directory_full_path)
        applied_count = 0
        
        if self.console_display:
            self.console_display.show_separator()
            self.console_display.show_status("Applying changes to repository", "info")
        
        # Create a mapping of filenames to remediated content if remediation was run
        remediated_content = {}
        if hasattr(result, 'remediation_results') and result.remediation_results:
            for rem_result in result.remediation_results.get('remediation_results', []):
                if rem_result.get('accuracy_success') and rem_result.get('final_content'):
                    filename = rem_result['filename']
                    remediated_content[filename] = rem_result['final_content']
        
        # Apply CREATE files
        for create_result in result.generation_results.get('create_results', []):
            if create_result.get('success'):
                try:
                    action = create_result.get('action')
                    if not action:
                        continue
                        
                    target_filename = action.target_file  # Now guaranteed to be non-null
                    
                    # Get content from remediated content or preview file
                    content = None
                    
                    # First try remediated content
                    if target_filename in remediated_content:
                        content = remediated_content[target_filename]
                        logger.info(f"Using remediated content for: {target_filename}")
                    else:
                        # Try to read from preview location
                        preview_file = Path("./llm_outputs/preview/create") / Path(target_filename).name
                        if preview_file.exists():
                            content = read(preview_file)
                            logger.info(f"Reading from preview: {preview_file}")
                    
                    if not content:
                        logger.warning(f"No content found for CREATE: {target_filename}")
                        continue
                    
                    # Apply to repository
                    # Extract just the filename if it includes path components
                    just_filename = Path(target_filename).name
                    target_path = working_dir_path / just_filename
                    mkdir(target_path.parent)
                    write(target_path, content)
                    
                    if self.console_display:
                        self.console_display.show_status(f"Applied CREATE: {target_filename}", "success")
                    logger.info(f"Applied CREATE: {target_filename}")
                    applied_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to apply CREATE {target_filename}: {e}")
                    if self.console_display:
                        self.console_display.show_error(f"Failed to create {target_filename}: {e}")
        
        # Apply UPDATE files
        for update_result in result.generation_results.get('update_results', []):
            if update_result.get('success'):
                try:
                    action = update_result.get('action')
                    if not action:
                        continue
                        
                    target_filename = action.target_file  # Now guaranteed to be non-null
                    
                    # Get content from remediated content or preview file
                    content = None
                    
                    # First try remediated content
                    if target_filename in remediated_content:
                        content = remediated_content[target_filename]
                        logger.info(f"Using remediated content for: {target_filename}")
                    else:
                        # Try to read from preview location
                        preview_file = Path("./llm_outputs/preview/update") / Path(target_filename).name
                        if preview_file.exists():
                            content = read(preview_file)
                            logger.info(f"Reading from preview: {preview_file}")
                    
                    if not content:
                        logger.warning(f"No content found for UPDATE: {target_filename}")
                        continue
                    
                    # Apply to repository
                    # Extract just the filename if it includes path components
                    just_filename = Path(target_filename).name
                    target_path = working_dir_path / just_filename
                    write(target_path, content)
                    
                    if self.console_display:
                        self.console_display.show_status(f"Applied UPDATE: {target_filename}", "success")
                    logger.info(f"Applied UPDATE: {target_filename}")
                    applied_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to apply UPDATE {target_filename}: {e}")
                    if self.console_display:
                        self.console_display.show_error(f"Failed to update {target_filename}: {e}")
        
        # Apply TOC changes
        if hasattr(result, 'toc_results') and result.toc_results and result.toc_results.get('success'):
            try:
                content = None
                
                # Get TOC content from results or preview file
                if result.toc_results.get('content'):
                    content = result.toc_results['content']
                    logger.info("Using TOC content from results")
                else:
                    # Try to read from preview location
                    working_dir_name = Path(result.working_directory_full_path).name
                    preview_file = Path("./llm_outputs/preview/toc") / f"TOC_{working_dir_name}.yml"
                    
                    if preview_file.exists():
                        content = read(preview_file)
                        logger.info(f"Reading TOC from preview: {preview_file}")
                
                if content:
                    # Apply to repository
                    toc_path = working_dir_path / "TOC.yml"
                    write(toc_path, content)
                    
                    if self.console_display:
                        self.console_display.show_status("Applied TOC.yml updates", "success")
                    logger.info("Applied TOC.yml updates")
                    applied_count += 1
                else:
                    logger.warning("No TOC content found to apply")
                    
            except Exception as e:
                logger.error(f"Failed to apply TOC.yml: {e}")
                if self.console_display:
                    self.console_display.show_error(f"Failed to update TOC.yml: {e}")
        
        # Update result flags
        if result.generation_results:
            result.generation_results['applied'] = True
        if hasattr(result, 'toc_results') and result.toc_results:
            result.toc_results['applied'] = True
        
        # Show summary
        if self.console_display:
            self.console_display.show_separator()
            self.console_display.show_metric("Total files applied", str(applied_count))
            self.console_display.show_status("All changes applied to repository", "success")
        
        logger.info(f"Applied {applied_count} changes to repository")
    
    def _execute_phase5(self, result: Result) -> None:
        """Execute Phase 5: TOC Management"""
        logger.info("=== Phase 5: TOC Management ===")
        
        # Reset step counter for Phase 5
        step_tracker = get_step_tracker()
        step_tracker.reset_phase(5)
        
        try:
            # Get working directory path
            working_dir_path = Path(result.working_directory_full_path)
            
            if self.console_display:
                with self.console_display.phase_progress("5: TOC Management", 2) as progress:
                    # Run TOC management
                    progress.update_func(description="Analyzing TOC structure")
                    from ..processors.phase5 import TOCProcessor
                    toc_processor = TOCProcessor(self.client, self.config, self.console_display)
                    toc_processor.set_phase_step(5, 1)  # Phase 5, Step 1: TOC processing
                    toc_results = toc_processor.process(
                        working_dir_path,
                        result.generation_results.get('created_files', []),
                        result.generation_results.get('updated_files', []),
                        {
                            'decisions': result.content_strategy.decisions if hasattr(result.content_strategy, 'decisions') else []
                        }
                    )
                    progress.update_func(1)
                    
                    # Always save to preview - actual application happens at the end
                    progress.update_func(description="Saving TOC preview")
                    toc_results['applied'] = False
                    # Add info about which files were created vs updated
                    toc_results['created_files'] = result.generation_results.get('created_files', [])
                    toc_results['updated_files'] = result.generation_results.get('updated_files', [])
                    if toc_results.get('success') and not toc_results.get('changes_made'):
                        self.console_display.show_status("No TOC changes needed", "info")
                    elif toc_results.get('success'):
                        self.console_display.show_status("TOC preview saved", "success")
                    progress.update_func(1)
            else:
                # Original flow
                from ..processors.phase5 import TOCProcessor
                toc_results = self._run_toc_phase(
                    working_dir_path,
                    result.generation_results.get('created_files', []),
                    result.generation_results.get('updated_files', []),
                    result.content_strategy
                )
                
                # Always save to preview - actual application happens at the end
                toc_results['applied'] = False
                # Add info about which files were created vs updated
                toc_results['created_files'] = result.generation_results.get('created_files', [])
                toc_results['updated_files'] = result.generation_results.get('updated_files', [])
            
            # Update result
            result.toc_results = toc_results
            result.toc_ready = True
            
            # Show phase summary
            if self.console_display:
                entries_added = len(toc_results.get('entries_added', []))
                # Count actual new entries (from created files)
                new_entries = sum(1 for entry in toc_results.get('entries_added', []) 
                                 if entry in toc_results.get('created_files', []))
                verified_entries = entries_added - new_entries
                
                summary_data = {
                    "New Entries Added": new_entries,
                    "Existing Entries Verified": verified_entries,
                    "Preview Status": "TOC saved to preview" if toc_results.get('changes_made') else "No changes needed",
                    "Result": toc_results.get('message', 'Completed')
                }
                
                self.console_display.show_phase_summary("5: TOC Management", summary_data)
            
            logger.info(f"Phase 5 completed: {toc_results.get('message', 'No message')}")
            
        except Exception as e:
            self._handle_phase5_error(result, e)
    
    def _handle_phase5_error(self, result: Result, error: Exception) -> None:
        """Handle Phase 5 execution errors"""
        logger.error(f"Phase 5 failed: {error}")
        
        if self.console_display:
            self.console_display.show_error(str(error), "Phase 5 Failed")
        
        result.toc_results = None
        result.toc_ready = False
    
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
        return toc_processor.process(
            working_dir_path,
            created_files,
            updated_files,
            {
                'decisions': strategy.decisions if hasattr(strategy, 'decisions') else []
            }
        )
    

    
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
    
    def _handle_phase4_error(self, result: Result, error: Exception) -> None:
        """Handle Phase 4 execution errors"""
        logger.error(f"Phase 4 failed: {error}")
        
        if self.console_display:
            self.console_display.show_error(str(error), "Phase 4 Failed")
        
        result.remediation_results = None
        result.remediation_ready = False
