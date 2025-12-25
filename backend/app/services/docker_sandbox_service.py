"""
Docker Sandbox Service - Manages isolated Docker containers for project execution
Like Bolt.new: Creates fresh containers for each project, manages lifecycle
"""

import os
import asyncio
import docker
from docker.errors import NotFound, APIError, ImageNotFound
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.sandbox_db_service import SandboxDBService
from app.models.sandbox import SandboxStatus
from app.core.logging_config import logger

# Sandbox public URL for preview (use sandbox EC2 public IP/domain in production)
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL") or os.getenv("SANDBOX_PREVIEW_BASE_URL", "http://localhost")


def get_preview_url(port: int) -> str:
    """Generate preview URL using sandbox public URL or localhost fallback"""
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        # Use path-based routing: /sandbox/PORT/
        # This works with Nginx reverse proxy that routes /sandbox/PORT/* to EC2:PORT
        return f"{base}/{port}/"
    return f"http://localhost:{port}"


@dataclass
class ContainerConfig:
    """Configuration for sandbox container"""
    image: str = "bharatbuild/runtime:latest"
    cpu_limit: float = 0.5
    memory_limit: str = "512m"
    container_port: int = 3000
    working_dir: str = "/workspace"
    environment: Dict[str, str] = None

    def __post_init__(self):
        if self.environment is None:
            self.environment = {
                "NODE_ENV": "development",
                "HOST": "0.0.0.0"
            }


@dataclass
class ContainerResult:
    """Result of container operation"""
    success: bool
    container_id: Optional[str]
    host_port: Optional[int]
    preview_url: Optional[str]
    error: Optional[str]
    logs: Optional[str] = None


