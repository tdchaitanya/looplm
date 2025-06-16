"""Tool registry for managing and discovering tools."""

import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Set

from .base import BaseTool, create_tool_from_function


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._loaded_modules: Set[str] = set()

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool

    def register_function(self, func) -> None:
        """Register a function as a tool."""
        if not hasattr(func, "_is_tool"):
            raise ValueError(f"Function {func.__name__} is not decorated with @tool")

        tool = create_tool_from_function(func)
        self.register_tool(tool)

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tools(self, names: Optional[List[str]] = None) -> Dict[str, BaseTool]:
        """Get tools by names, or all tools if names is None."""
        if names is None:
            return self._tools.copy()

        result = {}
        for name in names:
            if name in self._tools:
                result[name] = self._tools[name]
        return result

    def get_tool_schemas(self, names: Optional[List[str]] = None) -> List[Dict]:
        """Get schemas for tools in litellm format."""
        tools = self.get_tools(names)
        return [tool.get_schema() for tool in tools.values()]

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._loaded_modules.clear()

    def discover_tools_in_directory(self, directory: Path) -> List[str]:
        """Discover and register tools in a directory.

        Returns list of tool names that were registered.
        """
        if not directory.exists() or not directory.is_dir():
            return []

        discovered = []

        # Look for Python files in the directory
        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip private files

            try:
                # Import the module
                module_name = f"looplm.tools.{py_file.stem}"

                if module_name in self._loaded_modules:
                    continue  # Already loaded

                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find all functions decorated with @tool
                    for name, obj in inspect.getmembers(module):
                        if inspect.isfunction(obj) and hasattr(obj, "_is_tool"):
                            try:
                                self.register_function(obj)
                                discovered.append(obj._tool_name or name)
                            except ValueError:
                                # Tool already registered, skip
                                pass

                    self._loaded_modules.add(module_name)

            except Exception as e:
                # Log error but continue with other files
                print(f"Warning: Failed to load tools from {py_file}: {e}")

        return discovered

    def discover_tools_in_module(self, module_name: str) -> List[str]:
        """Discover and register tools in a module.

        Returns list of tool names that were registered.
        """
        if module_name in self._loaded_modules:
            return []

        try:
            module = importlib.import_module(module_name)
            discovered = []

            # Find all functions decorated with @tool
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and hasattr(obj, "_is_tool"):
                    try:
                        self.register_function(obj)
                        discovered.append(obj._tool_name or name)
                    except ValueError:
                        # Tool already registered, skip
                        pass

            self._loaded_modules.add(module_name)
            return discovered

        except ImportError as e:
            print(f"Warning: Failed to import module {module_name}: {e}")
            return []


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry
