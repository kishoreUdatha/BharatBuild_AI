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
from pathlib import Path
from typing import Dict, Optional, List, Tuple, AsyncGenerator, Any
from dataclasses import dataclass
from enum import Enum

from app.core.logging_config import logger
from app.services.log_bus import get_log_bus

# Sandbox public URL for preview (use sandbox EC2 public IP/domain in production)
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL") or os.getenv("SANDBOX_PREVIEW_BASE_URL", "http://localhost")


def get_preview_url(port: int) -> str:
    """Generate preview URL using sandbox public URL or localhost fallback"""
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        return f"{base}:{port}"
    return f"http://localhost:{port}"


class FrameworkType(Enum):
    REACT_VITE = "react-vite"
    REACT_CRA = "react-cra"
    NEXTJS = "nextjs"
    VUE = "vue"
    ANGULAR = "angular"
    NODE_EXPRESS = "node-express"
    PYTHON_FLASK = "python-flask"
    PYTHON_FASTAPI = "python-fastapi"
    PYTHON_DJANGO = "python-django"
    PYTHON_STREAMLIT = "python-streamlit"
    SPRING_BOOT = "spring-boot"
    GO = "go"
    STATIC_HTML = "static-html"
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
    FrameworkType.REACT_VITE: 5173,
    FrameworkType.REACT_CRA: 3000,
    FrameworkType.NEXTJS: 3000,
    FrameworkType.VUE: 5173,
    FrameworkType.ANGULAR: 4200,
    FrameworkType.NODE_EXPRESS: 3000,
    FrameworkType.PYTHON_FLASK: 5000,
    FrameworkType.PYTHON_FASTAPI: 8000,
    FrameworkType.PYTHON_DJANGO: 8000,
    FrameworkType.PYTHON_STREAMLIT: 8501,
    FrameworkType.SPRING_BOOT: 8080,
    FrameworkType.GO: 8080,
    FrameworkType.STATIC_HTML: 80,
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

    def detect_framework(self, project_path: Path) -> FrameworkType:
        """Detect the framework type from project files"""

        # Check for package.json (Node.js projects)
        package_json_path = project_path / "package.json"
        if package_json_path.exists():
            try:
                with open(package_json_path, 'r') as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                    # Check for specific frameworks
                    if "next" in deps:
                        return FrameworkType.NEXTJS
                    elif "vite" in deps:
                        if "vue" in deps:
                            return FrameworkType.VUE
                        return FrameworkType.REACT_VITE
                    elif "react-scripts" in deps:
                        return FrameworkType.REACT_CRA
                    elif "react" in deps:
                        return FrameworkType.REACT_VITE  # Default React to Vite
                    elif "vue" in deps:
                        return FrameworkType.VUE
                    elif "@angular/core" in deps:
                        return FrameworkType.ANGULAR
                    elif "express" in deps:
                        return FrameworkType.NODE_EXPRESS
                    else:
                        return FrameworkType.NODE_EXPRESS  # Default Node.js
            except Exception as e:
                logger.warning(f"Error reading package.json: {e}")

        # Check for Python projects
        requirements_path = project_path / "requirements.txt"
        if requirements_path.exists():
            try:
                with open(requirements_path, 'r') as f:
                    reqs = f.read().lower()

                    if "streamlit" in reqs:
                        return FrameworkType.PYTHON_STREAMLIT
                    elif "fastapi" in reqs:
                        return FrameworkType.PYTHON_FASTAPI
                    elif "django" in reqs:
                        return FrameworkType.PYTHON_DJANGO
                    elif "flask" in reqs:
                        return FrameworkType.PYTHON_FLASK
                    else:
                        return FrameworkType.PYTHON_FLASK  # Default Python
            except Exception as e:
                logger.warning(f"Error reading requirements.txt: {e}")

        # Check for Spring Boot
        pom_path = project_path / "pom.xml"
        if pom_path.exists():
            return FrameworkType.SPRING_BOOT

        # Check for Go
        go_mod_path = project_path / "go.mod"
        if go_mod_path.exists():
            return FrameworkType.GO

        # Check for static HTML
        index_html_path = project_path / "index.html"
        if index_html_path.exists():
            return FrameworkType.STATIC_HTML

        return FrameworkType.UNKNOWN

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
            preview_url = get_preview_url(host_port)

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
                            yield f"\n{'='*50}\n"
                            yield f"SERVER STARTED!\n"
                            yield f"Preview URL: {preview_url}\n"
                            yield f"{'='*50}\n\n"

                            # Send special event for frontend
                            yield f"__SERVER_STARTED__:{preview_url}\n"

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
                        yield f"\n{'='*50}\n"
                        yield f"SERVER STARTED!\n"
                        yield f"Preview URL: {preview_url}\n"
                        yield f"{'='*50}\n\n"
                        yield f"__SERVER_STARTED__:{preview_url}\n"

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
            from app.modules.execution.docker_executor_new import get_preview_url as get_url
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

    def _get_run_commands(self, framework: FrameworkType, project_path: Path) -> List[str]:
        """Get the commands to run the project directly (without Docker)"""
        commands = []

        if framework in [FrameworkType.REACT_VITE, FrameworkType.VUE]:
            commands = ["npm install", "npm run dev -- --host 0.0.0.0"]
        elif framework == FrameworkType.REACT_CRA:
            commands = ["npm install", "npm start"]
        elif framework == FrameworkType.NEXTJS:
            commands = ["npm install", "npm run dev"]
        elif framework in [FrameworkType.NODE_EXPRESS, FrameworkType.UNKNOWN]:
            commands = ["npm install", "npm start"]
        elif framework == FrameworkType.ANGULAR:
            commands = ["npm install", "npm start -- --host 0.0.0.0"]
        elif framework == FrameworkType.PYTHON_FLASK:
            commands = ["pip install -r requirements.txt", "flask run --host 0.0.0.0"]
        elif framework == FrameworkType.PYTHON_FASTAPI:
            commands = ["pip install -r requirements.txt", "uvicorn main:app --host 0.0.0.0 --port 8000"]
        elif framework == FrameworkType.PYTHON_DJANGO:
            commands = ["pip install -r requirements.txt", "python manage.py runserver 0.0.0.0:8000"]
        elif framework == FrameworkType.PYTHON_STREAMLIT:
            commands = ["pip install -r requirements.txt", "streamlit run app.py --server.address 0.0.0.0"]
        elif framework == FrameworkType.SPRING_BOOT:
            commands = ["mvn package -DskipTests", "java -jar target/*.jar"]
        elif framework == FrameworkType.GO:
            commands = ["go build -o main .", "./main"]
        elif framework == FrameworkType.STATIC_HTML:
            commands = ["python -m http.server 3000"]

        return commands

    async def run_direct(
        self,
        project_id: str,
        project_path: Path,
        framework: FrameworkType
    ) -> AsyncGenerator[str, None]:
        """
        Run project directly on host (fallback when Docker unavailable).
        Now with LogBus integration for auto-fix!

        Windows compatibility: Uses proper encoding and streams output in real-time.
        """
        yield "Running project directly (Docker unavailable)...\n"

        # Get LogBus for error collection (Bolt.new style!)
        log_bus = get_log_bus(project_id)

        # Error patterns for detection
        error_patterns = [
            'error', 'Error', 'ERROR',
            'Failed', 'failed', 'FAILED',
            'Cannot find', 'cannot find',
            'Module not found', 'module not found',
            'npm ERR!', 'ERR!',
            'SyntaxError', 'TypeError', 'ReferenceError',
            'ENOENT', 'EACCES', 'EPERM',
            'fatal:', 'warning:', 'critical:',
            'Traceback', 'Exception',
            'Internal server error',
        ]

        # Buffer to collect error context
        error_buffer = []
        # Track if any errors were detected (for deferred LogBus addition)
        has_error = False

        commands = self._get_run_commands(framework, project_path)
        default_port = DEFAULT_PORTS.get(framework, 3000)
        host_port = self._get_available_port(default_port)

        self._assigned_ports[project_id] = host_port

        for command in commands:
            yield f"$ {command}\n"

