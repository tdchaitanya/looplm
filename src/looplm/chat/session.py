# src/looplm/chat/session.py - Updated for new command system

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4
from pathlib import Path

import gnureadline
from litellm import completion
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from ..config.manager import ConfigManager
from ..config.providers import ProviderType
from ..commands import CommandManager


@dataclass
class TokenUsage:
    """Tracks token usage for a message"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TokenUsage":
        """Create from dictionary"""
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass
class Message:
    """Represents a chat message"""

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    token_usage: Optional[TokenUsage] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for API calls and serialization"""
        result = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.token_usage:
            result["token_usage"] = self.token_usage.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        """Create message from dictionary"""
        token_usage = None
        if "token_usage" in data:
            token_usage = TokenUsage.from_dict(data["token_usage"])

        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            token_usage=token_usage,
        )


@dataclass
class ChatSession:
    """Manages a chat session with history and configuration"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = field(default="New Chat")
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    total_usage: TokenUsage = field(default_factory=TokenUsage)
    base_path: Path = field(default_factory=lambda: Path(os.getcwd()))
    latest_response: Optional[str] = None

    # Configuration
    console: Console = field(
        default_factory=lambda: Console(
            force_terminal=True, force_interactive=True, width=None
        )
    )
    config_manager: ConfigManager = field(default_factory=ConfigManager)
    provider: Optional[ProviderType] = None
    model: Optional[str] = None
    custom_provider: Optional[str] = None

    def __post_init__(self):
        """Initialize after creation"""
        if not self.provider or not self.model:
            provider, model, custom_provider = self._get_provider_and_model()
            self.provider = provider
            self.model = model
            self.custom_provider = custom_provider

    def _get_provider_and_model(
        self, provider_name: Optional[str] = None, model_name: Optional[str] = None
    ) -> tuple[ProviderType, str, Optional[str]]:
        """Get provider and model configuration"""
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

    def _get_provider_config(self, provider: ProviderType) -> dict:
        """Get provider configuration"""
        providers = self.config_manager.get_configured_providers()
        if provider not in providers:
            raise ValueError(f"Provider {provider.value} is not configured")
        return providers[provider]

    def set_system_prompt(self, prompt: str):
        """Set or update system prompt"""
        # Remove existing system messages
        self.messages = [msg for msg in self.messages if msg.role != "system"]
        # Add new system prompt
        self.messages.insert(0, Message("system", prompt))
        self.updated_at = datetime.now()

    def set_model(self, model_name: str, provider_name: Optional[str] = None) -> None:
        """Set the model and optionally the provider for this session."""
        if provider_name:
            try:
                # Handle both standard and custom providers
                try:
                    provider = ProviderType(provider_name)
                except ValueError:
                    # Check if this is a custom provider
                    providers = self.config_manager.get_configured_providers()
                    other_config = providers.get(ProviderType.OTHER, {})
                    if (
                        other_config
                        and other_config.get("provider_name") == provider_name
                    ):
                        provider = ProviderType.OTHER
                        self.custom_provider = provider_name
                    else:
                        raise ValueError(f"Invalid provider: {provider_name}")

                # Validate provider is configured
                self._get_provider_config(provider)
                self.provider = provider
                self.model = model_name
            except Exception as e:
                raise ValueError(f"Error setting provider: {str(e)}")
        else:
            # Just update the model for current provider
            self.model = model_name

        self.updated_at = datetime.now()

    def get_system_prompt(self) -> Optional[str]:
        """Get current system prompt"""
        system_messages = [msg for msg in self.messages if msg.role == "system"]
        return system_messages[0].content if system_messages else None

    def _update_total_usage(self, usage: TokenUsage):
        """Update total token usage"""
        self.total_usage.input_tokens += usage.input_tokens
        self.total_usage.output_tokens += usage.output_tokens
        self.total_usage.total_tokens += usage.total_tokens
        self.updated_at = datetime.now()

    def _stream_markdown(self, content: str, live: Live) -> None:
        """Update live display with markdown content"""
        try:
            markdown = Markdown(content)
            live.update(markdown, refresh=True)
        except Exception:
            text = Text(content)
            live.update(text)

    def clear_history(self, keep_system_prompt: bool = True):
        """Clear chat history"""
        system_prompt = None
        if keep_system_prompt:
            system_prompt = self.get_system_prompt()

        self.messages.clear()
        self.total_usage = TokenUsage()

        if keep_system_prompt and system_prompt:
            self.set_system_prompt(system_prompt)

        self.updated_at = datetime.now()

    def send_message(
        self, content: str, stream: bool = True, show_tokens: bool = False, debug: bool = False
    ) -> str:
        """
        Send a message and get response.

        Handles command processing (@file, @folder, @github, @image) before sending
        to the model.

        Args:
            content: Message content, may contain @ commands
            stream: Whether to stream the response
            show_tokens: Whether to show token usage
            debug: Whether to debug command processing without sending to LLM

        Returns:
            str: Model's response

        Raises:
            Exception: If there's an error sending the message or processing commands
        """
        try:
            # Process all commands in the message using the CommandManager
            command_manager = CommandManager(base_path=self.base_path)
            
            # Process all commands in the message
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            processed_result = loop.run_until_complete(
                command_manager.process_text(content)
            )
            
            # Unpack the result - now includes processed text and image metadata
            processed_content, image_metadata = processed_result
            
            if debug:
                # In debug mode, just display the processed content
                self.console.print("\nProcessed Content:", style="bold blue")
                self.console.print(processed_content)
                if image_metadata:
                    self.console.print("\nImage Metadata:", style="bold magenta")
                    for img in image_metadata:
                        self.console.print(img)
                return processed_content
            
            # Only proceed with the LLM if command processing succeeded
            self.config_manager._prepare_environment(self.provider.value)
    
            # Add user message
            user_msg = Message("user", processed_content)
            self.messages.append(user_msg)

            # Prepare model name
            actual_model = self.model
            if self.provider == ProviderType.OTHER and self.custom_provider:
                actual_model = f"{self.custom_provider}/{self.model}"

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

            # Get messages for API
            messages = self.get_messages_for_api()
            
            # If we have images and the model supports vision, convert message format
            if image_metadata and model_supports_vision:
                # Update the last user message to have content as an array with text and images
                last_message = messages[-1]
                if last_message["role"] == "user":
                    # Create new content list with text and images
                    content_list = [
                        {
                            "type": "text",
                            "text": processed_content
                        }
                    ]
                    
                    # Add each image
                    for img in image_metadata:
                        content_list.append(img)
                    
                    # Replace content with the list
                    last_message["content"] = content_list
            elif image_metadata and not model_supports_vision:
                # Warn that the model doesn't support images
                self.console.print(
                    f"\nWarning: Model {actual_model} does not support vision input. Images will be ignored.",
                    style="bold yellow"
                )

            if stream:
                return self._handle_streaming_response(actual_model, messages, show_tokens)
            else:
                return self._handle_normal_response(actual_model, messages, show_tokens)

        except Exception as e:
            from rich.markup import escape
            error_message = escape(str(e))
            raise Exception(f"Error sending message: {error_message}")        
    def __del__(self):
        """Cleanup when session is destroyed."""
        pass

    def _handle_streaming_response(
        self, model: str, messages: List[Dict], show_tokens: bool = False
    ) -> str:
        """Handle streaming response from API"""
        accumulated_text = ""
        timestamp = datetime.now()

        self.console.print()  # Add newline before response
        self.console.print(f"{timestamp.strftime('%H:%M')} ", style="dim", end="")
        self.console.print("Assistant ▣", style="bright_green")

        with Live("", refresh_per_second=6, console=self.console) as live:
            live.console.width = None

            response = completion(
                model=model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
            )

            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                accumulated_text += content
                self._stream_markdown(accumulated_text, live)

            self.latest_response = accumulated_text

            # Add response to history with token usage
            token_usage = TokenUsage(
                input_tokens=chunk.usage.prompt_tokens,
                output_tokens=chunk.usage.completion_tokens,
                total_tokens=chunk.usage.prompt_tokens + chunk.usage.completion_tokens,
            )

            self.messages.append(
                Message(
                    "assistant",
                    accumulated_text,
                    timestamp=timestamp,
                    token_usage=token_usage,
                )
            )
            self._update_total_usage(token_usage)

            # Display token usage
            if show_tokens:
                self.console.print(
                    f"\n[dim]Token usage - Input: {token_usage.input_tokens}, "
                    f"Output: {token_usage.output_tokens}, "
                    f"Total: {token_usage.total_tokens}[/dim]"
                )
            return accumulated_text

    def _handle_normal_response(
        self, model: str, messages: List[Dict], show_tokens: bool = False
    ) -> str:
        """Handle normal (non-streaming) response from API"""
        response = completion(
            model=model,
            messages=messages,
        )

        content = response.choices[0].message.content
        self.latest_response = content

        token_usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.prompt_tokens
            + response.usage.completion_tokens,
        )

        self.messages.append(
            Message(
                "assistant", content, timestamp=datetime.now(), token_usage=token_usage
            )
        )
        self._update_total_usage(token_usage)

        timestamp = datetime.now()
        self.console.print()  # Add newline before response
        self.console.print(f"{timestamp.strftime('%H:%M')} ", style="dim", end="")
        self.console.print("Assistant ▣", style="bright_green")
        self.console.print(Markdown(content))

        # Optionally display token usage
        if show_tokens:
            self.console.print(
                f"\n[dim]Token usage - Input: {token_usage.input_tokens}, "
                f"Output: {token_usage.output_tokens}, "
                f"Total: {token_usage.total_tokens}[/dim]"
            )
        return content

    def to_dict(self) -> Dict:
        """Convert session to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "total_usage": self.total_usage.to_dict(),
            "provider": self.provider.value if self.provider else None,
            "model": self.model,
            "custom_provider": self.custom_provider,
        }

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """Get messages in format needed for API calls - only role and content"""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    @classmethod
    def from_dict(cls, data: Dict) -> "ChatSession":
        """Create session from dictionary"""
        messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        total_usage = TokenUsage.from_dict(data.get("total_usage", {}))
        provider = ProviderType(data["provider"]) if data.get("provider") else None

        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", "New Chat"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=messages,
            total_usage=total_usage,
            provider=provider,
            model=data.get("model"),
            custom_provider=data.get("custom_provider"),
        )