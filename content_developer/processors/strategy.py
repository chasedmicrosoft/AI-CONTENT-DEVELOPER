"""
Content strategy processor using LLM-native approach
"""
from pathlib import Path
from typing import Dict, List
import logging

from ..cache import UnifiedCache
from ..models import Config, ContentStrategy, DocumentChunk
from ..utils import get_hash
from ..prompts import (
    get_unified_content_strategy_prompt,
    UNIFIED_CONTENT_STRATEGY_SYSTEM
)
from .llm_native_processor import LLMNativeProcessor

logger = logging.getLogger(__name__)


class ContentStrategyProcessor(LLMNativeProcessor):
    """Process chunks and materials to generate content strategy using LLM intelligence"""
    
    def _process(self, chunks: List[DocumentChunk], materials: List[Dict], config: Config, 
                 repo_name: str, working_directory: str) -> ContentStrategy:
        """Process content strategy generation using LLM-native approach with integrated analysis"""
        
        # Get relevant chunks to analyze
        chunks_to_analyze = self._get_chunks_to_analyze(
            chunks, materials, config, repo_name, working_directory
        )
        
        # Generate strategy with integrated intent understanding and chunk ranking
        strategy = self._generate_unified_strategy(config, materials, chunks_to_analyze)
        
        return strategy
    
    def _get_chunks_to_analyze(self, chunks: List[DocumentChunk], materials: List[Dict], 
                              config: Config, repo_name: str, working_directory: str) -> List[DocumentChunk]:
        """Get chunks to analyze - either all for small sets or filtered by embeddings for large sets"""
        if not chunks:
            return []
        
        # For small sets, analyze all chunks directly
        if len(chunks) <= 30:
            logger.info(f"Analyzing all {len(chunks)} chunks directly")
            return chunks
        
        # For larger sets, use embeddings as initial filter
        logger.info(f"Using embeddings to filter {len(chunks)} chunks to top 30")
        cache_dir = Path(f"./llm_outputs/embeddings/{repo_name}/{working_directory}")
        cache = UnifiedCache(cache_dir)
        
        # Create search embedding from materials and goal
        search_text = self._create_search_text(materials, config)
        search_embedding = self._get_embedding(search_text, cache)
        
        # Get top candidates using embeddings
        candidates = self._get_embedding_candidates(chunks, search_embedding, cache, limit=30)
        
        return candidates
    
    def _create_search_text(self, materials: List[Dict], config: Config) -> str:
        """Create search text from materials and goal"""
        parts = [
            f"Goal: {config.content_goal}",
            f"Target audience: {config.audience}",
            f"Service area: {config.service_area}"
        ]
        
        # Add material topics
        topics = set()
        for material in materials:
            if topic := material.get('main_topic'):
                topics.add(topic)
            # Add key concepts too
            if concepts := material.get('key_concepts'):
                if isinstance(concepts, list):
                    topics.update(concepts[:3])  # Top 3 concepts
        
        if topics:
            parts.append(f"Key topics: {', '.join(topics)}")
        
        return " | ".join(parts)
    
    def _get_embedding_candidates(self, chunks: List[DocumentChunk], search_embedding: List[float],
                                 cache: UnifiedCache, limit: int = 30) -> List[DocumentChunk]:
        """Get initial candidates using embedding similarity"""
        if not search_embedding:
            return chunks[:limit]
        
        # Calculate similarities
        chunk_scores = []
        for chunk in chunks:
            chunk_embedding = self._get_chunk_embedding(chunk, cache)
            if chunk_embedding:
                score = self._cosine_similarity(search_embedding, chunk_embedding)
                chunk_scores.append((chunk, score))
        
        # Sort by score and return top candidates
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in chunk_scores[:limit]]
    
    def _get_embedding(self, text: str, cache: UnifiedCache) -> List[float]:
        """Get embedding for text with caching"""
        cache_key = f"intent_{get_hash(text)}"
        
        # Try to get from cache
        if cached_data := cache.get(cache_key):
            if embedding := cached_data.get('data'):
                return self._ensure_float_list(embedding)
        
        try:
            response = self.client.embeddings.create(
                model=self.config.embedding_model,
                input=text
            )
            embedding = response.data[0].embedding
            # Save to cache
            cache.put(cache_key, embedding, meta={'type': 'intent_embedding'})
            return embedding
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return []
    
    def _get_chunk_embedding(self, chunk: DocumentChunk, cache: UnifiedCache) -> List[float]:
        """Get or compute embedding for a chunk"""
        if chunk.embedding:
            return self._ensure_float_list(chunk.embedding)
        
        # Try to get from cache
        cache_key = f"chunk_{chunk.chunk_id}"
        if cached_data := cache.get(cache_key):
            if embedding := cached_data.get('data'):
                return self._ensure_float_list(embedding)
        
        # Generate embedding
        embedding_text = self._create_chunk_embedding_text(chunk)
        return self._get_embedding(embedding_text, cache)
    
    def _create_chunk_embedding_text(self, chunk: DocumentChunk) -> str:
        """Create text for chunk embedding"""
        parts = []
        
        # Add document metadata
        if chunk.frontmatter:
            if title := chunk.frontmatter.get('title'):
                parts.append(f"Document: {title}")
            if topic := chunk.frontmatter.get('ms.topic'):
                parts.append(f"Topic: {topic}")
            if desc := chunk.frontmatter.get('description'):
                parts.append(f"Description: {desc}")
        
        # Add section context
        if chunk.heading_path:
            parts.append(f"Section: {' > '.join(chunk.heading_path)}")
        
        # Add content
        parts.append(chunk.content)
        
        return " | ".join(parts)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _generate_unified_strategy(self, config: Config, materials: List[Dict], 
                                  chunks_to_analyze: List[DocumentChunk]) -> ContentStrategy:
        """Generate content strategy with integrated intent understanding and chunk ranking"""
        if self.console_display:
            self.console_display.show_operation("Generating comprehensive content strategy")
        
        # Create a minimal content standards object
        content_standards = {
            "contentTypes": [
                {
                    "name": "Overview", 
                    "frontMatter": {"ms.topic": "overview"},
                    "purpose": "High-level introduction to a feature or service",
                    "description": "Use when introducing new concepts or services"
                },
                {
                    "name": "Concept", 
                    "frontMatter": {"ms.topic": "concept"},
                    "purpose": "Deep technical explanation",
                    "description": "Use for architectural or theoretical content"
                },
                {
                    "name": "Quickstart", 
                    "frontMatter": {"ms.topic": "quickstart"},
                    "purpose": "Get users started in under 10 minutes",
                    "description": "Use for simple getting started guides"
                },
                {
                    "name": "How-To Guide", 
                    "frontMatter": {"ms.topic": "how-to"},
                    "purpose": "Step-by-step task completion",
                    "description": "Use for specific task instructions"
                },
                {
                    "name": "Tutorial", 
                    "frontMatter": {"ms.topic": "tutorial"},
                    "purpose": "End-to-end learning experience",
                    "description": "Use for comprehensive walkthroughs"
                }
            ]
        }
        
        # Format materials into a summary string
        materials_summary = self._format_materials_summary(materials)
        
        # Convert DocumentChunks to dictionaries for prompt formatting
        chunks_as_dicts = []
        for chunk in chunks_to_analyze:
            chunks_as_dicts.append({
                'file': chunk.file_path,
                'content_type': chunk.frontmatter.get('ms.topic', 'unknown') if chunk.frontmatter else 'unknown',
                'ms_topic': chunk.frontmatter.get('ms.topic', 'unknown') if chunk.frontmatter else 'unknown',
                'chunk_id': chunk.chunk_id,
                'section': ' > '.join(chunk.heading_path) if chunk.heading_path else 'Main',
                'content_preview': chunk.content[:200] if chunk.content else ''
            })
        
        # Create the unified prompt
        user_prompt = get_unified_content_strategy_prompt(
            config, materials_summary, chunks_as_dicts, content_standards
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
        
        # Build strategy object
        strategy = ContentStrategy(
            thinking=result.get('thinking', ''),
            decisions=result.get('decisions', []),
            confidence=result.get('confidence', 0.85),
            summary=result.get('summary', '')
        )
        
        # Add debug info if available
        if self.config.debug_similarity:
            strategy.debug_info = {
                'intent_analysis': result.get('intent_analysis', {}),
                'chunk_relevance': result.get('chunk_relevance', []),
                'chunks_analyzed': len(chunks_to_analyze),
                'similar_chunks': [
                    {'file': c.file_path, 'section': c.heading_path} 
                    for c in chunks_to_analyze[:10]
                ]
            }
        
        return strategy 
    
    def _format_materials_summary(self, materials: List[Dict]) -> str:
        """Format materials list into a summary string"""
        if not materials:
            return "No materials provided"
        
        summary_parts = []
        for i, material in enumerate(materials, 1):
            summary_parts.append(f"Material {i}: {material.get('source', 'Unknown')}")
            summary_parts.append(f"  Topic: {material.get('main_topic', 'N/A')}")
            summary_parts.append(f"  Type: {material.get('document_type', 'N/A')}")
            summary_parts.append(f"  Summary: {material.get('summary', 'N/A')}")
            summary_parts.append("")
        
        return "\n".join(summary_parts) 