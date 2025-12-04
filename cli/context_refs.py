"""
BharatBuild CLI Context References (@mentions)

Enables Claude Code style context references:
  > @src/models/ explain the database schema
  > @package.json what dependencies do we have?
  > @https://docs.example.com summarize this
"""

import os
import re
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import mimetypes

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class RefType(str, Enum):
    """Types of context references"""
    FILE = "file"           # @path/to/file.py
    FOLDER = "folder"       # @src/models/
    URL = "url"             # @https://example.com
    SYMBOL = "symbol"       # @ClassName or @function_name
    GIT = "git"             # @git:commit_hash or @git:branch
    SELECTION = "selection" # @selection (current editor selection)
    CLIPBOARD = "clipboard" # @clipboard


@dataclass
class ContextRef:
    """A context reference extracted from input"""
    ref_type: RefType
    value: str
    original: str  # Original text matched
    start: int     # Start position in original input
    end: int       # End position in original input
    content: Optional[str] = None  # Resolved content
    metadata: Dict[str, Any] = None


class ContextRefParser:
    """
    Parses @mentions from user input.

    Patterns:
    - @path/to/file.py - file reference
    - @src/folder/ - folder reference (ends with /)
    - @https://... or @http://... - URL reference
    - @ClassName - symbol reference
    - @git:abc123 - git commit reference
    - @clipboard - clipboard content
    """

    # Regex patterns for different ref types
    PATTERNS = {
        RefType.URL: r'@(https?://[^\s]+)',
        RefType.FOLDER: r'@([^\s@]+/)',
        RefType.FILE: r'@([^\s@]+\.[a-zA-Z0-9]+)',
        RefType.GIT: r'@git:([^\s]+)',
        RefType.CLIPBOARD: r'@(clipboard)',
        RefType.SYMBOL: r'@([A-Z][a-zA-Z0-9_]*)',  # CamelCase symbols
    }

    def __init__(self, working_dir: Optional[Path] = None):
        self.working_dir = working_dir or Path.cwd()

    def parse(self, text: str) -> Tuple[str, List[ContextRef]]:
        """
        Parse text and extract all context references.

        Returns:
            Tuple of (clean_text, list_of_refs)
        """
        refs = []

        # Find all matches for each pattern
        for ref_type, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text):
                refs.append(ContextRef(
                    ref_type=ref_type,
                    value=match.group(1),
                    original=match.group(0),
                    start=match.start(),
                    end=match.end()
                ))

        # Sort by position and remove duplicates
        refs.sort(key=lambda r: r.start)

        # Remove refs from text (going backwards to preserve positions)
        clean_text = text
        for ref in reversed(refs):
            clean_text = clean_text[:ref.start] + clean_text[ref.end:]

        # Clean up extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        return clean_text, refs

    def extract_refs(self, text: str) -> List[ContextRef]:
        """Extract refs without modifying text"""
        _, refs = self.parse(text)
        return refs


