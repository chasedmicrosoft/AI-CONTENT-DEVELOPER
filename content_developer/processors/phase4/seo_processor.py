"""
SEO Remediation Processor - Phase 4 Step 1
Optimizes content for search engine visibility
"""
import logging
from pathlib import Path
from typing import Dict, Tuple

from ...models import Config
from ...prompts.phase4 import get_seo_remediation_prompt, SEO_REMEDIATION_SYSTEM
from ..llm_native_processor import LLMNativeProcessor

logger = logging.getLogger(__name__)


class SEOProcessor(LLMNativeProcessor):
    """Processes content for SEO optimization"""
    
    def _process(self, content: str, file_info: Dict, config: Config) -> Tuple[str, Dict]:
        """Process content for SEO remediation
        
        Args:
            content: The content to optimize
            file_info: Information about the file (filename, content_type, etc.)
            config: Configuration object
            
        Returns:
            Tuple of (optimized_content, metadata)
        """
        if self.console_display:
            # Extract just the filename for display
            display_name = Path(file_info.get('filename', 'unknown')).name
            self.console_display.show_operation(f"SEO optimization: {display_name}")
        
        # Create the SEO remediation prompt
        prompt = get_seo_remediation_prompt(content, file_info, config.service_area)
        
        messages = [
            {"role": "system", "content": SEO_REMEDIATION_SYSTEM},
            {"role": "user", "content": prompt}
        ]
        
        # Call LLM for SEO optimization
        result = self._call_llm(
            messages,
            model=self.config.completion_model,
            response_format="json_object",
            operation_name="SEO Remediation"
        )
        
        # Extract and display thinking
        thinking = result.get('thinking', [])
        if thinking and self.console_display:
            self.console_display.show_thinking(thinking, "🔍 AI Thinking - SEO Analysis")
        
        # Extract optimized content
        optimized_content = result.get('optimized_content', content)
        
        # Build metadata
        metadata = {
            'seo_improvements': result.get('seo_improvements', []),
            'primary_keywords': result.get('primary_keywords', []),
            'meta_description': result.get('meta_description', ''),
            'internal_link_suggestions': result.get('internal_link_suggestions', []),
            'thinking': thinking
        }
        
        # Show improvements summary
        if self.console_display and metadata['seo_improvements']:
            self.console_display.show_metric(
                "SEO Improvements", 
                f"{len(metadata['seo_improvements'])} optimizations applied"
            )
            for improvement in metadata['seo_improvements'][:3]:  # Show top 3
                self.console_display.show_status(f"  • {improvement}", "success")
            if len(metadata['seo_improvements']) > 3:
                self.console_display.show_status(
                    f"  ... and {len(metadata['seo_improvements']) - 3} more", 
                    "info"
                )
        
        return optimized_content, metadata
    
    def process(self, content: str, file_info: Dict, config: Config) -> Tuple[str, Dict]:
        """Public interface for processing"""
        return self._process(content, file_info, config) 