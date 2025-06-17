# src/looplm/commands/__init__.py

from .file_command import FileProcessor
from .folder_command import FolderProcessor
from .github_command import GithubProcessor
from .image_command import ImageProcessor
from .manager import CommandManager
from .pdf_command import PDFProcessor
from .processor import CommandProcessor, ProcessingResult
from .registry import CommandRegistry
from .shell_command import ShellCommandProcessor

default_manager = CommandManager()

__all__ = [
    "CommandProcessor",
    "ProcessingResult",
    "CommandRegistry",
    "CommandManager",
    "default_manager",
    "FileProcessor",
    "FolderProcessor",
    "GithubProcessor",
    "ShellCommandProcessor",
    "ImageProcessor",
    "PDFProcessor",
]