class DockerSandboxService:
    """
    Manages Docker containers for project sandboxes.

    Features:
    - Create isolated containers for each project
    - Dynamic port allocation
    - Resource limits (CPU, memory)
    - Container lifecycle management
    - Log streaming
    - Command execution
    """

    # Port range for sandbox containers
    PORT_RANGE_START = 10000
    PORT_RANGE_END = 20000

    # Container name prefix
    CONTAINER_PREFIX = "sandbox_"

    # Base workspace path on host
    WORKSPACE_BASE = os.environ.get("SANDBOX_WORKSPACE_PATH", "/tmp/sandbox/workspace")

    def __init__(self, db: AsyncSession):
        self.db = db
        self.db_service = SandboxDBService(db)
        self._docker_client = None
        self._used_ports: set = set()

    @property
    def docker_client(self):
        """Lazy initialization of Docker client"""
        if self._docker_client is None:
            try:
                # Check for remote Docker host (ECS -> EC2 sandbox)
                sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
                if sandbox_docker_host:
                    logger.info(f"Connecting to remote Docker host: {sandbox_docker_host}")
                    self._docker_client = docker.DockerClient(base_url=sandbox_docker_host)
                    self._docker_client.ping()
                    logger.info("Docker client initialized via SANDBOX_DOCKER_HOST")
                else:
                    # Local Docker - try explicit URLs first
                    import platform
                    system = platform.system()

                    docker_urls = []
                    if system == "Windows":
                        docker_urls = ["npipe:////./pipe/docker_engine", "tcp://localhost:2375"]
                    else:
                        docker_urls = ["unix:///var/run/docker.sock", "tcp://localhost:2375"]

                    for url in docker_urls:
                        try:
                            self._docker_client = docker.DockerClient(base_url=url)
                            self._docker_client.ping()
                            logger.info(f"Docker client connected via: {url}")
                            break
                        except Exception:
                            self._docker_client = None
                            continue

                    # Fallback to from_env
                    if self._docker_client is None:
                        self._docker_client = docker.from_env()
                        self._docker_client.ping()

            except Exception as e:
                logger.error(f"Failed to connect to Docker: {e}")
                raise RuntimeError(f"Docker not available: {e}")
        return self._docker_client

    async def create_sandbox(
        self,
        project_id: UUID,
        workspace_path: str,
        config: Optional[ContainerConfig] = None
    ) -> ContainerResult:
        """
        Create a new sandbox container for a project.

        Steps:
        1. Allocate a free port
        2. Create container with project files mounted
        3. Start container
        4. Record in database
        5. Return container info
        """
        config = config or ContainerConfig()
        container_name = f"{self.CONTAINER_PREFIX}{str(project_id)[:8]}"

        try:
            # Step 1: Allocate port
            host_port = await self._allocate_port()
            if not host_port:
                return ContainerResult(
                    success=False,
                    container_id=None,
                    host_port=None,
                    preview_url=None,
                    error="No available ports"
                )

            # Step 2: Ensure image exists
            await self._ensure_image(config.image)

            # Step 3: Remove existing container if any
            await self._remove_container(container_name)

            # Step 4: Create container
            container = self.docker_client.containers.create(
                image=config.image,
                name=container_name,
                detach=True,
                ports={f"{config.container_port}/tcp": host_port},
                volumes={
                    workspace_path: {
                        "bind": config.working_dir,
                        "mode": "rw"
                    }
                },
                working_dir=config.working_dir,
                environment={
                    **config.environment,
                    "PORT": str(config.container_port),
                    "PROJECT_ID": str(project_id)
                },
                mem_limit=config.memory_limit,
                nano_cpus=int(config.cpu_limit * 1e9),
                labels={
                    "bharatbuild.sandbox": "true",
                    "bharatbuild.project_id": str(project_id),
                    "bharatbuild.created_at": datetime.utcnow().isoformat()
                },
                security_opt=["no-new-privileges:true"]
            )

            # Step 5: Start container
            container.start()

            # Step 6: Record in database
            sandbox = await self.db_service.create_sandbox_instance(
                project_id=project_id,
                docker_container_id=container.id,
                port_mappings={str(config.container_port): host_port},
                cpu_limit=str(config.cpu_limit),
                memory_limit=config.memory_limit
            )

            # Update with additional info
            await self.db_service.update_sandbox_status(
                sandbox_id=UUID(sandbox.id) if isinstance(sandbox.id, str) else sandbox.id,
                status=SandboxStatus.RUNNING
            )

            preview_url = get_preview_url(host_port)

            logger.info(f"Created sandbox container {container_name} on port {host_port}")

            return ContainerResult(
                success=True,
                container_id=container.id,
                host_port=host_port,
                preview_url=preview_url,
                error=None
            )

        except ImageNotFound as e:
            logger.error(f"Docker image not found: {e}")
            return ContainerResult(
                success=False,
                container_id=None,
                host_port=None,
                preview_url=None,
                error=f"Image not found: {config.image}"
            )
        except APIError as e:
            logger.error(f"Docker API error: {e}")
            return ContainerResult(
                success=False,
                container_id=None,
                host_port=None,
                preview_url=None,
                error=f"Docker error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            return ContainerResult(
                success=False,
                container_id=None,
                host_port=None,
                preview_url=None,
                error=str(e)
            )

    async def start_dev_server(
        self,
        container_id: str,
        command: str = "npm run dev"
    ) -> ContainerResult:
        """
        Start the development server inside a container.

        Common commands:
        - npm run dev (Vite, Next.js)
        - npm start (React CRA)
        - python main.py (Python)
        """
        try:
            container = self.docker_client.containers.get(container_id)

            # Execute command in background
            exec_result = container.exec_run(
                cmd=f"/bin/bash -c '{command}'",
                detach=True,
                tty=True
            )

            logger.info(f"Started dev server in container {container_id}: {command}")

            return ContainerResult(
                success=True,
                container_id=container_id,
                host_port=None,
                preview_url=None,
                error=None
            )

        except NotFound:
            return ContainerResult(
                success=False,
                container_id=None,
                host_port=None,
                preview_url=None,
                error="Container not found"
            )
        except Exception as e:
            return ContainerResult(
                success=False,
                container_id=None,
                host_port=None,
                preview_url=None,
                error=str(e)
            )

    async def execute_command(
        self,
        container_id: str,
        command: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Execute a command in a container and return output.

        Used for:
        - npm install
        - npm run build
        - Running tests
        - Any shell command
        """
        try:
            container = self.docker_client.containers.get(container_id)

            exec_result = container.exec_run(
                cmd=f"/bin/bash -c '{command}'",
                demux=True
            )

            stdout = exec_result.output[0].decode() if exec_result.output[0] else ""
            stderr = exec_result.output[1].decode() if exec_result.output[1] else ""

            return {
                "success": exec_result.exit_code == 0,
                "exit_code": exec_result.exit_code,
                "stdout": stdout,
                "stderr": stderr
            }

        except NotFound:
            return {"success": False, "error": "Container not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def install_dependencies(
        self,
        container_id: str,
        project_type: str = "node"
    ) -> Dict[str, Any]:
        """
        Install project dependencies based on project type.
        """
        commands = {
            "node": "npm install",
            "nextjs": "npm install",
            "vite": "npm install",
            "react": "npm install",
            "python": "pip install -r requirements.txt",
            "vue": "npm install"
        }

        command = commands.get(project_type, "npm install")
        return await self.execute_command(container_id, command, timeout=300)

    async def get_container_logs(
        self,
        container_id: str,
        tail: int = 100
    ) -> str:
        """Get recent logs from container"""
        try:
            container = self.docker_client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode() if isinstance(logs, bytes) else logs
        except NotFound:
            return "Container not found"
        except Exception as e:
            return f"Error: {e}"

    async def stop_sandbox(self, project_id: UUID) -> bool:
        """Stop and remove sandbox container"""
        container_name = f"{self.CONTAINER_PREFIX}{str(project_id)[:8]}"

        try:
            await self._remove_container(container_name)

            # Update database
            await self.db_service.cleanup_project_sandbox_data(project_id)

            logger.info(f"Stopped sandbox for project {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop sandbox: {e}")
            return False

    async def get_sandbox_status(self, container_id: str) -> Dict[str, Any]:
        """Get current status of a sandbox container"""
        try:
            container = self.docker_client.containers.get(container_id)
            return {
                "status": container.status,
                "running": container.status == "running",
                "health": container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown"),
                "started_at": container.attrs.get("State", {}).get("StartedAt"),
                "ports": container.ports
            }
        except NotFound:
            return {"status": "not_found", "running": False}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def list_sandboxes(self) -> List[Dict[str, Any]]:
        """List all active sandbox containers"""
        try:
            containers = self.docker_client.containers.list(
                filters={"label": "bharatbuild.sandbox=true"}
            )

            return [
                {
                    "container_id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "project_id": c.labels.get("bharatbuild.project_id"),
                    "created_at": c.labels.get("bharatbuild.created_at"),
                    "ports": c.ports
                }
                for c in containers
            ]
        except Exception as e:
            logger.error(f"Failed to list sandboxes: {e}")
            return []

    # ========== Private Methods ==========

    async def _allocate_port(self) -> Optional[int]:
        """Find an available port in the range"""
        # Get currently used ports
        used_ports = await self._get_used_ports()

        for port in range(self.PORT_RANGE_START, self.PORT_RANGE_END):
            if port not in used_ports:
                self._used_ports.add(port)
                return port

        return None

    async def _get_used_ports(self) -> set:
        """Get all ports currently in use by sandbox containers"""
        used = set(self._used_ports)

        try:
            containers = self.docker_client.containers.list(
                filters={"label": "bharatbuild.sandbox=true"}
            )

            for container in containers:
                for port_mapping in container.ports.values():
                    if port_mapping:
                        for pm in port_mapping:
                            used.add(int(pm["HostPort"]))
        except (KeyError, TypeError, ValueError) as e:
            logger.debug(f"Error getting used ports: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error getting used ports: {type(e).__name__}: {e}")

        return used

    async def _ensure_image(self, image: str):
        """Ensure Docker image exists, pull if not"""
        try:
            self.docker_client.images.get(image)
        except ImageNotFound:
            logger.info(f"Pulling Docker image: {image}")
            self.docker_client.images.pull(image)

    async def _remove_container(self, container_name: str):
        """Remove a container if it exists"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.stop(timeout=10)
            container.remove(force=True)
            logger.info(f"Removed existing container: {container_name}")
        except NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error removing container {container_name}: {e}")

    async def cleanup_stale_sandboxes(self, max_age_hours: int = 24):
        """Remove sandboxes older than max_age_hours"""
        try:
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": "bharatbuild.sandbox=true"}
            )

            now = datetime.utcnow()
            removed = 0

            for container in containers:
                created_at = container.labels.get("bharatbuild.created_at")
                if created_at:
                    try:
                        created = datetime.fromisoformat(created_at)
                        age_hours = (now - created).total_seconds() / 3600

                        if age_hours > max_age_hours:
                            container.stop(timeout=5)
                            container.remove(force=True)
                            removed += 1
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Error parsing container created_at: {e}")
                    except Exception as e:
                        logger.warning(f"Error processing stale container: {type(e).__name__}: {e}")

            logger.info(f"Cleaned up {removed} stale sandboxes")
            return removed

        except Exception as e:
            logger.error(f"Failed to cleanup sandboxes: {e}")
            return 0
