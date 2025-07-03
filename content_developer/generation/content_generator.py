"""
Main content generator orchestrator for Phase 3
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable

from ..models import ContentStrategy, DocumentChunk, ContentDecision
from ..processors.smart_processor import SmartProcessor
from ..processors import ContentDiscoveryProcessor
from ..processors.generation import ContentGenerationProcessor
from ..utils import write, mkdir, read
from ..utils.step_tracker import get_step_tracker

logger = logging.getLogger(__name__)


class ContentGenerator(SmartProcessor):
    """Main orchestrator for Phase 3 content generation"""
    
    def __init__(self, *args, **kwargs):
        """Initialize content generator"""
        super().__init__(*args, **kwargs)
        self.progress_callback = None  # For progress updates
    
    def _process(self, strategy: ContentStrategy, materials: List[Dict], 
                 working_dir_path: Path, repo_name: str, working_directory: str) -> Dict:
        """Process content generation based on strategy"""
        logger.info(f"Starting content generation with {len(strategy.decisions)} decisions")
        
        results = {
            'create_results': [],
            'update_results': [],
            'skip_results': [],
            'created_files': [],
            'updated_files': []
        }
        
        # Load existing chunks for UPDATE actions
        chunks = []
        if any(d.action == 'UPDATE' for d in strategy.decisions):
            if self.console_display:
                self.console_display.show_operation("Loading existing content")
            chunks = self._load_existing_chunks(working_dir_path, repo_name, working_directory)
        
        # Use the new generation processor
        generation_processor = ContentGenerationProcessor(self.client, self.config, self.console_display)
        if hasattr(self, 'current_phase') and self.current_phase:
            generation_processor.set_phase_step(self.current_phase, 1)
        
        # Process each decision
        for i, decision in enumerate(strategy.decisions, 1):
            logger.info(f"Processing decision {i}/{len(strategy.decisions)}: "
                       f"{decision.action} - {getattr(decision, 'filename', getattr(decision, 'target_file', 'N/A'))}")
            
            # Update progress if callback provided
            if self.progress_callback:
                action_name = getattr(decision, 'file_title', getattr(decision, 'filename', f"Decision {i}"))
                self.progress_callback(action_name)
            
            # Process the decision
            content, metadata = generation_processor.process(
                decision, materials, chunks, self.config, repo_name, working_directory
            )
            
            # Handle results based on action type and status
            if decision.action == "SKIP" or metadata.get('status') == 'skipped_insufficient_materials':
                results['skip_results'].append(metadata)
            elif decision.action == "CREATE":
                # Save preview file for CREATE
                preview_path = None
                if content:
                    preview_dir = Path("./llm_outputs/preview/create")
                    mkdir(preview_dir)
                    filename = decision.target_file  # Now guaranteed to be non-null
                    preview_path = preview_dir / Path(filename).name
                    write(preview_path, content)
                    preview_path = str(preview_path)
                    if self.console_display:
                        self.console_display.show_status(f"Writing to preview: create/{Path(filename).name}", "info")
                
                result = {
                    'action': decision,
                    'content': content,
                    'success': content is not None,
                    'preview_path': preview_path,
                    **metadata
                }
                results['create_results'].append(result)
                if result['success']:
                    results['created_files'].append(decision.target_file)
            elif decision.action == "UPDATE":
                # Save preview file for UPDATE
                preview_path = None
                if content:
                    preview_dir = Path("./llm_outputs/preview/update")
                    mkdir(preview_dir)
                    filename = decision.target_file  # Now guaranteed to be non-null
                    preview_path = preview_dir / Path(filename).name
                    write(preview_path, content)
                    preview_path = str(preview_path)
                    if self.console_display:
                        self.console_display.show_status(f"Writing to preview: update/{Path(filename).name}", "info")
                
                result = {
                    'action': decision,
                    'updated_content': content,
                    'success': content is not None,
                    'preview_path': preview_path,
                    **metadata
                }
                results['update_results'].append(result)
                if result['success']:
                    results['updated_files'].append(decision.target_file)
        
        # Add summary
        results['summary'] = self._create_summary(results)
        
        return results
    
    def _load_existing_chunks(self, working_dir_path: Path, repo_name: str, 
                             working_directory: str) -> List[DocumentChunk]:
        """Load existing chunks from the working directory"""
        processor = ContentDiscoveryProcessor(self.client, self.config, self.console_display)
        if hasattr(self, 'current_phase') and self.current_phase:
            processor.set_phase_step(self.current_phase, 2)
        return processor.process(
            working_dir_path, repo_name, working_directory
        )
    
    def _create_summary(self, results: Dict) -> Dict:
        """Create summary of generation results"""
        create_success = sum(1 for r in results['create_results'] if r.get('success'))
        update_success = sum(1 for r in results['update_results'] if r.get('success'))
        skip_count = len(results['skip_results'])
        
        logger.info(f"Content generation complete: {create_success} created, "
                   f"{update_success} updated, {skip_count} skipped")
        
        return {
            'total_actions': len(results['create_results']) + len(results['update_results']) + len(results['skip_results']),
            'create_attempted': len(results['create_results']),
            'create_success': create_success,
            'update_attempted': len(results['update_results']),
            'update_success': update_success,
            'skip_count': skip_count
        }
    
    def process(self, *args, **kwargs):
        """Public process method that delegates to _process"""
        return self._process(*args, **kwargs) 