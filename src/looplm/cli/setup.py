# src/looplm/cli/setup.py
import os
from typing import Dict, List

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from ..config.manager import ConfigManager
from ..config.providers import PROVIDER_CONFIGS, ProviderType

console = Console()


def handle_default_provider_selection(
    config_manager: ConfigManager, new_provider: ProviderType = None
):
    """Handle default provider selection

    Args:
        config_manager: Configuration manager instance
        new_provider: Newly configured provider (if any)
    """
    providers = config_manager.get_configured_providers()

    if len(providers) > 1:
        console.print("\nConfigured providers:", style="bold")
        provider_list = []
        for provider, config in providers.items():
            provider_config = PROVIDER_CONFIGS[provider]
            console.print(
                f"  • {provider_config.name} (Default model: {config['default_model']})"
            )
            provider_list.append(provider)

        if Confirm.ask("\nWould you like to change the default provider?"):
            for i, provider in enumerate(provider_list, 1):
                config = providers[provider]
                provider_info = PROVIDER_CONFIGS[provider]
                console.print(
                    f"{i}. {provider_info.name} (Default model: {config['default_model']})"
                )

            while True:
                try:
                    choice = int(
                        Prompt.ask(
                            "Select default provider",
                            choices=[str(i) for i in range(1, len(provider_list) + 1)],
                            default="1",
                        )
                    )

                    if 1 <= choice <= len(provider_list):
                        selected_provider = provider_list[choice - 1]
                        provider_config = providers[selected_provider]
                        config_manager.set_default_provider(
                            selected_provider, provider_config["default_model"]
                        )
                        console.print(
                            f"\n✨ Set {PROVIDER_CONFIGS[selected_provider].name} as default provider",
                            style="bold green",
                        )
                        break
                    else:
                        console.print(
                            "Invalid choice. Please select a valid number.",
                            style="bold red",
                        )
                except ValueError:
                    console.print("Please enter a valid number.", style="bold red")
                except Exception as e:
                    console.print(
                        f"Error setting default provider: {str(e)}", style="bold red"
                    )
                    break


def get_additional_env_vars() -> Dict[str, str]:
    """Get additional environment variables from user"""
    env_vars = {}
    while Confirm.ask("Would you like to set additional environment variables?"):
        var_input = Prompt.ask("Enter variable in format VAR_NAME=value")
        try:
            var_name, var_value = var_input.split("=", 1)
            env_vars[var_name.strip()] = var_value.strip()
        except ValueError:
            console.print("Invalid format. Please use VAR_NAME=value", style="red")
    return env_vars


def get_valid_models_for_provider(
    provider: ProviderType, env_vars: Dict[str, str]
) -> List[str]:
    """Get valid models for a specific provider"""
    current_env = dict(os.environ)
    os.environ.clear()

    for var, value in env_vars.items():
        os.environ[var] = value

    try:
        from litellm.utils import get_valid_models

        return get_valid_models()
    except Exception as e:
        console.print(
            f"Warning: Could not fetch valid models: {str(e)}", style="yellow"
        )
        return []
    finally:
        os.environ.clear()
        os.environ.update(current_env)


