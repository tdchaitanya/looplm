# src/looplm/commands/manager.py
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from .processor import CommandProcessor
from .registry import CommandRegistry


class CommandManager:
    """Central manager for command processing across different CLI modes"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(CommandManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize command manager with registry

        Args:
            base_path: Base path for resolving relative paths in commands
        """
        if self._initialized:
            # Update base_path if provided
            if base_path is not None:
                self.base_path = base_path
                self.registry = CommandRegistry(base_path=self.base_path)
                self._register_default_commands()
            return

        self.base_path = base_path or Path.cwd()
        self.registry = CommandRegistry(base_path=self.base_path)
        self._initialized = True
        self._register_default_commands()

    def _register_default_commands(self):
        """Register default built-in command processors"""
        # Import here to avoid circular imports
        from .file_command import FileProcessor
        from .folder_command import FolderProcessor
        from .github_command import GithubProcessor
        from .image_command import ImageProcessor
        from .pdf_command import PDFProcessor

        # Register default processors
        self.registry.register(FileProcessor)
        self.registry.register(FolderProcessor)
        self.registry.register(GithubProcessor)
        self.registry.register(ImageProcessor)
        self.registry.register(PDFProcessor)
        # Note: ShellCommandProcessor is not explicitly registered as an @ command
        # but is used internally by the registry for handling $() commands

    def register_command(self, processor_class: Type[CommandProcessor]):
        """Register a custom command processor

        Args:
            processor_class: Command processor class to register
        """
        self.registry.register(processor_class)

    def get_processor(self, name: str) -> Optional[CommandProcessor]:
        """Get a processor by name

        Args:
            name: Name of the processor to retrieve

        Returns:
            CommandProcessor if found, None otherwise
        """
        return self.registry.get_processor(name)

    def get_available_commands(self) -> List[str]:
        """Get list of available command names

        Returns:
            List of registered command names
        """
        # Include shell in available commands explicitly
        commands = list(self.registry._processors.keys())
        commands.append("shell")  # Add shell to available commands
        return commands

    async def process_text(self, text: str) -> Tuple[str, List[Dict]]:
        """Process text with all registered commands

        Args:
            text: Input text containing commands

        Returns:
            Tuple of (processed_text, media_metadata)
                - processed_text: Text with command outputs
                - media_metadata: List of media metadata for vision/document models

        Raises:
            Exception: If command processing fails
        """
        return await self.registry.process_text(text)

    def process_text_sync(self, text: str) -> Tuple[str, List[Dict]]:
        """Synchronous wrapper for process_text

        Args:
            text: Input text containing commands

        Returns:
            Tuple of (processed_text, media_metadata)
                - processed_text: Text with command outputs
                - media_metadata: List of media metadata for vision/document models

        Raises:
            Exception: If command processing fails
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.process_text(text))
