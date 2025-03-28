# src/looplm/commands/__init__.py

from .processor import CommandProcessor, ProcessingResult
from .registry import CommandRegistry
from .manager import CommandManager

# Create a default instance for easy access
default_manager = CommandManager()

__all__ = [
    'CommandProcessor',
    'ProcessingResult',
    'CommandRegistry',
    'CommandManager',
    'default_manager'
]