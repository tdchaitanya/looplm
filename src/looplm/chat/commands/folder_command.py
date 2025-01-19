# src/looplm/chat/commands/folder_command.py
from pathlib import Path
from typing import List
from gitingest import ingest
import os
from ..commands.processor import CommandProcessor, ProcessingResult

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
            summary, tree, content = ingest(str(path))
           
            tag_name = f"@folder({os.path.basename(str(path))})"
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
                content="",
                error=f"Error processing folder: {str(e)}"
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

    def get_completions(self, text: str) -> List[str]:
        """Get folder path completions
        
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
            
        # Get matching directories
        pattern = f"{path.name}*" if path.name else "*"
        completions = []
        
        for item in base.glob(pattern):
            if item.is_dir():
                prefix = text[:text.rfind('/') + 1] if '/' in text else ''
                new_part = str(item.name) + "/" 
                completions.append(prefix + new_part)
            
        return completions