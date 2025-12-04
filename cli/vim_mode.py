"""
BharatBuild CLI Vim/Emacs Keybindings

Provides Vim and Emacs editing modes for the CLI.
"""

from typing import Optional, Callable, Dict, Any
from enum import Enum

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.filters import Condition, vi_insert_mode, vi_navigation_mode, emacs_mode
from prompt_toolkit.document import Document
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.selection import SelectionType


class EditingMode(str, Enum):
    """Available editing modes"""
    EMACS = "emacs"
    VIM = "vim"
    DEFAULT = "default"


class VimKeyBindings:
    """
    Vim-style key bindings for prompt_toolkit.

    Features:
    - Normal mode (ESC)
    - Insert mode (i, a, o, etc.)
    - Visual mode (v, V)
    - Command mode (:)
    - Motion commands (h, j, k, l, w, b, etc.)
    - Text objects (iw, aw, i", a", etc.)
    - Operators (d, c, y, etc.)
    """

    def __init__(
        self,
        on_mode_change: Optional[Callable[[str], None]] = None
    ):
        self.on_mode_change = on_mode_change
        self._current_mode = "insert"
        self._register = ""  # Yank register
        self._last_search = ""
        self._command_buffer = ""

    def get_key_bindings(self) -> KeyBindings:
        """Get vim key bindings"""
        kb = KeyBindings()

        # ==================== Mode Switching ====================

        @kb.add('escape', filter=vi_insert_mode)
        def enter_normal_mode(event):
            """Enter normal mode"""
            event.app.vi_state.input_mode = 'navigation'
            self._current_mode = "normal"
            if self.on_mode_change:
                self.on_mode_change("normal")

        @kb.add('i', filter=vi_navigation_mode)
        def enter_insert_mode(event):
            """Enter insert mode"""
            event.app.vi_state.input_mode = 'insert'
            self._current_mode = "insert"
            if self.on_mode_change:
                self.on_mode_change("insert")

        @kb.add('a', filter=vi_navigation_mode)
        def enter_insert_after(event):
            """Enter insert mode after cursor"""
            buffer = event.current_buffer
            if buffer.text:
                buffer.cursor_position += 1
            event.app.vi_state.input_mode = 'insert'
            self._current_mode = "insert"
            if self.on_mode_change:
                self.on_mode_change("insert")

        @kb.add('A', filter=vi_navigation_mode)
        def enter_insert_end_of_line(event):
            """Enter insert mode at end of line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            # Move to end of line
            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)
            buffer.cursor_position = line_end

            event.app.vi_state.input_mode = 'insert'
            self._current_mode = "insert"

        @kb.add('I', filter=vi_navigation_mode)
        def enter_insert_start_of_line(event):
            """Enter insert mode at start of line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            # Move to start of line (after whitespace)
            line_start = text.rfind('\n', 0, pos) + 1
            while line_start < len(text) and text[line_start] in ' \t':
                line_start += 1
            buffer.cursor_position = line_start

            event.app.vi_state.input_mode = 'insert'
            self._current_mode = "insert"

        @kb.add('o', filter=vi_navigation_mode)
        def open_line_below(event):
            """Open line below and enter insert mode"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            # Find end of current line
            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)

            # Insert newline
            buffer.document = Document(
                text[:line_end] + '\n' + text[line_end:],
                line_end + 1
            )

            event.app.vi_state.input_mode = 'insert'
            self._current_mode = "insert"

        @kb.add('O', filter=vi_navigation_mode)
        def open_line_above(event):
            """Open line above and enter insert mode"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            # Find start of current line
            line_start = text.rfind('\n', 0, pos)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1

            # Insert newline above
            buffer.document = Document(
                text[:line_start] + '\n' + text[line_start:],
                line_start
            )

            event.app.vi_state.input_mode = 'insert'
            self._current_mode = "insert"

        # ==================== Motion Commands ====================

        @kb.add('h', filter=vi_navigation_mode)
        def move_left(event):
            """Move cursor left"""
            buffer = event.current_buffer
            if buffer.cursor_position > 0:
                buffer.cursor_position -= 1

        @kb.add('l', filter=vi_navigation_mode)
        def move_right(event):
            """Move cursor right"""
            buffer = event.current_buffer
            if buffer.cursor_position < len(buffer.text):
                buffer.cursor_position += 1

        @kb.add('j', filter=vi_navigation_mode)
        def move_down(event):
            """Move cursor down"""
            buffer = event.current_buffer
            buffer.cursor_down()

        @kb.add('k', filter=vi_navigation_mode)
        def move_up(event):
            """Move cursor up"""
            buffer = event.current_buffer
            buffer.cursor_up()

        @kb.add('w', filter=vi_navigation_mode)
        def move_word_forward(event):
            """Move to next word"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            # Skip current word
            while pos < len(text) and not text[pos].isspace():
                pos += 1
            # Skip whitespace
            while pos < len(text) and text[pos].isspace():
                pos += 1

            buffer.cursor_position = pos

        @kb.add('b', filter=vi_navigation_mode)
        def move_word_backward(event):
            """Move to previous word"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            # Skip whitespace backwards
            while pos > 0 and text[pos-1].isspace():
                pos -= 1
            # Skip word backwards
            while pos > 0 and not text[pos-1].isspace():
                pos -= 1

            buffer.cursor_position = pos

        @kb.add('e', filter=vi_navigation_mode)
        def move_word_end(event):
            """Move to end of word"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position + 1

            # Skip whitespace
            while pos < len(text) and text[pos].isspace():
                pos += 1
            # Move to end of word
            while pos < len(text) and not text[pos].isspace():
                pos += 1

            buffer.cursor_position = max(0, pos - 1)

        @kb.add('0', filter=vi_navigation_mode)
        def move_to_line_start(event):
            """Move to start of line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            line_start = text.rfind('\n', 0, pos) + 1
            buffer.cursor_position = line_start

        @kb.add('$', filter=vi_navigation_mode)
        def move_to_line_end(event):
            """Move to end of line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)
            buffer.cursor_position = max(0, line_end - 1) if line_end > 0 else 0

        @kb.add('^', filter=vi_navigation_mode)
        def move_to_first_non_blank(event):
            """Move to first non-blank character"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            line_start = text.rfind('\n', 0, pos) + 1
            while line_start < len(text) and text[line_start] in ' \t':
                line_start += 1

            buffer.cursor_position = line_start

        @kb.add('g', 'g', filter=vi_navigation_mode)
        def move_to_start(event):
            """Move to start of buffer"""
            event.current_buffer.cursor_position = 0

        @kb.add('G', filter=vi_navigation_mode)
        def move_to_end(event):
            """Move to end of buffer"""
            event.current_buffer.cursor_position = len(event.current_buffer.text)

        # ==================== Editing Commands ====================

        @kb.add('x', filter=vi_navigation_mode)
        def delete_char(event):
            """Delete character under cursor"""
            buffer = event.current_buffer
            if buffer.cursor_position < len(buffer.text):
                text = buffer.text
                buffer.document = Document(
                    text[:buffer.cursor_position] + text[buffer.cursor_position + 1:],
                    buffer.cursor_position
                )

        @kb.add('X', filter=vi_navigation_mode)
        def delete_char_before(event):
            """Delete character before cursor"""
            buffer = event.current_buffer
            if buffer.cursor_position > 0:
                text = buffer.text
                pos = buffer.cursor_position
                buffer.document = Document(
                    text[:pos - 1] + text[pos:],
                    pos - 1
                )

        @kb.add('d', 'd', filter=vi_navigation_mode)
        def delete_line(event):
            """Delete entire line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            # Find line boundaries
            line_start = text.rfind('\n', 0, pos)
            line_start = 0 if line_start == -1 else line_start + 1

            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)
            else:
                line_end += 1  # Include newline

            # Store in register
            self._register = text[line_start:line_end]

            # Delete line
            buffer.document = Document(
                text[:line_start] + text[line_end:],
                min(line_start, len(text) - (line_end - line_start))
            )

        @kb.add('d', 'w', filter=vi_navigation_mode)
        def delete_word(event):
            """Delete word"""
            buffer = event.current_buffer
            text = buffer.text
            start = buffer.cursor_position
            end = start

            # Move to end of word
            while end < len(text) and not text[end].isspace():
                end += 1
            # Include trailing whitespace
            while end < len(text) and text[end].isspace():
                end += 1

            self._register = text[start:end]
            buffer.document = Document(
                text[:start] + text[end:],
                start
            )

        @kb.add('c', 'w', filter=vi_navigation_mode)
        def change_word(event):
            """Change word"""
            buffer = event.current_buffer
            text = buffer.text
            start = buffer.cursor_position
            end = start

            # Move to end of word
            while end < len(text) and not text[end].isspace():
                end += 1

            self._register = text[start:end]
            buffer.document = Document(
                text[:start] + text[end:],
                start
            )

            event.app.vi_state.input_mode = 'insert'
            self._current_mode = "insert"

        @kb.add('c', 'c', filter=vi_navigation_mode)
        def change_line(event):
            """Change entire line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            # Find line boundaries
            line_start = text.rfind('\n', 0, pos)
            line_start = 0 if line_start == -1 else line_start + 1

            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)

            self._register = text[line_start:line_end]
            buffer.document = Document(
                text[:line_start] + text[line_end:],
                line_start
            )

            event.app.vi_state.input_mode = 'insert'
            self._current_mode = "insert"

        # ==================== Yank/Paste ====================

        @kb.add('y', 'y', filter=vi_navigation_mode)
        def yank_line(event):
            """Yank (copy) line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            line_start = text.rfind('\n', 0, pos)
            line_start = 0 if line_start == -1 else line_start + 1

            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)
            else:
                line_end += 1

            self._register = text[line_start:line_end]

        @kb.add('y', 'w', filter=vi_navigation_mode)
        def yank_word(event):
            """Yank word"""
            buffer = event.current_buffer
            text = buffer.text
            start = buffer.cursor_position
            end = start

            while end < len(text) and not text[end].isspace():
                end += 1

            self._register = text[start:end]

        @kb.add('p', filter=vi_navigation_mode)
        def paste_after(event):
            """Paste after cursor"""
            buffer = event.current_buffer
            if self._register:
                pos = buffer.cursor_position + 1
                text = buffer.text
                buffer.document = Document(
                    text[:pos] + self._register + text[pos:],
                    pos + len(self._register) - 1
                )

        @kb.add('P', filter=vi_navigation_mode)
        def paste_before(event):
            """Paste before cursor"""
            buffer = event.current_buffer
            if self._register:
                pos = buffer.cursor_position
                text = buffer.text
                buffer.document = Document(
                    text[:pos] + self._register + text[pos:],
                    pos + len(self._register) - 1
                )

        # ==================== Undo/Redo ====================

        @kb.add('u', filter=vi_navigation_mode)
        def undo(event):
            """Undo"""
            event.current_buffer.undo()

        @kb.add('c-r', filter=vi_navigation_mode)
        def redo(event):
            """Redo"""
            event.current_buffer.redo()

        # ==================== Search ====================

        @kb.add('/', filter=vi_navigation_mode)
        def search_forward(event):
            """Start forward search"""
            # This would need a search prompt implementation
            pass

        @kb.add('n', filter=vi_navigation_mode)
        def next_search(event):
            """Go to next search match"""
            pass

        @kb.add('N', filter=vi_navigation_mode)
        def prev_search(event):
            """Go to previous search match"""
            pass

        return kb

    @property
    def mode(self) -> str:
        """Get current vim mode"""
        return self._current_mode


class EmacsKeyBindings:
    """
    Emacs-style key bindings for prompt_toolkit.

    Features:
    - Movement (C-a, C-e, C-f, C-b, etc.)
    - Editing (C-k, C-w, C-y, etc.)
    - Search (C-s, C-r)
    """

    def __init__(self):
        self._kill_ring = []

    def get_key_bindings(self) -> KeyBindings:
        """Get emacs key bindings"""
        kb = KeyBindings()

        # Movement
        @kb.add('c-a', filter=emacs_mode)
        def beginning_of_line(event):
            """Move to beginning of line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position
            line_start = text.rfind('\n', 0, pos) + 1
            buffer.cursor_position = line_start

        @kb.add('c-e', filter=emacs_mode)
        def end_of_line(event):
            """Move to end of line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position
            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)
            buffer.cursor_position = line_end

        @kb.add('c-f', filter=emacs_mode)
        def forward_char(event):
            """Move forward one character"""
            buffer = event.current_buffer
            if buffer.cursor_position < len(buffer.text):
                buffer.cursor_position += 1

        @kb.add('c-b', filter=emacs_mode)
        def backward_char(event):
            """Move backward one character"""
            buffer = event.current_buffer
            if buffer.cursor_position > 0:
                buffer.cursor_position -= 1

        @kb.add('escape', 'f', filter=emacs_mode)
        def forward_word(event):
            """Move forward one word"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            while pos < len(text) and not text[pos].isalnum():
                pos += 1
            while pos < len(text) and text[pos].isalnum():
                pos += 1

            buffer.cursor_position = pos

        @kb.add('escape', 'b', filter=emacs_mode)
        def backward_word(event):
            """Move backward one word"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            while pos > 0 and not text[pos-1].isalnum():
                pos -= 1
            while pos > 0 and text[pos-1].isalnum():
                pos -= 1

            buffer.cursor_position = pos

        # Editing
        @kb.add('c-k', filter=emacs_mode)
        def kill_line(event):
            """Kill to end of line"""
            buffer = event.current_buffer
            text = buffer.text
            pos = buffer.cursor_position

            line_end = text.find('\n', pos)
            if line_end == -1:
                line_end = len(text)

            killed = text[pos:line_end]
            self._kill_ring.append(killed)

            buffer.document = Document(
                text[:pos] + text[line_end:],
                pos
            )

        @kb.add('c-w', filter=emacs_mode)
        def kill_region(event):
            """Kill region (selected text)"""
            buffer = event.current_buffer
            if buffer.selection_state:
                # Get selection
                start, end = buffer.document.selection_range()
                killed = buffer.text[start:end]
                self._kill_ring.append(killed)

                buffer.document = Document(
                    buffer.text[:start] + buffer.text[end:],
                    start
                )

        @kb.add('c-y', filter=emacs_mode)
        def yank(event):
            """Yank (paste) from kill ring"""
            if self._kill_ring:
                buffer = event.current_buffer
                pos = buffer.cursor_position
                text_to_insert = self._kill_ring[-1]

                buffer.document = Document(
                    buffer.text[:pos] + text_to_insert + buffer.text[pos:],
                    pos + len(text_to_insert)
                )

        @kb.add('c-d', filter=emacs_mode)
        def delete_char(event):
            """Delete character under cursor"""
            buffer = event.current_buffer
            if buffer.cursor_position < len(buffer.text):
                text = buffer.text
                pos = buffer.cursor_position
                buffer.document = Document(
                    text[:pos] + text[pos+1:],
                    pos
                )

        @kb.add('escape', 'd', filter=emacs_mode)
        def kill_word(event):
            """Kill word forward"""
            buffer = event.current_buffer
            text = buffer.text
            start = buffer.cursor_position
            end = start

            while end < len(text) and text[end].isalnum():
                end += 1
            while end < len(text) and not text[end].isalnum():
                end += 1

            killed = text[start:end]
            self._kill_ring.append(killed)

            buffer.document = Document(
                text[:start] + text[end:],
                start
            )

        # Undo
        @kb.add('c-/', filter=emacs_mode)
        @kb.add('c-_', filter=emacs_mode)
        def undo(event):
            """Undo"""
            event.current_buffer.undo()

        return kb


def get_editing_mode_bindings(mode: EditingMode) -> KeyBindings:
    """Get key bindings for specified editing mode"""
    if mode == EditingMode.VIM:
        return VimKeyBindings().get_key_bindings()
    elif mode == EditingMode.EMACS:
        return EmacsKeyBindings().get_key_bindings()
    else:
        return KeyBindings()  # Default/empty


def get_mode_indicator(mode: EditingMode, vim_mode: str = "insert") -> str:
    """Get mode indicator for status line"""
    if mode == EditingMode.VIM:
        indicators = {
            "normal": "[bold blue]NORMAL[/bold blue]",
            "insert": "[bold green]INSERT[/bold green]",
            "visual": "[bold magenta]VISUAL[/bold magenta]",
            "command": "[bold yellow]COMMAND[/bold yellow]",
        }
        return indicators.get(vim_mode, "[dim]--[/dim]")
    elif mode == EditingMode.EMACS:
        return "[dim]EMACS[/dim]"
    else:
        return ""
