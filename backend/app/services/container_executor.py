"""
Container Executor Service - Dynamic Container Spawning for Project Execution

Production Architecture:
- Each user's project runs in an isolated Docker container
- Containers are spawned on-demand based on project technology
- Auto-cleanup after execution or timeout
- Resource limits prevent abuse

Supported Technologies:
- Node.js (React, Vue, Next.js, Angular)
- Java (Spring Boot, Maven, Gradle)
- Python (FastAPI, Django, Flask, Streamlit)
- Go (Golang projects)
"""

import asyncio
import docker
from docker.errors import NotFound, APIError
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
import os
from datetime import datetime, timedelta

from app.core.logging_config import logger

# Sandbox public URL for preview (use sandbox EC2 public IP/domain in production)
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL") or os.getenv("SANDBOX_PREVIEW_BASE_URL", "http://localhost")


def _get_preview_url(port: int) -> str:
    """Generate preview URL using sandbox public URL or localhost fallback"""
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        return f"{base}:{port}"
    return f"http://localhost:{port}"


class Technology(Enum):
    """Supported technology stacks"""
    NODEJS = "nodejs"
    JAVA = "java"
    PYTHON = "python"
    GO = "go"
    UNKNOWN = "unknown"


@dataclass
class ContainerConfig:
    """Configuration for a technology container"""
    image: str
    run_command: str
    build_command: Optional[str] = None
    port: int = 3000
    memory_limit: str = "512m"
    cpu_limit: float = 0.5
    timeout_seconds: int = 300  # 5 minutes max


# Pre-built images for each technology
TECHNOLOGY_CONFIGS: Dict[Technology, ContainerConfig] = {
    Technology.NODEJS: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install",
        run_command="npm run dev",
        port=3000,
        memory_limit="512m"
    ),
    Technology.JAVA: ContainerConfig(
        image="maven:3.9-eclipse-temurin-17",
        build_command="mvn clean install -DskipTests",
        run_command="mvn spring-boot:run",
        port=8080,
        memory_limit="1g",
        cpu_limit=1.0
    ),
    Technology.PYTHON: ContainerConfig(
        image="python:3.11-slim",
        build_command="pip install -r requirements.txt",
        run_command="python -m uvicorn main:app --host 0.0.0.0 --port 8000",
        port=8000,
        memory_limit="512m"
    ),
    Technology.GO: ContainerConfig(
        image="golang:1.21-alpine",
        build_command="go mod download && go build -o main .",
        run_command="./main",
        port=8080,
        memory_limit="256m"
    ),
}


