"""
Unified cache system for AI Content Developer
"""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
import logging

from ..utils import save_json, load_json, mkdir

logger = logging.getLogger(__name__)


class UnifiedCache:
    """Thread-safe cache system with manifest recovery"""
    
    def __init__(self, base_path: Path):
        self.path = Path(base_path)
        self.manifest_path = self.path / "manifest.json"
        self._lock = threading.Lock()
        mkdir(self.path)
        
        # Try to load manifest, recover if corrupted
        try:
            self.manifest = load_json(self.manifest_path)
        except Exception as e:
            logger.warning(f"Manifest corrupted, attempting recovery: {e}")
            self.manifest = self._recover_manifest()
    
    def _recover_manifest(self) -> Dict[str, Any]:
        """Recover manifest from existing cache files"""
        manifest = {}
        
        # Scan for all JSON files except manifest
        for json_file in self.path.glob("*.json"):
            if json_file.name == "manifest.json":
                continue
            
            try:
                data = load_json(json_file)
                chunk_id = json_file.stem
                
                # Add to manifest
                manifest[chunk_id] = {
                    'timestamp': data.get('timestamp', datetime.now().isoformat()),
                    'meta': data.get('meta', {})
                }
            except Exception as e:
                logger.warning(f"Could not recover {json_file}: {e}")
        
        # Save recovered manifest
        save_json(self.manifest_path, manifest)
        logger.info(f"Recovered manifest with {len(manifest)} entries")
        return manifest
    
    def reload_manifest(self):
        """Reload manifest from disk with error recovery"""
        try:
            self.manifest = load_json(self.manifest_path)
        except Exception as e:
            logger.warning(f"Manifest reload failed, recovering: {e}")
            self.manifest = self._recover_manifest()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data by key"""
        cache_file = self.path / f"{key}.json"
        try:
            return load_json(cache_file) if cache_file.exists() else None
        except Exception as e:
            logger.warning(f"Cache file {key} corrupted: {e}")
            return None
    
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
                # Reload manifest to get latest changes
                self.reload_manifest()
                self.manifest[key] = {
                    'timestamp': datetime.now().isoformat(), 
                    'meta': meta
                }
                save_json(self.manifest_path, self.manifest)
            except Exception as e:
                logger.error(f"Failed to save cache entry {key}: {e}")
    
    def update_manifest_entry(self, key: str, value: Dict[str, Any]):
        """Thread-safe method to update a manifest entry with reload"""
        with self._lock:
            try:
                # Reload to get latest changes from other threads
                self.reload_manifest()
                self.manifest[key] = value
                save_json(self.manifest_path, self.manifest)
            except Exception as e:
                logger.error(f"Failed to update manifest entry {key}: {e}")
    
    def get_manifest_entry(self, key: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """Thread-safe method to get a manifest entry"""
        with self._lock:
            try:
                # Reload to get latest changes
                self.reload_manifest()
                return self.manifest.get(key, default)
            except Exception as e:
                logger.error(f"Failed to get manifest entry {key}: {e}")
                return default
    
    def needs_update(self, key: str, hash_val: str) -> bool:
        """Check if cache entry needs update based on hash"""
        with self._lock:
            try:
                self.reload_manifest()
                return self.manifest.get(key, {}).get('hash') != hash_val
            except Exception as e:
                logger.error(f"Failed to check update status for {key}: {e}")
                return True  # Assume update needed if we can't check
    
    def remove_old(self, pattern: str):
        """Remove old cache files matching pattern"""
        removed_count = 0
        for file in self.path.glob(pattern):
            if file.name != "manifest.json":
                try:
                    file.unlink()
                    removed_count += 1
                    # Remove from manifest if it's there
                    chunk_id = file.stem
                    if chunk_id in self.manifest:
                        del self.manifest[chunk_id]
                except Exception as e:
                    logger.warning(f"Failed to remove {file}: {e}")
        
        if removed_count > 0:
            # Save updated manifest
            save_json(self.manifest_path, self.manifest)
            logger.info(f"Removed {removed_count} cache files matching pattern '{pattern}'")
        
        return removed_count
    
    def cleanup_orphaned_chunks(self, current_chunk_ids: List[str], file_key: str):
        """
        Clean up orphaned chunks for a file based on manifest
        
        Args:
            current_chunk_ids: List of current valid chunk IDs for the file
            file_key: The file key in the manifest
        """
        with self._lock:
            orphaned_chunks = self._find_orphaned_chunks(current_chunk_ids, file_key)
            
            if not orphaned_chunks:
                return 0
            
            removed_count = self._remove_orphaned_chunks(orphaned_chunks)
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} orphaned chunks for {file_key}")
                save_json(self.manifest_path, self.manifest)
        
        return len(orphaned_chunks)
    
    def _find_orphaned_chunks(self, current_chunk_ids: List[str], file_key: str) -> set:
        """Find chunks that are no longer needed for a file"""
        old_manifest_entry = self.manifest.get(file_key, {})
        old_chunk_ids = old_manifest_entry.get('chunk_ids', [])
        
        return set(old_chunk_ids) - set(current_chunk_ids)
    
    def _remove_orphaned_chunks(self, orphaned_chunks: set) -> int:
        """Remove orphaned chunk files from disk"""
        removed_count = 0
        
        for chunk_id in orphaned_chunks:
            if self._remove_chunk_file(chunk_id):
                removed_count += 1
        
        return removed_count
    
    def _remove_chunk_file(self, chunk_id: str) -> bool:
        """Remove a single chunk file and its manifest entry"""
        chunk_file = self.path / f"{chunk_id}.json"
        
        if not chunk_file.exists():
            return False
            
        try:
            chunk_file.unlink()
            
            # Remove from manifest if it exists as a separate entry
            if chunk_id in self.manifest:
                del self.manifest[chunk_id]
            
            return True
        except Exception as e:
            logger.warning(f"Failed to remove orphaned chunk {chunk_id}: {e}")
            return False
    
    def verify_and_cleanup_manifest(self):
        """
        Verify manifest entries and clean up entries for files that no longer exist
        or chunks that are missing
        """
        with self._lock:
            self.reload_manifest()
            entries_to_remove, chunks_to_remove = self._validate_manifest_entries()
            
            # Remove invalid entries
            self._remove_invalid_entries(entries_to_remove, chunks_to_remove)
    
    def _validate_manifest_entries(self) -> tuple:
        """Validate all manifest entries and return lists of invalid ones"""
        entries_to_remove = []
        chunks_to_remove = []
        
        for key, entry in self.manifest.items():
            if 'meta' in entry:
                # This is a chunk entry
                if not self._validate_chunk_entry(key):
                    chunks_to_remove.append(key)
            elif 'chunk_ids' in entry:
                # This is a file entry
                if not self._validate_file_entry(key, entry):
                    entries_to_remove.append(key)
        
        return entries_to_remove, chunks_to_remove
    
    def _validate_chunk_entry(self, key: str) -> bool:
        """Validate a chunk entry exists on disk"""
        chunk_file = self.path / f"{key}.json"
        return chunk_file.exists()
    
    def _validate_file_entry(self, key: str, entry: Dict) -> bool:
        """Validate a file entry and update its chunk list"""
        chunk_ids = entry.get('chunk_ids', [])
        existing_chunks = []
        
        # Find existing chunks
        for chunk_id in chunk_ids:
            chunk_file = self.path / f"{chunk_id}.json"
            if chunk_file.exists():
                existing_chunks.append(chunk_id)
        
        # Update the entry if chunks have changed
        if len(existing_chunks) != len(chunk_ids):
            logger.info(f"Updating manifest for {key}: {len(chunk_ids)} -> {len(existing_chunks)} chunks")
            entry['chunk_ids'] = existing_chunks
        
        # Return False if no chunks remain (mark for removal)
        return len(existing_chunks) > 0
    
    def _remove_invalid_entries(self, entries_to_remove: List[str], chunks_to_remove: List[str]):
        """Remove invalid entries from manifest"""
        all_removals = entries_to_remove + chunks_to_remove
        
        if not all_removals:
            return
        
        # Remove entries
        for key in all_removals:
            del self.manifest[key]
        
        # Save updated manifest
        save_json(self.manifest_path, self.manifest)
        logger.info(f"Cleaned up manifest: {len(entries_to_remove)} file entries, "
                   f"{len(chunks_to_remove)} chunk entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache"""
        total_files = len(list(self.path.glob("*.json"))) - 1  # Exclude manifest
        total_size = sum(f.stat().st_size for f in self.path.glob("*.json"))
        
        # Count file entries vs chunk entries in manifest
        file_entries = sum(1 for entry in self.manifest.values() if 'chunk_ids' in entry)
        chunk_entries = sum(1 for entry in self.manifest.values() if 'meta' in entry)
        
        return {
            'total_entries': len(self.manifest),
            'file_entries': file_entries,
            'chunk_entries': chunk_entries,
            'total_files': total_files,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_path': str(self.path)
        }
