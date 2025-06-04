"""
Material processor for support materials
"""
from pathlib import Path
from typing import Dict, List, Optional
import logging

from ..extraction import ContentExtractor
from ..prompts import get_material_summary_prompt, MATERIAL_SUMMARY_SYSTEM
from .smart_processor import SmartProcessor

logger = logging.getLogger(__name__)


class MaterialProcessor(SmartProcessor):
    """Process support materials and generate summaries"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extractor = ContentExtractor(self.config)
    
    def _process(self, materials: List[str], repo_path: Path) -> List[Dict]:
        """Process list of materials and return summaries"""
        logger.info(f"MaterialProcessor._process called with {len(materials)} materials: {materials}")
        
        if self.console_display:
            self.console_display.show_operation(f"Processing {len(materials)} support materials")
        
        summaries = []
        for i, material in enumerate(materials, 1):
            if content := self.extractor.extract(material, repo_path):
                if self.console_display:
                    self.console_display.show_operation(f"Analyzing material {i}/{len(materials)}: {Path(material).name}")
                
                if summary := self._summarize(content, material):
                    summaries.append(summary)
        
        logger.info(f"Processed {len(summaries)}/{len(materials)} materials")
        return summaries
    
    def _summarize(self, content: str, source: str) -> Optional[Dict]:
        """Generate summary for material content"""
        prompt = get_material_summary_prompt(source, content)
        system = MATERIAL_SUMMARY_SYSTEM
        
        try:
            # Extract just the filename for cleaner display
            source_name = Path(source).name
            result = self.llm_call(system, prompt, operation_name=f"Material Analysis: {source_name}")
            
            # Display thinking if available
            if self.console_display and 'thinking' in result:
                self.console_display.show_thinking(result['thinking'], f"🤔 AI Thinking - Material Analysis: {source_name}")
            
            # save_interaction is now handled automatically by llm_call
            return result
        except Exception as e:
            logger.error(f"Failed to summarize {source}: {e}")
            return None 