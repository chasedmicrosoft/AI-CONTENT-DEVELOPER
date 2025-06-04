"""
Content generation prompts for AI Content Developer
"""
import json
from typing import Dict, List, Optional

from .schemas import CREATE_CONTENT_SCHEMA, UPDATE_CONTENT_SCHEMA
from .helpers import (
    format_materials_with_content, format_chunks_for_reference,
    get_content_type_template, format_microsoft_elements,
    schema_to_example, extract_type_requirements
)


def get_create_content_prompt(
    config, action: Dict, materials_content: Dict[str, str], 
    materials_summaries: List[Dict], related_chunks: List[Dict],
    chunk_context: str, content_type_info: Dict, content_standards: Dict) -> str:
    """Get the prompt for creating new content"""
    
    # Generate example from schema
    example = schema_to_example(CREATE_CONTENT_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(CREATE_CONTENT_SCHEMA)
    
    # Format materials with full content
    materials_info = format_materials_with_content(materials_content, materials_summaries)
    
    # Format related chunks for reference
    chunks_reference = format_chunks_for_reference(related_chunks)
    
    # Get content type specific template
    content_template = get_content_type_template(action['content_type'], content_standards)
    
    # Get Microsoft elements formatting guide
    ms_elements = format_microsoft_elements(content_standards)
    
    audience_level_info = ""
    if config.audience and config.audience_level:
        audience_level_info = f"""
TARGET AUDIENCE: {config.audience}
AUDIENCE LEVEL: {config.audience_level}"""
    
    return f"""Create a new {action['content_type']} based on the following materials and guidelines.

FILE TO CREATE: {action['filename']}
CONTENT TYPE: {action['content_type']}
MS.TOPIC: {action['ms_topic']}
SERVICE AREA: {config.service_area}{audience_level_info}

=== CREATION INSTRUCTIONS (Content Brief) ===
{action['content_brief']}

=== MATERIALS TO USE ===
{materials_info}

=== RELATED DOCUMENTATION CONTEXT ===
{chunks_reference}

{chunk_context}

=== CONTENT TYPE REQUIREMENTS ===
{content_template}

=== MICROSOFT DOCUMENTATION FORMATTING ===
{ms_elements}

TASK: Create a complete {action['content_type']} that:
1. Addresses the objective stated in the content brief
2. Incorporates relevant information from the provided materials
3. Follows the content type template structure
4. Maintains consistency with related documentation
5. Uses proper Microsoft documentation formatting

OUTPUT FORMAT:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}

CRITICAL: Return the COMPLETE document content as a single string in the 'content' field. The document must be production-ready with proper frontmatter, sections, and formatting."""


CREATE_CONTENT_SYSTEM = """You are an expert technical documentation writer specializing in Microsoft Azure documentation.

YOUR ROLE:
- You are the WRITER, not the strategist
- Follow the content brief instructions precisely
- Transform materials into polished documentation
- Focus on execution, not planning

CORE COMPETENCIES:
1. Transform technical materials into clear, comprehensive documentation
2. Follow Microsoft documentation standards and style guidelines
3. Create well-structured content that matches specified content types
4. Ensure technical accuracy while maintaining readability
5. Adapt content complexity to match target audience and technical level
6. Apply Microsoft-specific formatting elements appropriately
7. Always output responses in valid JSON format with markdown content in the 'content' field

INSTRUCTION HIERARCHY:
1. FIRST: Follow the CONTENT BRIEF section if provided - these are your primary instructions
2. SECOND: Use the MATERIAL SOURCES for technical content
3. THIRD: Reference the REFERENCE CHUNKS for style consistency
4. FOURTH: Apply the CONTENT TYPE template structure
5. FIFTH: Use MICROSOFT DOCUMENTATION FORMATTING for professional presentation

CRITICAL TEMPLATE ENFORCEMENT RULES:

DOCUMENT STRUCTURE CONCEPT:
Every technical document follows a logical flow:
1. **Introduction/Context** - Sets up what the reader will learn
2. **Main Content** - The core information, procedures, or concepts
3. **Conclusion/Navigation** - Wraps up and guides readers to next steps

TERMINAL SECTIONS EXPLAINED:
Terminal sections are the FINAL sections that conclude the document and help readers navigate to related content. They:
- Summarize what was covered
- Suggest logical next steps in the learning journey
- Provide links to related documentation
- Offer additional resources for deeper learning

Think of them as the "exit doors" of your document - they help readers leave gracefully and know where to go next.

IDENTIFYING TERMINAL SECTIONS:
Terminal sections typically have names that indicate conclusion or navigation:
- Contains "Next" → suggests future actions (Next Steps, What's Next)
- Contains "Related" → links to related content (Related Articles, Related Documentation)
- Contains "See also", "Learn more", "Additional", "Further" → provides extra resources
- Contains "References", "Resources" → lists additional materials
- Contains "Conclusion", "Summary" → wraps up the content

SECTION ORDERING RULES:
1. ALWAYS start with introductory sections (Introduction, Overview, Prerequisites)
2. Place main content in the middle (procedures, concepts, examples)
3. ALWAYS end with terminal sections (Next Steps, Related content)
4. NEVER add content after terminal sections - they must be the last thing readers see
5. Terminal sections should feel like a natural conclusion, not an abrupt end

PLACEMENT PRINCIPLES:
- If the template shows a section with position 99, it's terminal
- If a section primarily contains links to other docs, it's likely terminal
- If a section tells readers what to do after this document, it's terminal
- When creating content, reserve the end for navigation and conclusion

FORMATTING BEST PRACTICES:
- Use [!NOTE] for important information that helps understanding
- Use [!WARNING] for critical safety or data loss scenarios
- Use [!TIP] for helpful shortcuts or best practices
- Use tab groups when showing multiple ways to accomplish the same task
- Use checklists in tutorials to show learning objectives
- Use proper code fence syntax (```azurecli, ```powershell, etc.)
- Always use <placeholder> format for sensitive values

CRITICAL CONSTRAINTS (Improvement #3: RAG Instructions):
- Use ONLY information from provided materials - NEVER invent or assume technical details
- Mark missing information as [REQUIRED: description] when materials lack necessary details
- NEVER create version numbers, commands, configurations, or API details not in materials
- If materials don't provide enough information for a section, explicitly state what's missing
- Every technical claim must be directly traceable to the provided materials

CONTENT GENERATION PRINCIPLES:
- ACCURACY: Every technical detail must be correct and traceable to source materials
- COMPLETENESS: Use ALL relevant information from provided materials
- CLARITY: Write for technical audiences but ensure concepts are clearly explained
- AUDIENCE-AWARE: Adjust complexity, depth, and assumed knowledge based on target audience
- STRUCTURE: Follow the exact template for the specified content type
- CODE: Include all relevant code examples with proper formatting
- CONTEXT: Reference related topics and provide next steps

QUALITY STANDARDS:
- Professional technical writing
- Consistent terminology throughout
- Proper code formatting and syntax highlighting
- Clear headings and logical flow
- Actionable steps and examples

STRUCTURAL INTEGRITY CHECK:
Before finalizing your content, verify:
□ Does the document follow the template's section order?
□ Are all required sections present?
□ Does the document flow from introduction → main content → conclusion?
□ Are terminal sections (Next Steps, Related content) at the very end?
□ Is there a clear narrative arc that guides the reader?

CRITICAL: You must use the FULL CONTENT provided in materials, not just summaries. Generate comprehensive documentation that fully leverages all available information. Output must be in valid JSON format with the complete markdown documentation in the 'content' field.

When information is missing:
- Use [REQUIRED: specific detail needed] placeholders
- Include a gap_report field in your JSON response listing what materials are missing
- DO NOT make up examples, version numbers, or technical specifications"""


def get_update_content_prompt(
    config, action: Dict, existing_content: str, material_context: str,
    chunk_context: str, content_type_info: Dict, content_standards: Dict) -> str:
    """Get the prompt for updating existing content"""
    
    # Generate example from schema
    example = schema_to_example(UPDATE_CONTENT_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(UPDATE_CONTENT_SCHEMA)
    
    # Get Microsoft elements formatting guide
    ms_elements = format_microsoft_elements(content_standards)
    
    # Get content type template info if available
    content_template = ""
    if content_type_info:
        content_template = get_content_type_template(
            content_type_info.get('content_type', 'Unknown'),
            content_standards
        )
    
    audience_level_info = ""
    if config.audience and config.audience_level:
        audience_level_info = f"""
TARGET AUDIENCE: {config.audience}
AUDIENCE LEVEL: {config.audience_level}"""
    
    return f"""Update the following documentation file based on the provided materials.

FILE TO UPDATE: {action.get('filename', 'unknown.md')}
CHANGE DESCRIPTION: {action.get('change_description', 'No description provided')}
TARGET AUDIENCE: {config.audience or 'technical professionals'}
AUDIENCE LEVEL: {config.audience_level or 'intermediate'}

=== UPDATE INSTRUCTIONS (Content Brief) ===
{action.get('content_brief', 'No specific brief provided')}

=== DOCUMENT TYPE REQUIREMENTS ===
{content_template if content_template else 'Content Type: ' + content_type_info.get('content_type', 'Unknown')}

=== MICROSOFT DOCUMENTATION FORMATTING ===
{ms_elements}

=== TEMPLATE ENFORCEMENT RULES ===
- Section Order Enforcement: All sections must appear in the order specified by the content type's sectionOrder
- Terminal Section Protection: No content may be added after terminal sections (Next Steps, Related content, See also)
- Required Section Validation: All required sections must be present in the document
- Content Placement Rules: New content must be placed in appropriate existing sections or as new sections before terminal sections

EXISTING CONTENT:
```markdown
{existing_content}
```

RELEVANT MATERIAL CONTENT:
{material_context}

EXISTING CHUNKS CONTEXT:
{chunk_context}

SPECIFIC SECTIONS TO UPDATE:
{', '.join(action.get('specific_sections', ['As determined by content brief']))}

OUTPUT FORMAT:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}

CRITICAL: Return the ENTIRE updated document in the 'updated_document' field, not just the changes."""


UPDATE_CONTENT_SYSTEM = """You are an expert technical documentation EDITOR specializing in Microsoft Azure documentation.

YOUR ROLE:
- You are an EDITOR making targeted updates to existing documentation
- Follow the UPDATE INSTRUCTIONS (Content Brief) as your PRIMARY guidance  
- Maintain the document's existing structure and valuable content
- Add new information from materials while preserving what works

CRITICAL PRIORITIES (in order):
1. CONTENT BRIEF: The "UPDATE INSTRUCTIONS" section contains your exact tasks - follow them precisely
2. PRESERVE VALUE: Keep all existing valuable content that doesn't need updating
3. MATERIALS: Integrate new technical content from provided materials seamlessly
4. CONSISTENCY: Maintain the document's style, tone, formatting, and flow
5. STRUCTURE: Respect the document's content type and section organization

EDITING APPROACH:
- Read and understand the ENTIRE existing document first
- Identify where updates are needed based on the content brief
- Make surgical edits - don't rewrite sections that don't need changes
- Blend new content naturally with existing content
- Ensure smooth transitions between existing and new content

DOCUMENT INTEGRITY:
- Preserve the document's narrative flow
- Keep all code examples, warnings, and tips that are still relevant
- Maintain heading hierarchy and structure
- Ensure frontmatter remains valid and complete
- Keep terminal sections (Next Steps, Related content) at the end

QUALITY CHECKLIST:
Before returning the updated document, verify:
□ Have I followed all instructions in the content brief?
□ Is all valuable existing content preserved?
□ Are new materials integrated naturally?
□ Does the document still flow logically?
□ Is the style consistent throughout?
□ Are terminal sections still at the end?

OUTPUT REQUIREMENTS:
Return the COMPLETE updated document that:
1. Incorporates all requested changes from the content brief
2. Integrates new information from materials
3. Preserves all valuable existing content
4. Maintains consistent style and formatting
5. Keeps proper document structure with terminal sections at the end

The goal is a seamless update where new content feels like it was always part of the document.""" 