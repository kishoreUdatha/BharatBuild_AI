"""
SDK-based Fixer Agent

Uses Claude's official tool use API for automatic error fixing.
This is a production-ready implementation that:
- Automatically retries on failures
- Manages context efficiently
- Uses built-in tool handling
"""

import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import json
import re
import os

from anthropic import AsyncAnthropic

from app.core.logging_config import logger
from app.core.config import settings
from app.modules.sdk_agents.sdk_tools import SDKToolManager, SDK_FIXER_SYSTEM_PROMPT
from app.services.unified_storage import unified_storage as storage
from app.services.smart_project_analyzer import smart_analyzer, Technology, ProjectStructure


@dataclass
class FixResult:
    """Result of a fix attempt"""
    success: bool
    files_modified: List[str]
    error_fixed: bool
    message: str
    attempts: int
    final_error: Optional[str] = None


@dataclass
class ParsedError:
    """A single parsed error from build output"""
    file_path: str
    line_number: Optional[int]
    error_type: str  # 'import', 'missing_class', 'type_mismatch', 'syntax', 'other'
    message: str
    raw_text: str


class ErrorCategory:
    """Error categories with priority (lower = fix first)"""
    IMPORT = 1          # Missing imports/packages - fix FIRST (cascading)
    MISSING_FILE = 2    # Missing files/classes
    TYPE_MISMATCH = 3   # Type errors
    SYNTAX = 4          # Syntax errors
    OTHER = 5           # Everything else


