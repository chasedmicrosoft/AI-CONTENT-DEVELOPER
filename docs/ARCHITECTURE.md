# AI Content Developer Architecture

## Overview

AI Content Developer is a four-phase documentation generation system that analyzes repositories and creates or updates technical documentation based on support materials. The system uses Azure OpenAI models with Microsoft Entra ID authentication for intelligent content analysis and generation.

## Architecture Components

### 1. Main Entry Point (`main.py`)

The command-line interface that:
- Accepts repository URL, content goal, service area, and support materials
- Configures execution phases (1, 2, 3, 4, or combinations)
- Supports auto-confirmation, debug modes, apply-changes, and skip-toc flags
- Instantiates the orchestrator and displays results

### 2. Core Orchestrator (`content_developer/orchestrator/orchestrator.py`)

The `ContentDeveloperOrchestrator` class manages the four-phase workflow:

```
┌─────────────────────────┐
│ ContentDeveloperOrchestrator │
├─────────────────────────┤
│ - Phase Management      │
│ - Azure OpenAI Client   │
│ - Repository Manager    │
│ - Interactive Confirms  │
└─────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │   4 Phases   │
    └──────────────┘
```

### 3. Four-Phase Workflow

#### Phase 1: Repository Analysis & Directory Selection
- **Repository Management**: Clone/update target repository
- **Material Processing**: Extract and summarize support materials (PDFs, DOCX, URLs)
- **Directory Detection**: Use LLM to select optimal working directory (validates it's a directory, not a file)
- **Interactive Confirmation**: Confirm or manually select directory

#### Phase 2: Content Strategy
- **Content Discovery**: Chunk existing markdown files in working directory
- **Semantic Analysis**: Compare materials against existing content using embeddings
- **Strategy Generation**: Determine CREATE/UPDATE actions with specific files
- **Strategy Confirmation**: Review and confirm content strategy

#### Phase 3: Content Generation
- **Material Loading**: Load full content of support materials
- **Content Creation**: Generate new files based on CREATE actions
- **Content Updates**: Apply targeted updates to existing files
- **Apply Changes**: Optionally write changes to repository

#### Phase 4: TOC Management
- **TOC Analysis**: Parse existing TOC.yml structure
- **Entry Detection**: Identify which generated files are missing from TOC
- **Placement Strategy**: Determine optimal placement for new entries
- **TOC Update**: Generate updated TOC with new entries

### 4. Module Structure

```
content_developer/
├── models/           # Data models
│   ├── config.py     # Config dataclass
│   ├── content.py    # ContentStrategy, DocumentChunk
│   └── result.py     # Result dataclass
├── utils/            # Utilities
│   ├── core_utils.py     # Core utilities
│   ├── file_ops.py       # File operations
│   ├── imports.py        # Dynamic imports handler
│   └── logging.py        # Logging configuration
├── cache/            # Caching system
│   └── unified_cache.py  # Embeddings & manifest cache
├── extraction/       # Content extraction
│   └── content_extractor.py  # Extract from DOCX, PDF, URLs
├── chunking/         # Document chunking
│   └── smart_chunker.py  # Smart markdown chunking
├── processors/       # Core processors
│   ├── smart_processor.py    # SmartProcessor base class
│   ├── material.py           # MaterialProcessor
│   ├── directory.py          # DirectoryDetector
│   ├── discovery.py          # ContentDiscoveryProcessor
│   ├── strategy.py           # ContentStrategyProcessor
│   ├── strategy_helpers.py   # Strategy utilities
│   ├── strategy_debug.py     # Debug visualization
│   ├── llm_native_processor.py # LLM-native operations
│   └── toc_processor.py      # TOC management (Phase 4)
├── generation/       # Content generation (Phase 3)
│   ├── content_generator.py      # Main generator
│   ├── base_content_processor.py # Base class for processors
│   ├── material_loader.py        # Load material content
│   ├── create_processor.py       # Handle CREATE actions
│   └── update_processor.py       # Handle UPDATE actions
├── repository/       # Repository operations
│   └── manager.py    # Git operations & structure
├── interactive/      # User interaction
│   ├── generic_interactive.py  # GenericInteractive base
│   ├── directory.py            # Directory confirmation
│   ├── strategy.py             # Strategy confirmation
│   └── selector.py             # InteractiveSelector
├── display/          # Results display
│   ├── console_display.py  # Rich terminal output
│   └── results.py          # Display formatted results
└── prompts/          # LLM prompts
    ├── material.py     # Material analysis prompts
    ├── directory.py    # Directory selection prompts
    ├── strategy.py     # Strategy generation prompts
    ├── generation.py   # Content generation prompts
    ├── toc.py          # TOC management prompts
    ├── llm_native.py   # LLM-native operations
    ├── helpers.py      # Prompt formatting helpers
    └── schemas.py      # JSON response schemas
```

### 5. Key Components

#### SmartProcessor Base Class
All processors inherit from `SmartProcessor` which provides:
- Azure OpenAI client access via `AzureOpenAIHelper`
- Structured LLM calls with JSON response parsing
- Interaction saving to `llm_outputs/` with atomic methods
- Error handling and logging
- Thinking array formatting for display
- Atomic helper methods for better code organization:
  - `_prepare_output_path()`: Prepares output directory and file paths
  - `_ensure_directory_exists()`: Creates directories safely
  - `_sanitize_source_name()`: Ensures safe file naming
  - `_format_prompt_content()` / `_format_response_data()`: Consistent formatting
  - `_format_numbered_thinking()`: Formats thinking arrays for display

#### BaseContentProcessor Class
Base class for CREATE and UPDATE processors in the generation module:
- Extends SmartProcessor with content generation specific functionality
- Provides shared methods for building material and chunk context
- Handles gap analysis and error reporting
- Manages preview file saving
- Implements tutorial/reference content detection

#### UnifiedCache
Manages embeddings and file manifests with hash-based cache invalidation:
- Caches Azure OpenAI embeddings for semantic search
- Tracks file chunks and their relationships
- Uses SHA256 file hashes to detect changes
- Automatically cleans up orphaned chunks when files change
- Stores in `llm_outputs/embeddings/`
- Key features:
  - `needs_update()`: Compares file hashes to detect changes
  - `cleanup_orphaned_chunks()`: Removes outdated chunks when file is re-chunked
  - `verify_and_cleanup_manifest()`: Validates manifest integrity and removes missing chunks
  - Thread-safe operations with lock mechanism

#### Content Extraction
Supports multiple input formats:
- **DOCX**: Using python-docx
- **PDF**: Using PyPDF2
- **URLs**: Using requests + BeautifulSoup
- **Markdown**: Direct file reading

#### Smart Chunking
Intelligent markdown file chunking:
- Preserves document structure (headers, sections)
- Maintains frontmatter metadata
- Tracks chunk relationships (prev/next)
- Generates unique chunk IDs

### 6. Configuration

#### Config Dataclass
```python
@dataclass
class Config:
    repo_url: str
    content_goal: str
    service_area: str
    support_materials: List[str]
    audience: str = "technical professionals"
    audience_level: str = "intermediate"
    auto_confirm: bool = False
    work_dir: Path = Path("./work/tmp")
    max_repo_depth: int = 3
    content_limit: int = 15000
    phases: str = "all"
    debug_similarity: bool = False
    apply_changes: bool = False
    skip_toc: bool = False
    clean: bool = False
    # Azure OpenAI configurations loaded from environment
```

Post-initialization:
- `_validate_azure_config()`: Validates Azure OpenAI configuration
- `_create_output_directories()`: Creates all required output directories
- `_clean_outputs()`: Cleans previous outputs if --clean flag set

#### Environment Variables
```bash
# Required
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Deployment names (required)
AZURE_OPENAI_COMPLETION_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

# Optional
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_TEMPERATURE=0.3
AZURE_OPENAI_CREATIVE_TEMPERATURE=0.7
```

### 7. Data Flow

```
User Input → Config → Orchestrator
                           ↓
                    Phase 1: Analysis
                    - Clone/Update Repo
                    - Process Materials
                    - Detect Directory
                           ↓
                    Phase 2: Strategy
                    - Discover Content
                    - Generate Embeddings
                    - Analyze Gaps
                    - Plan Actions
                           ↓
                    Phase 3: Generation
                    - Load Materials
                    - Create Content
                    - Update Content
                           ↓
                    Phase 4: TOC Management
                    - Parse TOC.yml
                    - Identify Missing
                    - Update Structure
                           ↓
                    Display Results
```

### 8. LLM Integration

The system uses specialized prompts for each operation:
- **Material Summary**: Extracts key concepts, technologies, and summaries
- **Directory Selection**: Analyzes repository structure for optimal placement (with file/directory validation)
- **Content Strategy**: Performs gap analysis and plans actions
- **Content Generation**: Creates new content following Microsoft Learn standards
- **Content Updates**: Applies targeted updates to existing files
- **TOC Management**: Intelligently places new entries in existing TOC structure

Each LLM call:
- Uses structured JSON response format with schemas
- Includes thinking arrays for reasoning transparency
- Saves interactions to `llm_outputs/` for debugging
- Handles errors gracefully with tenacity retries

### 9. Performance Features

- **Embeddings Cache**: Reuses embeddings across runs
- **Incremental Processing**: Only processes changed files
- **Chunked Content**: Handles large repositories efficiently
- **Parallel Material Processing**: Processes multiple materials concurrently
- **Smart Context Management**: Only loads necessary content for LLM calls
- **Type-Safe Embeddings**: Ensures consistent float list format for vector operations
- **Azure OpenAI Integration**: Uses DefaultAzureCredential for secure authentication

### 10. Output Structure

```
llm_outputs/

├── embeddings/             # Cached embeddings
│   └── [repo]/[directory]/ # Organized by repository and directory
└── preview/                # Generated content preview
    ├── create/             # New files (flat structure)
    ├── updates/            # Updated files (flat structure)
    └── toc/                # TOC updates
```

### 11. Error Handling

- **Graceful Degradation**: Falls back to manual selection if LLM fails
- **Validation Gates**: Checks prerequisites before each phase
- **Material Validation**: Ensures materials are loaded before generation
- **Directory Validation**: Confirms directory exists and contains markdown (not a file)
- **Comprehensive Logging**: Detailed logs for debugging
- **Type Safety**: Ensures embeddings are always lists of floats with `_ensure_float_list()`
- **Defensive Programming**: 
  - Validates chunk data types before processing
  - Handles malformed strategy decisions gracefully
  - Checks for dictionary types before accessing keys
  - Provides fallback values for missing data
- **TOC Validation**: Handles invalid YAML syntax gracefully with --skip-toc option

### 12. Content Generation Features

#### Markdown Block Extraction
The system automatically extracts content from markdown code blocks that LLMs often wrap responses in:
- Handles ``` and ```` delimiters
- Supports language-specific blocks (```markdown)
- Extracts clean content for file writing

