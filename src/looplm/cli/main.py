# src/looplm/cli/main.py

# Suppress warnings before any other imports
import logging
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
@click.option(
    "--debug", is_flag=True, help="Show processed commands without sending to LLM"
)
@click.option(
    "--ui",
    type=click.Choice(["rich", "textual"], case_sensitive=False),
    default="rich",
    help="Choose the chat interface: 'rich' for traditional console or 'textual' for full-page TUI",
)
@click.option(
    "--tools",
    help="Enable tools (comma-separated list of tool names, or 'all' for all tools)",
)
@click.option(
    "--tools-approval",
    is_flag=True,
    help="Require human approval before executing tools",
)
def cli(
    prompt,
    provider,
    model,
    configure,
    reset,
    reset_provider,
    set_default,
    status,
    debug,
    ui,
    tools,
    tools_approval,
):
    """looplm - LLMs on the command line"""
    config_manager = ConfigManager()

    # Handle configuration commands
    if configure:
        initial_setup()
        return

    # chat mode
    if prompt and prompt[0] == "chat":
        try:
            if ui.lower() == "textual":
                # Use the new Textual interface
                from ..chat.textual_ui import run_textual_chat

                run_textual_chat(
                    provider=provider,
                    model=model,
                    debug=debug,
                    tools=tools,
                    tools_approval=tools_approval,
                )
            else:
                # Use the traditional Rich interface
                handler = CommandHandler(
                    provider=provider,
                    model=model,
                    debug=debug,
                    tools=tools,
                    tools_approval=tools_approval,
                )
                handler.start_session()

                if prompt:
                    if handler.session_manager.active_session:
                        handler.session_manager.active_session.send_message(
                            prompt, stream=True, show_tokens=False
                        )
                    else:
                        console.print("\nSession Closed", style="bold red")
        except Exception as e:
            # Use Rich's escape function to escape any markup in the error message
            from rich.markup import escape

            error_message = escape(str(e))
            console.print(
                f"\nFailed to process request: {error_message}", style="bold red"
            )
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
            providers = config_manager.get_configured_providers()
            provider_found = False
            provider_type = None

            # First try direct enum match
            try:
                provider_type = ProviderType(set_default)
                provider_found = True
            except ValueError:
                # Not a direct enum match, check other possibilities
                pass

            # Check if it's a custom (OTHER) provider
            if not provider_found:
                other_config = providers.get(ProviderType.OTHER, {})
                if other_config and other_config.get("provider_name") == set_default:
                    provider_type = ProviderType.OTHER
                    provider_found = True

            # Check if it matches any provider display name
            if not provider_found:
                for p_type, config in providers.items():
                    display_name = config_manager.get_provider_display_name(
                        p_type, config
                    ).lower()
                    if set_default.lower() == display_name:
                        provider_type = p_type
                        provider_found = True
                        break

            if not provider_found:
                console.print(
                    f"Provider '{set_default}' is not configured", style="bold red"
                )
                return

            if provider_type not in providers:
                console.print(
                    f"Provider '{set_default}' is not configured", style="bold red"
                )
                return

            # Get available models for this provider
            models = config_manager.get_provider_models(provider_type)

            if models:
                console.print("\nAvailable models for this provider:")
                for i, model_name in enumerate(models, 1):
                    console.print(f"  {i}. {model_name}")

                model_choice = click.prompt(
                    "Select model number or enter model name", default="1"
                )

                # Convert choice to model name if it's a number
                try:
                    choice_idx = int(model_choice) - 1
                    if 0 <= choice_idx < len(models):
                        model_name = models[choice_idx]
                    else:
                        model_name = model_choice
                except ValueError:
                    model_name = model_choice
            else:
                # Let user select a new default model
                model_name = click.prompt(
                    "Enter the default model name for this provider",
                    default=providers[provider_type]["default_model"],
                )

            config_manager.set_default_provider(provider_type, model_name)
            display_name = config_manager.get_provider_display_name(
                provider_type, providers[provider_type]
            )
            console.print(
                f"✨ Default provider set to {display_name} with model {model_name}",
                style="bold green",
            )
        except Exception as e:
            console.print(f"Error setting default provider: {str(e)}", style="bold red")
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

            handler = ConversationHandler(console, debug=debug)

            # Enable tools if specified
            if tools:
                if tools.lower() == "all":
                    handler.enable_tools(require_approval=tools_approval)
                else:
                    tool_list = [name.strip() for name in tools.split(",")]
                    handler.enable_tools(
                        tool_names=tool_list, require_approval=tools_approval
                    )

            handler.handle_prompt(prompt_text, provider=provider, model=model)
        except Exception as e:
            from rich.markup import escape

            error_message = escape(str(e))
            console.print(
                f"\nFailed to process request: {error_message}", style="bold red"
            )
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
    table.add_column("Models", style="green")
    table.add_column("Default Model", style="yellow")
    table.add_column("Status", style="yellow")

    for provider, config in providers.items():
        display_name = config_manager.get_provider_display_name(provider, config)

        # Get all models for this provider
        models = config_manager.get_provider_models(provider)

        # Strip provider prefix from model names for display
        display_models = []
        provider_prefix = f"{provider.value}/"
        for model in models:
            if model.startswith(provider_prefix):
                display_models.append(model[len(provider_prefix) :])
            else:
                display_models.append(model)

        models_str = ", ".join(display_models)

        # Also strip prefix from default model
        default_model = config.get("default_model", "")
        if default_model.startswith(provider_prefix):
            default_model_display = default_model[len(provider_prefix) :]
        else:
            default_model_display = default_model

        status = "DEFAULT" if provider == default_provider else "Configured"

        table.add_row(display_name, models_str, default_model_display, status)

    # Get available commands
    from looplm.commands import CommandManager

    command_manager = CommandManager()
    available_commands = command_manager.get_available_commands()

    console.print("\n🔄 LoopLM", style="bold blue")
    console.print(table)

    # Display available commands
    command_table = Table(title="Available Commands")
    command_table.add_column("Command", style="cyan")
    command_table.add_column("Description", style="white")

    # Add standard @ commands first
    for cmd_name in sorted(available_commands):
        processor = command_manager.get_processor(cmd_name)
        if (
            processor and cmd_name != "shell"
        ):  # Skip shell as we'll display it differently
            command_table.add_row(f"@{cmd_name}(arg)", processor.description)

    # Add shell command using $() syntax
    shell_processor = command_manager.get_processor("shell")
    if shell_processor:
        command_table.add_row("$(command)", shell_processor.description)

    console.print(command_table)

    console.print("\nUsage:", style="bold")
    console.print(
        '  looplm "your prompt"                        - Use default provider and model'
    )
    console.print(
        '  looplm --provider <n> "prompt"          - Use specific provider with its default model'
    )
    console.print(
        '  looplm --provider <n> --model <n> "prompt" - Use specific provider and model'
    )
    console.print(
        '  looplm --debug "prompt"                   - Debug mode: show processed commands without sending to LLM'
    )
    console.print('\nNote: For custom providers configured as "other", use either:')
    console.print('  looplm --provider other "prompt"           - Using internal name')
    console.print(
        '  looplm --provider <custom_name> "prompt"   - Using your configured name'
    )

    console.print("\nConfiguration:", style="bold")
    console.print("  looplm --configure             - Configure providers")
    console.print("  looplm --reset                - Reset all configuration")
    console.print("  looplm --reset-provider <n> - Reset specific provider")
    console.print("  looplm --set-default <n>   - Set default provider and model")
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
