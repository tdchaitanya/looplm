"""Shared fixtures for looplm tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add the src directory to the path so we can import looplm
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_home_dir(tmp_path, monkeypatch):
    """Create a temporary home directory for testing."""
    # Set HOME environment variable to the temporary path
    monkeypatch.setenv("HOME", str(tmp_path))

    # Mock Path.home() to return the temporary path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create .looplm directory
    looplm_dir = tmp_path / ".looplm"
    looplm_dir.mkdir(exist_ok=True)

    return tmp_path


@pytest.fixture
def mock_litellm():
    """Mock litellm for testing."""

    class MockResponse:
        def __init__(self, content="Test response"):
            self.usage = MagicMock()
            self.usage.prompt_tokens = 10
            self.usage.completion_tokens = 20
            self.choices = [MagicMock()]
            self.choices[0].message = MagicMock()
            self.choices[0].message.content = content
            self.choices[0].delta = MagicMock()
            self.choices[0].delta.content = content

    mock = MagicMock()
    mock.return_value = MockResponse()

    return mock


@pytest.fixture
def mock_stream_response():
    """Mock a streaming response from litellm."""

    class MockStreamResponse:
        def __init__(self, content="Test response", num_chunks=3):
            self.content = content
            self.num_chunks = num_chunks
            self.usage = MagicMock()
            self.usage.prompt_tokens = 10
            self.usage.completion_tokens = 20

            # Build chunks
            chunk_size = max(1, len(content) // num_chunks)
            self.chunks = []

            for i in range(num_chunks):
                start = i * chunk_size
                end = start + chunk_size if i < num_chunks - 1 else len(content)
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = content[start:end]
                chunk.usage = self.usage
                self.chunks.append(chunk)

        def __iter__(self):
            return iter(self.chunks)

    def mock_stream_fn(*args, **kwargs):
        return MockStreamResponse()

    return mock_stream_fn


@pytest.fixture
def os_name():
    """Return the current OS name for tests that need OS-specific behavior."""
    if sys.platform.startswith("win"):
        return "windows"
    elif sys.platform.startswith("darwin"):
        return "macos"
    else:
        return "linux"
