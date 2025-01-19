# src/looplm/chat/commands/file_command.py

import mimetypes
from pathlib import Path
from typing import List, Optional
import aiofiles
from urllib.parse import urlparse
import aiohttp
import os
from ..commands.processor import CommandProcessor, ProcessingResult

class FileProcessor(CommandProcessor):
    """Processor for @file command"""

    # File extensions that can be directly read as text
    TEXT_EXTENSIONS = {
        ".txt", ".py", ".js", ".html", ".css", ".json", ".xml", ".md",
        ".csv", ".yml", ".yaml", ".ini", ".conf", ".sh", ".bash", ".sql",
        ".log", ".env", ".rs", ".go", ".java", ".cpp", ".c", ".h", ".hpp",
    }

    @property
    def name(self) -> str:
        return "file"

    @property
    def description(self) -> str:
        return "Include and process file contents"

    def validate(self, arg: str) -> bool:
        """Validate file path/URL"""
        # Check if URL
        parsed = urlparse(arg)
        if parsed.scheme and parsed.netloc:
            return parsed.scheme in {'http', 'https'}

        # Check if local file exists
        path = Path(arg)
        if path.is_absolute():
            return path.exists()

        # Try relative to current directory and base path
        return (Path.cwd() / path).exists() or (self.base_path / path).exists()

    async def process(self, arg: str) -> ProcessingResult:
        """Process file inclusion
        
        Args:
            arg: File path or URL
            
        Returns:
            ProcessingResult containing file contents or error
        """
        try:
            is_url, resolved_path = self._resolve_path(arg)
            
            if is_url:
                return await self._handle_url(resolved_path)
            else:
                return await self._handle_local_file(resolved_path)
                
        except Exception as e:
            return ProcessingResult(
                content="",
                error=str(e)
            )

    def _resolve_path(self, path: str) -> tuple[bool, str]:
        """Resolve file path or URL
        
        Args:
            path: File path or URL to resolve
            
        Returns:
            Tuple of (is_url, resolved_path)
        """
        parsed = urlparse(path)
        is_url = bool(parsed.scheme and parsed.netloc)

        if is_url:
            return True, path

        path_obj = Path(path)
        if path_obj.is_absolute():
            if not path_obj.exists():
                raise FileNotFoundError(f"File not found: {path_obj}")
            return False, str(path_obj.resolve())

        # Try relative to current directory
        cwd_path = Path.cwd() / path_obj
        if cwd_path.exists():
            return False, str(cwd_path.resolve())

        # Try relative to base path
        base_path = self.base_path / path_obj
        if base_path.exists():
            return False, str(base_path.resolve())

        raise FileNotFoundError(
            f"File not found: {path}\n"
            f"Tried locations:\n"
            f"  - Relative to current dir: {cwd_path}\n"
            f"  - Relative to base path: {base_path}"
        )

    async def _handle_url(self, url: str) -> ProcessingResult:
        """Handle URL content retrieval
        
        Args:
            url: URL to process
            
        Returns:
            ProcessingResult containing content or error
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return ProcessingResult(
                            content="",
                            error=f"Failed to fetch URL: {response.status}"
                        )

                    content = await response.text()
                    ext = mimetypes.guess_extension(response.headers.get('content-type', ''))
                    
                    return ProcessingResult(
                        content=self._format_content(content, ext, url)
                    )
                    
        except Exception as e:
            return ProcessingResult(
                content="",
                error=f"Error fetching URL: {str(e)}"
            )

    async def _handle_local_file(self, file_path: str) -> ProcessingResult:
        """Handle local file processing
        
        Args:
            file_path: Path to local file
            
        Returns:
            ProcessingResult containing content or error
        """
        path = Path(file_path)
        if not path.exists():
            return ProcessingResult(
                content="",
                error=f"File not found: {file_path}"
            )

        if path.suffix.lower() not in self.TEXT_EXTENSIONS:
            return ProcessingResult(
                content="",
                error=f"Unsupported file type: {path.suffix}"
            )

        try:
            async with aiofiles.open(path, 'r') as f:
                content = await f.read()
                return ProcessingResult(
                    content=self._format_content(content, path.suffix, str(path))
                )
        except Exception as e:
            return ProcessingResult(
                content="",
                error=f"Error reading file: {str(e)}"
            )

    def _format_content(self, content: str, extension: str, path: str) -> str:
        """Format file content with syntax highlighting
        
        Args:
            content: Raw file content
            extension: File extension for syntax highlighting
            path: Original file path/URL
            
        Returns:
            Formatted content string
        """
        tag_name = f"@file({os.path.basename(path)})"
#         return f"""<{tag_name}>
# Path: {path}

# Content:
# {content}
# </{tag_name}>
# """
        return f"""<{tag_name}>
{content}
</{tag_name}>
"""
    def get_completions(self, text: str) -> List[str]:
        """Get file path completions
        
        Args:
            text: Current input text
            
        Returns:
            List of completion suggestions
        """
        path = Path(text)
        
        # Handle absolute paths
        if path.is_absolute():
            base = path.parent
        else:
            # Try both cwd and base_path
            cwd_base = Path.cwd() / path.parent
            base_path_base = self.base_path / path.parent
            
            base = cwd_base if cwd_base.exists() else base_path_base
        
        if not base.exists():
            return []
            
        # Get matching files
        pattern = f"{path.name}*" if path.name else "*"
        completions = []
        
        for item in base.glob(pattern):
            prefix = text[:text.rfind('/') + 1] if '/' in text else ''
            new_part = str(item.name)
            if item.is_dir():
                new_part += "/" 
            completions.append(prefix + new_part)
            
        return completions