#### Targeted Update System
Instead of overwriting entire files, the update processor:
- Requests specific changes from the LLM in JSON format
- Applies targeted replacements, modifications, and additions
- Preserves unchanged content for cleaner git diffs
- Maintains document structure and formatting

The update format:
```json
{
  "changes": [
    {
      "section": "Section name",
      "action": "add|replace|modify",
      "original": "Original text (for replace/modify)",
      "updated": "New or updated content",
      "reason": "Explanation"
    }
  ]
}
```

### 13. Thinking Arrays

All LLM responses now include thinking as arrays instead of strings:

```json
{
  "thinking": [
    "First, I analyze the repository structure",
    "Next, I identify the appropriate pattern",
    "Then, I select the best directory",
    "Finally, I validate my selection"
  ],
  // ... other fields
}
```

Benefits:
- **Better readability**: Each thought on its own line in terminal
- **Structured reasoning**: Clear step-by-step thinking
- **Easier processing**: Can iterate over individual thoughts
- **Consistent display**: Formatted with numbered bullets

### 14. Future Enhancements

1. **Batch Processing**: Handle multiple content goals
2. **Cross-Reference Updates**: Update related documents automatically
3. **Multi-Language Support**: Generate content in multiple languages
4. **Custom Templates**: Support custom content type templates
5. **CI/CD Integration**: GitHub Actions support
6. **Metrics Tracking**: Track generation quality and usage
7. **Private Endpoint Support**: Azure Private Link integration

