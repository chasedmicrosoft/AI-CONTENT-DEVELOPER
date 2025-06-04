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
    
    def get_structure(self, repo_path: Path, max_depth: int = 3) -> str:
        """Get repository structure as string"""
        lines = []
        
        def add_dir(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
            
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for i, item in enumerate(items):
                if item.name.startswith('.'):
                    continue
                
                is_last = i == len(items) - 1
                current = "└── " if is_last else "├── "
                lines.append(f"{prefix}{current}{item.name}")
                
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    add_dir(item, prefix + extension, depth + 1)
        
        # Start directly with repository contents, not the repository name
        add_dir(repo_path, "", 0)
        return "\n".join(lines) 