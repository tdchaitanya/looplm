"""Tests for the providers module."""

from looplm.config.providers import PROVIDER_CONFIGS, ProviderType


class TestProviderTypes:
    """Tests for the ProviderType enum."""

    def test_provider_types(self):
        """Test that all expected provider types are defined."""
        expected_types = ["OPENAI", "AZURE", "ANTHROPIC", "GEMINI", "BEDROCK", "OTHER"]

        for expected_type in expected_types:
            assert hasattr(ProviderType, expected_type)

    def test_provider_values(self):
        """Test that provider types have the expected values."""
        expected_values = {
            "OPENAI": "openai",
            "AZURE": "azure",
            "ANTHROPIC": "anthropic",
            "GEMINI": "gemini",
            "BEDROCK": "bedrock",
            "OTHER": "other",
        }

        for type_name, expected_value in expected_values.items():
            provider_type = getattr(ProviderType, type_name)
            assert provider_type.value == expected_value


class TestProviderConfigs:
    """Tests for the PROVIDER_CONFIGS dictionary."""

    def test_all_providers_have_configs(self):
        """Test that all provider types have configurations."""
        for provider_type in ProviderType:
            assert provider_type in PROVIDER_CONFIGS

    def test_provider_config_structure(self):
        """Test that provider configs have the expected structure."""
        for provider_type, config in PROVIDER_CONFIGS.items():
            assert hasattr(config, "name")
            assert hasattr(config, "required_env_vars")
            assert hasattr(config, "example_model")
            assert hasattr(config, "description")
            assert hasattr(config, "model_format")

            assert isinstance(config.name, str)
            assert isinstance(config.required_env_vars, list)
            assert isinstance(config.example_model, str)
            assert isinstance(config.description, str)
            assert isinstance(config.model_format, str)

    def test_specific_provider_configs(self):
        """Test specific provider configurations."""
        # Test Anthropic config
        anthropic_config = PROVIDER_CONFIGS[ProviderType.ANTHROPIC]
        assert anthropic_config.name == "anthropic"
        assert "ANTHROPIC_API_KEY" in anthropic_config.required_env_vars

        # Test OpenAI config
        openai_config = PROVIDER_CONFIGS[ProviderType.OPENAI]
        assert openai_config.name == "openai"
        assert "OPENAI_API_KEY" in openai_config.required_env_vars
