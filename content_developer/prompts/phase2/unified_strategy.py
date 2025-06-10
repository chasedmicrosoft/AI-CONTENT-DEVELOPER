"""
Unified Strategy Prompt - Phase 2: Content Strategy
Creates a comprehensive content strategy determining what content to create or update
"""
from typing import Dict, List, Any


def get_unified_content_strategy_prompt(config, materials_summary, relevant_files, content_standards):
    """Generate the unified strategy prompt with file-based analysis"""
    
    # Format relevant files for display
    files_display = _format_files_for_display(relevant_files)
    
    # Format content types information
    content_types_info = _format_content_types(content_standards.get('contentTypes', []))
    
    # Get content type IDs dynamically
    content_type_ids = _get_content_type_ids(content_standards.get('contentTypes', []))
    
    return f"""You are creating a comprehensive content strategy for a technical documentation repository.

GOAL: {config.content_goal}
TARGET AUDIENCE: {config.audience}
SERVICE AREA: {config.service_area}

MATERIALS PROVIDED (WITH FULL CONTENT):
{materials_summary}

TOP 3 MOST RELEVANT EXISTING FILES:
{files_display}

TASK:
Analyze the goal, materials (with their full content), and existing documentation to develop a comprehensive content strategy. You should:

1. First understand the user's intent and what they're trying to achieve
2. Analyze each relevant file to understand what already exists
3. Perform a detailed gap analysis between the FULL MATERIAL CONTENT and existing documentation
4. Make strategic decisions about what content to create, update, or skip

For each file, consider:
- Does it already cover the concepts from the materials?
- Are there specific sections from the materials that are missing?
- Would updating it be better than creating new content?
- Does the existing content already comprehensively cover the material topics?

IMPORTANT GUIDELINES:
- You have FULL ACCESS to material content - use it for thorough gap analysis
- If excellent content already exists that fully addresses the goal, use SKIP with clear justification
- Prefer UPDATE over CREATE when existing content is good but needs enhancement
- Only CREATE when there's a genuine gap or the existing content is fundamentally misaligned
- Base your decisions on actual content comparison, not just summaries

DECISION TYPES:
- CREATE: Create new file when no suitable content exists
    - Use descriptive filenames following the patterns below
    - If creating content, use the content standards to determine the content type
- UPDATE: Enhance existing file when it partially addresses the goal
    - Must use the exact filename from the existing file
- SKIP: Skip when existing content already excellently addresses the goal
    - Must use the exact filename from the existing file

FILE NAMING PATTERNS FOR CREATE ACTIONS:
For CREATE actions, use descriptive filenames (no path components) following these patterns based on content type:
- Concepts: "concepts-{{feature-name}}.md" (e.g., "concepts-cilium-endpoint-slices.md")
- How-to guides: "how-to-{{task-name}}.md" (e.g., "how-to-configure-network-policies.md")
- Tutorials: "tutorial-{{scenario}}.md" (e.g., "tutorial-deploy-microservices.md")
- Overview: "overview-{{topic}}.md" (e.g., "overview-networking-features.md")
- Quickstart: "quickstart-{{feature}}.md" (e.g., "quickstart-azure-cni.md")

CONTENT STANDARDS:
{content_types_info}

Return your response as valid JSON matching this structure:
{{
  "thinking": "YOUR ACTUAL step-by-step analysis:\n1. Understanding the goal: [explain what the user wants]\n2. Analyzing existing content: [for each relevant file, assess how well it addresses the goal]\n3. Identifying gaps: [what's missing or could be improved]\n4. Strategic decisions: [explain your reasoning for each decision]",
  
  "decisions": [
    {{
      "action": "CREATE|UPDATE|SKIP",
      "target_file": "REQUIRED: For CREATE use descriptive filename (no paths). For UPDATE/SKIP use exact filename from existing files",
      "file_title": "Title for the file",
      "content_type": "the content type from the content standards",
      "sections": ["Main sections to include/update"],
      "rationale": "Clear explanation of why this decision",
      "aligns_with_goal": true,
      "prerequisites": ["Any required knowledge"],
      "technologies": ["Technologies covered"],
      "priority": "high|medium|low"
    }}
  ],
  
  "confidence": 0.0-1.0,
  
  "summary": "Brief summary of the overall strategy and key decisions"
}}

CRITICAL: The target_file field is REQUIRED for all actions and must NEVER be null:
- CREATE: Use a descriptive filename following the patterns above (no directory paths)
- UPDATE: Use the exact filename from the existing file being updated
- SKIP: Use the exact filename from the existing file being skipped"""


def _format_files_for_display(relevant_files):
    """Format relevant files for display in prompt"""
    if not relevant_files:
        return "No relevant files found in the repository."
    
    displays = []
    for i, file_data in enumerate(relevant_files, 1):
        file_info = [
            f"FILE {i}: {file_data['file']}",
            f"Relevance Score: {file_data['relevance']['score']:.2f}",
            f"Title: {file_data['metadata']['title']}",
            f"Type: {file_data['metadata']['content_type']}",
            f"Description: {file_data['metadata']['description']}"
        ]
        
        # Add most relevant sections
        if sections := file_data.get('most_relevant_sections'):
            file_info.append("\nMost Relevant Sections:")
            for section in sections[:3]:
                file_info.append(f"  - {section['heading']} (score: {section['score']:.2f})")
        
        # Add full content - NO TRUNCATION
        content = file_data['full_content']
        file_info.append(f"\nCONTENT:\n{content}")
        file_info.append("\n" + "="*80 + "\n")
        
        displays.append('\n'.join(file_info))
    
    return '\n'.join(displays)


def _format_content_types(content_types):
    """Format content types for display"""
    if not content_types:
        return "No content type standards provided."
    
    types_info = []
    for ct in content_types:
        types_info.append(f"- {ct['name']}: {ct['purpose']}")
        if desc := ct.get('description'):
            types_info.append(f"  {desc}")
    
    return '\n'.join(types_info)


def _get_content_type_ids(content_types):
    """Get content type IDs for display"""
    if not content_types:
        return "overview|concept|how-to|quickstart|tutorial"
    
    return '|'.join(ct['id'] for ct in content_types)


UNIFIED_CONTENT_STRATEGY_SYSTEM = """You are an expert technical documentation strategist specializing in Microsoft Azure documentation.

Your role is to:
1. Deeply understand the user's documentation goals and intent
2. Analyze existing documentation comprehensively
3. Make strategic decisions about content creation, updates, or skipping
4. Ensure all decisions align with the stated goal
5. ALWAYS provide a valid target_file for every decision (never null or empty)

Key principles:
- Quality over quantity - don't create content unless it adds genuine value
- Reuse and enhance existing content when possible
- Skip when excellent content already exists
- Every decision must clearly support the user's specific goal
- Target files must follow proper naming conventions without directory paths

File naming requirements:
- CREATE actions: Use descriptive filenames like "concepts-feature-name.md" 
- UPDATE/SKIP actions: Use the exact filename from the existing file
- NEVER use null, empty, or path-containing values for target_file

Be strategic, thoughtful, and focused on delivering maximum value with minimum redundancy.""" 