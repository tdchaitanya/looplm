# src/looplm/commands/registry.py

from typing import Dict, List, Optional, Type, Tuple
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
        # Create shell processor but don't register it as an @ command
        # We'll still use it for processing $() commands
        self.shell_processor = ShellCommandProcessor(self.base_path)
        
    def register(self, processor_class: Type[CommandProcessor]) -> None:
        """Register a command processor
        
        Args:
            processor_class: CommandProcessor class to register
        """
        processor = processor_class(self.base_path)
        # Skip registering the shell processor as @shell
        if processor.name != "shell":
            self._processors[processor.name] = processor

    def get_processor(self, name: str) -> Optional[CommandProcessor]:
        """Get processor by command name
        
        Args:
            name: Command name
            
        Returns:
            CommandProcessor if registered, None otherwise
        """
        if name == "shell":
            return self.shell_processor
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

    async def process_text(self, text: str) -> Tuple[str, List[Dict]]:
        """Process all commands in text while preserving original
        
        Args:
            text: Input text containing commands
        
        Returns:
            Tuple of (processed_text, list_of_image_metadata)
                - processed_text: Text with commands output appended
                - list_of_image_metadata: List of image metadata for vision models
        """
        processed_outputs = []
        image_metadata = []
        error_messages = []
        error_found = False
        
        modified_text = text

        # Process shell commands
        shell_matches = list(self.SHELL_PATTERN.finditer(text))
        for match in shell_matches:
            command = match.group(1)
            full_match = match.group(0)

            if not command.strip():
                error_messages.append("Empty shell command in $()")
                error_found = True
                continue
                
            # Process shell command using the shell processor
            processed = await self.shell_processor.process(command)
            
            if processed.error:
                error_found = True
                error_messages.append(f"Shell command error: {processed.error}")
            else:
                processed_outputs.append(processed.content)
                
                # Get the full match for shell command
                full_match = text[match.start():match.end()]
                replacement = self.shell_processor.modify_input_text("shell", command, full_match)
                # Replace with the modified text
                # start, end = match.span()
                # modified_text = modified_text[:start] + replacement + modified_text[end:]

        # Process @ commands
        at_matches = list(self.COMMAND_PATTERN.finditer(text))
        for match in at_matches:
            command = match.group(1)
            # Get argument from either group 2 (parentheses) or group 3 (space-separated)
            arg = match.group(2) if match.group(2) is not None else match.group(3)
                        
            arg = arg or ""
            
            processor = self.get_processor(command)
            if not processor:
                error_messages.append(f"Unknown command: @{command}")
                error_found = True
                continue
            processed = await self.process_command(command, arg)

            if processed.error:
                error_found = True
                error_messages.append(f"@{command} error: {processed.error}")
            else:
                processed_outputs.append(processed.content)
                # Check if this is an image command with metadata
                if command == "image" and processed.metadata:
                    image_metadata.append(processed.metadata)

                # Get the modified input text from the processor
                # Get the modified input text from the processor
                full_match = text[match.start():match.end()]
                replacement = processor.modify_input_text(command, arg, full_match)

                # Replace the entire match with the modified text
                start, end = match.span()
                modified_text = modified_text[:start] + replacement + modified_text[end:]
                
                
        if error_found:
            error_text = "\n".join(error_messages)
            raise Exception(f"Command processing failed:\n{error_text}")
            
        # Use the modified text as the base, then add processed outputs at the end
        result = modified_text
        if processed_outputs:
            result += "\n\n" + "\n".join(processed_outputs)
        
        return result, image_metadata