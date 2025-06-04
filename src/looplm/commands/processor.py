# src/looplm/commands/processor.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ProcessingResult:
    """Result of processing a command"""

    content: str
    error: Optional[str] = None
    metadata: Optional[dict] = None


class CommandProcessor(ABC):
    """Base class for command processors"""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize processor with optional base path"""
        self.base_path = base_path or Path.cwd()

    @abstractmethod
    async def process(self, arg: str) -> ProcessingResult:
        """Process the command argument and return result

        Args:
            arg: Command argument to process

        Returns:
            ProcessingResult containing processed content and any errors
        """

    @abstractmethod
    def validate(self, arg: str) -> bool:
        """Validate the command argument

        Args:
            arg: Command argument to validate

        Returns:
            bool: True if argument is valid
        """

    @abstractmethod
    def get_completions(self, text: str) -> List[str]:
        """Get completion suggestions for the command

        Args:
            text: Current input text

        Returns:
            List of completion suggestions
        """

    def modify_input_text(self, command_name: str, arg: str, full_match: str) -> str:
        """Modify the input text for this command

        This controls how the command is replaced in the input text
        before sending to the LLM.

        Args:
            command_name: Name of the command (without @)
            arg: Command argument
            full_match: The complete command text that matched in the input

        Returns:
            str: Modified text to replace the command in the input

        Note:
            Default implementation returns the full original match (no modification),
            but individual commands can override this for custom behavior.
        """
        return full_match

    @property
    @abstractmethod
    def name(self) -> str:
        """Get command name"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Get command description"""
