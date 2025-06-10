"""
Directory Selection Prompt - Phase 1: Repository Analysis
Selects the appropriate working directory within a repository based on documentation structure
"""
from typing import Dict


def get_directory_selection_prompt(config, repo_path: str, repo_structure: str, materials_info: str) -> str:
    """Get the prompt for selecting working directory"""
    
    return f"""Select the most appropriate directory for documentation work.

CONTENT GOAL: {config.content_goal}
SERVICE AREA: {config.service_area}

REPOSITORY: {repo_path}

REPOSITORY STRUCTURE:
{repo_structure}

MATERIALS CONTEXT:
{materials_info}

TASK:
1. Find directories containing documentation (.md files, toc.yml)
2. Identify file structure patterns (e.g. service-based, topic-based, technology-based, hybrid, flat, unknown)
3. Identify which directory best matches the service area '{config.service_area}'
4. Validate it's the most relevant documentation directory

If multiple valid directories exist, choose the most relevant one.

REQUIRED OUTPUT:
Return a JSON object with these exact fields:

{{
  "thinking":"Your step-by-step thoughts",
  "working_directory": "docs/services/azure-functions",
  "justification": "Selected docs/services/azure-functions because it contains Azure Functions documentation with 15 .md files and a toc.yml file, directly matching the requested service area.",
  "confidence": 0.95,
  "validation": {{
    "is_documentation_directory": true,
    "matches_service_area": true,
    "alternative_considered": null,
    "validation_notes": "Directory contains toc.yml and well-organized content for Azure Functions"
  }}
}}

FIELD REQUIREMENTS:
- thinking: Array of your actual analysis steps
- working_directory: Path without leading/trailing slashes
- justification: Clear explanation of why this directory was selected (min 50 chars)
- confidence: Number between 0.0 and 1.0 based on match quality
- pattern: File structure pattern (e.g. service-based, topic-based, technology-based, hybrid, flat, unknown)
- validation:
  - is_documentation_directory: true if contains docs, false if it's code/samples/media/.
  - matches_service_area: true if content matches '{config.service_area}'
  - alternative_considered: Another directory path if current choice is suboptimal, else null
  - validation_notes: Brief notes about the validation

IMPORTANT:
- Select the directory most relevant to '{config.service_area}'
- If no directory matches the service area, select the main docs directory
- Set confidence based on how well it matches the service area
- If confidence < 0.7, suggest an alternative_considered if one exists"""


DIRECTORY_SELECTION_SYSTEM = """You are an expert at selecting the correct documentation directory for a specific service area.

PRIMARY OBJECTIVE:
Select the directory that best matches the requested service area for documentation work.

ANALYSIS APPROACH:
1. Scan for all documentation directories (containing .md files)
2. Identify semantic patterns in the directory structure
3. Match directories to the requested service area
4. Validate the selection is appropriate for documentation work

SELECTION PRIORITIES:
1. Service area match - Directory content should match the requested service
2. Documentation focus - Must be a docs directory, not code samples/media/tests
3. Primary location - Choose the main docs folder, not nested subsections
4. Has toc.yml - Prefer directories with table of contents files

COMMON PATTERNS:
- docs/services/{service-name}/ - Service-specific documentation
- docs/{service-name}/ - Direct service folders
- articles/{service-name}/ - Article-based organization
- {service-name}/docs/ - Service-first organization
- flat structure - no subdirectories

VALIDATION CHECKS:
- Contains .md files (documentation)
- Not a code/samples/tests/media directory
- Matches or relates to the service area
- At appropriate level (not too deep)

OUTPUT QUALITY:
- Be specific in justification
- Set confidence based on match quality
- Suggest alternatives if match is poor
- Always validate the selection""" 