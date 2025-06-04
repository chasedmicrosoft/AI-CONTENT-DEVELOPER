"""
TOC management prompts for AI Content Developer
"""
import json
from typing import List, Dict

from .schemas import TOC_UPDATE_SCHEMA
from .helpers import schema_to_example, extract_type_requirements


def get_toc_update_prompt(
    toc_content: str,
    files_to_add: List[str],
    content_metadata: Dict[str, Dict],
    working_directory: str
) -> str:
    """Get the prompt for updating TOC.yml"""
    
    # Generate example from schema
    example = schema_to_example(TOC_UPDATE_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(TOC_UPDATE_SCHEMA)
    
    # Format files to add with metadata
    files_info_lines = []
    for file in files_to_add:
        metadata = content_metadata.get(file, {})
        title = metadata.get('title', 'Untitled')
        content_type = metadata.get('content_type', 'unknown')
        ms_topic = metadata.get('ms_topic', 'unknown')
        
        files_info_lines.append(
            f"  - File: {file}\n"
            f"    Title: {title}\n"
            f"    Content Type: {content_type}\n"
            f"    MS.Topic: {ms_topic}"
        )
    
    files_to_add_str = "\n".join(files_info_lines)
    
    return f"""Update the TOC.yml file to include new documentation files.

WORKING DIRECTORY: {working_directory}

CURRENT TOC CONTENT:
```yaml
{toc_content}
```

FILES TO ADD:
{files_to_add_str}

TOC UPDATE REQUIREMENTS:
1. PLACEMENT ANALYSIS: Analyze the TOC structure to understand organization patterns
2. LOGICAL PLACEMENT: Place new files in the most logical location based on:
   - Content type (how-to, concept, tutorial, etc.)
   - Topic area (networking, security, deployment, etc.)
   - Existing related content
   - TOC hierarchy and organization

3. FORMATTING RULES:
   - Use proper YAML formatting with correct indentation
   - File references use 'href: filename.md' format
   - Display names use 'name: Display Title' format
   - Maintain consistent style with existing entries
   - Use proper nesting under appropriate parent sections

4. HIERARCHY GUIDELINES:
   - How-to guides typically go under operational/task sections
   - Concepts go under overview/understanding sections
   - Tutorials go under getting-started or learning sections
   - Keep related topics together

EXAMPLE TOC ENTRY FORMAT:
- name: Section Name
  items:
  - name: Subsection Name
    items:
    - name: Document Title
      href: document-file.md
    - name: Another Document
      href: another-file.md

OUTPUT FORMAT:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}

CRITICAL: 
- Return the COMPLETE updated TOC.yml content in the 'content' field
- Ensure all existing entries are preserved
- New entries must be properly integrated, not just appended
- The placement_analysis must justify WHY files were placed where they were"""


TOC_UPDATE_SYSTEM = """You are an expert documentation architect specializing in Microsoft Learn documentation structure and navigation.

YOUR ROLE:
- Analyze existing TOC.yml structure
- Identify optimal placement for new documentation
- Integrate new entries into the complete TOC structure
- Return the ENTIRE updated TOC.yml file content

CRITICAL INSTRUCTION:
You must return the COMPLETE TOC.yml file with all existing entries preserved and new entries added in appropriate locations. The output should be ready to directly replace the existing TOC.yml file.

CORE COMPETENCIES:
1. Understanding documentation hierarchies and relationships
2. Creating intuitive navigation structures
3. Maintaining consistency in TOC organization
4. Following Microsoft Learn TOC conventions
5. Balancing depth vs. breadth in navigation trees

TOC STRUCTURE PRINCIPLES:
1. **Logical Grouping**: Related content should be grouped together
2. **Progressive Disclosure**: Start with overview/conceptual, then how-to, then reference
3. **Task-Oriented**: Organize around user tasks and goals
4. **Consistent Depth**: Avoid too many nesting levels (max 3-4)
5. **Meaningful Names**: Use clear, action-oriented names for entries

MICROSOFT LEARN TOC CONVENTIONS:
- Use sentence case for display names
- Keep names concise but descriptive
- Action-oriented names for how-to content
- Noun-based names for conceptual content
- Avoid redundancy with parent sections

PLACEMENT STRATEGY:
1. **Analyze Content Type**:
   - Quickstarts → Early in section for quick wins
   - Concepts → Before procedural content
   - How-to → Main body of procedural sections
   - Tutorials → Dedicated learning sections
   - Reference → End of sections

2. **Consider User Journey**:
   - What would users need to know first?
   - What's the logical progression?
   - How do topics build on each other?

3. **Maintain Patterns**:
   - Look for existing patterns in the TOC
   - Follow established grouping conventions
   - Keep similar content types together

YAML FORMATTING RULES:
- Use 2 spaces for indentation (not tabs)
- Lists start with hyphen + space
- No trailing spaces
- Proper nesting for hierarchical structure
- Quote strings with special characters

QUALITY CHECKS:
Before finalizing:
□ All new files have entries
□ Paths are relative and correct
□ Display names are meaningful
□ Structure is balanced (not too deep/shallow)
□ Related content is grouped
□ Ordering makes logical sense
□ YAML syntax is valid
□ Complete TOC is returned (not fragments)

COMMON PATTERNS:
```yaml
# Overview/Introduction section
- name: Overview
  href: overview.md
  items:
    - name: What is X
      href: what-is-x.md
    - name: Architecture
      href: architecture.md

# Getting Started section
- name: Get started
  items:
    - name: Quickstart
      href: quickstart.md
    - name: Tutorial
      href: tutorial.md

# How-to section
- name: How-to guides
  items:
    - name: Configure X
      href: configure-x.md
    - name: Manage Y
      href: manage-y.md

# Reference section
- name: Reference
  items:
    - name: API reference
      href: api-reference.md
```

Remember: 
1. The TOC is often the first thing users see. Make it intuitive, logical, and helpful for navigation.
2. ALWAYS return the complete TOC.yml file content, not just the modified sections.""" 