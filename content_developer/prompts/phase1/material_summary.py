"""
Material Summary Prompt - Phase 1: Repository Analysis
Analyzes support materials (Word docs, PDFs, URLs) to extract key information
"""
from typing import Dict

def get_material_summary_prompt(source: str, content: str) -> str:
    """Get the prompt for summarizing material content"""
    
    return f"""Extract the required fields by analyzing this material.

SOURCE: {source}

CONTENT:
{content}

REQUIRED OUTPUT:
Return a JSON object with these exact fields:

{{
  "thinking":"Your step-by-step thoughts",
  "main_topic": "Primary Subject Starting With Capital Letter",
  "technologies": ["Tool1", "Framework2", "Language3"],
  "key_concepts": ["concept requiring documentation", "another key concept"],
  "microsoft_products": ["Azure Service Name", "Another Azure Product"],
  "document_type": "PRD|Design Document|Technical Specification|Meeting Notes|Email|API Documentation|Architecture Document|Requirements Document|User Story|Feature Brief|Other",
  "summary": "A 50-500 character summary of the provided material",
  "source": "{source}"
}}

FIELD REQUIREMENTS:
- thinking: Array of YOUR ACTUAL thoughts (not generic placeholders)
- main_topic: String (5-200 chars, must start with capital letter)
- technologies: Array of ALL tools, frameworks, languages, platforms explicitly mentioned
- key_concepts: Array of core concepts that need documentation (minimum 1)
- microsoft_products: Array of ONLY Microsoft/Azure services (must start with Azure/Microsoft/Office/Windows/Dynamics)
- document_type: Must be EXACTLY one of the values shown above
- summary: String (50-500 chars) describing what documentation could be created
- source: The exact source path provided

IMPORTANT:
- Extract ONLY information explicitly stated in the material
- Do NOT invent or assume information
- If a field has no applicable data, use empty array [] or appropriate empty value
- Your "thinking" steps must reflect YOUR ACTUAL analysis, not generic templates"""


MATERIAL_SUMMARY_SYSTEM = """You are a technical documentation analyst who extracts specific information from materials.

TASK: Extract information from the provided materials and return EXACTLY these fields:
1. thinking: Your step-by-step analysis process
2. main_topic: The primary subject (5-200 chars, start with capital)
3. technologies: ALL tools, frameworks, languages, platforms mentioned
4. key_concepts: Core ideas that need documentation
5. microsoft_products: ONLY Azure/Microsoft services (must start with Azure/Microsoft/Office/Windows/Dynamics)
6. document_type: Classify as one of: PRD, Design Document, Technical Specification, Meeting Notes, Email, API Documentation, Architecture Document, Requirements Document, User Story, Feature Brief, Other
7. summary: 50-500 char documentation-focused summary (start with capital, end with period)
8. source: The material source path

RULES:
- Extract ONLY what's explicitly stated in the material
- If a field has no data, return empty array/string
- Focus on information relevant for creating documentation
- Do NOT add analysis or interpretation beyond extraction
- Use thinking field to show your extraction process
- DO NOT invent any information that is not explicitly stated in the material""" 