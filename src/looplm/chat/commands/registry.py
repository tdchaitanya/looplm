# src/looplm/chat/commands/registry.py

from typing import Dict, List, Optional, Type
from pathlib import Path
import re
from .processor import CommandProcessor, ProcessingResult
from .shell_command import ShellCommandProcessor

class CommandRegistry:
    """Registry for command processors"""

    COMMAND_PATTERN = re.compile(r'@(\w+)(?:\s*\(([^)]*)\)|\s+([^\s@]*))')
    SHELL_PATTERN = re.compile(r'\$\((.*?)\)')

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize registry
        
        Args:
            base_path: Base path for resolving relative paths
        """
        self.base_path = base_path or Path.cwd()
        self._processors: Dict[str, CommandProcessor] = {}
        self.shell_processor = ShellCommandProcessor(self.base_path)
        
    def register(self, processor_class: Type[CommandProcessor]) -> None:
        """Register a command processor
        
        Args:
            processor_class: CommandProcessor class to register
        """
        processor = processor_class(self.base_path)
        self._processors[processor.name] = processor

    def get_processor(self, name: str) -> Optional[CommandProcessor]:
        """Get processor by command name
        
        Args:
            name: Command name
            
        Returns:
            CommandProcessor if registered, None otherwise
        """
        return self._processors.get(name)

    async def process_command(self, command: str, arg: str) -> ProcessingResult:
        """Process a single command
        
        Args:
            command: Command name
            arg: Command argument
            
        Returns:
            ProcessingResult with processed content
        """
        processor = self.get_processor(command)
        if not processor:
            return ProcessingResult(
                content="",
                error=f"Unknown command: @{command}"
            )
            
        # Clean up argument - remove quotes and extra whitespace
        arg = arg.strip().strip('"\'')
        
        if not arg:  # Empty argument
            return ProcessingResult(
                content="",
                error=f"No argument provided for @{command}"
            )
            
        if not processor.validate(arg):
            return ProcessingResult(
                content="",
                error=f"Invalid argument for @{command}: {arg}"
            )
            
        return await processor.process(arg)

    def get_completions(self, text: str) -> List[str]:
        """Get completions for current input
        
        Args:
            text: Current input text
            
        Returns:
            List of completion suggestions
        """
        # Extract command if present
        match = re.search(r'@(\w+)(?:\s+|\()(.*?)(?:\)|$)', text)
        if not match:
            # Return list of available commands
            return [f"@{name}" for name in self._processors.keys()]
            
        command, current_arg = match.groups()
        processor = self.get_processor(command)
        if not processor:
            return []
            
        return processor.get_completions(current_arg)

    async def process_text(self, text: str) -> str:
        """Process all commands in text while preserving original
        
        Args:
            text: Input text containing commands
            
        Returns:
            Processed text with commands output appended
        """
        processed_outputs = []
        error_messages = []
        error_found = False
        
        # Start with original text
        result = text + "\n\n"  # Add spacing after original text
        
        # Process shell commands
        for match in self.SHELL_PATTERN.finditer(text):
            command = match.group(1)
            if not command.strip():
                error_messages.append("Empty shell command in $()")
                error_found = True
                continue
                
            processed = await self.shell_processor.process(command)
            
            if processed.error:
                error_found = True
                error_messages.append(f"Shell command error: {processed.error}")
            else:
                processed_outputs.append(processed.content)

        # Process @ commands
        for match in self.COMMAND_PATTERN.finditer(text):
            command = match.group(1)
            # Get argument from either group 2 (parentheses) or group 3 (space-separated)
            arg = match.group(2) if match.group(2) is not None else match.group(3)
            
            processed = await self.process_command(command, arg or '')
            
            if processed.error:
                error_found = True
                error_messages.append(f"@{command} error: {processed.error}")
            else:
                processed_outputs.append(processed.content)
                
        if error_found:
            error_text = "\n".join(error_messages)
            raise Exception(f"Command processing failed:\n{error_text}")
            
        # Add all processed outputs after original text
        result += "\n".join(processed_outputs)
        
        return result