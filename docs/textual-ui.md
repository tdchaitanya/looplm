# Textual Chat UI

LoopLM now supports a sophisticated full-page Terminal User Interface (TUI) powered by [Textual](https://textual.textualize.io/). This provides a modern, interactive chat experience with advanced features.

## Features

### 🎨 Modern Interface
- **Full-page TUI**: Takes advantage of your entire terminal space
- **Real-time streaming**: See responses as they're generated, character by character
- **Syntax highlighting**: Built-in markdown rendering for code and formatted text
- **Responsive layout**: Adapts to different terminal sizes

### 📱 Intuitive Layout
- **Main chat area**: Scrollable conversation history with clear role indicators
- **Sidebar tabs**:
  - **Sessions**: Browse and load saved conversations
  - **Models**: Quick model switching with provider information
  - **Help**: Built-in command reference
- **Status bar**: Shows current operation status
- **Control panel**: Quick access to common actions

### ⚡ Enhanced Experience
- **Live streaming**: Watch responses appear in real-time
- **Smart scrolling**: Automatically follows new messages
- **Token display**: Optional real-time token usage and cost tracking
- **Error handling**: Graceful error display and recovery

## Getting Started

### Launch Textual Chat

```bash
# Start with the new Textual interface
looplm chat --ui textual

# Use with specific provider
looplm chat --ui textual --provider anthropic

# Use with specific model
looplm chat --ui textual --provider openai --model gpt-4o
```

### Traditional Rich Interface

```bash
# Use the original Rich console interface (default)
looplm chat
# or explicitly
looplm chat --ui rich
```

## Interface Guide

### Main Chat Area (70% width)
- **Message History**: Scrollable conversation with timestamps
- **Role Indicators**:
  - 🔵 **User** messages with blue header
  - 🟢 **Assistant** responses with green header
  - 🟡 **System** messages with yellow header
- **Live Streaming**: Real-time response generation
- **Markdown Rendering**: Code blocks, lists, and formatting

### Sidebar (30% width)

#### Sessions Tab
- **Browse Sessions**: List all saved conversations
- **Quick Load**: Click to load any session
- **Session Info**: Message count and last updated time
- **Auto-refresh**: Updates when new sessions are saved

#### Models Tab
- **Provider Groups**: Organized by provider with default indicators
- **One-click Switching**: Change models instantly
- **Current Status**: Shows which provider/model is active

#### Help Tab
- **Command Reference**: Complete list of chat commands
- **Keyboard Shortcuts**: Quick reference for key bindings
- **Usage Examples**: Learn how to use advanced features

### Control Panel
- **New Session**: Start fresh conversation
- **Save Session**: Persist current chat
- **Clear Chat**: Remove message history
- **Token Toggle**: Show/hide usage information

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Ctrl+C` | Exit application |
| `Tab` | Navigate between interface elements |
| `Shift+Tab` | Navigate backwards |
| `Page Up/Down` | Scroll chat history |
| `Home/End` | Jump to start/end of chat |

## Chat Commands

All traditional LoopLM commands work in the Textual interface:

### Session Management
- `/new` - Start a new session
- `/save` - Save current session
- `/clear` - Clear chat history
- `/usage` - View token usage

### Content Integration
- `@file(path)` - Include file content
- `@folder(path)` - Include folder structure
- `@github(url)` - Include GitHub content
- `@image(path)` - Include image (if model supports vision)
- `$(command)` - Execute shell command

### System Control
- `/model` - Change model (also available via sidebar)
- `/help` - Show help (also available in Help tab)

## Advanced Features

### Real-time Streaming
The Textual interface provides true real-time streaming where you can see each character as it's generated by the AI model. This creates a more engaging and responsive experience.

### Session Management
- **Auto-save**: Sessions are automatically tracked
- **Quick switching**: Load any previous conversation instantly
- **Visual indicators**: See message counts and timestamps at a glance

### Token Tracking
Enable token display to see:
- Input tokens used
- Output tokens generated
- Total token count
- Estimated cost per interaction

### Multi-provider Support
Switch between providers and models seamlessly:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude models)
- Google (Gemini models)
- Groq (fast inference)
- Custom providers

## Comparison: Rich vs Textual

| Feature | Rich Console | Textual TUI |
|---------|-------------|-------------|
| **Interface** | Line-by-line | Full-page |
| **Streaming** | Block updates | Character-by-character |
| **Navigation** | Scroll up only | Full scrolling |
| **Session Management** | Command-based | Visual + commands |
| **Model Switching** | Command-based | One-click sidebar |
| **Multitasking** | Sequential | Parallel UI updates |
| **Learning Curve** | Familiar | Modern app-like |

## Tips for Best Experience

1. **Terminal Size**: Use a reasonably large terminal (at least 120x30) for optimal layout
2. **Color Support**: Ensure your terminal supports 256 colors for best visual experience
3. **Font**: Use a monospace font with good Unicode support
4. **Keyboard**: Learn the shortcuts for faster navigation
5. **Sessions**: Use session names that help you remember the context

## Troubleshooting

### Common Issues

**Textual not found**
```bash
# Install missing dependency
poetry install
# or manually
pip install textual
```

**Layout issues**
- Increase terminal size
- Check terminal's color support
- Try different terminal emulator

**Slow performance**
- Disable token display if not needed
- Clear old sessions periodically
- Check network connection for streaming

### Fallback to Rich
If you encounter issues with the Textual interface, you can always fall back to the traditional Rich interface:

```bash
looplm chat --ui rich
```

## Future Enhancements

The Textual interface is actively developed. Upcoming features include:
- **Themes**: Dark/light mode and custom color schemes
- **Search**: Find messages across conversation history
- **Export**: Save conversations in various formats
- **Plugins**: Extensible UI components
- **Multi-session**: Handle multiple conversations simultaneously

---

*The Textual interface represents the future of LoopLM's chat experience, providing a modern, efficient, and enjoyable way to interact with language models.*
