# src/looplm/chat/commands/processor.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Any
from pathlib import Path

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
        pass

    @abstractmethod
    def validate(self, arg: str) -> bool:
        """Validate the command argument
        
        Args:
            arg: Command argument to validate
            
        Returns:
            bool: True if argument is valid
        """
        pass
    
    @abstractmethod
    def get_completions(self, text: str) -> List[str]:
        """Get completion suggestions for the command
        
        Args:
            text: Current input text
            
        Returns:
            List of completion suggestions
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get command name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get command description"""
        pass