# src/looplm/conversation/handler.py
import os
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
from ..preprocessor.files import FilePreprocessor


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
        self.file_preprocessor = FilePreprocessor(base_path=os.getcwd())

    def __del__(self):
        """Cleanup when handler is destroyed."""
        if hasattr(self, "file_preprocessor"):
            self.file_preprocessor.cleanup()

    def _get_provider_config(self, provider: ProviderType) -> dict:
        """Get full provider configuration including custom name if it's OTHER type"""
        providers = self.config_manager.get_configured_providers()
        if provider not in providers:
            raise ValueError(f"Provider {provider.value} is not configured")
        return providers[provider]

    def _setup_environment(self, provider: ProviderType) -> None:
        """Set up environment variables for the specified provide"""

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
            # markdown = Markdown(content)
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

        The prompt may contain @file directives which will be processed before sending
        to the LLM provider.

        Args:
            prompt: User prompt, possibly containing @file directives
            provider: Optional provider override
            model: Optional model override
        """
        try:

            processed_prompt = self.file_preprocessor.process_prompt(prompt)

            provider_type, model_name, custom_provider = self._get_provider_and_model(
                provider, model
            )

            self._setup_environment(provider_type)

            messages = [{"role": "user", "content": processed_prompt}]

            with Live(
                "", refresh_per_second=4, console=self.console, auto_refresh=True
            ) as live:
                live.console.width = None
                accumulated_text = ""

                actual_model = model_name
                if provider_type == ProviderType.OTHER and custom_provider:
                    actual_model = f"{custom_provider}/{model_name}"

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
