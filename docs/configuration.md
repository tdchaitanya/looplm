# Configuration Guide

LoopLM provides a straightforward way to configure different LLM providers. All configuration is handled through the CLI, with credentials stored securely using encryption.

## Initial Setup

To start configuring LoopLM, run:

```bash
looplm --configure
```

This will launch an interactive setup process where you can configure one or more providers.

## Supported Providers

LoopLM supports the following providers:

### Anthropic
Required environment variables:
- `ANTHROPIC_API_KEY`

Example model: `claude-3-5-sonnet-20240620`

### OpenAI
Required environment variables:
- `OPENAI_API_KEY`

Example model: `gpt-4o`

### Google Gemini
Required environment variables:
- `GEMINI_API_KEY`

Example model: `gemini/gemini-pro`

### Azure OpenAI
Required environment variables:
- `AZURE_API_KEY`
- `AZURE_API_BASE`
- `AZURE_API_VERSION`

Example model: `azure/gpt-4o`

### AWS Bedrock
Required environment variables:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION_NAME`

Example model: `anthropic.claude-3-5-sonnet-20240620-v1:0`

### Other Providers
LoopLM supports any provider that's compatible with LiteLLM. When configuring other providers, you'll need to:

1. Specify the provider name
2. Enter the required environment variables
3. Specify the model name according to LiteLLM's documentation

## Configuration Commands

### View Current Configuration

```bash
looplm --status
```

This shows:
- Configured providers
- Default provider and model
- Provider status

### Set Default Provider

```bash
looplm --set-default <provider>
```

Example:
```bash
looplm --set-default anthropic
```

### Reset Configuration

Reset all configuration:
```bash
looplm --reset
```

Reset specific provider:
```bash
looplm --reset-provider anthropic
```

## Configuration Storage

LoopLM stores configuration in two locations in your home directory:

1. `.looplm/config.json`: General configuration (non-sensitive)
2. `.looplm/secrets.enc`: Encrypted API keys and credentials

The configuration is encrypted using Fernet symmetric encryption, ensuring your API keys remain secure.

## Additional Environment Variables

When configuring a provider, you can set additional environment variables that might be required for your specific use case. These will be stored securely with your other credentials.