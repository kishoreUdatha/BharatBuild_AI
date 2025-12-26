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

# Note: Environment variables are read dynamically in _get_preview_url() to handle late initialization


def _get_preview_url(port: int, project_id: str = None) -> str:
    """
    Generate preview URL using API proxy pattern (production) or localhost (development).

    Production: Uses /api/v1/preview/{project_id}/ which proxies through backend
    Development: Uses localhost:{port}

    Note: Reads environment variables dynamically (not at import time) to ensure
    they are available even if module was imported before env was configured.
    """
    # Read environment variables dynamically
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip('/')
    environment = os.getenv("ENVIRONMENT", "development")
    sandbox_public_url = os.getenv("SANDBOX_PUBLIC_URL") or os.getenv("SANDBOX_PREVIEW_BASE_URL", "")

    # Determine if we're in production
    is_production = (
        environment == "production" or
        (frontend_url and "localhost" not in frontend_url and "127.0.0.1" not in frontend_url)
    )

    logger.info(f"[ContainerExecutor] _get_preview_url: port={port}, project_id={project_id}, "
                f"env={environment}, frontend_url={frontend_url}, is_production={is_production}")

    if is_production and project_id:
        # Use API proxy pattern - this routes through backend preview_proxy
        result = f"{frontend_url}/api/v1/preview/{project_id}/"
        logger.info(f"[ContainerExecutor] Preview URL (production): {result}")
        return result

    if sandbox_public_url and sandbox_public_url != "http://localhost":
        # Use sandbox public URL if available
        base = sandbox_public_url.rstrip('/')
        # Remove any existing port from base URL
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        result = f"{base}:{port}"
        logger.info(f"[ContainerExecutor] Preview URL (sandbox): {result}")
        return result

    result = f"http://localhost:{port}"
    logger.info(f"[ContainerExecutor] Preview URL (local): {result}")
    return result


class Technology(Enum):
    """Supported technology stacks - Universal Preview Architecture"""
    # Frontend Frameworks
    NODEJS = "nodejs"
    NODEJS_VITE = "nodejs_vite"  # Vite-based projects (React, Vue, Svelte with Vite)
    REACT_NATIVE = "react_native"  # React Native (Metro bundler - web preview)
    FLUTTER = "flutter"  # Flutter (web preview)
    ANGULAR = "angular"

    # Backend Frameworks
    JAVA = "java"  # Spring Boot
    PYTHON = "python"  # FastAPI, Django, Flask
    PYTHON_ML = "python_ml"  # AI/ML/DL with Jupyter
    GO = "go"
    DOTNET = "dotnet"  # ASP.NET Core

    # Blockchain
    BLOCKCHAIN = "blockchain"  # Solidity, Hardhat, Truffle

    # Databases (with web UI)
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    MYSQL = "mysql"

    # Specialized
    JUPYTER = "jupyter"  # Jupyter notebooks for AI/ML/DL
    STREAMLIT = "streamlit"  # Streamlit for ML dashboards

    UNKNOWN = "unknown"


@dataclass
class ContainerConfig:
    """Configuration for a technology container - uses CENTRALIZED settings"""
    image: str
    run_command: str
    build_command: Optional[str] = None
    port: int = 3000
    memory_limit: str = "512m"
    cpu_limit: float = 0.5
    # Use centralized timeout from settings (default 30 minutes)
    timeout_seconds: int = None

    def __post_init__(self):
        # Load from centralized settings if not specified
        from app.core.config import settings
        if self.timeout_seconds is None:
            self.timeout_seconds = settings.CONTAINER_IDLE_TIMEOUT_SECONDS


