# src/looplm/config/providers.py
import enum
from dataclasses import dataclass
from typing import Dict, List


class ProviderType(enum.Enum):
    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    BEDROCK = "bedrock"
    OTHER = "other"


@dataclass
class ProviderConfig:
    name: str
    required_env_vars: List[str]
    example_model: str
    description: str
    model_format: str


PROVIDER_CONFIGS: Dict[ProviderType, ProviderConfig] = {
    ProviderType.ANTHROPIC: ProviderConfig(
        name="anthropic",
        required_env_vars=["ANTHROPIC_API_KEY"],
        example_model="claude-3-opus-20240229",
        description="Anthropic",
        model_format="claude-* (e.g., claude-3-5-sonnet-20240620)",
    ),
    ProviderType.OPENAI: ProviderConfig(
        name="openai",
        required_env_vars=["OPENAI_API_KEY"],
        example_model="gpt-4o",
        description="OpenAI",
        model_format="gpt-*, o1-* (e.g., gpt-4o)",
    ),
    ProviderType.GEMINI: ProviderConfig(
        name="gemini",
        required_env_vars=["GEMINI_API_KEY"],
        example_model="gemini/gemini-pro",
        description="Gemini (Google AI Studio)",
        model_format="gemini/* (e.g., gemini/gemini-pro)",
    ),
    ProviderType.AZURE: ProviderConfig(
        name="azure",
        required_env_vars=["AZURE_API_KEY", "AZURE_API_BASE", "AZURE_API_VERSION"],
        example_model="azure/gpt-4",
        description="Azure OpenAI",
        model_format="azure/<deployment-name>",
    ),
    ProviderType.BEDROCK: ProviderConfig(
        name="bedrock",
        required_env_vars=[
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION_NAME",
        ],
        example_model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        description="AWS Bedrock",
        model_format="<provider.model-name> (e.g., anthropic.claude-*, amazon.titan-*)",
    ),
    ProviderType.OTHER: ProviderConfig(
        name="Other Providers",
        required_env_vars=[],
        example_model="",
        description="Configure any other provider supported by LiteLLM",
        model_format="Refer to LiteLLM documentation for model names",
    ),
}
