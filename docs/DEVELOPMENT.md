# AI Content Developer - Development Guide

## Development Environment Setup

### Prerequisites

1. **Python 3.12 or earlier**
   ```bash
   python --version  # Should be 3.12.x or lower
   ```

2. **Git**
   ```bash
   git --version
   ```

3. **Azure CLI**
   ```bash
   az --version
   ```

4. **Development Tools**
   - VS Code or PyCharm
   - Python extension for your IDE
   - Git integration

### Setting Up Development Environment

1. **Clone and Setup**
   ```bash
   git clone https://github.com/chasedmicrosoft/ai-content-developer.git
   cd ai-content-developer
   
   # Create virtual environment
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

2. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your Azure OpenAI settings
   ```

3. **Install Pre-commit Hooks** (if using)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Organization

### Directory Structure

```
content_developer/
├── __init__.py
├── constants.py           # Global constants (MAX_PHASES, etc.)
├── models/               # Data models
│   ├── __init__.py
│   ├── config.py        # Configuration model
│   ├── content.py       # Content-related models
│   └── result.py        # Result model
├── processors/          # Core processing logic
│   ├── __init__.py
│   ├── smart_processor.py      # Base class with embeddings
│   ├── llm_native_processor.py # Base class for LLM ops
│   ├── material.py            # Phase 1: Material processing
│   ├── directory.py           # Phase 1: Directory detection
│   ├── discovery.py           # Phase 2: Content discovery
│   ├── strategy.py            # Phase 2: Strategy generation
│   ├── phase4/               # Phase 4: Remediation processors
│   │   ├── __init__.py
│   │   ├── remediation_processor.py  # Main orchestrator
│   │   ├── seo_processor.py         # SEO optimization
│   │   ├── security_processor.py    # Security remediation
│   │   └── accuracy_processor.py    # Accuracy validation
│   └── phase5/               # Phase 5: TOC management
│       ├── __init__.py
│       └── toc_processor.py
├── generation/          # Phase 3: Content generation
├── extraction/          # Content extraction utilities
├── chunking/           # Document chunking
├── cache/              # Caching system
├── repository/         # Git operations
├── interactive/        # User interactions
├── display/            # Output display
├── prompts/            # LLM prompts (organized by phase)
│   ├── phase1/         # Repository analysis prompts
│   ├── phase2/         # Strategy prompts
│   ├── phase3/         # Generation prompts
│   ├── phase4/         # Remediation prompts
│   ├── phase5/         # TOC prompts
│   └── supporting/     # Helper prompts
├── utils/              # Utilities
│   ├── core_utils.py
│   ├── file_ops.py
│   ├── step_tracker.py  # Phase/step tracking
│   └── logging.py
└── orchestrator/       # Main orchestrator
```

### Import Organization

Follow this import order in Python files:

```python
"""Module docstring"""
# Standard library imports
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import openai
from azure.identity import DefaultAzureCredential

# Local imports
from ..models import Config, Result
from ..utils import write, mkdir, get_step_tracker
from .base_processor import BaseProcessor
```

## Phase Organization

The system operates in 5 phases:

1. **Phase 1**: Repository Analysis & Directory Selection
2. **Phase 2**: Content Strategy & Gap Analysis
3. **Phase 3**: Content Generation (creates preview files)
4. **Phase 4**: Content Remediation (SEO, Security, Accuracy)
5. **Phase 5**: TOC Management

**Important**: Content is only applied to repository after Phase 4 with `--apply-changes`.

## Development Workflow

### 1. Plan-Do-Summary Workflow

For each development task:

1. **PLAN** (`plans/PLAN_[feature].md`):
   ```markdown
   # Plan: [Feature Name]
   
   ## Objective
   Clear description of what we're building
   
   ## Requirements
   - Requirement 1
   - Requirement 2
   
   ## Implementation Steps
   1. Step 1
   2. Step 2
   
   ## Success Criteria
   - Criteria 1
   - Criteria 2
   ```

2. **DO** (Implement the feature):
   - Create feature branch
   - Implement changes
   - Test thoroughly
   - Update documentation

3. **SUMMARY** (`plans/SUMMARY_[feature].md`):
   ```markdown
   # Summary: [Feature Name]
   
   ## What Was Done
   - Implementation detail 1
   - Implementation detail 2
   
   ## Key Changes
   - File 1: Change description
   - File 2: Change description
   
   ## Testing
   - Test case 1: Result
   - Test case 2: Result
   
   ## Next Steps
   - Future enhancement 1
   - Future enhancement 2
   ```

