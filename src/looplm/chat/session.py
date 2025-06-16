# src/looplm/chat/session.py - Updated for new command system

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from litellm import completion, completion_cost
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from ..commands import CommandManager
from ..config.manager import ConfigManager
from ..config.providers import ProviderType


@dataclass
class TokenUsage:
    """Tracks token usage for a message"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TokenUsage":
        """Create from dictionary"""
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            cost=data.get("cost", 0.0),
        )

    def format_number(self, value: int) -> str:
        """Format numbers with K/M suffixes"""
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{value:,}"


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
    compacted: bool = False
    compact_summary: Optional[str] = None
    compact_index: Optional[int] = None

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
                # Check if this is a custom provider name
                providers = self.config_manager.get_configured_providers()
                found = False

                # First check for custom (OTHER) providers
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

            provider_config = self._get_provider_config(provider)
            if model_name:
                actual_name = (
                    provider_config.get("provider_name")
                    if provider == ProviderType.OTHER
                    else None
                )
                return provider, model_name, actual_name

            default_model = provider_config.get("default_model")
            if not default_model:
                # Fallback to first model in the models list if available
                models = provider_config.get("models", [])
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

    def clear_last_messages(self, count: int = 1, preserve_cost: bool = True):
        """Clear the last N messages (excluding system messages)

        Args:
            count: Number of messages to clear from the end
            preserve_cost: Whether to preserve the total cost (True) or recalculate (False)

        Returns:
            int: Number of messages actually cleared
        """
        # Get non-system messages
        non_system_messages = [msg for msg in self.messages if msg.role != "system"]

        if count > len(non_system_messages):
            count = len(non_system_messages)

        if count <= 0:
            return 0

        # Rebuild message list
        system_messages = [msg for msg in self.messages if msg.role == "system"]
        remaining_messages = non_system_messages[:-count]

        self.messages = system_messages + remaining_messages
        self.updated_at = datetime.now()

        if not preserve_cost:
            # Recalculate usage from remaining messages
            new_usage = TokenUsage()
            for msg in remaining_messages:
                if msg.token_usage:
                    new_usage.input_tokens += msg.token_usage.input_tokens
                    new_usage.output_tokens += msg.token_usage.output_tokens
                    new_usage.total_tokens += msg.token_usage.total_tokens
                    new_usage.cost += msg.token_usage.cost
            self.total_usage = new_usage

        return count

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
        self.total_usage.cost += usage.cost
        self.updated_at = datetime.now()

    def _stream_markdown(self, content: str, live: Live) -> None:
        """Update live display with markdown content"""
        try:
            markdown = Markdown(content)
            live.update(markdown, refresh=True)
        except Exception:
            text = Text(content)
            live.update(text)

    def _handle_streaming_response_with_progress(
        self, model: str, messages: List[Dict], show_tokens: bool = False
    ) -> str:
        """Handle streaming response with progress animation instead of real-time display"""
        accumulated_text = ""
        timestamp = datetime.now()

        self.console.print()  # Add newline before response
        self.console.print(f"{timestamp.strftime('%H:%M')} ", style="dim", end="")
        self.console.print("Assistant ▣", style="bright_green")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            # Create dynamic task description with model info and context
            provider_display = self.provider.value if self.provider else "unknown"

            # Count non-system messages for context
            non_system_count = len(
                [msg for msg in self.messages if msg.role != "system"]
            )

            # Estimate input tokens roughly (4 chars per token is a common approximation)
            input_content = " ".join([msg["content"] for msg in messages])
            estimated_input_tokens = len(input_content) // 4

            if estimated_input_tokens > 1000:
                token_display = f" (~{estimated_input_tokens//1000}K tokens)"
            elif estimated_input_tokens > 0:
                token_display = f" (~{estimated_input_tokens} tokens)"
            else:
                token_display = ""

            # Fun, dynamic messages to improve UX
            import random

            creative_messages = [
                # Thoughtful/Contemplative
                # f"🤔 Pondering with {provider_display}/{self.model}{token_display}...",
                # f"🧠 Deep thinking via {provider_display}/{self.model}{token_display}...",
                # f"💭 Brewing thoughts using {provider_display}/{self.model}{token_display}...",
                # f"🎯 Crafting response with {provider_display}/{self.model}{token_display}...",
                # f"🔍 Exploring possibilities with {provider_display}/{self.model}{token_display}...",
                # Thoughtful/Contemplative
                f"🤔 Pondering with {self.model}{token_display}...",
                f"🧠 Deep thinking via {self.model}{token_display}...",
                f"💭 Brewing thoughts using {self.model}{token_display}...",
                f"🎯 Crafting response with {self.model}{token_display}...",
                f"🔍 Exploring possibilities with {self.model}{token_display}...",
                # Magical/Mystical
                f"🔮 Consulting the AI oracle {self.model}{token_display}...",
                f"✨ Weaving digital magic via {self.model}{token_display}...",
                f"🪄 Conjuring wisdom through {self.model}{token_display}...",
                f"🌟 Channeling cosmic knowledge from {self.model}{token_display}...",
                # Creative/Artistic
                f"🎨 Painting words via {self.model}{token_display}...",
                f"🎭 Performing linguistic theatre with {self.model}{token_display}...",
                f"🎼 Composing a response using {self.model}{token_display}...",
                f"📝 Scribing wisdom through {self.model}{token_display}...",
                # Tech/Action
                f"⚡ Sparking neural networks in {self.model}{token_display}...",
                f"🚀 Launching query to {self.model}{token_display}...",
                f"⚙️ Processing magic through {self.model}{token_display}...",
                f"🔥 Igniting synapses in {self.model}{token_display}...",
                # Playful/Fun
                f"🤖 Having a chat with {self.model}{token_display}...",
                f"🎪 Putting on a thinking show via {self.model}{token_display}...",
                f"🎲 Rolling the dice of wisdom with {self.model}{token_display}...",
                f"🎈 Floating ideas through {self.model}{token_display}...",
            ]

            task_description = random.choice(creative_messages)
            task = progress.add_task(task_description, total=None)

            response = completion(
                model=model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
            )

            final_chunk = None
            cost = 0.0

            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                accumulated_text += content

                if hasattr(chunk, "usage") and chunk.usage is not None:
                    final_chunk = chunk

        # Extract cost from the final chunk with usage information
        if final_chunk and hasattr(final_chunk, "usage") and final_chunk.usage:
            try:
                cost = completion_cost(final_chunk)
            except Exception:
                cost = 0.0

        self.latest_response = accumulated_text

        # Display the complete response at once using Markdown
        try:
            markdown = Markdown(accumulated_text)
            self.console.print(markdown)
        except Exception:
            self.console.print(accumulated_text)

        # Add response to history with token usage
        token_usage = TokenUsage(
            input_tokens=final_chunk.usage.prompt_tokens,
            output_tokens=final_chunk.usage.completion_tokens,
            total_tokens=final_chunk.usage.prompt_tokens
            + final_chunk.usage.completion_tokens,
            cost=cost,
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
                f"Total: {token_usage.total_tokens}, "
                f"Cost: ${token_usage.cost:.6f}[/dim]"
            )
        return accumulated_text

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
        self,
        content: str,
        stream: bool = True,
        show_tokens: bool = False,
        debug: bool = False,
        use_progress_streaming: bool = True,
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
            use_progress_streaming: Whether to use progress animation (True) or real-time streaming (False)

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
            self.config_manager.load_environment(self.provider.value)

            # Add user message
            user_msg = Message("user", processed_content)
            self.messages.append(user_msg)

            # Prepare model name
            # IMPORTANT FIX: Check if the model name already contains the provider prefix
            if self.provider == ProviderType.OTHER and self.custom_provider:
                # For custom providers
                if not self.model.startswith(f"{self.custom_provider}/"):
                    actual_model = f"{self.custom_provider}/{self.model}"
                else:
                    actual_model = self.model
            else:
                # For standard providers
                provider_prefix = f"{self.provider.value}/"
                if self.model.startswith(provider_prefix):
                    # Model already has the provider prefix, use as is
                    actual_model = self.model
                else:
                    # Only add prefix for certain providers that need it
                    if self.provider in [
                        ProviderType.GEMINI,
                        ProviderType.BEDROCK,
                        ProviderType.AZURE,
                    ]:
                        actual_model = f"{self.provider.value}/{self.model}"
                    else:
                        # For most providers like OpenAI, Anthropic, Groq, etc. don't add prefix
                        actual_model = self.model

            # Check if the model supports vision
            try:
                import litellm

                model_supports_vision = litellm.supports_vision(model=actual_model)
            except Exception:
                # If we can't import litellm or check, assume model doesn't support vision
                model_supports_vision = False
                self.console.print(
                    f"\nWarning: Unable to verify if model {actual_model} supports vision. Proceeding with text-only input.",
                    style="bold yellow",
                )

            # Get messages for API
            messages = self.get_messages_for_api()

            # If we have images and the model supports vision, convert message format
            if image_metadata and model_supports_vision:
                # Update the last user message to have content as an array with text and images
                last_message = messages[-1]
                if last_message["role"] == "user":
                    # Create new content list with text and images
                    content_list = [{"type": "text", "text": processed_content}]

                    # Add each image
                    for img in image_metadata:
                        content_list.append(img)

                    # Replace content with the list
                    last_message["content"] = content_list
            elif image_metadata and not model_supports_vision:
                # Warn that the model doesn't support images
                self.console.print(
                    f"\nWarning: Model {actual_model} does not support vision input. Images will be ignored.",
                    style="bold yellow",
                )

            if stream:
                if use_progress_streaming:
                    return self._handle_streaming_response_with_progress(
                        actual_model, messages, show_tokens
                    )
                else:
                    return self._handle_streaming_response(
                        actual_model, messages, show_tokens
                    )
            else:
                return self._handle_normal_response(actual_model, messages, show_tokens)

        except Exception as e:
            from rich.markup import escape

            error_message = escape(str(e))
            raise Exception(f"Error sending message: {error_message}")

    def __del__(self):
        """Cleanup when session is destroyed."""

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

            final_chunk = None
            cost = 0.0

            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                accumulated_text += content
                self._stream_markdown(accumulated_text, live)

                if hasattr(chunk, "usage") and chunk.usage is not None:
                    final_chunk = chunk

            # Extract cost from the final chunk with usage information
            if final_chunk and hasattr(final_chunk, "usage") and final_chunk.usage:
                try:
                    cost = completion_cost(final_chunk)
                except Exception:
                    cost = 0.0

            self.latest_response = accumulated_text

            # Add response to history with token usage
            token_usage = TokenUsage(
                input_tokens=final_chunk.usage.prompt_tokens,
                output_tokens=final_chunk.usage.completion_tokens,
                total_tokens=final_chunk.usage.prompt_tokens
                + final_chunk.usage.completion_tokens,
                cost=cost,
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
                    f"Total: {token_usage.total_tokens}, "
                    f"Cost: ${token_usage.cost:.6f}[/dim]"
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

        try:
            cost = completion_cost(response)
        except Exception:
            cost = 0.0

        content = response.choices[0].message.content
        self.latest_response = content

        token_usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.prompt_tokens
            + response.usage.completion_tokens,
            cost=cost,
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
                f"Total: {token_usage.total_tokens}, ",
                f"Cost: ${token_usage.cost:.6f}[/dim]",
            )
        return content

    def to_dict(self) -> Dict:
        """Convert session to dictionary for serialization, including compact state."""
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
            "compacted": self.compacted,
            "compact_summary": self.compact_summary,
            "compact_index": self.compact_index,
        }

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """Get messages in format needed for API calls - only role and content."""
        if self.is_compacted:
            msgs = []
            # System prompt
            system_msgs = [msg for msg in self.messages if msg.role == "system"]
            if system_msgs:
                msgs.append({"role": "system", "content": system_msgs[0].content})
            # Summary as assistant message
            msgs.append({"role": "assistant", "content": self.compact_summary})
            # All messages after compact_index
            if self.compact_index is not None:
                for msg in self.messages[self.compact_index :]:
                    if msg.role != "system":
                        msgs.append({"role": msg.role, "content": msg.content})
            return msgs
        else:
            return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def set_compact_summary(self, summary: str):
        """Set the session as compacted, store summary and index."""
        self.compacted = True
        self.compact_summary = summary
        self.compact_index = len(self.messages)
        self.updated_at = datetime.now()

    def reset_compact(self):
        """Reset compact state, use full history again."""
        self.compacted = False
        self.compact_summary = None
        self.compact_index = None
        self.updated_at = datetime.now()

    @property
    def is_compacted(self) -> bool:
        """Return True if session is currently compacted."""
        return (
            self.compacted
            and self.compact_summary is not None
            and self.compact_index is not None
        )

    @classmethod
    def from_dict(cls, data: Dict) -> "ChatSession":
        """Create session from dictionary, including compact state."""
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
            compacted=data.get("compacted", False),
            compact_summary=data.get("compact_summary"),
            compact_index=data.get("compact_index"),
        )
