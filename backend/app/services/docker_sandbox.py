"""
Docker Sandbox Manager - Kubernetes-based Container Runtime for Layer 1

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DOCKER SANDBOX CLUSTER ON KUBERNETES                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Request → Create Pod → Mount Files → Run Command → Expose Port       │
│                                                                             │
│  Features:                                                                  │
│  • Auto-scaling with Kubernetes                                            │
│  • Isolated containers per student                                         │
│  • Multi-language support (Node, Python, Java, Go, Rust)                   │
│  • Fast startup (~2-5 seconds)                                             │
│  • Auto-cleanup on idle/timeout                                            │
│  • Preview URL with port forwarding                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
"""

import os
import asyncio
import json
import uuid
import platform
import re
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

import docker
from docker.errors import NotFound, APIError

from app.core.logging_config import logger


def _to_docker_path(path_str: str) -> str:
    """
    Convert a filesystem path to Docker-compatible format.

    On Windows with Docker Desktop (Linux containers), paths need to be converted:
    - C:\\tmp\\sandbox\\workspace -> /c/tmp/sandbox/workspace
    - C:/tmp/sandbox/workspace -> /c/tmp/sandbox/workspace

    On Linux/Mac, paths are passed through unchanged.
    """
    # Only convert on Windows
    if platform.system() == "Windows":
        # Match drive letter pattern (e.g., C:\ or C:/)
        match = re.match(r'^([A-Za-z]):[/\\](.*)$', path_str)
        if match:
            drive = match.group(1).lower()
            rest = match.group(2).replace('\\', '/')
            docker_path = f"/{drive}/{rest}"
            logger.debug(f"Converted Windows path '{path_str}' to Docker path '{docker_path}'")
            return docker_path

    # Non-Windows or no drive letter - return as-is with forward slashes
    return path_str.replace('\\', '/')


# Configuration
SANDBOX_NETWORK = os.getenv("SANDBOX_NETWORK", "bharatbuild-sandbox")
SANDBOX_TIMEOUT_MINUTES = int(os.getenv("SANDBOX_TIMEOUT_MINUTES", "30"))
SANDBOX_MEMORY_LIMIT = os.getenv("SANDBOX_MEMORY_LIMIT", "512m")
SANDBOX_CPU_LIMIT = float(os.getenv("SANDBOX_CPU_LIMIT", "0.5"))
SANDBOX_BASE_PORT = int(os.getenv("SANDBOX_BASE_PORT", "10000"))
MAX_CONCURRENT_SANDBOXES = int(os.getenv("MAX_CONCURRENT_SANDBOXES", "100"))

# Remote Docker Host (EC2 Sandbox Server)
# When running on ECS Fargate, connect to remote EC2 instance running Docker
SANDBOX_DOCKER_HOST = os.getenv("SANDBOX_DOCKER_HOST", "")  # e.g., "tcp://10.0.10.x:2375"
SANDBOX_PREVIEW_BASE_URL = os.getenv("SANDBOX_PREVIEW_BASE_URL", "http://localhost")  # e.g., "https://bharatbuild.com/sandbox"
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL", "http://localhost")  # e.g., "http://13.202.228.249" (direct port access)


def _get_preview_url(port: int) -> str:
    """Generate preview URL using sandbox public URL or localhost fallback"""
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        return f"{base}:{port}"
    return f"http://localhost:{port}"


class SandboxStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    EXPIRED = "expired"


class ProjectType(str, Enum):
    # Frontend
    NODEJS = "nodejs"
    REACT = "react"
    NEXTJS = "nextjs"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"

    # Backend
    PYTHON = "python"
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    JAVA = "java"
    SPRINGBOOT = "springboot"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    RAILS = "rails"
    PHP = "php"
    LARAVEL = "laravel"
    DOTNET = "dotnet"
    CSHARP = "csharp"

    # Data Science / ML
    JUPYTER = "jupyter"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    DATASCIENCE = "datascience"

    # Mobile
    FLUTTER = "flutter"
    REACTNATIVE = "reactnative"

    # Other
    STATIC = "static"
    CUSTOM = "custom"


