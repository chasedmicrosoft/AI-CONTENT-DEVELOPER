"""
Phase execution logic for content development workflow.
"""
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from ..models import Result
from ..processors import (
    ContentDiscoveryProcessor, ContentStrategyProcessor, DirectoryDetector,
    MaterialProcessor, TOCProcessor
)
from ..generation import ContentGenerator
from ..utils.step_tracker import get_step_tracker

# Import helper classes
from .phase_helpers import (
    PhaseErrorHandler, PhaseProgressManager, PhaseResultUpdater,
    PhaseSummaryDisplay, PhaseTracker
)

logger = logging.getLogger(__name__)


class PhaseExecutor:
    """Handles execution of individual phases in the content development workflow"""
    
    def __init__(self, orchestrator):
        """Initialize with reference to main orchestrator"""
        self.orchestrator = orchestrator
        self.config = orchestrator.config
        self.client = orchestrator.client
        self.console_display = orchestrator.console_display
        self.repo_manager = orchestrator.repo_manager
        self.dir_confirmator = orchestrator.dir_confirmator
        self.strategy_confirmator = orchestrator.strategy_confirmator
        
        # Initialize helpers
        self.error_handler = PhaseErrorHandler(self.console_display)
        self.progress_manager = PhaseProgressManager(self.console_display)
        self.summary_display = PhaseSummaryDisplay(self.console_display)
        self.context = {}  # Shared context for step execution
    
    def execute_phase1(self) -> Result:
        """Execute Phase 1: Repository Analysis & Directory Selection"""
        PhaseTracker.log_phase_start(1, "Repository Analysis")
        
        steps = [
            ("Cloning repository", self._clone_repository),
            ("Processing materials", self._process_materials),
            ("Analyzing structure", self._analyze_structure),
            ("Selecting directory", self._select_directory)
        ]
        
        self.context = self.progress_manager.execute_steps("1: Repository Analysis", steps, self.context)
        
        # Validate and confirm
        if self.config.auto_confirm:
            self._validate_auto_confirm_result()
        
        confirmed = self._confirm_directory()
        setup_result = self._setup_directory_phase1(self.context['repo_path'], confirmed['working_directory'])
        
        # Create result
        result = self._create_phase1_result(confirmed, setup_result)
        
        # Show summary
        self.summary_display.show_phase1_summary(confirmed, setup_result, self.context['materials'])
        
        return result
    
    def execute_phase2(self, result: Result) -> None:
        """Execute Phase 2: Content Strategy Analysis"""
        PhaseTracker.log_phase_start(2, "Content Strategy Analysis")
        
        try:
            working_dir_path = Path(result.working_directory_full_path)
            
            steps = [
                ("Discovering content", lambda: self._discover_content(working_dir_path, result)),
                ("Analyzing gaps", lambda: self._analyze_gaps(result))
            ]
            
            self.context = {}
            self.context = self.progress_manager.execute_steps("2: Content Strategy", steps, self.context)
            strategy = self.context['strategy']
            
            # Display and confirm
            self._display_strategy(strategy)
            
            if not self.config.auto_confirm and not self._confirm_strategy_phase2(strategy):
                self._handle_strategy_rejection(result)
                return
            
            # Update result
            PhaseResultUpdater.update_phase2_result(result, strategy)
            
            # Show summary
            self.summary_display.show_phase2_summary(strategy, self.context['chunks'])
            
        except Exception as e:
            self._handle_phase2_error(result, e)
    
    def execute_phase3(self, result: Result) -> None:
        """Execute Phase 3: Content Generation"""
        PhaseTracker.log_phase_start(3, "Content Generation")
        
        try:
            working_dir_path = Path(result.working_directory_full_path)
            active_decisions = self._filter_active_decisions(result.content_strategy.decisions)
            
            # Generate content
            generation_results = self._generate_content(result, working_dir_path, active_decisions)
            
            # Update result
            PhaseResultUpdater.update_phase3_result(result, generation_results)
            
            # Show status and summary
            self._show_phase3_status()
            self.summary_display.show_phase3_summary(generation_results)
            self._log_generation_summary(generation_results)
            
        except Exception as e:
            self.error_handler.handle_error(3, result, e)
    
    def execute_phase4(self, result: Result) -> None:
        """Execute Phase 4: Content Remediation"""
        PhaseTracker.log_phase_start(4, "Content Remediation")
        
        try:
            working_dir_path = Path(result.working_directory_full_path)
            files_to_process = self._count_files_to_remediate(result.generation_results)
            
            # Run remediation
            remediation_results = self._run_remediation(result, working_dir_path, files_to_process)
            
            # Update result
            PhaseResultUpdater.update_phase4_result(result, remediation_results)
            
            # Show status and summary
            self._show_phase4_status()
            self.summary_display.show_phase4_summary(remediation_results)
            
        except Exception as e:
            self.error_handler.handle_error(4, result, e)
    
    def execute_phase5(self, result: Result) -> None:
        """Execute Phase 5: TOC Management"""
        PhaseTracker.log_phase_start(5, "TOC Management")
        
        try:
            working_dir_path = Path(result.working_directory_full_path)
            
            # Get file lists
            created_files, updated_files = self._get_generated_files(result)
            
            # Run TOC management
            toc_results = self._run_toc_management(
                working_dir_path, created_files, updated_files, result.content_strategy
            )
            
            # Update result
            PhaseResultUpdater.update_phase5_result(result, toc_results)
            
            # Show summary
            self.summary_display.show_phase5_summary(toc_results)
            
        except Exception as e:
            self.error_handler.handle_error(5, result, e)
    
    # Phase 1 specific methods
    def _clone_repository(self) -> Path:
        """Clone or update repository"""
        return self.repo_manager.clone_or_update(self.config.repo_url, self.config.work_dir)
    
    def _process_materials(self) -> List[Dict]:
        """Process support materials"""
        repo_path = self.context['repo_path']
        processor = MaterialProcessor(self.client, self.config, self.console_display)
        processor.set_phase_step(1, 1)
        return processor.process(self.config.support_materials, repo_path)
    
    def _analyze_structure(self) -> str:
        """Analyze repository structure"""
        repo_path = self.context['repo_path']
        total_items = sum(1 for _ in repo_path.rglob("*") if not str(_).startswith('.'))
        
        if total_items > 5000:
            logger.info(f"Large repository detected ({total_items} items)")
            return self.repo_manager.get_directory_structure(repo_path, self.config.max_repo_depth)
        
        return self.repo_manager.get_structure(repo_path, self.config.max_repo_depth)
    
    def _select_directory(self) -> Dict:
        """Select working directory using LLM"""
        try:
            detector = DirectoryDetector(self.client, self.config, self.console_display)
            detector.set_phase_step(1, 1)
            llm_result = detector.process(
                self.context['repo_path'], 
                self.context['structure'], 
                self.context['materials']
            )
            return {
                'directory_selection': {
                    'llm_result': llm_result, 
                    'llm_failed': False, 
                    'error': ""
                }
            }
        except Exception as e:
            logger.warning(f"LLM failed: {e}")
            return {
                'directory_selection': {
                    'llm_result': None, 
                    'llm_failed': True, 
                    'error': str(e)
                }
            }
    
    def _validate_auto_confirm_result(self) -> None:
        """Validate directory selection in auto-confirm mode"""
        directory_result = self.context['directory_selection']
        
        if directory_result['llm_failed']:
            self._raise_auto_confirm_error(
                f"Auto-confirm enabled but LLM failed: {directory_result['error']}"
            )
        
        llm_result = directory_result['llm_result']
        
        if not llm_result.get('working_directory'):
            error_msg = llm_result.get('error', 'LLM returned empty directory')
            self._raise_auto_confirm_error(
                f"Auto-confirm enabled but directory selection failed: {error_msg}"
            )
        
        if llm_result.get('confidence', 0) < 0.7:
            logger.error(f"Directory selection confidence too low: {llm_result.get('confidence', 0):.2f}")
            logger.error(f"Selected directory: {llm_result.get('working_directory')}")
            self._raise_auto_confirm_error(
                f"Auto-confirm enabled but confidence too low: {llm_result.get('confidence', 0):.2f}"
            )
    
    def _raise_auto_confirm_error(self, message: str) -> None:
        """Log and raise auto-confirm error"""
        logger.error(message)
        raise RuntimeError(message)
    
    def _confirm_directory(self) -> Dict:
        """Confirm directory selection"""
        dir_result = self.context.get('directory_selection', {})
        return self.dir_confirmator.confirm(
            dir_result.get('llm_result'),
            self.context['structure'],
            dir_result.get('llm_failed', False),
            dir_result.get('error', '')
        )
    
    def _setup_directory_phase1(self, repo_path: Path, working_dir: str) -> Dict:
        """Setup directory for phase 1"""
        return self.orchestrator._setup_directory(repo_path, working_dir)
    
    def _create_phase1_result(self, confirmed: Dict, setup_result: Dict) -> Result:
        """Create Result object from Phase 1 outputs"""
        return Result(
            working_directory=confirmed['working_directory'],
            justification=confirmed['justification'],
            confidence=confirmed['confidence'],
            repo_url=self.config.repo_url,
            repo_path=str(self.context['repo_path']),
            material_summaries=self.context['materials'],
            content_goal=self.config.content_goal,
            service_area=self.config.service_area,
            directory_ready=setup_result['success'],
            working_directory_full_path=setup_result.get('full_path'),
            setup_error=setup_result.get('error')
        )
    
    # Phase 2 specific methods
    def _discover_content(self, working_dir_path: Path, result: Result) -> Dict:
        """Discover content chunks"""
        processor = ContentDiscoveryProcessor(self.client, self.config, self.console_display)
        processor.set_phase_step(2, 1)
        
        chunks = processor.process(
            working_dir_path,
            self.repo_manager.extract_name(self.config.repo_url),
            result.working_directory
        )
        
        logger.info(f"ContentDiscoveryProcessor returned {len(chunks)} chunks")
        return {'chunks': chunks}
    
    def _analyze_gaps(self, result: Result) -> Dict:
        """Analyze content gaps and generate strategy"""
        chunks = self.context.get('chunks', [])
        
        processor = ContentStrategyProcessor(self.client, self.config, self.console_display)
        processor.set_phase_step(2, 2)
        
        strategy = processor.process(
            chunks,
            result.material_summaries,
            self.config,
            self.repo_manager.extract_name(self.config.repo_url),
            result.working_directory
        )
        
        logger.info(f"ContentStrategyProcessor returned strategy: {strategy.summary[:50]}...")
        return {'strategy': strategy}
    
    def _display_strategy(self, strategy) -> None:
        """Display strategy decisions"""
        if not self.console_display:
            return
        
        for decision in strategy.decisions:
            self.console_display.show_strategy_decision(decision)
        
        self.console_display.show_separator()
        self.console_display.show_metric("Strategy Confidence", f"{strategy.confidence:.0%}")
    
    def _confirm_strategy_phase2(self, strategy) -> bool:
        """Confirm strategy for phase 2"""
        return self.orchestrator._confirm_strategy(strategy)
    
    def _handle_strategy_rejection(self, result: Result) -> None:
        """Handle strategy rejection by user"""
        if self.console_display:
            self.console_display.show_warning("Strategy rejected by user")
        
        result.success = False
        result.error = "User rejected the strategy"
    
    def _handle_phase2_error(self, result: Result, error: Exception) -> None:
        """Handle Phase 2 execution errors with special strategy handling"""
        import traceback
        logger.error(f"Phase 2 failed with exception: {type(error).__name__}: {error}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        if self.console_display:
            self.console_display.show_error(str(error), "Phase 2 Failed")
        
        # Special handling for phase 2
        error_strategy = self.strategy_confirmator.confirm(None, True, str(error))
        result.content_strategy = error_strategy
        result.strategy_ready = False
    
    # Phase 3 specific methods
    def _filter_active_decisions(self, decisions: List) -> List:
        """Filter out SKIP decisions"""
        return [d for d in decisions if d.action != 'SKIP']
    
    def _generate_content(self, result: Result, working_dir_path: Path, 
                         active_decisions: List) -> Dict:
        """Generate content for active decisions"""
        generator = ContentGenerator(self.client, self.config, self.console_display)
        generator.set_phase_step(3, 1)
        
        if self.console_display:
            with self.console_display.phase_progress(
                "3: Content Generation", len(active_decisions)
            ) as progress:
                def update_progress(action_name: str):
                    progress.update_func(1, description=f"Processing: {action_name}")
                
                generator.progress_callback = update_progress
                
                return generator.process(
                    result.content_strategy,
                    result.material_summaries,
                    working_dir_path,
                    self.repo_manager.extract_name(self.config.repo_url),
                    result.working_directory
                )
        else:
            return generator.process(
                result.content_strategy,
                result.material_summaries,
                working_dir_path,
                self.repo_manager.extract_name(self.config.repo_url),
                result.working_directory
            )
    
    def _show_phase3_status(self) -> None:
        """Show phase 3 status message"""
        if self.console_display:
            self.console_display.show_status("Content generated - proceed to remediation phase", "info")
    
    def _log_generation_summary(self, generation_results: Dict) -> None:
        """Log content generation summary"""
        create_count = sum(1 for r in generation_results.get('create_results', []) if r.get('success'))
        update_count = sum(1 for r in generation_results.get('update_results', []) if r.get('success'))
        logger.info(f"Phase 3 completed: Generated {create_count} new files, updated {update_count} files")
    
    # Phase 4 specific methods
    def _count_files_to_remediate(self, generation_results: Dict) -> int:
        """Count files that need remediation"""
        return (
            sum(1 for r in generation_results.get('create_results', []) if r.get('success')) +
            sum(1 for r in generation_results.get('update_results', []) if r.get('success'))
        )
    
    def _run_remediation(self, result: Result, working_dir_path: Path, 
                        files_to_process: int) -> Dict:
        """Run content remediation"""
        from ..processors.phase4 import ContentRemediationProcessor
        
        processor = ContentRemediationProcessor(self.client, self.config, self.console_display)
        processor.set_phase_step(4, 1)
        
        if self.console_display:
            with self.console_display.phase_progress(
                "4: Content Remediation", files_to_process * 3
            ) as progress:
                def update_progress(step_name: str = None):
                    progress.update_func(1, description=step_name or "Processing")
                
                processor.progress_callback = update_progress
                
                return processor.process(
                    result.generation_results,
                    result.material_summaries,
                    self.config,
                    working_dir_path
                )
        else:
            return processor.process(
                result.generation_results,
                result.material_summaries,
                self.config,
                working_dir_path
            )
    
    def _show_phase4_status(self) -> None:
        """Show phase 4 status message"""
        if self.console_display:
            self.console_display.show_status("Preview files updated with remediated content", "success")
    
    # Phase 5 specific methods
    def _get_generated_files(self, result: Result) -> Tuple[List, List]:
        """Get lists of created and updated files"""
        created_files = []
        updated_files = []
        
        # Get remediated content if available
        remediated_content = self._build_remediated_content_map(result)
        
        # Collect created files
        for create_result in result.generation_results.get('create_results', []):
            if create_result.get('success'):
                action = create_result.get('action')
                if action:
                    filename = getattr(action, 'filename', None) or getattr(action, 'target_file', None) or 'unknown'
                    # Use preview_path or construct path from action
                    path = create_result.get('preview_path') or action.target_file
                    created_files.append({
                        'path': path,
                        'content': remediated_content.get(filename, create_result['content'])
                    })
        
        # Collect updated files  
        for update_result in result.generation_results.get('update_results', []):
            if update_result.get('success'):
                action = update_result.get('action')
                if action:
                    filename = getattr(action, 'filename', None) or getattr(action, 'target_file', None) or 'unknown'
                    # Use preview_path or construct path from action
                    path = update_result.get('preview_path') or action.target_file
                    updated_files.append({
                        'path': path,
                        'content': remediated_content.get(filename, update_result.get('updated_content', update_result.get('content')))
                    })
        
        return created_files, updated_files
    
    def _build_remediated_content_map(self, result: Result) -> Dict[str, str]:
        """Build mapping of filenames to remediated content"""
        remediated_content = {}
        
        if hasattr(result, 'remediation_results') and result.remediation_results:
            for rem_result in result.remediation_results.get('remediation_results', []):
                if rem_result.get('accuracy_success') and rem_result.get('final_content'):
                    remediated_content[rem_result['filename']] = rem_result['final_content']
        
        return remediated_content
    
    def _run_toc_management(self, working_dir_path: Path, created_files: List,
                           updated_files: List, strategy) -> Dict:
        """Run TOC management phase"""
        return self.orchestrator._run_toc_phase(
            working_dir_path, created_files, updated_files, strategy
        ) 