"""
Helper classes for content strategy processing.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ..cache import UnifiedCache
from ..models import DocumentChunk
from ..utils import get_hash

logger = logging.getLogger(__name__)


class EmbeddingHelper:
    """Handles embedding operations with caching"""
    
    def __init__(self, client, config):
        self.client = client
        self.config = config
    
    def get_embedding(self, text: str, cache: UnifiedCache, cache_prefix: str = "intent") -> List[float]:
        """Get embedding for text with caching"""
        cache_key = f"{cache_prefix}_{get_hash(text)}"
        
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
            cache.put(cache_key, embedding, meta={'type': f'{cache_prefix}_embedding'})
            return embedding
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return []
    
    def get_chunk_embedding(self, chunk: DocumentChunk, cache: UnifiedCache) -> List[float]:
        """Get or compute embedding for a chunk"""
        if chunk.embedding:
            logger.debug(f"Using embedding from chunk object for {chunk.chunk_id}")
            return self._ensure_float_list(chunk.embedding)
        
        # Try to get from cache
        cache_key = f"chunk_{chunk.chunk_id}"
        if cached_data := cache.get(cache_key):
            # For chunk data, embedding is nested inside the data object
            if data := cached_data.get('data'):
                if isinstance(data, dict) and 'embedding' in data:
                    # This is a chunk with nested structure
                    if embedding := data.get('embedding'):
                        logger.debug(f"Found cached embedding for chunk {chunk.chunk_id}")
                        return self._ensure_float_list(embedding)
                elif isinstance(data, list):
                    # This is a direct embedding array (shouldn't happen for chunks)
                    logger.warning(f"Found direct embedding array for chunk {chunk.chunk_id} - this shouldn't happen")
                    return self._ensure_float_list(data)
        
        # Generate embedding
        logger.info(f"Generating new embedding for chunk {chunk.chunk_id}")
        embedding_text = self.create_chunk_embedding_text(chunk)
        
        # Generate the embedding
        try:
            response = self.client.embeddings.create(
                model=self.config.embedding_model,
                input=embedding_text
            )
            embedding = response.data[0].embedding
            
            # For chunks, we need to update the existing chunk data in cache
            cache_key = f"chunk_{chunk.chunk_id}"
            if cached_data := cache.get(cache_key):
                if data := cached_data.get('data'):
                    if isinstance(data, dict):
                        # Update the existing chunk data with the embedding
                        data['embedding'] = embedding
                        data['embedding_model'] = self.config.embedding_model
                        data['embedding_generated_at'] = datetime.now().isoformat()
                        
                        # Save the updated chunk data back to cache
                        cache.put(cache_key, data, cached_data.get('meta', {}))
                        
                        return self._ensure_float_list(embedding)
            
            # If no existing chunk data, just return the embedding
            # (This shouldn't normally happen for chunks)
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to create embedding for chunk: {e}")
            return []
    
    @staticmethod
    def create_chunk_embedding_text(chunk: DocumentChunk) -> str:
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
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    @staticmethod
    def _ensure_float_list(embedding: List) -> List[float]:
        """Ensure embedding is a list of floats"""
        return [float(x) for x in embedding]


class FileRelevanceScorer:
    """Scores files based on chunk relevance"""
    
    def __init__(self, embedding_helper: EmbeddingHelper):
        self.embedding_helper = embedding_helper
    
    def score_chunks(self, chunks: List[DocumentChunk], search_embedding: List[float], 
                    cache: UnifiedCache) -> Dict[str, Dict]:
        """Score all chunks using embeddings"""
        chunk_scores = {}
        
        for chunk in chunks:
            chunk_embedding = self.embedding_helper.get_chunk_embedding(chunk, cache)
            if chunk_embedding and search_embedding:
                score = self.embedding_helper.cosine_similarity(search_embedding, chunk_embedding)
                chunk_scores[chunk.chunk_id] = {
                    'chunk': chunk,
                    'score': score,
                    'file_path': chunk.file_path
                }
        
        return chunk_scores
    
    def aggregate_scores_by_file(self, chunk_scores: Dict[str, Dict], 
                                cache: UnifiedCache) -> Dict[str, Dict]:
        """Aggregate chunk scores by file using manifest"""
        file_relevance = {}
        
        # Get all file entries from manifest
        with cache._lock:
            cache.reload_manifest()
            for file_key, entry in cache.manifest.items():
                if 'chunk_ids' not in entry:
                    continue
                
                file_chunk_ids = entry.get('chunk_ids', [])
                file_scores, relevant_chunks = self._calculate_file_scores(
                    file_chunk_ids, chunk_scores
                )
                
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
    
    @staticmethod
    def _calculate_file_scores(file_chunk_ids: List[str], 
                              chunk_scores: Dict[str, Dict]) -> Tuple[List[float], List[str]]:
        """Calculate scores for a file's chunks"""
        file_scores = []
        relevant_chunks = []
        
        for chunk_id in file_chunk_ids:
            if chunk_id in chunk_scores:
                score = chunk_scores[chunk_id]['score']
                file_scores.append(score)
                if score > 0.7:  # Relevance threshold
                    relevant_chunks.append(chunk_id)
        
        return file_scores, relevant_chunks