# Base images for different project types
BASE_IMAGES = {
    # Frontend
    ProjectType.NODEJS: "node:20-alpine",
    ProjectType.REACT: "node:20-alpine",
    ProjectType.NEXTJS: "node:20-alpine",
    ProjectType.VUE: "node:20-alpine",
    ProjectType.ANGULAR: "node:20-alpine",
    ProjectType.SVELTE: "node:20-alpine",

    # Python ecosystem
    ProjectType.PYTHON: "python:3.11-slim",
    ProjectType.FASTAPI: "python:3.11-slim",
    ProjectType.DJANGO: "python:3.11-slim",
    ProjectType.FLASK: "python:3.11-slim",

    # Java ecosystem
    ProjectType.JAVA: "eclipse-temurin:17-jdk-alpine",
    ProjectType.SPRINGBOOT: "eclipse-temurin:17-jdk-alpine",

    # Other languages
    ProjectType.GO: "golang:1.21-alpine",
    ProjectType.RUST: "rust:1.74-slim",
    ProjectType.RUBY: "ruby:3.2-slim",
    ProjectType.RAILS: "ruby:3.2-slim",
    ProjectType.PHP: "php:8.2-apache",
    ProjectType.LARAVEL: "php:8.2-apache",
    ProjectType.DOTNET: "mcr.microsoft.com/dotnet/sdk:8.0",
    ProjectType.CSHARP: "mcr.microsoft.com/dotnet/sdk:8.0",

    # Data Science / ML
    ProjectType.JUPYTER: "jupyter/scipy-notebook:latest",
    ProjectType.TENSORFLOW: "tensorflow/tensorflow:latest-jupyter",
    ProjectType.PYTORCH: "pytorch/pytorch:latest",
    ProjectType.DATASCIENCE: "jupyter/datascience-notebook:latest",

    # Mobile
    ProjectType.FLUTTER: "cirrusci/flutter:latest",
    ProjectType.REACTNATIVE: "node:20-alpine",

    # Static
    ProjectType.STATIC: "nginx:alpine",
    ProjectType.CUSTOM: "ubuntu:22.04",
}

# Default commands for different project types
DEFAULT_COMMANDS = {
    # Frontend
    ProjectType.NODEJS: ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"],
    ProjectType.REACT: ["sh", "-c", "npm install && npm start"],
    ProjectType.NEXTJS: ["sh", "-c", "npm install && npm run dev"],
    ProjectType.VUE: ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"],
    ProjectType.ANGULAR: ["sh", "-c", "npm install && ng serve --host 0.0.0.0"],
    ProjectType.SVELTE: ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"],

    # Python
    ProjectType.PYTHON: ["sh", "-c", "pip install -r requirements.txt 2>/dev/null; python main.py"],
    ProjectType.FASTAPI: ["sh", "-c", "pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"],
    ProjectType.DJANGO: ["sh", "-c", "pip install -r requirements.txt && python manage.py runserver 0.0.0.0:8000"],
    ProjectType.FLASK: ["sh", "-c", "pip install -r requirements.txt && flask run --host 0.0.0.0"],

    # Java
    ProjectType.JAVA: ["sh", "-c", "javac Main.java && java Main"],
    ProjectType.SPRINGBOOT: ["sh", "-c", "./mvnw spring-boot:run"],

    # Other languages
    ProjectType.GO: ["sh", "-c", "go mod tidy 2>/dev/null; go run ."],
    ProjectType.RUST: ["sh", "-c", "cargo run"],
    ProjectType.RUBY: ["sh", "-c", "bundle install && ruby main.rb"],
    ProjectType.RAILS: ["sh", "-c", "bundle install && rails server -b 0.0.0.0"],
    ProjectType.PHP: ["sh", "-c", "php -S 0.0.0.0:8080"],
    ProjectType.LARAVEL: ["sh", "-c", "composer install && php artisan serve --host 0.0.0.0"],
    ProjectType.DOTNET: ["sh", "-c", "dotnet run --urls http://0.0.0.0:5000"],
    ProjectType.CSHARP: ["sh", "-c", "dotnet run"],

    # Data Science / ML
    ProjectType.JUPYTER: ["jupyter", "notebook", "--ip=0.0.0.0", "--allow-root", "--no-browser"],
    ProjectType.TENSORFLOW: ["jupyter", "notebook", "--ip=0.0.0.0", "--allow-root", "--no-browser"],
    ProjectType.PYTORCH: ["jupyter", "notebook", "--ip=0.0.0.0", "--allow-root", "--no-browser"],
    ProjectType.DATASCIENCE: ["jupyter", "notebook", "--ip=0.0.0.0", "--allow-root", "--no-browser"],

    # Mobile
    ProjectType.FLUTTER: ["sh", "-c", "flutter pub get && flutter run -d web-server --web-port 3000"],
    ProjectType.REACTNATIVE: ["sh", "-c", "npm install && npx expo start --web"],

    # Static
    ProjectType.STATIC: ["nginx", "-g", "daemon off;"],
    ProjectType.CUSTOM: ["sh", "-c", "echo 'Custom container ready' && sleep infinity"],
}

