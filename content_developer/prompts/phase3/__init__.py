"""
Phase 3: Content Generation prompts
"""
from .create_content import (
    get_create_content_prompt,
    CREATE_CONTENT_SYSTEM
)
from .update_content import (
    get_update_content_prompt,
    UPDATE_CONTENT_SYSTEM
)
from .material_sufficiency import (
    get_pregeneration_sufficiency_prompt,
    get_postgeneration_sufficiency_prompt
)

__all__ = [
    'get_create_content_prompt',
    'CREATE_CONTENT_SYSTEM',
    'get_update_content_prompt',
    'UPDATE_CONTENT_SYSTEM',
    'get_pregeneration_sufficiency_prompt',
    'get_postgeneration_sufficiency_prompt'
] 