"""
Create Content Prompt - Phase 3: Content Generation
Generates new documentation files from scratch based on materials and standards
"""
from typing import Dict, List


def get_create_content_prompt(
    config, action, materials_content: Dict[str, str], 
    materials_summaries: List[Dict], related_chunks: List[Dict],
    chunk_context: str, content_type_info: Dict, content_standards: Dict) -> str:
    """Get the prompt for creating new content
    
    Args:
        config: Configuration object
        action: ContentDecision dataclass with action details
        materials_content: Dictionary of material source to content
        materials_summaries: List of material summaries
        related_chunks: List of related document chunks
        chunk_context: Additional context about chunks
        content_type_info: Information about the content type
        content_standards: Content standards dictionary
    """
    
    # Format materials with full content
    materials_info = _format_materials_with_content(materials_content, materials_summaries)
    
    # Format related chunks for reference
    chunks_reference = _format_chunks_for_reference(related_chunks)
    
    # Get content type specific template
    content_template = _get_content_type_template(action.content_type, content_standards)
    
    # Get Microsoft elements formatting guide
    ms_elements = _format_microsoft_elements(content_standards)
    
    audience_level_info = ""
    if config.audience and config.audience_level:
        audience_level_info = f"""
TARGET AUDIENCE: {config.audience}
AUDIENCE LEVEL: {config.audience_level}"""
    
    return f"""Create a new {action.content_type} based on the following materials and guidelines.

FILE TO CREATE: {action.filename}
CONTENT TYPE: {action.content_type}
MS.TOPIC: {action.ms_topic}
SERVICE AREA: {config.service_area}{audience_level_info}

=== CREATION INSTRUCTIONS (Content Brief) ===
{action.content_brief}

=== MATERIALS TO USE ===
{materials_info}

=== RELATED DOCUMENTATION CONTEXT ===
{chunks_reference}

{chunk_context}

=== CONTENT TYPE REQUIREMENTS ===
{content_template}

=== MICROSOFT DOCUMENTATION FORMATTING ===
{ms_elements}

TASK: Create a complete {action.content_type} that:
1. Addresses the objective stated in the content brief
2. Incorporates relevant information from the provided materials
3. Follows the content type template structure
4. Maintains consistency with related documentation
5. Uses proper Microsoft documentation formatting

REQUIRED OUTPUT:
Return a JSON object with these exact fields:

{{
  "thinking": [
    "YOUR analysis of the content brief requirements",
    "YOUR identification of key information from materials",
    "YOUR planning of document structure",
    "YOUR integration of Microsoft formatting elements"
  ],
  "content": "---\\ntitle: Document Title\\ndescription: Clear description of what this document covers\\nms.topic: {action.ms_topic}\\nms.date: MM/DD/YYYY\\n---\\n\\n# Document Title\\n\\nIntroduction paragraph explaining what this document covers...\\n\\n## Prerequisites\\n\\n- Prerequisite 1\\n- Prerequisite 2\\n\\n## Main Content Section\\n\\nYour main content here...\\n\\n### Subsection\\n\\nDetailed content...\\n\\n## Next steps\\n\\n- [Link to related content](link)\\n- [Another related topic](link)",
  "metadata": {{
    "word_count": 250,
    "sections_created": ["Introduction", "Prerequisites", "Main Content Section", "Next steps"],
    "materials_used": ["{list(materials_content.keys())[0] if materials_content else 'material1.docx'}"],
    "key_topics_covered": ["topic1", "topic2", "topic3"]
  }}
}}

FIELD REQUIREMENTS:
- thinking: Array of YOUR ACTUAL content creation steps (3-20 items)
- content: Complete markdown document as a single string (minimum 100 characters)
  - Must include YAML frontmatter
  - Must follow the content type template structure
  - Must use proper markdown formatting
- metadata:
  - word_count: Integer count of words in content (minimum 50)
  - sections_created: Array of section headings created
  - materials_used: Array of material filenames used
  - key_topics_covered: Array of main topics covered

CRITICAL: Return the COMPLETE document content as a single string in the 'content' field. The document must be production-ready with proper frontmatter, sections, and formatting."""


def _format_materials_with_content(materials_content: Dict[str, str], summaries: List[Dict]) -> str:
    """Format materials with their full content"""
    sections = ["=== MATERIAL SOURCES (Full Content) ===\n"]
    
    for i, (source, content) in enumerate(materials_content.items(), 1):
        # Find matching summary
        summary = next((s for s in summaries if s.get('source') == source), {})
        
        sections.append(f"SOURCE {i}: {source}")
        
        # Add metadata
        if technologies := summary.get('technologies', []):
            sections.append(f"Technologies: {', '.join(technologies)}")
        
        if key_concepts := summary.get('key_concepts', []):
            sections.append(f"Key Concepts: {', '.join(key_concepts)}")
        
        sections.append(f"Summary: {summary.get('summary', 'No summary available')}")
        
        # Add content
        sections.extend([
            "\nFULL CONTENT:",
            "-" * 80,
            content,
            "-" * 80,
            ""
        ])
    
    return '\n'.join(sections)


def _format_chunks_for_reference(chunks: List[Dict]) -> str:
    """Format reference chunks for style and context"""
    if not chunks:
        return "=== REFERENCE CHUNKS ===\n\nNo reference chunks available."
    
    sections = ["=== REFERENCE CHUNKS (For Style and Context) ===\n"]
    
    for i, chunk in enumerate(chunks[:5], 1):  # Top 5 chunks
        sections.append(f"REFERENCE {i}:")
        sections.append(f"File: {chunk.get('file', 'Unknown')}")
        sections.append(f"Section: {chunk.get('section', 'Unknown')}")
        sections.append(f"Relevance: {chunk.get('relevance_score', 0):.2f}")
        sections.append(f"Content Preview: {chunk.get('content', '')[:200]}...")
        sections.append("")
    
    return '\n'.join(sections)


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