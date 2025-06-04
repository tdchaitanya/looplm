# src/looplm/commands/shell_command.py

import asyncio
import re
import shlex
from typing import List

from .processor import CommandProcessor, ProcessingResult


class ShellCommandProcessor(CommandProcessor):
    """Processor for $() shell commands"""

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "Execute shell commands and capture output"

    def validate(self, arg: str) -> bool:
        """Validate shell command

        Args:
            arg: Shell command to validate

        Returns:
            bool: True if command seems valid
        """
        # Basic validation - ensure command is not empty and doesn't contain dangerous operations
        if not arg.strip():
            return False

        # List of dangerous operations we want to prevent
        dangerous_patterns = [
            r"rm\s+-rf\s+[/*]",  # Dangerous rm commands
            r">[>]?",  # Output redirection
            r"\|\s*rm",  # Pipe to rm
            r"mkfs",  # Format filesystem
            r"dd",  # Disk operations
            r";\s*rm",  # Command chain with rm
            r"&\s*rm",  # Background rm
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, arg):
                return False

        return True

    async def process(self, arg: str) -> ProcessingResult:
        """Execute shell command and capture output

        Args:
            arg: Shell command to execute

        Returns:
            ProcessingResult containing command output
        """
        try:
            # Create subprocess with captured output
            process = await asyncio.create_subprocess_shell(
                arg,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.base_path),
            )

            # Wait for command to complete with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=300.0  # 5 min timeout
                )
            except asyncio.TimeoutError:
                # Try to terminate the process
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()  # Force kill if terminate doesn't work
                return ProcessingResult(
                    content="", error="Command timed out after 30 seconds"
                )

            # Check for errors
            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                if error_msg:
                    return ProcessingResult(
                        content="", error=f"Command failed: {error_msg}"
                    )
                return ProcessingResult(
                    content="",
                    error=f"Command failed with return code {process.returncode}",
                )

            # Format successful output
            output = stdout.decode("utf-8", errors="replace").strip()
            formatted_output = f"""
<$({arg})>
{output if output else "(No output)"}
</$({arg})>"""

            return ProcessingResult(content=formatted_output)

        except Exception as e:
            return ProcessingResult(
                content="", error=f"Error executing command: {str(e)}"
            )

    def modify_input_text(self, command_name: str, arg: str, full_match: str) -> str:
        """Modify the input text for shell commands

        Args:
            command_name: Name of the command (will be "shell")
            arg: Command argument (the shell command text)
            full_match: The complete command text that matched in the input ($(command))

        Returns:
            str: Modified text to replace the command in the input
        """
        # By default, keep the original $() syntax unchanged
        return full_match

    def get_completions(self, text: str) -> List[str]:
        """Get command completions

        Args:
            text: Current command text

        Returns:
            List of completion suggestions
        """
        try:
            import subprocess

            # Only provide completions if we have enough text
            if not text or len(text) < 2:
                return []

            # Use bash completion if available
            command = f"compgen -c {shlex.quote(text)}"
            output = subprocess.check_output(
                command, shell=True, text=True, stderr=subprocess.PIPE
            )

            return output.splitlines()

        except Exception:
            return []