class BuildErrorParser:
    """
    Parses build output to extract and categorize ALL compilation errors.

    Supports ALL major technologies:
    - Java (Maven/Gradle): "cannot find symbol", "package does not exist"
    - TypeScript/JavaScript: "Cannot find module", "TS2304", "TS2307"
    - Python: "ImportError", "ModuleNotFoundError", "NameError"
    - Go: "undefined:", "imported and not used", "cannot find package"
    - Rust: "unresolved import", "cannot find", "error[E0433]"
    - C#/.NET: "CS0246", "CS0234", "CS0103"
    - Generic fallback for any other technology

    Error Categories (by priority):
    1. import: Missing imports, packages, modules (FIX FIRST - cascading)
    2. missing_class: Missing classes, types, definitions
    3. type_mismatch: Type incompatibilities, wrong arguments
    4. syntax: Syntax errors, missing tokens
    5. other: Everything else
    """

    # Java error patterns
    JAVA_PATTERNS = {
        'import': [
            r'package\s+(\S+)\s+does not exist',
            r'cannot find symbol.*class\s+(\w+)',
            r'cannot find symbol.*variable\s+(\w+)',
            r'cannot access\s+(\w+)',
            r'error: cannot find symbol',
        ],
        'missing_class': [
            r'class\s+(\w+)\s+is public.*should be declared in a file',
            r'cannot be resolved to a type',
        ],
        'type_mismatch': [
            r'incompatible types',
            r'required:\s+\S+.*found:\s+\S+',
            r'method\s+\S+\s+in class\s+\S+\s+cannot be applied',
        ],
        'syntax': [
            r"';' expected",
            r"illegal start of",
            r"unclosed string literal",
            r"reached end of file while parsing",
        ],
    }

    # TypeScript/JavaScript error patterns
    TS_PATTERNS = {
        'import': [
            r"Cannot find module '([^']+)'",
            r"Module '([^']+)' has no exported member",
            r"TS2307.*Cannot find module",
            r"TS2305.*has no exported member",
        ],
        'missing_class': [
            r"TS2304.*Cannot find name '(\w+)'",
            r"'(\w+)' is not defined",
        ],
        'type_mismatch': [
            r"TS2322.*Type '.*' is not assignable",
            r"TS2345.*Argument of type",
            r"TS2339.*Property '(\w+)' does not exist",
        ],
        'syntax': [
            r"TS1005.*'.*' expected",
            r"Unexpected token",
            r"SyntaxError:",
        ],
    }

    # Python error patterns
    PYTHON_PATTERNS = {
        'import': [
            r"ImportError: No module named '?(\w+)'?",
            r"ModuleNotFoundError: No module named '?(\w+)'?",
            r"cannot import name '(\w+)'",
        ],
        'missing_class': [
            r"NameError: name '(\w+)' is not defined",
        ],
        'type_mismatch': [
            r"TypeError:",
            r"AttributeError: '(\w+)' object has no attribute",
        ],
        'syntax': [
            r"SyntaxError:",
            r"IndentationError:",
        ],
    }

    # Go error patterns
    GO_PATTERNS = {
        'import': [
            r'could not import\s+(\S+)',
            r'package\s+(\S+)\s+is not in',
            r'cannot find package',
            r'imported and not used',
        ],
        'missing_class': [
            r'undefined:\s+(\w+)',
            r'undeclared name:\s+(\w+)',
        ],
        'type_mismatch': [
            r'cannot use\s+.+\s+as\s+.+\s+in',
            r'cannot convert',
            r'incompatible type',
        ],
        'syntax': [
            r'expected\s+.+,\s+found',
            r'syntax error:',
            r'missing\s+.+\s+in',
        ],
    }

    # Rust error patterns
    RUST_PATTERNS = {
        'import': [
            r'unresolved import\s+`([^`]+)`',
            r"cannot find\s+.+\s+`([^`]+)`\s+in",
            r'failed to resolve',
            r'could not find\s+`([^`]+)`',
        ],
        'missing_class': [
            r'cannot find\s+(?:type|struct|enum|trait)\s+`([^`]+)`',
            r'not found in this scope',
        ],
        'type_mismatch': [
            r'mismatched types',
            r'expected\s+`[^`]+`,\s+found\s+`[^`]+`',
            r'the trait bound\s+.+\s+is not satisfied',
        ],
        'syntax': [
            r'expected\s+.+,\s+found\s+',
            r'unexpected\s+',
            r'unclosed delimiter',
        ],
    }

    # C#/.NET error patterns
    CSHARP_PATTERNS = {
        'import': [
            r"CS0246.*type or namespace name '(\w+)'.*could not be found",
            r"CS0234.*type or namespace name '(\w+)'.*does not exist",
            r'are you missing a using directive',
        ],
        'missing_class': [
            r"CS0103.*name '(\w+)' does not exist",
            r"CS1061.*does not contain a definition for '(\w+)'",
        ],
        'type_mismatch': [
            r'CS0029.*Cannot implicitly convert type',
            r'CS1503.*Argument.*cannot convert',
        ],
        'syntax': [
            r"CS1002.*';' expected",
            r'CS1513.*}.*expected',
            r'CS1519.*Invalid token',
        ],
    }

    @classmethod
    def parse_build_output(cls, output: str, technology: str = "auto") -> List[ParsedError]:
        """
        Parse build output and extract all errors.

        Supports ALL major technologies:
        - Java (Maven/Gradle)
        - TypeScript/JavaScript (npm, Vite, webpack)
        - Python (pip, pytest, mypy)
        - Go (go build, go test)
        - Rust (cargo build)
        - C#/.NET (dotnet build)
        - Generic fallback for others

        Args:
            output: Build command output (stdout + stderr)
            technology: Project technology (java, typescript, python, go, rust, csharp, auto)

        Returns:
            List of ParsedError objects grouped by file
        """
        errors = []
        lines = output.split('\n')

        # Auto-detect technology from output
        if technology == "auto":
            output_lower = output.lower()
            if 'maven' in output_lower or '.java:' in output or 'BUILD FAILURE' in output or 'gradle' in output_lower:
                technology = 'java'
            elif 'error TS' in output or ('.ts' in output and 'error' in output_lower):
                technology = 'typescript'
            elif 'Traceback' in output or 'ModuleNotFoundError' in output or '.py' in output:
                technology = 'python'
            elif '.go:' in output or 'go build' in output_lower or 'go test' in output_lower:
                technology = 'go'
            elif 'error[E' in output or 'cargo' in output_lower or '.rs:' in output:
                technology = 'rust'
            elif 'error CS' in output or 'dotnet' in output_lower or '.cs(' in output:
                technology = 'csharp'
            else:
                technology = 'generic'

        # Parse based on technology
        if technology == 'java':
            errors = cls._parse_java_errors(output, lines)
        elif technology in ['typescript', 'javascript']:
            errors = cls._parse_typescript_errors(output, lines)
        elif technology == 'python':
            errors = cls._parse_python_errors(output, lines)
        elif technology == 'go':
            errors = cls._parse_go_errors(output, lines)
        elif technology == 'rust':
            errors = cls._parse_rust_errors(output, lines)
        elif technology == 'csharp':
            errors = cls._parse_csharp_errors(output, lines)
        else:
            errors = cls._parse_generic_errors(output, lines)

        return errors

    @classmethod
    def _parse_java_errors(cls, output: str, lines: List[str]) -> List[ParsedError]:
        """Parse Java/Maven build errors"""
        errors = []

        # Pattern: [ERROR] /path/to/File.java:[line,col] error message
        error_pattern = re.compile(r'\[ERROR\]\s+(.+\.java):\[(\d+),\d+\]\s+(.+)')
        # Alternative: src/main/java/com/example/File.java:10: error: message
        alt_pattern = re.compile(r'(.+\.java):(\d+):\s*error:\s*(.+)')

        for i, line in enumerate(lines):
            match = error_pattern.search(line) or alt_pattern.search(line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                message = match.group(3)

                # Categorize error
                error_type = cls._categorize_java_error(message)

                errors.append(ParsedError(
                    file_path=file_path,
                    line_number=line_num,
                    error_type=error_type,
                    message=message,
                    raw_text=line
                ))

        return errors

    @classmethod
    def _categorize_java_error(cls, message: str) -> str:
        """Categorize a Java error message"""
        message_lower = message.lower()

        if 'package' in message_lower and 'does not exist' in message_lower:
            return 'import'
        if 'cannot find symbol' in message_lower:
            return 'import'
        if 'cannot access' in message_lower:
            return 'import'
        if 'incompatible types' in message_lower:
            return 'type_mismatch'
        if 'cannot be applied' in message_lower:
            return 'type_mismatch'
        if "expected" in message_lower or 'illegal start' in message_lower:
            return 'syntax'

        return 'other'

    @classmethod
    def _parse_typescript_errors(cls, output: str, lines: List[str]) -> List[ParsedError]:
        """Parse TypeScript/JavaScript build errors"""
        errors = []

        # Pattern: src/file.ts(10,5): error TS2304: Cannot find name 'X'
        # Or: src/file.ts:10:5 - error TS2304: Cannot find name 'X'
        error_pattern = re.compile(r'(.+\.[tj]sx?)[:\(](\d+)[,:]?\d*\)?:?\s*[-:]?\s*error\s+(TS\d+)?:?\s*(.+)')

        for line in lines:
            match = error_pattern.search(line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                ts_code = match.group(3) or ''
                message = match.group(4)

                # Categorize error
                error_type = cls._categorize_ts_error(ts_code, message)

                errors.append(ParsedError(
                    file_path=file_path,
                    line_number=line_num,
                    error_type=error_type,
                    message=message,
                    raw_text=line
                ))

        return errors

    @classmethod
    def _categorize_ts_error(cls, ts_code: str, message: str) -> str:
        """Categorize a TypeScript error"""
        if ts_code in ['TS2307', 'TS2305']:
            return 'import'
        if ts_code == 'TS2304':
            return 'missing_class'
        if ts_code in ['TS2322', 'TS2345', 'TS2339']:
            return 'type_mismatch'
        if ts_code == 'TS1005':
            return 'syntax'

        message_lower = message.lower()
        if 'cannot find module' in message_lower:
            return 'import'
        if 'cannot find name' in message_lower:
            return 'missing_class'
        if 'is not assignable' in message_lower:
            return 'type_mismatch'

        return 'other'

    @classmethod
    def _parse_python_errors(cls, output: str, lines: List[str]) -> List[ParsedError]:
        """Parse Python build/lint errors"""
        errors = []

        # Pattern: File "path/to/file.py", line 10
        file_pattern = re.compile(r'File "(.+\.py)", line (\d+)')
        error_line_pattern = re.compile(r'(ImportError|ModuleNotFoundError|NameError|TypeError|SyntaxError|IndentationError):?\s*(.+)?')

        current_file = None
        current_line = None

        for line in lines:
            file_match = file_pattern.search(line)
            if file_match:
                current_file = file_match.group(1)
                current_line = int(file_match.group(2))
                continue

            error_match = error_line_pattern.search(line)
            if error_match and current_file:
                error_name = error_match.group(1)
                message = error_match.group(2) or ''

                # Categorize
                if error_name in ['ImportError', 'ModuleNotFoundError']:
                    error_type = 'import'
                elif error_name == 'NameError':
                    error_type = 'missing_class'
                elif error_name == 'TypeError':
                    error_type = 'type_mismatch'
                else:
                    error_type = 'syntax'

                errors.append(ParsedError(
                    file_path=current_file,
                    line_number=current_line,
                    error_type=error_type,
                    message=f"{error_name}: {message}",
                    raw_text=line
                ))
                current_file = None

        return errors

    @classmethod
    def _parse_go_errors(cls, output: str, lines: List[str]) -> List[ParsedError]:
        """Parse Go build errors"""
        errors = []

        # Pattern: ./file.go:10:5: error message
        # Or: file.go:10: error message
        error_pattern = re.compile(r'\.?/?(.+\.go):(\d+)(?::\d+)?:\s*(.+)')

        for line in lines:
            match = error_pattern.search(line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                message = match.group(3)

                # Categorize error
                error_type = cls._categorize_go_error(message)

                errors.append(ParsedError(
                    file_path=file_path,
                    line_number=line_num,
                    error_type=error_type,
                    message=message,
                    raw_text=line
                ))

        return errors

    @classmethod
    def _categorize_go_error(cls, message: str) -> str:
        """Categorize a Go error message"""
        message_lower = message.lower()

        if 'could not import' in message_lower or 'cannot find package' in message_lower:
            return 'import'
        if 'imported and not used' in message_lower:
            return 'import'
        if 'undefined' in message_lower or 'undeclared' in message_lower:
            return 'missing_class'
        if 'cannot use' in message_lower or 'cannot convert' in message_lower:
            return 'type_mismatch'
        if 'expected' in message_lower or 'syntax error' in message_lower:
            return 'syntax'

        return 'other'

    @classmethod
    def _parse_rust_errors(cls, output: str, lines: List[str]) -> List[ParsedError]:
        """Parse Rust/Cargo build errors"""
        errors = []

        # Pattern: error[E0433]: failed to resolve...
        #    --> src/main.rs:5:5
        error_code_pattern = re.compile(r'error\[E\d+\]:\s*(.+)')
        location_pattern = re.compile(r'-->\s*(.+\.rs):(\d+):\d+')

        current_message = None

        for i, line in enumerate(lines):
            # Check for error message
            error_match = error_code_pattern.search(line)
            if error_match:
                current_message = error_match.group(1)
                continue

            # Check for location
            if current_message:
                loc_match = location_pattern.search(line)
                if loc_match:
                    file_path = loc_match.group(1)
                    line_num = int(loc_match.group(2))

                    # Categorize error
                    error_type = cls._categorize_rust_error(current_message)

                    errors.append(ParsedError(
                        file_path=file_path,
                        line_number=line_num,
                        error_type=error_type,
                        message=current_message,
                        raw_text=line
                    ))
                    current_message = None

        return errors

    @classmethod
    def _categorize_rust_error(cls, message: str) -> str:
        """Categorize a Rust error message"""
        message_lower = message.lower()

        if 'unresolved import' in message_lower or 'failed to resolve' in message_lower:
            return 'import'
        if 'could not find' in message_lower:
            return 'import'
        if 'cannot find' in message_lower or 'not found in this scope' in message_lower:
            return 'missing_class'
        if 'mismatched types' in message_lower or 'expected' in message_lower:
            return 'type_mismatch'
        if 'trait bound' in message_lower:
            return 'type_mismatch'
        if 'unexpected' in message_lower or 'unclosed' in message_lower:
            return 'syntax'

        return 'other'

    @classmethod
    def _parse_csharp_errors(cls, output: str, lines: List[str]) -> List[ParsedError]:
        """Parse C#/.NET build errors"""
        errors = []

        # Pattern: File.cs(10,5): error CS0246: The type or namespace...
        # Or: src/File.cs(10,5): error CS0246: message
        error_pattern = re.compile(r'(.+\.cs)\((\d+),\d+\):\s*error\s+(CS\d+):\s*(.+)')

        for line in lines:
            match = error_pattern.search(line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                cs_code = match.group(3)
                message = match.group(4)

                # Categorize error
                error_type = cls._categorize_csharp_error(cs_code, message)

                errors.append(ParsedError(
                    file_path=file_path,
                    line_number=line_num,
                    error_type=error_type,
                    message=f"{cs_code}: {message}",
                    raw_text=line
                ))

        return errors

    @classmethod
    def _categorize_csharp_error(cls, cs_code: str, message: str) -> str:
        """Categorize a C# error message"""
        # Common C# error codes
        import_errors = ['CS0246', 'CS0234', 'CS0400']  # Missing type/namespace
        missing_errors = ['CS0103', 'CS1061', 'CS0117']  # Name doesn't exist
        type_errors = ['CS0029', 'CS1503', 'CS0266']  # Cannot convert
        syntax_errors = ['CS1002', 'CS1513', 'CS1519', 'CS1026']  # Expected tokens

        if cs_code in import_errors:
            return 'import'
        if cs_code in missing_errors:
            return 'missing_class'
        if cs_code in type_errors:
            return 'type_mismatch'
        if cs_code in syntax_errors:
            return 'syntax'

        return 'other'

    @classmethod
    def _parse_generic_errors(cls, output: str, lines: List[str]) -> List[ParsedError]:
        """Parse generic error output"""
        errors = []

        # Generic pattern: file:line: error/Error message
        error_pattern = re.compile(r'(.+):(\d+):?\s*[Ee]rror:?\s*(.+)')

        for line in lines:
            match = error_pattern.search(line)
            if match:
                errors.append(ParsedError(
                    file_path=match.group(1),
                    line_number=int(match.group(2)),
                    error_type='other',
                    message=match.group(3),
                    raw_text=line
                ))

        return errors

    @classmethod
    def group_by_category(cls, errors: List[ParsedError]) -> Dict[str, List[ParsedError]]:
        """
        Group errors by category for prioritized fixing.

        Returns dict with keys: 'import', 'missing_class', 'type_mismatch', 'syntax', 'other'
        Sorted by priority (imports first).
        """
        groups = {
            'import': [],
            'missing_class': [],
            'type_mismatch': [],
            'syntax': [],
            'other': [],
        }

        for error in errors:
            if error.error_type in groups:
                groups[error.error_type].append(error)
            else:
                groups['other'].append(error)

        return groups

    @classmethod
    def group_by_file(cls, errors: List[ParsedError]) -> Dict[str, List[ParsedError]]:
        """Group errors by file path"""
        groups = {}
        for error in errors:
            if error.file_path not in groups:
                groups[error.file_path] = []
            groups[error.file_path].append(error)
        return groups

    @classmethod
    def get_unique_root_causes(cls, errors: List[ParsedError]) -> List[str]:
        """
        Extract unique root causes from errors.

        For example, 10 "cannot find symbol: User" errors are really 1 root cause.
        """
        seen = set()
        root_causes = []

        for error in errors:
            # Extract the key identifier from the message
            # For Java: extract class/variable name
            symbol_match = re.search(r'symbol:?\s*(?:class|variable|method)?\s*(\w+)', error.message, re.IGNORECASE)
            package_match = re.search(r'package\s+(\S+)', error.message)
            module_match = re.search(r"module '([^']+)'", error.message)

            if symbol_match:
                key = f"symbol:{symbol_match.group(1)}"
            elif package_match:
                key = f"package:{package_match.group(1)}"
            elif module_match:
                key = f"module:{module_match.group(1)}"
            else:
                key = error.message[:50]

            if key not in seen:
                seen.add(key)
                root_causes.append(key)

        return root_causes


class SDKFixerAgent:
    """
    Claude Agent SDK-style Fixer Agent.

    Uses the official Anthropic tool use API for:
    - Automatic tool execution loop
    - Built-in error handling
    - Context management
    - Retry logic
    - SMART PROJECT ANALYSIS for technology-aware fixing

    This replaces the manual implementation in fixer_agent.py with
    a cleaner, SDK-based approach that supports ALL technologies:
    - React, Vue, Angular, Svelte, Next.js
    - Python (FastAPI, Django, Flask)
    - Java (Spring Boot)
    - Go, Rust
    - Fullstack monorepos
    """

    MAX_ATTEMPTS = 5
    MAX_TOOL_ITERATIONS = 40  # Increased from 20 for complex fullstack projects

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192
    ):
        """Initialize the SDK Fixer Agent"""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model
        self.max_tokens = max_tokens
        self.tools = SDKToolManager.get_fixer_tools()
        self.system_prompt = SDK_FIXER_SYSTEM_PROMPT
        # Cache for project structures
        self._project_cache: Dict[str, ProjectStructure] = {}

    async def _get_project_structure(
        self,
        project_id: str,
        user_id: str
    ) -> Optional[ProjectStructure]:
        """
        Get project structure from cache or analyze.

        This enables technology-aware fixing with proper working directories.
        """
        cache_key = f"{project_id}:{user_id}"

        if cache_key not in self._project_cache:
            try:
                structure = await smart_analyzer.analyze_project(
                    project_id=project_id,
                    user_id=user_id
                )
                self._project_cache[cache_key] = structure
                logger.info(f"[SDKFixerAgent:{project_id}] Analyzed project: {structure.technology.value}")
            except Exception as e:
                logger.warning(f"[SDKFixerAgent:{project_id}] Failed to analyze project: {e}")
                return None

        return self._project_cache.get(cache_key)

    async def fix_error(
        self,
        project_id: str,
        user_id: str,
        error_message: str,
        stack_trace: str = "",
        command: str = "",
        context_files: Optional[Dict[str, str]] = None
    ) -> FixResult:
        """
        Fix an error using the SDK tool loop with technology awareness.

        Args:
            project_id: Project identifier
            user_id: User identifier
            error_message: The error to fix
            stack_trace: Stack trace if available
            command: Command that caused the error
            context_files: Dict of file paths to contents for context

        Returns:
            FixResult with success status and details
        """
        logger.info(f"[SDKFixerAgent:{project_id}] Starting fix for: {error_message[:100]}...")

        # Get project structure for technology-aware fixing
        project_structure = await self._get_project_structure(project_id, user_id)

        # Build initial message with error context AND technology info
        user_message = self._build_error_prompt(
            error_message=error_message,
            stack_trace=stack_trace,
            command=command,
            context_files=context_files,
            project_structure=project_structure
        )

        # Initialize conversation
        messages = [{"role": "user", "content": user_message}]
        files_modified = []
        attempts = 0

        try:
            # Run the agent loop
            while attempts < self.MAX_TOOL_ITERATIONS:
                attempts += 1

                # Call Claude with tools
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=self.system_prompt,
                    tools=self.tools,
                    messages=messages
                )

                logger.info(f"[SDKFixerAgent:{project_id}] Iteration {attempts}, stop_reason: {response.stop_reason}")

                # Check if we're done
                if response.stop_reason == "end_turn":
                    # Extract final message
                    final_text = self._extract_text(response.content)
                    return FixResult(
                        success=True,
                        files_modified=files_modified,
                        error_fixed=True,
                        message=final_text,
                        attempts=attempts
                    )

                # Process tool uses
                if response.stop_reason == "tool_use":
                    # Add assistant's response to messages
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Execute tools and collect results
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            result = await self._execute_tool(
                                project_id=project_id,
                                user_id=user_id,
                                tool_name=block.name,
                                tool_input=block.input
                            )

                            # Track modified files
                            if block.name in ["str_replace", "str_replace_all", "create_file", "insert_lines"]:
                                file_path = block.input.get("path", "")
                                if file_path and file_path not in files_modified:
                                    files_modified.append(file_path)

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result
                            })

                    # Add tool results to messages
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                else:
                    # Unexpected stop reason
                    logger.warning(f"[SDKFixerAgent:{project_id}] Unexpected stop_reason: {response.stop_reason}")
                    break

            # Max iterations reached
            return FixResult(
                success=False,
                files_modified=files_modified,
                error_fixed=False,
                message="Max iterations reached without completing fix",
                attempts=attempts
            )

        except Exception as e:
            logger.error(f"[SDKFixerAgent:{project_id}] Error during fix: {e}")
            return FixResult(
                success=False,
                files_modified=files_modified,
                error_fixed=False,
                message=str(e),
                attempts=attempts,
                final_error=str(e)
            )

    async def fix_with_retry(
        self,
        project_id: str,
        user_id: str,
        error_message: str,
        stack_trace: str = "",
        command: str = "",
        build_command: str = "npm run build",
        max_retries: int = 3
    ) -> FixResult:
        """
        Fix error with automatic retry and verification.

        After each fix attempt, runs the build command to verify.
        Continues until fixed or max retries reached.

        Args:
            project_id: Project identifier
            user_id: User identifier
            error_message: Initial error message
            stack_trace: Stack trace if available
            command: Command that caused the error
            build_command: Command to run for verification
            max_retries: Maximum number of fix attempts

        Returns:
            FixResult with final status
        """
        current_error = error_message
        current_stack = stack_trace
        all_files_modified = []
        total_attempts = 0

        for retry in range(max_retries):
            logger.info(f"[SDKFixerAgent:{project_id}] Fix attempt {retry + 1}/{max_retries}")

            # Attempt fix
            result = await self.fix_error(
                project_id=project_id,
                user_id=user_id,
                error_message=current_error,
                stack_trace=current_stack,
                command=command
            )

            total_attempts += result.attempts
            all_files_modified.extend(result.files_modified)

            if not result.success:
                continue

            # Verify by running build
            verify_result = await self._execute_tool(
                project_id=project_id,
                user_id=user_id,
                tool_name="bash",
                tool_input={"command": build_command, "timeout": 60}
            )

            # Check if build succeeded
            if "error" not in verify_result.lower() and "failed" not in verify_result.lower():
                logger.info(f"[SDKFixerAgent:{project_id}] Fix verified successfully!")
                return FixResult(
                    success=True,
                    files_modified=list(set(all_files_modified)),
                    error_fixed=True,
                    message=f"Fixed after {retry + 1} attempts",
                    attempts=total_attempts
                )

            # Extract new error for next attempt
            current_error = verify_result
            current_stack = ""
            logger.warning(f"[SDKFixerAgent:{project_id}] Build still failing, retrying...")

        # Max retries exhausted
        return FixResult(
            success=False,
            files_modified=list(set(all_files_modified)),
            error_fixed=False,
            message=f"Failed to fix after {max_retries} attempts",
            attempts=total_attempts,
            final_error=current_error
        )

    async def fix_all_errors_smart(
        self,
        project_id: str,
        user_id: str,
        build_command: str = "npm run build",
        max_category_iterations: int = 5,
        max_total_iterations: int = 15
    ) -> FixResult:
        """
        SMART BATCHING: Fix ALL compilation errors using prioritized category-based approach.

        This is the recommended method for fixing projects with many errors (100+).

        Strategy:
        1. Run build and collect ALL errors
        2. Parse and group errors by category (import, type, syntax, etc.)
        3. Fix one category at a time, starting with imports (highest impact)
        4. Rebuild after each category to see TRUE remaining errors
        5. Repeat until fixed or max iterations

        Why this works better:
        - 100 errors might be 5 root causes (e.g., missing import causes 20 "cannot find symbol")
        - Fixing imports first resolves cascading errors
        - Rebuilding after each category shows actual remaining issues

        Args:
            project_id: Project identifier
            user_id: User identifier
            build_command: Command to build/compile the project
            max_category_iterations: Max attempts per error category
            max_total_iterations: Max total fix iterations across all categories

        Returns:
            FixResult with final status
        """
        logger.info(f"[SmartFixer:{project_id}] Starting smart batching fix with command: {build_command}")

        all_files_modified = []
        total_attempts = 0
        iteration = 0

        # Priority order for fixing categories
        CATEGORY_PRIORITY = ['import', 'missing_class', 'type_mismatch', 'syntax', 'other']

        while iteration < max_total_iterations:
            iteration += 1
            logger.info(f"[SmartFixer:{project_id}] === Iteration {iteration}/{max_total_iterations} ===")

            # Step 1: Run build and collect ALL errors
            build_output = await self._execute_tool(
                project_id=project_id,
                user_id=user_id,
                tool_name="bash",
                tool_input={"command": build_command, "timeout": 120}
            )

            # Step 2: Check if build succeeded
            if self._is_build_successful(build_output):
                logger.info(f"[SmartFixer:{project_id}] ✓ Build succeeded! All errors fixed.")
                return FixResult(
                    success=True,
                    files_modified=list(set(all_files_modified)),
                    error_fixed=True,
                    message=f"All errors fixed after {iteration} iterations",
                    attempts=total_attempts
                )

            # Step 3: Parse and categorize errors
            errors = BuildErrorParser.parse_build_output(build_output)
            if not errors:
                # No parseable errors but build failed - use generic fix
                logger.warning(f"[SmartFixer:{project_id}] No parseable errors, falling back to generic fix")
                result = await self.fix_error(
                    project_id=project_id,
                    user_id=user_id,
                    error_message=build_output,
                    command=build_command
                )
                total_attempts += result.attempts
                all_files_modified.extend(result.files_modified)
                continue

            # Group errors by category
            error_groups = BuildErrorParser.group_by_category(errors)
            root_causes = BuildErrorParser.get_unique_root_causes(errors)

            logger.info(f"[SmartFixer:{project_id}] Found {len(errors)} errors, {len(root_causes)} unique root causes")
            for cat, errs in error_groups.items():
                if errs:
                    logger.info(f"[SmartFixer:{project_id}]   - {cat}: {len(errs)} errors")

            # Step 4: Fix highest priority category with errors
            fixed_category = False
            for category in CATEGORY_PRIORITY:
                category_errors = error_groups.get(category, [])
                if not category_errors:
                    continue

                logger.info(f"[SmartFixer:{project_id}] Fixing category: {category} ({len(category_errors)} errors)")

                # Build focused prompt for this category
                result = await self._fix_error_category(
                    project_id=project_id,
                    user_id=user_id,
                    category=category,
                    errors=category_errors,
                    build_command=build_command
                )

                total_attempts += result.attempts
                all_files_modified.extend(result.files_modified)

                if result.success:
                    fixed_category = True
                    logger.info(f"[SmartFixer:{project_id}] ✓ Category {category} fixed, rebuilding...")
                    break  # Rebuild to see remaining errors
                else:
                    logger.warning(f"[SmartFixer:{project_id}] ✗ Failed to fix {category}, trying next category")

            if not fixed_category:
                # No category could be fixed - try generic approach for remaining errors
                logger.warning(f"[SmartFixer:{project_id}] No category fixed, trying generic fix")
                result = await self.fix_error(
                    project_id=project_id,
                    user_id=user_id,
                    error_message=build_output[:5000],
                    command=build_command
                )
                total_attempts += result.attempts
                all_files_modified.extend(result.files_modified)

        # Max iterations reached
        logger.warning(f"[SmartFixer:{project_id}] Max iterations ({max_total_iterations}) reached")
        return FixResult(
            success=False,
            files_modified=list(set(all_files_modified)),
            error_fixed=False,
            message=f"Max iterations reached. Fixed some errors but build still failing.",
            attempts=total_attempts,
            final_error=build_output[:2000] if 'build_output' in locals() else "Unknown"
        )

    async def _fix_error_category(
        self,
        project_id: str,
        user_id: str,
        category: str,
        errors: List[ParsedError],
        build_command: str
    ) -> FixResult:
        """
        Fix all errors in a specific category.

        Groups errors by file and fixes them together for efficiency.
        """
        files_modified = []
        attempts = 0

        # Group errors by file for efficient fixing
        errors_by_file = BuildErrorParser.group_by_file(errors)
        root_causes = BuildErrorParser.get_unique_root_causes(errors)

        # Build a focused prompt for this category
        category_descriptions = {
            'import': 'IMPORT/PACKAGE ERRORS - Fix missing imports, wrong package names, missing dependencies',
            'missing_class': 'MISSING CLASS/TYPE ERRORS - Create missing files or fix references',
            'type_mismatch': 'TYPE MISMATCH ERRORS - Fix type incompatibilities and method signatures',
            'syntax': 'SYNTAX ERRORS - Fix syntax issues like missing semicolons, brackets',
            'other': 'OTHER ERRORS - Fix remaining compilation issues',
        }

        # Get project structure for context
        project_structure = await self._get_project_structure(project_id, user_id)

        # Build context files (files with errors)
        context_files = {}
        for file_path in list(errors_by_file.keys())[:10]:  # Limit to 10 files
            try:
                content = await storage.read_from_sandbox(project_id, file_path, user_id)
                if content:
                    context_files[file_path] = content
            except Exception:
                pass

        # Build the prompt
        error_summary = []
        for file_path, file_errors in errors_by_file.items():
            error_summary.append(f"\n### {file_path}")
            for err in file_errors[:5]:  # Limit errors per file
                error_summary.append(f"  Line {err.line_number}: {err.message}")

        prompt = f"""## {category_descriptions.get(category, 'ERRORS TO FIX')}

**Total Errors in this Category:** {len(errors)}
**Unique Root Causes:** {len(root_causes)}
**Root Causes:** {', '.join(root_causes[:10])}

**Files with Errors:**
{''.join(error_summary[:50])}

## Instructions

1. **Analyze** the root causes - many errors share the same cause
2. **Read** the affected files using `view_file`
3. **Fix** the root causes (not individual errors):
   - For import errors: Add missing imports, fix package names
   - For missing class: Create the missing file or fix the reference
   - For type errors: Fix the type definition or usage
4. **Verify** by running: `{build_command}`

IMPORTANT:
- Fix ROOT CAUSES, not individual error lines
- One missing import can cause 10+ "cannot find symbol" errors
- After fixing, the build will show remaining errors
"""

        # Use the main fix_error method with our focused prompt
        result = await self.fix_error(
            project_id=project_id,
            user_id=user_id,
            error_message=prompt,
            command=build_command
        )

        return result

    def _is_build_successful(self, build_output: str) -> bool:
        """Check if build output indicates success"""
        output_lower = build_output.lower()

        # Success indicators
        success_patterns = [
            'build successful',
            'build success',
            'compiled successfully',
            'compilation successful',
            '0 errors',
            'built in',  # Vite: "built in 1.23s"
        ]

        # Failure indicators
        failure_patterns = [
            'error:',
            'error ',
            'failed',
            'failure',
            'cannot find',
            'does not exist',
            'compilation error',
            'build failed',
        ]

        # Check for explicit success
        for pattern in success_patterns:
            if pattern in output_lower:
                # But make sure no errors
                has_error = any(fp in output_lower for fp in failure_patterns)
                if not has_error:
                    return True

        # Check for errors
        for pattern in failure_patterns:
            if pattern in output_lower:
                return False

        # No clear indication - assume success if short output without errors
        return len(build_output) < 500 and 'error' not in output_lower

    def _build_error_prompt(
        self,
        error_message: str,
        stack_trace: str = "",
        command: str = "",
        context_files: Optional[Dict[str, str]] = None,
        project_structure: Optional[ProjectStructure] = None
    ) -> str:
        """Build the initial prompt with error context and technology info"""
        parts = []

        # Add technology context if available
        if project_structure:
            parts.append("## Project Context\n")
            parts.append(f"**Technology:** {project_structure.technology.value}\n")
            parts.append(f"**Working Directory:** {project_structure.working_directory.name}/\n")
            parts.append(f"**Install Command:** `{project_structure.install_command}`\n")
            parts.append(f"**Run Command:** `{project_structure.run_command}`\n")
            if project_structure.entry_points:
                parts.append(f"**Entry Points:** {', '.join(project_structure.entry_points)}\n")
            parts.append("\n")

        parts.extend([
            "## Error to Fix\n",
            f"**Command:** `{command}`\n" if command else "",
            f"**Error Message:**\n```\n{error_message}\n```\n",
        ])

        if stack_trace:
            parts.append(f"**Stack Trace:**\n```\n{stack_trace[:2000]}\n```\n")

        if context_files:
            parts.append("\n## Related Files (READ THESE FIRST)\n")
            # Prioritize build config files
            build_configs = ["pom.xml", "build.gradle", "package.json", "requirements.txt", "go.mod", "Cargo.toml"]
            sorted_files = sorted(
                context_files.items(),
                key=lambda x: (0 if any(cfg in x[0] for cfg in build_configs) else 1, x[0])
            )
            # Include more context files - up to 15
            for path, content in sorted_files[:15]:
                # Truncate based on file type - build configs get more space
                is_build_config = any(cfg in path for cfg in build_configs)
                max_size = 3000 if is_build_config else 2000
                truncated = content[:max_size] if len(content) > max_size else content
                # Identify file type for syntax highlighting
                ext = path.split('.')[-1] if '.' in path else ''
                lang = {'java': 'java', 'py': 'python', 'ts': 'typescript', 'tsx': 'tsx',
                        'js': 'javascript', 'json': 'json', 'xml': 'xml', 'properties': 'properties',
                        'go': 'go', 'rs': 'rust', 'toml': 'toml', 'gradle': 'groovy'}.get(ext, '')
                parts.append(f"### {path}\n```{lang}\n{truncated}\n```\n")

        # Technology-specific fix guidance
        tech_guidance = ""
        if project_structure:
            tech = project_structure.technology
            if tech in [Technology.REACT_VITE, Technology.VUE_VITE]:
                tech_guidance = """
**React/Vite Specific:**
- For import errors, check if the package exists in package.json
- For "Failed to resolve import", the file might be missing - create it
- For TypeScript errors, check tsconfig.json settings
- Working directory is where package.json is located
"""
            elif tech in [Technology.FASTAPI, Technology.FLASK, Technology.DJANGO]:
                tech_guidance = """
**Python Specific:**
- For import errors, check if the package is in requirements.txt
- For module not found, check the file path and __init__.py files
- For FastAPI, check Pydantic model definitions
- Run pip install -r requirements.txt if dependencies are missing
"""
            elif tech in [Technology.SPRING_BOOT_MAVEN, Technology.SPRING_BOOT_GRADLE]:
                tech_guidance = """
**Java/Spring Boot Specific:**
- **CRITICAL**: Spring Boot 3+ uses `jakarta.*` instead of `javax.*` - replace ALL occurrences
  - `javax.validation.*` → `jakarta.validation.*`
  - `javax.persistence.*` → `jakarta.persistence.*`
  - `javax.servlet.*` → `jakarta.servlet.*`
- Use `str_replace_all` to fix all javax imports in a file at once
- For "cannot find symbol" on getters/setters: Add explicit getter/setter methods (NO LOMBOK - generate manually)
- For "package does not exist": Add the correct dependency to pom.xml
- Build command: `mvn clean compile` (not install, just compile to test)
- Check pom.xml for Spring Boot version - if 3.x, ALL javax must be jakarta
"""
            elif tech in [Technology.GO]:
                tech_guidance = """
**Go Specific:**
- For import errors, check go.mod and run go mod tidy
- For undefined errors, check function/type visibility (capitalization)
- For struct errors, check field names and types
"""
            elif tech in [Technology.RUST]:
                tech_guidance = """
**Rust Specific:**
- For borrow checker errors, consider using references or cloning
- For missing trait implementations, add #[derive] or impl blocks
- For type mismatches, check ownership and lifetimes
- Run cargo build after changes
"""

        parts.append(f"""
## Your Task

1. **Analyze** the error message and identify the root cause
2. **Read the build config** (pom.xml, package.json, etc.) to understand dependencies
3. **Read the error file** using `view_file` to see the exact code
4. **Fix the issue**:
   - Use `str_replace` for single fixes
   - Use `str_replace_all` for fixing ALL occurrences (e.g., javax→jakarta)
   - Use `create_file` for missing files
5. **Verify** by running the build command with `bash`
6. **Repeat** if there are more errors
{tech_guidance}
**IMPORTANT:**
- Working directory: {project_structure.working_directory.name if project_structure else 'project root'}
- Read files BEFORE modifying them
- Fix ALL related errors, not just the first one
- Run the build after each major fix to see remaining errors

Start by analyzing the error and reading the relevant build config file.
""")

        return "".join(parts)

    def _extract_text(self, content: List[Any]) -> str:
        """Extract text from response content blocks"""
        text_parts = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    async def _execute_tool(
        self,
        project_id: str,
        user_id: str,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """
        Execute a tool and return the result.

        This connects SDK tools to BharatBuild's sandbox environment.
        """
        logger.info(f"[SDKFixerAgent:{project_id}] Executing tool: {tool_name}")

        try:
            if tool_name == "bash":
                return await self._execute_bash(project_id, user_id, tool_input)
            elif tool_name == "view_file":
                return await self._execute_view_file(project_id, user_id, tool_input)
            elif tool_name == "str_replace":
                return await self._execute_str_replace(project_id, user_id, tool_input)
            elif tool_name == "str_replace_all":
                return await self._execute_str_replace_all(project_id, user_id, tool_input)
            elif tool_name == "create_file":
                return await self._execute_create_file(project_id, user_id, tool_input)
            elif tool_name == "insert_lines":
                return await self._execute_insert_lines(project_id, user_id, tool_input)
            elif tool_name == "glob":
                return await self._execute_glob(project_id, user_id, tool_input)
            elif tool_name == "grep":
                return await self._execute_grep(project_id, user_id, tool_input)
            elif tool_name == "list_directory":
                return await self._execute_list_dir(project_id, user_id, tool_input)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"[SDKFixerAgent:{project_id}] Tool error: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def _execute_bash(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Execute a bash command in the sandbox with smart working directory"""
        command = tool_input.get("command", "")
        timeout = tool_input.get("timeout", 120)

        if not command:
            return "Error: No command provided"

        try:
            # Get sandbox path
            sandbox_path = storage.get_sandbox_path(project_id, user_id)

            # Use smart working directory from cached project structure
            cache_key = f"{project_id}:{user_id}"
            working_dir = sandbox_path

            if cache_key in self._project_cache:
                project_structure = self._project_cache[cache_key]
                # Use the smart analyzer's detected working directory
                working_dir = str(project_structure.working_directory)
                logger.info(f"[SDKFixerAgent:{project_id}] Using smart working dir: {working_dir}")
            else:
                # Try to get working directory from smart analyzer
                try:
                    project_structure = await smart_analyzer.analyze_project(
                        project_id=project_id,
                        user_id=user_id
                    )
                    working_dir = str(project_structure.working_directory)
                    self._project_cache[cache_key] = project_structure
                    logger.info(f"[SDKFixerAgent:{project_id}] Analyzed and using working dir: {working_dir}")
                except Exception as e:
                    logger.warning(f"[SDKFixerAgent:{project_id}] Could not analyze, using sandbox root: {e}")

            # Execute command in the correct working directory (non-blocking)
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return f"Error: Command timed out after {timeout} seconds"

            output = ""
            if stdout:
                output += f"STDOUT:\n{stdout.decode('utf-8', errors='replace')}\n"
            if stderr:
                output += f"STDERR:\n{stderr.decode('utf-8', errors='replace')}\n"
            output += f"Exit Code: {process.returncode}"

            return output if output else "Command completed with no output"

        except asyncio.TimeoutError:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    async def _execute_view_file(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Read a file from the sandbox"""
        path = tool_input.get("path", "")
        start_line = tool_input.get("start_line")
        end_line = tool_input.get("end_line")

        if not path:
            return "Error: No path provided"

        try:
            content = await storage.read_from_sandbox(project_id, path, user_id)

            if content is None:
                return f"Error: File not found: {path}"

            # Apply line range if specified
            if start_line or end_line:
                lines = content.split("\n")
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                lines = lines[start:end]
                # Add line numbers
                numbered = [f"{i + start + 1}: {line}" for i, line in enumerate(lines)]
                return "\n".join(numbered)

            # Add line numbers
            lines = content.split("\n")
            numbered = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
            return "\n".join(numbered)

        except Exception as e:
            return f"Error reading file: {str(e)}"

    async def _execute_str_replace(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Replace string in a file"""
        path = tool_input.get("path", "")
        old_str = tool_input.get("old_str", "")
        new_str = tool_input.get("new_str", "")

        if not path or not old_str:
            return "Error: path and old_str are required"

        try:
            # Read current content
            content = await storage.read_from_sandbox(project_id, path, user_id)

            if content is None:
                return f"Error: File not found: {path}"

            # Check if old_str exists
            if old_str not in content:
                return f"Error: Could not find the exact string to replace in {path}. Make sure old_str matches exactly (including whitespace)."

            # Replace (single occurrence)
            new_content = content.replace(old_str, new_str, 1)

            # Write back
            await storage.write_to_sandbox(project_id, path, new_content, user_id)

            return f"Successfully replaced text in {path}"

        except Exception as e:
            return f"Error replacing text: {str(e)}"

    async def _execute_str_replace_all(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Replace ALL occurrences of a string in a file"""
        path = tool_input.get("path", "")
        old_str = tool_input.get("old_str", "")
        new_str = tool_input.get("new_str", "")

        if not path or not old_str:
            return "Error: path and old_str are required"

        try:
            # Read current content
            content = await storage.read_from_sandbox(project_id, path, user_id)

            if content is None:
                return f"Error: File not found: {path}"

            # Check if old_str exists
            if old_str not in content:
                return f"Error: Could not find the string '{old_str}' in {path}"

            # Count occurrences
            count = content.count(old_str)

            # Replace ALL occurrences
            new_content = content.replace(old_str, new_str)

            # Write back
            await storage.write_to_sandbox(project_id, path, new_content, user_id)

            return f"Successfully replaced {count} occurrence(s) of '{old_str}' with '{new_str}' in {path}"

        except Exception as e:
            return f"Error replacing text: {str(e)}"

    async def _execute_create_file(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Create a new file"""
        path = tool_input.get("path", "")
        content = tool_input.get("content", "")

        if not path:
            return "Error: path is required"

        try:
            await storage.write_to_sandbox(project_id, path, content, user_id)
            return f"Successfully created {path}"
        except Exception as e:
            return f"Error creating file: {str(e)}"

    async def _execute_insert_lines(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Insert lines at a position"""
        path = tool_input.get("path", "")
        line = tool_input.get("line", 0)
        content = tool_input.get("content", "")

        if not path:
            return "Error: path is required"

        try:
            # Read current content
            current = await storage.read_from_sandbox(project_id, path, user_id)

            if current is None:
                return f"Error: File not found: {path}"

            # Split and insert
            lines = current.split("\n")
            insert_lines = content.split("\n")
            lines[line:line] = insert_lines

            # Write back
            new_content = "\n".join(lines)
            await storage.write_to_sandbox(project_id, path, new_content, user_id)

            return f"Successfully inserted {len(insert_lines)} lines at line {line} in {path}"

        except Exception as e:
            return f"Error inserting lines: {str(e)}"

    async def _execute_glob(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Find files matching a pattern"""
        pattern = tool_input.get("pattern", "")

        if not pattern:
            return "Error: pattern is required"

        try:
            import glob as glob_module

            sandbox_path = storage.get_sandbox_path(project_id, user_id)
            full_pattern = os.path.join(sandbox_path, pattern)

            matches = glob_module.glob(full_pattern, recursive=True)

            # Convert to relative paths
            relative = [os.path.relpath(m, sandbox_path) for m in matches]

            if not relative:
                return f"No files found matching: {pattern}"

            return "Matching files:\n" + "\n".join(relative[:50])

        except Exception as e:
            return f"Error searching files: {str(e)}"

    async def _execute_grep(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Search for pattern in files"""
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", ".")
        include = tool_input.get("include", "")

        if not pattern:
            return "Error: pattern is required"

        try:
            sandbox_path = storage.get_sandbox_path(project_id, user_id)
            search_path = os.path.join(sandbox_path, path)

            # Build grep command
            cmd = f'grep -rn "{pattern}" "{search_path}"'
            if include:
                cmd = f'grep -rn --include="{include}" "{pattern}" "{search_path}"'

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return f"Error: Grep command timed out after 30 seconds"

            output = stdout.decode('utf-8', errors='replace') or stderr.decode('utf-8', errors='replace')
            if not output:
                return f"No matches found for: {pattern}"

            # Limit output
            lines = output.split("\n")[:30]
            return "\n".join(lines)

        except asyncio.TimeoutError:
            return f"Error: Grep command timed out after 30 seconds"
        except Exception as e:
            return f"Error searching: {str(e)}"

    async def _execute_list_dir(
        self,
        project_id: str,
        user_id: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """List directory contents"""
        path = tool_input.get("path", ".")
        recursive = tool_input.get("recursive", False)

        try:
            sandbox_path = storage.get_sandbox_path(project_id, user_id)
            full_path = os.path.join(sandbox_path, path)

            if not os.path.exists(full_path):
                return f"Error: Directory not found: {path}"

            if recursive:
                items = []
                for root, dirs, files in os.walk(full_path):
                    rel_root = os.path.relpath(root, sandbox_path)
                    for f in files:
                        items.append(os.path.join(rel_root, f))
                return "\n".join(items[:100])
            else:
                items = os.listdir(full_path)
                result = []
                for item in sorted(items):
                    item_path = os.path.join(full_path, item)
                    prefix = "[DIR]" if os.path.isdir(item_path) else "[FILE]"
                    result.append(f"{prefix} {item}")
                return "\n".join(result)

        except Exception as e:
            return f"Error listing directory: {str(e)}"


# Singleton instance
sdk_fixer_agent = SDKFixerAgent()
