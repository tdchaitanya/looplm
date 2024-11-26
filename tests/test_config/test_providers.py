# tests/test_config/test_providers.py
from looplm.config.providers import ProviderType, PROVIDER_CONFIGS


def test_provider_configs_completeness():
    """Test that all provider types have corresponding configs"""
    for provider in ProviderType:
        assert provider in PROVIDER_CONFIGS
        config = PROVIDER_CONFIGS[provider]
        assert hasattr(config, "name")
        assert hasattr(config, "required_env_vars")
        assert hasattr(config, "example_model")
