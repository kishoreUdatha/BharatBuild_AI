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
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from anthropic import AsyncAnthropic

from app.core.logging_config import logger
from app.core.config import settings
from app.services.unified_file_manager import unified_file_manager


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


class ErrorCategory(str, Enum):
    """Error category for specialized fixing (Bolt.new style)"""
    CODE = "code"           # Syntax, type, logic errors -> Code Agent
    DEPENDENCY = "dependency"  # npm/pnpm, missing packages -> Dependency Agent
    INFRASTRUCTURE = "infrastructure"  # Docker, ports, containers -> Infra Agent
    NETWORK = "network"     # Timeouts, DNS, registry -> NOT fixable by code
    UNKNOWN = "unknown"     # Needs investigation


def classify_error(error_message: str, context: str = "") -> tuple[ErrorCategory, str]:
    """
    Classify error into category for specialized handling (Bolt.new style).

    Returns:
        Tuple of (ErrorCategory, reason_for_classification)
    """
    error_lower = error_message.lower()
    context_lower = context.lower()
    combined = f"{error_lower} {context_lower}"

    # =====================================================
    # SYSTEM ERRORS - Internal platform errors, NOT fixable by user code
    # These are issues with the BharatBuild platform itself
    # =====================================================
    system_patterns = [
        ("No such image: docker/compose", "helper container image missing"),
        ("No such image: python:", "helper container image missing"),
        ("No such image: node:", "helper container image missing"),
        ("No such image: alpine", "helper container image missing"),
        ("helper container", "internal helper container error"),
        ("_run_shell_on_sandbox", "internal sandbox error"),
        ("ContainerExecutor", "internal executor error"),
        ("Failed to create helper container", "internal container error"),
        ("No files found in database", "project restore failed"),
        ("No files to restore", "project restore failed"),
        ("ERROR: No files", "project restore failed"),
        ("S3 restore failed", "S3 restore error"),
        ("Project restore timed out", "restore timeout"),
    ]
    for pattern, reason in system_patterns:
        if pattern.lower() in combined:
            return ErrorCategory.NETWORK, f"SYSTEM: {reason}"  # Use NETWORK to skip AI fix

    # =====================================================
    # NETWORK ERRORS - NOT fixable by code changes
    # =====================================================
    network_patterns = [
        ("ETIMEDOUT", "npm registry timeout"),
        ("ENOTFOUND", "DNS resolution failed"),
        ("ECONNREFUSED", "connection refused"),
        ("ECONNRESET", "connection reset"),
        ("socket hang up", "network socket error"),
        ("network timeout", "network timeout"),
        ("fetch failed", "fetch failed"),
        ("ERR_INTERNET_DISCONNECTED", "no internet"),
        ("getaddrinfo", "DNS lookup failed"),
        ("CERT_", "SSL certificate error"),
    ]
    for pattern, reason in network_patterns:
        if pattern.lower() in combined:
            return ErrorCategory.NETWORK, reason

    # =====================================================
    # INFRASTRUCTURE ERRORS - Docker, ports, containers
    # =====================================================
    infra_patterns = [
        ("port already in use", "port conflict"),
        ("address already in use", "port conflict"),
        ("EADDRINUSE", "port already allocated"),
        ("container", "container issue"),
        ("docker", "docker issue"),
        ("permission denied", "permission issue"),
        ("EACCES", "permission error"),
        ("disk full", "disk space"),
        ("no space left", "disk space"),
        ("out of memory", "memory exhausted"),
        ("OOMKilled", "container killed by OOM"),
        ("sandbox", "sandbox issue"),
        ("Cannot connect to Docker", "docker not running"),
    ]
    for pattern, reason in infra_patterns:
        if pattern.lower() in combined:
            return ErrorCategory.INFRASTRUCTURE, reason

    # =====================================================
    # DEPENDENCY ERRORS - npm/pnpm/yarn conflicts
    # =====================================================
    dependency_patterns = [
        ("npm ERR!", "npm error"),
        ("pnpm ERR!", "pnpm error"),
        ("yarn error", "yarn error"),
        ("ERESOLVE", "dependency resolution conflict"),
        ("peer dep", "peer dependency issue"),
        ("Could not resolve dependency", "dependency conflict"),
        ("ERR_PNPM_", "pnpm specific error"),
        ("EOVERRIDE", "dependency override needed"),
        ("lockfile", "lockfile mismatch"),
        ("package-lock", "lockfile issue"),
        ("pnpm-lock", "lockfile issue"),
        ("Cannot find module", "missing module"),
        ("MODULE_NOT_FOUND", "module not found"),
        ("missing dependencies", "missing deps"),
        ("npm install", "install failure"),
        ("node_modules", "node_modules issue"),
        ("packageManager", "package manager mismatch"),
    ]
    for pattern, reason in dependency_patterns:
        if pattern.lower() in combined:
            return ErrorCategory.DEPENDENCY, reason

    # =====================================================
    # CODE ERRORS - Syntax, type, logic (fixable by AI)
    # =====================================================
    code_patterns = [
        ("SyntaxError", "syntax error"),
        ("TypeError", "type error"),
        ("ReferenceError", "reference error"),
        ("NameError", "name error"),
        ("ImportError", "import error"),
        ("IndentationError", "indentation error"),
        ("TS2", "TypeScript error"),  # TS2304, TS2322, etc.
        ("TS6", "TypeScript warning"),
        ("error TS", "TypeScript error"),
        ("ESLint", "lint error"),
        ("Parsing error", "parse error"),
        ("Unexpected token", "syntax error"),
        ("is not defined", "undefined variable"),
        ("Cannot read property", "null reference"),
        ("Cannot read properties", "null reference"),
        ("is not a function", "type error"),
        ("declared but", "unused declaration"),
        ("Property '", "property error"),
        ("does not exist on type", "type error"),
        ("Expected", "syntax error"),
        ("Unexpected", "syntax error"),
        ("missing", "missing element"),
        ("Cannot find name", "undefined name"),
        ("build failed", "build error"),
        ("compilation failed", "compile error"),
        ("vite", "vite build error"),
        ("webpack", "webpack error"),
    ]
    for pattern, reason in code_patterns:
        if pattern.lower() in combined:
            return ErrorCategory.CODE, reason

    # Default to CODE for unknown errors (let AI try to fix)
    return ErrorCategory.UNKNOWN, "unclassified error"


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

NPM / YARN DEPENDENCY ERRORS:
- npm error E404 / 404 Not Found: Package doesn't exist on npm registry
  - SOLUTION: Remove the non-existent package from BOTH package.json AND package-lock.json
  - In package.json: Remove the line from dependencies or devDependencies
  - In package-lock.json: Find and remove all entries for the package (search for the package name)
  - If the package was needed, find an alternative or remove the import from code
- npm ERESOLVE: Dependency resolution conflict
  - SOLUTION: Check for conflicting version requirements in package.json
- Missing peer dependency: Add the required peer dependency to package.json
- IMPORTANT: Always check BOTH package.json AND package-lock.json for npm errors!

VITE / ESBUILD DEPENDENCY SCAN ERRORS:
- "Failed to scan for dependencies from entries": Module import can't be resolved
  - SOLUTION: Find and remove/fix the bad import statement in the source code
  - Search source files (.tsx, .ts, .jsx, .js) for imports of non-existent packages
  - Either remove the import entirely, or replace with an alternative package
- "Could not resolve": Same as above - module not found
- "Failed to resolve import": The import path is wrong or package doesn't exist
  - Check if the package is in package.json - if not, either add it or remove the import
- IMPORT ANALYSIS: When you see "[IMPORT ANALYSIS - MISSING DEPENDENCIES]" in the context,
  this shows imports that are NOT in package.json. These are the problematic imports!
  - For each listed import, either:
    a) Remove the import statement from the source file if the package is not needed
    b) Replace with an alternative package that IS in package.json
    c) If the import is from code that should be removed entirely, delete that code

EXPORT MISMATCH ERRORS (esbuild "No matching export"):
- When you see "[EXPORT MISMATCH ERRORS - FIX THESE FIRST!]" in the context, these are CRITICAL!
- Error: "No matching export in 'file.tsx' for import 'ComponentName'"
  - This means the file exists but doesn't export what's being imported
  - SOLUTION: Open the file and add the missing export
  - If the file has `export default Component`, change to `export const ComponentName = Component` or add named export
  - If using React Context, make sure BOTH the context AND the provider are exported:
    Example: `export const AuthContext = createContext(...); export const AuthProvider = ...`
  - Check if there's a typo in the export name vs import name

