"""
Terminal Error Auto-Fixer - Bolt.new Style

This module implements automatic terminal error detection and fixing:
1. Classify errors into known categories (Dependency, Port, Command, etc.)
2. Apply rule-based fixes for common errors (NO AI needed)
3. Escalate to AI only when rules fail
4. Re-execution loop with retry limits

Based on Bolt.new's approach:
- Trust exit codes, not AI confidence
- Rules before AI (cheap, fast fixes first)
- Minimal changes (small, reversible fixes)
- Deterministic + AI hybrid

Error Categories:
- dependency: npm/pip install errors, missing modules
- port: EADDRINUSE, port conflicts
- command: command not found, executable missing
- permission: EACCES, permission denied
- env: process.env.X undefined, missing env vars
- runtime: version mismatch, runtime errors
- syntax: parse errors, syntax issues
- file: ENOENT, missing files
"""

import re
import os
import json
import asyncio
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.core.logging_config import logger
from app.services.unified_file_manager import unified_file_manager


class ErrorCategory(Enum):
    """Terminal error categories"""
    DEPENDENCY = "dependency"
    PORT = "port"
    COMMAND = "command"
    PERMISSION = "permission"
    ENV = "env"
    RUNTIME = "runtime"
    SYNTAX = "syntax"
    FILE = "file"
    UNKNOWN = "unknown"


@dataclass
class TerminalError:
    """Parsed terminal error with context"""
    category: ErrorCategory
    raw_error: str
    root_cause: str
    affected_file: Optional[str] = None
    missing_module: Optional[str] = None
    port: Optional[int] = None
    command: Optional[str] = None
    confidence: float = 0.9
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TerminalFix:
    """A fix to apply for a terminal error"""
    fix_type: str  # "command", "file_edit", "env_set", "port_change"
    command: Optional[str] = None  # Shell command to run
    file_path: Optional[str] = None  # File to edit
    file_content: Optional[str] = None  # New content or patch
    env_var: Optional[str] = None  # Environment variable to set
    env_value: Optional[str] = None  # Value to set
    description: str = ""  # Human-readable description
    requires_ai: bool = False  # If AI is needed for this fix


