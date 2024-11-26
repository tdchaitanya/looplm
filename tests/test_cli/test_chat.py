# tests/test_cli/test_chat.py
from unittest.mock import patch
from click.testing import CliRunner
from looplm.cli.chat import chat


def test_chat_success():
    """Test successful chat command"""
    with patch("looplm.cli.chat.ConversationHandler") as mock_handler:
        runner = CliRunner()
        result = runner.invoke(chat, ["test prompt"])
        assert result.exit_code == 0
        mock_handler.return_value.handle_prompt.assert_called_once_with(
            "test prompt", None
        )


def test_chat_with_model():
    """Test chat command with model override"""
    with patch("looplm.cli.chat.ConversationHandler") as mock_handler:
        runner = CliRunner()
        result = runner.invoke(chat, ["test prompt", "--model", "gpt-4"])
        assert result.exit_code == 0
        mock_handler.return_value.handle_prompt.assert_called_once_with(
            "test prompt", "gpt-4"
        )


def test_chat_error():
    """Test chat command error handling"""
    with patch("looplm.cli.chat.ConversationHandler") as mock_handler:
        mock_handler.return_value.handle_prompt.side_effect = Exception("API Error")
        runner = CliRunner()
        result = runner.invoke(chat, ["test prompt"])
        assert result.exit_code != 0
        assert "Failed to process request: API Error" in result.output