class ContainerExecutor:
    """
    Manages Docker containers for project execution.

    Each project runs in an isolated container with:
    - Technology-specific base image
    - Resource limits (CPU, memory)
    - Automatic cleanup after timeout
    - Volume mounting for project files
    """

    def __init__(self):
        self.docker_client: Optional[docker.DockerClient] = None
        self.active_containers: Dict[str, Dict[str, Any]] = {}  # project_id -> container info
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize Docker client"""
        try:
            # First, try SANDBOX_DOCKER_HOST env var (for ECS -> EC2 sandbox connection)
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST") or os.environ.get("DOCKER_HOST")
            if sandbox_docker_host:
                try:
                    self.docker_client = docker.DockerClient(base_url=sandbox_docker_host)
                    self.docker_client.ping()
                    logger.info(f"[ContainerExecutor] Docker client initialized via SANDBOX_DOCKER_HOST: {sandbox_docker_host}")
                except Exception as remote_err:
                    logger.warning(f"[ContainerExecutor] Remote Docker {sandbox_docker_host} failed: {remote_err}")
                    self.docker_client = None

            # Try Unix socket first (Linux/Docker Desktop), then Windows named pipe
            if not self.docker_client:
                socket_paths = [
                    "unix:///var/run/docker.sock",  # Linux / Docker in container
                    "unix://var/run/docker.sock",   # Alternative format
                    "npipe:////./pipe/docker_engine",  # Windows
                ]

                for socket_path in socket_paths:
                    try:
                        self.docker_client = docker.DockerClient(base_url=socket_path)
                        self.docker_client.ping()
                        logger.info(f"[ContainerExecutor] Docker client initialized via {socket_path}")
                        break
                    except Exception as socket_err:
                        logger.debug(f"[ContainerExecutor] Socket {socket_path} failed: {socket_err}")
                        continue

            # Fallback to from_env if explicit paths fail
            if not self.docker_client:
                self.docker_client = docker.from_env()
                self.docker_client.ping()
                logger.info("[ContainerExecutor] Docker client initialized via from_env()")

            # Start cleanup background task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            # Pull base images in background
            asyncio.create_task(self._pull_base_images())

            return True
        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to initialize Docker client: {e}")
            return False

    async def _pull_base_images(self):
        """Pre-pull base images for faster container startup"""
        for tech, config in TECHNOLOGY_CONFIGS.items():
            try:
                logger.info(f"[ContainerExecutor] Pulling image: {config.image}")
                self.docker_client.images.pull(config.image)
                logger.info(f"[ContainerExecutor] Image ready: {config.image}")
            except Exception as e:
                logger.warning(f"[ContainerExecutor] Failed to pull {config.image}: {e}")

    def detect_technology(self, project_path: str) -> Technology:
        """
        Detect project technology based on files present.

        Detection priority:
        1. package.json -> Node.js
        2. pom.xml or build.gradle -> Java
        3. requirements.txt or pyproject.toml -> Python
        4. go.mod -> Go
        """
        files = os.listdir(project_path) if os.path.exists(project_path) else []

        # Node.js detection
        if "package.json" in files:
            return Technology.NODEJS

        # Java detection
        if "pom.xml" in files or "build.gradle" in files or "build.gradle.kts" in files:
            return Technology.JAVA

        # Python detection
        if "requirements.txt" in files or "pyproject.toml" in files or "setup.py" in files:
            return Technology.PYTHON

        # Go detection
        if "go.mod" in files:
            return Technology.GO

        # Check file extensions as fallback
        for f in files:
            if f.endswith(('.tsx', '.jsx', '.ts', '.js')):
                return Technology.NODEJS
            if f.endswith('.java'):
                return Technology.JAVA
            if f.endswith('.py'):
                return Technology.PYTHON
            if f.endswith('.go'):
                return Technology.GO

        return Technology.UNKNOWN

    async def create_container(
        self,
        project_id: str,
        user_id: str,
        project_path: str,
        technology: Optional[Technology] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Create and start a container for project execution.

        Args:
            project_id: Unique project identifier
            user_id: User who owns the project
            project_path: Path to project files on host
            technology: Technology stack (auto-detected if not provided)

        Returns:
            Tuple of (success, message, port)
        """
        if not self.docker_client:
            return False, "Docker client not initialized", None

        # Auto-detect technology if not provided
        if technology is None:
            technology = self.detect_technology(project_path)

        if technology == Technology.UNKNOWN:
            return False, "Could not detect project technology", None

        config = TECHNOLOGY_CONFIGS.get(technology)
        if not config:
            return False, f"Unsupported technology: {technology.value}", None

        # Generate unique container name
        container_name = f"bharatbuild_{user_id[:8]}_{project_id[:8]}_{uuid.uuid4().hex[:6]}"

        # Find available port
        host_port = self._find_available_port()

        try:
            logger.info(f"[ContainerExecutor] Creating container for {project_id} ({technology.value})")

            # Create container
            container = self.docker_client.containers.run(
                image=config.image,
                name=container_name,
                detach=True,
                working_dir="/app",
                volumes={
                    project_path: {"bind": "/app", "mode": "rw"}
                },
                ports={f"{config.port}/tcp": host_port},
                mem_limit=config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(config.cpu_limit * 100000),
                environment={
                    "NODE_ENV": "development",
                    "JAVA_OPTS": "-Xmx512m",
                    "PYTHONUNBUFFERED": "1"
                },
                command=f"sh -c '{config.build_command} && {config.run_command}'" if config.build_command else config.run_command,
                labels={
                    "bharatbuild": "true",
                    "project_id": project_id,
                    "user_id": user_id,
                    "technology": technology.value
                }
            )

            # Track container
            self.active_containers[project_id] = {
                "container_id": container.id,
                "container_name": container_name,
                "user_id": user_id,
                "technology": technology.value,
                "port": host_port,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(seconds=config.timeout_seconds)
            }

            logger.info(f"[ContainerExecutor] Container {container_name} started on port {host_port}")

            return True, f"Container started successfully", host_port

        except APIError as e:
            logger.error(f"[ContainerExecutor] Docker API error: {e}")
            return False, f"Failed to create container: {str(e)}", None
        except Exception as e:
            logger.error(f"[ContainerExecutor] Error creating container: {e}")
            return False, f"Error: {str(e)}", None

    async def stop_container(self, project_id: str) -> Tuple[bool, str]:
        """Stop and remove a project's container"""
        if project_id not in self.active_containers:
            return False, "Container not found"

        container_info = self.active_containers[project_id]

        try:
            container = self.docker_client.containers.get(container_info["container_id"])
            container.stop(timeout=10)
            container.remove()

            del self.active_containers[project_id]

            logger.info(f"[ContainerExecutor] Container stopped for project {project_id}")
            return True, "Container stopped successfully"

        except NotFound:
            del self.active_containers[project_id]
            return True, "Container already removed"
        except Exception as e:
            logger.error(f"[ContainerExecutor] Error stopping container: {e}")
            return False, f"Error: {str(e)}"

    async def get_container_logs(self, project_id: str, tail: int = 100) -> Optional[str]:
        """Get logs from a project's container"""
        if project_id not in self.active_containers:
            return None

        container_info = self.active_containers[project_id]

        try:
            container = self.docker_client.containers.get(container_info["container_id"])
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs
        except Exception as e:
            logger.error(f"[ContainerExecutor] Error getting logs: {e}")
            return None

    async def get_container_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a project's container"""
        if project_id not in self.active_containers:
            return None

        container_info = self.active_containers[project_id]

        try:
            container = self.docker_client.containers.get(container_info["container_id"])
            return {
                "status": container.status,
                "port": container_info["port"],
                "technology": container_info["technology"],
                "created_at": container_info["created_at"].isoformat(),
                "expires_at": container_info["expires_at"].isoformat(),
                "url": _get_preview_url(container_info['port'])
            }
        except NotFound:
            del self.active_containers[project_id]
            return None
        except Exception as e:
            logger.error(f"[ContainerExecutor] Error getting status: {e}")
            return None

    async def execute_command(
        self,
        project_id: str,
        command: str,
        timeout: int = 60
    ) -> Tuple[bool, str]:
        """Execute a command in a project's container"""
        if project_id not in self.active_containers:
            return False, "Container not found"

        container_info = self.active_containers[project_id]

        try:
            container = self.docker_client.containers.get(container_info["container_id"])
            exit_code, output = container.exec_run(
                command,
                workdir="/app",
                demux=True
            )

            stdout = output[0].decode('utf-8') if output[0] else ""
            stderr = output[1].decode('utf-8') if output[1] else ""

            return exit_code == 0, stdout + stderr

        except Exception as e:
            logger.error(f"[ContainerExecutor] Error executing command: {e}")
            return False, f"Error: {str(e)}"

    def _find_available_port(self, start: int = 10000, end: int = 20000) -> int:
        """Find an available port for container mapping"""
        import socket

        used_ports = {info["port"] for info in self.active_containers.values()}

        for port in range(start, end):
            if port in used_ports:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                    return port
                except OSError:
                    continue

        raise RuntimeError("No available ports")

    async def _cleanup_loop(self):
        """Background task to cleanup expired containers"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                now = datetime.utcnow()
                expired = [
                    project_id for project_id, info in self.active_containers.items()
                    if info["expires_at"] < now
                ]

                for project_id in expired:
                    logger.info(f"[ContainerExecutor] Auto-cleanup expired container: {project_id}")
                    await self.stop_container(project_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ContainerExecutor] Cleanup error: {e}")

    async def cleanup_all(self):
        """Stop all containers (for shutdown)"""
        for project_id in list(self.active_containers.keys()):
            await self.stop_container(project_id)

        if self._cleanup_task:
            self._cleanup_task.cancel()


# Global instance
container_executor = ContainerExecutor()
