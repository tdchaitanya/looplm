"""Base classes and decorators for tool definitions."""

import inspect
import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


class BaseTool(ABC):
    """Base class for all tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters."""

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get the OpenAPI schema for this tool."""


class FunctionTool(BaseTool):
    """Tool implementation for Python functions."""

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or "No description provided"
        self.parameters = parameters or {}

        # Extract parameters from function signature if not provided
        if not self.parameters:
            self.parameters = self._extract_parameters()

    def _extract_parameters(self) -> Dict[str, Any]:
        """Extract parameter schema from function signature."""
        sig = inspect.signature(self.func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_info = {
                "type": "string",  # Default type
                "description": f"Parameter {param_name}",
            }

            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation == list:
                    param_info["type"] = "array"
                elif param.annotation == dict:
                    param_info["type"] = "object"

            properties[param_name] = param_info

            # Mark as required if no default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {"type": "object", "properties": properties, "required": required}

    def execute(self, **kwargs) -> str:
        """Execute the function with given parameters."""
        try:
            result = self.func(**kwargs)

            # Convert result to string
            if isinstance(result, str):
                return result
            elif isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            else:
                return str(result)

        except Exception as e:
            return f"Error executing tool {self.name}: {str(e)}"

    def get_schema(self) -> Dict[str, Any]:
        """Get the OpenAPI schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator to register a function as a tool.

    Args:
        name: Optional custom name for the tool
        description: Optional custom description
        parameters: Optional custom parameter schema

    Example:
        @tool(description="Get the current weather for a location")
        def get_weather(location: str, unit: str = "celsius") -> str:
            # Implementation
            return f"Weather in {location}: 22°{unit}"
    """

    def decorator(func: Callable) -> Callable:
        # Store tool metadata on the function
        func._tool_name = name or func.__name__
        func._tool_description = (
            description or func.__doc__ or "No description provided"
        )
        func._tool_parameters = parameters
        func._is_tool = True

        return func

    return decorator


def create_tool_from_function(func: Callable) -> FunctionTool:
    """Create a FunctionTool from a decorated function."""
    if not hasattr(func, "_is_tool"):
        raise ValueError(f"Function {func.__name__} is not decorated with @tool")

    return FunctionTool(
        func=func,
        name=getattr(func, "_tool_name", None),
        description=getattr(func, "_tool_description", None),
        parameters=getattr(func, "_tool_parameters", None),
    )
