"""
LLM-Native Processor Base Class
Leverages LLM intelligence instead of complex programmatic logic
"""
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .smart_processor import SmartProcessor
from ..prompts import (
    CONTENT_PLACEMENT_SYSTEM,
    get_content_placement_prompt,
    TERMINAL_SECTION_SYSTEM,
    get_terminal_section_prompt,
    get_content_quality_system,
    get_content_quality_prompt,
    INFORMATION_EXTRACTION_SYSTEM,
    get_information_extraction_prompt
)

logger = logging.getLogger(__name__)


class LLMNativeProcessor(SmartProcessor):
    """Enhanced base class for LLM-native processing"""
    
    def suggest_content_placement(self, document: str, new_content_description: str, 
                                 content_type: str = None, operation_name: str = "Content Placement") -> Dict:
        """Let LLM decide where content should go in a document"""
        response = self._call_llm(
            messages=[
                {"role": "system", "content": CONTENT_PLACEMENT_SYSTEM},
                {"role": "user", "content": get_content_placement_prompt(document, new_content_description, content_type)}
            ],
            response_format="json_object",
            operation_name=operation_name
        )
        
        # Define expected types
        expected_types = {
            'recommended_placement': str,
            'reasoning': str,
            'alternative_placements': list,
            'creates_new_section': bool,
            'new_section_name': str  # Can be None, but if present should be str
        }
        
        return self._validate_response_types(response, expected_types)
    
    def is_terminal_section(self, section_name: str, document_context: str = None,
                           operation_name: str = "Terminal Section Check") -> bool:
        """Determine if a section is terminal using LLM understanding"""
        response = self._call_llm(
            messages=[
                {"role": "system", "content": TERMINAL_SECTION_SYSTEM},
                {"role": "user", "content": get_terminal_section_prompt(section_name, document_context)}
            ],
            response_format="json_object",
            operation_name=operation_name
        )
        
        # Define expected types
        expected_types = {
            'is_terminal': bool,
            'reasoning': str,
            'section_purpose': str
        }
        
        validated = self._validate_response_types(response, expected_types)
        return validated.get('is_terminal', False)
    
    def analyze_content_quality(self, content: str, content_type: str,
                               operation_name: str = "Content Quality Analysis") -> Dict:
        """Analyze content quality and completeness"""
        response = self._call_llm(
            messages=[
                {"role": "system", "content": get_content_quality_system(content_type)},
                {"role": "user", "content": get_content_quality_prompt(content, content_type)}
            ],
            response_format="json_object",
            operation_name=operation_name
        )
        
        # Define expected types
        expected_types = {
            'quality_score': int,  # Will convert float to int if needed
            'missing_sections': list,
            'strengths': list,
            'improvements': list,
            'completeness': int
        }
        
        return self._validate_response_types(response, expected_types)
    
    def extract_key_information(self, content: str, extraction_purpose: str,
                               operation_name: str = "Information Extraction") -> Dict:
        """Extract specific information from content using LLM"""
        response = self._call_llm(
            messages=[
                {"role": "system", "content": INFORMATION_EXTRACTION_SYSTEM},
                {"role": "user", "content": get_information_extraction_prompt(content, extraction_purpose)}
            ],
            response_format="json_object",
            operation_name=operation_name
        )
        
        # Since this is flexible, we don't enforce specific types
        # but we can ensure common patterns
        if 'is_valid' in response:
            response = self._validate_response_types(response, {'is_valid': bool})
        
        return response
    
    def _ensure_float_list(self, value: Any) -> List[float]:
        """Ensure value is a list of floats for embeddings"""
        if not value:
            return []
        
        if isinstance(value, list):
            try:
                return [float(x) for x in value]
            except (ValueError, TypeError):
                logger.error(f"Could not convert list to floats: {type(value)}")
                return []
        
        logger.error(f"Expected list for embedding, got: {type(value)}")
        return []
    
    def _validate_response_types(self, response: Dict, expected_types: Dict[str, type]) -> Dict:
        """Validate and coerce response types to match expectations
        
        Args:
            response: The LLM response dictionary
            expected_types: Dict mapping field names to expected types
            
        Returns:
            Response with validated/coerced types
        """
        validated = response.copy()
        
        for field, expected_type in expected_types.items():
            if field not in validated:
                continue
                
            value = validated[field]
            actual_type = type(value)
            
            # If type matches, we're good
            if isinstance(value, expected_type):
                continue
            
            # Try to coerce to expected type
            logger.warning(f"Field '{field}' expected {expected_type.__name__}, got {actual_type.__name__}")
            
            if expected_type == str:
                if isinstance(value, list):
                    # Convert list to string
                    validated[field] = ' '.join(str(item) for item in value)
                else:
                    validated[field] = str(value)
                    
            elif expected_type == list:
                if isinstance(value, str):
                    # Convert string to single-item list
                    validated[field] = [value]
                else:
                    # Try to convert to list
                    try:
                        validated[field] = list(value)
                    except:
                        validated[field] = [str(value)]
                        
            elif expected_type == bool:
                # Convert to boolean
                validated[field] = bool(value)
                
            elif expected_type == int or expected_type == float:
                # Try to convert to number
                try:
                    validated[field] = expected_type(value)
                except:
                    logger.error(f"Could not convert '{field}' to {expected_type.__name__}")
                    validated[field] = 0 if expected_type == int else 0.0
        
        return validated 