### 2. Creating New Processors

#### Base Processor Selection

Choose the appropriate base class:

```python
# For operations requiring embeddings/caching
from .smart_processor import SmartProcessor

class MyProcessor(SmartProcessor):
    def _process(self, *args, **kwargs):
        # Implementation
        pass

# For direct LLM operations (e.g., remediation)
from .llm_native_processor import LLMNativeProcessor

class MyLLMProcessor(LLMNativeProcessor):
    def _process(self, *args, **kwargs):
        # Implementation
        pass
```

#### Processor Template with Step Tracking

```python
"""
My processor description
"""
import logging
from typing import Dict, List
from pathlib import Path

from ..models import Config
from ..utils import get_step_tracker
from .smart_processor import SmartProcessor

logger = logging.getLogger(__name__)


class MyProcessor(SmartProcessor):
    """Detailed processor description"""
    
    def _process(self, input_data: Dict, config: Config) -> Dict:
        """Process the input data
        
        Args:
            input_data: Input dictionary
            config: Configuration object
            
        Returns:
            Dictionary with results
        """
        # Validate input
        self._validate_input(input_data)
        
        # Show operation if console available
        if self.console_display:
            self.console_display.show_operation("Processing...")
        
        # Track step if phase/step is set
        step_tracker = get_step_tracker()
        if hasattr(self, 'phase') and hasattr(self, 'step'):
            step_tracker.track(self.phase, self.step, "My Operation")
        
        # Main processing logic
        result = self._perform_operation(input_data)
        
        # Save interaction if needed
        self.save_interaction("operation_type", input_data, result)
        
        return result
    
    def _validate_input(self, input_data: Dict) -> None:
        """Validate input data"""
        if not input_data:
            raise ValueError("Input data is required")
    
    def _perform_operation(self, input_data: Dict) -> Dict:
        """Perform the main operation"""
        # Implementation
        return {"success": True}
    
    def process(self, *args, **kwargs):
        """Public interface"""
        return self._process(*args, **kwargs)
```

### 3. Adding New Prompts

#### Prompt Organization by Phase

Create prompts in the appropriate phase directory:

```
prompts/
├── phase1/              # Repository analysis
│   ├── __init__.py
│   ├── material_summary.py
│   └── directory_selection.py
├── phase2/              # Content strategy
│   ├── __init__.py
│   └── unified_strategy.py
├── phase3/              # Content generation
│   ├── __init__.py
│   ├── create_content.py
│   ├── update_content.py
│   └── material_sufficiency.py
├── phase4/              # Remediation
│   ├── __init__.py
│   ├── seo_remediation.py
│   ├── security_remediation.py
│   └── accuracy_validation.py
├── phase5/              # TOC management
│   ├── __init__.py
│   └── toc_update.py
└── supporting/          # Helper prompts
    ├── __init__.py
    └── content_placement.py
```

#### Prompt Structure

```python
"""
Prompt description - Phase N: Operation Name
"""

def get_my_prompt(param1: str, param2: Dict) -> str:
    """Generate prompt for specific operation
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Formatted prompt string
    """
    return f"""Your prompt here with {param1}
    
    Context: {param2}
    
    Instructions:
    1. Instruction 1
    2. Instruction 2
    
    Output format:
    {{
        "field1": "value",
        "field2": "value"
    }}
    """

MY_SYSTEM_PROMPT = """You are an expert..."""
```

#### Prompt Best Practices

1. **Clear Instructions**: Be explicit about what you want
2. **Examples**: Provide examples of expected output
3. **Constraints**: Specify what NOT to do
4. **Output Format**: Define exact JSON structure
5. **Token Awareness**: Keep prompts concise

### 4. Working with Phases

#### Adding Logic to Existing Phase

1. Locate the phase method in `orchestrator.py`:
   ```python
   def _execute_phase[N](self, result: Result) -> None:
   ```

2. Add your logic maintaining the pattern:
   ```python
   # Reset step counter
   step_tracker = get_step_tracker()
   step_tracker.reset_phase(N)
   
   # Your logic here
   processor = YourProcessor(self.client, self.config, self.console_display)
   processor.set_phase_step(N, step_number)
   output = processor.process(...)
   ```

#### Working with Phase 4 (Remediation)

Phase 4 has special considerations:

