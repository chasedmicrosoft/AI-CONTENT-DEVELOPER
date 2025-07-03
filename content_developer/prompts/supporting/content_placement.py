"""
Content Placement Prompt - Supporting Prompts
Determines optimal placement for new content in documentation hierarchy
"""
from typing import Dict, List


def get_content_placement_prompt(new_content_info: Dict, toc_structure: Dict, 
                                existing_content_analysis: List[Dict]) -> str:
    """Get the prompt for determining content placement in TOC"""
    
    return f"""Analyze the documentation structure and determine the optimal placement for new content.

NEW CONTENT INFORMATION:
{new_content_info}

CURRENT TOC STRUCTURE:
{toc_structure}

EXISTING CONTENT ANALYSIS:
{existing_content_analysis}

Determine:
1. The most logical section for this content
2. The specific placement within that section
3. How it relates to existing content
4. Whether any reorganization is beneficial

Consider:
- Content type alignment
- User navigation flow
- Logical grouping
- Progressive disclosure
- Balanced section sizes

REQUIRED OUTPUT:
Return a JSON object with these exact fields:

{{
  "thinking": [
    "YOUR analysis of the current structure",
    "YOUR evaluation of content relationships",
    "YOUR placement reasoning"
  ],
  "recommended_placement": "Getting Started > Installation > Prerequisites",
  "alternative_placements": [
    "Concepts > Architecture > Components",
    "How-to Guides > Setup > Initial Configuration"
  ],
  "creates_new_section": false,
  "new_section_name": null
}}

FIELD REQUIREMENTS:
- thinking: Array of YOUR ACTUAL analysis steps (2-10 items)
- recommended_placement: String path showing where to place content (use " > " as separator)
- alternative_placements: Array of other valid placement options
- creates_new_section: Boolean indicating if a new section is needed
- new_section_name: String name for new section if created, otherwise null"""


CONTENT_PLACEMENT_SYSTEM = """You are an expert at organizing technical documentation for optimal user navigation.

CORE COMPETENCIES:
1. Understanding documentation hierarchy and information architecture
2. Analyzing content relationships and dependencies
3. Optimizing navigation flow for different user journeys
4. Balancing section sizes and content distribution
5. Maintaining logical grouping of related topics

PRIMARY OBJECTIVES:
- Ensure content is discoverable where users expect it
- Group related topics together logically
- Follow progressive disclosure principles
- Maintain consistency with existing patterns
- Optimize for common user tasks and workflows

PLACEMENT PRINCIPLES:
1. Concepts before procedures for the same feature
2. Prerequisites before advanced topics
3. Common scenarios before edge cases
4. Overview content before detailed references
5. Troubleshooting near related feature documentation

ANALYSIS APPROACH:
- Review existing structure patterns
- Identify content type and purpose
- Consider target audience needs
- Evaluate relationship to existing content
- Determine optimal user flow

OUTPUT REQUIREMENTS:
- Clear recommendation for placement
- Logical justification for the decision
- Alternative placements if applicable
- Impact assessment on navigation
- Specific insertion point in hierarchy""" 