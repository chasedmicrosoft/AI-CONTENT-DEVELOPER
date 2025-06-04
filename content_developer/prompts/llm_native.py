"""
LLM-Native prompts for intelligent document processing
"""

import json
from .schemas import (
    CONTENT_PLACEMENT_SCHEMA,
    TERMINAL_SECTION_SCHEMA,
    CONTENT_QUALITY_SCHEMA,
    CHUNK_RANKING_SCHEMA,
    get_information_extraction_schema
)
from .helpers import schema_to_example, extract_type_requirements


# Content Placement
CONTENT_PLACEMENT_SYSTEM = """You are an expert at document organization and content placement.
You understand:
- Logical flow of technical documentation
- Where different types of content belong
- Terminal sections must remain at the end
- Content should enhance document coherence

CRITICAL: You MUST follow JSON type specifications exactly. When a field specifies STRING, never return an array/list. When a field specifies LIST/ARRAY, never return a string."""

def get_content_placement_prompt(document: str, new_content_description: str, content_type: str = None) -> str:
    """Get prompt for suggesting content placement"""
    
    # Generate example from schema
    example = schema_to_example(CONTENT_PLACEMENT_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(CONTENT_PLACEMENT_SCHEMA)
    
    content_type_info = f"\nCONTENT TYPE: {content_type}" if content_type else ""
    
    return f"""I need to add new content to this document:

EXISTING DOCUMENT:
{document}

NEW CONTENT TO ADD:
{new_content_description}
{content_type_info}

Where should this content be placed? Consider:
1. Logical flow and reader experience
2. Related existing sections
3. Terminal sections must stay at the end

Return JSON with EXACTLY these fields and types:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}"""

# Terminal Section Detection
TERMINAL_SECTION_SYSTEM = """You are an expert at understanding document structure.
Terminal sections are those that conclude a document and guide readers to next steps.
Examples include: Next Steps, Related Documentation, See Also, Conclusion, References.

CRITICAL: You MUST follow JSON type specifications exactly. Return booleans as true/false, not strings."""

def get_terminal_section_prompt(section_title: str) -> str:
    """Get prompt for detecting terminal sections"""
    
    # Generate example from schema
    example = schema_to_example(TERMINAL_SECTION_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(TERMINAL_SECTION_SCHEMA)
    
    return f"""Is '{section_title}' a terminal section (a section that typically comes at the end of documentation)?

Terminal sections are like "exit doors" - once you reach them, you're leaving the main content. Examples:
- "What's Next?" / "Next Steps" - Leading readers elsewhere
- "Related Documentation" / "See Also" - External references  
- "Additional Resources" / "Further Reading" - Supplementary materials
- "References" / "Links" - Citation sections

Consider the semantic meaning, not just exact words. 

Return JSON with EXACTLY these fields and types:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}"""

# Content Quality Analysis
def get_content_quality_system(content_type: str) -> str:
    """Get system prompt for content quality analysis"""
    return f"""You are an expert at evaluating technical documentation quality.
You're analyzing a {content_type} document for:
- Completeness of required sections
- Clarity and organization
- Technical accuracy indicators
- Audience appropriateness

CRITICAL: You MUST follow JSON type specifications exactly. Numbers must be actual numbers, not strings."""

def get_content_quality_prompt(content: str, content_type: str = None) -> str:
    """Get prompt for analyzing content quality"""
    
    # Generate example from schema
    example = schema_to_example(CONTENT_QUALITY_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(CONTENT_QUALITY_SCHEMA)
    
    type_context = f"\nContent Type: {content_type}" if content_type else ""
    
    return f"""Analyze the quality of this content:{type_context}

{content}

Return JSON with EXACTLY these fields and types:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}"""

# Information Extraction
INFORMATION_EXTRACTION_SYSTEM = """You are an expert at extracting structured information from documents.
You can identify and extract key concepts, technical details, and relationships.

CRITICAL: You MUST follow JSON type specifications exactly. Always return the requested structure with correct types."""

def get_information_extraction_prompt(content: str, extraction_purpose: str, expected_format: dict = None) -> str:
    """Get prompt for extracting specific information"""
    
    # Special handling for directory validation
    if "directory" in extraction_purpose.lower() and "validate" in extraction_purpose.lower():
        schema = get_information_extraction_schema(extraction_purpose)
        example = schema_to_example(schema)
        type_requirements = extract_type_requirements(schema)
        
        return f"""Extract information for: {extraction_purpose}

From this content:
{content}

VALIDATION APPROACH:
- Understand the repository's organizational pattern
- Evaluate if the selected directory fits that pattern
- Consider practical constraints (what directories actually exist)
- Validate the reasoning, not rigid rules

Return a JSON response with:
{json.dumps(example, indent=2)}

VALIDATION PRINCIPLES:
- Accept practical decisions when ideal options don't exist
- Media/assets/includes directories are NOT valid for documentation
- If no perfect match exists, a general directory is acceptable
- Consider the repository's actual structure, not theoretical ideals
- Only suggest alternatives if they actually exist and are clearly better

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}"""
    
    # Default extraction with format support
    if expected_format:
        # If format is provided, include thinking in the format if not present
        if "thinking" not in expected_format:
            expected_format = {"thinking": [
                "First, I'll analyze the content for the extraction purpose",
                "Then, I'll identify the key information requested",
                "Finally, I'll structure the data according to the required format"
            ], **expected_format}
        format_spec = f"\nReturn JSON matching this structure:\n{json.dumps(expected_format, indent=2)}"
    else:
        # Use schema to generate example
        schema = get_information_extraction_schema(extraction_purpose)
        example = schema_to_example(schema)
        type_requirements = extract_type_requirements(schema)
        
        format_spec = f"""
Return JSON matching this exact structure:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}"""
    
    return f"""Extract information for: {extraction_purpose}

Content:
{content}
{format_spec}"""

# Chunk Ranking
CHUNK_RANKING_SYSTEM = """You are an expert at identifying relevant documentation.

CRITICAL: You MUST follow JSON type specifications exactly. The ranked_indices must be an array of numbers."""

def get_chunk_ranking_prompt(goal: str, chunks_list: str) -> str:
    """Get prompt for ranking content chunks"""
    
    # Generate example from schema
    example = schema_to_example(CHUNK_RANKING_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(CHUNK_RANKING_SCHEMA)
    
    return f"""Rank these content chunks by relevance to the goal.

GOAL: {goal}

CHUNKS TO RANK:
{chunks_list}

Return JSON with EXACTLY these fields and types:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}""" 