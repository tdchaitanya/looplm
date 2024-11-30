import asyncio
from ..config.manager import ConfigManager
from ..conversation.handler import ConversationHandler

class InteractiveShell:
    """
    Interactive shell mode for looplm.
    This shell wraps bash functionality while adding LLM capabilities. It maintains
    full bash compatibility while providing additional features for LoopLM based assistance.
    """
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the interactive shell

        Args:
            config_manager: Optional ConfigManager instance. If not provided,
                            a new one will be created
        """
        self.config_manager = config_manager or ConfigManager()
        self.console = Console()
        self.session_id = str(uuid.uuid4)
        self.setup_session_directories()
        self.setup_prompt_session()




    def setup_session_directories(self) -> None:
        """Setup a directory structure ofr the interactive session."""
        base_dir = Path.home() / ".looplm"
        self.session_dir = base_dir / "sessions" / "active" / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Create sub-directories
        (self.session_dir / "context").mkdir(exist_ok=True)
        (self.session_dir / "logs").mkdir(exist_ok=True)

        # Set up a history file
        self.history_file = base_dir / "history" / "shell_history"
        self.history_file.parent.mkdir(exist_ok=True)
        self.history_file.touch(exist_ok=True)

    def setup_prompt_session(self) -> None:
        """Configure the prompt session with history and autosuggestions."""
        self.session = PromptSession(
            history=FileHistory(str(self.history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            complete_in_thread=True, wrap_lines=True, mouse_support=True, multiline=True
        )