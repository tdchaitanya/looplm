# src/looplm/config/manager.py
import json
import os
from base64 import b64encode
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .providers import PROVIDER_CONFIGS, ProviderType


class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".looplm"
        self.config_file = self.config_dir / "config.json"
        self.secrets_file = self.config_dir / "secrets.enc"
        self._init_encryption()
        self.ensure_config_dir()

    def _init_encryption(self):
        """Initialize encryption key"""
        salt = b"looplm_salt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = b64encode(kdf.derive(b"looplm_secret_key"))
        self._fernet = Fernet(key)

    def set_default_provider(self, provider: ProviderType, model_name: str = None):
        """Set default provider and optionally update its default model

        Args:
            provider: Provider to set as default
            model_name: Optional new default model for the provider
        """
        config = self.load_config()
        if "providers" not in config or provider.value not in config["providers"]:
            raise ValueError(f"Provider {provider.value} is not configured")

        config["default_provider"] = provider.value

        if model_name:
            config["providers"][provider.value]["default_model"] = model_name

        self.save_config(config)

    def ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(exist_ok=True)
        if not self.config_file.exists():
            self.save_config({})
        if not self.secrets_file.exists():
            self.secrets_file.write_bytes(self._fernet.encrypt(b"{}"))

    def load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                return json.loads(self.config_file.read_text())
            return {}
        except json.JSONDecodeError:
            return {}

    def save_config(self, config: Dict):
        """Save configuration to file"""
        self.config_file.write_text(json.dumps(config, indent=2))

    def load_secrets(self) -> Dict[str, str]:
        """Load encrypted secrets"""
        try:
            if not self.secrets_file.exists() or self.secrets_file.stat().st_size == 0:
                return {}
            encrypted_data = self.secrets_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except Exception:
            return {}

    def _prepare_environment(self, provider: str) -> None:
        """Set up environment variables for the specified provider

        Args:
            provider: The provider name (e.g., 'anthropic', 'openai', 'other')
        """
        secrets = self.load_secrets()

        if provider == ProviderType.OTHER.value:
            for key, value in secrets.items():
                if key.startswith(f"{provider}_"):
                    env_var = key.split(f"{provider}_", 1)[1]
                    os.environ[env_var] = value
        else:
            for key, value in secrets.items():
                if key.startswith(f"{provider}_"):
                    env_var = key.replace(f"{provider}_", "")
                    os.environ[env_var] = value

    def save_secrets(self, secrets: Dict[str, str]):
        """Save encrypted secrets"""
        encrypted_data = self._fernet.encrypt(json.dumps(secrets).encode())
        self.secrets_file.write_bytes(encrypted_data)

    def save_provider_config(
        self,
        provider: ProviderType,
        model_name: str,
        env_vars: Dict[str, str],
        is_default: bool = False,
        additional_config: Dict = None,
    ):
        """Save provider configuration with model

        Args:
            provider: Provider type
            model_name: Default model for this provider
            env_vars: Environment variables for provider
            is_default: Whether this should be the default provider
            additional_config: Additional params (e.g., provider name for OTHER type)
        """
        secrets = self.load_secrets()

        if provider == ProviderType.OTHER:
            for key, value in env_vars.items():
                secrets[f"{provider.value}_{key}"] = value
        else:
            for key, value in env_vars.items():
                secrets[f"{provider.value}_{key}"] = value

        self.save_secrets(secrets)

        config = self.load_config()
        if "providers" not in config:
            config["providers"] = {}

        config["providers"][provider.value] = {
            "default_model": model_name,
            "env_vars": list(env_vars.keys()),
        }
        if additional_config:
            config["providers"][provider.value].update(additional_config)

        if is_default or "default_provider" not in config:
            config["default_provider"] = provider.value

        self.save_config(config)

    def get_configured_providers(self) -> Dict[ProviderType, Dict[str, Any]]:
        """Get dictionary of configured providers and their configurations

        Returns:
            Dict mapping ProviderType to provider configuration dict containing
            'default_model' and 'env_vars'
        """
        config = self.load_config()
        providers = config.get("providers", {})
        return {ProviderType(p): data for p, data in providers.items()}

    def get_provider_credentials(self, provider: ProviderType) -> Dict[str, str]:
        """Get provider credentials

        Args:
            provider: Provider type

        Returns:
            Dict of environment variables for the provider
        """
        secrets = self.load_secrets()
        provider_secrets = {}

        for key, value in secrets.items():
            if key.startswith(f"{provider.value}_"):
                if provider == ProviderType.OTHER:
                    env_var = key.split(f"{provider.value}_", 1)[1]
                else:
                    env_var = key.replace(f"{provider.value}_", "")
                provider_secrets[env_var] = value

        return provider_secrets

    def get_default_provider(self) -> Tuple[Optional[ProviderType], Optional[str]]:
        """Get default provider and its default model

        Returns:
            Tuple of (ProviderType, model_name) or (None, None) if not set
        """
        config = self.load_config()
        provider_name = config.get("default_provider")

        if provider_name:
            try:
                provider = ProviderType(provider_name)
                provider_config = config.get("providers", {}).get(provider_name, {})
                return provider, provider_config.get("default_model")
            except ValueError:
                return None, None
        return None, None

    def get_provider_display_name(self, provider: ProviderType, config: Dict) -> str:
        """Get display name for provider

        Args:
            provider: Provider type
            config: Provider configuration dictionary

        Returns:
            str: Display name for the provider
        """
        if provider == ProviderType.OTHER:
            return config.get("provider_name", "Other Provider")
        return PROVIDER_CONFIGS[provider].name

    def validate_provider_setup(
        self,
        provider: str,
        model_name: str,
        env_vars: Dict[str, str] = None,
        custom_provider: Optional[str] = None,
    ) -> bool:
        """Validate provider setup using LiteLLM

        Args:
            provider: Provider name
            model_name: Model name to test
            env_vars: Optional new environment variables for validation

        Returns:
            bool: True if validation successful
        """
        try:
            current_env = dict(os.environ)
            os.environ.clear()

            if env_vars:
                for key, value in env_vars.items():
                    os.environ[key] = value
            else:
                self._prepare_environment(provider)

            try:
                from litellm import completion

                # actual_model = model_name
                # if provider == ProviderType.OTHER.value and custom_provider:
                #     actual_model = f"{custom_provider}/{model_name}"

                completion(
                    model=model_name,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                )
                return True
            except Exception as e:
                print(f"Validation error: {str(e)}")
                return False
            finally:
                os.environ.clear()
                os.environ.update(current_env)
        except Exception as e:
            print(f"Setup validation error: {str(e)}")
            return False

    def reset_provider(self, provider: ProviderType):
        """Reset specific provider configuration"""
        secrets = self.load_secrets()
        config = self.load_config()
        provider_config = config.get("providers", {}).get(provider.value, {})

        for env_var in provider_config.get("env_vars", []):
            key = f"{provider.value}_{env_var}"
            if key in secrets:
                del secrets[key]

        if "providers" in config and provider.value in config["providers"]:
            del config["providers"][provider.value]

        if config.get("default_provider") == provider.value:
            config.pop("default_provider", None)
            config.pop("default_model", None)

            remaining = list(config.get("providers", {}).keys())
            if remaining:
                config["default_provider"] = remaining[0]
                config["default_model"] = config["providers"][remaining[0]]["model"]

        self.save_secrets(secrets)
        self.save_config(config)

    def reset_all(self):
        """Reset all configuration"""
        self.secrets_file.write_bytes(self._fernet.encrypt(b"{}"))
        self.save_config({})
