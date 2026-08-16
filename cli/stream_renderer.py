"""
BharatBuild CLI — Live Streaming Markdown Renderer
====================================================
Mirrors Goose/Kiro's streaming_buffer.rs logic in Python.

How it works
------------
Text chunks arrive one at a time from the SSE stream.
Instead of printing immediately (which produces broken **bold or
unclosed `code spans`), we accumulate text and only flush up to the
last "safe" byte — a position where no markdown construct is open.

Safe positions:
  • End of any line where parse state is clean
  • After a closing code-fence line
  • After a closing inline construct (bold, italic, code, link)

Usage
-----
    renderer = StreamingMarkdownRenderer(console)
    renderer.start()

    async for event in client.stream_sse(...):
        if event["type"] == "text":
            renderer.push(event.get("data", {}).get("content", ""))
        elif event["type"] == "complete":
            break

    renderer.finish()   # flushes any remaining buffer
"""

from __future__ import annotations

import re
import sys
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text


# ── inline token regex (mirrors Goose's INLINE_TOKEN_RE) ────────────────────
_TOKEN_RE = re.compile(
    r"(\\."              # escaped char  — highest priority
    r"|`+"               # inline code   — variable backtick length
    r"|\*\*\*"           # bold + italic
    r"|\*\*"             # bold
    r"|\*"               # italic
    r"|___"              # bold + italic (underscore)
    r"|__"               # bold (underscore)
    r"|_"                # italic (underscore)
    r"|~~"               # strikethrough
    r"|\!\["             # image start
    r"|\]\("             # link URL start
    r"|\["               # link text start
    r"|\]"               # bracket close
    r"|\)"               # link URL end / paren close
    r"|[^\\\*_`~\[\]!()]+" # plain text
    r"|.)"               # any other single char
)


# ── parse state ──────────────────────────────────────────────────────────────

class _ParseState:
    """Tracks which markdown constructs are currently open."""

    __slots__ = (
        "in_code_block", "code_fence_char", "code_fence_len",
        "in_table", "pending_heading",
        "in_inline_code", "inline_code_len",
        "in_bold", "in_italic", "in_strikethrough",
        "in_link_text", "in_link_url", "in_image_alt",
    )

    def __init__(self):
        self.in_code_block    = False
        self.code_fence_char  = ""
        self.code_fence_len   = 0
        self.in_table         = False
        self.pending_heading  = False
        self.in_inline_code   = False
        self.inline_code_len  = 0
        self.in_bold          = False
        self.in_italic        = False
        self.in_strikethrough = False
        self.in_link_text     = False
        self.in_link_url      = False
        self.in_image_alt     = False

    def is_clean(self) -> bool:
        return not any([
            self.in_code_block, self.in_table, self.pending_heading,
            self.in_inline_code, self.in_bold, self.in_italic,
            self.in_strikethrough, self.in_link_text,
            self.in_link_url, self.in_image_alt,
        ])

    def copy(self) -> "_ParseState":
        s = _ParseState()
        for attr in self.__slots__:
            setattr(s, attr, getattr(self, attr))
        return s


# ── streaming markdown buffer ─────────────────────────────────────────────────

