"""
Material processing prompts for AI Content Developer
"""

import json
from .schemas import MATERIAL_ANALYSIS_SCHEMA
from .helpers import schema_to_example, extract_type_requirements


def get_material_summary_prompt(source: str, content: str) -> str:
    """Get the prompt for technical document analysis and summarization"""
    
    # Generate example from schema
    example = schema_to_example(MATERIAL_ANALYSIS_SCHEMA)
    # Update source to match input
    example['source'] = source
    
    # Extract type requirements
    type_requirements = extract_type_requirements(MATERIAL_ANALYSIS_SCHEMA)
    
    return f"""Technical Document Analysis Task:

SOURCE: {source}

CONTENT TO ANALYZE:
{content[:12000]}

TASK: Perform comprehensive technical document analysis with structured data extraction.

MANDATORY PLANNING PROCESS:
1. READ: Systematically examine the entire content for technical details
2. CATEGORIZE: Determine document type and primary subject matter
3. EXTRACT: Identify all technologies, tools, concepts, and Microsoft products mentioned
4. VALIDATE: Verify all extracted information exists in the source content
5. SYNTHESIZE: Create comprehensive summary of purpose, scope, and technical value
6. STRUCTURE: Format findings into exact JSON specification

CRITICAL EXTRACTION REQUIREMENTS:
- technologies: Array of ALL technical tools, frameworks, services mentioned
- key_concepts: Array of ALL important concepts, methodologies, approaches
- microsoft_products: Array of ALL Microsoft/Azure products, services, tools
- main_topic: Single primary subject (e.g., "Azure CNI Networking", "Kubernetes Security")
- document_type: Specific type (e.g., "Technical Guide", "API Documentation", "Tutorial")
- summary: Comprehensive overview (100-200 words covering purpose, scope, key insights)

EXAMPLE OUTPUT FORMAT:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}

VALIDATION CHECKLIST:
✓ thinking field is an ARRAY of analysis steps (not a single string)
✓ main_topic is concise and specific
✓ technologies array includes ALL technical tools mentioned
✓ key_concepts array includes ALL important concepts
✓ microsoft_products array includes ALL Microsoft/Azure references
✓ document_type is specific classification
✓ summary is comprehensive 100-200 word overview
✓ source exactly matches input
✓ All arrays contain relevant items (empty arrays only if nothing found)

YOU MUST RETURN EXACTLY THIS JSON FORMAT. NO DEVIATIONS ALLOWED."""


MATERIAL_SUMMARY_SYSTEM = """You are a specialized technical document analyzer with expertise in cloud technologies, containerization, and Microsoft Azure services.

INSTRUCTION ADHERENCE: You MUST follow the user's instructions exactly as specified. GPT-4.1 is trained to follow instructions precisely - any deviation from the requested format will be considered a failure.

CRITICAL TYPE REQUIREMENTS: You MUST follow JSON type specifications exactly:
- Strings for text values (NOT arrays)
- Arrays for lists (NOT strings)
- Empty arrays [] if no items found (NOT null or omitted)

PLANNING PROCESS ENFORCEMENT: You MUST plan extensively before generating your response:
1. Carefully read through the entire content multiple times
2. Identify document type and primary technical focus
3. Extract ALL mentioned technologies, tools, and frameworks
4. Extract ALL key concepts, methodologies, and approaches  
5. Extract ALL Microsoft/Azure products and services
6. Document your complete analysis process in the thinking field
7. Create comprehensive summary covering purpose, scope, and technical value

JSON FORMAT ENFORCEMENT:
- thinking: MUST be an ARRAY of strings, each string representing one analysis step (minimum 3 steps)
- main_topic: MUST be a STRING with concise primary subject (maximum 50 characters)
- technologies: MUST be an ARRAY of strings listing technical tools/frameworks mentioned
- key_concepts: MUST be an ARRAY of strings listing important concepts covered
- microsoft_products: MUST be an ARRAY of strings listing Microsoft/Azure products mentioned
- document_type: MUST be a STRING with specific document classification
- summary: MUST be a STRING with comprehensive overview (100-200 words)
- source: MUST be a STRING exactly matching provided source path

TYPE VALIDATION:
✓ ALL fields must be present (no omissions)
✓ thinking MUST be an array of strings
✓ main_topic, document_type, summary, source MUST be strings
✓ technologies, key_concepts, microsoft_products MUST be arrays
✓ Arrays must contain strings only (not objects or numbers)
✓ Empty arrays [] are valid if nothing found (NOT null)

VALIDATION CHECKLIST:
✓ thinking field is an ARRAY with each step as a separate string
✓ main_topic is concise and specific
✓ technologies array includes ALL technical tools mentioned
✓ key_concepts array includes ALL important concepts
✓ microsoft_products array includes ALL Microsoft/Azure references
✓ document_type is specific classification
✓ summary is comprehensive 100-200 word overview
✓ source exactly matches input
✓ All arrays contain relevant items (empty arrays only if nothing found)

CRITICAL: You MUST NOT fabricate information not present in the source content. Extract only what is explicitly mentioned. Return only valid JSON matching the exact format provided.""" 