class ContextResolver:
    """
    Resolves context references to actual content.

    Usage:
        resolver = ContextResolver(working_dir)
        refs = parser.extract_refs("@src/app.py explain this")
        resolved = await resolver.resolve_all(refs)
    """

    def __init__(
        self,
        working_dir: Path,
        console: Optional[Console] = None,
        max_file_size: int = 100_000,  # 100KB
        max_folder_files: int = 50
    ):
        self.working_dir = working_dir
        self.console = console or Console()
        self.max_file_size = max_file_size
        self.max_folder_files = max_folder_files

    async def resolve(self, ref: ContextRef) -> ContextRef:
        """Resolve a single context reference"""
        if ref.ref_type == RefType.FILE:
            return await self._resolve_file(ref)
        elif ref.ref_type == RefType.FOLDER:
            return await self._resolve_folder(ref)
        elif ref.ref_type == RefType.URL:
            return await self._resolve_url(ref)
        elif ref.ref_type == RefType.GIT:
            return await self._resolve_git(ref)
        elif ref.ref_type == RefType.CLIPBOARD:
            return await self._resolve_clipboard(ref)
        elif ref.ref_type == RefType.SYMBOL:
            return await self._resolve_symbol(ref)
        return ref

    async def resolve_all(self, refs: List[ContextRef]) -> List[ContextRef]:
        """Resolve all context references"""
        tasks = [self.resolve(ref) for ref in refs]
        return await asyncio.gather(*tasks)

    async def _resolve_file(self, ref: ContextRef) -> ContextRef:
        """Resolve file reference"""
        # Try multiple paths
        paths_to_try = [
            self.working_dir / ref.value,
            Path(ref.value),
        ]

        for path in paths_to_try:
            if path.exists() and path.is_file():
                try:
                    # Check file size
                    if path.stat().st_size > self.max_file_size:
                        ref.content = f"[File too large: {path.stat().st_size} bytes]"
                        ref.metadata = {"path": str(path), "size": path.stat().st_size, "truncated": True}
                        return ref

                    # Read content
                    content = path.read_text(errors='replace')
                    ref.content = content
                    ref.metadata = {
                        "path": str(path),
                        "size": len(content),
                        "lines": len(content.splitlines()),
                        "language": self._detect_language(path)
                    }
                    return ref
                except Exception as e:
                    ref.content = f"[Error reading file: {e}]"
                    return ref

        ref.content = f"[File not found: {ref.value}]"
        return ref

    async def _resolve_folder(self, ref: ContextRef) -> ContextRef:
        """Resolve folder reference - get list of files"""
        folder_path = self.working_dir / ref.value

        if not folder_path.exists():
            ref.content = f"[Folder not found: {ref.value}]"
            return ref

        if not folder_path.is_dir():
            ref.content = f"[Not a folder: {ref.value}]"
            return ref

        try:
            files = []
            file_contents = []

            for item in sorted(folder_path.rglob('*')):
                if item.is_file():
                    rel_path = item.relative_to(folder_path)
                    files.append(str(rel_path))

                    # Read small files
                    if len(files) <= self.max_folder_files:
                        try:
                            if item.stat().st_size < 10000:  # 10KB
                                content = item.read_text(errors='replace')
                                file_contents.append({
                                    "path": str(rel_path),
                                    "content": content[:5000]  # Truncate
                                })
                        except Exception:
                            pass

            ref.content = f"Folder: {ref.value}\nFiles ({len(files)}):\n" + "\n".join(f"  - {f}" for f in files[:50])
            if len(files) > 50:
                ref.content += f"\n  ... and {len(files) - 50} more files"

            ref.metadata = {
                "path": str(folder_path),
                "files": files,
                "file_contents": file_contents,
                "total_files": len(files)
            }
            return ref

        except Exception as e:
            ref.content = f"[Error reading folder: {e}]"
            return ref

    async def _resolve_url(self, ref: ContextRef) -> ContextRef:
        """Resolve URL reference - fetch content"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(ref.value, follow_redirects=True)
                response.raise_for_status()

                content_type = response.headers.get('content-type', '')

                if 'text/html' in content_type:
                    # Parse HTML and extract text
                    html = response.text
                    text = self._html_to_text(html)
                    ref.content = text[:10000]  # Truncate
                elif 'application/json' in content_type:
                    ref.content = response.text[:10000]
                elif 'text/' in content_type:
                    ref.content = response.text[:10000]
                else:
                    ref.content = f"[Binary content: {content_type}]"

                ref.metadata = {
                    "url": ref.value,
                    "status": response.status_code,
                    "content_type": content_type
                }

        except Exception as e:
            ref.content = f"[Error fetching URL: {e}]"

        return ref

    async def _resolve_git(self, ref: ContextRef) -> ContextRef:
        """Resolve git reference (commit, branch, diff)"""
        import subprocess

        try:
            value = ref.value

            if value.startswith("diff"):
                # Git diff
                result = subprocess.run(
                    ["git", "diff"],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=10
                )
                ref.content = result.stdout[:10000] if result.stdout else "[No changes]"

            elif value.startswith("log"):
                # Git log
                result = subprocess.run(
                    ["git", "log", "--oneline", "-20"],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=10
                )
                ref.content = result.stdout

            elif value.startswith("status"):
                # Git status
                result = subprocess.run(
                    ["git", "status"],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=10
                )
                ref.content = result.stdout

            else:
                # Assume commit hash - show commit
                result = subprocess.run(
                    ["git", "show", value, "--stat"],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=10
                )
                ref.content = result.stdout[:5000] if result.stdout else f"[Commit not found: {value}]"

            ref.metadata = {"type": "git", "ref": value}

        except Exception as e:
            ref.content = f"[Git error: {e}]"

        return ref

    async def _resolve_clipboard(self, ref: ContextRef) -> ContextRef:
        """Resolve clipboard content"""
        try:
            import pyperclip
            content = pyperclip.paste()
            ref.content = content[:10000] if content else "[Clipboard is empty]"
            ref.metadata = {"source": "clipboard", "length": len(content) if content else 0}
        except ImportError:
            ref.content = "[Clipboard access requires pyperclip: pip install pyperclip]"
        except Exception as e:
            ref.content = f"[Clipboard error: {e}]"

        return ref

    async def _resolve_symbol(self, ref: ContextRef) -> ContextRef:
        """Resolve symbol reference - search for class/function definition"""
        symbol = ref.value

        try:
            import subprocess

            # Use ripgrep to search for symbol definition
            patterns = [
                f"class {symbol}",
                f"def {symbol}",
                f"function {symbol}",
                f"const {symbol}",
                f"let {symbol}",
                f"var {symbol}",
                f"interface {symbol}",
                f"type {symbol}",
            ]

            results = []
            for pattern in patterns:
                result = subprocess.run(
                    ["rg", "-n", "-l", pattern],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=5
                )
                if result.stdout:
                    results.extend(result.stdout.strip().split('\n'))

            if results:
                # Get unique files
                files = list(set(results))[:5]
                content_parts = [f"Symbol '{symbol}' found in:"]

                for file_path in files:
                    full_path = self.working_dir / file_path
                    if full_path.exists():
                        try:
                            file_content = full_path.read_text(errors='replace')
                            # Find relevant lines
                            lines = file_content.splitlines()
                            for i, line in enumerate(lines):
                                if symbol in line:
                                    start = max(0, i - 2)
                                    end = min(len(lines), i + 10)
                                    snippet = '\n'.join(lines[start:end])
                                    content_parts.append(f"\n--- {file_path}:{i+1} ---\n{snippet}")
                                    break
                        except Exception:
                            pass

                ref.content = '\n'.join(content_parts)
            else:
                ref.content = f"[Symbol not found: {symbol}]"

            ref.metadata = {"symbol": symbol, "files": results[:10] if results else []}

        except FileNotFoundError:
            ref.content = f"[ripgrep (rg) required for symbol search]"
        except Exception as e:
            ref.content = f"[Symbol search error: {e}]"

        return ref

    def _detect_language(self, path: Path) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.jsx': 'javascript', '.tsx': 'typescript', '.json': 'json',
            '.yaml': 'yaml', '.yml': 'yaml', '.md': 'markdown',
            '.html': 'html', '.css': 'css', '.sql': 'sql',
            '.sh': 'bash', '.rs': 'rust', '.go': 'go',
            '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.h': 'c',
            '.rb': 'ruby', '.php': 'php', '.swift': 'swift'
        }
        return ext_map.get(path.suffix.lower(), 'text')

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Get text
            text = soup.get_text(separator='\n', strip=True)

            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines)

        except ImportError:
            # Fallback: basic regex cleanup
            import re
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()


class ContextManager:
    """
    High-level manager for context references.

    Usage:
        ctx = ContextManager(working_dir, console)

        # Process input with refs
        clean_text, context = await ctx.process_input("@src/app.py explain this code")

        # Build context for AI
        full_prompt = ctx.build_prompt(clean_text, context)
    """

    def __init__(
        self,
        working_dir: Path,
        console: Console
    ):
        self.working_dir = working_dir
        self.console = console
        self.parser = ContextRefParser(working_dir)
        self.resolver = ContextResolver(working_dir, console)

    async def process_input(self, text: str) -> Tuple[str, List[ContextRef]]:
        """Process input and resolve all context references"""
        clean_text, refs = self.parser.parse(text)

        if refs:
            # Show what we're resolving
            self.console.print(f"[dim]Resolving {len(refs)} context reference(s)...[/dim]")

            # Resolve all refs
            resolved = await self.resolver.resolve_all(refs)

            # Show summary
            for ref in resolved:
                icon = self._get_ref_icon(ref.ref_type)
                if ref.content and not ref.content.startswith("["):
                    size = len(ref.content)
                    self.console.print(f"  {icon} [cyan]{ref.value}[/cyan] [dim]({size:,} chars)[/dim]")
                else:
                    self.console.print(f"  {icon} [yellow]{ref.value}[/yellow] [dim]{ref.content}[/dim]")

            return clean_text, resolved

        return clean_text, []

    def build_prompt(self, text: str, refs: List[ContextRef]) -> str:
        """Build full prompt with context"""
        if not refs:
            return text

        context_parts = []
        for ref in refs:
            if ref.content and not ref.content.startswith("["):
                context_parts.append(f"=== {ref.ref_type.value}: {ref.value} ===\n{ref.content}")

        if context_parts:
            context_block = "\n\n".join(context_parts)
            return f"Context:\n{context_block}\n\nUser request:\n{text}"

        return text

    def _get_ref_icon(self, ref_type: RefType) -> str:
        """Get icon for ref type"""
        icons = {
            RefType.FILE: "📄",
            RefType.FOLDER: "📁",
            RefType.URL: "🌐",
            RefType.GIT: "󰊢",
            RefType.CLIPBOARD: "📋",
            RefType.SYMBOL: "🔤",
        }
        return icons.get(ref_type, "📎")

    def show_ref_help(self):
        """Show help for context references"""
        help_text = """
[bold cyan]Context References (@mentions)[/bold cyan]

Use @mentions to add context to your prompts:

[green]@path/to/file.py[/green]     Include file content
[green]@src/folder/[/green]         Include folder listing (ends with /)
[green]@https://...[/green]         Fetch and include URL content
[green]@ClassName[/green]           Search for symbol definition
[green]@git:diff[/green]            Include git diff
[green]@git:log[/green]             Include recent commits
[green]@git:status[/green]          Include git status
[green]@clipboard[/green]           Include clipboard content

[bold]Examples:[/bold]
  @src/models/user.py explain this model
  @src/components/ what components do we have?
  @https://api.example.com/docs summarize the API
  @UserService where is this class used?
  @git:diff review my changes
"""
        panel = Panel(
            Text.from_markup(help_text),
            title="[bold]Context References[/bold]",
            border_style="cyan"
        )
        self.console.print(panel)
