"""
Security Remediation Processor - Phase 4 Step 2
Ensures documentation security best practices
"""
import logging
from pathlib import Path
from typing import Dict, Tuple

from ...models import Config
from ...prompts.phase4 import get_security_remediation_prompt, SECURITY_REMEDIATION_SYSTEM
from ..llm_native_processor import LLMNativeProcessor

logger = logging.getLogger(__name__)


class SecurityProcessor(LLMNativeProcessor):
    """Processes content for security remediation"""
    
    def _process(self, content: str, file_info: Dict, config: Config) -> Tuple[str, Dict]:
        """Process content for security remediation
        
        Args:
            content: The content to review and remediate
            file_info: Information about the file (filename, content_type, etc.)
            config: Configuration object
            
        Returns:
            Tuple of (remediated_content, metadata)
        """
        if self.console_display:
            # Extract just the filename for display
            display_name = Path(file_info.get('filename', 'unknown')).name
            self.console_display.show_operation(f"Security review: {display_name}")
        
        # Create the security remediation prompt
        prompt = get_security_remediation_prompt(content, file_info, config.service_area)
        
        messages = [
            {"role": "system", "content": SECURITY_REMEDIATION_SYSTEM},
            {"role": "user", "content": prompt}
        ]
        
        # Call LLM for security remediation
        result = self._call_llm(
            messages,
            model=self.config.completion_model,
            response_format="json_object",
            operation_name="Security Remediation"
        )
        
        # Extract and display thinking
        thinking = result.get('thinking', [])
        if thinking and self.console_display:
            self.console_display.show_thinking(thinking, "🔐 AI Thinking - Security Analysis")
        
        # Extract remediated content
        remediated_content = result.get('remediated_content', content)
        
        # Build metadata
        metadata = {
            'security_issues_found': result.get('security_issues_found', []),
            'security_warnings_added': result.get('security_warnings_added', []),
            'compliance_notes': result.get('compliance_notes', []),
            'confidence': result.get('confidence', 0.9),
            'thinking': thinking
        }
        
        # Show security findings
        if self.console_display:
            issues = metadata['security_issues_found']
            if issues:
                self.console_display.show_warning(
                    f"Security issues found: {len(issues)}"
                )
                for issue in issues[:3]:  # Show top 3
                    self.console_display.show_status(
                        f"  • {issue.get('type', 'unknown')}: {issue.get('description', '')}", 
                        "warning"
                    )
                if len(issues) > 3:
                    self.console_display.show_status(
                        f"  ... and {len(issues) - 3} more", 
                        "warning"
                    )
            else:
                self.console_display.show_status(
                    "✓ No security issues found", 
                    "success"
                )
            
            # Show confidence
            self.console_display.show_metric(
                "Security Confidence", 
                f"{metadata['confidence'] * 100:.0f}%"
            )
        
        return remediated_content, metadata
    
    def process(self, content: str, file_info: Dict, config: Config) -> Tuple[str, Dict]:
        """Public interface for processing"""
        return self._process(content, file_info, config) 