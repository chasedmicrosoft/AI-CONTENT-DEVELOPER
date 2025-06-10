"""
Directory confirmation using LLM-native approach
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models import Config
from ..processors.llm_native_processor import LLMNativeProcessor
from .generic_interactive import GenericInteractive

logger = logging.getLogger(__name__)


class DirectoryConfirmation(GenericInteractive):
    """Confirm working directory selection using LLM intelligence"""
    
    def __init__(self, config, client):
        """Initialize with config and OpenAI client"""
        super().__init__(config)
        self.client = client
    
    def confirm(self, llm_result: Optional[Dict], structure: str = None, 
                failed: bool = False, error: str = "") -> Dict:
        """Confirm directory selection
        
        Args:
            llm_result: Result from LLM directory detection
            structure: Repository structure (for manual selection)
            failed: Whether LLM detection failed
            error: Error message if failed
            
        Returns:
            Confirmed directory selection dict
        """
        # If auto-confirm is enabled and LLM succeeded, return the result
        if self.config.auto_confirm and not failed and llm_result:
            return llm_result
        
        # If LLM failed or manual selection is needed
        if failed or not llm_result or llm_result.get('confidence', 0) < 0.7:
            return self._manual_selection(structure, error)
        
        # Interactive confirmation of LLM result
        return self._interact_with_llm_result(llm_result, structure)
    
    def _interact_with_llm_result(self, llm_result: Dict, structure: str) -> Dict:
        """Interactively confirm LLM's directory selection"""
        print(f"\n📁 Suggested directory: {llm_result.get('working_directory', 'Unknown')}")
        print(f"   Confidence: {llm_result.get('confidence', 0):.1%}")
        print(f"   Reason: {llm_result.get('justification', 'No reason provided')}")
        
        while True:
            choice = input("\nAccept this directory? (y/n/m for manual): ").strip().lower()
            
            if choice == 'y':
                return llm_result
            elif choice == 'n':
                raise SystemExit("Operation cancelled")
            elif choice == 'm':
                return self._manual_selection(structure, "User requested manual selection")
            else:
                print("Invalid choice. Please enter y, n, or m.")
    
    def _manual_selection(self, structure: str, reason: str) -> Dict:
        """Handle manual directory selection"""
        print(f"\n⚠️  Manual selection needed: {reason}")
        
        # Extract possible directories from structure
        directories = self._extract_directories(structure)
        
        if not directories:
            raise RuntimeError("No valid directories found in repository")
        
        # Use prompt_user to get selection
        selected = self.prompt_user(self.config, directories)
        
        if not selected:
            raise SystemExit("Directory selection cancelled")
        
        return {
            'working_directory': selected,
            'confidence': 1.0,
            'justification': 'Manually selected by user'
        }
    
    def _extract_directories(self, structure: str) -> List[str]:
        """Extract directory paths from repository structure"""
        directories = []
        
        if not structure:
            return directories
        
        # Parse structure to find directories containing documentation
        lines = structure.split('\n')
        for line in lines:
            # Look for lines that represent directories
            if '/' in line and not line.strip().startswith('.'):
                # Extract the directory path
                parts = line.split('/')
                if len(parts) >= 2 and 'articles' in parts[0]:
                    # Reconstruct the path
                    path = '/'.join(parts).strip()
                    # Remove any trailing characters or tree symbols
                    path = path.split(' ')[0].rstrip('/')
                    if path and path not in directories and not path.endswith('.md'):
                        directories.append(path)
        
        # Filter to only include actual documentation directories
        doc_dirs = []
        for d in directories:
            # Skip media/includes directories
            if not any(skip in d for skip in ['media', 'includes', 'images']):
                doc_dirs.append(d)
        
        return sorted(set(doc_dirs))
    
    def prompt_user(self, config: Config, directories: List[str]) -> Optional[str]:
        """Prompt user to select the correct working directory
        
        Args:
            config: Config object with context
            directories: List of possible directories
            
        Returns:
            Selected directory path or None if cancelled
        """
        # Use LLM to analyze directory structure
        llm_processor = LLMNativeProcessor(self.client, config)
        
        directory_structure = self._get_directory_structure(directories)
        
        # Ask LLM to understand the directory structure
        analysis = llm_processor.extract_key_information(
            content=directory_structure,
            extraction_purpose="Identify the most likely documentation directory based on structure and naming",
            operation_name="Directory Analysis"
        )
        
        # Get LLM's recommendation
        recommended = analysis.get('recommended_directory', '')
        confidence = analysis.get('confidence', 0)
        
        # Build prompt
        print("\n" + "="*60)
        print("WORKING DIRECTORY SELECTION")
        print("="*60)
        
        if recommended and confidence > 0.7:
            print(f"\n📁 Recommended directory: {recommended}")
            print(f"   Confidence: {confidence:.0%}")
            print(f"   Reason: {analysis.get('reason', 'Based on directory structure')}")
        
        print("\nAvailable directories:")
        for i, dir_path in enumerate(directories, 1):
            marker = " ← (recommended)" if dir_path == recommended else ""
            print(f"{i}. {dir_path}{marker}")
        
        # Interactive selection
        while True:
            choice = input("\nSelect directory number (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(directories):
                    selected = directories[index]
                    print(f"\n✓ Selected: {selected}")
                    return selected
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a number or 'q' to quit.")
    
    def _get_directory_structure(self, directories: List[str]) -> str:
        """Get a simple representation of directory structure"""
        structure_lines = ["Directory structure:"]
        
        for dir_path in directories:
            path_obj = Path(dir_path)
            
            # Show the directory and a few key subdirectories
            structure_lines.append(f"\n{dir_path}/")
            
            try:
                # List immediate subdirectories
                subdirs = [d for d in path_obj.iterdir() if d.is_dir() and not d.name.startswith('.')]
                for subdir in sorted(subdirs)[:5]:  # Show first 5 subdirs
                    structure_lines.append(f"  ├── {subdir.name}/")
                
                if len(subdirs) > 5:
                    structure_lines.append(f"  └── ... ({len(subdirs) - 5} more)")
                
                # Check for key documentation files
                doc_files = []
                for pattern in ['README.md', 'TOC.yml', 'index.md']:
                    if (path_obj / pattern).exists():
                        doc_files.append(pattern)
                
                if doc_files:
                    structure_lines.append(f"  📄 Files: {', '.join(doc_files)}")
                    
            except Exception as e:
                logger.warning(f"Could not list directory {dir_path}: {e}")
                structure_lines.append(f"  [Unable to read directory]")
        
        return '\n'.join(structure_lines) 