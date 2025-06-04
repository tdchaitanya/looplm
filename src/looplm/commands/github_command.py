# src/looplm/commands/github_command.py
import asyncio
import re
from typing import List

from gitingest import ingest

from .processor import CommandProcessor, ProcessingResult


class GithubProcessor(CommandProcessor):
    """Processor for @github command"""

    # Regex for validating GitHub URLs
    GITHUB_URL_PATTERN = re.compile(
        r"^https?://github\.com/[a-zA-Z0-9-]+/[a-zA-Z0-9._-]+/?.*$"
    )

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "Process and analyze GitHub repository contents"

    def validate(self, arg: str) -> bool:
        """Validate GitHub URL format

        Args:
            arg: GitHub URL to validate

        Returns:
            bool: True if URL is valid GitHub format
        """
        return bool(self.GITHUB_URL_PATTERN.match(arg))

    async def process(self, arg: str) -> ProcessingResult:
        """Process GitHub repository using gitingest

        Args:
            arg: GitHub URL to process

        Returns:
            ProcessingResult containing repository analysis
        """
        try:
            # Clean up URL (remove trailing slashes, etc)
            url = arg.rstrip("/")

            # Since ingest() is synchronous, run it in a thread pool
            loop = asyncio.get_event_loop()
            summary, tree, content = await loop.run_in_executor(None, ingest, url)

            # Format output
            tag_name = f"{self._get_repo_name(url)}"

            result = f"""
<{tag_name}>

{tree}

{content}
</{tag_name}>"""

            return ProcessingResult(content=result)

        except Exception as e:
            return ProcessingResult(
                content="", error=f"Error processing GitHub repository: {str(e)}"
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

    def get_completions(self, text: str) -> List[str]:
        """Get GitHub URL completions

        Args:
            text: Current input text

        Returns:
            List of completion suggestions
        """
        # For GitHub URLs, we don't provide dynamic completions
        # but we can suggest the basic URL structure
        if not text:
            return ["https://github.com/"]
        return []

    def _get_repo_name(self, url: str) -> str:
        """Extract repository name from URL

        Args:
            url: GitHub URL

        Returns:
            str: Repository name or full URL if parsing fails
        """
        try:
            # Extract repo name from URL
            match = re.search(r"github\.com/[^/]+/([^/]+)", url)
            if match:
                return match.group(1)
        except Exception:
            pass
        return url
