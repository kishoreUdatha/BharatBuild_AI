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
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking Docker: {e}")
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
            preview_url = f"http://localhost:{host_port}"

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
            return f"http://localhost:{port}"
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
        """
        yield "Running project directly (Docker unavailable)...\n"

        commands = self._get_run_commands(framework, project_path)
        default_port = DEFAULT_PORTS.get(framework, 3000)
        host_port = self._get_available_port(default_port)

        self._assigned_ports[project_id] = host_port

        for command in commands:
            yield f"$ {command}\n"

            try:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=str(project_path)
                )

                self._running_processes[project_id] = process

                async for line in process.stdout:
                    output = line.decode().strip()
                    if output:
                        yield f"{output}\n"

                        # Detect server start
                        detected_port = self._extract_port_from_output(output, framework)
                        if detected_port:
                            preview_url = f"http://localhost:{host_port}"
                            yield f"\n{'='*50}\n"
                            yield f"SERVER STARTED!\n"
                            yield f"Preview URL: {preview_url}\n"
                            yield f"{'='*50}\n\n"
                            yield f"__SERVER_STARTED__:{preview_url}\n"

                await process.wait()

                if process.returncode != 0:
                    yield f"Command exited with code: {process.returncode}\n"

            except Exception as e:
                yield f"ERROR: {str(e)}\n"

    async def stop_direct(self, project_id: str) -> bool:
        """Stop a directly running process"""
        if project_id in self._running_processes:
            process = self._running_processes[project_id]
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
            finally:
                del self._running_processes[project_id]
                if project_id in self._assigned_ports:
                    del self._assigned_ports[project_id]
            return True
        return False

    # ============= SMART RUN (DOCKER WITH FALLBACK) =============

    async def run_project(
        self,
        project_id: str,
        project_path: Path
    ) -> AsyncGenerator[str, None]:
        """
        Smart run: Try Docker first, fall back to direct execution if Docker fails.

        Flow:
        1. Check if Docker is available
        2. If yes: Run in Docker container
        3. If no: Fall back to direct execution
        4. Stream output and detect server start
        5. Return preview URL
        """
        # Ensure Dockerfile exists
        framework, dockerfile_created = await self.ensure_dockerfile(project_path)

        if dockerfile_created:
            yield f"Auto-generated Dockerfile for {framework.value} project\n"
        else:
            yield f"Using existing Dockerfile (detected: {framework.value})\n"

        # Check Docker availability
        docker_available = await self._check_docker_available()

        if docker_available:
            yield "Docker available - running in container...\n"
            try:
                async for output in self.run_container(project_id, project_path, framework):
                    yield output
            except Exception as e:
                yield f"Docker execution failed: {str(e)}\n"
                yield "Falling back to direct execution...\n"
                async for output in self.run_direct(project_id, project_path, framework):
                    yield output
        else:
            yield "Docker not available - running directly on host...\n"
            async for output in self.run_direct(project_id, project_path, framework):
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
    ERROR_PATTERNS = [
        # Build errors
        r'error:?\s+(.+)',
        r'ERROR:?\s+(.+)',
        r'failed to build',
        r'cannot find module',
        r'Module not found',
        r'SyntaxError:?\s+(.+)',
        r'TypeError:?\s+(.+)',
        r'ReferenceError:?\s+(.+)',
        r'ImportError:?\s+(.+)',
        r'ModuleNotFoundError:?\s+(.+)',
        r'NameError:?\s+(.+)',
        r'AttributeError:?\s+(.+)',
        r'KeyError:?\s+(.+)',
        r'npm ERR!',
        r'pip install.*failed',
        r'command.*not found',
        r'permission denied',
        r'ENOENT',
        r'EACCES',
        r'Cannot find',
        r'Unexpected token',
        r'Uncaught',
        r'exited with code [1-9]',
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

    def _extract_error_info(self, output_lines: List[str]) -> Dict[str, Any]:
        """Extract error information from output"""
        errors = []
        error_context = []

        for i, line in enumerate(output_lines):
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
                "error_count": len(errors),
                "errors": errors,
                "full_output": "\n".join(output_lines[-100:])  # Last 100 lines
            }

        return {"has_errors": False}

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
                                port = int(match.group(1)) if match else 3000
                                preview_url = f"http://localhost:{port}"
                                yield f"\n{'='*50}\n"
                                yield f"SERVER STARTED!\n"
                                yield f"Preview URL: {preview_url}\n"
                                yield f"{'='*50}\n"
                                yield f"__SERVER_STARTED__:{preview_url}\n"
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

                yield f"\n{'='*50}\n"
                yield f"ERRORS DETECTED - Attempting auto-fix...\n"
                yield f"{'='*50}\n\n"

                # Stop current compose
                await self.stop_compose(project_id, project_path)

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
