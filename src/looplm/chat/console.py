# src/looplm/chat/console.py

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pyperclip
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..config.manager import ConfigManager
from .prompt_manager import PromptManager
from .session import ChatSession, TokenUsage


class ChatConsole:
    """Handles chat UI rendering and interaction"""

    def __init__(self, console: Optional[Console] = None):
        """Initialize chat console"""
        self.console = console or Console(
            force_terminal=True,
            force_interactive=True,
            width=None,
        )
        self.prompt_manager = PromptManager(console=self.console, base_path=Path.cwd())
        self.current_session = None
        # Add key bindings for copying
        kb = KeyBindings()

        @kb.add("c-b")  # Ctrl+B
        @kb.add("escape", "b")
        def copy_to_clipboard(event):
            """Copy latest response to clipboard"""
            if self.current_session and self.current_session.latest_response:
                try:
                    pyperclip.copy(self.current_session.latest_response)
                except Exception as e:
                    pass

        self.key_bindings = kb

    def display_welcome(self):
        """Display welcome message and instructions"""
        config_manager = ConfigManager()
        default_provider, _ = config_manager.get_default_provider()
        providers = config_manager.get_configured_providers()

        # Provider info table
        provider_table = Table(title="Configured Providers")
        provider_table.add_column("Provider", style="cyan")
        provider_table.add_column("Models", style="green")
        provider_table.add_column("Default Model", style="yellow")
        provider_table.add_column("Status", style="yellow")

        for provider, config in providers.items():
            display_name = config_manager.get_provider_display_name(provider, config)

            # Get all models for this provider
            models = config_manager.get_provider_models(provider)
            models_str = ", ".join(models)

            default_model = config.get("default_model", "")
            status = "DEFAULT" if provider == default_provider else "Configured"

            provider_table.add_row(display_name, models_str, default_model, status)

        # Get available commands from the CommandManager
        from looplm.commands import CommandManager

        command_manager = CommandManager()
        available_commands = command_manager.get_available_commands()

        # Combined commands table
        commands_table = Table(
            title="LoopLM Commands & Shortcuts",
            title_style="bold blue",
            border_style="blue",
            show_header=True,
            header_style="bold cyan",
        )

        commands_table.add_column("Command", style="cyan", width=30)
        commands_table.add_column("Description", style="white")
        # Session commands
        commands_table.add_row("Session Management", "", style="bold cyan")
        commands_table.add_row("/new", "Start a new session")
        commands_table.add_row("/save", "Save current session")
        commands_table.add_row("/load", "Load a saved session")
        commands_table.add_row("/list", "List saved sessions")
        commands_table.add_row("/delete", "Delete a session")
        commands_table.add_row("/rename", "Rename current session")
        commands_table.add_row("/clear, /c", "Clear chat history")
        commands_table.add_row("/clear-last [N]", "Clear last N messages (default: 1)")
        commands_table.add_row(
            "/compact",
            "Summarize and compact conversation so far (reduces context/cost)",
        )
        commands_table.add_row("/compact-info", "Show compact status and statistics")
        commands_table.add_row(
            "/compact-reset", "Reset compact state and use full history"
        )
        commands_table.add_row("/quit, /q", "Exit chat session")
        commands_table.add_row("/help, /h", "Show this help message")

        # System commands
        commands_table.add_row("System Controls", "", style="bold yellow")
        commands_table.add_row("/model", "Change model")
        commands_table.add_row("/system", "View/update system prompt")
        commands_table.add_row("/usage", "View token usage")

        # Content commands
        commands_table.add_row("Content & Code", "", style="bold green")

        # Add command processors
        for cmd_name in available_commands:
            processor = command_manager.get_processor(cmd_name)
            if processor:
                if cmd_name != "shell":
                    # Standard @ commands
                    commands_table.add_row(f"@{cmd_name}(path)", processor.description)

        # Add shell command with $() syntax
        shell_processor = command_manager.get_processor("shell")
        if shell_processor:
            commands_table.add_row("$(command)", shell_processor.description)

        # Keyboard shortcuts
        commands_table.add_row("Keyboard Shortcuts", "", style="bold magenta")
        commands_table.add_row("Ctrl+B", "Copy last assistant response")

        # Display tables
        self.console.print("\n💬 LoopLM Chat", style="bold blue")
        self.console.print(provider_table)
        self.console.print("\n")
        self.console.print(commands_table)
        self.console.print("\n")

    def display_sessions(self, sessions: List[Dict]):
        """Display list of available chat sessions"""
        if not sessions:
            self.console.print("\nNo saved sessions found.", style="yellow")
            return

        table = Table(title="Saved Chat Sessions")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Messages", justify="right")
        table.add_column("Total Tokens", justify="right")
        table.add_column("Cost", justify="right")
        table.add_column("Last Updated", style="blue")
        temp_usage = TokenUsage()
        for session in sessions:
            updated_at = datetime.fromisoformat(session["updated_at"])
            cost = session.get("cost", 0.0)
            table.add_row(
                session["id"][:8],  # Show shortened ID
                session["name"],
                str(session["message_count"]),
                temp_usage.format_number(session["total_tokens"]),
                f"${cost:.6f}" if cost > 0 else "$0.000000",
                updated_at.strftime("%Y-%m-%d %H:%M"),
            )

        self.console.print(table)

    def display_token_usage(
        self, title: str, usage: Dict, show_automatically: bool = False
    ):
        """Display token usage statistics"""

        token_usage = TokenUsage(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            cost=usage.get("cost", 0.0),
        )
        table = Table(title=title)
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("Input Tokens", f"{usage['input_tokens']:,}")
        table.add_row("Output Tokens", f"{usage['output_tokens']:,}")
        table.add_row("Total Tokens", f"{usage['total_tokens']:,}")
        table.add_row("Cost", f"${usage['cost']:.6f}")

        self.console.print(table)

        if show_automatically:
            self.console.print("\n[dim]Session usage summary[/dim]")

    def display_provider_info(self, provider_name: str, model_name: str):
        """Display current provider and model information"""
        provider_msg = f"[bright_cyan]{provider_name}[/bright_cyan]"
        model_msg = f"[bright_green]{model_name}[/bright_green]"
        self.console.print(f"\n Using {model_msg} from {provider_msg}")
        self.console.print()

    def confirm_action(self, message: str) -> bool:
        """Get user confirmation for an action"""
        return Confirm.ask(message)

    def select_session(self, sessions: List[Dict]) -> Optional[str]:
        """Prompt user to select a session"""
        if not sessions:
            self.console.print("\nNo sessions available.", style="yellow")
            return None

        self.display_sessions(sessions)

        session_ids = {s["id"][:8]: s["id"] for s in sessions}
        while True:
            session_id = Prompt.ask(
                "\nEnter session ID (or 'cancel')", default="cancel"
            )

            if session_id.lower() == "cancel":
                return None

            if session_id in session_ids:
                return session_ids[session_id]

            self.console.print("Invalid session ID. Please try again.", style="red")

    def get_session_name(self, current_name: Optional[str] = None) -> Optional[str]:
        """Get session name from user"""
        default = current_name or "New Chat"
        name = Prompt.ask("Enter session name", default=default)
        return name if name != default else None

    def display_message(
        self, role: str, content: str, timestamp: Optional[datetime] = None
    ):
        """Display a chat message with improved formatting"""
        if role == "system":
            return  # Don't display system messages

        # Set up styling based on role
        if role == "user":
            prefix = "[bright_blue]User ►[/bright_blue]"
            content_style = "bright_white"
        else:  # assistant
            prefix = "[bright_green]Assistant ▣[/bright_green]"
            content_style = "bright_white"

        # Create timestamp string if provided
        time_str = f"[dim]{timestamp.strftime('%H:%M')}[/dim] " if timestamp else ""

        # Display the message
        try:
            if role == "user":
                # For user messages, simple format
                self.console.print(
                    f"\n{time_str}{prefix} {content}", style=content_style
                )
            else:
                # For assistant messages, add a newline and try markdown
                self.console.print(f"\n{time_str}{prefix}")
                md = Markdown(content, code_theme="monokai")
                # self.console.print(Markdown(content))
                self.console.print(md, soft_wrap=True)

        except Exception:
            # Fallback to plain text if markdown parsing fails
            self.console.print(f"\n{time_str}{prefix} {content}", style=content_style)

    def prompt_user(self) -> str:
        """Get user input with improved prompt and file completion"""
        timestamp = datetime.now()
        time_str = timestamp.strftime("%H:%M")
        prompt_text = f"{time_str} User ► "

        # Use PromptManager for input with completion and key bindings
        user_input = self.prompt_manager.get_input(
            f"\n{prompt_text}", key_bindings=self.key_bindings
        )

        if user_input.lower() in ("exit", "quit"):
            return "/quit"

        return user_input.strip()

    def set_current_session(self, session: "ChatSession"):
        """Set current active session for key bindings"""
        self.current_session = session

    def display_error(self, message: str):
        """Display error message"""
        from rich.markup import escape

        # Escape any Rich markup in the error message
        safe_message = escape(message)
        self.console.print(f"\nError: {safe_message}", style="bold red")

    def display_success(self, message: str):
        """Display success message"""
        self.console.print(message, style="bold green")

    def display_info(self, message: str, style: Optional[str] = "blue"):
        """Display info message"""
        self.console.print(message, style=style)