## Cache System

The application uses a unified cache system for storing chunks and embeddings:

### Unified Data Structure
Each chunk is stored with all its data in a single cache entry:
```json
{
  "chunk_id": "abc123...",
  "data": {
    "content": "chunk text...",
    "file_path": "path/to/file.md",
    "heading_path": ["Section", "Subsection"],
    "embedding": [0.123, 0.456, ...],  // null until generated
    "embedding_model": "text-embedding-3-small",
    "embedding_generated_at": "2025-06-01T10:00:00Z",
    // ... other chunk fields
  },
  "meta": {
    "type": "chunk",
    "has_embedding": true,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### Benefits
- **No cache collisions**: Chunks and embeddings stored together
- **Atomic updates**: All data for a chunk updated together
- **Better performance**: Single cache lookup gets all data
- **Easier debugging**: All related data in one place

### Migration
The system automatically migrates legacy cache entries to the unified structure. To clean cache and start fresh:
```bash
./scripts/reset.sh cache
```

## Technical Notes

### Azure OpenAI Authentication
Uses DefaultAzureCredential which supports:
- Azure CLI authentication (recommended for development)
- Managed Identity (for Azure-hosted environments)
- Environment variables (service principal)
- Visual Studio Code credentials
- Azure PowerShell authentication

### Python Version Compatibility
- Requires Python 3.8-3.12
- Python 3.13 is not yet supported due to dependencies requiring updates

### Model Selection
- Completion operations use the deployment specified in `AZURE_OPENAI_COMPLETION_DEPLOYMENT`
- Embedding operations use the deployment specified in `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- All models are accessed through Azure OpenAI deployments, not OpenAI directly 