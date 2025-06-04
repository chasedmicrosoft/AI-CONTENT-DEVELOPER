"""
Main content generator orchestrator for Phase 3
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ..models import ContentStrategy, DocumentChunk
from ..processors.smart_processor import SmartProcessor
from ..processors import ContentDiscoveryProcessor
from .material_loader import MaterialContentLoader
from .create_processor import CreateContentProcessor
from .update_processor import UpdateContentProcessor

logger = logging.getLogger(__name__)


class ContentGenerator(SmartProcessor):
    """Main orchestrator for Phase 3 content generation"""
    
    def __init__(self, *args, **kwargs):
        """Initialize content generator"""
        super().__init__(*args, **kwargs)
        self.progress_callback = None  # For progress updates
    
    def _process(self, strategy: ContentStrategy, materials: List[Dict], 
                 working_dir_path: Path, repo_name: str, working_directory: str) -> Dict:
        """Process all content generation actions from the strategy"""
        logger.info("Starting content generation...")
        
        # Validate materials
        validation_result = self._validate_materials(materials, strategy)
        if validation_result:
            return validation_result
        
        # Load existing chunks for reference
        if self.console_display:
            self.console_display.show_operation("Loading existing content chunks")
        chunks = self._load_existing_chunks(working_dir_path, repo_name, working_directory)
        
        # Load material content
        if self.console_display:
            self.console_display.show_operation("Loading support material content")
        materials_content = self._load_material_content(materials, strategy)
        if not materials_content:
            return materials_content  # Error result
        
        logger.info(f"Successfully loaded {len(materials_content)} materials for content generation")
        
        # Process actions
        results = self._process_all_actions(strategy, materials, materials_content, 
                                          chunks, working_dir_path, repo_name, working_directory)
        
        # Add debug info if enabled
        if self.config.debug_similarity:
            self._add_debug_info(results, materials_content, chunks)
        
        return results
    
    def _validate_materials(self, materials: List[Dict], strategy: ContentStrategy) -> Optional[Dict]:
        """Validate that materials are provided (Improvement #1)"""
        if not materials:
            error_msg = "Content generation requires support materials. Please provide at least one material file."
            logger.error(error_msg)
            return self._create_error_result(
                strategy, error_msg, "No materials provided"
            )
        return None
    
    def _load_existing_chunks(self, working_dir_path: Path, repo_name: str, 
                             working_directory: str) -> List[DocumentChunk]:
        """Load existing chunks from the working directory"""
        # Pass console_display to child processor
        processor = ContentDiscoveryProcessor(self.client, self.config, self.console_display)
        if hasattr(self, 'current_phase') and self.current_phase:
            processor.set_phase_step(self.current_phase, 2)  # Step 2: Load chunks
        return processor.process(
            working_dir_path, repo_name, working_directory
        )
    
    def _load_material_content(self, materials: List[Dict], strategy: ContentStrategy) -> Dict[str, str]:
        """Load content from materials"""
        # Pass console_display to child processor
        material_loader = MaterialContentLoader(self.client, self.config, self.console_display)
        if hasattr(self, 'current_phase') and self.current_phase:
            material_loader.set_phase_step(self.current_phase, 3)  # Step 3: Load materials
        materials_content = material_loader.process(materials)
        
        if not materials_content:
            error_msg = f"Failed to load content from any of the {len(materials)} provided materials"
            logger.error(error_msg)
            return self._create_error_result(
                strategy, error_msg, "Failed to load material content"
            )
        
        return materials_content
    
    def _process_all_actions(self, strategy: ContentStrategy, materials: List[Dict],
                            materials_content: Dict[str, str], chunks: List[DocumentChunk],
                            working_dir_path: Path, repo_name: str, 
                            working_directory: str) -> Dict:
        """Process all CREATE and UPDATE actions"""
        # Ensure decisions is a list of dictionaries
        decisions = strategy.decisions if isinstance(strategy.decisions, list) else []
        
        # Filter and validate decisions
        valid_decisions = []
        for decision in decisions:
            if isinstance(decision, dict) and 'action' in decision:
                valid_decisions.append(decision)
            else:
                logger.warning(f"Skipping invalid decision: {decision}")
        
        # Separate actions by type
        create_actions = [decision for decision in valid_decisions 
                         if decision.get('action') == 'CREATE']
        update_actions = [decision for decision in valid_decisions 
                         if decision.get('action') == 'UPDATE']
        
        # Process CREATE actions
        create_results = self._process_create_actions(
            create_actions, materials, materials_content, chunks,
            repo_name, working_directory
        )
        
        # Process UPDATE actions
        update_results = self._process_update_actions(
            update_actions, materials, materials_content, chunks,
            working_dir_path, repo_name, working_directory
        )
        
        # Create summary
        return self._create_results_summary(strategy, create_results, update_results)
    
    def _process_create_actions(self, create_actions: List[Dict], materials: List[Dict],
                               materials_content: Dict[str, str], chunks: List[DocumentChunk],
                               repo_name: str, working_directory: str) -> List[Dict]:
        """Process all CREATE actions"""
        # Pass console_display to child processor
        create_processor = CreateContentProcessor(self.client, self.config, self.console_display)
        if hasattr(self, 'current_phase') and self.current_phase:
            create_processor.set_phase_step(self.current_phase, 4)  # Step 4: Create content
        results = []
        
        for action in create_actions:
            filename = action.get('filename', 'unknown')
            logger.info(f"Generating new content: {filename}")
            
            # Update progress if callback provided
            if self.progress_callback:
                self.progress_callback(f"Creating: {filename}")
            
            # Prepare chunk data for this action
            relevant_chunks, chunks_with_context = self._prepare_chunk_data(
                action, chunks
            )
            
            # Process the action - pass working_directory as parameter
            result = create_processor._process(
                action, materials, materials_content, chunks, 
                repo_name, working_directory,
                relevant_chunks=relevant_chunks,
                chunks_with_context=chunks_with_context
            )
            results.append(result)
        
        return results
    
    def _process_update_actions(self, update_actions: List[Dict], materials: List[Dict],
                               materials_content: Dict[str, str], chunks: List[DocumentChunk],
                               working_dir_path: Path, repo_name: str, 
                               working_directory: str) -> List[Dict]:
        """Process all UPDATE actions"""
        # Pass console_display to child processor
        update_processor = UpdateContentProcessor(self.client, self.config, self.console_display)
        if hasattr(self, 'current_phase') and self.current_phase:
            update_processor.set_phase_step(self.current_phase, 5)  # Step 5: Update content
        results = []
        
        for action in update_actions:
            filename = action.get('filename', 'unknown')
            logger.info(f"Updating existing content: {filename}")
            
            # Update progress if callback provided
            if self.progress_callback:
                self.progress_callback(f"Updating: {filename}")
            
            # Prepare chunk data for this action
            relevant_chunks, chunks_with_context = self._prepare_chunk_data(
                action, chunks
            )
            
            # Process the action - pass working_directory as parameter
            result = update_processor._process(
                action, materials, materials_content, chunks, 
                working_dir_path, repo_name, working_directory,
                relevant_chunks=relevant_chunks,
                chunks_with_context=chunks_with_context
            )
            results.append(result)
        
        return results
    
    def _prepare_chunk_data(self, action: Dict, chunks: List[DocumentChunk]) -> tuple:
        """Prepare chunk data for an action (Improvements #2 and #6)"""
        relevant_chunk_ids = action.get('relevant_chunks', [])
        
        # Get full chunk content for relevant chunks (Improvement #2)
        relevant_chunks = self._get_chunks_by_ids(chunks, relevant_chunk_ids)
        
        # Get chunks with context (Improvement #6)
        chunks_with_context = self._get_chunks_with_context_for_ids(
            chunks, relevant_chunk_ids
        )
        
        return relevant_chunks, chunks_with_context
    
    def _get_chunks_by_ids(self, chunks: List[DocumentChunk], 
                          chunk_ids: List[str]) -> Dict[str, DocumentChunk]:
        """Get chunks by their IDs for reference"""
        chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
        return {chunk_id: chunk_map.get(chunk_id) 
                for chunk_id in chunk_ids if chunk_id in chunk_map}
    
    def _get_chunks_with_context_for_ids(self, chunks: List[DocumentChunk], 
                                        chunk_ids: List[str]) -> Dict[str, Dict]:
        """Get chunks with context for multiple IDs"""
        chunks_with_context = {}
        for chunk_id in chunk_ids:
            chunk_context = self._get_chunk_with_context(chunks, chunk_id)
            if chunk_context:
                chunks_with_context[chunk_id] = chunk_context
        return chunks_with_context
    
    def _get_chunk_with_context(self, chunks: List[DocumentChunk], chunk_id: str, 
                               context_size: int = 200) -> Optional[Dict]:
        """Get chunk with surrounding context"""
        chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
        target_chunk = chunk_map.get(chunk_id)
        
        if not target_chunk:
            return None
            
        result = {
            'chunk': target_chunk,
            'prev_content': '',
            'next_content': ''
        }
        
        # Get previous chunk content if available
        if target_chunk.prev_chunk_id and target_chunk.prev_chunk_id in chunk_map:
            prev_chunk = chunk_map[target_chunk.prev_chunk_id]
            result['prev_content'] = prev_chunk.content[-context_size:] if prev_chunk.content else ''
            
        # Get next chunk content if available  
        if target_chunk.next_chunk_id and target_chunk.next_chunk_id in chunk_map:
            next_chunk = chunk_map[target_chunk.next_chunk_id]
            result['next_content'] = next_chunk.content[:context_size] if next_chunk.content else ''
            
        return result
    
    def _create_results_summary(self, strategy: ContentStrategy, create_results: List[Dict],
                               update_results: List[Dict]) -> Dict:
        """Create summary of generation results"""
        create_success = sum(1 for result in create_results if result.get('success'))
        update_success = sum(1 for result in update_results if result.get('success'))
        
        # Collect successfully created/updated file paths
        created_files = [
            result['action'].get('filename', '') 
            for result in create_results 
            if result.get('success') and result.get('action', {}).get('filename')
        ]
        
        updated_files = [
            result['action'].get('filename', '') 
            for result in update_results 
            if result.get('success') and result.get('action', {}).get('filename')
        ]
        
        logger.info(f"Content generation complete: {create_success}/{len(create_results)} created, "
                   f"{update_success}/{len(update_results)} updated")
        
        return {
            'create_results': create_results,
            'update_results': update_results,
            'created_files': created_files,
            'updated_files': updated_files,
            'summary': {
                'total_actions': len(strategy.decisions),
                'create_attempted': len(create_results),
                'create_success': create_success,
                'update_attempted': len(update_results),
                'update_success': update_success
            }
        }
    
    def _create_error_result(self, strategy: ContentStrategy, error_msg: str, 
                            error_type: str) -> Dict:
        """Create an error result structure"""
        return {
            'create_results': [],
            'update_results': [],
            'error': error_msg,
            'summary': {
                'total_actions': len(strategy.decisions),
                'create_attempted': 0,
                'create_success': 0,
                'update_attempted': 0,
                'update_success': 0,
                'error': error_type
            }
        }
    
    def _add_debug_info(self, results: Dict, materials_content: Dict[str, str],
                       chunks: List[DocumentChunk]) -> None:
        """Add debug information if enabled (Improvement #7)"""
        results['debug_info'] = {
            'materials_loaded': list(materials_content.keys()),
            'total_chunks_available': len(chunks),
            'chunks_with_content': sum(1 for chunk in chunks if chunk.content),
            'generation_mode': 'RAG-constrained (no hallucination)'
        }
        
        # Add gap reports summary
        gap_reports = self._collect_gap_reports(results)
        if gap_reports:
            results['debug_info']['gap_reports'] = gap_reports
    
    def _collect_gap_reports(self, results: Dict) -> List[Dict]:
        """Collect gap reports from all results"""
        gap_reports = []
        all_results = results.get('create_results', []) + results.get('update_results', [])
        
        for result_item in all_results:
            gap_report = result_item.get('gap_report')
            if not gap_report:
                continue
            gap_reports.append(gap_report)
        
        return gap_reports 