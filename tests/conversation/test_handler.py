"""Tests for the conversation handler."""

import os
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from looplm.config.providers import ProviderType
from looplm.conversation.handler import ConversationHandler


@pytest.fixture
def mock_config_manager():
    """Mock the ConfigManager."""
    with patch("looplm.conversation.handler.ConfigManager") as mock:
        manager = MagicMock()
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_command_manager():
    """Mock the CommandManager."""
    with patch("looplm.conversation.handler.CommandManager") as mock:
        manager = MagicMock()
        mock.return_value = manager
        yield manager


@pytest.fixture
def handler(mock_config_manager, mock_command_manager):
    """Create a ConversationHandler instance with mocked dependencies."""
    return ConversationHandler(console=Console(width=80))


@pytest.mark.unit
def test_init_without_console():
    """Test initialization without providing a console."""
    handler = ConversationHandler()
    assert handler.console is not None
    assert handler.console.width == 80


@pytest.mark.unit
def test_init_with_console():
    """Test initialization with a provided console."""
    console = Console(width=80)
    handler = ConversationHandler(console=console)
    assert handler.console == console
    assert handler.console.width == 80


@pytest.mark.unit
def test_get_provider_config(handler, mock_config_manager):
    """Test getting provider configuration."""
    mock_config_manager.get_configured_providers.return_value = {
        ProviderType.OPENAI: {"api_key": "test_key"}
    }

    config = handler._get_provider_config(ProviderType.OPENAI)
    assert config == {"api_key": "test_key"}

    # Test with invalid provider
    with pytest.raises(ValueError, match="Provider anthropic is not configured"):
        handler._get_provider_config(ProviderType.ANTHROPIC)


@pytest.mark.unit
def test_setup_environment(handler, mock_config_manager):
    """Test setting up environment variables."""
    mock_config_manager.get_provider_credentials.return_value = {
        "OPENAI_API_KEY": "test_key"
    }

    handler._setup_environment(ProviderType.OPENAI)
    assert os.environ["OPENAI_API_KEY"] == "test_key"


@pytest.mark.unit
def test_get_provider_and_model_with_provider(handler, mock_config_manager):
    """Test getting provider and model with provider specified."""
    mock_config_manager.get_configured_providers.return_value = {
        ProviderType.OPENAI: {"default_model": "gpt-4", "provider_name": "OpenAI"}
    }

    provider, model, custom_name = handler._get_provider_and_model(
        provider_name="openai", model_name="gpt-3.5-turbo"
    )
    assert provider == ProviderType.OPENAI
    assert model == "gpt-3.5-turbo"
    assert custom_name is None


@pytest.mark.unit
def test_get_provider_and_model_without_provider(handler, mock_config_manager):
    """Test getting provider and model without provider specified."""
    mock_config_manager.get_default_provider.return_value = (
        ProviderType.OPENAI,
        "gpt-4",
    )
    mock_config_manager.get_configured_providers.return_value = {
        ProviderType.OPENAI: {"default_model": "gpt-4", "provider_name": "OpenAI"}
    }

    provider, model, custom_name = handler._get_provider_and_model()
    assert provider == ProviderType.OPENAI
    assert model == "gpt-4"
    assert custom_name is None


@pytest.mark.unit
def test_handle_prompt_debug_mode(handler, mock_command_manager):
    """Test handling prompt in debug mode."""
    handler.debug = True
    mock_command_manager.process_text_sync.return_value = (
        "processed content",
        [{"type": "image", "url": "test.jpg"}],
    )

    handler.handle_prompt("test prompt")
    mock_command_manager.process_text_sync.assert_called_once_with("test prompt")
