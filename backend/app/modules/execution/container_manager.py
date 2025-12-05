"""
Container Manager - Per-Project Docker Container Isolation

This is the CORE architecture that makes BharatBuild work like Bolt.new/Replit.
Each user project runs in its own isolated Docker container.

Architecture:
    Frontend (Browser)
         ↓
    Backend API (FastAPI)
         ↓
    Container Manager (this module)
         ↓
    Docker Engine
         ↓
    Isolated Container per Project
         ↓
    Stream output back via SSE

Why this matters:
- Security: Projects can't access each other's data
- Isolation: One project crash doesn't affect others
- Resources: Each project has CPU/memory limits
- Clean: Auto-cleanup after 24 hours (ephemeral)
"""

import asyncio
import docker
import logging
import os
import uuid
import json
import time
import socket
import random
import platform
import re
from typing import Optional, Dict, Any, AsyncGenerator, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from threading import Lock
from app.core.config import settings

logger = logging.getLogger(__name__)


def _to_docker_path(path: Path) -> str:
    """
    Convert a filesystem path to Docker-compatible format.

    On Windows with Docker Desktop (Linux containers), paths need to be converted:
    - C:\\tmp\\sandbox\\workspace -> /c/tmp/sandbox/workspace
    - C:/tmp/sandbox/workspace -> /c/tmp/sandbox/workspace

    On Linux/Mac, paths are passed through unchanged.

    Args:
        path: Path object to convert

    Returns:
        Docker-compatible path string
    """
    path_str = str(path.absolute())

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


class ContainerStatus(Enum):
    """Container lifecycle states"""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DELETED = "deleted"


