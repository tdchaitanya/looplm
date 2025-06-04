# src/looplm/preprocessor/files.py

import mimetypes
import os
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from markitdown import MarkItDown
from markitdown._markitdown import UnsupportedFormatException


class FileProcessingError(Exception):
    """Custom exception for file processing errors"""

    def __init__(self, message: str, file_path: str):
        self.file_path = file_path
        self.message = message
        super().__init__(f"Error processing file '{file_path}': {message}")

    def __str__(self):
        return f"Error processing file '{self.file_path}': {self.message}"


class FilePreprocessor:
    """Handles file inclusion preprocessing in prompts using @file directives."""

    # File extensions that can be directly read as text
    TEXT_EXTENSIONS = {
        ".txt",
        ".py",
        ".js",
        ".html",
        ".css",
        ".json",
        ".xml",
        ".md",
        ".csv",
        ".yml",
        ".yaml",
        ".ini",
        ".conf",
        ".sh",
        ".bash",
        ".sql",
        ".log",
        ".env",
        ".rs",
        ".go",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
    }

    # Precompiled regex patterns for better performance
    QUOTED_PATTERN = re.compile(r'@file\("([^"]+)"\)')
    UNQUOTED_PATTERN = re.compile(r'@file\s+([^\s"]+)')
    UNQUOTED_PATTERN_BRACKET = re.compile(r"@file\(([^)]+)\)")

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the file preprocessor.

        Args:
            base_path: Optional base path for resolving relative paths.
                      If not provided, uses current working directory.
        """
        self.temp_dir = Path(tempfile.mkdtemp())
        # Convert to absolute path and resolve any symlinks
        self.base_path = Path(base_path or os.getcwd()).resolve()

    def process_prompt(self, prompt: str, raise_errors: bool = True) -> str:
        """
        Process a prompt and replace all @file directives with file contents.

        Args:
            prompt: The input prompt containing @file directives
            raise_errors: If True, raises exceptions; if False, returns error messages

        Returns:
            str: Processed prompt with file contents or error messages included

        Raises:
            FileProcessingError: If raise_errors is True and an error occurs
        """

        def replace_match(match):
            file_path = match.group(1)
            try:
                return self._process_file_directive(file_path)
            except Exception as e:
                if raise_errors:
                    raise FileProcessingError(str(e), file_path)
                return f"Error processing @file({file_path}): {str(e)}"

        try:
            # Process all patterns using precompiled regex
            prompt = self.QUOTED_PATTERN.sub(replace_match, prompt)
            prompt = self.UNQUOTED_PATTERN.sub(replace_match, prompt)
            prompt = self.UNQUOTED_PATTERN_BRACKET.sub(replace_match, prompt)
            return prompt
        except FileProcessingError as e:
            if raise_errors:
                raise
            return f"Error: {str(e)}"

    def _process_file_directive(self, path: str) -> str:
        """
        Process a single @file directive.

        Args:
            path: File path or URL to process

        Returns:
            str: Processed file content with appropriate formatting
        """
        is_url, resolved_path = self._resolve_path(path)

        if is_url:
            return self._handle_url(resolved_path)
        else:
            return self._handle_local_file(resolved_path)

    def _resolve_path(self, path: str) -> Tuple[bool, str]:
        """
        Determine if path is URL or local file and resolve it.

        Handles both absolute and relative paths.

        Args:
            path: File path or URL to resolve

        Returns:
            Tuple[bool, str]: (is_url, resolved_path)
        """
        parsed = urllib.parse.urlparse(path)
        is_url = bool(parsed.scheme and parsed.netloc)

        if is_url:
            return True, path

        # Handle local paths
        path_obj = Path(path)

        if path_obj.is_absolute():
            if not path_obj.exists():
                raise FileNotFoundError(f"File not found: {path_obj}")
            return False, str(path_obj.resolve())

        # Try relative to current directory first
        cwd_path = Path.cwd() / path_obj
        if cwd_path.exists():
            return False, str(cwd_path.resolve())

        # Try relative to base_path
        base_path = self.base_path / path_obj
        if base_path.exists():
            return False, str(base_path.resolve())

        # If neither exists, raise error with helpful message
        raise FileNotFoundError(
            f"File not found: {path}\n"
            f"Tried locations:\n"
            f"  - Relative to current dir: {cwd_path}\n"
            f"  - Relative to base path: {base_path}"
        )

    def _handle_url(self, url: str) -> str:
        """
        Handle URL-based file inclusion with security checks.

        Args:
            url: URL to download and process

        Returns:
            str: Processed file content

        Raises:
            ValueError: If URL is invalid, unsecured, or content type is unsupported
        """
        try:
            # Validate URL scheme
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"}:
                raise ValueError(
                    f"Unsupported URL scheme: {parsed_url.scheme}. Only http and https are allowed."
                )

            # Make request with security headers and timeout
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; LoopLM/1.0)",
                "Accept": "text/plain, text/html, application/json, */*",
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=10,
                stream=True,
                verify=True,  # Verify SSL certificates
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").split(";")[0]
            ext = mimetypes.guess_extension(content_type) or ".tmp"
            temp_file = self.temp_dir / f"download{ext}"

            # Download with size limit (10MB)
            max_size = 10 * 1024 * 1024
            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    if temp_file.stat().st_size > max_size:
                        raise ValueError(
                            f"File too large. Maximum size is {max_size/1024/1024}MB"
                        )

            return self._handle_local_file(str(temp_file))

        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch URL {url}: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to process URL {url}: {str(e)}")

    def _handle_local_file(self, file_path: str) -> str:
        """
        Handle local file inclusion.

        Args:
            file_path: Path to local file

        Returns:
            str: Processed file content

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Handle text files directly
        if file_path.suffix.lower() in self.TEXT_EXTENSIONS:
            return self._format_text_content(file_path)

        # Use markitdown for supported formats
        try:
            md = MarkItDown()
            result = md.convert(str(file_path))
            return result.text_content
        except UnsupportedFormatException as e:
            # Get the unsupported format from the error message
            unsupported_format = (
                file_path.suffix.lower() if file_path.suffix.lower() else "unknown"
            )
            raise FileProcessingError(
                f"File format '{unsupported_format}' is not supported.", str(file_path)
            )
        except Exception as e:
            raise ValueError(f"Unsupported file format or conversion error: {str(e)}")

    def _format_text_content(self, file_path: Path) -> str:
        """
        Format text file content with path and syntax highlighting.

        Args:
            file_path: Path to text file

        Returns:
            str: Formatted file content
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            ext = file_path.suffix.lstrip(".")

            return f"File: {file_path}\n" f"```{ext}\n" f"{content}\n" "```"
        except UnicodeDecodeError:
            raise ValueError("File appears to be binary or uses unsupported encoding")

    def cleanup(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __del__(self):
        """Ensure cleanup is called when the object is deleted."""
        self.cleanup()
