# src/looplm/preprocessor/files.py

import re
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Tuple, Optional
import mimetypes
# from markitdown import MarkItDown
import tempfile

class FilePreprocessor:
    """Handles file inclusion preprocessing in prompts using @file directives."""

    # File extensions that can be directly read as text
    TEXT_EXTENSIONS = {
        '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.csv',
        '.yml', '.yaml', '.ini', '.conf', '.sh', '.bash', '.sql', '.log',
        '.env', '.rs', '.go', '.java', '.cpp', '.c', '.h', '.hpp'
    }

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

    def process_prompt(self, prompt: str) -> str:
        """
        Process a prompt and replace all @file directives with file contents.

        Supports formats:
        - @file("path/to/file")
        - @file path/to/file
        - @file(path/to/file)

        Args:
            prompt: The input prompt containing @file directives

        Returns:
            str: Processed prompt with file contents included

        Raises:
            FileNotFoundError: If a local file cannot be found
            ValueError: If file format is unsupported or URL is invalid
            RuntimeError: If there are issues processing the file
        """
        # Pattern for @file("path") format
        quoted_pattern = r'@file\("([^"]+)"\)'
        # Pattern for @file path format
        unquoted_pattern = r'@file\s+([^\s"]+)'
        # Pattern for @file(path) format
        unquoted_pattern_bracket = r'@file\(([^)]+)\)'

        def replace_match(match):
            file_path = match.group(1)
            try:
                return self._process_file_directive(file_path)
            except Exception as e:
                # Keep the original directive and append error message
                return f'@file("{file_path}") // Error: {str(e)}'

        # Process both patterns
        prompt = re.sub(quoted_pattern, replace_match, prompt)
        prompt = re.sub(unquoted_pattern, replace_match, prompt)
        prompt = re.sub(unquoted_pattern_bracket, replace_match, prompt)

        return prompt

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
        Handle URL-based file inclusion.

        Args:
            url: URL to download and process

        Returns:
            str: Processed file content

        Raises:
            ValueError: If URL is invalid or content type is unsupported
        """
        try:
            with urllib.request.urlopen(url) as response:
                content_type = response.headers.get('content-type', '').split(';')[0]

                # Create temp file with appropriate extension
                ext = mimetypes.guess_extension(content_type) or '.tmp'
                temp_file = self.temp_dir / f"download{ext}"

                # Download file
                with open(temp_file, 'wb') as f:
                    f.write(response.read())

                # Process the downloaded file
                return self._handle_local_file(temp_file)

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
        # try:
            # md = MarkItDown()
            # result = md.convert(str(file_path))
            # return result.text_content
        # except Exception as e:
        #     raise ValueError(f"Unsupported file format or conversion error: {str(e)}")

    def _format_text_content(self, file_path: Path) -> str:
        """
        Format text file content with path and syntax highlighting.

        Args:
            file_path: Path to text file

        Returns:
            str: Formatted file content
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            ext = file_path.suffix.lstrip('.')

            return (
                f"File: {file_path}\n"
                f"```{ext}\n"
                f"{content}\n"
                "```"
            )
        except UnicodeDecodeError:
            raise ValueError("File appears to be binary or uses unsupported encoding")

    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)