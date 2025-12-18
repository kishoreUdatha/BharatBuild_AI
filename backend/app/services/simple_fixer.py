"""
Simple Fixer - Bolt.new Style (UNIVERSAL) - COST OPTIMIZED

This is a SIMPLE auto-fixer that follows Bolt.new's approach:
1. Process exits with non-zero code OR output contains clear error indicators
2. Send FULL output + relevant files to AI
3. AI decides what to fix
4. Apply fixes
5. Retry the command

COST OPTIMIZATIONS (Bolt.new style):
1. USER CONFIRMATION - Errors are queued, user must approve before fix
2. HAIKU FOR SIMPLE ERRORS - Use cheap model ($0.25/$1.25) for simple errors
3. SMALLER CONTEXT - Only send files mentioned in error + 3-5 key configs
4. LOWER MAX ITERATIONS - 5 instead of 20 (if 5 tries don't fix it, ask user)

HANDLES ALL ERROR SOURCES:
- Terminal stdout/stderr (build, runtime, dependencies)
- Browser console (TypeError, runtime JS)
- Build tools (Webpack, Vite, Next.js)
- Framework errors (React warnings, rendering errors)
- Backend API errors (5xx, 404, CORS)
- Docker runtime (port issues, container crashes)
- Lint/Type-check tools (tsc, eslint)

NO pattern matching. NO multiple systems. Just simple AI-powered fixing.
"""

import asyncio
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from anthropic import AsyncAnthropic

from app.core.logging_config import logger
from app.core.config import settings


# Rate limiting to prevent infinite loops
_fix_timestamps: Dict[str, List[float]] = {}
_FIX_COOLDOWN_SECONDS = 15  # Minimum seconds between fix attempts
_MAX_FIXES_PER_WINDOW = 10  # Max fix attempts per window
_FIX_WINDOW_SECONDS = 300  # 5 minute window

# COST OPTIMIZATION: Pending fixes queue (for user confirmation)
_pending_fixes: Dict[str, 'PendingFix'] = {}


class ErrorComplexity(str, Enum):
    """Error complexity for model selection"""
    SIMPLE = "simple"      # Missing import, typo, syntax error -> Haiku
    MODERATE = "moderate"  # Multiple files, config issues -> Sonnet
    COMPLEX = "complex"    # Architecture, runtime logic -> Sonnet


@dataclass
class PendingFix:
    """Pending fix awaiting user confirmation"""
    project_id: str
    errors: List[Dict[str, Any]]
    context: str
    command: Optional[str]
    file_tree: Optional[List[str]]
    recently_modified: Optional[List[Dict]]
    complexity: ErrorComplexity
    estimated_cost: float  # Estimated API cost in dollars
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        """Convert to dict for API response"""
        return {
            "project_id": self.project_id,
            "error_count": len(self.errors),
            "error_summary": self.errors[0].get("message", "")[:200] if self.errors else "",
            "complexity": self.complexity.value,
            "estimated_cost": f"${self.estimated_cost:.3f}",
            "command": self.command,
            "created_at": self.created_at
        }


@dataclass
class SimpleFixResult:
    """Result of a fix attempt"""
    success: bool
    files_modified: List[str]
    message: str
    patches_applied: int = 0
    pending_confirmation: bool = False  # NEW: True if fix is queued for user approval
    pending_fix_id: Optional[str] = None  # NEW: ID to approve/reject fix


# Simple system prompt - UNIVERSAL for ALL technologies
SIMPLE_FIXER_PROMPT = """You are an expert polyglot developer fixing build/runtime errors across ALL programming languages and frameworks.

You will receive:
1. Error source (terminal, browser, build, compiler, runtime, docker, etc.)
2. Error message and context
3. Relevant project files (sometimes only ~50 lines around the error line for efficiency)

Your job:
1. Analyze the error in context of the specific technology
2. Determine the root cause
3. Fix it by creating or modifying files

SUPPORTED TECHNOLOGIES & COMMON ERRORS:

PYTHON:
- SyntaxError, IndentationError, NameError, ImportError, ModuleNotFoundError
- TypeError, AttributeError, KeyError, ValueError
- Django/Flask/FastAPI/Streamlit specific errors

JAVASCRIPT / TYPESCRIPT:
- SyntaxError, TypeError, ReferenceError
- ESLint errors, TSC type errors (TS2304, TS2322, etc.)
- React: Component errors, hook rules, render failures
- Vite/Webpack: Build failures, HMR errors, plugin issues
- Node.js: Module not found, require/import errors

JAVA:
- NullPointerException, ClassNotFoundException, NoSuchMethodError
- Compilation errors: "cannot find symbol", "incompatible types"
- Maven/Gradle build errors
- Spring Boot configuration issues

GO:
- "undefined:", "declared but not used", "imported but not used"
- "missing return", "cannot use", type conversion errors
- Go module issues (go.mod, go.sum)

RUST:
- Borrow checker: "borrowed value", "use of moved value"
- "mismatched types", "cannot find", lifetime errors
- Cargo build errors

C / C++:
- Segmentation fault, undefined reference, undeclared identifier
- Compilation errors, linker errors
- CMake/Make build failures

IMPORTANT RULES:
- If the output shows SUCCESS (build success, server started, etc.) - respond with "NO_FIX_NEEDED"
- Only fix ACTUAL errors, not warnings or info messages
- Be precise - fix the exact issue, don't over-engineer
- Create missing files if needed (config files, missing modules)
- Fix import/include errors, syntax errors, type errors
- For CORS errors, update backend CORS configuration
- For missing dependencies, suggest installing OR fix the import path

CRITICAL - PARTIAL FILE HANDLING:
- When you see "[PARTIAL FILE - SHOWING LINES X-Y of Z total lines]", you are seeing ONLY A PORTION of the file
- For partial files, you MUST use str_replace tool to fix the specific problematic lines
- NEVER use create_file on partial files - this would delete the rest of the file!
- The str_replace tool takes "old_str" (exact text to find) and "new_str" (replacement text)
- Copy the exact problematic lines as old_str, then provide the fixed version as new_str

When you identify a fix, use the tools to apply it."""