```python
# Phase 4 processes files through 3 sequential steps
class ContentRemediationProcessor(SmartProcessor):
    def _process(self, generation_results, materials, config, working_dir):
        # Step 1: SEO
        seo_processor = SEOProcessor(...)
        seo_processor.set_phase_step(4, 1)
        
        # Step 2: Security
        security_processor = SecurityProcessor(...)
        security_processor.set_phase_step(4, 2)
        
        # Step 3: Accuracy
        accuracy_processor = AccuracyProcessor(...)
        accuracy_processor.set_phase_step(4, 3)
```

Each remediation step:
- Reads content from preview
- Applies specific improvements
- Overwrites the preview file
- Passes content to next step

#### Creating New Phase

1. Update `constants.py`:
   ```python
   MAX_PHASES = 6  # Increment
   ```

2. Add phase method to orchestrator:
   ```python
   def _execute_phase6(self, result: Result) -> None:
       """Execute Phase 6: Your Phase"""
       logger.info("=== Phase 6: Your Phase ===")
       
       # Reset step counter
       step_tracker = get_step_tracker()
       step_tracker.reset_phase(6)
       
       # Implementation
   ```

3. Update phase execution in `execute()` method

4. Create processors in `processors/phase6/`

5. Create prompts in `prompts/phase6/`

## Testing

### Unit Testing

Create tests in `tests/` directory:

```python
import unittest
from unittest.mock import Mock, patch
from content_developer.processors import MyProcessor

class TestMyProcessor(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.config = Mock()
        self.processor = MyProcessor(self.client, self.config)
    
    def test_process_success(self):
        # Test implementation
        result = self.processor.process(test_input)
        self.assertTrue(result['success'])
    
    def test_process_validation_error(self):
        with self.assertRaises(ValueError):
            self.processor.process(None)
    
    def test_step_tracking(self):
        # Test step tracking
        self.processor.set_phase_step(1, 1)
        result = self.processor.process(test_input)
        # Verify step was tracked
```

### Integration Testing

Test full workflows:

```bash
# Test single phase
python main.py --repo https://github.com/test/repo \
    --goal "Test goal" \
    --service "Test Service" \
    -m test.md \
    --phases 1

# Test phase combination
python main.py ... --phases 12 --auto-confirm

# Test remediation
python main.py ... --phases 34 --apply-changes
```

### Manual Testing Checklist

- [ ] Test with minimal inputs
- [ ] Test with large inputs
- [ ] Test error cases
- [ ] Test recovery from failures
- [ ] Test with different content types
- [ ] Test with various repository sizes
- [ ] Verify console output formatting
- [ ] Check log output
- [ ] Verify step tracking works
- [ ] Test remediation improvements

## Debugging

### Enable Debug Mode

```python
# In your code
logger.debug(f"Processing {len(items)} items")

# Set environment
export LOG_LEVEL=DEBUG
export AI_CONTENT_DEBUG=true
```

### Common Debugging Techniques

1. **Add Console Output**:
   ```python
   if self.console_display:
       self.console_display.show_operation(f"Debug: {variable}")
   ```

2. **Save Intermediate Results**:
   ```python
   self.save_interaction("debug_stage", input_data, output)
   ```

3. **Use Python Debugger**:
   ```python
   import pdb; pdb.set_trace()
   ```

4. **Log LLM Interactions**:
   ```python
   logger.debug(f"LLM Request: {messages}")
   logger.debug(f"LLM Response: {response}")
   ```

5. **Track Phase Progress**:
   ```python
   step_tracker = get_step_tracker()
   logger.debug(f"Current phase: {step_tracker.current_phase}")
   logger.debug(f"Current step: {step_tracker.current_step}")
   ```

## Code Quality Standards

### 1. Method Design

- **Single Responsibility**: Each method does one thing
- **Atomic Methods**: 20-30 lines max
- **Clear Naming**: `_validate_input()`, `_process_chunks()`
- **Type Hints**: Always use type hints

### 2. Error Handling

```python
try:
    result = self._process_data(data)
except SpecificError as e:
    logger.error(f"Failed to process: {e}")
    if self.console_display:
        self.console_display.show_error(str(e))
    return self._create_error_result(e)
```

### 3. Documentation

- **Module Docstrings**: Describe purpose
- **Class Docstrings**: Explain responsibility
- **Method Docstrings**: Document args, returns, raises
- **Inline Comments**: Explain "why", not "what"

### 4. Constants

Define in `constants.py`:
```python
# Phase limits
MAX_PHASES = 5
DEFAULT_PHASE = "all"

# Processing limits
MAX_CHUNK_SIZE = 1000
MAX_EMBEDDINGS_BATCH = 100

# Timeouts
LLM_TIMEOUT = 60  # seconds

# Remediation steps
REMEDIATION_STEPS = ["seo", "security", "accuracy"]
```

