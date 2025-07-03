"""
Base interactive confirmation class
"""
import logging
from typing import Any, Optional, List

from ..models import Config

logger = logging.getLogger(__name__)


class GenericInteractive:
    """Base class for interactive confirmations"""
    
    def __init__(self, config, formatter=None):
        self.config = config
        self.formatter = formatter or (lambda x: str(x))
    
    def confirm(self, result, failed=False, error=""):
        """Confirm result with user"""
        if self.config.auto_confirm and not failed:
            return result
        
        if failed:
            return self._handle_failure(error)
        
        return self._interact(result)
    
    def _get_summary(self, result):
        """Get summary of result"""
        return self.formatter(result)
    
    def _handle_failure(self, error):
        """Handle failure case"""
        print(f"\n❌ Operation failed: {error}")
        return self._manual_selection("Operation failed")
    
    def _interact(self, result):
        """Interactive confirmation"""
        print(f"\n{self._get_summary(result)}")
        
        # Define action handlers
        actions = {
            'y': lambda: result,
            'n': lambda: self._handle_cancellation(),
            'm': lambda: self._handle_manual_request()
        }
        
        while True:
            choice = input("\nAccept? (y/n/m for manual): ").lower()
            
            handler = actions.get(choice)
            if not handler:
                print("Invalid choice. Please enter y, n, or m.")
                continue
            
            return handler()
    
    def _handle_cancellation(self):
        """Handle operation cancellation"""
        raise SystemExit("Operation cancelled")
    
    def _handle_manual_request(self):
        """Handle manual selection request"""
        return self._manual_selection("User requested manual selection")
    
    def _manual_selection(self, reason):
        """Override in subclasses"""
        raise NotImplementedError("Subclass must implement _manual_selection")
    
    def prompt_user(self, config: Config, options: List) -> Optional[str]:
        """Prompt user for selection with pagination support"""
        if not options:
            return None
        
        page_size = 10
        current_page = 0
        total_pages = (len(options) - 1) // page_size + 1
        
        while True:
            # Calculate page boundaries
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(options))
            page_options = options[start_idx:end_idx]
            
            # Display options
            print(f"\n📁 Available Directories (Page {current_page + 1}/{total_pages}):")
            print("─" * 60)
            
            for i, option in enumerate(page_options, 1):
                # Handle both string and tuple formats
                if isinstance(option, tuple):
                    path, metadata = option
                    md_count = metadata.get('md_count', 0)
                    has_toc = metadata.get('has_toc', False)
                    
                    # Format the display - handle empty string as repository root
                    display_path = path if path else "[Repository Root]"
                    display = f"{i:2d}. {display_path}"
                    if md_count > 0:
                        display += f" ({md_count} .md)"
                    if has_toc:
                        display += " [TOC]"
                    print(display)
                else:
                    # Fallback for string options
                    print(f"{i:2d}. {option}")
            
            print("─" * 60)
            
            # Show navigation options
            nav_options = []
            if current_page > 0:
                nav_options.append("'p' for previous")
            if current_page < total_pages - 1:
                nav_options.append("'n' for next")
            nav_options.append("'q' to quit")
            
            print(f"\nOptions: {', '.join(nav_options)}")
            print(f"Enter number (1-{len(page_options)}): ", end='')
            
            choice = input().strip().lower()
            
            # Handle navigation
            if choice == 'p' and current_page > 0:
                current_page -= 1
                continue
            elif choice == 'n' and current_page < total_pages - 1:
                current_page += 1
                continue
            elif choice == 'q':
                return None
            
            # Handle numeric selection
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(page_options):
                    selected = page_options[idx]
                    # Extract path from tuple if needed
                    if isinstance(selected, tuple):
                        return selected[0]  # Return just the path
                    return selected
                else:
                    print("❌ Invalid selection. Please try again.")
            except ValueError:
                print("❌ Please enter a number, 'p', 'n', or 'q'.") 