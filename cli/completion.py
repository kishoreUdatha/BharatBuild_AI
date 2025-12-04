"""
BharatBuild CLI Tab Completion & Fuzzy Search

Provides intelligent tab completion and fuzzy file search.
"""

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Iterable
from dataclasses import dataclass

from prompt_toolkit.completion import Completer, Completion, CompleteEvent, PathCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText

from rich.console import Console


@dataclass
class CompletionItem:
    """A completion suggestion"""
    text: str
    display: str = ""
    description: str = ""
    style: str = ""
    start_position: int = 0


class SmartCompleter(Completer):
    """
    Smart completer with multiple completion sources.

    Provides completions for:
    - Slash commands (/help, /quit, etc.)
    - File paths
    - Context references (@file, @folder)
    - Code symbols
    - Git branches
    """

    def __init__(
        self,
        working_dir: Path,
        commands: Dict[str, str] = None,
        symbols: List[str] = None,
        enable_fuzzy: bool = True
    ):
        self.working_dir = working_dir
        self.commands = commands or {}
        self.symbols = symbols or []
        self.enable_fuzzy = enable_fuzzy

        # Sub-completers
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Get completions for current input"""
        text = document.text_before_cursor
        word = document.get_word_before_cursor()

        # Slash commands
        if text.startswith('/'):
            yield from self._complete_commands(text, word)
            return

        # Context references (@)
        if '@' in text:
            at_pos = text.rfind('@')
            ref_text = text[at_pos + 1:]
            yield from self._complete_context_refs(ref_text, at_pos, document)
            return

        # File paths
        if '/' in word or '\\' in word or word.startswith('.'):
            yield from self._complete_paths(document, complete_event)
            return

        # General completions
        yield from self._complete_general(word)

    def _complete_commands(self, text: str, word: str) -> Iterable[Completion]:
        """Complete slash commands"""
        cmd_text = text[1:]  # Remove leading /

        for cmd, desc in self.commands.items():
            if cmd.startswith(cmd_text) or self._fuzzy_match(cmd_text, cmd):
                yield Completion(
                    text=cmd,
                    start_position=-len(cmd_text),
                    display=f"/{cmd}",
                    display_meta=desc
                )

    def _complete_context_refs(
        self,
        ref_text: str,
        at_pos: int,
        document: Document
    ) -> Iterable[Completion]:
        """Complete context references (@file, @folder, etc.)"""
        # Special completions
        special_refs = [
            ("clipboard", "Clipboard content"),
            ("git:diff", "Git diff"),
            ("git:status", "Git status"),
            ("git:log", "Git log"),
        ]

        for ref, desc in special_refs:
            if ref.startswith(ref_text.lower()):
                yield Completion(
                    text=ref,
                    start_position=-len(ref_text),
                    display=f"@{ref}",
                    display_meta=desc
                )

        # File/folder completions
        yield from self._complete_files_for_ref(ref_text)

    def _complete_files_for_ref(self, ref_text: str) -> Iterable[Completion]:
        """Complete file paths for @ references"""
        try:
            # Get base path
            if '/' in ref_text:
                base_path = self.working_dir / ref_text.rsplit('/', 1)[0]
                prefix = ref_text.rsplit('/', 1)[0] + '/'
                search = ref_text.rsplit('/', 1)[1] if '/' in ref_text else ref_text
            else:
                base_path = self.working_dir
                prefix = ""
                search = ref_text

            if not base_path.exists():
                return

            for item in base_path.iterdir():
                name = item.name

                # Skip hidden files
                if name.startswith('.'):
                    continue

                # Match
                if name.lower().startswith(search.lower()) or self._fuzzy_match(search, name):
                    display_name = prefix + name
                    if item.is_dir():
                        display_name += "/"

                    yield Completion(
                        text=display_name,
                        start_position=-len(ref_text),
                        display=f"@{display_name}",
                        display_meta="folder" if item.is_dir() else "file"
                    )

        except Exception:
            pass

    def _complete_paths(
        self,
        document: Document,
        complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Complete file paths"""
        yield from self.path_completer.get_completions(document, complete_event)

    def _complete_general(self, word: str) -> Iterable[Completion]:
        """General completions (symbols, etc.)"""
        if not word:
            return

        # Symbol completions
        for symbol in self.symbols:
            if symbol.lower().startswith(word.lower()):
                yield Completion(
                    text=symbol,
                    start_position=-len(word),
                    display=symbol,
                    display_meta="symbol"
                )

    def _fuzzy_match(self, query: str, target: str) -> bool:
        """Check if query fuzzy matches target"""
        if not self.enable_fuzzy:
            return False

        query = query.lower()
        target = target.lower()

        # Simple subsequence matching
        query_idx = 0
        for char in target:
            if query_idx < len(query) and char == query[query_idx]:
                query_idx += 1

        return query_idx == len(query)

    def update_symbols(self, symbols: List[str]):
        """Update available symbols for completion"""
        self.symbols = symbols

    def update_commands(self, commands: Dict[str, str]):
        """Update available commands"""
        self.commands = commands


