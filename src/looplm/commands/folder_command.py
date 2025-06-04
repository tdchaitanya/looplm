# src/looplm/commands/folder_command.py
import asyncio
import os
from pathlib import Path
from typing import List, Tuple, Union

from gitingest import ingest

from .processor import CommandProcessor, ProcessingResult


class FolderProcessor(CommandProcessor):
    """Processor for @folder command"""

    @property
    def name(self) -> str:
        return "folder"

    @property
    def description(self) -> str:
        return "Process and summarize folder contents"

    def validate(self, arg: str) -> bool:
        """Validate folder path exists

        Args:
            arg: Folder path to validate

        Returns:
            bool: True if folder exists
        """
        path = Path(arg)

        # Handle absolute paths
        if path.is_absolute():
            return path.is_dir() and path.exists()

        # Try relative to current directory
        cwd_path = Path.cwd() / path
        if cwd_path.exists():
            return cwd_path.is_dir()

        # Try relative to base path
        base_path = self.base_path / path
        return base_path.exists() and base_path.is_dir()

    async def process(self, arg: str) -> ProcessingResult:
        """Process folder contents using gitingest

        Args:
            arg: Folder path to process

        Returns:
            ProcessingResult containing folder analysis
        """
        try:
            path = self._resolve_path(arg)
            loop = asyncio.get_event_loop()
            summary, tree, content = await loop.run_in_executor(None, ingest, str(path))

            tag_name = f"{os.path.basename(str(path))}"
            result = f"""
<{tag_name}>
```
{tree}
```

{content}
</{tag_name}>"""

            return ProcessingResult(content=result)

        except Exception as e:
            return ProcessingResult(
                content="", error=f"Error processing folder: {str(e)}"
            )

    def _resolve_path(self, path: str) -> Path:
        """Resolve folder path

        Args:
            path: Folder path to resolve

        Returns:
            Path: Resolved absolute path

        Raises:
            FileNotFoundError: If folder doesn't exist
        """
        path_obj = Path(path)

        if path_obj.is_absolute():
            if not path_obj.exists() or not path_obj.is_dir():
                raise FileNotFoundError(f"Folder not found: {path_obj}")
            return path_obj.resolve()

        # Try relative to current directory
        cwd_path = Path.cwd() / path_obj
        if cwd_path.exists() and cwd_path.is_dir():
            return cwd_path.resolve()

        # Try relative to base path
        base_path = self.base_path / path_obj
        if base_path.exists() and base_path.is_dir():
            return base_path.resolve()

        raise FileNotFoundError(
            f"Folder not found: {path}\n"
            f"Tried locations:\n"
            f"  - Relative to current dir: {cwd_path}\n"
            f"  - Relative to base path: {base_path}"
        )

    def modify_input_text(self, command_name: str, arg: str, full_match: str) -> str:
        """Modify the input text for image commands

        Args:
            command_name: Name of the command (will be "image")
            arg: Command argument (the image path/URL)
            full_match: The complete command text that matched in the input (@image(...))

        Returns:
            str: Modified text to replace the command in the input
        """
        return arg.strip()

    def get_completions(self, text: str) -> List[Union[str, Tuple[str, str]]]:
        """Get folder path completions

        Args:
            text: Current input text

        Returns:
            List of completion suggestions
        """
        try:
            path = Path(text)

            if text.endswith("/"):
                base = path
                prefix = text
                pattern = "*"
            else:
                base = path.parent
                prefix = text[: text.rfind("/") + 1] if "/" in text else ""
                pattern = f"{path.name}*" if path.name else "*"

            # Handle absolute paths
            if path.is_absolute():
                base = base if base.exists() else Path("/")
            else:
                # Try both cwd and base_path
                cwd_base = Path.cwd() / base
                base_path_base = self.base_path / base
                base = cwd_base if cwd_base.exists() else base_path_base
                if not base.exists():
                    base = Path(".")

            completions = []
            try:
                for item in base.glob(pattern):
                    if item.is_dir():
                        new_part = item.name
                        # Add type indicator (D/F)
                        display = f"\033[44;97m D \033[0m {new_part}"  # bright blue background with white text
                        completions.append((prefix + new_part, display))
            except (PermissionError, OSError):
                pass

            return sorted(completions)

        except Exception:
            return []
