"""
Material content loader for Phase 3 content generation
"""
import logging
from typing import Dict, List
from pathlib import Path

from ..processors.smart_processor import SmartProcessor
from ..extraction import ContentExtractor

logger = logging.getLogger(__name__)


class MaterialContentLoader(SmartProcessor):
    """Load full content of materials for reference during content generation"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extractor = ContentExtractor(self.config)
    
    def _process(self, materials: List[Dict]) -> Dict[str, str]:
        """Load full content of each material file"""
        materials_content = {}
        
        for material in materials:
            source = material.get('source', '')
            if source:
                content = self.extractor.extract(source)
                if content:
                    materials_content[source] = content
                    logger.debug(f"Loaded content for material: {source}")
                else:
                    logger.warning(f"Could not load content for material: {source}")
        
        logger.info(f"Loaded content for {len(materials_content)} materials")
        return materials_content 