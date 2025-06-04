# Example: Creating a Custom Command
# custom_date_command.py - A command that gets the current date/time in various formats

import datetime
from typing import List

from looplm.commands.processor import CommandProcessor, ProcessingResult


class DateProcessor(CommandProcessor):
    """Processor for @date command that returns formatted date/time"""

    @property
    def name(self) -> str:
        return "date"

    @property
    def description(self) -> str:
        return "Get the current date and time in various formats"

    def validate(self, arg: str) -> bool:
        """Validate format argument

        Args:
            arg: Format string (optional)

        Returns:
            bool: Always true since any format string is valid
        """
        # All arguments are valid (empty means default format)
        return True

    async def process(self, arg: str) -> ProcessingResult:
        """Process date command

        Args:
            arg: Format string (optional)

        Returns:
            ProcessingResult with formatted date
        """
        try:
            now = datetime.datetime.now()

            # If no format provided, use default
            if not arg.strip():
                formatted = now.strftime("%Y-%m-%d %H:%M:%S")
                formats = {
                    "ISO": now.isoformat(),
                    "RFC": now.strftime("%a, %d %b %Y %H:%M:%S"),
                    "Short": now.strftime("%m/%d/%Y"),
                    "Time": now.strftime("%H:%M:%S"),
                }

                result = f"Current date and time: {formatted}\n\n"
                result += "Available formats:\n"
                for name, value in formats.items():
                    result += f"- {name}: {value}\n"
            else:
                # Try to use the provided format string
                try:
                    formatted = now.strftime(arg)
                    result = formatted
                except ValueError:
                    return ProcessingResult(
                        content="", error=f"Invalid date format: {arg}"
                    )

            return ProcessingResult(content=f"<@date>\n{result}\n</@date>")

        except Exception as e:
            return ProcessingResult(
                content="", error=f"Error processing date: {str(e)}"
            )

    def get_completions(self, text: str) -> List[str]:
        """Get format completions

        Args:
            text: Current input text

        Returns:
            List of common format strings
        """
        common_formats = [
            "%Y-%m-%d",  # 2023-04-25
            "%Y-%m-%d %H:%M:%S",  # 2023-04-25 14:30:45
            "%m/%d/%Y",  # 04/25/2023
            "%d/%m/%Y",  # 25/04/2023
            "%b %d, %Y",  # Apr 25, 2023
            "%H:%M:%S",  # 14:30:45
            "%I:%M %p",  # 02:30 PM
        ]

        return [fmt for fmt in common_formats if fmt.startswith(text)]


# To register and use the custom command:
from looplm.commands import CommandManager

# Register the custom command with the command manager
command_manager = CommandManager()
command_manager.register_command(DateProcessor)

# Now you can use @date in your prompts!
# Examples:
# @date - Shows current date/time with available formats
# @date(%Y-%m-%d) - Shows date in YYYY-MM-DD format
# @date(%I:%M %p) - Shows time in HH:MM AM/PM format
