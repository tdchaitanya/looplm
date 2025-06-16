"""
Compact Handler for LoopLM Chat Sessions

This module provides a dedicated handler for the compact functionality,
which summarizes conversations to reduce token usage while preserving
the complete conversation history.
"""

import logging
from typing import Dict, List, Tuple

from litellm import completion
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config.providers import ProviderType
from .prompt_manager import PromptManager
from .session import ChatSession

logger = logging.getLogger(__name__)


class CompactError(Exception):
    """Custom exception for compact-related errors"""


class CompactHandler:
    """Handles conversation compacting functionality"""

    def __init__(self, console, prompt_manager: PromptManager):
        """Initialize the compact handler

        Args:
            console: ChatConsole for output (has console.console for Rich Console)
            prompt_manager: Manager for prompts
        """
        self.console = console
        self.prompt_manager = prompt_manager

    def can_compact(self, session: ChatSession) -> Tuple[bool, str]:
        """Check if a session can be compacted

        Args:
            session: The chat session to check

        Returns:
            Tuple of (can_compact, reason)
        """
        if not session:
            return False, "No active session"

        if session.is_compacted:
            return False, "Session is already compacted"

        # Exclude system messages for counting
        non_system_messages = [msg for msg in session.messages if msg.role != "system"]

        if len(non_system_messages) < 2:
            return (
                False,
                "Not enough messages to compact (need at least 2 non-system messages)",
            )

        return True, "Session can be compacted"

    def get_compact_stats(self, session: ChatSession) -> Dict:
        """Get statistics about what would be compacted

        Args:
            session: The chat session

        Returns:
            Dictionary with compaction statistics
        """
        if not session:
            return {}

        non_system_messages = [msg for msg in session.messages if msg.role != "system"]

        # Calculate current token usage for messages that would be compacted
        current_tokens = 0
        for msg in non_system_messages:
            if msg.token_usage:
                current_tokens += msg.token_usage.total_tokens
            else:
                # Rough estimation: 4 chars per token
                current_tokens += len(msg.content) // 4

        return {
            "total_messages": len(session.messages),
            "non_system_messages": len(non_system_messages),
            "estimated_current_tokens": current_tokens,
            "system_prompt": session.get_system_prompt() is not None,
        }

    def _resolve_model_name(self, session: ChatSession) -> str:
        """Resolve the correct model name for the session

        Args:
            session: The chat session

        Returns:
            Resolved model name

        Raises:
            CompactError: If model resolution fails
        """
        try:
            if session.provider == ProviderType.OTHER and session.custom_provider:
                if not session.model.startswith(f"{session.custom_provider}/"):
                    return f"{session.custom_provider}/{session.model}"
                else:
                    return session.model
            else:
                provider_prefix = (
                    f"{session.provider.value}/" if session.provider else ""
                )
                if (
                    session.model
                    and provider_prefix
                    and session.model.startswith(provider_prefix)
                ):
                    return session.model
                elif session.provider and session.provider in [
                    ProviderType.GEMINI,
                    ProviderType.BEDROCK,
                    ProviderType.AZURE,
                ]:
                    return f"{session.provider.value}/{session.model}"
                else:
                    return session.model
        except Exception as e:
            raise CompactError(f"Failed to resolve model name: {str(e)}")

    def _prepare_compact_messages(self, session: ChatSession) -> List[Dict[str, str]]:
        """Prepare messages for the compact LLM call

        Args:
            session: The chat session

        Returns:
            List of messages for the LLM
        """
        # Get all non-system messages
        prev_msgs = [msg for msg in session.messages if msg.role != "system"]

        # Use the current system prompt or default
        system_prompt = (
            session.get_system_prompt() or "You are LoopLM, a helpful assistant."
        )

        # Get the compact prompt
        try:
            compact_prompt = self.prompt_manager.get_prompt("compact")
        except (KeyError, AttributeError):
            # Fallback if compact prompt is not found
            compact_prompt = (
                "Please provide a comprehensive summary of this conversation."
            )
            logger.warning("Compact prompt not found, using fallback")

        # Prepare messages for LLM
        llm_messages = [{"role": "system", "content": system_prompt}]

        for msg in prev_msgs:
            llm_messages.append({"role": msg.role, "content": msg.content})

        llm_messages.append({"role": "user", "content": compact_prompt})

        return llm_messages

    def compact_session(self, session: ChatSession, show_progress: bool = True) -> bool:
        """Compact a chat session by generating a summary

        Args:
            session: The chat session to compact
            show_progress: Whether to show progress indicator

        Returns:
            True if successful, False otherwise
        """
        # Validate session can be compacted
        can_compact, reason = self.can_compact(session)
        if not can_compact:
            self.console.display_error(f"Cannot compact session: {reason}")
            return False

        # Show statistics before compacting
        stats = self.get_compact_stats(session)
        self.console.display_info(
            f"Compacting {stats['non_system_messages']} messages "
            f"(~{stats['estimated_current_tokens']:,} tokens)",
            "dim",
        )

        try:
            # Resolve model name
            actual_model = self._resolve_model_name(session)

            # Prepare messages
            llm_messages = self._prepare_compact_messages(session)

            # Make LLM call with progress indication
            if show_progress:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console.console,
                    transient=True,
                ) as progress:
                    task = progress.add_task("Generating summary...", total=None)
                    summary = self._call_llm_for_summary(actual_model, llm_messages)
            else:
                summary = self._call_llm_for_summary(actual_model, llm_messages)

            # Set the compact summary
            session.set_compact_summary(summary)

            # Calculate estimated token savings
            estimated_savings = stats["estimated_current_tokens"] - (len(summary) // 4)

            # Success message
            self.console.display_success("✓ Conversation compacted successfully!")
            self.console.display_info(
                f"Estimated token savings: ~{estimated_savings:,} tokens", "dim"
            )

            # Show summary with nice formatting
            self.console.console.print("\n[bold blue]Generated Summary:[/bold blue]")
            self.console.console.print(f"[dim]{'-' * 50}[/dim]")
            self.console.console.print(summary)
            self.console.console.print(f"[dim]{'-' * 50}[/dim]")

            return True

        except CompactError as e:
            self.console.display_error(f"Compact error: {str(e)}")
            return False
        except Exception as e:
            logger.exception("Unexpected error during compact")
            self.console.display_error(f"Unexpected error during compact: {str(e)}")
            return False

    def _call_llm_for_summary(self, model: str, messages: List[Dict[str, str]]) -> str:
        """Make the actual LLM call to generate summary

        Args:
            model: Model name to use
            messages: Messages to send to LLM

        Returns:
            Generated summary

        Raises:
            CompactError: If LLM call fails
        """
        try:
            response = completion(model=model, messages=messages)

            if not response.choices or not response.choices[0].message:
                raise CompactError("Empty response from LLM")

            raw_summary = response.choices[0].message.content

            if not raw_summary or raw_summary.strip() == "":
                raise CompactError("LLM returned empty summary")

            # Try to extract content between <summary> tags
            parsed_summary = self._extract_summary_content(raw_summary)

            return parsed_summary

        except Exception as e:
            if "CompactError" in str(type(e)):
                raise
            raise CompactError(f"LLM call failed: {str(e)}")

    def _extract_summary_content(self, raw_response: str) -> str:
        """Extract summary content from LLM response

        Args:
            raw_response: Raw response from LLM

        Returns:
            Extracted summary content
        """
        import re

        # Try to find content between <summary> tags (case insensitive)
        summary_match = re.search(
            r"<summary>\s*(.*?)\s*</summary>", raw_response, re.DOTALL | re.IGNORECASE
        )

        if summary_match:
            extracted_content = summary_match.group(1).strip()
            if extracted_content:
                logger.info("Successfully extracted summary from structured response")
                return extracted_content
            else:
                logger.warning("Found summary tags but content was empty")
        else:
            logger.info("No summary tags found, using full response as fallback")

        # Fallback: use the entire response but clean it up
        cleaned_response = raw_response.strip()

        # Remove any analysis sections that might be at the beginning
        analysis_pattern = r"<analysis>.*?</analysis>\s*"
        cleaned_response = re.sub(
            analysis_pattern, "", cleaned_response, flags=re.DOTALL | re.IGNORECASE
        )

        # If we still have summary tags visible in the output, warn about it
        if (
            "<summary>" in cleaned_response.lower()
            or "</summary>" in cleaned_response.lower()
        ):
            logger.warning(
                "Summary tags are visible in output - LLM may not have followed instructions properly"
            )

        return cleaned_response.strip()

    def reset_compact(self, session: ChatSession) -> bool:
        """Reset compact state for a session

        Args:
            session: The chat session

        Returns:
            True if successful
        """
        if not session:
            self.console.display_error("No active session")
            return False

        if not session.is_compacted:
            self.console.display_info("Session is not currently compacted", "yellow")
            return True

        session.reset_compact()
        self.console.display_success(
            "✓ Compact state reset. Full conversation history will be used."
        )
        return True

    def show_compact_info(self, session: ChatSession) -> None:
        """Show information about the compact state

        Args:
            session: The chat session
        """
        if not session:
            self.console.display_error("No active session")
            return

        stats = self.get_compact_stats(session)

        self.console.console.print("\n[bold blue]Compact Information:[/bold blue]")
        self.console.console.print(f"Total messages: {stats['total_messages']}")
        self.console.console.print(
            f"Non-system messages: {stats['non_system_messages']}"
        )
        self.console.console.print(
            f"Estimated tokens: ~{stats['estimated_current_tokens']:,}"
        )

        if session.is_compacted:
            self.console.console.print("[green]Status: Compacted[/green]")
            self.console.console.print(
                f"Messages before compact: {session.compact_index}"
            )
            self.console.console.print(
                f"Summary length: {len(session.compact_summary) if session.compact_summary else 0} chars"
            )
        else:
            self.console.console.print("[yellow]Status: Not compacted[/yellow]")
            can_compact, reason = self.can_compact(session)
            if can_compact:
                self.console.console.print("[green]Can compact: Yes[/green]")
            else:
                self.console.console.print(f"[red]Can compact: No ({reason})[/red]")
