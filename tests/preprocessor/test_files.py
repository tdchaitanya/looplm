"""Tests for the file preprocessor module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests
from markitdown._markitdown import UnsupportedFormatException

from looplm.preprocessor.files import FilePreprocessor, FileProcessingError


class TestFilePreprocessor:
    """Tests for the FilePreprocessor class."""

    def test_init(self, temp_dir):
        """Test that the preprocessor initializes correctly."""
        preprocessor = FilePreprocessor(base_path=str(temp_dir))

        assert preprocessor.base_path == Path(temp_dir).resolve()
        assert hasattr(preprocessor, "temp_dir")
        assert preprocessor.temp_dir.exists()
        assert preprocessor.temp_dir.is_dir()

    def test_cleanup(self, temp_dir):
        """Test that cleanup removes temporary directory."""
        preprocessor = FilePreprocessor(base_path=str(temp_dir))
        temp_path = preprocessor.temp_dir

        # Verify temp directory exists
        assert temp_path.exists()

        # Cleanup should remove the temp directory
        preprocessor.cleanup()
        assert not temp_path.exists()

        # Running cleanup again shouldn't error
        preprocessor.cleanup()

    def test_del(self):
        """Test that __del__ calls cleanup."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            preprocessor = FilePreprocessor(base_path=tmp_dir)
            temp_path = preprocessor.temp_dir

            # Mock the cleanup method
            with patch.object(preprocessor, "cleanup") as mock_cleanup:
                # Manually call __del__
                preprocessor.__del__()

                # Verify cleanup was called
                mock_cleanup.assert_called_once()

    def test_process_text_file(self, preprocessor, sample_files):
        """Test processing a text file."""
        file_path = sample_files["txt_file"]

        result = preprocessor._process_file_directive(str(file_path))

        # Check that the result includes file content
        assert "This is a sample text file" in result
        # Check that the result includes file path
        assert str(file_path) in result
        # Check that the result includes proper formatting
        assert "```" in result

    def test_process_python_file(self, preprocessor, sample_files):
        """Test processing a Python file."""
        file_path = sample_files["python_file"]

        result = preprocessor._process_file_directive(str(file_path))

        # Check that the result includes file content
        assert "def hello():" in result
        assert "print('Hello, world!')" in result
        # Check for Python syntax highlighting
        assert "```py" in result or "```python" in result

    def test_process_nested_file(self, preprocessor, sample_files):
        """Test processing a file in a nested directory."""
        file_path = sample_files["nested_file"]

        result = preprocessor._process_file_directive(str(file_path))

        # Check that the result includes file content
        assert "This is a nested file" in result

    def test_process_unicode_file(self, preprocessor, sample_files):
        """Test processing a file with unicode content."""
        file_path = sample_files["unicode_file"]

        result = preprocessor._process_file_directive(str(file_path))

        # Check that the result includes unicode content
        assert "你好, 世界!" in result

    def test_resolve_path_absolute(self, preprocessor, sample_files):
        """Test resolving an absolute file path."""
        file_path = sample_files["txt_file"]

        is_url, resolved_path = preprocessor._resolve_path(str(file_path))

        assert not is_url
        assert resolved_path == str(file_path.resolve())

    def test_resolve_path_relative(self, preprocessor, sample_files):
        """Test resolving a relative file path."""
        # Get the relative path from the base path
        rel_path = os.path.relpath(
            sample_files["txt_file"], start=preprocessor.base_path
        )

        is_url, resolved_path = preprocessor._resolve_path(rel_path)

        assert not is_url
        assert resolved_path == str(sample_files["txt_file"].resolve())

    def test_resolve_path_url(self, preprocessor):
        """Test resolving a URL."""
        url = "https://example.com/file.txt"

        is_url, resolved_path = preprocessor._resolve_path(url)

        assert is_url
        assert resolved_path == url

    def test_resolve_path_not_found(self, preprocessor):
        """Test resolving a non-existent file path."""
        non_existent_path = "non_existent_file.txt"

        with pytest.raises(FileNotFoundError):
            preprocessor._resolve_path(non_existent_path)

    def test_handle_url(self, preprocessor, mock_requests):
        """Test handling a URL."""
        url = "https://example.com/file.txt"

        result = preprocessor._handle_url(url)

        # Check that the request was made
        mock_requests.assert_called_once_with(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LoopLM/1.0)",
                "Accept": "text/plain, text/html, application/json, */*",
            },
            timeout=10,
            stream=True,
            verify=True,
        )

        # Check that the result contains the content
        assert "Mock content from URL" in result

    def test_handle_url_error(self, preprocessor):
        """Test handling a URL with an error."""
        url = "https://example.com/file.txt"

        # Mock requests.get to raise an exception
        with patch(
            "requests.get", side_effect=requests.RequestException("Connection error")
        ):
            with pytest.raises(ValueError, match="Failed to fetch URL"):
                preprocessor._handle_url(url)

    def test_handle_url_unsupported_scheme(self, preprocessor):
        """Test handling a URL with an unsupported scheme."""
        url = "ftp://example.com/file.txt"

        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            preprocessor._handle_url(url)

    def test_handle_url_too_large(self, preprocessor, mock_requests):
        """Test handling a URL that returns content that's too large."""
        url = "https://example.com/large-file.txt"

        # Mock the response to simulate large content
        mock_response = mock_requests.return_value
        mock_response.headers = {"content-type": "text/plain"}

        # Create large content that exceeds the 10MB limit
        large_chunk = b"X" * 1024 * 1024  # 1MB chunk

        # We'll yield 11 chunks of 1MB each, exceeding the 10MB limit
        chunks = [large_chunk] * 11

        # Mock iter_content to yield our large chunks
        mock_response.iter_content.return_value = chunks

        # Patch the stat method to control file size reporting
        with patch("pathlib.Path.stat") as mock_stat:
            # Create a mock stat result object that reports increasing file sizes
            mock_stat_result = MagicMock()

            # Start with a small size, then increase beyond the limit after a few chunks
            sizes = [
                0,
                5 * 1024 * 1024,
                9 * 1024 * 1024,
                11 * 1024 * 1024,
            ]  # 0, 5MB, 9MB, 11MB

            mock_stat_result.st_size = 0
            calls = 0

            def increase_size():
                nonlocal calls
                if calls < len(sizes):
                    mock_stat_result.st_size = sizes[calls]
                    calls += 1
                return mock_stat_result

            mock_stat.return_value = mock_stat_result
            mock_stat.side_effect = lambda: increase_size()

            with patch("builtins.open", mock_open()) as mock_file:
                # This should now raise ValueError due to the file becoming too large
                with pytest.raises(ValueError, match="File too large"):
                    preprocessor._handle_url(url)

    def test_handle_local_file_not_found(self, preprocessor):
        """Test handling a non-existent local file."""
        with pytest.raises(FileNotFoundError):
            preprocessor._handle_local_file("non_existent_file.txt")

    def test_handle_unsupported_file_format(
        self, preprocessor, mock_markitdown, temp_dir
    ):
        """Test handling an unsupported file format."""
        # Create a binary file
        binary_file = temp_dir / "binary.bin"
        with open(binary_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03")

        # Specifically test ValueError by making mock raise a general exception
        mock_class, mock_instance = mock_markitdown
        mock_instance.convert.side_effect = Exception(
            "General error, not UnsupportedFormatException"
        )

        with pytest.raises(
            ValueError, match="Unsupported file format or conversion error"
        ):
            preprocessor._handle_local_file(str(binary_file))

    def test_handle_unsupported_format_exception(
        self, preprocessor, mock_markitdown, temp_dir
    ):
        """Test handling MarkItDown's UnsupportedFormatException."""
        # Create a file with an unsupported extension
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.write_text("Some content")

        # Mock the convert method to raise UnsupportedFormatException
        mock_class, mock_instance = mock_markitdown
        mock_instance.convert.side_effect = UnsupportedFormatException(
            "Unsupported format"
        )

        with pytest.raises(
            FileProcessingError, match="File format '.xyz' is not supported"
        ):
            preprocessor._handle_local_file(str(unsupported_file))

    def test_markitdown_unexpected_error(self, preprocessor, mock_markitdown, temp_dir):
        """Test handling an unexpected error from MarkItDown."""
        # Create a file
        test_file = temp_dir / "test.docx"
        test_file.write_bytes(b"Not a real docx file")

        # Mock MarkItDown to raise a different error
        mock_class, mock_instance = mock_markitdown
        mock_instance.convert.side_effect = Exception("Unexpected MarkItDown error")

        with pytest.raises(
            ValueError, match="Unsupported file format or conversion error"
        ):
            preprocessor._handle_local_file(str(test_file))

    def test_format_text_content(self, preprocessor, sample_files):
        """Test formatting text file content."""
        file_path = sample_files["txt_file"]

        result = preprocessor._format_text_content(file_path)

        assert "File: " in result
        assert str(file_path) in result
        assert "```" in result
        assert "This is a sample text file" in result

    def test_format_text_content_unicode_error(self, preprocessor, temp_dir):
        """Test formatting content with unicode decode error."""
        # Create a binary file
        binary_file = temp_dir / "binary.txt"
        with open(binary_file, "wb") as f:
            f.write(b"\x80\x81\x82\x83")  # Invalid UTF-8

        with pytest.raises(ValueError, match="unsupported encoding"):
            preprocessor._format_text_content(binary_file)

    def test_process_prompt_with_file(self, preprocessor, sample_files):
        """Test processing a prompt with a @file directive."""
        file_path = sample_files["txt_file"]
        prompt = f'Please analyze this file: @file("{file_path}")'

        processed_prompt = preprocessor.process_prompt(prompt)

        # Original text should be preserved
        assert "Please analyze this file:" in processed_prompt
        # File content should be included
        assert "This is a sample text file" in processed_prompt

    def test_process_prompt_with_multiple_files(self, preprocessor, sample_files):
        """Test processing a prompt with multiple @file directives."""
        python_file = sample_files["python_file"]
        txt_file = sample_files["txt_file"]

        prompt = (
            f'Python file: @file("{python_file}")\n' f'Text file: @file("{txt_file}")'
        )

        processed_prompt = preprocessor.process_prompt(prompt)

        # Check that both files are included
        assert "def hello():" in processed_prompt
        assert "This is a sample text file" in processed_prompt

    def test_process_prompt_unquoted(self, preprocessor, sample_files):
        """Test processing a prompt with unquoted @file directive."""
        file_path = sample_files["txt_file"]
        prompt = f"Please analyze this file: @file {file_path}"

        processed_prompt = preprocessor.process_prompt(prompt)

        # File content should be included
        assert "This is a sample text file" in processed_prompt

    def test_process_prompt_with_brackets(self, preprocessor, sample_files):
        """Test processing a prompt with @file() directive."""
        file_path = sample_files["txt_file"]
        prompt = f"Please analyze this file: @file({file_path})"

        processed_prompt = preprocessor.process_prompt(prompt)

        # File content should be included
        assert "This is a sample text file" in processed_prompt

    def test_process_prompt_with_error(self, preprocessor):
        """Test processing a prompt with an error in @file directive."""
        prompt = 'Please analyze this file: @file("non_existent_file.txt")'

        # Test with raise_errors=True (default)
        with pytest.raises(FileProcessingError):
            preprocessor.process_prompt(prompt)

        # Test with raise_errors=False
        processed_prompt = preprocessor.process_prompt(prompt, raise_errors=False)
        assert "Error processing @file" in processed_prompt

    def test_markitdown_integration(self, preprocessor, mock_markitdown, temp_dir):
        """Test integration with MarkItDown for non-text files."""
        # Create a PDF file (just for the extension, content doesn't matter)
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(b"Not really a PDF")

        # We've mocked MarkItDown to return "Converted file content"
        result = preprocessor._handle_local_file(str(pdf_file))

        assert "Converted file content" in result
        mock_class, mock_instance = mock_markitdown
        mock_instance.convert.assert_called_once_with(str(pdf_file))

    def test_markitdown_unsupported_format(
        self, preprocessor, mock_markitdown, temp_dir
    ):
        """Test MarkItDown with unsupported format."""
        # Create a file with an extension MarkItDown doesn't support
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.write_text("Some content")

        # Mock the convert method to raise UnsupportedFormatException
        mock_class, mock_instance = mock_markitdown
        mock_instance.convert.side_effect = UnsupportedFormatException(
            "Unsupported format"
        )

        with pytest.raises(
            FileProcessingError, match="File format .* is not supported"
        ):
            preprocessor._handle_local_file(str(unsupported_file))
