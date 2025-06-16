from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from looplm.chat.compact_handler import CompactError, CompactHandler
from looplm.chat.prompt_manager import PromptManager
from looplm.chat.session import ChatSession, Message


@pytest.fixture
def mock_console():
    console = Mock()
    # Mock the underlying Rich console
    console.console = Mock(spec=Console)
    # Mock ChatConsole methods
    console.display_error = Mock()
    console.display_success = Mock()
    console.display_info = Mock()
    return console


@pytest.fixture
def mock_prompt_manager():
    """Mock prompt manager"""
    pm = Mock(spec=PromptManager)
    pm.get_prompt.return_value = "Please summarize this conversation."
    return pm


@pytest.fixture
def compact_handler(mock_console, mock_prompt_manager):
    return CompactHandler(mock_console, mock_prompt_manager)


@pytest.fixture
def sample_session():
    session = ChatSession()
    session.set_system_prompt("You are LoopLM, a helpful assistant.")
    session.messages.append(
        Message("user", "How do I use the API?", timestamp=datetime.now())
    )
    session.messages.append(
        Message("assistant", "You can use the API by ...", timestamp=datetime.now())
    )
    session.messages.append(
        Message("user", "Show me an example.", timestamp=datetime.now())
    )
    session.messages.append(
        Message("assistant", "Here is an example: ...", timestamp=datetime.now())
    )
    return session


class TestCompactHandler:
    def test_can_compact_valid_session(self, compact_handler, sample_session):
        can_compact, reason = compact_handler.can_compact(sample_session)
        assert can_compact is True
        assert reason == "Session can be compacted"

    def test_can_compact_no_session(self, compact_handler):
        can_compact, reason = compact_handler.can_compact(None)
        assert can_compact is False
        assert reason == "No active session"

    def test_can_compact_already_compacted(self, compact_handler, sample_session):
        sample_session.set_compact_summary("Test summary")
        can_compact, reason = compact_handler.can_compact(sample_session)
        assert can_compact is False
        assert reason == "Session is already compacted"

    def test_can_compact_not_enough_messages(self, compact_handler):
        session = ChatSession()
        session.set_system_prompt("Test prompt")
        session.messages.append(
            Message("user", "Single message", timestamp=datetime.now())
        )

        can_compact, reason = compact_handler.can_compact(session)
        assert can_compact is False
        assert "Not enough messages" in reason

    def test_get_compact_stats(self, compact_handler, sample_session):
        stats = compact_handler.get_compact_stats(sample_session)

        assert stats["total_messages"] == 5  # 1 system + 4 user/assistant
        assert stats["non_system_messages"] == 4
        assert stats["estimated_current_tokens"] > 0
        assert stats["system_prompt"] is True

    def test_get_compact_stats_no_session(self, compact_handler):
        stats = compact_handler.get_compact_stats(None)
        assert stats == {}

    def test_resolve_model_name_regular_provider(self, compact_handler, sample_session):
        from looplm.config.providers import ProviderType

        sample_session.provider = ProviderType.OPENAI
        sample_session.model = "gpt-4"

        model_name = compact_handler._resolve_model_name(sample_session)
        assert model_name == "gpt-4"

    def test_resolve_model_name_custom_provider(self, compact_handler, sample_session):
        from looplm.config.providers import ProviderType

        sample_session.provider = ProviderType.OTHER
        sample_session.custom_provider = "custom"
        sample_session.model = "custom-model"

        model_name = compact_handler._resolve_model_name(sample_session)
        assert model_name == "custom/custom-model"

    def test_prepare_compact_messages(
        self, compact_handler, sample_session, mock_prompt_manager
    ):
        mock_prompt_manager.get_prompt.return_value = (
            "Please summarize this conversation."
        )

        messages = compact_handler._prepare_compact_messages(sample_session)

        # Should have: system + 4 conversation messages + compact prompt
        assert len(messages) == 6
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Please summarize this conversation."

    @patch("looplm.chat.compact_handler.completion")
    def test_compact_session_success(
        self, mock_completion, compact_handler, sample_session, mock_console
    ):
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a test summary."
        mock_completion.return_value = mock_response

        result = compact_handler.compact_session(sample_session, show_progress=False)

        assert result is True
        assert sample_session.is_compacted is True
        assert sample_session.compact_summary == "This is a test summary."
        mock_console.display_success.assert_called()

    def test_compact_session_cannot_compact(self, compact_handler, mock_console):
        session = ChatSession()  # Empty session

        result = compact_handler.compact_session(session)

        assert result is False
        mock_console.display_error.assert_called_with(
            "Cannot compact session: Not enough messages to compact (need at least 2 non-system messages)"
        )

    @patch("looplm.chat.compact_handler.completion")
    def test_compact_session_llm_error(
        self, mock_completion, compact_handler, sample_session, mock_console
    ):
        mock_completion.side_effect = Exception("LLM Error")

        result = compact_handler.compact_session(sample_session, show_progress=False)

        assert result is False
        assert not sample_session.is_compacted

    def test_reset_compact_success(self, compact_handler, sample_session, mock_console):
        sample_session.set_compact_summary("Test summary")

        result = compact_handler.reset_compact(sample_session)

        assert result is True
        assert not sample_session.is_compacted
        mock_console.display_success.assert_called_with(
            "✓ Compact state reset. Full conversation history will be used."
        )

    def test_reset_compact_not_compacted(
        self, compact_handler, sample_session, mock_console
    ):
        result = compact_handler.reset_compact(sample_session)

        assert result is True
        mock_console.display_info.assert_called_with(
            "Session is not currently compacted", "yellow"
        )

    def test_reset_compact_no_session(self, compact_handler, mock_console):
        result = compact_handler.reset_compact(None)

        assert result is False
        mock_console.display_error.assert_called_with("No active session")

    def test_show_compact_info_normal_session(
        self, compact_handler, sample_session, mock_console
    ):
        compact_handler.show_compact_info(sample_session)

        # Should print compact information via console.console.print
        calls = mock_console.console.print.call_args_list
        assert any("Compact Information" in str(call) for call in calls)
        assert any("Not compacted" in str(call) for call in calls)

    def test_show_compact_info_compacted_session(
        self, compact_handler, sample_session, mock_console
    ):
        sample_session.set_compact_summary("Test summary")

        compact_handler.show_compact_info(sample_session)

        calls = mock_console.console.print.call_args_list
        assert any("Compact Information" in str(call) for call in calls)
        assert any("Compacted" in str(call) for call in calls)

    def test_show_compact_info_no_session(self, compact_handler, mock_console):
        compact_handler.show_compact_info(None)

        mock_console.display_error.assert_called_with("No active session")

    def test_call_llm_for_summary_success(self, compact_handler):
        with patch("looplm.chat.compact_handler.completion") as mock_completion:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test summary"
            mock_completion.return_value = mock_response

            result = compact_handler._call_llm_for_summary("test-model", [])

            assert result == "Test summary"

    def test_call_llm_for_summary_empty_response(self, compact_handler):
        with patch("looplm.chat.compact_handler.completion") as mock_completion:
            mock_response = Mock()
            mock_response.choices = []
            mock_completion.return_value = mock_response

            with pytest.raises(CompactError, match="Empty response from LLM"):
                compact_handler._call_llm_for_summary("test-model", [])

    def test_call_llm_for_summary_llm_error(self, compact_handler):
        with patch("looplm.chat.compact_handler.completion") as mock_completion:
            mock_completion.side_effect = Exception("Network error")

            with pytest.raises(CompactError, match="LLM call failed"):
                compact_handler._call_llm_for_summary("test-model", [])
