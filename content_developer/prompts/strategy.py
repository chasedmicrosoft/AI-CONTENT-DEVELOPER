"""
Content strategy prompts for AI Content Developer
"""
import json
from typing import Dict, List

from .schemas import CONTENT_STRATEGY_SCHEMA
from .helpers import (
    format_semantic_matches, format_content_types,
    format_top_chunks, format_chunk_clusters,
    schema_to_example, extract_type_requirements
)


def get_unified_content_strategy_prompt(config, materials_summary: str, 
existing_chunks: List[Dict], 
content_standards: Dict,
top_chunks: List[Dict] = None,
chunk_clusters: Dict[str, List[Dict]] = None) -> str:
    """Get the prompt for unified content strategy with gap analysis and content type selection"""
    
    # Generate example from schema
    example = schema_to_example(CONTENT_STRATEGY_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(CONTENT_STRATEGY_SCHEMA)
    
    # Format existing chunks for prompt (using semantic matches formatter for backward compatibility)
    chunks_info = format_semantic_matches(existing_chunks)
    
    # Format content type definitions
    content_types_info = format_content_types(content_standards)
    
    # Format top chunks if provided
    top_chunks_info = ""
    if top_chunks:
        top_chunks_info = "\n\n" + format_top_chunks(top_chunks)
    
    # Format chunk clusters if provided
    clusters_info = ""
    if chunk_clusters:
        clusters_info = "\n\n" + format_chunk_clusters(chunk_clusters)
    
    audience_level_info = ""
    if config.audience and config.audience_level:
        audience_level_info = f"""
TARGET AUDIENCE: {config.audience}
AUDIENCE LEVEL: {config.audience_level}"""
        
    return f"""Unified Content Strategy Analysis Task:

CONTENT GOAL: {config.content_goal}
SERVICE AREA: {config.service_area}{audience_level_info}

USER MATERIALS ANALYSIS:
{materials_summary}


EXISTING CONTENT ANALYSIS:
{chunks_info}{top_chunks_info}{clusters_info}


{content_types_info}

TASK: Perform comprehensive gap analysis and generate content strategy with specific actions.

AUDIENCE CONSIDERATIONS:
- Target readers: {config.audience or 'technical professionals'}
- Technical depth: {config.audience_level or 'intermediate'} level
- Beginner: Include prerequisites, detailed explanations, basic concepts
- Intermediate: Balance explanation with technical detail
- Advanced: Focus on implementation, optimization, and edge cases

ANALYSIS REQUIREMENTS:
1. GAP ANALYSIS: Compare user materials against existing content considering:
   - Content type mismatches (need how-to but only have overview)
   - Coverage depth (surface mention vs comprehensive coverage)
   - Missing features or concepts from materials
   
2. DECISION FRAMEWORK:
   - If coverage < 30% OR wrong content type exists → CREATE new content
   - If coverage 30-70% AND same content type needed → UPDATE with additions
   - If coverage > 70% but missing key details → UPDATE with specific sections
   
3. FOR CREATE ACTIONS:
   - Select appropriate content type based on user materials and goal
   - Set ms_topic based on content type (e.g., "concept" for Concept, "how-to" for How-To Guide)
   - Reference specific chunk_ids from TOP RELEVANT CHUNKS section
   - Specify exact filename and comprehensive reason
   - Create detailed content_brief with:
     * Clear objective stating what reader will accomplish
     * Specific topics from materials that must be covered
     * Prerequisites based on existing content analysis
     * Related docs from the repository to reference
     * Logical next steps based on content progression
     * Technical depth guidance based on audience level
     * Specific examples from materials to include
   
4. FOR UPDATE ACTIONS:
   - Identify current content type from ms.topic
   - Include current ms_topic value for consistency
   - Specify exact sections/information to add
   - Reference specific chunk_ids that show where to add content
   - Provide specific change description
   - Create detailed content_brief with:
     * Update objective explaining the gap being filled
     * Specific sections to add with placement guidance
     * Sections to modify with clear preservation instructions
     * New examples from materials to incorporate
     * Additional links to connect updated content
     * Style consistency requirements

5. RELEVANT CHUNKS: Use ONLY chunk_ids from the provided TOP RELEVANT CHUNKS or from file's relevant_chunks

MS_TOPIC MAPPING:
- Concept → "concept"
- How-To Guide → "how-to"
- Quickstart → "quickstart"
- Tutorial → "tutorial"
- Overview → "overview"
- Reference → "reference"

OUTPUT FORMAT:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}

FILENAME REQUIREMENTS:
- For CREATE actions: Use simple filenames like "my-guide.md" without any path prefixes
- For UPDATE actions: Use ONLY the filename from the chunk data (e.g., "azure-cni-powered-by-cilium.md"), never include repository names or directory paths
- NEVER include paths like "repo-name/articles/..." in filenames."""


UNIFIED_CONTENT_STRATEGY_SYSTEM = """You are an expert content strategist specializing in technical documentation gap analysis and content planning.

CORE RESPONSIBILITIES:
1. Analyze semantic gaps between user materials and existing documentation
2. Determine optimal content strategy (CREATE new vs UPDATE existing)
3. Select appropriate content types for new content
4. Create detailed content briefs with specific, actionable instructions
5. Provide clear guidance that content writers can follow
6. Always return responses in valid JSON format

YOUR ROLE AS CONTENT STRATEGIST:
- You analyze and plan; you don't write the content
- You create detailed briefs that tell writers exactly what to produce
- You identify relationships between content pieces
- You ensure consistency across the documentation set
- You think about the reader's journey through the docs

GAP ANALYSIS CRITERIA:
- High Coverage (>70%): Existing content addresses most material concepts
- Medium Coverage (30-70%): Partial coverage, missing important details
- Low Coverage (<30%): Minimal or no relevant existing content

DECISION LOGIC:
- CREATE when: Low coverage OR need different content type OR topic not addressed
- UPDATE when: Medium/high coverage AND same content type works AND specific sections can be added
- ALWAYS include ms_topic field that matches the content_type (see MS_TOPIC MAPPING in prompt)

CONTENT TYPE SELECTION:
- Match content type to user's goal and material structure
- Overview: High-level technical explanations (ms_topic: "overview")
- Concept: Deep understanding of how things work (ms_topic: "concept")
- Quickstart: Get users started quickly (<10 min) (ms_topic: "quickstart")
- How-To: Step-by-step task completion (ms_topic: "how-to")
- Tutorial: End-to-end learning scenarios (ms_topic: "tutorial")
- Reference: Technical specifications and API docs (ms_topic: "reference")

CONTENT BRIEF REQUIREMENTS:
- Be specific: Don't say "explain networking" - say "explain how Cilium uses eBPF for packet filtering"
- Reference materials: Point to specific concepts from materials that must be included
- Consider flow: Think about what reader knows before and needs after
- Identify examples: Call out specific code/configs from materials to include
- Set boundaries: Be clear about what NOT to cover to maintain focus

CRITICAL: Each decision must be justified with specific evidence from materials and gap analysis. Your content briefs must be detailed enough that a writer can execute without guessing. Output must be valid JSON format."""