# Pre-built images for each technology - Universal Preview Architecture
TECHNOLOGY_CONFIGS: Dict[Technology, ContainerConfig] = {
    # ==================== FRONTEND FRAMEWORKS ====================
    Technology.NODEJS: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install",
        run_command="npm run dev -- --host 0.0.0.0 --no-open",
        port=3000,
        memory_limit="512m"
    ),
    Technology.NODEJS_VITE: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install",
        run_command="npm run dev -- --host 0.0.0.0 --no-open",
        port=5173,  # Vite default port
        memory_limit="512m"
    ),
    Technology.ANGULAR: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install",
        run_command="npm run start -- --host 0.0.0.0 --port 4200 --disable-host-check",
        port=4200,
        memory_limit="512m"
    ),
    Technology.REACT_NATIVE: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install && npx expo export:web",
        run_command="npx serve dist -l 3000",
        port=3000,  # Web preview for React Native
        memory_limit="1g"
    ),
    Technology.FLUTTER: ContainerConfig(
        image="cirrusci/flutter:stable",
        build_command="flutter pub get && flutter build web",
        run_command="python3 -m http.server 8080 --directory build/web",
        port=8080,  # Flutter web preview
        memory_limit="1g",
        cpu_limit=1.0
    ),

    # ==================== BACKEND FRAMEWORKS ====================
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
    Technology.DOTNET: ContainerConfig(
        image="mcr.microsoft.com/dotnet/sdk:8.0",
        build_command="dotnet restore && dotnet build",
        run_command="dotnet run --urls=http://0.0.0.0:5000",
        port=5000,
        memory_limit="1g",
        cpu_limit=1.0
    ),

    # ==================== AI / ML / DL ====================
    Technology.PYTHON_ML: ContainerConfig(
        image="python:3.11",
        build_command="pip install -r requirements.txt",
        run_command="python main.py",
        port=8000,
        memory_limit="2g",  # ML needs more memory
        cpu_limit=2.0
    ),
    Technology.JUPYTER: ContainerConfig(
        image="jupyter/scipy-notebook:latest",
        build_command=None,
        run_command="jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token=''",
        port=8888,
        memory_limit="2g",
        cpu_limit=2.0
    ),
    Technology.STREAMLIT: ContainerConfig(
        image="python:3.11-slim",
        build_command="pip install streamlit pandas numpy matplotlib",
        run_command="streamlit run app.py --server.address=0.0.0.0 --server.port=8501",
        port=8501,
        memory_limit="1g"
    ),

    # ==================== BLOCKCHAIN ====================
    Technology.BLOCKCHAIN: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install",
        run_command="npx hardhat node",  # Local Ethereum node
        port=8545,
        memory_limit="1g"
    ),

    # ==================== DATABASES (with Web UI) ====================
    Technology.POSTGRESQL: ContainerConfig(
        image="dpage/pgadmin4:latest",
        build_command=None,
        run_command=None,  # pgAdmin runs automatically
        port=80,  # pgAdmin web UI
        memory_limit="512m"
    ),
    Technology.MONGODB: ContainerConfig(
        image="mongo-express:latest",
        build_command=None,
        run_command=None,  # Mongo Express runs automatically
        port=8081,  # Mongo Express web UI
        memory_limit="256m"
    ),
    Technology.MYSQL: ContainerConfig(
        image="phpmyadmin/phpmyadmin:latest",
        build_command=None,
        run_command=None,  # phpMyAdmin runs automatically
        port=80,  # phpMyAdmin web UI
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
        files = []

        # Check if we're using remote Docker (files are on EC2, not local ECS)
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        if sandbox_docker_host and self.docker_client:
            # Remote mode: use Docker to list files on EC2
            try:
                logger.info(f"[ContainerExecutor] Remote mode: listing files via Docker on {project_path}")
                result = self.docker_client.containers.run(
                    "alpine:latest",
                    f"ls -1 {project_path}",
                    remove=True,
                    volumes={project_path: {"bind": project_path, "mode": "ro"}}
                )
                files = result.decode('utf-8').strip().split('\n') if result else []
                logger.info(f"[ContainerExecutor] Found {len(files)} files: {files[:5]}")
            except Exception as e:
                logger.warning(f"[ContainerExecutor] Failed to list remote files: {e}")
                # Default to Node.js for most generated projects
                return Technology.NODEJS
        else:
            # Local mode: use os.listdir
            files = os.listdir(project_path) if os.path.exists(project_path) else []

        # Node.js detection - check for Vite first
        if "package.json" in files:
            # Check for Vite config files
            vite_configs = ["vite.config.js", "vite.config.ts", "vite.config.mjs", "vite.config.cjs"]
            if any(vf in files for vf in vite_configs):
                logger.info(f"[ContainerExecutor] Detected Vite project (config file found)")
                return Technology.NODEJS_VITE

            # Also check package.json for vite dependency
            try:
                import json
                pkg_path = os.path.join(project_path, "package.json")
                if os.path.exists(pkg_path):
                    with open(pkg_path, 'r') as f:
                        pkg = json.load(f)
                        deps = pkg.get("dependencies", {})
                        dev_deps = pkg.get("devDependencies", {})
                        if "vite" in deps or "vite" in dev_deps:
                            logger.info(f"[ContainerExecutor] Detected Vite project (package.json)")
                            return Technology.NODEJS_VITE
            except Exception as e:
                logger.warning(f"[ContainerExecutor] Error reading package.json: {e}")

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
        Create or reuse a container for project execution.

        Optimization: Reuses existing container if available, avoiding recreation overhead.

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

        # ===== OPTIMIZATION: Try to reuse existing container =====
        existing_container = await self._get_existing_container(project_id)
        if existing_container:
            reused, message, port = await self._reuse_container(existing_container, project_id, user_id)
            if reused:
                return True, message, port
            # If reuse failed, continue to create new container
            logger.info(f"[ContainerExecutor] Container reuse failed, creating new: {message}")

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

            # Traefik routing labels for preview gateway
            # Architecture: Browser → /api/v1/preview/{project_id}/ → Backend → Traefik → Container
            #
            # Flow:
            # 1. Vite generates: <script src="/api/v1/preview/{project_id}/src/main.tsx">
            # 2. Browser requests: /api/v1/preview/{project_id}/src/main.tsx
            # 3. CloudFront routes /api/* → ALB → ECS backend preview_proxy.py
            # 4. Backend proxies to Traefik: /api/v1/preview/{project_id}/src/main.tsx (FULL path)
            # 5. Traefik matches PathPrefix and forwards WITHOUT stripping
            # 6. Vite with --base=/api/v1/preview/{project_id}/ matches and serves the file

            # Build run command - Vite needs --base for correct asset URL generation AND request matching
            run_command = config.run_command
            if technology == Technology.NODEJS_VITE:
                # Use full path so Vite matches incoming requests correctly
                full_base = f"/api/v1/preview/{project_id}/"
                run_command = f"npm run dev -- --host 0.0.0.0 --no-open --base={full_base}"
                logger.info(f"[ContainerExecutor] Using Vite with base path: {full_base}")

            # Traefik routes /api/v1/preview/{project_id}/... to container
            # NO stripPrefix - Vite expects the full path to match its --base
            full_prefix = f"/api/v1/preview/{project_id}"
            traefik_labels = {
                "traefik.enable": "true",
                # Route by full path prefix
                f"traefik.http.routers.{project_id[:12]}.rule": f"PathPrefix(`{full_prefix}`)",
                f"traefik.http.routers.{project_id[:12]}.entrypoints": "web",
                # Service port (container's internal port)
                f"traefik.http.services.{project_id[:12]}.loadbalancer.server.port": str(config.port),
                # NO stripPrefix middleware - Vite handles the full path with --base
            }

            logger.info(f"[ContainerExecutor] Traefik routing {full_prefix}/ → container (no strip)")

            # Merge with basic labels
            all_labels = {
                "bharatbuild": "true",
                "project_id": project_id,
                "user_id": user_id,
                "technology": technology.value,
                **traefik_labels
            }

            # Create container - NO port mapping needed! Traefik handles routing via Docker network
            container = self.docker_client.containers.run(
                image=config.image,
                name=container_name,
                detach=True,
                working_dir="/app",
                volumes={
                    project_path: {"bind": "/app", "mode": "rw"}
                },
                # NO ports parameter - Traefik routes via Docker internal IPs
                network="bharatbuild-sandbox",  # Must be on same network as Traefik
                mem_limit=config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(config.cpu_limit * 100000),
                environment={
                    "NODE_ENV": "development",
                    "JAVA_OPTS": "-Xmx512m",
                    "PYTHONUNBUFFERED": "1"
                },
                command=f"sh -c '{config.build_command} && {run_command}'" if config.build_command else run_command,
                labels=all_labels
            )

            # Track container (no host_port - routing via Traefik gateway)
            self.active_containers[project_id] = {
                "container_id": container.id,
                "container_name": container_name,
                "user_id": user_id,
                "technology": technology.value,
                "internal_port": config.port,  # Container's internal port (5173, 3000, etc.)
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(seconds=config.timeout_seconds)
            }

            logger.info(f"[ContainerExecutor] Container {container_name} started (internal port: {config.port})")

            # Return internal_port instead of host_port - routing via Traefik gateway
            return True, f"Container started successfully", config.port

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
                "url": _get_preview_url(container_info['port'], project_id)  # Pass project_id for production URL
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

    async def _get_existing_container(self, project_id: str):
        """
        Find an existing container for this project.

        Returns:
            Container object if found, None otherwise
        """
        if not self.docker_client:
            return None

        try:
            # Find containers with this project_id label
            containers = self.docker_client.containers.list(
                all=True,  # Include stopped containers
                filters={"label": f"project_id={project_id}"}
            )

            if containers:
                # Return the first (should be only one per project)
                return containers[0]
            return None

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Error finding existing container: {e}")
            return None

    async def _reuse_container(self, container, project_id: str, user_id: str) -> Tuple[bool, str, Optional[int]]:
        """
        Attempt to reuse an existing container.

        - If running: Just update tracking and return success
        - If stopped: Start it and return success
        - If unhealthy/error: Return False to trigger new container creation

        Returns:
            Tuple of (success, message, port)
        """
        try:
            container.reload()  # Refresh container state
            status = container.status
            container_name = container.name

            logger.info(f"[ContainerExecutor] Found existing container {container_name} in state: {status}")

            # Extract port from container labels or inspect
            port = None
            try:
                # Try to get port from container's network settings
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        port = int(host_bindings[0]['HostPort'])
                        break

                # If no port mapping (Traefik mode), use a tracking port
                if port is None:
                    # Check if we have it tracked
                    if project_id in self.active_containers:
                        port = self.active_containers[project_id].get("port", 3000)
                    else:
                        port = self._find_available_port()
            except Exception:
                port = 3000  # Default fallback

            if status == "running":
                # Container is already running - just update tracking
                logger.info(f"[ContainerExecutor] Reusing running container {container_name} for {project_id}")

                # Update active_containers tracking
                self.active_containers[project_id] = {
                    "container_id": container.id,
                    "container_name": container_name,
                    "user_id": user_id,
                    "port": port,
                    "technology": container.labels.get("technology", "unknown"),
                    "created_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(hours=24),
                    "reused": True
                }

                return True, f"Reused existing container (already running)", port

            elif status in ["exited", "created", "paused"]:
                # Container exists but stopped - start it
                logger.info(f"[ContainerExecutor] Starting stopped container {container_name} for {project_id}")

                if status == "paused":
                    container.unpause()
                else:
                    container.start()

                # Wait briefly for container to be ready
                await asyncio.sleep(1)
                container.reload()

                if container.status == "running":
                    # Update tracking
                    self.active_containers[project_id] = {
                        "container_id": container.id,
                        "container_name": container_name,
                        "user_id": user_id,
                        "port": port,
                        "technology": container.labels.get("technology", "unknown"),
                        "created_at": datetime.utcnow(),
                        "expires_at": datetime.utcnow() + timedelta(hours=24),
                        "reused": True
                    }

                    return True, f"Reused existing container (restarted)", port
                else:
                    # Failed to start - remove and let caller create new
                    logger.warning(f"[ContainerExecutor] Failed to restart container {container_name}")
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass
                    return False, "Container failed to restart", None
            else:
                # Container in bad state (dead, removing, etc.) - remove it
                logger.warning(f"[ContainerExecutor] Container {container_name} in bad state: {status}")
                try:
                    container.remove(force=True)
                except Exception:
                    pass
                if project_id in self.active_containers:
                    del self.active_containers[project_id]
                return False, f"Container in bad state: {status}", None

        except Exception as e:
            logger.error(f"[ContainerExecutor] Error reusing container: {e}")
            return False, str(e), None

    async def _cleanup_project_container(self, project_id: str):
        """
        Clean up any existing container for a specific project.
        Called when container reuse fails and we need a fresh container.
        """
        if not self.docker_client:
            return

        try:
            # Find containers with this project_id label
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": f"project_id={project_id}"}
            )

            for container in containers:
                try:
                    logger.info(f"[ContainerExecutor] Removing existing container {container.name} for project {project_id}")
                    if container.status == "running":
                        container.stop(timeout=5)
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"[ContainerExecutor] Failed to remove container {container.name}: {e}")

            # Also remove from active_containers dict
            if project_id in self.active_containers:
                del self.active_containers[project_id]

        except Exception as e:
            logger.error(f"[ContainerExecutor] Error cleaning up project container: {e}")

    async def _cleanup_loop(self):
        """Background task to cleanup expired containers"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                # 1. Clean up in-memory tracked containers
                now = datetime.utcnow()
                expired = [
                    project_id for project_id, info in self.active_containers.items()
                    if info["expires_at"] < now
                ]

                for project_id in expired:
                    logger.info(f"[ContainerExecutor] Auto-cleanup expired container: {project_id}")
                    await self.stop_container(project_id)

                # 2. Clean up orphaned containers directly from Docker
                # This handles containers that exist but aren't tracked in memory
                # (e.g., after backend restart)
                await self._cleanup_orphaned_containers()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ContainerExecutor] Cleanup error: {e}")

    async def _cleanup_orphaned_containers(self):
        """
        Clean up bharatbuild containers that are older than the idle timeout.
        This queries Docker directly, handling containers that survived backend restarts.
        Uses centralized CONTAINER_IDLE_TIMEOUT_SECONDS from settings.
        """
        if not self.docker_client:
            return

        try:
            from app.core.config import settings

            # Find all bharatbuild containers
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": "bharatbuild=true"}
            )

            now = datetime.utcnow()
            # Use centralized timeout setting
            max_age_minutes = settings.CONTAINER_IDLE_TIMEOUT_SECONDS / 60

            for container in containers:
                try:
                    # Get container creation time
                    created_str = container.attrs.get("Created", "")
                    if created_str:
                        # Parse Docker timestamp (e.g., "2025-12-22T09:00:00.000000000Z")
                        created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00").split(".")[0])
                        created_at = created_at.replace(tzinfo=None)  # Make naive for comparison
                        age_minutes = (now - created_at).total_seconds() / 60

                        if age_minutes > max_age_minutes:
                            project_id = container.labels.get("project_id", "unknown")
                            logger.info(f"[ContainerExecutor] Removing orphaned container {container.name} "
                                       f"(project: {project_id}, age: {age_minutes:.1f} min)")

                            if container.status == "running":
                                container.stop(timeout=5)
                            container.remove(force=True)

                            # Also remove from active_containers if tracked
                            if project_id in self.active_containers:
                                del self.active_containers[project_id]

                except Exception as e:
                    logger.warning(f"[ContainerExecutor] Failed to cleanup container {container.name}: {e}")

        except Exception as e:
            logger.error(f"[ContainerExecutor] Error in orphaned container cleanup: {e}")

    async def cleanup_all(self):
        """Stop all containers (for shutdown)"""
        for project_id in list(self.active_containers.keys()):
            await self.stop_container(project_id)

        if self._cleanup_task:
            self._cleanup_task.cancel()

    async def run_project(
        self,
        project_id: str,
        project_path: str,
        user_id: Optional[str] = None
    ):
        """
        Run a project in a container and stream output.

        This is the main entry point for remote Docker execution.
        Handles container creation, log streaming, and server detection.
        """
        import re
        import asyncio

        user_id = user_id or "anonymous"

        # Ensure Docker client is initialized
        if not self.docker_client:
            yield f"🔧 Initializing Docker client...\n"
            initialized = await self.initialize()
            if not initialized or not self.docker_client:
                yield f"ERROR: Docker client not available\n"
                return

        yield f"🔍 Detecting project technology...\n"

        # Detect technology
        technology = self.detect_technology(project_path)
        if technology == Technology.UNKNOWN:
            # Default to Node.js for unknown projects
            technology = Technology.NODEJS
            yield f"  ⚠️ Could not detect technology, defaulting to Node.js\n"
        else:
            yield f"  📦 Detected: {technology.value}\n"

        config = TECHNOLOGY_CONFIGS.get(technology)
        if not config:
            yield f"ERROR: Unsupported technology: {technology.value}\n"
            return

        yield f"🐳 Preparing container...\n"
        yield f"  📁 Project path: {project_path}\n"
        yield f"  🔌 Container port: {config.port}\n"

        # Create or reuse container
        success, message, host_port = await self.create_container(
            project_id=project_id,
            user_id=user_id,
            project_path=project_path,
            technology=technology
        )

        if not success:
            yield f"ERROR: {message}\n"
            return

        # Check if container was reused (message contains "Reused")
        if "Reused" in message:
            yield f"♻️ {message}\n"
        else:
            yield f"✅ Container created on port {host_port}\n"
        yield f"📜 Streaming container logs...\n\n"

        # Stream container logs
        container_info = self.active_containers.get(project_id)
        if not container_info:
            yield f"ERROR: Container not found\n"
            return

        try:
            container = self.docker_client.containers.get(container_info["container_id"])

            # Generate preview URL upfront
            preview_url = _get_preview_url(host_port, project_id)
            logger.info(f"[ContainerExecutor] Preview URL generated: {preview_url}")
            yield f"📍 Preview URL: {preview_url}\n\n"

            # Stream logs using async-compatible approach
            # The Docker SDK's logs() is synchronous, so we use a queue-based async pattern
            server_started = False
            start_patterns = [
                r"Local:\s*http://\S+:(\d+)",
                r"listening on port (\d+)",
                r"Server running at http://\S+:(\d+)",
                r"Started.*on port (\d+)",
                r"ready.*http://\S+:(\d+)",
                r"VITE.*Local:\s*http://\S+:(\d+)",
                r"ready in \d+",  # Vite ready message
                r"compiled successfully",  # Webpack
            ]

            # Use asyncio queue for thread-safe async log streaming
            log_queue: asyncio.Queue = asyncio.Queue()

            # Get the current event loop BEFORE starting thread
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()

            def stream_logs_sync():
                """Synchronous log streaming in separate thread"""
                try:
                    for log in container.logs(stream=True, follow=True, timestamps=False):
                        try:
                            line = log.decode('utf-8', errors='ignore').strip()
                            if line:
                                # Put log line in queue (thread-safe)
                                asyncio.run_coroutine_threadsafe(
                                    log_queue.put(line),
                                    loop
                                )
                        except Exception as decode_err:
                            logger.debug(f"[ContainerExecutor] Log decode error: {decode_err}")
                            continue
                except Exception as e:
                    logger.error(f"[ContainerExecutor] Log streaming thread error: {e}")
                finally:
                    # Signal completion
                    asyncio.run_coroutine_threadsafe(
                        log_queue.put(None),  # Sentinel value
                        loop
                    )

            # Start log streaming in background thread
            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            log_future = executor.submit(stream_logs_sync)

            # Process logs from queue asynchronously
            timeout_seconds = 120  # 2 minute timeout for server to start
            start_time = loop.time()

            while True:
                try:
                    # Wait for log with timeout
                    line = await asyncio.wait_for(log_queue.get(), timeout=5.0)

                    if line is None:
                        # Stream ended
                        break

                    yield f"{line}\n"

                    # Check for server start patterns
                    if not server_started:
                        for pattern in start_patterns:
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                server_started = True
                                logger.info(f"[ContainerExecutor] Server started! Pattern matched: {pattern}")
                                yield f"\n{'='*50}\n"
                                yield f"🚀 SERVER STARTED!\n"
                                yield f"Preview URL: {preview_url}\n"
                                yield f"{'='*50}\n\n"
                                # Emit both markers for compatibility
                                yield f"__SERVER_STARTED__:{preview_url}\n"
                                yield f"_PREVIEW_URL_:{preview_url}\n"
                                break

                except asyncio.TimeoutError:
                    # No log for 5 seconds - check if we've timed out or server started
                    elapsed = loop.time() - start_time
                    if elapsed > timeout_seconds and not server_started:
                        logger.warning(f"[ContainerExecutor] Timeout waiting for server start")
                        yield f"\n⚠️ Timeout waiting for server. Container may still be starting...\n"
                        break
                    # Send keepalive
                    yield f"  ⏳ Waiting for server... ({int(elapsed)}s)\n"
                    continue

            # Cleanup
            executor.shutdown(wait=False)

            # If we exited the loop without detecting server start, still emit the URL
            if not server_started and preview_url:
                logger.warning(f"[ContainerExecutor] Server start not detected, emitting URL anyway")
                yield f"\n📍 Container running - Preview may be available at: {preview_url}\n"
                yield f"_PREVIEW_URL_:{preview_url}\n"

        except Exception as e:
            logger.error(f"[ContainerExecutor] Error streaming logs: {e}")
            yield f"ERROR: Failed to stream logs: {e}\n"


# Global instance
container_executor = ContainerExecutor()
