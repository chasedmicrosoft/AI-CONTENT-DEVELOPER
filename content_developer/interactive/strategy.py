"""
Strategy confirmation for content actions
"""
import logging
from typing import Dict, List

from ..models import ContentStrategy
from .generic_interactive import GenericInteractive

logger = logging.getLogger(__name__)


class StrategyConfirmation(GenericInteractive):
    """Confirm content strategy actions"""
    
    def __init__(self, config):
        super().__init__(config, self._format_strategy)
    
    def _format_strategy(self, strategy):
        """Format strategy for display"""
        return f"📋 Content Strategy\n{'-'*50}\n" \
               f"💭 {strategy.summary}\n" \
               f"🎯 Confidence: {strategy.confidence:.0%}\n" \
               f"📊 Actions: {len(strategy.decisions)}"
    
    def _display_actions(self, strategy):
        """Display detailed actions"""
        create_actions = [d for d in strategy.decisions if d.get('action') == 'CREATE']
        update_actions = [d for d in strategy.decisions if d.get('action') == 'UPDATE']
        
        if create_actions:
            print(f"\n✨ CREATE Actions ({len(create_actions)}):")
            for i, action in enumerate(create_actions, 1):
                print(f"\n{i}. {action.get('filename', 'Unknown')}")
                print(f"   Type: {action.get('content_type', 'Unknown')}")
                print(f"   Reason: {action.get('reason', 'No reason')[:100]}...")
                if chunks := action.get('relevant_chunks'):
                    print(f"   References: {len(chunks)} chunks")
        
        if update_actions:
            print(f"\n📝 UPDATE Actions ({len(update_actions)}):")
            for i, action in enumerate(update_actions, 1):
                print(f"\n{i}. {action.get('filename', 'Unknown')}")
                print(f"   Change: {action.get('change_description', 'No description')[:100]}...")
                if sections := action.get('specific_sections'):
                    print(f"   Sections: {', '.join(sections[:3])}")
                if chunks := action.get('relevant_chunks'):
                    print(f"   References: {len(chunks)} chunks")
    
    def _interact(self, result):
        """Interactive strategy confirmation"""
        print(f"\n{self._get_summary(result)}")
        self._display_actions(result)
        
        # Define action handlers
        actions = {
            'y': lambda: result,
            'n': lambda: self._handle_rejection(),
            'd': lambda: self._show_details_and_continue(result)
        }
        
        while True:
            choice = input("\n\nProceed with strategy? (y/n/d for details): ").lower()
            
            handler = actions.get(choice)
            if not handler:
                print("Invalid choice. Please enter y, n, or d.")
                continue
                
            result_or_continue = handler()
            if result_or_continue is not None:
                return result_or_continue
    
    def _handle_rejection(self):
        """Handle strategy rejection"""
        raise SystemExit("Strategy rejected")
    
    def _show_details_and_continue(self, result):
        """Show thinking details and continue loop"""
        print(f"\n💭 Thinking:\n{result.thinking}")
        return None  # Continue the loop
    
    def _manual_selection(self, reason):
        """No manual strategy creation supported"""
        raise SystemExit(f"Cannot manually create strategy: {reason}") 