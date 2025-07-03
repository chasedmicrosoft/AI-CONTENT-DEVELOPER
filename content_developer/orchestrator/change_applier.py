"""
Change application logic for content development workflow.
"""
import logging
from pathlib import Path
from typing import Dict, Optional, List

from ..models import Result
from ..utils import write, mkdir, read

logger = logging.getLogger(__name__)


class ChangeApplier:
    """Handles application of generated changes to the repository"""
    
    def __init__(self, console_display=None):
        """Initialize with optional console display"""
        self.console_display = console_display
        self.applied_count = 0
    
    def apply_all_changes(self, result: Result) -> None:
        """Apply all changes from preview directories to the repository"""
        logger.info("=== Applying All Changes to Repository ===")
        
        if not self._validate_generation_ready(result):
            return
        
        working_dir_path = Path(result.working_directory_full_path)
        self.applied_count = 0
        
        self._show_start_status()
        
        # Build remediated content map
        remediated_map = self._build_remediated_content_map(result)
        
        # Apply changes in order
        self._apply_create_files(result, remediated_map, working_dir_path)
        self._apply_update_files(result, remediated_map, working_dir_path)
        self._apply_toc_changes(result, working_dir_path)
        
        # Finalize
        self._update_result_flags(result)
        self._show_final_status()
    
    def _validate_generation_ready(self, result: Result) -> bool:
        """Validate that generation is ready to apply"""
        if not result.generation_ready:
            logger.warning("No generated content to apply")
            return False
        return True
    
    def _show_start_status(self) -> None:
        """Show starting status message"""
        if self.console_display:
            self.console_display.show_separator()
            self.console_display.show_status("Applying changes to repository", "info")
    
    def _build_remediated_content_map(self, result: Result) -> Dict[str, str]:
        """Build mapping of filenames to remediated content"""
        remediated_content = {}
        
        if not hasattr(result, 'remediation_results') or not result.remediation_results:
            return remediated_content
        
        for rem_result in result.remediation_results.get('remediation_results', []):
            if rem_result.get('accuracy_success') and rem_result.get('final_content'):
                filename = rem_result['filename']
                remediated_content[filename] = rem_result['final_content']
        
        return remediated_content
    
    def _apply_create_files(self, result: Result, remediated_map: Dict[str, str], 
                           working_dir_path: Path) -> None:
        """Apply CREATE file operations"""
        create_results = result.generation_results.get('create_results', [])
        
        for create_result in create_results:
            if create_result.get('success'):
                self._apply_single_create(create_result, remediated_map, working_dir_path)
    
    def _apply_single_create(self, create_result: Dict, remediated_map: Dict[str, str],
                            working_dir_path: Path) -> None:
        """Apply a single CREATE operation"""
        try:
            action = create_result.get('action')
            if not action:
                return
            
            target_filename = action.target_file
            content = self._get_content_for_file(target_filename, remediated_map, "create")
            
            if not content:
                logger.warning(f"No content found for CREATE: {target_filename}")
                return
            
            # Apply to repository
            target_path = self._get_target_path(working_dir_path, target_filename)
            self._write_file_with_mkdir(target_path, content)
            
            self._log_success("CREATE", target_filename)
            self.applied_count += 1
            
        except Exception as e:
            self._log_error("CREATE", target_filename, e)
    
    def _apply_update_files(self, result: Result, remediated_map: Dict[str, str],
                           working_dir_path: Path) -> None:
        """Apply UPDATE file operations"""
        update_results = result.generation_results.get('update_results', [])
        
        for update_result in update_results:
            if update_result.get('success'):
                self._apply_single_update(update_result, remediated_map, working_dir_path)
    
    def _apply_single_update(self, update_result: Dict, remediated_map: Dict[str, str],
                            working_dir_path: Path) -> None:
        """Apply a single UPDATE operation"""
        try:
            action = update_result.get('action')
            if not action:
                return
            
            target_filename = action.target_file
            content = self._get_content_for_file(target_filename, remediated_map, "update")
            
            if not content:
                logger.warning(f"No content found for UPDATE: {target_filename}")
                return
            
            # Apply to repository
            target_path = self._get_target_path(working_dir_path, target_filename)
            self._write_file_with_mkdir(target_path, content)
            
            self._log_success("UPDATE", target_filename)
            self.applied_count += 1
            
        except Exception as e:
            self._log_error("UPDATE", target_filename, e)
    
    def _apply_toc_changes(self, result: Result, working_dir_path: Path) -> None:
        """Apply TOC.yml changes"""
        if not self._has_toc_changes(result):
            return
        
        try:
            content = self._get_toc_content(result, working_dir_path)
            
            if not content:
                logger.warning("No TOC content found to apply")
                return
            
            # Apply to repository
            toc_path = working_dir_path / "TOC.yml"
            write(toc_path, content)
            
            self._log_success("TOC", "TOC.yml")
            self.applied_count += 1
            
        except Exception as e:
            self._log_error("TOC", "TOC.yml", e)
    
    def _get_content_for_file(self, filename: str, remediated_map: Dict[str, str], 
                             action_type: str) -> Optional[str]:
        """Get content for a file from remediated map or preview"""
        # First try remediated content
        if filename in remediated_map:
            logger.info(f"Using remediated content for: {filename}")
            return remediated_map[filename]
        
        # Try to read from preview location
        preview_file = Path(f"./llm_outputs/preview/{action_type}") / Path(filename).name
        if preview_file.exists():
            logger.info(f"Reading from preview: {preview_file}")
            return read(preview_file)
        
        return None
    
    def _get_toc_content(self, result: Result, working_dir_path: Path) -> Optional[str]:
        """Get TOC content from results or preview file"""
        # Try from results first
        if result.toc_results.get('content'):
            logger.info("Using TOC content from results")
            return result.toc_results['content']
        
        # Try to read from preview location
        working_dir_name = Path(working_dir_path).name
        preview_file = Path("./llm_outputs/preview/toc") / f"TOC_{working_dir_name}.yml"
        
        if preview_file.exists():
            logger.info(f"Reading TOC from preview: {preview_file}")
            return read(preview_file)
        
        return None
    
    def _get_target_path(self, working_dir_path: Path, filename: str) -> Path:
        """Get target path for a file, extracting just the filename"""
        just_filename = Path(filename).name
        return working_dir_path / just_filename
    
    def _write_file_with_mkdir(self, target_path: Path, content: str) -> None:
        """Write file, creating parent directories if needed"""
        mkdir(target_path.parent)
        write(target_path, content)
    
    def _has_toc_changes(self, result: Result) -> bool:
        """Check if there are TOC changes to apply"""
        return (
            hasattr(result, 'toc_results') and 
            result.toc_results and 
            result.toc_results.get('success')
        )
    
    def _update_result_flags(self, result: Result) -> None:
        """Update result flags to indicate changes were applied"""
        if result.generation_results:
            result.generation_results['applied'] = True
        
        if hasattr(result, 'toc_results') and result.toc_results:
            result.toc_results['applied'] = True
    
    def _show_final_status(self) -> None:
        """Show final status summary"""
        if not self.console_display:
            return
        
        self.console_display.show_separator()
        self.console_display.show_metric("Total files applied", str(self.applied_count))
        self.console_display.show_status("All changes applied to repository", "success")
        
        logger.info(f"Applied {self.applied_count} changes to repository")
    
    def _log_success(self, operation: str, filename: str) -> None:
        """Log successful operation"""
        message = f"Applied {operation}: {filename}"
        
        if self.console_display:
            self.console_display.show_status(message, "success")
        
        logger.info(message)
    
    def _log_error(self, operation: str, filename: str, error: Exception) -> None:
        """Log operation error"""
        message = f"Failed to apply {operation} {filename}: {error}"
        
        logger.error(message)
        
        if self.console_display:
            self.console_display.show_error(f"Failed to {operation.lower()} {filename}: {error}") 