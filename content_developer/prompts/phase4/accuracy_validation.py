"""
Technical Accuracy Validation Prompt - Phase 5 Step 3
Validates content accuracy against supporting materials and technical specifications
"""

ACCURACY_VALIDATION_SYSTEM = """You are a technical accuracy validator specializing in cloud documentation. Your task is to validate technical content against source materials, ensuring all statements, code examples, and procedures are accurate and up-to-date. You have deep expertise in cloud technologies and documentation standards."""


def get_accuracy_validation_prompt(content: str, file_info: dict, materials: list, service_area: str) -> str:
    """Generate prompt for technical accuracy validation
    
    Args:
        content: The content to validate
        file_info: Dictionary with filename, content_type, etc.
        materials: List of source materials used
        service_area: The service area (e.g., Azure Kubernetes Service)
    """
    # Format materials for validation
    materials_summary = _format_materials_for_validation(materials)
    
    return f"""Validate the technical accuracy of the following documentation against the source materials.

SERVICE AREA: {service_area}
CONTENT TYPE: {file_info.get('content_type', 'unknown')}
FILE: {file_info.get('filename', 'unknown')}

CONTENT TO VALIDATE:
{content}

SOURCE MATERIALS:
{materials_summary}

VALIDATION REQUIREMENTS:
1. Technical Accuracy
   - Verify all technical statements against source materials
   - Check version numbers and compatibility claims
   - Validate API calls, parameters, and responses
   - Ensure command syntax is correct
   - Verify configuration values and limits

2. Code Examples
   - Validate all code snippets compile/run correctly
   - Check for deprecated methods or features
   - Ensure proper error handling is shown
   - Verify output matches what's described

3. Procedures and Steps
   - Confirm step sequences are correct
   - Validate prerequisites are complete
   - Check that outcomes match descriptions
   - Ensure no steps are missing

4. Factual Accuracy
   - Verify all facts against source materials
   - Check service limits and quotas
   - Validate pricing tier information
   - Ensure regional availability is correct

5. Consistency
   - Check terminology consistency
   - Verify naming conventions
   - Ensure consistent formatting
   - Validate cross-references

6. Currency
   - Flag any outdated information
   - Suggest updates for deprecated features
   - Note when newer alternatives exist
   - Check for recent service updates

VALIDATION APPROACH:
- Compare each claim against source materials
- Flag unsupported statements
- Suggest corrections based on materials
- Note when additional verification is needed
- Maintain technical precision

Return your response as JSON with this structure:
{{
  "thinking": [
    "Cross-referencing content with materials",
    "Identifying accuracy issues",
    "Validating technical claims",
    "Checking for completeness"
  ],
  "validation_result": "pass|fail|pass_with_corrections",
  "accuracy_score": 0.0-1.0,
  "validated_content": "The full validated markdown content only",
  "accuracy_issues": [
    {{
      "type": "factual|code|procedure|version|deprecated",
      "location": "section or line reference",
      "issue": "description of the issue",
      "correction": "suggested correction",
      "source": "material reference"
    }}
  ],
  "unsupported_claims": [
    "List of claims not found in source materials"
  ],
  "suggestions": [
    "Additional improvements for accuracy"
  ]
}}"""


def _format_materials_for_validation(materials: list) -> str:
    """Format materials for the validation prompt"""
    if not materials:
        return "No source materials provided"
    
    formatted = []
    for i, material in enumerate(materials, 1):
        material_dict = material if isinstance(material, dict) else material.__dict__
        
        formatted.append(f"=== MATERIAL {i}: {material_dict.get('source', 'Unknown')} ===")
        formatted.append(f"Type: {material_dict.get('document_type', 'N/A')}")
        formatted.append(f"Topic: {material_dict.get('main_topic', 'N/A')}")
        
        # Include key technical details
        if summary := material_dict.get('summary'):
            formatted.append(f"\nSummary:\n{summary}")
        
        if technologies := material_dict.get('technologies'):
            formatted.append(f"\nTechnologies: {', '.join(technologies[:10])}")
        
        # Add relevant content excerpts
        if content := material_dict.get('content'):
            # Show more content for validation purposes
            if len(content) > 10000:
                content = content[:10000] + "\n\n[... additional content available ...]"
            formatted.append(f"\nContent:\n{content}")
        
        formatted.append("")  # Empty line between materials
    
    return '\n'.join(formatted) 