def setup_provider(provider: ProviderType, config_manager: ConfigManager) -> bool:
    """Setup a specific provider

    Args:
        provider: Provider type to configure
        config_manager: Configuration manager instance

    Returns:
        bool: True if setup successful
    """
    config = PROVIDER_CONFIGS[provider]
    console.print(f"\nConfiguring {config.name}", style="bold blue")

    # Check if provider is already configured
    providers = config_manager.get_configured_providers()
    provider_exists = provider in providers

    # If provider exists, check if user wants to add a new model
    is_new_model = False
    existing_models = []
    existing_env_vars = {}

    if provider_exists:
        # Get existing models for this provider
        existing_models = config_manager.get_provider_models(provider)

        # Display existing models
        console.print("\nExisting models for this provider:", style="bold cyan")
        for i, model in enumerate(existing_models, 1):
            is_default = model == providers[provider].get("default_model")
            console.print(f"  {i}. {model}" + (" (default)" if is_default else ""))

        # Ask if user wants to add a new model or reconfigure
        action = Prompt.ask(
            "\nWhat would you like to do?",
            choices=["add", "reconfigure"],
            default="add",
        )

        is_new_model = action == "add"

        if is_new_model:
            console.print(
                "\nAdding a new model to existing provider", style="bold green"
            )
            # Reuse existing credentials
            existing_env_vars = config_manager.get_provider_credentials(provider)
        else:
            console.print("\nReconfiguring provider", style="bold yellow")

    provider_name = None
    if provider == ProviderType.OTHER:
        console.print(
            "\nPlease refer to LiteLLM documentation for required environment variables:"
        )
        console.print("https://docs.litellm.ai/docs/providers")
        provider_name = (
            Prompt.ask("\nEnter the provider name (e.g., cohere, replicate)")
            .lower()
            .strip()
        )

    # Only ask for env vars if this is a new provider or we're reconfiguring
    env_vars = {}
    if not provider_exists or not is_new_model:
        for var in config.required_env_vars:
            value = Prompt.ask(f"Enter your {var}")
            env_vars[var] = value

        if provider == ProviderType.OTHER:
            console.print(
                f"\nEnter the required environment variables for the {provider_name}:"
            )
            var_input = Prompt.ask("Enter variable in format VAR_NAME=value")
            try:
                var_name, var_value = var_input.split("=", 1)
                env_vars[var_name.strip()] = var_value.strip()
            except ValueError:
                console.print("Invalid format. Please use VAR_NAME=value", style="red")

        additional_vars = get_additional_env_vars()
        env_vars.update(additional_vars)
    else:
        # Reuse existing credentials
        env_vars = existing_env_vars

    if provider == ProviderType.OTHER:
        console.print("\nPlease refer to LiteLLM documentation for model names:")
        console.print("https://docs.litellm.ai/docs/providers")
        # For OTHER providers, we just want the model name without the provider prefix
        model_name = Prompt.ask("Enter the model name").strip()

    elif provider == ProviderType.AZURE:
        console.print(
            "\nProvide your deployed model name in the format: azure/<model-name>"
        )
        console.print("Example: azure/gpt-4o", style="bold")
        model_name = Prompt.ask("Enter model name", default="azure/gpt-4o")

    elif provider == ProviderType.BEDROCK:
        console.print("\nProvide the model name in the format: <provider.modelname>")
        console.print(
            "Example: anthropic.claude-3-5-sonnet-20240620-v1:0", style="bold"
        )
        model_name = Prompt.ask(
            "Enter model name", default="anthropic.claude-3-5-sonnet-20240620-v1:0"
        )

    elif provider == ProviderType.OTHER:
        console.print("\nPlease refer to LiteLLM documentation for model names:")
        console.print("https://docs.litellm.ai/docs/providers")
        model_name = Prompt.ask(
            "Enter the default model name (as per LiteLLM documentation)"
        )

    else:
        console.print(f"\nExample model: {config.example_model}", style="bold")
        model_name = Prompt.ask(
            "Enter default model name", default=config.example_model
        )

    # Set as default model?
    set_as_default = False
    if is_new_model and existing_models:
        set_as_default = Confirm.ask(
            f"Set {model_name} as the default model for {config.name}?"
        )

    # Validate only if we have new env_vars or a new model
    if not is_new_model or not provider_exists:
        if not config_manager.validate_provider_setup(
            provider.value if provider != ProviderType.OTHER else provider_name,
            model_name,
            env_vars,
            custom_provider=provider_name if provider == ProviderType.OTHER else None,
        ):
            console.print("❌ Configuration validation failed", style="red")
            return False

    is_first = len(config_manager.get_configured_providers()) == 0
    provider_config = {
        "default_model": (
            model_name
            if set_as_default or not is_new_model
            else providers[provider].get("default_model")
        ),
        "env_vars": list(env_vars.keys()),
    }

    if provider == ProviderType.OTHER:
        provider_config["provider_name"] = provider_name

    config_manager.save_provider_config(
        provider,
        model_name,
        env_vars,
        is_default=is_first,
        additional_config=provider_config if provider == ProviderType.OTHER else None,
        is_new_model=is_new_model,
    )

    return True


