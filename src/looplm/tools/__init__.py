"""Tool calling functionality for LoopLM.

This module provides:
- Tool discovery and registration
- Tool execution with safety checks
- Integration with litellm for function calling
"""

from .base import BaseTool, tool
from .manager import ToolManager
from .registry import ToolRegistry, get_registry

__all__ = ["ToolManager", "ToolRegistry", "BaseTool", "tool", "get_registry"]
