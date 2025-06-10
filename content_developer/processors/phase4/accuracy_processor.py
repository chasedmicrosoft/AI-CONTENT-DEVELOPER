"""
Technical Accuracy Validation Processor - Phase 4 Step 3
Validates content accuracy against source materials
"""
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from ...models import Config
from ...prompts.phase4 import get_accuracy_validation_prompt, ACCURACY_VALIDATION_SYSTEM
from ..llm_native_processor import LLMNativeProcessor

logger = logging.getLogger(__name__)


class AccuracyProcessor(LLMNativeProcessor):
    """Processes content for technical accuracy validation"""
    
    def _process(self, content: str, file_info: Dict, materials: List[Dict], 
                 config: Config) -> Tuple[str, Dict]:
        """Process content for accuracy validation
        
        Args:
            content: The content to validate
            file_info: Information about the file (filename, content_type, etc.)
            materials: List of source materials used
            config: Configuration object
            
        Returns:
            Tuple of (validated_content, metadata)
        """
        if self.console_display:
            # Extract just the filename for display
            display_name = Path(file_info.get('filename', 'unknown')).name
            self.console_display.show_operation(
                f"Technical validation: {display_name}"
            )
        
        # Create the accuracy validation prompt
        prompt = get_accuracy_validation_prompt(content, file_info, materials, config.service_area)
        
        messages = [
            {"role": "system", "content": ACCURACY_VALIDATION_SYSTEM},
            {"role": "user", "content": prompt}
        ]
        
        # Call LLM for accuracy validation
        result = self._call_llm(
            messages,
            model=self.config.completion_model,
            response_format="json_object",
            operation_name="Technical Accuracy Validation"
        )
        
        # Extract and display thinking
        thinking = result.get('thinking', [])
        if thinking and self.console_display:
            self.console_display.show_thinking(thinking, "📊 AI Thinking - Accuracy Validation")
        
        # Extract validated content
        validated_content = result.get('validated_content', content)
        validation_result = result.get('validation_result', 'unknown')
        accuracy_score = result.get('accuracy_score', 0.0)
        
        # Build metadata
        metadata = {
            'validation_result': validation_result,
            'accuracy_score': accuracy_score,
            'accuracy_issues': result.get('accuracy_issues', []),
            'unsupported_claims': result.get('unsupported_claims', []),
            'suggestions': result.get('suggestions', []),
            'thinking': thinking
        }
        
        # Show validation results
        if self.console_display:
            # Show overall result
            if validation_result == 'pass':
                self.console_display.show_status(
                    f"✓ Technical accuracy validated: {accuracy_score * 100:.0f}%", 
                    "success"
                )
            elif validation_result == 'pass_with_corrections':
                self.console_display.show_warning(
                    f"⚠️  Accuracy validated with corrections: {accuracy_score * 100:.0f}%"
                )
            else:
                self.console_display.show_error(
                    f"❌ Accuracy validation failed: {accuracy_score * 100:.0f}%",
                    "Validation Failed"
                )
            
            # Show issues if any
            issues = metadata['accuracy_issues']
            if issues:
                self.console_display.show_metric(
                    "Accuracy Issues", 
                    f"{len(issues)} issues found"
                )
                for issue in issues[:3]:  # Show top 3
                    self.console_display.show_status(
                        f"  • {issue.get('type', 'unknown')}: {issue.get('issue', '')}", 
                        "warning"
                    )
                if len(issues) > 3:
                    self.console_display.show_status(
                        f"  ... and {len(issues) - 3} more", 
                        "warning"
                    )
            
            # Show unsupported claims
            unsupported = metadata['unsupported_claims']
            if unsupported:
                self.console_display.show_warning(
                    f"Unsupported claims: {len(unsupported)}"
                )
                for claim in unsupported[:2]:  # Show top 2
                    self.console_display.show_status(f"  • {claim[:100]}...", "warning")
        
        return validated_content, metadata
    
    def process(self, content: str, file_info: Dict, materials: List[Dict], 
                config: Config) -> Tuple[str, Dict]:
        """Public interface for processing"""
        return self._process(content, file_info, materials, config) 