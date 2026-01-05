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
import docker.tls
import os
import uuid
import json
import time
import socket
import random
import platform
import re
from typing import Optional, Dict, Any, AsyncGenerator, List, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from threading import Lock
from app.core.config import settings
from app.core.logging_config import logger

# Import workspace restore for fixing common project issues
try:
    from app.services.workspace_restore import workspace_restore
    WORKSPACE_RESTORE_AVAILABLE = True
except ImportError:
    WORKSPACE_RESTORE_AVAILABLE = False
    logger.warning("[ContainerManager] Workspace restore service not available")

# Import container state service for Redis persistence
try:
    from app.services.container_state import (
        ContainerStateService,
        ContainerInfo,
        ContainerState as RedisContainerState,
        get_container_state_service,
        save_container_state,
        get_container_state,
        update_container_heartbeat,
        delete_container_state,
    )
    REDIS_STATE_AVAILABLE = True
except ImportError:
    REDIS_STATE_AVAILABLE = False
    logger.warning("[ContainerManager] Redis state service not available, using in-memory only")

# Preview URL Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip('/')
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL") or os.getenv("SANDBOX_PREVIEW_BASE_URL", "http://localhost")


def _get_preview_url(port: int, project_id: str = None) -> str:
    """
    Generate preview URL - works in both local and production.

    Args:
        port: The container port
        project_id: Optional project ID for API-based preview URL (production)
    """
    # Check if we're in production
    is_production = (
        ENVIRONMENT == "production" or
        (FRONTEND_URL and "localhost" not in FRONTEND_URL and "127.0.0.1" not in FRONTEND_URL)
    )

    # Production with project_id: Use domain-based API preview proxy
    if is_production and project_id:
        return f"{FRONTEND_URL}/api/v1/preview/{project_id}/"

    # Fallback to IP:port
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        return f"{base}:{port}"

    return f"http://localhost:{port}"


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

    # Port range for container mappings (loaded from centralized settings)
    PORT_RANGE_START = settings.CONTAINER_PORT_RANGE_START
    PORT_RANGE_END = settings.CONTAINER_PORT_RANGE_END

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
    """Configuration for project container - uses CENTRALIZED settings"""
    # Resource limits
    memory_limit: str = field(default_factory=lambda: settings.CONTAINER_MEMORY_LIMIT)
    cpu_limit: float = field(default_factory=lambda: settings.CONTAINER_CPU_LIMIT)
    disk_limit: str = "1g"              # Max disk space

    # Timeouts (CENTRALIZED - single source of truth)
    idle_timeout: int = field(default_factory=lambda: settings.CONTAINER_IDLE_TIMEOUT_SECONDS)
    max_lifetime: int = field(default_factory=lambda: settings.CONTAINER_MAX_LIFETIME_SECONDS)
    command_timeout: int = field(default_factory=lambda: settings.CONTAINER_COMMAND_TIMEOUT)
    pause_after_idle: int = field(default_factory=lambda: settings.CONTAINER_PAUSE_AFTER_IDLE_SECONDS)

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
    docker_host: Optional[str] = None  # For multi-EC2 scaling

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

    def should_pause(self) -> bool:
        """Check if container should be paused (not deleted yet)"""
        if self.status == ContainerStatus.STOPPED:
            return False  # Already stopped/paused

        now = datetime.utcnow()
        idle_seconds = (now - self.last_activity).total_seconds()
        return idle_seconds > self.config.pause_after_idle and idle_seconds < self.config.idle_timeout

    def touch(self):
        """Update last activity time"""
        self.last_activity = datetime.utcnow()

    def to_redis_info(self) -> "ContainerInfo":
        """Convert to Redis-compatible ContainerInfo"""
        if REDIS_STATE_AVAILABLE:
            return ContainerInfo(
                container_id=self.container_id,
                project_id=self.project_id,
                user_id=self.user_id,
                state=self.status.value,
                created_at=self.created_at.isoformat(),
                last_activity=self.last_activity.isoformat(),
                port_mappings=self.port_mappings,
                active_port=self.active_port,
                docker_host=self.docker_host,
                memory_limit=self.config.memory_limit,
                cpu_limit=self.config.cpu_limit
            )
        return None


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
        Initialize container manager with TLS support and graceful degradation.

        Args:
            projects_base_path: Base path for project files (defaults to settings.USER_PROJECTS_DIR)
            docker_host: Docker daemon URL (default: local socket)
        """
        if projects_base_path is None:
            from app.core.config import settings
            projects_base_path = str(settings.USER_PROJECTS_DIR)
        self.projects_base_path = Path(projects_base_path)
        self.projects_base_path.mkdir(parents=True, exist_ok=True)

        # Store docker host for multi-EC2 tracking
        self.docker_host = docker_host or os.environ.get("SANDBOX_DOCKER_HOST")

        # Connect to Docker with TLS support and fallback
        self.docker = self._connect_to_docker(self.docker_host)

        # Track running containers (in-memory + Redis persistence)
        self.containers: Dict[str, ProjectContainer] = {}

        # Redis state service for persistence
        self._state_service = get_container_state_service() if REDIS_STATE_AVAILABLE else None

        # Port manager for multi-user port allocation
        self.port_manager = get_port_manager()

        # Recover ports from existing Docker containers (handles server restart)
        if self.docker:
            self.port_manager.recover_from_docker(self.docker)
            # Recover container tracking from Docker (handles server restart)
            self._recover_containers_from_docker()

        # User networks for isolation
        self._user_networks: Dict[str, str] = {}  # user_id -> network_id

    def _connect_to_docker(self, docker_host: Optional[str]) -> Optional[docker.DockerClient]:
        """
        Connect to Docker with TLS support and graceful fallback.

        Tries multiple connection methods:
        1. docker_client_helper (uses AWS Secrets Manager certs)
        2. Remote Docker with TLS (production)
        3. Remote Docker without TLS (development)
        4. Local Docker socket
        5. None (graceful degradation)
        """
        # Try docker_client_helper first (uses AWS Secrets Manager certs)
        if docker_host:
            try:
                from app.services.docker_client_helper import get_docker_client as get_tls_client
                client = get_tls_client()
                if client:
                    client.ping()
                    logger.info("Connected to Docker via docker_client_helper (Secrets Manager TLS)")
                    return client
            except Exception as e:
                logger.debug(f"docker_client_helper failed: {e}")

        # Fallback: Try remote Docker host
        if docker_host:
            # Try with TLS if enabled
            if settings.DOCKER_TLS_ENABLED and os.path.exists(settings.DOCKER_TLS_CA_CERT):
                try:
                    tls_config = docker.tls.TLSConfig(
                        ca_cert=settings.DOCKER_TLS_CA_CERT,
                        client_cert=(settings.DOCKER_TLS_CLIENT_CERT, settings.DOCKER_TLS_CLIENT_KEY),
                        verify=settings.DOCKER_TLS_VERIFY
                    )
                    # Convert tcp:// to https:// for TLS
                    secure_host = docker_host.replace("tcp://", "https://").replace(":2375", ":2376")
                    client = docker.DockerClient(base_url=secure_host, tls=tls_config)
                    client.ping()
                    logger.info(f"Connected to Docker daemon via TLS: {secure_host}")
                    return client
                except Exception as e:
                    logger.warning(f"TLS Docker connection failed: {e}")

            # Try without TLS (development/internal network)
            try:
                client = docker.DockerClient(base_url=docker_host)
                client.ping()
                logger.info(f"Connected to Docker daemon: {docker_host}")
                return client
            except Exception as e:
                logger.warning(f"Remote Docker connection failed: {e}")

        # Try local Docker socket
        try:
            client = docker.from_env()
            client.ping()
            logger.info("Connected to local Docker daemon")
            return client
        except Exception as e:
            logger.warning(f"Local Docker connection failed: {e}")

        # Graceful degradation - no Docker available
        logger.error("No Docker daemon available - container features disabled")
        return None

    def is_available(self) -> bool:
        """Check if Docker is available"""
        if not self.docker:
            return False
        try:
            self.docker.ping()
            return True
        except Exception:
            return False

    async def _get_or_create_user_network(self, user_id: str) -> Optional[str]:
        """
        Get or create a Docker network for user isolation.

        Each user gets their own Docker network to prevent cross-user access.

        Args:
            user_id: User identifier

        Returns:
            Network name or None if failed
        """
        if not self.docker:
            return None

        network_name = f"bb-user-{user_id[:12]}"

        # Check cache first
        if user_id in self._user_networks:
            return self._user_networks[user_id]

        try:
            # Check if network already exists
            try:
                network = self.docker.networks.get(network_name)
                self._user_networks[user_id] = network_name
                return network_name
            except docker.errors.NotFound:
                pass

            # Create new network for user
            network = self.docker.networks.create(
                name=network_name,
                driver="bridge",
                labels={
                    "bharatbuild": "true",
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            self._user_networks[user_id] = network_name
            logger.info(f"Created Docker network for user {user_id}: {network_name}")
            return network_name

        except Exception as e:
            logger.warning(f"Failed to create user network: {e}")
            return None

    async def get_or_reuse_container(
        self,
        project_id: str,
        user_id: str,
        project_type: str = "node",
        config: Optional[ContainerConfig] = None
    ) -> Tuple[ProjectContainer, bool]:
        """
        Get existing container or create new one (container reuse strategy).

        This implements the container reuse optimization to avoid creating
        new containers for every request.

        Args:
            project_id: Unique project identifier
            user_id: User who owns the project
            project_type: Type of project (node, python, etc.)
            config: Container configuration

        Returns:
            Tuple of (ProjectContainer, was_reused: bool)
        """
        if not settings.CONTAINER_REUSE_ENABLED:
            container = await self.create_container(project_id, user_id, project_type, config)
            return container, False

        # Check in-memory cache first
        if project_id in self.containers:
            existing = self.containers[project_id]
            if await self._is_container_healthy(existing):
                # Reuse existing container
                existing.touch()
                await self._persist_container_state(existing)
                logger.info(f"Reusing existing container for project {project_id}")
                return existing, True
            else:
                # Container unhealthy, clean up and create new
                logger.info(f"Existing container unhealthy, creating new for {project_id}")
                await self.delete_container(project_id)

        # Check Redis state for container on another instance
        if self._state_service:
            try:
                redis_info = await get_container_state(project_id)
                if redis_info and redis_info.state == "running":
                    # Container exists on another backend instance
                    # Try to recover it
                    recovered = await self._try_recover_container(redis_info)
                    if recovered:
                        return recovered, True
            except Exception as e:
                logger.warning(f"Redis container lookup failed: {e}")

        # Create new container
        container = await self.create_container(project_id, user_id, project_type, config)
        return container, False

    async def _is_container_healthy(self, container: ProjectContainer) -> bool:
        """
        Check if a container is healthy and running.

        Args:
            container: ProjectContainer to check

        Returns:
            True if container is healthy
        """
        if not self.docker:
            return False

        try:
            docker_container = self.docker.containers.get(container.container_id)
            if docker_container.status != "running":
                # Try to start paused container
                if docker_container.status == "paused":
                    docker_container.unpause()
                    await asyncio.sleep(1)
                    return docker_container.status == "running"
                elif docker_container.status == "exited":
                    docker_container.start()
                    await asyncio.sleep(1)
                    return docker_container.status == "running"
                return False
            return True
        except docker.errors.NotFound:
            return False
        except Exception as e:
            logger.warning(f"Container health check failed: {e}")
            return False

    async def _try_recover_container(self, redis_info: "ContainerInfo") -> Optional[ProjectContainer]:
        """
        Try to recover a container from Redis state info.

        Args:
            redis_info: Container info from Redis

        Returns:
            ProjectContainer if recovery successful, None otherwise
        """
        if not self.docker:
            return None

        try:
            docker_container = self.docker.containers.get(redis_info.container_id)
            if docker_container.status == "running":
                # Recover the container
                project_container = ProjectContainer(
                    container_id=redis_info.container_id,
                    project_id=redis_info.project_id,
                    user_id=redis_info.user_id,
                    status=ContainerStatus.RUNNING,
                    created_at=datetime.fromisoformat(redis_info.created_at),
                    last_activity=datetime.utcnow(),
                    port_mappings=redis_info.port_mappings,
                    active_port=redis_info.active_port,
                    docker_host=redis_info.docker_host
                )
                self.containers[redis_info.project_id] = project_container
                logger.info(f"Recovered container {redis_info.project_id} from Redis")
                return project_container
        except Exception as e:
            logger.warning(f"Failed to recover container: {e}")

        return None

    async def _persist_container_state(self, container: ProjectContainer):
        """
        Persist container state to Redis.

        Args:
            container: Container to persist
        """
        if REDIS_STATE_AVAILABLE and self._state_service:
            try:
                redis_info = container.to_redis_info()
                if redis_info:
                    await save_container_state(redis_info)
            except Exception as e:
                logger.warning(f"Failed to persist container state: {e}")

    async def pause_container(self, project_id: str) -> bool:
        """
        Pause a container to save resources (warm pause).

        Paused containers use ~0 CPU but preserve state.
        They can be quickly resumed on user action.

        Args:
            project_id: Project identifier

        Returns:
            True if paused successfully
        """
        if project_id not in self.containers:
            return False

        if not self.docker:
            return False

        project_container = self.containers[project_id]

        try:
            container = self.docker.containers.get(project_container.container_id)
            if container.status == "running":
                container.pause()
                project_container.status = ContainerStatus.STOPPED
                await self._persist_container_state(project_container)
                logger.info(f"Paused container for project {project_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to pause container: {e}")

        return False

    async def resume_container(self, project_id: str) -> bool:
        """
        Resume a paused container.

        Args:
            project_id: Project identifier

        Returns:
            True if resumed successfully
        """
        if project_id not in self.containers:
            return False

        if not self.docker:
            return False

        project_container = self.containers[project_id]

        try:
            container = self.docker.containers.get(project_container.container_id)
            if container.status == "paused":
                container.unpause()
                project_container.status = ContainerStatus.RUNNING
                project_container.touch()
                await self._persist_container_state(project_container)
                logger.info(f"Resumed container for project {project_id}")
                return True
            elif container.status == "exited":
                container.start()
                project_container.status = ContainerStatus.RUNNING
                project_container.touch()
                await self._persist_container_state(project_container)
                logger.info(f"Started container for project {project_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to resume container: {e}")

        return False

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

        Raises:
            RuntimeError: If Docker is not available (graceful degradation info provided)
        """
        # Graceful degradation - check Docker availability
        if not self.is_available():
            raise RuntimeError(
                "Docker is not available. Container features are disabled. "
                "Please check Docker configuration or try again later."
            )

        config = config or ContainerConfig()

        # Check if container already exists in memory
        if project_id in self.containers:
            existing = self.containers[project_id]
            if existing.status == ContainerStatus.RUNNING:
                existing.touch()
                await self._persist_container_state(existing)
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

        # Fix common project issues before container starts (vite open:true, missing tsconfig.node.json, etc.)
        if WORKSPACE_RESTORE_AVAILABLE:
            try:
                fix_result = await workspace_restore.fix_common_issues(project_path, project_id=project_id)
                if fix_result.get("fixes_applied"):
                    logger.info(f"[ContainerManager] Applied pre-start fixes for {project_id}: {fix_result['fixes_applied']}")
            except Exception as e:
                logger.warning(f"[ContainerManager] Error applying pre-start fixes: {e}")

        # Always use multi-technology base image (supports Node.js, Java, Maven, Python, Go, etc.)
        # This ensures fullstack projects (e.g., Spring Boot + React) work correctly
        image = self.BASE_IMAGE
        logger.info(f"Using multi-technology sandbox image: {image}")

        # Get or create user network for isolation
        user_network = await self._get_or_create_user_network(user_id)

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

        # Current timestamp for labels
        now = datetime.utcnow()
        now_iso = now.isoformat()

        try:
            # Build container run kwargs
            container_kwargs = {
                "image": image,
                "name": f"bb-{project_id[:12]}",
                "detach": True,
                "tty": True,
                "stdin_open": True,

                # Mount project directory (convert Windows paths for Docker)
                "volumes": {
                    _to_docker_path(project_path): {
                        "bind": "/workspace",
                        "mode": "rw"
                    }
                },

                # Working directory
                "working_dir": "/workspace",

                # Resource limits
                "mem_limit": config.memory_limit,
                "cpu_period": 100000,
                "cpu_quota": int(config.cpu_limit * 100000),

                # Port mappings
                "ports": port_bindings,

                # Security settings
                "read_only": config.read_only_root,
                "privileged": config.privileged,
                "cap_drop": config.cap_drop,
                "cap_add": config.cap_add,

                # Environment
                "environment": {
                    "PROJECT_ID": project_id,
                    "USER_ID": user_id,
                    "NODE_ENV": "development",
                    "TERM": "xterm-256color",
                },

                # Keep running
                "command": "tail -f /dev/null",

                # Labels for management - includes heartbeat for race condition fix
                "labels": {
                    "bharatbuild": "true",
                    "project_id": project_id,
                    "user_id": user_id,
                    "created_at": now_iso,
                    "last_activity": now_iso,  # Heartbeat label for EC2 cron
                    "idle_timeout": str(config.idle_timeout),
                    "docker_host": self.docker_host or "local",
                },

                # Auto-remove on stop (ephemeral)
                "auto_remove": False,
            }

            # Add user network if available (isolation)
            if user_network:
                container_kwargs["network"] = user_network

            # Create container
            container = self.docker.containers.run(**container_kwargs)

            # Create container record
            project_container = ProjectContainer(
                container_id=container.id,
                project_id=project_id,
                user_id=user_id,
                status=ContainerStatus.RUNNING,
                created_at=now,
                last_activity=now,
                port_mappings=port_mappings,
                config=config,
                docker_host=self.docker_host,
            )

            self.containers[project_id] = project_container

            # Persist to Redis for cross-instance recovery
            await self._persist_container_state(project_container)

            logger.info(f"Created container {container.id[:12]} for project {project_id} (network: {user_network or 'default'})")

            return project_container

        except docker.errors.ImageNotFound:
            # Base image not found - try to pull or fallback to node image
            logger.warning(f"Image {image} not found, attempting to pull...")
            try:
                self.docker.images.pull(image)
                return await self.create_container(project_id, user_id, project_type, config)
            except Exception as pull_error:
                # Fallback to node:20 which has npm for most projects
                logger.warning(f"Failed to pull {image}: {pull_error}. Falling back to node:20")
                fallback_image = self.RUNTIME_IMAGES.get(project_type, "node:20")
                self.docker.images.pull(fallback_image)
                # Update BASE_IMAGE for future containers in this session
                self.__class__.BASE_IMAGE = fallback_image
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

    # Directories to hide from file explorer (generated/build artifacts)
    HIDDEN_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
        'dist', 'build', '.next', '.vite', '.cache', '.turbo',
        'target', '.gradle', '.idea', '.vs',
        'coverage', '.nyc_output', '.pytest_cache', '__snapshots__'
    }

    async def list_files(self,
                         project_id: str,
                         path: str = ".",
                         user_id: Optional[str] = None,
                         include_hidden: bool = False) -> List[Dict[str, Any]]:
        """
        List files in project directory.

        Args:
            project_id: Project identifier
            path: Relative path within project
            user_id: User identifier for user-scoped paths
            include_hidden: If True, include node_modules and other generated dirs

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
            # Skip hidden/generated directories unless explicitly requested
            if not include_hidden and item.is_dir() and item.name in self.HIDDEN_DIRS:
                continue

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
                return _get_preview_url(host_port)

        # Priority 2: Use requested container_port
        host_port = container.port_mappings.get(container_port)
        if host_port:
            return _get_preview_url(host_port)

        # Priority 3: Try first available mapped port
        if container.port_mappings:
            first_port = next(iter(container.port_mappings.values()))
            logger.info(f"[Preview] Falling back to first available port: {first_port}")
            return _get_preview_url(first_port)

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
            urls[container_port] = _get_preview_url(host_port)

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
            # Try to delete from Redis state even if not in memory
            if REDIS_STATE_AVAILABLE:
                await delete_container_state(project_id)
            return False

        project_container = self.containers[project_id]

        try:
            if self.docker:
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

        # Remove from Redis state
        if REDIS_STATE_AVAILABLE:
            await delete_container_state(project_id)

        logger.info(f"Deleted container for project {project_id}")
        return True

    async def cleanup_expired(self) -> Dict[str, int]:
        """
        Clean up expired containers with warm pause strategy.

        Strategy:
        1. Containers idle > 5 min but < 30 min → PAUSE (preserve state, use ~0 CPU)
        2. Containers idle > 30 min → DELETE (free resources)
        3. Containers > 24 hours → DELETE (max lifetime reached)

        Returns:
            Dict with counts: {"paused": N, "deleted": M}
        """
        paused = 0
        deleted = 0

        for project_id in list(self.containers.keys()):
            container = self.containers[project_id]

            if container.is_expired():
                # Fully expired - delete
                logger.info(f"Cleaning up expired container: {project_id}")
                await self.delete_container(project_id, delete_files=True)
                deleted += 1
            elif container.should_pause():
                # Idle but not expired - pause to save resources
                logger.info(f"Pausing idle container: {project_id}")
                success = await self.pause_container(project_id)
                if success:
                    paused += 1

        return {"paused": paused, "deleted": deleted}

    async def update_container_heartbeat(self, project_id: str) -> bool:
        """
        Update container heartbeat (called on user activity).

        This updates both in-memory state and Docker container labels,
        preventing race conditions with EC2 cron cleanup.

        Args:
            project_id: Project identifier

        Returns:
            True if successful
        """
        if project_id not in self.containers:
            return False

        container = self.containers[project_id]
        container.touch()

        # Update Docker container label (for EC2 cron to read)
        if self.docker:
            try:
                docker_container = self.docker.containers.get(container.container_id)
                # Note: Docker doesn't support updating labels on running containers
                # But we can add a file inside the container that the cleanup script reads
                # For now, we rely on Redis state which the cleanup should check
            except Exception as e:
                logger.warning(f"Could not update Docker heartbeat: {e}")

        # Update Redis state
        if REDIS_STATE_AVAILABLE:
            await update_container_heartbeat(project_id)

        # Persist full state
        await self._persist_container_state(container)

        return True

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
            # JavaScript/Node.js
            r'Local:\s*http://localhost:(\d+)',           # Vite, CRA
            r'localhost:(\d+)',                            # Generic localhost:port
            r'127\.0\.0\.1:(\d+)',                         # 127.0.0.1:port
            r'0\.0\.0\.0:(\d+)',                           # 0.0.0.0:port
            r'started server on.*:(\d+)',                  # Next.js
            r'listening on.*:(\d+)',                       # Express
            r'Server running on port (\d+)',               # Generic
            r'App running at.*:(\d+)',                     # Vue CLI
            r'Compiled successfully.*localhost:(\d+)',     # Webpack
            # Java/Spring Boot
            r'Tomcat started on port\(s\):\s*(\d+)',       # Spring Boot Tomcat
            r'Tomcat initialized with port\(s\):\s*(\d+)', # Tomcat initialization
            r'Netty started on port\(s\):\s*(\d+)',        # Spring WebFlux Netty
            r'Started \w+ in .* seconds.*:(\d+)',          # Spring Boot startup
            r'Undertow started on port\(s\)\s*(\d+)',      # Spring Boot Undertow
            # Python
            r'Uvicorn running on.*:(\d+)',                 # FastAPI/Uvicorn
            r'Running on http://.*:(\d+)',                 # Flask
            r'Starting development server at.*:(\d+)',     # Django
            r'Streamlit.*running.*:(\d+)',                 # Streamlit
            # Go
            r'Listening on.*:(\d+)',                       # Go HTTP server
            r'Starting server on.*:(\d+)',                 # Go server
            # .NET
            r'Now listening on.*:(\d+)',                   # ASP.NET Core
            # Ruby
            r'Listening on.*:(\d+)',                       # Rails/Puma
            # PHP
            r'Development Server.*started.*:(\d+)',        # PHP built-in server
            r'Laravel development server started.*:(\d+)', # Laravel
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
    """
    Background task to clean up expired containers.

    Uses centralized CONTAINER_CLEANUP_INTERVAL_SECONDS from settings.
    Implements warm pause strategy: idle containers are paused before deletion.
    """
    manager = get_container_manager()
    cleanup_interval = settings.CONTAINER_CLEANUP_INTERVAL_SECONDS

    while True:
        try:
            result = await manager.cleanup_expired()
            if result["deleted"] > 0 or result["paused"] > 0:
                logger.info(
                    f"Container cleanup: {result['deleted']} deleted, {result['paused']} paused"
                )
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

        # Use centralized config for interval
        await asyncio.sleep(cleanup_interval)
