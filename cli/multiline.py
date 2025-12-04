"""
BharatBuild CLI Multi-line Input Support

Enables Shift+Enter for new lines in prompts:
  > Write a function that:     (Shift+Enter)
    - Takes a list of numbers
    - Returns the sum
"""

from typing import Optional, Callable, List
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.filters import Condition
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.validation import Validator, ValidationError


class MultiLineInputHandler:
    """
    Handles multi-line input with Shift+Enter for new lines.

    Usage:
        handler = MultiLineInputHandler()

        # Get multi-line input
        text = await handler.get_input("❯ ")

        # With custom key bindings
        handler = MultiLineInputHandler(
            submit_key="enter",
            newline_key="shift-enter"
        )
    """

    def __init__(
        self,
        history_file: Optional[str] = None,
        multiline_mode: str = "shift_enter",  # "shift_enter", "escape_enter", "ctrl_enter"
        max_lines: int = 50,
        show_line_numbers: bool = False,
        syntax_highlight: bool = False
    ):
        self.history_file = history_file
        self.multiline_mode = multiline_mode
        self.max_lines = max_lines
        self.show_line_numbers = show_line_numbers
        self.syntax_highlight = syntax_highlight

        # State
        self._multiline_active = False
        self._line_count = 1

        # Create key bindings
        self.key_bindings = self._create_key_bindings()

        # Create session
        self.session = self._create_session()

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for multi-line input"""
        kb = KeyBindings()

        @kb.add('escape', 'enter')
        def escape_enter(event):
            """Escape + Enter = submit in escape_enter mode or newline otherwise"""
            if self.multiline_mode == "escape_enter":
                event.current_buffer.validate_and_handle()
            else:
                event.current_buffer.insert_text('\n')
                self._line_count += 1

        @kb.add('s-enter')  # Shift+Enter
        def shift_enter(event):
            """Shift + Enter = newline in shift_enter mode or submit otherwise"""
            if self.multiline_mode == "shift_enter":
                event.current_buffer.insert_text('\n')
                self._line_count += 1
            else:
                event.current_buffer.validate_and_handle()

        @kb.add('c-enter')  # Ctrl+Enter
        def ctrl_enter(event):
            """Ctrl + Enter = submit in ctrl_enter mode or newline otherwise"""
            if self.multiline_mode == "ctrl_enter":
                event.current_buffer.validate_and_handle()
            else:
                event.current_buffer.insert_text('\n')
                self._line_count += 1

        @kb.add('enter')
        def enter(event):
            """Enter key behavior based on mode"""
            buffer = event.current_buffer
            text = buffer.text

            # In shift_enter mode, Enter submits
            if self.multiline_mode == "shift_enter":
                buffer.validate_and_handle()
            # In ctrl_enter mode, Enter adds newline
            elif self.multiline_mode == "ctrl_enter":
                buffer.insert_text('\n')
                self._line_count += 1
            # In escape_enter mode, Enter adds newline
            elif self.multiline_mode == "escape_enter":
                buffer.insert_text('\n')
                self._line_count += 1

        @kb.add('c-c')
        def cancel(event):
            """Cancel current input"""
            event.current_buffer.reset()
            self._line_count = 1

        @kb.add('c-d')
        def eof(event):
            """Handle Ctrl+D (EOF)"""
            if not event.current_buffer.text:
                event.app.exit(result=None)

        @kb.add('tab')
        def tab_indent(event):
            """Tab for indentation"""
            event.current_buffer.insert_text('    ')  # 4 spaces

        @kb.add('s-tab')
        def shift_tab_dedent(event):
            """Shift+Tab for dedentation"""
            buffer = event.current_buffer
            text = buffer.text
            cursor_pos = buffer.cursor_position

            # Find start of current line
            line_start = text.rfind('\n', 0, cursor_pos) + 1

            # Check if line starts with spaces
            line_text = text[line_start:cursor_pos]
            if line_text.startswith('    '):
                # Remove 4 spaces
                new_text = text[:line_start] + text[line_start + 4:]
                buffer.document = Document(new_text, cursor_pos - 4)
            elif line_text.startswith('  '):
                # Remove 2 spaces
                new_text = text[:line_start] + text[line_start + 2:]
                buffer.document = Document(new_text, cursor_pos - 2)

        return kb

    def _create_session(self) -> PromptSession:
        """Create prompt session with multi-line support"""
        kwargs = {
            'key_bindings': self.key_bindings,
            'multiline': True,
            'enable_history_search': True,
            'auto_suggest': AutoSuggestFromHistory(),
        }

        if self.history_file:
            kwargs['history'] = FileHistory(self.history_file)

        return PromptSession(**kwargs)

    def _get_prompt(self, prompt_text: str) -> HTML:
        """Get prompt with optional line numbers"""
        if self.show_line_numbers and self._line_count > 1:
            return HTML(f'<line_num>{self._line_count:3}</line_num> {prompt_text}')
        return HTML(prompt_text)

    def _get_continuation_prompt(self, width: int, line_number: int, is_soft_wrap: bool) -> str:
        """Get continuation prompt for multi-line input"""
        if self.show_line_numbers:
            return f'{line_number:3} ... '
        return '... '

    async def get_input(
        self,
        prompt_text: str = "❯ ",
        style: Optional[Style] = None
    ) -> Optional[str]:
        """
        Get input from user with multi-line support.

        Returns:
            User input string, or None if cancelled/EOF
        """
        self._line_count = 1

        try:
            result = await self.session.prompt_async(
                self._get_prompt(prompt_text),
                style=style,
                prompt_continuation=self._get_continuation_prompt
            )
            return result
        except (EOFError, KeyboardInterrupt):
            return None

    def get_input_sync(
        self,
        prompt_text: str = "❯ ",
        style: Optional[Style] = None
    ) -> Optional[str]:
        """Synchronous version of get_input"""
        self._line_count = 1

        try:
            result = self.session.prompt(
                self._get_prompt(prompt_text),
                style=style,
                prompt_continuation=self._get_continuation_prompt
            )
            return result
        except (EOFError, KeyboardInterrupt):
            return None


class EnhancedPromptSession:
    """
    Enhanced prompt session with Claude Code-like features.

    Features:
    - Multi-line input (Shift+Enter)
    - Vim/Emacs keybindings
    - Tab completion
    - Syntax highlighting
    - Line numbers
    """

    def __init__(
        self,
        history_file: Optional[str] = None,
        vi_mode: bool = False,
        emacs_mode: bool = True,
        multiline_key: str = "shift_enter",  # "shift_enter", "ctrl_enter", "escape_enter"
        show_line_numbers: bool = False,
        enable_completion: bool = True,
        completion_handler: Optional[Callable] = None
    ):
        self.history_file = history_file
        self.vi_mode = vi_mode
        self.emacs_mode = emacs_mode
        self.multiline_key = multiline_key
        self.show_line_numbers = show_line_numbers
        self.enable_completion = enable_completion
        self.completion_handler = completion_handler

        # Build key bindings
        self.key_bindings = self._build_key_bindings()

        # Build prompt style
        self.prompt_style = Style.from_dict({
            'prompt': '#00D9FF bold',      # Cyan
            'path': '#4ADE80',              # Green
            'git': '#FF79C6',               # Pink
            'line_num': '#737373',          # Dim
            'continuation': '#737373',      # Dim
        })

        # Create session
        from prompt_toolkit.editing_mode import EditingMode

        editing_mode = EditingMode.VI if vi_mode else EditingMode.EMACS

        session_kwargs = {
            'key_bindings': self.key_bindings,
            'style': self.prompt_style,
            'multiline': True,
            'enable_history_search': True,
            'auto_suggest': AutoSuggestFromHistory(),
            'editing_mode': editing_mode,
        }

        if history_file:
            session_kwargs['history'] = FileHistory(history_file)

        self.session = PromptSession(**session_kwargs)

        # State
        self._in_multiline = False

    def _build_key_bindings(self) -> KeyBindings:
        """Build comprehensive key bindings"""
        kb = KeyBindings()

        # Multi-line behavior
        if self.multiline_key == "shift_enter":
            @kb.add('s-enter')
            def newline(event):
                event.current_buffer.insert_text('\n')

            @kb.add('enter')
            def submit(event):
                event.current_buffer.validate_and_handle()

        elif self.multiline_key == "ctrl_enter":
            @kb.add('c-enter')
            def submit(event):
                event.current_buffer.validate_and_handle()

            @kb.add('enter')
            def newline(event):
                event.current_buffer.insert_text('\n')

        elif self.multiline_key == "escape_enter":
            @kb.add('escape', 'enter')
            def submit(event):
                event.current_buffer.validate_and_handle()

            @kb.add('enter')
            def newline(event):
                event.current_buffer.insert_text('\n')

        # Common shortcuts
        @kb.add('c-l')
        def clear_screen(event):
            event.app.renderer.clear()

        @kb.add('c-c')
        def cancel(event):
            event.current_buffer.reset()

        @kb.add('c-w')
        def delete_word(event):
            """Delete word before cursor"""
            buffer = event.current_buffer
            pos = buffer.cursor_position
            text = buffer.text

            # Find word start
            while pos > 0 and text[pos-1].isspace():
                pos -= 1
            while pos > 0 and not text[pos-1].isspace():
                pos -= 1

            buffer.document = Document(
                text[:pos] + text[buffer.cursor_position:],
                pos
            )

        @kb.add('c-u')
        def delete_to_start(event):
            """Delete to start of line"""
            buffer = event.current_buffer
            pos = buffer.cursor_position
            text = buffer.text

            # Find line start
            line_start = text.rfind('\n', 0, pos) + 1

            buffer.document = Document(
                text[:line_start] + text[pos:],
                line_start
            )

        @kb.add('c-k')
        def delete_to_end(event):
            """Delete to end of line"""
            buffer = event.current_buffer
            pos = buffer.cursor_position
            text = buffer.text

            # Find line end
            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)

            buffer.document = Document(
                text[:pos] + text[line_end:],
                pos
            )

        @kb.add('c-a')
        def go_to_start(event):
            """Go to start of line"""
            buffer = event.current_buffer
            pos = buffer.cursor_position
            text = buffer.text

            line_start = text.rfind('\n', 0, pos) + 1
            buffer.cursor_position = line_start

        @kb.add('c-e')
        def go_to_end(event):
            """Go to end of line"""
            buffer = event.current_buffer
            pos = buffer.cursor_position
            text = buffer.text

            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)
            buffer.cursor_position = line_end

        # Tab handling
        @kb.add('tab')
        def handle_tab(event):
            """Tab for completion or indentation"""
            buffer = event.current_buffer

            # If at start of line or after whitespace, indent
            pos = buffer.cursor_position
            text = buffer.text

            if pos == 0 or text[pos-1] in ' \t\n':
                buffer.insert_text('    ')
            else:
                # Trigger completion
                buffer.start_completion(select_first=True)

        return kb

    def _get_continuation(self, width: int, line_number: int, is_soft_wrap: bool) -> str:
        """Get continuation prompt"""
        if self.show_line_numbers:
            return f'{line_number:3} │ '
        return '  │ '

    async def prompt(
        self,
        message: str = "❯ ",
        **kwargs
    ) -> Optional[str]:
        """Get input with all enhanced features"""
        try:
            return await self.session.prompt_async(
                HTML(message),
                prompt_continuation=self._get_continuation,
                **kwargs
            )
        except (EOFError, KeyboardInterrupt):
            return None

    def prompt_sync(
        self,
        message: str = "❯ ",
        **kwargs
    ) -> Optional[str]:
        """Synchronous version"""
        try:
            return self.session.prompt(
                HTML(message),
                prompt_continuation=self._get_continuation,
                **kwargs
            )
        except (EOFError, KeyboardInterrupt):
            return None


# Hint text for multi-line mode
MULTILINE_HINTS = {
    "shift_enter": "[dim]Shift+Enter[/dim] new line  [dim]Enter[/dim] send",
    "ctrl_enter": "[dim]Enter[/dim] new line  [dim]Ctrl+Enter[/dim] send",
    "escape_enter": "[dim]Enter[/dim] new line  [dim]Esc+Enter[/dim] send",
}


def get_multiline_hint(mode: str) -> str:
    """Get hint text for multi-line mode"""
    return MULTILINE_HINTS.get(mode, MULTILINE_HINTS["shift_enter"])
