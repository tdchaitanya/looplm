# src/looplm/commands/__init__.py

from .processor import CommandProcessor, ProcessingResult
from .registry import CommandRegistry
from .manager import CommandManager
from .file_command import FileProcessor
from .folder_command import FolderProcessor
from .github_command import GithubProcessor
from .shell_command import ShellCommandProcessor
from .image_command import ImageProcessor

default_manager = CommandManager()

__all__ = [
    'CommandProcessor',
    'ProcessingResult',
    'CommandRegistry',
    'CommandManager',
    'default_manager',
    'FileProcessor',
    'FolderProcessor',
    'GithubProcessor',
    'ShellCommandProcessor',
    'ImageProcessor'
]