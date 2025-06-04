"""
Base interactive confirmation class
"""
import logging
from typing import Any, Optional

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