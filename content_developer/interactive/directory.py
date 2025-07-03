"""
Directory confirmation using LLM-native approach
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

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
        
        # Build the directory tree from the structure
        tree = self._build_directory_tree(structure)
        
        if not tree:
            raise RuntimeError("No valid directories found in repository")
        
        # Use interactive tree browser
        selected = self._interactive_tree_browser(tree)
        
        if not selected:
            raise SystemExit("Directory selection cancelled")
        
        return {
            'working_directory': selected,
            'confidence': 1.0,
            'justification': 'Manually selected by user'
        }
    
    def _build_directory_tree(self, structure: str) -> Dict:
        """Build a hierarchical tree structure from the flat repository structure"""
        if not structure:
            return {}
        
        # Parse all directories with their metadata
        directories = self._extract_directories(structure)
        
        # Build tree structure
        tree = {
            'name': '[Repository Root]',
            'path': '',
            'md_count': 0,
            'has_toc': False,
            'children': {}
        }
        
        # Get root metadata
        for path, metadata in directories:
            if path == '':
                tree['md_count'] = metadata.get('md_count', 0)
                tree['has_toc'] = metadata.get('has_toc', False)
                break
        
        # Build the tree - handle both actual directories and parent paths
        all_paths = set()
        for path, metadata in directories:
            if path == '':  # Skip root, already processed
                continue
            
            # Add all parent paths to ensure complete tree
            parts = path.split('/')
            for i in range(1, len(parts) + 1):
                all_paths.add('/'.join(parts[:i]))
        
        # Build tree with all paths
        for path in sorted(all_paths):
            parts = path.split('/')
            current = tree
            
            # Navigate/create path in tree
            for i, part in enumerate(parts):
                if part not in current['children']:
                    current_path = '/'.join(parts[:i+1])
                    current['children'][part] = {
                        'name': part,
                        'path': current_path,
                        'md_count': 0,
                        'has_toc': False,
                        'children': {}
                    }
                current = current['children'][part]
        
        # Now update metadata for directories we have info for
        for path, metadata in directories:
            if path == '':  # Skip root
                continue
                
            parts = path.split('/')
            current = tree
            
            # Navigate to the directory
            for part in parts:
                if part in current['children']:
                    current = current['children'][part]
                else:
                    break
            
            # Update metadata
            if current['path'] == path:
                current['md_count'] = metadata.get('md_count', 0)
                current['has_toc'] = metadata.get('has_toc', False)
        
        return tree
    
    def _interactive_tree_browser(self, tree: Dict) -> Optional[str]:
        """Interactive tree-based directory browser"""
        current_node = tree
        path_stack = []
        
        # Show initial header
        print("\n" + "="*60)
        print("INTERACTIVE DIRECTORY BROWSER")
        print("="*60)
        
        while True:
            # Clear screen for better UX (optional, can be removed if too aggressive)
            print("\n" * 2)
            
            # Show current location
            if path_stack:
                current_path = '/'.join(path_stack)
                print(f"📁 Current Path: /{current_path}")
            else:
                print("📁 Current Path: [Repository Root]")
            print("─" * 60)
            
            # Show tree view
            self._display_tree_view(current_node, path_stack)
            
            # Show commands
            print("\nCommands:")
            if current_node['children']:
                num_children = len(current_node['children'])
                if num_children > 0:
                    print(f"  1-{num_children}  : Enter subdirectory")
            
            # Show appropriate directory name in select option
            if path_stack:
                print(f"  s     : Select current directory ({current_node['name']})")
            else:
                print(f"  s     : Select repository root")
                
            if path_stack:  # Not at root
                print("  ..    : Go up to parent directory")
            print("  /     : Go to repository root")
            print("  q     : Quit")
            
            # Get user input
            command = input("\nEnter command: ").strip().lower()
            
            # Handle commands
            if command == 'q':
                return None
            elif command == 's':
                # Return the path of current directory
                return current_node['path']
            elif command == '..' and path_stack:
                # Go up one level
                path_stack.pop()
                current_node = self._navigate_to_path(tree, path_stack)
            elif command == '/':
                # Go to root
                path_stack = []
                current_node = tree
            elif command.isdigit():
                # Try to enter subdirectory
                idx = int(command) - 1
                children_list = list(current_node['children'].items())
                if 0 <= idx < len(children_list):
                    child_name, child_node = children_list[idx]
                    path_stack.append(child_name)
                    current_node = child_node
                else:
                    print("\n❌ Invalid selection. Please try again.")
            else:
                print("\n❌ Invalid command. Please try again.")
    
    def _navigate_to_path(self, tree: Dict, path_stack: List[str]) -> Dict:
        """Navigate to a specific path in the tree"""
        current = tree
        for part in path_stack:
            current = current['children'][part]
        return current
    
    def _display_tree_view(self, node: Dict, path_stack: List[str]):
        """Display the tree view for the current node"""
        # Show the path context
        if path_stack:
            # Show abbreviated parent path
            print("[Repository Root]")
            for i, part in enumerate(path_stack[:-1]):
                print("  " * (i + 1) + "└── " + part)
            
            # Show current directory with indicator
            current_indent = "  " * len(path_stack)
            md_info = f" ({node['md_count']} .md)" if node['md_count'] > 0 else ""
            toc_info = " [TOC]" if node['has_toc'] else ""
            print(f"{current_indent}└── {node['name']}{md_info}{toc_info}    ← You are here")
        else:
            # At root
            md_info = f" ({node['md_count']} .md)" if node['md_count'] > 0 else ""
            toc_info = " [TOC]" if node['has_toc'] else ""
            print(f"{node['name']}{md_info}{toc_info}    ← You are here")
        
        # Show children
        if node['children']:
            children_list = list(node['children'].items())
            base_indent = "  " * (len(path_stack) + 1) if path_stack else ""
            
            for i, (name, child) in enumerate(children_list):
                is_last = (i == len(children_list) - 1)
                prefix = "└── " if is_last else "├── "
                
                # Format child info
                md_info = f" ({child['md_count']} .md)" if child['md_count'] > 0 else ""
                toc_info = " [TOC]" if child['has_toc'] else ""
                
                # Show if it has children
                has_children = bool(child['children'])
                child_indicator = "/" if has_children else ""
                
                # Add count of subdirectories if many
                subdir_count = len(child['children']) if has_children else 0
                if subdir_count > 5:
                    child_info = f" ({subdir_count} subdirs)"
                else:
                    child_info = ""
                
                print(f"{base_indent}{prefix}{i+1}. {name}{child_indicator}{md_info}{toc_info}{child_info}")
                
                # Show a preview of subdirectories (first 2 levels deep)
                if child['children'] and len(path_stack) < 2:
                    subchildren = list(child['children'].items())[:3]
                    for j, (subname, _) in enumerate(subchildren):
                        sub_indent = base_indent + ("    " if not is_last else "    ")
                        sub_prefix = "├── " if j < len(subchildren) - 1 else "└── "
                        print(f"{sub_indent}{sub_prefix}{subname}")
                    
                    if len(child['children']) > 3:
                        sub_indent = base_indent + ("    " if not is_last else "    ")
                        print(f"{sub_indent}└── ... ({len(child['children']) - 3} more)")
        else:
            print("\n(No subdirectories)")
    
    def _extract_directories(self, structure: str) -> List[Tuple[str, Dict]]:
        """Extract directory paths and metadata from repository structure"""
        if not structure:
            return []
        
        directories = []
        lines = structure.split('\n')
        path_stack = []  # Stack to track current path
        level_stack = []  # Stack to track indentation levels
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Skip the [Repository Root] line but process it for root
            if '[Repository Root]' in line:
                # Extract metadata for root
                match = re.search(r'\((\d+)\s*\.md\)', line)
                md_count = int(match.group(1)) if match else 0
                directories.append(('', {'md_count': md_count, 'has_toc': False}))
                continue
            
            # Extract directory info from tree format
            directory_info = self._parse_tree_line(line)
            if directory_info:
                name = directory_info['name']
                level = directory_info['level']
                
                # Adjust path stack based on level
                while level_stack and level_stack[-1] >= level:
                    path_stack.pop()
                    level_stack.pop()
                
                # Add current directory to path
                path_stack.append(name)
                level_stack.append(level)
                
                # Build full path
                full_path = '/'.join(path_stack)
                
                # Add to directories list with proper nesting
                directories.append((full_path, {
                    'md_count': directory_info['md_count'],
                    'has_toc': directory_info['has_toc']
                }))
                
                # Also check if this line has subdirectories indicated by │ on next lines
                # This helps maintain proper nesting context
        
        return directories
    
    def _extract_all_directory_paths(self, structure: str) -> List[str]:
        """Legacy method - kept for compatibility"""
        return [path for path, _ in self._extract_directories(structure)]
    
    def _filter_documentation_directories(self, directories: List[str]) -> List[str]:
        """Legacy method - kept for compatibility"""
        return directories
    
    def _get_directory_structure(self, directories: List[Tuple[str, Dict]]) -> str:
        """Get a simple representation of directory structure"""
        structure_lines = ["Directory structure:"]
        
        for dir_path, metadata in directories:
            path_obj = Path(dir_path) if dir_path else Path(".")  # Handle empty string for root
            
            # Show the directory and a few key subdirectories
            display_path = dir_path if dir_path else "[Repository Root]"
            structure_lines.append(f"\n{display_path}/")
            
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
    
    def _parse_tree_line(self, line: str) -> Optional[Dict]:
        """Parse a single tree line to extract directory information"""
        # Skip empty lines or lines without directory markers
        if not line.strip() or '──' not in line:
            return None
        
        # Extract the directory part of the line
        # Look for patterns like "├── directory_name/" or "└── directory_name/"
        match = re.search(r'[├└]──\s*([^/\s\[]+)(?:/)?(?:\s*\[TOC\])?(?:\s*\((\d+)\s*\.md\))?', line)
        if not match:
            return None
        
        name = match.group(1).strip()
        md_count = match.group(2) if match.group(2) else "0"
        has_toc = '[TOC]' in line
        
        # Calculate tree level based on the position of the tree character
        # Find where the ├ or └ character appears
        tree_char_pos = -1
        for i, char in enumerate(line):
            if char in '├└':
                tree_char_pos = i
                break
        
        # Each level is indented by 4 characters ("    " or "│   ")
        # Level 0 = position 0, Level 1 = position 4, Level 2 = position 8, etc.
        level = tree_char_pos // 4 if tree_char_pos >= 0 else 0
        
        return {
            'name': name,
            'level': level,
            'md_count': int(md_count),
            'has_toc': has_toc
        } 