class TerminalErrorClassifier:
    """
    Classifies terminal errors into known categories.
    Uses pattern matching - NO AI.
    """

    # Error patterns mapped to categories
    PATTERNS = {
        ErrorCategory.DEPENDENCY: [
            # NPM errors
            (r"Cannot find module ['\"](.+?)['\"]", "missing_npm_module"),
            (r"Module not found:.*['\"](.+?)['\"]", "missing_npm_module"),
            (r"npm ERR! code ERESOLVE", "npm_dependency_conflict"),
            (r"npm ERR! peer dep missing", "npm_peer_dep"),
            (r"npm ERR! code E404", "npm_package_not_found"),
            (r"\[postcss\] Cannot find module ['\"](.+?)['\"]", "missing_postcss_plugin"),
            # Python errors
            (r"ModuleNotFoundError: No module named ['\"](.+?)['\"]", "missing_python_module"),
            (r"ImportError: No module named (.+)", "missing_python_module"),
            (r"pip.*No matching distribution found for (.+)", "pip_package_not_found"),
            # esbuild/vite errors
            (r"Failed to resolve import ['\"](.+?)['\"]", "missing_import"),
            (r"Could not resolve ['\"](.+?)['\"]", "missing_import"),
        ],
        ErrorCategory.PORT: [
            (r"EADDRINUSE.*:(\d+)", "port_in_use"),
            (r"address already in use.*:(\d+)", "port_in_use"),
            (r"port (\d+) is already in use", "port_in_use"),
            (r"listen EADDRINUSE: address already in use :::(\d+)", "port_in_use"),
        ],
        ErrorCategory.COMMAND: [
            (r"command not found: (.+)", "command_not_found"),
            (r"'(.+)' is not recognized", "command_not_found"),
            (r"sh: (.+): not found", "command_not_found"),
            (r"bash: (.+): command not found", "command_not_found"),
        ],
        ErrorCategory.PERMISSION: [
            (r"EACCES: permission denied", "permission_denied"),
            (r"Permission denied", "permission_denied"),
            (r"EPERM: operation not permitted", "permission_denied"),
        ],
        ErrorCategory.ENV: [
            (r"process\.env\.(\w+) is undefined", "missing_env_var"),
            (r"Cannot read.*'(\w+)'.*undefined", "missing_env_var"),
            (r"env: (.+): No such file or directory", "missing_env_var"),
        ],
        ErrorCategory.FILE: [
            (r"ENOENT: no such file or directory.*['\"](.+?)['\"]", "file_not_found"),
            (r"Error: Cannot find module ['\"]\.\/(.+?)['\"]", "local_file_not_found"),
            (r"Failed to resolve import ['\"]\.\/(.+?)['\"].*Does the file exist", "local_file_not_found"),
            (r"parsing (.+) failed: Error: ENOENT", "config_file_missing"),
        ],
        ErrorCategory.SYNTAX: [
            (r"SyntaxError: (.+)", "syntax_error"),
            (r"Unexpected token (.+)", "syntax_error"),
            (r"Parse error: (.+)", "syntax_error"),
            (r"Expected (.+) but found (.+)", "syntax_error"),
        ],
        ErrorCategory.RUNTIME: [
            (r"ReferenceError: (.+) is not defined", "reference_error"),
            (r"TypeError: (.+)", "type_error"),
            (r"Error: (.+)", "generic_error"),
        ],
    }

    def classify(self, error_output: str) -> List[TerminalError]:
        """
        Classify terminal error output into known categories.
        Returns list of detected errors with their categories.
        """
        errors = []
        lines = error_output.split('\n')

        for category, patterns in self.PATTERNS.items():
            for pattern, error_type in patterns:
                matches = re.finditer(pattern, error_output, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    error = TerminalError(
                        category=category,
                        raw_error=match.group(0),
                        root_cause=error_type,
                        confidence=0.9
                    )

                    # Extract specific info based on error type
                    if error_type in ["missing_npm_module", "missing_postcss_plugin",
                                       "missing_import", "missing_python_module"]:
                        if match.groups():
                            error.missing_module = match.group(1)

                    elif error_type == "port_in_use":
                        if match.groups():
                            try:
                                error.port = int(match.group(1))
                            except ValueError:
                                pass

                    elif error_type in ["command_not_found"]:
                        if match.groups():
                            error.command = match.group(1)

                    elif error_type in ["file_not_found", "local_file_not_found", "config_file_missing"]:
                        if match.groups():
                            error.affected_file = match.group(1)

                    errors.append(error)

        # Deduplicate by root cause
        seen = set()
        unique_errors = []
        for error in errors:
            key = (error.category, error.root_cause, error.missing_module or error.affected_file or error.port)
            if key not in seen:
                seen.add(key)
                unique_errors.append(error)

        return unique_errors

    def get_primary_error(self, errors: List[TerminalError]) -> Optional[TerminalError]:
        """Get the most important error to fix first"""
        if not errors:
            return None

        # Priority order for fixing
        priority = {
            ErrorCategory.DEPENDENCY: 1,  # Fix dependencies first
            ErrorCategory.FILE: 2,  # Then missing files
            ErrorCategory.COMMAND: 3,
            ErrorCategory.PORT: 4,
            ErrorCategory.PERMISSION: 5,
            ErrorCategory.ENV: 6,
            ErrorCategory.SYNTAX: 7,
            ErrorCategory.RUNTIME: 8,
            ErrorCategory.UNKNOWN: 9,
        }

        return min(errors, key=lambda e: priority.get(e.category, 10))


class RuleBasedFixer:
    """
    Applies rule-based fixes for common terminal errors.
    NO AI involved - just deterministic heuristics.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def get_fix(self, error: TerminalError) -> Optional[TerminalFix]:
        """
        Get a fix for the error if a rule exists.
        Returns None if AI is needed.
        """
        if error.category == ErrorCategory.DEPENDENCY:
            return self._fix_dependency(error)
        elif error.category == ErrorCategory.PORT:
            return self._fix_port(error)
        elif error.category == ErrorCategory.COMMAND:
            return self._fix_command(error)
        elif error.category == ErrorCategory.PERMISSION:
            return self._fix_permission(error)
        elif error.category == ErrorCategory.FILE:
            return self._fix_file(error)
        elif error.category == ErrorCategory.ENV:
            return self._fix_env(error)

        # No rule for this error - needs AI
        return None

    def _fix_dependency(self, error: TerminalError) -> Optional[TerminalFix]:
        """Fix missing dependency errors"""
        if not error.missing_module:
            return None

        module = error.missing_module

        # Determine if NPM or Python
        if error.root_cause in ["missing_npm_module", "missing_postcss_plugin", "missing_import"]:
            # Check if it's a local import (starts with ./ or ../)
            if module.startswith('.') or module.startswith('/'):
                # Local file import - needs AI or file creation
                return TerminalFix(
                    fix_type="file_edit",
                    description=f"Create missing local module: {module}",
                    requires_ai=True
                )

            # Extract package name (handle scoped packages)
            if module.startswith('@'):
                # Scoped package like @tailwindcss/forms
                package = module
            else:
                # Regular package - get base name
                package = module.split('/')[0]

            # Check if package is in devDependencies list
            dev_packages = ['@tailwindcss/forms', '@tailwindcss/typography',
                           'tailwindcss', 'postcss', 'autoprefixer',
                           '@types/', 'typescript', 'eslint', 'prettier']
            is_dev = any(package.startswith(p) for p in dev_packages)

            flag = "--save-dev" if is_dev else "--save"

            return TerminalFix(
                fix_type="command",
                command=f"npm install {package} {flag}",
                description=f"Install missing npm package: {package}"
            )

        elif error.root_cause == "missing_python_module":
            return TerminalFix(
                fix_type="command",
                command=f"pip install {module}",
                description=f"Install missing Python package: {module}"
            )

        return None

    def _fix_port(self, error: TerminalError) -> Optional[TerminalFix]:
        """Fix port conflict errors"""
        if not error.port:
            return None

        # Option 1: Kill the process using the port (aggressive)
        # Option 2: Change to a different port (safer)

        # We'll generate a new port
        new_port = error.port + 1
        if new_port > 65000:
            new_port = 3000

        return TerminalFix(
            fix_type="port_change",
            description=f"Port {error.port} is in use. Use port {new_port} instead.",
            metadata={"old_port": error.port, "new_port": new_port}
        )

    def _fix_command(self, error: TerminalError) -> Optional[TerminalFix]:
        """Fix command not found errors"""
        if not error.command:
            return None

        cmd = error.command.strip()

        # Common command mappings
        command_fixes = {
            "node": "Install Node.js from https://nodejs.org",
            "npm": "Install Node.js from https://nodejs.org",
            "npx": "npm install -g npx",
            "python": "Install Python from https://python.org",
            "python3": "Install Python from https://python.org",
            "pip": "Install Python from https://python.org",
            "pip3": "Install Python from https://python.org",
            "docker": "Install Docker from https://docker.com",
            "git": "Install Git from https://git-scm.com",
            "curl": "Install curl (apt install curl / brew install curl)",
        }

        if cmd in command_fixes:
            return TerminalFix(
                fix_type="info",
                description=command_fixes[cmd]
            )

        # Try to install via npm globally if it's a common tool
        npm_tools = ['vite', 'next', 'create-react-app', 'typescript', 'ts-node', 'eslint', 'prettier']
        if cmd in npm_tools:
            return TerminalFix(
                fix_type="command",
                command=f"npm install -g {cmd}",
                description=f"Install {cmd} globally via npm"
            )

        return None

    def _fix_permission(self, error: TerminalError) -> Optional[TerminalFix]:
        """Fix permission errors"""
        if error.affected_file:
            return TerminalFix(
                fix_type="command",
                command=f"chmod +x {error.affected_file}",
                description=f"Make {error.affected_file} executable"
            )

        return TerminalFix(
            fix_type="info",
            description="Permission denied. Try running with sudo or check file permissions."
        )

    def _fix_file(self, error: TerminalError) -> Optional[TerminalFix]:
        """Fix missing file errors"""
        if not error.affected_file:
            return None

        file_path = error.affected_file

        # Common config files that can be auto-generated
        config_templates = {
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
            "postcss.config.js": '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}''',
            ".env": '''# Environment variables
NODE_ENV=development
''',
        }

        # Check if it's a known config file
        filename = Path(file_path).name
        if filename in config_templates:
            return TerminalFix(
                fix_type="file_edit",
                file_path=file_path,
                file_content=config_templates[filename],
                description=f"Create missing config file: {filename}"
            )

        # For other files, we need AI
        return TerminalFix(
            fix_type="file_edit",
            file_path=file_path,
            description=f"Create missing file: {file_path}",
            requires_ai=True
        )

    def _fix_env(self, error: TerminalError) -> Optional[TerminalFix]:
        """Fix missing environment variable errors"""
        # Just inform - we can't auto-set env vars
        return TerminalFix(
            fix_type="info",
            description=f"Missing environment variable. Check your .env file or environment settings."
        )


class TerminalErrorFixer:
    """
    Main terminal error fixer that combines classification and rule-based fixing.
    Orchestrates the fix flow and manages retry limits.
    """

    MAX_RETRIES = 3

    def __init__(self, project_path: Path, project_id: str, user_id: str = None):
        self.project_path = project_path
        self.project_id = project_id
        self.user_id = user_id
        self.classifier = TerminalErrorClassifier()
        self.rule_fixer = RuleBasedFixer(project_path)
        self.retry_count = 0
        self.fix_history: List[TerminalFix] = []

    async def analyze_and_fix(
        self,
        error_output: str,
        exit_code: int = 1,
        command: str = None
    ) -> Dict[str, Any]:
        """
        Analyze terminal error and attempt to fix it.

        Args:
            error_output: The stderr/stdout from failed command
            exit_code: The exit code from the command
            command: The command that failed

        Returns:
            Dict with:
                - fixed: bool - whether a fix was applied
                - fix_type: str - "rule" or "ai" or None
                - fix: TerminalFix - the fix applied
                - needs_ai: bool - if AI is needed
                - errors: List[TerminalError] - classified errors
                - retry_allowed: bool - if more retries are allowed
        """
        result = {
            "fixed": False,
            "fix_type": None,
            "fix": None,
            "needs_ai": False,
            "errors": [],
            "retry_allowed": self.retry_count < self.MAX_RETRIES,
            "retry_count": self.retry_count,
            "command": command,
        }

        # Check retry limit
        if self.retry_count >= self.MAX_RETRIES:
            logger.warning(f"[TerminalFixer] Max retries ({self.MAX_RETRIES}) reached for {self.project_id}")
            result["retry_allowed"] = False
            return result

        # Classify errors
        errors = self.classifier.classify(error_output)
        result["errors"] = [
            {
                "category": e.category.value,
                "root_cause": e.root_cause,
                "raw_error": e.raw_error[:200],
                "missing_module": e.missing_module,
                "affected_file": e.affected_file,
                "port": e.port,
            }
            for e in errors
        ]

        if not errors:
            logger.info(f"[TerminalFixer] No classifiable errors found in output")
            result["needs_ai"] = True  # Unclassified error needs AI
            return result

        # Get primary error to fix
        primary_error = self.classifier.get_primary_error(errors)
        if not primary_error:
            return result

        logger.info(f"[TerminalFixer] Primary error: {primary_error.category.value} - {primary_error.root_cause}")

        # Try rule-based fix
        fix = self.rule_fixer.get_fix(primary_error)

        if fix:
            if fix.requires_ai:
                result["needs_ai"] = True
                result["fix"] = {
                    "fix_type": fix.fix_type,
                    "description": fix.description,
                    "file_path": fix.file_path,
                }
                return result

            # Apply rule-based fix
            success = await self._apply_fix(fix)
            if success:
                self.retry_count += 1
                self.fix_history.append(fix)
                result["fixed"] = True
                result["fix_type"] = "rule"
                result["fix"] = {
                    "fix_type": fix.fix_type,
                    "command": fix.command,
                    "description": fix.description,
                    "file_path": fix.file_path,
                }
                logger.info(f"[TerminalFixer] Applied rule-based fix: {fix.description}")
            else:
                result["needs_ai"] = True
        else:
            result["needs_ai"] = True

        return result

    async def _apply_fix(self, fix: TerminalFix) -> bool:
        """Apply a fix and return success status"""
        try:
            if fix.fix_type == "command":
                return await self._run_command(fix.command)
            elif fix.fix_type == "file_edit":
                return await self._write_file(fix.file_path, fix.file_content)
            elif fix.fix_type == "port_change":
                # Port change is handled by modifying the run command
                # This is informational only
                return True
            elif fix.fix_type == "info":
                # Just informational, no action needed
                return True

            return False
        except Exception as e:
            logger.error(f"[TerminalFixer] Error applying fix: {e}")
            return False

    async def _run_command(self, command: str) -> bool:
        """Run a shell command in the project directory"""
        try:
            # Check if we're using remote Docker (EC2)
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")

            if sandbox_docker_host:
                # Need to run command inside the container on EC2
                # This will be handled by the container executor
                logger.info(f"[TerminalFixer] Command to run on EC2: {command}")
                # For now, return True and let the caller handle EC2 execution
                return True
            else:
                # Run locally
                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(self.project_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    logger.info(f"[TerminalFixer] Command succeeded: {command}")
                    return True
                else:
                    logger.warning(f"[TerminalFixer] Command failed: {command}\n{stderr.decode()}")
                    return False

        except Exception as e:
            logger.error(f"[TerminalFixer] Error running command: {e}")
            return False

    async def _write_file(self, file_path: str, content: str) -> bool:
        """Write content to a file in the project"""
        try:
            if not content:
                return False

            full_path = self.project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"[TerminalFixer] Created file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"[TerminalFixer] Error writing file: {e}")
            return False

    def reset_retry_count(self):
        """Reset retry counter (call when user manually intervenes)"""
        self.retry_count = 0
        self.fix_history.clear()


# Singleton instances per project
_fixer_instances: Dict[str, TerminalErrorFixer] = {}


def get_terminal_fixer(project_id: str, project_path: Path, user_id: str = None) -> TerminalErrorFixer:
    """Get or create a terminal fixer instance for a project"""
    key = f"{project_id}:{user_id or 'anon'}"
    if key not in _fixer_instances:
        _fixer_instances[key] = TerminalErrorFixer(project_path, project_id, user_id)
    return _fixer_instances[key]


def clear_terminal_fixer(project_id: str, user_id: str = None):
    """Clear the terminal fixer instance for a project"""
    key = f"{project_id}:{user_id or 'anon'}"
    if key in _fixer_instances:
        del _fixer_instances[key]


# ============================================================================
# UnifiedFixer Integration Bridge
# ============================================================================

async def fix_with_unified(
    error_output: str,
    project_path: str,
    project_id: str,
    user_id: str,
    file_path: str = None
) -> Dict[str, Any]:
    """
    Bridge function to use UnifiedFixer with TerminalErrorFixer compatibility.

    Uses the optimized 3-tier architecture:
    - Tier 1: Deterministic (FREE) - pattern-based fixes
    - Tier 2: Haiku AI ($0.001) - simple AI fixes
    - Tier 3: Sonnet AI ($0.01) - complex AI fixes

    Args:
        error_output: Error message/output
        project_path: Path to project
        project_id: Project ID
        user_id: User ID
        file_path: Optional file path with error

    Returns:
        Dict compatible with TerminalErrorFixer results:
            - fixed: bool
            - fix_type: str ("tier1", "tier2", "tier3", "cache")
            - files_modified: List[str]
            - cost: float
            - time_ms: int
            - error: Optional[str]
    """
    try:
        from app.services.unified_fixer import UnifiedFixer, FixTier

        # Get or create unified fixer
        fixer = UnifiedFixer(
            file_manager=unified_file_manager,
            enable_cache=True,
            escalate_on_fail=True
        )

        # Attempt fix
        result = await fixer.fix(
            error=error_output,
            project_path=project_path,
            project_id=project_id,
            user_id=user_id,
            file_path=file_path
        )

        # Convert to compatible format
        fix_type_map = {
            FixTier.DETERMINISTIC: "tier1",
            FixTier.HAIKU: "tier2",
            FixTier.SONNET: "tier3"
        }

        return {
            "fixed": result.success,
            "fix_type": "cache" if result.from_cache else fix_type_map.get(result.final_tier, "unknown"),
            "files_modified": result.files_modified,
            "command_run": result.command_run,
            "cost": result.total_cost,
            "time_ms": result.total_time_ms,
            "category": result.error_category.value,
            "error": result.error,
            "attempts": len(result.attempts)
        }

    except ImportError:
        logger.warning("[TerminalFixer] UnifiedFixer not available, using legacy fixer")
        return {
            "fixed": False,
            "fix_type": None,
            "error": "UnifiedFixer not available"
        }
    except Exception as e:
        logger.error(f"[TerminalFixer] UnifiedFixer error: {e}")
        return {
            "fixed": False,
            "fix_type": None,
            "error": str(e)
        }
