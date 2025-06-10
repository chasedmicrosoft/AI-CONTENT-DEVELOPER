"""
Smart chunking system for markdown files
"""
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import logging

from ..models import DocumentChunk
from ..cache import UnifiedCache
from ..utils import file_ops, get_hash

logger = logging.getLogger(__name__)


class SmartChunker:
    """Smart chunking for markdown files with heading awareness"""
    
    def __init__(self, max_size=3000, min_size=500):
        self.max_size = max_size
        self.min_size = min_size
    
    def chunk_markdown(self, file_path: Path, cache: UnifiedCache) -> List[DocumentChunk]:
        """Chunk a markdown file into semantic chunks"""
        content = file_ops.read(file_path, limit=None)
        frontmatter, body = self._parse_frontmatter(content)
        
        chunks = []
        file_id = file_ops.get_hash(file_path)
        self._process_body(body, file_path, frontmatter, file_id, chunks, cache)
        
        # Link chunks
        for i, chunk in enumerate(chunks):
            chunk.total_chunks_in_file = len(chunks)
            if i > 0:
                chunk.prev_chunk_id = chunks[i-1].chunk_id
                chunks[i-1].next_chunk_id = chunk.chunk_id
        
        return chunks
    
    def _parse_frontmatter(self, content: str) -> tuple:
        """Parse YAML frontmatter from markdown content"""
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1]) or {}, parts[2]
                except yaml.YAMLError:
                    pass
        return {}, content
    
    def _process_body(self, body: str, file_path: Path, frontmatter: Dict, 
                     file_id: str, chunks: List, cache: UnifiedCache):
        """Process markdown body and create chunks"""
        # Initialize processing state
        state = self._initialize_processing_state()
        
        # Process each line
        for line in body.split('\n'):
            if line.startswith('#'):
                # Process heading line
                self._process_heading_line(line, state, file_path, frontmatter, 
                                         file_id, chunks)
            else:
                # Add content line
                state['current_chunk'] += line + '\n'
        
        # Add final chunk if exists
        if state['current_chunk'].strip():
            self._add_chunks(state['current_chunk'].strip(), file_path, 
                           state['heading_stack'], frontmatter, file_id, 
                           state['current_parent_id'], chunks)
    
    def _initialize_processing_state(self) -> Dict:
        """Initialize state for processing markdown body"""
        return {
            'current_chunk': "",
            'heading_stack': [],
            'heading_to_chunk_id': {},
            'current_parent_id': None
        }
    
    def _process_heading_line(self, line: str, state: Dict, file_path: Path,
                             frontmatter: Dict, file_id: str, chunks: List):
        """Process a heading line and update state"""
                # Save current chunk if exists
        if state['current_chunk'].strip():
            self._add_chunks(state['current_chunk'].strip(), file_path, 
                           state['heading_stack'][:], frontmatter, file_id, 
                           state['current_parent_id'], chunks)
        
        # Parse heading
        level, heading = self._parse_heading(line)
                
                # Update heading stack
        state['heading_stack'] = state['heading_stack'][:level-1] + [heading]
                
        # Track heading chunk ID
        heading_path = ' > '.join(state['heading_stack'])
        current_chunk_id = get_hash(f"{file_id}_{heading_path}")
        state['heading_to_chunk_id'][heading_path] = current_chunk_id
                
                # Determine parent
        state['current_parent_id'] = self._determine_parent_id(
            level, state['heading_stack'], state['heading_to_chunk_id']
        )
        
        # Start new chunk with heading
        state['current_chunk'] = line + '\n'
    
    def _parse_heading(self, line: str) -> tuple:
        """Parse heading level and text from a heading line"""
        level = len(line) - len(line.lstrip('#'))
        heading = line.lstrip('# ').strip()
        return level, heading
    
    def _determine_parent_id(self, level: int, heading_stack: List[str], 
                            heading_to_chunk_id: Dict[str, str]) -> Optional[str]:
        """Determine parent chunk ID for current heading"""
        if level > 1 and len(heading_stack) > 1:
            parent_heading = ' > '.join(heading_stack[:-1])
            return heading_to_chunk_id.get(parent_heading)
        return None
    
    def _add_chunks(self, content: str, file_path: Path, heading_path: List[str], 
                   frontmatter: Dict, file_id: str, parent_id: str, chunks: List):
        """Add content as one or more chunks"""
        for chunk_content in self._smart_split(content):
            chunk_id = get_hash(f"{file_id}_{len(chunks)}_{chunk_content[:50]}")
            chunks.append(self._create_chunk(
                chunk_content, file_path, heading_path, frontmatter,
                len(chunks), file_id, chunk_id, parent_id
            ))
    
    def _smart_split(self, content: str) -> List[str]:
        """Split content into chunks respecting paragraph boundaries"""
        if len(content) <= self.max_size:
            return [content]
        
        paragraphs = content.split('\n\n')
        return self._process_paragraphs_into_chunks(paragraphs) or [content]
    
    def _process_paragraphs_into_chunks(self, paragraphs: List[str]) -> List[str]:
        """Process paragraphs into properly sized chunks"""
        chunks = []
        current = ""
        
        for para in paragraphs:
            current = self._add_paragraph_to_chunk(para, current, chunks)
        
        # Handle any remaining content
        if current.strip():
            chunks.append(current.strip())
        
        return chunks
    
    def _add_paragraph_to_chunk(self, para: str, current: str, chunks: List[str]) -> str:
        """Add a paragraph to the current chunk or start a new one"""
        # Check if paragraph fits in current chunk
        if len(current) + len(para) + 2 <= self.max_size:
            return current + para + '\n\n'
        
        # Current chunk is large enough, save it and start new
        if len(current) >= self.min_size:
            chunks.append(current.strip())
            return para + '\n\n'
        
        # Current chunk is too small, force add paragraph
        current += para + '\n\n'
        
        # Check if forced addition made it large enough
        if len(current) >= self.min_size:
            chunks.append(current.strip())
            return ""
        
        return current
    
    def _create_chunk(self, content: str, file_path: Path, heading_path: List[str], 
                     frontmatter: Dict, index: int, file_id: str, chunk_id: str, 
                     parent_id: str) -> DocumentChunk:
        """Create a DocumentChunk with metadata"""
        # Build embedding content
        embedding_content = self._build_embedding_content(content, frontmatter, heading_path)
        
        # Create chunk
        return DocumentChunk(
            content=content.strip(),
            file_path=str(file_path),
            heading_path=heading_path,
            section_level=len(heading_path),
            chunk_index=index,
            frontmatter=frontmatter,
            embedding_content=embedding_content,
            embedding=None,  # No embedding yet
            content_hash=get_hash(embedding_content),
            file_id=file_id,
            chunk_id=chunk_id,
            parent_heading_chunk_id=parent_id
        )
    
    def _build_embedding_content(self, content: str, frontmatter: Dict, 
                                heading_path: List[str]) -> str:
        """Build embedding content with context"""
        context_parts = []
        
        # Add frontmatter context
        context_parts.extend(self._extract_frontmatter_context(frontmatter))
        
        # Add heading context
        if heading_path:
            context_parts.append(f"Section: {' > '.join(heading_path)}")
        
        # Add actual content
        context_parts.append(content)
        
        return " | ".join(filter(None, context_parts))
    
    def _extract_frontmatter_context(self, frontmatter: Dict) -> List[str]:
        """Extract relevant context from frontmatter"""
        if not frontmatter:
            return []
            
        context_parts = []
        
        if title := frontmatter.get('title'):
            context_parts.append(f"Document: {title}")
            
        if topic := frontmatter.get('ms.topic'):
            context_parts.append(f"Topic: {topic}")
            
        if desc := frontmatter.get('description'):
            context_parts.append(f"Description: {desc[:100]}")
        
        return context_parts
