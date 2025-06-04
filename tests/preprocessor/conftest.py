"""Fixtures for preprocessor tests."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from looplm.preprocessor.files import FilePreprocessor


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing."""
    # Create text files
    python_file = temp_dir / "sample.py"
    python_file.write_text("def hello():\n    print('Hello, world!')")

    txt_file = temp_dir / "sample.txt"
    txt_file.write_text("This is a sample text file.")

    json_file = temp_dir / "sample.json"
    json_file.write_text('{"key": "value", "number": 42}')

    # Create nested directories
    nested_dir = temp_dir / "nested"
    nested_dir.mkdir()

    nested_file = nested_dir / "nested_file.txt"
    nested_file.write_text("This is a nested file.")

    # Create a file with unicode content
    unicode_file = temp_dir / "unicode.txt"
    unicode_file.write_text("Unicode text: 你好, 世界!")

    # Return a dict with paths to all created files
    return {
        "python_file": python_file,
        "txt_file": txt_file,
        "json_file": json_file,
        "nested_dir": nested_dir,
        "nested_file": nested_file,
        "unicode_file": unicode_file,
        "root_dir": temp_dir,
    }


@pytest.fixture
def preprocessor(temp_dir):
    """Create a FilePreprocessor instance with a specified base path."""
    return FilePreprocessor(base_path=str(temp_dir))


@pytest.fixture
def mock_requests():
    """Mock the requests module for testing URL handling."""
    with patch("requests.get") as mock_get:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.iter_content.return_value = [b"Mock content from URL"]

        # Set up the mock get function
        mock_get.return_value = mock_response

        yield mock_get


@pytest.fixture
def mock_markitdown():
    """Mock the MarkItDown class for testing non-text files."""
    with patch("looplm.preprocessor.files.MarkItDown") as mock_class:
        mock_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.text_content = "Converted file content"
        mock_instance.convert.return_value = mock_result
        mock_class.return_value = mock_instance

        yield mock_class, mock_instance
