# Adding Custom Tools to LoopLM

LoopLM supports custom tools that extend its functionality beyond the built-in tools. This guide shows you how to create, install, and use custom tools with your LoopLM installation.

## Quick Start

1. **Enable tools in chat mode:**
   ```bash
   looplm chat --tools all
   ```

2. **Find your tools directory:**
   ```
   /tools-dir
   ```

3. **Create a new tool:**
   ```
   /tools-create my_tool "Description of what it does"
   ```

4. **Edit the generated file and reload:**
   ```
   /tools-reload
   ```

## User Tools Directory

LoopLM automatically creates a tools directory in your home folder:

```
~/.looplm/tools/
```

This directory contains:
- **`__init__.py`**: Makes it a Python package
- **`sample_tools.py`**: Example tools (commented out by default)
- **Your custom tool files**: Any `.py` files you create

## Creating Custom Tools

### Method 1: Using the CLI (Recommended)

1. Start a chat session with tools enabled:
   ```bash
   looplm chat --tools all
   ```

2. Create a new tool template:
   ```
   /tools-create weather_checker "Get weather information for a location"
   ```

3. This creates `~/.looplm/tools/weather_checker_tool.py` with a template

4. Edit the file to implement your tool logic

5. Reload tools to use it:
   ```
   /tools-reload
   ```

### Method 2: Manual Creation

1. Navigate to your tools directory:
   ```bash
   cd ~/.looplm/tools/
   ```

2. Create a new Python file (e.g., `my_tools.py`):
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

3. Restart LoopLM or use `/tools-reload` to load your new tools

## Tool Development Guide

### Basic Tool Structure

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

### Parameter Types

LoopLM automatically infers parameter types and requirements:

- **Supported types**: `str`, `int`, `float`, `bool`, `list`, `dict`
- **Required vs Optional**: Parameters with default values are optional
- **Type hints**: Always include type hints for proper validation

### Advanced Examples

#### Tool with Multiple Parameters
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

#### Tool with API Integration
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

#### Tool with File Operations
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

## Tool Management Commands

### In Chat Mode

| Command | Description |
|---------|-------------|
| `/tools` | Show all tool commands |
| `/tools-list` | List available tools |
| `/tools-enable [tool1,tool2]` | Enable specific tools or all |
| `/tools-disable` | Disable all tools |
| `/tools-create <name> [desc]` | Create new tool template |
| `/tools-dir` | Show tools directory path |
| `/tools-reload` | Reload tools from directories |
| `/tools-approval` | Toggle approval mode |

### From Command Line

```bash
# Enable all tools
looplm chat --tools all

# Enable specific tools
looplm chat --tools "my_tool,count_words"

# Enable with approval mode
looplm chat --tools all --tools-approval
```

## Best Practices

### Security
- **Validate inputs**: Always validate and sanitize user inputs
- **Handle errors**: Use try-catch blocks and return meaningful error messages
- **Avoid dangerous operations**: Be careful with file system and network operations
- **Use approval mode**: For potentially dangerous tools, recommend users enable approval mode

### Performance
- **Keep tools fast**: Avoid long-running operations that could block the chat
- **Cache when appropriate**: Cache expensive computations or API calls
- **Limit resource usage**: Be mindful of memory and CPU usage

### User Experience
- **Clear descriptions**: Write descriptive `@tool` descriptions and docstrings
- **Meaningful return values**: Return formatted, human-readable results
- **Error handling**: Provide helpful error messages, not just exceptions

### Code Organization
- **Group related tools**: Put related tools in the same file
- **Use descriptive names**: Make function names clear and specific
- **Document thoroughly**: Include examples in docstrings when helpful

## Example: Complete Custom Tool File

```python
"""Custom productivity tools for LoopLM."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from looplm.tools.base import tool

@tool(description="Create a simple TODO list item")
def create_todo(task: str, priority: str = "medium") -> str:
    """Create a TODO item with timestamp and priority.

    Args:
        task: The task description
        priority: Priority level (low, medium, high)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(priority, "🟡")

    return f"{priority_emoji} [{timestamp}] {task}"

@tool(description="Extract email addresses from text")
def extract_emails(text: str) -> str:
    """Extract all email addresses from the given text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)

    if not emails:
        return "No email addresses found in the text."

    return f"Found {len(emails)} email addresses:\n" + "\n".join(f"- {email}" for email in emails)

@tool(description="Format JSON text for better readability")
def format_json(json_text: str, indent: int = 2) -> str:
    """Format JSON text with proper indentation."""
    try:
        parsed = json.loads(json_text)
        formatted = json.dumps(parsed, indent=indent, ensure_ascii=False)
        return f"Formatted JSON:\n```json\n{formatted}\n```"
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {str(e)}"
```

## Troubleshooting

### Tool Not Loading
1. Check the file is in `~/.looplm/tools/`
2. Ensure the file has a `.py` extension
3. Verify the `@tool` decorator is imported and used correctly
4. Use `/tools-reload` to refresh
5. Check for Python syntax errors

### Tool Not Working
1. Verify parameter types match the function signature
2. Check that required parameters are provided
3. Review error messages in the chat
4. Test the function independently in a Python script

### Permission Issues
1. Ensure the tools directory is writable
2. Check file permissions on your tool files
3. Try recreating the tools directory: `rm -rf ~/.looplm/tools && looplm chat --tools all`

## Advanced Topics

### Using External Libraries
```python
# Install libraries in your Python environment
# pip install requests beautifulsoup4

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

### Environment Variables and Configuration
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

## Integration Examples

### With Local Databases
```python
import sqlite3
from looplm.tools.base import tool

@tool(description="Query local SQLite database")
def query_db(sql: str, db_path: str = "~/.looplm/data.db") -> str:
    """Execute a SELECT query on local database."""
    try:
        expanded_path = Path(db_path).expanduser()
        with sqlite3.connect(expanded_path) as conn:
            cursor = conn.execute(sql)
            results = cursor.fetchall()

        return f"Query returned {len(results)} rows:\n" + "\n".join(str(row) for row in results[:10])
    except Exception as e:
        return f"Database error: {str(e)}"
```

### With Local Services
```python
@tool(description="Check if local service is running")
def check_service(port: int) -> str:
    """Check if a local service is running on the specified port."""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            if result == 0:
                return f"✅ Service is running on port {port}"
            else:
                return f"❌ No service found on port {port}"
    except Exception as e:
        return f"Error checking port {port}: {str(e)}"
```

---

**Happy tool building!** 🔧

For more examples and updates, check the [LoopLM documentation](https://github.com/your-repo/looplm) and the `sample_tools.py` file in your tools directory.
