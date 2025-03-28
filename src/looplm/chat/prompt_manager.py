# src/looplm/chat/prompt_manager.py - Updated for new command system

import os
from pathlib import Path
from typing import List, Optional, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import ANSI
from rich.console import Console
from looplm.commands import CommandManager


class CommandCompleter(Completer):
    """Completer for @ commands with context-aware completion"""

    def __init__(self, base_path: Path = None):
        """Initialize completer with command manager
        
        Args:
            base_path: Base path for resolving relative paths
        """
        # Use the singleton CommandManager instead of creating a new registry
        self.command_manager = CommandManager(base_path=base_path or Path.cwd())

    def get_completions(self, document, complete_event):
        """Get completions for current input
        
        Args:
            document: Current document
            complete_event: Completion event
            
        Returns:
            Generator of completions
        """
        text = document.text_before_cursor
        
        # Find any @ symbol before cursor
        at_pos = text.rfind('@')
        if at_pos == -1:
            return
            
        # Get text after @ symbol
        after_at = text[at_pos:]
        
        # Calculate start position
        if '(' in after_at:
            cmd_name = after_at[1:after_at.find('(')]
            path_text = after_at[after_at.find('(')+1:]
            # Get processor for command
            processor = self.command_manager.get_processor(cmd_name)
            if processor:
                # Get completion from processor
                completions = processor.get_completions(path_text)
                # start position calculation
                start_pos = -len(path_text)

                for completion_tuple in completions:
                    if isinstance(completion_tuple, tuple):
                        completion_text, display_text = completion_tuple
                        yield Completion(
                            completion_text,
                            start_position=start_pos,
                            display=ANSI(display_text),
                        )
                    else:
                        # Handle case where completion isn't a tuple
                        yield Completion(
                            completion_tuple,
                            start_position=start_pos
                        )
                
        else:
            # Get completions from the registry's get_completions method
            completions = self.command_manager.registry.get_completions(after_at)
            for completion in completions:
                yield Completion(
                    completion,
                    start_position=-len(after_at),
                )


class PromptManager:
    """Manages prompt toolkit integration with custom completions"""

    def __init__(self, console: Console = None, base_path: str = None):
        """Initialize prompt manager
        
        Args:
            console: Optional rich console for output
            base_path: Base path for resolving file paths
        """
        self.console = console or Console()
        self.base_path = base_path or os.getcwd()
        
        # Setup prompt styling
        self.style = Style.from_dict({
            "prompt": "#0000ff bold",
            "timestamp": "#666666",
        })

        # Setup history
        history_file = os.path.expanduser("~/.looplm/history")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        # Setup key bindings
        kb = KeyBindings()
        
        @kb.add('(')
        def _(event):
            """ Auto-close parentheses """
            event.current_buffer.insert_text('()')
            event.current_buffer.cursor_left()
            event.current_buffer.start_completion()

        @kb.add('"')
        def _(event):
            """ Auto-close quotes """
            buf = event.current_buffer
            if buf.document.current_char == '"':
                buf.cursor_right()
            else:
                buf.insert_text('""')
                buf.cursor_left()
        
        @kb.add('/')
        def _(event):
            """Auto-trigger completion after slash in paths""" 
            event.current_buffer.insert_text('/')
            event.current_buffer.start_completion()

        # Initialize prompt session with command completion
        self.session = PromptSession(
            history=FileHistory(history_file),
            auto_suggest=AutoSuggestFromHistory(),
            completer=CommandCompleter(base_path=Path(self.base_path)),
            style=self.style,
            complete_while_typing=True,
            key_bindings=kb,
            complete_in_thread=True,
        )

    def create_prompt_fragments(self, prompt_str: str):
        """Create styled prompt fragments"""
        return [
            ("class:timestamp", prompt_str[:5]),  # timestamp
            ("", " "),
            ("class:prompt", "User ► ")
        ]

    def get_input(self, prompt_str: str = "", key_bindings=None) -> str:
        """Get user input with completion and history"""
        try:
            if key_bindings:
                combined_bindings = KeyBindings()

                # Copy existing bindings
                if self.session.key_bindings:
                    for binding in self.session.key_bindings.bindings:
                        combined_bindings.add(*binding.keys)(binding.handler)

                # Add new bindings
                for binding in key_bindings.bindings:
                    combined_bindings.add(*binding.keys)(binding.handler)
                kb = combined_bindings
            
            else:
                kb = self.session.key_bindings

            result = self.session.prompt(
                self.create_prompt_fragments(prompt_str),
                style=self.style,
                complete_in_thread=True,
                key_bindings=kb
            )
            return result.strip()
        except KeyboardInterrupt:
            return ""
        except EOFError:
            return "exit"