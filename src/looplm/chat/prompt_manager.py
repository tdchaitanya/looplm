# src/looplm/chat/prompt_manager.py
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
from typing import List, Optional
from prompt_toolkit.completion import Completer, Completion
from .commands.registry import CommandRegistry
from .commands.file_command import FileProcessor
from .commands.folder_command import FolderProcessor
from .commands.github_command import GithubProcessor

class CommandCompleter(Completer):
    """Completer for @ commands with context-aware completion"""

    def __init__(self, registry: CommandRegistry):
        """Initialize completer with command registry
        
        Args:
            command_registry: Registry of available commands
        """
        self.registry = registry

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
            processor = self.registry.get_processor(cmd_name)
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
            completions = self.registry.get_completions(after_at)
            for completion in completions:
                yield Completion(
                    completion,
                    start_position=-len(after_at),
                )



class FilePathCompleter(Completer):
    """Completer for @file directives with path completion"""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.getcwd())
        self.additional_paths = [Path.cwd(), Path.home()]
        if self.base_path not in self.additional_paths:
            self.additional_paths.append(self.base_path)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        
        if "@file" not in text:
            return

        # Find the position after @file
        file_pos = text.rfind("@file")
        after_file = text[file_pos:]
        
        # Get the word being completed
        if '("' in after_file:
            word_start = after_file.find('("') + 2
            closing = '")'
        elif "(" in after_file:
            word_start = after_file.find('(') + 1
            closing = ')'
        else:
            word_start = len("@file ")
            if len(after_file) <= word_start:
                yield Completion('(', start_position=0)
                return
            closing = ''
            
        # Get the path being completed
        current_input = after_file[word_start:]
        path = current_input.split(closing)[0] if closing in current_input else current_input
        path = path.strip()

        # Get completions from all base paths
        seen = set()
        for base_dir in self.additional_paths:
            try:
                # Get all matching files
                pattern = f"*{path}*" if path else "*"
                for file_path in base_dir.glob(pattern):
                    if file_path.name in seen:
                        continue
                        
                    seen.add(file_path.name)
                    rel_path = str(file_path.relative_to(base_dir))
                    
                    if path and not rel_path.startswith(path):
                        continue
                        
                    # If it's an exact match, don't yield completion
                    if rel_path == path:
                        continue

                    # Add closing characters for files
                    display_meta = str(file_path)
                    if file_path.is_file() and closing and closing not in current_input:
                        rel_path += closing
                    
                    # Calculate the start position to replace only what needs to be replaced
                    replace_start = -len(path) if path else 0
                    
                    yield Completion(
                        rel_path,
                        start_position=replace_start,
                        display=file_path.name,
                        display_meta=display_meta
                    )
            except Exception:
                continue


class PromptManager:
    """Manages prompt toolkit integration with custom completions"""

    def __init__(self, console: Console = None, base_path: str = None):
        self.console = console or Console()
        self.base_path = base_path or os.getcwd()
        
        # Initialize command registry
        self.command_registry = CommandRegistry(base_path=Path(self.base_path))
        
        # Register command processors
        self.command_registry.register(FileProcessor)
        self.command_registry.register(FolderProcessor)
        self.command_registry.register(GithubProcessor)
        
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
            completer=CommandCompleter(self.command_registry),
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