"""
Update processor for modifying existing content
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
import re
import json

from ..models import DocumentChunk
from ..utils import read, write, mkdir, extract_from_markdown_block
from ..prompts import get_update_content_prompt, UPDATE_CONTENT_SYSTEM
from .base_content_processor import BaseContentProcessor

logger = logging.getLogger(__name__)


class UpdateContentProcessor(BaseContentProcessor):
    """Process UPDATE actions from content strategy"""
    
    def _normalize_filename(self, filename: str, working_dir_path: Path, repo_name: str) -> str:
        """Normalize filename by removing repository and path prefixes
        
        Examples:
            - 'azure-aks-docs/articles/aks/file.md' -> 'file.md'
            - '/articles/aks/file.md' -> 'file.md' 
            - 'articles/aks/file.md' -> 'file.md'
            - 'file.md' -> 'file.md'
        """
        # Convert to Path for easier manipulation
        file_path = Path(filename)
        
        # Get the working directory relative to repo
        working_dir_parts = working_dir_path.parts
        
        # Remove repo name if present at start
        if file_path.parts and file_path.parts[0] == repo_name:
            file_path = Path(*file_path.parts[1:])
        
        # Remove working directory path if present
        if len(file_path.parts) > 1:
            # Check if the file path contains the working directory structure
            for i in range(len(file_path.parts)):
                remaining_parts = file_path.parts[i:]
                # If we find a valid file at this level, use it
                test_path = working_dir_path / Path(*remaining_parts)
                if test_path.exists() and test_path.is_file():
                    logger.info(f"Normalized '{filename}' to '{Path(*remaining_parts)}'")
                    return str(Path(*remaining_parts))
        
        # If no match found, try just the filename
        if file_path.name and (working_dir_path / file_path.name).exists():
            logger.info(f"Normalized '{filename}' to '{file_path.name}'")
            return file_path.name
            
        # Otherwise return the original filename and let it fail naturally
        logger.warning(f"Could not normalize filename '{filename}', using as-is")
        return filename
    
    def _process(self, action: Dict, materials: List[Dict], 
                       materials_content: Dict[str, str], chunks: List[DocumentChunk],
                       working_dir_path: Path, repo_name: str, working_directory: str,
                       relevant_chunks: Dict[str, DocumentChunk] = None,
                       chunks_with_context: Dict[str, Dict] = None) -> Dict:
        """Process a single UPDATE action"""
        original_filename = action.get('filename', '')
        
        # Normalize the filename to handle path issues
        filename = self._normalize_filename(original_filename, working_dir_path, repo_name)
        
        # Load existing file content
        file_path = working_dir_path / filename
        if not file_path.exists():
            # Try one more time with just the base filename
            base_filename = Path(original_filename).name
            file_path = working_dir_path / base_filename
            if file_path.exists():
                filename = base_filename
            else:
                return self._create_error_result(action, f"File not found: {original_filename} (tried: {filename})")
        
        # Read existing content
        existing_content = read(file_path, limit=None)
        
        # Check for missing information
        gap_report = self._check_for_gaps(action, materials_content)
        if gap_report['has_gaps']:
            return self._create_gap_result(action, gap_report)
        
        # Generate updated content
        updated_content = self._update_content(
            action, existing_content, materials, materials_content, 
            relevant_chunks, chunks_with_context
        )
        
        if updated_content and updated_content != existing_content:
            # Save preview
            preview_path = self._save_update_preview(
                updated_content, filename, working_dir_path, repo_name
            )
            
            return {
                'action': action,
                'success': True,
                'updated_content': updated_content,
                'preview_path': preview_path
            }
        else:
            return self._create_error_result(action, "Failed to update content")
    
    def _extract_content_type_from_document(self, content: str) -> Dict:
        """Extract content type information from document frontmatter"""
        # Extract frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            logger.warning("No frontmatter found in document")
            return {'ms_topic': 'unknown', 'content_type': 'Unknown'}
        
        frontmatter = frontmatter_match.group(1)
        
        # Extract ms.topic
        ms_topic_match = re.search(r'ms\.topic:\s*(\S+)', frontmatter)
        ms_topic = ms_topic_match.group(1) if ms_topic_match else 'unknown'
        
        # Map ms.topic to content type
        ms_topic_to_content_type = {
            'overview': 'Overview',
            'concept-article': 'Concept', 
            'quickstart': 'Quickstart',
            'how-to': 'How-To Guide',
            'tutorial': 'Tutorial'
        }
        
        content_type = ms_topic_to_content_type.get(ms_topic, 'Unknown')
        
        return {
            'ms_topic': ms_topic,
            'content_type': content_type
        }
    
    def _update_content(self, action: Dict, existing_content: str, 
                       materials: List[Dict], materials_content: Dict[str, str],
                       relevant_chunks: Dict[str, DocumentChunk],
                       chunks_with_context: Dict[str, Dict]) -> Optional[str]:
        """Generate updated content for the file using LLM-native approach"""
        # Extract document content type
        doc_info = self._extract_content_type_from_document(existing_content)
        content_type = doc_info['content_type']
        
        # Load content standards and get content type info
        content_standards = self._load_content_standards()
        content_type_info = self._get_content_type_info(content_standards, content_type)
        
        # Build context from relevant chunks
        chunk_context = self._build_chunk_context(relevant_chunks, chunks_with_context)
        
        # Build material context
        material_context = self._build_material_context(materials, materials_content, action)
        
        # Create update prompt
        messages = [
            {
                "role": "system",
                "content": UPDATE_CONTENT_SYSTEM
            },
            {
                "role": "user",
                "content": get_update_content_prompt(
                    self.config, action, existing_content, material_context, chunk_context,
                    content_type_info,  # Pass content type info
                    content_standards   # Pass full standards for formatting
                )
            }
        ]
        
        try:
            result = self._call_llm(messages, model=self.config.completion_model, 
                                  response_format="json_object",
                                  operation_name=f"Content Update: {action.get('filename', 'unknown')}")
            
            # Extract and display thinking if available
            if self.console_display and 'thinking' in result:
                self.console_display.show_thinking(result['thinking'], f"🤔 AI Thinking - Content Update: {action.get('filename', 'unknown')}")
            
            # Get the complete updated document from the LLM response
            updated_document = result.get('updated_document', '')
            
            if not updated_document:
                logger.error("LLM did not return an updated document")
                return None
            
            # Log summary of changes
            if 'changes_summary' in result:
                logger.info(f"Update summary: {result['changes_summary']}")
            
            # Log metadata
            if 'metadata' in result:
                metadata = result['metadata']
                logger.info(f"Sections modified: {', '.join(metadata.get('sections_modified', []))}")
                if metadata.get('sections_added'):
                    logger.info(f"Sections added: {', '.join(metadata['sections_added'])}")
            
            return updated_document
            
        except Exception as e:
            logger.error(f"Failed to generate updated content: {e}")
            return None
    
    def _apply_changes(self, original_content: str, changes: List[Dict]) -> str:
        """DEPRECATED: No longer needed with LLM-native approach"""
        logger.warning("_apply_changes called but is deprecated in LLM-native approach")
        return original_content
    
    def _save_update_preview(self, content: str, filename: str,
                            working_dir: Path, repo_name: str) -> str:
        """Save updated content preview"""
        preview_dir = Path("./llm_outputs/preview/update")
        mkdir(preview_dir)
        
        # Use just the base filename for preview to avoid nested paths
        base_filename = Path(filename).name
        preview_path = preview_dir / base_filename
        write(preview_path, content)
        
        return str(preview_path) 