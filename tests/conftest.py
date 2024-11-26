# tests/conftest.py
import pytest
from rich.console import Console
from looplm.config.manager import ConfigManager
from looplm.conversation.handler import ConversationHandler


@pytest.fixture
def mock_console():
    """Provides a Rich console for testing"""
    return Console(force_terminal=True, width=80)


@pytest.fixture
def config_manager(tmp_path):
    """Provides a ConfigManager instance with temporary path"""
    import os

    os.environ["HOME"] = str(tmp_path)
    return ConfigManager()


@pytest.fixture
def conversation_handler(mock_console):
    """Provides a ConversationHandler instance"""
    return ConversationHandler(mock_console)
