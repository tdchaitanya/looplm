"""Shared fixtures for config module tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from looplm.config.manager import ConfigManager


@pytest.fixture
def mock_config_dir(tmp_path, monkeypatch):
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / ".looplm"
    config_dir.mkdir(exist_ok=True)

    # Mock the home directory to point to our temp path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    return config_dir


@pytest.fixture
def mock_fernet():
    """Mock Fernet encryption with a deterministic version."""
    mock_fernet = MagicMock(spec=Fernet)

    # Define clear behavior for encrypt and decrypt
    def mock_encrypt(data):
        if not isinstance(data, bytes):
            data = data.encode()
        return b"encrypted_" + data

    def mock_decrypt(data):
        if data.startswith(b"encrypted_"):
            return data[len(b"encrypted_") :]
        return data

    mock_fernet.encrypt.side_effect = mock_encrypt
    mock_fernet.decrypt.side_effect = mock_decrypt

    return mock_fernet


@pytest.fixture
def config_manager(mock_config_dir, mock_fernet):
    """Create a ConfigManager with mocked dependencies."""
    # Patch the _init_encryption method to do nothing
    with (
        patch.object(ConfigManager, "_init_encryption"),
        patch.object(ConfigManager, "ensure_config_dir"),
    ):

        manager = ConfigManager()
        # Explicitly set the _fernet attribute on the instance
        manager._fernet = mock_fernet

        # Explicitly set paths to use our test directory
        manager.config_dir = mock_config_dir
        manager.config_file = mock_config_dir / "config.json"
        manager.secrets_file = mock_config_dir / "secrets.enc"

        # Create empty config files
        manager.config_file.write_text("{}")
        manager.secrets_file.write_bytes(b"encrypted_{}")

        yield manager


@pytest.fixture
def real_config_manager(tmp_path, monkeypatch):
    """Create a ConfigManager that uses real encryption."""
    config_dir = tmp_path / ".looplm"
    config_dir.mkdir(exist_ok=True)

    # Mock the home directory to point to our temp path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create a real ConfigManager (not mocked)
    manager = ConfigManager()

    yield manager
