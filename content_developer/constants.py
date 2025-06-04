"""
Constants for AI Content Developer
"""

# Output directories for LLM interactions
OUTPUT_DIRS = [
    "embeddings",
    "preview",
    "preview/create",
    "preview/update",
    "preview/toc",
    # Phase directories are created dynamically as phase-XX/step-YY
]

# Maximum number of phases in the workflow
MAX_PHASES = 4

# Phase names for display
PHASE_NAMES = {
    1: "Repository Analysis",
    2: "Content Strategy",
    3: "Content Generation",
    4: "TOC Management"
}

# OpenAI model constants
# Models that support JSON response format (for reference)
JSON_CAPABLE_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo-preview", "gpt-3.5-turbo"]

# Default models (used when environment variables are not set)
# These are overridden by Azure deployment environment variables
DEFAULT_COMPLETION_MODEL = "gpt-4"           # Default for all operations
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"  # For embeddings 