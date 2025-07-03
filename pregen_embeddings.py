#!/usr/bin/env python3
"""
Standalone Embedding Pre-generation Script for AI Content Developer

This script pre-generates embeddings for all directories in a repository,
creating the exact same cache structure that the main application expects.

Usage:
    python pregen_embeddings.py --repo https://github.com/MicrosoftDocs/azure-docs
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Azure OpenAI imports
try:
    from openai import AzureOpenAI
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
except ImportError:
    print("Error: Required packages not installed.")
    print("Please install: pip install openai azure-identity")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Utility Functions (Mirror the application's utilities)
# ============================================================================

def get_hash(content: str) -> str:
    """Generate hash for content - must match app's implementation"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def file_get_hash(file_path: Path) -> str:
    """Generate hash for file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return get_hash(content)
    except Exception as e:
        logger.error(f"Error hashing file {file_path}: {e}")
        return ""


def save_json(file_path: Path, data: Dict):
    """Save JSON data to file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: Path) -> Dict:
    """Load JSON data from file"""
    if not file_path.exists():
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================================
# Document Chunk Model (Mirror DocumentChunk)
# ============================================================================

class DocumentChunk:
    """Represents a chunk of document content with metadata"""
    def __init__(self, content: str, file_path: str, heading_path: List[str],
                 section_level: int, chunk_index: int, frontmatter: Dict[str, Any],
                 embedding_content: str, embedding: Optional[List[float]] = None,
                 content_hash: Optional[str] = None, file_id: str = "",
                 chunk_id: str = "", prev_chunk_id: Optional[str] = None,
                 next_chunk_id: Optional[str] = None,
                 parent_heading_chunk_id: Optional[str] = None,
                 total_chunks_in_file: int = 0):
        self.content = content
        self.file_path = file_path
        self.heading_path = heading_path
        self.section_level = section_level
        self.chunk_index = chunk_index
        self.frontmatter = frontmatter
        self.embedding_content = embedding_content
        self.embedding = embedding
        self.content_hash = content_hash or get_hash(embedding_content)
        self.file_id = file_id
        self.chunk_id = chunk_id
        self.prev_chunk_id = prev_chunk_id
        self.next_chunk_id = next_chunk_id
        self.parent_heading_chunk_id = parent_heading_chunk_id
        self.total_chunks_in_file = total_chunks_in_file


# ============================================================================
# Smart Chunker (Mirror SmartChunker from the application)
# ============================================================================

