# src/looplm/cli/chat.py
import click
from rich.console import Console
from ..conversation.handler import ConversationHandler

console = Console()


@click.command()
@click.argument("prompt", required=True)
@click.option("--model", help="Override default model for this request")
def chat(prompt: str, model: str = None):
    """Send a prompt to the configured LLM and stream the response

    Args:
        prompt: The prompt to send to the LLM
        model: Optional model override
    """
    try:
        handler = ConversationHandler(console)
        handler.handle_prompt(prompt, model)
    except Exception as e:
        console.print(f"\nFailed to process request: {str(e)}", style="bold red")
        raise click.Abort()
