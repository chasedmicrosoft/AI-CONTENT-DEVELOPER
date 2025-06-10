"""
Update Content Prompt - Phase 3: Content Generation
Updates existing documentation files while preserving valuable content
"""
from typing import Dict
from ...models import ContentDecision


def get_update_content_prompt(config, action: ContentDecision, existing_document: str, material_context: str, 
                             chunk_context: str, content_type_info: Dict, content_standards: Dict) -> str:
    """Create prompt for updating existing content
    
    Args:
        config: Configuration object with audience and content goal
        action: ContentDecision object with update details
        existing_document: The full existing document content
        material_context: Formatted material content
        chunk_context: Context from relevant chunks
        content_type_info: Information about the content type
        content_standards: Content standards from JSON file
    """
    # Extract attributes from dataclass
    filename = action.filename or action.target_file or 'unknown.md'
    change_description = action.change_description or action.rationale or 'No description provided'
    content_brief = action.content_brief or action.rationale or 'No specific brief provided'
    specific_sections = action.specific_sections or action.sections or ['As determined by content brief']
    
    # Get Microsoft elements formatting guide
    ms_elements = _format_microsoft_elements(content_standards)
    
    # Get content type template info if available
    content_template = ""
    if content_type_info:
        content_template = _get_content_type_template(
            content_type_info.get('content_type', 'Unknown'),
            content_standards
        )
    
    audience_level_info = ""
    if config.audience and config.audience_level:
        audience_level_info = f"""
TARGET AUDIENCE: {config.audience}
AUDIENCE LEVEL: {config.audience_level}"""
    
    return f"""Update the following documentation file based on the provided materials.

FILE TO UPDATE: {filename}
CHANGE DESCRIPTION: {change_description}
TARGET AUDIENCE: {config.audience or 'technical professionals'}
AUDIENCE LEVEL: {config.audience_level or 'intermediate'}

=== UPDATE INSTRUCTIONS (Content Brief) ===
{content_brief}

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
{existing_document}
```

RELEVANT MATERIAL CONTENT:
{material_context}

EXISTING CHUNKS CONTEXT:
{chunk_context}

SPECIFIC SECTIONS TO UPDATE:
{', '.join(specific_sections)}

REQUIRED OUTPUT:
Return a JSON object with these exact fields:

{{
  "thinking": [
    "YOUR analysis of the update requirements",
    "YOUR identification of sections to modify",
    "YOUR plan for integrating new content",
    "YOUR preservation strategy for existing content"
  ],
  "updated_document": "---\\ntitle: Updated Document Title\\ndescription: Updated description\\nms.topic: {content_type_info.get('ms_topic', 'conceptual')}\\nms.date: MM/DD/YYYY\\n---\\n\\n# Updated Document Title\\n\\nUpdated introduction paragraph...\\n\\n## Existing Section\\n\\nExisting content preserved with new information added...\\n\\n## New Section\\n\\nCompletely new content from materials...\\n\\n## Next steps\\n\\n- [Existing link](link)\\n- [New related topic](link)",
  "changes_summary": "Added new section on authentication methods and updated existing security section with latest best practices from materials.",
  "metadata": {{
    "sections_modified": ["## Security", "## Authentication"],
    "sections_added": ["## OAuth 2.0 Flow"],
    "word_count_before": 450,
    "word_count_after": 625
  }}
}}

FIELD REQUIREMENTS:
- thinking: Array of YOUR ACTUAL update analysis steps (3-20 items)
- updated_document: Complete updated markdown document as a single string (minimum 100 characters)
  - Must include the ENTIRE document, not just changes
  - Must preserve all valuable existing content
  - Must integrate new content seamlessly
- changes_summary: Brief description of changes made (minimum 20 characters)
- metadata:
  - sections_modified: Array of section headings that were modified
  - sections_added: Array of new section headings added
  - word_count_before: Integer count of words before update
  - word_count_after: Integer count of words after update

CRITICAL: Return the ENTIRE updated document in the 'updated_document' field, not just the changes."""


def _get_content_type_template(content_type: str, standards: Dict) -> str:
    """Get the template for a specific content type"""
    # Find the content type in standards
    ct_info = next((ct for ct in standards.get('contentTypes', []) 
                   if ct['name'] == content_type), None)
    
    if not ct_info:
        return f"=== CONTENT TYPE: {content_type} ===\n\nNo template available. Use standard documentation structure."
    
    template = f"=== CONTENT TYPE: {content_type} ===\n\n"
    template += f"Purpose: {ct_info.get('purpose', '')}\n"
    template += f"Description: {ct_info.get('description', '')}\n\n"
    
    if ct_info.get('structure'):
        template += "REQUIRED STRUCTURE:\n"
        for section in ct_info['structure']:
            template += f"- {section}\n"
    
    template += f"\nFRONTMATTER REQUIREMENTS:\n"
    for key, value in ct_info.get('frontMatter', {}).items():
        template += f"- {key}: {value}\n"
    
    return template


def _format_microsoft_elements(content_standards: Dict) -> str:
    """Format Microsoft-specific formatting elements for prompt inclusion"""
    if not content_standards:
        return ""
    
    formatting_elements = content_standards.get('formattingElements', [])
    code_guidelines = content_standards.get('codeGuidelines', {})
    
    # Build formatting guide
    lines = ["=== MICROSOFT DOCUMENTATION FORMATTING ===\n"]
    
    # Add special elements
    lines.append("SPECIAL FORMATTING ELEMENTS:")
    for element in formatting_elements:
        lines.append(f"\n{element['name']}:")
        lines.append(f"Format: {element['format']}")
        if element['name'] in ['Note', 'Warning', 'Tip']:
            lines.append(f"Use for: {element['name'].lower()} callouts that need reader attention")
        elif element['name'] == 'Checklist':
            lines.append("Use for: Tutorial objectives or feature lists")
        elif element['name'] == 'Next step link':
            lines.append("Use for: Prominent navigation to the next article in a series")
    
    # Add code language guidelines
    lines.append("\n\nCODE BLOCK LANGUAGES:")
    languages = code_guidelines.get('languages', [])
    for lang in languages:
        lines.append(f"- {lang['syntax']} - {lang['useFor']}")
    
    # Add common tab groups
    tab_groups = content_standards.get('commonTabGroups', [])
    if tab_groups:
        lines.append("\n\nTAB GROUPS (for multiple approaches):")
        lines.append("Format: #### [Tab Name](#tab/tab-id)")
        lines.append("Common groups: Azure portal, Azure CLI, PowerShell, ARM template, Bicep")
        lines.append("End with: ---")
    
    # Add security reminders
    lines.append("\n\nSECURITY REQUIREMENTS:")
    lines.append("- Use <placeholder-name> for all sensitive values")
    lines.append("- NEVER include real credentials or secrets")
    lines.append("- Show managed identity approaches when applicable")
    
    return "\n".join(lines)


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