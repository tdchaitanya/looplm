# src/looplm/cli/main.py

# Suppress warnings before any other imports
import logging
import os
import warnings

# Force suppress all warnings
warnings.simplefilter("ignore")
warnings.filterwarnings("ignore", message=".*Valid config keys have changed in V2.*")
warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("ignore", UserWarning)
warnings.simplefilter("ignore", RuntimeWarning)
warnings.simplefilter("ignore", PendingDeprecationWarning)

# Disable all logging except critical
logging.getLogger().setLevel(logging.CRITICAL)

import sys

import click
from rich.console import Console
from rich.table import Table

from ..chat.control import CommandHandler
from ..config.manager import ConfigManager
from ..config.providers import ProviderType
from ..conversation.handler import ConversationHandler
from .setup import initial_setup

console = Console()


def get_input_from_pipe() -> str:
    """Read input from pipe if available"""
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def process_input(args: tuple, piped_input: str = "") -> str:
    """Process input from arguments and/or pipe"""
    if piped_input:
        return piped_input
    elif args:
        # Join args with spaces and preserve newlines
        return " ".join(args)
    return ""


@click.command()
@click.argument("prompt", nargs=-1, required=False)
@click.option("--provider", help="Use specific provider credentials")
@click.option("--model", help="Use specific model from the provider")
@click.option("--configure", is_flag=True, help="Configure a new provider")
@click.option("--reset", is_flag=True, help="Reset all configuration")
@click.option("--reset-provider", help="Reset configuration for specific provider")
@click.option("--set-default", help="Set default provider and model")
@click.option("--status", is_flag=True, help="Show configuration status")
@click.option("--debug", is_flag=True, help="Show processed commands without sending to LLM")
def cli(prompt, provider, model, configure, reset, reset_provider, set_default, status, debug):
    """looplm - LLMs on the command line"""
    config_manager = ConfigManager()

    # Handle configuration commands
    if configure:
        initial_setup()
        return

    # chat mode
    if prompt and prompt[0] == "chat":
        try:
            handler = CommandHandler(provider=provider, model=model, debug=debug)
            handler.start_session()

            if prompt:
                if handler.session_manager.active_session:
                    handler.session_manager.active_session.send_message(
                        prompt, stream=True, show_tokens=False
                    )
                else:
                    console.print("\nSession Closed", style="bold red")
        except Exception as e:
            console.print(f"\nFailed to process request: {str(e)}", style="bold red")
            raise click.Abort()

        return

    if reset:
        if click.confirm("Are you sure you want to reset all configuration?"):
            config_manager.reset_all()
            console.print(
                "✨ All configuration reset successfully.", style="bold green"
            )
        return

    if reset_provider:
        try:
            provider_type = ProviderType(reset_provider)
            if click.confirm(f"Are you sure you want to reset {reset_provider}?"):
                config_manager.reset_provider(provider_type)
                console.print(
                    f"✨ {reset_provider} configuration reset successfully.",
                    style="bold green",
                )
        except ValueError:
            # Check if this is a custom provider
            providers = config_manager.get_configured_providers()
            other_config = providers.get(ProviderType.OTHER, {})
            if other_config and other_config.get("provider_name") == reset_provider:
                if click.confirm(f"Are you sure you want to reset {reset_provider}?"):
                    config_manager.reset_provider(ProviderType.OTHER)
                    console.print(
                        f"✨ {reset_provider} configuration reset successfully.",
                        style="bold green",
                    )
            else:
                console.print(f"Invalid provider: {reset_provider}", style="bold red")
        return

    if set_default:
        try:
            provider_type = ProviderType(set_default)
            providers = config_manager.get_configured_providers()

            if set_default not in [p.value for p in ProviderType]:
                other_config = providers.get(ProviderType.OTHER, {})
                if other_config and other_config.get("provider_name") == set_default:
                    provider_type = ProviderType.OTHER
                else:
                    console.print(
                        f"Provider {set_default} is not configured", style="bold red"
                    )
                    return

            if provider_type not in providers:
                console.print(
                    f"Provider {set_default} is not configured", style="bold red"
                )
                return

            # Let user select a new default model
            model_name = click.prompt(
                "Enter the default model name for this provider",
                default=providers[provider_type]["default_model"],
            )

            config_manager.set_default_provider(provider_type, model_name)
            display_name = (
                providers[provider_type].get("provider_name", "")
                if provider_type == ProviderType.OTHER
                else set_default
            )
            console.print(
                f"✨ Default provider set to {display_name} with model {model_name}",
                style="bold green",
            )
        except ValueError:
            console.print(f"Invalid provider: {set_default}", style="bold red")
        return

    if status:
        show_status()
        return

    # Check if configuration exists
    if not config_manager.get_configured_providers():
        console.print(
            "\n⚠️  No providers configured. Starting initial setup...", style="yellow"
        )
        initial_setup()
        return

    # Handle chat/prompt
    piped_input = get_input_from_pipe()
    prompt_text = process_input(prompt, piped_input)

    if prompt_text:
        try:
            if provider and provider not in [p.value for p in ProviderType]:
                providers = config_manager.get_configured_providers()
                other_config = providers.get(ProviderType.OTHER, {})
                if other_config and other_config.get("provider_name") == provider:
                    provider = "other"  # Use the internal provider type

            handler = ConversationHandler(console)
            handler.handle_prompt(prompt_text, provider=provider, model=model)
        except Exception as e:
            console.print(f"\nFailed to process request: {str(e)}", style="bold red")
            raise click.Abort()
    else:
        show_status()


def show_status():
    """Show current configuration status"""
    config_manager = ConfigManager()
    default_provider, _ = config_manager.get_default_provider()
    providers = config_manager.get_configured_providers()

    table = Table(title="Configured Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Default Model", style="green")
    table.add_column("Status", style="yellow")

    for provider, config in providers.items():
        display_name = config_manager.get_provider_display_name(provider, config)
        status = "DEFAULT" if provider == default_provider else "Configured"
        table.add_row(display_name, config["default_model"], status)

    console.print("\n🔄 LoopLM", style="bold blue")
    console.print(table)

    console.print("\nUsage:", style="bold")
    console.print(
        '  looplm "your prompt"                        - Use default provider and model'
    )
    console.print(
        '  looplm --provider <name> "prompt"          - Use specific provider with its default model'
    )
    console.print(
        '  looplm --provider <name> --model <name> "prompt" - Use specific provider and model'
    )
    console.print('\nNote: For custom providers configured as "other", use either:')
    console.print('  looplm --provider other "prompt"           - Using internal name')
    console.print(
        '  looplm --provider <custom_name> "prompt"   - Using your configured name'
    )

    console.print("\nConfiguration:", style="bold")
    console.print("  looplm --configure             - Configure providers")
    console.print("  looplm --reset                - Reset all configuration")
    console.print("  looplm --reset-provider <name> - Reset specific provider")
    console.print("  looplm --set-default <name>   - Set default provider and model")
    console.print("  looplm --status               - Show current status")


def main():
    """Main entry point for the CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n\nOperation cancelled by user", style="yellow")
        sys.exit(1)


if __name__ == "__main__":
    main()