class MarkdownStreamBuffer:
    """
    Accumulates streaming text and yields only complete markdown segments.

    Call push(chunk) → get back a string to render (or None if still buffering).
    Call flush()     → force-render everything left (end of stream).
    """

    def __init__(self):
        self._buf   = ""
        self._state = _ParseState()
        self._last_safe = 0   # byte offset of last clean position

    # ── public API ────────────────────────────────────────────────────────────

    def push(self, chunk: str) -> Optional[str]:
        """Add a chunk. Returns renderable text or None."""
        self._buf += chunk
        safe_end = self._find_safe_end()
        if safe_end > 0:
            out      = self._buf[:safe_end]
            self._buf = self._buf[safe_end:]
            # reset after drain
            self._state     = _ParseState()
            self._last_safe = 0
            return out
        return None

    def flush(self) -> str:
        """Return everything remaining (even if constructs are open)."""
        out       = self._buf
        self._buf = ""
        self._state     = _ParseState()
        self._last_safe = 0
        return out

    # ── scanning ──────────────────────────────────────────────────────────────

    def _find_safe_end(self) -> int:
        """Return the last byte offset that is safe to flush up to."""
        buf   = self._buf
        size  = len(buf)
        state = _ParseState()          # full rescan each call (simple & correct)
        last_safe = 0
        pos   = 0

        while pos < size:
            at_line_start = (pos == 0 or buf[pos - 1] == "\n")

            if at_line_start:
                new_pos = self._process_line_start(buf, pos, size, state)
                if new_pos is not None:
                    pos = new_pos
                    if state.is_clean():
                        last_safe = pos
                    continue

            if state.in_code_block:
                # skip to next newline inside code block
                nl = buf.find("\n", pos)
                pos = (nl + 1) if nl != -1 else size
                continue

            # find end of current line
            nl = buf.find("\n", pos)
            line_end = (nl + 1) if nl != -1 else size
            line = buf[pos:line_end]

            for m in _TOKEN_RE.finditer(line):
                token     = m.group(0)
                token_end = pos + m.end()
                self._process_inline_token(state, token)
                if state.is_clean():
                    last_safe = token_end

            if nl != -1:
                state.pending_heading = False
                if state.is_clean():
                    last_safe = line_end

            pos = line_end

        return last_safe

    # ── line-start block detection ────────────────────────────────────────────

    def _process_line_start(
        self, buf: str, pos: int, size: int, state: _ParseState
    ) -> Optional[int]:
        remaining = buf[pos:]

        if state.pending_heading:
            state.pending_heading = False

        # code fence
        result = self._check_code_fence(remaining, state)
        if result is not None:
            return pos + result

        if state.in_code_block:
            return None

        # heading
        if remaining.startswith("#"):
            hashes = len(remaining) - len(remaining.lstrip("#"))
            if 1 <= hashes <= 6:
                after = remaining[hashes:]
                if not after or after[0] in (" ", "\n"):
                    state.pending_heading = True
                    return None

        # table row
        if remaining.startswith("|"):
            state.in_table = True
            return None

        # blank line ends table
        if remaining.startswith("\n") and state.in_table:
            state.in_table = False
            return pos + 1

        if not remaining.startswith("|") and state.in_table:
            state.in_table = False

        return None

    def _check_code_fence(
        self, line: str, state: _ParseState
    ) -> Optional[int]:
        stripped = line.lstrip()
        if not stripped:
            return None
        fc = stripped[0]
        if fc not in ("`", "~"):
            return None

        fence_len = len(stripped) - len(stripped.lstrip(fc))
        if fence_len < 3:
            return None

        after = stripped[fence_len:]

        if state.in_code_block:
            if (fc == state.code_fence_char
                    and fence_len >= state.code_fence_len
                    and (not after or after.strip() == "")):
                state.in_code_block   = False
                state.code_fence_char = ""
                state.code_fence_len  = 0
                nl = line.find("\n")
                return (nl + 1) if nl != -1 else len(line)
        else:
            state.in_code_block   = True
            state.code_fence_char = fc
            state.code_fence_len  = fence_len
            nl = line.find("\n")
            return (nl + 1) if nl != -1 else len(line)

        return None

    # ── inline token state machine ────────────────────────────────────────────

    @staticmethod
    def _process_inline_token(state: _ParseState, token: str) -> None:
        # escaped char
        if token.startswith("\\") and len(token) == 2:
            return

        # inline code
        if token.startswith("`"):
            tl = len(token)
            if state.in_inline_code:
                if tl == state.inline_code_len:
                    state.in_inline_code = False
                    state.inline_code_len = 0
            else:
                state.in_inline_code  = True
                state.inline_code_len = tl
            return

        if state.in_inline_code:
            return

        if token in ("***", "___"):
            if state.in_bold and state.in_italic:
                state.in_bold = state.in_italic = False
            elif state.in_bold:
                state.in_italic = not state.in_italic
            elif state.in_italic:
                state.in_bold = not state.in_bold
            else:
                state.in_bold = state.in_italic = True
        elif token in ("**", "__"):
            state.in_bold = not state.in_bold
        elif token in ("*", "_"):
            state.in_italic = not state.in_italic
        elif token == "~~":
            state.in_strikethrough = not state.in_strikethrough
        elif token == "![":
            state.in_image_alt = True
        elif token == "[":
            if not state.in_link_text and not state.in_image_alt:
                state.in_link_text = True
        elif token == "](" :
            if state.in_link_text:
                state.in_link_text = False
                state.in_link_url  = True
            elif state.in_image_alt:
                state.in_image_alt = False
                state.in_link_url  = True
        elif token == ")" and state.in_link_url:
            state.in_link_url = False


