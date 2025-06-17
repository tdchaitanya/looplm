# src/looplm/conversation/handler.py
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from litellm import completion
from litellm.utils import trim_messages
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from ..commands import CommandManager
from ..config.manager import ConfigManager
from ..config.providers import ProviderType
from ..tools import ToolManager


class ConversationHandler:
    """Handles conversation interactions with LLM providers"""

    def __init__(self, console: Optional[Console] = None, debug: bool = False):
        """Initialize conversation handler"""
        if console is None:
            self.console = Console(
                force_terminal=True, force_interactive=True, width=None
            )
        else:
            self.console = console
            self.console.width = None
        self.config_manager = ConfigManager()
        # Use command manager instead of file preprocessor
        self.command_manager = CommandManager(base_path=Path.cwd())
        self.debug = debug

        # Initialize tool manager (disabled by default)
        self.tool_manager = None

    def enable_tools(
        self, tool_names: Optional[List[str]] = None, require_approval: bool = False
    ) -> None:
        """Enable tool calling functionality.

        Args:
            tool_names: List of specific tools to enable (None = all available)
            require_approval: Whether to require human approval for tool execution
        """
        self.tool_manager = ToolManager(
            console=self.console, require_approval=require_approval
        )

        if tool_names:
            loaded = self.tool_manager.load_tools_from_names(tool_names)
            if loaded:
                self.console.print(
                    f"🔧 Enabled tools: {', '.join(loaded)}", style="blue"
                )
        else:
            # Load all available tools
            available = self.tool_manager.registry.list_tools()
            if available:
                self.console.print(
                    f"🔧 Enabled {len(available)} tools: {', '.join(available)}",
                    style="blue",
                )

    def disable_tools(self) -> None:
        """Disable tool calling functionality."""
        self.tool_manager = None
        self.console.print("🔧 Tools disabled", style="dim")

    def list_available_tools(self) -> None:
        """Display available tools."""
        if not self.tool_manager:
            self.console.print("Tools are not enabled", style="yellow")
            return

        self.tool_manager.display_available_tools()

    def _get_provider_config(self, provider: ProviderType) -> dict:
        """Get full provider configuration including custom name if it's OTHER type"""
        providers = self.config_manager.get_configured_providers()
        if provider not in providers:
            raise ValueError(f"Provider {provider.value} is not configured")
        return providers[provider]

    def _setup_environment(self, provider: ProviderType) -> None:
        """Set up environment variables for the specified provider"""
        credentials = self.config_manager.get_provider_credentials(provider)
        for key, value in credentials.items():
            os.environ[key] = value

    def _get_provider_and_model(
        self, provider_name: Optional[str] = None, model_name: Optional[str] = None
    ) -> Tuple[ProviderType, str, Optional[str]]:
        """Get provider and model to use"""
        if provider_name:
            try:
                # Try to get the provider as an enum
                provider = ProviderType(provider_name)
            except ValueError:
                # Check if this is a custom provider name
                providers = self.config_manager.get_configured_providers()
                found = False
                for p_type, p_config in providers.items():
                    if (
                        p_type == ProviderType.OTHER
                        and p_config.get("provider_name") == provider_name
                    ):
                        provider = ProviderType.OTHER
                        found = True
                        break

                if not found:
                    # If not found in OTHER providers, check if it matches any provider name more flexibly
                    # This handles cases like 'groq' not being an exact enum match but a configured provider
                    for provider_type, config in providers.items():
                        provider_display = (
                            self.config_manager.get_provider_display_name(
                                provider_type, config
                            ).lower()
                        )
                        if provider_name.lower() == provider_display:
                            provider = provider_type
                            found = True
                            break

                    if not found:
                        raise ValueError(f"Invalid provider: {provider_name}")

            # Now get the provider configuration
            provider_config = self._get_provider_config(provider)

            # If model is specified, use it
            if model_name:
                actual_name = (
                    provider_config.get("provider_name")
                    if provider == ProviderType.OTHER
                    else None
                )
                return provider, model_name, actual_name

            # Otherwise use default model
            default_model = provider_config.get("default_model")
            if not default_model:
                # Fallback to first model in the list if default isn't set
                models = self.config_manager.get_provider_models(provider)
                if models:
                    default_model = models[0]
                else:
                    raise ValueError(
                        f"No models configured for provider {provider_name}"
                    )

            actual_name = (
                provider_config.get("provider_name")
                if provider == ProviderType.OTHER
                else None
            )
            return provider, default_model, actual_name

        # No provider specified, use default
        provider, default_model = self.config_manager.get_default_provider()
        if not provider or not default_model:
            raise ValueError(
                "No default provider configured. Run 'looplm --configure' first."
            )

        provider_config = self._get_provider_config(provider)

        # If model is specified, use it with the default provider
        if model_name:
            actual_name = (
                provider_config.get("provider_name")
                if provider == ProviderType.OTHER
                else None
            )
            return provider, model_name, actual_name

        # Otherwise use default provider and model
        actual_name = (
            provider_config.get("provider_name")
            if provider == ProviderType.OTHER
            else None
        )
        return provider, default_model, actual_name

    def _stream_markdown(self, content: str, live: Live) -> None:
        """Update live display with markdown-formatted content"""
        try:
            markdown = Markdown(content, code_theme="monokai")
            # panel = Panel(
            #     markdown,
            #     style=Style(bgcolor="rgb(40,44,52)"),
            #     border_style="dim white",
            #     padding=(1, 2),
            #     expand=True,
            # )
            live.update(markdown, refresh=True)
        except Exception:
            text = Text(content)
            # panel = Panel(
            #     text,
            #     style=Style(bgcolor="rgb(40,44,52)"),
            #     border_style="dim white",
            #     padding=(1, 2),
            #     expand=True,
            # )

            live.update(text)

    def handle_prompt(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        use_progress_streaming: bool = True,
    ) -> None:
        """
        Handle a user prompt and stream the response.

        The prompt may contain commands (@file, @folder, @github, @image) which will be processed before sending
        to the LLM provider. If tools are enabled, the LLM may also call tools.

        Args:
            prompt: User prompt, possibly containing commands
            provider: Optional provider override
            model: Optional model override
        """
        try:
            # Process the prompt using the command manager
            processed_content, media_metadata = self.command_manager.process_text_sync(
                prompt
            )

            if self.debug:
                # In debug mode, just display the processed content
                self.console.print("\nProcessed Content:", style="bold blue")
                self.console.print(processed_content)
                if media_metadata:
                    self.console.print("\nMedia Metadata:", style="bold magenta")
                    for media in media_metadata:
                        self.console.print(media)
                return  # Exit early in debug mode

            provider_type, model_name, custom_provider = self._get_provider_and_model(
                provider, model
            )

            self._setup_environment(provider_type)

            # Prepare actual model name
            if provider_type == ProviderType.OTHER and custom_provider:
                # For custom providers
                if not model_name.startswith(f"{custom_provider}/"):
                    actual_model = f"{custom_provider}/{model_name}"
                else:
                    actual_model = model_name
            else:
                # For standard providers
                provider_prefix = f"{provider_type.value}/"
                if model_name.startswith(provider_prefix):
                    # Model already has the provider prefix, use as is
                    actual_model = model_name
                else:
                    # Only add prefix for certain providers that need it
                    if provider_type in [
                        ProviderType.GEMINI,
                        ProviderType.BEDROCK,
                        ProviderType.AZURE,
                    ]:
                        actual_model = f"{provider_type.value}/{model_name}"
                    else:
                        # For most providers like OpenAI, Anthropic, Groq, etc. don't add prefix
                        actual_model = model_name

            # Check if the model supports vision, PDF input, and function calling
            try:
                import litellm
                from litellm.utils import supports_pdf_input

                model_supports_vision = litellm.supports_vision(model=actual_model)
                model_supports_pdf = supports_pdf_input(model=actual_model)
                model_supports_tools = litellm.supports_function_calling(
                    model=actual_model
                )
            except Exception:
                # If we can't import litellm or check, assume model doesn't support these features
                model_supports_vision = False
                model_supports_pdf = False
                model_supports_tools = False
                self.console.print(
                    f"\nWarning: Unable to verify model capabilities for {actual_model}. Proceeding with basic functionality.",
                    style="bold yellow",
                )

            # Check tool compatibility
            if self.tool_manager and not model_supports_tools:
                self.console.print(
                    f"\n⚠️ Warning: Model {actual_model} does not support function calling. Tools will be disabled for this request.",
                    style="yellow",
                )

            # Separate media by type
            images = []
            pdfs = []
            if media_metadata:
                for media in media_metadata:
                    if media.get("type") == "image_url":
                        images.append(media)
                    elif media.get("type") == "file_url":
                        pdfs.append(media)

            # Create messages based on what media we have and what the model supports
            content_list = [{"type": "text", "text": processed_content}]

            # Handle images
            if images and model_supports_vision:
                content_list.extend(images)
            elif images and not model_supports_vision:
                self.console.print(
                    f"\nWarning: Model {actual_model} does not support vision input. Images will be ignored.",
                    style="bold yellow",
                )

            # Handle PDFs
            if pdfs and model_supports_pdf:
                content_list.extend([pdf["file_data"] for pdf in pdfs])
            elif pdfs and not model_supports_pdf:
                self.console.print(
                    f"\nWarning: Model {actual_model} does not support PDF input. PDFs will be ignored.",
                    style="bold yellow",
                )

            # Create the final message
            if len(content_list) > 1:
                # We have media content
                messages = [{"role": "user", "content": content_list}]
            else:
                # Standard text message only
                messages = [{"role": "user", "content": processed_content}]

            # Get tool schemas if tools are enabled and supported
            tools = None
            if self.tool_manager and model_supports_tools:
                tool_schemas = self.tool_manager.get_tool_schemas()
                if tool_schemas:
                    tools = tool_schemas

            # Call the LLM with enhanced handling for tools
            self._handle_llm_interaction(actual_model, messages, tools, model_name)

        except Exception as e:
            self.console.print(f"Error: {str(e)}", style="bold red")
            raise

    def _handle_llm_interaction(
        self,
        model: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        display_model_name: str = None,
    ) -> None:
        """Handle the LLM interaction with potential tool calls."""
        display_name = display_model_name or model

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            # Fun, dynamic messages to improve UX
            import random

            creative_messages = [
                # Thoughtful/Contemplative
                f"🤔 Pondering with {display_name}...",
                f"🧠 Deep thinking via {display_name}...",
                f"💭 Brewing thoughts using {display_name}...",
                f"🎯 Crafting response with {display_name}...",
                f"🔍 Exploring possibilities with {display_name}...",
                # Magical/Mystical
                f"🔮 Consulting the AI oracle {display_name}...",
                f"✨ Weaving digital magic via {display_name}...",
                f"🪄 Conjuring wisdom through {display_name}...",
                f"🌟 Channeling cosmic knowledge from {display_name}...",
                # Creative/Artistic
                f"🎨 Painting words via {display_name}...",
                f"🎭 Performing linguistic theatre with {display_name}...",
                f"🎼 Composing a response using {display_name}...",
                f"📝 Scribing wisdom through {display_name}...",
                # Tech/Action
                f"⚡ Sparking neural networks in {display_name}...",
                f"🚀 Launching query to {display_name}...",
                f"⚙️ Processing magic through {display_name}...",
                f"🔥 Igniting synapses in {display_name}...",
                # Playful/Fun
                f"🤖 Having a chat with {display_name}...",
                f"🎪 Putting on a thinking show via {display_name}...",
                f"🎲 Rolling the dice of wisdom with {display_name}...",
                f"🎈 Floating ideas through {display_name}...",
            ]

            task_description = random.choice(creative_messages)
            task = progress.add_task(task_description, total=None)

            # Make the initial API call
            call_kwargs = {
                "model": model,
                "messages": trim_messages(messages),
                "stream": True,
            }

            if tools:
                call_kwargs["tools"] = tools
                call_kwargs["tool_choice"] = "auto"

            response = completion(**call_kwargs)
            accumulated_text = ""
            tool_calls = []

            for chunk in response:
                delta = chunk.choices[0].delta

                # Handle text content
                if delta.content:
                    accumulated_text += delta.content

                # Handle tool calls
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        # Extend tool_calls list if needed
                        while len(tool_calls) <= tool_call.index:
                            tool_calls.append(
                                {
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )

                        # Update the tool call
                        if tool_call.id:
                            tool_calls[tool_call.index]["id"] = tool_call.id
                        if tool_call.function.name:
                            tool_calls[tool_call.index]["function"][
                                "name"
                            ] = tool_call.function.name
                        if tool_call.function.arguments:
                            tool_calls[tool_call.index]["function"][
                                "arguments"
                            ] += tool_call.function.arguments

        # Display the text response if any
        if accumulated_text.strip():
            try:
                markdown = Markdown(accumulated_text, code_theme="monokai")
                self.console.print(markdown)
            except Exception:
                self.console.print(accumulated_text)

        # Handle tool calls if any
        if tool_calls and self.tool_manager:
            self._handle_tool_calls(
                model, messages, tool_calls, tools, accumulated_text
            )

    def _handle_tool_calls(
        self,
        model: str,
        original_messages: List[Dict],
        tool_calls: List[Dict],
        tools: List[Dict],
        assistant_message: str,
    ) -> None:
        """Handle tool calls and get the final response."""
        # Add the assistant's message with tool calls to the conversation
        assistant_msg = {
            "role": "assistant",
            "content": assistant_message or None,
            "tool_calls": tool_calls,
        }
        messages = original_messages + [assistant_msg]

        # Execute each tool call
        for tool_call in tool_calls:
            if tool_call.get("function"):
                tool_call_id = tool_call["id"]
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]

                # Execute the tool
                _, result = self.tool_manager.execute_tool_call(
                    tool_call_id, function_name, arguments
                )

                # Add tool result to messages (following LiteLLM format)
                messages.append(
                    {
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": function_name,
                        "content": result,
                    }
                )

        # Get the final response from the model
        self.console.print("\n" + "─" * 50)
        self.console.print(
            "🤖 Getting final response from assistant...", style="dim blue"
        )

        final_response = completion(
            model=model, messages=trim_messages(messages), stream=True
        )

        final_text = ""
        for chunk in final_response:
            content = chunk.choices[0].delta.content or ""
            final_text += content

        # Display the final response
        if final_text.strip():
            try:
                markdown = Markdown(final_text, code_theme="monokai")
                self.console.print(markdown)
            except Exception:
                self.console.print(final_text)
