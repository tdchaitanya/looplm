#!/usr/bin/env python3
"""
Entry point for running looplm.cli as a module.

This allows commands like:
    python -m looplm.cli
    python -m looplm.cli chat --tools all
"""

from .main import cli

if __name__ == "__main__":
    cli()
