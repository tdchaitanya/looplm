# looplm Tests

This directory contains tests for the looplm CLI tool. The tests are organized by module to match the package structure.

## Directory Structure

```
tests/
├── config/          # Tests for configuration module
├── chat/            # Tests for chat module
├── preprocessor/    # Tests for preprocessor module
├── conversation/    # Tests for conversation module
├── cli/             # Tests for CLI module
└── integration/     # Integration tests across modules
```

## Running Tests

To run all tests:

```bash
pytest
```

To run tests for a specific module:

```bash
pytest tests/config
```

To generate a coverage report:

```bash
pytest --cov=looplm
```
