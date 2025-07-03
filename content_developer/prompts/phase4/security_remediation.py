"""
Documentation Security Remediation Prompt - Phase 5 Step 2
Ensures documentation follows security best practices and doesn't expose sensitive information
"""

SECURITY_REMEDIATION_SYSTEM = """You are a security expert specializing in technical documentation. Your task is to review and remediate documentation for security concerns, ensuring no sensitive information is exposed while maintaining useful technical content. You understand cloud security, DevSecOps practices, and documentation security standards."""


def get_security_remediation_prompt(content: str, file_info: dict, service_area: str) -> str:
    """Generate prompt for security remediation of content
    
    Args:
        content: The content to review and remediate
        file_info: Dictionary with filename, content_type, etc.
        service_area: The service area (e.g., Azure Kubernetes Service)
    """
    return f"""Review and remediate the following technical documentation for security concerns.

SERVICE AREA: {service_area}
CONTENT TYPE: {file_info.get('content_type', 'unknown')}
FILE: {file_info.get('filename', 'unknown')}

CURRENT CONTENT:
{content}

SECURITY REVIEW REQUIREMENTS:
1. Sensitive Information Check
   - Remove any hardcoded credentials, keys, or tokens
   - Replace real IP addresses with RFC 1918 private ranges or examples
   - Remove real domain names (use example.com, contoso.com)
   - Remove real email addresses
   - Remove employee names or personal information

2. Resource Identifiers
   - Replace real Azure subscription IDs with placeholders
   - Use generic resource group names
   - Replace real storage account names with examples
   - Ensure no production resource names are exposed

3. Security Best Practices
   - Ensure examples follow least privilege principle
   - Add security warnings where appropriate
   - Include security considerations sections
   - Highlight when examples are simplified for clarity

4. Code Security
   - Review code examples for security vulnerabilities
   - Ensure no insecure practices are demonstrated
   - Add comments about security implications
   - Include secure alternatives where applicable

5. Network Security
   - Use proper CIDR notation for examples
   - Don't expose real network topologies
   - Include firewall/NSG best practices where relevant

6. Compliance Considerations
   - Ensure examples are compliant with common standards
   - Add notes about compliance requirements where relevant
   - Include data residency considerations if applicable

REMEDIATION GUIDELINES:
- Replace sensitive data with realistic but safe placeholders
- Maintain technical accuracy and usefulness
- Add [!INCLUDE] statements for common security warnings
- Preserve the educational value of examples
- Use Microsoft documentation standards for placeholders

Return your response as JSON with this structure:
{{
  "thinking": [
    "Identification of security issues",
    "Analysis of sensitive data exposure",
    "Strategy for remediation",
    "Validation of technical usefulness"
  ],
  "remediated_content": "The full remediated markdown content only",
  "security_issues_found": [
    {{"type": "credential|ip|domain|etc", "description": "what was found", "remediation": "how it was fixed"}}
  ],
  "security_warnings_added": [
    "List of security warnings or notes added"
  ],
  "compliance_notes": ["Any compliance considerations added"],
  "confidence": 0.0-1.0
}}""" 