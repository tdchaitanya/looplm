# src/looplm/commands/registry.py

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from .processor import CommandProcessor, ProcessingResult
from .shell_command import ShellCommandProcessor


class CommandRegistry:
    """Registry for command processors"""

    # COMMAND_PATTERN = re.compile(r"@(\w+)(?:\s*\(([^)]*)\)|\s+([^\s@]*))")
    SHELL_PATTERN = re.compile(r"\$\((.*?)\)")

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

    def _is_valid_command_syntax(self, text: str) -> bool:
        """Check if text contains valid command syntax"""
        # Look for @ followed by word characters and parentheses
        potential_commands = re.findall(r"@(\w+)\s*\(", text)

        for cmd in potential_commands:
            if cmd not in self._processors:
                return False
        return True

    def _get_command_pattern(self) -> re.Pattern:
        """Build pattern that only matches @command(...) for known commands"""
        if not self._processors:
            return re.compile(r"(?!.*)")  # Match nothing

        # Build a pattern that only matches exact registered commands with parentheses
        command_names = "|".join(re.escape(name) for name in self._processors.keys())

        # This pattern is very specific:
        # - @ symbol
        # - One of our registered command names (exact match)
        # - Opening parenthesis directly after the command name (no space)
        # - Any content inside the parentheses
        # - Closing parenthesis
        return re.compile(rf"@({command_names})\(([^)]*)\)")

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
            return ProcessingResult(content="", error=f"Unknown command: @{command}")

        # Clean up argument - remove quotes and extra whitespace
        arg = arg.strip().strip("\"'")

        if not arg:  # Empty argument
            return ProcessingResult(
                content="", error=f"No argument provided for @{command}"
            )

        if not processor.validate(arg):
            return ProcessingResult(
                content="", error=f"Invalid argument for @{command}: {arg}"
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
        match = re.search(r"@(\w+)(?:\s+|\()(.*?)(?:\)|$)", text)
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
            Tuple of (processed_text, list_of_media_metadata)
                - processed_text: Text with commands output appended
                - list_of_media_metadata: List of media metadata for vision/document models
        """
        processed_outputs = []
        media_metadata = []
        error_messages = []

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
                full_match = text[match.start() : match.end()]
                replacement = self.shell_processor.modify_input_text(
                    "shell", command, full_match
                )
                # Replace with the modified text
                # start, end = match.span()
                # modified_text = modified_text[:start] + replacement + modified_text[end:]

        # Process @ commands
        command_pattern = self._get_command_pattern()
        at_matches = list(command_pattern.finditer(text))
        for match in at_matches:
            command = match.group(1)
            arg = match.group(2)

            processed = await self.process_command(command, arg)
            if processed.error:
                error_messages.append(f"@{command} error: {processed.error}")
            else:
                processed_outputs.append(processed.content)
                if command in ["image", "pdf"] and processed.metadata:
                    media_metadata.append(processed.metadata)

                # Replace command with modified text
                full_match = text[match.start() : match.end()]
                processor = self.get_processor(command)
                replacement = processor.modify_input_text(command, arg, full_match)
                start, end = match.span()
                modified_text = (
                    modified_text[:start] + replacement + modified_text[end:]
                )

        if error_messages:
            raise Exception("Command processing failed:\n" + "\n".join(error_messages))

        # Combine results
        result = modified_text
        if processed_outputs:
            result += "\n\n" + "\n".join(processed_outputs)

        return result, media_metadata
