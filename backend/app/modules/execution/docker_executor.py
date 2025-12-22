"""
Docker-based Project Executor

Runs student projects in isolated Docker containers with:
1. Auto-generated Dockerfile if missing
2. Automatic port detection
3. Live preview URL support
"""

import asyncio
import json
import re
import os
import shutil
import threading
from pathlib import Path
from typing import Dict, Optional, List, Tuple, AsyncGenerator, Any
from dataclasses import dataclass
from enum import Enum

from app.core.logging_config import logger
from app.utils.config_templates import get_template, VITE_REACT_TEMPLATES
from app.services.log_bus import get_log_bus
from app.services.fix_executor import FixExecutor
from app.services.universal_autofixer import UniversalAutoFixer, fix_error_universal, ErrorCategory
from app.services.production_autofixer import ProductionAutoFixer, fix_error_production, FixStrategy, get_global_metrics
from app.services.fullstack_integrator import FullstackIntegrator
from app.services.smart_project_analyzer import smart_analyzer, Technology
from app.modules.sdk_agents.sdk_fixer_agent import SDKFixerAgent
from app.services.simple_fixer import simple_fixer
from app.services.container_executor import container_executor, Technology as ContainerTech

# Preview URL Configuration
# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip('/')
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL") or os.getenv("SANDBOX_PREVIEW_BASE_URL", "http://localhost")

# Log the values at startup for debugging
logger.info(f"[DockerExecutor] Preview config: ENV={ENVIRONMENT}, FRONTEND_URL={FRONTEND_URL}, SANDBOX_PUBLIC_URL={SANDBOX_PUBLIC_URL}")


def get_preview_url(port: int, project_id: str = None) -> str:
    """
    Generate preview URL for the running container.

    Works in both local and production:
    - Local: http://localhost:{port}
    - Production with project_id: https://bharatbuild.ai/api/v1/preview/{project_id}/
    - Production without project_id: Uses SANDBOX_PUBLIC_URL with port

    Args:
        port: The container port
        project_id: Optional project ID for API-based preview URL (production)

    Returns:
        Preview URL string
    """
    # Check if we're in production (not localhost)
    is_production = (
        ENVIRONMENT == "production" or
        (FRONTEND_URL and "localhost" not in FRONTEND_URL and "127.0.0.1" not in FRONTEND_URL)
    )

    if is_production and project_id:
        # Production with project_id: Use domain-based API preview proxy
        # This routes through: https://bharatbuild.ai/api/v1/preview/{project_id}/
        result = f"{FRONTEND_URL}/api/v1/preview/{project_id}/"
        logger.info(f"[DockerExecutor] get_preview_url({port}, {project_id}) -> {result} (production/domain)")
        return result

    if is_production and SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        # Production without project_id: Direct IP:port (fallback)
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        result = f"{base}:{port}"
        logger.info(f"[DockerExecutor] get_preview_url({port}) -> {result} (production/direct)")
        return result

    # Local development: Use localhost
    result = f"http://localhost:{port}"
    logger.info(f"[DockerExecutor] get_preview_url({port}) -> {result} (local)")
    return result


def get_direct_preview_url(port: int) -> str:
    """
    Get direct IP:port URL (bypasses API proxy).
    Used for HMR/WebSocket connections that need direct container access.
    """
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        return f"{base}:{port}"
    return f"http://localhost:{port}"


def replace_port_in_command(command: str, old_port: int, new_port: int) -> str:
    """
    Safely replace port number in command string.
    Only replaces port when it appears in port-specific contexts to avoid
    accidentally replacing the same number if it appears elsewhere (e.g., in filenames).

    Contexts matched:
    - --port 3000, --port=3000, -p 3000
    - :3000 (URL or binding)
    - PORT=3000 (environment variable)
    - port 3000 (space-separated)
    """
    import re
    old = str(old_port)
    new = str(new_port)

    # Patterns for port contexts (with word boundaries to avoid partial matches)
    patterns = [
        (rf'(--port[=\s])({old})\b', rf'\g<1>{new}'),           # --port 3000 or --port=3000
        (rf'(-p\s+)({old})\b', rf'\g<1>{new}'),                  # -p 3000
        (rf'(:)({old})\b', rf'\g<1>{new}'),                      # :3000 (URL or port binding)
        (rf'(PORT[=\s])({old})\b', rf'\g<1>{new}'),              # PORT=3000 or PORT 3000
        (rf'(\sport\s+)({old})\b', rf'\g<1>{new}', re.IGNORECASE),  # " port 3000"
    ]

    result = command
    for pattern in patterns:
        if len(pattern) == 3:
            result = re.sub(pattern[0], pattern[1], result, flags=pattern[2])
        else:
            result = re.sub(pattern[0], pattern[1], result)

    # Fallback: if no pattern matched but port exists, use simple replace
    # This handles edge cases but logs a warning
    if old in result and new not in result:
        logger.warning(f"[replace_port] Fallback to simple replace for: {command[:100]}")
        result = command.replace(old, new)

    return result


class FrameworkType(Enum):
    # ===== FRONTEND =====
    REACT_VITE = "react-vite"
    REACT_CRA = "react-cra"
    NEXTJS = "nextjs"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"
    STATIC_HTML = "static-html"

    # ===== BACKEND NODE.JS =====
    NODE_EXPRESS = "node-express"

    # ===== PYTHON =====
    PYTHON_FLASK = "python-flask"
    PYTHON_FASTAPI = "python-fastapi"
    PYTHON_DJANGO = "python-django"
    PYTHON_STREAMLIT = "python-streamlit"
    PYTHON_ML = "python-ml"  # AI/ML projects (TensorFlow, PyTorch, etc.)

    # ===== JAVA =====
    SPRING_BOOT = "spring-boot"
    ANDROID = "android"  # Android (Kotlin/Java)

    # ===== GO =====
    GO = "go"

    # ===== RUST =====
    RUST = "rust"

    # ===== RUBY =====
    RUBY_RAILS = "ruby-rails"

    # ===== PHP =====
    PHP_LARAVEL = "php-laravel"

    # ===== .NET =====
    DOTNET = "dotnet"

    # ===== iOS =====
    IOS_SWIFT = "ios-swift"

    # ===== BLOCKCHAIN =====
    SOLIDITY = "solidity"  # Ethereum/EVM
    RUST_SOLANA = "rust-solana"  # Solana

    # ===== FULLSTACK MONOREPO =====
    FULLSTACK_REACT_SPRING = "fullstack-react-spring"  # React + Spring Boot monorepo
    FULLSTACK_REACT_EXPRESS = "fullstack-react-express"  # React + Express monorepo
    FULLSTACK_REACT_FASTAPI = "fullstack-react-fastapi"  # React + FastAPI monorepo

    # ===== OTHER =====
    UNKNOWN = "unknown"


@dataclass
class FrameworkInfo:
    type: FrameworkType
    default_port: int
    dockerfile_template: str
    docker_compose_template: Optional[str] = None


# Dockerfile Templates
DOCKERFILE_TEMPLATES: Dict[FrameworkType, str] = {
    FrameworkType.REACT_VITE: '''FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Expose port
EXPOSE 5173

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
''',

    FrameworkType.REACT_CRA: '''FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Expose port
EXPOSE 3000

# Set host to allow external connections
ENV HOST=0.0.0.0

# Start development server
CMD ["npm", "start"]
''',

    FrameworkType.NEXTJS: '''FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev"]
''',

    FrameworkType.VUE: '''FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Expose port
EXPOSE 5173

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
''',

    FrameworkType.ANGULAR: '''FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Expose port
EXPOSE 4200

# Start development server with host binding
CMD ["npm", "start", "--", "--host", "0.0.0.0"]
''',

    FrameworkType.NODE_EXPRESS: '''FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Expose port
EXPOSE 3000

# Start server
CMD ["npm", "start"]
''',

    FrameworkType.PYTHON_FLASK: '''FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Expose port
EXPOSE 5000

# Set Flask environment
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Start Flask server
CMD ["flask", "run"]
''',

    FrameworkType.PYTHON_FASTAPI: '''FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Expose port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
''',

    FrameworkType.PYTHON_DJANGO: '''FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Expose port
EXPOSE 8000

# Start Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
''',

    FrameworkType.PYTHON_STREAMLIT: '''FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Expose port
EXPOSE 8501

# Start Streamlit server
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
''',

    FrameworkType.SPRING_BOOT: '''FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /app

# Copy pom.xml and download dependencies
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source code
COPY src ./src

# Build the application
RUN mvn package -DskipTests

# Runtime stage
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Copy the built JAR from build stage
COPY --from=build /app/target/*.jar app.jar

# Expose port
EXPOSE 8080

# Start the application
CMD ["java", "-jar", "app.jar"]
''',

    FrameworkType.GO: '''FROM golang:1.21-alpine AS build

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum* ./

# Download dependencies
RUN go mod download

# Copy source files
COPY . .

# Build the application
RUN go build -o main .

# Runtime stage
FROM alpine:latest

WORKDIR /app

# Copy binary from build stage
COPY --from=build /app/main .

# Expose port
EXPOSE 8080

# Start the application
CMD ["./main"]
''',

    FrameworkType.STATIC_HTML: '''FROM nginx:alpine

# Copy HTML files to nginx html directory
COPY . /usr/share/nginx/html/

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
''',

    FrameworkType.UNKNOWN: '''FROM node:18-alpine

WORKDIR /app

# Copy all files
COPY . .

# Try to install if package.json exists
RUN if [ -f package.json ]; then npm install; fi

# Expose common port
EXPOSE 3000

# Try to run
CMD ["npm", "start"]
'''
}


# Default ports for each framework
DEFAULT_PORTS: Dict[FrameworkType, int] = {
    # Frontend
    FrameworkType.REACT_VITE: 5173,
    FrameworkType.REACT_CRA: 3000,
    FrameworkType.NEXTJS: 3000,
    FrameworkType.VUE: 5173,
    FrameworkType.ANGULAR: 4200,
    FrameworkType.SVELTE: 5173,
    FrameworkType.STATIC_HTML: 80,

    # Backend Node.js
    FrameworkType.NODE_EXPRESS: 3000,

    # Python
    FrameworkType.PYTHON_FLASK: 5000,
    FrameworkType.PYTHON_FASTAPI: 8000,
    FrameworkType.PYTHON_DJANGO: 8000,
    FrameworkType.PYTHON_STREAMLIT: 8501,
    FrameworkType.PYTHON_ML: 8888,  # Jupyter notebook default

    # Java
    FrameworkType.SPRING_BOOT: 8080,
    FrameworkType.ANDROID: 5555,  # ADB default

    # Go
    FrameworkType.GO: 8080,

    # Rust
    FrameworkType.RUST: 8080,

    # iOS
    FrameworkType.IOS_SWIFT: 8080,

    # Blockchain
    FrameworkType.SOLIDITY: 8545,  # Hardhat/Ganache default
    FrameworkType.RUST_SOLANA: 8899,  # Solana validator default

    # Fullstack (frontend port - backend gets +1000)
    FrameworkType.FULLSTACK_REACT_SPRING: 5173,
    FrameworkType.FULLSTACK_REACT_EXPRESS: 5173,
    FrameworkType.FULLSTACK_REACT_FASTAPI: 5173,

    # Other
    FrameworkType.UNKNOWN: 3000,
}


# Port detection patterns from logs
PORT_PATTERNS = [
    r'https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)',
    r'Local:\s*https?://[^:]+:(\d+)',
    r'running\s+(?:on|at)\s+(?:port\s+)?(\d+)',
    r'server\s+(?:started|listening|running)\s+(?:on|at)\s+(?:port\s+)?(\d+)',
    r'listening\s+(?:on|at)\s+(?:port\s+)?(\d+)',
    r'Tomcat started on port\(s\): (\d+)',
    r'Started .+ in .+ seconds .+ port\(s\): (\d+)',
    r'Uvicorn running on .+:(\d+)',
    r'Streamlit.*running.*:(\d+)',
    r'Development server.*:(\d+)',
    r'Ready on http://[^:]+:(\d+)',
    r'Network: http://[^:]+:(\d+)',
]


