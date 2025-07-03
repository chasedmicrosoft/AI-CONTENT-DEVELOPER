# AI Content Developer - Architecture

## System Overview

AI Content Developer is a sophisticated documentation generation system that leverages Azure OpenAI to analyze repositories and create or update documentation based on support materials. The system is designed with modularity, extensibility, and reliability in mind.

## Core Principles

### 1. Phased Execution
The system operates in 5 distinct phases, each with clear inputs, outputs, and responsibilities:

- **Phase 1**: Repository Analysis & Directory Selection
- **Phase 2**: Content Strategy & Gap Analysis
- **Phase 3**: Content Generation
- **Phase 4**: Content Remediation (SEO, Security, Accuracy)
- **Phase 5**: TOC Management

### 2. Processor-Based Architecture
Every major operation is encapsulated in a processor that inherits from either:
- `SmartProcessor`: For operations requiring embeddings and caching
- `LLMNativeProcessor`: For direct LLM operations without embeddings

### 3. Intelligent Caching
The system implements sophisticated caching for embeddings and document chunks to optimize performance and reduce costs.

## Component Architecture

### Core Components

#### 1. Orchestrator (`orchestrator/orchestrator.py`)
The main coordinator that:
- Manages phase execution flow
- Handles configuration and authentication
- Coordinates processor interactions
- Manages state between phases
- Applies remediated content to repository

#### 2. Processors (`processors/`)
Specialized components for specific tasks:

**Base Processors:**
- `SmartProcessor`: Base class with embedding support
- `LLMNativeProcessor`: Base class for direct LLM operations

**Phase 1 Processors:**
- `MaterialProcessor`: Extracts and analyzes support materials
- `DirectoryDetector`: Uses LLM to select optimal working directory

**Phase 2 Processors:**
- `ContentDiscoveryProcessor`: Chunks documents and manages cache
- `ContentStrategyProcessor`: Performs gap analysis and creates strategy

**Phase 3 Processors:**
- `ContentGenerator`: Orchestrates content creation/updates
- `CreateProcessor`: Generates new documentation
- `UpdateProcessor`: Updates existing documentation

**Phase 4 Processors (Content Remediation):**
- `ContentRemediationProcessor`: Orchestrates three-step remediation
- `SEOProcessor`: Optimizes for search engines
- `SecurityProcessor`: Removes sensitive information
- `AccuracyProcessor`: Validates technical accuracy

**Phase 5 Processors (TOC Management):**
- `TOCProcessor`: Analyzes and updates table of contents

### 3. Cache System (`cache/unified_cache.py`)

The unified cache manages:
- Document embeddings
- Chunk metadata
- File manifests
- Orphaned chunk cleanup

```python
Cache Structure:
./llm_outputs/embeddings/
└── [repo_name]/
    └── [working_directory]/
        ├── manifest.json       # File hash mappings
        └── [chunk_id].json    # Chunk data + embeddings
```

### 4. Content Extraction (`extraction/content_extractor.py`)

Supports multiple formats:
- PDF documents (via PyPDF2)
- Word documents (via python-docx)
- Markdown files
- Web pages (via BeautifulSoup)
- Plain text

### 5. Document Chunking (`chunking/smart_chunker.py`)

Smart chunking that:
- Preserves document structure
- Maintains heading hierarchy
- Creates linkable chunks
- Generates embedding-optimized content

### 6. Repository Management (`repository/manager.py`)

Handles:
- Git operations (clone, update)
- Directory structure analysis
- File system operations
- Large repository optimization

## Data Flow

### Phase 1: Repository Analysis
```
Materials → MaterialProcessor → Summaries
     ↓
Repository → Clone → Structure Analysis → DirectoryDetector → Working Directory
     ↓
Confirmation → Result
```

### Phase 2: Content Strategy
```
Working Directory → ContentDiscoveryProcessor → Chunks
         ↓
Chunks + Embeddings → Cache
         ↓
Chunks + Materials → ContentStrategyProcessor → Strategy
         ↓
Strategy Confirmation → Result
```

### Phase 3: Content Generation
```
Strategy → ContentGenerator
    ↓
CREATE actions → CreateProcessor → New Files
UPDATE actions → UpdateProcessor → Updated Files
    ↓
Preview Files → Result (No direct application)
```

### Phase 4: Content Remediation
```
Preview Files → ContentRemediationProcessor
         ↓
    Step 1: SEOProcessor → SEO Optimized Content
         ↓
    Step 2: SecurityProcessor → Secure Content
         ↓
    Step 3: AccuracyProcessor → Validated Content
         ↓
Final Content → Apply to Repository (if --apply-changes)
```

### Phase 5: TOC Management
```
Generated Files → TOCProcessor
        ↓
TOC.yml Analysis → Missing Entries
        ↓
Placement Strategy → Updated TOC
        ↓
Apply Changes → TOC.yml (if --apply-changes)
```

## Key Design Patterns

### 1. Template Method Pattern
Base processors define the structure, subclasses implement specifics:

```python
class SmartProcessor:
    def process(self, *args, **kwargs):
        return self._process(*args, **kwargs)
    
    def _process(self, *args, **kwargs):
        # Subclass implementation
        pass
```

### 2. Strategy Pattern
Different strategies for content generation, updates, and remediation.

### 3. Chain of Responsibility
Remediation steps form a chain where each processor improves the content sequentially.

### 4. Factory Pattern
Prompt generation uses factory methods to create phase-specific prompts.

## Security Architecture

### Authentication
- Uses Azure Entra ID (formerly Azure AD) via DefaultAzureCredential
- No API keys stored in code or configuration
- Supports multiple authentication methods

