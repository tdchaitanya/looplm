"""Tests for the command manager."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from looplm.commands.manager import CommandManager
from looplm.commands.processor import CommandProcessor


class MockProcessor(CommandProcessor):
    """Mock command processor for testing."""

    command = "mock"

    async def process(self, text: str) -> tuple[str, list[dict]]:
        return f"processed: {text}", []


@pytest.fixture
def mock_registry():
    """Mock the CommandRegistry."""
    with patch("looplm.commands.manager.CommandRegistry") as mock:
        registry = MagicMock()
        mock.return_value = registry
        yield registry


@pytest.fixture
def manager(mock_registry):
    """Create a CommandManager instance with mocked registry."""
    return CommandManager(base_path=Path.cwd())


@pytest.mark.unit
def test_singleton_pattern():
    """Test that CommandManager follows singleton pattern."""
    manager1 = CommandManager()
    manager2 = CommandManager()
    assert manager1 is manager2


@pytest.mark.unit
def test_init_with_base_path():
    """Test initialization with base path."""
    # Reset the singleton instance
    CommandManager._instance = None
    CommandManager._initialized = False

    base_path = Path("/test/path")
    with patch("looplm.commands.manager.CommandRegistry") as mock_registry:
        registry = MagicMock()
        mock_registry.return_value = registry

        manager = CommandManager(base_path=base_path)
        assert manager.base_path == base_path
        mock_registry.assert_called_once_with(base_path=base_path)
        assert manager.registry == registry


@pytest.mark.unit
def test_register_command(manager, mock_registry):
    """Test registering a custom command."""
    # Reset the mock to clear any previous calls
    mock_registry.reset_mock()
    manager.register_command(MockProcessor)
    mock_registry.register.assert_called_once_with(MockProcessor)


@pytest.mark.unit
def test_get_processor(manager, mock_registry):
    """Test getting a processor by name."""
    mock_processor = MagicMock()
    mock_registry.get_processor.return_value = mock_processor

    processor = manager.get_processor("test")
    assert processor == mock_processor
    mock_registry.get_processor.assert_called_once_with("test")


@pytest.mark.unit
def test_get_available_commands(manager, mock_registry):
    """Test getting list of available commands."""
    mock_registry._processors = {"file": MagicMock(), "folder": MagicMock()}

    commands = manager.get_available_commands()
    assert set(commands) == {"file", "folder", "shell"}


@pytest.mark.asyncio
async def test_process_text(manager, mock_registry):
    """Test processing text asynchronously."""

    async def mock_process():
        return ("processed", [])

    mock_registry.process_text.return_value = mock_process()

    result = await manager.process_text("test")
    assert result == ("processed", [])
    mock_registry.process_text.assert_called_once_with("test")


@pytest.mark.unit
def test_process_text_sync(manager, mock_registry):
    """Test processing text synchronously."""

    async def mock_process():
        return ("processed", [])

    mock_registry.process_text.return_value = mock_process()

    result = manager.process_text_sync("test")
    assert result == ("processed", [])
    mock_registry.process_text.assert_called_once_with("test")


@pytest.mark.unit
def test_process_text_sync_new_loop(manager, mock_registry):
    """Test processing text synchronously with new event loop."""
    # Simulate no existing event loop
    with patch("asyncio.get_event_loop", side_effect=RuntimeError):

        async def mock_process():
            return ("processed", [])

        mock_registry.process_text.return_value = mock_process()

        result = manager.process_text_sync("test")
        assert result == ("processed", [])
        mock_registry.process_text.assert_called_once_with("test")
