"""Tool manager for handling tool execution and safety."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import litellm
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .registry import ToolRegistry, get_registry


def get_user_tools_directory() -> Path:
    """Get the user tools directory, creating it if it doesn't exist."""
    user_config_dir = Path.home() / ".looplm"
    tools_dir = user_config_dir / "tools"

    # Create the directory structure if it doesn't exist
    tools_dir.mkdir(parents=True, exist_ok=True)

    # Create an __init__.py file if it doesn't exist
    init_file = tools_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""User-defined tools for LoopLM."""\n')

    # Create a sample tool file if no tools exist yet
    sample_file = tools_dir / "sample_tools.py"
    if not sample_file.exists() and not any(tools_dir.glob("*.py")):
        sample_content = '''"""Sample custom tools for LoopLM.

This file demonstrates how to create custom tools. You can:
1. Add new tools to this file
2. Create new .py files in this directory
3. Import and use any Python libraries you need

To get started, uncomment the sample tools below or create your own!
"""

from looplm.tools.base import tool

# Uncomment to enable sample tools:

# @tool(description="Convert text to uppercase")
# def to_uppercase(text: str) -> str:
#     """Convert the given text to uppercase."""
#     return text.upper()

# @tool(description="Count words in text")
# def count_words(text: str) -> str:
#     """Count the number of words in the given text."""
#     word_count = len(text.split())
#     return f"The text contains {word_count} words."

# @tool(description="Generate a simple greeting")
# def greet_user(name: str = "User") -> str:
#     """Generate a personalized greeting."""
#     return f"Hello, {name}! Nice to meet you!"
'''
        sample_file.write_text(sample_content)

    return tools_dir


class ToolManager:
    """Manages tool execution with safety checks and user approval."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        console: Optional[Console] = None,
        require_approval: bool = False,
        auto_discover: bool = True,
        discover_user_tools: bool = True,
    ):
        """Initialize tool manager.

        Args:
            registry: Tool registry to use (default: global registry)
            console: Rich console for output (default: create new)
            require_approval: Whether to require human approval for tool execution
            auto_discover: Whether to auto-discover built-in tools on initialization
            discover_user_tools: Whether to auto-discover user tools from ~/.looplm/tools/
        """
        self.registry = registry or get_registry()
        self.console = console or Console()
        self.require_approval = require_approval
        self.user_tools_dir = get_user_tools_directory()

        if auto_discover:
            discovered_builtin = self.discover_default_tools()
            discovered_user = []

            if discover_user_tools:
                discovered_user = self.discover_user_tools()

            total_discovered = len(discovered_builtin) + len(discovered_user)
            if total_discovered > 0:
                sources = []
                if discovered_builtin:
                    sources.append(f"{len(discovered_builtin)} built-in")
                if discovered_user:
                    sources.append(f"{len(discovered_user)} user-defined")

                self.console.print(
                    f"🔧 Discovered {total_discovered} tools: {', '.join(sources)}",
                    style="dim blue",
                )

    def discover_default_tools(self) -> List[str]:
        """Discover tools in the default built-in tools directory."""
        tools_dir = Path(__file__).parent / "builtin"
        discovered = []

        if tools_dir.exists():
            discovered = self.registry.discover_tools_in_directory(tools_dir)

        return discovered

    def discover_user_tools(self) -> List[str]:
        """Discover tools in the user tools directory (~/.looplm/tools/)."""
        if not self.user_tools_dir.exists():
            return []

        discovered = []

        # Add user tools directory to Python path temporarily
        import sys

        user_tools_parent = str(self.user_tools_dir.parent)
        if user_tools_parent not in sys.path:
            sys.path.insert(0, user_tools_parent)

        try:
            discovered = self.registry.discover_tools_in_directory(self.user_tools_dir)
        finally:
            # Clean up path
            if user_tools_parent in sys.path:
                sys.path.remove(user_tools_parent)

        return discovered

    def get_user_tools_directory_path(self) -> str:
        """Get the path to the user tools directory for display purposes."""
        return str(self.user_tools_dir)

    def create_sample_tool(self, tool_name: str, description: str) -> bool:
        """Create a sample tool file in the user tools directory.

        Args:
            tool_name: Name of the tool function
            description: Description of what the tool does

        Returns:
            True if successfully created, False otherwise
        """
        try:
            filename = f"{tool_name}_tool.py"
            tool_file = self.user_tools_dir / filename

            if tool_file.exists():
                self.console.print(
                    f"Tool file {filename} already exists", style="yellow"
                )
                return False

            template = f'''"""Custom tool: {tool_name}

Created by LoopLM tool generator.
"""

from looplm.tools.base import tool

@tool(description="{description}")
def {tool_name}(param: str) -> str:
    """Implementation for {tool_name}.

    Args:
        param: Input parameter (customize as needed)

    Returns:
        Result string (customize as needed)
    """
    # TODO: Implement your tool logic here
    return f"Tool {tool_name} executed with parameter: {{param}}"
'''

            tool_file.write_text(template)
            self.console.print(f"✅ Created sample tool at: {tool_file}", style="green")
            self.console.print(
                "Edit this file to implement your tool logic, then restart LoopLM to use it.",
                style="dim",
            )
            return True

        except Exception as e:
            self.console.print(f"Error creating tool file: {e}", style="red")
            return False

    def load_tools_from_directory(self, directory: Path) -> List[str]:
        """Load tools from a specific directory."""
        return self.registry.discover_tools_in_directory(directory)

    def load_tools_from_names(self, tool_names: List[str]) -> List[str]:
        """Load specific tools by name from the registry."""
        available = self.registry.list_tools()
        loaded = []

        for name in tool_names:
            if name in available:
                loaded.append(name)
            else:
                self.console.print(
                    f"⚠️ Tool '{name}' not found in registry", style="yellow"
                )

        return loaded

    def check_model_compatibility(self, model: str) -> bool:
        """Check if a model supports function calling."""
        try:
            return litellm.supports_function_calling(model=model)
        except Exception as e:
            self.console.print(
                f"Warning: Unable to check function calling support for {model}: {e}",
                style="yellow",
            )
            return False

    def get_available_tools(self, tool_names: Optional[List[str]] = None) -> Dict:
        """Get available tools for the current session."""
        return self.registry.get_tools(tool_names)

    def get_tool_schemas(self, tool_names: Optional[List[str]] = None) -> List[Dict]:
        """Get tool schemas in litellm format."""
        return self.registry.get_tool_schemas(tool_names)

    def display_available_tools(self, tool_names: Optional[List[str]] = None) -> None:
        """Display available tools in a nice table."""
        tools = self.get_available_tools(tool_names)

        if not tools:
            self.console.print("No tools available", style="yellow")
            return

        table = Table(
            title="🔧 Available Tools", show_header=True, header_style="bold blue"
        )
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")

        for tool in tools.values():
            table.add_row(tool.name, tool.description)

        self.console.print(table)

    def execute_tool_call(
        self, tool_call_id: str, function_name: str, arguments: str
    ) -> Tuple[str, str]:
        """Execute a tool call and return the result.

        Args:
            tool_call_id: The tool call ID from the LLM
            function_name: Name of the function to call
            arguments: JSON string of arguments

        Returns:
            Tuple of (tool_call_id, result)
        """
        tool = self.registry.get_tool(function_name)
        if not tool:
            return tool_call_id, f"Error: Tool '{function_name}' not found"

        try:
            # Parse arguments
            args = json.loads(arguments)

            # Display tool execution info
            self._display_tool_execution(function_name, args)

            # Check for approval if required
            if self.require_approval:
                if not self._get_user_approval(function_name, args):
                    return tool_call_id, "Tool execution cancelled by user"

            # Execute tool
            result = tool.execute(**args)

            # Display result
            self._display_tool_result(function_name, result)

            return tool_call_id, result

        except json.JSONDecodeError as e:
            error_msg = f"Error: Invalid JSON arguments for {function_name}: {e}"
            self.console.print(error_msg, style="red")
            return tool_call_id, error_msg

        except Exception as e:
            error_msg = f"Error executing {function_name}: {str(e)}"
            self.console.print(error_msg, style="red")
            return tool_call_id, error_msg

    def _display_tool_execution(self, function_name: str, args: Dict) -> None:
        """Display tool execution info."""
        args_str = json.dumps(args, indent=2) if args else "No arguments"

        panel = Panel(
            f"[bold cyan]Function:[/bold cyan] {function_name}\n"
            f"[bold cyan]Arguments:[/bold cyan]\n{args_str}",
            title="🔧 Tool Execution",
            title_align="left",
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(panel)

    def _display_tool_result(self, function_name: str, result: str) -> None:
        """Display tool execution result."""
        # Truncate very long results for display
        display_result = result
        if len(result) > 500:
            display_result = result[:500] + "\n... (truncated)"

        panel = Panel(
            display_result,
            title=f"✅ Tool Result: {function_name}",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(panel)

    def _get_user_approval(self, function_name: str, args: Dict) -> bool:
        """Get user approval for tool execution."""
        self.console.print(
            f"\n[yellow]⚠️ Tool '{function_name}' is requesting execution with arguments: {args}[/yellow]"
        )

        while True:
            response = (
                input("Do you want to proceed? (y/n/d for details): ").strip().lower()
            )

            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            elif response in ["d", "details"]:
                tool = self.registry.get_tool(function_name)
                if tool:
                    self.console.print(f"\n[bold]Tool:[/bold] {tool.name}")
                    self.console.print(f"[bold]Description:[/bold] {tool.description}")
                    schema = tool.get_schema()
                    if "function" in schema and "parameters" in schema["function"]:
                        params = schema["function"]["parameters"]
                        self.console.print(
                            f"[bold]Parameters:[/bold] {json.dumps(params, indent=2)}"
                        )
                    self.console.print()
            else:
                self.console.print(
                    "Please enter 'y' for yes, 'n' for no, or 'd' for details."
                )

    def set_approval_mode(self, require_approval: bool) -> None:
        """Set whether to require approval for tool execution."""
        self.require_approval = require_approval
        mode_str = "enabled" if require_approval else "disabled"
        self.console.print(f"Tool approval mode {mode_str}", style="blue")
