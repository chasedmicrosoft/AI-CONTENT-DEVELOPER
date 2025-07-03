"""
Content strategy processor using LLM-native approach
"""
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import json

from ..cache import UnifiedCache
from ..models import Config, ContentStrategy, DocumentChunk, ContentDecision
from ..utils import get_hash
from ..prompts import (
    get_unified_content_strategy_prompt,
    UNIFIED_CONTENT_STRATEGY_SYSTEM
)
from .llm_native_processor import LLMNativeProcessor
from .strategy_helpers import EmbeddingHelper, FileRelevanceScorer, FileContentBuilder

logger = logging.getLogger(__name__)


class ContentStrategyProcessor(LLMNativeProcessor):
    """Process chunks and materials to generate content strategy using LLM intelligence"""
    
    def __init__(self, client, config: Config, console_display=None):
        """Initialize with client and config"""
        super().__init__(client, config, console_display)
        self.embedding_helper = EmbeddingHelper(client, config)
        self.file_scorer = FileRelevanceScorer(self.embedding_helper)
        self.file_builder = FileContentBuilder()
    
    def _process(self, chunks: List[DocumentChunk], materials: List[Dict], config: Config, 
                 repo_name: str, working_directory: str) -> ContentStrategy:
        """Process content strategy generation using LLM-native approach with file-based analysis"""
        
        # Get relevant files with full content
        relevant_files = self._get_relevant_files_with_content(
            chunks, materials, config, repo_name, working_directory
        )
        
        # Generate strategy with file-based analysis
        strategy = self._generate_unified_strategy(config, materials, relevant_files)
        
        return strategy
    
    def _get_relevant_files_with_content(self, chunks: List[DocumentChunk], materials: List[Dict], 
                                       config: Config, repo_name: str, working_directory: str) -> List[Dict]:
        """Get most relevant files with their full content using embeddings and manifest"""
        if not chunks:
            return []
        
        # Setup cache
        cache_dir = Path(f"./llm_outputs/embeddings/{repo_name}/{working_directory}")
        cache = UnifiedCache(cache_dir)
        
        # Create search embedding from materials and goal
        search_text = self._create_search_text(materials, config)
        search_embedding = self.embedding_helper.get_embedding(search_text, cache)
        
        # Score all chunks using embeddings
        chunk_scores = self.file_scorer.score_chunks(chunks, search_embedding, cache)
        
        # Aggregate scores by file
        file_relevance = self.file_scorer.aggregate_scores_by_file(chunk_scores, cache)
        
        # Select top 3 files (changed from 10)
        top_files = sorted(file_relevance.items(), 
                          key=lambda x: x[1]['combined_score'], 
                          reverse=True)[:3]
        
        # Reconstruct full file content
        result = []
        for file_path, relevance_info in top_files:
            file_data = self.file_builder.build_file_data(
                file_path, relevance_info, chunk_scores, chunks
            )
            if file_data:
                result.append(file_data)
        
        logger.info(f"Selected {len(result)} most relevant files for strategy analysis")
        return result
    
    def _create_search_text(self, materials: List[Dict], config: Config) -> str:
        """Create search text from materials and goal"""
        parts = [
            f"Goal: {config.content_goal}",
            f"Target audience: {config.audience}",
            f"Service area: {config.service_area}"
        ]
        
        # Add material topics and key concepts
        topics = set()
        concepts = set()
        for material in materials:
            if topic := material.get('main_topic'):
                topics.add(topic)
            if material_concepts := material.get('key_concepts'):
                if isinstance(material_concepts, list):
                    concepts.update(material_concepts[:5])
        
        if topics:
            parts.append(f"Key topics: {', '.join(topics)}")
        if concepts:
            parts.append(f"Key concepts: {', '.join(list(concepts)[:10])}")
        
        return " | ".join(parts)
    
    def _load_content_standards(self) -> Dict:
        """Load content standards from JSON file"""
        standards_path = Path('content_standards.json')
        if standards_path.exists():
            try:
                with open(standards_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load content standards: {e}")
                return self._get_fallback_standards()
        else:
            logger.warning("content_standards.json not found, using fallback")
            return self._get_fallback_standards()
    
    def _get_fallback_standards(self) -> Dict:
        """Get fallback content standards"""
        return {
            "contentTypes": [
                {"name": "Overview", "id": "overview", "purpose": "High-level introduction", "description": "Use for introductions"},
                {"name": "Concept", "id": "concept", "purpose": "Deep technical explanation", "description": "Use for concepts"},
                {"name": "Quickstart", "id": "quickstart", "purpose": "Get started quickly", "description": "Use for quickstarts"},
                {"name": "How-To Guide", "id": "howto", "purpose": "Step-by-step instructions", "description": "Use for how-to guides"},
                {"name": "Tutorial", "id": "tutorial", "purpose": "End-to-end learning", "description": "Use for tutorials"}
            ]
        }
    
    def _generate_unified_strategy(self, config: Config, materials: List[Dict], 
                                  relevant_files: List[Dict]) -> ContentStrategy:
        """Generate content strategy with file-based analysis"""
        if self.console_display:
            self.console_display.show_operation("Generating comprehensive content strategy")
        
        # Load actual content standards from JSON file
        content_standards = self._load_content_standards()
        
        # Format materials into a summary string
        materials_summary = self._format_materials_summary(materials)
        
        # Create the unified prompt with relevant files
        user_prompt = get_unified_content_strategy_prompt(
            config, materials_summary, relevant_files, content_standards
        )
        
        # Call LLM
        messages = [
            {"role": "system", "content": UNIFIED_CONTENT_STRATEGY_SYSTEM},
            {"role": "user", "content": user_prompt}
        ]
        
        result = self._call_llm(
            messages, 
            model=self.config.completion_model,
            response_format="json_object",
            operation_name="Unified Strategy Generation"
        )
        
        # Extract thinking if available for console display
        if self.console_display and 'thinking' in result:
            self.console_display.show_thinking(result['thinking'], "🤔 AI Thinking - Strategy Development")
        
        # Parse decisions
        parsed_decisions = self._parse_decisions(result)
        
        # Build strategy object
        strategy = ContentStrategy(
            thinking=result.get('thinking', ''),
            decisions=parsed_decisions,
            confidence=result.get('confidence', 0.85),
            summary=result.get('summary', '')
        )
        
        # Add debug info if available
        if self.config.debug_similarity:
            strategy.debug_info = self._build_debug_info(relevant_files)
        
        return strategy
    
    def _parse_decisions(self, result: Dict) -> List[ContentDecision]:
        """Parse decisions from LLM result"""
        parsed_decisions = []
        
        for i, decision_data in enumerate(result.get('decisions', [])):
            # Validate target_file is present and not null
            target_file = decision_data.get('target_file')
            if not target_file or target_file.strip() == "":
                logger.error(f"Decision {i+1} has null or empty target_file: {decision_data}")
                raise ValueError(f"Decision {i+1} is missing required target_file field. Action: {decision_data.get('action')}")
            
            # Create ContentDecision with new format
            decision = ContentDecision(
                action=decision_data.get('action', 'CREATE'),
                target_file=target_file.strip(),
                file_title=decision_data.get('file_title', ''),
                content_type=decision_data.get('content_type', 'concept'),
                sections=decision_data.get('sections', []),
                rationale=decision_data.get('rationale', ''),
                priority=decision_data.get('priority', 'medium'),
                aligns_with_goal=decision_data.get('aligns_with_goal', True),
                prerequisites=decision_data.get('prerequisites', []),
                technologies=decision_data.get('technologies', [])
            )
            
            # For backward compatibility, also set legacy fields
            if decision.action != "SKIP":
                decision.filename = decision.target_file
                decision.reason = decision.rationale
                decision.ms_topic = decision.content_type
            
            parsed_decisions.append(decision)
        
        return parsed_decisions
    
    def _build_debug_info(self, relevant_files: List[Dict]) -> Dict:
        """Build debug information"""
        return {
            'files_analyzed': len(relevant_files),
            'relevant_files': [
                {
                    'file': f['file'], 
                    'score': f['relevance']['score'],
                    'type': f['metadata']['content_type']
                } 
                for f in relevant_files
            ]
        }
    
    def _format_materials_summary(self, materials: List[Dict]) -> str:
        """Format materials list into a comprehensive display with full content"""
        if not materials:
            return "No materials provided"
        
        summary_parts = []
        for i, material in enumerate(materials, 1):
            summary_parts.extend(self._format_single_material(i, material))
        
        return "\n".join(summary_parts)
    
    def _format_single_material(self, index: int, material: Dict) -> List[str]:
        """Format a single material entry"""
        parts = [
            f"=== MATERIAL {index} ===",
            f"Source: {material.get('source', 'Unknown')}",
            f"Topic: {material.get('main_topic', 'N/A')}",
            f"Type: {material.get('document_type', 'N/A')}",
            f"Summary: {material.get('summary', 'N/A')}"
        ]
        
        # Add key concepts and technologies
        if concepts := material.get('key_concepts'):
            parts.append(f"Key Concepts: {', '.join(concepts[:5])}")
        if techs := material.get('technologies'):
            parts.append(f"Technologies: {', '.join(techs[:5])}")
        
        # Add full content if available - NO TRUNCATION
        if full_content := material.get('full_content'):
            parts.extend([
                "\nFULL CONTENT:",
                "-" * 80,
                full_content,
                "-" * 80
            ])
        
        parts.append("")  # Empty line between materials
        return parts 