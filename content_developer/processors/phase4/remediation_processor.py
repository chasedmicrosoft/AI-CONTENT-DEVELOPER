"""
Content Remediation Processor - Phase 4 Main Orchestrator
Coordinates SEO, Security, and Accuracy remediation steps
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ...models import Config, Result
from ...utils import write, mkdir, read, get_step_tracker
from ..smart_processor import SmartProcessor
from .seo_processor import SEOProcessor
from .security_processor import SecurityProcessor
from .accuracy_processor import AccuracyProcessor

logger = logging.getLogger(__name__)


class ContentRemediationProcessor(SmartProcessor):
    """Main processor for Phase 5 content remediation"""
    
    def _process(self, generation_results: Dict, materials: List[Dict], 
                 config: Config, working_dir_path: Path) -> Dict:
        """Process all generated content through remediation steps
        
        Args:
            generation_results: Results from Phase 3 content generation
            materials: List of source materials
            config: Configuration object
            working_dir_path: Path to working directory
            
        Returns:
            Dictionary with remediation results
        """
        results = {
            'remediation_results': [],
            'total_processed': 0,
            'seo_optimized': 0,
            'security_remediated': 0,
            'accuracy_validated': 0,
            'summary': {}
        }
        
        # Get files to process (created and updated)
        files_to_process = []
        
        # Add created files - read from preview
        for create_result in generation_results.get('create_results', []):
            if create_result.get('success') and create_result.get('preview_path'):
                action = create_result.get('action')
                if action:
                    # Read content from preview file
                    preview_path = Path(create_result['preview_path'])
                    if preview_path.exists():
                        content = read(preview_path)
                        files_to_process.append({
                            'filename': action.filename or action.target_file or 'unknown',
                            'content': content,
                            'content_type': action.content_type or 'unknown',
                            'action_type': 'create',
                            'preview_path': str(preview_path)
                        })
        
        # Add updated files - read from preview
        for update_result in generation_results.get('update_results', []):
            if update_result.get('success') and update_result.get('preview_path'):
                action = update_result.get('action')
                if action:
                    # Read content from preview file
                    preview_path = Path(update_result['preview_path'])
                    if preview_path.exists():
                        content = read(preview_path)
                        files_to_process.append({
                            'filename': action.filename or action.target_file or 'unknown',
                            'content': content,
                            'content_type': action.content_type or 'unknown',
                            'action_type': 'update',
                            'preview_path': str(preview_path)
                        })
        
        # Process each file through all three steps
        step_tracker = get_step_tracker()
        for i, file_info in enumerate(files_to_process, 1):
            if self.console_display:
                self.console_display.show_separator()
                # Extract just the filename for display
                display_filename = Path(file_info['filename']).name
                self.console_display.show_metric(
                    "Processing", 
                    f"File {i}/{len(files_to_process)}: {display_filename} (from preview)"
                )
            
            try:
                # Process through each step
                file_result = self._process_file(file_info, materials, config, working_dir_path)
                results['remediation_results'].append(file_result)
                results['total_processed'] += 1
                
                # Update counters
                if file_result.get('seo_success'):
                    results['seo_optimized'] += 1
                if file_result.get('security_success'):
                    results['security_remediated'] += 1
                if file_result.get('accuracy_success'):
                    results['accuracy_validated'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing {file_info['filename']}: {e}")
                results['remediation_results'].append({
                    'filename': file_info['filename'],
                    'error': str(e),
                    'success': False
                })
        
        # Create summary
        results['summary'] = self._create_summary(results)
        
        return results
    
    def _process_file(self, file_info: Dict, materials: List[Dict], 
                     config: Config, working_dir_path: Path) -> Dict:
        """Process a single file through all remediation steps"""
        result = {
            'filename': file_info['filename'],
            'action_type': file_info['action_type'],
            'steps_completed': []
        }
        
        current_content = file_info['content']
        
        # Step 1: SEO Remediation
        if self.console_display:
            self.console_display.show_status("Step 1: SEO Remediation", "info")
        
        try:
            seo_processor = SEOProcessor(self.client, self.config, self.console_display)
            seo_processor.set_phase_step(4, 1)
            
            seo_content, seo_metadata = seo_processor.process(
                current_content, file_info, config
            )
            
            # Save SEO optimized version
            seo_path = self._save_remediated_content(
                seo_content, file_info['filename'], 'seo', 
                file_info['action_type'], working_dir_path
            )
            
            result['seo_success'] = True
            result['seo_metadata'] = seo_metadata
            result['seo_path'] = seo_path
            result['steps_completed'].append('seo')
            current_content = seo_content  # Use for next step
            
        except Exception as e:
            logger.error(f"SEO remediation failed for {file_info['filename']}: {e}")
            result['seo_success'] = False
            result['seo_error'] = str(e)
        
        # Step 2: Security Remediation
        if self.console_display:
            self.console_display.show_status("Step 2: Security Remediation", "info")
        
        try:
            security_processor = SecurityProcessor(self.client, self.config, self.console_display)
            security_processor.set_phase_step(4, 2)
            
            security_content, security_metadata = security_processor.process(
                current_content, file_info, config
            )
            
            # Save security remediated version
            security_path = self._save_remediated_content(
                security_content, file_info['filename'], 'security',
                file_info['action_type'], working_dir_path
            )
            
            result['security_success'] = True
            result['security_metadata'] = security_metadata
            result['security_path'] = security_path
            result['steps_completed'].append('security')
            current_content = security_content  # Use for next step
            
        except Exception as e:
            logger.error(f"Security remediation failed for {file_info['filename']}: {e}")
            result['security_success'] = False
            result['security_error'] = str(e)
        
        # Step 3: Technical Accuracy Validation
        if self.console_display:
            self.console_display.show_status("Step 3: Technical Accuracy Validation", "info")
        
        try:
            accuracy_processor = AccuracyProcessor(self.client, self.config, self.console_display)
            accuracy_processor.set_phase_step(4, 3)
            
            validated_content, accuracy_metadata = accuracy_processor.process(
                current_content, file_info, materials, config
            )
            
            # Save final validated version
            final_path = self._save_remediated_content(
                validated_content, file_info['filename'], 'final',
                file_info['action_type'], working_dir_path
            )
            
            result['accuracy_success'] = True
            result['accuracy_metadata'] = accuracy_metadata
            result['final_path'] = final_path
            result['steps_completed'].append('accuracy')
            result['final_content'] = validated_content
            
        except Exception as e:
            logger.error(f"Accuracy validation failed for {file_info['filename']}: {e}")
            result['accuracy_success'] = False
            result['accuracy_error'] = str(e)
        
        return result
    
    def _save_remediated_content(self, content: str, filename: str, step: str,
                                action_type: str, working_dir_path: Path) -> str:
        """Save remediated content to preview directory - overwrites the same file"""
        # Use the same preview directory structure as phase 3
        preview_dir = Path("./llm_outputs/preview") / action_type
        mkdir(preview_dir)
        
        # Extract just the filename from the full path
        filename_only = Path(filename).name
        
        # Overwrite the same preview file
        preview_path = preview_dir / filename_only
        write(preview_path, content)
        
        logger.info(f"Writing to preview ({step}): {preview_path}")
        if self.console_display:
            self.console_display.show_status(f"Writing to preview: {action_type}/{filename_only} ({step})", "info")
        return str(preview_path)
    
    def _create_summary(self, results: Dict) -> Dict:
        """Create summary of remediation results"""
        total = results['total_processed']
        
        return {
            'success_rate': {
                'seo': results['seo_optimized'] / total if total > 0 else 0,
                'security': results['security_remediated'] / total if total > 0 else 0,
                'accuracy': results['accuracy_validated'] / total if total > 0 else 0
            },
            'total_files': total,
            'all_steps_completed': sum(
                1 for r in results['remediation_results'] 
                if len(r.get('steps_completed', [])) == 3
            ),
            'issues_found': {
                'seo': sum(
                    len(r.get('seo_metadata', {}).get('seo_improvements', []))
                    for r in results['remediation_results']
                ),
                'security': sum(
                    len(r.get('security_metadata', {}).get('security_issues_found', []))
                    for r in results['remediation_results']
                ),
                'accuracy': sum(
                    len(r.get('accuracy_metadata', {}).get('accuracy_issues', []))
                    for r in results['remediation_results']
                )
            }
        }
    
    def process(self, *args, **kwargs):
        """Public interface for processing"""
        return self._process(*args, **kwargs) 