class DockerExecutor:
    """Handles Docker-based project execution with fallback to direct execution"""

    def __init__(self, project_base_path: str = "/tmp/student_projects"):
        self.project_base_path = Path(project_base_path)
        self._running_containers: Dict[str, str] = {}  # project_id -> container_id
        self._assigned_ports: Dict[str, int] = {}  # project_id -> host_port
        self._running_processes: Dict[str, asyncio.subprocess.Process] = {}  # For direct execution
        self._docker_available: Optional[bool] = None  # Cache Docker availability
        self._fix_in_progress: Dict[str, bool] = {}  # Track fix status per project
        self._fix_lock = threading.Lock()  # Lock for thread-safe fix status updates
        self._background_monitors: Dict[str, bool] = {}  # Track background monitors per project

    def _should_use_ai_fixer(self, error_message: str, project_path: Path) -> bool:
        """
        Determine if an error should be routed directly to AI fixer.

        DYNAMIC APPROACH: Instead of hardcoding specific fixes, detect error COMPLEXITY
        and route to AI for anything that requires understanding code context.

        Returns True for:
        - Compilation errors (Java, TypeScript, Go, Rust, etc.)
        - Build failures with multiple errors
        - Import/symbol resolution errors
        - Type errors requiring code analysis
        - Any error in a language/framework where ProductionAutoFixer has no patterns

        Returns False for:
        - Simple missing package errors (npm install X, pip install X)
        - Port in use errors
        - Simple config issues with known fixes
        """
        error_lower = error_message.lower()

        # ===== ALWAYS use AI for these complex error types =====

        # 1. Compilation/Build errors (require code understanding)
        # NOTE: Be very specific to avoid false positives from Spring Boot logs
        compilation_indicators = [
            'cannot find symbol',
            'package .* does not exist',
            'compilation error',
            'compile error',
            'compilation failure',
            '[error] compilation error',  # Maven compilation error (specific)
            '[error] failed to execute goal',  # Maven goal failure (specific)
            'cannot resolve',
            'unresolved reference',
            'undefined reference',
            'incompatible types',
            'type mismatch',
            'missing method',
            'method .* not found',
            'no such method',
            'unexpected token',
            'expected.*but got',
            'enoent: no such file',  # File not found (Vite/Node)
            '[plugin:vite:',  # Vite plugin errors
            'failed to resolve import',
        ]

        # Patterns that should NOT trigger AI fixer (false positives)
        false_positive_indicators = [
            '[info] build failure',  # Maven dependency output (NOT an error)
            'build success',
            'started application',
            'tomcat started',
            '\\/ ___ \'',  # Spring Boot ASCII art
        ]

        # Check for false positives first
        if any(fp in error_lower for fp in false_positive_indicators):
            return False

        if any(indicator in error_lower for indicator in compilation_indicators):
            return True

        # 2. Multiple errors (complex debugging needed)
        error_count_patterns = [
            r'\d+ error',
            r'\d+ errors',
            r'found \d+ error',
            r'\[info\] \d+ error',
        ]
        import re
        for pattern in error_count_patterns:
            match = re.search(pattern, error_lower)
            if match:
                # Extract number and check if > 1
                nums = re.findall(r'\d+', match.group())
                if nums and int(nums[0]) > 1:
                    return True

        # 3. Java/Maven/Gradle projects (complex build systems)
        pom_exists = (project_path / "pom.xml").exists() or (project_path / "backend/pom.xml").exists()
        gradle_exists = (project_path / "build.gradle").exists() or (project_path / "backend/build.gradle").exists()

        if pom_exists or gradle_exists:
            # Any Java build error should use AI
            java_indicators = ['maven', 'mvn', 'gradle', '.java:', '[error]', 'javac']
            if any(ind in error_lower for ind in java_indicators):
                return True

        # 4. Python import/type errors (need code analysis)
        python_complex = [
            'importerror',
            'modulenotfound',
            'attributeerror',
            'typeerror',
            'nameerror',
            'indentationerror',
        ]
        if any(p in error_lower for p in python_complex):
            # Check if it's a simple pip install case
            if 'no module named' in error_lower:
                # This could be simple pip install - let ProductionAutoFixer try first
                return False
            return True

        # 5. Go/Rust compilation errors
        go_rust_indicators = [
            'cannot find package',
            'undefined:',
            'error[e',  # Rust error codes like error[E0432]
            'unresolved import',
        ]
        if any(ind in error_lower for ind in go_rust_indicators):
            return True

        # ===== Let ProductionAutoFixer handle simple cases =====

        # Simple cases that have pattern-based fixes
        simple_patterns = [
            'eaddrinuse',  # Port in use
            'enoent',      # Simple file not found
            'npm warn',    # Just warnings
            'deprecated',  # Deprecation warnings
        ]
        if any(p in error_lower for p in simple_patterns):
            return False

        # If we're not sure, default to AI for safety
        # Better to use AI and succeed than use patterns and fail
        return True

    def _start_background_error_monitor(
        self,
        project_id: str,
        project_path: Path,
        process,  # subprocess.Popen
        command: str,
        error_patterns: List[str],
        user_id: Optional[str] = None
    ) -> None:
        """
        Start a background thread to continuously monitor dev server output for errors.
        This handles errors that occur AFTER the server has started (e.g., PostCSS errors
        that happen when the browser requests CSS files).
        """
        # Avoid starting multiple monitors for the same project
        if self._background_monitors.get(project_id, False):
            logger.debug(f"[DockerExecutor:{project_id}] Background monitor already running")
            return

        import threading

        def monitor_output():
            self._background_monitors[project_id] = True
            error_buffer = []
            last_fix_time = 0
            FIX_COOLDOWN = 30  # Minimum seconds between fix attempts

            try:
                logger.info(f"[DockerExecutor:{project_id}] Background error monitor started")
                while process.poll() is None:  # While process is running
                    try:
                        line = process.stdout.readline()
                        if not line:
                            continue

                        line = line.strip() if isinstance(line, str) else line.decode('utf-8', errors='replace').strip()
                        if not line:
                            continue

                        error_buffer.append(line)
                        if len(error_buffer) > 100:
                            error_buffer.pop(0)

                        # Check for critical errors
                        if any(p in line for p in error_patterns):
                            import time
                            current_time = time.time()

                            # Rate limit fix attempts
                            if current_time - last_fix_time < FIX_COOLDOWN:
                                logger.debug(f"[DockerExecutor:{project_id}] Background monitor: Cooldown active, skipping fix")
                                continue

                            last_fix_time = current_time
                            full_context = '\n'.join(error_buffer[-50:])
                            logger.info(f"[DockerExecutor:{project_id}] Background monitor detected error: {line[:100]}")

                            # Trigger auto-fix
                            self._trigger_auto_fix_background(
                                project_id=project_id,
                                project_path=project_path,
                                error_message=full_context,
                                command=command,
                                user_id=user_id
                            )

                    except Exception as e:
                        logger.debug(f"[DockerExecutor:{project_id}] Background monitor read error: {e}")
                        break

            except Exception as e:
                logger.error(f"[DockerExecutor:{project_id}] Background monitor error: {e}")
            finally:
                self._background_monitors[project_id] = False
                logger.info(f"[DockerExecutor:{project_id}] Background error monitor stopped")

        # Start the monitor thread
        monitor_thread = threading.Thread(target=monitor_output, daemon=True, name=f"error-monitor-{project_id}")
        monitor_thread.start()

    def _trigger_auto_fix_background(
        self,
        project_id: str,
        project_path: Path,
        error_message: str,
        command: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        PRODUCTION-READY Auto-Fix System for 100k+ Users

        Architecture:
        1. ProductionAutoFixer (deterministic, fast, free) - handles 80% of errors
        2. SDK Fixer Agent (AI-powered) - handles complex file creation
        3. Rate limiting, circuit breaker, caching for production scale

        Key Production Features:
        - Deterministic fixes first (no AI = fast + cheap)
        - Rate limiting per project (10/min, 100/hour)
        - Circuit breaker (5 failures = 2min cooldown)
        - Fix caching (don't fix same error twice)
        - Full metrics and logging
        - Pending error queue for errors that arrive during a fix
        """
        # Extract user_id from project_path if not provided
        # Path structure: C:\tmp\sandbox\workspace\{user_id}\{project_id}
        if not user_id:
            try:
                path_parts = str(project_path).replace('\\', '/').split('/')
                # Find 'workspace' and get the next part as user_id
                if 'workspace' in path_parts:
                    workspace_idx = path_parts.index('workspace')
                    if workspace_idx + 1 < len(path_parts):
                        user_id = path_parts[workspace_idx + 1]
                        logger.info(f"[DockerExecutor:{project_id}] Extracted user_id from path: {user_id}")
            except Exception as e:
                logger.warning(f"[DockerExecutor:{project_id}] Could not extract user_id from path: {e}")
        # Initialize pending errors queue if needed
        if not hasattr(self, '_pending_errors'):
            self._pending_errors = {}

        # Thread-safe check and set for fix_in_progress to prevent race conditions
        # Multiple threads (reader thread + main loop) may try to trigger auto-fix simultaneously
        with self._fix_lock:
            # If a fix is in progress, queue this error for later (unless it's a duplicate)
            if self._fix_in_progress.get(project_id, False):
                # Check if this is a high-priority error (real errors should be processed)
                high_priority_patterns = [
                    'class does not exist',  # Tailwind
                    '[postcss]',
                    '[vite]',
                    'Module not found',
                    'Cannot find module',
                    'SyntaxError',
                    'TypeError',
                ]
                is_high_priority = any(p in error_message for p in high_priority_patterns)

                if is_high_priority:
                    # Store the error for processing after current fix completes
                    if project_id not in self._pending_errors:
                        self._pending_errors[project_id] = []
                    # Avoid duplicate errors in queue
                    error_hash = hash(error_message[:500])
                    existing_hashes = [hash(e['error'][:500]) for e in self._pending_errors.get(project_id, [])]
                    if error_hash not in existing_hashes:
                        self._pending_errors[project_id].append({
                            'error': error_message,
                            'command': command,
                            'user_id': user_id,
                            'project_path': project_path,
                        })
                        logger.info(f"[DockerExecutor:{project_id}] Queued high-priority error for later processing")

                logger.info(f"[DockerExecutor:{project_id}] Fix already in progress, skipping (queued={is_high_priority})")
                return

            # Atomically mark fix as in progress BEFORE releasing the lock
            # This prevents another thread from also passing the check
            self._fix_in_progress[project_id] = True

        async def run_production_auto_fix():
            """
            SIMPLIFIED Auto-Fix - Bolt.new Style

            Let AI decide what's an error and how to fix it.
            No complex routing, no pattern matching, just simple AI-powered fixing.
            """
            try:
                # Fix already marked as in progress above (atomically with lock)
                logger.info(f"[DockerExecutor:{project_id}] [SIMPLE] Auto-fix triggered")

                # First, let SimpleFixer decide if this is a real error
                should_fix = await simple_fixer.should_fix(None, error_message)

                if not should_fix:
                    logger.info(f"[DockerExecutor:{project_id}] SimpleFixer: No fix needed (not a real error)")
                    return

                # Use SimpleFixer for all errors - let AI decide
                logger.info(f"[DockerExecutor:{project_id}] Using SimpleFixer (Bolt.new style)")
                result = await simple_fixer.fix(
                    project_path=project_path,
                    command=command or "unknown",
                    output=error_message,
                    exit_code=None
                )

                # Log result
                if result.success:
                    logger.info(f"[DockerExecutor:{project_id}] [SIMPLE] Fix successful: {result.message}")
                    logger.info(f"[DockerExecutor:{project_id}] [SIMPLE] Files modified: {result.files_modified}")

                    # Notify frontend
                    log_bus = get_log_bus(project_id)
                    if log_bus:
                        log_bus.add_log(
                            source="autofixer",
                            level="success",
                            message=f"[OK] Auto-fix applied successfully"
                        )
                else:
                    logger.warning(f"[DockerExecutor:{project_id}] [SIMPLE] Fix failed: {result.message}")

            except Exception as e:
                logger.error(f"[DockerExecutor:{project_id}] [PRODUCTION] Auto-fix error: {e}")
                import traceback
                logger.error(traceback.format_exc())
            finally:
                # Thread-safe clear of fix_in_progress
                with self._fix_lock:
                    self._fix_in_progress[project_id] = False

                    # Process any queued errors (get them while holding the lock)
                    pending = []
                    if hasattr(self, '_pending_errors') and project_id in self._pending_errors:
                        pending = self._pending_errors.pop(project_id, [])

                # Process pending errors outside the lock to avoid deadlock
                if pending:
                    logger.info(f"[DockerExecutor:{project_id}] Processing {len(pending)} queued errors")
                    for queued_error in pending[:3]:  # Limit to 3 queued errors to avoid infinite loops
                        # Schedule the queued error to be processed
                        self._trigger_auto_fix_background(
                            project_id=project_id,
                            project_path=queued_error['project_path'],
                            error_message=queued_error['error'],
                            command=queued_error.get('command'),
                            user_id=queued_error.get('user_id'),
                        )
                        break  # Only process one at a time

        # Create background task - handle both async and threaded contexts
        try:
            # Try to get the running event loop (works in async context)
            loop = asyncio.get_running_loop()
            asyncio.create_task(run_production_auto_fix())
        except RuntimeError:
            # No running event loop - we're in a thread
            # Run in a new event loop in this thread
            import threading
            def run_in_thread():
                try:
                    asyncio.run(run_production_auto_fix())
                except Exception as e:
                    logger.error(f"[DockerExecutor:{project_id}] Auto-fix thread error: {e}")

            fix_thread = threading.Thread(target=run_in_thread, daemon=True, name=f"auto-fix-{project_id}")
            fix_thread.start()
            logger.info(f"[DockerExecutor:{project_id}] Started auto-fix in background thread")

    async def _run_universal_fix(
        self,
        autofixer: UniversalAutoFixer,
        error_message: str,
        project_id: str
    ) -> None:
        """Run UniversalAutoFixer for non-missing-file errors"""
        # Try to fix the error
        success = await autofixer.fix_error(error_message)

        if success:
            logger.info(f"[DockerExecutor:{project_id}] ✅ UNIVERSAL AUTO-FIX successful!")
            logger.info(f"[DockerExecutor:{project_id}] Fixes applied: {autofixer.fixes_applied}")

            # Notify frontend that fix was applied (trigger reload/rebuild)
            log_bus = get_log_bus(project_id)
            if log_bus:
                log_bus.add_log(
                    source="autofixer",
                    level="success",
                    message=f"Auto-fix applied: {', '.join(autofixer.fixes_applied) or 'Files updated'}"
                )
        else:
            logger.warning(f"[DockerExecutor:{project_id}] ⚠️ UNIVERSAL AUTO-FIX: First attempt failed, trying AI fix...")

            # Try AI-powered fix as fallback
            result = await autofixer.fix_with_ai(error_message)
            if result.get("success"):
                logger.info(f"[DockerExecutor:{project_id}] ✅ AI fix successful: {result.get('files_modified', [])}")
            else:
                logger.error(f"[DockerExecutor:{project_id}] ❌ AUTO-FIX failed: {result.get('error', 'Unknown')}")

    async def _get_context_files_for_fix(
        self,
        project_path: Path,
        error_message: str
    ) -> Dict[str, str]:
        """
        Get context files for SDK Fixer Agent.

        DYNAMIC approach: Include ALL build config files and error-mentioned files
        so Claude can reason about the fix without hardcoded patterns.
        """
        context_files = {}
        import re

        # ===== PHASE 1: Include ALL build configuration files =====
        # These are critical for Claude to understand project structure
        build_config_files = [
            # Java/Maven
            "pom.xml",
            "backend/pom.xml",
            "build.gradle",
            "backend/build.gradle",
            "settings.gradle",
            "backend/settings.gradle",
            # Node.js
            "package.json",
            "frontend/package.json",
            "package-lock.json",
            "frontend/package-lock.json",
            # Python
            "requirements.txt",
            "backend/requirements.txt",
            "pyproject.toml",
            "backend/pyproject.toml",
            "setup.py",
            # Config files
            "frontend/vite.config.ts",
            "frontend/vite.config.js",
            "frontend/tsconfig.json",
            "frontend/tsconfig.node.json",
            "tsconfig.json",
            "tsconfig.node.json",
            "frontend/tailwind.config.js",
            "frontend/postcss.config.js",
            # Application config
            "backend/src/main/resources/application.properties",
            "backend/src/main/resources/application.yml",
            "backend/src/main/resources/application.yaml",
            ".env",
            "backend/.env",
            "frontend/.env",
        ]

        for file_rel in build_config_files:
            file_path = project_path / file_rel
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    # Limit size to avoid token overflow
                    if len(content) < 50000:
                        context_files[file_rel] = content
                        logger.info(f"[DockerExecutor] Added build config: {file_rel}")
                except Exception as e:
                    logger.warning(f"[DockerExecutor] Could not read {file_rel}: {e}")

        # ===== PHASE 2: Extract files mentioned in error message =====
        # Parse error to find file paths (works for ALL languages)
        file_path_patterns = [
            # Java/Maven errors: [ERROR] /path/to/File.java:[line]:[col]: error
            r'\[ERROR\]\s+([A-Za-z]:[/\\][^\s:]+\.java)',  # Windows path
            r'\[ERROR\]\s+(/[^\s:]+\.java)',  # Unix path
            r'([A-Za-z]:[/\\][^\s:]+\.(java|kt|scala|groovy))',  # Any JVM file Windows
            r'(/[^\s:]+\.(java|kt|scala|groovy))',  # Any JVM file Unix
            # Python errors
            r'File "([^"]+\.py)"',
            # Node.js/TypeScript errors
            r'at\s+([^\s]+\.(ts|tsx|js|jsx))',
            r'Failed to resolve import ["\']([^"\']+)["\']',
            r'Cannot find module ["\']([^"\']+)["\']',
            # Generic path patterns
            r'(src/[^\s:]+\.(java|ts|tsx|js|py|go|rs))',
            r'(backend/[^\s:]+\.(java|ts|tsx|js|py|go|rs))',
            r'(frontend/[^\s:]+\.(ts|tsx|js|jsx))',
        ]

        error_mentioned_files = set()
        for pattern in file_path_patterns:
            matches = re.findall(pattern, error_message, re.IGNORECASE)
            for match in matches:
                # Handle tuple matches from groups
                if isinstance(match, tuple):
                    match = match[0]
                if match:
                    error_mentioned_files.add(match)

        # Read files mentioned in error
        for file_mention in error_mentioned_files:
            # Try to resolve to actual path
            possible_paths = [
                project_path / file_mention,
                project_path / file_mention.lstrip('/'),
                # Handle absolute paths by making them relative
            ]

            # Also try to find by filename in common directories
            filename = Path(file_mention).name
            for src_dir in ["backend/src", "frontend/src", "src"]:
                src_path = project_path / src_dir
                if src_path.exists():
                    for found_file in src_path.rglob(filename):
                        possible_paths.append(found_file)

            for file_path in possible_paths:
                if isinstance(file_path, Path) and file_path.exists() and file_path.is_file():
                    try:
                        rel_path = str(file_path.relative_to(project_path))
                        if rel_path not in context_files:
                            content = file_path.read_text(encoding='utf-8')
                            if len(content) < 30000:
                                context_files[rel_path] = content
                                logger.info(f"[DockerExecutor] Added error file: {rel_path}")
                        break
                    except Exception:
                        pass

        # ===== PHASE 3: For Java projects, include key source files =====
        # Check if this is a Java project
        pom_exists = (project_path / "pom.xml").exists() or (project_path / "backend/pom.xml").exists()
        gradle_exists = (project_path / "build.gradle").exists() or (project_path / "backend/build.gradle").exists()

        if pom_exists or gradle_exists:
            # Find Java source files mentioned in error or key files
            java_src_dirs = ["backend/src/main/java", "src/main/java"]
            for src_dir in java_src_dirs:
                src_path = project_path / src_dir
                if src_path.exists():
                    # Add all Java files (up to 20 to avoid token overflow)
                    java_files = list(src_path.rglob("*.java"))[:20]
                    for java_file in java_files:
                        try:
                            rel_path = str(java_file.relative_to(project_path))
                            if rel_path not in context_files:
                                content = java_file.read_text(encoding='utf-8')
                                if len(content) < 20000:
                                    context_files[rel_path] = content
                                    logger.info(f"[DockerExecutor] Added Java source: {rel_path}")
                        except Exception:
                            pass

        # ===== PHASE 4: Include main entry points =====
        entry_points = [
            "frontend/src/App.tsx",
            "frontend/src/main.tsx",
            "frontend/src/index.tsx",
            "src/App.tsx",
            "src/main.tsx",
            "src/index.tsx",
            "backend/src/main/java/**/Application.java",  # Spring Boot entry
            "backend/app/main.py",  # FastAPI entry
            "backend/manage.py",  # Django entry
        ]

        for entry in entry_points:
            if "*" in entry:
                # Handle glob patterns
                for match in project_path.glob(entry):
                    try:
                        rel_path = str(match.relative_to(project_path))
                        if rel_path not in context_files:
                            content = match.read_text(encoding='utf-8')
                            context_files[rel_path] = content
                            logger.info(f"[DockerExecutor] Added entry point: {rel_path}")
                    except Exception:
                        pass
            else:
                file_path = project_path / entry
                if file_path.exists():
                    try:
                        rel_path = entry
                        if rel_path not in context_files:
                            content = file_path.read_text(encoding='utf-8')
                            context_files[rel_path] = content
                            logger.info(f"[DockerExecutor] Added entry point: {rel_path}")
                    except Exception:
                        pass

        logger.info(f"[DockerExecutor] Total context files for AI: {len(context_files)}")
        return context_files

    async def _validate_imports_proactively(
        self,
        project_id: str,
        project_path: Path,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Proactively validate all local imports in React/TypeScript files BEFORE running the server.

        This catches "Failed to resolve import" errors before Vite even starts, allowing us to
        trigger the SDK Fixer Agent to create missing files.

        Returns True if all imports are valid, False if missing files were detected and fix was triggered.
        """
        missing_imports = []

        # Find all source directories
        src_dirs = ["src", "frontend/src"]

        for src_dir in src_dirs:
            src_path = project_path / src_dir
            if not src_path.exists():
                continue

            # Scan all TypeScript/JavaScript files
            for ext in ["*.tsx", "*.ts", "*.jsx", "*.js"]:
                for source_file in src_path.rglob(ext):
                    try:
                        content = source_file.read_text(encoding='utf-8')

                        # Find all local imports (starting with ./ or ../)
                        import_patterns = [
                            r"import\s+(?:[\w*{},\s]+)\s+from\s+['\"](\./[^'\"]+|\.\.\/[^'\"]+)['\"]",
                            r"import\s+['\"](\./[^'\"]+|\.\.\/[^'\"]+)['\"]",
                        ]

                        for pattern in import_patterns:
                            matches = re.findall(pattern, content)
                            for import_path in matches:
                                # Resolve the import path relative to the source file
                                file_dir = source_file.parent

                                # Try different extensions
                                possible_files = []
                                if not any(import_path.endswith(e) for e in ['.tsx', '.ts', '.jsx', '.js', '.css', '.json']):
                                    # No extension - try common ones
                                    for ext_try in ['.tsx', '.ts', '.jsx', '.js', '/index.tsx', '/index.ts', '/index.jsx', '/index.js']:
                                        possible_files.append(file_dir / (import_path + ext_try))
                                else:
                                    possible_files.append(file_dir / import_path)

                                # Check if any of the possible files exist
                                file_exists = any(p.resolve().exists() for p in possible_files)

                                if not file_exists:
                                    rel_source = str(source_file.relative_to(project_path))
                                    missing_imports.append({
                                        "source_file": rel_source,
                                        "import_path": import_path,
                                        "expected_paths": [str(p.relative_to(project_path)) for p in possible_files[:2]]
                                    })

                    except Exception as e:
                        logger.warning(f"[DockerExecutor] Error scanning imports in {source_file}: {e}")

        if not missing_imports:
            logger.info(f"[DockerExecutor:{project_id}] ✅ All imports validated - no missing files detected")
            return True

        # We have missing imports! Build an error message and trigger SDK Fixer
        logger.warning(f"[DockerExecutor:{project_id}] ⚠️ Found {len(missing_imports)} missing imports!")
        for mi in missing_imports:
            logger.warning(f"  - {mi['source_file']} imports '{mi['import_path']}' which doesn't exist")

        # Build error message in Vite-style format
        error_parts = []
        for mi in missing_imports[:5]:  # Limit to first 5 to avoid overwhelming the fixer
            error_parts.append(
                f'Failed to resolve import "{mi["import_path"]}" from "{mi["source_file"]}". Does the file exist?'
            )

        error_message = "\n".join(error_parts)
        logger.info(f"[DockerExecutor:{project_id}] 🔧 Triggering proactive SDK Fixer for missing imports...")

        # Trigger SDK Fixer in background
        self._trigger_auto_fix_background(
            project_id=project_id,
            project_path=project_path,
            error_message=error_message,
            command="proactive_import_validation",
            user_id=user_id
        )

        return False

    def detect_framework(self, project_path: Path) -> FrameworkType:
        """Detect the framework type from project files - supports ALL technologies!"""

        # ===== FULLSTACK MONOREPO (Check first - has frontend/ and backend/ folders) =====
        frontend_dir = project_path / "frontend"
        backend_dir = project_path / "backend"

        if frontend_dir.exists() and backend_dir.exists():
            # Check what type of frontend
            frontend_pkg = frontend_dir / "package.json"
            has_react_frontend = False
            has_vite = False
            if frontend_pkg.exists():
                try:
                    with open(frontend_pkg, 'r') as f:
                        pkg = json.load(f)
                        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                        has_react_frontend = "react" in deps
                        has_vite = "vite" in deps or "@vitejs/plugin-react" in deps
                except:
                    pass

            # Check what type of backend (check for actual files, not just folder existence)
            has_spring_backend = (backend_dir / "pom.xml").exists() or (backend_dir / "build.gradle").exists()
            has_express_backend = (backend_dir / "package.json").exists()
            has_fastapi_backend = (backend_dir / "requirements.txt").exists() or (backend_dir / "main.py").exists()
            backend_has_files = has_spring_backend or has_express_backend or has_fastapi_backend

            if has_react_frontend:
                if has_spring_backend:
                    return FrameworkType.FULLSTACK_REACT_SPRING
                elif has_fastapi_backend:
                    return FrameworkType.FULLSTACK_REACT_FASTAPI
                elif has_express_backend:
                    return FrameworkType.FULLSTACK_REACT_EXPRESS
                elif not backend_has_files:
                    # Frontend-only project with empty backend folder
                    # Detect the frontend framework and we'll run from frontend/ dir
                    logger.info(f"[FrameworkDetection] Detected frontend-only project in {frontend_dir}")
                    if has_vite:
                        return FrameworkType.REACT_VITE
                    else:
                        return FrameworkType.REACT_CRA

        # ===== ANDROID (Check first - has build.gradle but different from Spring) =====
        android_manifest = project_path / "app" / "src" / "main" / "AndroidManifest.xml"
        if android_manifest.exists():
            return FrameworkType.ANDROID
        # Also check for root-level Android indicators
        if (project_path / "settings.gradle").exists() or (project_path / "settings.gradle.kts").exists():
            gradle_file = project_path / "build.gradle"
            gradle_kts = project_path / "build.gradle.kts"
            if gradle_file.exists() or gradle_kts.exists():
                try:
                    content = ""
                    if gradle_file.exists():
                        with open(gradle_file, 'r') as f:
                            content = f.read()
                    elif gradle_kts.exists():
                        with open(gradle_kts, 'r') as f:
                            content = f.read()
                    if "com.android" in content or "android {" in content:
                        return FrameworkType.ANDROID
                except:
                    pass

        # ===== iOS/SWIFT =====
        # Check for Xcode project or Package.swift
        if (project_path / "Package.swift").exists():
            return FrameworkType.IOS_SWIFT
        # Check for .xcodeproj or .xcworkspace
        for item in project_path.iterdir():
            if item.suffix in ['.xcodeproj', '.xcworkspace']:
                return FrameworkType.IOS_SWIFT
        # Check for Podfile (CocoaPods)
        if (project_path / "Podfile").exists():
            return FrameworkType.IOS_SWIFT

        # ===== BLOCKCHAIN - SOLIDITY =====
        # Check for Hardhat, Truffle, or Foundry
        if (project_path / "hardhat.config.js").exists() or (project_path / "hardhat.config.ts").exists():
            return FrameworkType.SOLIDITY
        if (project_path / "truffle-config.js").exists():
            return FrameworkType.SOLIDITY
        if (project_path / "foundry.toml").exists():
            return FrameworkType.SOLIDITY
        # Check for .sol files in contracts folder
        contracts_dir = project_path / "contracts"
        if contracts_dir.exists():
            for item in contracts_dir.iterdir():
                if item.suffix == '.sol':
                    return FrameworkType.SOLIDITY

        # ===== BLOCKCHAIN - SOLANA (Rust) =====
        if (project_path / "Anchor.toml").exists():
            return FrameworkType.RUST_SOLANA

        # ===== RUST =====
        if (project_path / "Cargo.toml").exists():
            # Check if it's a Solana project
            try:
                with open(project_path / "Cargo.toml", 'r') as f:
                    cargo_content = f.read()
                    if "anchor-lang" in cargo_content or "solana-program" in cargo_content:
                        return FrameworkType.RUST_SOLANA
            except:
                pass
            return FrameworkType.RUST

        # ===== NODE.JS / FRONTEND PROJECTS =====
        package_json_path = project_path / "package.json"
        if package_json_path.exists():
            try:
                with open(package_json_path, 'r') as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                    # Check for specific frameworks
                    if "next" in deps:
                        return FrameworkType.NEXTJS
                    elif "svelte" in deps or "@sveltejs/kit" in deps:
                        return FrameworkType.SVELTE
                    elif "vite" in deps:
                        if "vue" in deps:
                            return FrameworkType.VUE
                        if "svelte" in deps:
                            return FrameworkType.SVELTE
                        return FrameworkType.REACT_VITE
                    elif "react-scripts" in deps:
                        return FrameworkType.REACT_CRA
                    elif "react" in deps:
                        return FrameworkType.REACT_VITE  # Default React to Vite
                    elif "vue" in deps:
                        return FrameworkType.VUE
                    elif "@angular/core" in deps:
                        return FrameworkType.ANGULAR
                    # Blockchain JS libraries
                    elif "hardhat" in deps or "ethers" in deps or "web3" in deps:
                        return FrameworkType.SOLIDITY
                    elif "express" in deps:
                        return FrameworkType.NODE_EXPRESS
                    else:
                        return FrameworkType.NODE_EXPRESS  # Default Node.js
            except Exception as e:
                logger.warning(f"Error reading package.json: {e}")

        # ===== PYTHON PROJECTS =====
        requirements_path = project_path / "requirements.txt"
        pyproject_path = project_path / "pyproject.toml"

        python_deps = ""
        if requirements_path.exists():
            try:
                with open(requirements_path, 'r') as f:
                    python_deps = f.read().lower()
            except:
                pass
        if pyproject_path.exists():
            try:
                with open(pyproject_path, 'r') as f:
                    python_deps += f.read().lower()
            except:
                pass

        if python_deps:
            # Web frameworks - check FIRST (before ML detection)
            # Streamlit apps often use pandas/numpy but should run as streamlit, not jupyter
            if "streamlit" in python_deps:
                return FrameworkType.PYTHON_STREAMLIT
            elif "fastapi" in python_deps:
                return FrameworkType.PYTHON_FASTAPI
            elif "django" in python_deps:
                return FrameworkType.PYTHON_DJANGO
            elif "flask" in python_deps:
                return FrameworkType.PYTHON_FLASK

            # AI/ML frameworks (check AFTER web frameworks)
            ml_indicators = ['tensorflow', 'torch', 'pytorch', 'keras', 'scikit-learn',
                            'sklearn', 'transformers', 'huggingface', 'opencv', 'cv2',
                            'numpy', 'pandas', 'matplotlib', 'seaborn', 'jupyter',
                            'notebook', 'xgboost', 'lightgbm', 'catboost', 'spacy',
                            'nltk', 'gensim', 'openai', 'langchain', 'llama']
            if any(lib in python_deps for lib in ml_indicators):
                return FrameworkType.PYTHON_ML

            # Default Python fallback
            return FrameworkType.PYTHON_FLASK

        # ===== JAVA - SPRING BOOT =====
        pom_path = project_path / "pom.xml"
        build_gradle = project_path / "build.gradle"
        build_gradle_kts = project_path / "build.gradle.kts"

        if pom_path.exists():
            return FrameworkType.SPRING_BOOT
        if build_gradle.exists() or build_gradle_kts.exists():
            # It's a Java/Gradle project (not Android - we checked above)
            return FrameworkType.SPRING_BOOT

        # ===== GO =====
        go_mod_path = project_path / "go.mod"
        if go_mod_path.exists():
            return FrameworkType.GO

        # ===== RUBY ON RAILS =====
        gemfile_path = project_path / "Gemfile"
        if gemfile_path.exists():
            try:
                with open(gemfile_path, 'r') as f:
                    gemfile_content = f.read().lower()
                    if "rails" in gemfile_content:
                        return FrameworkType.RUBY_RAILS
            except:
                pass

        # ===== PHP LARAVEL =====
        composer_json = project_path / "composer.json"
        artisan_file = project_path / "artisan"
        if artisan_file.exists():
            return FrameworkType.PHP_LARAVEL
        if composer_json.exists():
            try:
                with open(composer_json, 'r') as f:
                    composer = json.load(f)
                    deps = {**composer.get("require", {}), **composer.get("require-dev", {})}
                    if "laravel/framework" in deps:
                        return FrameworkType.PHP_LARAVEL
            except:
                pass

        # ===== .NET CORE =====
        # Check for .csproj or .sln files
        csproj_files = list(project_path.glob("*.csproj")) + list(project_path.glob("**/*.csproj"))
        sln_files = list(project_path.glob("*.sln"))
        if csproj_files or sln_files:
            return FrameworkType.DOTNET

        # ===== STATIC HTML =====
        index_html_path = project_path / "index.html"
        if index_html_path.exists():
            return FrameworkType.STATIC_HTML

        return FrameworkType.UNKNOWN

    def get_effective_working_directory(self, project_path: Path, framework: FrameworkType) -> Path:
        """
        Get the effective working directory for running commands.

        For frontend-only projects in subfolder structure (e.g., frontend/ folder with empty backend/),
        returns the frontend/ directory instead of the root.
        For fullstack projects, returns the root (they handle subdirs in commands).
        """
        # IMPORTANT: Fullstack frameworks ALWAYS run from project root
        # because their commands use 'cd frontend' and 'cd backend' relative paths
        fullstack_frameworks = [
            FrameworkType.FULLSTACK_REACT_SPRING,
            FrameworkType.FULLSTACK_REACT_EXPRESS,
            FrameworkType.FULLSTACK_REACT_FASTAPI,
        ]
        if framework in fullstack_frameworks:
            logger.info(f"[WorkingDir] Fullstack project - using project root for {framework.value}")
            return project_path

        frontend_dir = project_path / "frontend"
        backend_dir = project_path / "backend"

        # Check if this is a frontend-only project with subfolder structure
        if frontend_dir.exists() and backend_dir.exists():
            # Check if backend is empty (no actual files)
            has_backend_files = any([
                (backend_dir / "pom.xml").exists(),
                (backend_dir / "build.gradle").exists(),
                (backend_dir / "package.json").exists(),
                (backend_dir / "requirements.txt").exists(),
                (backend_dir / "main.py").exists(),
            ])

            # Check if frontend has package.json
            frontend_has_pkg = (frontend_dir / "package.json").exists()

            if frontend_has_pkg and not has_backend_files:
                # Frontend-only project in subfolder - run from frontend/
                logger.info(f"[WorkingDir] Using frontend/ as working directory for {framework.value}")
                return frontend_dir

        # Check if there's no root package.json but frontend/ has one
        # BUT only if backend doesn't have real files (indicating fullstack)
        root_pkg = project_path / "package.json"
        if not root_pkg.exists() and frontend_dir.exists():
            # Double-check it's NOT a fullstack project
            has_backend_files = backend_dir.exists() and any([
                (backend_dir / "pom.xml").exists(),
                (backend_dir / "build.gradle").exists(),
                (backend_dir / "package.json").exists(),
                (backend_dir / "requirements.txt").exists(),
                (backend_dir / "main.py").exists(),
            ])
            if not has_backend_files and (frontend_dir / "package.json").exists():
                logger.info(f"[WorkingDir] No root package.json, using frontend/ for {framework.value}")
                return frontend_dir

        # Default: use project root
        return project_path

    def generate_dockerfile(self, project_path: Path, framework: FrameworkType) -> str:
        """Generate appropriate Dockerfile for the framework"""
        return DOCKERFILE_TEMPLATES.get(framework, DOCKERFILE_TEMPLATES[FrameworkType.UNKNOWN])

    def generate_dockerignore(self, framework: FrameworkType) -> str:
        """Generate .dockerignore file content"""
        base_ignores = [
            "node_modules",
            ".git",
            ".gitignore",
            ".env",
            ".env.local",
            ".env.*.local",
            "*.log",
            "npm-debug.log*",
            ".DS_Store",
            "Thumbs.db",
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            ".coverage",
            "htmlcov",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "target",
            "*.class",
        ]
        return "\n".join(base_ignores)

    async def ensure_dockerfile(self, project_path: Path) -> Tuple[FrameworkType, bool]:
        """
        Ensure project has a Dockerfile. Creates one if missing.
        Returns (framework_type, was_created)
        """
        dockerfile_path = project_path / "Dockerfile"
        dockerignore_path = project_path / ".dockerignore"

        framework = self.detect_framework(project_path)
        was_created = False

        if not dockerfile_path.exists():
            logger.info(f"Creating Dockerfile for {framework.value} project")
            dockerfile_content = self.generate_dockerfile(project_path, framework)

            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            was_created = True

        if not dockerignore_path.exists():
            dockerignore_content = self.generate_dockerignore(framework)
            with open(dockerignore_path, 'w') as f:
                f.write(dockerignore_content)

        return framework, was_created

    def _get_available_port(self, start_port: int = 3001) -> int:
        """Find an available port on the host"""
        import socket
        port = start_port
        used_ports = set(self._assigned_ports.values())

        while port < 65535:
            if port in used_ports:
                port += 1
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                port += 1
        return start_port

    def _extract_port_from_output(self, output: str, framework: FrameworkType) -> Optional[int]:
        """Extract port number from container output"""
        for pattern in PORT_PATTERNS:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        return None

    def _is_port_conflict(self, output: str) -> bool:
        """
        Detect if output indicates a port conflict (EADDRINUSE).
        Port conflicts are handled specially with automatic port reallocation.
        """
        port_conflict_patterns = [
            'EADDRINUSE',
            'address already in use',
            'Address already in use',
            'port is already in use',
            'Port is already in use',
            'listen EADDRINUSE',
            'Error: listen EADDRINUSE',
            'bind: address already in use',
            'Only one usage of each socket address',
            'port already allocated',
            'Address in use',
        ]
        output_lower = output.lower()
        for pattern in port_conflict_patterns:
            if pattern.lower() in output_lower:
                return True
        return False

    def _extract_conflicting_port(self, output: str) -> Optional[int]:
        """Extract the conflicting port number from error message"""
        # Common patterns: "port 3000 is already in use", "EADDRINUSE :::3000", etc.
        patterns = [
            r'(?:port\s+)?(\d{4,5})\s+(?:is\s+)?already\s+in\s+use',
            r'EADDRINUSE\s*(?:::)?(\d{4,5})',
            r'listen\s+EADDRINUSE\s*(?:::)?(\d{4,5})',
            r'address\s+already\s+in\s+use\s*(?:::)?(\d{4,5})',
            r'bind.*:(\d{4,5})',
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        return None

    async def _check_docker_available(self) -> bool:
        """Check if Docker is available and running"""
        import shutil
        try:
            # First check if docker is in PATH
            docker_path = shutil.which("docker")
            if not docker_path:
                logger.warning("[DockerExecutor] Docker not found in PATH")
                return False

            logger.info(f"[DockerExecutor] Found docker at: {docker_path}")

            # Use shell=True on Windows for better compatibility
            import sys
            if sys.platform == "win32":
                process = await asyncio.create_subprocess_shell(
                    "docker info",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    "docker", "info",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info("[DockerExecutor] Docker is available and running")
                return True
            else:
                stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ''
                logger.warning(f"[DockerExecutor] Docker info failed (code {process.returncode}): {stderr_text[:200]}")
                return False

        except FileNotFoundError:
            logger.warning("[DockerExecutor] Docker executable not found")
            return False
        except Exception as e:
            logger.error(f"[DockerExecutor] Error checking Docker: {type(e).__name__}: {e}")
            return False

    async def build_image(
        self,
        project_id: str,
        project_path: Path
    ) -> AsyncGenerator[str, None]:
        """Build Docker image for the project, yielding progress output"""

        image_name = f"student-project-{project_id}".lower()

        # Get LogBus for Docker log collection
        try:
            from app.services.log_bus import get_log_bus
            log_bus = get_log_bus(project_id)
        except Exception:
            log_bus = None

        yield f"Building Docker image: {image_name}...\n"

        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "build", "-t", image_name, ".",
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            async for line in process.stdout:
                output = line.decode().strip()
                if output:
                    yield f"{output}\n"

                    # Send to LogBus
                    if log_bus:
                        if 'error' in output.lower() or 'ERROR' in output:
                            log_bus.add_docker_error(output)
                        else:
                            log_bus.add_docker_log(output)

            await process.wait()

            if process.returncode == 0:
                yield f"Successfully built image: {image_name}\n"
            else:
                error_msg = f"Failed to build image (exit code: {process.returncode})"
                yield f"ERROR: {error_msg}\n"
                if log_bus:
                    log_bus.add_docker_error(error_msg)
                raise Exception(f"Docker build failed with exit code {process.returncode}")

        except Exception as e:
            yield f"ERROR: {str(e)}\n"
            raise

    async def run_container(
        self,
        project_id: str,
        project_path: Path,
        framework: FrameworkType
    ) -> AsyncGenerator[str, None]:
        """
        Run Docker container for the project.
        Yields streaming output including the preview URL when detected.
        """

        # Get LogBus for Docker log collection
        try:
            from app.services.log_bus import get_log_bus
            log_bus = get_log_bus(project_id)
        except Exception:
            log_bus = None

        # Check Docker availability
        if not await self._check_docker_available():
            error_msg = "Docker is not available. Please ensure Docker is installed and running."
            yield f"ERROR: {error_msg}\n"
            if log_bus:
                log_bus.add_docker_error(error_msg)
            return

        image_name = f"student-project-{project_id}".lower()
        container_name = f"run-{project_id}".lower()

        # Stop any existing container with same name
        await self.stop_container(project_id)

        # Get available port
        default_port = DEFAULT_PORTS.get(framework, 3000)
        host_port = self._get_available_port(default_port)

        yield f"Starting container on port {host_port}...\n"

        try:
            # Build image first
            async for output in self.build_image(project_id, project_path):
                yield output

            # Run container
            process = await asyncio.create_subprocess_exec(
                "docker", "run",
                "--rm",  # Auto-remove when stopped
                "--name", container_name,
                "-p", f"{host_port}:{default_port}",
                "-v", f"{project_path}:/app",  # Mount project for live reload
                image_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            self._running_containers[project_id] = container_name
            self._assigned_ports[project_id] = host_port

            port_detected = False
            preview_url = get_preview_url(host_port, project_id)

            # Stream output and detect server ready
            async for line in process.stdout:
                output = line.decode().strip()
                if output:
                    yield f"{output}\n"

                    # Send to LogBus for Docker log collection
                    if log_bus:
                        if 'error' in output.lower() or 'ERROR' in output or 'failed' in output.lower():
                            log_bus.add_docker_error(output)
                        else:
                            log_bus.add_docker_log(output)

                    # Try to detect port from output
                    if not port_detected:
                        detected_port = self._extract_port_from_output(output, framework)
                        if detected_port:
                            port_detected = True
                            # For FULLSTACK projects, ALWAYS use the frontend port for preview
                            if framework in [FrameworkType.FULLSTACK_REACT_SPRING, FrameworkType.FULLSTACK_REACT_EXPRESS, FrameworkType.FULLSTACK_REACT_FASTAPI]:
                                preview_url = get_preview_url(host_port, project_id)
                                backend_port = host_port + 1000
                                backend_url = get_direct_preview_url(backend_port)
                                yield f"\n{'='*50}\n"
                                yield f"FULLSTACK SERVERS STARTED!\n"
                                yield f"Frontend (Preview): {preview_url}\n"
                                yield f"Backend API: {backend_url}\n"
                                yield f"{'='*50}\n\n"
                                yield f"_PREVIEW_URL_:{preview_url}\n"
                            else:
                                yield f"\n{'='*50}\n"
                                yield f"SERVER STARTED!\n"
                                yield f"Preview URL: {preview_url}\n"
                                yield f"{'='*50}\n\n"
                                yield f"_PREVIEW_URL_:{preview_url}\n"

                    # Check for common "ready" messages
                    ready_patterns = [
                        "ready in",
                        "compiled successfully",
                        "started server",
                        "listening on",
                        "running on",
                        "development server",
                        "server started",
                    ]
                    if not port_detected and any(p in output.lower() for p in ready_patterns):
                        port_detected = True
                        # For FULLSTACK projects, ALWAYS use the frontend port for preview
                        if framework in [FrameworkType.FULLSTACK_REACT_SPRING, FrameworkType.FULLSTACK_REACT_EXPRESS, FrameworkType.FULLSTACK_REACT_FASTAPI]:
                            preview_url = get_preview_url(host_port, project_id)
                            backend_port = host_port + 1000
                            backend_url = get_direct_preview_url(backend_port)
                            yield f"\n{'='*50}\n"
                            yield f"FULLSTACK SERVERS STARTED!\n"
                            yield f"Frontend (Preview): {preview_url}\n"
                            yield f"Backend API: {backend_url}\n"
                            yield f"{'='*50}\n\n"
                            yield f"_PREVIEW_URL_:{preview_url}\n"
                        else:
                            yield f"\n{'='*50}\n"
                            yield f"SERVER STARTED!\n"
                            yield f"Preview URL: {preview_url}\n"
                            yield f"{'='*50}\n\n"
                            yield f"_PREVIEW_URL_:{preview_url}\n"

            await process.wait()
            yield f"Container exited with code: {process.returncode}\n"

        except Exception as e:
            yield f"ERROR: {str(e)}\n"
            raise
        finally:
            # Cleanup
            if project_id in self._running_containers:
                del self._running_containers[project_id]
            if project_id in self._assigned_ports:
                del self._assigned_ports[project_id]

    async def stop_container(self, project_id: str) -> bool:
        """Stop a running container"""
        container_name = f"run-{project_id}".lower()

        try:
            # Try to stop the container
            process = await asyncio.create_subprocess_exec(
                "docker", "stop", container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.wait(), timeout=10.0)

            # Clean up tracking
            if project_id in self._running_containers:
                del self._running_containers[project_id]
            if project_id in self._assigned_ports:
                del self._assigned_ports[project_id]

            logger.info(f"Stopped container: {container_name}")
            return True

        except asyncio.TimeoutError:
            # Force kill
            kill_process = await asyncio.create_subprocess_exec(
                "docker", "kill", container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await kill_process.wait()
            return True

        except Exception as e:
            logger.warning(f"Error stopping container {container_name}: {e}")
            return False

    def get_preview_url(self, project_id: str) -> Optional[str]:
        """Get the preview URL for a running project"""
        if project_id in self._assigned_ports:
            port = self._assigned_ports[project_id]
            # Use module-level get_preview_url function
            from app.modules.execution.docker_executor import get_preview_url as get_url
            return get_url(port)
        return None

    async def get_container_status(self, project_id: str) -> dict:
        """Get status of a project's container"""
        container_name = f"run-{project_id}".lower()

        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "inspect", container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                data = json.loads(stdout.decode())
                if data:
                    state = data[0].get("State", {})
                    return {
                        "running": state.get("Running", False),
                        "status": state.get("Status", "unknown"),
                        "started_at": state.get("StartedAt"),
                        "port": self._assigned_ports.get(project_id),
                        "preview_url": self.get_preview_url(project_id)
                    }

            return {"running": False, "status": "not_found"}

        except Exception as e:
            return {"running": False, "status": "error", "error": str(e)}

    # ============= DIRECT EXECUTION (FALLBACK) =============

    def _get_run_commands(self, framework: FrameworkType, project_path: Path, port: int = 3000) -> List[str]:
        """Get the commands to run the project directly (without Docker)

        Args:
            framework: Detected framework type
            project_path: Path to project
            port: Dynamic port to use (allocated by _get_available_port)
        """
        commands = []

        if framework in [FrameworkType.REACT_VITE, FrameworkType.VUE]:
            # Vite: use --port flag for dynamic port
            # Run TypeScript check FIRST to catch errors (Vite/esbuild skips type checking)
            # This enables auto-fixer to detect and fix TypeScript errors
            has_tsconfig = (project_path / "tsconfig.json").exists()
            if has_tsconfig:
                commands = ["npm install", "npx tsc --noEmit", f"npm run dev -- --host 0.0.0.0 --port {port} --no-open"]
            else:
                commands = ["npm install", f"npm run dev -- --host 0.0.0.0 --port {port} --no-open"]
        elif framework == FrameworkType.REACT_CRA:
            # CRA uses PORT env variable
            commands = ["npm install", f"set PORT={port} && npm start"]
        elif framework == FrameworkType.NEXTJS:
            # Next.js: use -p flag for port
            commands = ["npm install", f"npm run dev -- -p {port}"]
        elif framework in [FrameworkType.NODE_EXPRESS, FrameworkType.UNKNOWN]:
            # Generic Node: set PORT env variable
            commands = ["npm install", f"set PORT={port} && npm start"]
        elif framework == FrameworkType.ANGULAR:
            commands = ["npm install", f"npm start -- --host 0.0.0.0 --port {port}"]
        elif framework == FrameworkType.PYTHON_FLASK:
            commands = ["pip install -r requirements.txt", f"flask run --host 0.0.0.0 --port {port}"]
        elif framework == FrameworkType.PYTHON_FASTAPI:
            commands = ["pip install -r requirements.txt", f"uvicorn main:app --host 0.0.0.0 --port {port}"]
        elif framework == FrameworkType.PYTHON_DJANGO:
            commands = ["pip install -r requirements.txt", f"python manage.py runserver 0.0.0.0:{port}"]
        elif framework == FrameworkType.PYTHON_STREAMLIT:
            commands = ["pip install -r requirements.txt", f"streamlit run app.py --server.address 0.0.0.0 --server.port {port}"]
        elif framework == FrameworkType.SPRING_BOOT:
            # Check for Gradle vs Maven
            has_gradle = (project_path / "build.gradle").exists() or (project_path / "build.gradle.kts").exists()
            has_maven = (project_path / "pom.xml").exists()

            if has_gradle:
                # Gradle project: compile first to catch errors, then build and run
                commands = [
                    "gradle clean compileJava",  # Compile first to catch errors
                    "gradle bootJar -x test",     # Build JAR without tests
                    f"java -jar build/libs/*.jar --server.port={port}"
                ]
            elif has_maven:
                # Maven project: compile first to catch errors, then package and run
                commands = [
                    "mvn compile",                          # Compile first to catch errors early
                    "mvn package -DskipTests -q",           # Package quietly
                    f"java -jar target/*.jar --server.port={port}"
                ]
            else:
                # Fallback to Maven
                commands = ["mvn package -DskipTests", f"java -jar target/*.jar --server.port={port}"]

        elif framework == FrameworkType.GO:
            # Go project: download deps, build, and run with port
            has_go_mod = (project_path / "go.mod").exists()
            # Check for common entry point locations
            has_cmd_main = (project_path / "cmd" / "main.go").exists() or (project_path / "cmd" / "server" / "main.go").exists()

            if has_go_mod:
                commands = [
                    "go mod download",         # Download dependencies
                    "go mod tidy",             # Ensure go.sum is up to date
                    "go build -o main .",      # Build the binary
                    f"PORT={port} ./main"      # Run with PORT env variable
                ]
            else:
                commands = [
                    "go build -o main .",
                    f"PORT={port} ./main"
                ]

        # ===== NEW TECHNOLOGIES =====

        elif framework == FrameworkType.SVELTE:
            # Svelte/SvelteKit: similar to Vite
            has_tsconfig = (project_path / "tsconfig.json").exists()
            if has_tsconfig:
                commands = ["npm install", "npx tsc --noEmit", f"npm run dev -- --host 0.0.0.0 --port {port}"]
            else:
                commands = ["npm install", f"npm run dev -- --host 0.0.0.0 --port {port}"]

        elif framework == FrameworkType.PYTHON_ML:
            # AI/ML Python project: Install deps and run Jupyter or main script
            has_notebook = any((project_path).glob("*.ipynb"))
            has_main = (project_path / "main.py").exists() or (project_path / "train.py").exists()

            if has_notebook:
                commands = [
                    "pip install -r requirements.txt",
                    f"jupyter notebook --ip=0.0.0.0 --port={port} --no-browser --allow-root"
                ]
            elif has_main:
                main_file = "main.py" if (project_path / "main.py").exists() else "train.py"
                commands = [
                    "pip install -r requirements.txt",
                    f"python {main_file}"
                ]
            else:
                commands = [
                    "pip install -r requirements.txt",
                    f"jupyter notebook --ip=0.0.0.0 --port={port} --no-browser --allow-root"
                ]

        elif framework == FrameworkType.RUST:
            # Rust project: build and run
            commands = [
                "cargo build --release",
                f"PORT={port} ./target/release/*"
            ]

        elif framework == FrameworkType.RUBY_RAILS:
            # Ruby on Rails project
            has_gemfile = (project_path / "Gemfile").exists()
            if has_gemfile:
                commands = [
                    "bundle install",
                    "bundle exec rails db:migrate || true",  # Migrate if DB exists
                    f"bundle exec rails server -b 0.0.0.0 -p {port}"
                ]
            else:
                commands = [f"ruby main.rb"]

        elif framework == FrameworkType.PHP_LARAVEL:
            # PHP Laravel project
            has_composer = (project_path / "composer.json").exists()
            has_artisan = (project_path / "artisan").exists()
            if has_artisan:
                commands = [
                    "composer install --no-dev --optimize-autoloader",
                    "php artisan key:generate --force || true",
                    "php artisan migrate --force || true",
                    f"php artisan serve --host=0.0.0.0 --port={port}"
                ]
            elif has_composer:
                commands = [
                    "composer install",
                    f"php -S 0.0.0.0:{port} -t public"
                ]
            else:
                commands = [f"php -S 0.0.0.0:{port}"]

        elif framework == FrameworkType.DOTNET:
            # .NET Core project
            has_csproj = any(project_path.glob("*.csproj")) or any(project_path.glob("**/*.csproj"))
            has_sln = any(project_path.glob("*.sln"))
            if has_sln or has_csproj:
                commands = [
                    "dotnet restore",
                    "dotnet build --configuration Release",
                    f"dotnet run --urls http://0.0.0.0:{port}"
                ]
            else:
                commands = [f"dotnet run --urls http://0.0.0.0:{port}"]

        elif framework == FrameworkType.ANDROID:
            # Android project: build APK (can't really run directly)
            has_gradle_wrapper = (project_path / "gradlew").exists()
            if has_gradle_wrapper:
                commands = [
                    "./gradlew clean",
                    "./gradlew assembleDebug"
                ]
            else:
                commands = [
                    "gradle clean",
                    "gradle assembleDebug"
                ]

        elif framework == FrameworkType.IOS_SWIFT:
            # iOS project: build (can't run without simulator)
            has_package_swift = (project_path / "Package.swift").exists()
            if has_package_swift:
                commands = [
                    "swift build",
                    "swift run"
                ]
            else:
                # Xcode project - just build
                commands = [
                    "xcodebuild -scheme * -configuration Debug build"
                ]

        elif framework == FrameworkType.SOLIDITY:
            # Solidity/Hardhat project: compile and run local node
            has_hardhat = (project_path / "hardhat.config.js").exists() or (project_path / "hardhat.config.ts").exists()
            has_truffle = (project_path / "truffle-config.js").exists()
            has_foundry = (project_path / "foundry.toml").exists()

            if has_hardhat:
                commands = [
                    "npm install",
                    "npx hardhat compile",
                    f"npx hardhat node --port {port}"
                ]
            elif has_truffle:
                commands = [
                    "npm install",
                    "truffle compile",
                    f"truffle develop --port {port}"
                ]
            elif has_foundry:
                commands = [
                    "forge build",
                    f"anvil --port {port}"
                ]
            else:
                commands = [
                    "npm install",
                    "npx hardhat compile"
                ]

        elif framework == FrameworkType.RUST_SOLANA:
            # Solana/Anchor project: build and test
            has_anchor = (project_path / "Anchor.toml").exists()
            if has_anchor:
                commands = [
                    "anchor build",
                    "anchor test"
                ]
            else:
                commands = [
                    "cargo build-bpf",
                    "cargo test-bpf"
                ]

        elif framework == FrameworkType.STATIC_HTML:
            commands = [f"python -m http.server {port}"]

        # ===== FULLSTACK MONOREPO PROJECTS =====
        # These run BOTH frontend AND backend simultaneously!
        elif framework == FrameworkType.FULLSTACK_REACT_SPRING:
            # React + Spring Boot monorepo - START BOTH!
            frontend_path = project_path / "frontend"
            backend_path = project_path / "backend"
            backend_port = port + 1000  # Backend on different port (e.g., 4000 if frontend is 3000)

            has_tsconfig = (frontend_path / "tsconfig.json").exists()
            has_gradle = (backend_path / "build.gradle").exists() or (backend_path / "build.gradle.kts").exists()
            has_maven = (backend_path / "pom.xml").exists()

            # Frontend commands
            if has_tsconfig:
                frontend_cmd = f"cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port {port} --no-open"
            else:
                frontend_cmd = f"cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port {port} --no-open"

            # Backend commands - Spring Boot
            if has_gradle:
                backend_cmd = f"cd backend && gradle bootRun --args='--server.port={backend_port}'"
            elif has_maven:
                backend_cmd = f"cd backend && mvn spring-boot:run -Dspring-boot.run.arguments=--server.port={backend_port}"
            else:
                backend_cmd = f"cd backend && mvn spring-boot:run -Dspring-boot.run.arguments=--server.port={backend_port}"

            # Run BOTH: backend first (in background), then frontend
            # Using 'start' on Windows to run backend in background
            commands = [
                f"cd backend && mvn dependency:resolve",  # Install backend deps first
                f"start /B cmd /c \"{backend_cmd}\"",     # Start backend in background (Windows)
                frontend_cmd                               # Start frontend (foreground - streams output)
            ]

        elif framework == FrameworkType.FULLSTACK_REACT_EXPRESS:
            # React + Express monorepo - START BOTH!
            frontend_path = project_path / "frontend"
            backend_path = project_path / "backend"
            backend_port = port + 1000

            has_tsconfig = (frontend_path / "tsconfig.json").exists()

            # Frontend commands
            if has_tsconfig:
                frontend_cmd = f"cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port {port} --no-open"
            else:
                frontend_cmd = f"cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port {port} --no-open"

            # Backend commands - Express
            backend_cmd = f"cd backend && npm install && set PORT={backend_port} && npm start"

            # Run BOTH
            commands = [
                f"start /B cmd /c \"cd backend && npm install && set PORT={backend_port} && npm start\"",  # Backend in background
                frontend_cmd  # Frontend in foreground
            ]

        elif framework == FrameworkType.FULLSTACK_REACT_FASTAPI:
            # React + FastAPI monorepo - START BOTH!
            frontend_path = project_path / "frontend"
            backend_path = project_path / "backend"
            backend_port = port + 1000

            has_tsconfig = (frontend_path / "tsconfig.json").exists()

            # Frontend commands
            if has_tsconfig:
                frontend_cmd = f"cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port {port} --no-open"
            else:
                frontend_cmd = f"cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port {port} --no-open"

            # Backend commands - FastAPI
            backend_cmd = f"cd backend && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port {backend_port} --reload"

            # Run BOTH
            commands = [
                f"start /B cmd /c \"{backend_cmd}\"",  # Backend in background
                frontend_cmd  # Frontend in foreground
            ]

        return commands

    async def run_direct(
        self,
        project_id: str,
        project_path: Path,
        framework: FrameworkType,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Run project in isolated container (using ContainerExecutor).
        Falls back to direct host execution if container spawning fails.

        Production-ready: Spawns technology-specific containers for each project.
        Auto-fixes ANY errors that occur during execution.
        """
        # ===== TRY CONTAINER EXECUTOR FIRST (Production Mode) =====
        # This spawns isolated containers with the right technology stack
        try:
            yield "🐳 Spawning isolated container for project...\n"

            # Initialize container executor if needed
            if not container_executor.docker_client:
                await container_executor.initialize()

            if container_executor.docker_client:
                # Detect technology and spawn appropriate container
                tech = container_executor.detect_technology(str(project_path))
                yield f"  📦 Detected technology: {tech.value}\n"

                success, message, port = await container_executor.create_container(
                    project_id=project_id,
                    user_id=user_id or "anonymous",
                    project_path=str(project_path),
                    technology=tech
                )

                if success and port:
                    yield f"  ✅ Container started on port {port}\n"
                    yield f"  🌐 Preview URL: {get_preview_url(port, project_id)}\n"

                    # Store the port
                    self._assigned_ports[project_id] = port

                    # Stream container logs
                    yield "  📜 Streaming container logs...\n\n"
                    for _ in range(60):  # Monitor for up to 60 seconds
                        await asyncio.sleep(2)
                        logs = await container_executor.get_container_logs(project_id, tail=20)
                        if logs:
                            yield logs

                        # Check if server is ready
                        status = await container_executor.get_container_status(project_id)
                        if status and status.get("status") == "running":
                            preview_url = get_preview_url(port, project_id)
                            yield f"\n✅ Server running at {preview_url}\n"
                            yield f"_PREVIEW_URL_:{preview_url}\n"
                            return

                    preview_url = get_preview_url(port, project_id)
                    yield f"\n⚠️ Container started but server may not be ready\n"
                    yield f"_PREVIEW_URL_:{preview_url}\n"
                    return
                else:
                    yield f"  ⚠️ Container spawn failed: {message}\n"
                    yield "  Falling back to direct execution...\n\n"
            else:
                yield "  ⚠️ Docker not available for containers\n"
                yield "  Falling back to direct execution...\n\n"

        except Exception as e:
            logger.warning(f"[DockerExecutor:{project_id}] Container executor failed: {e}")
            yield f"  ⚠️ Container executor error: {str(e)[:100]}\n"
            yield "  Falling back to direct execution...\n\n"

        # ===== FALLBACK: Direct execution on host =====
        yield "Running project directly on host...\n"

        # Check if required runtimes are available for this project type
        import shutil
        missing_runtimes = []

        if framework == FrameworkType.SPRING_BOOT:
            if not shutil.which("mvn") and not shutil.which("gradle"):
                missing_runtimes.append("Maven/Gradle (Java build tools)")
            if not shutil.which("java"):
                missing_runtimes.append("Java JDK")
        elif framework in [FrameworkType.GO, FrameworkType.FULLSTACK_GO_REACT]:
            if not shutil.which("go"):
                missing_runtimes.append("Go runtime")
        elif framework in [FrameworkType.PYTHON_FASTAPI, FrameworkType.PYTHON_FLASK, FrameworkType.PYTHON_DJANGO, FrameworkType.PYTHON_STREAMLIT, FrameworkType.PYTHON_ML]:
            if not shutil.which("python3") and not shutil.which("python"):
                missing_runtimes.append("Python runtime")
        elif framework in [FrameworkType.REACT_VITE, FrameworkType.NEXTJS, FrameworkType.NODE_EXPRESS]:
            if not shutil.which("node"):
                missing_runtimes.append("Node.js runtime")
        elif framework == FrameworkType.RUBY_RAILS:
            if not shutil.which("ruby"):
                missing_runtimes.append("Ruby runtime")
            if not shutil.which("bundle"):
                missing_runtimes.append("Bundler (gem install bundler)")
        elif framework == FrameworkType.PHP_LARAVEL:
            if not shutil.which("php"):
                missing_runtimes.append("PHP runtime")
            if not shutil.which("composer"):
                missing_runtimes.append("Composer (PHP package manager)")
        elif framework == FrameworkType.DOTNET:
            if not shutil.which("dotnet"):
                missing_runtimes.append(".NET SDK")
        elif framework == FrameworkType.RUST:
            if not shutil.which("cargo"):
                missing_runtimes.append("Rust/Cargo")

        if missing_runtimes:
            yield "\n❌ RUNTIME ERROR: Required tools not found on this server:\n"
            for runtime in missing_runtimes:
                yield f"   • {runtime}\n"
            yield "\n💡 SOLUTION OPTIONS:\n"
            yield "   1. Enable Docker containers (preferred) - Set DOCKER_AVAILABLE=true\n"
            yield "   2. Install the missing runtimes on the server\n"
            yield "   3. Use the Docker-based sandbox with bharatbuild/runtime:latest image\n"
            yield "\n📦 To build the runtime image: docker-compose -f docker-compose.prod.yml build runtime\n"
            return

        # Store user_id for auto-fix
        self._current_user_id = user_id

        # Get LogBus for error collection (Bolt.new style!)
        log_bus = get_log_bus(project_id)

        # Error patterns for detection (supports all technologies!)
        error_patterns = [
            # ===== GENERAL =====
            'error', 'Error', 'ERROR',
            'Failed', 'failed', 'FAILED',
            'Cannot find', 'cannot find',
            'fatal:', 'critical:',
            'Internal server error',

            # ===== JAVASCRIPT/NODE.JS =====
            'Module not found', 'module not found',
            'npm ERR!', 'ERR!',
            'SyntaxError', 'TypeError', 'ReferenceError',
            'ENOENT', 'EACCES', 'EPERM',
            'Unexpected token',
            'Cannot read property',
            'is not defined',
            'is not a function',

            # ===== PYTHON =====
            'Traceback', 'Exception',
            'ImportError', 'ModuleNotFoundError',
            'IndentationError', 'SyntaxError',
            'NameError', 'AttributeError', 'KeyError',
            'ValueError', 'TypeError',
            'FileNotFoundError', 'PermissionError',

            # ===== JAVA/SPRING BOOT/MAVEN =====
            'java.lang.', 'javax.',
            'NullPointerException', 'ClassNotFoundException',
            'NoClassDefFoundError', 'IllegalArgumentException',
            'IllegalStateException', 'RuntimeException',
            'BUILD FAILURE', 'BUILD FAILED',
            '[FATAL]', '[ERROR]',  # Maven log levels
            'Non-parseable POM', 'Non-parseable',  # Maven POM parsing errors
            'PITarget', 'processing instruction',  # XML parsing errors
            'Invalid XML', 'Malformed POM',
            'Compilation failure', 'compilation error',
            'cannot find symbol', 'incompatible types',
            'Failed to execute goal',
            'Could not resolve dependencies',
            'BeanCreationException', 'NoSuchBeanDefinitionException',
            'ApplicationContextException',
            'org.springframework', 'Spring Boot',
            'maven-compiler-plugin', 'mvn ',
            'gradle', 'Execution failed for task',
            'JpaSystemException', 'DataIntegrityViolationException',
            'org.hibernate', 'HibernateException',
            'BindException', 'MethodArgumentNotValidException',

            # ===== GO/GOLANG =====
            'go:', 'go build', 'go run',
            'cannot find package', 'package .* is not in',
            'undefined:', 'undeclared name',
            'imported and not used',
            'missing go.sum entry',
            'cannot load', 'cannot find module',
            'panic:', 'runtime error:',
            'goroutine', 'stack trace',
            'build constraints exclude',
            'invalid operation',
            'type .* has no field or method',

            # ===== RUST =====
            'error[E', 'cargo',
            'rustc', 'borrow checker',

            # ===== AI/ML (TensorFlow, PyTorch, Keras, etc.) =====
            'tensorflow', 'tf.',
            'CUDA', 'cudnn', 'GPU',
            'OutOfMemoryError', 'ResourceExhaustedError',
            'InvalidArgumentError', 'OpError',
            'torch', 'pytorch', 'RuntimeError: CUDA',
            'RuntimeError: Expected', 'size mismatch',
            'shape mismatch', 'dimension mismatch',
            'keras', 'model.fit', 'model.predict',
            'ValueError: Shapes', 'ValueError: Input',
            'scikit-learn', 'sklearn',
            'numpy', 'np.', 'ndarray',
            'pandas', 'DataFrame',
            'matplotlib', 'plt.',
            'opencv', 'cv2',
            'huggingface', 'transformers',
            'wandb', 'mlflow',

            # ===== BLOCKCHAIN (Solidity, Web3, Hardhat, etc.) =====
            'solidity', 'solc',
            'CompilerError', 'ParserError',
            'DeclarationError', 'TypeError:',
            'revert', 'require(', 'assert(',
            'out of gas', 'gas estimation',
            'hardhat', 'truffle', 'foundry',
            'ethers', 'web3.js', 'web3.py',
            'MetaMask', 'wallet',
            'contract', 'transaction failed',
            'insufficient funds', 'nonce too low',
            'EVM', 'bytecode',
            'abi', 'deploy',
            'anchor', 'solana',
            'substrate', 'polkadot',

            # ===== ANDROID (Kotlin, Java, Gradle) =====
            'android', 'AndroidManifest',
            'kotlin', 'kotlinc',
            'gradle', 'Gradle',
            'AAPT', 'aapt2',
            'R.', 'R.layout', 'R.id',
            'ActivityNotFoundException',
            'NullPointerException',
            'AndroidRuntimeException',
            'inflating class', 'inflate',
            'Could not find com.android',
            'minSdkVersion', 'targetSdkVersion',
            'APK', 'dex', 'D8', 'R8',
            'JetBrains', 'coroutines',
            'Compose', 'Jetpack',
            'Room', 'LiveData', 'ViewModel',
            'Retrofit', 'OkHttp',
            'Firebase', 'google-services',

            # ===== iOS (Swift, Xcode, CocoaPods) =====
            'swift', 'swiftc',
            'xcode', 'xcodebuild',
            'Undefined symbols', 'Linker command failed',
            'ld: framework not found',
            'ld: library not found',
            'clang', 'llvm',
            'Segmentation fault', 'EXC_BAD_ACCESS',
            'NSException', 'NSInvalidArgumentException',
            'unrecognized selector', '@objc',
            'IBOutlet', 'IBAction', 'Storyboard',
            'UIKit', 'SwiftUI', 'Combine',
            'CoreData', 'CloudKit',
            'CocoaPods', 'pod install',
            'Podfile', 'Podfile.lock',
            'Carthage', 'SPM', 'Package.swift',
            'Provisioning profile', 'Code signing',
            'Simulator', 'Device',
            'Archive', 'IPA',

            # ===== CYBERSECURITY TOOLS =====
            'permission denied', 'access denied',
            'authentication failed', 'unauthorized',
            'SSL', 'TLS', 'certificate',
            'handshake', 'connection refused',
            'timeout', 'ETIMEDOUT',
            'socket', 'bind failed',
            'cryptography', 'encryption',
            'hash', 'digest',
            'jwt', 'token', 'oauth',
            'vulnerability', 'exploit',
            'injection', 'XSS', 'CSRF',
            'sanitize', 'escape',
            'nmap', 'metasploit',
            'burp', 'wireshark',
            'reverse shell', 'payload',

            # ===== CLOUD/DEVOPS =====
            'aws', 'AWS', 'boto3',
            'azure', 'Azure',
            'gcp', 'GCP', 'google-cloud',
            'kubernetes', 'k8s', 'kubectl',
            'terraform', 'tf.',
            'ansible', 'playbook',
            'jenkins', 'CI/CD',
            'nginx', 'apache',
            'redis', 'mongodb', 'postgresql',

            # ===== DOCKER =====
            'docker:', 'Dockerfile',
            'container', 'image not found',
        ]

        # Port conflict patterns (handled specially with auto-retry)
        port_conflict_patterns = [
            'EADDRINUSE',
            'address already in use',
            'Address already in use',
            'port is already in use',
            'Port is already in use',
            'listen EADDRINUSE',
            'Error: listen EADDRINUSE',
            'bind: address already in use',
            'Only one usage of each socket address',
            'port already allocated',
            'Address in use',
        ]

        # Buffer to collect error context
        error_buffer = []
        # Track if any errors were detected (for deferred LogBus addition)
        has_error = False
        # Track port conflict for auto-retry
        port_conflict_detected = False
        port_conflict_retries = 0
        MAX_PORT_CONFLICT_RETRIES = 3

        # Get available port FIRST, then build commands with that port
        default_port = DEFAULT_PORTS.get(framework, 3000)
        host_port = self._get_available_port(default_port)

        # Get effective working directory (handles frontend-only projects in subdirs)
        working_dir = self.get_effective_working_directory(project_path, framework)
        if working_dir != project_path:
            yield f"Using working directory: {working_dir.name}/\n"

        # Now get commands using the allocated port (use working_dir for command generation)
        commands = self._get_run_commands(framework, working_dir, host_port)

        self._assigned_ports[project_id] = host_port

        yield f"Allocated port: {host_port}\n"

        for command in commands:
            yield f"$ {command}\n"

            try:
                import os
                import sys
                import subprocess as sync_subprocess
                env = os.environ.copy()
                env['NO_COLOR'] = '1'
                env['FORCE_COLOR'] = '0'
                env['CI'] = 'true'
                env['BROWSER'] = 'none'  # Prevent auto-opening browser
                env['TERM'] = 'dumb'

                if sys.platform == 'win32':
                    env['PYTHONIOENCODING'] = 'utf-8'
                    env['PYTHONUTF8'] = '1'

                logger.info(f"[DockerExecutor:{project_id}] Starting: {command}")

                # WINDOWS FIX: Use synchronous subprocess for reliable output capture
                if sys.platform == 'win32':
                    # Detect if this is ONLY an install command (not followed by a dev server)
                    # Commands like "npm install && npm run dev" should NOT be treated as install-only
                    cmd_lower = command.lower()
                    has_install = 'install' in cmd_lower or 'dependency:resolve' in cmd_lower
                    has_dev_server = any(p in cmd_lower for p in ['npm run dev', 'npm start', 'run dev', 'spring-boot:run', 'bootrun', 'uvicorn', 'flask run', 'streamlit'])
                    is_install = has_install and not has_dev_server
                    logger.info(f"[DockerExecutor:{project_id}] Windows mode, install={is_install}, has_dev={has_dev_server}")

                    if is_install:
                        result = sync_subprocess.run(
                            command, shell=True, cwd=str(working_dir), env=env,
                            capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=300
                        )
                        all_output = (result.stdout or '') + (result.stderr or '')
                        exit_code = result.returncode
                        logger.info(f"[DockerExecutor:{project_id}] Install exit={exit_code}, len={len(all_output)}")
                    else:
                        import threading
                        import queue
                        import time as time_module
                        proc = sync_subprocess.Popen(
                            command, shell=True, cwd=str(working_dir), env=env,
                            stdout=sync_subprocess.PIPE, stderr=sync_subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace'
                        )
                        self._running_processes[project_id] = proc
                        output_lines = []
                        output_queue = queue.Queue()  # Queue to share output with background monitor

                        # Define critical error patterns - MUST be very specific to avoid false positives
                        # These patterns indicate ACTUAL errors that need fixing
                        critical_error_patterns_for_reader = [
                            # Vite/Frontend errors (very specific)
                            'Failed to resolve import',
                            'Does the file exist?',  # More specific with question mark
                            '[plugin:vite:',  # Must have colon after vite
                            'Cannot find module',
                            'Module not found:',  # More specific with colon
                            'ENOENT: no such file',  # File not found
                            'SyntaxError:',  # JS/TS syntax errors
                            'TypeError:',  # Type errors
                            # Maven/Java errors (very specific)
                            '[ERROR] COMPILATION ERROR',  # Maven compilation error
                            'Non-parseable POM',
                            '[ERROR] Failed to execute goal',
                            'java.lang.NullPointerException',
                            'java.lang.ClassNotFoundException',
                            # PostCSS/Tailwind
                            '[postcss] ',  # PostCSS with space
                        ]

                        # Patterns that should NOT trigger auto-fix (false positives)
                        false_positive_patterns = [
                            '[INFO] BUILD FAILURE',  # This appears during SUCCESSFUL dependency resolution
                            'BUILD SUCCESS',
                            'Started Application',
                            'Tomcat started on port',
                            'DispatcherServlet',
                            '\\/ ___ \'',  # Spring Boot ASCII art
                            '( ( )\\_',  # Spring Boot ASCII art
                            'Hibernate:',  # Normal Hibernate SQL logging
                            '--- maven',  # Maven lifecycle output
                        ]

                        # Reference to self for the thread
                        executor_self = self
                        reader_error_buffer = []
                        last_fix_time = [0]  # Use list to allow mutation in closure
                        FIX_COOLDOWN = 60  # Increased to 60 seconds to prevent spam

                        def read_output_with_monitoring():
                            """Read output and also monitor for errors that occur after server starts"""
                            try:
                                for line in iter(proc.stdout.readline, ''):
                                    if line:
                                        line_stripped = line.rstrip()
                                        output_lines.append(line_stripped)
                                        output_queue.put(line_stripped)  # Also put in queue for potential use

                                        # Add to error buffer
                                        reader_error_buffer.append(line_stripped)
                                        if len(reader_error_buffer) > 100:
                                            reader_error_buffer.pop(0)

                                        # Check for critical errors CONTINUOUSLY
                                        # First check if it's a false positive
                                        is_false_positive = any(fp in line_stripped for fp in false_positive_patterns)
                                        is_critical_error = any(p in line_stripped for p in critical_error_patterns_for_reader)

                                        if is_critical_error and not is_false_positive:
                                            current_time = time_module.time()

                                            # Rate limit fix attempts
                                            if current_time - last_fix_time[0] >= FIX_COOLDOWN:
                                                last_fix_time[0] = current_time
                                                full_context = '\n'.join(reader_error_buffer[-50:])
                                                logger.info(f"[DockerExecutor:{project_id}] Reader thread detected REAL error: {line_stripped[:100]}")

                                                # Trigger auto-fix
                                                executor_self._trigger_auto_fix_background(
                                                    project_id=project_id,
                                                    project_path=project_path,
                                                    error_message=full_context,
                                                    command=command,
                                                    user_id=getattr(executor_self, '_current_user_id', None)
                                                )
                            except Exception as e:
                                logger.debug(f"[DockerExecutor:{project_id}] Reader thread error: {e}")

                        reader = threading.Thread(target=read_output_with_monitoring, daemon=True)
                        reader.start()
                        reader.join(timeout=15)
                        all_output = '\n'.join(output_lines)
                        exit_code = proc.poll()
                        logger.info(f"[DockerExecutor:{project_id}] Dev exit={exit_code}, lines={len(output_lines)}")

                    lines = [l for l in all_output.strip().split('\n') if l.strip()]
                    server_started = False
                    for line in lines:
                        yield f"{line}\n"
                        error_buffer.append(line)
                        if len(error_buffer) > 100:
                            error_buffer.pop(0)
                        if any(p in line for p in error_patterns):
                            has_error = True
                            # Check for critical errors that need immediate auto-fix
                            # Uses the same patterns defined above for the reader thread
                            # NOTE: We no longer trigger auto-fix here since the reader thread handles it
                            # This prevents duplicate triggers and race conditions
                        # Detect port conflicts for auto-retry
                        if self._is_port_conflict(line):
                            port_conflict_detected = True
                            conflicting_port = self._extract_conflicting_port(line)
                            logger.warning(f"[DockerExecutor:{project_id}] Port conflict detected on port {conflicting_port or host_port}")
                        if ('localhost' in line.lower() or 'http://' in line.lower()) and not server_started:
                            detected_port = self._extract_port_from_output(line, framework)
                            if detected_port:
                                server_started = True
                                # For FULLSTACK projects, ALWAYS use the frontend port for preview
                                # (backend port may be detected first but users want to see the UI)
                                if framework in [FrameworkType.FULLSTACK_REACT_SPRING, FrameworkType.FULLSTACK_REACT_EXPRESS, FrameworkType.FULLSTACK_REACT_FASTAPI]:
                                    # host_port is the frontend port, backend is +1000
                                    preview_url = get_preview_url(host_port, project_id)
                                    backend_port = host_port + 1000
                                    backend_url = get_direct_preview_url(backend_port)
                                    yield f"\n{'='*50}\nFULLSTACK SERVERS STARTED!\nFrontend (Preview): {preview_url}\nBackend API: {backend_url}\n{'='*50}\n\n_PREVIEW_URL_:{preview_url}\n"
                                else:
                                    preview_url = get_preview_url(detected_port, project_id)
                                    yield f"\n{'='*50}\nSERVER STARTED!\nPreview URL: {preview_url}\n{'='*50}\n\n_PREVIEW_URL_:{preview_url}\n"

                    # NOTE: Background error monitoring is now handled by the reader thread itself
                    # (read_output_with_monitoring) which continues running after the 15s join timeout
                    if server_started and proc and proc.poll() is None:
                        logger.info(f"[DockerExecutor:{project_id}] Reader thread continuing to monitor for errors in background")

                    # Handle port conflict with automatic retry
                    if port_conflict_detected and port_conflict_retries < MAX_PORT_CONFLICT_RETRIES:
                        port_conflict_retries += 1
                        old_port = host_port
                        # Get a new available port
                        host_port = self._get_available_port(host_port + 1)
                        self._assigned_ports[project_id] = host_port
                        yield f"\n{'='*50}\n"
                        yield f"PORT CONFLICT DETECTED on port {old_port}!\n"
                        yield f"Auto-allocating new port: {host_port}\n"
                        yield f"Retry attempt {port_conflict_retries}/{MAX_PORT_CONFLICT_RETRIES}\n"
                        yield f"{'='*50}\n\n"
                        logger.info(f"[DockerExecutor:{project_id}] Port conflict retry {port_conflict_retries}: {old_port} -> {host_port}")
                        # Kill the current process if running
                        if proc and proc.poll() is None:
                            proc.terminate()
                            try:
                                proc.wait(timeout=5)
                            except:
                                proc.kill()
                        # Regenerate command with new port and retry (safe port replacement)
                        new_command = replace_port_in_command(command, old_port, host_port)
                        port_conflict_detected = False
                        has_error = False
                        # Execute the new command
                        yield f"$ {new_command}\n"
                        proc = sync_subprocess.Popen(
                            new_command, shell=True, cwd=str(working_dir), env=env,
                            stdout=sync_subprocess.PIPE, stderr=sync_subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace'
                        )
                        self._running_processes[project_id] = proc
                        output_lines = []
                        def read_output_retry():
                            try:
                                for line in iter(proc.stdout.readline, ''):
                                    if line:
                                        output_lines.append(line.rstrip())
                            except:
                                pass
                        reader = threading.Thread(target=read_output_retry, daemon=True)
                        reader.start()
                        reader.join(timeout=15)
                        all_output = '\n'.join(output_lines)
                        exit_code = proc.poll()
                        # Process the new output
                        lines = [l for l in all_output.strip().split('\n') if l.strip()]
                        for line in lines:
                            yield f"{line}\n"
                            error_buffer.append(line)
                            if len(error_buffer) > 100:
                                error_buffer.pop(0)
                            if self._is_port_conflict(line):
                                port_conflict_detected = True
                            if ('localhost' in line.lower() or 'http://' in line.lower()) and not server_started:
                                detected_port = self._extract_port_from_output(line, framework)
                                if detected_port:
                                    server_started = True
                                    # For FULLSTACK projects, ALWAYS use the frontend port for preview
                                    if framework in [FrameworkType.FULLSTACK_REACT_SPRING, FrameworkType.FULLSTACK_REACT_EXPRESS, FrameworkType.FULLSTACK_REACT_FASTAPI]:
                                        preview_url = get_preview_url(host_port, project_id)
                                        backend_port = host_port + 1000
                                        backend_url = get_direct_preview_url(backend_port)
                                        yield f"\n{'='*50}\nFULLSTACK SERVERS STARTED!\nFrontend (Preview): {preview_url}\nBackend API: {backend_url}\n{'='*50}\n\n_PREVIEW_URL_:{preview_url}\n"
                                    else:
                                        preview_url = get_preview_url(detected_port, project_id)
                                        yield f"\n{'='*50}\nSERVER STARTED!\nPreview URL: {preview_url}\n{'='*50}\n\n_PREVIEW_URL_:{preview_url}\n"

                    # ============================================================
                    # DYNAMIC AUTO-FIX: Triggered for ANY failure, not just patterns!
                    # Claude will analyze the FULL output and determine the fix.
                    # ============================================================
                    if exit_code is not None and exit_code != 0 and not port_conflict_detected:
                        error_msg = f"Command '{command}' exited with code: {exit_code}"
                        yield f"{error_msg}\n"
                        full_context = '\n'.join(error_buffer[-50:]) or f"Command: {command}"
                        log_bus.add_build_error(message=f"{error_msg}\n\nFull Output:\n{full_context}")
                        # DYNAMIC: Send FULL output to Claude for analysis - no pattern matching needed!
                        logger.info(f"[DockerExecutor:{project_id}] DYNAMIC AUTO-FIX triggered (exit_code={exit_code})")
                        self._trigger_auto_fix_background(project_id, project_path, full_context, command, getattr(self, '_current_user_id', None))
                    elif has_error and not port_conflict_detected:
                        full_context = '\n'.join(error_buffer[-50:])
                        log_bus.add_build_error(message=f"Errors detected:\n\n{full_context}")
                        # DYNAMIC: Pattern-detected errors also sent to Claude for smart fixing
                        logger.info(f"[DockerExecutor:{project_id}] DYNAMIC AUTO-FIX triggered (pattern match)")
                        self._trigger_auto_fix_background(project_id, project_path, full_context, command, getattr(self, '_current_user_id', None))

                else:
                    process = await asyncio.create_subprocess_shell(
                        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                        cwd=str(working_dir), env=env
                    )
                    self._running_processes[project_id] = process
                    server_started = False
                    lines_read = 0

                    if process.stdout:
                        async for line in process.stdout:
                            lines_read += 1
                            output = line.decode('utf-8', errors='replace').strip()
                            if output:
                                yield f"{output}\n"
                                error_buffer.append(output)
                                if len(error_buffer) > 100:
                                    error_buffer.pop(0)
                                if any(p in output for p in error_patterns):
                                    has_error = True
                                    # Check for critical errors that need immediate auto-fix
                                    # (even if server is still running)
                                    critical_error_patterns = [
                                        'Failed to resolve import',
                                        'Does the file exist',
                                        '[plugin:vite',
                                        'Cannot find module',
                                        'Module not found',
                                        # Maven/Java critical errors
                                        '[FATAL]',
                                        'Non-parseable POM',
                                        'BUILD FAILURE',
                                        'Compilation failure',
                                        # General fatal errors
                                        'FATAL ERROR',
                                        'fatal error',
                                    ]
                                    if any(p in output for p in critical_error_patterns):
                                        full_context = '\n'.join(error_buffer[-50:])
                                        log_bus.add_build_error(message=f"Critical error detected:\n\n{full_context}")
                                        # Trigger auto-fix immediately for critical errors
                                        self._trigger_auto_fix_background(project_id, project_path, full_context, command, getattr(self, '_current_user_id', None))
                                        logger.info(f"[DockerExecutor:{project_id}] Critical error triggered auto-fix: {output[:100]}")
                                # Detect port conflicts for auto-retry
                                if self._is_port_conflict(output):
                                    port_conflict_detected = True
                                    conflicting_port = self._extract_conflicting_port(output)
                                    logger.warning(f"[DockerExecutor:{project_id}] Port conflict detected on port {conflicting_port or host_port}")
                                if not server_started:
                                    detected_port = self._extract_port_from_output(output, framework)
                                    if detected_port:
                                        server_started = True
                                        # For FULLSTACK projects, ALWAYS use the frontend port for preview
                                        if framework in [FrameworkType.FULLSTACK_REACT_SPRING, FrameworkType.FULLSTACK_REACT_EXPRESS, FrameworkType.FULLSTACK_REACT_FASTAPI]:
                                            preview_url = get_preview_url(host_port, project_id)
                                            backend_port = host_port + 1000
                                            backend_url = get_direct_preview_url(backend_port)
                                            yield f"\n{'='*50}\nFULLSTACK SERVERS STARTED!\nFrontend (Preview): {preview_url}\nBackend API: {backend_url}\n{'='*50}\n\n_PREVIEW_URL_:{preview_url}\n"
                                        else:
                                            preview_url = get_preview_url(detected_port, project_id)
                                            yield f"\n{'='*50}\nSERVER STARTED!\nPreview URL: {preview_url}\n{'='*50}\n\n_PREVIEW_URL_:{preview_url}\n"

                    await process.wait()

                    # Handle port conflict with automatic retry (Unix/async path)
                    if port_conflict_detected and port_conflict_retries < MAX_PORT_CONFLICT_RETRIES:
                        port_conflict_retries += 1
                        old_port = host_port
                        # Get a new available port
                        host_port = self._get_available_port(host_port + 1)
                        self._assigned_ports[project_id] = host_port
                        yield f"\n{'='*50}\n"
                        yield f"PORT CONFLICT DETECTED on port {old_port}!\n"
                        yield f"Auto-allocating new port: {host_port}\n"
                        yield f"Retry attempt {port_conflict_retries}/{MAX_PORT_CONFLICT_RETRIES}\n"
                        yield f"{'='*50}\n\n"
                        logger.info(f"[DockerExecutor:{project_id}] Port conflict retry {port_conflict_retries}: {old_port} -> {host_port}")
                        # Regenerate command with new port and retry (safe port replacement)
                        new_command = replace_port_in_command(command, old_port, host_port)
                        port_conflict_detected = False
                        has_error = False
                        # Execute the new command
                        yield f"$ {new_command}\n"
                        process = await asyncio.create_subprocess_shell(
                            new_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                            cwd=str(working_dir), env=env
                        )
                        self._running_processes[project_id] = process
                        if process.stdout:
                            async for line in process.stdout:
                                output = line.decode('utf-8', errors='replace').strip()
                                if output:
                                    yield f"{output}\n"
                                    error_buffer.append(output)
                                    if len(error_buffer) > 100:
                                        error_buffer.pop(0)
                                    if self._is_port_conflict(output):
                                        port_conflict_detected = True
                                    if not server_started:
                                        detected_port = self._extract_port_from_output(output, framework)
                                        if detected_port:
                                            server_started = True
                                            # For FULLSTACK projects, ALWAYS use the frontend port for preview
                                            if framework in [FrameworkType.FULLSTACK_REACT_SPRING, FrameworkType.FULLSTACK_REACT_EXPRESS, FrameworkType.FULLSTACK_REACT_FASTAPI]:
                                                preview_url = get_preview_url(host_port, project_id)
                                                backend_port = host_port + 1000
                                                backend_url = get_direct_preview_url(backend_port)
                                                yield f"\n{'='*50}\nFULLSTACK SERVERS STARTED!\nFrontend (Preview): {preview_url}\nBackend API: {backend_url}\n{'='*50}\n\n_PREVIEW_URL_:{preview_url}\n"
                                            else:
                                                preview_url = get_preview_url(detected_port, project_id)
                                                yield f"\n{'='*50}\nSERVER STARTED!\nPreview URL: {preview_url}\n{'='*50}\n\n_PREVIEW_URL_:{preview_url}\n"
                        await process.wait()

                    if process.returncode != 0 and not port_conflict_detected:
                        error_msg = f"Command '{command}' exited with code: {process.returncode}"
                        yield f"{error_msg}\n"
                        full_context = '\n'.join(error_buffer[-50:]) or f"No output. Command: {command}"
                        log_bus.add_build_error(message=f"{error_msg}\n\nFull Output:\n{full_context}")
                        # Trigger auto-fix in background
                        self._trigger_auto_fix_background(project_id, project_path, full_context, command, getattr(self, '_current_user_id', None))
                    elif has_error and not port_conflict_detected:
                        full_context = '\n'.join(error_buffer[-50:])
                        log_bus.add_build_error(message=f"Errors detected:\n\n{full_context}")
                        # Trigger auto-fix in background
                        self._trigger_auto_fix_background(project_id, project_path, full_context, command, getattr(self, '_current_user_id', None))

            except FileNotFoundError as e:
                error_msg = f"Command not found: {command}. Error: {str(e)}"
                yield f"ERROR: {error_msg}\n"
                log_bus.add_build_error(message=error_msg)
                logger.error(f"[DockerExecutor:{project_id}] Command not found: {error_msg}")
                # Trigger auto-fix in background
                self._trigger_auto_fix_background(project_id, project_path, error_msg, command, getattr(self, '_current_user_id', None))

            except PermissionError as e:
                error_msg = f"Permission denied running: {command}. Error: {str(e)}"
                yield f"ERROR: {error_msg}\n"
                log_bus.add_build_error(message=error_msg)
                logger.error(f"[DockerExecutor:{project_id}] Permission error: {error_msg}")
                # Trigger auto-fix in background
                self._trigger_auto_fix_background(project_id, project_path, error_msg, command, getattr(self, '_current_user_id', None))

            except Exception as e:
                import traceback
                error_msg = str(e) if str(e) else f"{type(e).__name__}: Unknown error"
                tb = traceback.format_exc()
                yield f"ERROR: {error_msg}\n"

                full_context = "\n".join(error_buffer[-50:]) if error_buffer else ""
                context_msg = f"Execution error: {error_msg}\n\nTraceback:\n{tb}"
                if full_context:
                    context_msg += f"\n\nCaptured Output:\n{full_context}"
                else:
                    context_msg += f"\n\nNo output captured. Command: {command}\nWorking directory: {project_path}"

                log_bus.add_build_error(message=context_msg)
                logger.error(f"[DockerExecutor:{project_id}] Exception: {error_msg}, context lines: {len(error_buffer)}, traceback: {tb[:500]}")
                # Trigger auto-fix in background
                self._trigger_auto_fix_background(project_id, project_path, context_msg, command, getattr(self, '_current_user_id', None))

    async def stop_direct(self, project_id: str) -> bool:
        """Stop a directly running process and all its children (Windows-compatible)"""
        stopped = False

        # Method 1: Kill process from our tracking dict
        if project_id in self._running_processes:
            process = self._running_processes[project_id]
            pid = process.pid
            try:
                # On Windows, we need to kill the entire process tree
                import platform
                if platform.system() == 'Windows':
                    # Use taskkill to kill process tree on Windows
                    import subprocess
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                                   capture_output=True, timeout=10)
                    logger.info(f"[Stop] Killed process tree for PID {pid}")
                else:
                    # On Unix, send SIGTERM to process group
                    import os
                    import signal
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass

                process.terminate()
                # Wait for process to finish (process.wait() is synchronous for subprocess.Popen)
                # Since we already killed the process tree with taskkill, just poll
                process.poll()
            except Exception as e:
                logger.warning(f"[Stop] Error stopping process {pid}: {e}")
            finally:
                del self._running_processes[project_id]
                stopped = True

        # Method 2: Kill any processes using the assigned port
        if project_id in self._assigned_ports:
            port = self._assigned_ports[project_id]
            try:
                await self._kill_process_on_port(port)
                logger.info(f"[Stop] Killed processes on port {port}")
            except Exception as e:
                logger.warning(f"[Stop] Error killing process on port {port}: {e}")
            finally:
                del self._assigned_ports[project_id]
                stopped = True

        return stopped

    async def _kill_process_on_port(self, port: int) -> bool:
        """Kill any process listening on the specified port"""
        import platform
        import subprocess

        try:
            if platform.system() == 'Windows':
                # Find PID using netstat
                result = subprocess.run(
                    ['netstat', '-ano'],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.splitlines():
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if parts:
                            pid = parts[-1]
                            if pid.isdigit():
                                subprocess.run(['taskkill', '/F', '/PID', pid],
                                             capture_output=True, timeout=10)
                                logger.info(f"[Stop] Killed PID {pid} on port {port}")
                                return True
            else:
                # Unix: use lsof or fuser
                result = subprocess.run(
                    ['lsof', '-t', f'-i:{port}'],
                    capture_output=True, text=True, timeout=10
                )
                pids = result.stdout.strip().splitlines()
                for pid in pids:
                    if pid.isdigit():
                        subprocess.run(['kill', '-9', pid], capture_output=True, timeout=10)
                        logger.info(f"[Stop] Killed PID {pid} on port {port}")
                        return True
        except Exception as e:
            logger.warning(f"[Stop] Error finding/killing process on port {port}: {e}")

        return False


    async def _ensure_essential_configs(self, project_path: Path, project_id: str) -> list:
        """
        Ensure essential config files exist for the project.
        Creates missing files from templates if they don't exist.
        
        Returns list of created files.
        """
        created_files = []
        
        # Detect project type
        frontend_path = project_path / 'frontend'
        has_frontend = frontend_path.exists()
        
        # Check for React/Vite indicators
        is_vite_react = False
        package_json_path = frontend_path / 'package.json' if has_frontend else project_path / 'package.json'
        
        if package_json_path.exists():
            try:
                import json
                with open(package_json_path, 'r') as f:
                    pkg = json.load(f)
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                is_vite_react = 'vite' in deps or 'react' in deps
            except:
                pass
        
        if not is_vite_react:
            return created_files
            
        # Essential files for Vite/React projects
        essential_files = {
            'tsconfig.json': VITE_REACT_TEMPLATES.get('tsconfig.json'),
            'tsconfig.node.json': VITE_REACT_TEMPLATES.get('tsconfig.node.json'),
            'tailwind.config.js': VITE_REACT_TEMPLATES.get('tailwind.config.js'),
            'postcss.config.js': VITE_REACT_TEMPLATES.get('postcss.config.js'),
            'vite.config.ts': VITE_REACT_TEMPLATES.get('vite.config.ts'),
        }
        
        # Determine base path
        base_path = frontend_path if has_frontend else project_path
        
        for filename, template_content in essential_files.items():
            if not template_content:
                continue
                
            file_path = base_path / filename
            if not file_path.exists():
                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(template_content)
                    created_files.append(str(filename))
                    logger.info(f'[DockerExecutor:{project_id}] Created missing config: {filename}')
                except Exception as e:
                    logger.warning(f'[DockerExecutor:{project_id}] Failed to create {filename}: {e}')
        
        return created_files

    # ============= SMART RUN (DOCKER WITH FALLBACK) =============

    async def run_project(
        self,
        project_id: str,
        project_path: Path,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Smart run with UNIVERSAL AUTO-FIX: Try Docker first, fall back to direct execution.

        Flow:
        0. SMART ANALYSIS: Proactively analyze project structure and apply auto-fixes
        1. PRE-RUN SETUP: Auto-install dependencies (npm install, pip install, etc.)
        2. Check if Docker is available
        3. If yes: Run in Docker container
        4. If no: Fall back to direct execution
        5. Stream output and detect server start
        6. AUTO-FIX any errors that occur
        7. Return preview URL

        This is the PERMANENT solution that automatically fixes ALL errors.
        """
        # VERSION MARKER - used to verify deployment
        yield "🚀 BharatBuild Executor v2.1 (Remote Docker Support)\n"

        # Check if using remote Docker (EC2 sandbox) - files are on EC2, not local ECS
        sandbox_docker_host = os.getenv("SANDBOX_DOCKER_HOST")
        is_remote_docker = bool(sandbox_docker_host)

        # Debug: Log environment status
        logger.info(f"[SmartRun:{project_id}] SANDBOX_DOCKER_HOST={sandbox_docker_host}, is_remote={is_remote_docker}")
        yield f"  🔧 Environment: {'EC2 Sandbox' if is_remote_docker else 'Local Docker'}\n"

        if is_remote_docker:
            logger.info(f"[SmartRun:{project_id}] Using remote Docker: {sandbox_docker_host}")
            yield "🐳 Running on remote Docker sandbox...\n"

        # ===== SMART PROJECT ANALYSIS: Proactive detection & auto-fix =====
        # This runs BEFORE anything else to understand the project and prevent errors
        yield "🧠 Analyzing project structure...\n"

        try:
            # Skip local file analysis when using remote Docker (files are on EC2)
            if is_remote_docker:
                # Use container_executor for remote execution
                logger.info(f"[SmartRun:{project_id}] Skipping local analysis (files on remote EC2)")
                yield "  📁 Remote sandbox mode - using container executor\n"

                # Delegate to container_executor which handles remote Docker
                async for output in container_executor.run_project(
                    project_id=project_id,
                    project_path=str(project_path),
                    user_id=user_id
                ):
                    yield output
                return

            # Analyze project proactively (only for local Docker)
            project_structure = await smart_analyzer.analyze_project(
                project_id=project_id,
                user_id=user_id or "anonymous",
                project_path=project_path
            )

            yield f"  📁 Technology: {project_structure.technology.value}\n"
            yield f"  📂 Working Directory: {project_structure.working_directory.name}/\n"
            yield f"  🔌 Default Port: {project_structure.default_port}\n"

            # Report any issues detected
            if project_structure.issues:
                yield f"  ⚠️ {len(project_structure.issues)} issues detected:\n"
                for issue in project_structure.issues[:3]:  # Show max 3
                    yield f"     • {issue}\n"

            # Apply auto-fixes proactively
            if project_structure.auto_fixes:
                yield f"  🔧 Applying {len(project_structure.auto_fixes)} auto-fixes...\n"
                files_modified = await smart_analyzer.apply_auto_fixes(
                    project_id=project_id,
                    user_id=user_id or "anonymous",
                    structure=project_structure
                )
                for f in files_modified:
                    yield f"     ✅ Created: {f}\n"

            yield "✅ Smart analysis complete\n\n"

            # Use the analyzer's detected working directory
            effective_working_dir = project_structure.working_directory
            logger.info(f"[SmartRun:{project_id}] Using working dir: {effective_working_dir}")

        except Exception as e:
            logger.warning(f"[SmartRun:{project_id}] Smart analysis failed (continuing): {e}")
            yield f"  ⚠️ Smart analysis failed (continuing anyway): {str(e)[:50]}\n\n"
            effective_working_dir = project_path  # Fall back to project root

        # ===== PRE-RUN SETUP: Install dependencies BEFORE running =====
        yield "🔧 Running pre-flight checks...\n"

        autofixer = UniversalAutoFixer(project_id, project_path, user_id)
        setup_commands = await autofixer.pre_run_checks()

        if setup_commands:
            yield f"📦 Installing dependencies ({len(setup_commands)} tasks)...\n"
            for cmd, work_dir in setup_commands:
                yield f"  → {cmd}\n"
                exit_code, stdout, stderr = await autofixer.execute_command(cmd, cwd=work_dir, timeout=180)
                if exit_code == 0:
                    yield f"  ✅ {cmd} completed\n"
                else:
                    yield f"  ⚠️ {cmd} had issues (attempting fix...)\n"
                    # Use optimized SimpleFixer (Haiku + minimal context) instead of expensive ProductionFixerAgent
                    if stderr:
                        try:
                            # SimpleFixer expects: project_path, command, output, exit_code
                            result = await simple_fixer.fix(
                                project_path=project_path,
                                command=cmd,
                                output=stderr[:2000],
                                exit_code=exit_code
                            )
                            if result.success:
                                yield f"  ✅ SimpleFixer fixed the issue\n"
                            else:
                                yield f"  ⚠️ Could not auto-fix (continuing anyway)\n"
                        except Exception as fix_err:
                            logger.warning(f"[DockerExecutor:{project_id}] SimpleFixer failed: {fix_err}")
                            yield f"  ⚠️ Auto-fix failed (continuing anyway)\n"

        yield "✅ Pre-flight checks complete\n\n"

        # ===== PROACTIVE IMPORT VALIDATION: Check for missing imports BEFORE running =====
        # This catches "Failed to resolve import" errors before Vite even starts!
        yield "🔍 Validating imports...\n"
        imports_valid = await self._validate_imports_proactively(project_id, project_path, user_id)
        if imports_valid:
            yield "✅ All imports validated\n\n"
        else:
            yield "⚠️ Missing imports detected - SDK Fixer Agent triggered in background\n"
            yield "   (The server will start while missing files are being generated)\n\n"

        # ===== ENSURE ESSENTIAL CONFIG FILES: Create missing tsconfig, tailwind, etc. =====
        yield "📋 Checking essential config files...\n"
        created_configs = await self._ensure_essential_configs(project_path, project_id)
        if created_configs:
            for cfg in created_configs:
                yield f"  + Created missing: {cfg}\n"
            yield f"✅ Created {len(created_configs)} missing config files\n\n"
        else:
            yield "✅ All config files present\n\n"

        # Ensure Dockerfile exists
        framework, dockerfile_created = await self.ensure_dockerfile(project_path)

        # ===== FULLSTACK INTEGRATION: Configure frontend-backend communication =====
        if framework in [FrameworkType.FULLSTACK_REACT_SPRING, FrameworkType.FULLSTACK_REACT_EXPRESS, FrameworkType.FULLSTACK_REACT_FASTAPI]:
            yield "🔗 Configuring frontend-backend integration...\n"
            try:
                # Get ports - frontend gets base port, backend gets +1000
                frontend_port = self._assigned_ports.get(project_id, 3000)
                backend_port = frontend_port + 1000

                integrator = FullstackIntegrator(project_path, frontend_port, backend_port)
                integration_result = await integrator.integrate()

                if integration_result.get("success"):
                    for action in integration_result.get("actions", []):
                        yield f"  ✅ {action}\n"
                    frontend_url = get_direct_preview_url(frontend_port)
                    backend_url = get_direct_preview_url(backend_port)
                    yield f"  📍 Frontend: {frontend_url}\n"
                    yield f"  📍 Backend API: {backend_url}\n"
                else:
                    yield f"  ⚠️ Integration had issues: {integration_result.get('error', 'Unknown')}\n"

                yield "✅ Frontend-Backend integration configured\n\n"
            except Exception as e:
                yield f"  ⚠️ Integration error (continuing anyway): {e}\n\n"

        if dockerfile_created:
            yield f"Auto-generated Dockerfile for {framework.value} project\n"
        else:
            yield f"Using existing Dockerfile (detected: {framework.value})\n"

        # Use run_direct which has container_executor logic with pre-built images
        # This spawns isolated containers using maven:3.9, node:20, python:3.11, etc.
        # Much faster than building Docker images from project Dockerfiles
        yield "🚀 Running with pre-built container images...\n"
        async for output in self.run_direct(project_id, project_path, framework, user_id=user_id):
            yield output

    async def stop_project(self, project_id: str) -> bool:
        """Stop a running project (container or direct process)"""
        # Try stopping container first
        container_stopped = await self.stop_container(project_id)

        # Also try stopping direct process
        direct_stopped = await self.stop_direct(project_id)

        return container_stopped or direct_stopped


# ============================================================================
# DOCKER-COMPOSE TEMPLATES (For full-stack projects)
# ============================================================================
#
# PORT ISOLATION STRATEGY FOR MULTI-USER PRODUCTION:
# ---------------------------------------------------
# Problem: If 100 users run Java/Spring Boot projects simultaneously,
#          all trying to use PostgreSQL on port 5432 → PORT CONFLICT!
#
# Solution: ISOLATED DOCKER NETWORKS + DYNAMIC PORT ALLOCATION
#
# 1. Each project gets its OWN Docker network (network: project_{id}_network)
# 2. Services communicate via SERVICE NAMES within the network:
#    - backend connects to "db:5432" (not localhost:5432)
#    - This works because they're on the same Docker network
# 3. Database ports are NOT exposed to host (no port mapping)
#    - Only frontend/backend ports are exposed with DYNAMIC allocation
# 4. The DockerComposeExecutor replaces ${FRONTEND_PORT}, ${BACKEND_PORT}
#    with dynamically allocated available ports
#
# Result: User A's PostgreSQL and User B's PostgreSQL both run on internal
#         port 5432, but in SEPARATE networks, so NO CONFLICT!
# ============================================================================

DOCKER_COMPOSE_TEMPLATES = {
    "fullstack_react_fastapi": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
    volumes:
      - ./backend:/app
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    networks:
      - app_network
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # NO PORT EXPOSED TO HOST - only accessible within app_network
    networks:
      - app_network

networks:
  app_network:
    driver: bridge

volumes:
  postgres_data:
''',

    "fullstack_react_django": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
      - DEBUG=True
    depends_on:
      - db
    volumes:
      - ./backend:/app
    command: python manage.py runserver 0.0.0.0:8000
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    networks:
      - app_network
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app_network

networks:
  app_network:
    driver: bridge

volumes:
  postgres_data:
''',

    "frontend_only": '''version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    volumes:
      - .:/app
      - /app/node_modules
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge
''',

    "backend_only_python": '''version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
    depends_on:
      - db
    volumes:
      - .:/app
    networks:
      - app_network
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app_network

networks:
  app_network:
    driver: bridge

volumes:
  postgres_data:
''',

    # ============== MYSQL TEMPLATES ==============
    "fullstack_react_mysql": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=mysql://root:password@db:3306/app
      - MYSQL_HOST=db
      - MYSQL_USER=root
      - MYSQL_PASSWORD=password
      - MYSQL_DATABASE=app
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=app
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - app_network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  app_network:
    driver: bridge

volumes:
  mysql_data:
''',

    # ============== MONGODB TEMPLATES ==============
    "fullstack_react_mongodb": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - MONGODB_URL=mongodb://mongo:27017/app
      - MONGO_HOST=mongo
      - MONGO_DB=app
    depends_on:
      - mongo
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

  mongo:
    image: mongo:6.0
    volumes:
      - mongo_data:/data/db
    networks:
      - app_network

networks:
  app_network:
    driver: bridge

volumes:
  mongo_data:
''',

    # ============== POSTGRESQL + REDIS (Full Production Stack) ==============
    "fullstack_production": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
      - NEXT_PUBLIC_WS_URL=ws://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - app_network
    command: redis-server --appendonly yes

  # Optional: Background worker for async tasks
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.celery worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
''',

    # ============== SPRING BOOT + POSTGRESQL ==============
    "fullstack_spring_postgres": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8080"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:postgresql://db:5432/app
      - SPRING_DATASOURCE_USERNAME=postgres
      - SPRING_DATASOURCE_PASSWORD=postgres
      - SPRING_JPA_HIBERNATE_DDL_AUTO=update
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  app_network:
    driver: bridge

volumes:
  postgres_data:
''',

    # ============== SPRING BOOT + MYSQL ==============
    "fullstack_spring_mysql": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8080"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://db:3306/app?useSSL=false&allowPublicKeyRetrieval=true
      - SPRING_DATASOURCE_USERNAME=root
      - SPRING_DATASOURCE_PASSWORD=password
      - SPRING_JPA_HIBERNATE_DDL_AUTO=update
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=app
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - app_network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  app_network:
    driver: bridge

volumes:
  mysql_data:
''',

    # ============== EXPRESS + MONGODB (MERN Stack) ==============
    "mern_stack": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:5000"
    environment:
      - MONGODB_URI=mongodb://mongo:27017/app
      - JWT_SECRET=your-secret-key
      - NODE_ENV=development
    depends_on:
      - mongo
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

  mongo:
    image: mongo:6.0
    volumes:
      - mongo_data:/data/db
    networks:
      - app_network

networks:
  app_network:
    driver: bridge

volumes:
  mongo_data:
''',
}


# ============================================================================
# SHARED INFRASTRUCTURE TEMPLATES (Production Mode)
# ============================================================================
# These templates connect to EXTERNAL shared database infrastructure
# instead of spinning up per-project database containers.
#
# Benefits:
# - 1 PostgreSQL cluster serves 10,000+ projects
# - Faster startup (no DB container init)
# - Lower resource usage
# - Easier management and backups
# ============================================================================

SHARED_INFRA_TEMPLATES = {
    # ============== React + FastAPI (Shared PostgreSQL) ==============
    "shared_react_fastapi_postgres": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      # Injected by BharatBuild - connects to shared infrastructure
      - DATABASE_URL=${DATABASE_URL}
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_PORT=${POSTGRES_PORT}
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - REDIS_URL=${REDIS_URL}
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge
''',

    # ============== React + Django (Shared PostgreSQL) ==============
    "shared_react_django_postgres": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_PORT=${POSTGRES_PORT}
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - DEBUG=False
    command: python manage.py runserver 0.0.0.0:8000
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge
''',

    # ============== Spring Boot + PostgreSQL (Shared) ==============
    "shared_spring_postgres": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8080"
    environment:
      # Spring Boot auto-configures from these
      - SPRING_DATASOURCE_URL=${SPRING_DATASOURCE_URL}
      - SPRING_DATASOURCE_USERNAME=${SPRING_DATASOURCE_USERNAME}
      - SPRING_DATASOURCE_PASSWORD=${SPRING_DATASOURCE_PASSWORD}
      - SPRING_JPA_HIBERNATE_DDL_AUTO=update
      - SPRING_JPA_SHOW_SQL=false
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge
''',

    # ============== Spring Boot + MySQL (Shared) ==============
    "shared_spring_mysql": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8080"
    environment:
      - SPRING_DATASOURCE_URL=${SPRING_DATASOURCE_URL}
      - SPRING_DATASOURCE_USERNAME=${SPRING_DATASOURCE_USERNAME}
      - SPRING_DATASOURCE_PASSWORD=${SPRING_DATASOURCE_PASSWORD}
      - SPRING_JPA_HIBERNATE_DDL_AUTO=update
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge
''',

    # ============== Node.js/Express + MongoDB (Shared) ==============
    "shared_mern_mongodb": '''version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:5000"
    environment:
      - MONGODB_URI=${MONGODB_URL}
      - MONGO_URL=${MONGODB_URL}
      - JWT_SECRET=${JWT_SECRET}
      - NODE_ENV=production
    networks:
      - app_network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT}:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:${BACKEND_PORT}
    depends_on:
      - backend
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge
''',

    # ============== Backend Only (Shared PostgreSQL) ==============
    "shared_backend_postgres": '''version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_PORT=${POSTGRES_PORT}
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge
''',

    # ============== Backend Only (Shared MySQL) ==============
    "shared_backend_mysql": '''version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT}:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - MYSQL_HOST=${MYSQL_HOST}
      - MYSQL_PORT=${MYSQL_PORT}
      - MYSQL_DATABASE=${MYSQL_DATABASE}
      - MYSQL_USER=${MYSQL_USER}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
    networks:
      - app_network
    restart: unless-stopped

networks:
  app_network:
    driver: bridge
''',
}


class PortAllocator:
    """
    Dynamic Port Allocator for Multi-User Isolation

    Allocates unique ports for each project to avoid conflicts when
    multiple users run Docker containers simultaneously.

    Port Ranges:
    - Frontend: 3000-3999 (1000 projects)
    - Backend: 8000-8999 (1000 projects)
    - For overflow: 10000-65000
    """

    # Port ranges
    FRONTEND_PORT_START = 3000
    FRONTEND_PORT_END = 3999
    BACKEND_PORT_START = 8000
    BACKEND_PORT_END = 8999
    OVERFLOW_PORT_START = 10000

    def __init__(self):
        self._allocated_ports: Dict[str, Dict[str, int]] = {}  # project_id -> {frontend: port, backend: port}
        self._used_ports: set = set()

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available on the host"""
        import socket
        if port in self._used_ports:
            return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def _find_available_port(self, start: int, end: int) -> Optional[int]:
        """Find an available port in range"""
        for port in range(start, end + 1):
            if self._is_port_available(port):
                return port
        # Overflow to high ports
        for port in range(self.OVERFLOW_PORT_START, 65000):
            if self._is_port_available(port):
                return port
        return None

    def allocate_ports(self, project_id: str) -> Dict[str, int]:
        """
        Allocate frontend and backend ports for a project.
        Returns {"frontend": port, "backend": port}
        """
        # Return existing allocation if already allocated
        if project_id in self._allocated_ports:
            return self._allocated_ports[project_id]

        # Find available ports
        frontend_port = self._find_available_port(
            self.FRONTEND_PORT_START,
            self.FRONTEND_PORT_END
        )
        backend_port = self._find_available_port(
            self.BACKEND_PORT_START,
            self.BACKEND_PORT_END
        )

        if frontend_port and backend_port:
            self._used_ports.add(frontend_port)
            self._used_ports.add(backend_port)

            allocation = {
                "frontend": frontend_port,
                "backend": backend_port
            }
            self._allocated_ports[project_id] = allocation

            logger.info(f"Allocated ports for project {project_id}: frontend={frontend_port}, backend={backend_port}")
            return allocation
        else:
            raise RuntimeError("No available ports - server at capacity")

    def release_ports(self, project_id: str):
        """Release ports when project stops"""
        if project_id in self._allocated_ports:
            allocation = self._allocated_ports[project_id]
            self._used_ports.discard(allocation.get("frontend"))
            self._used_ports.discard(allocation.get("backend"))
            del self._allocated_ports[project_id]
            logger.info(f"Released ports for project {project_id}")

    def get_ports(self, project_id: str) -> Optional[Dict[str, int]]:
        """Get allocated ports for a project"""
        return self._allocated_ports.get(project_id)


# Global port allocator
port_allocator = PortAllocator()


class DockerComposeExecutor:
    """
    Docker Compose Executor with Auto-Fix Loop and Multi-User Port Isolation

    Features:
    1. Runs docker-compose up and streams output
    2. Detects errors from build/runtime output
    3. Sends errors to Fixer Agent for automatic fixes
    4. Retries until successful or max retries reached
    5. DYNAMIC PORT ALLOCATION - Each project gets unique ports
    6. NETWORK ISOLATION - Each project runs in isolated Docker network
    """

    MAX_RETRIES = 3
    MAX_PORT_CONFLICT_RETRIES = 3
    ERROR_PATTERNS = [
        # ===== GENERAL =====
        r'error:?\s+(.+)',
        r'ERROR:?\s+(.+)',
        r'failed to build',
        r'command.*not found',
        r'permission denied',
        r'exited with code [1-9]',
        r'Uncaught',

        # ===== JAVASCRIPT/NODE.JS =====
        r'cannot find module',
        r'Module not found',
        r'SyntaxError:?\s+(.+)',
        r'TypeError:?\s+(.+)',
        r'ReferenceError:?\s+(.+)',
        r'npm ERR!',
        r'ENOENT',
        r'EACCES',
        r'Cannot find',
        r'Unexpected token',
        r'Cannot read property',
        r'is not defined',
        r'is not a function',

        # ===== VITE/BUNDLER SPECIFIC =====
        r'Failed to resolve import',
        r'Does the file exist',
        r'\[plugin:vite',
        r'vite:import-analysis',
        r'Could not resolve',
        r'Pre-transform error',
        r'Transform failed',
        r'Build failed',

        # ===== PYTHON =====
        r'ImportError:?\s+(.+)',
        r'ModuleNotFoundError:?\s+(.+)',
        r'NameError:?\s+(.+)',
        r'AttributeError:?\s+(.+)',
        r'KeyError:?\s+(.+)',
        r'IndentationError',
        r'pip install.*failed',
        r'Traceback \(most recent call last\)',
        r'FileNotFoundError',
        r'PermissionError',

        # ===== JAVA/SPRING BOOT =====
        r'java\.lang\.\w+Exception',
        r'javax\.\w+',
        r'NullPointerException',
        r'ClassNotFoundException',
        r'NoClassDefFoundError',
        r'IllegalArgumentException',
        r'IllegalStateException',
        r'BUILD FAILURE',
        r'BUILD FAILED',
        r'Compilation failure',
        r'cannot find symbol',
        r'incompatible types',
        r'Failed to execute goal',
        r'Could not resolve dependencies',
        r'BeanCreationException',
        r'NoSuchBeanDefinitionException',
        r'ApplicationContextException',
        r'org\.springframework\.',
        r'maven-compiler-plugin',
        r'Execution failed for task',
        r'JpaSystemException',
        r'DataIntegrityViolationException',
        r'org\.hibernate\.',
        r'HibernateException',
        r'BindException',
        r'MethodArgumentNotValidException',

        # ===== GO/GOLANG =====
        r'go:.*error',
        r'cannot find package',
        r'package .* is not in',
        r'undefined:',
        r'undeclared name',
        r'imported and not used',
        r'missing go\.sum entry',
        r'cannot load',
        r'cannot find module',
        r'panic:',
        r'runtime error:',
        r'goroutine .* \[running\]',
        r'build constraints exclude',
        r'invalid operation',
        r'type .* has no field or method',

        # ===== RUST =====
        r'error\[E\d+\]',
        r'cargo.*error',
        r'rustc.*error',

        # ===== PORT CONFLICTS =====
        r'EADDRINUSE',
        r'address already in use',
        r'port.*already.*in.*use',
        r'listen EADDRINUSE',
        r'bind.*address already in use',
    ]
    PORT_CONFLICT_PATTERNS = [
        'EADDRINUSE',
        'address already in use',
        'Address already in use',
        'port is already in use',
        'Port is already in use',
        'listen EADDRINUSE',
        'Error: listen EADDRINUSE',
        'bind: address already in use',
        'Only one usage of each socket address',
        'port already allocated',
        'Address in use',
    ]

    def __init__(self):
        self._running_compose: Dict[str, asyncio.subprocess.Process] = {}
        self._error_buffer: Dict[str, List[str]] = {}

    def _is_error_line(self, line: str) -> bool:
        """Check if a line contains an error"""
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _is_port_conflict(self, line: str) -> bool:
        """Check if a line indicates a port conflict"""
        line_lower = line.lower()
        for pattern in self.PORT_CONFLICT_PATTERNS:
            if pattern.lower() in line_lower:
                return True
        return False

    def _extract_error_info(self, output_lines: List[str]) -> Dict[str, Any]:
        """Extract error information from output"""
        errors = []
        error_context = []
        is_port_conflict = False

        for i, line in enumerate(output_lines):
            # Check for port conflicts (handle specially)
            if self._is_port_conflict(line):
                is_port_conflict = True
            if self._is_error_line(line):
                # Get context (5 lines before and after)
                start = max(0, i - 5)
                end = min(len(output_lines), i + 6)
                context = output_lines[start:end]

                errors.append({
                    "line": line.strip(),
                    "line_number": i,
                    "context": "\n".join(context)
                })

        if errors:
            return {
                "has_errors": True,
                "is_port_conflict": is_port_conflict,
                "error_count": len(errors),
                "errors": errors,
                "full_output": "\n".join(output_lines[-100:])  # Last 100 lines
            }

        return {"has_errors": False, "is_port_conflict": False}

    async def _check_docker_compose_available(self) -> bool:
        """Check if docker-compose is available"""
        try:
            # Try new 'docker compose' command first
            process = await asyncio.create_subprocess_exec(
                "docker", "compose", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            if process.returncode == 0:
                return True

            # Fall back to 'docker-compose'
            process = await asyncio.create_subprocess_exec(
                "docker-compose", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking docker-compose: {e}")
            return False

    def _get_compose_command(self) -> List[str]:
        """Get the appropriate docker-compose command"""
        # Prefer 'docker compose' (new) over 'docker-compose' (old)
        return ["docker", "compose"]

    async def generate_docker_compose(
        self,
        project_path: Path,
        project_id: Optional[str] = None
    ) -> Tuple[Optional[str], Dict[str, int]]:
        """
        Generate appropriate docker-compose.yml based on project structure.

        MULTI-USER ISOLATION:
        - Allocates unique ports for frontend and backend
        - Replaces ${FRONTEND_PORT} and ${BACKEND_PORT} in template
        - Creates project-specific Docker network

        Returns (template_name, {"frontend": port, "backend": port})
        """
        compose_path = project_path / "docker-compose.yml"

        # Allocate unique ports for this project
        if project_id:
            ports = port_allocator.allocate_ports(project_id)
        else:
            # Generate temp project_id if not provided
            import uuid
            temp_id = str(uuid.uuid4())[:8]
            ports = port_allocator.allocate_ports(temp_id)

        frontend_port = ports["frontend"]
        backend_port = ports["backend"]

        # Check if already exists
        if compose_path.exists():
            logger.info(f"docker-compose.yml already exists at {project_path}")
            # Still need to update ports in existing file
            with open(compose_path, 'r') as f:
                existing_content = f.read()

            # Replace port placeholders if present
            updated_content = existing_content.replace("${FRONTEND_PORT}", str(frontend_port))
            updated_content = updated_content.replace("${BACKEND_PORT}", str(backend_port))

            with open(compose_path, 'w') as f:
                f.write(updated_content)

            return "existing", ports

        # Detect project structure
        has_frontend = (project_path / "frontend").exists() or (project_path / "package.json").exists()
        has_backend = (project_path / "backend").exists() or (project_path / "requirements.txt").exists()

        # Check for Spring Boot (pom.xml)
        has_spring = (project_path / "backend" / "pom.xml").exists() or (project_path / "pom.xml").exists()

        # Check for specific database requirements
        has_mysql = False
        has_mongodb = False
        has_postgres = True  # Default

        # Check requirements or config files for database type
        for config_file in ["requirements.txt", "package.json", "pom.xml"]:
            for search_path in [project_path, project_path / "backend"]:
                config_path = search_path / config_file
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            content = f.read().lower()
                            if "mysql" in content or "mariadb" in content:
                                has_mysql = True
                                has_postgres = False
                            elif "mongodb" in content or "mongoose" in content:
                                has_mongodb = True
                                has_postgres = False
                    except:
                        pass

        # Determine framework
        framework_type = docker_executor.detect_framework(project_path)

        # Select template
        template_name = None
        template_content = None

        if has_frontend and has_backend:
            # Full-stack
            if has_spring:
                if has_mysql:
                    template_name = "fullstack_spring_mysql"
                else:
                    template_name = "fullstack_spring_postgres"
            elif has_mongodb:
                template_name = "fullstack_react_mongodb"
            elif has_mysql:
                template_name = "fullstack_react_mysql"
            else:
                backend_path = project_path / "backend"
                if backend_path.exists():
                    req_path = backend_path / "requirements.txt"
                    if req_path.exists():
                        with open(req_path) as f:
                            reqs = f.read().lower()
                            if "django" in reqs:
                                template_name = "fullstack_react_django"
                            else:
                                template_name = "fullstack_react_fastapi"
                    else:
                        template_name = "fullstack_react_fastapi"
                else:
                    template_name = "fullstack_react_fastapi"
        elif has_frontend:
            template_name = "frontend_only"
        elif has_backend:
            template_name = "backend_only_python"
        else:
            # Use frontend_only as fallback
            template_name = "frontend_only"

        template_content = DOCKER_COMPOSE_TEMPLATES.get(template_name)

        if template_content:
            # Replace port placeholders with allocated ports
            template_content = template_content.replace("${FRONTEND_PORT}", str(frontend_port))
            template_content = template_content.replace("${BACKEND_PORT}", str(backend_port))

            # Replace network name with project-specific name for extra isolation
            if project_id:
                short_id = project_id[:8] if len(project_id) > 8 else project_id
                template_content = template_content.replace(
                    "app_network",
                    f"project_{short_id}_network"
                )

            with open(compose_path, 'w') as f:
                f.write(template_content)
            logger.info(f"Generated docker-compose.yml using template: {template_name}")
            logger.info(f"Ports allocated - frontend: {frontend_port}, backend: {backend_port}")
            return template_name, ports

        return None, ports

    async def run_compose(
        self,
        project_id: str,
        project_path: Path,
        build: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Run docker-compose up and stream output.
        Detects errors and yields error info for auto-fix.
        """
        compose_cmd = self._get_compose_command()
        cmd = compose_cmd + ["up"]

        if build:
            cmd.append("--build")

        yield f"$ {' '.join(cmd)}\n"
        yield f"Working directory: {project_path}\n\n"

        output_lines = []
        server_started = False

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            self._running_compose[project_id] = process

            async for line in process.stdout:
                output = line.decode().strip()
                output_lines.append(output)

                if output:
                    yield f"{output}\n"

                    # Detect server start
                    if not server_started:
                        for pattern in PORT_PATTERNS:
                            if re.search(pattern, output, re.IGNORECASE):
                                server_started = True
                                # Try to extract port
                                match = re.search(r':(\d+)', output)
                                detected_port = int(match.group(1)) if match else 3000

                                # For fullstack Docker Compose, prefer the frontend port
                                is_fullstack = (project_path / "frontend").exists() and (project_path / "backend").exists()
                                allocated = port_allocator.get_ports(project_id)

                                if is_fullstack and allocated:
                                    # Use frontend port for preview (user wants to see UI, not API)
                                    frontend_port = allocated.get("frontend", detected_port)
                                    backend_port_val = allocated.get("backend", detected_port + 1000)
                                    preview_url = get_preview_url(frontend_port, project_id)
                                    backend_url = get_direct_preview_url(backend_port_val)
                                    yield f"\n{'='*50}\n"
                                    yield f"FULLSTACK SERVERS STARTED!\n"
                                    yield f"Frontend (Preview): {preview_url}\n"
                                    yield f"Backend API: {backend_url}\n"
                                    yield f"{'='*50}\n"
                                    yield f"_PREVIEW_URL_:{preview_url}\n"
                                else:
                                    preview_url = get_preview_url(detected_port, project_id)
                                    yield f"\n{'='*50}\n"
                                    yield f"SERVER STARTED!\n"
                                    yield f"Preview URL: {preview_url}\n"
                                    yield f"{'='*50}\n"
                                    yield f"_PREVIEW_URL_:{preview_url}\n"
                                break

            await process.wait()

            # Check for errors
            if process.returncode != 0:
                error_info = self._extract_error_info(output_lines)
                yield f"__COMPOSE_ERROR__:{json.dumps(error_info)}\n"
            elif not server_started:
                yield f"Compose completed with exit code: {process.returncode}\n"

        except Exception as e:
            yield f"ERROR: {str(e)}\n"
            yield f"__COMPOSE_ERROR__:{json.dumps({'has_errors': True, 'errors': [{'line': str(e)}]})}\n"
        finally:
            if project_id in self._running_compose:
                del self._running_compose[project_id]

    async def stop_compose(self, project_id: str, project_path: Path) -> bool:
        """Stop docker-compose services and release ports"""
        try:
            compose_cmd = self._get_compose_command()
            process = await asyncio.create_subprocess_exec(
                *compose_cmd, "down", "--remove-orphans",
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.wait(), timeout=30.0)

            if project_id in self._running_compose:
                del self._running_compose[project_id]

            # Release allocated ports
            port_allocator.release_ports(project_id)

            logger.info(f"Stopped compose and released ports for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping compose: {e}")
            return False

    async def run_with_auto_fix(
        self,
        project_id: str,
        project_path: Path,
        fixer_callback: Optional[callable] = None
    ) -> AsyncGenerator[str, None]:
        """
        Run docker-compose with automatic error fixing.

        Flow:
        1. Run docker-compose up
        2. If error detected, call fixer agent
        3. Apply fixes and retry
        4. Repeat until success or max retries

        MULTI-USER ISOLATION:
        - Each project gets unique ports (no conflicts!)
        - Each project runs in isolated Docker network
        - Database ports NOT exposed to host (internal only)
        """
        from app.modules.agents.production_fixer_agent import production_fixer_agent
        from app.modules.agents.base_agent import AgentContext

        # Ensure docker-compose.yml exists WITH UNIQUE PORTS
        template_used, ports = await self.generate_docker_compose(project_path, project_id)
        if template_used:
            yield f"Using docker-compose template: {template_used}\n"
            yield f"Allocated ports - Frontend: {ports['frontend']}, Backend: {ports['backend']}\n"
            yield f"Network: project_{project_id[:8]}_network (isolated)\n\n"

        retry_count = 0
        success = False

        while retry_count < self.MAX_RETRIES and not success:
            if retry_count > 0:
                yield f"\n{'='*50}\n"
                yield f"RETRY ATTEMPT {retry_count}/{self.MAX_RETRIES}\n"
                yield f"{'='*50}\n\n"

            error_info = None

            async for output in self.run_compose(project_id, project_path, build=True):
                yield output

                # Check for error marker
                if output.startswith("__COMPOSE_ERROR__:"):
                    error_json = output.replace("__COMPOSE_ERROR__:", "").strip()
                    try:
                        error_info = json.loads(error_json)
                    except:
                        error_info = {"has_errors": True, "errors": [{"line": error_json}]}

                # Check for success marker
                if output.startswith("__SERVER_STARTED__:"):
                    success = True

            if success:
                yield f"\n{'='*50}\n"
                yield f"PROJECT RUNNING SUCCESSFULLY!\n"
                yield f"{'='*50}\n"
                break

            if error_info and error_info.get("has_errors"):
                retry_count += 1

                if retry_count >= self.MAX_RETRIES:
                    yield f"\n{'='*50}\n"
                    yield f"MAX RETRIES REACHED ({self.MAX_RETRIES})\n"
                    yield f"Please fix errors manually.\n"
                    yield f"{'='*50}\n"
                    break

                # Stop current compose
                await self.stop_compose(project_id, project_path)

                # Handle port conflicts specially - reallocate ports without calling fixer agent
                if error_info.get("is_port_conflict"):
                    yield f"\n{'='*50}\n"
                    yield f"PORT CONFLICT DETECTED!\n"
                    yield f"Auto-reallocating ports and retrying...\n"
                    yield f"{'='*50}\n\n"
                    logger.info(f"[DockerComposeExecutor:{project_id}] Port conflict detected, reallocating ports")

                    # Release old ports and allocate new ones
                    port_allocator.release_ports(project_id)
                    new_ports = port_allocator.allocate_ports(project_id)

                    # Regenerate docker-compose.yml with new ports
                    compose_path = project_path / "docker-compose.yml"
                    if compose_path.exists():
                        with open(compose_path, 'r') as f:
                            compose_content = f.read()
                        # Replace old ports with new ports
                        compose_content = re.sub(
                            r'"(\d+):(\d+)"',
                            lambda m: f'"{new_ports["frontend"] if int(m.group(2)) in [3000, 5173, 4200] else new_ports["backend"]}:{m.group(2)}"',
                            compose_content
                        )
                        with open(compose_path, 'w') as f:
                            f.write(compose_content)

                    yield f"New ports allocated - Frontend: {new_ports['frontend']}, Backend: {new_ports['backend']}\n"
                    yield f"Retry attempt {retry_count}/{self.MAX_RETRIES}\n\n"
                    ports = new_ports
                    # Small delay before retry
                    await asyncio.sleep(2)
                    continue

                yield f"\n{'='*50}\n"
                yield f"ERRORS DETECTED - Attempting auto-fix...\n"
                yield f"{'='*50}\n\n"

                # Call fixer agent
                try:
                    # Get project files for context
                    project_files = []
                    file_contents = {}

                    for file_path in project_path.rglob("*"):
                        if file_path.is_file():
                            rel_path = str(file_path.relative_to(project_path)).replace("\\", "/")

                            skip_patterns = ['node_modules', '__pycache__', '.git', 'dist', 'build']
                            if any(p in rel_path for p in skip_patterns):
                                continue

                            project_files.append(rel_path)

                            if any(ext in rel_path for ext in ['.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.yml', '.yaml']):
                                try:
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()
                                        if len(content) < 50000:
                                            file_contents[rel_path] = content
                                except:
                                    pass

                    # Build error message
                    error_messages = [e.get("line", "") for e in error_info.get("errors", [])]
                    error_message = "\n".join(error_messages[:5])  # First 5 errors

                    context = AgentContext(
                        project_id=project_id,
                        user_prompt=f"Fix docker-compose build/runtime error: {error_message}",
                        metadata={
                            "error_message": error_message,
                            "stack_trace": error_info.get("full_output", ""),
                            "error_type": "docker_compose",
                            "project_files": project_files,
                            "file_contents": file_contents,
                            "project_path": str(project_path)
                        }
                    )

                    yield f"Calling Fixer Agent...\n"

                    result = await production_fixer_agent.process(context)

                    if result.get("success"):
                        fixed_files = result.get("fixed_files", [])

                        for file_info in fixed_files:
                            file_path_str = file_info.get("path")
                            content = file_info.get("content")

                            if file_path_str and content:
                                full_path = project_path / file_path_str
                                full_path.parent.mkdir(parents=True, exist_ok=True)

                                with open(full_path, 'w', encoding='utf-8') as f:
                                    f.write(content)

                                yield f"Fixed: {file_path_str}\n"

                        yield f"\nApplied {len(fixed_files)} fixes. Retrying...\n"
                    else:
                        yield f"Fixer agent could not fix errors: {result.get('error', 'Unknown')}\n"
                        yield f"Retrying anyway...\n"

                except Exception as e:
                    yield f"Error calling fixer agent: {str(e)}\n"
                    yield f"Retrying without fixes...\n"

                # Small delay before retry
                await asyncio.sleep(2)
            else:
                # No errors detected but also no server started
                yield f"Compose exited without errors or server detection.\n"
                break


# Global instances
docker_executor = DockerExecutor()
docker_compose_executor = DockerComposeExecutor()
