"""
Textual-based chat interface for LoopLM
Provides a sophisticated full-page terminal UI experience
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)
from textual.worker import get_current_worker

from ..config.manager import ConfigManager
from .control import CommandHandler
from .persistence import SessionManager
from .session import ChatSession


class UserPrompt(Markdown):
    """Widget for user prompts - inherits text selection from Markdown"""


class AssistantResponse(Markdown):
    """Widget for assistant responses - inherits text selection from Markdown"""

    BORDER_TITLE = "Assistant"


class SystemMessage(Markdown):
    """Widget for system messages"""

    BORDER_TITLE = "System"


class StreamingResponse(Static):
    """Widget for streaming assistant responses"""

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self.border_title = "Assistant (typing...)"
        self._content = ""

    def stream_content(self, content: str) -> None:
        """Update content as it streams"""
        self._content = content
        self.update(content)

    def finalize(self, final_content: str, token_usage: Optional[Dict] = None):
        """Convert to final response with token usage"""
        usage_text = ""
        if token_usage:
            usage_text = f"\n\n---\n*Tokens: {token_usage.get('total_tokens', 0):,} | Cost: ${token_usage.get('cost', 0):.6f}*"

        final_markdown = Markdown(final_content + usage_text)
        final_markdown.border_title = "Assistant"
        return final_markdown


class SessionNameDialog(Static):
    """Simple dialog for entering session name"""

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static("Enter session name:", classes="dialog-title")
            yield Input(
                placeholder="e.g., 'Python debugging help' or 'API design discussion'",
                id="session-name-input",
            )
            with Horizontal(classes="dialog-buttons"):
                yield Button("Save", id="save-confirm", variant="primary")
                yield Button("Cancel", id="save-cancel")

    @on(Input.Submitted, "#session-name-input")
    async def handle_name_input(self, event: Input.Submitted) -> None:
        """Handle Enter key in session name input"""
        app = self.app
        if hasattr(app, "handle_button_press"):
            # Trigger save action
            save_button = self.query_one("#save-confirm", Button)
            await app.handle_button_press(Button.Pressed(save_button))


class SessionList(Static):
    """Widget for displaying saved sessions"""

    def __init__(self, sessions: List[Dict], **kwargs):
        super().__init__(**kwargs)
        self.sessions = sessions

    def compose(self) -> ComposeResult:
        if not self.sessions:
            yield Static("No saved sessions found", classes="no-sessions")
            return

        yield Static("Saved Sessions", classes="section-header")
        for session in self.sessions:
            updated_at = datetime.fromisoformat(session["updated_at"])
            with Horizontal(classes="session-item"):
                yield Button(
                    f"{session['name'][:30]}...",
                    id=f"load-{session['id']}",
                    classes="session-button",
                )
                yield Static(
                    f"{session['message_count']} msgs | {updated_at.strftime('%m/%d %H:%M')}",
                    classes="session-info",
                )


class ModelSelector(Static):
    """Widget for model selection"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_manager = ConfigManager()

    def compose(self) -> ComposeResult:
        providers = self.config_manager.get_configured_providers()
        default_provider, _ = self.config_manager.get_default_provider()

        yield Static("Model Selection", classes="section-header")

        for provider, config in providers.items():
            provider_name = self.config_manager.get_provider_display_name(
                provider, config
            )
            models = self.config_manager.get_provider_models(provider)

            with Vertical(classes="provider-section"):
                is_default = provider == default_provider
                status = " (DEFAULT)" if is_default else ""
                yield Static(f"{provider_name}{status}", classes="provider-header")

                for model in models:
                    # Sanitize model name for valid widget ID (replace invalid characters)
                    sanitized_model = (
                        model.replace("/", "_").replace(".", "_").replace(":", "_")
                    )
                    yield Button(
                        model,
                        id=f"model-{provider.value}-{sanitized_model}",
                        classes="model-button",
                    )