# ── rich terminal renderer ────────────────────────────────────────────────────

class StreamingMarkdownRenderer:
    """
    Wraps MarkdownStreamBuffer and renders safe chunks to a Rich Console.

    Kiro-style behaviour:
      • Plain text renders inline as it arrives
      • Complete markdown blocks (code fences, bold, links) render via
        rich.Markdown for proper syntax highlighting
      • A thinking spinner shows while waiting for first token
      • Token counter updates after each chunk
    """

    # extensions that get syntax highlighting
    _EXT_MAP = {
        ".py": "python",   ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript",".jsx":"javascript", ".html": "html",
        ".css": "css",     ".json": "json",      ".yaml": "yaml",
        ".yml": "yaml",    ".toml": "toml",      ".md": "markdown",
        ".sh":  "bash",    ".sql": "sql",        ".rs": "rust",
        ".go":  "go",      ".java": "java",      ".kt": "kotlin",
    }

    def __init__(self, console: Console, show_token_count: bool = True):
        self.console          = console
        self.show_token_count = show_token_count
        self._buffer          = MarkdownStreamBuffer()
        self._token_count     = 0
        self._first_token     = True
        self._spinner         = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Call before streaming begins — shows the thinking spinner."""
        self._first_token = True
        self._token_count = 0
        self._spinner = self.console.status(
            "[dim cyan]thinking…[/dim cyan]", spinner="dots"
        )
        self._spinner.__enter__()

    def push(self, chunk: str) -> None:
        """Feed a text chunk from the stream."""
        if not chunk:
            return

        # hide spinner on first real token
        if self._first_token and chunk.strip():
            self._first_token = False
            if self._spinner:
                self._spinner.__exit__(None, None, None)
                self._spinner = None
            self.console.print()  # blank line before response

        self._token_count += len(chunk.split())

        safe = self._buffer.push(chunk)
        if safe:
            self._render(safe)

    def finish(self) -> None:
        """Call when the stream ends — flushes remaining buffer."""
        # stop spinner if it never fired
        if self._spinner:
            self._spinner.__exit__(None, None, None)
            self._spinner = None

        remaining = self._buffer.flush()
        if remaining:
            self._render(remaining)

        if self.show_token_count and self._token_count:
            self.console.print(
                f"\n[dim]~{self._token_count:,} tokens[/dim]"
            )
        self.console.print()

    # ── rendering ─────────────────────────────────────────────────────────────

    def _render(self, text: str) -> None:
        """
        Choose the best rendering strategy for a chunk:
          - Fenced code block  → Syntax with language detection
          - Other markdown     → rich.Markdown
          - Plain text         → direct print (fastest)
        """
        if not text.strip():
            self.console.print(text, end="", highlight=False)
            return

        # detect fenced code block
        if "```" in text or "~~~" in text:
            self._render_markdown(text)
            return

        # detect inline markdown markers
        if any(m in text for m in ("**", "*", "_", "`", "~~", "[")):
            self._render_markdown(text)
            return

        # plain text — print as-is for maximum speed
        self.console.print(text, end="", highlight=False, markup=False)

    def _render_markdown(self, text: str) -> None:
        """Render text as markdown using rich."""
        try:
            self.console.print(Markdown(text))
        except Exception:
            # fallback to plain if markdown parsing fails
            self.console.print(text, end="", highlight=False, markup=False)

    def _detect_lang(self, info_string: str) -> str:
        """Detect language from code fence info string."""
        info = info_string.strip().lower()
        if info:
            return info
        return "text"
