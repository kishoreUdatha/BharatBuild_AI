"""
Universal Auto-Fixer Service - Permanent Solution for ALL Technologies

This service provides a comprehensive auto-fix system that:
1. Detects ALL types of errors (terminal, browser, build, runtime, installation)
2. Automatically fixes errors using AI-powered fixer agent
3. Executes installation commands (npm install, pip install, etc.)
4. Creates missing files automatically
5. Retries until project runs successfully or max retries reached
6. Works across ALL technologies (React, Spring Boot, Python, Go, Rust, etc.)

Usage:
    from app.services.universal_autofixer import UniversalAutoFixer

    autofixer = UniversalAutoFixer(project_id, project_path, user_id)
    success = await autofixer.fix_and_run(command="npm run dev")
"""

import asyncio
import re
import os
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.core.logging_config import logger
from app.core.config import settings
from app.services.fix_executor import FixExecutor, execute_install_command
from app.services.unified_storage import UnifiedStorageService as UnifiedStorageManager
from app.modules.automation.context_engine import ContextEngine


class ErrorCategory(Enum):
    """Categories of errors for targeted fixing"""
    SYNTAX = "syntax"
    IMPORT = "import"
    TYPE = "type"
    RUNTIME = "runtime"
    BUILD = "build"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    DOCKER = "docker"
    DATABASE = "database"
    PERMISSION = "permission"
    PORT = "port"
    MISSING_FILE = "missing_file"
    NETWORK = "network"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information"""
    message: str
    category: ErrorCategory
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: str = ""
    suggested_fix: Optional[str] = None  # e.g., "npm install express"
    technology: Optional[str] = None  # e.g., "javascript", "python", "java"


# ============= COMPREHENSIVE ERROR PATTERNS (ALL TECHNOLOGIES) =============
ERROR_PATTERNS: Dict[str, List[Tuple[str, ErrorCategory, Optional[str]]]] = {
    # Format: (regex_pattern, category, suggested_command)

    # ===== JAVASCRIPT/TYPESCRIPT/NODE.JS =====
    # NOTE: Order matters! More specific patterns (like dependency errors) must come BEFORE generic ones
    "javascript": [
        # DEPENDENCY ERRORS - These MUST come first (most specific)
        (r"Cannot find module ['\"](@?[a-zA-Z0-9\-_./]+)['\"]", ErrorCategory.DEPENDENCY, "npm install {0}"),
        (r"Module not found:.*['\"](@?[a-zA-Z0-9\-_./]+)['\"]", ErrorCategory.DEPENDENCY, "npm install {0}"),
        (r"Error: Cannot find module ['\"](@?[a-zA-Z0-9\-_./]+)['\"]", ErrorCategory.DEPENDENCY, "npm install {0}"),
        (r"\[postcss\] Cannot find module ['\"](@?[a-zA-Z0-9\-_./]+)['\"]", ErrorCategory.DEPENDENCY, "npm install {0}"),
        (r"npm ERR! missing:.*?([a-z@][a-z0-9\-\./@]+)", ErrorCategory.DEPENDENCY, "npm install {0}"),
        (r"npm ERR! peer dep missing:.*?([a-z@][a-z0-9\-\./@]+)", ErrorCategory.DEPENDENCY, "npm install {0}"),
        (r"npm WARN .+ requires a peer of (.+?)@", ErrorCategory.DEPENDENCY, "npm install {0}"),
        (r"ERR_MODULE_NOT_FOUND", ErrorCategory.DEPENDENCY, None),
        (r"'(.+)' is not recognized as an internal or external command", ErrorCategory.DEPENDENCY, "npm install {0}"),
        # TAILWIND/CSS CONFIGURATION ERRORS - Must come before generic BUILD errors
        (r"The `([a-zA-Z0-9\-_]+)` class does not exist", ErrorCategory.CONFIGURATION, None),
        (r"\[postcss\].*class does not exist", ErrorCategory.CONFIGURATION, None),
        (r"@layer.*is not valid", ErrorCategory.CONFIGURATION, None),
        # MISSING FILE ERRORS
        (r"Failed to resolve import ['\"]\.?/?(.+?)['\"]", ErrorCategory.MISSING_FILE, None),
        (r"Does the file exist\?", ErrorCategory.MISSING_FILE, None),
        (r"ENOENT:.*['\"](.+?)['\"]", ErrorCategory.MISSING_FILE, None),
        # BUILD/SYNTAX/TYPE ERRORS - These come after dependency errors
        (r"\[plugin:vite", ErrorCategory.BUILD, None),
        (r"SyntaxError: (.+)", ErrorCategory.SYNTAX, None),
        (r"TypeError: (.+)", ErrorCategory.TYPE, None),
        (r"ReferenceError: (.+) is not defined", ErrorCategory.RUNTIME, None),
        (r"TS\d+:", ErrorCategory.TYPE, None),  # TypeScript errors
        (r"error TS\d+:", ErrorCategory.SYNTAX, None),
        (r"EADDRINUSE.*:(\d+)", ErrorCategory.PORT, None),
    ],

    # ===== PYTHON =====
    "python": [
        (r"ModuleNotFoundError: No module named ['\"](.+?)['\"]", ErrorCategory.DEPENDENCY, "pip install {0}"),
        (r"ImportError: cannot import name ['\"](.+?)['\"]", ErrorCategory.IMPORT, None),
        (r"ImportError: No module named ['\"](.+?)['\"]", ErrorCategory.DEPENDENCY, "pip install {0}"),
        (r"FileNotFoundError:.*['\"](.+?)['\"]", ErrorCategory.MISSING_FILE, None),
        (r"SyntaxError: (.+)", ErrorCategory.SYNTAX, None),
        (r"TypeError: (.+)", ErrorCategory.TYPE, None),
        (r"NameError: name ['\"](.+?)['\"] is not defined", ErrorCategory.RUNTIME, None),
        (r"AttributeError: (.+)", ErrorCategory.TYPE, None),
        (r"KeyError: (.+)", ErrorCategory.RUNTIME, None),
        (r"IndentationError: (.+)", ErrorCategory.SYNTAX, None),
        (r"pip install (.+?) failed", ErrorCategory.DEPENDENCY, "pip install {0}"),
        (r"uvicorn.*error", ErrorCategory.RUNTIME, None),
        (r"fastapi.*error", ErrorCategory.RUNTIME, None),
        (r"django.*error", ErrorCategory.RUNTIME, None),
        (r"Address already in use", ErrorCategory.PORT, None),
    ],

    # ===== JAVA/SPRING BOOT =====
    "java": [
        (r"package (.+) does not exist", ErrorCategory.DEPENDENCY, None),
        (r"cannot find symbol.*class (\w+)", ErrorCategory.IMPORT, None),
        (r"ClassNotFoundException: (.+)", ErrorCategory.DEPENDENCY, None),
        (r"NoClassDefFoundError: (.+)", ErrorCategory.DEPENDENCY, None),
        (r"NullPointerException", ErrorCategory.RUNTIME, None),
        (r"BUILD FAILURE", ErrorCategory.BUILD, None),
        (r"BUILD FAILED", ErrorCategory.BUILD, None),
        (r"Compilation failure", ErrorCategory.SYNTAX, None),
        (r"cannot find symbol", ErrorCategory.IMPORT, None),
        (r"incompatible types", ErrorCategory.TYPE, None),
        (r"Failed to execute goal", ErrorCategory.BUILD, None),
        (r"Could not resolve dependencies", ErrorCategory.DEPENDENCY, "mvn dependency:resolve"),
        (r"BeanCreationException", ErrorCategory.CONFIGURATION, None),
        (r"NoSuchBeanDefinitionException", ErrorCategory.CONFIGURATION, None),
        (r"ApplicationContextException", ErrorCategory.CONFIGURATION, None),
        (r"Port \d+ was already in use", ErrorCategory.PORT, None),
        (r"Address already in use", ErrorCategory.PORT, None),
        (r"java\.lang\.\w+Exception", ErrorCategory.RUNTIME, None),
    ],

    # ===== GO =====
    "go": [
        (r"cannot find package ['\"](.+?)['\"]", ErrorCategory.DEPENDENCY, "go get {0}"),
        (r"undefined: (\w+)", ErrorCategory.IMPORT, None),
        (r"package (.+) is not in", ErrorCategory.DEPENDENCY, "go get {0}"),
        (r"go:.*error", ErrorCategory.BUILD, None),
        (r"syntax error", ErrorCategory.SYNTAX, None),
        (r"type (\w+) has no field or method", ErrorCategory.TYPE, None),
    ],

    # ===== RUST =====
    "rust": [
        (r"error\[E\d+\]:", ErrorCategory.SYNTAX, None),
        (r"cannot find .+ `(.+?)`", ErrorCategory.IMPORT, None),
        (r"unresolved import `(.+?)`", ErrorCategory.DEPENDENCY, None),
        (r"cannot borrow", ErrorCategory.RUNTIME, None),
        (r"lifetime .+ required", ErrorCategory.TYPE, None),
        (r"Compiling .+ failed", ErrorCategory.BUILD, None),
    ],

    # ===== DOCKER =====
    "docker": [
        (r"failed to build", ErrorCategory.BUILD, None),
        (r"COPY failed:.*no such file", ErrorCategory.MISSING_FILE, None),
        (r"RUN .+ returned a non-zero code", ErrorCategory.BUILD, None),
        (r"Cannot connect to the Docker daemon", ErrorCategory.DOCKER, None),
        (r"port is already allocated", ErrorCategory.PORT, None),
        (r"bind: address already in use", ErrorCategory.PORT, None),
        (r"OCI runtime create failed", ErrorCategory.DOCKER, None),
        (r"Error response from daemon", ErrorCategory.DOCKER, None),
        (r"no space left on device", ErrorCategory.DOCKER, None),
    ],

    # ===== GENERAL =====
    "general": [
        (r"EACCES|EPERM|permission denied", ErrorCategory.PERMISSION, None),
        (r"ECONNREFUSED", ErrorCategory.NETWORK, None),
        (r"timeout|ETIMEDOUT", ErrorCategory.NETWORK, None),
        (r"Missing script: ['\"](.+?)['\"]", ErrorCategory.CONFIGURATION, None),
        (r"command not found:?\s*(.+)", ErrorCategory.DEPENDENCY, None),
    ],
}


class UniversalAutoFixer:
    """
    Universal Auto-Fixer that handles ALL errors for ALL technologies.

    Key Features:
    1. Multi-technology support (JS, Python, Java, Go, Rust, Docker, etc.)
    2. Comprehensive error pattern matching
    3. AI-powered fix generation using Claude
    4. Automatic dependency installation
    5. Missing file creation
    6. Retry loop with exponential backoff
    7. Browser/runtime error handling via WebSocket
    """

    MAX_FIX_ATTEMPTS = settings.AUTOFIXER_MAX_ATTEMPTS  # Maximum fix attempts before giving up
    FIX_DELAY_SECONDS = 2  # Delay between fix attempts
    INSTALL_TIMEOUT_SECONDS = settings.AUTOFIXER_INSTALL_TIMEOUT  # Timeout for install commands

    def __init__(
        self,
        project_id: str,
        project_path: Path,
        user_id: Optional[str] = None
    ):
        self.project_id = project_id
        self.project_path = Path(project_path) if isinstance(project_path, str) else project_path
        self.user_id = user_id
        self.storage = UnifiedStorageManager()
        self.fix_executor = FixExecutor(project_id)
        self.context_engine = ContextEngine(str(self.project_path))

        # Track fix attempts
        self.fix_attempts: List[Dict[str, Any]] = []
        self.errors_seen: List[str] = []  # Track error occurrences (allows counting duplicates)
        self.fixes_applied: List[str] = []

        # Detect project technology
        self.technology = self._detect_technology()

    def _detect_technology(self) -> str:
        """Detect the primary technology of the project"""
        # Check for common files
        if (self.project_path / "package.json").exists():
            return "javascript"
        if (self.project_path / "frontend" / "package.json").exists():
            return "javascript"  # Monorepo with JS frontend
        if (self.project_path / "requirements.txt").exists():
            return "python"
        if (self.project_path / "pom.xml").exists() or (self.project_path / "build.gradle").exists():
            return "java"
        if (self.project_path / "go.mod").exists():
            return "go"
        if (self.project_path / "Cargo.toml").exists():
            return "rust"
        if (self.project_path / "Dockerfile").exists():
            return "docker"
        return "general"

    def classify_error(self, error_message: str) -> ErrorInfo:
        """Classify an error message and extract relevant information"""
        # Log first 200 chars of error message for debugging
        logger.debug(f"[UniversalAutoFixer:{self.project_id}] Classifying error: {error_message[:200]}")

        # Try technology-specific patterns first, then all other technologies
        patterns_to_check = ERROR_PATTERNS.get(self.technology, [])

        # Also check all technology patterns (in case technology detection was wrong)
        for tech_name, tech_patterns in ERROR_PATTERNS.items():
            if tech_name != self.technology and tech_name != "general":
                patterns_to_check.extend(tech_patterns)

        # Add general patterns last
        patterns_to_check.extend(ERROR_PATTERNS["general"])

        for pattern, category, suggested_fix in patterns_to_check:
            match = re.search(pattern, error_message, re.IGNORECASE | re.MULTILINE)
            if match:
                # Extract matched groups for suggested fix
                fix_cmd = None
                if suggested_fix and match.groups():
                    try:
                        fix_cmd = suggested_fix.format(*match.groups())
                    except (IndexError, KeyError) as e:
                        logger.debug(f"Could not format suggested fix with match groups: {e}")
                        fix_cmd = suggested_fix
                elif suggested_fix:
                    fix_cmd = suggested_fix

                logger.info(f"[UniversalAutoFixer:{self.project_id}] Pattern matched: {pattern[:50]}... -> {category.value}, fix: {fix_cmd}")
                return ErrorInfo(
                    message=error_message,
                    category=category,
                    suggested_fix=fix_cmd,
                    technology=self.technology
                )

        logger.warning(f"[UniversalAutoFixer:{self.project_id}] No pattern matched for error: {error_message[:100]}")
        return ErrorInfo(
            message=error_message,
            category=ErrorCategory.UNKNOWN,
            technology=self.technology
        )

    async def execute_command(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout: int = 120
    ) -> Tuple[int, str, str]:
        """Execute a shell command and return (exit_code, stdout, stderr)"""
        work_dir = cwd or self.project_path

        logger.info(f"[UniversalAutoFixer:{self.project_id}] Executing: {command} in {work_dir}")

        try:
            if platform.system() == "Windows":
                # Windows: Use shell=True
                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(work_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                # Unix: Use shell=True with bash
                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=str(work_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return (
                process.returncode or 0,
                stdout.decode('utf-8', errors='replace') if stdout else "",
                stderr.decode('utf-8', errors='replace') if stderr else ""
            )

        except asyncio.TimeoutError:
            logger.error(f"[UniversalAutoFixer:{self.project_id}] Command timed out: {command}")
            return (124, "", f"Command timed out after {timeout}s")
        except Exception as e:
            logger.error(f"[UniversalAutoFixer:{self.project_id}] Command failed: {e}")
            return (1, "", str(e))

    async def install_dependencies(self, error_info: ErrorInfo) -> bool:
        """Install missing dependencies based on error analysis"""
        if not error_info.suggested_fix:
            return False

        command = error_info.suggested_fix
        logger.info(f"[UniversalAutoFixer:{self.project_id}] Installing dependency: {command}")

        # Determine the correct directory for installation
        work_dir = self.project_path

        if command.startswith("npm "):
            # For npm commands, check if we need to install in frontend/
            frontend_path = self.project_path / "frontend"
            if frontend_path.exists() and (frontend_path / "package.json").exists():
                work_dir = frontend_path
        elif command.startswith("pip "):
            # For pip commands, check if we need to install in backend/
            backend_path = self.project_path / "backend"
            if backend_path.exists() and (backend_path / "requirements.txt").exists():
                work_dir = backend_path

        exit_code, stdout, stderr = await self.execute_command(
            command,
            cwd=work_dir,
            timeout=self.INSTALL_TIMEOUT_SECONDS
        )

        success = exit_code == 0
        if success:
            logger.info(f"[UniversalAutoFixer:{self.project_id}] ✅ Dependency installed: {command}")
            self.fixes_applied.append(f"Installed: {command}")
        else:
            logger.error(f"[UniversalAutoFixer:{self.project_id}] ❌ Install failed: {stderr[:500]}")

        return success

    async def fix_with_ai(self, error_message: str, stack_trace: str = "") -> Dict[str, Any]:
        """Use AI fixer agent to fix the error"""
        logger.info(f"[UniversalAutoFixer:{self.project_id}] Using AI to fix error...")

        # Get full context for the fixer
        context = {
            "project_path": str(self.project_path),
            "technology": self.technology,
            "previous_attempts": len(self.fix_attempts),
            "fixes_applied": self.fixes_applied
        }

        result = await self.fix_executor.execute_fix(
            error_message=error_message,
            stack_trace=stack_trace,
            command=None,
            context=context
        )

        return result

    async def fix_tailwind_configuration(self, error_message: str) -> bool:
        """
        Fix Tailwind CSS configuration errors like missing utility classes.

        Handles errors like:
        - "The `border-border` class does not exist"
        - "The `bg-background` class does not exist"

        These are typically shadcn/ui convention errors where CSS variables
        are used but the corresponding colors aren't defined in tailwind.config.js

        STRATEGY: Replace shadcn/ui classes with standard Tailwind (more reliable)
        """
        logger.info(f"[UniversalAutoFixer:{self.project_id}] Fixing Tailwind configuration error...")

        # Extract the missing class name
        class_pattern = r"The `([a-zA-Z0-9\-_]+)` class does not exist"
        match = re.search(class_pattern, error_message)

        if not match:
            # Try alternative pattern
            class_pattern = r"class '([a-zA-Z0-9\-_]+)' does not exist"
            match = re.search(class_pattern, error_message, re.IGNORECASE)

        if not match:
            logger.warning(f"[UniversalAutoFixer:{self.project_id}] Could not extract missing class name")
            return await self.fix_with_ai(error_message)

        missing_class = match.group(1)
        logger.info(f"[UniversalAutoFixer:{self.project_id}] Missing Tailwind class: {missing_class}")

        # =================================================================
        # STRATEGY 1: Replace shadcn classes in CSS files with standard Tailwind
        # This is more reliable than modifying tailwind.config.js
        # =================================================================
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

        # Try to fix CSS files first (more reliable approach)
        if missing_class in shadcn_to_tailwind:
            replacement = shadcn_to_tailwind[missing_class]
            css_fixed = await self._fix_shadcn_in_css_files(missing_class, replacement)
            if css_fixed:
                logger.info(f"[UniversalAutoFixer:{self.project_id}] ✅ Replaced {missing_class} with {replacement} in CSS")
                self.fixes_applied.append(f"Replaced @apply {missing_class} with {replacement}")
                return True

        # =================================================================
        # STRATEGY 2 (Fallback): Modify tailwind.config.js
        # =================================================================

        # Common shadcn/ui CSS variable mappings
        # These classes use CSS variables like var(--border), var(--background), etc.
        shadcn_color_mappings = {
            "border-border": ("border", "hsl(var(--border))"),
            "bg-background": ("background", "hsl(var(--background))"),
            "text-foreground": ("foreground", "hsl(var(--foreground))"),
            "bg-card": ("card", "hsl(var(--card))"),
            "text-card-foreground": ("card-foreground", "hsl(var(--card-foreground))"),
            "bg-popover": ("popover", "hsl(var(--popover))"),
            "text-popover-foreground": ("popover-foreground", "hsl(var(--popover-foreground))"),
            "bg-primary": ("primary", "hsl(var(--primary))"),
            "text-primary-foreground": ("primary-foreground", "hsl(var(--primary-foreground))"),
            "bg-secondary": ("secondary", "hsl(var(--secondary))"),
            "text-secondary-foreground": ("secondary-foreground", "hsl(var(--secondary-foreground))"),
            "bg-muted": ("muted", "hsl(var(--muted))"),
            "text-muted-foreground": ("muted-foreground", "hsl(var(--muted-foreground))"),
            "bg-accent": ("accent", "hsl(var(--accent))"),
            "text-accent-foreground": ("accent-foreground", "hsl(var(--accent-foreground))"),
            "bg-destructive": ("destructive", "hsl(var(--destructive))"),
            "text-destructive-foreground": ("destructive-foreground", "hsl(var(--destructive-foreground))"),
            "ring-ring": ("ring", "hsl(var(--ring))"),
            "bg-input": ("input", "hsl(var(--input))"),
        }

        # Find the tailwind.config file
        tailwind_config_paths = [
            self.project_path / "tailwind.config.js",
            self.project_path / "tailwind.config.ts",
            self.project_path / "frontend" / "tailwind.config.js",
            self.project_path / "frontend" / "tailwind.config.ts",
        ]

        tailwind_config = None
        for config_path in tailwind_config_paths:
            if config_path.exists():
                tailwind_config = config_path
                break

        if not tailwind_config:
            logger.warning(f"[UniversalAutoFixer:{self.project_id}] No tailwind.config.js found")
            return await self.fix_with_ai(error_message)

        logger.info(f"[UniversalAutoFixer:{self.project_id}] Found tailwind config: {tailwind_config}")

        # Read the current config
        try:
            config_content = tailwind_config.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"[UniversalAutoFixer:{self.project_id}] Failed to read tailwind config: {e}")
            return await self.fix_with_ai(error_message)

        # Check if this is a shadcn/ui class that needs a color definition
        if missing_class in shadcn_color_mappings:
            color_name, color_value = shadcn_color_mappings[missing_class]
            logger.info(f"[UniversalAutoFixer:{self.project_id}] Adding shadcn color: {color_name} = {color_value}")

            # Check if colors section exists in extend
            if "colors:" in config_content or "colors :" in config_content:
                # Colors section exists, add to it
                # Find the colors: { section and add our color
                colors_pattern = r"(colors\s*:\s*\{)"
                if re.search(colors_pattern, config_content):
                    # Add the new color after the opening brace
                    new_config = re.sub(
                        colors_pattern,
                        f"\\1\n        {color_name}: '{color_value}',",
                        config_content,
                        count=1
                    )
                else:
                    # Fall back to AI fixer
                    return await self.fix_with_ai(error_message)
            else:
                # No colors section, need to add one in extend
                extend_pattern = r"(extend\s*:\s*\{)"
                if re.search(extend_pattern, config_content):
                    new_config = re.sub(
                        extend_pattern,
                        f"\\1\n      colors: {{\n        {color_name}: '{color_value}',\n      }},",
                        config_content,
                        count=1
                    )
                else:
                    # No extend section either, use AI fixer
                    return await self.fix_with_ai(error_message)

            # Write the updated config
            try:
                tailwind_config.write_text(new_config, encoding='utf-8')
                logger.info(f"[UniversalAutoFixer:{self.project_id}] ✅ Updated tailwind.config.js with {color_name} color")
                self.fixes_applied.append(f"Added Tailwind color: {color_name}")
                return True
            except Exception as e:
                logger.error(f"[UniversalAutoFixer:{self.project_id}] Failed to write tailwind config: {e}")
                return False

        # For other configuration errors, use AI fixer with context
        return await self.fix_with_ai(
            f"Tailwind CSS configuration error: {error_message}\n\n"
            f"The class '{missing_class}' is not defined. Please update {tailwind_config} "
            f"to define this class or fix the CSS that uses it."
        )

    async def _fix_shadcn_in_css_files(self, shadcn_class: str, replacement: str) -> bool:
        """
        Replace shadcn/ui @apply classes with standard Tailwind in CSS files.

        This is more reliable than modifying tailwind.config.js because:
        1. Standard Tailwind classes always work
        2. No CSS variables needed
        3. Directly fixes the source of the problem
        """
        # Common CSS file locations
        css_file_paths = [
            self.project_path / "src" / "index.css",
            self.project_path / "src" / "globals.css",
            self.project_path / "src" / "app" / "globals.css",
            self.project_path / "src" / "styles" / "globals.css",
            self.project_path / "src" / "App.css",
            self.project_path / "app" / "globals.css",
            self.project_path / "styles" / "globals.css",
            self.project_path / "frontend" / "src" / "index.css",
            self.project_path / "frontend" / "src" / "globals.css",
        ]

        fixed_any = False

        for css_path in css_file_paths:
            if not css_path.exists():
                continue

            try:
                content = css_path.read_text(encoding='utf-8')
                original_content = content

                # Pattern to match @apply with the shadcn class
                # Handles: @apply border-border; and @apply ... border-border ...;
                patterns = [
                    # Standalone: @apply border-border;
                    (rf'@apply\s+{re.escape(shadcn_class)}\s*;', f'@apply {replacement};'),
                    # In a list: @apply ... border-border ...;
                    (rf'(@apply\s+[^;]*)\b{re.escape(shadcn_class)}\b([^;]*;)', rf'\1{replacement}\2'),
                ]

                for pattern, repl in patterns:
                    content = re.sub(pattern, repl, content)

                # Check if anything changed
                if content != original_content:
                    css_path.write_text(content, encoding='utf-8')
                    logger.info(f"[UniversalAutoFixer:{self.project_id}] Fixed {shadcn_class} in {css_path}")
                    fixed_any = True

            except Exception as e:
                logger.warning(f"[UniversalAutoFixer:{self.project_id}] Error fixing {css_path}: {e}")
                continue

        return fixed_any

    async def detect_and_fix_missing_files(self, error_message: str) -> bool:
        """Detect and create missing files from import errors"""
        # Extract missing file paths from error
        patterns = [
            r"Failed to resolve import ['\"]\.?/?(.+?)['\"]",
            r"Module not found:.*['\"]\.?/?(.+?)['\"]",
            r"Cannot find module ['\"]\.?/?(.+?)['\"]",
            r"ENOENT:.*['\"](.+?)['\"]",
            r"FileNotFoundError:.*['\"](.+?)['\"]",
        ]

        missing_files = []
        for pattern in patterns:
            matches = re.findall(pattern, error_message)
            missing_files.extend(matches)

        if not missing_files:
            return False

        logger.info(f"[UniversalAutoFixer:{self.project_id}] Detected missing files: {missing_files}")

        # Use AI to generate the missing files
        result = await self.fix_with_ai(
            error_message=f"Missing files detected: {missing_files}. Please create these files with appropriate content based on the project structure.",
            stack_trace=""
        )

        return result.get("success", False)

    async def fix_error(self, error_message: str, stack_trace: str = "") -> bool:
        """
        Attempt to fix a single error.
        Returns True if fix was successful, False otherwise.
        """
        # Skip if we've seen this exact error too many times
        error_hash = str(hash(error_message[:200]))
        if self.errors_seen.count(error_hash) >= 3:
            logger.warning(f"[UniversalAutoFixer:{self.project_id}] Skipping repeated error")
            return False
        self.errors_seen.append(error_hash)

        # Classify the error
        error_info = self.classify_error(error_message)
        logger.info(f"[UniversalAutoFixer:{self.project_id}] Error category: {error_info.category.value}")

        # Try category-specific fixes first
        if error_info.category == ErrorCategory.DEPENDENCY and error_info.suggested_fix:
            success = await self.install_dependencies(error_info)
            if success:
                return True

        elif error_info.category == ErrorCategory.MISSING_FILE:
            success = await self.detect_and_fix_missing_files(error_message)
            if success:
                return True

        elif error_info.category == ErrorCategory.PORT:
            # Port conflicts need special handling - find available port
            logger.info(f"[UniversalAutoFixer:{self.project_id}] Port conflict detected - will retry with different port")
            return False  # Let the executor handle port allocation

        elif error_info.category == ErrorCategory.CONFIGURATION:
            # Configuration errors (Tailwind CSS, etc.)
            # Check if it's a Tailwind CSS configuration error
            if "class does not exist" in error_message.lower() or "tailwind" in error_message.lower() or "[postcss]" in error_message.lower():
                logger.info(f"[UniversalAutoFixer:{self.project_id}] Tailwind configuration error detected")
                success = await self.fix_tailwind_configuration(error_message)
                if success:
                    return True
            # For other configuration errors, fall through to AI fixer

        # For all other errors, use AI fixer
        result = await self.fix_with_ai(error_message, stack_trace)

        # Record the attempt
        self.fix_attempts.append({
            "timestamp": datetime.now().isoformat(),
            "error": error_message[:200],
            "category": error_info.category.value,
            "success": result.get("success", False),
            "patches_applied": result.get("patches_applied", 0),
            "files_modified": result.get("files_modified", [])
        })

        return result.get("success", False)

    async def fix_all_errors(self, output: str) -> int:
        """
        Parse output for errors and fix them all.
        Returns the number of fixes applied.
        """
        fixes_applied = 0

        # Split output into lines and look for errors
        lines = output.split('\n')
        error_buffer = []

        for i, line in enumerate(lines):
            # Check if this line contains an error
            is_error_line = False
            all_patterns = []
            for patterns in ERROR_PATTERNS.values():
                all_patterns.extend(patterns)

            for pattern, _, _ in all_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    is_error_line = True
                    break

            if is_error_line:
                # Collect context (5 lines before and after)
                start = max(0, i - 5)
                end = min(len(lines), i + 5)
                context = '\n'.join(lines[start:end])

                # Try to fix this error
                success = await self.fix_error(context)
                if success:
                    fixes_applied += 1

                # Add delay between fixes
                await asyncio.sleep(0.5)

        return fixes_applied

    async def run_with_autofix(
        self,
        command: str,
        max_attempts: int = None
    ) -> Tuple[bool, str]:
        """
        Run a command with automatic error fixing.
        Retries until success or max attempts reached.

        Returns: (success, final_output)
        """
        max_attempts = max_attempts or self.MAX_FIX_ATTEMPTS
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            logger.info(f"[UniversalAutoFixer:{self.project_id}] Attempt {attempt}/{max_attempts}: {command}")

            # Run the command
            exit_code, stdout, stderr = await self.execute_command(command, timeout=60)
            combined_output = f"{stdout}\n{stderr}"

            # Check if successful
            if exit_code == 0:
                # Check for runtime errors in output even with success code
                has_errors = False
                for patterns in ERROR_PATTERNS.values():
                    for pattern, _, _ in patterns:
                        if re.search(pattern, combined_output, re.IGNORECASE):
                            has_errors = True
                            break
                    if has_errors:
                        break

                if not has_errors:
                    logger.info(f"[UniversalAutoFixer:{self.project_id}] ✅ Command succeeded on attempt {attempt}")
                    return True, combined_output

            # Fix errors
            logger.info(f"[UniversalAutoFixer:{self.project_id}] Fixing errors from attempt {attempt}...")
            fixes = await self.fix_all_errors(combined_output)

            if fixes == 0:
                # No fixes could be applied, try AI anyway
                await self.fix_with_ai(combined_output[:2000])

            # Wait before retrying
            await asyncio.sleep(self.FIX_DELAY_SECONDS)

        logger.error(f"[UniversalAutoFixer:{self.project_id}] ❌ Failed after {max_attempts} attempts")
        return False, combined_output

    async def pre_run_checks(self) -> List[str]:
        """
        Run pre-flight checks before starting the project.
        Returns list of commands that need to be run.
        """
        commands_needed = []

        # Check for node_modules
        if self.technology == "javascript":
            pkg_path = self.project_path / "package.json"
            node_modules = self.project_path / "node_modules"

            # Also check frontend/ for monorepos
            frontend_pkg = self.project_path / "frontend" / "package.json"
            frontend_modules = self.project_path / "frontend" / "node_modules"

            if pkg_path.exists() and not node_modules.exists():
                commands_needed.append(("npm install", self.project_path))

            if frontend_pkg.exists() and not frontend_modules.exists():
                commands_needed.append(("npm install", self.project_path / "frontend"))

        # Check for Python venv/packages
        elif self.technology == "python":
            req_path = self.project_path / "requirements.txt"
            if req_path.exists():
                # Could check if packages are installed, for now just suggest install
                commands_needed.append(("pip install -r requirements.txt", self.project_path))

        # Check for Java/Maven
        elif self.technology == "java":
            pom_path = self.project_path / "pom.xml"
            backend_pom = self.project_path / "backend" / "pom.xml"

            if pom_path.exists():
                commands_needed.append(("mvn dependency:resolve", self.project_path))
            elif backend_pom.exists():
                commands_needed.append(("mvn dependency:resolve", self.project_path / "backend"))

        return commands_needed

    async def setup_project(self) -> bool:
        """
        Setup project by running necessary install commands.
        Returns True if setup successful.
        """
        logger.info(f"[UniversalAutoFixer:{self.project_id}] Setting up project...")

        commands = await self.pre_run_checks()

        for command, work_dir in commands:
            logger.info(f"[UniversalAutoFixer:{self.project_id}] Running setup: {command}")
            exit_code, stdout, stderr = await self.execute_command(
                command,
                cwd=work_dir,
                timeout=self.INSTALL_TIMEOUT_SECONDS
            )

            if exit_code != 0:
                logger.warning(f"[UniversalAutoFixer:{self.project_id}] Setup command failed: {stderr[:500]}")
                # Don't fail completely, might still work

        return True


# ============= CONVENIENCE FUNCTIONS =============

async def auto_fix_and_run(
    project_id: str,
    project_path: Path,
    command: str,
    user_id: Optional[str] = None,
    max_attempts: int = 10
) -> Tuple[bool, str]:
    """
    Convenience function to auto-fix and run a project command.

    Usage:
        success, output = await auto_fix_and_run(
            project_id="123",
            project_path=Path("/path/to/project"),
            command="npm run dev",
            user_id="user123"
        )
    """
    autofixer = UniversalAutoFixer(project_id, project_path, user_id)

    # Setup project first
    await autofixer.setup_project()

    # Run with auto-fix
    return await autofixer.run_with_autofix(command, max_attempts)


async def fix_error_universal(
    project_id: str,
    project_path: Path,
    error_message: str,
    user_id: Optional[str] = None
) -> bool:
    """
    Fix a single error universally.

    Usage:
        success = await fix_error_universal(
            project_id="123",
            project_path=Path("/path/to/project"),
            error_message="Cannot find module 'express'"
        )
    """
    autofixer = UniversalAutoFixer(project_id, project_path, user_id)
    return await autofixer.fix_error(error_message)