### 5. Working with ContentDecision

Always use as dataclass, not dictionary:

```python
# Correct
if action.filename:
    process_file(action.filename)

# Incorrect (old style)
if action['filename']:
    process_file(action['filename'])
```

## Performance Optimization

### 1. Caching Strategy

```python
# Check cache first
cached_result = self._get_from_cache(key)
if cached_result:
    return cached_result

# Process and cache
result = self._expensive_operation()
self._save_to_cache(key, result)
return result
```

### 2. Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(self._process_item, item): item 
               for item in items}
    
    for future in as_completed(futures):
        result = future.result()
        # Handle result
```

### 3. Memory Management

```python
# Process in chunks
for chunk in self._chunk_iterator(large_list, chunk_size=100):
    self._process_chunk(chunk)
    
# Clear unnecessary data
del large_temporary_data
```

### 4. Embedding Optimization

```python
# Reuse embeddings for unchanged files
if not cache.needs_update(file_key, file_hash):
    return cache.get_embeddings(file_key)
```

## Contributing Guidelines

### 1. Branch Strategy

```bash
# Feature branch
git checkout -b feature/your-feature-name

# Bug fix
git checkout -b fix/issue-description

# Documentation
git checkout -b docs/update-description
```

### 2. Commit Messages

Follow conventional commits:
```
feat: add new processor for X
fix: resolve embedding cache issue
docs: update troubleshooting guide
refactor: simplify strategy processor
test: add unit tests for Y
```

### 3. Pull Request Process

1. **Create PR with**:
   - Clear description
   - Link to issue (if applicable)
   - Test results
   - Documentation updates

2. **PR Checklist**:
   - [ ] Tests pass
   - [ ] Documentation updated
   - [ ] No hardcoded values
   - [ ] Follows code standards
   - [ ] Backwards compatible
   - [ ] Step tracking implemented

### 4. Code Review Focus

- **Functionality**: Does it work as intended?
- **Performance**: Any bottlenecks?
- **Security**: No credentials or sensitive data?
- **Maintainability**: Easy to understand?
- **Testing**: Adequate test coverage?
- **Phase Integration**: Fits phase pattern?

## Troubleshooting Development Issues

### Common Development Problems

1. **Import Errors**:
   ```python
   # Ensure proper package structure
   # Add __init__.py files
   # Use relative imports correctly
   from ..models import Config  # Not from models import Config
   ```

2. **Type Errors**:
   ```python
   # Always validate types
   if not isinstance(input_data, dict):
       raise TypeError(f"Expected dict, got {type(input_data)}")
   
   # Use dataclasses correctly
   if hasattr(action, 'filename'):  # ContentDecision is dataclass
       filename = action.filename
   ```

3. **Phase Dependencies**:
   ```python
   # Ensure required data exists
   if not result.generation_results:
       raise ValueError("Phase 4 requires Phase 3 results")
   ```

### Development Tools

1. **Linting**:
   ```bash
   pip install flake8 black mypy
   flake8 content_developer/
   black content_developer/
   mypy content_developer/
   ```

2. **Testing**:
   ```bash
   pip install pytest pytest-cov
   pytest tests/
   pytest --cov=content_developer tests/
   ```

3. **Documentation**:
   ```bash
   pip install sphinx
   # Generate API docs
   sphinx-apidoc -o docs/api content_developer/
   ```

## Key Patterns to Follow

### 1. Processor Pattern
- Inherit from appropriate base class
- Implement `_process()` method
- Add `process()` public interface
- Use step tracking

### 2. Prompt Pattern
- Organize by phase
- Include system prompt
- Define clear output format
- Handle edge cases

### 3. Cache Pattern
- Check cache before processing
- Update cache after processing
- Handle cache misses gracefully
- Clean orphaned entries

### 4. Console Display Pattern
- Check if console_display exists
- Show appropriate messages
- Use correct severity levels
- Provide progress updates

## Next Steps

1. **Explore the Codebase**:
   - Start with `main.py`
   - Follow execution to `orchestrator.py`
   - Understand phase flow
   - Study processor patterns

2. **Make Small Changes**:
   - Fix a typo
   - Improve logging
   - Add validation
   - Enhance error messages

3. **Contribute Features**:
   - Pick an issue
   - Discuss approach
   - Implement with tests
   - Submit PR

4. **Learn Patterns**:
   - Study existing processors
   - Understand prompt structure
   - Follow established patterns
   - Review recent PRs 