class PortManager:
    """
    Manages dynamic port allocation for multi-user Docker containers.

    Features:
    - Checks if port is actually available (not just tracking)
    - Tracks ports per project to prevent conflicts
    - Releases ports when containers are deleted
    - Handles concurrent port allocation safely
    - Recovers from server restarts by scanning Docker
    """

    # Port range for container mappings (loaded from settings)
    PORT_RANGE_START = settings.CONTAINER_PORT_RANGE_START
    PORT_RANGE_END = 60000

    def __init__(self):
        self._allocated_ports: Dict[str, Set[int]] = {}  # project_id -> set of ports
        self._all_ports_in_use: Set[int] = set()
        self._lock = Lock()

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is actually available on the host"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.bind(('0.0.0.0', port))
                return True
        except (socket.error, OSError):
            return False

    def allocate_port(self, project_id: str) -> int:
        """
        Allocate a unique available port for a project.

        Args:
            project_id: Project identifier

        Returns:
            Available port number

        Raises:
            RuntimeError: If no ports are available
        """
        with self._lock:
            # Try up to 100 random ports to find an available one
            attempts = 0
            max_attempts = 100

            while attempts < max_attempts:
                # Pick a random port in range (better distribution for multi-user)
                port = random.randint(self.PORT_RANGE_START, self.PORT_RANGE_END)

                # Skip if already tracked as in use
                if port in self._all_ports_in_use:
                    attempts += 1
                    continue

                # Actually check if port is available
                if self._is_port_available(port):
                    # Track it
                    self._all_ports_in_use.add(port)
                    if project_id not in self._allocated_ports:
                        self._allocated_ports[project_id] = set()
                    self._allocated_ports[project_id].add(port)

                    logger.info(f"Allocated port {port} for project {project_id}")
                    return port

                attempts += 1

            # If random selection fails, try sequential
            for port in range(self.PORT_RANGE_START, self.PORT_RANGE_END):
                if port not in self._all_ports_in_use and self._is_port_available(port):
                    self._all_ports_in_use.add(port)
                    if project_id not in self._allocated_ports:
                        self._allocated_ports[project_id] = set()
                    self._allocated_ports[project_id].add(port)

                    logger.info(f"Allocated port {port} for project {project_id} (sequential)")
                    return port

            raise RuntimeError("No available ports in range")

    def release_ports(self, project_id: str):
        """
        Release all ports allocated to a project.

        Args:
            project_id: Project identifier
        """
        with self._lock:
            if project_id in self._allocated_ports:
                ports = self._allocated_ports[project_id]
                self._all_ports_in_use -= ports
                del self._allocated_ports[project_id]
                logger.info(f"Released {len(ports)} ports for project {project_id}: {ports}")

    def release_port(self, project_id: str, port: int):
        """Release a specific port"""
        with self._lock:
            if project_id in self._allocated_ports:
                self._allocated_ports[project_id].discard(port)
            self._all_ports_in_use.discard(port)

    def get_project_ports(self, project_id: str) -> Set[int]:
        """Get all ports allocated to a project"""
        return self._allocated_ports.get(project_id, set()).copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get port allocation statistics"""
        return {
            "total_allocated": len(self._all_ports_in_use),
            "projects_with_ports": len(self._allocated_ports),
            "port_range": f"{self.PORT_RANGE_START}-{self.PORT_RANGE_END}",
            "available": self.PORT_RANGE_END - self.PORT_RANGE_START - len(self._all_ports_in_use)
        }

    def recover_from_docker(self, docker_client):
        """
        Recover port allocations from running Docker containers.
        Called on startup to handle server restarts.
        """
        try:
            containers = docker_client.containers.list(
                filters={"label": "bharatbuild=true"}
            )

            for container in containers:
                project_id = container.labels.get("project_id", "unknown")
                ports = container.ports

                if ports:
                    for container_port, host_bindings in ports.items():
                        if host_bindings:
                            for binding in host_bindings:
                                host_port = int(binding.get("HostPort", 0))
                                if host_port > 0:
                                    with self._lock:
                                        self._all_ports_in_use.add(host_port)
                                        if project_id not in self._allocated_ports:
                                            self._allocated_ports[project_id] = set()
                                        self._allocated_ports[project_id].add(host_port)

            logger.info(f"Recovered {len(self._all_ports_in_use)} ports from {len(containers)} containers")

        except Exception as e:
            logger.warning(f"Could not recover ports from Docker: {e}")


# Global port manager instance
_port_manager: Optional[PortManager] = None


def get_port_manager() -> PortManager:
    """Get the global port manager instance"""
    global _port_manager
    if _port_manager is None:
        _port_manager = PortManager()
    return _port_manager


@dataclass
class ContainerConfig:
    """Configuration for project container"""
    # Resource limits
    memory_limit: str = "512m"          # Max memory (e.g., "512m", "1g")
    cpu_limit: float = 0.5              # CPU cores (0.5 = half a core)
    disk_limit: str = "1g"              # Max disk space

    # Timeouts (loaded from settings)
    idle_timeout: int = 3600            # Kill after 1 hour idle (seconds)
    max_lifetime: int = field(default_factory=lambda: settings.CONTAINER_MAX_LIFETIME)
    command_timeout: int = field(default_factory=lambda: settings.CONTAINER_COMMAND_TIMEOUT)

    # Network
    network_enabled: bool = True        # Allow network access
    # Expose common dev server ports and fallback ports (3000-3005, 5173-5175 for Vite, etc.)
    exposed_ports: List[int] = field(default_factory=lambda: [
        3000, 3001, 3002, 3003, 3004, 3005,  # Node.js/React common ports and fallbacks
        4173, 4174,                           # Vite preview ports
        5000, 5001,                           # Flask/Python common ports
        5173, 5174, 5175,                     # Vite default dev ports
        8000, 8001,                           # FastAPI/Django ports
        8080, 8081                            # General web server ports
    ])

    # Security
    read_only_root: bool = False        # Read-only root filesystem
    privileged: bool = False            # Never allow privileged mode
    cap_drop: List[str] = field(default_factory=lambda: ["ALL"])  # Drop all capabilities
    cap_add: List[str] = field(default_factory=lambda: ["CHOWN", "SETUID", "SETGID"])  # Add minimal


@dataclass
class ProjectContainer:
    """Represents a running project container"""
    container_id: str
    project_id: str
    user_id: str
    status: ContainerStatus
    created_at: datetime
    last_activity: datetime
    port_mappings: Dict[int, int] = field(default_factory=dict)  # container_port -> host_port
    config: ContainerConfig = field(default_factory=ContainerConfig)
    active_port: Optional[int] = None  # Detected active port from app output (e.g., Vite on 3001)

    def is_expired(self) -> bool:
        """Check if container should be cleaned up"""
        now = datetime.utcnow()

        # Check max lifetime
        if (now - self.created_at).total_seconds() > self.config.max_lifetime:
            return True

        # Check idle timeout
        if (now - self.last_activity).total_seconds() > self.config.idle_timeout:
            return True

        return False

    def touch(self):
        """Update last activity time"""
        self.last_activity = datetime.utcnow()


class ContainerManager:
    """
    Manages Docker containers for project execution.

    This is how Bolt.new/Replit work:
    1. User creates project → Spin up isolated container
    2. User runs code → Execute inside container
    3. Stream output → SSE back to browser
    4. Auto-cleanup → Delete after 24 hours

    Key Features:
    - Per-project isolation (security)
    - Resource limits (prevent abuse)
    - Auto-cleanup (cost savings)
    - Port forwarding (preview URLs)
    """

    # Base image with all runtimes pre-installed
    BASE_IMAGE = "bharatbuild/runtime:latest"

    # Fallback images by project type
    RUNTIME_IMAGES = {
        "node": "node:20-alpine",
        "python": "python:3.11-slim",
        "java": "eclipse-temurin:17-jdk",
        "go": "golang:1.21-alpine",
        "rust": "rust:1.75-alpine",
        "ruby": "ruby:3.2-alpine",
        "php": "php:8.2-cli-alpine",
        "static": "nginx:alpine",
    }

    def __init__(self,
                 projects_base_path: str = None,
                 docker_host: Optional[str] = None):
        """
        Initialize container manager.

        Args:
            projects_base_path: Base path for project files (defaults to settings.USER_PROJECTS_DIR)
            docker_host: Docker daemon URL (default: local socket)
        """
        if projects_base_path is None:
            from app.core.config import settings
            projects_base_path = str(settings.USER_PROJECTS_DIR)
        self.projects_base_path = Path(projects_base_path)
        self.projects_base_path.mkdir(parents=True, exist_ok=True)

        # Connect to Docker
        try:
            if docker_host:
                self.docker = docker.DockerClient(base_url=docker_host)
            else:
                self.docker = docker.from_env()

            # Verify connection
            self.docker.ping()
            logger.info("Connected to Docker daemon")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise RuntimeError(f"Docker not available: {e}")

        # Track running containers (in-memory, could use Redis)
        self.containers: Dict[str, ProjectContainer] = {}

        # Port manager for multi-user port allocation
        self.port_manager = get_port_manager()

        # Recover ports from existing Docker containers (handles server restart)
        self.port_manager.recover_from_docker(self.docker)

        # Recover container tracking from Docker (handles server restart)
        self._recover_containers_from_docker()

    def _allocate_port_for_project(self, project_id: str) -> int:
        """Allocate a unique available host port for a project"""
        return self.port_manager.allocate_port(project_id)

    def _recover_containers_from_docker(self):
        """
        Recover container tracking from running Docker containers.
        Called on startup to handle server restarts gracefully.
        """
        try:
            containers = self.docker.containers.list(
                filters={"label": "bharatbuild=true"}
            )

            for container in containers:
                try:
                    project_id = container.labels.get("project_id")
                    user_id = container.labels.get("user_id", "anonymous")
                    created_at_str = container.labels.get("created_at")

                    if not project_id:
                        continue

                    # Parse created_at from label
                    try:
                        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()
                    except (ValueError, TypeError):
                        created_at = datetime.utcnow()

                    # Extract port mappings from Docker
                    port_mappings = {}
                    if container.ports:
                        for container_port, host_bindings in container.ports.items():
                            if host_bindings:
                                # container_port is like "3000/tcp"
                                port_num = int(container_port.split('/')[0])
                                host_port = int(host_bindings[0].get("HostPort", 0))
                                if host_port > 0:
                                    port_mappings[port_num] = host_port

                    # Determine status from Docker container state
                    status = ContainerStatus.RUNNING if container.status == "running" else ContainerStatus.STOPPED

                    # Create ProjectContainer entry
                    project_container = ProjectContainer(
                        container_id=container.id,
                        project_id=project_id,
                        user_id=user_id,
                        status=status,
                        created_at=created_at,
                        last_activity=datetime.utcnow(),
                        port_mappings=port_mappings,
                        config=ContainerConfig(),
                    )

                    self.containers[project_id] = project_container
                    logger.info(f"Recovered container for project {project_id}: ports={port_mappings}, status={status.value}")

                except Exception as e:
                    logger.warning(f"Failed to recover container {container.id[:12]}: {e}")

            logger.info(f"Recovered {len(self.containers)} containers from Docker")

        except Exception as e:
            logger.warning(f"Could not recover containers from Docker: {e}")

    def _get_project_path(self, project_id: str, user_id: Optional[str] = None) -> Path:
        """
        Get filesystem path for project following Bolt.new structure.

        Structure: projects_base_path/{user_id}/{project_id}/
        Example: /data/projects/user_123/project_001/

        Args:
            project_id: Project identifier
            user_id: User identifier for user-scoped paths

        Returns:
            Path to project directory
        """
        if user_id:
            user_path = self.projects_base_path / user_id / project_id

            # Check if specified user path has actual project files
            if user_path.exists() and (user_path / "package.json").exists():
                logger.info(f"Found project with package.json at user path: {user_path}")
                return user_path

            # Search all user folders for existing project (handles auth mismatch)
            # This is needed because user_id from JWT may differ from original creator
            if self.projects_base_path.exists():
                for user_dir in self.projects_base_path.iterdir():
                    if user_dir.is_dir():
                        potential_path = user_dir / project_id
                        if potential_path.exists() and (potential_path / "package.json").exists():
                            logger.info(f"Found existing project in {user_dir.name}/{project_id}, using that path")
                            return potential_path

            # No existing project found - use the specified user path (will be created)
            logger.info(f"No existing project found, using new path: {user_path}")
            return user_path
        else:
            # Legacy fallback: {base}/{project_id}
            return self.projects_base_path / project_id

    async def create_container(self,
                               project_id: str,
                               user_id: str,
                               project_type: str = "node",
                               config: Optional[ContainerConfig] = None) -> ProjectContainer:
        """
        Create a new isolated container for a project.

        This is called when:
        1. User creates a new project
        2. User opens an existing project

        Args:
            project_id: Unique project identifier
            user_id: User who owns the project
            project_type: Type of project (node, python, etc.)
            config: Container configuration

        Returns:
            ProjectContainer with connection details
        """
        config = config or ContainerConfig()

        # Check if container already exists in memory
        if project_id in self.containers:
            existing = self.containers[project_id]
            if existing.status == ContainerStatus.RUNNING:
                existing.touch()
                return existing

        # Check if Docker container already exists (handles server restart case)
        container_name = f"bb-{project_id[:12]}"
        try:
            existing_container = self.docker.containers.get(container_name)
            logger.info(f"Found existing Docker container {container_name}, removing it...")
            existing_container.remove(force=True)
            # Release any ports that were tracked for this project
            self.port_manager.release_ports(project_id)
        except docker.errors.NotFound:
            pass  # Container doesn't exist, good
        except Exception as e:
            logger.warning(f"Error checking/removing existing container: {e}")

        # Get project directory (user-scoped like Bolt.new)
        project_path = self._get_project_path(project_id, user_id)
        project_path.mkdir(parents=True, exist_ok=True)
        docker_mount_path = _to_docker_path(project_path)
        logger.info(f"Project path for {user_id}/{project_id}: {project_path}")
        logger.info(f"Docker mount path: {docker_mount_path}")

        # Select runtime image
        image = self.RUNTIME_IMAGES.get(project_type, self.RUNTIME_IMAGES["node"])

        # Allocate unique ports for this project (multi-user safe)
        port_mappings = {}
        for container_port in config.exposed_ports:
            host_port = self._allocate_port_for_project(project_id)
            port_mappings[container_port] = host_port

        logger.info(f"Allocated ports for {project_id}: {port_mappings}")

        # Build port bindings for Docker
        port_bindings = {
            f"{cp}/tcp": hp for cp, hp in port_mappings.items()
        }

        try:
            # Create container
            container = self.docker.containers.run(
                image=image,
                name=f"bb-{project_id[:12]}",
                detach=True,
                tty=True,
                stdin_open=True,

                # Mount project directory (convert Windows paths for Docker)
                volumes={
                    _to_docker_path(project_path): {
                        "bind": "/workspace",
                        "mode": "rw"
                    }
                },

                # Working directory
                working_dir="/workspace",

                # Resource limits
                mem_limit=config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(config.cpu_limit * 100000),

                # Port mappings
                ports=port_bindings,

                # Security settings
                read_only=config.read_only_root,
                privileged=config.privileged,
                cap_drop=config.cap_drop,
                cap_add=config.cap_add,

                # Environment
                environment={
                    "PROJECT_ID": project_id,
                    "USER_ID": user_id,
                    "NODE_ENV": "development",
                    "TERM": "xterm-256color",
                },

                # Keep running
                command="tail -f /dev/null",

                # Labels for management
                labels={
                    "bharatbuild": "true",
                    "project_id": project_id,
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat(),
                },

                # Auto-remove on stop (ephemeral)
                auto_remove=False,
            )

            # Create container record
            project_container = ProjectContainer(
                container_id=container.id,
                project_id=project_id,
                user_id=user_id,
                status=ContainerStatus.RUNNING,
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                port_mappings=port_mappings,
                config=config,
            )

            self.containers[project_id] = project_container

            logger.info(f"Created container {container.id[:12]} for project {project_id}")

            return project_container

        except docker.errors.ImageNotFound:
            # Pull image and retry
            logger.info(f"Pulling image {image}...")
            self.docker.images.pull(image)
            return await self.create_container(project_id, user_id, project_type, config)

        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            raise RuntimeError(f"Container creation failed: {e}")

    async def execute_command(self,
                              project_id: str,
                              command: str,
                              timeout: Optional[int] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a command inside project container and stream output.

        This is the CORE function that makes code execution work.

        Args:
            project_id: Project identifier
            command: Command to execute (e.g., "npm install", "python main.py")
            timeout: Command timeout in seconds

        Yields:
            Stream of events: {"type": "stdout/stderr/exit", "data": "..."}
        """
        # Get container
        if project_id not in self.containers:
            yield {"type": "error", "data": "Container not found. Create project first."}
            return

        project_container = self.containers[project_id]
        project_container.touch()  # Update activity

        timeout = timeout or project_container.config.command_timeout

        try:
            # Get Docker container
            container = self.docker.containers.get(project_container.container_id)

            # Check container is running
            if container.status != "running":
                container.start()
                await asyncio.sleep(1)

            yield {"type": "status", "data": f"Executing: {command}"}

            # Get LogBus for this project to collect backend logs
            try:
                from app.services.log_bus import get_log_bus
                log_bus = get_log_bus(project_id)
            except Exception:
                log_bus = None

            # Execute command with streaming
            exec_id = container.client.api.exec_create(
                container.id,
                command,
                tty=True,
                stdin=False,
                stdout=True,
                stderr=True,
                workdir="/workspace",
            )

            # Start execution with streaming
            output = container.client.api.exec_start(
                exec_id["Id"],
                stream=True,
                tty=True,
            )

            # Stream output
            start_time = time.time()
            buffer = ""

            for chunk in output:
                # Check timeout
                if time.time() - start_time > timeout:
                    yield {"type": "error", "data": f"Command timed out after {timeout}s"}
                    break

                if isinstance(chunk, bytes):
                    text = chunk.decode("utf-8", errors="replace")
                else:
                    text = str(chunk)

                buffer += text

                # Yield complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    yield {"type": "stdout", "data": line}

                    # Detect active port from output (e.g., "Local: http://localhost:3001/")
                    self._detect_active_port(project_id, line)

                    # Send to LogBus for backend log collection
                    if log_bus:
                        self._send_to_logbus(log_bus, line, command)

                # Also yield partial output for real-time feel
                if buffer and len(buffer) > 80:
                    yield {"type": "stdout", "data": buffer}
                    if log_bus:
                        self._send_to_logbus(log_bus, buffer, command)
                    buffer = ""

            # Yield remaining buffer
            if buffer:
                yield {"type": "stdout", "data": buffer}
                if log_bus:
                    self._send_to_logbus(log_bus, buffer, command)

            # Get exit code
            exec_info = container.client.api.exec_inspect(exec_id["Id"])
            exit_code = exec_info.get("ExitCode", 0)

            yield {
                "type": "exit",
                "data": exit_code,
                "success": exit_code == 0
            }

        except docker.errors.NotFound:
            yield {"type": "error", "data": "Container was deleted"}
            del self.containers[project_id]

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            yield {"type": "error", "data": str(e)}

    async def write_file(self,
                         project_id: str,
                         file_path: str,
                         content: str,
                         user_id: Optional[str] = None) -> bool:
        """
        Write a file to project container.

        Args:
            project_id: Project identifier
            file_path: Relative path within project
            content: File content
            user_id: User identifier for user-scoped paths

        Returns:
            True if successful
        """
        # Get user_id from container record if not provided
        if not user_id and project_id in self.containers:
            user_id = self.containers[project_id].user_id

        project_path = self._get_project_path(project_id, user_id)
        full_path = project_path / file_path

        # Security: Prevent path traversal
        try:
            full_path.resolve().relative_to(project_path.resolve())
        except ValueError:
            raise ValueError("Invalid file path: path traversal detected")

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content, encoding="utf-8")

        # Update activity
        if project_id in self.containers:
            self.containers[project_id].touch()

        logger.info(f"Wrote file {file_path} to project {project_id}")
        return True

    async def read_file(self,
                        project_id: str,
                        file_path: str,
                        user_id: Optional[str] = None) -> Optional[str]:
        """
        Read a file from project container.

        Args:
            project_id: Project identifier
            file_path: Relative path within project
            user_id: User identifier for user-scoped paths

        Returns:
            File content or None if not found
        """
        # Get user_id from container record if not provided
        if not user_id and project_id in self.containers:
            user_id = self.containers[project_id].user_id

        project_path = self._get_project_path(project_id, user_id)
        full_path = project_path / file_path

        # Security: Prevent path traversal
        try:
            full_path.resolve().relative_to(project_path.resolve())
        except ValueError:
            raise ValueError("Invalid file path: path traversal detected")

        if not full_path.exists():
            return None

        return full_path.read_text(encoding="utf-8")

    async def list_files(self,
                         project_id: str,
                         path: str = ".",
                         user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List files in project directory.

        Args:
            project_id: Project identifier
            path: Relative path within project
            user_id: User identifier for user-scoped paths

        Returns:
            List of file/directory info
        """
        # Get user_id from container record if not provided
        if not user_id and project_id in self.containers:
            user_id = self.containers[project_id].user_id

        project_path = self._get_project_path(project_id, user_id)
        target_path = project_path / path

        # Security: Prevent path traversal
        try:
            target_path.resolve().relative_to(project_path.resolve())
        except ValueError:
            raise ValueError("Invalid path: path traversal detected")

        if not target_path.exists():
            return []

        files = []
        for item in target_path.iterdir():
            rel_path = item.relative_to(project_path)
            files.append({
                "name": item.name,
                "path": str(rel_path),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
            })

        return sorted(files, key=lambda x: (x["type"] != "directory", x["name"]))

    async def get_preview_url(self,
                              project_id: str,
                              container_port: int = 3000) -> Optional[str]:
        """
        Get the preview URL for a running project.

        Uses detected active_port if available (e.g., when Vite falls back to 3001).

        Args:
            project_id: Project identifier
            container_port: Port inside container (fallback if active_port not detected)

        Returns:
            URL like "http://localhost:10001" or None
        """
        if project_id not in self.containers:
            return None

        container = self.containers[project_id]

        # Priority 1: Use detected active port if available
        if container.active_port:
            host_port = container.port_mappings.get(container.active_port)
            if host_port:
                logger.info(f"[Preview] Using detected active port {container.active_port} -> {host_port}")
                return f"http://localhost:{host_port}"

        # Priority 2: Use requested container_port
        host_port = container.port_mappings.get(container_port)
        if host_port:
            return f"http://localhost:{host_port}"

        # Priority 3: Try first available mapped port
        if container.port_mappings:
            first_port = next(iter(container.port_mappings.values()))
            logger.info(f"[Preview] Falling back to first available port: {first_port}")
            return f"http://localhost:{first_port}"

        return None

    def get_all_preview_urls(self, project_id: str) -> Dict[int, str]:
        """
        Get all available preview URLs for a project.

        Returns:
            Dict mapping container_port -> preview_url
        """
        if project_id not in self.containers:
            return {}

        container = self.containers[project_id]
        urls = {}

        for container_port, host_port in container.port_mappings.items():
            urls[container_port] = f"http://localhost:{host_port}"

        return urls

    async def stop_container(self, project_id: str) -> bool:
        """
        Stop a project container.

        Args:
            project_id: Project identifier

        Returns:
            True if stopped successfully
        """
        if project_id not in self.containers:
            return False

        project_container = self.containers[project_id]

        try:
            container = self.docker.containers.get(project_container.container_id)
            container.stop(timeout=10)
            project_container.status = ContainerStatus.STOPPED
            logger.info(f"Stopped container for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            return False

    async def delete_container(self, project_id: str, delete_files: bool = False) -> bool:
        """
        Delete a project container and optionally its files.

        Args:
            project_id: Project identifier
            delete_files: Also delete project files

        Returns:
            True if deleted successfully
        """
        if project_id not in self.containers:
            return False

        project_container = self.containers[project_id]

        try:
            container = self.docker.containers.get(project_container.container_id)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")

        # Delete files if requested (use user-scoped path)
        if delete_files:
            import shutil
            project_path = self._get_project_path(project_id, project_container.user_id)
            if project_path.exists():
                shutil.rmtree(project_path)
                logger.info(f"Deleted project files at {project_path}")

        # Release allocated ports
        self.port_manager.release_ports(project_id)

        # Remove from tracking
        del self.containers[project_id]

        logger.info(f"Deleted container for project {project_id}")
        return True

    async def cleanup_expired(self) -> int:
        """
        Clean up expired containers (called periodically).

        This is what makes storage ephemeral - auto-delete after 24 hours.

        Returns:
            Number of containers cleaned up
        """
        cleaned = 0

        for project_id in list(self.containers.keys()):
            container = self.containers[project_id]

            if container.is_expired():
                logger.info(f"Cleaning up expired container: {project_id}")
                await self.delete_container(project_id, delete_files=True)
                cleaned += 1

        return cleaned

    async def get_container_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get resource usage stats for a container.

        Args:
            project_id: Project identifier

        Returns:
            Stats dict with CPU, memory, network usage
        """
        if project_id not in self.containers:
            return None

        project_container = self.containers[project_id]

        try:
            container = self.docker.containers.get(project_container.container_id)
            stats = container.stats(stream=False)

            # Parse stats
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                        stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]

            cpu_percent = (cpu_delta / system_delta) * 100 if system_delta > 0 else 0

            memory_usage = stats["memory_stats"].get("usage", 0)
            memory_limit = stats["memory_stats"].get("limit", 0)
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0

            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage_mb": round(memory_usage / 1024 / 1024, 2),
                "memory_limit_mb": round(memory_limit / 1024 / 1024, 2),
                "memory_percent": round(memory_percent, 2),
                "status": container.status,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return None

    def _detect_active_port(self, project_id: str, text: str) -> Optional[int]:
        """
        Detect the active port from terminal output.

        Parses output from various dev servers:
        - Vite: "Local: http://localhost:3001/"
        - Next.js: "ready - started server on 0.0.0.0:3000"
        - Create React App: "Local: http://localhost:3000"
        - Express: "Server running on port 3000"

        Returns the detected port if found, None otherwise.
        """
        import re

        # Patterns to detect server startup with port
        port_patterns = [
            r'Local:\s*http://localhost:(\d+)',           # Vite, CRA
            r'localhost:(\d+)',                            # Generic localhost:port
            r'127\.0\.0\.1:(\d+)',                         # 127.0.0.1:port
            r'0\.0\.0\.0:(\d+)',                           # 0.0.0.0:port
            r'started server on.*:(\d+)',                  # Next.js
            r'listening on.*:(\d+)',                       # Express
            r'Server running on port (\d+)',               # Generic
            r'App running at.*:(\d+)',                     # Vue CLI
            r'Compiled successfully.*localhost:(\d+)',     # Webpack
        ]

        for pattern in port_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                port = int(match.group(1))
                # Validate it's a reasonable port
                if 1000 <= port <= 65535:
                    # Update container's active port
                    if project_id in self.containers:
                        container = self.containers[project_id]
                        if container.active_port != port:
                            container.active_port = port
                            logger.info(f"[Port] Detected active port {port} for project {project_id}")
                    return port

        return None

    def _send_to_logbus(self, log_bus, text: str, command: str) -> None:
        """
        Send log line to LogBus for collection.
        Detects errors vs info based on content.
        Also triggers auto-fix for terminal/build errors.
        """
        import re
        import asyncio

        # Strip ALL ANSI escape codes for pattern matching
        # Extended regex to catch all escape sequences including cursor movement, etc.
        ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\r')
        clean_text = ansi_escape.sub('', text).strip()

        # Skip empty lines
        if not clean_text:
            return

        # ASCII-safe debug logging (replace non-ASCII chars)
        safe_text = clean_text.encode('ascii', 'replace').decode('ascii')[:100]
        logger.info(f"[LogBus:{log_bus.project_id}] Processing line: {safe_text}")

        # Error patterns for backend runtime
        error_patterns = [
            r'\berror\b', r'\bError\b', r'\bERROR\b',
            r'\bexception\b', r'\bException\b', r'\bEXCEPTION\b',
            r'\bfailed\b', r'\bFailed\b', r'\bFAILED\b',
            r'Traceback', r'traceback',
            r'ModuleNotFoundError', r'ImportError',
            r'TypeError', r'ValueError', r'KeyError',
            r'RuntimeError', r'AttributeError',
            r'\b500\b', r'\b404\b', r'Internal Server Error',
            r'Connection refused', r'ECONNREFUSED',
            r'EADDRINUSE', r'port.*in use',
            r'Cannot find package', r'Cannot find module',
            r'Pre-transform error', r'Build failed',
            r'ENOENT', r'spawn.*ENOENT',
        ]

        # Use clean_text (without ANSI codes) for pattern matching
        is_error = any(re.search(p, clean_text, re.IGNORECASE) for p in error_patterns)

        # Log which pattern matched (if any)
        if is_error:
            for p in error_patterns:
                if re.search(p, clean_text, re.IGNORECASE):
                    logger.info(f"[LogBus:{log_bus.project_id}] MATCHED pattern '{p}'")

        # Check if it's a stack trace
        has_stack = 'at ' in clean_text or 'File "' in clean_text or 'line ' in clean_text.lower()

        if is_error:
            logger.info(f"[LogBus] Detected error in terminal for {log_bus.project_id}: {text[:150]}")
            log_bus.add_backend_error(
                message=text,
                stack=text if has_stack else None
            )

            # ======= AUTO-FIX TRIGGER FOR TERMINAL ERRORS =======
            # Trigger auto-fix for build/compile errors from terminal
            # Skip certain non-fixable errors (system errors, warnings that don't need code changes)
            skip_patterns = [
                r'spawn.*ENOENT',  # System command not found (xdg-open in Docker)
                r'warning:',  # Warnings typically don't need fixes
                r'WARN\s',
            ]
            should_skip = any(re.search(p, clean_text, re.IGNORECASE) for p in skip_patterns)

            if should_skip:
                logger.debug(f"[AutoFix] Skipping non-fixable error: {text[:100]}")
            else:
                logger.info(f"[AutoFix] Attempting to trigger for: {text[:100]}")
                try:
                    from app.api.v1.endpoints.log_stream import log_stream_manager
                    # Try multiple approaches to get event loop
                    try:
                        # Method 1: Get running loop (works if we're in async context)
                        loop = asyncio.get_running_loop()
                        loop.create_task(
                            log_stream_manager.trigger_auto_fix(log_bus.project_id, is_error=True)
                        )
                        logger.info(f"[AutoFix] Task created for {log_bus.project_id}")
                    except RuntimeError:
                        # Method 2: Use thread-safe method if no running loop
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    log_stream_manager.trigger_auto_fix(log_bus.project_id, is_error=True),
                                    loop
                                )
                                logger.info(f"[AutoFix] Coroutine scheduled thread-safe for {log_bus.project_id}")
                            else:
                                # Method 3: Create new event loop if needed
                                asyncio.run(log_stream_manager.trigger_auto_fix(log_bus.project_id, is_error=True))
                                logger.info(f"[AutoFix] Created new loop for {log_bus.project_id}")
                        except Exception as e2:
                            logger.warning(f"[AutoFix] All loop methods failed for {log_bus.project_id}: {e2}")
                except Exception as e:
                    logger.warning(f"[AutoFix] Could not trigger for {log_bus.project_id}: {e}")
        else:
            # Determine if it's Docker or backend based on command
            if 'docker' in command.lower():
                log_bus.add_docker_log(text, level="info")
            else:
                log_bus.add_backend_log(text, level="info")


# Singleton instance
_container_manager: Optional[ContainerManager] = None


def get_container_manager() -> ContainerManager:
    """Get the global container manager instance"""
    global _container_manager

    if _container_manager is None:
        _container_manager = ContainerManager()

    return _container_manager


# Background cleanup task
async def cleanup_loop():
    """Background task to clean up expired containers"""
    manager = get_container_manager()

    while True:
        try:
            cleaned = await manager.cleanup_expired()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired containers")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

        # Run every 5 minutes
        await asyncio.sleep(300)
