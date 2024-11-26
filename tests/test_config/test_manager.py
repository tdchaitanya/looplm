# tests/test_config/test_manager.py
import pytest
from looplm.config.providers import ProviderType


def test_config_manager_initialization(config_manager, tmp_path):
    """Test ConfigManager initialization creates necessary files"""
    assert (tmp_path / ".looplm").exists()
    assert (tmp_path / ".looplm" / "config.json").exists()
    assert (tmp_path / ".looplm" / "secrets.enc").exists()


def test_save_config_io_error(config_manager, tmp_path):
    """Test save_config with IO error"""
    import os

    config_file = tmp_path / ".looplm" / "config.json"
    os.chmod(config_file.parent, 0o444)  # Make directory read-only

    with pytest.raises(IOError):
        config_manager.save_config({"test": "data"})


def test_validate_provider_setup_error(config_manager):
    """Test provider validation with error"""
    result = config_manager.validate_provider_setup(
        provider=ProviderType.ANTHROPIC.value,
        model_name="invalid-model",
        env_vars={"ANTHROPIC_API_KEY": "invalid-key"},
    )
    assert result is False


def test_reset_provider_invalid(config_manager):
    """Test resetting unconfigured provider"""
    config_manager.reset_provider(ProviderType.ANTHROPIC)
    # Should not raise an exception


def test_encryption_roundtrip(config_manager):
    """Test encryption/decryption of secrets"""
    test_secrets = {"key": "secret-value"}
    config_manager.save_secrets(test_secrets)
    loaded_secrets = config_manager.load_secrets()
    assert loaded_secrets == test_secrets


def test_load_corrupted_secrets(config_manager, tmp_path):
    """Test loading corrupted secrets file"""
    secrets_file = tmp_path / ".looplm" / "secrets.enc"
    secrets_file.write_bytes(b"corrupted data")

    # Should return empty dict for corrupted file
    assert config_manager.load_secrets() == {}


def test_save_secrets(config_manager):
    """Test saving and loading secrets"""
    test_secrets = {"anthropic_API_KEY": "test-key-1", "openai_API_KEY": "test-key-2"}
    config_manager.save_secrets(test_secrets)
    loaded_secrets = config_manager.load_secrets()
    assert loaded_secrets == test_secrets


def test_reset_provider(config_manager):
    """Test resetting a specific provider"""
    # First set up a provider
    provider = ProviderType.ANTHROPIC
    config_manager.save_provider_config(
        provider=provider,
        model_name="claude-3-opus-20240229",
        env_vars={"ANTHROPIC_API_KEY": "test-key"},
        is_default=True,
    )

    # Now reset it
    config_manager.reset_provider(provider)

    # Verify provider is removed
    providers = config_manager.get_configured_providers()
    assert provider not in providers

    # Verify default provider is updated if this was the default
    default_provider, _ = config_manager.get_default_provider()
    assert default_provider != provider


def test_get_provider_credentials_empty(config_manager):
    """Test getting credentials for unconfigured provider"""
    credentials = config_manager.get_provider_credentials(ProviderType.OPENAI)
    assert credentials == {}


def test_save_and_load_config(config_manager):
    """Test saving and loading configuration"""
    test_config = {
        "default_provider": "anthropic",
        "providers": {
            "anthropic": {
                "default_model": "claude-3-opus-20240229",
                "env_vars": ["ANTHROPIC_API_KEY"],
            }
        },
    }
    config_manager.save_config(test_config)
    loaded_config = config_manager.load_config()
    assert loaded_config == test_config


def test_get_provider_credentials(config_manager):
    """Test storing and retrieving provider credentials"""
    provider = ProviderType.ANTHROPIC
    test_creds = {"ANTHROPIC_API_KEY": "test-key"}

    config_manager.save_provider_config(
        provider=provider, model_name="claude-3-opus-20240229", env_vars=test_creds
    )

    credentials = config_manager.get_provider_credentials(provider)
    # The key should be exactly as stored
    assert credentials["ANTHROPIC_API_KEY"] == "test-key"


def test_set_default_provider(config_manager):
    """Test setting default provider"""
    provider = ProviderType.ANTHROPIC
    model_name = "claude-3-opus-20240229"

    config_manager.save_provider_config(
        provider=provider,
        model_name=model_name,
        env_vars={"ANTHROPIC_API_KEY": "test-key"},
        is_default=True,
    )

    default_provider, default_model = config_manager.get_default_provider()
    assert default_provider == provider
    assert default_model == model_name
