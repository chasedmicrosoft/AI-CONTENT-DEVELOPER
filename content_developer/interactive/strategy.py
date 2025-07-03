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
        # Display CREATE actions
        create_actions = [a for a in strategy.decisions if a.action == 'CREATE']
        if create_actions:
            print(f"\n📄 Files to Create ({len(create_actions)}):")
            for i, action in enumerate(create_actions, 1):
                filename = action.filename or action.target_file or 'Unknown'
                content_type = action.content_type or 'Unknown'
                reason = action.reason or action.rationale or 'No reason'
                print(f"\n{i}. {filename}")
                print(f"   Type: {content_type}")
                print(f"   Reason: {reason[:100]}...")
                if action.relevant_chunks:
                    print(f"   Relevant chunks: {len(action.relevant_chunks)}")
        
        # Display UPDATE actions
        update_actions = [a for a in strategy.decisions if a.action == 'UPDATE']
        if update_actions:
            print(f"\n✏️  Files to Update ({len(update_actions)}):")
            for i, action in enumerate(update_actions, 1):
                filename = action.filename or action.target_file or 'Unknown'
                change_desc = action.change_description or action.rationale or 'No description'
                print(f"\n{i}. {filename}")
                print(f"   Change: {change_desc[:100]}...")
                if action.specific_sections:
                    print(f"   Sections: {', '.join(action.specific_sections[:3])}...")
                if action.relevant_chunks:
                    print(f"   Relevant chunks: {len(action.relevant_chunks)}")
    
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