IMPORTANT RULES:
- If the output shows SUCCESS (build success, server started, etc.) - respond with "NO_FIX_NEEDED"
- Only fix ACTUAL errors, not warnings or info messages
- Be precise - fix the exact issue, don't over-engineer
- Create missing files if needed (config files, missing modules)
- Fix import/include errors, syntax errors, type errors
- For CORS errors, update backend CORS configuration
- For missing dependencies, suggest installing OR fix the import path
- For npm 404 errors (package not found), REMOVE the non-existent package from package.json

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

    # ==================== BOLT.NEW STYLE ERROR ROUTING ====================
    async def _handle_by_category(
        self,
        project_id: str,
        project_path: Path,
        error_category: ErrorCategory,
        category_reason: str,
        errors: List[Dict[str, Any]],
        context: str,
        command: Optional[str] = None
    ) -> Optional[SimpleFixResult]:
        """
        Bolt.new style specialized handling based on error category.

        Routes errors to the appropriate fixer:
        - NETWORK: Return early (not fixable by code)
        - DEPENDENCY: Try package manager fixes first
        - INFRASTRUCTURE: Handle container/port issues
        - CODE/UNKNOWN: Return None to continue to AI fixer

        Returns:
            SimpleFixResult if handled, None if should continue to AI fixer
        """
        logger.info(f"[SimpleFixer:{project_id}] Error classified as {error_category.value}: {category_reason}")

        # =====================================================
        # NETWORK/SYSTEM ERRORS - Not fixable by code changes
        # =====================================================
        if error_category == ErrorCategory.NETWORK:
            # Differentiate system errors from network errors
            if category_reason.startswith("SYSTEM:"):
                logger.warning(f"[SimpleFixer:{project_id}] System error detected - internal platform issue")
                return SimpleFixResult(
                    success=False,
                    files_modified=[],
                    message=f"Internal system error ({category_reason}) - this is a platform issue, not your code. "
                            "Please try again or contact support if the issue persists.",
                    patches_applied=0
                )
            else:
                logger.warning(f"[SimpleFixer:{project_id}] Network error detected - not fixable by code")
                return SimpleFixResult(
                    success=False,
                    files_modified=[],
                    message=f"Network error ({category_reason}) - cannot be fixed by code changes. "
                            "Please check your internet connection or wait for registry availability.",
                    patches_applied=0
                )

        # =====================================================
        # DEPENDENCY ERRORS - Try package manager fixes first
        # =====================================================
        if error_category == ErrorCategory.DEPENDENCY:
            logger.info(f"[SimpleFixer:{project_id}] Dependency error - trying package manager fixes first")
            try:
                from app.services.workspace_restore import workspace_restore

                # Run the common issues fixer which handles package manager conflicts
                fix_result = await workspace_restore.fix_common_issues(
                    workspace_path=project_path,
                    project_id=project_id
                )

                if fix_result.get("fixes_applied", []):
                    fixes_list = fix_result.get("fixes_applied", [])
                    logger.info(f"[SimpleFixer:{project_id}] Applied {len(fixes_list)} dependency fixes")

                    # Check if we fixed package manager conflicts specifically
                    pkg_manager_fixed = any(
                        "package manager" in str(f).lower() or
                        "pnpm" in str(f).lower() or
                        "lockfile" in str(f).lower()
                        for f in fixes_list
                    )

                    if pkg_manager_fixed:
                        return SimpleFixResult(
                            success=True,
                            files_modified=fix_result.get("modified_files", []),
                            message=f"Fixed dependency issues: {', '.join(fixes_list[:3])}",
                            patches_applied=len(fixes_list)
                        )

                    # For other dependency fixes, still continue to AI if error persists
                    logger.info(f"[SimpleFixer:{project_id}] Dependency fixes applied, but may need AI fix too")

            except Exception as e:
                logger.warning(f"[SimpleFixer:{project_id}] Dependency fix failed: {e}")

            # Continue to AI fixer for remaining dependency issues
            return None

        # =====================================================
        # INFRASTRUCTURE ERRORS - Container/port issues
        # =====================================================
        if error_category == ErrorCategory.INFRASTRUCTURE:
            logger.info(f"[SimpleFixer:{project_id}] Infrastructure error - checking for fixable issues")

            # Port conflicts - can sometimes be fixed by changing the port in config
            if "port" in category_reason.lower():
                # This could be fixed by modifying vite.config or similar
                # Let AI handle it, but log the specific issue
                logger.info(f"[SimpleFixer:{project_id}] Port conflict - letting AI modify config")
                return None

            # Permission errors on sandbox might be transient
            if "permission" in category_reason.lower():
                logger.warning(f"[SimpleFixer:{project_id}] Permission error - may need container restart")
                return SimpleFixResult(
                    success=False,
                    files_modified=[],
                    message=f"Infrastructure error ({category_reason}) - may require container restart. "
                            "If this persists, try stopping and starting the preview again.",
                    patches_applied=0
                )

            # Other infrastructure errors
            return None

        # CODE and UNKNOWN - Continue to AI fixer
        return None

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

        # =================================================================
        # BOLT.NEW STYLE: Classify error by category FIRST
        # Route to specialized handlers before AI fixer
        # =================================================================
        error_text = context
        for err in errors:
            error_text += " " + err.get("message", "")

        # =================================================================
        # STEP 0: Try deterministic fixes FIRST (before any classification)
        # This handles tsconfig.node.json, postcss.config.js, port conflicts etc. without AI
        # =================================================================
        config_fix_result = await self._try_deterministic_config_file_fix(project_path, error_text)
        if config_fix_result:
            logger.info(f"[SimpleFixer:{project_id}] Deterministic config file fix applied (early) - skipping AI")
            return config_fix_result

        # Try port conflict fix
        port_fix_result = await self._try_deterministic_port_fix(project_path, error_text, project_id)
        if port_fix_result:
            logger.info(f"[SimpleFixer:{project_id}] Deterministic port fix applied - skipping AI")
            return port_fix_result

        error_category, category_reason = classify_error(error_text, context)

        # Try specialized handler first
        category_result = await self._handle_by_category(
            project_id=project_id,
            project_path=project_path,
            error_category=error_category,
            category_reason=category_reason,
            errors=errors,
            context=context,
            command=command
        )

        # If specialized handler returned a result, use it
        if category_result is not None:
            return category_result

        # =================================================================
        # Continue to AI fixer for CODE/UNKNOWN errors
        # =================================================================

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

    async def fix_from_backend(
        self,
        project_id: str,
        project_path: Path,
        payload: Dict[str, Any]
    ) -> SimpleFixResult:
        """
        BACKEND-FIRST AUTO-FIX: Fix errors captured directly from container execution.

        This is the CORRECT architecture - errors are captured in the backend
        (ExecutionContext) and sent here for fixing. NO FRONTEND INVOLVEMENT.

        Payload contains:
        - stderr: Complete stderr buffer (SINGLE SOURCE OF TRUTH)
        - stdout: Last 100 lines of stdout for context
        - command: The command that failed
        - runtime: Detected runtime (node, python, java, etc.)
        - exit_code: The exit code from the container
        - fix_attempt: Current fix attempt number
        - error_file/error_line: Classified error location (if detected)

        This is the production-grade approach used by Bolt.new and similar platforms.
        """
        stderr = payload.get("stderr", "")
        stdout = payload.get("stdout", "")
        command = payload.get("command", "")
        runtime = payload.get("runtime", "unknown")
        exit_code = payload.get("exit_code", 1)
        fix_attempt = payload.get("fix_attempt", 0)
        error_file = payload.get("error_file")
        error_line = payload.get("error_line")
        primary_error_type = payload.get("primary_error_type")

        logger.info(
            f"[SimpleFixer:{project_id}] fix_from_backend called: "
            f"runtime={runtime}, exit_code={exit_code}, attempt={fix_attempt}, "
            f"stderr_len={len(stderr)}, error_type={primary_error_type}"
        )

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

        # Build context from stderr + stdout (stderr is primary)
        combined_context = stderr
        if stdout:
            combined_context += f"\n\n--- STDOUT (for context) ---\n{stdout[-2000:]}"

        # Build errors list from backend-captured data
        errors = [{
            "source": "terminal",
            "type": primary_error_type or "build_error",
            "message": stderr[:2000] if stderr else "Unknown error",
            "file": error_file,
            "line": error_line,
            "severity": "error"
        }]

        # =================================================================
        # STEP 0: Try deterministic fixes FIRST (before any classification)
        # This handles tsconfig.node.json, postcss.config.js, port conflicts etc. without AI
        # =================================================================
        config_fix_result = await self._try_deterministic_config_file_fix(project_path, combined_context)
        if config_fix_result:
            logger.info(f"[SimpleFixer:{project_id}] Deterministic config file fix applied (early) - skipping AI")
            return config_fix_result

        # Try port conflict fix
        port_fix_result = await self._try_deterministic_port_fix(project_path, combined_context, project_id)
        if port_fix_result:
            logger.info(f"[SimpleFixer:{project_id}] Deterministic port fix applied - skipping AI")
            return port_fix_result

        # =================================================================
        # BOLT.NEW STYLE: Classify error by category FIRST
        # Route to specialized handlers before AI fixer
        # =================================================================
        error_category, category_reason = classify_error(stderr, combined_context)

        # Try specialized handler first
        category_result = await self._handle_by_category(
            project_id=project_id,
            project_path=project_path,
            error_category=error_category,
            category_reason=category_reason,
            errors=errors,
            context=combined_context,
            command=command
        )

        # If specialized handler returned a result, use it
        if category_result is not None:
            return category_result

        # =================================================================
        # Continue to AI fixer for CODE/UNKNOWN errors
        # =================================================================

        # Classify error complexity for model selection
        complexity = self._classify_error_complexity(errors, combined_context)

        # Record fix attempt
        self._record_fix_attempt(project_id)

        # Execute fix with combined context
        return await self._execute_fix_internal(
            project_id=project_id,
            project_path=project_path,
            errors=errors,
            context=combined_context,
            command=command,
            file_tree=None,  # Will be gathered by _gather_context_optimized
            recently_modified=None,
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
            # STEP 0a: Try deterministic React import fix (fast, free, no AI)
            # =================================================================
            react_fix_result = await self._try_deterministic_react_import_fix(project_path)
            if react_fix_result:
                logger.info(f"[SimpleFixer:{project_id}] Deterministic React import fix applied - skipping AI")
                return react_fix_result

            # =================================================================
            # STEP 0b: Try deterministic CSS fix FIRST (fast, free, no API call)
            # =================================================================
            error_text = context or ""
            for err in errors:
                error_text += " " + err.get("message", "")
            deterministic_result = await self._try_deterministic_css_fix(project_path, error_text)
            if deterministic_result:
                logger.info(f"[SimpleFixer:{project_id}] Deterministic CSS fix applied - skipping AI")
                return deterministic_result

            # =================================================================
            # STEP 0c: Try deterministic export mismatch fix (fast, free, no AI)
            # =================================================================
            export_fix_result = await self._try_deterministic_export_mismatch_fix(project_path, error_text)
            if export_fix_result:
                logger.info(f"[SimpleFixer:{project_id}] Deterministic export fix applied - skipping AI")
                return export_fix_result

            # =================================================================
            # STEP 0d: Try deterministic config file fix (fast, free, no AI)
            # Handles: tsconfig.node.json, postcss.config.js, etc.
            # =================================================================
            config_fix_result = await self._try_deterministic_config_file_fix(project_path, error_text)
            if config_fix_result:
                logger.info(f"[SimpleFixer:{project_id}] Deterministic config file fix applied - skipping AI")
                return config_fix_result

            # =================================================================
            # STEP 0e: Try deterministic port conflict fix (fast, free, no AI)
            # =================================================================
            port_fix_result = await self._try_deterministic_port_fix(project_path, error_text, project_id)
            if port_fix_result:
                logger.info(f"[SimpleFixer:{project_id}] Deterministic port fix applied - skipping AI")
                return port_fix_result

            # COST OPTIMIZATION #2: Select model based on complexity
            model = self._select_model(complexity)

            # COST OPTIMIZATION #3: Gather SMALLER context (only error-mentioned files + key configs)
            # Also returns modified context with export mismatch info if detected
            context_files, enriched_context = await self._gather_context_optimized(project_path, context, errors)

            # Build error summary
            error_summary = self._format_errors(errors)

            # COST OPTIMIZATION #3: Smaller context window
            # Use enriched_context which may contain export mismatch info
            context_limit = 8000 if complexity == ErrorComplexity.SIMPLE else 12000
            user_message = f"""Error Source: {errors[0].get('source', 'unknown') if errors else 'unknown'}
Command: {command or 'N/A'}

Errors:
{error_summary}

Full Context:
```
{enriched_context[-context_limit:] if enriched_context else '(no context)'}
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
            sync_failures = []  # Track files that failed to sync to S3
            iterations = 0
            # Allow up to 5 iterations for complex fixes
            max_iterations = 5

            while response.stop_reason == "tool_use" and iterations < max_iterations:
                iterations += 1
                logger.info(f"[SimpleFixer:{project_id}] Iteration {iterations}/{max_iterations}")

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Log all tool calls for debugging
                        logger.info(f"[SimpleFixer] Tool call: {block.name} on {block.input.get('path', 'N/A')}")
                        if block.name == "str_replace":
                            old_str_preview = block.input.get('old_str', '')[:100]
                            logger.info(f"[SimpleFixer] str_replace old_str preview: {old_str_preview!r}")

                        result = await self._execute_tool(
                            project_path,
                            block.name,
                            block.input,
                            project_id=project_id
                        )
                        logger.info(f"[SimpleFixer] Tool result: {result[:200] if result else 'None'}")

                        # Track sync failures for batch reporting
                        if result and "S3 sync failed" in result:
                            path = block.input.get("path", "unknown")
                            sync_failures.append(path)
                            logger.warning(f"[SimpleFixer] Sync failure tracked: {path}")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                        if block.name in ["create_file", "str_replace"]:
                            path = block.input.get("path", "")
                            # Normalize path (remove /app/ prefix if present)
                            if path.startswith("/app/"):
                                path = path[5:]
                            elif path.startswith("/"):
                                path = path.lstrip("/")
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

            # Build result message with sync failure warnings
            result_message = f"Fixed {len(files_modified)} files (model={model.split('-')[1]}, iterations={iterations})"
            if sync_failures:
                result_message += f" [WARNING: {len(sync_failures)} file(s) failed to sync to S3 - fixes may be lost on restart: {', '.join(sync_failures[:3])}]"
                logger.warning(f"[SimpleFixer:{project_id}] {len(sync_failures)} sync failures: {sync_failures}")

            return SimpleFixResult(
                success=len(files_modified) > 0,
                files_modified=files_modified,
                message=result_message,
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

    def _find_missing_imports(self, project_path: Path, source_files: List[str]) -> List[Dict[str, str]]:
        """
        Analyze source files to find imports that are NOT in package.json.
        This helps identify which import is causing Vite "Failed to scan" errors.

        Returns list of: [{"import": "package-name", "file": "src/App.tsx"}, ...]
        """
        import json

        # Step 1: Get all dependencies from package.json files
        dependencies = set()
        package_json_paths = [
            project_path / "package.json",
            project_path / "frontend" / "package.json",
            project_path / "client" / "package.json",
        ]

        for pkg_path in package_json_paths:
            if pkg_path.exists():
                try:
                    with open(pkg_path, 'r', encoding='utf-8') as f:
                        pkg_data = json.load(f)
                        # Get all dependencies
                        for key in ["dependencies", "devDependencies", "peerDependencies"]:
                            if key in pkg_data and isinstance(pkg_data[key], dict):
                                dependencies.update(pkg_data[key].keys())
                except Exception as e:
                    logger.debug(f"[SimpleFixer] Could not parse {pkg_path}: {e}")

        if not dependencies:
            logger.debug("[SimpleFixer] No dependencies found in package.json")
            return []

        logger.debug(f"[SimpleFixer] Found {len(dependencies)} packages in package.json")

        # Step 2: Extract imports from source files
        # Pattern matches: import ... from 'package' or import 'package' or require('package')
        import_pattern = re.compile(
            r'''(?:import\s+.*?\s+from\s+['"]([^'"./][^'"]*?)['"])|'''  # import X from 'package'
            r'''(?:import\s+['"]([^'"./][^'"]*?)['"])|'''  # import 'package'
            r'''(?:require\s*\(\s*['"]([^'"./][^'"]*?)['"]\s*\))'''  # require('package')
        )

        missing_imports = []

        for src_file in source_files[:15]:  # Limit to 15 files
            src_path = project_path / src_file
            if not src_path.exists():
                continue

            try:
                content = src_path.read_text(encoding='utf-8')
                matches = import_pattern.findall(content)

                for match in matches:
                    # match is a tuple of groups, get the non-empty one
                    package_name = match[0] or match[1] or match[2]
                    if not package_name:
                        continue

                    # Extract the base package name (e.g., '@types/react' -> '@types/react', 'lodash/merge' -> 'lodash')
                    if package_name.startswith('@'):
                        # Scoped package: @scope/package or @scope/package/subpath
                        parts = package_name.split('/')
                        base_package = '/'.join(parts[:2]) if len(parts) >= 2 else package_name
                    else:
                        # Regular package: package or package/subpath
                        base_package = package_name.split('/')[0]

                    # Check if package is in dependencies
                    if base_package not in dependencies:
                        # Also check if it's a built-in Node.js module
                        builtin_modules = {
                            'fs', 'path', 'os', 'util', 'events', 'stream', 'http', 'https',
                            'url', 'querystring', 'crypto', 'zlib', 'buffer', 'child_process',
                            'cluster', 'dgram', 'dns', 'net', 'tls', 'readline', 'repl',
                            'vm', 'assert', 'console', 'process', 'module'
                        }

                        if base_package not in builtin_modules:
                            # Check if we already added this import
                            already_added = any(
                                m['import'] == base_package and m['file'] == src_file
                                for m in missing_imports
                            )
                            if not already_added:
                                missing_imports.append({
                                    "import": base_package,
                                    "file": src_file,
                                    "full_import": package_name
                                })
                                logger.info(f"[SimpleFixer] Missing import: '{base_package}' in {src_file}")

            except Exception as e:
                logger.debug(f"[SimpleFixer] Could not analyze {src_file}: {e}")

        return missing_imports

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

    async def _gather_context_optimized(self, project_path: Path, output: str, errors: List[Dict[str, Any]]) -> tuple:
        """
        COST OPTIMIZATION #3: Gather SMALLER context.

        TOKEN OPTIMIZATION:
        - For files with errors: Send only ~50 lines around error (not full file!)
        - For config files: Send full content (usually small)
        - Result: ~90% token reduction for large files

        Returns:
            tuple: (files_dict, modified_output) - files and output with export mismatch info added
        """
        files = {}

        # Initialize variables for import error detection
        missing_imports = []
        is_vite_scan_error = False

        # KEY config files only (small files, send full content)
        # Include both root-level AND multi-folder project paths
        key_configs = [
            # Root level
            "package.json",
            "tsconfig.json",
            "vite.config.ts",
            "vite.config.js",
            "pom.xml",
            "requirements.txt",
            "pyproject.toml",
            # Multi-folder fullstack projects
            "frontend/package.json",
            "frontend/tsconfig.json",
            "frontend/vite.config.ts",
            "frontend/vite.config.js",
            "backend/package.json",
            "backend/requirements.txt",
            "backend/pom.xml",
            "client/package.json",
            "server/package.json",
        ]

        for rel_path in key_configs:
            full_path = project_path / rel_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8')
                    if len(content) < 5000:  # Config files should be small
                        files[rel_path] = content
                except (IOError, OSError, UnicodeDecodeError) as e:
                    logger.debug(f"Could not read config file {rel_path}: {e}")

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
                    except (IOError, OSError, UnicodeDecodeError) as e:
                        logger.debug(f"Could not read error file {file_path}: {e}")

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

        # CRITICAL: Detect npm/yarn dependency errors and add package.json
        # npm errors like "npm error code E404", "npm ERR! 404", "Cannot find module" need package.json
        output_lower = output.lower()
        npm_error_indicators = [
            'npm error',       # npm 10+
            'npm err!',        # npm < 10
            'e404',            # npm error code
            '404 not found',   # registry 404
            'enoent',          # file not found
            'eresolve',        # dependency resolution error
            'peer dep',        # peer dependency
            'missing peer',    # missing peer dependency
            'could not resolve',
            'unable to resolve',
            'cannot find module',
            'module not found',
            'no matching version',
            'yarn error',      # yarn errors
        ]
        is_npm_error = any(indicator in output_lower for indicator in npm_error_indicators)

        if is_npm_error:
            logger.info(f"[SimpleFixer] Detected npm/dependency error - ensuring package.json files are included")
            # Add package.json AND package-lock.json files to mentioned list for npm errors
            # IMPORTANT: package-lock.json can cache old dependencies even after package.json is fixed
            npm_files_to_check = [
                "package.json",
                "package-lock.json",
                "frontend/package.json",
                "frontend/package-lock.json",
                "backend/package.json",
                "backend/package-lock.json",
                "client/package.json",
                "client/package-lock.json",
                "server/package.json",
                "server/package-lock.json",
            ]
            for npm_file in npm_files_to_check:
                npm_path = project_path / npm_file
                if npm_path.exists() and npm_file not in mentioned:
                    mentioned.append(npm_file)
                    logger.info(f"[SimpleFixer] Added {npm_file} for npm error context")

        # CRITICAL: Check for esbuild export mismatch errors
        # Pattern 1: No matching export in "file.tsx" for import "ExportName"
        # Debug: Log if we see the export mismatch indicator
        if 'matching export' in output_lower or 'no matching export' in output_lower:
            logger.info(f"[SimpleFixer] Detected 'matching export' in output - checking for mismatch pattern")
        export_mismatch_pattern = re.compile(
            r'No matching export in ["\']([^"\']+)["\'] for import ["\']([^"\']+)["\']',
            re.IGNORECASE
        )
        export_mismatches = export_mismatch_pattern.findall(output)
        logger.info(f"[SimpleFixer] Export mismatch pattern search: found {len(export_mismatches)} matches")

        # Pattern 2: Extract files from esbuild file:line:column format (e.g., src/hooks/useAuth.ts:2:9)
        # This catches errors even when full message isn't passed
        esbuild_file_pattern = re.compile(
            r'(?:^|\s)([a-zA-Z0-9_\-./]+\.(?:tsx?|jsx?|vue|svelte)):(\d+):(\d+)',
            re.MULTILINE
        )
        esbuild_files = esbuild_file_pattern.findall(output)
        if esbuild_files:
            logger.info(f"[SimpleFixer] Found {len(esbuild_files)} files from esbuild errors")
            for file_path, line, col in esbuild_files[:5]:
                normalized_path = file_path
                if not normalized_path.startswith('frontend/'):
                    frontend_path = f"frontend/{file_path}"
                    if (project_path / frontend_path).exists():
                        normalized_path = frontend_path
                if normalized_path not in mentioned:
                    mentioned.insert(0, normalized_path)
                    logger.info(f"[SimpleFixer] Added {normalized_path} from esbuild error (line {line})")

        # Pattern 3: Extract import paths from error messages (e.g., from '../contexts/AuthContext')
        import_path_pattern = re.compile(
            r"from\s+['\"]([^'\"]+)['\"]",
            re.IGNORECASE
        )
        import_paths = import_path_pattern.findall(output)
        for imp_path in import_paths[:5]:
            # Convert relative import to file path
            if imp_path.startswith('.'):
                # Try common extensions
                for ext in ['.tsx', '.ts', '.jsx', '.js', '/index.tsx', '/index.ts']:
                    # Normalize path (remove leading ./ or ../)
                    clean_path = imp_path.lstrip('.').lstrip('/')
                    test_path = f"frontend/src/{clean_path}{ext}"
                    if (project_path / test_path).exists() and test_path not in mentioned:
                        mentioned.insert(0, test_path)
                        logger.info(f"[SimpleFixer] Added {test_path} from import path")
                        break
        if export_mismatches:
            logger.info(f"[SimpleFixer] Found {len(export_mismatches)} export mismatch errors")
            for source_file, export_name in export_mismatches:
                # Normalize path - handle both src/ and frontend/src/ paths
                normalized_path = source_file
                if not normalized_path.startswith('frontend/'):
                    # Try with frontend/ prefix for multi-folder projects
                    frontend_path = f"frontend/{source_file}"
                    if (project_path / frontend_path).exists():
                        normalized_path = frontend_path

                if normalized_path not in mentioned:
                    mentioned.insert(0, normalized_path)  # Prioritize these files at the beginning
                    logger.info(f"[SimpleFixer] Added {normalized_path} (missing export '{export_name}')")

            # Add export mismatch info to the output for AI context - this is CRITICAL
            export_info = "\n\n[EXPORT MISMATCH ERRORS - FIX THESE FIRST!]\n"
            for source_file, export_name in export_mismatches:
                export_info += f"- File '{source_file}' does NOT export '{export_name}'\n"
                export_info += f"  FIX: Add 'export {{ {export_name} }}' or 'export const {export_name} = ...' to the file\n"
            export_info += "[END EXPORT MISMATCH ERRORS]\n"
            output = output + export_info
            logger.info(f"[SimpleFixer] Added export mismatch info to context: {len(export_mismatches)} errors")

        # CRITICAL: Detect Vite/esbuild scan errors - these need source files searched
        # Error like "Failed to scan for dependencies from entries" means bad import in code
        vite_scan_indicators = [
            'failed to scan for dependencies',
            'could not resolve',
            'failed to resolve import',
            'cannot find module',
            'module not found',
            'failed to load',
            'pre-transform error',
        ]
        is_vite_scan_error = any(indicator in output_lower for indicator in vite_scan_indicators)  # Update the pre-initialized variable

        if is_vite_scan_error:
            logger.info(f"[SimpleFixer] Detected Vite/esbuild scan error - searching source files")
            # Search for source files that might have bad imports
            source_patterns = [
                "src/**/*.tsx", "src/**/*.ts", "src/**/*.jsx", "src/**/*.js",
                "frontend/src/**/*.tsx", "frontend/src/**/*.ts",
                "frontend/src/**/*.jsx", "frontend/src/**/*.js",
                "*.tsx", "*.ts", "*.jsx", "*.js",
            ]
            import glob as glob_module
            source_files_found = []
            for pattern in source_patterns:
                matches = list(project_path.glob(pattern))
                for match in matches[:20]:  # Limit to first 20 per pattern
                    rel_path = str(match.relative_to(project_path)).replace("\\", "/")
                    if rel_path not in mentioned and rel_path not in source_files_found:
                        # Skip node_modules and common non-source dirs
                        if 'node_modules' not in rel_path and 'dist' not in rel_path:
                            source_files_found.append(rel_path)

            # Add source files to mentioned (limit to 10 most relevant)
            for src_file in source_files_found[:10]:
                if src_file not in mentioned:
                    mentioned.append(src_file)
                    logger.info(f"[SimpleFixer] Added {src_file} for Vite scan error")

            # CRITICAL: Analyze imports vs dependencies to find missing packages
            # This helps the AI know exactly which import is problematic
            missing_imports = self._find_missing_imports(project_path, source_files_found)
            if missing_imports:
                # Add missing imports info to the output for AI context
                missing_info = "\n\n[IMPORT ANALYSIS - MISSING DEPENDENCIES]\n"
                for imp in missing_imports[:5]:  # Limit to 5 most relevant
                    missing_info += f"- Import '{imp['import']}' in {imp['file']} is NOT in package.json\n"
                missing_info += "[END IMPORT ANALYSIS]\n"
                output = output + missing_info
                logger.info(f"[SimpleFixer] Found {len(missing_imports)} missing imports: {[m['import'] for m in missing_imports[:5]]}")

                # CRITICAL: Prioritize files with missing imports - add them first with FULL content
                # so the AI can see and fix the import statements
                for imp in missing_imports[:3]:  # Top 3 files with bad imports
                    bad_file = imp['file']
                    if bad_file not in mentioned:
                        mentioned.insert(0, bad_file)  # Add at the beginning
                        logger.info(f"[SimpleFixer] Prioritized {bad_file} (has missing import)")

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
                        # Large file without line number - check if this file has missing imports
                        lines = content.split('\n')
                        has_missing_import = any(
                            m.get('file') == path_fragment
                            for m in missing_imports
                        ) if missing_imports else False

                        if has_missing_import or is_vite_scan_error:
                            # For import errors, send FIRST 80 lines (imports) + LAST 40 lines
                            first_80 = '\n'.join(lines[:80]) if len(lines) > 80 else content
                            last_40 = '\n'.join(lines[-40:]) if len(lines) > 120 else ''
                            if last_40:
                                files[path_fragment] = f"""[PARTIAL FILE - SHOWING FIRST 80 + LAST 40 LINES of {total_lines} total]
[⚠️ USE str_replace TOOL ONLY - file is larger than shown]
{first_80}

... [MIDDLE SECTION OMITTED - {len(lines) - 120} lines] ...

{last_40}
[END PARTIAL FILE]"""
                            else:
                                files[path_fragment] = f"""[PARTIAL FILE - FIRST 80 LINES of {total_lines} total]
[⚠️ USE str_replace TOOL ONLY - file is larger than shown]
{first_80}
[END PARTIAL FILE]"""
                            logger.info(f"[SimpleFixer] Sent first 80 + last 40 lines of {path_fragment} (import error)")
                        else:
                            # For other errors, send last 100 lines (where syntax errors usually are)
                            last_100 = '\n'.join(lines[-100:]) if len(lines) > 100 else content
                            files[path_fragment] = f"""[PARTIAL FILE - SHOWING LAST {min(100, len(lines))} LINES of {total_lines} total]
[⚠️ USE str_replace TOOL ONLY - file is larger than shown]
{last_100}
[END PARTIAL FILE]"""
                            logger.info(f"[SimpleFixer] Sent last 100 lines of {path_fragment} (no line number available)")
                    continue
                except (IOError, OSError, UnicodeDecodeError) as e:
                    logger.debug(f"Could not read file {path_fragment}: {e}")

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
                    except (IOError, OSError, UnicodeDecodeError) as e:
                        logger.debug(f"Could not read glob matched file {p}: {e}")
                    break

        total_chars = sum(len(v) for v in files.values())
        logger.info(f"[SimpleFixer] Gathered {len(files)} context files (~{total_chars} chars, optimized)")
        # Return both files and modified output (output may have export mismatch info added)
        return files, output

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

    async def _try_deterministic_react_import_fix(self, project_path: Path) -> Optional[SimpleFixResult]:
        """
        Proactively fix missing React import in main.tsx (no AI call needed).

        This fixes the common "React is not defined" browser error that happens
        when main.tsx uses React.StrictMode without importing React.

        Returns SimpleFixResult if fixed, None if no fix needed.
        """
        # Check common main.tsx locations
        main_tsx_paths = [
            project_path / "src" / "main.tsx",
            project_path / "frontend" / "src" / "main.tsx",
            project_path / "client" / "src" / "main.tsx",
        ]

        files_modified = []
        sync_failures = []  # Track S3 sync failures

        for main_path in main_tsx_paths:
            if not main_path.exists():
                continue

            try:
                content = main_path.read_text(encoding='utf-8')

                # Check if file uses React (React.StrictMode, React.createElement, etc.)
                uses_react = 'React.' in content or '<React.' in content

                # Check if React is already imported
                has_react_import = bool(re.search(r'''import\s+(?:\*\s+as\s+)?React\s+from\s+['"]react['"]''', content))

                if uses_react and not has_react_import:
                    logger.info(f"[SimpleFixer] Found main.tsx using React without import: {main_path}")

                    # Add React import at the top
                    # Check if there's already a react-dom import to add after it
                    if "import ReactDOM from 'react-dom/client'" in content:
                        new_content = content.replace(
                            "import ReactDOM from 'react-dom/client'",
                            "import React from 'react'\nimport ReactDOM from 'react-dom/client'"
                        )
                    elif 'import ReactDOM from "react-dom/client"' in content:
                        new_content = content.replace(
                            'import ReactDOM from "react-dom/client"',
                            "import React from 'react'\nimport ReactDOM from \"react-dom/client\""
                        )
                    else:
                        # Just add at the very beginning
                        new_content = "import React from 'react'\n" + content

                    # Write fixed content
                    main_path.write_text(new_content, encoding='utf-8')
                    rel_path = str(main_path.relative_to(project_path))
                    files_modified.append(rel_path)
                    logger.info(f"[SimpleFixer] Added missing React import to {rel_path}")

                    # Sync to S3 and track failures
                    path_parts = str(project_path).replace("\\", "/").split("/")
                    project_id = path_parts[-1] if path_parts else None
                    if project_id:
                        sync_ok = await self._sync_to_s3(project_id, rel_path, new_content)
                        if not sync_ok:
                            sync_failures.append(rel_path)

            except Exception as e:
                logger.warning(f"[SimpleFixer] Error checking {main_path}: {e}")
                continue

        if files_modified:
            message = f"Added missing 'import React from react' to {', '.join(files_modified)}"
            if sync_failures:
                message += f" [WARNING: {len(sync_failures)} sync failure(s)]"
            return SimpleFixResult(
                success=True,
                files_modified=files_modified,
                message=message,
                patches_applied=len(files_modified)
            )

        return None

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
        sync_failures = []  # Track S3 sync failures

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

                    # Sync to S3 and track failures
                    path_parts = str(project_path).replace("\\", "/").split("/")
                    project_id = path_parts[-1] if path_parts else None
                    if project_id:
                        sync_ok = await self._sync_to_s3(project_id, rel_path, content)
                        if not sync_ok:
                            sync_failures.append(rel_path)

            except Exception as e:
                logger.warning(f"[SimpleFixer] Error fixing {css_path}: {e}")
                continue

        if files_modified:
            message = f"Replaced @apply {missing_class} with {replacement}"
            if sync_failures:
                message += f" [WARNING: {len(sync_failures)} sync failure(s)]"
            return SimpleFixResult(
                success=True,
                files_modified=files_modified,
                message=message,
                patches_applied=len(files_modified)
            )

        return None

    async def _try_deterministic_export_mismatch_fix(
        self,
        project_path: Path,
        output: str
    ) -> Optional[SimpleFixResult]:
        """
        Deterministically fix export/import mismatches (no AI needed).

        This fixes the common error:
        - "No matching export in 'X.tsx' for import 'default'"

        When components use named exports (export const X = ...) but
        imports expect default exports (import X from ...).

        The fix: Add 'export default ComponentName;' at the end of the file.
        """
        # Pattern: No matching export in "path" for import "default"
        export_error_pattern = r'No matching export in ["\']([^"\']+)["\'] for import ["\']default["\']'
        matches = re.findall(export_error_pattern, output)

        if not matches:
            return None

        logger.info(f"[SimpleFixer] Found {len(matches)} export mismatch errors")

        files_modified = []
        sync_failures = []  # Track S3 sync failures
        unique_files = set(matches)

        for rel_path in unique_files:
            try:
                # Handle paths like src/components/UI/Button.tsx
                file_path = project_path / rel_path

                # Also try with frontend/ prefix for full-stack projects
                if not file_path.exists():
                    file_path = project_path / "frontend" / rel_path
                if not file_path.exists():
                    logger.warning(f"[SimpleFixer] File not found: {rel_path}")
                    continue

                content = file_path.read_text(encoding='utf-8')

                # Check if file already has a default export
                if re.search(r'export\s+default\s+', content):
                    logger.info(f"[SimpleFixer] File already has default export: {rel_path}")
                    continue

                # Find the component name from named exports
                # Pattern: export const ComponentName = ...
                # or: export function ComponentName(...
                # or: export const ComponentName: React.FC = ...
                component_match = re.search(
                    r'export\s+(?:const|function|class)\s+([A-Z][a-zA-Z0-9]*)',
                    content
                )

                if not component_match:
                    logger.warning(f"[SimpleFixer] Could not find component name in {rel_path}")
                    continue

                component_name = component_match.group(1)
                logger.info(f"[SimpleFixer] Found component '{component_name}' in {rel_path}")

                # Add default export at the end of the file
                # Check if file ends with a newline
                if content.endswith('\n'):
                    new_content = content + f"\nexport default {component_name};\n"
                else:
                    new_content = content + f"\n\nexport default {component_name};\n"

                # Write fixed content
                file_path.write_text(new_content, encoding='utf-8')

                # Determine the correct relative path for storage
                try:
                    final_rel_path = str(file_path.relative_to(project_path))
                except ValueError:
                    final_rel_path = rel_path

                files_modified.append(final_rel_path)
                logger.info(f"[SimpleFixer] Added 'export default {component_name}' to {final_rel_path}")

                # Sync to S3 and track failures
                path_parts = str(project_path).replace("\\", "/").split("/")
                project_id = path_parts[-1] if path_parts else None
                if project_id:
                    sync_ok = await self._sync_to_s3(project_id, final_rel_path, new_content)
                    if not sync_ok:
                        sync_failures.append(final_rel_path)

            except Exception as e:
                logger.warning(f"[SimpleFixer] Error fixing {rel_path}: {e}")
                continue

        if files_modified:
            message = f"Added default exports to {len(files_modified)} component(s)"
            if sync_failures:
                message += f" [WARNING: {len(sync_failures)} sync failure(s)]"
            return SimpleFixResult(
                success=True,
                files_modified=files_modified,
                message=message,
                patches_applied=len(files_modified)
            )

        return None

    async def _try_deterministic_config_file_fix(
        self,
        project_path: Path,
        error_text: str,
        project_id: Optional[str] = None
    ) -> Optional[SimpleFixResult]:
        """
        Deterministically fix missing config/entry files (no AI needed).

        Handles common missing files:
        - tsconfig.node.json (Vite TypeScript projects)
        - postcss.config.js/cjs (Tailwind CSS projects)
        - index.html (Vite entry point)
        - src/main.tsx (React entry)
        - src/App.tsx (React main component)
        """
        # Config file templates
        CONFIG_TEMPLATES = {
            "tsconfig.node.json": '''{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}''',
            "postcss.config.js": '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}''',
            "postcss.config.cjs": '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}''',
            "tailwind.config.js": '''/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}''',
            "index.html": '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>''',
            "src/main.tsx": '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)''',
            "src/App.tsx": '''function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <h1 className="text-3xl font-bold text-gray-800">Hello World</h1>
    </div>
  )
}

export default App''',
            "src/index.css": '''@tailwind base;
@tailwind components;
@tailwind utilities;''',
        }

        # Patterns to detect missing files
        config_patterns = [
            # tsconfig.node.json
            (r'ENOENT.*tsconfig\.node\.json', 'tsconfig.node.json'),
            (r'parsing.*tsconfig\.node\.json.*failed', 'tsconfig.node.json'),
            (r'Cannot find.*tsconfig\.node\.json', 'tsconfig.node.json'),
            # postcss.config
            (r'ENOENT.*postcss\.config', 'postcss.config.js'),
            (r'Cannot find.*postcss\.config', 'postcss.config.js'),
            (r'Loading PostCSS.*failed', 'postcss.config.js'),
            # tailwind.config
            (r'ENOENT.*tailwind\.config', 'tailwind.config.js'),
            (r'Cannot find.*tailwindcss', 'tailwind.config.js'),
            # index.html
            (r'ENOENT.*index\.html', 'index.html'),
            (r'Could not resolve.*index\.html', 'index.html'),
            (r'Failed to scan for dependencies.*index\.html', 'index.html'),
            # main.tsx
            (r'ENOENT.*main\.tsx', 'src/main.tsx'),
            (r'Cannot find module.*[\'"]\.\/main[\'"]', 'src/main.tsx'),
            (r'Failed to resolve.*main\.tsx', 'src/main.tsx'),
            # App.tsx
            (r'ENOENT.*App\.tsx', 'src/App.tsx'),
            (r'Cannot find module.*[\'"]\.\/App[\'"]', 'src/App.tsx'),
            # index.css
            (r'ENOENT.*index\.css', 'src/index.css'),
            (r'Cannot find.*index\.css', 'src/index.css'),
        ]

        files_created = []
        logger.info(f"[SimpleFixer] Checking deterministic config fix for error: {error_text[:200]}...")

        for pattern, config_file in config_patterns:
            if re.search(pattern, error_text, re.IGNORECASE):
                logger.info(f"[SimpleFixer] ✓ Pattern matched: {pattern} -> {config_file}")
                template = CONFIG_TEMPLATES.get(config_file)
                if not template:
                    logger.warning(f"[SimpleFixer] No template for {config_file}")
                    continue

                # Determine if file goes in root or has its own path (e.g., src/main.tsx)
                if '/' in config_file:
                    # File has directory path (e.g., src/main.tsx)
                    prefixes = ['', 'frontend/']
                else:
                    # Config file in root
                    prefixes = ['', 'frontend/']

                for prefix in prefixes:
                    file_path = project_path / prefix / config_file
                    if file_path.exists():
                        logger.info(f"[SimpleFixer] File already exists: {file_path}")
                        continue  # File exists, skip

                    # For non-root files, check if this is a valid project directory
                    if prefix:
                        pkg_json = project_path / prefix / 'package.json'
                        if not pkg_json.exists():
                            continue  # Not a valid project root

                    try:
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        file_path.write_text(template, encoding='utf-8')
                        rel_path = f"{prefix}{config_file}" if prefix else config_file
                        files_created.append(rel_path)
                        logger.info(f"[SimpleFixer] ✓ Created missing file: {rel_path}")

                        # Note: S3 sync will be done by errors.py after this returns
                        # The project_id extraction here was incorrect, so we skip it
                        # errors.py has the correct project_id and handles sync properly

                        break  # Only create in one location

                    except Exception as e:
                        logger.error(f"[SimpleFixer] ✗ Error creating {config_file}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue

        if files_created:
            logger.info(f"[SimpleFixer] ✓ Deterministic fix created {len(files_created)} file(s): {files_created}")
            return SimpleFixResult(
                success=True,
                files_modified=files_created,
                message=f"Created missing file(s): {', '.join(files_created)}",
                patches_applied=len(files_created)
            )

        logger.info(f"[SimpleFixer] No deterministic config fix matched")
        return None

    async def _try_deterministic_port_fix(
        self,
        project_path: Path,
        error_text: str,
        project_id: Optional[str] = None
    ) -> Optional[SimpleFixResult]:
        """
        Deterministically fix port conflict errors (no AI needed).

        Handles EADDRINUSE errors by changing the port in vite.config.ts/js.
        Tries ports 5174, 5175, 5176, etc. until finding an available one.
        """
        # Port conflict patterns
        port_patterns = [
            r'EADDRINUSE.*:(\d+)',
            r'port (\d+) is already in use',
            r'address already in use.*:(\d+)',
            r'listen EADDRINUSE.*:(\d+)',
            r'Error: listen EADDRINUSE',
        ]

        # Check if this is a port conflict error
        conflicting_port = None
        for pattern in port_patterns:
            match = re.search(pattern, error_text, re.IGNORECASE)
            if match:
                if match.groups():
                    conflicting_port = int(match.group(1))
                else:
                    conflicting_port = 5173  # Default Vite port
                logger.info(f"[SimpleFixer] Port conflict detected: {conflicting_port}")
                break

        if not conflicting_port:
            return None

        # Find vite.config.ts or vite.config.js
        vite_config_paths = [
            project_path / 'vite.config.ts',
            project_path / 'vite.config.js',
            project_path / 'vite.config.mjs',
            project_path / 'frontend' / 'vite.config.ts',
            project_path / 'frontend' / 'vite.config.js',
            project_path / 'frontend' / 'vite.config.mjs',
        ]

        vite_config = None
        for path in vite_config_paths:
            if path.exists():
                vite_config = path
                break

        if not vite_config:
            logger.warning(f"[SimpleFixer] Port conflict detected but no vite.config found")
            return None

        try:
            content = vite_config.read_text(encoding='utf-8')
            original_content = content

            # Calculate new port (increment by 1)
            new_port = conflicting_port + 1
            if new_port > 5180:
                new_port = 5174  # Reset to 5174 if we've gone too high

            # Check if server config already exists
            if 'server:' in content or 'server :' in content:
                # Server config exists, update the port
                # Pattern 1: port: 5173
                content = re.sub(
                    r'port\s*:\s*\d+',
                    f'port: {new_port}',
                    content
                )
                # If no port was in server config, add it
                if f'port: {new_port}' not in content and 'port:' not in content:
                    # Add port to existing server config
                    content = re.sub(
                        r'(server\s*:\s*\{)',
                        f'\\1\n    port: {new_port},',
                        content
                    )
            else:
                # No server config, add it
                # Look for defineConfig({ and add server config after plugins
                if 'plugins:' in content:
                    content = re.sub(
                        r'(plugins\s*:\s*\[[^\]]*\]\s*,?)',
                        f'''\\1
  server: {{
    port: {new_port},
    host: true,
  }},''',
                        content,
                        count=1
                    )
                else:
                    # Add before closing of defineConfig
                    content = re.sub(
                        r'(defineConfig\s*\(\s*\{)',
                        f'''\\1
  server: {{
    port: {new_port},
    host: true,
  }},''',
                        content,
                        count=1
                    )

            if content != original_content:
                vite_config.write_text(content, encoding='utf-8')
                rel_path = str(vite_config.relative_to(project_path))
                logger.info(f"[SimpleFixer] ✓ Port conflict fixed: {conflicting_port} -> {new_port} in {rel_path}")

                return SimpleFixResult(
                    success=True,
                    files_modified=[rel_path],
                    message=f"Port conflict fixed: changed port from {conflicting_port} to {new_port}",
                    patches_applied=1
                )
            else:
                logger.warning(f"[SimpleFixer] Could not modify vite.config for port fix")
                return None

        except Exception as e:
            logger.error(f"[SimpleFixer] Error fixing port conflict: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
        1. TRY DETERMINISTIC FIX FIRST (fast, free) - React import, Tailwind CSS errors, config files
        2. Classify error complexity for model selection
        3. Gather SMALLER context (only error-mentioned files + key configs)
        4. Send to AI with selected model
        5. Apply fixes with max 5 iterations
        """
        try:
            # =================================================================
            # STEP 0a: Try deterministic React import fix (fast, free, no AI)
            # =================================================================
            react_fix_result = await self._try_deterministic_react_import_fix(project_path)
            if react_fix_result:
                logger.info(f"[SimpleFixer] Deterministic React import fix applied - skipping AI")
                return react_fix_result

            # =================================================================
            # STEP 0b: Try deterministic CSS fix (fast, free, no API call)
            # =================================================================
            deterministic_result = await self._try_deterministic_css_fix(project_path, output)
            if deterministic_result:
                logger.info(f"[SimpleFixer] Deterministic CSS fix applied - skipping AI")
                return deterministic_result

            # =================================================================
            # STEP 0c: Try deterministic export mismatch fix (fast, free, no AI)
            # =================================================================
            export_fix_result = await self._try_deterministic_export_mismatch_fix(project_path, output)
            if export_fix_result:
                logger.info(f"[SimpleFixer] Deterministic export fix applied - skipping AI")
                return export_fix_result

            # =================================================================
            # STEP 0d: Try deterministic config file fix (fast, free, no AI)
            # Handles: tsconfig.node.json, postcss.config.js, etc.
            # =================================================================
            config_fix_result = await self._try_deterministic_config_file_fix(project_path, output)
            if config_fix_result:
                logger.info(f"[SimpleFixer] Deterministic config file fix applied - skipping AI")
                return config_fix_result

            # =================================================================
            # STEP 0e: Try deterministic port conflict fix (fast, free, no AI)
            # =================================================================
            port_fix_result = await self._try_deterministic_port_fix(project_path, output)
            if port_fix_result:
                logger.info(f"[SimpleFixer] Deterministic port fix applied - skipping AI")
                return port_fix_result

            # COST OPTIMIZATION #2: Classify error for model selection
            errors = [{"message": output[-2000:], "source": "terminal"}]
            complexity = self._classify_error_complexity(errors, output)
            model = self._select_model(complexity)

            # COST OPTIMIZATION #3: Gather SMALLER context
            # Also returns modified output with export mismatch info if detected
            context_files, enriched_output = await self._gather_context_optimized(project_path, output, errors)

            # COST OPTIMIZATION #3: Smaller context window based on complexity
            # Use enriched_output which may contain export mismatch info
            context_limit = 6000 if complexity == ErrorComplexity.SIMPLE else 10000
            user_message = f"""Command: {command}
Exit code: {exit_code}

Full output:
```
{enriched_output[-context_limit:]}
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
            # Allow up to 5 iterations for complex fixes
            max_iterations = 5

            while response.stop_reason == "tool_use" and iterations < max_iterations:
                iterations += 1
                logger.info(f"[SimpleFixer] Terminal fix iteration {iterations}/{max_iterations}")

                # Execute tools
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Note: project_id=None for terminal fix path - S3 sync will be skipped
                        result = await self._execute_tool(
                            project_path,
                            block.name,
                            block.input,
                            project_id=None
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
                except (IOError, OSError, UnicodeDecodeError) as e:
                    logger.debug(f"Could not read config file {rel_path}: {e}")

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
                    except (IOError, OSError, UnicodeDecodeError, ValueError) as e:
                        logger.debug(f"Could not read error-mentioned file {p}: {e}")
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

    def _validate_fixed_content(self, file_path: str, content: str) -> Tuple[bool, str]:
        """
        Gap #13: Validate fixed file content before S3 sync.

        Returns (is_valid, error_message).
        """
        # Check for empty content
        if not content or not content.strip():
            return False, "Empty or whitespace-only content"

        # Validate JSON files
        if file_path.endswith('.json'):
            try:
                import json
                json.loads(content)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {str(e)[:100]}"

        # Validate JS/TS/TSX/JSX files - basic syntax check
        if file_path.endswith(('.js', '.ts', '.tsx', '.jsx', '.mjs')):
            # Check for obvious truncation or corruption
            open_braces = content.count('{')
            close_braces = content.count('}')
            open_parens = content.count('(')
            close_parens = content.count(')')

            # Allow some tolerance (2) for template literals, strings, etc.
            if abs(open_braces - close_braces) > 2:
                return False, f"Unbalanced braces: {open_braces} open, {close_braces} close"
            if abs(open_parens - close_parens) > 2:
                return False, f"Unbalanced parentheses: {open_parens} open, {close_parens} close"

        # Validate YAML files
        if file_path.endswith(('.yml', '.yaml')):
            try:
                import yaml
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                return False, f"Invalid YAML: {str(e)[:100]}"

        return True, ""

    async def _sync_to_s3(self, project_id: str, file_path: str, content: str, max_retries: int = 3) -> bool:
        """
        Sync fixed file to BOTH S3 AND database with retries.

        CRITICAL: Uses save_to_database() which:
        1. Uploads to S3 with content-addressed key (hash-based)
        2. Updates database record with new s3_key

        Returns True if sync succeeded, False otherwise.
        This allows callers to track sync failures and handle appropriately.
        """
        import asyncio
        from app.services.unified_storage import unified_storage

        # Gap #13: Validate content before syncing
        is_valid, validation_error = self._validate_fixed_content(file_path, content)
        if not is_valid:
            logger.warning(f"[SimpleFixer] ✗ Content validation failed for {file_path}: {validation_error}")
            return False

        last_error = None
        for attempt in range(max_retries):
            try:
                # Use save_to_database which properly updates BOTH S3 and database
                success = await unified_storage.save_to_database(
                    project_id=project_id,
                    file_path=file_path,
                    content=content
                )

                if success:
                    logger.info(f"[SimpleFixer] ✓ Persisted fix to S3+DB: {file_path} (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"[SimpleFixer] ✗ save_to_database returned False for: {file_path}")
                    last_error = "save_to_database returned False"

            except Exception as e:
                last_error = str(e)
                logger.warning(f"[SimpleFixer] ✗ S3 sync attempt {attempt + 1}/{max_retries} failed for {file_path}: {e}")

            # Exponential backoff before retry
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))

        # All retries failed
        logger.error(f"[SimpleFixer] ✗ CRITICAL: Failed to sync fix to S3+DB after {max_retries} attempts: {file_path} - {last_error}")
        return False

    async def _execute_tool(
        self,
        project_path: Path,
        tool_name: str,
        tool_input: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> str:
        """Execute a tool and return result"""
        try:
            path = tool_input.get("path", "")

            # CRITICAL FIX: AI sometimes returns container absolute paths like /app/frontend/file.ts
            # These need to be converted to relative paths for local filesystem operations
            # Use settings.SANDBOX_PATH consistently - supports both /tmp and /efs paths
            sandbox_base = settings.SANDBOX_PATH
            if path.startswith("/app/"):
                original_path = path
                path = path[5:]  # Remove "/app/" prefix
                logger.info(f"[SimpleFixer] Normalized container path: '{original_path}' -> '{path}'")
            elif path.startswith(sandbox_base + "/") or path.startswith("/efs/sandbox/workspace/") or path.startswith("/tmp/sandbox/workspace/"):
                # Remote sandbox absolute path - extract just the relative path
                # Path format: {sandbox_base}/{user_id}/{project_id}/{relative_path}
                original_path = path
                path_parts = path.split("/")
                # Find relative path after workspace (then user_id, project_id)
                if "workspace" in path_parts:
                    workspace_idx = path_parts.index("workspace")
                    # After workspace: user_id, project_id, then relative path
                    if len(path_parts) > workspace_idx + 3:
                        path = "/".join(path_parts[workspace_idx + 3:])
                        logger.info(f"[SimpleFixer] Extracted relative path from sandbox: '{original_path}' -> '{path}'")
                    else:
                        path = path_parts[-1] if path_parts else path
                        logger.warning(f"[SimpleFixer] Could not parse sandbox path, using filename: '{original_path}' -> '{path}'")
            elif path.startswith("/"):
                # Other absolute path - strip leading slash
                original_path = path
                path = path.lstrip("/")
                logger.info(f"[SimpleFixer] Stripped leading slash: '{original_path}' -> '{path}'")

            # NORMALIZE PATH: Apply project structure rules (fullstack -> frontend/ or backend/)
            # This ensures files go to correct folders based on project type
            if project_id:
                # Try to extract user_id from project_path (format: {sandbox_base}/{user_id}/{project_id})
                try:
                    path_parts = str(project_path).split("/")
                    if "workspace" in path_parts:
                        workspace_idx = path_parts.index("workspace")
                        if len(path_parts) > workspace_idx + 1:
                            user_id = path_parts[workspace_idx + 1]
                            original_path = path
                            path = unified_file_manager.normalize_path(path, project_id, user_id)
                            if path != original_path:
                                logger.info(f"[SimpleFixer] Normalized for project structure: '{original_path}' -> '{path}'")
                except Exception as e:
                    logger.warning(f"[SimpleFixer] Could not normalize path: {e}")

            # VALIDATION: Prevent creating files in new/unexpected directories
            # AI sometimes hallucinates paths like "app/tsconfig.node.json" instead of "tsconfig.node.json"
            if "/" in path or "\\" in path:
                dir_path = Path(path).parent
                full_dir_path = project_path / dir_path
                # Only allow creating files in existing directories OR standard Vite/React directories
                allowed_dirs = {"src", "public", "components", "pages", "hooks", "utils", "lib", "assets", "styles"}
                if not full_dir_path.exists() and str(dir_path) not in allowed_dirs:
                    # Check if this looks like a config file that should be at root
                    filename = Path(path).name
                    config_files = {"tsconfig.json", "tsconfig.node.json", "package.json", "vite.config.ts",
                                   "vite.config.js", "tailwind.config.js", "postcss.config.js", ".env"}
                    if filename in config_files:
                        # Fix the path - use root instead of nested directory
                        logger.warning(f"[SimpleFixer] Correcting path: '{path}' -> '{filename}' (config file should be at root)")
                        path = filename
                    else:
                        logger.warning(f"[SimpleFixer] Rejected create_file in non-existent directory: {path}")
                        return f"Error: Cannot create file in non-existent directory '{dir_path}'. Check the file path."

            full_path = project_path / path

            # Use the passed project_id directly - no need to extract from path
            # The project_id is passed in from fix_from_frontend which has the actual UUID
            # Old code tried to extract from path which fails for temp directories like /tmp/fixer_xxx

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

                # For JSON files, validate and re-serialize to remove duplicate keys
                if path.endswith('.json'):
                    try:
                        import json
                        parsed = json.loads(content)
                        content = json.dumps(parsed, indent=2, ensure_ascii=False) + '\n'
                        logger.info(f"[SimpleFixer] Validated JSON on create: {path}")
                    except json.JSONDecodeError as je:
                        logger.warning(f"[SimpleFixer] JSON validation failed for {path}: {je}")
                        # Try to fix trailing comma issues
                        import re
                        fixed_content = re.sub(r',(\s*[}\]])', r'\1', content)
                        try:
                            parsed = json.loads(fixed_content)
                            content = json.dumps(parsed, indent=2, ensure_ascii=False) + '\n'
                            logger.info(f"[SimpleFixer] Fixed JSON on create: {path}")
                        except json.JSONDecodeError:
                            logger.warning(f"[SimpleFixer] Could not fix JSON on create: {path}")

                # LAYER 1: Write to sandbox
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding='utf-8')
                logger.info(f"[SimpleFixer] Created file: {path} ({len(content)} chars)")

                # LAYER 2: Sync to S3 (with retry and failure tracking)
                sync_success = True
                if project_id:
                    sync_success = await self._sync_to_s3(project_id, path, content)

                if sync_success:
                    return f"Created {path} ({len(content)} chars)"
                else:
                    return f"Created {path} ({len(content)} chars) [WARNING: S3 sync failed - fix may be lost on restart]"

            elif tool_name == "str_replace":
                if not full_path.exists():
                    return f"Error: File {path} not found"
                content = full_path.read_text(encoding='utf-8')
                old_str = tool_input["old_str"]
                new_str = tool_input["new_str"]
                if old_str not in content:
                    return f"Error: String not found in {path}"
                new_content = content.replace(old_str, new_str, 1)

                # For JSON files, validate and re-serialize to remove duplicate keys
                if path.endswith('.json'):
                    try:
                        import json
                        parsed = json.loads(new_content)
                        new_content = json.dumps(parsed, indent=2, ensure_ascii=False) + '\n'
                        logger.info(f"[SimpleFixer] Validated JSON: {path}")
                    except json.JSONDecodeError as je:
                        logger.warning(f"[SimpleFixer] JSON validation failed for {path}: {je}")
                        # Try to fix trailing comma issues
                        import re
                        fixed_content = re.sub(r',(\s*[}\]])', r'\1', new_content)
                        try:
                            parsed = json.loads(fixed_content)
                            new_content = json.dumps(parsed, indent=2, ensure_ascii=False) + '\n'
                            logger.info(f"[SimpleFixer] Fixed JSON trailing commas: {path}")
                        except json.JSONDecodeError:
                            # Keep original content if still fails
                            logger.warning(f"[SimpleFixer] Could not fix JSON: {path}")

                # LAYER 1: Write to sandbox
                full_path.write_text(new_content, encoding='utf-8')
                logger.info(f"[SimpleFixer] Modified file: {path}")

                # LAYER 2: Sync to S3 (with retry and failure tracking)
                sync_success = True
                if project_id:
                    sync_success = await self._sync_to_s3(project_id, path, new_content)

                if sync_success:
                    return f"Replaced in {path}"
                else:
                    return f"Replaced in {path} [WARNING: S3 sync failed - fix may be lost on restart]"

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
