# src/looplm/conversation/handler.py
import os
from pathlib import Path
from typing import Optional, Tuple

from litellm import completion
from litellm.utils import trim_messages
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from ..config.manager import ConfigManager
from ..config.providers import ProviderType
from ..commands import CommandManager


class ConversationHandler:
    """Handles conversation interactions with LLM providers"""

    def __init__(self, console: Optional[Console] = None):
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
                    if p_type == ProviderType.OTHER and p_config.get("provider_name") == provider_name:
                        provider = ProviderType.OTHER
                        found = True
                        break
                
                if not found:
                    # If not found in OTHER providers, check if it matches any provider name more flexibly
                    # This handles cases like 'groq' not being an exact enum match but a configured provider
                    for provider_type, config in providers.items():
                        provider_display = self.config_manager.get_provider_display_name(provider_type, config).lower()
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
                    raise ValueError(f"No models configured for provider {provider_name}")
                
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
            markdown = Markdown(content, code_theme='monokai')
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
            self, prompt: str, provider: Optional[str] = None, model: Optional[str] = None
        ) -> None:
        """
        Handle a user prompt and stream the response.

        The prompt may contain commands (@file, @folder, @github, @image) which will be processed before sending
        to the LLM provider.

        Args:
            prompt: User prompt, possibly containing commands
            provider: Optional provider override
            model: Optional model override
        """
        try:
            # Process the prompt using the command manager
            processed_content, image_metadata = self.command_manager.process_text_sync(prompt)

            provider_type, model_name, custom_provider = self._get_provider_and_model(
                provider, model
            )

            self._setup_environment(provider_type)

            # Prepare actual model name
            # IMPORTANT FIX: Check if the model name already contains the provider prefix
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
                    if provider_type in [ProviderType.GEMINI, ProviderType.BEDROCK, ProviderType.AZURE]:
                        actual_model = f"{provider_type.value}/{model_name}"
                    else:
                        # For most providers like OpenAI, Anthropic, Groq, etc. don't add prefix
                        actual_model = model_name
            
            # Check if the model supports vision
            try:
                import litellm
                model_supports_vision = litellm.supports_vision(model=actual_model)
            except Exception:
                # If we can't import litellm or check, assume model doesn't support vision
                model_supports_vision = False
                self.console.print(
                    f"\nWarning: Unable to verify if model {actual_model} supports vision. Proceeding with text-only input.",
                    style="bold yellow"
                )

            # Create messages based on whether we have images
            if image_metadata and model_supports_vision:
                # Create content as an array with text and images
                content_list = [
                    {
                        "type": "text",
                        "text": processed_content
                    }
                ]
                
                # Add each image
                for img in image_metadata:
                    content_list.append(img)
                
                messages = [{"role": "user", "content": content_list}]
            elif image_metadata and not model_supports_vision:
                # Warn that the model doesn't support images
                self.console.print(
                    f"\nWarning: Model {actual_model} does not support vision input. Images will be ignored.",
                    style="bold yellow"
                )
                messages = [{"role": "user", "content": processed_content}]
            else:
                # Standard text message
                messages = [{"role": "user", "content": processed_content}]

            with Live(
                "", refresh_per_second=4, console=self.console, auto_refresh=True
            ) as live:
                live.console.width = None
                accumulated_text = ""

                response = completion(
                    model=actual_model, messages=trim_messages(messages), stream=True
                )

                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    accumulated_text += content
                    self._stream_markdown(accumulated_text, live)

        except Exception as e:
            self.console.print(f"Error: {str(e)}", style="bold red")
            raise