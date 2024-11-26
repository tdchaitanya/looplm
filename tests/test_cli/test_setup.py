# tests/test_cli/test_setup.py
import pytest
from unittest.mock import patch, MagicMock
from looplm.cli.setup import setup_provider
from looplm.config.providers import ProviderType


@pytest.fixture
def mock_prompt_responses():
    """Mock user responses to prompts"""
    return {
        "Enter your ANTHROPIC_API_KEY": "test-key",
        "Enter default model name": "claude-3-opus-20240229",
        "Would you like to configure another provider?": False,
    }


@patch("looplm.cli.setup.Prompt.ask")
@patch("looplm.cli.setup.Confirm.ask")
def test_setup_provider(mock_confirm, mock_prompt):
    """Test provider setup process"""
    # Create mock config manager
    mock_config = MagicMock()
    mock_config.validate_provider_setup.return_value = True

    # Set up prompt responses
    mock_prompt.side_effect = ["test-key", "claude-3-opus-20240229"]
    mock_confirm.return_value = False

    # Mock the ConfigManager to return empty list of configured providers
    mock_config.get_configured_providers.return_value = {}

    result = setup_provider(ProviderType.ANTHROPIC, mock_config)
    assert result is True

    # Verify save_provider_config was called correctly
    # The actual implementation uses positional args, not keyword args
    mock_config.save_provider_config.assert_called_once_with(
        ProviderType.ANTHROPIC,
        "claude-3-opus-20240229",
        {"ANTHROPIC_API_KEY": "test-key"},
        is_default=True,  # First provider is set as default
    )


@patch("looplm.cli.setup.Prompt.ask")
@patch("looplm.cli.setup.Confirm.ask")
def test_setup_provider_not_first(mock_confirm, mock_prompt):
    """Test provider setup when it's not the first provider"""
    mock_config = MagicMock()
    mock_config.validate_provider_setup.return_value = True

    # Mock that we already have a provider configured
    mock_config.get_configured_providers.return_value = {
        ProviderType.OPENAI: {"default_model": "gpt-4"}
    }

    mock_prompt.side_effect = ["test-key", "claude-3-opus-20240229"]
    mock_confirm.return_value = False

    result = setup_provider(ProviderType.ANTHROPIC, mock_config)
    assert result is True

    mock_config.save_provider_config.assert_called_once_with(
        ProviderType.ANTHROPIC,
        "claude-3-opus-20240229",
        {"ANTHROPIC_API_KEY": "test-key"},
        is_default=False,  # Not first provider, so not default
    )