class SmartChunker:
    """Smart chunking for markdown files with heading awareness"""
    
    def __init__(self, max_size=3000, min_size=500):
        self.max_size = max_size
        self.min_size = min_size
    
    def chunk_markdown(self, file_path: Path) -> List[DocumentChunk]:
        """Chunk a markdown file into semantic chunks"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []
        
        frontmatter, body = self._parse_frontmatter(content)
        
        chunks = []
        file_id = file_get_hash(file_path)
        self._process_body(body, file_path, frontmatter, file_id, chunks)
        
        # Link chunks
        for i, chunk in enumerate(chunks):
            chunk.total_chunks_in_file = len(chunks)
            if i > 0:
                chunk.prev_chunk_id = chunks[i-1].chunk_id
                chunks[i-1].next_chunk_id = chunk.chunk_id
        
        return chunks
    
    def _parse_frontmatter(self, content: str) -> Tuple[Dict, str]:
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
                     file_id: str, chunks: List):
        """Process markdown body and create chunks"""
        # Initialize processing state
        state = {
            'current_chunk': "",
            'heading_stack': [],
            'heading_to_chunk_id': {},
            'current_parent_id': None
        }
        
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
    
    def _process_heading_line(self, line: str, state: Dict, file_path: Path,
                             frontmatter: Dict, file_id: str, chunks: List):
        """Process a heading line and update state"""
        # Save current chunk if exists
        if state['current_chunk'].strip():
            self._add_chunks(state['current_chunk'].strip(), file_path, 
                           state['heading_stack'][:], frontmatter, file_id, 
                           state['current_parent_id'], chunks)
        
        # Parse heading
        level = len(line) - len(line.lstrip('#'))
        heading = line.lstrip('# ').strip()
        
        # Update heading stack
        state['heading_stack'] = state['heading_stack'][:level-1] + [heading]
        
        # Track heading chunk ID
        heading_path = ' > '.join(state['heading_stack'])
        current_chunk_id = get_hash(f"{file_id}_{heading_path}")
        state['heading_to_chunk_id'][heading_path] = current_chunk_id
        
        # Determine parent
        if level > 1 and len(state['heading_stack']) > 1:
            parent_heading = ' > '.join(state['heading_stack'][:-1])
            state['current_parent_id'] = state['heading_to_chunk_id'].get(parent_heading)
        else:
            state['current_parent_id'] = None
        
        # Start new chunk with heading
        state['current_chunk'] = line + '\n'
    
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
        chunks = []
        current = ""
        
        for para in paragraphs:
            # Check if paragraph fits in current chunk
            if len(current) + len(para) + 2 <= self.max_size:
                current += para + '\n\n'
            elif len(current) >= self.min_size:
                # Current chunk is large enough, save it
                chunks.append(current.strip())
                current = para + '\n\n'
            else:
                # Current chunk too small, force add
                current += para + '\n\n'
                if len(current) >= self.min_size:
                    chunks.append(current.strip())
                    current = ""
        
        if current.strip():
            chunks.append(current.strip())
        
        return chunks or [content]
    
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
            embedding=None,  # Will be set when embedding is generated
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
        if frontmatter:
            if title := frontmatter.get('title'):
                context_parts.append(f"Document: {title}")
            if topic := frontmatter.get('ms.topic'):
                context_parts.append(f"Topic: {topic}")
            if desc := frontmatter.get('description'):
                context_parts.append(f"Description: {desc[:100]}")
        
        # Add heading context
        if heading_path:
            context_parts.append(f"Section: {' > '.join(heading_path)}")
        
        # Add actual content
        context_parts.append(content)
        
        return " | ".join(filter(None, context_parts))


# ============================================================================
# Unified Cache (Mirror UnifiedCache from the application)
# ============================================================================

class UnifiedCache:
    """Thread-safe cache system with manifest recovery"""
    
    def __init__(self, base_path: Path):
        self.path = Path(base_path)
        self.manifest_path = self.path / "manifest.json"
        self._lock = threading.Lock()
        self.path.mkdir(parents=True, exist_ok=True)
        
        # Try to load manifest
        try:
            self.manifest = load_json(self.manifest_path)
        except Exception as e:
            logger.warning(f"Manifest corrupted, starting fresh: {e}")
            self.manifest = {}
    
    def put(self, key: str, data: Any, meta: Optional[Dict] = None):
        """Store data in cache with metadata"""
        with self._lock:
            try:
                cache_file = self.path / f"{key}.json"
                save_json(cache_file, {
                    'data': data, 
                    'meta': meta or {}, 
                    'timestamp': datetime.now().isoformat()
                })
                
                # Update manifest
                self.manifest[key] = {
                    'timestamp': datetime.now().isoformat(), 
                    'meta': meta
                }
                save_json(self.manifest_path, self.manifest)
            except Exception as e:
                logger.error(f"Failed to save cache entry {key}: {e}")
    
    def update_manifest_entry(self, key: str, value: Dict[str, Any]):
        """Update a manifest entry"""
        with self._lock:
            self.manifest[key] = value
            save_json(self.manifest_path, self.manifest)


# ============================================================================
# Repository Manager
# ============================================================================

class RepositoryManager:
    """Manages repository cloning and operations"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
    
    def clone_or_update(self, repo_url: str, work_dir: Path) -> Path:
        """Clone or update repository"""
        repo_name = self.extract_name(repo_url)
        repo_path = work_dir / repo_name
        
        if repo_path.exists():
            print(f"📥 Updating existing repository...")
            self._update_repo(repo_path)
        else:
            print(f"📥 Cloning repository...")
            self._clone_repo(repo_url, repo_path)
        
        return repo_path
    
    def extract_name(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        parsed = urlparse(repo_url)
        path = parsed.path.strip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return path.split('/')[-1]
    
    def _clone_repo(self, repo_url: str, repo_path: Path):
        """Clone repository"""
        # Add token to URL if available
        if self.github_token and 'github.com' in repo_url:
            parsed = urlparse(repo_url)
            repo_url = f"https://{self.github_token}@{parsed.netloc}{parsed.path}"
        
        try:
            subprocess.run(['git', 'clone', repo_url, str(repo_path)], 
                         check=True, capture_output=True, text=True)
            print(f"   ✓ Repository cloned successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e.stderr}")
            raise
    
    def _update_repo(self, repo_path: Path):
        """Update existing repository"""
        try:
            subprocess.run(['git', 'pull'], cwd=repo_path, 
                         check=True, capture_output=True, text=True)
            print(f"   ✓ Repository updated successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update repository: {e.stderr}")
            # Continue anyway - might be local changes


# ============================================================================
# Embedding Generator
# ============================================================================

class EmbeddingGenerator:
    """Handles embedding generation using Azure OpenAI"""
    
    def __init__(self):
        # Initialize Azure OpenAI client
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
        
        # Get deployment name
        self.deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        
        # Initialize client with Azure AD authentication
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default"
        )
        
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            response = self.client.embeddings.create(
                model=self.deployment,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise


# ============================================================================
# Main Pre-generation Logic
# ============================================================================

class EmbeddingPreGenerator:
    """Main class for pre-generating embeddings"""
    
    def __init__(self):
        self.work_dir = Path("./work/tmp")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.chunker = SmartChunker()
        self.embedding_generator = EmbeddingGenerator()
        self.stats = {
            'directories_processed': 0,
            'files_processed': 0,
            'chunks_created': 0,
            'embeddings_generated': 0,
            'errors': []
        }
    
    def process_repository(self, repo_url: str):
        """Process entire repository"""
        start_time = datetime.now()
        
        print(f"\n🚀 Pre-generating embeddings for {repo_url}")
        
        # Clone or update repository
        repo_manager = RepositoryManager(os.getenv("GITHUB_TOKEN"))
        repo_path = repo_manager.clone_or_update(repo_url, self.work_dir)
        repo_name = repo_manager.extract_name(repo_url)
        
        # Find all directories with markdown files
        directories = self.find_markdown_directories(repo_path)
        print(f"📁 Found {len(directories)} directories to process\n")
        
        # Process each directory
        for i, directory in enumerate(directories, 1):
            relative_dir = directory.relative_to(repo_path)
            print(f"📂 Processing ({i}/{len(directories)}): {relative_dir}")
            
            try:
                self.process_directory(repo_path, directory, repo_name, str(relative_dir))
                self.stats['directories_processed'] += 1
            except Exception as e:
                logger.error(f"Error processing {relative_dir}: {e}")
                self.stats['errors'].append(f"{relative_dir}: {str(e)}")
        
        # Print summary
        self.print_summary(start_time)
    
    def find_markdown_directories(self, repo_path: Path) -> List[Path]:
        """Find all directories containing markdown files"""
        markdown_dirs = set()
        
        for md_file in repo_path.rglob("*.md"):
            # Skip hidden directories
            if any(part.startswith('.') for part in md_file.parts):
                continue
            
            # Add the directory
            markdown_dirs.add(md_file.parent)
        
        # Sort by path for consistent processing
        return sorted(markdown_dirs)
    
    def process_directory(self, repo_path: Path, directory: Path, 
                         repo_name: str, relative_dir: str):
        """Process all markdown files in a directory"""
        # Setup cache for this directory
        cache_dir = Path(f"./llm_outputs/embeddings/{repo_name}/{relative_dir}")
        cache = UnifiedCache(cache_dir)
        
        # Find markdown files
        md_files = list(directory.glob("*.md"))
        if not md_files:
            return
        
        print(f"   📄 Processing {len(md_files)} markdown files...")
        
        chunks_in_dir = 0
        embeddings_in_dir = 0
        
        for md_file in md_files:
            try:
                # Chunk the file
                chunks = self.chunker.chunk_markdown(md_file)
                if not chunks:
                    continue
                
                self.stats['files_processed'] += 1
                self.stats['chunks_created'] += len(chunks)
                chunks_in_dir += len(chunks)
                
                # Generate embeddings for each chunk
                chunk_ids = []
                for chunk in chunks:
                    # Generate embedding
                    embedding = self.embedding_generator.generate_embedding(
                        chunk.embedding_content
                    )
                    
                    # Prepare chunk data with embedding
                    chunk_data = {
                        'content': chunk.content,
                        'file_path': chunk.file_path,
                        'heading_path': chunk.heading_path,
                        'section_level': chunk.section_level,
                        'chunk_index': chunk.chunk_index,
                        'frontmatter': chunk.frontmatter,
                        'embedding_content': chunk.embedding_content,
                        'embedding': embedding,
                        'embedding_model': self.embedding_generator.deployment,
                        'embedding_generated_at': datetime.now().isoformat(),
                        'content_hash': chunk.content_hash,
                        'file_id': chunk.file_id,
                        'chunk_id': chunk.chunk_id,
                        'prev_chunk_id': chunk.prev_chunk_id,
                        'next_chunk_id': chunk.next_chunk_id,
                        'parent_heading_chunk_id': chunk.parent_heading_chunk_id,
                        'total_chunks_in_file': chunk.total_chunks_in_file
                    }
                    
                    # Store in cache
                    cache.put(chunk.chunk_id, chunk_data, {
                        'type': 'chunk',
                        'file': chunk.file_path,
                        'section': chunk.heading_path,
                        'has_embedding': True
                    })
                    
                    chunk_ids.append(chunk.chunk_id)
                    self.stats['embeddings_generated'] += 1
                    embeddings_in_dir += 1
                
                # Update manifest for the file
                cache.update_manifest_entry(str(md_file), {
                    'type': 'file',
                    'hash': file_get_hash(md_file),
                    'chunk_ids': chunk_ids,
                    'chunk_count': len(chunk_ids)
                })
                
            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
                self.stats['errors'].append(f"{md_file}: {str(e)}")
        
        print(f"   ✓ Generated {embeddings_in_dir} embeddings from {chunks_in_dir} chunks")
    
    def print_summary(self, start_time: datetime):
        """Print processing summary"""
        duration = datetime.now() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ Setup complete! Repository is ready for AI Content Developer")
        print(f"{'='*60}")
        print(f"\nSummary:")
        print(f"  • Directories processed: {self.stats['directories_processed']}")
        print(f"  • Total files: {self.stats['files_processed']}")
        print(f"  • Total chunks: {self.stats['chunks_created']}")
        print(f"  • Total embeddings: {self.stats['embeddings_generated']}")
        print(f"  • Time taken: {duration}")
        
        # Calculate cache size
        cache_path = Path("./llm_outputs/embeddings")
        if cache_path.exists():
            size_mb = sum(f.stat().st_size for f in cache_path.rglob("*") if f.is_file()) / (1024 * 1024)
            print(f"  • Cache size: {size_mb:.1f} MB")
        
        if self.stats['errors']:
            print(f"\n⚠️  Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                print(f"     - {error}")
            if len(self.stats['errors']) > 5:
                print(f"     ... and {len(self.stats['errors']) - 5} more")
        
        print(f"\nYour repository is now optimized for fast content generation!")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Pre-generate embeddings for AI Content Developer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pregen_embeddings.py --repo https://github.com/MicrosoftDocs/azure-docs
  python pregen_embeddings.py --repo https://github.com/Azure/azure-sdk-for-python

Environment Variables Required:
  AZURE_OPENAI_ENDPOINT              - Your Azure OpenAI endpoint
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT  - Embedding model deployment name
  GITHUB_TOKEN                       - (Optional) For private repositories
        """
    )
    
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository URL to process"
    )
    
    args = parser.parse_args()
    
    # Check Azure configuration
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("Error: AZURE_OPENAI_ENDPOINT environment variable not set")
        print("Please set your Azure OpenAI configuration in .env or environment")
        sys.exit(1)
    
    try:
        # Run pre-generation
        generator = EmbeddingPreGenerator()
        generator.process_repository(args.repo)
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main() 