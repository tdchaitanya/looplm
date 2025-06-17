# src/looplm/commands/pdf_command.py
import base64
import os
from pathlib import Path
from typing import List, Optional, Tuple, Union
from urllib.parse import urlparse

try:
    from litellm.utils import supports_pdf_input
except ImportError:
    # Fallback if litellm is not available
    def supports_pdf_input(model: str, api_key: Optional[str] = None) -> bool:
        """Fallback PDF support check"""
        # Some common models that support PDF input
        pdf_supporting_models = [
            "bedrock/anthropic.claude-3-5-sonnet",
            "bedrock/anthropic.claude-3-sonnet",
            "bedrock/anthropic.claude-3-haiku",
            "anthropic.claude-3-5-sonnet",
            "anthropic.claude-3-sonnet",
            "anthropic.claude-3-haiku",
        ]
        return any(model.startswith(supported) for supported in pdf_supporting_models)


from .processor import CommandProcessor, ProcessingResult


class PDFProcessor(CommandProcessor):
    """Processor for @pdf command to include PDF documents in prompts for document-capable models"""

    # Supported PDF extensions
    PDF_EXTENSIONS = {".pdf"}

    @property
    def name(self) -> str:
        return "pdf"

    @property
    def description(self) -> str:
        return "Include a PDF document from file or URL for document-capable LLMs"

    def validate(self, arg: str) -> bool:
        """Validate PDF path/URL

        Args:
            arg: PDF path or URL to validate

        Returns:
            bool: True if PDF path/URL is valid
        """
        # Check if URL
        parsed = urlparse(arg)
        if parsed.scheme and parsed.netloc:
            return parsed.scheme in {"http", "https"}

        # Check if local file exists and is a PDF
        path = Path(arg)
        if path.is_absolute():
            return path.exists() and path.suffix.lower() in self.PDF_EXTENSIONS

        # Try relative to current directory and base path
        return (
            (Path.cwd() / path).exists()
            and (Path.cwd() / path).suffix.lower() in self.PDF_EXTENSIONS
        ) or (
            (self.base_path / path).exists()
            and (self.base_path / path).suffix.lower() in self.PDF_EXTENSIONS
        )

    async def process(self, arg: str) -> ProcessingResult:
        """Process PDF inclusion

        Args:
            arg: PDF path or URL

        Returns:
            ProcessingResult containing PDF content or error
        """
        try:
            is_url, resolved_path = self._resolve_path(arg)

            if is_url:
                # For URLs, we can just use the URL directly
                return self._format_pdf_content(
                    resolved_path, resolved_path, is_url=True
                )
            else:
                # For local files, we need to handle them
                return await self._handle_local_pdf(resolved_path)

        except Exception as e:
            return ProcessingResult(content="", error=str(e))

    def _resolve_path(self, path: str) -> Tuple[bool, str]:
        """Resolve PDF path or URL

        Args:
            path: PDF path or URL to resolve

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
                raise FileNotFoundError(f"PDF not found: {path_obj}")
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
            f"PDF not found: {path}\n"
            f"Tried locations:\n"
            f"  - Relative to current dir: {cwd_path}\n"
            f"  - Relative to base path: {base_path}"
        )

    async def _handle_local_pdf(self, file_path: str) -> ProcessingResult:
        """Handle local PDF processing

        Args:
            file_path: Path to local PDF file

        Returns:
            ProcessingResult containing PDF content or error
        """
        path = Path(file_path)
        if not path.exists():
            return ProcessingResult(content="", error=f"PDF not found: {file_path}")

        if path.suffix.lower() not in self.PDF_EXTENSIONS:
            return ProcessingResult(
                content="",
                error=f"Unsupported file format: {path.suffix}. Only PDF files are supported.",
            )

        try:
            # Encode local PDF to base64
            base64_pdf = self._encode_pdf(file_path)

            # Create data URL for PDF
            data_url = f"data:application/pdf;base64,{base64_pdf}"

            return self._format_pdf_content(file_path, data_url, is_url=False)

        except Exception as e:
            return ProcessingResult(
                content="", error=f"Error processing local PDF: {str(e)}"
            )

    def _encode_pdf(self, pdf_path: str) -> str:
        """Encode PDF to base64 string

        Args:
            pdf_path: Path to the PDF file

        Returns:
            str: Base64 encoded PDF string

        Raises:
            Exception: If there's an error reading or encoding the PDF
        """
        try:
            with open(pdf_path, "rb") as pdf_file:
                return base64.b64encode(pdf_file.read()).decode("utf-8")
        except Exception as e:
            raise Exception(f"Failed to encode PDF {pdf_path}: {str(e)}")

    def _format_pdf_content(
        self, path: str, pdf_data: str, is_url: bool = False
    ) -> ProcessingResult:
        """Format PDF content for inclusion in prompt

        Args:
            path: Original PDF path/URL (for display)
            pdf_data: PDF URL or data URL for the file
            is_url: Whether this is a URL or local file

        Returns:
            ProcessingResult with formatted content
        """
        # Use the basename if it's a file path
        display_name = (
            os.path.basename(path)
            if not path.startswith(("http://", "https://"))
            else path
        )
        tag_name = f"@pdf({display_name})"

        # Create file object based on litellm format
        if is_url:
            # For URLs, use file_id
            file_data = {
                "type": "file",
                "file": {
                    "file_id": pdf_data,
                },
            }
        else:
            # For local files, use file_data with base64 data URL
            file_data = {
                "type": "file",
                "file": {
                    "file_data": pdf_data,
                },
            }

        # Create formatted content (empty since we include metadata)
        content = ""

        # Include metadata in the ProcessingResult - this matches the structure expected by the LLM
        metadata = {"type": "file_url", "file_data": file_data}

        return ProcessingResult(content=content, metadata=metadata)

    def modify_input_text(self, command_name: str, arg: str, full_match: str) -> str:
        """Modify the input text for PDF commands

        Args:
            command_name: Name of the command (will be "pdf")
            arg: Command argument (the PDF path/URL)
            full_match: The complete command text that matched in the input (@pdf(...))

        Returns:
            str: Modified text to replace the command in the input
        """
        # Return empty string to remove the command from the input text
        # The actual PDF content will be handled via metadata
        return ""

    def get_completions(self, text: str) -> List[Union[str, Tuple[str, str]]]:
        """Get PDF path completions

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
                    # Only include directories and PDF files
                    if item.is_dir() or item.suffix.lower() in self.PDF_EXTENSIONS:
                        new_part = item.name
                        # Add type indicator with color
                        if item.is_dir():
                            display = f"\033[44;97m D \033[0m {new_part}"  # bright blue background with white text
                        else:
                            display = f"\033[41;97m P \033[0m {new_part}"  # red background with white text for PDFs
                        completions.append((prefix + new_part, display))
            except (PermissionError, OSError):
                pass

            return sorted(completions)

        except Exception:
            return []

    def check_model_support(self, model: str) -> bool:
        """Check if the model supports PDF input

        Args:
            model: Model name to check

        Returns:
            bool: True if model supports PDF input
        """
        try:
            return supports_pdf_input(model, None)
        except Exception:
            # Fallback check for common PDF-supporting models
            pdf_supporting_models = [
                "bedrock/anthropic.claude-3-5-sonnet",
                "bedrock/anthropic.claude-3-sonnet",
                "bedrock/anthropic.claude-3-haiku",
                "anthropic.claude-3-5-sonnet",
                "anthropic.claude-3-sonnet",
                "anthropic.claude-3-haiku",
            ]
            return any(
                model.startswith(supported) for supported in pdf_supporting_models
            )
