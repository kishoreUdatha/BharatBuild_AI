"""
BharatBuild CLI Project Indexing & Search

Provides fast project-wide search and indexing:
  /search function authenticate
  /files *.py
  /symbols UserModel
"""

import os
import re
import json
import time
import fnmatch
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple, Generator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text


class SymbolType(str, Enum):
    """Types of code symbols"""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    TYPE = "type"
    IMPORT = "import"
    EXPORT = "export"


@dataclass
class Symbol:
    """A code symbol (class, function, etc.)"""
    name: str
    symbol_type: SymbolType
    file_path: str
    line_number: int
    column: int = 0
    signature: str = ""
    docstring: str = ""


@dataclass
class SearchResult:
    """A search result"""
    file_path: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)


@dataclass
class FileInfo:
    """Information about an indexed file"""
    path: str
    size: int
    modified: float
    hash: str
    language: str
    lines: int
    symbols: List[Symbol] = field(default_factory=list)


@dataclass
class ProjectIndex:
    """The project index"""
    root: str
    files: Dict[str, FileInfo] = field(default_factory=dict)
    symbols: Dict[str, List[Symbol]] = field(default_factory=dict)  # name -> symbols
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ProjectIndexer:
    """
    Indexes a project for fast searching.

    Usage:
        indexer = ProjectIndexer(console, project_root)

        # Build index
        await indexer.build_index()

        # Search content
        results = indexer.search("authenticate")

        # Search files
        files = indexer.find_files("*.py")

        # Search symbols
        symbols = indexer.find_symbols("User")
    """

    # File patterns to index
    INDEXABLE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs',
        '.rb', '.php', '.c', '.cpp', '.h', '.hpp', '.cs', '.swift',
        '.kt', '.scala', '.vue', '.svelte', '.html', '.css', '.scss',
        '.json', '.yaml', '.yml', '.toml', '.md', '.txt', '.sql',
        '.sh', '.bash', '.ps1', '.bat'
    }

    # Directories to ignore
    IGNORE_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        'dist', 'build', '.next', '.nuxt', 'target', 'vendor',
        '.idea', '.vscode', 'coverage', '.pytest_cache', '.mypy_cache'
    }

    # Files to ignore
    IGNORE_FILES = {
        '.DS_Store', 'Thumbs.db', '*.pyc', '*.pyo', '*.class',
        '*.o', '*.obj', '*.exe', '*.dll', '*.so', '*.dylib',
        'package-lock.json', 'yarn.lock', 'poetry.lock'
    }

    # Language detection
    LANGUAGE_MAP = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'javascript', '.tsx': 'typescript', '.java': 'java',
        '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
        '.c': 'c', '.cpp': 'cpp', '.h': 'c', '.hpp': 'cpp',
        '.cs': 'csharp', '.swift': 'swift', '.kt': 'kotlin',
        '.scala': 'scala', '.vue': 'vue', '.svelte': 'svelte',
        '.html': 'html', '.css': 'css', '.scss': 'scss',
        '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
        '.md': 'markdown', '.sql': 'sql', '.sh': 'bash'
    }

    # Symbol patterns by language
    SYMBOL_PATTERNS = {
        'python': [
            (r'^class\s+(\w+)', SymbolType.CLASS),
            (r'^def\s+(\w+)', SymbolType.FUNCTION),
            (r'^\s+def\s+(\w+)', SymbolType.METHOD),
            (r'^(\w+)\s*=', SymbolType.VARIABLE),
            (r'^([A-Z_]+)\s*=', SymbolType.CONSTANT),
        ],
        'javascript': [
            (r'class\s+(\w+)', SymbolType.CLASS),
            (r'function\s+(\w+)', SymbolType.FUNCTION),
            (r'const\s+(\w+)\s*=\s*(?:async\s*)?\(', SymbolType.FUNCTION),
            (r'const\s+([A-Z_]+)\s*=', SymbolType.CONSTANT),
            (r'(?:export\s+)?(?:const|let|var)\s+(\w+)', SymbolType.VARIABLE),
            (r'interface\s+(\w+)', SymbolType.INTERFACE),
            (r'type\s+(\w+)', SymbolType.TYPE),
        ],
        'typescript': [
            (r'class\s+(\w+)', SymbolType.CLASS),
            (r'function\s+(\w+)', SymbolType.FUNCTION),
            (r'const\s+(\w+)\s*=\s*(?:async\s*)?\(', SymbolType.FUNCTION),
            (r'interface\s+(\w+)', SymbolType.INTERFACE),
            (r'type\s+(\w+)', SymbolType.TYPE),
            (r'enum\s+(\w+)', SymbolType.TYPE),
        ],
        'java': [
            (r'class\s+(\w+)', SymbolType.CLASS),
            (r'interface\s+(\w+)', SymbolType.INTERFACE),
            (r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(', SymbolType.METHOD),
        ],
        'go': [
            (r'type\s+(\w+)\s+struct', SymbolType.CLASS),
            (r'type\s+(\w+)\s+interface', SymbolType.INTERFACE),
            (r'func\s+(\w+)\s*\(', SymbolType.FUNCTION),
            (r'func\s+\([^)]+\)\s+(\w+)\s*\(', SymbolType.METHOD),
        ],
    }

    def __init__(
        self,
        console: Console,
        root: Path,
        cache_dir: Optional[Path] = None,
        max_file_size: int = 1_000_000  # 1MB
    ):
        self.console = console
        self.root = root
        self.cache_dir = cache_dir or (Path.home() / ".bharatbuild" / "index")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size

        self.index: Optional[ProjectIndex] = None
        self._lock = threading.Lock()

        # Load cached index
        self._load_index()

    def _get_cache_path(self) -> Path:
        """Get cache file path for this project"""
        project_hash = hashlib.md5(str(self.root).encode()).hexdigest()[:12]
        return self.cache_dir / f"{project_hash}.json"

    def _load_index(self):
        """Load index from cache"""
        cache_path = self._get_cache_path()

        if cache_path.exists():
            try:
                with open(cache_path) as f:
                    data = json.load(f)

                self.index = ProjectIndex(
                    root=data["root"],
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", "")
                )

                for path, file_data in data.get("files", {}).items():
                    symbols = [
                        Symbol(
                            name=s["name"],
                            symbol_type=SymbolType(s["symbol_type"]),
                            file_path=s["file_path"],
                            line_number=s["line_number"],
                            column=s.get("column", 0),
                            signature=s.get("signature", ""),
                            docstring=s.get("docstring", "")
                        )
                        for s in file_data.get("symbols", [])
                    ]

                    self.index.files[path] = FileInfo(
                        path=path,
                        size=file_data["size"],
                        modified=file_data["modified"],
                        hash=file_data["hash"],
                        language=file_data["language"],
                        lines=file_data["lines"],
                        symbols=symbols
                    )

                # Build symbol index
                for file_info in self.index.files.values():
                    for symbol in file_info.symbols:
                        if symbol.name not in self.index.symbols:
                            self.index.symbols[symbol.name] = []
                        self.index.symbols[symbol.name].append(symbol)

            except Exception as e:
                self.console.print(f"[yellow]Could not load index cache: {e}[/yellow]")
                self.index = None

    def _save_index(self):
        """Save index to cache"""
        if not self.index:
            return

        cache_path = self._get_cache_path()

        try:
            files_data = {}
            for path, file_info in self.index.files.items():
                files_data[path] = {
                    "size": file_info.size,
                    "modified": file_info.modified,
                    "hash": file_info.hash,
                    "language": file_info.language,
                    "lines": file_info.lines,
                    "symbols": [
                        {
                            "name": s.name,
                            "symbol_type": s.symbol_type.value,
                            "file_path": s.file_path,
                            "line_number": s.line_number,
                            "column": s.column,
                            "signature": s.signature,
                            "docstring": s.docstring
                        }
                        for s in file_info.symbols
                    ]
                }

            data = {
                "root": self.index.root,
                "files": files_data,
                "created_at": self.index.created_at,
                "updated_at": self.index.updated_at
            }

            with open(cache_path, 'w') as f:
                json.dump(data, f)

        except Exception as e:
            self.console.print(f"[yellow]Could not save index cache: {e}[/yellow]")

    # ==================== Indexing ====================

    def build_index(self, show_progress: bool = True) -> int:
        """
        Build or rebuild the project index.

        Returns number of files indexed.
        """
        self.index = ProjectIndex(root=str(self.root))

        files_to_index = list(self._get_indexable_files())

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"Indexing {len(files_to_index)} files...", total=len(files_to_index))

                for file_path in files_to_index:
                    self._index_file(file_path)
                    progress.advance(task)
        else:
            for file_path in files_to_index:
                self._index_file(file_path)

        self.index.updated_at = datetime.now().isoformat()
        self._save_index()

        return len(self.index.files)

    def update_index(self) -> Tuple[int, int]:
        """
        Update index with changed files.

        Returns (added, updated) counts.
        """
        if not self.index:
            count = self.build_index()
            return count, 0

        added = 0
        updated = 0

        for file_path in self._get_indexable_files():
            rel_path = str(file_path.relative_to(self.root))
            stat = file_path.stat()

            if rel_path not in self.index.files:
                self._index_file(file_path)
                added += 1
            elif self.index.files[rel_path].modified < stat.st_mtime:
                self._index_file(file_path)
                updated += 1

        self.index.updated_at = datetime.now().isoformat()
        self._save_index()

        return added, updated

    def _get_indexable_files(self) -> Generator[Path, None, None]:
        """Get all indexable files in the project"""
        for root, dirs, files in os.walk(self.root):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith('.')]

            for file in files:
                file_path = Path(root) / file

                # Check extension
                if file_path.suffix.lower() not in self.INDEXABLE_EXTENSIONS:
                    continue

                # Check ignore patterns
                if any(fnmatch.fnmatch(file, pattern) for pattern in self.IGNORE_FILES):
                    continue

                # Check size
                try:
                    if file_path.stat().st_size > self.max_file_size:
                        continue
                except Exception:
                    continue

                yield file_path

    def _index_file(self, file_path: Path):
        """Index a single file"""
        try:
            stat = file_path.stat()
            rel_path = str(file_path.relative_to(self.root))

            content = file_path.read_text(errors='replace')
            lines = content.splitlines()

            # Compute hash
            file_hash = hashlib.md5(content.encode()).hexdigest()[:12]

            # Detect language
            ext = file_path.suffix.lower()
            language = self.LANGUAGE_MAP.get(ext, 'text')

            # Extract symbols
            symbols = self._extract_symbols(content, rel_path, language)

            # Store file info
            file_info = FileInfo(
                path=rel_path,
                size=stat.st_size,
                modified=stat.st_mtime,
                hash=file_hash,
                language=language,
                lines=len(lines),
                symbols=symbols
            )

            with self._lock:
                self.index.files[rel_path] = file_info

                # Update symbol index
                for symbol in symbols:
                    if symbol.name not in self.index.symbols:
                        self.index.symbols[symbol.name] = []
                    self.index.symbols[symbol.name].append(symbol)

        except Exception:
            pass  # Skip files that can't be indexed

    def _extract_symbols(self, content: str, file_path: str, language: str) -> List[Symbol]:
        """Extract symbols from file content"""
        symbols = []

        patterns = self.SYMBOL_PATTERNS.get(language, [])
        if not patterns:
            return symbols

        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            for pattern, symbol_type in patterns:
                match = re.match(pattern, line)
                if match:
                    name = match.group(1)
                    symbols.append(Symbol(
                        name=name,
                        symbol_type=symbol_type,
                        file_path=file_path,
                        line_number=i,
                        column=match.start(1),
                        signature=line.strip()[:100]
                    ))

        return symbols

    # ==================== Searching ====================

    def search(
        self,
        query: str,
        file_pattern: Optional[str] = None,
        case_sensitive: bool = False,
        regex: bool = False,
        context: int = 2,
        max_results: int = 100
    ) -> List[SearchResult]:
        """
        Search for text in indexed files.

        Args:
            query: Search query (text or regex)
            file_pattern: Optional glob pattern to filter files
            case_sensitive: Whether search is case sensitive
            regex: Whether query is a regex
            context: Lines of context to include
            max_results: Maximum results to return
        """
        results = []

        if not self.index:
            self.build_index(show_progress=False)

        # Compile pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        if regex:
            pattern = re.compile(query, flags)
        else:
            pattern = re.compile(re.escape(query), flags)

        for rel_path, file_info in self.index.files.items():
            # Filter by file pattern
            if file_pattern and not fnmatch.fnmatch(rel_path, file_pattern):
                continue

            try:
                file_path = self.root / rel_path
                content = file_path.read_text(errors='replace')
                lines = content.splitlines()

                for i, line in enumerate(lines):
                    match = pattern.search(line)
                    if match:
                        # Get context
                        start = max(0, i - context)
                        end = min(len(lines), i + context + 1)

                        results.append(SearchResult(
                            file_path=rel_path,
                            line_number=i + 1,
                            line_content=line,
                            match_start=match.start(),
                            match_end=match.end(),
                            context_before=lines[start:i],
                            context_after=lines[i+1:end]
                        ))

                        if len(results) >= max_results:
                            return results

            except Exception:
                continue

        return results

    def find_files(
        self,
        pattern: str,
        include_hidden: bool = False
    ) -> List[str]:
        """
        Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.py", "src/**/*.js")
            include_hidden: Whether to include hidden files
        """
        if not self.index:
            self.build_index(show_progress=False)

        matches = []

        for rel_path in self.index.files.keys():
            if fnmatch.fnmatch(rel_path, pattern):
                if include_hidden or not any(p.startswith('.') for p in rel_path.split(os.sep)):
                    matches.append(rel_path)

        return sorted(matches)

    def find_symbols(
        self,
        name: str,
        symbol_type: Optional[SymbolType] = None,
        exact_match: bool = False
    ) -> List[Symbol]:
        """
        Find symbols by name.

        Args:
            name: Symbol name or partial name
            symbol_type: Optional type filter
            exact_match: Whether to require exact name match
        """
        if not self.index:
            self.build_index(show_progress=False)

        matches = []

        if exact_match:
            if name in self.index.symbols:
                matches = self.index.symbols[name].copy()
        else:
            # Partial match
            name_lower = name.lower()
            for symbol_name, symbols in self.index.symbols.items():
                if name_lower in symbol_name.lower():
                    matches.extend(symbols)

        # Filter by type
        if symbol_type:
            matches = [s for s in matches if s.symbol_type == symbol_type]

        return matches

    # ==================== Display ====================

    def show_search_results(self, results: List[SearchResult], query: str):
        """Display search results"""
        if not results:
            self.console.print(f"[dim]No results found for '{query}'[/dim]")
            return

        self.console.print(f"\n[bold cyan]Search results for '{query}'[/bold cyan]")
        self.console.print(f"[dim]Found {len(results)} matches[/dim]\n")

        # Group by file
        by_file: Dict[str, List[SearchResult]] = {}
        for result in results:
            if result.file_path not in by_file:
                by_file[result.file_path] = []
            by_file[result.file_path].append(result)

        for file_path, file_results in by_file.items():
            self.console.print(f"[bold cyan]{file_path}[/bold cyan]")

            for result in file_results[:5]:  # Max 5 per file
                # Highlight match
                line = result.line_content
                highlighted = (
                    line[:result.match_start] +
                    f"[bold yellow]{line[result.match_start:result.match_end]}[/bold yellow]" +
                    line[result.match_end:]
                )

                self.console.print(f"  [dim]{result.line_number:4}:[/dim] {highlighted.strip()}")

            if len(file_results) > 5:
                self.console.print(f"  [dim]... and {len(file_results) - 5} more matches[/dim]")

            self.console.print()

    def show_symbols(self, symbols: List[Symbol]):
        """Display symbol results"""
        if not symbols:
            self.console.print("[dim]No symbols found[/dim]")
            return

        table = Table(title="Symbols", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("File")
        table.add_column("Line", justify="right")
        table.add_column("Signature")

        for symbol in symbols[:50]:  # Limit display
            table.add_row(
                symbol.name,
                symbol.symbol_type.value,
                symbol.file_path,
                str(symbol.line_number),
                symbol.signature[:40] + "..." if len(symbol.signature) > 40 else symbol.signature
            )

        self.console.print(table)

        if len(symbols) > 50:
            self.console.print(f"[dim]... and {len(symbols) - 50} more symbols[/dim]")

    def show_stats(self):
        """Show index statistics"""
        if not self.index:
            self.console.print("[dim]No index built. Run /index to build.[/dim]")
            return

        # Compute stats
        total_files = len(self.index.files)
        total_lines = sum(f.lines for f in self.index.files.values())
        total_symbols = sum(len(s) for s in self.index.symbols.values())
        total_size = sum(f.size for f in self.index.files.values())

        # Language breakdown
        languages: Dict[str, int] = {}
        for f in self.index.files.values():
            languages[f.language] = languages.get(f.language, 0) + 1

        # Display
        self.console.print("\n[bold cyan]Project Index Statistics[/bold cyan]\n")

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Files indexed", f"[cyan]{total_files:,}[/cyan]")
        table.add_row("Lines of code", f"[cyan]{total_lines:,}[/cyan]")
        table.add_row("Symbols found", f"[cyan]{total_symbols:,}[/cyan]")
        table.add_row("Total size", f"[cyan]{total_size / 1024 / 1024:.1f} MB[/cyan]")
        table.add_row("Last updated", f"[dim]{self.index.updated_at[:19]}[/dim]")

        self.console.print(table)

        # Language breakdown
        self.console.print("\n[bold]Languages:[/bold]")
        for lang, count in sorted(languages.items(), key=lambda x: -x[1])[:10]:
            self.console.print(f"  [cyan]{lang}:[/cyan] {count} files")
