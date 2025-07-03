"""
TOC Update Prompt - Phase 4: TOC Management
Updates table of contents (TOC) YAML files with new or updated content entries
"""
from typing import Dict, List


def get_toc_update_prompt(toc_content: str, files_to_add: List[str], 
                         content_metadata: Dict[str, Dict], working_directory: str) -> str:
    """Get the prompt for updating a TOC file with integrated placement analysis"""
    
    # Format file information
    file_info = []
    for file in files_to_add:
        metadata = content_metadata.get(file, {})
        file_info.append(f"""
File: {file}
- Title: {metadata.get('title', 'Untitled')}
- Content Type: {metadata.get('content_type', 'Unknown')}
- MS Topic: {metadata.get('ms_topic', 'Unknown')}
- Description: {metadata.get('description', 'No description available')}""")
    
    return f"""Update the Table of Contents (TOC) YAML file to include new documentation files.

WORKING DIRECTORY: {working_directory}

=== CURRENT TOC STRUCTURE ===
{toc_content}

=== FILES TO ADD ===
{chr(10).join(file_info)}

=== INTEGRATED TASK ===
1. ANALYZE the current TOC structure to understand:
   - The organizational hierarchy
   - Grouping patterns (by feature, content type, etc.)
   - Naming conventions for sections
   - Existing content distribution

2. DETERMINE optimal placement for each new file by:
   - Matching content type to existing sections
   - Following the established organizational pattern
   - Considering logical user navigation flow
   - Maintaining balanced section sizes

3. UPDATE the TOC by:
   - Adding entries in the determined locations
   - Using proper YAML indentation (2 spaces)
   - Following existing naming conventions
   - Preserving all existing entries and structure

=== PLACEMENT GUIDELINES ===
- Group similar content types together
- Place concepts before how-tos for the same feature
- Keep related topics in proximity
- Maintain alphabetical order within sections when applicable
- Ensure new entries don't disrupt the logical flow

=== YAML FORMAT REQUIREMENTS ===
- Use exactly 2 spaces for each indentation level
- Place href at the same level as name
- Include displayName only if different from filename
- Do not use tabs, only spaces
- Maintain consistent structure throughout

REQUIRED OUTPUT:
Return a JSON object with these exact fields:

{{
  "thinking": [
    "YOUR analysis of the current TOC structure",
    "YOUR identification of organizational patterns",
    "YOUR determination of optimal placement for each file",
    "YOUR reasoning for the placement decisions"
  ],
  "placement_analysis": {{
    "structure_type": "feature-based organization with content type grouping",
    "main_sections": ["Getting Started", "Concepts", "How-to Guides", "Reference"],
    "placement_rationale": "Files placed according to content type within relevant feature sections"
  }},
  "content": "- name: Root Section\\n  items:\\n  - name: Getting Started\\n    href: getting-started.md\\n  - name: Concepts\\n    items:\\n    - name: Overview\\n      href: overview.md\\n    - name: New Concept\\n      href: new-concept.md\\n  - name: How-to Guides\\n    items:\\n    - name: Existing Guide\\n      href: existing-guide.md\\n    - name: New Guide\\n      href: new-guide.md",
  "entries_added": [
    "new-concept.md",
    "new-guide.md"
  ],
  "placement_decisions": {{
    "new-concept.md": "Placed under Concepts section as it's a conceptual document explaining core principles",
    "new-guide.md": "Added to How-to Guides section following the existing pattern for procedural content"
  }}
}}

FIELD REQUIREMENTS:
- thinking: Array of YOUR ACTUAL analysis steps (3-20 items)
- placement_analysis:
  - structure_type: Description of the TOC's organizational pattern
  - main_sections: Array of main section names in the TOC
  - placement_rationale: Overall strategy for placing new files
- content: Complete updated TOC.yml content as a single string
  - Must include ALL existing entries
  - Must add new entries in appropriate locations
  - Must use proper YAML formatting (2-space indentation)
- entries_added: Array of filenames that were added to the TOC
- placement_decisions: Object mapping each filename to explanation of its placement

CRITICAL: 
- Return the COMPLETE updated TOC with new entries properly integrated
- Each placement decision must include clear reasoning
- The structure_preserved field must be true unless major reorganization was needed
- The validation_status must confirm the YAML is valid"""


TOC_UPDATE_SYSTEM = """You are an expert at managing Microsoft documentation Table of Contents (TOC) files.

CORE COMPETENCIES:
1. Understanding YAML structure and formatting requirements
2. Analyzing documentation hierarchy and organization patterns
3. Making logical content placement decisions
4. Maintaining consistency in naming and structure
5. Ensuring valid YAML syntax with proper indentation

PRIMARY RESPONSIBILITIES:
1. Preserve the existing TOC structure and all current entries
2. Integrate new files in the most logical locations
3. Follow established patterns for naming and organization
4. Maintain proper YAML formatting (2-space indentation)
5. Provide clear reasoning for placement decisions

PLACEMENT STRATEGY:
- Analyze the existing structure before making changes
- Group related content together
- Follow the principle of progressive disclosure
- Consider the user's navigation journey
- Balance section sizes for better usability

YAML FORMATTING RULES:
- Always use 2 spaces for indentation (never tabs)
- Maintain consistent structure throughout
- Place 'href' at the same indentation level as 'name'
- Use 'displayName' only when it differs from the filename
- Ensure proper list formatting with '- name:' structure

QUALITY STANDARDS:
- Every placement must have logical justification
- The updated TOC must maintain its navigational clarity
- New entries should feel naturally integrated
- The YAML must be syntactically valid
- Structure changes should be minimal and justified

OUTPUT REQUIREMENTS:
- Complete updated TOC with all existing and new entries
- Clear reasoning for each placement decision
- Confirmation of structure preservation
- Validation that the YAML is properly formatted""" 