"""
Constants for AI Content Developer
"""

# Maximum number of phases in the workflow
MAX_PHASES = 5

# Default models (used when environment variables are not set)
# These are overridden by Azure deployment environment variables
DEFAULT_COMPLETION_MODEL = "gpt-4"           # Default for all operations
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"  # For embeddings 