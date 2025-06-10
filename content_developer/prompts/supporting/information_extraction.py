"""
Information Extraction Prompt - Supporting Prompts
Flexible information extraction for various analysis needs
"""
from typing import Dict, Optional


def get_information_extraction_prompt(content: str, extraction_purpose: str, 
                                    expected_format: Dict = None) -> str:
    """Get the prompt for flexible information extraction
    
    Args:
        content: The content to extract information from
        extraction_purpose: What specific information to extract and why
        expected_format: Optional expected format for the extraction
    """
    
    if expected_format:
        schema_info = f"""
Expected output format:
{expected_format}
"""
    else:
        # Provide purpose-specific examples
        if "directory" in extraction_purpose.lower() and "validat" in extraction_purpose.lower():
            schema_info = """
REQUIRED OUTPUT for directory validation:
Return a JSON object with these exact fields:

{
  "thinking": [
    "YOUR analysis of the directory structure",
    "YOUR validation reasoning"
  ],
  "is_valid": true,
  "is_documentation_directory": true,
  "pattern_match": "docs/*",
  "reason": "Directory contains markdown files and follows documentation patterns",
  "concerns": [],
  "suggested_alternative": null
}"""
        elif "sufficiency" in extraction_purpose.lower() or "sufficient" in extraction_purpose.lower():
            schema_info = """
REQUIRED OUTPUT for sufficiency check:
Return a JSON object with these exact fields:

{
  "thinking": [
    "YOUR analysis of available information",
    "YOUR assessment of completeness"
  ],
  "has_sufficient_information": true,
  "insufficient_areas": ["Missing API examples", "No error handling details"],
  "coverage_percentage": 75
}"""
        elif "gap" in extraction_purpose.lower() or "missing" in extraction_purpose.lower():
            schema_info = """
REQUIRED OUTPUT for gap analysis:
Return a JSON object with these exact fields:

{
  "thinking": [
    "YOUR identification of gaps",
    "YOUR recommendations for filling them"
  ],
  "missing_items": ["Authentication details", "Performance considerations"],
  "recommendations": ["Add OAuth flow documentation", "Include benchmarks"]
}"""
        else:
            schema_info = f"""
Extract information that helps achieve: {extraction_purpose}

The output should be a JSON object containing relevant extracted information with a 'thinking' field showing your analysis steps."""
    
    return f"""Extract specific information from the provided content.

PURPOSE: {extraction_purpose}

CONTENT:
{content}

{schema_info}

EXTRACTION GUIDELINES:
1. Focus on information relevant to the stated purpose
2. Be comprehensive but concise
3. Maintain accuracy - don't infer beyond what's stated
4. Structure the output for easy consumption
5. Flag any ambiguities or missing information

Return a JSON object with the extracted information."""


INFORMATION_EXTRACTION_SYSTEM = """You are an expert at extracting structured information from technical content.

CORE CAPABILITIES:
1. Identify key information based on specific purposes
2. Structure extracted data in clear, usable formats
3. Distinguish between stated facts and implications
4. Recognize patterns and relationships in content
5. Maintain accuracy while being comprehensive

EXTRACTION PRINCIPLES:
- Purpose-driven: Extract only what's relevant to the stated goal
- Accuracy-first: Never invent or assume information not present
- Structure-focused: Organize information for easy consumption
- Context-aware: Consider the broader context when extracting
- Quality-oriented: Flag uncertainties or ambiguities

COMMON EXTRACTION TASKS:
1. Technical specifications and requirements
2. Key concepts and definitions
3. Relationships and dependencies
4. Action items and recommendations
5. Gaps and missing information

EXTRACTION APPROACH:
1. Understand the extraction purpose
2. Scan content for relevant information
3. Extract and structure the data
4. Validate completeness and accuracy
5. Format according to requirements

OUTPUT STANDARDS:
- Clear, well-structured JSON
- Relevant to stated purpose
- Accurate representation of source
- Appropriate level of detail
- Useful for downstream processing""" 