<div align="center">

# LoopLM

🤖 A powerful tool for seamlessly integrating LLMs in your development workflow

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://chaitanya.one/looplm)

</div>

---

> [!NOTE]
> LoopLM is in active development. While fully functional, expect frequent updates and improvements.

LoopLM is a highly customisable command line tool that seamlessly integrates various Language Models into your development workflow. It offers a unified, secure, and efficient way to interact with state-of-the-art AI models directly from your terminal.

## Features

- 🚀 **Support for multiple LLM providers**: Works with OpenAI, Anthropic, Google Gemini, Azure OpenAI, AWS Bedrock, and other providers through [LiteLLM](https://litellm.vercel.app/docs/providers) integration. You can easily switch between different providers and models
- 🔒 **Secure Configuration**: All API keys and credentials are stored securely using encryption
- 💻 **Simple CLI**: Intuitive command-line interface for quick access to LLMs and pipe support for integration with Unix tools
- 🔍 **Rich Output**: Beautiful terminal output with markdown support

## Quick Start

1. Install LoopLM using pipx:
```bash
pipx install looplm
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
- API keys for the providers you want to use

## 📖 Documentation

For comprehensive documentation, visit [our documentation site](https://chaitanya.one/looplm).