def initial_setup():
    """Run initial setup if not configured"""
    config_manager = ConfigManager()
    existing_providers = config_manager.get_configured_providers()
    is_first_setup = len(existing_providers) == 0

    if is_first_setup:
        # More detailed ASCII art logo
        logo = """
            [gradient(#4B56D2,#82AAAD)]

               [bold white]██╗      ██████╗  ██████╗ ██████╗ ██╗     ███╗   ███╗[/bold white]
               [bold white]██║     ██╔═══██╗██╔═══██╗██╔══██╗██║     ████╗ ████║[/bold white]
               [bold white]██║     ██║   ██║██║   ██║██████╔╝██║     ██╔████╔██║[/bold white]
               [bold white]██║     ██║   ██║██║   ██║██╔═══╝ ██║     ██║╚██╔╝██║[/bold white]
               [bold white]███████╗╚██████╔╝╚██████╔╝██║     ███████╗██║ ╚═╝ ██║[/bold white]
               [bold white]╚══════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚══════╝╚═╝     ╚═╝[/bold white]

               [italic #F5F5F5]Language Models at your command[/italic #F5F5F5]

                                                              [/gradient(#4B56D2,#82AAAD)]"""

        description = """
        [bright_cyan underline]Enhance your day-to-day workflows with assistance from LLMs[/bright_cyan underline]

        [white][bright_blue]✦[/bright_blue] [bright_white]Collaborate[/bright_white] with LLMs to improve your code
        [bright_blue]✦[/bright_blue] [bright_white]Learn[/bright_white] and understand through intelligent assistance
        [bright_blue]✦[/bright_blue] [bright_white]Streamline[/bright_white] your daily development tasks
        [bright_blue]✦[/bright_blue] [bright_white]Maintain[/bright_white] full control over your workflow[/white]

        [dim]Configure your preferred LLM provider to get started:
        Supported providers include [bright_blue]Anthropic Claude[/bright_blue], [bright_green]OpenAI GPT[/bright_green], [bright_red]Google Gemini[/bright_red], and more.[/dim]"""

        footer = """
        [dim white]Use arrow keys to navigate • Press Enter to select • Press 'q' to quit[/dim white]"""

        title_panel = Panel(
            Align.center(
                Text.from_markup(f"{logo}\n{description}\n{footer}"), vertical="middle"
            ),
            border_style="bright_blue",
            padding=(1, 2),
            title="[bold white]🔧 Configuration Setup[/bold white]",
            title_align="center",
            subtitle="[dim]v1.0.0[/dim]",
            subtitle_align="right",
        )

        console.print()
        console.print(title_panel)
        console.print()

    configured_any = False
    providers_configured = []

    while True:
        # First, show existing configured providers
        if existing_providers:
            console.print("\nAlready configured providers:", style="bold green")
            provider_table = Table(title="Configured Providers")
            provider_table.add_column("Provider", style="cyan")
            provider_table.add_column("Models", style="green")
            provider_table.add_column("Default Model", style="yellow")

            for provider, config in existing_providers.items():
                display_name = config_manager.get_provider_display_name(
                    provider, config
                )
                default_model = config.get("default_model", "")

                # Get all models for this provider
                models = config_manager.get_provider_models(provider)
                models_str = ", ".join(models)

                provider_table.add_row(display_name, models_str, default_model)

            console.print(provider_table)

        console.print("\nAvailable providers:", style="bold")
        for provider in ProviderType:
            config = PROVIDER_CONFIGS[provider]
            status = "[configured]" if provider in existing_providers else ""
            console.print(f"  • {config.name}: {config.description} {status}")

        provider_names = [p.value for p in ProviderType]
        selected = Prompt.ask(
            "\nWhich provider would you like to configure?",
            choices=provider_names,
            default=provider_names[0],
        )

        provider = ProviderType(selected)
        if setup_provider(provider, config_manager):
            configured_any = True
            is_first_setup = False
            providers_configured.append(provider)
            console.print("✅  Provider configured successfully!", style="bold green")

            if not is_first_setup:
                handle_default_provider_selection(config_manager, provider)

            if not Confirm.ask(
                "\nWould you like to configure another provider or model?"
            ):
                break
        else:
            console.print("❌  Provider configuration failed", style="bold red")
            if not configured_any:
                continue
            if not Confirm.ask("\nWould you like to try configuring another provider?"):
                break

    if configured_any:
        console.print("\n✨ Setup completed successfully!", style="bold green")
        console.print("\n[dim white]Example usage:[/dim white]")
        console.print(
            '[bright_green]$[/bright_green] [white]looplm "What are the best practices for Python error handling?"[/white]'
        )
        console.print(
            '[bright_green]$[/bright_green] [white]looplm "Write a detailed docstring for this function: $(cat function.py)"[/white]'
        )
        console.print(
            '[bright_green]$[/bright_green] [white]cat error.log | looplm "Explain this error and suggest solutions"[/white]'
        )
        console.print("\n[dim white]For a specific model, use:[/dim white]")
        console.print(
            '[bright_green]$[/bright_green] [white]looplm --model <model-name> "Your prompt here"[/white]'
        )
        return
