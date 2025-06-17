# src/looplm/chat/session.py - Updated for new command system

import os
import random
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

    # Tool calling attributes
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for API calls and serialization"""
        result = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.token_usage:
            result["token_usage"] = self.token_usage.to_dict()
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.name:
            result["name"] = self.name
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
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
        )


# Enhanced creative messages
def get_creative_message(model_name, token_display, has_images=False, has_pdfs=False):
    if has_images and has_pdfs:
        # Mixed media - images and PDFs
        creative_messages = [
            f"📄🖼️ Analyzing documents and visuals with {model_name}{token_display}...",
            f"📊👁️ Processing PDFs and images via {model_name}{token_display}...",
            f"🔍📋 Examining multimedia content with {model_name}{token_display}...",
            f"📑🎨 Reading documents and visuals through {model_name}{token_display}...",
            f"🗃️📸 Analyzing files and images with {model_name}{token_display}...",
            f"📖🌅 Processing text and visual content via {model_name}{token_display}...",
        ]
    elif has_pdfs:
        # PDF-focused messages
        creative_messages = [
            f"📄 Analyzing documents with {model_name}{token_display}...",
            f"📑 Reading PDF content via {model_name}{token_display}...",
            f"📋 Processing document text with {model_name}{token_display}...",
            f"📖 Examining PDF files through {model_name}{token_display}...",
            f"🗃️ Document analysis in progress with {model_name}{token_display}...",
            f"📊 Parsing the document content via {model_name}{token_display}...",
            f"📝 Digesting document information with {model_name}{token_display}...",
            f"🔍 Reviewing PDF content through {model_name}{token_display}...",
        ]
    elif has_images:
        # Image-focused messages
        creative_messages = [
            f"🖼️ Analyzing visuals with {model_name}{token_display}...",
            f"👁️ Looking at images through {model_name}{token_display}...",
            f"🎨 Processing visual content via {model_name}{token_display}...",
            f"📸 Examining images with {model_name}{token_display}...",
            f"🔍 Visual analysis in progress with {model_name}{token_display}...",
            f"🌅 Reading pixels and text via {model_name}{token_display}...",
            f"🎭 Interpreting visual stories with {model_name}{token_display}...",
            f"🖼️ Decoding images and text through {model_name}{token_display}...",
        ]
    else:
        creative_messages = [
            # Thoughtful/Contemplative
            f"🤔 Pondering with {model_name}{token_display}...",
            f"🧠 Deep thinking via {model_name}{token_display}...",
            f"💭 Brewing thoughts using {model_name}{token_display}...",
            f"🎯 Crafting response with {model_name}{token_display}...",
            f"🔍 Exploring possibilities with {model_name}{token_display}...",
            f"🔮 Consulting the AI oracle {model_name}{token_display}...",
            f"✨ Weaving digital magic via {model_name}{token_display}...",
            f"🪄 Conjuring wisdom through {model_name}{token_display}...",
            f"🌟 Channeling cosmic knowledge from {model_name}{token_display}...",
            f"🎨 Painting words via {model_name}{token_display}...",
            f"🎭 Performing linguistic theatre with {model_name}{token_display}...",
            f"🎼 Composing a response using {model_name}{token_display}...",
            f"📝 Scribing wisdom through {model_name}{token_display}...",
            f"⚡ Sparking neural networks in {model_name}{token_display}...",
            f"🚀 Launching query to {model_name}{token_display}...",
            f"⚙️ Processing magic through {model_name}{token_display}...",
            f"🔥 Igniting synapses in {model_name}{token_display}...",
            f"🤖 Having a chat with {model_name}{token_display}...",
            f"🎪 Putting on a thinking show via {model_name}{token_display}...",
            f"🎲 Rolling the dice of wisdom with {model_name}{token_display}...",
            f"🎈 Floating ideas through {model_name}{token_display}...",
            f"⏳ Traveling through time and tokens with {model_name}{token_display}...",
            f"🗺️ Mapping out the perfect response via {model_name}{token_display}...",
            f"🧭 Navigating the knowledge seas with {model_name}{token_display}...",
            f"👨‍🍳 Cooking up something special with {model_name}{token_display}...",
            f"🍳 Whisking up wisdom via {model_name}{token_display}...",
            f"🦋 Letting thoughts bloom via {model_name}{token_display}...",
            f"🌊 Riding the waves of knowledge with {model_name}{token_display}...",
        ]

    return creative_messages


def analyze_message_content(messages):
    """Analyze messages to count text tokens, images, and PDFs"""
    text_content = []
    image_count = 0
    pdf_count = 0

    for msg in messages:
        content = msg.get("content")
        if not content:
            continue

        if isinstance(content, str):
            text_content.append(content)
        elif isinstance(content, list):
            # Media content - extract text and count images/PDFs
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_value = item.get("text", "")
                        # Ensure we don't add None values
                        if text_value is not None:
                            text_content.append(text_value)
                    elif item.get("type") == "image_url":
                        image_count += 1
                    elif item.get("type") == "file":
                        # This is a PDF file
                        pdf_count += 1

    # Estimate text tokens
    # Filter out any None values that might have slipped through
    text_content = [text for text in text_content if text is not None]
    all_text = " ".join(text_content)
    estimated_tokens = len(all_text) // 4

    return estimated_tokens, image_count, pdf_count


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

    # Tool support
    tool_manager: Optional[object] = None

    def enable_tools(
        self, tool_names: Optional[List[str]] = None, require_approval: bool = False
    ) -> None:
        """Enable tools for this session"""
        from ..tools.manager import ToolManager

        self.tool_manager = ToolManager(
            console=self.console, require_approval=require_approval
        )

        if tool_names:
            loaded = self.tool_manager.load_tools_from_names(tool_names)
            if loaded:
                self.console.print(
                    f"🔧 Enabled {len(loaded)} tools: {', '.join(loaded)}", style="blue"
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
        """Disable tools for this session"""
        self.tool_manager = None
        self.console.print("🔧 Tools disabled", style="dim")

    def list_available_tools(self) -> List[str]:
        """List available tools"""
        if not self.tool_manager:
            return []
        return self.tool_manager.registry.list_tools()

    def list_enabled_tools(self) -> List[str]:
        """List enabled tools"""
        if not self.tool_manager:
            return []
        return self.tool_manager.registry.list_tools()

    def add_message_dict(self, message_dict: Dict) -> None:
        """Add a message from a dictionary (for tool calls)"""
        msg = Message(
            role=message_dict["role"],
            content=message_dict.get("content", ""),
            tool_calls=message_dict.get("tool_calls"),
            tool_call_id=message_dict.get("tool_call_id"),
            name=message_dict.get("name"),
        )
        self.messages.append(msg)

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
        self.messages.insert(0, Message(role="system", content=prompt))
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
            stream: Whether to stream the response (affects API call, not UI)
            show_tokens: Whether to show token usage
            debug: Whether to debug command processing without sending to LLM
            use_progress_streaming: Deprecated - always uses progress animation now

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
            processed_content, media_metadata = processed_result

            if debug:
                # In debug mode, just display the processed content
                self.console.print("\nProcessed Content:", style="bold blue")
                self.console.print(processed_content)
                if media_metadata:
                    self.console.print("\nMedia Metadata:", style="bold magenta")
                    for media in media_metadata:
                        self.console.print(media)
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

            # Check if the model supports vision and function calling
            try:
                import litellm

                model_supports_vision = litellm.supports_vision(model=actual_model)
                model_supports_tools = litellm.supports_function_calling(
                    model=actual_model
                )
            except Exception:
                # If we can't import litellm or check, assume model doesn't support these features
                model_supports_vision = False
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

            # Get tool schemas if tools are enabled and supported
            tools = None
            if self.tool_manager and model_supports_tools:
                tool_schemas = self.tool_manager.get_tool_schemas()
                if tool_schemas:
                    tools = tool_schemas

            # Get messages for API - use tool-aware version if tools are enabled
            if tools:
                messages = self.get_messages_for_api_with_tools()
            else:
                messages = self.get_messages_for_api()

            # Check if model supports PDF input as well
            try:
                from litellm.utils import supports_pdf_input

                model_supports_pdf = supports_pdf_input(model=actual_model)
            except Exception:
                model_supports_pdf = False

            # Separate media by type
            images = []
            pdfs = []
            if media_metadata:
                for media in media_metadata:
                    if media.get("type") == "image_url":
                        images.append(media)
                    elif media.get("type") == "file_url":
                        pdfs.append(media)

            # If we have media and the model supports it, convert message format
            if (images or pdfs) and (model_supports_vision or model_supports_pdf):
                # Update the last user message to have content as an array with text and media
                last_message = messages[-1]
                if last_message["role"] == "user":
                    # Create new content list with text
                    text_content = (
                        processed_content if processed_content is not None else ""
                    )
                    content_list = [{"type": "text", "text": text_content}]

                    # Add images if supported
                    if images and model_supports_vision:
                        content_list.extend(images)
                    elif images and not model_supports_vision:
                        self.console.print(
                            f"\nWarning: Model {actual_model} does not support vision input. Images will be ignored.",
                            style="bold yellow",
                        )

                    # Add PDFs if supported
                    if pdfs and model_supports_pdf:
                        content_list.extend([pdf["file_data"] for pdf in pdfs])
                    elif pdfs and not model_supports_pdf:
                        self.console.print(
                            f"\nWarning: Model {actual_model} does not support PDF input. PDFs will be ignored.",
                            style="bold yellow",
                        )

                    # Replace content with the list
                    last_message["content"] = content_list
            elif media_metadata:
                # We have media but model doesn't support any of it
                if images and not model_supports_vision:
                    self.console.print(
                        f"\nWarning: Model {actual_model} does not support vision input. Images will be ignored.",
                        style="bold yellow",
                    )
                if pdfs and not model_supports_pdf:
                    self.console.print(
                        f"\nWarning: Model {actual_model} does not support PDF input. PDFs will be ignored.",
                        style="bold yellow",
                    )

            # Always use the unified response handler with progress animation
            return self._handle_response_with_progress(
                actual_model, messages, show_tokens, stream, tools
            )

        except Exception as e:
            from rich.markup import escape

            error_message = escape(str(e))
            raise Exception(f"Error sending message: {error_message}")

    def _handle_response_with_progress(
        self,
        model: str,
        messages: List[Dict],
        show_tokens: bool = False,
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
    ) -> str:
        """Handle both streaming and non-streaming responses with progress animation"""
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

            # input_content = " ".join([
            #     msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
            #     for msg in messages
            #     if msg.get("content")
            # ])
            # Create dynamic task description with model info and context
            estimated_tokens, image_count, pdf_count = analyze_message_content(messages)

            # Build context display
            context_parts = []
            if estimated_tokens > 1000:
                context_parts.append(f"~{estimated_tokens//1000}K tokens")
            elif estimated_tokens > 0:
                context_parts.append(f"~{estimated_tokens} tokens")

            if image_count > 0:
                if image_count == 1:
                    context_parts.append("1 image")
                else:
                    context_parts.append(f"{image_count} images")

            if pdf_count > 0:
                if pdf_count == 1:
                    context_parts.append("1 PDF")
                else:
                    context_parts.append(f"{pdf_count} PDFs")

            if context_parts:
                token_display = f" ({', '.join(context_parts)})"
            else:
                token_display = ""

            # Fun, dynamic messages to improve UX
            task_description = random.choice(
                get_creative_message(
                    self.model, token_display, image_count > 0, pdf_count > 0
                )
            )
            task = progress.add_task(task_description, total=None)

            # Prepare API call arguments
            call_kwargs = {
                "model": model,
                "messages": messages,
                "stream": True,
                "stream_options": {"include_usage": True} if stream else None,
            }

            if tools:
                call_kwargs["tools"] = tools
                call_kwargs["tool_choice"] = "auto"

            # Make API call with or without streaming
            response = completion(**call_kwargs)

            final_chunk = None
            cost = 0.0
            tool_calls = []

            for chunk in response:
                delta = chunk.choices[0].delta

                # Handle text content
                if delta.content:
                    accumulated_text += delta.content

                # Handle tool calls (streaming)
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

                # Check for usage information
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    final_chunk = chunk

        # Extract cost from the final chunk with usage information
        if final_chunk and hasattr(final_chunk, "usage") and final_chunk.usage:
            try:
                cost = completion_cost(final_chunk)
            except Exception:
                cost = 0.0

            # Create token usage from streaming response
            token_usage = TokenUsage(
                input_tokens=final_chunk.usage.prompt_tokens,
                output_tokens=final_chunk.usage.completion_tokens,
                total_tokens=final_chunk.usage.prompt_tokens
                + final_chunk.usage.completion_tokens,
                cost=cost,
            )
        else:
            # Fallback if no usage info in streaming
            token_usage = TokenUsage()

        # Handle ReACT-style tool calling cycle
        if tool_calls and self.tool_manager:
            # Add assistant message with tool calls to conversation
            # Note: Some models require non-null content even when tool_calls are present
            assistant_message = Message(
                role="assistant",
                content=accumulated_text or "",
                timestamp=timestamp,
                token_usage=token_usage,
                tool_calls=tool_calls,
            )
            self.messages.append(assistant_message)

            # Display assistant response if there's content
            if accumulated_text:
                try:
                    markdown = Markdown(accumulated_text)
                    self.console.print(markdown)
                except Exception:
                    self.console.print(accumulated_text)

            # Execute all tool calls for this round
            for tool_call in tool_calls:
                try:
                    tool_call_id, result = self.tool_manager.execute_tool_call(
                        tool_call["id"],
                        tool_call["function"]["name"],
                        tool_call["function"]["arguments"],
                    )

                    # Add tool response to conversation (following LiteLLM format)
                    tool_message = Message(
                        role="tool",
                        content=str(result),
                        timestamp=datetime.now(),
                        tool_call_id=tool_call["id"],
                        name=tool_call["function"]["name"],
                    )
                    self.messages.append(tool_message)

                except Exception as e:
                    error_message = f"Tool execution failed: {str(e)}"
                    self.console.print(f"[red]⚠️ {error_message}[/red]")

                    # Add error response to conversation (following LiteLLM format)
                    tool_message = Message(
                        role="tool",
                        content=error_message,
                        timestamp=datetime.now(),
                        tool_call_id=tool_call["id"],
                        name=tool_call["function"]["name"],
                    )
                    self.messages.append(tool_message)

            # ReACT cycle: Continue until LLM provides final response (no more tool calls)
            final_text = self._continue_react_cycle(model, tools, token_usage)
            self.latest_response = final_text

        else:
            # Regular response without tool calls
            self.latest_response = accumulated_text

            # Display the complete response at once using Markdown
            try:
                markdown = Markdown(accumulated_text)
                self.console.print(markdown)
            except Exception:
                self.console.print(accumulated_text)

            # Add response to history with token usage
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
        return self.latest_response

    def _continue_react_cycle(
        self,
        model: str,
        tools: Optional[List[Dict]],
        token_usage: TokenUsage,
        max_iterations: int = 10,
    ) -> str:
        """
        Continue the ReACT cycle until LLM provides final response.

        ReACT Pattern:
        1. Reason: LLM analyzes available information
        2. Act: LLM calls tools if more information needed
        3. Observe: LLM sees tool results
        4. Repeat until LLM has enough information for final answer

        Args:
            model: Model to use for completions
            tools: Available tools
            token_usage: Token usage tracker to update
            max_iterations: Maximum ReACT cycles to prevent infinite loops

        Returns:
            Final response text from LLM
        """
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Get current conversation with all tool interactions
            messages = self.get_messages_for_api_with_tools()

            # Let LLM reason about tool results and decide next action
            response = completion(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=False,
            )

            response_message = response.choices[0].message
            new_tool_calls = getattr(response_message, "tool_calls", None)

            # Update token usage
            try:
                cycle_cost = completion_cost(response)
                token_usage.input_tokens += response.usage.prompt_tokens
                token_usage.output_tokens += response.usage.completion_tokens
                token_usage.total_tokens += response.usage.total_tokens
                token_usage.cost += cycle_cost
            except Exception:
                pass

            # If no more tool calls, LLM is providing final answer
            if not new_tool_calls:
                final_text = response_message.content

                # Add final assistant message to conversation
                final_message = Message(
                    "assistant",
                    final_text,
                    timestamp=datetime.now(),
                    token_usage=TokenUsage(
                        input_tokens=(
                            response.usage.prompt_tokens
                            if hasattr(response, "usage")
                            else 0
                        ),
                        output_tokens=(
                            response.usage.completion_tokens
                            if hasattr(response, "usage")
                            else 0
                        ),
                        total_tokens=(
                            response.usage.total_tokens
                            if hasattr(response, "usage")
                            else 0
                        ),
                        cost=cycle_cost if "cycle_cost" in locals() else 0.0,
                    ),
                )
                self.messages.append(final_message)

                # Display final response
                try:
                    markdown = Markdown(final_text)
                    self.console.print(markdown)
                except Exception:
                    self.console.print(final_text)

                return final_text

            # LLM wants to call more tools - continue ReACT cycle
            # Add assistant message with new tool calls
            assistant_message = Message(
                role="assistant",
                content=response_message.content or "",
                timestamp=datetime.now(),
                tool_calls=new_tool_calls,
            )
            self.messages.append(assistant_message)

            # Display reasoning if LLM provided any
            if response_message.content:
                try:
                    markdown = Markdown(response_message.content)
                    self.console.print(markdown)
                except Exception:
                    self.console.print(response_message.content)

            # Execute the new round of tool calls
            for tool_call in new_tool_calls:
                try:
                    tool_call_id, result = self.tool_manager.execute_tool_call(
                        tool_call.id,
                        tool_call.function.name,
                        tool_call.function.arguments,
                    )

                    # Add tool response to conversation
                    tool_message = Message(
                        role="tool",
                        content=str(result),
                        timestamp=datetime.now(),
                        tool_call_id=tool_call.id,
                        name=tool_call.function.name,
                    )
                    self.messages.append(tool_message)

                except Exception as e:
                    error_message = f"Tool execution failed: {str(e)}"
                    self.console.print(f"[red]⚠️ {error_message}[/red]")

                    # Add error response to conversation
                    tool_message = Message(
                        role="tool",
                        content=error_message,
                        timestamp=datetime.now(),
                        tool_call_id=tool_call.id,
                        name=tool_call.function.name,
                    )
                    self.messages.append(tool_message)

        # If we've hit max iterations, force a final response
        self.console.print(
            f"[yellow]⚠️ Maximum ReACT iterations ({max_iterations}) reached. Getting final response...[/yellow]"
        )

        messages = self.get_messages_for_api_with_tools()
        final_response = completion(
            model=model,
            messages=messages,
            stream=False,  # No tools for final forced response
        )

        final_text = final_response.choices[0].message.content
        final_message = Message("assistant", final_text, timestamp=datetime.now())
        self.messages.append(final_message)

        # Display final response
        try:
            markdown = Markdown(final_text)
            self.console.print(markdown)
        except Exception:
            self.console.print(final_text)

        return final_text

    def __del__(self):
        """Cleanup when session is destroyed."""

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
                        msgs.append({"role": msg.role, "content": msg.content or ""})
            return msgs
        else:
            return [
                {"role": msg.role, "content": msg.content or ""}
                for msg in self.messages
            ]

    def get_messages_for_api_with_tools(self) -> List[Dict]:
        """Get messages in format needed for API calls including tool calls and responses."""
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
                        msg_dict = {"role": msg.role, "content": msg.content or ""}
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            msg_dict["tool_calls"] = msg.tool_calls
                        if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                            msg_dict["tool_call_id"] = msg.tool_call_id
                        if hasattr(msg, "name") and msg.name:
                            msg_dict["name"] = msg.name
                        msgs.append(msg_dict)
            return msgs
        else:
            msgs = []
            for msg in self.messages:
                msg_dict = {"role": msg.role, "content": msg.content or ""}
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    msg_dict["tool_calls"] = msg.tool_calls
                if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                    msg_dict["tool_call_id"] = msg.tool_call_id
                if hasattr(msg, "name") and msg.name:
                    msg_dict["name"] = msg.name
                msgs.append(msg_dict)
            return msgs

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