class LoopLMChat(App):
    """Main Textual chat application"""

    AUTO_FOCUS = "Input"

    CSS = """
    Screen {
        layout: vertical;
    }

    /* User prompts styling */
    UserPrompt {
        background: $primary 10%;
        color: $text;
        margin: 1;
        margin-right: 8;
        padding: 1 2 0 2;
        border: round $primary 50%;
    }

    /* Assistant responses styling */
    AssistantResponse {
        border: wide $success;
        background: $success 10%;
        color: $text;
        margin: 1;
        margin-left: 8;
        padding: 1 2 0 2;
    }

    /* Streaming responses */
    StreamingResponse {
        border: wide $success;
        background: $success 10%;
        color: $text;
        margin: 1;
        margin-left: 8;
        padding: 1 2 0 2;
    }

    /* System messages */
    SystemMessage {
        border: round $warning;
        background: $warning 10%;
        color: $text;
        margin: 1;
        padding: 1 2 0 2;
        text-align: center;
    }

    .chat-container {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }

    .input-container {
        height: auto;
        margin: 0 1;
        padding: 1;
        border: solid $secondary;
    }

    .sidebar {
        width: 30%;
        border: solid $secondary;
        margin: 1 0 1 1;
    }

    .main-chat {
        width: 70%;
        margin: 1 1 1 0;
    }

    .status-bar {
        height: 1;
        background: $accent 20%;
        color: $accent;
        padding: 0 1;
    }

    .input-field {
        width: 1fr;
    }

    .send-button {
        width: auto;
        margin: 0 0 0 1;
    }

    .controls {
        height: auto;
        margin: 1 0 0 0;
    }

    .control-button {
        margin: 0 1 0 0;
    }

    /* Dialog styling */
    .dialog {
        width: 50;
        height: 10;
        background: $surface;
        border: thick $primary;
        padding: 2;
        margin: 4;
    }

    SessionNameDialog {
        dock: top;
        layer: overlay;
        align: center middle;
        background: $surface 90%;
    }

    .dialog-title {
        text-style: bold;
        margin: 0 0 1 0;
    }

    .dialog-buttons {
        height: auto;
        margin: 1 0 0 0;
    }

    .dialog-buttons Button {
        margin: 0 1 0 0;
    }

    /* Session and model styling */
    .section-header {
        text-style: bold;
        color: $accent;
        margin: 0 0 1 0;
        padding: 1;
        background: $accent 20%;
    }

    .session-item {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
    }

    .session-button {
        width: 1fr;
        margin: 0 1 0 0;
    }

    .session-info {
        width: auto;
        color: $text 70%;
        padding: 1 0;
    }

    .no-sessions {
        padding: 2;
        color: $text 50%;
        text-align: center;
    }

    .provider-section {
        margin: 0 0 1 0;
        padding: 1;
        border: solid $secondary 50%;
    }

    .provider-header {
        text-style: bold;
        color: $secondary;
        margin: 0 0 1 0;
    }

    .model-button {
        width: 100%;
        margin: 0 0 1 0;
    }

    Input {
        margin: 0;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_manager = SessionManager()
        self.command_handler = CommandHandler()
        self.config_manager = ConfigManager()
        self.current_session: Optional[ChatSession] = None
        self.streaming_response: Optional[StreamingResponse] = None
        self.show_tokens = False
        self.session_dialog_visible = False
        self.initial_provider = None
        self.initial_model = None

    def compose(self) -> ComposeResult:
        """Compose the main application layout"""
        yield Header(show_clock=True)

        with Horizontal():
            # Main chat area
            with Vertical(classes="main-chat"):
                with VerticalScroll(id="chat-view", classes="chat-container"):
                    yield SystemMessage(
                        "**Welcome to LoopLM Chat**\n\nType your message below or use `/help` for commands"
                    )

                # Status bar
                yield Static("Ready", id="status-bar", classes="status-bar")

                # Input area
                with Horizontal(classes="input-container"):
                    yield Input(
                        placeholder="Ask me anything... (Enter to send, /help for commands)",
                        id="message-input",
                        classes="input-field",
                    )
                    yield Button("Send", id="send-button", variant="primary")

                # Controls
                with Horizontal(classes="controls"):
                    yield Button(
                        "New Session", id="new-session", classes="control-button"
                    )
                    yield Button(
                        "Save Session", id="save-session", classes="control-button"
                    )
                    yield Button("Clear", id="clear-chat", classes="control-button")
                    yield Switch(value=False, id="token-switch")
                    yield Label("Show Tokens")

            # Sidebar
            with TabbedContent(classes="sidebar"):
                with TabPane("Sessions", id="sessions-tab"):
                    yield SessionList([], id="session-list")

                with TabPane("Models", id="models-tab"):
                    yield ModelSelector(id="model-selector")

                with TabPane("Help", id="help-tab"):
                    yield Markdown(self._get_help_text(), id="help-content")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application"""
        self._create_new_session()
        self._refresh_sessions()
        self._update_status("Ready - Type a message to start chatting")

    def _get_help_text(self) -> str:
        """Get help text in markdown format"""
        return """# LoopLM Chat Commands

## Quick Actions
- **Enter** - Send message
- **Ctrl+N** - New session
- **Ctrl+S** - Save session (with custom name)
- **Ctrl+L** - Clear chat

## Session Management
- `/new` - Start a new session
- `/save` - Save current session with custom name
- `/load` - Load a saved session
- `/list` - List saved sessions
- `/delete` - Delete a session
- `/rename` - Rename current session
- `/clear` or `/c` - Clear chat history
- `/clear-last [N]` - Clear last N messages
- `/quit` or `/q` - Exit chat

## System Controls
- `/model` - Change model (use Models tab)
- `/system` - View/update system prompt
- `/usage` - View token usage
- `/help` or `/h` - Show help

## Content Commands
- `@file(path)` - Include file content
- `@folder(path)` - Include folder structure
- `@github(url)` - Include GitHub content
- `@image(path)` - Include image
- `$(command)` - Execute shell command

## UI Features
- **Text Selection** - All code and text in responses can be selected and copied
- **Streaming** - Responses stream in real-time
- **Token Usage** - Toggle token display with the switch
- **Model Switching** - Click model buttons in Models tab to switch
- **Session Management** - Sessions tab shows all saved conversations

## Tips
- Use the sidebar tabs to manage sessions, switch models, or view help
- All responses support full text selection for easy copying
- Token usage and costs are shown when enabled
- Sessions are automatically saved with custom names
"""

    @on(Button.Pressed, "#send-button")
    @on(Input.Submitted, "#message-input")
    async def send_message(self, event) -> None:
        """Handle sending a message"""
        input_widget = self.query_one("#message-input", Input)
        message = input_widget.value.strip()

        if not message:
            return

        input_widget.value = ""

        # Handle commands
        if message.startswith("/"):
            await self._handle_command(message[1:])
            return

        if not self.current_session:
            self._create_new_session()

        # Start the LLM worker
        self.send_to_llm(message)

    async def key_enter(self) -> None:
        """Handle Enter key press - send message"""
        # Check if we're in a dialog
        if self.session_dialog_visible:
            # Handle dialog submission
            await self.handle_button_press(
                Button.Pressed(self.query_one("#save-confirm", Button))
            )
        else:
            # Send message
            await self.send_message(None)

    async def _handle_command(self, cmd: str) -> None:
        """Handle chat commands"""
        chat_messages = self.query_one("#chat-view", VerticalScroll)

        if cmd.lower() in ["help", "h"]:
            await chat_messages.mount(
                SystemMessage("Help command executed - check Help tab")
            )
            chat_messages.scroll_end()

        elif cmd.lower() in ["new"]:
            self._create_new_session()
            await chat_messages.mount(SystemMessage("New session started"))
            chat_messages.scroll_end()

        elif cmd.lower() in ["clear", "c"]:
            if self.current_session:
                # Clear the UI
                chat_messages.remove_children()
                # Clear the session
                self.current_session.clear_history()
                await chat_messages.mount(SystemMessage("Chat history cleared"))
                chat_messages.scroll_end()

        elif cmd.lower() == "save":
            if self.current_session:
                # Show session name dialog
                await self._show_save_dialog()

        elif cmd.lower() == "usage":
            if (
                self.current_session
                and self.current_session.total_usage.total_tokens > 0
            ):
                usage = self.current_session.total_usage
                usage_text = f"""**Token Usage for Current Session**

- Input Tokens: {usage.input_tokens:,}
- Output Tokens: {usage.output_tokens:,}
- Total Tokens: {usage.total_tokens:,}
- Cost: ${usage.cost:.6f}"""

                await chat_messages.mount(SystemMessage(usage_text))
                chat_messages.scroll_end()

        else:
            await chat_messages.mount(SystemMessage(f"Unknown command: {cmd}"))
            chat_messages.scroll_end()

    async def _show_save_dialog(self) -> None:
        """Show dialog to enter session name"""
        if self.session_dialog_visible:
            return

        self.session_dialog_visible = True
        dialog = SessionNameDialog(id="session-dialog")
        await self.mount(dialog)

        # Pre-fill with current name if it's not the default
        name_input = dialog.query_one("#session-name-input", Input)
        if self.current_session and self.current_session.name != "New Chat":
            name_input.value = self.current_session.name
        name_input.focus()

    async def _save_session_with_name(self, name: str) -> None:
        """Save session with given name"""
        if not self.current_session:
            return

        chat_messages = self.query_one("#chat-view", VerticalScroll)

        if name.strip():
            self.current_session.name = name.strip()
        else:
            # Auto-generate name if empty
            self.current_session.name = (
                f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

        if self.session_manager.save_session(self.current_session):
            await chat_messages.mount(
                SystemMessage(
                    f"Session '{self.current_session.name}' saved successfully"
                )
            )
            self._refresh_sessions()
        else:
            await chat_messages.mount(SystemMessage("Failed to save session"))
        chat_messages.scroll_end()

    @work()
    async def send_to_llm(self, message: str) -> None:
        """Send message to LLM with streaming response - using new worker API"""
        if not self.current_session:
            return

        chat_messages = self.query_one("#chat-view", VerticalScroll)

        # Add user message
        user_msg = UserPrompt(message)
        await chat_messages.mount(user_msg)
        chat_messages.scroll_end()

        # Create streaming message widget
        self.streaming_response = StreamingResponse()
        await chat_messages.mount(self.streaming_response)
        chat_messages.scroll_end()

        self._update_status("Generating response...")

        try:
            await self._stream_llm_response(message)
            self._update_status("Ready")

        except Exception as e:
            if self.streaming_response:
                error_response = AssistantResponse(f"Error: {str(e)}")
                await chat_messages.mount(error_response)
                self.streaming_response.remove()
                self.streaming_response = None
            self._update_status(f"Error: {str(e)}")

        chat_messages.scroll_end()

    async def _stream_llm_response(self, message: str) -> None:
        """Handle streaming LLM response with real-time UI updates"""
        from litellm import completion

        from ..commands import CommandManager

        # Process commands in the message
        command_manager = CommandManager(base_path=self.current_session.base_path)
        processed_result = await command_manager.process_text(message)
        processed_content, media_metadata = processed_result

        # Load environment and prepare for API call
        self.current_session.config_manager.load_environment(
            self.current_session.provider.value
        )

        # Add user message to session
        from .session import Message

        user_msg = Message("user", processed_content)
        self.current_session.messages.append(user_msg)

        # Prepare model name (same logic as in session.py)
        if (
            self.current_session.provider.name == "OTHER"
            and self.current_session.custom_provider
        ):
            if not self.current_session.model.startswith(
                f"{self.current_session.custom_provider}/"
            ):
                actual_model = f"{self.current_session.custom_provider}/{self.current_session.model}"
            else:
                actual_model = self.current_session.model
        else:
            from ..config.providers import ProviderType

            provider_prefix = f"{self.current_session.provider.value}/"
            if self.current_session.model.startswith(provider_prefix):
                actual_model = self.current_session.model
            else:
                if self.current_session.provider in [
                    ProviderType.GEMINI,
                    ProviderType.BEDROCK,
                    ProviderType.AZURE,
                ]:
                    actual_model = f"{self.current_session.provider.value}/{self.current_session.model}"
                else:
                    actual_model = self.current_session.model

        # Check if tools are available
        tools_available = (
            self.current_session.tool_manager
            and hasattr(self.current_session.tool_manager, "get_tool_schemas")
            and self.current_session.tool_manager.get_tool_schemas()
        )

        # Get messages for API - use tool-aware version if tools are enabled
        if tools_available:
            messages = self.current_session.get_messages_for_api_with_tools()
        else:
            messages = self.current_session.get_messages_for_api()

        # Handle media (images and PDFs) if needed
        if media_metadata:
            try:
                import litellm
                from litellm.utils import supports_pdf_input

                model_supports_vision = litellm.supports_vision(model=actual_model)
                model_supports_pdf = supports_pdf_input(model=actual_model)

                if (model_supports_vision or model_supports_pdf) and messages:
                    last_message = messages[-1]
                    if last_message["role"] == "user":
                        content_list = [{"type": "text", "text": processed_content}]

                        # Separate media by type and add if supported
                        for media in media_metadata:
                            if (
                                media.get("type") == "image_url"
                                and model_supports_vision
                            ):
                                content_list.append(media)
                            elif media.get("type") == "file_url" and model_supports_pdf:
                                content_list.append(media["file_data"])

                        last_message["content"] = content_list
            except Exception:
                pass

        # Stream the response
        accumulated_text = ""
        timestamp = datetime.now()

        try:
            response = completion(
                model=actual_model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
            )

            final_chunk = None
            chat_messages = self.query_one("#chat-view", VerticalScroll)

            for chunk in response:
                # Check if worker is cancelled
                worker = get_current_worker()
                if worker.is_cancelled:
                    break

                content = chunk.choices[0].delta.content or ""
                if content:
                    accumulated_text += content
                    # Update the streaming widget in real-time
                    if self.streaming_response:
                        self.streaming_response.stream_content(accumulated_text)
                        # Use call_later for smooth UI updates
                        await asyncio.sleep(0.01)

                if hasattr(chunk, "usage") and chunk.usage is not None:
                    final_chunk = chunk

            # Calculate cost
            cost = 0.0
            if final_chunk and hasattr(final_chunk, "usage") and final_chunk.usage:
                try:
                    from litellm import completion_cost

                    cost = completion_cost(final_chunk)
                except Exception:
                    cost = 0.0

            # Create token usage
            from .session import TokenUsage

            if final_chunk and final_chunk.usage:
                token_usage = TokenUsage(
                    input_tokens=final_chunk.usage.prompt_tokens,
                    output_tokens=final_chunk.usage.completion_tokens,
                    total_tokens=final_chunk.usage.prompt_tokens
                    + final_chunk.usage.completion_tokens,
                    cost=cost,
                )
            else:
                token_usage = TokenUsage()

            # Add response to session
            assistant_msg = Message(
                "assistant",
                accumulated_text,
                timestamp=timestamp,
                token_usage=token_usage,
            )
            self.current_session.messages.append(assistant_msg)
            self.current_session._update_total_usage(token_usage)
            self.current_session.latest_response = accumulated_text

            # Replace streaming widget with final response
            if self.streaming_response:
                final_response = self.streaming_response.finalize(
                    accumulated_text,
                    token_usage.to_dict() if self.show_tokens else None,
                )
                await chat_messages.mount(final_response)
                self.streaming_response.remove()
                self.streaming_response = None

        except Exception as e:
            if self.streaming_response:
                error_response = AssistantResponse(f"Error: {str(e)}")
                await chat_messages.mount(error_response)
                self.streaming_response.remove()
                self.streaming_response = None
            raise e

    @on(Button.Pressed)
    async def handle_button_press(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "new-session":
            self._create_new_session()
            self._update_status("New session created")

        elif button_id == "save-session":
            await self._handle_command("save")

        elif button_id == "clear-chat":
            await self._handle_command("clear")

        elif button_id == "save-confirm":
            # Handle session name dialog confirmation
            if self.session_dialog_visible:
                dialog = self.query_one("#session-dialog", SessionNameDialog)
                name_input = dialog.query_one("#session-name-input", Input)
                session_name = name_input.value

                # Remove dialog
                dialog.remove()
                self.session_dialog_visible = False

                # Save session
                await self._save_session_with_name(session_name)

        elif button_id == "save-cancel":
            # Handle session name dialog cancellation
            if self.session_dialog_visible:
                dialog = self.query_one("#session-dialog", SessionNameDialog)
                dialog.remove()
                self.session_dialog_visible = False

        elif button_id and button_id.startswith("load-"):
            session_id = button_id.replace("load-", "")
            await self._load_session(session_id)

        elif button_id and button_id.startswith("model-"):
            # Extract provider and sanitized model from button ID
            parts = button_id.replace("model-", "").split("-", 1)
            if len(parts) == 2:
                provider, sanitized_model = parts
                # Find the original model name by matching the sanitized version
                original_model = self._find_original_model(provider, sanitized_model)
                if original_model:
                    await self._change_model(provider, original_model)

    @on(Switch.Changed, "#token-switch")
    def toggle_tokens(self, event: Switch.Changed) -> None:
        """Toggle token display"""
        self.show_tokens = event.value
        status = "enabled" if self.show_tokens else "disabled"
        self._update_status(f"Token display {status}")

    def _create_new_session(self) -> None:
        """Create a new chat session"""
        self.current_session = ChatSession(base_path=Path.cwd())

        # Set provider and model if specified at startup
        if self.initial_provider or self.initial_model:
            try:
                if self.initial_provider and self.initial_model:
                    self.current_session.set_model(
                        self.initial_model, self.initial_provider
                    )
                elif self.initial_model:
                    # Use default provider with specified model
                    default_provider, _ = self.config_manager.get_default_provider()
                    if default_provider:
                        self.current_session.set_model(
                            self.initial_model, default_provider.value
                        )
                elif self.initial_provider:
                    # Use specified provider with its default model
                    from ..config.providers import ProviderType

                    try:
                        provider_type = ProviderType(self.initial_provider)
                        models = self.config_manager.get_provider_models(provider_type)
                        if models:
                            self.current_session.set_model(
                                models[0], self.initial_provider
                            )
                    except ValueError:
                        # Might be a custom provider
                        providers = self.config_manager.get_configured_providers()
                        other_config = providers.get(ProviderType.OTHER, {})
                        if (
                            other_config
                            and other_config.get("provider_name")
                            == self.initial_provider
                        ):
                            models = self.config_manager.get_provider_models(
                                ProviderType.OTHER
                            )
                            if models:
                                self.current_session.set_model(models[0], "other")
            except Exception as e:
                # If setting fails, just use defaults and show an error
                self._update_status(f"Warning: Could not set provider/model: {str(e)}")

        self.session_manager.active_session = self.current_session

        # Clear chat messages
        chat_messages = self.query_one("#chat-view", VerticalScroll)
        chat_messages.remove_children()

        # Add welcome message with current model info
        provider_info = ""
        if self.current_session.provider and self.current_session.model:
            provider_info = f"\n\nUsing **{self.current_session.model}** from **{self.current_session.provider.value}**"

        welcome_msg = SystemMessage(
            f"**New Chat Session Started**{provider_info}\n\nType your message below or use `/help` for commands"
        )
        self.call_later(chat_messages.mount, welcome_msg)

        self._update_status("New session ready")

    async def _load_session(self, session_id: str) -> None:
        """Load a saved session"""
        try:
            session = self.session_manager.load_session(session_id)
            if session:
                self.current_session = session
                self.session_manager.active_session = session

                # Clear and reload chat messages
                chat_messages = self.query_one("#chat-view", VerticalScroll)
                chat_messages.remove_children()

                # Add all messages from the session
                for msg in session.messages:
                    if msg.role == "user":
                        chat_msg = UserPrompt(msg.content)
                    elif msg.role == "assistant":
                        token_usage = (
                            msg.token_usage.to_dict()
                            if msg.token_usage and self.show_tokens
                            else None
                        )
                        content = msg.content
                        if token_usage:
                            # Add token info to the content
                            usage_text = f"\n\n---\n*Tokens: {token_usage.get('total_tokens', 0):,} | Cost: ${token_usage.get('cost', 0):.6f}*"
                            content += usage_text
                        chat_msg = AssistantResponse(content)
                    else:  # system message
                        if msg.content.strip():  # Only show non-empty system messages
                            chat_msg = SystemMessage(msg.content)
                        else:
                            continue

                    await chat_messages.mount(chat_msg)

                chat_messages.scroll_end()
                self._update_status(f"Loaded session: {session.name}")

        except Exception as e:
            self._update_status(f"Error loading session: {str(e)}")

    async def _change_model(self, provider: str, model: str) -> None:
        """Change the current model"""
        if self.current_session:
            try:
                self.current_session.set_model(model, provider)
                self._update_status(f"Changed to {model} from {provider}")

                # Add system message
                chat_messages = self.query_one("#chat-view", VerticalScroll)
                await chat_messages.mount(
                    SystemMessage(f"Model changed to **{model}** from **{provider}**")
                )
                chat_messages.scroll_end()

            except Exception as e:
                self._update_status(f"Error changing model: {str(e)}")

    def _refresh_sessions(self) -> None:
        """Refresh the sessions list"""
        try:
            sessions = self.session_manager.get_session_list()

            # Find and replace the session list widget
            try:
                session_list = self.query_one("#session-list", SessionList)
                session_list.remove()
            except NoMatches:
                pass

            # Create new session list
            new_session_list = SessionList(sessions, id="session-list")
            sessions_tab = self.query_one("#sessions-tab", TabPane)
            self.call_later(sessions_tab.mount, new_session_list)
        except Exception as e:
            # If refresh fails, just continue - don't crash the app
            self._update_status(f"Warning: Could not refresh sessions list: {str(e)}")

    def _find_original_model(
        self, provider_name: str, sanitized_model: str
    ) -> Optional[str]:
        """Find the original model name from a sanitized version"""
        try:
            from ..config.providers import ProviderType

            provider = ProviderType(provider_name)
            models = self.config_manager.get_provider_models(provider)

            for model in models:
                sanitized = model.replace("/", "_").replace(".", "_").replace(":", "_")
                if sanitized == sanitized_model:
                    return model
        except Exception:
            pass
        return None

    def _update_status(self, message: str) -> None:
        """Update the status bar"""
        try:
            status_bar = self.query_one("#status-bar", Static)
            status_bar.update(message)
        except NoMatches:
            pass

    async def key_ctrl_n(self) -> None:
        """Handle Ctrl+N - New session"""
        self._create_new_session()
        self._update_status("New session created (Ctrl+N)")

    async def key_ctrl_s(self) -> None:
        """Handle Ctrl+S - Save session"""
        if self.current_session:
            await self._show_save_dialog()

    async def key_ctrl_l(self) -> None:
        """Handle Ctrl+L - Clear chat"""
        await self._handle_command("clear")

    async def key_escape(self) -> None:
        """Handle Escape key - close dialogs"""
        if self.session_dialog_visible:
            dialog = self.query_one("#session-dialog", SessionNameDialog)
            dialog.remove()
            self.session_dialog_visible = False


def run_textual_chat(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    debug: bool = False,
) -> None:
    """Run the Textual chat interface"""
    app = LoopLMChat()

    # Set initial provider and model if specified
    if provider or model:
        app.initial_provider = provider
        app.initial_model = model

    app.run()
