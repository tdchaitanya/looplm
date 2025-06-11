"""Tests for the main CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from looplm.cli.main import get_input_from_pipe, process_input


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_config_manager():
    """Mock the ConfigManager."""
    with patch("looplm.cli.main.ConfigManager", autospec=True) as mock:
        manager = MagicMock()
        manager.get_configured_providers.return_value = {
            "openai": {"provider_name": "OpenAI", "default_model": "gpt-3.5-turbo"}
        }
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_conversation_handler():
    """Mock the ConversationHandler."""
    with patch("looplm.cli.main.ConversationHandler", autospec=True) as mock:
        handler = MagicMock()
        mock.return_value = handler
        yield handler


@pytest.mark.unit
def test_get_input_from_pipe():
    """Test getting input from pipe."""
    # Test when stdin is not a tty
    with patch("sys.stdin.isatty", return_value=False):
        with patch("sys.stdin.read", return_value="piped input"):
            assert get_input_from_pipe() == "piped input"

    # Test when stdin is a tty
    with patch("sys.stdin.isatty", return_value=True):
        assert get_input_from_pipe() == ""


@pytest.mark.unit
def test_process_input():
    """Test processing input from arguments and pipe."""
    # Test with piped input
    assert process_input(("arg1", "arg2"), "piped input") == "piped input"

    # Test with args
    assert process_input(("arg1", "arg2")) == "arg1 arg2"

    # Test with empty input
    assert process_input(()) == ""


# @pytest.mark.unit
# def test_cli_configure(runner, mock_config_manager):
#     """Test the configure command."""
#     with patch("looplm.cli.main.initial_setup", autospec=True) as mock_setup:
#         mock_setup.return_value = True
#         result = runner.invoke(cli, ["--configure"])
#         assert result.exit_code == 0
#         mock_setup.assert_called_once()


# @pytest.mark.unit
# def test_cli_reset(runner, mock_config_manager):
#     """Test the reset command."""
#     mock_config_manager.reset_all.return_value = True
#     with patch("click.confirm", return_value=True):
#         result = runner.invoke(cli, ["--reset"])
#         assert result.exit_code == 0
#         mock_config_manager.reset_all.assert_called_once()


# @pytest.mark.unit
# def test_cli_reset_provider(runner, mock_config_manager):
#     """Test the reset-provider command."""
#     mock_config_manager.get_configured_providers.return_value = {
#         "openai": {"provider_name": "OpenAI"},
#         "other": {"provider_name": "Custom Provider"}
#     }
#     mock_config_manager.reset_provider.return_value = True

#     with patch("click.confirm", return_value=True):
#         # Test with valid provider
#         result = runner.invoke(cli, ["--reset-provider", "openai"])
#         assert result.exit_code == 0
#         mock_config_manager.reset_provider.assert_called_once_with(ProviderType.OPENAI)

#         # Test with invalid provider
#         result = runner.invoke(cli, ["--reset-provider", "invalid"])
#         assert result.exit_code == 0
#         assert "Invalid provider" in result.output


# @pytest.mark.unit
# def test_cli_status(runner, mock_config_manager):
#     """Test the status command."""
#     result = runner.invoke(cli, ["--status"])
#     assert result.exit_code == 0


# @pytest.mark.unit
# def test_cli_prompt(runner, mock_conversation_handler, mock_config_manager):
#     """Test handling a prompt."""
#     mock_conversation_handler.handle_prompt.return_value = "test response"
#     result = runner.invoke(cli, ["test prompt"])
#     assert result.exit_code == 0
#     mock_conversation_handler.handle_prompt.assert_called_once_with(
#         "test prompt", provider=None, model=None
#     )


# @pytest.mark.unit
# def test_cli_chat_mode(runner, mock_config_manager):
#     """Test chat mode."""
#     with patch("looplm.cli.main.CommandHandler", autospec=True) as mock_handler:
#         handler = MagicMock()
#         mock_handler.return_value = handler
#         session = MagicMock()
#         handler.session_manager.active_session = session
#         session.send_message.return_value = "test response"

#         result = runner.invoke(cli, ["chat", "test message"])
#         assert result.exit_code == 0
#         session.send_message.assert_called_once_with(
#             ("chat", "test message"), stream=True, show_tokens=False
#         )


# @pytest.mark.unit
# def test_cli_error_handling(runner, mock_conversation_handler, mock_config_manager):
#     """Test error handling in CLI."""
#     mock_conversation_handler.handle_prompt.side_effect = Exception("Test error")
#     result = runner.invoke(cli, ["test prompt"])
#     assert result.exit_code == 1
#     assert "Test error" in result.output
