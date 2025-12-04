"""
Context Engine for BharatBuild
Intelligently selects relevant files to send to Claude for fixing errors.

Like Bolt.new's context engine, this module:
1. Extracts files from error logs and stack traces
2. Analyzes imports to find dependencies
3. Scores files by relevance to the error
4. Builds optimal context payload (full content, not truncated)
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from app.core.logging_config import logger


@dataclass
class FileContext:
    """Represents a file with its content and relevance score"""
    path: str
    content: str
    relevance_score: float = 0.0
    reason: str = ""  # Why this file was included
    line_hint: Optional[int] = None  # Line number from error
    is_primary: bool = False  # Is this the file with the error?


@dataclass
class ContextPayload:
    """The final payload to send to Claude"""
    user_message: str
    file_tree: List[str]
    relevant_files: Dict[str, str]
    logs: Dict[str, List[str]]
    tech_stack: str
    error_summary: str
    total_tokens_estimate: int = 0


class ContextEngine:
    """
    Intelligent context builder for Claude Fixer Agent.

    Usage:
        engine = ContextEngine(project_path="/path/to/project")
        payload = engine.build_context(
            user_message="Home page is blank",
            errors=[{"message": "TypeError at Home.jsx:22", "stack": "..."}],
            terminal_logs=[...],
            all_files=[...]
        )
    """

    # Maximum tokens to send to Claude (leave room for response)
    MAX_CONTEXT_TOKENS = 100000  # ~100K tokens for context
    CHARS_PER_TOKEN = 4  # Rough estimate
    MAX_CONTEXT_CHARS = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN

    # Maximum number of files to include
    MAX_FILES = 15

    # File extensions by language
    IMPORT_PATTERNS = {
        # JavaScript/TypeScript
        'js': [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]',
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
            r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
        ],
        'ts': None,  # Same as js
        'jsx': None,
        'tsx': None,

        # Python
        'py': [
            r'^import\s+([\w.]+)',
            r'^from\s+([\w.]+)\s+import',
        ],

        # Go
        'go': [
            r'import\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+\(\s*[\'"]([^\'"]+)[\'"]',
        ],

        # Java
        'java': [
            r'^import\s+([\w.]+);',
        ],

        # Rust
        'rs': [
            r'^use\s+([\w:]+)',
            r'^mod\s+(\w+)',
        ],
    }

    # Error patterns to extract file paths
    ERROR_FILE_PATTERNS = [
        # JavaScript/Node errors
        r'at\s+(?:\w+\s+)?\(?([^\s:()]+\.[jt]sx?):(\d+)(?::\d+)?\)?',
        r'([^\s:]+\.[jt]sx?):(\d+)(?::\d+)?',

        # Python errors
        r'File\s+"([^"]+)"(?:,\s+line\s+(\d+))?',
        r'([^\s:]+\.py):(\d+)',

        # Go errors
        r'([^\s:]+\.go):(\d+)',

        # Rust errors
        r'-->\s*([^\s:]+\.rs):(\d+)',

        # Java errors
        r'at\s+[\w.$]+\(([^:]+\.java):(\d+)\)',

        # Generic pattern
        r'([^\s:]+\.\w+):(\d+)(?::\d+)?',

        # Module not found
        r"Cannot find module '([^']+)'",
        r'Module not found.*[\'"]([^\'"]+)[\'"]',
        r'No module named [\'"]?([^\'"]+)[\'"]?',
    ]

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self._file_cache: Dict[str, str] = {}
        self._import_graph: Dict[str, Set[str]] = defaultdict(set)

    def build_context(
        self,
        user_message: str,
        errors: List[Dict],
        terminal_logs: List[Dict],
        all_files: List[Dict],
        active_file: Optional[str] = None,
        tech_stack: Optional[List[str]] = None
    ) -> ContextPayload:
        """
        Build the optimal context payload for Claude.

        Args:
            user_message: User's problem description
            errors: List of error objects with message, file, line, stack
            terminal_logs: Terminal output logs
            all_files: All project files (with path and optionally content)
            active_file: Currently open file in editor (optional)
            tech_stack: Detected tech stack (optional)

        Returns:
            ContextPayload ready to send to Claude
        """
        logger.info(f"[ContextEngine] Building context for: {user_message[:50]}...")

        # 1. Extract files from errors
        error_files = self._extract_files_from_errors(errors)
        logger.info(f"[ContextEngine] Found {len(error_files)} files in errors")

        # 2. Extract files from terminal logs
        log_files = self._extract_files_from_logs(terminal_logs)
        logger.info(f"[ContextEngine] Found {len(log_files)} files in logs")

        # 3. Build import graph for dependency analysis
        self._build_import_graph(all_files)

        # 4. Score and select relevant files
        relevant_files = self._select_relevant_files(
            error_files=error_files,
            log_files=log_files,
            all_files=all_files,
            active_file=active_file
        )
        logger.info(f"[ContextEngine] Selected {len(relevant_files)} relevant files")

        # 5. Build file tree (paths only)
        file_tree = [f.get("path", "") for f in all_files]

        # 6. Build logs summary
        logs_summary = self._summarize_logs(errors, terminal_logs)

        # 7. Build error summary
        error_summary = self._build_error_summary(errors)

        # 8. Assemble payload
        payload = ContextPayload(
            user_message=user_message,
            file_tree=file_tree,
            relevant_files={f.path: f.content for f in relevant_files},
            logs=logs_summary,
            tech_stack=", ".join(tech_stack) if tech_stack else "Unknown",
            error_summary=error_summary,
            total_tokens_estimate=self._estimate_tokens(relevant_files)
        )

        logger.info(f"[ContextEngine] Built payload with ~{payload.total_tokens_estimate} tokens")

        return payload

    def _extract_files_from_errors(self, errors: List[Dict]) -> List[Tuple[str, Optional[int], str]]:
        """Extract file paths and line numbers from error objects"""
        files = []
        seen = set()

        for error in errors:
            # Direct file reference
            if error.get("file"):
                file_path = error["file"]
                line = error.get("line")
                if file_path not in seen:
                    files.append((file_path, line, "error_file"))
                    seen.add(file_path)

            # Parse message
            message = error.get("message", "")
            for match in self._extract_file_refs(message):
                if match[0] not in seen:
                    files.append((match[0], match[1], "error_message"))
                    seen.add(match[0])

            # Parse stack trace
            stack = error.get("stack", "")
            for match in self._extract_file_refs(stack):
                if match[0] not in seen:
                    files.append((match[0], match[1], "stack_trace"))
                    seen.add(match[0])

        return files

    def _extract_files_from_logs(self, logs: List[Dict]) -> List[Tuple[str, Optional[int], str]]:
        """Extract file paths from terminal logs"""
        files = []
        seen = set()

        for log in logs:
            content = log.get("content", "")
            log_type = log.get("type", "")

            # Only process error logs
            if log_type not in ["error", "stderr"]:
                continue

            for match in self._extract_file_refs(content):
                if match[0] not in seen:
                    files.append((match[0], match[1], "terminal_log"))
                    seen.add(match[0])

        return files

    def _extract_file_refs(self, text: str) -> List[Tuple[str, Optional[int]]]:
        """Extract file references from text using patterns"""
        refs = []

        for pattern in self.ERROR_FILE_PATTERNS:
            for match in re.finditer(pattern, text, re.MULTILINE):
                groups = match.groups()
                file_path = groups[0] if groups else None
                line_num = int(groups[1]) if len(groups) > 1 and groups[1] else None

                if file_path:
                    # Normalize path
                    file_path = self._normalize_path(file_path)
                    if self._is_valid_project_file(file_path):
                        refs.append((file_path, line_num))

        return refs

    def _normalize_path(self, path: str) -> str:
        """Normalize file path for comparison"""
        # Remove leading ./ or /
        path = re.sub(r'^\.?/', '', path)
        # Convert backslashes to forward slashes
        path = path.replace('\\', '/')
        # Remove node_modules prefix if it leaked in
        if 'node_modules' in path:
            return ""
        return path

    def _is_valid_project_file(self, path: str) -> bool:
        """Check if path is a valid project file (not node_modules, etc.)"""
        if not path:
            return False
        invalid_patterns = [
            'node_modules',
            '__pycache__',
            '.git',
            'dist/',
            'build/',
            '.next/',
            'venv/',
            '.venv/',
        ]
        return not any(p in path for p in invalid_patterns)

    def _build_import_graph(self, all_files: List[Dict]) -> None:
        """Build a graph of file dependencies based on imports"""
        self._import_graph.clear()

        for file_info in all_files:
            path = file_info.get("path", "")
            content = file_info.get("content", "")

            if not content:
                content = self._read_file(path)

            if content:
                imports = self._extract_imports(path, content)
                self._import_graph[path].update(imports)

    def _extract_imports(self, file_path: str, content: str) -> Set[str]:
        """Extract imported file paths from a file's content"""
        imports = set()
        ext = Path(file_path).suffix.lstrip('.')

        # Get patterns for this file type
        patterns = self.IMPORT_PATTERNS.get(ext)
        if patterns is None:
            # Check for aliases (tsx -> ts -> js)
            if ext in ['tsx', 'ts']:
                patterns = self.IMPORT_PATTERNS.get('js')
            else:
                return imports

        if not patterns:
            return imports

        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                import_path = match.group(1)

                # Resolve relative imports
                resolved = self._resolve_import(file_path, import_path)
                if resolved:
                    imports.add(resolved)

        return imports

    def _resolve_import(self, from_file: str, import_path: str) -> Optional[str]:
        """Resolve an import path to an actual file path"""
        # Skip external packages
        if not import_path.startswith('.') and not import_path.startswith('/'):
            # Check if it's a local alias (@/ or ~/)
            if import_path.startswith('@/'):
                import_path = import_path[2:]  # Remove @/
            elif import_path.startswith('~/'):
                import_path = import_path[2:]  # Remove ~/
            else:
                return None  # External package

        # Get directory of the importing file
        from_dir = str(Path(from_file).parent)

        # Handle relative imports
        if import_path.startswith('.'):
            # Resolve relative path
            if import_path.startswith('./'):
                import_path = import_path[2:]
            elif import_path.startswith('../'):
                from_dir = str(Path(from_dir).parent)
                import_path = import_path[3:]

            resolved = str(Path(from_dir) / import_path)
        else:
            resolved = import_path

        # Try common extensions if not specified
        resolved = resolved.replace('\\', '/')
        if not Path(resolved).suffix:
            for ext in ['.tsx', '.ts', '.jsx', '.js', '.py', '/index.tsx', '/index.ts', '/index.js']:
                if self._file_exists(resolved + ext):
                    return resolved + ext

        if self._file_exists(resolved):
            return resolved

        return None

    def _file_exists(self, path: str) -> bool:
        """Check if a file exists in the project"""
        full_path = self.project_path / path
        return full_path.exists()

    def _read_file(self, path: str) -> str:
        """Read file content from disk with caching"""
        if path in self._file_cache:
            return self._file_cache[path]

        try:
            full_path = self.project_path / path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    self._file_cache[path] = content
                    return content
        except Exception as e:
            logger.warning(f"[ContextEngine] Failed to read {path}: {e}")

        return ""

    def _select_relevant_files(
        self,
        error_files: List[Tuple[str, Optional[int], str]],
        log_files: List[Tuple[str, Optional[int], str]],
        all_files: List[Dict],
        active_file: Optional[str]
    ) -> List[FileContext]:
        """Select and score relevant files for context"""
        scored_files: Dict[str, FileContext] = {}

        # Create lookup for all files
        all_files_map = {f.get("path", ""): f for f in all_files}

        # 1. Add files from errors (highest priority)
        for path, line, source in error_files:
            content = all_files_map.get(path, {}).get("content", "") or self._read_file(path)
            if content:
                scored_files[path] = FileContext(
                    path=path,
                    content=content,
                    relevance_score=100.0,  # Highest priority
                    reason=f"Error in {source}",
                    line_hint=line,
                    is_primary=True
                )

        # 2. Add files from logs (high priority)
        for path, line, source in log_files:
            if path not in scored_files:
                content = all_files_map.get(path, {}).get("content", "") or self._read_file(path)
                if content:
                    scored_files[path] = FileContext(
                        path=path,
                        content=content,
                        relevance_score=80.0,
                        reason=f"Referenced in {source}",
                        line_hint=line,
                        is_primary=False
                    )

        # 3. Add active file if not already included
        if active_file and active_file not in scored_files:
            content = all_files_map.get(active_file, {}).get("content", "") or self._read_file(active_file)
            if content:
                scored_files[active_file] = FileContext(
                    path=active_file,
                    content=content,
                    relevance_score=70.0,
                    reason="Active in editor",
                    is_primary=False
                )

        # 4. Add dependencies of error files
        for path in list(scored_files.keys()):
            if scored_files[path].is_primary:
                deps = self._get_dependencies(path, depth=1)
                for dep in deps:
                    if dep not in scored_files:
                        content = all_files_map.get(dep, {}).get("content", "") or self._read_file(dep)
                        if content:
                            scored_files[dep] = FileContext(
                                path=dep,
                                content=content,
                                relevance_score=50.0,
                                reason=f"Imported by {path}",
                                is_primary=False
                            )

        # 5. Add files that import error files (reverse dependencies)
        primary_files = [p for p, f in scored_files.items() if f.is_primary]
        for file_path, imports in self._import_graph.items():
            for primary in primary_files:
                if primary in imports and file_path not in scored_files:
                    content = all_files_map.get(file_path, {}).get("content", "") or self._read_file(file_path)
                    if content:
                        scored_files[file_path] = FileContext(
                            path=file_path,
                            content=content,
                            relevance_score=40.0,
                            reason=f"Imports {primary}",
                            is_primary=False
                        )

        # 6. Sort by relevance and limit
        sorted_files = sorted(
            scored_files.values(),
            key=lambda f: (-f.relevance_score, f.path)
        )

        # 7. Limit to MAX_FILES and MAX_CONTEXT_CHARS
        selected = []
        total_chars = 0

        for file_ctx in sorted_files:
            if len(selected) >= self.MAX_FILES:
                break

            file_chars = len(file_ctx.content)
            if total_chars + file_chars > self.MAX_CONTEXT_CHARS:
                # Try to include truncated if it's a primary file
                if file_ctx.is_primary:
                    remaining = self.MAX_CONTEXT_CHARS - total_chars
                    if remaining > 2000:
                        file_ctx.content = file_ctx.content[:remaining]
                        file_ctx.reason += " (truncated)"
                        selected.append(file_ctx)
                        total_chars += remaining
                break

            selected.append(file_ctx)
            total_chars += file_chars

        return selected

    def _get_dependencies(self, file_path: str, depth: int = 1) -> Set[str]:
        """Get dependencies of a file up to specified depth"""
        deps = set()
        current_level = {file_path}

        for _ in range(depth):
            next_level = set()
            for path in current_level:
                file_deps = self._import_graph.get(path, set())
                for dep in file_deps:
                    if dep not in deps:
                        deps.add(dep)
                        next_level.add(dep)
            current_level = next_level

        return deps

    def _summarize_logs(
        self,
        errors: List[Dict],
        terminal_logs: List[Dict]
    ) -> Dict[str, List[str]]:
        """Summarize logs by category"""
        logs = {
            "browser": [],
            "build": [],
            "backend": [],
            "terminal": []
        }

        # Categorize errors
        for error in errors:
            source = error.get("source", "browser")
            message = error.get("message", "")[:500]  # Limit length

            if source == "browser":
                logs["browser"].append(message)
            elif source == "build":
                logs["build"].append(message)
            elif source == "network":
                logs["backend"].append(message)
            else:
                logs["terminal"].append(message)

        # Add recent terminal errors
        error_logs = [
            log for log in terminal_logs
            if log.get("type") in ["error", "stderr"]
        ][-10:]  # Last 10

        for log in error_logs:
            content = log.get("content", "")[:300]
            if content and content not in logs["terminal"]:
                logs["terminal"].append(content)

        # Remove empty categories
        return {k: v for k, v in logs.items() if v}

    def _build_error_summary(self, errors: List[Dict]) -> str:
        """Build a concise error summary"""
        if not errors:
            return "No specific errors reported"

        summary_parts = []
        for i, error in enumerate(errors[:5], 1):  # Top 5 errors
            msg = error.get("message", "Unknown error")[:200]
            file = error.get("file", "")
            line = error.get("line", "")

            if file:
                summary_parts.append(f"{i}. {msg} (in {file}:{line})")
            else:
                summary_parts.append(f"{i}. {msg}")

        return "\n".join(summary_parts)

    def _estimate_tokens(self, files: List[FileContext]) -> int:
        """Estimate total tokens in the selected files"""
        total_chars = sum(len(f.content) for f in files)
        return total_chars // self.CHARS_PER_TOKEN


# Convenience function for quick context building
def build_fixer_context(
    project_path: str,
    user_message: str,
    errors: List[Dict],
    terminal_logs: List[Dict],
    all_files: List[Dict],
    active_file: Optional[str] = None,
    tech_stack: Optional[List[str]] = None
) -> ContextPayload:
    """
    Build context payload for Claude Fixer Agent.

    Usage:
        payload = build_fixer_context(
            project_path="/path/to/project",
            user_message="Home page is blank",
            errors=[{"message": "TypeError", "file": "Home.jsx", "line": 22}],
            terminal_logs=[...],
            all_files=[{"path": "src/App.jsx", "content": "..."}]
        )

        # Send to Claude:
        # payload.relevant_files contains full file contents
        # payload.file_tree contains all file paths
        # payload.logs contains categorized error logs
    """
    engine = ContextEngine(project_path)
    return engine.build_context(
        user_message=user_message,
        errors=errors,
        terminal_logs=terminal_logs,
        all_files=all_files,
        active_file=active_file,
        tech_stack=tech_stack
    )
