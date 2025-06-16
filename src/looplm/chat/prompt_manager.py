# src/looplm/chat/prompt_manager.py - Updated for new command system

import os
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console

from looplm.commands import CommandManager


class CommandCompleter(Completer):
    """Completer for @ commands and chat commands with context-aware completion"""

    def __init__(self, base_path: Path = None):
        """Initialize completer with command manager

        Args:
            base_path: Base path for resolving relative paths
        """
        # Use the singleton CommandManager instead of creating a new registry
        self.command_manager = CommandManager(base_path=base_path or Path.cwd())

        # Define chat commands with descriptions
        # Format: "primary_command": {"aliases": ["alias1", "alias2"], "description": "..."}
        self.chat_commands = {
            # Basic commands
            "quit": {"aliases": ["q"], "description": "Exit chat session"},
            "help": {"aliases": ["h"], "description": "Show this help message"},
            "clear": {"aliases": ["c"], "description": "Clear chat history"},
            "clear-last": {
                "aliases": [],
                "description": "Clear last N messages (default: 1)",
            },
            # Session management
            "save": {"aliases": [], "description": "Save current session"},
            "load": {"aliases": [], "description": "Load a saved session"},
            "new": {"aliases": [], "description": "Start a new session"},
            "list": {"aliases": [], "description": "List saved sessions"},
            "delete": {"aliases": [], "description": "Delete a session"},
            "rename": {"aliases": [], "description": "Rename current session"},
            # Configuration
            "model": {"aliases": [], "description": "Change model"},
            "system": {"aliases": [], "description": "View/update system prompt"},
            "usage": {"aliases": [], "description": "View token usage"},
            "compact": {
                "aliases": [],
                "description": "Summarize and compact conversation so far (reduces context/cost)",
            },
            "compact-info": {
                "aliases": [],
                "description": "Show compact status and statistics",
            },
            "compact-reset": {
                "aliases": [],
                "description": "Reset compact state and use full history",
            },
        }

        # Create a flat mapping for quick lookup (includes both primary commands and aliases)
        self.command_lookup = {}
        for primary, data in self.chat_commands.items():
            self.command_lookup[primary] = primary
            for alias in data["aliases"]:
                self.command_lookup[alias] = primary

    def _get_chat_command_completions(self, text_after_slash: str):
        """Get completions for chat commands starting with /

        Args:
            text_after_slash: Text after the / symbol

        Returns:
            Generator of completions
        """
        # Track which primary commands we've already shown to avoid duplicates
        shown_commands = set()

        for cmd_or_alias in self.command_lookup.keys():
            if cmd_or_alias.startswith(text_after_slash.lower()):
                primary_cmd = self.command_lookup[cmd_or_alias]

                # Skip if we've already shown this primary command
                if primary_cmd in shown_commands:
                    continue

                shown_commands.add(primary_cmd)
                cmd_data = self.chat_commands[primary_cmd]

                # Format the command display with aliases
                if cmd_data["aliases"]:
                    aliases_str = "/" + ", /".join(cmd_data["aliases"])
                    command_display = f"{primary_cmd} ({aliases_str})"
                else:
                    command_display = primary_cmd

                # Create a completion with command, aliases, and description
                display_text = (
                    f"\033[1;90m/{command_display}\033[0m - {cmd_data['description']}"
                )

                # The completion text should be the specific command/alias that was typed
                completion_text = (
                    cmd_or_alias
                    if cmd_or_alias.startswith(text_after_slash.lower())
                    else primary_cmd
                )

                yield Completion(
                    completion_text,
                    start_position=-len(text_after_slash),
                    display=ANSI(display_text),
                )

    def get_completions(self, document, complete_event):
        """Get completions for current input

        Args:
            document: Current document
            complete_event: Completion event

        Returns:
            Generator of completions
        """
        text = document.text_before_cursor

        # Check for chat commands starting with /
        slash_pos = text.rfind("/")
        if slash_pos != -1:
            # Check if this is a chat command (not part of a path)
            text_before_slash = text[:slash_pos]
            # If the slash is at the beginning or after whitespace, treat as command
            if slash_pos == 0 or text_before_slash[-1].isspace():
                text_after_slash = text[slash_pos + 1 :]
                # Only provide completions if we don't have spaces after the slash
                # (to avoid interfering with command arguments)
                if " " not in text_after_slash:
                    yield from self._get_chat_command_completions(text_after_slash)
                    return

        # Find any @ symbol before cursor
        at_pos = text.rfind("@")
        if at_pos == -1:
            return

        # Get text after @ symbol
        after_at = text[at_pos:]
        if "(" not in after_at:
            # Check if the text after @ matches start of any command
            potential_cmd = after_at[1:]  # Remove @
            matching_commands = [
                cmd
                for cmd in self.command_manager.registry._processors.keys()
                if cmd.startswith(potential_cmd)
            ]
            if not matching_commands:
                return  # Don't show completions for non-matching @ symbols

        # Calculate start position
        if "(" in after_at:
            cmd_name = after_at[1 : after_at.find("(")]
            path_text = after_at[after_at.find("(") + 1 :]
            # Get processor for command
            processor = self.command_manager.get_processor(cmd_name)
            if processor:
                # Get completion from processor
                completions = processor.get_completions(path_text)
                # start position calculation
                start_pos = -len(path_text)

                for completion_tuple in completions:
                    if isinstance(completion_tuple, tuple):
                        completion_text, display_text = completion_tuple
                        yield Completion(
                            completion_text,
                            start_position=start_pos,
                            display=ANSI(display_text),
                        )
                    else:
                        # Handle case where completion isn't a tuple
                        yield Completion(completion_tuple, start_position=start_pos)

        else:
            # Get @ command completions with descriptions
            completions = self.command_manager.registry.get_completions(after_at)
            for completion in completions:
                # Get the command name (remove @ if present)
                cmd_name = completion.replace("@", "")

                # Get the processor to access its description
                processor = self.command_manager.get_processor(cmd_name)
                if processor:
                    # Format with description
                    display_text = (
                        f"\033[1;90m{completion}\033[0m - {processor.description}"
                    )
                    yield Completion(
                        completion,
                        start_position=-len(after_at),
                        display=ANSI(display_text),
                    )
                else:
                    # Fallback to just the command name if processor not found
                    yield Completion(
                        completion,
                        start_position=-len(after_at),
                    )


