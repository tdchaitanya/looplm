# Usage Guide

LoopLM provides a simple yet powerful command-line interface for interacting with Language Models. Here's how to make the most of it.

## Basic Usage

### Simple Prompt

```bash
looplm "Write a Python function to sort a dictionary by values"
```

This uses your default provider and model to process the prompt.

### Specify Provider

```bash
looplm --provider anthropic "Explain quantum computing"
```

### Specify Model

```bash
looplm --provider openai --model gpt-4o "Write a regex for email validation"
```

## Command Structure

The basic command structure is:

```bash
looplm [OPTIONS] PROMPT
```

### Available Options

- `--provider`: Use a specific provider
- `--model`: Use a specific model
- `--configure`: Launch configuration setup
- `--status`: Show current configuration
- `--reset`: Reset all configuration
- `--reset-provider`: Reset specific provider configuration
- `--set-default`: Set default provider and model

## Example Use Cases

### Development Assistance

1. **Code Explanation**
```bash
looplm "Explain what this code does: $(cat complex_function.py)"
```

2. **Debug Help**
```bash
looplm "Help me debug this error: $(cat error_log.txt)"
```

3. **Code Generation**
```bash
looplm "Write a Python script to backup files older than 30 days"
```

### Documentation

1. **Generate Docstrings**
```bash
looplm "Write a detailed docstring for this function: $(cat function.py)"
```

2. **README Creation**
```bash
looplm "Write a README for a Python package that does web scraping"
```

### Learning

1. **Concept Explanation**
```bash
looplm "Explain how async/await works in Python"
```

2. **Best Practices**
```bash
looplm "What are the best practices for Python error handling?"
```

## Tips and Tricks

### 1. Using with Pipes

LoopLM works well with Unix pipes:

```bash
cat error.log | looplm "Explain this error and suggest solutions"
```

### 2. Shell Aliases

Create useful aliases for common tasks:

```bash
# Add to your .bashrc or .zshrc
alias explain='looplm "Explain what this code does: "'
alias debug='looplm "Help debug this error: "'
alias docstring='looplm "Write a docstring for: "'
```

### 3. Multiple Lines

For multiple-line prompts, use quotes:

```bash
looplm "Review this code and suggest improvements:

def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result"
```

### 4. Script Integration

You can integrate LoopLM into your scripts:

```bash
#!/bin/bash
error_output=$(your_command 2>&1)
if [ $? -ne 0 ]; then
    looplm "Help debug this error: $error_output"
fi
```