"""
Base class for content generation processors using LLM-native approach
"""
from abc import abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import json
import logging

from ..models import DocumentChunk
from ..processors.llm_native_processor import LLMNativeProcessor
from ..utils import write, mkdir

logger = logging.getLogger(__name__)


class BaseContentProcessor(LLMNativeProcessor):
    """Base class for CREATE and UPDATE processors using LLM-native approach"""
    
    @abstractmethod
    def _process_action(self, action: Dict, materials: List[Dict], 
                       materials_content: Dict[str, str], chunks: List[DocumentChunk],
                       repo_name: str, working_directory: str,
                       relevant_chunks: Dict[str, DocumentChunk],
                       chunks_with_context: Dict[str, Dict],
                       working_dir_path: Path) -> Dict:
        """Process a single action - must be implemented by subclasses"""
        pass
    
    def process(self, action: Dict, materials: List[Dict], 
               materials_content: Dict[str, str], chunks: List[DocumentChunk],
               working_dir_path: Path, repo_name: str, working_directory: str,
               relevant_chunks: Optional[Dict[str, DocumentChunk]] = None,
               chunks_with_context: Optional[Dict[str, Dict]] = None) -> Dict:
        """Public interface for processing an action"""
        return self._process_action(
            action, materials, materials_content, chunks,
            repo_name, working_directory,
            relevant_chunks or {},
            chunks_with_context or {},
            working_dir_path
        )
    
    def _create_error_result(self, action: Dict, error_message: str) -> Dict:
        """Create a standardized error result"""
        return {
            'action': action,
            'success': False,
            'error': error_message
        }
    
    def _create_gap_result(self, action: Dict, gap_report: Dict) -> Dict:
        """Create a result with gap analysis"""
        return {
            'action': action,
            'success': False,
            'gap_report': gap_report
        }
    
    def _check_for_gaps(self, action: Dict, materials_content: Dict[str, str]) -> Dict:
        """Check if we have the required materials for this action"""
        gaps = []
        
        # Check if materials are empty
        if not materials_content:
            gaps.append("No materials provided")
        
        # Use LLM to analyze if materials are sufficient for the requested action
        if materials_content and action.get('reason'):
            sufficiency_check = self.extract_key_information(
                content=str(materials_content),
                extraction_purpose=f"Check if materials contain sufficient information for: {action.get('reason')}",
                operation_name="Material Sufficiency Check"
            )
            
            # Display thinking if available
            if self.console_display and 'thinking' in sufficiency_check:
                self.console_display.show_thinking(sufficiency_check['thinking'], "🤔 AI Thinking - Material Sufficiency Check")
            
            if sufficiency_check.get('insufficient_areas'):
                gaps.extend(sufficiency_check['insufficient_areas'])
        
        return {
            'has_gaps': len(gaps) > 0,
            'missing_info': gaps,
            'requested_file': action.get('filename', 'Unknown')
        }
    
    def _save_preview(self, content: str, filename: str, repo_name: str, 
                     working_directory: str, action_type: str) -> str:
        """Save content preview and return path"""
        preview_dir = Path("./llm_outputs/preview") / repo_name / working_directory / action_type
        mkdir(preview_dir)
        
        preview_path = preview_dir / filename
        write(preview_path, content)
        
        return str(preview_path)
    
    def _build_material_context(self, materials: List[Dict], 
                               materials_content: Dict[str, str], 
                               action: Dict) -> str:
        """Build material context for prompt"""
        if not materials_content:
            return "No materials available"
        
        context_parts = []
        
        for material in materials:
            source = material.get('source', 'Unknown')
            if source in materials_content:
                content = materials_content[source]
                # Truncate very long content
                if len(content) > 10000:
                    content = content[:10000] + "\n... [content truncated]"
                
                context_parts.append(f"=== Material: {source} ===")
                context_parts.append(f"Topic: {material.get('main_topic', 'N/A')}")
                context_parts.append(f"Type: {material.get('document_type', 'N/A')}")
                context_parts.append(f"\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _build_chunk_context(self, relevant_chunks: Dict[str, DocumentChunk],
                            chunks_with_context: Dict[str, Dict]) -> str:
        """Build context from relevant chunks"""
        if not relevant_chunks:
            return "No existing documentation context available"
        
        context_parts = []
        
        for chunk_id, chunk in relevant_chunks.items():
            context_parts.append(f"\n--- Existing Documentation ---")
            context_parts.append(f"File: {chunk.file_path}")
            context_parts.append(f"Section: {' > '.join(chunk.heading_path) if chunk.heading_path else 'Main'}")
            
            # Add context if available
            if chunk_id in chunks_with_context:
                context_info = chunks_with_context[chunk_id]
                if context_info.get('prev_content'):
                    context_parts.append(f"[Previous: ...{context_info['prev_content']}]")
                
                context_parts.append(f"\n{chunk.content}\n")
                
                if context_info.get('next_content'):
                    context_parts.append(f"[Next: {context_info['next_content']}...]")
            else:
                context_parts.append(f"\n{chunk.content}\n")
        
        return "\n".join(context_parts)
    
    def _load_content_standards(self) -> Dict:
        """Load content standards from JSON file"""
        standards_path = Path('content_standards.json')
        if standards_path.exists():
            try:
                with open(standards_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load content standards: {e}")
        return {}
    
    def _get_content_type_info(self, standards: Dict, content_type: str) -> Dict:
        """Get content type information from standards"""
        if not standards:
            return {'name': content_type}
        
        content_types = standards.get('contentTypes', [])
        for ct in content_types:
            if ct.get('name') == content_type:
                return ct
        
        return {'name': content_type}
    
    def _create_gap_report(self, action: Dict, materials_content: Dict[str, str],
                          relevant_chunks: Optional[Dict], error: str = None,
                          additional_info: List[str] = None) -> Dict:
        """Create a comprehensive gap report for missing information"""
        gap_report = {
            'requested_action': action.get('action', 'Unknown'),
            'requested_file': action.get('filename', 'Unknown'),
            'content_type': action.get('content_type', 'Unknown'),
            'materials_provided': list(materials_content.keys()) if materials_content else [],
            'has_relevant_chunks': bool(relevant_chunks),
            'error': error,
            'missing_information': [],
            'recommendations': []
        }
        
        # Use LLM to analyze what's missing
        if materials_content:
            gap_analysis = self.extract_key_information(
                content=f"Action requested: {action}\nMaterials available: {list(materials_content.keys())}",
                extraction_purpose="Identify what information is missing to fulfill this documentation request",
                operation_name="Gap Analysis"
            )
            
            # Display thinking if available
            if self.console_display and 'thinking' in gap_analysis:
                self.console_display.show_thinking(gap_analysis['thinking'], "🤔 AI Thinking - Gap Analysis")
            
            if gap_analysis.get('missing_items'):
                gap_report['missing_information'].extend(gap_analysis['missing_items'])
            if gap_analysis.get('recommendations'):
                gap_report['recommendations'].extend(gap_analysis['recommendations'])
        
        # Add any additional info provided
        if additional_info:
            gap_report['missing_information'].extend(additional_info)
        
        return gap_report 