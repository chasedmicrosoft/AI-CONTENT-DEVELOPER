"""
Global step tracker for managing LLM call step numbers
"""
from typing import Dict


class StepTracker:
    """Tracks step numbers globally across all processors"""
    
    def __init__(self):
        self.phase_steps: Dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
        
    def get_next_step(self, phase: int) -> int:
        """Get the next step number for a phase and increment the counter"""
        self.phase_steps[phase] += 1
        return self.phase_steps[phase]
    
    def reset_phase(self, phase: int):
        """Reset step counter for a phase (optional)"""
        self.phase_steps[phase] = 0
    
    def get_current_step(self, phase: int) -> int:
        """Get the current step number without incrementing"""
        return self.phase_steps[phase]


# Global instance
_step_tracker = StepTracker()


def get_step_tracker() -> StepTracker:
    """Get the global step tracker instance"""
    return _step_tracker 