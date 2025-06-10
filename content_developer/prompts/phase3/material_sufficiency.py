"""
Material Sufficiency Prompts - Phase 3: Content Generation
Checks if materials are sufficient before and after content generation
"""
from typing import Dict, List, Optional


def get_pregeneration_sufficiency_prompt(decision, materials: List[Dict], 
                                       existing_content: Optional[str] = None) -> str:
    """Create prompt for pre-generation material sufficiency check
    
    Args:
        decision: ContentDecision object with planned action details
        materials: List of material dictionaries
        existing_content: Optional existing content for UPDATE actions
    """
    materials_summary = _format_materials_for_prompt(materials)
    
    context = ""
    if existing_content:
        context = f"\n\nEXISTING CONTENT TO BE UPDATED:\n{existing_content[:2000]}..."
    
    return f"""Evaluate whether the provided materials are sufficient to create/update the planned documentation.

PLANNED ACTION: {decision.action}
ACTION REASON: {decision.rationale}
CONTENT TYPE: {decision.content_type}
FILE TITLE: {decision.file_title}

PLANNED SECTIONS:
{chr(10).join(f"- {section}" for section in decision.sections[:10])}

MATERIALS PROVIDED:
{materials_summary}{context}

Analyze whether the materials provide enough information to:
1. Cover all planned sections with substance
2. Meet the content goal with technical accuracy
3. Provide value to the target audience (technical professionals)

Think through your analysis step by step, considering:
- Coverage of each planned section by the materials
- Technical depth and accuracy possible with these materials
- Gaps that would require significant inference or external knowledge

Return your response as valid JSON matching this structure:
{{
  "thinking": [
    "Analysis of material coverage for each planned section",
    "Evaluation of technical depth available in materials",
    "Identification of critical gaps that would affect quality"
  ],
  "is_sufficient": "yes|no|partial",
  "coverage_percentage": 0-100,
  "confidence": 0.0-1.0,
  "confidence_reason": "Brief explanation of the assessment",
  "missing_topics": [
    "Critical topics/sections that lack material support"
  ],
  "suggestions": [
    "Specific materials that would improve coverage"
  ]
}}"""


def get_postgeneration_sufficiency_prompt(content: str, decision, 
                                        materials: List[Dict]) -> str:
    """Create prompt for post-generation material sufficiency check
    
    Args:
        content: The generated content to evaluate
        decision: ContentDecision object with action details
        materials: List of material dictionaries
    """
    materials_summary = _format_materials_for_prompt(materials)
    
    return f"""Evaluate whether the provided materials were sufficient to create comprehensive documentation.

CONTENT GOAL: {decision.rationale}
CONTENT TYPE: {decision.content_type}

MATERIALS PROVIDED:
{materials_summary}

GENERATED CONTENT:
{content}

Analyze the generated content against the materials to determine:
1. What percentage of the content is directly supported by the materials (0-100)
2. What areas lack sufficient material support
3. Whether the materials were adequate for creating comprehensive documentation

Think through your analysis step by step, considering:
- Which sections of the generated content directly match material content
- Which sections required inference or external knowledge
- The depth and completeness of material coverage for each topic

Return your response as valid JSON matching this structure:
{{
  "thinking": [
    "Step-by-step analysis of material coverage",
    "Evaluation of each major section against source materials",
    "Identification of gaps and areas of inference"
  ],
  "is_sufficient": "yes|no|partial",
  "coverage_percentage": 0-100,
  "confidence": 0.0-1.0,
  "confidence_reason": "Brief explanation of confidence level",
  "insufficient_areas": [
    "List of specific topics/sections that lack material support"
  ],
  "suggestions": [
    "Specific suggestions for what additional materials would help"
  ]
}}"""


def _format_materials_for_prompt(materials: List[Dict]) -> str:
    """Format materials for inclusion in prompt
    
    Args:
        materials: List of material dictionaries
    """
    if not materials:
        return "No materials provided"
    
    formatted = []
    for i, material in enumerate(materials, 1):
        material_dict = material if isinstance(material, dict) else material.__dict__
        
        formatted.append(f"=== MATERIAL {i}: {material_dict.get('source', 'Unknown')} ===")
        formatted.append(f"Topic: {material_dict.get('main_topic', 'N/A')}")
        formatted.append(f"Type: {material_dict.get('document_type', 'N/A')}")
        
        # Add summary
        if summary := material_dict.get('summary'):
            formatted.append(f"\nSummary:\n{summary}")
        
        # Add key concepts
        if concepts := material_dict.get('key_concepts'):
            formatted.append(f"\nKey Concepts: {', '.join(concepts[:10])}")
        
        # Add technologies
        if techs := material_dict.get('technologies'):
            formatted.append(f"Technologies: {', '.join(techs[:10])}")
        
        # Add FULL content - check both 'full_content' and 'content' fields
        full_content = material_dict.get('full_content') or material_dict.get('content')
        if full_content:
            formatted.append(f"\nFULL CONTENT:\n{'-' * 80}\n{full_content}\n{'-' * 80}")
        else:
            formatted.append("\n[WARNING: No content available for this material]")
        
        formatted.append("")  # Empty line between materials
    
    return '\n'.join(formatted) 