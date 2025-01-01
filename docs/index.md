# LoopLM - Loop Language Models in your Terminal

> 🚫🚫🚫
> This tool is still in active development

`looplm` -- LoopLM is a highly customisable command-line interface that seamlessly integrates various Language Models into your development workflow. Whether you need quick code assistance, want to explore ideas, or engage in interactive conversations with LLMs, LoopLM provides an intuitive terminal-based interface to access state-of-the-art language models.


## Features

- 🚀 **Support for multiple LLM providers**: Works with OpenAI, Anthropic, Google Gemini, Azure OpenAI, AWS Bedrock, and other providers through [LiteLLM](https://litellm.vercel.app/docs/providers) integration. You can easily switch between different providers and models
- 📂 **File Integration**: Include files directly in your prompts using @file directives, supporting code files, logs, configurations, and even PDFs and documents
- 🔒 **Secure Configuration**: All API keys and credentials are stored securely using encryption
- 💻 **Simple CLI**: Intuitive command-line interface for quick access to AI capabilities
- 💬 **Interactive Chat Mode**: Engage in persistent, interactive conversations with your preferred LLM using looplm chat
- 🔍 **Rich Output**: Beautiful terminal output with markdown support
- 🔍 **Smart Context**: Maintain conversation context and system prompts for consistent interactions

## Quick Start

1. Install LoopLM ([pipx](https://github.com/pypa/pipx) is recommended):
```bash
pipx install looplm
```

2. Configure your first provider:
```bash
looplm --configure
```

3. Start using the CLI with direct file support:
```bash
# Review code with file directive
looplm "Review this code: @file(src/main.py)"

# Compare implementations
looplm "Compare these files: @file(v1.py) vs @file(v2.py)"

# Analyze logs
looplm "Check this log: @file(/var/log/app.log)"
```

4. Start an interactive chat session:
```bash
looplm chat
```

## Why LoopLM?

LoopLM is designed for developers who:
- Want quick access to LLMs without leaving the terminal
- Need to frequently analyze code, logs, and configuration files
- Work with multiple LLM providers and need a unified interface
- Want to integrate LLM assistance into their development workflow
- Need to maintain context across development sessions

## Requirementss

- Python 3.10 or higher
- API keys for the providers you want to use

For detailed usage instructions, see:
- [Direct Usage Guide](direct-usage.md)
- [Chat Mode Guide](chat-usage.md)
- [Configuration Guide](configuration.md)