### Data Security
- Sensitive information removed during remediation
- No production credentials in examples
- Safe domain names and IP ranges used
- Placeholder patterns for sensitive values

### Caching Security
- Embeddings stored locally
- No sensitive content in cache keys
- Cache isolated by repository and directory

## Performance Optimizations

### 1. Intelligent Caching
- File hash-based change detection
- Embedding reuse for unchanged content
- Manifest-based orphan cleanup
- Automatic cache verification

### 2. Parallel Processing
- Concurrent file processing in discovery
- Thread pool for chunk generation
- Async where beneficial

### 3. Large Repository Handling
- Directory-only view for >5,000 files
- Excluded directories (node_modules, etc.)
- Depth limiting for structure analysis
- Automatic detection and optimization

### 4. Prompt Optimization
- Token-aware content truncation
- Relevant chunk selection
- Context window management
- Dynamic content type loading

## Error Handling

### Graceful Degradation
- Each phase can fail independently
- Partial results are preserved
- Clear error messages with recovery suggestions

### Retry Logic
- API calls have retry with exponential backoff
- Cache operations are atomic
- File operations have rollback capability

### Validation
- Input validation at each phase
- Output validation before proceeding
- Schema validation for LLM responses
- Content type compatibility checks

## Phase 4: Content Remediation Details

### Three-Step Remediation Process

#### Step 1: SEO Optimization
- Title tag optimization (H1 < 60 chars)
- Meta description generation (150-160 chars)
- Heading hierarchy improvement
- Keyword density optimization
- Internal linking suggestions
- Featured snippet optimization

#### Step 2: Security Remediation
- Credential removal and replacement
- IP address sanitization (RFC 1918)
- Domain name standardization
- PII removal
- Resource identifier anonymization
- Security warning additions

#### Step 3: Accuracy Validation
- Cross-reference with source materials
- Technical claim verification
- Code syntax validation
- Version compatibility checks
- Service limit validation
- Completeness assessment

### Remediation Data Flow
```
Each file goes through all three steps sequentially:
Original → SEO → Security → Accuracy → Final

Preview files are overwritten at each step:
./llm_outputs/preview/{create|update}/file.md (updated 3 times)
```

## Extensibility Points

### 1. New Processors
Create new processors by inheriting from base classes:
```python
class MyProcessor(SmartProcessor):
    def _process(self, ...):
        # Implementation
```

### 2. New Content Types
Add to `content_standards.json`:
```json
{
  "contentTypes": [
    {
      "id": "new-type",
      "name": "New Type",
      "structure": [...]
    }
  ]
}
```

### 3. New Material Formats
Extend `ContentExtractor`:
```python
def extract_new_format(self, file_path):
    # Implementation
```

### 4. Custom Prompts
Add new prompts in `prompts/phase*/`:
```python
def get_custom_prompt(...):
    return f"""Custom prompt..."""
```

### 5. New Remediation Steps
Add processors in `processors/phase4/`:
```python
class CustomRemediationProcessor(LLMNativeProcessor):
    def _process(self, content, file_info, config):
        # Implementation
```

## Configuration Management

### Environment Variables
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `AZURE_OPENAI_COMPLETION_DEPLOYMENT`: Model for completion
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`: Model for embeddings
- `AZURE_OPENAI_API_VERSION`: API version (default: 2024-08-01-preview)

### Command Line Configuration
- Repository and materials
- Phase selection
- Output control
- Debug options
- Apply changes flag

### Content Standards
`content_standards.json` defines:
- Document types
- Structure templates
- Formatting rules
- Code guidelines
- Microsoft-specific elements

## Monitoring and Logging

### Logging Structure
- Phase-level logging
- Processor-level operations
- LLM interactions saved
- Error tracking with context
- Step tracking system

### Metrics
- Token usage per phase
- Processing times
- Cache hit rates
- Error frequencies
- Remediation improvements

### Output Structure
```
./llm_outputs/
├── tool_logs.txt               # LLM interaction logs
├── materials_summary/          # Material analysis
├── decisions/                  # Directory selection
├── content_strategy/           # Strategy results
├── embeddings/                 # Cache directory
├── generation/                 # Generation logs
├── phase4/                     # Remediation logs
├── phase5/                     # TOC management logs
└── preview/                    # Generated content
    ├── create/                 # New files
    └── update/                 # Updated files
```

## Future Architecture Considerations

### Potential Enhancements
1. **Streaming Generation**: Stream content as it's generated
2. **Distributed Processing**: Process large repos across multiple workers
3. **Plugin System**: Allow custom processors via plugins
4. **Web UI**: Add web interface for better UX
5. **Multi-Model Support**: Support different LLM providers
6. **Custom Remediation Steps**: Allow user-defined remediation

### Scalability Considerations
- Database for large-scale caching
- Queue system for async processing
- Horizontal scaling for parallel execution
- CDN for material storage

## Architecture Decisions

### Why Phases?
- Clear separation of concerns
- Ability to run partial workflows
- Better error isolation
- Easier debugging and testing

### Why Processor Pattern?
- Encapsulation of logic
- Reusability across phases
- Consistent interface
- Easy to extend

### Why Local Caching?
- No external dependencies
- Fast access
- Full control
- Privacy preservation

### Why Azure OpenAI?
- Enterprise security
- Consistent performance
- Compliance capabilities
- Integration with Azure services

### Why Progressive Remediation?
- Each step builds on previous improvements
- Specialized focus for each concern
- Measurable quality improvements
- Flexibility to add/remove steps 