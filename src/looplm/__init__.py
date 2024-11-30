# src/looplm/__init__.py
"""looplm - LLMs on the command line"""
__version__ = "0.1.0"

from .config.manager import ConfigManager
from .config.providers import ProviderType, ProviderConfig, PROVIDER_CONFIGS
from .conversation.handler import ConversationHandler
