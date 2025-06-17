# src/looplm/commands/image_command.py
import base64
import mimetypes
import os
from pathlib import Path
from typing import List, Optional, Tuple, Union
from urllib.parse import urlparse

from .processor import CommandProcessor, ProcessingResult


class ImageProcessor(CommandProcessor):
    """Processor for @image command to include images in prompts for vision models"""

    # Supported image extensions
    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".tiff",
        ".tif",
    }

    @property
    def name(self) -> str:
        return "image"

    @property
    def description(self) -> str:
        return "Include an image from file or URL for vision-capable LLMs"

    def validate(self, arg: str) -> bool:
        """Validate image path/URL

        Args:
            arg: Image path or URL to validate

        Returns:
            bool: True if image path/URL is valid
        """
        # Check if URL
        parsed = urlparse(arg)
        if parsed.scheme and parsed.netloc:
            return parsed.scheme in {"http", "https"}

        # Check if local file exists and is an image
        path = Path(arg)
        if path.is_absolute():
            return path.exists() and path.suffix.lower() in self.IMAGE_EXTENSIONS

        # Try relative to current directory and base path
        return (
            (Path.cwd() / path).exists()
            and (Path.cwd() / path).suffix.lower() in self.IMAGE_EXTENSIONS
        ) or (
            (self.base_path / path).exists()
            and (self.base_path / path).suffix.lower() in self.IMAGE_EXTENSIONS
        )

    async def process(self, arg: str) -> ProcessingResult:
        """Process image inclusion

        Args:
            arg: Image path or URL

        Returns:
            ProcessingResult containing image URL or error
        """
        try:
            is_url, resolved_path = self._resolve_path(arg)

            if is_url:
                # For URLs, we can just use the URL directly
                return self._format_image_content(resolved_path, resolved_path)
            else:
                # For local files, we need to handle them
                return await self._handle_local_image(resolved_path)

        except Exception as e:
            return ProcessingResult(content="", error=str(e))

    def _resolve_path(self, path: str) -> Tuple[bool, str]:
        """Resolve image path or URL

        Args:
            path: Image path or URL to resolve

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
                raise FileNotFoundError(f"Image not found: {path_obj}")
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
            f"Image not found: {path}\n"
            f"Tried locations:\n"
            f"  - Relative to current dir: {cwd_path}\n"
            f"  - Relative to base path: {base_path}"
        )

    async def _handle_local_image(self, file_path: str) -> ProcessingResult:
        """Handle local image processing

        Args:
            file_path: Path to local image file

        Returns:
            ProcessingResult containing image content or error
        """
        path = Path(file_path)
        if not path.exists():
            return ProcessingResult(content="", error=f"Image not found: {file_path}")

        if path.suffix.lower() not in self.IMAGE_EXTENSIONS:
            return ProcessingResult(
                content="", error=f"Unsupported image format: {path.suffix}"
            )

        try:
            # Encode local image to base64
            base64_image = self._encode_image(file_path)

            # Get the mime type for the image
            mime_type = (
                mimetypes.guess_type(file_path)[0] or f"image/{path.suffix.lstrip('.')}"
            )

            # Create data URL
            data_url = f"data:{mime_type};base64,{base64_image}"

            return self._format_image_content(file_path, data_url, mime_type)

        except Exception as e:
            return ProcessingResult(
                content="", error=f"Error processing local image: {str(e)}"
            )

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string

        Args:
            image_path: Path to the image file

        Returns:
            str: Base64 encoded image string

        Raises:
            Exception: If there's an error reading or encoding the image
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            raise Exception(f"Failed to encode image {image_path}: {str(e)}")

    def _format_image_content(
        self, path: str, image_url: str, mime_type: Optional[str] = None
    ) -> ProcessingResult:
        """Format image content for inclusion in prompt

        Args:
            path: Original image path/URL (for display)
            image_url: Actual URL to access the image
            mime_type: Optional MIME type of the image

        Returns:
            ProcessingResult with formatted content
        """
        # Use the basename if it's a file path
        display_name = (
            os.path.basename(path)
            if not path.startswith(("http://", "https://"))
            else path
        )
        tag_name = f"@image({display_name})"

        # Create JSON object for the image URL
        image_json = {"url": image_url}

        if mime_type:
            image_json["format"] = mime_type

        # Create formatted content
        content = """"""

        # Include metadata in the ProcessingResult
        metadata = {"type": "image_url", "image_url": image_json}

        return ProcessingResult(content=content, metadata=metadata)

    def modify_input_text(self, command_name: str, arg: str, full_match: str) -> str:
        """Modify the input text for image commands

        Args:
            command_name: Name of the command (will be "image")
            arg: Command argument (the image path/URL)
            full_match: The complete command text that matched in the input (@image(...))

        Returns:
            str: Modified text to replace the command in the input
        """
        # return the image path/URL
        # return arg.strip()

        return ""

    def get_completions(self, text: str) -> List[Union[str, Tuple[str, str]]]:
        """Get image path completions

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
                    # Only include directories and image files
                    if item.is_dir() or item.suffix.lower() in self.IMAGE_EXTENSIONS:
                        new_part = item.name
                        # Add type indicator with color
                        if item.is_dir():
                            display = f"\033[44;97m D \033[0m {new_part}"  # bright blue background with white text
                        else:
                            display = f"\033[45;97m I \033[0m {new_part}"  # magenta background with white text for images
                        completions.append((prefix + new_part, display))
            except (PermissionError, OSError):
                pass

            return sorted(completions)

        except Exception:
            return []
