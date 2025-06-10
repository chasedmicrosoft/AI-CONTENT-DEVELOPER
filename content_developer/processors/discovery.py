"""
Content discovery and chunking processor
"""
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict
import logging

from ..cache import UnifiedCache
from ..models import Config, DocumentChunk
from ..utils import file_get_hash
from ..chunking import SmartChunker
from .smart_processor import SmartProcessor

logger = logging.getLogger(__name__)


class ContentDiscoveryProcessor(SmartProcessor):
    """Discover and chunk content in the repository"""
    
    def _process(self, working_dir: Path, repo_name: str, working_directory: str) -> List[DocumentChunk]:
        """Process content discovery"""
        logger.info(f"Starting content discovery in {working_dir}")
        cache_dir = Path(f"./llm_outputs/embeddings/{repo_name}/{working_directory}")
        cache = UnifiedCache(cache_dir)
        
        # Cleanup orphaned chunks from manifest
        logger.info("Verifying and cleaning up cache manifest...")
        cache.verify_and_cleanup_manifest()
        
        # Find all markdown files
        markdown_files = self._find_markdown_files(working_dir)
        logger.info(f"Found {len(markdown_files)} markdown files")
        
        # Process files and generate chunks
        all_chunks = self._process_markdown_files(markdown_files, cache)
        
        # Generate embeddings if missing
        self._generate_missing_embeddings(all_chunks, cache)
        
        logger.info(f"Content discovery complete: {len(all_chunks)} chunks")
        return all_chunks
    
    def _find_markdown_files(self, working_dir: Path) -> List[Path]:
        """Find all markdown files in directory"""
        return list(working_dir.rglob("*.md"))
    
    def _process_markdown_files(self, markdown_files: List[Path], cache: UnifiedCache) -> List[DocumentChunk]:
        """Process markdown files with intelligent caching"""
        ProcessResult = namedtuple('ProcessResult', ['file_path', 'chunks', 'needs_update'])
        
        # Check which files need updates
        files_to_process = []
        cached_chunks = []
        
        for md_file in markdown_files:
            file_hash = file_get_hash(md_file)
            file_key = str(md_file)
            
            # Check if file needs update
            if cache.needs_update(file_key, file_hash):
                files_to_process.append(md_file)
            else:
                # Load from cache
                chunks = self._load_chunks_from_cache(md_file, cache)
                if chunks:
                    cached_chunks.extend(chunks)
                else:
                    # Cache corrupted, reprocess
                    files_to_process.append(md_file)
        
        logger.info(f"Files to process: {len(files_to_process)}, cached: {len(markdown_files) - len(files_to_process)}")
        
        # Process files that need updates
        if files_to_process:
            new_chunks = self._process_files_parallel(files_to_process, cache)
            return cached_chunks + new_chunks
        
        return cached_chunks
    
    def _load_chunks_from_cache(self, md_file: Path, cache: UnifiedCache) -> List[DocumentChunk]:
        """Load chunks from cache for a file"""
        file_key = str(md_file)
        manifest_entry = cache.get_manifest_entry(file_key)
        
        if not manifest_entry:
            return []
        
        chunks = []
        chunk_ids = manifest_entry.get('chunk_ids', [])
        
        for chunk_id in chunk_ids:
            cached_data = cache.get(chunk_id)
            if cached_data and 'data' in cached_data:
                # Get unified chunk data
                chunk_data = cached_data['data']
                
                # Defensive check: ensure chunk_data is a dictionary with expected structure
                if not isinstance(chunk_data, dict) or 'content' not in chunk_data:
                    logger.warning(f"Invalid chunk data structure for {chunk_id}. Skipping.")
                    continue
                
                try:
                    chunk = DocumentChunk(
                        content=chunk_data.get('content', ''),
                        file_path=chunk_data.get('file_path', ''),
                        heading_path=chunk_data.get('heading_path', []),
                        section_level=chunk_data.get('section_level', 0),
                        chunk_index=chunk_data.get('chunk_index', 0),
                        frontmatter=chunk_data.get('frontmatter', {}),
                        embedding_content=chunk_data.get('embedding_content', ''),
                        embedding=chunk_data.get('embedding'),  # Load existing embedding if present
                        content_hash=chunk_data.get('content_hash'),
                        file_id=chunk_data.get('file_id', ''),
                        chunk_id=chunk_data.get('chunk_id', ''),
                        prev_chunk_id=chunk_data.get('prev_chunk_id'),
                        next_chunk_id=chunk_data.get('next_chunk_id'),
                        parent_heading_chunk_id=chunk_data.get('parent_heading_chunk_id'),
                        total_chunks_in_file=chunk_data.get('total_chunks_in_file', 0)
                    )
                    chunks.append(chunk)
                except Exception as e:
                    logger.error(f"Failed to create DocumentChunk from cache for {chunk_id}: {e}")
                    continue
        
        return chunks
    
    def _process_files_parallel(self, files_to_process: List[Path], 
                               cache: UnifiedCache) -> List[DocumentChunk]:
        """Process multiple files in parallel"""
        all_chunks = []
        chunker = SmartChunker()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(self._process_single_file, md_file, chunker, cache): md_file
                for md_file in files_to_process
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                md_file = future_to_file[future]
                try:
                    chunks = future.result()
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Failed to process {md_file}: {e}")
        
        return all_chunks
    
    def _process_single_file(self, md_file: Path, chunker: SmartChunker, 
                            cache: UnifiedCache) -> List[DocumentChunk]:
        """Process a single markdown file"""
        logger.info(f"Processing {md_file}")
        
        # Chunk the file
        chunks = chunker.chunk_markdown(md_file, cache)
        
        # Store chunks in cache
        chunk_ids = self._store_chunks_in_cache(chunks, cache)
        
        # Update manifest
        self._update_file_manifest(md_file, chunk_ids, cache)
        
        return chunks
    
    def _store_chunks_in_cache(self, chunks: List[DocumentChunk], cache: UnifiedCache) -> List[str]:
        """Store chunks in cache and return their IDs"""
        chunk_ids = []
        
        for chunk in chunks:
            # Prepare unified data structure
            unified_data = {
                'content': chunk.content,
                'file_path': chunk.file_path,
                'heading_path': chunk.heading_path,
                'section_level': chunk.section_level,
                'chunk_index': chunk.chunk_index,
                'frontmatter': chunk.frontmatter,
                'embedding_content': chunk.embedding_content,
                'embedding': chunk.embedding,  # Will be None initially
                'embedding_model': None,  # Will be set when embedding is generated
                'embedding_generated_at': None,  # Will be set when embedding is generated
                'content_hash': chunk.content_hash,
                'file_id': chunk.file_id,
                'chunk_id': chunk.chunk_id,
                'prev_chunk_id': chunk.prev_chunk_id,
                'next_chunk_id': chunk.next_chunk_id,
                'parent_heading_chunk_id': chunk.parent_heading_chunk_id,
                'total_chunks_in_file': chunk.total_chunks_in_file
            }
            
            # Store with metadata
            cache.put(chunk.chunk_id, unified_data, {
                'type': 'chunk',
                'file': chunk.file_path,
                'section': chunk.heading_path,
                'has_embedding': chunk.embedding is not None
            })
            chunk_ids.append(chunk.chunk_id)
        
        return chunk_ids
    
    def _update_file_manifest(self, md_file: Path, chunk_ids: List[str], 
                             cache: UnifiedCache) -> None:
        """Update file manifest with new chunk IDs and cleanup orphaned chunks"""
        file_key = str(md_file)
        
        # Get existing manifest entry
        existing_entry = cache.get_manifest_entry(file_key, {})
        old_chunk_ids = existing_entry.get('chunk_ids', [])
        
        # Cleanup orphaned chunks if any
        if old_chunk_ids:
            cache.cleanup_orphaned_chunks(chunk_ids, file_key)
        
        # Update manifest
        manifest_entry = {
            'type': 'file',
            'hash': file_get_hash(md_file),
            'chunk_ids': chunk_ids,
            'chunk_count': len(chunk_ids)
        }
        
        cache.update_manifest_entry(file_key, manifest_entry)
    
    def _generate_missing_embeddings(self, chunks: List[DocumentChunk], 
                                    cache: UnifiedCache) -> None:
        """Generate embeddings for chunks that don't have them yet"""
        chunks_needing_embeddings = [chunk for chunk in chunks if chunk.embedding is None]
        
        if chunks_needing_embeddings:
            logger.info(f"Generating embeddings for {len(chunks_needing_embeddings)} chunks")
            # Embeddings will be generated on demand during strategy processing
        else:
            logger.info("All chunks have embeddings cached") 