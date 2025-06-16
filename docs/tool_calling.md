# Tool Calling in LoopLM

LoopLM supports **ReACT (Reasoning and Acting)** style tool calling, enabling LLMs to perform complex multi-step problem solving by iteratively using tools based on reasoning and observations.

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Chat Commands](#chat-commands)
- [Built-in Tools](#built-in-tools)
- [Custom Tools](#custom-tools)
- [Model Compatibility](#model-compatibility)
- [Safety Features](#safety-features)
- [Advanced Usage](#advanced-usage)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

### ReACT Pattern

LoopLM implements the ReACT pattern for intelligent tool usage:

1. **🤔 REASON**: LLM analyzes the problem and available tools
2. **🔧 ACT**: LLM calls one or more tools to gather information
3. **👁️ OBSERVE**: LLM processes the tool results
4. **🔄 REPEAT**: LLM can reason about results and call more tools if needed
5. **✅ RESPOND**: LLM provides final answer when it has sufficient information

This enables:
- **Multi-step reasoning**: Break complex problems into manageable steps
- **Adaptive tool usage**: Choose tools based on previous results
- **Parallel execution**: Call multiple tools simultaneously when appropriate
- **Sequential problem solving**: Use tool results to inform next actions
- **Natural conversation flow**: Seamless integration of tool usage

### Example: ReACT in Action

**Query**: *"List files in current directory, then read the first Python file you find"*

**ReACT Flow**:
```
🤔 LLM Reasons: "I need to see what files are available first"
🔧 LLM Acts: Calls list_directory('.')
👁️ LLM Observes: Gets ['app.py', 'test.py', 'README.md', 'data.json']
🤔 LLM Reasons: "I see Python files. Let me read app.py first."
🔧 LLM Acts: Calls read_file('app.py')
👁️ LLM Observes: Gets file contents
✅ LLM Responds: "Found 4 files including 2 Python files. Here's app.py: [content analysis]"
```

**Simple Query**: *"What's the current time and calculate 15 * 23?"*

**Parallel ReACT Flow**:
```
🤔 LLM Reasons: "I need both current time AND a calculation"
🔧 LLM Acts: Calls get_current_time() AND calculate('15 * 23') in parallel
👁️ LLM Observes: Gets time='2025-01-15 14:30:22' and result='345'
✅ LLM Responds: "The current time is 2:30 PM and 15 × 23 = 345"
```

## Quick Start

### CLI Usage

Enable tools for a single command:
```bash
# Enable all available tools (built-in + custom)
looplm --tools all "What's 123 + 456?"

# Enable specific tools
looplm --tools calculate,get_current_time "What time is it and what's 50 * 2?"

# Enable tools with approval mode (requires confirmation before execution)
looplm --tools-approval --tools all "Create a file called test.txt"
```

### Chat Mode Usage

Start chat with tools enabled:
```bash
# Enable all tools (auto-discovers built-in and custom tools)
looplm chat --tools all

# Enable specific tools
looplm chat --tools calculate,read_file,my_custom_tool

# Enable with approval mode for safety
looplm chat --tools all --tools-approval
```

## Chat Commands

### Tool Management Commands

Within chat mode, you can manage tools dynamically:

| Command | Description |
|---------|-------------|
| `/tools` | Show all tool management commands |
| `/tools-list` | List all available tools (built-in + custom) |
| `/tools-enable all` | Enable all discovered tools |
| `/tools-enable tool1,tool2` | Enable specific tools |
| `/tools-disable` | Disable all tools |
| `/tools-approval` | Toggle approval mode on/off |

### Custom Tool Commands

**NEW**: Commands for managing custom tools:

| Command | Description |
|---------|-------------|
| `/tools-dir` | Show your custom tools directory path |
| `/tools-create <name> [description]` | Create a new custom tool template |
| `/tools-reload` | Reload tools from directories |

### Example Workflow
```bash
# Start chat with tools
looplm chat --tools all

# Check what tools are available
/tools-list

# Find your custom tools directory
/tools-dir

# Create a new tool
/tools-create weather_checker "Get weather information for cities"

# Edit the generated file, then reload
/tools-reload

# Now use your custom tool!
"What's the weather like in San Francisco?"
```

## Built-in Tools

LoopLM comes with several built-in tools that are automatically discovered:

### System & File Operations
- **`get_current_time`** - Get current date and time
- **`get_current_directory`** - Get current working directory path
- **`get_system_info`** - Get system information (OS, CPU, memory)
- **`list_directory`** - List files and directories with sizes
- **`read_file`** - Read text file contents (with safety limits)
- **`create_file`** - Create new text files

### Utilities
- **`calculate`** - Safely evaluate mathematical expressions

Built-in tools are automatically loaded and available immediately when you enable tools.

## Custom Tools

### Overview

LoopLM supports user-defined custom tools stored in `~/.looplm/tools/`. This directory is:
- **Portable**: Survives LoopLM updates and reinstalls
- **User-specific**: Each user has their own tools
- **Auto-discovered**: Custom tools are automatically found and loaded
- **Shareable**: Easy to backup, version control, or share with team members

### Quick Start with Custom Tools

#### Method 1: Using Built-in Commands (Recommended)

1. **Start chat with tools enabled:**
   ```bash
   looplm chat --tools all
   ```

2. **Find your tools directory:**
   ```
   /tools-dir
   ```
   Output: `User tools directory: /Users/username/.looplm/tools`

3. **Create a new tool template:**
   ```
   /tools-create weather_checker "Get weather information for a city"
   ```
   Creates: `~/.looplm/tools/weather_checker_tool.py`

4. **Edit the generated file** with your custom logic

5. **Reload tools:**
   ```
   /tools-reload
   ```

#### Method 2: Manual Creation

1. **Navigate to your tools directory:**
   ```bash
   cd ~/.looplm/tools/
   ```

2. **Create a Python file** (e.g., `my_tools.py`):
   ```python
   """My custom tools for LoopLM."""

   from looplm.tools.base import tool

   @tool(description="Convert text to uppercase")
   def to_uppercase(text: str) -> str:
       """Convert the given text to uppercase."""
       return text.upper()

   @tool(description="Count words in text")
   def count_words(text: str) -> str:
       """Count the number of words in the given text."""
       word_count = len(text.split())
       return f"The text contains {word_count} words."
   ```

3. **Restart LoopLM** or use `/tools-reload` to load your new tools

### Tool Development Guide

#### Basic Tool Structure

```python
from looplm.tools.base import tool

@tool(description="Brief description of what the tool does")
def my_tool_function(param1: str, param2: int = 10) -> str:
    """Detailed docstring explaining the tool.

    Args:
        param1: Description of required parameter
        param2: Description of optional parameter (default: 10)

    Returns:
        A string result that will be shown to the user and LLM
    """
    # Your tool implementation here
    result = do_something(param1, param2)
    return f"Result: {result}"
```

#### Parameter Types

LoopLM automatically infers parameter types and requirements:

- **Supported types**: `str`, `int`, `float`, `bool`, `list`, `dict`
- **Required vs Optional**: Parameters with default values are optional
- **Type hints**: Always include type hints for proper validation

#### Advanced Examples

**Tool with Multiple Parameters:**
```python
@tool(description="Search and replace text")
def search_replace(text: str, search: str, replace: str, case_sensitive: bool = True) -> str:
    """Search and replace text with options."""
    if case_sensitive:
        return text.replace(search, replace)
    else:
        import re
        pattern = re.compile(re.escape(search), re.IGNORECASE)
        return pattern.sub(replace, text)
```

**Tool with API Integration:**
```python
import requests

@tool(description="Get current weather for a city")
def get_weather(city: str, api_key: str) -> str:
    """Get weather information using OpenWeatherMap API."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": api_key, "units": "metric"}
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]

        return f"Weather in {city}: {temp}°C, {desc}"
    except Exception as e:
        return f"Error getting weather: {str(e)}"
```

**Tool with File Operations:**
```python
from pathlib import Path

@tool(description="Count lines in a file")
def count_file_lines(file_path: str) -> str:
    """Count the number of lines in a text file."""
    try:
        path = Path(file_path).expanduser()
        if not path.exists():
            return f"Error: File '{file_path}' does not exist"

        with path.open('r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f)

        return f"File '{file_path}' contains {line_count} lines"
    except Exception as e:
        return f"Error reading file: {str(e)}"
```

### Directory Structure

Your custom tools directory (`~/.looplm/tools/`) structure:

```
~/.looplm/tools/
├── __init__.py              # Makes it a Python package (auto-created)
├── sample_tools.py          # Example tools (auto-created, commented out)
├── my_productivity_tools.py # Your custom tools
├── weather_tool.py          # Generated tool template
└── database_tools.py        # More custom tools
```

### Using External Libraries

Custom tools can use any Python libraries installed in your environment:

```python
# Install libraries: pip install requests beautifulsoup4

from looplm.tools.base import tool
import requests
from bs4 import BeautifulSoup

@tool(description="Get the title of a webpage")
def get_page_title(url: str) -> str:
    """Extract the title from a webpage."""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title')
        return f"Page title: {title.text.strip()}" if title else "No title found"
    except Exception as e:
        return f"Error fetching page: {str(e)}"
```

## Model Compatibility

Not all models support function calling. LoopLM automatically checks compatibility:

✅ **Supported Models:**
- **OpenAI**: gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o
- **Anthropic**: claude-3-opus, claude-3-sonnet, claude-3-haiku, claude-3.5-sonnet
- **Google**: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash
- **Other providers**: Many other LiteLLM-supported models

❌ **Unsupported Models:**
- Older OpenAI models (text-davinci-003, etc.)
- Some local/custom models without function calling support

LoopLM will show a warning if you try to use tools with an incompatible model.

## Safety Features

### Human Approval Mode

Enable approval mode to review tool calls before execution:

```bash
looplm chat --tools all --tools-approval
```

When a tool is called, you'll see:
```
⚠️ Tool 'create_file' is requesting execution with arguments:
{
  "file_path": "important_data.txt",
  "content": "Critical information..."
}

Do you want to proceed? (y/n/d for details):
```

Options:
- **`y`** - Execute the tool
- **`n`** - Cancel execution and inform the LLM
- **`d`** - Show detailed tool information

### Built-in Safety Limits

- **File size limits**: Text file operations limited to 1MB
- **Safe calculations**: Calculator only allows basic mathematical operations
- **Path validation**: Protection against path traversal attacks
- **Timeout protection**: Long-running operations are terminated
- **Error handling**: Graceful error handling with informative messages

### Best Practices for Custom Tools

- **Validate inputs**: Always check and sanitize user inputs
- **Handle errors gracefully**: Use try-catch blocks and return meaningful error messages
- **Avoid dangerous operations**: Be careful with file system and network operations
- **Use approval mode**: For potentially dangerous tools, recommend enabling approval mode

## Advanced Usage

### Programmatic Tool Management

```python
from looplm.tools import ToolManager, get_registry
from looplm.conversation.handler import ConversationHandler

# Create and configure tool manager
tool_manager = ToolManager(require_approval=True)

# Load specific tools (built-in and custom)
tool_manager.load_tools_from_names(["calculate", "get_current_time", "my_custom_tool"])

# Use with conversation handler
handler = ConversationHandler()
handler.tool_manager = tool_manager

# Check model compatibility
if tool_manager.check_model_compatibility("gpt-4"):
    print("Model supports tools!")
```

### Custom Tool Registry

```python
from looplm.tools import get_registry, tool

# Get global registry
registry = get_registry()

# Register tools manually
@tool(description="Custom function")
def my_function(x: int) -> str:
    return str(x * 2)

registry.register_function(my_function)

# List all tools
print(registry.list_tools())
```

### Environment Variables and Configuration

Custom tools can use environment variables for configuration:

```python
import os
from looplm.tools.base import tool

@tool(description="Tool that uses API keys from environment")
def api_tool(query: str) -> str:
    """Example tool that uses environment variables."""
    api_key = os.getenv('MY_API_KEY')
    if not api_key:
        return "Error: MY_API_KEY environment variable not set"

    # Use the API key for your tool logic
    return f"Processed query: {query}"
```

Set environment variables:
```bash
export MY_API_KEY="your-key-here"
looplm chat --tools all
```

## Examples

### Example 1: File Operations with ReACT

```
User: "List the files in the current directory and tell me the size of README.md"

🤔 LLM Reasons: "I need to first list the directory contents, then get details about README.md"
🔧 LLM Acts: Calls list_directory('.')
👁️ LLM Observes: Gets file listing including README.md (2.3KB)
✅ LLM Responds: "Found 8 files in current directory. README.md is 2.3KB..."
```

### Example 2: Custom Weather Tool

```
User: "What's the weather like in Tokyo?"

🤔 LLM Reasons: "I need to get weather information for Tokyo"
🔧 LLM Acts: Calls get_weather('Tokyo', api_key='your_key')
👁️ LLM Observes: Gets weather data
✅ LLM Responds: "Tokyo weather: 18°C, partly cloudy with light winds..."
```

### Example 3: Multi-step Problem Solving

```
User: "Create a summary of all Python files in the current directory"

🤔 LLM Reasons: "I need to find Python files, then read and summarize each one"
🔧 LLM Acts: Calls list_directory('.')
👁️ LLM Observes: Finds ['app.py', 'utils.py', 'config.py']
🤔 LLM Reasons: "Now I'll read each Python file to understand their contents"
🔧 LLM Acts: Calls read_file('app.py'), read_file('utils.py'), read_file('config.py') in parallel
👁️ LLM Observes: Gets contents of all three files
✅ LLM Responds: "Found 3 Python files. Here's a summary of each..."
```

## Troubleshooting

### Custom Tools Not Loading

1. **Check the tools directory:**
   ```
   /tools-dir
   ```
   Ensure files are in the correct location: `~/.looplm/tools/`

2. **Verify file format:**
   - Files must have `.py` extension
   - Must contain `@tool` decorated functions
   - Must import: `from looplm.tools.base import tool`

3. **Check for syntax errors:**
   ```bash
   python -m py_compile ~/.looplm/tools/your_tool.py
   ```

4. **Reload tools:**
   ```
   /tools-reload
   ```

### Tool Execution Errors

1. **Check tool parameters**: Ensure you're passing the right types and required parameters
2. **Review error messages**: Tool errors are displayed in the chat
3. **Test independently**: Test your tool functions in a Python script first
4. **Check dependencies**: Ensure required libraries are installed

### Permission Issues

1. **Check directory permissions:**
   ```bash
   ls -la ~/.looplm/
   ```

2. **Recreate tools directory:**
   ```bash
   rm -rf ~/.looplm/tools
   looplm chat --tools all  # Will recreate the directory
   ```

### Model Compatibility Issues

If you get function calling errors:

1. **Check model support:**
   ```bash
   looplm chat --tools all --model gpt-4  # Use a known compatible model
   ```

2. **Update your model**: Some older models don't support function calling

3. **Try different provider**: Some providers have better function calling support

---

For more examples and advanced usage patterns, see the complete [Custom Tools Guide](CUSTOM_TOOLS.md).