# Default ports for different project types
DEFAULT_PORTS = {
    # Frontend
    ProjectType.NODEJS: 3000,
    ProjectType.REACT: 3000,
    ProjectType.NEXTJS: 3000,
    ProjectType.VUE: 5173,
    ProjectType.ANGULAR: 4200,
    ProjectType.SVELTE: 5173,

    # Python
    ProjectType.PYTHON: 8000,
    ProjectType.FASTAPI: 8000,
    ProjectType.DJANGO: 8000,
    ProjectType.FLASK: 5000,

    # Java
    ProjectType.JAVA: 8080,
    ProjectType.SPRINGBOOT: 8080,

    # Other languages
    ProjectType.GO: 8080,
    ProjectType.RUST: 8080,
    ProjectType.RUBY: 3000,
    ProjectType.RAILS: 3000,
    ProjectType.PHP: 8080,
    ProjectType.LARAVEL: 8000,
    ProjectType.DOTNET: 5000,
    ProjectType.CSHARP: 5000,

    # Data Science / ML
    ProjectType.JUPYTER: 8888,
    ProjectType.TENSORFLOW: 8888,
    ProjectType.PYTORCH: 8888,
    ProjectType.DATASCIENCE: 8888,

    # Mobile
    ProjectType.FLUTTER: 3000,
    ProjectType.REACTNATIVE: 19006,

    # Static
    ProjectType.STATIC: 80,
    ProjectType.CUSTOM: 8080,
}


# Technology detection from files
def detect_project_type(files: list) -> ProjectType:
    """Auto-detect project type from files"""
    file_names = [f.lower() if isinstance(f, str) else f.get('name', '').lower() for f in files]
    file_paths = [f.lower() if isinstance(f, str) else f.get('path', '').lower() for f in files]
    all_files = file_names + file_paths

    # Check for specific frameworks
    if 'next.config.js' in all_files or 'next.config.ts' in all_files:
        return ProjectType.NEXTJS
    if 'angular.json' in all_files:
        return ProjectType.ANGULAR
    if 'svelte.config.js' in all_files:
        return ProjectType.SVELTE
    if 'vue.config.js' in all_files or 'vite.config.ts' in all_files:
        return ProjectType.VUE
    if 'manage.py' in all_files:
        return ProjectType.DJANGO
    if 'artisan' in all_files:
        return ProjectType.LARAVEL
    if 'Gemfile' in all_files:
        if 'config.ru' in all_files or any('rails' in f for f in all_files):
            return ProjectType.RAILS
        return ProjectType.RUBY
    if 'pom.xml' in all_files or 'build.gradle' in all_files:
        return ProjectType.SPRINGBOOT
    if 'go.mod' in all_files:
        return ProjectType.GO
    if 'Cargo.toml' in all_files:
        return ProjectType.RUST
    if 'pubspec.yaml' in all_files:
        return ProjectType.FLUTTER
    if any('.ipynb' in f for f in all_files):
        return ProjectType.JUPYTER
    if any('.csproj' in f for f in all_files) or any('.sln' in f for f in all_files):
        return ProjectType.DOTNET
    if 'composer.json' in all_files:
        return ProjectType.PHP
    if 'requirements.txt' in all_files:
        return ProjectType.PYTHON
    if 'package.json' in all_files:
        return ProjectType.NODEJS
    if 'index.html' in all_files:
        return ProjectType.STATIC

    return ProjectType.CUSTOM


@dataclass
class SandboxInfo:
    """Information about a running sandbox"""
    sandbox_id: str
    project_id: str
    user_id: str
    container_id: Optional[str] = None
    status: SandboxStatus = SandboxStatus.CREATING
    project_type: ProjectType = ProjectType.NODEJS
    internal_port: int = 3000
    external_port: Optional[int] = None
    preview_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "container_id": self.container_id,
            "status": self.status.value,
            "project_type": self.project_type.value,
            "internal_port": self.internal_port,
            "external_port": self.external_port,
            "preview_url": self.preview_url,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "error_message": self.error_message,
        }


