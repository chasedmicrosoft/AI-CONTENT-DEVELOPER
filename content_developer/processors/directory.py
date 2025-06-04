"""
Directory detection processor using LLM-native approach
"""
from pathlib import Path
from typing import Dict, List
import logging

from ..prompts import get_directory_selection_prompt, DIRECTORY_SELECTION_SYSTEM
from .llm_native_processor import LLMNativeProcessor

logger = logging.getLogger(__name__)


class DirectoryDetector(LLMNativeProcessor):
    """Detect appropriate working directory for content development using LLM intelligence"""
    
    def _process(self, repo_path: Path, repo_structure: str, summaries: List[Dict]) -> Dict:
        """Process repository structure and materials to select working directory"""
        materials_info = self._format_materials(summaries) if summaries else "No materials"
        
        # Get directory recommendation with integrated analysis and validation
        prompt = get_directory_selection_prompt(
            self.config, 
            str(repo_path), 
            repo_structure, 
            materials_info
        )
        
        messages = [
            {"role": "system", "content": DIRECTORY_SELECTION_SYSTEM},
            {"role": "user", "content": prompt}
        ]
        
        result = self._call_llm(
            messages,
            response_format="json_object",
            operation_name="Working Directory Selection & Validation"
        )
        
        # Display thinking if available
        if self.console_display and 'thinking' in result:
            self.console_display.show_thinking(result['thinking'], "🤔 AI Thinking - Working Directory Selection & Validation")
        
        # Validate the result format and directory existence
        result = self._validate_result_format(result, repo_path)
        
        return result
    
    def _validate_result_format(self, result: Dict, repo_path: Path) -> Dict:
        """Validate the LLM result format and directory existence"""
        working_dir = result.get('working_directory', '')
        
        if not working_dir:
            result['confidence'] = 0.0
            result['error'] = 'No directory selected'
            return result
        
        # Check if validation was performed by the LLM
        validation = result.get('validation', {})
        if not validation.get('is_documentation_directory', True):
            result['working_directory'] = ''
            result['confidence'] = 0.0
            result['error'] = 'Selected directory is not suitable for documentation'
            return result
        
        # Check if the LLM flagged service area mismatch
        if not validation.get('matches_service_area', True):
            # Check if there's a better alternative suggested
            if alternative := validation.get('alternative_considered'):
                alt_path = repo_path / alternative
                if alt_path.exists():
                    logger.info(f"Using LLM-suggested alternative directory: {alternative}")
                    result['working_directory'] = alternative
                    result['justification'] = f"Switched to better match: {validation.get('validation_notes', '')}"
                    result['confidence'] = result.get('confidence', 0.5) * 1.1  # Slight confidence boost
        
        # Log any validation concerns
        if validation_notes := validation.get('validation_notes'):
            logger.info(f"Directory validation notes: {validation_notes}")
        
        # Final check: verify directory exists
        if result.get('working_directory'):
            full_path = repo_path / result['working_directory']
            if not full_path.exists():
                logger.warning(f"Selected directory does not exist: {full_path}")
                result['working_directory'] = ''
                result['confidence'] = 0.0
                result['error'] = f'Directory does not exist: {result.get("working_directory")}'
        
        return result
    
    def _format_materials(self, summaries: List[Dict]) -> str:
        """Format material summaries for prompt"""
        formatted_summaries = []
        
        for s in summaries:
            # Safely get list fields, ensuring they are actually lists
            technologies = s.get('technologies', [])
            if not isinstance(technologies, list):
                technologies = [technologies] if technologies else []
                
            key_concepts = s.get('key_concepts', [])
            if not isinstance(key_concepts, list):
                key_concepts = [key_concepts] if key_concepts else []
                
            microsoft_products = s.get('microsoft_products', [])
            if not isinstance(microsoft_products, list):
                microsoft_products = [microsoft_products] if microsoft_products else []
            
            summary_text = (
            f"• {s.get('source', 'Unknown')}: {s.get('main_topic', 'N/A')}\n"
            f"  Summary: {s.get('summary', 'N/A')}\n"
                f"  Technologies: {', '.join(str(t) for t in technologies)}\n"
                f"  Key Concepts: {', '.join(str(k) for k in key_concepts)}\n"
                f"  Products: {', '.join(str(p) for p in microsoft_products)}"
            )
            formatted_summaries.append(summary_text)
            
        return "\n".join(formatted_summaries) 