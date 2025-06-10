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

logger = logging.getLogger(__name__)


class ContentStrategyProcessor(LLMNativeProcessor):
    """Process chunks and materials to generate content strategy using LLM intelligence"""
    
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
        search_embedding = self._get_embedding(search_text, cache)
        
        # Score all chunks using embeddings
        chunk_scores = self._score_chunks(chunks, search_embedding, cache)
        
        # Aggregate scores by file
        file_relevance = self._aggregate_scores_by_file(chunk_scores, cache)
        
        # Select top 3 files (changed from 10)
        top_files = sorted(file_relevance.items(), 
                          key=lambda x: x[1]['combined_score'], 
                          reverse=True)[:3]
        
        # Reconstruct full file content
        result = []
        for file_path, relevance_info in top_files:
            file_data = self._build_file_data(
                file_path, relevance_info, chunk_scores, chunks
            )
            if file_data:
                result.append(file_data)
        
        logger.info(f"Selected {len(result)} most relevant files for strategy analysis")
        return result
    
    def _score_chunks(self, chunks: List[DocumentChunk], search_embedding: List[float], 
                     cache: UnifiedCache) -> Dict[str, Dict]:
        """Score all chunks using embeddings"""
        chunk_scores = {}
        
        for chunk in chunks:
            chunk_embedding = self._get_chunk_embedding(chunk, cache)
            if chunk_embedding and search_embedding:
                score = self._cosine_similarity(search_embedding, chunk_embedding)
                chunk_scores[chunk.chunk_id] = {
                    'chunk': chunk,
                    'score': score,
                    'file_path': chunk.file_path
                }
        
        return chunk_scores
    
    def _aggregate_scores_by_file(self, chunk_scores: Dict[str, Dict], 
                                 cache: UnifiedCache) -> Dict[str, Dict]:
        """Aggregate chunk scores by file using manifest"""
        file_relevance = {}
        
        # Get all file entries from manifest
        with cache._lock:
            cache.reload_manifest()
            for file_key, entry in cache.manifest.items():
                if 'chunk_ids' in entry:  # This is a file entry
                    file_chunk_ids = entry.get('chunk_ids', [])
                    
                    # Calculate file relevance based on its chunks
                    file_scores = []
                    relevant_chunks = []
                    for chunk_id in file_chunk_ids:
                        if chunk_id in chunk_scores:
                            score = chunk_scores[chunk_id]['score']
                            file_scores.append(score)
                            if score > 0.7:  # Relevance threshold
                                relevant_chunks.append(chunk_id)
                    
                    if file_scores:
                        file_relevance[file_key] = {
                            'max_score': max(file_scores),
                            'avg_score': sum(file_scores) / len(file_scores),
                            'num_relevant_chunks': len(relevant_chunks),
                            'combined_score': max(file_scores) * 0.6 + (sum(file_scores) / len(file_scores)) * 0.4,
                            'chunk_ids': file_chunk_ids,
                            'relevant_chunk_ids': relevant_chunks
                        }
        
        return file_relevance
    
    def _build_file_data(self, file_path: str, relevance_info: Dict, 
                        chunk_scores: Dict[str, Dict], all_chunks: List[DocumentChunk]) -> Dict:
        """Build complete file data including full content"""
        # Get all chunks for this file
        file_chunks = []
        for chunk_id in relevance_info['chunk_ids']:
            if chunk_id in chunk_scores:
                file_chunks.append(chunk_scores[chunk_id]['chunk'])
            else:
                # Try to find chunk in all_chunks if not in scores
                for chunk in all_chunks:
                    if chunk.chunk_id == chunk_id:
                        file_chunks.append(chunk)
                        break
        
        if not file_chunks:
            return None
            
        # Sort chunks by chunk_index to maintain order
        file_chunks.sort(key=lambda c: c.chunk_index)
        
        # Reconstruct full content
        full_content = self._reconstruct_file_content(file_chunks)
        
        # Get file metadata from first chunk
        file_metadata = {
            'title': file_chunks[0].frontmatter.get('title', 'Unknown'),
            'content_type': file_chunks[0].frontmatter.get('ms.topic', 'unknown'),
            'description': file_chunks[0].frontmatter.get('description', '')
        }
        
        # Get most relevant sections
        most_relevant_sections = self._get_most_relevant_sections(
            file_chunks, chunk_scores, relevance_info['relevant_chunk_ids']
        )
        
        return {
            'file': file_path,
            'relevance': {
                'score': relevance_info['combined_score'],
                'max_chunk_score': relevance_info['max_score'],
                'relevant_chunks': relevance_info['num_relevant_chunks']
            },
            'metadata': file_metadata,
            'full_content': full_content,
            'most_relevant_sections': most_relevant_sections
        }
    
    def _reconstruct_file_content(self, file_chunks: List[DocumentChunk]) -> str:
        """Reconstruct full file content from ordered chunks"""
        if not file_chunks:
            return ""
        
        content_parts = []
        
        # Add frontmatter from first chunk
        if file_chunks[0].frontmatter:
            fm_lines = ["---"]
            for key, value in file_chunks[0].frontmatter.items():
                if isinstance(value, str):
                    # Handle multiline strings
                    if '\n' in value:
                        fm_lines.append(f'{key}: |')
                        for line in value.split('\n'):
                            fm_lines.append(f'  {line}')
                    else:
                        fm_lines.append(f"{key}: {value}")
                else:
                    fm_lines.append(f"{key}: {value}")
            fm_lines.append("---\n")
            content_parts.append('\n'.join(fm_lines))
        
        # Add all chunk contents in order
        for chunk in file_chunks:
            content_parts.append(chunk.content)
        
        return '\n'.join(content_parts)
    
    def _get_most_relevant_sections(self, file_chunks: List[DocumentChunk], 
                                   chunk_scores: Dict[str, Dict], 
                                   relevant_chunk_ids: List[str]) -> List[Dict]:
        """Get the most relevant sections within a file"""
        relevant_sections = []
        
        for chunk_id in relevant_chunk_ids[:5]:  # Top 5 relevant sections
            if chunk_id in chunk_scores:
                chunk = chunk_scores[chunk_id]['chunk']
                score = chunk_scores[chunk_id]['score']
                
                section_path = ' > '.join(chunk.heading_path) if chunk.heading_path else 'Main Content'
                
                relevant_sections.append({
                    'heading': section_path,
                    'score': score,
                    'preview': chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content
                })
        
        return sorted(relevant_sections, key=lambda x: x['score'], reverse=True)
    
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
    
    def _load_content_standards(self) -> Dict:
        """Load content standards from JSON file"""
        standards_path = Path('content_standards.json')
        if standards_path.exists():
            try:
                with open(standards_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load content standards: {e}")
                # Return minimal fallback
                return {
                    "contentTypes": [
                        {"name": "Overview", "id": "overview", "purpose": "High-level introduction", "description": "Use for introductions"},
                        {"name": "Concept", "id": "concept", "purpose": "Deep technical explanation", "description": "Use for concepts"},
                        {"name": "Quickstart", "id": "quickstart", "purpose": "Get started quickly", "description": "Use for quickstarts"},
                        {"name": "How-To Guide", "id": "howto", "purpose": "Step-by-step instructions", "description": "Use for how-to guides"},
                        {"name": "Tutorial", "id": "tutorial", "purpose": "End-to-end learning", "description": "Use for tutorials"}
                    ]
                }
        else:
            logger.warning("content_standards.json not found, using fallback")
            # Return minimal fallback with id fields
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
        
        # Parse decisions with new format
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
        
        # Build strategy object
        strategy = ContentStrategy(
            thinking=result.get('thinking', ''),
            decisions=parsed_decisions,
            confidence=result.get('confidence', 0.85),
            summary=result.get('summary', '')
        )
        
        # Add debug info if available
        if self.config.debug_similarity:
            strategy.debug_info = {
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
        
        return strategy
    
    def _format_materials_summary(self, materials: List[Dict]) -> str:
        """Format materials list into a comprehensive display with full content"""
        if not materials:
            return "No materials provided"
        
        summary_parts = []
        for i, material in enumerate(materials, 1):
            summary_parts.append(f"=== MATERIAL {i} ===")
            summary_parts.append(f"Source: {material.get('source', 'Unknown')}")
            summary_parts.append(f"Topic: {material.get('main_topic', 'N/A')}")
            summary_parts.append(f"Type: {material.get('document_type', 'N/A')}")
            summary_parts.append(f"Summary: {material.get('summary', 'N/A')}")
            
            # Add key concepts and technologies
            if concepts := material.get('key_concepts'):
                summary_parts.append(f"Key Concepts: {', '.join(concepts[:5])}")
            if techs := material.get('technologies'):
                summary_parts.append(f"Technologies: {', '.join(techs[:5])}")
            
            # Add full content if available - NO TRUNCATION
            if full_content := material.get('full_content'):
                summary_parts.append("\nFULL CONTENT:")
                summary_parts.append("-" * 80)
                summary_parts.append(full_content)
                summary_parts.append("-" * 80)
            
            summary_parts.append("")  # Empty line between materials
        
        return "\n".join(summary_parts) 