class FuzzyFileFinder:
    """
    Fuzzy file finder for quick navigation.

    Similar to fzf or Ctrl+P in VS Code.

    Usage:
        finder = FuzzyFileFinder(working_dir)

        # Search files
        results = finder.search("app.py")

        # Get ranked results
        ranked = finder.search_ranked("usrmdl")  # finds "UserModel.py"
    """

    # Directories to ignore
    IGNORE_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        'dist', 'build', '.next', '.nuxt', 'target', 'vendor',
        '.idea', '.vscode', 'coverage'
    }

    def __init__(
        self,
        root: Path,
        max_results: int = 50,
        max_depth: int = 10
    ):
        self.root = root
        self.max_results = max_results
        self.max_depth = max_depth

        # Cache file list
        self._files: List[str] = []
        self._last_scan = 0

        # Build initial cache
        self.refresh()

    def refresh(self):
        """Refresh the file cache"""
        import time
        self._files = []
        self._scan_directory(self.root, 0)
        self._last_scan = time.time()

    def _scan_directory(self, path: Path, depth: int):
        """Recursively scan directory for files"""
        if depth > self.max_depth:
            return

        try:
            for item in path.iterdir():
                if item.is_dir():
                    if item.name not in self.IGNORE_DIRS and not item.name.startswith('.'):
                        self._scan_directory(item, depth + 1)
                else:
                    rel_path = str(item.relative_to(self.root))
                    self._files.append(rel_path)

        except PermissionError:
            pass

    def search(self, query: str, limit: int = None) -> List[str]:
        """
        Search for files matching query.

        Returns list of matching file paths.
        """
        if not query:
            return self._files[:limit or self.max_results]

        limit = limit or self.max_results
        results = []

        query_lower = query.lower()

        for file_path in self._files:
            if self._matches(query_lower, file_path.lower()):
                results.append(file_path)
                if len(results) >= limit:
                    break

        return results

    def search_ranked(self, query: str, limit: int = None) -> List[tuple]:
        """
        Search with ranking scores.

        Returns list of (file_path, score) tuples, highest score first.
        """
        if not query:
            return [(f, 0) for f in self._files[:limit or self.max_results]]

        limit = limit or self.max_results
        scored = []

        query_lower = query.lower()

        for file_path in self._files:
            score = self._score_match(query_lower, file_path.lower())
            if score > 0:
                scored.append((file_path, score))

        # Sort by score (descending), then by path length (ascending)
        scored.sort(key=lambda x: (-x[1], len(x[0])))

        return scored[:limit]

    def _matches(self, query: str, target: str) -> bool:
        """Check if query matches target (subsequence match)"""
        query_idx = 0
        for char in target:
            if query_idx < len(query) and char == query[query_idx]:
                query_idx += 1

        return query_idx == len(query)

    def _score_match(self, query: str, target: str) -> int:
        """
        Score how well query matches target.

        Higher score = better match.
        """
        if not self._matches(query, target):
            return 0

        score = 0
        query_idx = 0
        prev_match_idx = -2
        consecutive_bonus = 0

        # Get just the filename for bonus scoring
        filename = target.split('/')[-1].split('\\')[-1]

        for i, char in enumerate(target):
            if query_idx < len(query) and char == query[query_idx]:
                # Base match score
                score += 10

                # Consecutive character bonus
                if i == prev_match_idx + 1:
                    consecutive_bonus += 5
                    score += consecutive_bonus
                else:
                    consecutive_bonus = 0

                # Start of word bonus
                if i == 0 or target[i-1] in '/_-.':
                    score += 15

                # Filename match bonus
                filename_start = len(target) - len(filename)
                if i >= filename_start:
                    score += 20

                # Exact start bonus
                if query_idx == 0 and i == filename_start:
                    score += 30

                prev_match_idx = i
                query_idx += 1

        # Penalty for longer paths
        score -= len(target) // 10

        return max(0, score)


