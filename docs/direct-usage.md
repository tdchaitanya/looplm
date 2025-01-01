# Direct Command Usage

This guide covers using LoopLM for quick, one-off interactions with language models directly from your command line.

## Basic Usage

### Simple Prompts

```bash
# Basic query
looplm "Write a Python function to calculate factorial"
```

### Provider Selection

```bash
# Use specific provider
looplm --provider gemini "Explain async/await in Python"

# Use specific model
looplm --provider openai --model gpt-4o-mini "Write unit tests for a login function"
```

## Input Methods

### File Input

LoopLM supports several ways to include file contents in your prompts:

1. Using @file directive:
```bash
# Using quoted path
looplm "Explain this code: @file(\"src/main.py\")"

# Using space-separated path
looplm "Review this configuration: @file config/settings.yml"

# Using absolute paths
looplm "Analyze this log: @file(/var/log/app.log)"
```

2. Using command substitution (traditional method):
```bash
# Pass file content
looplm "Explain this code: $(cat script.py)"

# Multiple files
looplm "Compare these implementations: $(cat impl1.py) vs $(cat impl2.py)"
```

The @file directive supports:
- Text files (code, logs, config files, etc.)
- Common document formats (PDF, Word, Excel, etc.) through automatic conversion
- Both relative and absolute paths
- Multiple file inclusions in a single prompt

### Pipe Input


```bash
# Pipe error output
python script.py 2>&1 | looplm "Help me debug this error"

# Pipe file content
cat complex_code.py | looplm "Explain this code in detail"

# Process command output
git diff | looplm "Summarize these changes"
```

## Common Use Cases

### Code Tasks

```bash
# Code review with file directive
looplm "Review this implementation: @file(src/auth.py)"

# Documentation with multiple files
looplm "Write documentation for this module: @file(src/module.py) and its tests @file(tests/test_module.py)"

# Bug fixing
looplm "Fix this buggy code: @file(src/buggy.py)"

# Code analysis
looplm "Analyze the complexity of this function: @file(src/complex_function.py)"
```

### Development Support

```bash
# Git commit messages
git diff --cached | looplm "Write a commit message for these changes"

# API documentation
cat api_endpoint.py | looplm "Write OpenAPI documentation for this endpoint"

# Config file generation
looplm "Create a Docker Compose file for a Python web app with Redis and PostgreSQL"
```

### Learning and Understanding

```bash
# Concept explanation
looplm "Explain how Python's GIL works"

# Code breakdown
cat complex_algorithm.py | looplm "Break down how this algorithm works"

# Best practices
looplm "What are the best practices for Python error handling?"
```

## Tips and Tricks

### Shell Aliases

Add these to your `.bashrc` or `.zshrc`:

```bash
# Quick code explanation
alias explain='looplm "Explain this code: "'

# Debug helper
alias debug='looplm "Help debug this error: "'

# Documentation generator
alias docstring='looplm "Write a docstring for: "'

# Git commit helper
alias commit-msg='git diff --cached | looplm "Write a commit message"'
```

### Shell Functions

```bash
# Function to explain the last error
explain_error() {
    local error_output=$(fc -ln -1 2>&1)
    looplm "Explain this error and suggest fixes: $error_output"
}

# Function to document Python functions
document_function() {
    if [ -z "$1" ]; then
        echo "Usage: document_function <python_file>"
        return 1
    fi
    cat "$1" | looplm "Write comprehensive docstrings for this code"
}
```

### Integration with Development Tools

#### Git Hooks

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Auto-generate commit message based on staged changes

staged_diff=$(git diff --cached)
if [ -n "$staged_diff" ]; then
    echo "$staged_diff" | looplm "Write a concise commit message" > .git/COMMIT_EDITMSG
fi
```

#### Editor Integration (VSCode tasks.json)

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Document Function",
            "type": "shell",
            "command": "cat ${file} | looplm 'Write a docstring for this function, just return the docstring and nothing else'",
            "presentation": {
                "reveal": "always",
                "panel": "new"
            }
        }
    ]
}
```

## Best Practices

1. **Handle Large Inputs**
   ```bash
   # For large files, focus on specific sections
   cat large_file.py | grep -A 10 "class MyClass" | looplm "Explain this class"
   ```
2. **Use Appropriate Models**
   ```bash
   # Complex tasks: Use more capable models
   looplm --provider anthropic --model claude-3.5-sonnet "Design a system architecture"

   # Simple tasks: Use faster models
   looplm --provider openai --model gpt-4o-mini "Format this JSON"
   ```
3. **Provide Context When Needed**
   ```bash
   # Include relevant details
   looplm "Write a unit test for this function considering these edge cases: $(cat edge_cases.txt)"
   ```
4. **Keep Prompts Clear and Specific**
   ```bash
   # Good
   looplm "Write a Python function to sort a list of dictionaries by the 'date' key"

   # Less effective
   looplm "Sort dictionaries"
   ```
