"""
Helper classes for phase execution to reduce code duplication.
"""
import logging
from typing import Dict, List, Tuple, Callable, Optional, Any
from pathlib import Path

from ..models import Result
from ..utils.step_tracker import get_step_tracker

logger = logging.getLogger(__name__)


class PhaseErrorHandler:
    """Handles error management for phase execution"""
    
    def __init__(self, console_display=None):
        self.console_display = console_display
    
    def handle_error(self, phase: int, result: Result, error: Exception) -> None:
        """Generic error handler for any phase"""
        phase_name = f"Phase {phase}"
        logger.error(f"{phase_name} failed: {error}")
        
        if self.console_display:
            self.console_display.show_error(str(error), f"{phase_name} Failed")
        
        # Update result based on phase
        self._update_result_for_error(phase, result, error)
    
    def _update_result_for_error(self, phase: int, result: Result, error: Exception) -> None:
        """Update result object based on phase failure"""
        if phase == 2:
            # Special handling for phase 2 - needs strategy confirmator
            result.strategy_ready = False
        elif phase == 3:
            result.generation_results = None
            result.generation_ready = False
        elif phase == 4:
            result.remediation_results = None
            result.remediation_ready = False
        elif phase == 5:
            result.toc_results = None
            result.toc_ready = False


class PhaseProgressManager:
    """Manages progress tracking for phase execution"""
    
    def __init__(self, console_display=None):
        self.console_display = console_display
        self.context = {}
    
    def execute_steps(self, phase_name: str, steps: List[Tuple[str, Callable]], 
                     context: Dict = None) -> Dict:
        """Execute steps with optional progress tracking"""
        # Use provided context or create new one
        self.context = context if context is not None else {}
        
        if not self.console_display:
            return self._execute_without_progress(steps)
        
        return self._execute_with_progress(phase_name, steps)
    
    def _execute_with_progress(self, phase_name: str, steps: List[Tuple]) -> Dict:
        """Execute steps with progress display"""
        with self.console_display.phase_progress(phase_name, len(steps)) as progress:
            for description, step_func in steps:
                progress.update_func(description=description)
                result = self._execute_step(step_func)
                progress.update_func(1)
            
            return self.context
    
    def _execute_without_progress(self, steps: List[Tuple]) -> Dict:
        """Execute steps without progress display"""
        for _, step_func in steps:
            self._execute_step(step_func)
        
        return self.context
    
    def _execute_step(self, step_func: Callable) -> Any:
        """Execute a single step and store result in context"""
        result = step_func()
        
        if isinstance(result, dict):
            self.context.update(result)
        else:
            # Map function names to context keys
            key_mapping = {
                '_clone_repository': 'repo_path',
                '_process_materials': 'materials',
                '_analyze_structure': 'structure',
                '_select_directory': 'directory_selection',
                '_discover_content': 'chunks',
                '_analyze_gaps': 'strategy'
            }
            
            key = key_mapping.get(step_func.__name__, step_func.__name__.replace('_', ''))
            self.context[key] = result
        
        return result


class PhaseResultUpdater:
    """Handles result object updates for different phases"""
    
    @staticmethod
    def update_phase1_result(result: Result, **kwargs) -> None:
        """Update result for phase 1 completion"""
        for key, value in kwargs.items():
            setattr(result, key, value)
    
    @staticmethod
    def update_phase2_result(result: Result, strategy) -> None:
        """Update result for phase 2 completion"""
        result.content_strategy = strategy
        result.strategy_ready = strategy.confidence > 0
    
    @staticmethod
    def update_phase3_result(result: Result, generation_results: Dict) -> None:
        """Update result for phase 3 completion"""
        result.generation_results = generation_results
        result.generation_ready = True
    
    @staticmethod
    def update_phase4_result(result: Result, remediation_results: Dict) -> None:
        """Update result for phase 4 completion"""
        result.remediation_results = remediation_results
        result.remediation_ready = True
        result.generation_results['applied'] = False
    
    @staticmethod
    def update_phase5_result(result: Result, toc_results: Dict) -> None:
        """Update result for phase 5 completion"""
        result.toc_results = toc_results
        result.toc_ready = True


class PhaseSummaryDisplay:
    """Handles phase summary displays"""
    
    def __init__(self, console_display=None):
        self.console_display = console_display
    
    def show_phase1_summary(self, confirmed: Dict, setup_result: Dict, materials: List) -> None:
        """Show phase 1 summary"""
        if not self.console_display:
            return
        
        self.console_display.show_phase_summary("1: Repository Analysis", {
            "Selected Directory": confirmed['working_directory'],
            "Confidence": f"{confirmed['confidence']:.1%}",
            "Materials Processed": len(materials),
            "Markdown Files": setup_result.get('markdown_count', 0)
        })
    
    def show_phase2_summary(self, strategy, chunks: List) -> None:
        """Show phase 2 summary"""
        if not self.console_display:
            return
        
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
    
    def show_phase3_summary(self, generation_results: Dict) -> None:
        """Show phase 3 summary"""
        if not self.console_display:
            return
        
        create_count = sum(1 for r in generation_results.get('create_results', []) 
                          if r.get('success'))
        update_count = sum(1 for r in generation_results.get('update_results', []) 
                          if r.get('success'))
        skip_count = len(generation_results.get('skip_results', []))
        
        self.console_display.show_phase_summary("3: Content Generation", {
            "Files Created (Preview)": create_count,
            "Files Updated (Preview)": update_count,
            "Files Skipped": skip_count,
            "Status": "All content saved to preview directory"
        })
    
    def show_phase4_summary(self, remediation_results: Dict) -> None:
        """Show phase 4 summary"""
        if not self.console_display:
            return
        
        summary = remediation_results.get('summary', {})
        
        self.console_display.show_phase_summary("4: Content Remediation", {
            "Files Processed": summary.get('total_files', 0),
            "SEO Optimized": f"{summary.get('success_rate', {}).get('seo', 0) * 100:.0f}%",
            "Security Checked": f"{summary.get('success_rate', {}).get('security', 0) * 100:.0f}%",
            "Accuracy Validated": f"{summary.get('success_rate', {}).get('accuracy', 0) * 100:.0f}%",
            "All Steps Complete": summary.get('all_steps_completed', 0)
        })
    
    def show_phase5_summary(self, toc_results: Dict) -> None:
        """Show phase 5 summary"""
        if not self.console_display:
            return
        
        summary_data = {
            "TOC Files Analyzed": len(toc_results.get('toc_files', [])),
            "TOC Files Updated": len([f for f in toc_results.get('toc_files', []) 
                                     if f.get('updated')]),
            "New Entries Added": sum(len(f.get('new_entries', [])) 
                                    for f in toc_results.get('toc_files', [])),
            "Status": "Success" if toc_results.get('success') else "Failed"
        }
        
        self.console_display.show_phase_summary("5: TOC Management", summary_data)


class PhaseTracker:
    """Manages phase tracking"""
    
    @staticmethod
    def reset_phase(phase: int) -> None:
        """Reset step tracker for a phase"""
        step_tracker = get_step_tracker()
        step_tracker.reset_phase(phase)
    
    @staticmethod
    def log_phase_start(phase: int, name: str) -> None:
        """Log phase start"""
        logger.info(f"=== Phase {phase}: {name} ===")
        PhaseTracker.reset_phase(phase) 