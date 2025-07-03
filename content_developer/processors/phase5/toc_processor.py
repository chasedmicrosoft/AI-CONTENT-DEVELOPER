"""
TOC Management Processor
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from ...utils import write, mkdir, read
from ..llm_native_processor import LLMNativeProcessor
from ...models import Config
from ...prompts.phase5 import get_toc_update_prompt, TOC_UPDATE_SYSTEM
from ... import display

logger = logging.getLogger(__name__)


class TOCProcessor(LLMNativeProcessor):
    """Process TOC.yml using intelligent LLM understanding"""
    
    def process(
        self,
        working_directory: Path,
        created_files: List[str],
        updated_files: List[str],
        strategy_results: Dict
    ) -> Dict:
        """Process TOC.yml to add/verify entries for created and updated files
        
        Args:
            working_directory: Path to the working directory
            created_files: List of newly created file paths
            updated_files: List of updated file paths
            strategy_results: Results from the strategy phase
            
        Returns:
            Dict with TOC update results
        """
        return self._process(working_directory, created_files, updated_files, strategy_results)
    
    def _process(
        self,
        working_directory: Path,
        created_files: List[str],
        updated_files: List[str],
        strategy_results: Dict
    ) -> Dict:
        """Internal processing logic using LLM-native approach with integrated placement analysis"""
        toc_path = working_directory / "TOC.yml"
        
        # Check if TOC.yml exists
        if not toc_path.exists():
            logger.warning(f"TOC.yml not found at {toc_path}")
            return {
                'success': False,
                'message': 'TOC.yml not found in working directory',
                'toc_path': str(toc_path)
            }
        
        # Read existing TOC
        try:
            toc_content = read(toc_path, limit=None)  # Read entire file without truncation
            logger.info(f"TOC.yml has {len(toc_content.split(chr(10)))} lines")
        except Exception as e:
            logger.error(f"Failed to read TOC.yml: {e}")
            return {
                'success': False,
                'message': f'Failed to read TOC.yml: {str(e)}',
                'toc_path': str(toc_path)
            }
        
        # Prepare entries that need TOC placement
        all_files = created_files + updated_files
        if not all_files:
            logger.info("No files to add to TOC")
            return {
                'success': True,
                'message': 'No files to add to TOC',
                'changes_made': False,
                'toc_path': str(toc_path)
            }
        
        # Extract file descriptions from strategy results
        file_entries = self._prepare_file_entries(all_files, strategy_results)
        
        # Generate updated TOC with integrated placement analysis
        if self.console_display:
            self.console_display.show_operation("Analyzing TOC and determining placements")
        
        updated_toc_result = self._generate_updated_toc_with_placement(
            toc_content, 
            created_files,
            updated_files,
            file_entries,
            working_directory
        )
        
        if not updated_toc_result:
            return {
                'success': False,
                'message': 'Failed to generate updated TOC',
                'toc_path': str(toc_path)
            }
        
        # Extract thinking if available
        if self.console_display and 'thinking' in updated_toc_result:
            self.console_display.show_thinking(updated_toc_result['thinking'], "🤔 AI Thinking - TOC Update")
        
        # Save preview
        preview_path = self._save_toc_preview(updated_toc_result['content'], working_directory)
        
        # Extract placement information
        placement_analysis = updated_toc_result.get('placement_analysis', {})
        placement_rationale = placement_analysis.get('placement_rationale', [])
        
        return {
            'success': True,
            'message': 'TOC updated successfully',
            'changes_made': True,
            'toc_path': str(toc_path),
            'preview_path': str(preview_path),
            'content': updated_toc_result['content'],  # Add content for later use
            'placements': placement_rationale,
            'placement_decisions': updated_toc_result.get('placement_decisions', {}),
            'entries_added': updated_toc_result.get('entries_added', []),
            'toc_pattern': placement_analysis.get('toc_pattern', 'Unknown pattern')
        }
    
    def _prepare_file_entries(self, files: List[str], strategy_results: Dict) -> List[Dict[str, str]]:
        """Prepare file entries with descriptions from strategy"""
        entries = []
        decisions = strategy_results.get('decisions', [])
        
        # Map strategy decisions to files that need TOC entries
        decision_map = {}
        for decision in decisions:
            if hasattr(decision, 'filename') and decision.filename:
                decision_map[decision.filename] = decision
        
        # Process each file
        for file_path in files:
            entry = {'filename': file_path}
            
            if file_path in decision_map:
                # Use the decision to get metadata
                decision = decision_map[file_path]
                
                # Add metadata for better placement
                entry['description'] = decision.reason or decision.rationale or ''
                entry['content_type'] = decision.content_type or ''
                entry['ms_topic'] = decision.ms_topic or ''
                
                # Extract content brief if available
                content_brief = decision.content_brief or {}
                if isinstance(content_brief, dict):
                    entry['objective'] = content_brief.get('objective', '')
                    entry['primary_topic'] = content_brief.get('primary_topic', '')
                    entry['technical_level'] = content_brief.get('technical_level', '')
                
                # Generate title from filename if not provided
                title = file_path.replace('.md', '').replace('-', ' ')
                entry['title'] = ' '.join(word.capitalize() for word in title.split())
            else:
                # Default values for files not in strategy
                entry['description'] = ''
                entry['content_type'] = 'unknown'
                entry['ms_topic'] = 'unknown'
                entry['title'] = file_path.replace('.md', '').replace('-', ' ').title()
            
            entries.append(entry)
        
        return entries
    
    def _generate_updated_toc_with_placement(self, current_toc: str, 
                                           created_files: List[str],
                                           updated_files: List[str],
                                           file_entries: List[Dict],
                                           working_directory: Path) -> Optional[Dict]:
        """Generate the updated TOC content with integrated placement analysis"""
        # Create file descriptions mapping
        file_descriptions = {entry['filename']: entry for entry in file_entries}
        
        # Combine created and updated files into a single list
        files_to_add = created_files + updated_files
        
        prompt = get_toc_update_prompt(
            current_toc,
            files_to_add,          # Combined list of files to add
            file_descriptions,     # Metadata dictionary
            str(working_directory) # Convert Path to string
        )
        
        messages = [
            {"role": "system", "content": TOC_UPDATE_SYSTEM},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_llm(
                messages,
                model=self.config.completion_model,
                response_format="json_object",
                operation_name="TOC Update with Placement Analysis"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate TOC updates: {e}")
            return None
    
    def _save_toc_preview(self, updated_toc: str, working_directory: Path) -> Path:
        """Save TOC preview"""
        preview_dir = Path("./llm_outputs/preview/toc")
        preview_dir.mkdir(parents=True, exist_ok=True)
        
        # Use working directory name in preview filename
        working_dir_name = working_directory.name
        preview_path = preview_dir / f"TOC_{working_dir_name}.yml"
        
        write(preview_path, updated_toc)
        
        if self.console_display:
            self.console_display.show_status(f"Writing to preview: toc/{preview_path.name}", "info")
        
        return preview_path 