class PromptManager:
    """Manages prompt toolkit integration with custom completions and file-based prompt loading"""

    SHIPPED_PROMPT_DIR = Path(__file__).parent.parent / "prompts"
    USER_PROMPT_DIR = Path.home() / ".looplm" / "prompts"

    def __init__(self, console: Console = None, base_path: str = None):
        """Initialize prompt manager

        Args:
            console: Optional rich console for output
            base_path: Base path for resolving file paths
        """
        self.console = console or Console()
        self.base_path = base_path or os.getcwd()

        # Setup prompt styling
        self.style = Style.from_dict(
            {
                "prompt": "#0000ff bold",
                "timestamp": "#666666",
            }
        )

        # Setup history
        history_file = os.path.expanduser("~/.looplm/history")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)

        # Setup key bindings
        kb = KeyBindings()

        @kb.add("(")
        def _(event):
            """Auto-close parentheses"""
            event.current_buffer.insert_text("()")
            event.current_buffer.cursor_left()
            event.current_buffer.start_completion()

        @kb.add('"')
        def _(event):
            """Auto-close quotes"""
            buf = event.current_buffer
            if buf.document.current_char == '"':
                buf.cursor_right()
            else:
                buf.insert_text('""')
                buf.cursor_left()

        @kb.add("/")
        def _(event):
            """Auto-trigger completion after slash (for paths and commands)"""
            event.current_buffer.insert_text("/")
            event.current_buffer.start_completion()

        # Initialize prompt session with command completion
        self.session = PromptSession(
            history=FileHistory(history_file),
            auto_suggest=AutoSuggestFromHistory(),
            completer=CommandCompleter(base_path=Path(self.base_path)),
            style=self.style,
            complete_while_typing=True,
            key_bindings=kb,
            complete_in_thread=True,
        )

        # Load shipped and user prompts
        self.shipped_prompts = self._load_prompts_from_dir(self.SHIPPED_PROMPT_DIR)
        self.user_prompts = self._load_prompts_from_dir(self.USER_PROMPT_DIR)

    def _load_prompts_from_dir(self, dir_path: Path) -> dict:
        prompts = {}
        if dir_path.exists():
            for file in dir_path.glob("*.txt"):
                name = file.stem
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        prompts[name] = f.read().strip()
                except Exception:
                    continue
        return prompts

    def get_prompt(self, name: str) -> str:
        """Get a prompt by name, preferring user prompt over shipped default."""
        if name in self.user_prompts:
            return self.user_prompts[name]
        if name in self.shipped_prompts:
            return self.shipped_prompts[name]
        raise KeyError(f"Prompt '{name}' not found in user or shipped prompts.")

    def get_compact_prompt(self) -> str:
        """Return the compact prompt (default or user-customized)."""
        return self.get_prompt("compact")

    def create_prompt_fragments(self, prompt_str: str):
        """Create styled prompt fragments"""
        # Extract just the timestamp part (everything before the first space)
        parts = prompt_str.split(" ", 1)
        timestamp = parts[0] if parts else ""

        return [
            ("class:timestamp", timestamp),  # timestamp
            ("", " "),
            ("class:prompt", "User ► "),
        ]

    def get_input(self, prompt_str: str = "", key_bindings=None) -> str:
        """Get user input with completion and history"""
        try:
            if key_bindings:
                combined_bindings = KeyBindings()

                # Copy existing bindings
                if self.session.key_bindings:
                    for binding in self.session.key_bindings.bindings:
                        combined_bindings.add(*binding.keys)(binding.handler)

                # Add new bindings
                for binding in key_bindings.bindings:
                    combined_bindings.add(*binding.keys)(binding.handler)
                kb = combined_bindings

            else:
                kb = self.session.key_bindings

            result = self.session.prompt(
                self.create_prompt_fragments(prompt_str),
                style=self.style,
                complete_in_thread=True,
                key_bindings=kb,
            )
            return result.strip()
        except KeyboardInterrupt:
            return ""
        except EOFError:
            return "exit"
