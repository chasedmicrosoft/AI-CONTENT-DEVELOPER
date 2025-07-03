"""
LLM Native prompts - Backward compatibility imports
This file maintains backward compatibility by importing from the new location
"""
from .supporting.content_placement import (
    get_content_placement_prompt,
    CONTENT_PLACEMENT_SYSTEM
)
from .supporting.terminal_section import (
    get_terminal_section_prompt,
    TERMINAL_SECTION_SYSTEM
)
from .supporting.content_quality import (
    get_content_quality_prompt,
    get_content_quality_system
)
from .supporting.information_extraction import (
    get_information_extraction_prompt,
    INFORMATION_EXTRACTION_SYSTEM
)

# Re-export for backward compatibility
__all__ = [
    'CONTENT_PLACEMENT_SYSTEM',
    'get_content_placement_prompt',
    'TERMINAL_SECTION_SYSTEM',
    'get_terminal_section_prompt',
    'get_content_quality_system',
    'get_content_quality_prompt',
    'INFORMATION_EXTRACTION_SYSTEM',
    'get_information_extraction_prompt'
] 