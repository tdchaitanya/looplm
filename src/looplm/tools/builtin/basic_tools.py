"""Basic built-in tools for LoopLM."""

import os
import platform
from datetime import datetime
from pathlib import Path

from looplm.tools.base import tool


@tool(description="Get the current date and time")
def get_current_time() -> str:
    """Get the current date and time in a human-readable format."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")


@tool(description="Get information about the current working directory")
def get_current_directory() -> str:
    """Get the current working directory path."""
    return str(Path.cwd())


@tool(description="List files and directories in a given path")
def list_directory(path: str = ".") -> str:
    """List the contents of a directory.

    Args:
        path: The directory path to list (defaults to current directory)
    """
    try:
        target_path = Path(path).expanduser().resolve()

        if not target_path.exists():
            return f"Error: Path '{path}' does not exist"

        if not target_path.is_dir():
            return f"Error: Path '{path}' is not a directory"

        items = []
        for item in sorted(target_path.iterdir()):
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size // 1024}KB"
                else:
                    size_str = f"{size // (1024 * 1024)}MB"
                items.append(f"📄 {item.name} ({size_str})")

        if not items:
            return f"Directory '{path}' is empty"

        return f"Contents of '{path}':\n" + "\n".join(items)

    except PermissionError:
        return f"Error: Permission denied accessing '{path}'"
    except Exception as e:
        return f"Error listing directory '{path}': {str(e)}"


@tool(description="Read the contents of a text file")
def read_file(file_path: str, max_lines: int = 100) -> str:
    """Read the contents of a text file.

    Args:
        file_path: Path to the file to read
        max_lines: Maximum number of lines to read (default: 100)
    """
    try:
        target_path = Path(file_path).expanduser().resolve()

        if not target_path.exists():
            return f"Error: File '{file_path}' does not exist"

        if not target_path.is_file():
            return f"Error: '{file_path}' is not a file"

        # Check file size (limit to 1MB)
        if target_path.stat().st_size > 1024 * 1024:
            return f"Error: File '{file_path}' is too large (>1MB)"

        with target_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... (truncated after {max_lines} lines)")
                    break
                lines.append(line.rstrip())

        return f"Contents of '{file_path}':\n" + "\n".join(lines)

    except PermissionError:
        return f"Error: Permission denied reading '{file_path}'"
    except UnicodeDecodeError:
        return f"Error: '{file_path}' is not a text file or uses unsupported encoding"
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


@tool(description="Get system information")
def get_system_info() -> str:
    """Get basic system information including OS, Python version, etc."""
    info = {
        "Operating System": platform.system(),
        "OS Version": platform.version(),
        "Architecture": platform.machine(),
        "Processor": platform.processor(),
        "Python Version": platform.python_version(),
        "Hostname": platform.node(),
        "Current User": os.getenv("USER") or os.getenv("USERNAME") or "Unknown",
    }

    result = "System Information:\n"
    for key, value in info.items():
        result += f"  {key}: {value}\n"

    return result.strip()


@tool(description="Execute a simple calculator operation")
def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression.

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 3 * 4")
    """
    try:
        # Only allow basic mathematical operations for safety
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Expression contains invalid characters. Only numbers, +, -, *, /, ., (, ), and spaces are allowed."

        # Use eval with restricted namespace for safety
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{expression} = {result}"

    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error evaluating expression '{expression}': {str(e)}"


@tool(description="Create a simple text file")
def create_file(file_path: str, content: str) -> str:
    """Create a text file with the given content.

    Args:
        file_path: Path where to create the file
        content: Content to write to the file
    """
    try:
        target_path = Path(file_path).expanduser().resolve()

        # Safety check: don't overwrite existing files without explicit confirmation
        if target_path.exists():
            return f"Error: File '{file_path}' already exists. Use a different name or delete the existing file first."

        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with target_path.open("w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully created file '{file_path}' with {len(content)} characters"

    except PermissionError:
        return f"Error: Permission denied creating file '{file_path}'"
    except Exception as e:
        return f"Error creating file '{file_path}': {str(e)}"
