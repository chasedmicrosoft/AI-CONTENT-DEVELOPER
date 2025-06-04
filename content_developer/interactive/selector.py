"""
Interactive selection utilities
"""
import math
from typing import List, Optional, Dict, Callable, Tuple


class InteractiveSelector:
    """Interactive selection utilities"""
    
    @staticmethod
    def paginated_selection(items: List[str], title: str = "Select Item", page_size: int = 25) -> Optional[str]:
        """Paginated selection from list of items"""
        if not items:
            print("No items to select from")
            return None
        
        selector = PaginatedSelector(items, title, page_size)
        return selector.run()


class PaginatedSelector:
    """Internal class for paginated selection logic"""
    
    def __init__(self, items: List[str], title: str, page_size: int):
        self.items = items
        self.title = title
        self.page_size = page_size
        self.total_pages = math.ceil(len(items) / page_size)
        self.current_page = 0
        
        # Define action handlers
        self.actions: Dict[str, Callable] = {
            'p': self._handle_previous_page,
            'n': self._handle_next_page,
            's': self._handle_search,
            'q': self._handle_quit
        }
    
    def run(self) -> Optional[str]:
        """Run the paginated selection interface"""
        while True:
            self._display_current_page()
            
            choice = input("\nEnter number or option: ").strip().lower()
            
            # Try to handle as number selection first
            result = self._handle_number_selection(choice)
            if result is not None:
                return result
            
            # Try to handle as action
            result = self._handle_action(choice)
            if result is not None:
                return result
            
            # Invalid input
            print("Invalid option")
    
    def _display_current_page(self) -> None:
        """Display current page with items and navigation"""
        page_items = self._get_current_page_items()
        
        self._display_header()
        self._display_items(page_items)
        self._display_navigation()
    
    def _get_current_page_items(self) -> List[str]:
        """Get items for current page"""
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.items))
        return self.items[start_idx:end_idx]
    
    def _display_header(self) -> None:
        """Display page header"""
        print(f"\n{'='*60}")
        print(f"{self.title} (Page {self.current_page + 1}/{self.total_pages})")
        print(f"{'='*60}")
    
    def _display_items(self, page_items: List[str]) -> None:
        """Display items for current page"""
        for index, item in enumerate(page_items, 1):
            print(f"{index:2d}. {item}")
    
    def _display_navigation(self) -> None:
        """Display navigation options"""
        print(f"\n{'='*60}")
        nav_options = self._get_navigation_options()
        print(f"Options: {', '.join(nav_options)}")
        print(f"{'='*60}")
    
    def _get_navigation_options(self) -> List[str]:
        """Get available navigation options"""
        options = []
        
        if self.current_page > 0:
            options.append("p=previous")
        if self.current_page < self.total_pages - 1:
            options.append("n=next")
        
        options.extend(["s=search", "q=quit"])
        return options
    
    def _handle_number_selection(self, choice: str) -> Optional[str]:
        """Handle numeric selection"""
        if not choice.isdigit():
            return None
        
        index = int(choice) - 1
        page_items = self._get_current_page_items()
        
        if 0 <= index < len(page_items):
            return page_items[index]
        
        print("Invalid selection")
        return None
    
    def _handle_action(self, choice: str) -> Optional[str]:
        """Handle action commands"""
        handler = self.actions.get(choice)
        if handler:
            return handler()
        return None
    
    def _handle_previous_page(self) -> None:
        """Handle previous page action"""
        if self.current_page > 0:
            self.current_page -= 1
        return None
    
    def _handle_next_page(self) -> None:
        """Handle next page action"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        return None
    
    def _handle_search(self) -> Optional[str]:
        """Handle search action"""
        return InteractiveSelector.search_and_select(self.items, self.title)
    
    def _handle_quit(self) -> Optional[str]:
        """Handle quit action"""
        return ""  # Return empty string to signal quit
    
    @staticmethod
    def search_and_select(items: List[str], title: str = "Search") -> Optional[str]:
        """Search and select from items"""
        search_term = input("\nEnter search term: ").strip().lower()
        if not search_term:
            return None
        
        # Filter items
        matches = InteractiveSelector._find_matches(items, search_term)
        
        return InteractiveSelector._handle_search_results(matches, title)
    
    @staticmethod
    def _find_matches(items: List[str], search_term: str) -> List[str]:
        """Find items matching search term"""
        return [item for item in items if search_term in item.lower()]
    
    @staticmethod
    def _handle_search_results(matches: List[str], title: str) -> Optional[str]:
        """Handle search results"""
        if not matches:
            print("No matches found")
            return None
        
        if len(matches) == 1:
            return InteractiveSelector._confirm_single_match(matches[0])
        
        print(f"\nFound {len(matches)} matches")
        return InteractiveSelector.paginated_selection(
            matches, 
            f"{title} - Search Results"
        )
    
    @staticmethod
    def _confirm_single_match(match: str) -> Optional[str]:
        """Confirm selection of single match"""
        print(f"Found: {match}")
        if input("Select this? (y/n): ").lower() == 'y':
            return match
        return None 