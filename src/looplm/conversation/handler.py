# src/looplm/conversation/handler.py
from typing import Optional, Tuple
import os
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from litellm import completion
from ..config.manager import ConfigManager
from ..config.providers import ProviderType


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

    def _get_provider_config(self, provider: ProviderType) -> dict:
        """Get full provider configuration including custom name if it's OTHER type"""
        providers = self.config_manager.get_configured_providers()
        if provider not in providers:
            raise ValueError(f"Provider {provider.value} is not configured")
        return providers[provider]

    def _setup_environment(self, provider: ProviderType) -> None:
        """Set up environment variables for the specified provide"""
        for key in list(os.environ.keys()):
            if any(
                key.startswith(p)
                for p in ["ANTHROPIC_", "OPENAI_", "AZURE_", "AWS_", "GEMINI_"]
            ):
                del os.environ[key]

        credentials = self.config_manager.get_provider_credentials(provider)
        for key, value in credentials.items():
            os.environ[key] = value

    def _get_provider_and_model(
        self, provider_name: Optional[str] = None, model_name: Optional[str] = None
    ) -> Tuple[ProviderType, str]:
        """Get provider and model to use"""
        if provider_name:
            try:
                provider = ProviderType(provider_name)
            except ValueError:
                raise ValueError(f"Invalid provider: {provider_name}")
            provider_config = self._get_provider_config(provider)
            if model_name:
                actual_name = (
                    provider_config.get("provider_name")
                    if provider == ProviderType.OTHER
                    else None
                )
                return provider, model_name, actual_name
            actual_name = (
                provider_config.get("provider_name")
                if provider == ProviderType.OTHER
                else None
            )
            return provider, provider_config["default_model"], actual_name

            # providers = self.config_manager.get_configured_providers()
            # if provider not in providers:
            #     raise ValueError(f"Provider {provider_name} is not configured")

            # if model_name:
            #     return provider, model_name
            # return provider, providers[provider]["default_model"]

        provider, default_model = self.config_manager.get_default_provider()
        if not provider or not default_model:
            raise ValueError(
                "No default provider configured. Run 'looplm --configure' first."
            )
        provider_config = self._get_provider_config(provider)
        if model_name:
            actual_name = (
                provider_config.get("provider_name")
                if provider == ProviderType.OTHER
                else None
            )
            return provider, model_name, actual_name
        actual_name = (
            provider_config.get("provider_name")
            if provider == ProviderType.OTHER
            else None
        )
        return provider, default_model, actual_name
        # if model_name:
        #     return provider, model_name
        # return provider, default_model

    def _stream_markdown(self, content: str, live: Live) -> None:
        """Update live display with markdown-formatted content"""
        try:
            live.update(Markdown(content))
        except Exception:
            live.update(Text(content))

    def handle_prompt(
        self, prompt: str, provider: Optional[str] = None, model: Optional[str] = None
    ) -> None:
        """Handle a user prompt and stream the response"""
        try:
            provider_type, model_name, custom_provider = self._get_provider_and_model(
                provider, model
            )

            self._setup_environment(provider_type)

            messages = [{"role": "user", "content": prompt}]

            with Live(
                "", refresh_per_second=6, console=self.console, auto_refresh=True
            ) as live:
                live.console.width = None
                accumulated_text = ""

                actual_model = model_name
                if provider_type == ProviderType.OTHER and custom_provider:
                    actual_model = f"{custom_provider}/{model_name}"

                response = completion(
                    model=actual_model, messages=messages, stream=True
                )

                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    accumulated_text += content
                    self._stream_markdown(accumulated_text, live)

        except Exception as e:
            self.console.print(f"Error: {str(e)}", style="bold red")
            raise
