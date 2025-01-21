# src/looplm/chat/commands.py

from typing import Optional

from rich.prompt import Prompt
from rich.table import Table

from ..config.manager import ConfigManager
from ..config.providers import ProviderType
from .console import ChatConsole
from .persistence import SessionManager
from .prompts import PromptsManager
from .session import ChatSession

class CommandHandler:
    """Handles chat commands and orchestrates components"""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None,  debug: bool = False):
        """Initialize command handler"""
        self.console = ChatConsole()
        self.session_manager = SessionManager()
        self.config_manager = ConfigManager()
        self.prompts_manager = PromptsManager()
        self.override_provider = provider
        self.override_model = model
        self.debug = debug

    def handle_command(self, cmd: str) -> bool:
        """
        Handle chat commands

        Args:
            cmd: Command string (without leading slash)

        Returns:
            bool: True if should continue chat, False if should exit
        """
        cmd = cmd.lower().strip()

        # Basic commands
        if cmd in ["quit", "q"]:
            return self._handle_quit()
        elif cmd in ["help", "h"]:
            return self._handle_help()
        elif cmd in ["clear", "c"]:
            return self._handle_clear()

        # Session management
        elif cmd == "save":
            return self._handle_save()
        elif cmd == "load":
            return self._handle_load()
        elif cmd == "new":
            return self._handle_new()
        elif cmd == "list":
            return self._handle_list()
        elif cmd == "delete":
            return self._handle_delete()
        elif cmd == "rename":
            return self._handle_rename()

        # Configuration
        elif cmd == "model":
            return self._handle_model()
        elif cmd == "system":
            return self._handle_system()
        elif cmd == "usage":
            return self._handle_usage()
        else:
            self.console.display_error(f"Unknown command: {cmd}")
            return True

    def _handle_quit(self) -> bool:
        """Handle quit command"""
        try:
            if self.session_manager.active_session:
                if self.console.confirm_action("Save session before quitting?"):
                    self._handle_save()

                # Clear the active session before quitting
                self.session_manager.active_session = None

            return False
        except Exception as e:
            self.console.display_error(f"Error during quit: {str(e)}")
            # Force quit even if there's an error
            return False

    def _handle_help(self) -> bool:
        """Handle help command"""
        self.console.display_welcome()
        return True

    def _handle_clear(self) -> bool:
        """Handle clear command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        if self.console.confirm_action("Clear chat history?"):
            self.session_manager.active_session.clear_history()
            self.console.display_success("Chat history cleared")
        return True

    def _handle_save(self) -> bool:
        """Handle save command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session to save")
            return True

        session = self.session_manager.active_session

        # Get session name if not set
        if session.name == "New Chat":
            new_name = self.console.get_session_name()
            if new_name:
                session.name = new_name

        if self.session_manager.save_session(session):
            self.console.display_success(f"Session '{session.name}' saved successfully")
        else:
            self.console.display_error("Failed to save session")

        return True

    def _handle_load(self) -> bool:
        """Handle load command"""
        sessions = self.session_manager.get_session_list()

        # Save current session if exists
        if self.session_manager.active_session:
            if self.console.confirm_action("Save current session before loading?"):
                self._handle_save()

        session_id = self.console.select_session(sessions)
        if not session_id:
            return True

        session = self.session_manager.load_session(session_id)
        if session:
            self.console.display_success(f"Loaded session: {session.name}")

            # Display recent messages
            recent_messages = (
                session.messages[-5:] if len(session.messages) > 5 else session.messages
            )
            for msg in recent_messages:
                if msg.role != "system":  # Don't show system messages
                    self.console.display_message(msg.role, msg.content)
        else:
            self.console.display_error("Failed to load session")

        # Display provider info for loaded session
        provider_name, model_name = self.get_provider_display_info(session)
        self.console.display_provider_info(provider_name, model_name)

        return True

    def _handle_new(self) -> bool:
        """Handle new session command"""
        if self.session_manager.active_session:
            if self.console.confirm_action("Save current session before creating new?"):
                self._handle_save()

        name = self.console.get_session_name()
        session = self.session_manager.create_session(name)

        # Set default system prompt
        default_prompt = self.prompts_manager.get_prompt("default")
        session.set_system_prompt(default_prompt)

        self.console.display_success(f"Created new session: {session.name}")
        return True

    def _handle_list(self) -> bool:
        """Handle list command"""
        sessions = self.session_manager.get_session_list()
        self.console.display_sessions(sessions)
        return True

    def _handle_delete(self) -> bool:
        """Handle delete command"""
        sessions = self.session_manager.get_session_list()
        session_id = self.console.select_session(sessions)

        if not session_id:
            return True

        if self.console.confirm_action("Are you sure you want to delete this session?"):
            if self.session_manager.delete_session(session_id):
                self.console.display_success("Session deleted successfully")
            else:
                self.console.display_error("Failed to delete session")

        return True

    def _handle_rename(self) -> bool:
        """Handle rename command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session to rename")
            return True

        session = self.session_manager.active_session
        new_name = self.console.get_session_name(session.name)

        if new_name and new_name != session.name:
            session.name = new_name
            if self.session_manager.save_session(session):
                self.console.display_success(f"Session renamed to: {new_name}")
            else:
                self.console.display_error("Failed to save session with new name")

        return True

    def _handle_model(self) -> bool:
        """Handle model command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        # Display current model
        session = self.session_manager.active_session
        self.console.display_info(f"\nCurrent model: {session.model}")

        # Display available providers
        providers = self.config_manager.get_configured_providers()
        self.console.display_info("\nConfigured providers:")
        for provider, config in providers.items():
            provider_name = self.config_manager.get_provider_display_name(
                provider, config
            )
            self.console.display_info(f"  • {provider_name}: {config['default_model']}")

        # Get provider selection
        provider_input = Prompt.ask(
            "\nEnter provider name (or press Enter to keep current)"
        )
        if provider_input:
            model_input = Prompt.ask("Enter model name")
            session.set_model(model_input, provider_input)
            self.console.display_success(
                f"Switched to {provider_input} with model {model_input}"
            )
        else:
            model_input = Prompt.ask("Enter model name")
            session.set_model(model_input)
            self.console.display_success(f"Switched to model: {model_input}")

        return True

    def _handle_system(self) -> bool:
        """Handle system command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session

        # Display current prompt
        current_prompt = session.get_system_prompt()
        self.console.display_info("\nCurrent system prompt:")
        self.console.display_info(f"[dim]{current_prompt}[/dim]")

        # Show options
        self.console.display_info("\nOptions:", style="bold")
        self.console.display_info("1. Use saved prompt")
        self.console.display_info("2. Create new prompt")
        self.console.display_info("3. Save current prompt")
        self.console.display_info("4. Delete saved prompt")
        self.console.display_info("5. Cancel")

        choice = Prompt.ask(
            "Select option", choices=["1", "2", "3", "4", "5"], default="5"
        )

        if choice == "1":
            # Show saved prompts
            prompts = self.prompts_manager.list_prompts()
            table = Table(title="Saved System Prompts")
            table.add_column("Name", style="cyan")
            table.add_column("Preview", style="dim")

            for name, prompt in prompts.items():
                preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
                table.add_row(name, preview)

            self.console.display_info(table)

            # Select prompt
            name = Prompt.ask("Enter prompt name", default="default")
            if name in prompts:
                session.set_system_prompt(prompts[name])
                self.console.display_success(f"System prompt set to '{name}'")
            else:
                self.console.display_error("Prompt not found")

        elif choice == "2":
            # Create new prompt
            new_prompt = Prompt.ask("Enter new system prompt")
            save = Prompt.ask(
                "Save this prompt? (y/n)", choices=["y", "n"], default="n"
            )

            if save.lower() == "y":
                name = Prompt.ask("Enter name for this prompt")
                self.prompts_manager.save_prompt(name, new_prompt)
                self.console.display_success(f"Prompt saved as '{name}'")

            session.set_system_prompt(new_prompt)
            self.console.display_success("System prompt updated")

        elif choice == "3":
            # Save current prompt
            if not current_prompt:
                self.console.display_error("No current prompt to save")
                return True

            name = Prompt.ask("Enter name for this prompt")
            self.prompts_manager.save_prompt(name, current_prompt)
            self.console.display_success(f"Current prompt saved as '{name}'")

        elif choice == "4":
            # Delete saved prompt
            prompts = self.prompts_manager.list_prompts()
            table = Table(title="Saved System Prompts")
            table.add_column("Name", style="cyan")
            table.add_column("Preview", style="dim")

            for name, prompt in prompts.items():
                preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
                table.add_row(name, preview)

            self.console.print(table)

            name = Prompt.ask("Enter prompt name to delete")
            if self.prompts_manager.delete_prompt(name):
                self.console.display_success(f"Prompt '{name}' deleted")
            else:
                self.console.display_error(
                    "Cannot delete prompt (not found or is default)"
                )

        return True

    def _handle_usage(self) -> bool:
        """Handle usage command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        self.console.display_token_usage(
            f"Token Usage - {session.name}", session.total_usage.to_dict()
        )
        return True

    def get_provider_display_info(self, session: ChatSession) -> tuple[str, str]:
        """Get display-friendly provider name and model"""
        if session.provider == ProviderType.OTHER and session.custom_provider:
            return session.custom_provider, session.model

        provider_config = self.config_manager.get_configured_providers().get(
            session.provider, {}
        )
        provider_name = self.config_manager.get_provider_display_name(
            session.provider, provider_config
        )
        return provider_name, session.model

    def start_session(self):
        """Start new chat session"""
        # Check for configured providers
        if not self.config_manager.get_configured_providers():
            self.console.display_error(
                "No providers configured. Please run 'looplm --configure' first."
            )
            return

        # Show welcome message
        self.console.display_welcome()

        # Create initial session
        if not self.session_manager.active_session:
            # session = self.session_manager.create_session()
            session = self._create_new_session()

            # Connect session to console for clipboard access
            self.console.set_current_session(session)
            
            # Set default system prompt
            default_prompt = self.prompts_manager.get_prompt("default")
            session.set_system_prompt(default_prompt)
        # Main chat loop
        while True:
            try:
                user_input = self.console.prompt_user()

                # Handle commands
                if user_input.startswith("/"):
                    cmd = user_input[1:]  # Remove leading slash
                    if not self.handle_command(cmd):
                        break
                    continue

                # Handle normal message
                if not self.session_manager.active_session:
                    self.console.display_error("No active session")
                    continue

                try:
                    # Try to process the message
                    self.session_manager.active_session.send_message(
                        user_input, stream=True, show_tokens=False, debug=self.debug
                    )
                except Exception as e:
                    # Handle other errors
                    self.console.display_error(str(e))

            except KeyboardInterrupt:
                self.console.display_info("\nUse /quit to exit")
                continue

            except Exception as e:
                self.console.display_error(str(e))

    def _create_new_session(self) -> ChatSession:
        """Create a new session with provider/model overrides if specified"""
        session = self.session_manager.create_session()

        if self.override_provider:
            try:
                # Handle both standard and custom providers
                try:
                    provider_type = ProviderType(self.override_provider)
                except ValueError:
                    # Check if this is a custom provider
                    providers = self.config_manager.get_configured_providers()
                    other_config = providers.get(ProviderType.OTHER, {})
                    if (
                        other_config
                        and other_config.get("provider_name") == self.override_provider
                    ):
                        provider_type = ProviderType.OTHER
                        custom_provider = self.override_provider
                    else:
                        raise ValueError(f"Invalid provider: {self.override_provider}")

                # Get provider configuration
                provider_config = self._get_provider_config(provider_type)

                # Set model (either override or provider default)
                model = self.override_model or provider_config["default_model"]

                # Update session
                session.provider = provider_type
                session.model = model
                if provider_type == ProviderType.OTHER:
                    session.custom_provider = custom_provider

                provider_name, model_name = self.get_provider_display_info(session)
                self.console.display_provider_info(provider_name, model_name)

            except Exception as e:
                self.console.display_error(f"Error setting provider: {str(e)}")
                # Fall back to defaults
                provider, model, custom_provider = session._get_provider_and_model()
                session.provider = provider
                session.model = model
                session.custom_provider = custom_provider

                provider_name, model_name = self.get_provider_display_info(session)
                self.console.display_provider_info(provider_name, model_name)
        elif self.override_model:
            provider, _, custom_provider = session._get_provider_and_model()
            session.provider = provider
            session.model = self.override_model
            session.custom_provider = custom_provider

            provider_name, model_name = self.get_provider_display_info(session)
            self.console.display_provider_info(provider_name, model_name)

        else:
            # Display default provider info
            provider_name, model_name = self.get_provider_display_info(session)
            self.console.display_provider_info(provider_name, model_name)

        return session

    def _get_provider_config(self, provider: ProviderType) -> dict:
        """Get provider configuration"""
        providers = self.config_manager.get_configured_providers()
        if provider not in providers:
            raise ValueError(f"Provider {provider.value} is not configured")
        return providers[provider]
