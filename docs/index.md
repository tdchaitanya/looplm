# LoopLM - Language Models on the Command Line

> 🚫🚫🚫
> This tool is still in active development

`looplm` -- Command LM is a highly customisable command-line interface for interacting with various Language Models. It provides a simple and straighforward way to access state-of-the-art language models directly from your terminal.

## Features

- 🚀 **Support for multiple LLM providers**: Works with OpenAI, Anthropic, Google Gemini, Azure OpenAI, AWS Bedrock, and other providers through [LiteLLM](https://litellm.vercel.app/docs/providers) integration. You can easily switch between different providers and models
- 🔒 **Secure Configuration**: All API keys and credentials are stored securely using encryption
- 💻 **Simple CLI**: Intuitive command-line interface for quick access to AI capabilities
- 🔍 **Rich Output**: Beautiful terminal output with markdown support

## Quick Start

1. Install LoopLM using pip:
```bash
pip install looplm
```

2. Configure your first provider:
```bash
looplm --configure
```

3. Start using the CLI:
```bash
looplm "Write a function to calculate fibonacci numbers in Python"
```

## Why LoopLM?

LoopLM is designed for developers who:
- Want quick access to LLMs without leaving the terminal
- Work with multiple LLM providers and need a unified interface
- Want to integrate LLM assistance into their development workflow

## Requirements

- Python 3.10 or higher
- Internet connection
- API keys for the providers you want to use