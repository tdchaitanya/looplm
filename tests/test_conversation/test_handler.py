# tests/test_conversation/test_handler.py
import pytest
from unittest.mock import patch

# def test_conversation_handler_environment_setup(conversation_handler):
#     """Test environment setup for conversation"""
#     with patch('os.environ') as mock_environ:
#         mock_environ.keys.return_value = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']
#         conversation_handler._setup_environment(provider='anthropic')
#         # Check that old credentials were cleared
#         assert 'OPENAI_API_KEY' not in mock_environ


def test_conversation_handler_error(conversation_handler, mock_console):
    """Test error handling in conversation handler"""
    with patch("looplm.conversation.handler.completion") as mock_completion:
        mock_completion.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            conversation_handler.handle_prompt("Test prompt")

        assert "API Error" in str(exc_info.value)
