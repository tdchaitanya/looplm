# src/looplm/chat/console.py

from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
from rich.table import Table
from pathlib import Path
from ..config.manager import ConfigManager
from .prompt_manager import PromptManager

class ChatConsole:
    """Handles chat UI rendering and interaction"""

    def __init__(self, console: Optional[Console] = None):
        """Initialize chat console"""
        self.console = console or Console(
            force_terminal=True, force_interactive=True, width=None
        )
        self.prompt_manager = PromptManager(
            console=self.console,
            base_path=Path.cwd()
        )


    def display_welcome(self):
        """Display welcome message and instructions"""
        config_manager = ConfigManager()
        default_provider, _ = config_manager.get_default_provider()
        providers = config_manager.get_configured_providers()

        table = Table(title="Configured Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Default Model", style="green")
        table.add_column("Status", style="yellow")

        for provider, config in providers.items():
            display_name = config_manager.get_provider_display_name(provider, config)
            status = "DEFAULT" if provider == default_provider else "Configured"
            table.add_row(display_name, config["default_model"], status)

        self.console.print("\n💬 LoopLM Chat", style="bold blue")
        self.console.print(table)

        commands = {
            "/help or /h": "Show this help message",
            "/clear or /c": "Clear chat history",
            "/quit or /q": "chat session",
            "/save": "Save current session",
            "/load": "Load a saved session",
            "/new": "Start a new session",
            "/list": "List saved sessions",
            "/delete": "Delete a session",
            "/rename": "Rename current session",
            "/model": "Change model",
            "/system": "View/update system prompt",
            "/usage": "View token usage",
        }

        table = Table(title="Available Commands")
        table.add_column("command", style="cyan")
        table.add_column("description", style="yellow")

        for cmd, desc in commands.items():
            table.add_row(cmd, desc)

        self.console.print(table)

        # panel = Panel(
        #     Align.center(Text.from_markup(f"{logo}\n{help_text}"), vertical="middle"),
        #     border_style="bright_blue",
        #     padding=(1, 2),
        # )

        # self.console.print()
        # self.console.print(panel)
        # self.console.print()

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
        table.add_column("Last Updated", style="blue")

        for session in sessions:
            updated_at = datetime.fromisoformat(session["updated_at"])
            table.add_row(
                session["id"][:8],  # Show shortened ID
                session["name"],
                str(session["message_count"]),
                f"{session['total_tokens']:,}",
                updated_at.strftime("%Y-%m-%d %H:%M"),
            )

        self.console.print(table)

    def display_token_usage(self, title: str, usage: Dict):
        """Display token usage statistics"""
        table = Table(title=title)
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("Input Tokens", f"{usage['input_tokens']:,}")
        table.add_row("Output Tokens", f"{usage['output_tokens']:,}")
        table.add_row("Total Tokens", f"{usage['total_tokens']:,}")

        self.console.print(table)

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
                self.console.print(Markdown(content))

        except Exception:
            # Fallback to plain text if markdown parsing fails
            self.console.print(f"\n{time_str}{prefix} {content}", style=content_style)

    def prompt_user(self) -> str:
        """Get user input with improved prompt and file completion"""
        timestamp = datetime.now()
        # Format prompt parts
        time_str = timestamp.strftime('%H:%M')
        # Let prompt toolkit handle the styling
        prefix = f"{time_str} User ► "
        
        # Use PromptManager for input with completion
        user_input = self.prompt_manager.get_input(f"\n{time_str}{prefix}")
        
        if user_input.lower() in ("exit", "quit"):
            return "/quit"
            
        return user_input.strip()

    def display_error(self, message: str):
        """Display error message"""
        self.console.print(f"\nError: {message}", style="bold red")

    def display_success(self, message: str):
        """Display success message"""
        self.console.print(message, style="bold green")

    def display_info(self, message: str, style: Optional[str] = "blue"):
        """Display info message"""
        self.console.print(message, style=style)