class FileContentBuilder:
    """Builds complete file data including reconstruction"""
    
    @staticmethod
    def build_file_data(file_path: str, relevance_info: Dict, 
                       chunk_scores: Dict[str, Dict], all_chunks: List[DocumentChunk]) -> Optional[Dict]:
        """Build complete file data including full content"""
        # Get all chunks for this file
        file_chunks = FileContentBuilder._collect_file_chunks(
            relevance_info['chunk_ids'], chunk_scores, all_chunks
        )
        
        if not file_chunks:
            return None
        
        # Sort chunks by chunk_index to maintain order
        file_chunks.sort(key=lambda c: c.chunk_index)
        
        # Build file data
        return {
            'file': file_path,
            'relevance': {
                'score': relevance_info['combined_score'],
                'max_chunk_score': relevance_info['max_score'],
                'relevant_chunks': relevance_info['num_relevant_chunks']
            },
            'metadata': FileContentBuilder._extract_file_metadata(file_chunks[0]),
            'full_content': FileContentBuilder.reconstruct_file_content(file_chunks),
            'most_relevant_sections': FileContentBuilder._get_most_relevant_sections(
                file_chunks, chunk_scores, relevance_info['relevant_chunk_ids']
            )
        }
    
    @staticmethod
    def _collect_file_chunks(chunk_ids: List[str], chunk_scores: Dict[str, Dict], 
                           all_chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Collect all chunks for a file"""
        file_chunks = []
        
        for chunk_id in chunk_ids:
            if chunk_id in chunk_scores:
                file_chunks.append(chunk_scores[chunk_id]['chunk'])
            else:
                # Try to find chunk in all_chunks if not in scores
                for chunk in all_chunks:
                    if chunk.chunk_id == chunk_id:
                        file_chunks.append(chunk)
                        break
        
        return file_chunks
    
    @staticmethod
    def _extract_file_metadata(first_chunk: DocumentChunk) -> Dict:
        """Extract metadata from the first chunk of a file"""
        return {
            'title': first_chunk.frontmatter.get('title', 'Unknown'),
            'content_type': first_chunk.frontmatter.get('ms.topic', 'unknown'),
            'description': first_chunk.frontmatter.get('description', '')
        }
    
    @staticmethod
    def reconstruct_file_content(file_chunks: List[DocumentChunk]) -> str:
        """Reconstruct full file content from ordered chunks"""
        if not file_chunks:
            return ""
        
        content_parts = []
        
        # Add frontmatter from first chunk
        if file_chunks[0].frontmatter:
            content_parts.append(FileContentBuilder._format_frontmatter(file_chunks[0].frontmatter))
        
        # Add all chunk contents in order
        for chunk in file_chunks:
            content_parts.append(chunk.content)
        
        return '\n'.join(content_parts)
    
    @staticmethod
    def _format_frontmatter(frontmatter: Dict) -> str:
        """Format frontmatter into YAML"""
        fm_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, str) and '\n' in value:
                fm_lines.append(f'{key}: |')
                for line in value.split('\n'):
                    fm_lines.append(f'  {line}')
            else:
                fm_lines.append(f"{key}: {value}")
        fm_lines.append("---\n")
        return '\n'.join(fm_lines)
    
    @staticmethod
    def _get_most_relevant_sections(file_chunks: List[DocumentChunk], 
                                  chunk_scores: Dict[str, Dict], 
                                  relevant_chunk_ids: List[str]) -> List[Dict]:
        """Get the most relevant sections within a file"""
        relevant_sections = []
        
        for chunk_id in relevant_chunk_ids[:5]:  # Top 5 relevant sections
            if chunk_id not in chunk_scores:
                continue
            
            chunk = chunk_scores[chunk_id]['chunk']
            score = chunk_scores[chunk_id]['score']
            
            section_path = ' > '.join(chunk.heading_path) if chunk.heading_path else 'Main Content'
            preview = chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content
            
            relevant_sections.append({
                'heading': section_path,
                'score': score,
                'preview': preview
            })
        
        return sorted(relevant_sections, key=lambda x: x['score'], reverse=True) 