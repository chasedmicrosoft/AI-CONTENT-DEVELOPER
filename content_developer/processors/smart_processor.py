"""
Base processor class for AI Content Developer
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import write, save_json, mkdir
from ..utils.step_tracker import get_step_tracker


class SmartProcessor:
    """Base class for all content processors"""
    
    def __init__(self, client, config, console_display=None):
        """Initialize processor with OpenAI client and config"""
        self.client = client
        self.config = config
        self.console_display = console_display
        self.current_phase = None
        self.current_step = None
    
    def set_phase_step(self, phase: int, step: int):
        """Set current phase and step for directory organization"""
        self.current_phase = phase
        self.current_step = step
    
    def process(self, *args, **kwargs):
        """Public process method"""
        return self._process(*args, **kwargs)
    
    def _process(self, *args, **kwargs):
        """Abstract method to be implemented by subclasses"""
        raise NotImplementedError
    
    def llm_call(self, system: str, user: str, model: str = None, 
                 operation_name: str = None) -> Dict:
        """Make LLM API call with JSON response format"""
        # Show operation if console display available
        if self.console_display and operation_name:
            self.console_display.show_operation(f"Calling LLM for {operation_name}")
        
        # Use configured completion model if not specified
        if model is None:
            model = self.config.completion_model
            
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=self.config.temperature,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Automatically save ALL LLM interactions for complete observability
        if operation_name:
            # Use phase/step directory structure
            output_dir = self._determine_phase_step_directory()
            
            # Save the interaction
            self.save_interaction(
                prompt=user,
                response=result,
                operation=operation_name,
                output_dir=output_dir,
                source=operation_name.replace(" ", "_").lower()
            )
        
        return result
    
    def _call_llm(self, messages: List[Dict[str, str]], 
                  model: str = None, 
                  response_format: Optional[str] = None,
                  operation_name: str = None) -> Dict:
        """Make LLM API call with messages format
        
        Used by generation processors for more control over conversation
        """
        # Show operation if console display available
        if self.console_display and operation_name:
            self.console_display.show_operation(f"Calling LLM for {operation_name}")
        
        # Use configured model if not specified
        if model is None:
            model = self.config.completion_model
            
        kwargs = self._build_llm_kwargs(messages, model, response_format)
        response = self.client.chat.completions.create(**kwargs)
        
        result = self._parse_llm_response(response, response_format)
        
        # Automatically save ALL LLM interactions for complete observability
        if operation_name:
            # Use phase/step directory structure
            output_dir = self._determine_phase_step_directory()
            
            # Extract prompt from messages
            prompt = self._extract_prompt_from_messages(messages)
            
            # Save the interaction
            self.save_interaction(
                prompt=prompt,
                response=result,
                operation=operation_name,
                output_dir=output_dir,
                source=operation_name.replace(" ", "_").lower()
            )
        
        return result
    
    def _determine_phase_step_directory(self) -> str:
        """Determine directory based on current phase and step"""
        if self.current_phase is not None:
            # Get next step from global tracker
            step_tracker = get_step_tracker()
            step = step_tracker.get_next_step(self.current_phase)
            
            # Use the step for this LLM call
            directory = f"./llm_outputs/phase-{self.current_phase:02d}/step-{step:02d}"
            
            return directory
        else:
            # Fallback if phase not set (shouldn't happen in normal operation)
            return "./llm_outputs/untracked"
    
    def _extract_prompt_from_messages(self, messages: List[Dict[str, str]]) -> str:
        """Extract prompt content from messages format"""
        prompt_parts = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role and content:
                prompt_parts.append(f"=== {role.upper()} ===")
                prompt_parts.append(content)
                prompt_parts.append("")
        
        return "\n".join(prompt_parts)
    

    
    def _build_llm_kwargs(self, messages: List[Dict[str, str]], model: str, 
                         response_format: Optional[str]) -> Dict:
        """Build keyword arguments for LLM call"""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": self.config.temperature
        }
        
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}
        
        return kwargs
    
    def _parse_llm_response(self, response, response_format: Optional[str]) -> Dict:
        """Parse LLM response based on expected format"""
        content = response.choices[0].message.content
        
        if response_format == "json_object":
            return json.loads(content)
        
        return {"content": content}
    
    def save_interaction(self, prompt: str, response: Any, operation: str, 
                        output_dir: str, source: str = ""):
        """Save LLM interaction for debugging and auditing"""
        # Prepare file paths
        base_path = self._prepare_output_path(output_dir, operation, source)
        
        # Save both prompt and response
        self._save_prompt_to_file(base_path, prompt, operation)
        self._save_response_to_file(base_path, response, operation)
    
    def _prepare_output_path(self, output_dir: str, operation: str, source: str) -> Path:
        """Prepare output directory and return base path for files"""
        # Ensure output directory exists
        self._ensure_directory_exists(output_dir)
        
        # Generate filename components
        timestamp = self._generate_timestamp()
        safe_source = self._sanitize_source_name(source, operation)
        
        # Construct base path
        return Path(output_dir) / f"{timestamp}_{safe_source}"
    
    def _ensure_directory_exists(self, directory: str) -> None:
        """Create directory if it doesn't exist"""
        mkdir(directory)
    
    def _generate_timestamp(self) -> str:
        """Generate timestamp for file naming"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _sanitize_source_name(self, source: str, fallback: str) -> str:
        """Sanitize source name for safe file naming"""
        if not source:
            return fallback
        
        # Remove unsafe characters and limit length
        # Simple character replacement instead of regex
        safe_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_- '
        safe_name = ''.join(c if c in safe_chars else '_' for c in source)
        return safe_name[:50]
    
    def _save_prompt_to_file(self, base_path: Path, prompt: str, operation: str) -> None:
        """Save prompt content to text file"""
        prompt_content = self._format_prompt_content(prompt, operation)
        write(base_path.with_suffix('.txt'), prompt_content)
    
    def _save_response_to_file(self, base_path: Path, response: Any, operation: str) -> None:
        """Save response data to JSON file"""
        response_data = self._format_response_data(response, operation)
        save_json(base_path.with_suffix('.json'), response_data)
    
    def _format_prompt_content(self, prompt: str, operation: str) -> str:
        """Format prompt content with metadata header"""
        header = f"=== {operation.upper()} ===\n"
        header += f"{datetime.now().isoformat()}\n"
        header += f"{'='*50}\n\n"
        return header + prompt
    
    def _format_response_data(self, response: Any, operation: str) -> Dict[str, Any]:
        """Format response data with metadata"""
        return {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "operation": operation
                },
                "data": response
            }