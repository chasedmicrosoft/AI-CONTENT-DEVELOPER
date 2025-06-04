"""
Create content processor for generating new documentation
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ..models import DocumentChunk
from ..prompts import get_create_content_prompt, CREATE_CONTENT_SYSTEM
from ..utils import write, mkdir, extract_from_markdown_block
from .base_content_processor import BaseContentProcessor

logger = logging.getLogger(__name__)


class CreateContentProcessor(BaseContentProcessor):
    """Generate new content files based on CREATE actions"""
    
    def _process(self, action: Dict, materials: List[Dict], materials_content: Dict[str, str], 
                 existing_chunks: List[DocumentChunk], repo_name: str, working_directory: str,
                 relevant_chunks: Optional[Dict[str, DocumentChunk]] = None,
                 chunks_with_context: Optional[Dict[str, Dict]] = None) -> Dict:
        """Generate content for a CREATE action"""
        filename = action.get('filename', 'untitled.md')
        content_type = action.get('content_type', 'How-To Guide')
        
        # Defensive fallback for ms_topic based on content_type
        ms_topic_mapping = {
            'Concept': 'concept',
            'How-To Guide': 'how-to',
            'Quickstart': 'quickstart',
            'Tutorial': 'tutorial',
            'Overview': 'overview',
            'Reference': 'reference'
        }
        ms_topic = action.get('ms_topic', ms_topic_mapping.get(content_type, 'how-to'))
        
        # Format material sources for the prompt
        materials_text = self._format_materials(materials_content)
        
        # Format relevant chunks if provided
        reference_chunks_text = ""
        if relevant_chunks:
            reference_chunks_text = self._format_reference_chunks(
                relevant_chunks, chunks_with_context
            )
        
        # Format content standards
        content_standards = self._load_content_standards()
        content_type_info = self._get_content_type_info(content_standards, content_type)
        
        try:
            # Generate content using LLM
            response = self._generate_content(
                action, materials_text, reference_chunks_text, 
                content_type_info, filename, materials_content
            )
            
            # Extract content from markdown block if present
            content = response.get('content', '')
            content = extract_from_markdown_block(content)
            
            # Save to file preview
            preview_path = self._save_preview(filename, content, 'create')
            
            # Create success result
            return self._create_success_result(action, response, preview_path, content)
            
        except Exception as e:
            logger.error(f"Failed to generate content for {filename}: {e}")
            return self._create_error_result(action, materials_content, relevant_chunks, e)
    
    def _generate_content(self, action: Dict, materials_text: str, 
                         reference_chunks_text: str, content_type_info: Dict,
                         filename: str, materials_content: Dict[str, str]) -> Dict:
        """Generate content using LLM"""
        # Load full content standards
        content_standards = self._load_content_standards()
        
        # Get the prompt with all necessary information
        prompt = get_create_content_prompt(
            self.config, 
            action, 
            materials_content,  # Pass the original Dict[str, str] not formatted text
            [],  # Empty list for materials_summaries (not needed for content creation)
            [],  # Empty list for related_chunks (we have reference_chunks_text instead)
            reference_chunks_text,  # Use reference_chunks_text as chunk_context
            content_type_info,
            content_standards
        )
        
        # Call LLM for content generation
        messages = [
            {"role": "system", "content": CREATE_CONTENT_SYSTEM},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_llm(messages, response_format="json_object", 
                                operation_name=f"Content Creation: {filename}")
        
        # Display thinking if available
        if self.console_display and 'thinking' in response:
            self.console_display.show_thinking(response['thinking'], f"🤔 AI Thinking - Content Creation: {filename}")
        
        return response
    
    def _create_success_result(self, action: Dict, response: Dict, preview_path, content: str) -> Dict:
        """Create successful result structure"""
        return {
            'success': True,
            'action': action,
            'content': content,
            'preview_path': str(preview_path),
            'metadata': response.get('metadata', {}),
            'thinking': response.get('thinking', ''),
            'gap_report': response.get('gap_report', None)  # Improvement #5
        }
    
    def _create_error_result(self, action: Dict, materials_content: Dict[str, str],
                            relevant_chunks: Optional[Dict], error: Exception) -> Dict:
        """Create error result with gap report"""
        content_type = action.get('content_type', 'Unknown')
        
        # Create gap report (Improvement #5)
        gap_report = self._create_gap_report(
            action, materials_content, relevant_chunks,
            error=str(error),
            additional_info=[
                f"Failed to generate {content_type} content",
                "Check if materials contain necessary information for this content type"
            ]
        )
        
        return {
            'success': False,
            'action': action,
            'error': str(error),
            'gap_report': gap_report
        }
    
    def _format_reference_chunks(self, relevant_chunks: Dict[str, DocumentChunk],
                                chunks_with_context: Optional[Dict[str, Dict]] = None) -> str:
        """Format reference chunks with their content and context"""
        if not relevant_chunks:
            return "No reference chunks available."
        
        formatted_chunks = []
        for chunk_id, chunk in relevant_chunks.items():
            chunk_text = f"Chunk ID: {chunk_id}\n"
            chunk_text += f"File: {chunk.file_path}\n"
            chunk_text += f"Section: {' > '.join(chunk.heading_path)}\n"
            
            # Add context if available
            if chunks_with_context and chunk_id in chunks_with_context:
                context = chunks_with_context[chunk_id]
                if context['prev_content']:
                    chunk_text += f"[Previous context: ...{context['prev_content']}]\n"
                chunk_text += f"Content: {chunk.content}\n"
                if context['next_content']:
                    chunk_text += f"[Next context: {context['next_content']}...]\n"
            else:
                chunk_text += f"Content: {chunk.content}\n"
            
            formatted_chunks.append(chunk_text)
        
        return "\n---\n".join(formatted_chunks)
    
    def _format_materials(self, materials_content: Dict[str, str]) -> str:
        """Format material content for the prompt"""
        if not materials_content:
            return "No material content available."
        
        formatted = []
        for source, content in materials_content.items():
            formatted.append(f"=== Material: {source} ===\n{content}")
        
        return "\n\n".join(formatted)
    
    def _save_preview(self, filename: str, content: str, action_type: str) -> Path:
        """Save preview content"""
        preview_dir = Path('./llm_outputs/preview') / action_type
        mkdir(preview_dir)
        
        preview_path = preview_dir / filename
        write(preview_path, content)
        
        return preview_path 