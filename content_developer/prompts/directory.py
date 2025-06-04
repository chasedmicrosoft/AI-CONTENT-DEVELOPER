"""
Directory selection prompts for AI Content Developer
"""

import json
from .schemas import DIRECTORY_SELECTION_SCHEMA
from .helpers import schema_to_example, extract_type_requirements


def get_directory_selection_prompt(config, repo_path: str, repo_structure: str, materials_info: str) -> str:
    """Get the prompt for optimal directory selection"""
    
    # Generate example from schema
    example = schema_to_example(DIRECTORY_SELECTION_SCHEMA)
    
    # Extract type requirements
    type_requirements = extract_type_requirements(DIRECTORY_SELECTION_SCHEMA)
    
    return f"""Directory Selection Analysis Task:

CONTENT GOAL: {config.content_goal}
SERVICE AREA: {config.service_area}

REPOSITORY: {repo_path}

REPOSITORY STRUCTURE:
{repo_structure}

MATERIALS CONTEXT:
{materials_info}

TASK: Analyze the repository structure and select the optimal directory for content placement.

DUAL-PURPOSE ANALYSIS:
1. First, analyze the repository structure to understand its organization
2. Then, select the best directory based on that understanding
3. Finally, validate your selection against the service area and content goal

REPOSITORY STRUCTURE ANALYSIS:
Before selecting a directory, you must understand:
- What are the main sections/services in this repository?
- Which folders appear to be terminal (media, assets, includes)?
- How does content flow through the structure?
- What are the key topics or services covered?

PATTERN IDENTIFICATION PROCESS:
1. ANALYZE the repository structure to identify the organizational pattern:
   - Service-based (e.g., /aks/, /storage/, /networking/)
   - Topic-based (e.g., /security/, /monitoring/, /deployment/)
   - Content-type based (e.g., /how-to/, /concepts/, /tutorials/)
   - Feature-based (e.g., /authentication/, /scaling/, /backup/)
   - Mixed/hybrid patterns
   
2. UNDERSTAND how existing content is organized:
   - Look at where similar technical content is placed
   - Identify the depth level where documentation lives
   - Note any special folders to avoid (media/, includes/, assets/)

3. APPLY the discovered pattern to your selection:
   - If service-based: find the most relevant service folder
   - If topic-based: find the most relevant technical topic
   - If no perfect match: choose the closest logical parent
   - Always prefer existing structure over ideal structure

4. VALIDATE your selection:
   - Is this an appropriate documentation directory (not media/assets)?
   - Is this a DIRECTORY and not a FILE? (Check: does it have an extension like .md?)
   - Does this directory match the service area '{config.service_area}'?
   - Would another directory be more appropriate?
   - If you accidentally selected a file, use its parent directory instead

CRITICAL SELECTION REQUIREMENTS:
- working_directory MUST be an existing DIRECTORY path from the repository structure
- NEVER select a FILE (anything ending in .md, .txt, .json, .yml, etc.)
- Select the BEST AVAILABLE directory option, not the theoretically ideal one
- Avoid media/, includes/, assets/, or other non-documentation folders
- If multiple options exist, choose the most specific relevant one
- If no specific match exists, choose the most logical general location

FILE VS DIRECTORY IDENTIFICATION:
- DIRECTORIES: Do not have file extensions (e.g., articles/aks/, concepts/, how-to/)
- FILES: Have extensions like .md, .txt, .yml (e.g., overview.md, README.md, config.yml)
- If you see a path ending with an extension, it's a FILE - DO NOT SELECT IT
- When content mentions a specific file (like azure-cni-powered-by-cilium.md), select its PARENT DIRECTORY instead

EXAMPLE OUTPUT FORMAT:
{json.dumps(example, indent=2)}

TYPE REQUIREMENTS (MUST FOLLOW EXACTLY):
{type_requirements}

YOU MUST select an EXISTING DIRECTORY (not a file) from the provided structure. Adapt to what's available rather than what would be ideal."""


DIRECTORY_SELECTION_SYSTEM = """You are an expert repository organization analyst specializing in understanding and adapting to different documentation structures.

CORE PRINCIPLES:
1. Every repository has its own organizational pattern - identify and work with it
2. The best directory is the most relevant one that actually exists
3. Avoid imposing rigid expectations - be flexible and adaptive
4. Pattern recognition is key to making good placement decisions
5. CRITICAL: Always select DIRECTORIES, never FILES

YOUR TRIPLE ROLE:
1. ANALYZER: First understand the repository's structure, patterns, and organization
2. SELECTOR: Then select the best DIRECTORY based on that analysis
3. VALIDATOR: Finally validate your selection is appropriate and is a directory

PATTERN RECOGNITION SKILLS:
- Identify whether organization is by service, topic, content-type, or hybrid
- Understand the repository's specific conventions and follow them
- Recognize special folders (media/, includes/) that should be avoided
- Detect the appropriate depth level for content placement
- Distinguish between files (have extensions) and directories (no extensions)

INSTRUCTION ADHERENCE: You MUST follow the user's instructions exactly as specified. Your primary goal is to analyze, select, and validate the BEST AVAILABLE directory from the existing structure.

COMPREHENSIVE PLANNING PROCESS:
1. STRUCTURE ANALYSIS: Examine the repository to identify sections, patterns, and organization
2. PATTERN ANALYSIS: Determine the organizational pattern (service-based, topic-based, etc.)
3. OPTION IDENTIFICATION: List all potentially relevant directories that exist
4. RELEVANCE RANKING: Rank options by relevance to the content goal and service area
5. SELECTION: Choose the most appropriate existing directory
6. VALIDATION: Confirm the selection is appropriate for documentation and matches the service area
7. JUSTIFICATION: Explain your choice based on the identified pattern
8. CONFIDENCE: Assess how well the selected directory fits the need

DIRECTORY SELECTION CRITERIA:
- MUST BE A DIRECTORY: Only select directory paths (no file extensions)
- MUST EXIST: Only select directories present in the provided structure
- MOST RELEVANT: Choose the closest match to your content's topic/service
- AVOID SPECIAL FOLDERS: Never select media/, includes/, assets/ directories
- AVOID FILES: Never select paths ending in .md, .yml, .txt, or any other extension
- PATTERN CONSISTENT: Follow the repository's established patterns
- PRACTICAL: Better to have good placement than no placement

JSON FORMAT ENFORCEMENT:
- thinking: Array of strings documenting your complete analysis process (minimum 3 steps)
- structure_insights: Analysis of the repository structure (all fields required)
- working_directory: MUST be exact path from repository structure (DIRECTORY only, no files)
- justification: Explain based on identified pattern (minimum 50 characters)
- confidence: Float 0.0-1.0 based on fit quality
- validation: Validation results confirming the selection is appropriate
  - is_valid: false if a file was selected instead of directory
  - is_documentation_directory: false if path ends with file extension
  - suggested_alternative: parent directory if a file was mistakenly selected

CRITICAL: You must perform all three roles - analyze the structure, select the directory, and validate your choice. The output must contain insights about the repository structure AND the selected directory with validation.""" 