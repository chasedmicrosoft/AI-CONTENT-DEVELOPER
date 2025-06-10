"""
Repository management for cloning and updating git repositories
"""
import logging
import subprocess
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RepositoryManager:
    """Manage git repository operations"""
    
    @staticmethod
    def extract_name(url: str) -> str:
        """Extract repository name from URL"""
        # Remove trailing .git and slashes
        cleaned_url = url.rstrip('.git').rstrip('/')
        
        # Parse URL and extract path
        parsed_url = urlparse(cleaned_url)
        url_path = parsed_url.path.rstrip('/')
        
        # Get last component of path
        path_components = url_path.split('/')
        repo_name = path_components[-1] if path_components else "repo"
        
        # Default to "repo" if empty
        return repo_name or "repo"
    
    def clone_or_update(self, repo_url: str, work_dir: Path) -> Path:
        """Clone or update repository"""
        repo_name = self.extract_name(repo_url)
        repo_path = work_dir / repo_name
        
        if repo_path.exists():
            return self._update_repo(repo_path, repo_url)
        else:
            return self._clone_repo(repo_url, repo_path)
    
    def _run_git(self, cmd: List[str], cwd: Path = None):
        """Run git command"""
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    
    def _update_repo(self, repo_path: Path, repo_url: str) -> Path:
        """Update existing repository"""
        logger.info(f"Updating repository at {repo_path}")
        try:
            self._run_git(["git", "fetch"], repo_path)
            self._run_git(["git", "pull"], repo_path)
            logger.info("Repository updated successfully")
            return repo_path
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to update repo: {e}")
            return repo_path
    
    def _clone_repo(self, repo_url: str, repo_path: Path) -> Path:
        """Clone new repository"""
        logger.info(f"Cloning {repo_url} to {repo_path}")
        self._run_git(["git", "clone", repo_url, str(repo_path)])
        logger.info("Repository cloned successfully")
        return repo_path
    
    def get_directory_structure(self, repo_path: Path, max_depth: int = 3) -> str:
        """Get repository directory structure with markdown file counts"""
        lines = []
        
        def count_md_files(path: Path) -> int:
            """Count markdown files in a directory (non-recursive)"""
            try:
                return len([f for f in path.iterdir() if f.is_file() and f.suffix.lower() == '.md'])
            except:
                return 0
        
        def has_toc(path: Path) -> bool:
            """Check if directory has TOC.yml"""
            return (path / "TOC.yml").exists() or (path / "toc.yml").exists()
        
        def add_dir(path: Path, prefix: str = "", depth: int = 0, parent_shown: bool = True):
            if depth > max_depth:
                return
            
            # Get only directories
            dirs = [item for item in sorted(path.iterdir(), key=lambda x: x.name) 
                   if item.is_dir() and not item.name.startswith('.')]
            
            # Skip common non-documentation directories
            skip_dirs = {'node_modules', 'dist', 'build', 'target', '.git', 
                        'test', 'tests', '__pycache__', 'coverage', 'media', 
                        'images', 'assets', 'static', 'vendor', 'dependencies'}
            
            dirs = [d for d in dirs if d.name.lower() not in skip_dirs]
            
            for i, dir_item in enumerate(dirs):
                is_last = i == len(dirs) - 1
                current = "└── " if is_last else "├── "
                
                # Count markdown files and check for TOC
                md_count = count_md_files(dir_item)
                toc_indicator = " [TOC]" if has_toc(dir_item) else ""
                md_indicator = f" ({md_count} .md)" if md_count > 0 else ""
                
                # Show directory with indicators
                lines.append(f"{prefix}{current}{dir_item.name}{toc_indicator}{md_indicator}")
                
                # Recurse into subdirectories
                extension = "    " if is_last else "│   "
                add_dir(dir_item, prefix + extension, depth + 1)
        
        # Add repository root info
        root_md_count = count_md_files(repo_path)
        root_toc = " [TOC]" if has_toc(repo_path) else ""
        lines.append(f"[Repository Root]{root_toc} ({root_md_count} .md)")
        
        # Start with repository contents
        add_dir(repo_path, "", 0)
        
        return "\n".join(lines)
    
    def get_structure(self, repo_path: Path, max_depth: int = 3, show_files: bool = False) -> str:
        """Get repository structure as string
        
        Args:
            repo_path: Path to repository
            max_depth: Maximum depth to traverse
            show_files: Ignored (always shows directories only for performance)
            
        Returns:
            Tree structure as string
        """
        # Always use directory-only structure for better performance
        return self.get_directory_structure(repo_path, max_depth)
    

 