class SimpleFixer:
    """
    Bolt.new-style simple fixer - COST OPTIMIZED.

    Key principles:
    1. Let AI decide what's an error (no hardcoded patterns)
    2. Always provide full context
    3. Single, simple flow

    COST OPTIMIZATIONS (Bolt.new style):
    1. User confirmation before fixing (prevents unnecessary API calls)
    2. Use Haiku for simple errors (12x cheaper: $0.25/$1.25 vs $3/$15)
    3. Smaller context window (only error-mentioned files + key configs)
    4. Lower max iterations (5 instead of 20)
    """

    # Model costs per 1M tokens (for estimation)
    MODEL_COSTS = {
        "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},  # Haiku - CHEAP
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},    # Sonnet - EXPENSIVE
    }

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model_haiku = "claude-3-5-haiku-20241022"   # For simple errors (12x cheaper)
        self.model_sonnet = "claude-sonnet-4-20250514"  # For complex errors
        # Auto-fix mode: True = immediate fix, False = queue for confirmation (Bolt.new style)
        self.auto_fix_enabled = True  # Can be toggled via API
        # Token tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._call_count = 0
        self._last_model_used = "haiku"

    def reset_token_tracking(self):
        """Reset token tracking counters"""
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._call_count = 0
        self._last_model_used = "haiku"

    def get_token_usage(self) -> Dict[str, Any]:
        """Get accumulated token usage"""
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "call_count": self._call_count,
            "model": self._last_model_used
        }

    def _track_tokens(self, response, model: str):
        """Track tokens from API response"""
        if hasattr(response, 'usage'):
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._call_count += 1
            self._last_model_used = "haiku" if "haiku" in model.lower() else "sonnet"
            logger.debug(f"[SimpleFixer] Token usage: +{response.usage.input_tokens} in, +{response.usage.output_tokens} out (call #{self._call_count})")

    def _classify_error_complexity(self, errors: List[Dict[str, Any]], context: str) -> ErrorComplexity:
        """
        COST OPTIMIZATION #2: Classify error complexity to choose appropriate model.

        SIMPLE (use Haiku - 12x cheaper):
        - Syntax errors (SyntaxError, unexpected token, etc.)
        - Missing import/module
        - Single file with clear line number
        - Typo in variable/function name

        MODERATE/COMPLEX (use Sonnet):
        - Multiple files involved
        - Config file issues
        - Architecture/logic errors
        - Runtime exceptions without clear source
        """
        if not errors:
            return ErrorComplexity.SIMPLE

        first_error = errors[0]
        error_msg = first_error.get("message", "").lower()
        has_file = bool(first_error.get("file"))
        has_line = bool(first_error.get("line"))

        # Also check the raw context for error patterns (more reliable)
        context_lower = context.lower() if context else ""
        combined_text = f"{error_msg} {context_lower}"

        # Count files mentioned in errors
        files_mentioned = set()
        for err in errors:
            if err.get("file"):
                files_mentioned.add(err.get("file"))

        # SIMPLE patterns (use Haiku - 12x cheaper!)
        # These are errors that have clear, localized fixes - UNIVERSAL for ALL technologies
        simple_patterns = [
            # === PYTHON ===
            "syntaxerror", "syntax error", "indentationerror", "indentation error",
            "modulenotfounderror", "importerror", "nameerror", "attributeerror",
            "typeerror", "keyerror", "indexerror", "valueerror", "zerodivisionerror",
            "filenotfounderror", "permissionerror", "unboundlocalerror",

            # === JAVASCRIPT / TYPESCRIPT ===
            "unexpected token", "unexpected eof", "unexpected end of input",
            "missing semicolon", "missing bracket", "missing parenthesis",
            "cannot find module", "module not found", "is not defined",
            "is not a function", "cannot read property", "cannot read properties",
            "undefined is not", "null is not", "referenceerror", "typeerror",
            "cannot assign to", "property does not exist", "has no exported member",
            "ts2304", "ts2322", "ts2339", "ts2345",  # Common TypeScript error codes
            "eslint", "parsing error",

            # === JAVA ===
            "nullpointerexception", "classnotfoundexception", "nosuchmethoderror",
            "arrayindexoutofboundsexception", "numberformatexception",
            "illegalargumentexception", "illegalstateexception", "ioexception",
            "cannot find symbol", "incompatible types", "method does not override",
            "unreported exception", "variable might not have been initialized",
            "class, interface, or enum expected", "reached end of file while parsing",

            # === GO ===
            "undefined:", "cannot use", "missing return", "not enough arguments",
            "too many arguments", "declared but not used", "imported but not used",
            "no new variables", "cannot convert", "invalid operation",
            "missing function body", "expected declaration",

            # === RUST ===
            "cannot find", "expected", "mismatched types", "borrowed value",
            "use of moved value", "lifetime", "trait bound", "no method named",
            "unresolved import", "cannot borrow", "value used after move",
            "missing lifetime", "type annotations needed",

            # === C / C++ ===
            "undeclared identifier", "undefined reference", "no matching function",
            "invalid operands", "expected expression", "expected ';'",
            "implicit declaration", "incompatible pointer", "segmentation fault",
            "use of undeclared", "no member named",

            # === GENERAL / CROSS-LANGUAGE ===
            "unterminated string", "missing colon", "unexpected character",
            "enoent", "no such file", "file not found", "permission denied",
            "connection refused", "timeout", "out of memory",
            "stack overflow", "recursion", "circular dependency",
        ]

        # Check if error matches simple pattern in either error message OR context
        for pattern in simple_patterns:
            if pattern in combined_text:
                # For syntax errors, we can fix with just the relevant lines
                if len(files_mentioned) <= 2:
                    logger.info(f"[SimpleFixer] Classified as SIMPLE (pattern: '{pattern}') - using Haiku (12x cheaper)")
                    return ErrorComplexity.SIMPLE

        # Multiple errors or files = more complex
        if len(errors) > 3 or len(files_mentioned) > 2:
            logger.info(f"[SimpleFixer] Classified as COMPLEX (errors={len(errors)}, files={len(files_mentioned)})")
            return ErrorComplexity.COMPLEX

        # Config file issues = moderate (ALL technologies)
        config_keywords = [
            # General
            "config", ".env", "dockerfile", "docker-compose",
            # JavaScript/TypeScript
            "tsconfig", "package.json", "webpack", "vite.config", "eslint", "babel",
            # Python
            "requirements", "pyproject.toml", "setup.py", "setup.cfg", "poetry.lock",
            # Java
            "pom.xml", "build.gradle", "settings.gradle", "application.properties", "application.yml",
            # Go
            "go.mod", "go.sum",
            # Rust
            "cargo.toml", "cargo.lock",
            # C/C++
            "cmake", "makefile", "meson.build",
            # .NET
            "csproj", "appsettings.json", "nuget",
        ]
        if any(kw in error_msg for kw in config_keywords):
            logger.info(f"[SimpleFixer] Classified as MODERATE (config-related)")
            return ErrorComplexity.MODERATE

        # Single file with line number = likely simple
        if has_file and has_line and len(files_mentioned) == 1:
            logger.info(f"[SimpleFixer] Classified as SIMPLE (single file with line number) - using Haiku")
            return ErrorComplexity.SIMPLE

        # Default to moderate
        logger.info(f"[SimpleFixer] Classified as MODERATE (default)")
        return ErrorComplexity.MODERATE

    def _estimate_cost(self, complexity: ErrorComplexity, context_size: int) -> float:
        """
        Estimate API cost for a fix attempt (for user confirmation UI).

        Assumptions:
        - Input: context_size chars ~ context_size/4 tokens
        - Output: ~2000 tokens per iteration
        - Simple: 2 iterations avg, Moderate: 3, Complex: 5
        """
        model = self.model_haiku if complexity == ErrorComplexity.SIMPLE else self.model_sonnet
        costs = self.MODEL_COSTS[model]

        input_tokens = context_size / 4  # rough estimate
        iterations = 2 if complexity == ErrorComplexity.SIMPLE else (3 if complexity == ErrorComplexity.MODERATE else 5)
        output_tokens = 2000 * iterations

        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        return round(input_cost + output_cost, 4)

    def _select_model(self, complexity: ErrorComplexity) -> str:
        """COST OPTIMIZATION #2: Select model based on error complexity"""
        if complexity == ErrorComplexity.SIMPLE:
            logger.info(f"[SimpleFixer] Using Haiku model (12x cheaper)")
            return self.model_haiku
        logger.info(f"[SimpleFixer] Using Sonnet model (complex error)")
        return self.model_sonnet

    # ==================== COST OPTIMIZATION #1: User Confirmation ====================
    def queue_fix(
        self,
        project_id: str,
        errors: List[Dict[str, Any]],
        context: str,
        command: Optional[str],
        file_tree: Optional[List[str]],
        recently_modified: Optional[List[Dict]]
    ) -> Dict:
        """
        Queue a fix for user confirmation instead of executing immediately.
        Returns fix details including estimated cost for UI to display.
        """
        complexity = self._classify_error_complexity(errors, context)
        estimated_cost = self._estimate_cost(complexity, len(context))

        pending_fix = PendingFix(
            project_id=project_id,
            errors=errors,
            context=context,
            command=command,
            file_tree=file_tree,
            recently_modified=recently_modified,
            complexity=complexity,
            estimated_cost=estimated_cost
        )

        _pending_fixes[project_id] = pending_fix
        logger.info(f"[SimpleFixer:{project_id}] Queued fix for confirmation (est. ${estimated_cost:.3f})")

        return {
            "status": "pending_confirmation",
            "fix_id": project_id,
            **pending_fix.to_dict()
        }

    def get_pending_fix(self, project_id: str) -> Optional[Dict]:
        """Get pending fix details for a project"""
        if project_id in _pending_fixes:
            return _pending_fixes[project_id].to_dict()
        return None

    def cancel_pending_fix(self, project_id: str) -> bool:
        """Cancel a pending fix"""
        if project_id in _pending_fixes:
            del _pending_fixes[project_id]
            logger.info(f"[SimpleFixer:{project_id}] Pending fix cancelled by user")
            return True
        return False

    async def approve_and_execute_fix(self, project_id: str, project_path: Path) -> SimpleFixResult:
        """Execute a previously queued fix after user approval"""
        if project_id not in _pending_fixes:
            return SimpleFixResult(
                success=False,
                files_modified=[],
                message="No pending fix found for this project",
                patches_applied=0
            )

        pending = _pending_fixes.pop(project_id)
        logger.info(f"[SimpleFixer:{project_id}] User approved fix, executing...")

        # Execute the fix with the stored context
        return await self._execute_fix_internal(
            project_id=project_id,
            project_path=project_path,
            errors=pending.errors,
            context=pending.context,
            command=pending.command,
            file_tree=pending.file_tree,
            recently_modified=pending.recently_modified,
            complexity=pending.complexity
        )

    def _can_attempt_fix(self, project_id: str) -> tuple:
        """Rate limit check"""
        now = time.time()
        if project_id not in _fix_timestamps:
            _fix_timestamps[project_id] = []

        timestamps = _fix_timestamps[project_id]
        timestamps[:] = [t for t in timestamps if now - t < _FIX_WINDOW_SECONDS]

        if timestamps and now - timestamps[-1] < _FIX_COOLDOWN_SECONDS:
            remaining = _FIX_COOLDOWN_SECONDS - (now - timestamps[-1])
            return False, f"Cooldown active ({remaining:.1f}s remaining)"

        if len(timestamps) >= _MAX_FIXES_PER_WINDOW:
            return False, f"Max attempts ({_MAX_FIXES_PER_WINDOW}) reached"

        return True, "OK"

    def _record_fix_attempt(self, project_id: str):
        """Record a fix attempt"""
        if project_id not in _fix_timestamps:
            _fix_timestamps[project_id] = []
        _fix_timestamps[project_id].append(time.time())

    async def fix_from_frontend(
        self,
        project_id: str,
        project_path: Path,
        errors: List[Dict[str, Any]],
        context: str = "",
        command: Optional[str] = None,
        file_tree: Optional[List[str]] = None,
        recently_modified: Optional[List[Dict]] = None
    ) -> SimpleFixResult:
        """
        Fix errors reported from frontend - ALL error sources.
        COST OPTIMIZED with user confirmation option.

        This is the UNIFIED entry point for:
        - Browser errors (TypeError, ReferenceError)
        - Build errors (Vite, Webpack)
        - React errors (component/hook errors)
        - HMR errors
        - Network errors (CORS)
        - Docker errors
        """
        # Rate limit check
        can_fix, reason = self._can_attempt_fix(project_id)
        if not can_fix:
            logger.warning(f"[SimpleFixer:{project_id}] Rate limited: {reason}")
            return SimpleFixResult(
                success=False,
                files_modified=[],
                message=f"Rate limited: {reason}",
                patches_applied=0
            )

        # COST OPTIMIZATION #1: Queue for user confirmation if auto_fix_enabled is False
        if not self.auto_fix_enabled:
            queue_result = self.queue_fix(
                project_id=project_id,
                errors=errors,
                context=context,
                command=command,
                file_tree=file_tree,
                recently_modified=recently_modified
            )
            return SimpleFixResult(
                success=False,
                files_modified=[],
                message=f"Fix queued for confirmation (est. {queue_result['estimated_cost']})",
                patches_applied=0,
                pending_confirmation=True,
                pending_fix_id=project_id
            )

        # COST OPTIMIZATION #2: Classify error complexity for model selection
        complexity = self._classify_error_complexity(errors, context)

        self._record_fix_attempt(project_id)

        return await self._execute_fix_internal(
            project_id=project_id,
            project_path=project_path,
            errors=errors,
            context=context,
            command=command,
            file_tree=file_tree,
            recently_modified=recently_modified,
            complexity=complexity
        )

    async def _execute_fix_internal(
        self,
        project_id: str,
        project_path: Path,
        errors: List[Dict[str, Any]],
        context: str,
        command: Optional[str],
        file_tree: Optional[List[str]],
        recently_modified: Optional[List[Dict]],
        complexity: ErrorComplexity
    ) -> SimpleFixResult:
        """Internal method to execute fix with cost optimizations"""
        try:
            # =================================================================
            # STEP 0: Try deterministic CSS fix FIRST (fast, free, no API call)
            # =================================================================
            error_text = context or ""
            for err in errors:
                error_text += " " + err.get("message", "")
            deterministic_result = await self._try_deterministic_css_fix(project_path, error_text)
            if deterministic_result:
                logger.info(f"[SimpleFixer:{project_id}] Deterministic CSS fix applied - skipping AI")
                return deterministic_result

            # COST OPTIMIZATION #2: Select model based on complexity
            model = self._select_model(complexity)

            # COST OPTIMIZATION #3: Gather SMALLER context (only error-mentioned files + key configs)
            context_files = await self._gather_context_optimized(project_path, context, errors)

            # Build error summary
            error_summary = self._format_errors(errors)

            # COST OPTIMIZATION #3: Smaller context window
            context_limit = 8000 if complexity == ErrorComplexity.SIMPLE else 12000
            user_message = f"""Error Source: {errors[0].get('source', 'unknown') if errors else 'unknown'}
Command: {command or 'N/A'}

Errors:
{error_summary}

Full Context:
```
{context[-context_limit:] if context else '(no context)'}
```

Project Files:
{self._format_files(context_files)}

Recently Modified:
{self._format_recently_modified(recently_modified)}

Please analyze and fix these errors. If the output shows success or warnings only, respond with "NO_FIX_NEEDED".
"""

            logger.info(f"[SimpleFixer:{project_id}] Processing {len(errors)} errors (model={model.split('/')[-1]}, complexity={complexity.value})")

            # Call AI with selected model
            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=SIMPLE_FIXER_PROMPT,
                tools=self._get_tools(),
                messages=[{"role": "user", "content": user_message}]
            )
            self._track_tokens(response, model)

            # Check if no fix needed
            if response.stop_reason == "end_turn":
                text = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        text += block.text
                if "NO_FIX_NEEDED" in text:
                    logger.info(f"[SimpleFixer:{project_id}] No fix needed")
                    return SimpleFixResult(
                        success=True,
                        files_modified=[],
                        message="No fix needed",
                        patches_applied=0
                    )

            # Process tool calls
            files_modified = []
            iterations = 0
            # COST OPTIMIZATION #4: Lower max iterations (3 instead of 5)
            # If 3 tries don't fix it, ask user or try different approach
            max_iterations = 3

            while response.stop_reason == "tool_use" and iterations < max_iterations:
                iterations += 1
                logger.info(f"[SimpleFixer:{project_id}] Iteration {iterations}/{max_iterations}")

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(
                            project_path,
                            block.name,
                            block.input
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                        if block.name in ["create_file", "str_replace"]:
                            path = block.input.get("path", "")
                            if path and path not in files_modified:
                                files_modified.append(path)

                # Continue conversation with selected model
                response = await self.client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=SIMPLE_FIXER_PROMPT,
                    tools=self._get_tools(),
                    messages=[
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": response.content},
                        {"role": "user", "content": tool_results}
                    ]
                )
                self._track_tokens(response, model)

            logger.info(f"[SimpleFixer:{project_id}] Fixed {len(files_modified)} files in {iterations} iterations")
            return SimpleFixResult(
                success=len(files_modified) > 0,
                files_modified=files_modified,
                message=f"Fixed {len(files_modified)} files (model={model.split('-')[1]}, iterations={iterations})",
                patches_applied=len(files_modified)
            )

        except Exception as e:
            logger.error(f"[SimpleFixer:{project_id}] Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return SimpleFixResult(
                success=False,
                files_modified=[],
                message=str(e),
                patches_applied=0
            )

    def _extract_relevant_lines(self, content: str, error_line: int, context_lines: int = 25) -> str:
        """
        Extract only relevant lines around the error.
        Returns ~50 lines (25 before + error line + 25 after) with line numbers.

        This reduces token usage by ~90% for large files!
        """
        lines = content.split('\n')
        total_lines = len(lines)

        # Calculate range
        start = max(0, error_line - context_lines - 1)  # -1 because line numbers are 1-indexed
        end = min(total_lines, error_line + context_lines)

        # Build output with line numbers
        result_lines = []
        for i in range(start, end):
            line_num = i + 1
            marker = " >>> " if line_num == error_line else "     "
            result_lines.append(f"{line_num:4d}{marker}| {lines[i]}")

        return '\n'.join(result_lines)

    async def _gather_context_optimized(self, project_path: Path, output: str, errors: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        COST OPTIMIZATION #3: Gather SMALLER context.

        TOKEN OPTIMIZATION:
        - For files with errors: Send only ~50 lines around error (not full file!)
        - For config files: Send full content (usually small)
        - Result: ~90% token reduction for large files
        """
        files = {}

        # KEY config files only (small files, send full content)
        key_configs = [
            "package.json",
            "tsconfig.json",
            "vite.config.ts",
            "vite.config.js",
            "pom.xml",
            "requirements.txt",
            "pyproject.toml",
        ]

        for rel_path in key_configs:
            full_path = project_path / rel_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8')
                    if len(content) < 5000:  # Config files should be small
                        files[rel_path] = content
                except:
                    pass

        # Extract files mentioned in errors - ONLY RELEVANT LINES!
        for err in errors[:5]:
            file_path = err.get("file")
            error_line = err.get("line")

            if file_path:
                full_path = project_path / file_path
                if full_path.exists():
                    try:
                        content = full_path.read_text(encoding='utf-8')

                        # If we have a line number, extract only relevant lines
                        if error_line and isinstance(error_line, int) and error_line > 0:
                            # Send only ~50 lines around the error (huge token savings!)
                            relevant_content = self._extract_relevant_lines(content, error_line, context_lines=25)
                            files[file_path] = f"[Lines {max(1, error_line-25)}-{error_line+25} around error at line {error_line}]\n{relevant_content}"
                            logger.info(f"[SimpleFixer] Extracted ~50 lines around line {error_line} from {file_path} (was {len(content)} chars)")
                        elif len(content) < 5000:
                            # Small file - send full content
                            files[file_path] = content
                        else:
                            # Large file without line number - send first/last portions
                            files[file_path] = f"[File truncated - {len(content)} chars]\n{content[:2000]}\n...\n{content[-2000:]}"
                            logger.info(f"[SimpleFixer] Truncated large file {file_path} (was {len(content)} chars)")
                    except:
                        pass

        # Parse line numbers from error output (e.g., "line 687", ":687:", "at line 687")
        line_pattern = r'(?:line\s+(\d+)|:(\d+):|at\s+line\s+(\d+))'
        line_matches = re.findall(line_pattern, output, re.IGNORECASE)
        error_lines = [int(m[0] or m[1] or m[2]) for m in line_matches if any(m)]

        # Extract files from traceback paths (e.g., "/path/to/app.py", "File "app.py"")
        # Pattern 1: Full paths in tracebacks
        full_path_pattern = r'File\s+"([^"]+)"'
        full_paths = re.findall(full_path_pattern, output)

        # Pattern 2: Simple filenames with extensions (ALL technologies)
        simple_pattern = r'\b([\w.-]+\.(?:tsx?|jsx?|py|java|go|rs|vue|svelte|c|cpp|cc|cxx|h|hpp|cs|rb|php|kt|scala|swift|m|mm|pl|pm|sh|bash|yaml|yml|json|xml|toml|sql|lua|r|R|jl|ex|exs|erl|hrl|hs|elm|clj|cljs|cljc|coffee|dart))\b'
        simple_files = re.findall(simple_pattern, output)

        # Combine and deduplicate
        mentioned = []
        for fp in full_paths:
            # Extract just the filename from full path
            fname = Path(fp).name
            if fname not in mentioned:
                mentioned.append(fname)
        for sf in simple_files:
            if sf not in mentioned:
                mentioned.append(sf)

        # If no files found, check for common entry files (ALL technologies)
        # Trigger if we have error_lines OR if we detected any error keywords in output
        has_error_keywords = any(kw in output.lower() for kw in ['syntaxerror', 'error:', 'exception', 'traceback', 'failed'])
        if not mentioned and (error_lines or has_error_keywords):
            common_entry_files = [
                # Python
                "app.py", "main.py", "run.py", "server.py", "index.py", "manage.py", "wsgi.py",
                # JavaScript/TypeScript
                "index.js", "app.js", "main.js", "server.js",
                "index.ts", "app.ts", "main.ts", "server.ts",
                "index.tsx", "App.tsx", "main.tsx",
                "index.mjs", "index.cjs",
                # Java
                "Main.java", "App.java", "Application.java",
                "src/main/java/Main.java", "src/main/java/App.java",
                "src/main/java/Application.java",
                # Go
                "main.go", "app.go", "server.go",
                "cmd/main.go", "cmd/server.go",
                # Rust
                "src/main.rs", "main.rs", "src/lib.rs",
                # Vue/Svelte
                "App.vue", "main.vue", "App.svelte", "main.svelte",
                "src/App.vue", "src/main.vue", "src/App.svelte",
                # C/C++
                "main.c", "main.cpp", "main.cc", "app.c", "app.cpp",
                "src/main.c", "src/main.cpp",
                # C# / .NET
                "Program.cs", "App.cs", "Main.cs",
                # Ruby
                "app.rb", "main.rb", "server.rb", "config.ru",
                # PHP
                "index.php", "app.php", "main.php",
                # Kotlin
                "Main.kt", "App.kt", "Application.kt",
                # Swift
                "main.swift", "App.swift",
                # Dart/Flutter
                "main.dart", "lib/main.dart",
            ]
            for cf in common_entry_files:
                cf_path = project_path / cf
                if cf_path.exists():
                    mentioned.append(cf)
                    logger.info(f"[SimpleFixer] No files in output, found entry file: {cf}")
                    break

            # Also check src/ directory for any source files (ALL technologies)
            if not mentioned:
                src_path = project_path / "src"
                if src_path.exists():
                    for ext in [
                        "*.py", "*.ts", "*.tsx", "*.js", "*.jsx",  # Python, JS/TS
                        "*.java", "*.kt", "*.scala",               # JVM languages
                        "*.go",                                     # Go
                        "*.rs",                                     # Rust
                        "*.c", "*.cpp", "*.cc", "*.h", "*.hpp",    # C/C++
                        "*.cs",                                     # C#
                        "*.rb",                                     # Ruby
                        "*.php",                                    # PHP
                        "*.swift",                                  # Swift
                        "*.dart",                                   # Dart
                    ]:
                        for src_file in src_path.glob(ext):
                            mentioned.append(str(src_file.relative_to(project_path)))
                            logger.info(f"[SimpleFixer] Found source file in src/: {src_file.name}")
                            break
                        if mentioned:
                            break

        logger.info(f"[SimpleFixer] Files to check: {mentioned[:5]}, error_lines: {error_lines[:3]}")

        for path_fragment in mentioned[:3]:  # Limit to 3 files
            if path_fragment in files:
                continue  # Already added
            # Try exact match first, then glob
            exact_path = project_path / path_fragment
            if exact_path.exists() and exact_path.is_file():
                try:
                    content = exact_path.read_text(encoding='utf-8')
                    total_lines = len(content.split('\n'))

                    # Use first error line found
                    if error_lines and len(content) > 3000:
                        relevant_content = self._extract_relevant_lines(content, error_lines[0], context_lines=25)
                        files[path_fragment] = f"""[PARTIAL FILE - SHOWING LINES {max(1,error_lines[0]-25)}-{min(total_lines, error_lines[0]+25)} of {total_lines} total lines]
[⚠️ USE str_replace TOOL ONLY - DO NOT use create_file as this is partial content]
{relevant_content}
[END PARTIAL FILE - File continues beyond this excerpt]"""
                        logger.info(f"[SimpleFixer] Extracted ~50 lines around line {error_lines[0]} from {path_fragment}")
                    elif len(content) < 5000:
                        # Small file - send full content
                        files[path_fragment] = content
                        logger.info(f"[SimpleFixer] Sent full file {path_fragment} ({len(content)} chars)")
                    else:
                        # Large file without line number - send last portion (where syntax errors usually are)
                        # Get last 100 lines where SyntaxError is likely
                        lines = content.split('\n')
                        last_100 = '\n'.join(lines[-100:]) if len(lines) > 100 else content
                        files[path_fragment] = f"""[PARTIAL FILE - SHOWING LAST {min(100, len(lines))} LINES of {total_lines} total]
[⚠️ USE str_replace TOOL ONLY - file is larger than shown]
{last_100}
[END PARTIAL FILE]"""
                        logger.info(f"[SimpleFixer] Sent last 100 lines of {path_fragment} (no line number available)")
                    continue
                except:
                    pass

            # Fallback to glob search
            for p in project_path.rglob(f"*{path_fragment}"):
                if p.is_file():
                    try:
                        rel = str(p.relative_to(project_path))
                        content = p.read_text(encoding='utf-8')
                        total_lines = len(content.split('\n'))

                        # Use first error line found for this file
                        if error_lines and len(content) > 5000:
                            relevant_content = self._extract_relevant_lines(content, error_lines[0], context_lines=25)
                            files[rel] = f"""[PARTIAL FILE - SHOWING LINES {max(1,error_lines[0]-25)}-{min(total_lines, error_lines[0]+25)} of {total_lines} total lines]
[⚠️ USE str_replace TOOL ONLY - DO NOT use create_file as this is partial content]
{relevant_content}
[END PARTIAL FILE - File continues beyond this excerpt]"""
                        elif len(content) < 5000:
                            files[rel] = content
                        else:
                            # Large file without line number - send last portion
                            lines = content.split('\n')
                            last_100 = '\n'.join(lines[-100:]) if len(lines) > 100 else content
                            files[rel] = f"""[PARTIAL FILE - SHOWING LAST {min(100, len(lines))} LINES of {total_lines} total]
[⚠️ USE str_replace TOOL ONLY - file is larger than shown]
{last_100}
[END PARTIAL FILE]"""
                    except:
                        pass
                    break

        total_chars = sum(len(v) for v in files.values())
        logger.info(f"[SimpleFixer] Gathered {len(files)} context files (~{total_chars} chars, optimized)")
        return files

    def _format_errors(self, errors: List[Dict[str, Any]]) -> str:
        """Format errors for the prompt"""
        lines = []
        for i, err in enumerate(errors[:10], 1):
            source = err.get('source', 'unknown')
            msg = err.get('message', '')[:500]
            file = err.get('file', '')
            line = err.get('line', '')
            stack = err.get('stack', '')[:300] if err.get('stack') else ''

            lines.append(f"{i}. [{source.upper()}] {msg}")
            if file:
                lines.append(f"   File: {file}:{line}" if line else f"   File: {file}")
            if stack:
                lines.append(f"   Stack: {stack}")
        return "\n".join(lines)

    def _format_recently_modified(self, recently_modified: Optional[List[Dict]]) -> str:
        """Format recently modified files"""
        if not recently_modified:
            return "(none)"
        lines = []
        for f in recently_modified[:10]:
            lines.append(f"- {f.get('path', '')} ({f.get('action', '')})")
        return "\n".join(lines)

    async def should_fix(self, exit_code: Optional[int], output: str) -> bool:
        """
        Simple check: should we attempt a fix?

        - Non-zero exit code = yes
        - Contains obvious error indicators = yes
        - Otherwise = no
        """
        # Non-zero exit code is a clear signal
        if exit_code is not None and exit_code != 0:
            return True

        # Check for clear error indicators in output
        # COMPREHENSIVE patterns for ALL technologies
        clear_errors = [
            # ===== JavaScript/TypeScript =====
            'ENOENT: no such file',
            'Cannot find module',
            'Module not found',
            'SyntaxError:',
            'TypeError:',
            'ReferenceError:',
            'error TS',  # TypeScript errors (error TS2304, etc.)
            'Failed to resolve import',

            # ===== React/Vite/Webpack =====
            '[plugin:vite:',
            '[vite] error',
            'Failed to compile',
            'Module build failed',
            'Invalid hook call',
            'render error',

            # ===== Next.js =====
            'next build failed',
            'Error occurred prerendering',

            # ===== Angular =====
            'ERROR in ',  # Angular CLI errors
            'NG0',  # Angular runtime errors (NG0100, etc.)

            # ===== Vue =====
            '[Vue warn]',
            'vue-loader',

            # ===== Java/Spring Boot/Maven =====
            '[ERROR] COMPILATION ERROR',
            'Non-parseable POM',
            'BUILD FAILURE',  # Maven
            'java.lang.NullPointerException',
            'java.lang.ClassNotFoundException',
            'NoSuchBeanDefinitionException',
            'BeanCreationException',

            # ===== Gradle =====
            'FAILURE: Build failed',
            'Execution failed for task',

            # ===== Python =====
            'ModuleNotFoundError:',
            'ImportError:',
            'NameError:',
            'AttributeError:',
            'IndentationError:',
            'Traceback (most recent call last)',
            'SyntaxError: invalid syntax',

            # ===== Go =====
            'error: ',  # Go compiler
            'undefined:',
            'cannot find package',
            'panic:',

            # ===== Rust =====
            'error[E',  # Rust compiler (error[E0425], etc.)
            'cannot find',

            # ===== Ruby/Rails =====
            'LoadError:',
            'NameError:',
            'NoMethodError:',
            'ActionController::RoutingError',

            # ===== PHP/Laravel =====
            'PHP Fatal error',
            'PHP Parse error',
            'Symfony\\Component\\Debug\\Exception',

            # ===== .NET/C# =====
            'error CS',  # C# compiler errors (error CS1002, etc.)
            'System.NullReferenceException',
            'System.InvalidOperationException',

            # ===== Docker =====
            'Error response from daemon',
            'container exited with code',
            'COPY failed',

            # ===== Generic =====
            'fatal error',
            'FATAL:',
            'Exception:',
            'exception:',
        ]

        # Check for success indicators (should NOT fix)
        success_indicators = [
            # ===== JavaScript/Node =====
            'Compiled successfully',
            'ready in',  # Vite ready
            'compiled client and server',

            # ===== Java/Maven =====
            'BUILD SUCCESS',
            'BUILD SUCCESSFUL',  # Gradle

            # ===== Python =====
            'Server running',
            'Listening on',
            'Uvicorn running',
            'Serving Flask app',

            # ===== Go =====
            'go build successful',

            # ===== Generic =====
            'Started Application',
            'Application started',
            'Server started',
            'Watching for file changes',
        ]

        # If we see success, don't fix
        for success in success_indicators:
            if success.lower() in output.lower():
                return False

        # If we see clear error, fix
        for error in clear_errors:
            if error.lower() in output.lower():
                return True

        return False

    async def _try_deterministic_css_fix(self, project_path: Path, output: str) -> Optional[SimpleFixResult]:
        """
        Try to fix Tailwind CSS errors deterministically (no AI call needed).

        Handles errors like:
        - "The `border-border` class does not exist"
        - "The `bg-background` class does not exist"

        Returns SimpleFixResult if fixed, None if not a CSS error or fix failed.
        """
        # Check if this is a Tailwind CSS class error
        if "class does not exist" not in output.lower():
            return None

        # Extract the missing class name
        class_pattern = r"The [`']([a-zA-Z0-9\-_]+)[`'] class does not exist"
        match = re.search(class_pattern, output)
        if not match:
            return None

        missing_class = match.group(1)
        logger.info(f"[SimpleFixer] Detected missing Tailwind class: {missing_class}")

        # Mapping of shadcn/ui classes to standard Tailwind
        shadcn_to_tailwind = {
            "border-border": "border-gray-200 dark:border-gray-700",
            "bg-background": "bg-white dark:bg-gray-900",
            "text-foreground": "text-gray-900 dark:text-white",
            "bg-card": "bg-white dark:bg-gray-800",
            "text-card-foreground": "text-gray-900 dark:text-gray-100",
            "bg-popover": "bg-white dark:bg-gray-800",
            "text-popover-foreground": "text-gray-900 dark:text-gray-100",
            "bg-primary": "bg-blue-600",
            "text-primary-foreground": "text-white",
            "bg-secondary": "bg-gray-100 dark:bg-gray-700",
            "text-secondary-foreground": "text-gray-900 dark:text-gray-100",
            "bg-muted": "bg-gray-100 dark:bg-gray-800",
            "text-muted-foreground": "text-gray-500 dark:text-gray-400",
            "bg-accent": "bg-gray-100 dark:bg-gray-700",
            "text-accent-foreground": "text-gray-900 dark:text-gray-100",
            "bg-destructive": "bg-red-600",
            "text-destructive-foreground": "text-white",
            "ring-ring": "ring-blue-500",
            "bg-input": "bg-white dark:bg-gray-800",
        }

        if missing_class not in shadcn_to_tailwind:
            logger.info(f"[SimpleFixer] No mapping for class: {missing_class}")
            return None

        replacement = shadcn_to_tailwind[missing_class]

        # Find and fix CSS files
        css_file_paths = [
            project_path / "src" / "index.css",
            project_path / "src" / "globals.css",
            project_path / "src" / "app" / "globals.css",
            project_path / "src" / "styles" / "globals.css",
            project_path / "src" / "App.css",
            project_path / "app" / "globals.css",
            project_path / "styles" / "globals.css",
            project_path / "frontend" / "src" / "index.css",
            project_path / "frontend" / "src" / "globals.css",
        ]

        files_modified = []

        for css_path in css_file_paths:
            if not css_path.exists():
                continue

            try:
                content = css_path.read_text(encoding='utf-8')
                original_content = content

                # Replace @apply with the shadcn class
                patterns = [
                    (rf'@apply\s+{re.escape(missing_class)}\s*;', f'@apply {replacement};'),
                    (rf'(@apply\s+[^;]*)\b{re.escape(missing_class)}\b([^;]*;)', rf'\1{replacement}\2'),
                ]

                for pattern, repl in patterns:
                    content = re.sub(pattern, repl, content)

                if content != original_content:
                    css_path.write_text(content, encoding='utf-8')
                    rel_path = str(css_path.relative_to(project_path))
                    files_modified.append(rel_path)
                    logger.info(f"[SimpleFixer] Fixed {missing_class} -> {replacement} in {rel_path}")

            except Exception as e:
                logger.warning(f"[SimpleFixer] Error fixing {css_path}: {e}")
                continue

        if files_modified:
            return SimpleFixResult(
                success=True,
                files_modified=files_modified,
                message=f"Replaced @apply {missing_class} with {replacement}",
                patches_applied=len(files_modified)
            )

        return None

    async def fix(
        self,
        project_path: Path,
        command: str,
        output: str,
        exit_code: Optional[int] = None
    ) -> SimpleFixResult:
        """
        Fix an error using AI - COST OPTIMIZED.

        Simple flow:
        1. TRY DETERMINISTIC FIX FIRST (fast, free) - Tailwind CSS errors
        2. Classify error complexity for model selection
        3. Gather SMALLER context (only error-mentioned files + key configs)
        4. Send to AI with selected model
        5. Apply fixes with max 5 iterations
        """
        try:
            # =================================================================
            # STEP 0: Try deterministic fix FIRST (fast, free, no API call)
            # =================================================================
            deterministic_result = await self._try_deterministic_css_fix(project_path, output)
            if deterministic_result:
                logger.info(f"[SimpleFixer] Deterministic CSS fix applied - skipping AI")
                return deterministic_result
            # COST OPTIMIZATION #2: Classify error for model selection
            errors = [{"message": output[-2000:], "source": "terminal"}]
            complexity = self._classify_error_complexity(errors, output)
            model = self._select_model(complexity)

            # COST OPTIMIZATION #3: Gather SMALLER context
            context_files = await self._gather_context_optimized(project_path, output, errors)

            # COST OPTIMIZATION #3: Smaller context window based on complexity
            context_limit = 6000 if complexity == ErrorComplexity.SIMPLE else 10000
            user_message = f"""Command: {command}
Exit code: {exit_code}

Full output:
```
{output[-context_limit:]}
```

Project files:
{self._format_files(context_files)}

Please analyze the output and fix any errors. If there are no errors to fix (e.g., the output shows success), respond with "NO_FIX_NEEDED".
"""

            logger.info(f"[SimpleFixer] Terminal fix (model={model.split('-')[1]}, complexity={complexity.value})")

            # Call AI with selected model
            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=SIMPLE_FIXER_PROMPT,
                tools=self._get_tools(),
                messages=[{"role": "user", "content": user_message}]
            )
            self._track_tokens(response, model)

            # Check if no fix needed
            if response.stop_reason == "end_turn":
                text = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        text += block.text
                if "NO_FIX_NEEDED" in text:
                    return SimpleFixResult(
                        success=True,
                        files_modified=[],
                        message="No fix needed - output indicates success"
                    )

            # Process tool calls
            files_modified = []
            iterations = 0
            # COST OPTIMIZATION #4: Lower max iterations (3 instead of 5)
            # If 3 tries don't fix it, ask user or try different approach
            max_iterations = 3

            while response.stop_reason == "tool_use" and iterations < max_iterations:
                iterations += 1
                logger.info(f"[SimpleFixer] Terminal fix iteration {iterations}/{max_iterations}")

                # Execute tools
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(
                            project_path,
                            block.name,
                            block.input
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                        # Track file modifications
                        if block.name in ["create_file", "str_replace"]:
                            path = block.input.get("path", "")
                            if path and path not in files_modified:
                                files_modified.append(path)

                # Continue conversation with selected model
                response = await self.client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=SIMPLE_FIXER_PROMPT,
                    tools=self._get_tools(),
                    messages=[
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": response.content},
                        {"role": "user", "content": tool_results}
                    ]
                )
                self._track_tokens(response, model)

            return SimpleFixResult(
                success=len(files_modified) > 0,
                files_modified=files_modified,
                message=f"Fixed {len(files_modified)} files (model={model.split('-')[1]}, iterations={iterations})"
            )

        except Exception as e:
            logger.error(f"[SimpleFixer] Error: {e}")
            return SimpleFixResult(
                success=False,
                files_modified=[],
                message=str(e)
            )

    async def _gather_context(self, project_path: Path, output: str) -> Dict[str, str]:
        """Gather relevant project files for context"""
        files = {}

        # Always include config files - COMPREHENSIVE for all technologies
        config_files = [
            # ===== JavaScript/TypeScript/Node.js =====
            "package.json",
            "package-lock.json",
            "tsconfig.json",
            "tsconfig.node.json",
            "tsconfig.app.json",
            "jsconfig.json",
            ".eslintrc.js",
            ".eslintrc.json",

            # ===== React/Vite =====
            "vite.config.ts",
            "vite.config.js",
            "vite.config.mjs",

            # ===== Next.js =====
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",

            # ===== Vue =====
            "vue.config.js",
            "vite.config.ts",
            "nuxt.config.js",
            "nuxt.config.ts",

            # ===== Angular =====
            "angular.json",
            "tsconfig.app.json",
            "tsconfig.spec.json",

            # ===== Svelte =====
            "svelte.config.js",

            # ===== Java/Spring Boot/Maven/Gradle =====
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "settings.gradle.kts",
            "src/main/resources/application.properties",
            "src/main/resources/application.yml",
            "src/main/resources/application.yaml",

            # ===== Python =====
            "requirements.txt",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "Pipfile",
            "poetry.lock",
            "manage.py",  # Django
            "app.py",     # Flask
            "main.py",    # FastAPI
            "wsgi.py",
            "asgi.py",

            # ===== Go =====
            "go.mod",
            "go.sum",

            # ===== Rust =====
            "Cargo.toml",
            "Cargo.lock",

            # ===== Ruby/Rails =====
            "Gemfile",
            "Gemfile.lock",
            "config/routes.rb",
            "config/database.yml",

            # ===== PHP/Laravel =====
            "composer.json",
            "composer.lock",
            "artisan",
            ".env",

            # ===== .NET/C# =====
            "*.csproj",
            "*.sln",
            "appsettings.json",
            "appsettings.Development.json",
            "Program.cs",

            # ===== Docker =====
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            ".dockerignore",

            # ===== Fullstack project paths =====
            "frontend/package.json",
            "frontend/tsconfig.json",
            "frontend/tsconfig.node.json",
            "frontend/vite.config.ts",
            "frontend/vite.config.js",
            "frontend/next.config.js",
            "frontend/angular.json",
            "client/package.json",
            "client/tsconfig.json",
            "web/package.json",

            # ===== Backend paths =====
            "backend/pom.xml",
            "backend/build.gradle",
            "backend/requirements.txt",
            "backend/pyproject.toml",
            "backend/go.mod",
            "backend/Cargo.toml",
            "backend/src/main/resources/application.properties",
            "backend/src/main/resources/application.yml",
            "server/package.json",
            "server/tsconfig.json",
            "api/package.json",
            "api/requirements.txt",
        ]

        for rel_path in config_files:
            full_path = project_path / rel_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8')
                    if len(content) < 20000:  # Skip huge files
                        files[rel_path] = content
                except:
                    pass

        # Extract files mentioned in error output
        import re
        # Match paths like /path/to/file.ts or C:\path\to\file.ts
        path_pattern = r'[\w/\\.-]+\.(tsx?|jsx?|py|java|go|rs|json|xml|properties)'
        mentioned = re.findall(path_pattern, output)

        for path_fragment in mentioned[:10]:  # Limit to 10 files
            # Try to find the file
            for p in project_path.rglob(f"*{path_fragment}"):
                if p.is_file():
                    try:
                        rel = p.relative_to(project_path)
                        content = p.read_text(encoding='utf-8')
                        if len(content) < 20000:
                            files[str(rel)] = content
                    except:
                        pass
                    break

        return files

    def _format_files(self, files: Dict[str, str]) -> str:
        """Format files for the prompt"""
        result = []
        for path, content in files.items():
            result.append(f"=== {path} ===\n{content}\n")
        return "\n".join(result) if result else "(No relevant files found)"

    def _get_tools(self) -> List[Dict]:
        """Get tool definitions for Claude"""
        return [
            {
                "name": "create_file",
                "description": "Create a new file or overwrite an existing file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to project root"
                        },
                        "content": {
                            "type": "string",
                            "description": "File content"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "str_replace",
                "description": "Replace a string in a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to project root"
                        },
                        "old_str": {
                            "type": "string",
                            "description": "String to find and replace"
                        },
                        "new_str": {
                            "type": "string",
                            "description": "Replacement string"
                        }
                    },
                    "required": ["path", "old_str", "new_str"]
                }
            },
            {
                "name": "view_file",
                "description": "Read a file's contents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to project root"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_directory",
                "description": "List files in a directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path relative to project root"
                        }
                    },
                    "required": ["path"]
                }
            }
        ]

    async def _sync_to_s3(self, project_id: str, file_path: str, content: str) -> None:
        """Sync fixed file to S3 storage"""
        try:
            from app.services.unified_storage import unified_storage

            # Upload to S3
            s3_key = f"projects/{project_id}/{file_path}"
            await unified_storage.upload_content(
                content=content.encode('utf-8'),
                key=s3_key,
                content_type='text/plain'
            )
            logger.info(f"[SimpleFixer] Synced to S3: {s3_key}")
        except Exception as e:
            # Don't fail the fix if S3 sync fails - just log it
            logger.warning(f"[SimpleFixer] Failed to sync to S3: {e}")

    async def _execute_tool(
        self,
        project_path: Path,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """Execute a tool and return result"""
        try:
            path = tool_input.get("path", "")
            full_path = project_path / path

            # Extract project_id and user_id from path for S3 sync
            # Path format: /tmp/sandbox/workspace/{user_id}/{project_id}/
            path_parts = str(project_path).replace("\\", "/").split("/")
            project_id = path_parts[-1] if path_parts else None
            user_id = path_parts[-2] if len(path_parts) >= 2 else None

            if tool_name == "create_file":
                content = tool_input.get("content", "")

                # VALIDATION: Reject empty content
                if not content or not content.strip():
                    logger.warning(f"[SimpleFixer] Rejected create_file with empty content: {path}")
                    return f"Error: Cannot create file with empty content. Please provide the full file content."

                # FIX: Remove leading empty lines - content should start from first line
                # This fixes the issue where AI leaves first line blank
                content = content.lstrip('\n\r')

                # CRITICAL: Prevent overwriting existing files with partial content (truncation bug fix)
                if full_path.exists():
                    existing_content = full_path.read_text(encoding='utf-8')
                    existing_lines = len(existing_content.split('\n'))
                    new_lines = len(content.split('\n'))
                    # If new content is much shorter than existing, reject to prevent truncation
                    if existing_lines > 100 and new_lines < existing_lines * 0.7:
                        logger.warning(f"[SimpleFixer] Rejected create_file that would truncate {path}: {existing_lines} -> {new_lines} lines")
                        return f"Error: This would truncate {path} from {existing_lines} to {new_lines} lines. Use str_replace to modify specific parts instead."

                # VALIDATION: Reject content with partial file markers
                if "[PARTIAL FILE" in content or "[END PARTIAL FILE" in content:
                    logger.warning(f"[SimpleFixer] Rejected create_file with partial file markers: {path}")
                    return f"Error: Use str_replace for partial file content, not create_file."

                # VALIDATION: Reject suspiciously short content (likely truncated)
                is_config = any(ext in path.lower() for ext in ['.json', '.yml', '.yaml', '.toml', '.xml', '.properties', '.env'])
                min_length = 10 if is_config else 50

                if len(content.strip()) < min_length and not is_config:
                    logger.warning(f"[SimpleFixer] Rejected create_file with suspiciously short content ({len(content)} chars): {path}")
                    return f"Error: Content too short ({len(content)} chars). This might be truncated. Please provide complete file content."

                # Ensure file ends with single newline (standard convention)
                content = content.rstrip() + '\n'

                # LAYER 1: Write to sandbox
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding='utf-8')
                logger.info(f"[SimpleFixer] Created file: {path} ({len(content)} chars)")

                # LAYER 2: Sync to S3
                if project_id:
                    await self._sync_to_s3(project_id, path, content)

                return f"Created {path} ({len(content)} chars)"

            elif tool_name == "str_replace":
                if not full_path.exists():
                    return f"Error: File {path} not found"
                content = full_path.read_text(encoding='utf-8')
                old_str = tool_input["old_str"]
                new_str = tool_input["new_str"]
                if old_str not in content:
                    return f"Error: String not found in {path}"
                new_content = content.replace(old_str, new_str, 1)

                # LAYER 1: Write to sandbox
                full_path.write_text(new_content, encoding='utf-8')
                logger.info(f"[SimpleFixer] Modified file: {path}")

                # LAYER 2: Sync to S3
                if project_id:
                    await self._sync_to_s3(project_id, path, new_content)

                return f"Replaced in {path}"

            elif tool_name == "view_file":
                if not full_path.exists():
                    return f"Error: File {path} not found"
                content = full_path.read_text(encoding='utf-8')
                return content[:10000]  # Limit size

            elif tool_name == "list_directory":
                if not full_path.exists():
                    return f"Error: Directory {path} not found"
                items = []
                for item in full_path.iterdir():
                    prefix = "[DIR]" if item.is_dir() else "[FILE]"
                    items.append(f"{prefix} {item.name}")
                return "\n".join(items[:50])  # Limit entries

            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error: {str(e)}"


# Singleton instance
simple_fixer = SimpleFixer()
