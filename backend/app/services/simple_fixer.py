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


# Simple system prompt - let AI be smart
SIMPLE_FIXER_PROMPT = """You are an expert developer fixing build/runtime errors.

You will receive:
1. Error source (terminal, browser, build, react, network, docker, etc.)
2. Error message and context
3. Relevant project files

Your job:
1. Analyze the error
2. Determine the root cause
3. Fix it by creating or modifying files

ERROR TYPES YOU HANDLE:
- Terminal/Build: npm errors, compilation errors, missing modules
- Browser: TypeError, ReferenceError, runtime JS errors
- React: Component errors, hook errors, render failures
- Vite/Webpack: HMR errors, plugin errors, build failures
- Network: CORS errors, API failures (fix server-side config)
- Docker: Container crashes, port conflicts

IMPORTANT RULES:
- If the output shows SUCCESS (build success, server started, etc.) - respond with "NO_FIX_NEEDED"
- Only fix ACTUAL errors, not warnings or info messages
- Be precise - fix the exact issue, don't over-engineer
- Create missing files if needed (like tsconfig.node.json)
- Fix import errors, syntax errors, missing dependencies
- For CORS errors, update backend CORS configuration
- For missing modules, check if import path is wrong

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
        - Single file mentioned
        - Missing import/module
        - Syntax error with clear location
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

        # Count files mentioned in errors
        files_mentioned = set()
        for err in errors:
            if err.get("file"):
                files_mentioned.add(err.get("file"))

        # SIMPLE patterns (use Haiku - 12x cheaper!)
        simple_patterns = [
            "cannot find module",
            "module not found",
            "import error",
            "syntaxerror",
            "unexpected token",
            "missing semicolon",
            "missing bracket",
            "missing import",
            "undefined variable",
            "is not defined",
            "typo",
            "expected",
            "enoent",
            "no such file",
        ]

        # Check if error matches simple pattern AND has clear location
        for pattern in simple_patterns:
            if pattern in error_msg:
                if has_file and len(files_mentioned) <= 2:
                    logger.info(f"[SimpleFixer] Classified as SIMPLE (pattern: {pattern}) - using Haiku")
                    return ErrorComplexity.SIMPLE

        # Multiple errors or files = more complex
        if len(errors) > 3 or len(files_mentioned) > 2:
            logger.info(f"[SimpleFixer] Classified as COMPLEX (errors={len(errors)}, files={len(files_mentioned)})")
            return ErrorComplexity.COMPLEX

        # Config file issues = moderate
        config_keywords = ["config", "tsconfig", "package.json", "pom.xml", "requirements", "gradle", "cargo"]
        if any(kw in error_msg for kw in config_keywords):
            logger.info(f"[SimpleFixer] Classified as MODERATE (config-related)")
            return ErrorComplexity.MODERATE

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

    async def _gather_context_optimized(self, project_path: Path, output: str, errors: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        COST OPTIMIZATION #3: Gather SMALLER context.

        Only include:
        1. Files explicitly mentioned in error messages
        2. 3-5 KEY config files (not 100+)
        """
        files = {}

        # KEY config files only (not the full 100+ list)
        key_configs = [
            "package.json",
            "tsconfig.json",
            "vite.config.ts",
            "vite.config.js",
            "pom.xml",
            "requirements.txt",
            "pyproject.toml",
            # Fullstack variants
            "frontend/package.json",
            "frontend/tsconfig.json",
            "backend/pom.xml",
            "backend/requirements.txt",
        ]

        for rel_path in key_configs:
            full_path = project_path / rel_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8')
                    if len(content) < 15000:  # Smaller limit
                        files[rel_path] = content
                except:
                    pass

        # Extract files mentioned in errors (most important!)
        for err in errors[:5]:
            file_path = err.get("file")
            if file_path:
                # Try to find the file
                full_path = project_path / file_path
                if full_path.exists():
                    try:
                        content = full_path.read_text(encoding='utf-8')
                        if len(content) < 15000:
                            files[file_path] = content
                    except:
                        pass

        # Extract files mentioned in error output
        path_pattern = r'[\w/\\.-]+\.(tsx?|jsx?|py|java|go|rs|json|xml)'
        mentioned = re.findall(path_pattern, output)

        for path_fragment in mentioned[:5]:  # Limit to 5 files
            for p in project_path.rglob(f"*{path_fragment}"):
                if p.is_file():
                    try:
                        rel = p.relative_to(project_path)
                        content = p.read_text(encoding='utf-8')
                        if len(content) < 15000:
                            files[str(rel)] = content
                    except:
                        pass
                    break

        logger.info(f"[SimpleFixer] Gathered {len(files)} context files (optimized)")
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
        1. Classify error complexity for model selection
        2. Gather SMALLER context (only error-mentioned files + key configs)
        3. Send to AI with selected model
        4. Apply fixes with max 5 iterations
        """
        try:
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

            if tool_name == "create_file":
                content = tool_input.get("content", "")

                # VALIDATION: Reject empty content
                if not content or not content.strip():
                    logger.warning(f"[SimpleFixer] Rejected create_file with empty content: {path}")
                    return f"Error: Cannot create file with empty content. Please provide the full file content."

                # FIX: Remove leading empty lines - content should start from first line
                # This fixes the issue where AI leaves first line blank
                content = content.lstrip('\n\r')

                # VALIDATION: Reject suspiciously short content (likely truncated)
                # Config files can be short, but source files should have meaningful content
                is_config = any(ext in path.lower() for ext in ['.json', '.yml', '.yaml', '.toml', '.xml', '.properties', '.env'])
                min_length = 10 if is_config else 50

                if len(content.strip()) < min_length and not is_config:
                    logger.warning(f"[SimpleFixer] Rejected create_file with suspiciously short content ({len(content)} chars): {path}")
                    return f"Error: Content too short ({len(content)} chars). This might be truncated. Please provide complete file content."

                # Ensure file ends with single newline (standard convention)
                content = content.rstrip() + '\n'

                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding='utf-8')
                logger.info(f"[SimpleFixer] Created file: {path} ({len(content)} chars)")
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
                full_path.write_text(new_content, encoding='utf-8')
                logger.info(f"[SimpleFixer] Modified file: {path}")
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
