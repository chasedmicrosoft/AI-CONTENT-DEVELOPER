"""
Prompts for AI Content Developer
"""

# Phase 1: Repository Analysis
from .phase1 import (
    get_material_summary_prompt,
    MATERIAL_SUMMARY_SYSTEM,
    get_directory_selection_prompt,
    DIRECTORY_SELECTION_SYSTEM
)

# Phase 2: Content Strategy
from .phase2 import (
    get_unified_content_strategy_prompt,
    UNIFIED_CONTENT_STRATEGY_SYSTEM
)

# Phase 3: Content Generation
from .phase3 import (
    get_create_content_prompt,
    CREATE_CONTENT_SYSTEM,
    get_update_content_prompt,
    UPDATE_CONTENT_SYSTEM,
    get_pregeneration_sufficiency_prompt,
    get_postgeneration_sufficiency_prompt
)

# Phase 4: Content Remediation
from .phase4 import (
    get_seo_remediation_prompt,
    SEO_REMEDIATION_SYSTEM,
    get_security_remediation_prompt,
    SECURITY_REMEDIATION_SYSTEM,
    get_accuracy_validation_prompt,
    ACCURACY_VALIDATION_SYSTEM
)

# Phase 5: TOC Management
from .phase5 import (
    get_toc_update_prompt,
    TOC_UPDATE_SYSTEM
)

# Supporting prompts
from .supporting import (
    get_content_placement_prompt,
    CONTENT_PLACEMENT_SYSTEM,
    get_terminal_section_prompt,
    TERMINAL_SECTION_SYSTEM,
    get_content_quality_prompt,
    get_content_quality_system,
    get_information_extraction_prompt,
    INFORMATION_EXTRACTION_SYSTEM
)

__all__ = [
    # Phase 1
    'get_material_summary_prompt',
    'MATERIAL_SUMMARY_SYSTEM',
    'get_directory_selection_prompt',
    'DIRECTORY_SELECTION_SYSTEM',
    
    # Phase 2
    'get_unified_content_strategy_prompt',
    'UNIFIED_CONTENT_STRATEGY_SYSTEM',
    
    # Phase 3
    'get_create_content_prompt',
    'CREATE_CONTENT_SYSTEM',
    'get_update_content_prompt',
    'UPDATE_CONTENT_SYSTEM',
    'get_pregeneration_sufficiency_prompt',
    'get_postgeneration_sufficiency_prompt',
    
    # Phase 4
    'get_seo_remediation_prompt',
    'SEO_REMEDIATION_SYSTEM',
    'get_security_remediation_prompt',
    'SECURITY_REMEDIATION_SYSTEM',
    'get_accuracy_validation_prompt',
    'ACCURACY_VALIDATION_SYSTEM',
    
    # Phase 5
    'get_toc_update_prompt',
    'TOC_UPDATE_SYSTEM',
    
    # Supporting
    'CONTENT_PLACEMENT_SYSTEM',
    'get_content_placement_prompt',
    'TERMINAL_SECTION_SYSTEM',
    'get_terminal_section_prompt',
    'get_content_quality_system',
    'get_content_quality_prompt',
    'INFORMATION_EXTRACTION_SYSTEM',
    'get_information_extraction_prompt'
]
