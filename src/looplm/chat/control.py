# src/looplm/chat/commands.py

from typing import Optional

from rich.prompt import Prompt
from rich.table import Table

from ..config.manager import ConfigManager
from ..config.providers import ProviderType
from ..utils.prompts import PromptsManager
from .compact_handler import CompactHandler
from .console import ChatConsole
from .persistence import SessionManager
from .session import ChatSession


class CommandHandler:
    """Handles chat commands and orchestrates components"""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        debug: bool = False,
        tools: Optional[str] = None,
        tools_approval: bool = False,
    ):
        """Initialize command handler"""
        self.console = ChatConsole()
        self.session_manager = SessionManager()
        self.config_manager = ConfigManager()
        self.prompts_manager = PromptsManager()
        self.compact_handler = CompactHandler(self.console, self.prompts_manager)
        self.override_provider = provider
        self.override_model = model
        self.debug = debug
        self.tools_config = tools
        self.tools_approval = tools_approval

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
        elif cmd.startswith("clear-last"):
            parts = cmd.split(" ", 1)
            count_param = parts[1] if len(parts) > 1 else "1"
            return self._handle_clear_last(count_param)

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
        elif cmd == "compact":
            return self._handle_compact()
        elif cmd == "compact-info":
            return self._handle_compact_info()
        elif cmd == "compact-reset":
            return self._handle_compact_reset()

        # Tool commands
        elif cmd == "tools":
            return self._handle_tools()
        elif cmd == "tools-list":
            return self._handle_tools_list()
        elif cmd.startswith("tools-enable"):
            parts = cmd.split(" ", 1)
            tool_names = parts[1] if len(parts) > 1 else "all"
            return self._handle_tools_enable(tool_names)
        elif cmd == "tools-disable":
            return self._handle_tools_disable()
        elif cmd == "tools-approval":
            return self._handle_tools_approval()
        elif cmd.startswith("tools-create"):
            parts = cmd.split(" ", 1)
            args = parts[1] if len(parts) > 1 else ""
            return self._handle_tools_create(args)
        elif cmd == "tools-dir":
            return self._handle_tools_dir()
        elif cmd == "tools-reload":
            return self._handle_tools_reload()
        else:
            self.console.display_error(f"Unknown command: {cmd}")
            return True

    def _handle_clear_last(self, count: str = "1") -> bool:
        """Handle clear-last command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        try:
            num_to_clear = int(count) if count.isdigit() else 1
        except ValueError:
            self.console.display_error("Invalid number format")
            return True

        session = self.session_manager.active_session

        # Check if there are messages to clear
        non_system_count = len(
            [msg for msg in session.messages if msg.role != "system"]
        )
        if non_system_count == 0:
            self.console.display_error("No messages to clear")
            return True

        # Confirm action
        actual_count = min(num_to_clear, non_system_count)
        if actual_count == 1:
            if not self.console.confirm_action("Clear the last message?"):
                return True
        else:
            if not self.console.confirm_action(
                f"Clear the last {actual_count} messages?"
            ):
                return True

        # Clear messages - preserve cost by default
        cleared_count = session.clear_last_messages(actual_count, preserve_cost=True)

        if cleared_count == 1:
            self.console.display_success("Last message cleared")
        else:
            self.console.display_success(f"Last {cleared_count} messages cleared")

        return True

    def _handle_quit(self) -> bool:
        """Handle quit command"""
        try:
            if self.session_manager.active_session:
                session = self.session_manager.active_session
                if session.total_usage.total_tokens > 0:
                    self.console.display_token_usage(
                        f"Session Summary - {session.name}",
                        session.total_usage.to_dict(),
                        show_automatically=True,
                    )

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
            models = config.get("models", [config.get("default_model")])
            default_model = config.get("default_model")

            self.console.display_info(f"  • {provider_name}:")
            for model in models:
                is_default = model == default_model
                self.console.display_info(
                    f"      - {model}" + (" (default)" if is_default else "")
                )

        # Get provider selection
        provider_input = Prompt.ask(
            "\nEnter provider name (or press Enter to keep current)"
        )

        if provider_input:
            # If provider selected, show its models
            try:
                # Try to find the provider
                selected_provider = None

                # Try to get provider as ProviderType directly
                try:
                    selected_provider = ProviderType(provider_input)
                    if selected_provider not in providers:
                        selected_provider = None
                except ValueError:
                    # Not a direct enum match
                    pass

                # Check if it's a custom provider
                if selected_provider is None:
                    for p, config in providers.items():
                        if (
                            p == ProviderType.OTHER
                            and config.get("provider_name") == provider_input
                        ):
                            selected_provider = p
                            break

                # Check if it matches any provider display name
                if selected_provider is None:
                    for p, config in providers.items():
                        display_name = self.config_manager.get_provider_display_name(
                            p, config
                        ).lower()
                        if provider_input.lower() == display_name:
                            selected_provider = p
                            break

                if selected_provider is None:
                    self.console.display_error(f"Provider {provider_input} not found")
                    return True

                # Get models for selected provider
                provider_config = providers[selected_provider]
                models = provider_config.get(
                    "models", [provider_config.get("default_model")]
                )

                if models:
                    self.console.display_info(
                        f"\nAvailable models for {provider_input}:"
                    )
                    for i, model in enumerate(models, 1):
                        self.console.display_info(f"  {i}. {model}")

                    model_choice = Prompt.ask("Enter model number or name", default="1")

                    # Convert choice to model name if it's a number
                    model_input = None
                    try:
                        choice_idx = int(model_choice) - 1
                        if 0 <= choice_idx < len(models):
                            model_input = models[choice_idx]
                        else:
                            model_input = model_choice
                    except ValueError:
                        model_input = model_choice
                else:
                    model_input = Prompt.ask("Enter model name")

                # Use the display name for better UX
                display_name = self.config_manager.get_provider_display_name(
                    selected_provider, provider_config
                )
                session.set_model(model_input, selected_provider.value)
                self.console.display_success(
                    f"Switched to {display_name} with model {model_input}"
                )
            except Exception as e:
                self.console.display_error(f"Error selecting provider: {str(e)}")
                return True
        else:
            # Just changing the model for current provider
            current_provider = session.provider
            provider_config = providers.get(current_provider, {})
            models = provider_config.get(
                "models", [provider_config.get("default_model")]
            )

            if models:
                self.console.display_info("\nAvailable models for current provider:")
                for i, model in enumerate(models, 1):
                    self.console.display_info(f"  {i}. {model}")

                model_choice = Prompt.ask("Enter model number or name", default="1")

                # Convert choice to model name if it's a number
                model_input = None
                try:
                    choice_idx = int(model_choice) - 1
                    if 0 <= choice_idx < len(models):
                        model_input = models[choice_idx]
                    else:
                        model_input = model_choice
                except ValueError:
                    model_input = model_choice
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
            # Create new prompt using multi-line input
            new_prompt = self._get_multiline_input()
            if new_prompt:  # Only proceed if we got input
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

    def _handle_compact(self) -> bool:
        """Handle /compact command by summarizing conversation so far using LLM."""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        self.compact_handler.compact_session(session)
        return True

    def _handle_compact_info(self) -> bool:
        """Handle /compact-info command to show compact status and statistics."""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        self.compact_handler.show_compact_info(session)
        return True

    def _handle_compact_reset(self) -> bool:
        """Handle /compact-reset command to reset compact state."""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        self.compact_handler.reset_compact(session)
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

    def _get_multiline_input(self, current_text: str = "") -> str:
        """Get multi-line input from user with instructions

        Args:
            current_text: Optional existing text to pre-fill

        Returns:
            str: Complete multi-line input
        """
        self.console.display_info(
            "\nEnter your prompt. Type ':done' on a new line to finish."
        )
        self.console.display_info("To cancel, type ':cancel' or use Ctrl+C")

        lines = []
        if current_text:
            lines.extend(current_text.split("\n"))
            for line in lines:
                self.console.display_info(line)

        while True:
            try:
                line = Prompt.ask("", default="")
                # Check for termination commands
                if line.strip().lower() == ":done":
                    break
                if line.strip().lower() == ":cancel":
                    return ""
                lines.append(line)
            except KeyboardInterrupt:
                self.console.display_info("\nCancelled input.")
                return ""

        return "\n".join(lines)

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

        # Enable tools if specified in initialization
        if self.tools_config:
            if self.tools_config.lower() == "all":
                session.enable_tools(require_approval=self.tools_approval)
            else:
                tool_list = [name.strip() for name in self.tools_config.split(",")]
                session.enable_tools(
                    tool_names=tool_list, require_approval=self.tools_approval
                )

        return session

    def _get_provider_config(self, provider: ProviderType) -> dict:
        """Get provider configuration"""
        providers = self.config_manager.get_configured_providers()
        if provider not in providers:
            raise ValueError(f"Provider {provider.value} is not configured")
        return providers[provider]

    def _handle_tools(self) -> bool:
        """Handle /tools command to show tool status"""
        self.console.display_info("\n🔧 Tool Commands:")
        commands = [
            ("/tools-list", "List available tools"),
            ("/tools-enable [tool1,tool2]", "Enable tools (all if no names given)"),
            ("/tools-disable", "Disable all tools"),
            ("/tools-approval", "Toggle approval mode for tool execution"),
            ("/tools-create <name>", "Create a new custom tool template"),
            ("/tools-dir", "Show user tools directory path"),
            ("/tools-reload", "Reload tools from directories"),
        ]

        for cmd, desc in commands:
            self.console.console.print(f"  {cmd:<25} - {desc}", style="dim")

        return True

    def _handle_tools_create(self, args: str) -> bool:
        """Handle /tools-create command to create a new custom tool"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        if not args.strip():
            self.console.display_error("Usage: /tools-create <tool_name> [description]")
            return True

        parts = args.strip().split(maxsplit=1)
        tool_name = parts[0]
        description = parts[1] if len(parts) > 1 else f"Custom tool: {tool_name}"

        # Validate tool name
        if not tool_name.isidentifier():
            self.console.display_error("Tool name must be a valid Python identifier")
            return True

        session = self.session_manager.active_session
        if not session.tool_manager:
            self.console.display_error(
                "Tools are not enabled. Use /tools-enable first."
            )
            return True

        success = session.tool_manager.create_sample_tool(tool_name, description)
        if success:
            self.console.display_info(
                "Use /tools-reload to load the new tool after editing it."
            )

        return True

    def _handle_tools_dir(self) -> bool:
        """Handle /tools-dir command to show user tools directory"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        if not session.tool_manager:
            self.console.display_error("Tools are not enabled")
            return True

        tools_dir = session.tool_manager.get_user_tools_directory_path()
        self.console.display_info(f"User tools directory: {tools_dir}")
        self.console.console.print(
            "Place your custom .py files with @tool decorated functions in this directory.",
            style="dim",
        )
        return True

    def _handle_tools_reload(self) -> bool:
        """Handle /tools-reload command to reload tools from directories"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        if not session.tool_manager:
            self.console.display_error("Tools are not enabled")
            return True

        # Clear existing tools and reload
        session.tool_manager.registry.clear()
        builtin_count = len(session.tool_manager.discover_default_tools())
        user_count = len(session.tool_manager.discover_user_tools())

        total = builtin_count + user_count
        self.console.display_info(
            f"🔄 Reloaded {total} tools ({builtin_count} built-in, {user_count} user-defined)"
        )
        return True

    def _handle_tools_list(self) -> bool:
        """Handle /tools-list command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        available_tools = session.list_available_tools()
        enabled_tools = session.list_enabled_tools()

        if not available_tools:
            self.console.display_info(
                "No tools discovered. Tools are auto-discovered from src/looplm/tools/builtin/"
            )
        else:
            self.console.display_info(f"Available tools ({len(available_tools)}):")
            for tool_name in available_tools:
                status = "✅ enabled" if tool_name in enabled_tools else "⭕ available"
                self.console.console.print(f"  🔧 {tool_name} - {status}", style="cyan")

        return True

    def _handle_tools_enable(self, tool_names: str = "all") -> bool:
        """Handle /tools-enable command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session

        if tool_names == "all":
            session.enable_tools(require_approval=self.tools_approval)
        else:
            tool_list = [name.strip() for name in tool_names.split(",")]
            session.enable_tools(
                tool_names=tool_list, require_approval=self.tools_approval
            )

        return True

    def _handle_tools_disable(self) -> bool:
        """Handle /tools-disable command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        session.disable_tools()
        return True

    def _handle_tools_approval(self) -> bool:
        """Handle /tools-approval command"""
        if not self.session_manager.active_session:
            self.console.display_error("No active session")
            return True

        session = self.session_manager.active_session
        if session.tool_manager:
            current_mode = session.tool_manager.require_approval
            session.tool_manager.set_approval_mode(not current_mode)
            new_mode = "enabled" if not current_mode else "disabled"
            self.console.display_success(f"Tool approval mode {new_mode}")
        else:
            self.console.display_error("Tools are not enabled in this session")

        return True