class DockerSandboxManager:
    """
    Manages Docker containers for code execution and preview.

    This is Layer 1 of the 3-Layer Storage Architecture.
    Containers are ephemeral - destroyed on idle/close.
    """

    def __init__(self):
        self._client: Optional[docker.DockerClient] = None
        self._sandboxes: Dict[str, SandboxInfo] = {}
        self._port_allocator = PortAllocator(SANDBOX_BASE_PORT, SANDBOX_BASE_PORT + 1000)
        self._initialized = False

    def _get_client(self) -> docker.DockerClient:
        """Lazy initialization of Docker client"""
        if self._client is None:
            try:
                # Check if we should connect to remote Docker host (EC2 sandbox server)
                if SANDBOX_DOCKER_HOST:
                    logger.info(f"Connecting to remote Docker host: {SANDBOX_DOCKER_HOST}")
                    self._client = docker.DockerClient(base_url=SANDBOX_DOCKER_HOST)
                else:
                    # Local Docker - try multiple connection methods
                    import platform
                    system = platform.system()

                    # Try explicit paths first to avoid DOCKER_HOST env issues
                    docker_urls = []
                    if system == "Windows":
                        docker_urls = [
                            "npipe:////./pipe/docker_engine",
                            "tcp://localhost:2375",
                        ]
                    else:
                        docker_urls = [
                            "unix:///var/run/docker.sock",
                            "unix://var/run/docker.sock",
                            "tcp://localhost:2375",
                        ]

                    for url in docker_urls:
                        try:
                            logger.debug(f"Trying Docker URL: {url}")
                            self._client = docker.DockerClient(base_url=url)
                            self._client.ping()
                            logger.info(f"Connected to Docker via: {url}")
                            break
                        except Exception as url_err:
                            logger.debug(f"Docker URL {url} failed: {url_err}")
                            self._client = None
                            continue

                    # Fallback to from_env() if explicit URLs failed
                    if self._client is None:
                        logger.debug("Trying docker.from_env() as fallback")
                        docker_host = os.getenv("DOCKER_HOST", "")
                        logger.debug(f"DOCKER_HOST env: {docker_host}")
                        self._client = docker.from_env()

                self._ensure_network()
                self._initialized = True
                logger.info("Docker client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Docker client: {e}")
                # Provide more helpful error message
                docker_host = os.getenv("DOCKER_HOST", "not set")
                sandbox_host = SANDBOX_DOCKER_HOST or "not set"
                raise RuntimeError(f"Docker not available: {e}. DOCKER_HOST={docker_host}, SANDBOX_DOCKER_HOST={sandbox_host}")
        return self._client

    def _ensure_network(self):
        """Create sandbox network if it doesn't exist"""
        try:
            self._client.networks.get(SANDBOX_NETWORK)
        except NotFound:
            self._client.networks.create(
                SANDBOX_NETWORK,
                driver="bridge",
                internal=False
            )
            logger.info(f"Created sandbox network: {SANDBOX_NETWORK}")

    async def create_sandbox(
        self,
        project_id: str,
        user_id: str,
        project_type: ProjectType = ProjectType.NODEJS,
        files_path: Optional[str] = None,
        custom_command: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> SandboxInfo:
        """
        Create a new sandbox container for a project.

        Args:
            project_id: Unique project identifier
            user_id: User who owns the sandbox
            project_type: Type of project (nodejs, python, etc.)
            files_path: Path to project files (mounted into container)
            custom_command: Custom command to run (overrides default)
            environment: Environment variables

        Returns:
            SandboxInfo with container details
        """
        sandbox_id = f"sandbox-{project_id[:8]}-{uuid.uuid4().hex[:8]}"

        # Check concurrent sandbox limit
        active_count = sum(1 for s in self._sandboxes.values()
                         if s.status == SandboxStatus.RUNNING)
        if active_count >= MAX_CONCURRENT_SANDBOXES:
            raise RuntimeError(f"Maximum concurrent sandboxes ({MAX_CONCURRENT_SANDBOXES}) reached")

        # Allocate port
        external_port = self._port_allocator.allocate()
        if not external_port:
            raise RuntimeError("No available ports for sandbox")

        internal_port = DEFAULT_PORTS.get(project_type, 3000)

        sandbox = SandboxInfo(
            sandbox_id=sandbox_id,
            project_id=project_id,
            user_id=user_id,
            project_type=project_type,
            internal_port=internal_port,
            external_port=external_port,
            status=SandboxStatus.CREATING
        )
        self._sandboxes[sandbox_id] = sandbox

        try:
            client = self._get_client()

            # Prepare container config
            image = BASE_IMAGES.get(project_type, BASE_IMAGES[ProjectType.NODEJS])
            command = custom_command or DEFAULT_COMMANDS.get(project_type)

            # Volume mounts (convert Windows paths for Docker)
            volumes = {}
            if files_path:
                docker_path = _to_docker_path(files_path)
                volumes[docker_path] = {"bind": "/app", "mode": "rw"}

            # Environment
            env = {
                "NODE_ENV": "development",
                "PORT": str(internal_port),
                "HOST": "0.0.0.0",
                **(environment or {})
            }

            # Create container
            container = client.containers.run(
                image=image,
                command=command,
                name=sandbox_id,
                detach=True,
                remove=False,
                working_dir="/app",
                volumes=volumes,
                environment=env,
                ports={f"{internal_port}/tcp": external_port},
                network=SANDBOX_NETWORK,
                mem_limit=SANDBOX_MEMORY_LIMIT,
                cpu_quota=int(SANDBOX_CPU_LIMIT * 100000),
                labels={
                    "bharatbuild.sandbox": "true",
                    "bharatbuild.project_id": project_id,
                    "bharatbuild.user_id": user_id,
                    "bharatbuild.created_at": datetime.utcnow().isoformat()
                }
            )

            sandbox.container_id = container.id
            sandbox.status = SandboxStatus.RUNNING
            # Use configured preview URL base (for production with ALB routing)
            if SANDBOX_PREVIEW_BASE_URL and SANDBOX_PREVIEW_BASE_URL != "http://localhost":
                sandbox.preview_url = f"{SANDBOX_PREVIEW_BASE_URL}/{sandbox_id}"
            else:
                # Use direct port access via SANDBOX_PUBLIC_URL
                sandbox.preview_url = _get_preview_url(external_port)

            logger.info(f"Created sandbox {sandbox_id} for project {project_id}")
            return sandbox

        except Exception as e:
            sandbox.status = SandboxStatus.FAILED
            sandbox.error_message = str(e)
            self._port_allocator.release(external_port)
            logger.error(f"Failed to create sandbox: {e}")
            raise

    async def get_sandbox(self, sandbox_id: str) -> Optional[SandboxInfo]:
        """Get sandbox information"""
        return self._sandboxes.get(sandbox_id)

    async def get_sandbox_by_project(self, project_id: str) -> Optional[SandboxInfo]:
        """Get sandbox by project ID"""
        for sandbox in self._sandboxes.values():
            if sandbox.project_id == project_id and sandbox.status == SandboxStatus.RUNNING:
                return sandbox
        return None

    async def stop_sandbox(self, sandbox_id: str) -> bool:
        """Stop and remove a sandbox container"""
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox:
            return False

        try:
            client = self._get_client()
            container = client.containers.get(sandbox.container_id)
            container.stop(timeout=5)
            container.remove()

            sandbox.status = SandboxStatus.STOPPED
            if sandbox.external_port:
                self._port_allocator.release(sandbox.external_port)

            logger.info(f"Stopped sandbox {sandbox_id}")
            return True

        except NotFound:
            sandbox.status = SandboxStatus.STOPPED
            return True
        except Exception as e:
            logger.error(f"Failed to stop sandbox {sandbox_id}: {e}")
            return False

    async def get_logs(self, sandbox_id: str, tail: int = 100) -> List[str]:
        """Get container logs"""
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox or not sandbox.container_id:
            return []

        try:
            client = self._get_client()
            container = client.containers.get(sandbox.container_id)
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs.split('\n')
        except Exception as e:
            logger.error(f"Failed to get logs for {sandbox_id}: {e}")
            return [f"Error: {e}"]

    async def execute_command(
        self,
        sandbox_id: str,
        command: List[str],
        workdir: str = "/app"
    ) -> Dict[str, Any]:
        """Execute a command in the sandbox container"""
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox or sandbox.status != SandboxStatus.RUNNING:
            return {"success": False, "error": "Sandbox not running"}

        try:
            client = self._get_client()
            container = client.containers.get(sandbox.container_id)

            result = container.exec_run(
                command,
                workdir=workdir,
                demux=True
            )

            stdout = result.output[0].decode('utf-8') if result.output[0] else ""
            stderr = result.output[1].decode('utf-8') if result.output[1] else ""

            sandbox.last_activity = datetime.utcnow()

            return {
                "success": result.exit_code == 0,
                "exit_code": result.exit_code,
                "stdout": stdout,
                "stderr": stderr
            }

        except Exception as e:
            logger.error(f"Failed to execute command in {sandbox_id}: {e}")
            return {"success": False, "error": str(e)}

    async def write_file(
        self,
        sandbox_id: str,
        file_path: str,
        content: str
    ) -> bool:
        """Write a file to the sandbox container"""
        result = await self.execute_command(
            sandbox_id,
            ["sh", "-c", f"mkdir -p $(dirname {file_path}) && cat > {file_path}"],
        )

        if not result.get("success"):
            # Use alternative method
            sandbox = self._sandboxes.get(sandbox_id)
            if sandbox and sandbox.container_id:
                try:
                    client = self._get_client()
                    container = client.containers.get(sandbox.container_id)

                    import tarfile
                    import io

                    # Create tar archive with file
                    tar_stream = io.BytesIO()
                    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                        data = content.encode('utf-8')
                        tarinfo = tarfile.TarInfo(name=file_path.lstrip('/'))
                        tarinfo.size = len(data)
                        tar.addfile(tarinfo, io.BytesIO(data))

                    tar_stream.seek(0)
                    container.put_archive('/app', tar_stream)
                    return True
                except Exception as e:
                    logger.error(f"Failed to write file to container: {e}")
                    return False

        return result.get("success", False)

    async def cleanup_expired(self) -> int:
        """Clean up expired/idle sandboxes"""
        cleaned = 0
        expiry_time = datetime.utcnow() - timedelta(minutes=SANDBOX_TIMEOUT_MINUTES)

        for sandbox_id, sandbox in list(self._sandboxes.items()):
            if sandbox.last_activity < expiry_time:
                if await self.stop_sandbox(sandbox_id):
                    del self._sandboxes[sandbox_id]
                    cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired sandboxes")

        return cleaned

    async def list_sandboxes(self, user_id: Optional[str] = None) -> List[SandboxInfo]:
        """List all sandboxes, optionally filtered by user"""
        sandboxes = list(self._sandboxes.values())
        if user_id:
            sandboxes = [s for s in sandboxes if s.user_id == user_id]
        return sandboxes

    async def get_stats(self) -> Dict[str, Any]:
        """Get sandbox cluster statistics"""
        running = sum(1 for s in self._sandboxes.values() if s.status == SandboxStatus.RUNNING)
        stopped = sum(1 for s in self._sandboxes.values() if s.status == SandboxStatus.STOPPED)
        failed = sum(1 for s in self._sandboxes.values() if s.status == SandboxStatus.FAILED)

        return {
            "total_sandboxes": len(self._sandboxes),
            "running": running,
            "stopped": stopped,
            "failed": failed,
            "max_concurrent": MAX_CONCURRENT_SANDBOXES,
            "available_ports": self._port_allocator.available_count(),
            "memory_limit": SANDBOX_MEMORY_LIMIT,
            "cpu_limit": SANDBOX_CPU_LIMIT,
            "timeout_minutes": SANDBOX_TIMEOUT_MINUTES
        }


class PortAllocator:
    """Manages port allocation for sandbox containers"""

    def __init__(self, start_port: int, end_port: int):
        self.start_port = start_port
        self.end_port = end_port
        self.allocated: set = set()

    def allocate(self) -> Optional[int]:
        """Allocate an available port"""
        for port in range(self.start_port, self.end_port):
            if port not in self.allocated:
                self.allocated.add(port)
                return port
        return None

    def release(self, port: int):
        """Release an allocated port"""
        self.allocated.discard(port)

    def available_count(self) -> int:
        """Count available ports"""
        return (self.end_port - self.start_port) - len(self.allocated)


# Singleton instance
docker_sandbox = DockerSandboxManager()


# Background cleanup task
async def sandbox_cleanup_loop():
    """Background task to clean up expired sandboxes"""
    while True:
        try:
            await docker_sandbox.cleanup_expired()
        except Exception as e:
            logger.error(f"Sandbox cleanup error: {e}")

        # Run every 5 minutes
        await asyncio.sleep(300)
