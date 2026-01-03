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
    missing_modules: List[Dict] = field(default_factory=list)  # Files that need to be CREATED


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
        # ============= VITE/WEBPACK SPECIFIC PATTERNS =============
        # Vite: Failed to resolve import "./components/Header" from "src/App.tsx"
        r'Failed to resolve import ["\']([^"\']+)["\'] from ["\']([^"\']+)["\']',
        # Vite: Could not resolve "./components/Header" from "src/App.tsx"
        r'Could not resolve ["\']([^"\']+)["\'] from ["\']([^"\']+)["\']',
        # Vite plugin error: /workspace/src/App.tsx:4:23
        r'/workspace/([^\s:]+):(\d+)(?::\d+)?',
        # Webpack: Module not found: Can't resolve './Header' in '/path/to/src/components'
        r"Can't resolve ['\"]([^'\"]+)['\"] in ['\"]([^'\"]+)['\"]",
        # esbuild: Could not resolve "react"
        r'Could not resolve ["\']([^"\']+)["\']',

        # ============= JAVASCRIPT/NODE ERRORS =============
        r'at\s+(?:\w+\s+)?\(?([^\s:()]+\.[jt]sx?):(\d+)(?::\d+)?\)?',
        r'([^\s:]+\.[jt]sx?):(\d+)(?::\d+)?',

        # ============= PYTHON ERRORS =============
        r'File\s+"([^"]+)"(?:,\s+line\s+(\d+))?',
        r'([^\s:]+\.py):(\d+)',

        # ============= GO ERRORS =============
        r'([^\s:]+\.go):(\d+)',

        # ============= RUST ERRORS =============
        r'-->\s*([^\s:]+\.rs):(\d+)',

        # ============= JAVA ERRORS =============
        r'at\s+[\w.$]+\(([^:]+\.java):(\d+)\)',

        # ============= GENERIC FILE:LINE PATTERN =============
        r'([^\s:]+\.\w+):(\d+)(?::\d+)?',

        # ============= MODULE NOT FOUND PATTERNS =============
        r"Cannot find module '([^']+)'",
        r'Module not found.*[\'"]([^\'"]+)[\'"]',
        r'No module named [\'"]?([^\'"]+)[\'"]?',
        # Import statement extraction
        r'import\s+.*from\s+["\']([^"\']+)["\']',
    ]

    # Patterns to extract missing modules (files that need to be CREATED)
    # Format: (pattern, 'missing_group_index', 'source_group_index')
    MISSING_MODULE_PATTERNS = [
        # ============= JAVASCRIPT/TYPESCRIPT =============
        # Vite/esbuild: Failed to resolve import "./components/Header" from "src/App.tsx"
        (r'Failed to resolve import ["\']([^"\']+)["\'] from ["\']([^"\']+)["\']', 'missing', 'source'),
        # Webpack: Can't resolve './Header'
        (r"Can't resolve ['\"]([^'\"]+)['\"]", 'missing', None),
        # Node: Cannot find module './components/Header'
        (r"Cannot find module ['\"]([^'\"]+)['\"]", 'missing', None),
        # TypeScript: Cannot find module './Header' or its corresponding type declarations
        (r"Cannot find module ['\"]([^'\"]+)['\"] or its corresponding type declarations", 'missing', None),
        # Module not found: Error: Can't resolve
        (r"Module not found.*Can't resolve ['\"]([^'\"]+)['\"]", 'missing', None),

        # ============= PYTHON =============
        # ModuleNotFoundError: No module named 'mymodule'
        (r"No module named ['\"]?([^'\"]+)['\"]?", 'missing', None),
        # ImportError: cannot import name 'MyClass' from 'mymodule'
        (r"cannot import name ['\"]?([^'\"]+)['\"]? from ['\"]?([^'\"]+)['\"]?", 'name', 'module'),
        # ModuleNotFoundError: No module named 'app.services.helper'
        (r"ModuleNotFoundError: No module named ['\"]?([^'\"]+)['\"]?", 'missing', None),

        # ============= GO =============
        # cannot find package "github.com/user/repo" in any of:
        (r'cannot find package ["\']([^"\']+)["\']', 'missing', None),
        # package mypackage is not in GOROOT
        (r'package ([^\s]+) is not in GOROOT', 'missing', None),
        # no required module provides package
        (r'no required module provides package ([^\s;]+)', 'missing', None),

        # ============= RUST =============
        # unresolved import `mymodule`
        (r'unresolved import `([^`]+)`', 'missing', None),
        # error[E0433]: failed to resolve: use of undeclared crate or module `mymod`
        (r'use of undeclared crate or module `([^`]+)`', 'missing', None),
        # cannot find crate `mycrate`
        (r"cannot find crate `([^`]+)`", 'missing', None),

        # ============= JAVA/KOTLIN =============
        # package com.example.helper does not exist
        (r'package ([^\s]+) does not exist', 'missing', None),
        # cannot find symbol: class MyHelper
        (r'cannot find symbol.*class ([^\s]+)', 'missing', None),
        # ClassNotFoundException: com.example.MyClass
        (r'ClassNotFoundException: ([^\s]+)', 'missing', None),

        # ============= RUBY =============
        # LoadError: cannot load such file -- mymodule
        (r"cannot load such file -- ([^\s]+)", 'missing', None),
        # NameError: uninitialized constant MyModule
        (r'uninitialized constant ([^\s]+)', 'missing', None),

        # ============= PHP =============
        # Class 'App\Services\Helper' not found
        (r"Class ['\"]?([^'\"]+)['\"]? not found", 'missing', None),
        # require_once(): Failed opening required 'helper.php'
        (r"Failed opening required ['\"]?([^'\"]+)['\"]?", 'missing', None),

        # ============= C# =============
        # The type or namespace name 'MyClass' could not be found
        (r"type or namespace name ['\"]?([^'\"]+)['\"]? could not be found", 'missing', None),
    ]

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self._file_cache: Dict[str, str] = {}
        self._import_graph: Dict[str, Set[str]] = defaultdict(set)
        self._missing_modules: List[Dict] = []  # Track modules that need to be created

    def scan_project_files(self, extensions: Optional[List[str]] = None) -> List[Dict]:
        """
        Scan project directory for all source files.
        Like Bolt.new, this gives us full project context.
        Supports ALL major programming languages.
        """
        if extensions is None:
            extensions = [
                # JavaScript/TypeScript
                '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.vue', '.svelte',
                # Python
                '.py', '.pyx', '.pyi',
                # Go
                '.go',
                # Rust
                '.rs',
                # Java/Kotlin
                '.java', '.kt', '.kts', '.gradle',
                # C/C++
                '.c', '.cpp', '.cc', '.h', '.hpp', '.hh',
                # C#/.NET
                '.cs', '.csproj', '.sln',
                # Ruby
                '.rb', '.erb', '.rake',
                # PHP
                '.php', '.blade.php',
                # Swift
                '.swift',
                # Scala
                '.scala', '.sc',
                # Elixir/Erlang
                '.ex', '.exs', '.erl', '.hrl',
                # Haskell
                '.hs', '.lhs',
                # F#/OCaml
                '.fs', '.fsx', '.ml', '.mli',
                # Clojure
                '.clj', '.cljs', '.cljc', '.edn',
                # Config files
                '.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.env',
                # Web
                '.html', '.css', '.scss', '.sass', '.less',
                # Docs
                '.md', '.rst', '.txt',
                # Shell
                '.sh', '.bash', '.zsh', '.fish',
                # Docker/Infra
                '.dockerfile',
            ]

        files = []
        exclude_dirs = {
            'node_modules', '__pycache__', '.git', 'dist', 'build', '.next',
            'venv', '.venv', 'env', '.env', 'target', '.cache', 'vendor',
            'coverage', '.nyc_output', 'obj', 'bin', '.gradle', '.idea',
            '.vs', '.vscode', 'packages', '.dart_tool', 'Pods'
        }

        try:
            for root, dirs, filenames in os.walk(self.project_path):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for filename in filenames:
                    ext = Path(filename).suffix.lower()
                    if ext in extensions or filename in ['package.json', 'tsconfig.json', 'Dockerfile', 'requirements.txt']:
                        file_path = Path(root) / filename
                        rel_path = str(file_path.relative_to(self.project_path)).replace('\\', '/')

                        try:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')
                            files.append({
                                'path': rel_path,
                                'content': content,
                                'size': len(content)
                            })
                        except Exception as e:
                            logger.warning(f"[ContextEngine] Failed to read {rel_path}: {e}")

            logger.info(f"[ContextEngine] Scanned {len(files)} project files")
            return files

        except Exception as e:
            logger.error(f"[ContextEngine] Failed to scan project: {e}")
            return []

    def extract_missing_modules(self, errors: List[Dict]) -> List[Dict]:
        """
        Extract modules that need to be CREATED (not just fixed).
        This is key for Bolt.new-style functionality.

        Returns list of:
        {
            'missing_path': './components/Header',
            'source_file': 'src/App.tsx',
            'suggested_path': 'src/components/Header.tsx',
            'type': 'component'  # component, hook, util, type, etc.
        }
        """
        missing = []
        seen = set()

        for error in errors:
            # SAFETY: Handle None values from error dict (key exists but value is None)
            message = error.get('message', '') or ''
            stack = error.get('stack', '') or ''
            # Ensure they are strings
            if not isinstance(message, str):
                message = str(message) if message else ''
            if not isinstance(stack, str):
                stack = str(stack) if stack else ''
            full_text = f"{message}\n{stack}"

            for pattern, missing_group, source_group in self.MISSING_MODULE_PATTERNS:
                for match in re.finditer(pattern, full_text, re.MULTILINE | re.IGNORECASE):
                    groups = match.groups()
                    missing_path = groups[0] if groups else None
                    source_file = groups[1] if len(groups) > 1 and source_group else error.get('file', '')

                    if missing_path and missing_path not in seen:
                        seen.add(missing_path)

                        # Resolve to actual file path
                        suggested_path = self._resolve_missing_module(missing_path, source_file)

                        # Determine module type
                        module_type = self._classify_module_type(missing_path)

                        missing.append({
                            'missing_path': missing_path,
                            'source_file': source_file,
                            'suggested_path': suggested_path,
                            'type': module_type
                        })

                        logger.info(f"[ContextEngine] Found missing module: {missing_path} -> {suggested_path}")

        self._missing_modules = missing
        return missing

    def _resolve_missing_module(self, import_path: str, source_file: str) -> str:
        """Resolve import path to actual file path"""
        # Handle relative imports
        if import_path.startswith('./') or import_path.startswith('../'):
            # Get directory of source file
            source_dir = str(Path(source_file).parent)

            if import_path.startswith('./'):
                resolved = str(Path(source_dir) / import_path[2:])
            else:
                resolved = str(Path(source_dir) / import_path)
        elif import_path.startswith('@/'):
            # Common alias for src/
            resolved = 'src/' + import_path[2:]
        else:
            resolved = import_path

        # Normalize path
        resolved = resolved.replace('\\', '/')

        # Add extension if missing
        if not Path(resolved).suffix:
            # Try to determine extension based on project type
            for ext in ['.tsx', '.ts', '.jsx', '.js']:
                if self._file_exists(resolved + ext):
                    return resolved + ext
            # Default to .tsx for components
            if '/components/' in resolved or 'Component' in resolved:
                return resolved + '.tsx'
            return resolved + '.ts'

        return resolved

    def _classify_module_type(self, import_path: str) -> str:
        """Classify what type of module this is"""
        path_lower = import_path.lower()

        if '/components/' in path_lower or 'component' in path_lower:
            return 'component'
        elif '/hooks/' in path_lower or path_lower.startswith('use'):
            return 'hook'
        elif '/utils/' in path_lower or '/lib/' in path_lower:
            return 'util'
        elif '/types/' in path_lower or '.d.ts' in path_lower:
            return 'type'
        elif '/context/' in path_lower or 'context' in path_lower:
            return 'context'
        elif '/services/' in path_lower or '/api/' in path_lower:
            return 'service'
        elif '/store/' in path_lower or 'store' in path_lower:
            return 'store'
        else:
            return 'module'

    def get_sibling_files(self, file_path: str, all_files: List[Dict]) -> List[Dict]:
        """
        Get files in the same directory (for pattern matching).
        Like Bolt.new, we look at siblings to understand coding patterns.
        """
        file_dir = str(Path(file_path).parent)
        siblings = []

        for f in all_files:
            f_dir = str(Path(f.get('path', '')).parent)
            if f_dir == file_dir and f.get('path') != file_path:
                siblings.append(f)

        return siblings

    def get_related_java_files(self, file_path: str, all_files: List[Dict]) -> List[Dict]:
        """
        For Java projects, get related files that should be checked for consistency.

        When fixing UserServiceImpl.java, also include:
        - UserService.java (interface)
        - User.java (model/entity)
        - UserDto.java (DTO)
        - UserController.java (controller)
        - UserRepository.java (repository)

        This enables the fixer to check consistency across related files.
        """
        if not file_path.endswith('.java'):
            return []

        related = []
        file_name = Path(file_path).stem  # e.g., "UserServiceImpl"

        # Extract entity name from various patterns
        entity_name = None

        # Pattern: UserServiceImpl -> User
        if file_name.endswith('ServiceImpl'):
            entity_name = file_name[:-11]  # Remove "ServiceImpl"
        # Pattern: UserService -> User
        elif file_name.endswith('Service'):
            entity_name = file_name[:-7]  # Remove "Service"
        # Pattern: UserController -> User
        elif file_name.endswith('Controller'):
            entity_name = file_name[:-10]  # Remove "Controller"
        # Pattern: UserRepository -> User
        elif file_name.endswith('Repository'):
            entity_name = file_name[:-10]  # Remove "Repository"
        # Pattern: UserDto -> User
        elif file_name.endswith('Dto') or file_name.endswith('DTO'):
            entity_name = file_name[:-3]  # Remove "Dto" or "DTO"
        # Pattern: Could be the entity itself (User.java)
        elif file_name[0].isupper() and not any(file_name.endswith(s) for s in ['Impl', 'Test', 'Config']):
            entity_name = file_name

        if not entity_name:
            return []

        logger.info(f"[ContextEngine] Looking for Java files related to entity: {entity_name}")

        # Find all related files by entity name
        related_patterns = [
            f"{entity_name}.java",           # Entity/Model
            f"{entity_name}Dto.java",        # DTO
            f"{entity_name}DTO.java",        # DTO (alternative)
            f"{entity_name}Service.java",    # Service interface
            f"{entity_name}ServiceImpl.java", # Service implementation
            f"{entity_name}Controller.java", # Controller
            f"{entity_name}Repository.java", # Repository
        ]

        for f in all_files:
            f_path = f.get('path', '')
            f_name = Path(f_path).name

            # Check if this file matches any related pattern
            if f_name in related_patterns and f_path != file_path:
                related.append(f)
                logger.info(f"[ContextEngine] Found related Java file: {f_path}")

        return related

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

        # 0. If no files provided, scan project directory
        if not all_files:
            logger.info("[ContextEngine] No files provided, scanning project directory...")
            all_files = self.scan_project_files()

        # 1. Extract MISSING modules (files that need to be CREATED)
        missing_modules = self.extract_missing_modules(errors)
        logger.info(f"[ContextEngine] Found {len(missing_modules)} missing modules to create")

        # 2. Extract files from errors
        error_files = self._extract_files_from_errors(errors)
        logger.info(f"[ContextEngine] Found {len(error_files)} files in errors")

        # 3. Extract files from terminal logs
        log_files = self._extract_files_from_logs(terminal_logs)
        logger.info(f"[ContextEngine] Found {len(log_files)} files in logs")

        # 4. Build import graph for dependency analysis
        self._build_import_graph(all_files)

        # 5. Score and select relevant files (including siblings for pattern matching)
        relevant_files = self._select_relevant_files(
            error_files=error_files,
            log_files=log_files,
            all_files=all_files,
            active_file=active_file,
            missing_modules=missing_modules  # Pass missing modules for sibling detection
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
            total_tokens_estimate=self._estimate_tokens(relevant_files),
            missing_modules=missing_modules  # Include files that need to be CREATED
        )

        logger.info(f"[ContextEngine] Built payload with ~{payload.total_tokens_estimate} tokens, {len(missing_modules)} missing modules")

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

            # Parse message (with null safety)
            message = error.get("message", "") or ""
            if not isinstance(message, str):
                message = str(message) if message else ""
            for match in self._extract_file_refs(message):
                if match[0] not in seen:
                    files.append((match[0], match[1], "error_message"))
                    seen.add(match[0])

            # Parse stack trace (with null safety)
            stack = error.get("stack", "") or ""
            if not isinstance(stack, str):
                stack = str(stack) if stack else ""
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

        # SAFETY: Handle None or non-string text
        if text is None or not isinstance(text, str):
            return refs

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
        active_file: Optional[str],
        missing_modules: Optional[List[Dict]] = None
    ) -> List[FileContext]:
        """Select and score relevant files for context"""
        scored_files: Dict[str, FileContext] = {}
        missing_modules = missing_modules or []

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

        # 2. Add SOURCE files for missing modules (the file that has the broken import)
        for missing in missing_modules:
            source_file = missing.get('source_file', '')
            if source_file and source_file not in scored_files:
                content = all_files_map.get(source_file, {}).get("content", "") or self._read_file(source_file)
                if content:
                    scored_files[source_file] = FileContext(
                        path=source_file,
                        content=content,
                        relevance_score=100.0,
                        reason=f"Has missing import: {missing.get('missing_path', '')}",
                        is_primary=True
                    )
                    logger.info(f"[ContextEngine] Added source file for missing module: {source_file}")

        # 3. Add SIBLING files for pattern matching (Bolt.new style!)
        for missing in missing_modules:
            suggested_path = missing.get('suggested_path', '')
            if suggested_path:
                # Get directory where the missing file should be created
                target_dir = str(Path(suggested_path).parent)

                # Find existing files in that directory for pattern matching
                for f in all_files:
                    f_path = f.get('path', '')
                    f_dir = str(Path(f_path).parent)

                    if f_dir == target_dir and f_path not in scored_files:
                        content = f.get('content', '') or self._read_file(f_path)
                        if content:
                            scored_files[f_path] = FileContext(
                                path=f_path,
                                content=content,
                                relevance_score=90.0,  # High priority - pattern matching
                                reason=f"Sibling file for pattern matching (creating {Path(suggested_path).name})",
                                is_primary=False
                            )
                            logger.info(f"[ContextEngine] Added sibling file for pattern: {f_path}")

        # 4. Add files from logs (high priority)
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

        # 5. Add active file if not already included
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

        # 6. Add dependencies of error files
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

        # 7. Add files that import error files (reverse dependencies)
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

        # 8. Add RELATED Java files for consistency checking (CRITICAL for Java projects)
        # When fixing UserServiceImpl.java, also include User.java, UserDto.java, etc.
        primary_files = [p for p, f in scored_files.items() if f.is_primary]
        for primary_path in primary_files:
            if primary_path.endswith('.java'):
                related_files = self.get_related_java_files(primary_path, all_files)
                for related in related_files:
                    related_path = related.get('path', '')
                    if related_path not in scored_files:
                        content = related.get('content', '') or self._read_file(related_path)
                        if content:
                            scored_files[related_path] = FileContext(
                                path=related_path,
                                content=content,
                                relevance_score=95.0,  # Very high - consistency is critical
                                reason=f"Related Java file for consistency with {Path(primary_path).name}",
                                is_primary=False
                            )
                            logger.info(f"[ContextEngine] Added related Java file: {related_path}")

        # 9. Sort by relevance and limit
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
