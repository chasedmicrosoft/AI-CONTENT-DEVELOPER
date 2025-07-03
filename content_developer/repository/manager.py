"""
Repository management for cloning and updating git repositories
"""
import logging
import subprocess
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, urlunparse
import re

logger = logging.getLogger(__name__)


class RepositoryManager:
    """Manage git repository operations"""
    
    def __init__(self, github_token: Optional[str] = None):
        """Initialize with optional GitHub token for private repositories"""
        self.github_token = github_token
    
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
        
        # Build authenticated URL if token is available
        clone_url = self._build_clone_url(repo_url)
        
        if repo_path.exists():
            return self._update_repo(repo_path, clone_url, repo_url)
        else:
            return self._clone_repo(clone_url, repo_path, repo_url)
    
    def _build_clone_url(self, repo_url: str) -> str:
        """Build clone URL with authentication if token available"""
        # If no token, return original URL
        if not self.github_token:
            return repo_url
        
        # Only add authentication for GitHub URLs
        if 'github.com' not in repo_url:
            return repo_url
        
        # Parse URL to add authentication
        parsed = urlparse(repo_url)
        
        # Add token authentication
        # Format: https://TOKEN@github.com/user/repo.git
        auth_netloc = f"{self.github_token}@{parsed.netloc}"
        auth_url = urlunparse(parsed._replace(netloc=auth_netloc))
        
        return auth_url
    
    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in URL for logging"""
        if '@' in url and self.github_token:
            # Replace token with asterisks
            return url.replace(self.github_token, '****')
        return url
    
    def _run_git(self, cmd: List[str], cwd: Path = None):
        """Run git command with error handling"""
        try:
            # Use --quiet to minimize token exposure in output
            if cmd[1] in ['clone', 'fetch', 'pull'] and '--quiet' not in cmd:
                cmd.append('--quiet')
            
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
            return result
        except subprocess.CalledProcessError as e:
            # Mask any tokens in error messages
            if self.github_token and self.github_token in e.stderr:
                e.stderr = e.stderr.replace(self.github_token, '****')
            raise e
    
    def _update_repo(self, repo_path: Path, clone_url: str, original_url: str) -> Path:
        """Update existing repository"""
        logger.info(f"Updating repository at {repo_path}")
        try:
            # Update remote URL if using authentication
            if self.github_token and 'github.com' in original_url:
                self._run_git(["git", "remote", "set-url", "origin", clone_url], repo_path)
            
            self._run_git(["git", "fetch"], repo_path)
            self._run_git(["git", "pull"], repo_path)
            logger.info("Repository updated successfully")
            return repo_path
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to update repo: {e.stderr}")
            # Continue with existing repo even if update fails
            return repo_path
    
    def _clone_repo(self, clone_url: str, repo_path: Path, original_url: str) -> Path:
        """Clone new repository with error handling"""
        logger.info(f"Cloning {self._mask_url(clone_url)} to {repo_path}")
        
        try:
            self._run_git(["git", "clone", "--depth", "1", clone_url, str(repo_path)])
            logger.info("Repository cloned successfully")
            return repo_path
        except subprocess.CalledProcessError as e:
            self._handle_clone_error(e, original_url)
    
    def _handle_clone_error(self, error: subprocess.CalledProcessError, repo_url: str):
        """Handle clone errors with helpful messages"""
        error_msg = error.stderr.lower()
        
        if "authentication failed" in error_msg or "could not read" in error_msg or "repository not found" in error_msg:
            # Check if this might be a private repo
            if self._might_be_private(repo_url):
                raise RuntimeError(
                    f"Failed to access repository: {repo_url}\n"
                    "This appears to be a private repository.\n\n"
                    "To access private repositories:\n"
                    "1. Create a GitHub token at: https://github.com/settings/tokens\n"
                    "2. Add to your .env file: GITHUB_TOKEN=your_token_here\n"
                    "3. Ensure the token has 'repo' scope for classic tokens\n"
                    "   or 'Contents: Read' permission for fine-grained tokens"
                )
            else:
                raise RuntimeError(
                    f"Failed to clone repository: {repo_url}\n"
                    f"Error: {error.stderr}"
                )
        else:
            # Other errors
            raise RuntimeError(f"Git clone failed: {error.stderr}")
    
    def _might_be_private(self, repo_url: str) -> bool:
        """Quick check if repo might be private (without token)"""
        if 'github.com' not in repo_url:
            return False
        
        # If we already have a token, it's definitely private if auth failed
        if self.github_token:
            return True
        
        # Extract owner/repo from URL
        match = re.search(r'github\.com[/:]([^/]+)/([^/\.]+)', repo_url)
        if not match:
            return False
        
        owner, repo = match.groups()
        
        # Try to access public API endpoint
        try:
            import requests
            response = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                timeout=3,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )
            # 404 suggests private (or non-existent)
            return response.status_code == 404
        except:
            # If we can't check, assume it might be private
            return True
    
    @staticmethod
    def _count_md_files(path: Path) -> int:
        """Count markdown files in a directory (non-recursive)"""
        try:
            return len([f for f in path.iterdir() if f.is_file() and f.suffix.lower() == '.md'])
        except:
            return 0
    
    @staticmethod
    def _has_toc(path: Path) -> bool:
        """Check if directory has TOC.yml"""
        return (path / "TOC.yml").exists() or (path / "toc.yml").exists()
    
    @staticmethod
    def _should_skip_directory(dir_name: str) -> bool:
        """Check if directory should be skipped"""
        skip_dirs = {
            'node_modules', 'dist', 'build', 'target', '.git', 
            'test', 'tests', '__pycache__', 'coverage', 'media', 
            'images', 'assets', 'static', 'vendor', 'dependencies'
        }
        return dir_name.lower() in skip_dirs
    
    def get_directory_structure(self, repo_path: Path, max_depth: int = 3) -> str:
        """Get repository directory structure with markdown file counts"""
        lines = []
        
        # Add repository root info
        root_md_count = self._count_md_files(repo_path)
        root_toc = " [TOC]" if self._has_toc(repo_path) else ""
        lines.append(f"[Repository Root]{root_toc} ({root_md_count} .md)")
        
        # Build directory tree
        self._add_directory_tree(repo_path, lines, "", 0, max_depth)
        
        return "\n".join(lines)
    
    def _add_directory_tree(self, path: Path, lines: List[str], prefix: str, 
                           depth: int, max_depth: int) -> None:
        """Add directory tree to lines list"""
        if depth > max_depth:
            return
        
        # Get only directories
        directories = self._get_valid_directories(path)
        
        for i, dir_item in enumerate(directories):
            is_last = i == len(directories) - 1
            self._add_directory_line(dir_item, lines, prefix, is_last)
            
            # Recurse into subdirectories
            extension = "    " if is_last else "│   "
            self._add_directory_tree(dir_item, lines, prefix + extension, 
                                   depth + 1, max_depth)
    
    def _get_valid_directories(self, path: Path) -> List[Path]:
        """Get list of valid directories to display"""
        try:
            dirs = [item for item in sorted(path.iterdir(), key=lambda x: x.name) 
                   if item.is_dir() and not item.name.startswith('.')]
            
            # Filter out directories we should skip
            return [d for d in dirs if not self._should_skip_directory(d.name)]
        except:
            return []
    
    def _add_directory_line(self, dir_item: Path, lines: List[str], 
                           prefix: str, is_last: bool) -> None:
        """Add a single directory line to the output"""
        current = "└── " if is_last else "├── "
        
        # Count markdown files and check for TOC
        md_count = self._count_md_files(dir_item)
        toc_indicator = " [TOC]" if self._has_toc(dir_item) else ""
        md_indicator = f" ({md_count} .md)" if md_count > 0 else ""
        
        # Show directory with indicators
        lines.append(f"{prefix}{current}{dir_item.name}{toc_indicator}{md_indicator}")
    
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
    

 