class CommandCompleter(Completer):
    """
    Completer specifically for slash commands with arguments.

    Provides intelligent completion for command arguments:
    - /model haiku|sonnet|opus
    - /prompt set <prompt_name>
    - /branch switch <branch_name>
    """

    def __init__(self, command_specs: Dict[str, Dict[str, Any]]):
        """
        Initialize with command specifications.

        command_specs format:
        {
            "model": {
                "args": ["haiku", "sonnet", "opus"],
                "description": "Set AI model"
            },
            "prompt": {
                "subcommands": {
                    "set": {"args_func": get_prompt_names},
                    "show": {"args_func": get_prompt_names}
                }
            }
        }
        """
        self.command_specs = command_specs

    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Get completions for command input"""
        text = document.text_before_cursor.strip()

        if not text.startswith('/'):
            return

        parts = text[1:].split()

        if len(parts) == 0:
            # Complete command name
            yield from self._complete_command_names("")
        elif len(parts) == 1 and not text.endswith(' '):
            # Still completing command name
            yield from self._complete_command_names(parts[0])
        else:
            # Complete arguments
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            current_arg = args[-1] if args and not text.endswith(' ') else ""

            yield from self._complete_arguments(cmd, args, current_arg)

    def _complete_command_names(self, prefix: str) -> Iterable[Completion]:
        """Complete command names"""
        for cmd, spec in self.command_specs.items():
            if cmd.startswith(prefix):
                yield Completion(
                    text=cmd,
                    start_position=-len(prefix),
                    display=f"/{cmd}",
                    display_meta=spec.get("description", "")
                )

    def _complete_arguments(
        self,
        cmd: str,
        args: List[str],
        current: str
    ) -> Iterable[Completion]:
        """Complete command arguments"""
        if cmd not in self.command_specs:
            return

        spec = self.command_specs[cmd]

        # Check for subcommands
        if "subcommands" in spec:
            if len(args) <= 1:
                # Complete subcommand
                for subcmd in spec["subcommands"]:
                    if subcmd.startswith(current):
                        yield Completion(
                            text=subcmd,
                            start_position=-len(current),
                            display=subcmd
                        )
            else:
                # Complete subcommand arguments
                subcmd = args[0]
                if subcmd in spec["subcommands"]:
                    yield from self._complete_from_spec(
                        spec["subcommands"][subcmd],
                        current
                    )
        else:
            # Complete direct arguments
            yield from self._complete_from_spec(spec, current)

    def _complete_from_spec(
        self,
        spec: Dict[str, Any],
        current: str
    ) -> Iterable[Completion]:
        """Complete from argument specification"""
        # Static args list
        if "args" in spec:
            for arg in spec["args"]:
                if str(arg).startswith(current):
                    yield Completion(
                        text=str(arg),
                        start_position=-len(current),
                        display=str(arg)
                    )

        # Dynamic args function
        if "args_func" in spec:
            try:
                args = spec["args_func"]()
                for arg in args:
                    if str(arg).startswith(current):
                        yield Completion(
                            text=str(arg),
                            start_position=-len(current),
                            display=str(arg)
                        )
            except Exception:
                pass


def create_cli_completer(
    working_dir: Path,
    console: Console
) -> SmartCompleter:
    """Create completer for CLI with default commands"""
    commands = {
        "help": "Show help",
        "quit": "Exit CLI",
        "exit": "Exit CLI",
        "clear": "Clear screen",
        "config": "Show/edit configuration",
        "model": "Change AI model",
        "prompt": "Manage system prompts",
        "branch": "Manage conversation branches",
        "undo": "Undo last change",
        "redo": "Redo undone change",
        "history": "Show history",
        "search": "Search project",
        "files": "List project files",
        "index": "Index project",
        "mcp": "Manage MCP servers",
        "hooks": "Manage hooks",
        "image": "Add image to prompt",
        "resume": "Resume interrupted workflow",
        "cost": "Show session costs",
    }

    return SmartCompleter(working_dir, commands=commands)
