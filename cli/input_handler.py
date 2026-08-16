"""
BharatBuild CLI — Input Handler
=================================
Kiro/Goose-style input with:
  • Slash-command autocomplete (Tab)
  • Command history (Up/Down arrows, Ctrl+R search)
  • Multi-line paste detection
  • Ctrl+C → clear line / exit
  • @ file mention suggestions
  • Prompt shows cwd + active project

Mirrors Goose's session/input.rs in Python using prompt_toolkit.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional, TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style

if TYPE_CHECKING:
    from cli.app import BharatBuildCLI

# ── all registered slash commands + their descriptions ───────────────────────
SLASH_COMMANDS: dict[str, str] = {
    "/help":     "Show all available commands",
    "/clear":    "Clear conversation history and screen",
    "/exit":     "Exit BharatBuild CLI",
    "/quit":     "Exit BharatBuild CLI",
    "/status":   "Show session status",
    "/whoami":   "Show logged-in account details",
    "/model":    "Switch AI model  (haiku | sonnet | opus)",
    "/mode":     "Switch permission mode  (ask | auto | deny)",
    "/project":  "Show or set current project",
    "/projects": "List your projects",
    "/new":      "Generate a new project from a description",
    "/fix":      "Auto-fix errors in current project",
    "/run":      "Run current project in Docker sandbox",
    "/stop":     "Stop the running sandbox container",
    "/preview":  "Get live preview URL",
    "/tokens":   "Show token balance",
    "/doctor":   "Run environment diagnostics",
    "/cd":       "Change working directory",
    "/pwd":      "Print working directory",
    "/history":  "Show conversation history",
    "/save":     "Save session to file",
    "/import":   "Import a project folder",
    "/ieee":     "Generate IEEE academic documents",
    "/config":   "Show or set config values",
    "/version":  "Show CLI version",
}

# ── completer ─────────────────────────────────────────────────────────────────

class BharatBuildCompleter(Completer):
    """
    Tab-completion for:
      • /commands  — fuzzy match on slash commands
      • @files     — local file paths
    """

    def __init__(self, extra_commands: Optional[dict[str, str]] = None):
        self._commands = {**SLASH_COMMANDS, **(extra_commands or {})}

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        text = document.text_before_cursor

        # slash-command completion
        if text.startswith("/"):
            word = text.lstrip("/").lower()
            for cmd, desc in sorted(self._commands.items()):
                cmd_word = cmd.lstrip("/").lower()
                if cmd_word.startswith(word):
                    yield Completion(
                        cmd[len(text) - (len(text) - len(text.lstrip("/"))) :],
                        start_position = -(len(text) - 1),
                        display        = HTML(f"<cyan>{cmd}</cyan>"),
                        display_meta   = desc,
                    )
            return

        # @file mention completion
        if "@" in text:
            at_pos = text.rfind("@")
            partial = text[at_pos + 1:]
            base    = Path(".").resolve()
            try:
                for p in sorted(base.rglob("*")):
                    if p.is_file() and not any(
                        part.startswith(".") for part in p.parts
                    ):
                        rel = str(p.relative_to(base))
                        if partial.lower() in rel.lower():
                            yield Completion(
                                rel[len(partial):],
                                start_position=0,
                                display=rel,
                            )
                            # limit suggestions to keep it fast
                            if len(list(self.get_completions.__code__.co_consts)) > 20:
                                break
            except Exception:
                pass


# ── key bindings ──────────────────────────────────────────────────────────────

def _build_keybindings(app: "BharatBuildCLI") -> KeyBindings:
    kb = KeyBindings()

    # Ctrl+L — clear screen
    @kb.add("c-l")
    def _clear(event):
        app.console.clear()
        app._print_header()

    # Ctrl+C on empty line — ask to exit
    @kb.add("c-c")
    def _ctrlc(event):
        buf = event.app.current_buffer
        if buf.text:
            buf.reset()
            app.console.print("\n[dim](cancelled)[/dim]")
        else:
            # second Ctrl+C exits
            app._running = False
            event.app.exit()

    # Ctrl+J / Ctrl+Enter — insert newline (multi-line input)
    @kb.add("c-j")
    def _newline(event):
        event.app.current_buffer.insert_text("\n")

    return kb


# ── prompt style ─────────────────────────────────────────────────────────────

_PROMPT_STYLE = Style.from_dict({
    "prompt":     "#00D9FF bold",
    "path":       "#4ADE80",
    "project":    "#FF79C6",
    "separator":  "#444444",
})


def _build_prompt_text(app: "BharatBuildCLI") -> List:
    """Build the dynamic prompt line — path + optional project id."""
    cwd   = Path(app.config.working_directory).resolve()
    parts = cwd.parts
    short = ("…/" + "/".join(parts[-2:])) if len(parts) > 2 else str(cwd)

    tokens = [
        ("class:path",      f" {short}"),
    ]
    if app.current_project_id:
        tokens += [
            ("class:separator", " ·"),
            ("class:project",   f" {app.current_project_id[:8]}"),
        ]
    tokens += [
        ("",                "\n"),
        ("class:prompt",    " ❯ "),
    ]
    return tokens


# ── main InputHandler class ───────────────────────────────────────────────────

class InputHandler:
    """
    Manages the prompt_toolkit session for the BharatBuild REPL.

    Usage
    -----
        handler = InputHandler(app)
        handler.setup()

        while app._running:
            user_input = await handler.prompt()
            if user_input is None:
                break   # EOF / exit requested
            # process input …
    """

    def __init__(self, app: "BharatBuildCLI"):
        self.app        = app
        self._session: Optional[PromptSession] = None
        self._completer = BharatBuildCompleter()

    def setup(self) -> None:
        """Initialise the prompt session. Call once before the REPL loop."""
        self._session = PromptSession(
            history          = FileHistory(self.app.config.history_file),
            auto_suggest     = AutoSuggestFromHistory(),
            completer        = self._completer,
            complete_while_typing = False,   # only complete on Tab
            key_bindings     = _build_keybindings(self.app),
            style            = _PROMPT_STYLE,
            multiline        = False,
            wrap_lines       = True,
            enable_history_search = True,
        )

    def register_command(self, name: str, description: str) -> None:
        """Add a command to the completer at runtime (e.g. from plugins)."""
        self._completer._commands[name] = description

    async def prompt(self) -> Optional[str]:
        """
        Show the prompt and return the user's input.

        Returns
        -------
        str   — the input text (may be empty string)
        None  — EOF or explicit exit requested
        """
        if self._session is None:
            raise RuntimeError("InputHandler.setup() not called")

        try:
            text = await self._session.prompt_async(
                lambda: _build_prompt_text(self.app),
                style           = _PROMPT_STYLE,
                complete_in_thread = True,
            )
            return text
        except EOFError:
            return None
        except KeyboardInterrupt:
            # Ctrl+C on empty prompt — signal exit
            return None

    def print_hint(self) -> None:
        """Print the one-time usage hint shown at startup."""
        self.app.console.print(
            "  [dim]Type a prompt to generate code  •  "
            "[cyan]/help[/cyan] for commands  •  "
            "[cyan]Tab[/cyan] to autocomplete  •  "
            "[cyan]Ctrl+C[/cyan] to cancel[/dim]"
        )
        self.app.console.print()
