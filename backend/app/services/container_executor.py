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
import socket
import subprocess
import threading
import docker
from docker.errors import NotFound, APIError
from typing import Optional, Dict, Any, Tuple, AsyncGenerator, List
from dataclasses import dataclass
from enum import Enum
import uuid
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

# Preview Gap #1: Thread lock for atomic port allocation
_port_allocation_lock = threading.Lock()

from app.core.logging_config import logger
from app.services.execution_context import (
    ExecutionContext,
    ExecutionState,
    RuntimeType,
    create_execution_context,
    get_execution_context,
    remove_execution_context,
)
from app.modules.agents.docker_infra_fixer_agent import docker_infra_fixer, DockerInfraFixerAgent
from app.modules.agents.production_fixer_agent import production_fixer_agent
from app.modules.agents.base_agent import AgentContext
from app.services.project_sanitizer import sanitize_project_file
from app.services.technology_validator import technology_validator

# =============================================================================
# PREVIEW URL - Use centralized function from app.core.preview_url
# =============================================================================
# IMPORTANT: All preview URL generation goes through this single function
# to ensure consistency between frontend and backend.

from app.core.preview_url import get_preview_url as _get_preview_url_impl, check_preview_health


def _get_preview_url(port: int, project_id: str = None) -> str:
    """
    Generate preview URL - delegates to centralized function.

    See app.core.preview_url for implementation details.
    """
    return _get_preview_url_impl(port, project_id or "")


def _get_sandbox_base() -> str:
    """
    Get sandbox base path from settings (supports EFS mount).

    Returns settings.SANDBOX_PATH for Docker volume mounts.
    This ensures EFS compatibility when SANDBOX_PATH=/efs/sandbox/workspace
    """
    from app.core.config import settings
    return settings.SANDBOX_PATH


# =============================================================================
# Dynamic IP Discovery for Spot/ASG instances
# =============================================================================
# Cache for SSM parameter values (refresh every 60 seconds)
_ssm_cache: Dict[str, Tuple[str, float]] = {}
_SSM_CACHE_TTL = 60  # seconds


def _get_sandbox_docker_host() -> str:
    """
    Get sandbox Docker host URL with dynamic IP discovery support.

    Priority order:
    1. Static env var SANDBOX_DOCKER_HOST (if set and not empty)
    2. SSM Parameter Store (always tries if static not set)
    3. DOCKER_HOST env var as final fallback

    This supports Spot instances with ASG where the IP changes on replacement.

    Returns:
        Docker host URL (e.g., "tcp://10.0.1.50:2375")
    """
    import time

    # 1. Try static env var first
    static_host = os.environ.get("SANDBOX_DOCKER_HOST", "")
    if static_host:
        return static_host

    # 2. Try SSM Parameter Store (always, not just when flag is set)
    ssm_param = os.environ.get("SANDBOX_SSM_PARAM_DOCKER_HOST", "/bharatbuild/sandbox/docker-host")

    # Check cache first
    if ssm_param in _ssm_cache:
        cached_value, cached_time = _ssm_cache[ssm_param]
        if time.time() - cached_time < _SSM_CACHE_TTL:
            return cached_value

    # Fetch from SSM
    try:
        import boto3
        ssm = boto3.client('ssm', region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        response = ssm.get_parameter(Name=ssm_param)
        value = response['Parameter']['Value']

        # Cache the result
        _ssm_cache[ssm_param] = (value, time.time())
        logger.info(f"[ContainerExecutor] Docker host from SSM: {value}")
        return value
    except Exception as e:
        logger.warning(f"[ContainerExecutor] Failed to get Docker host from SSM: {e}")

    # 3. Final fallback to DOCKER_HOST
    return os.environ.get("DOCKER_HOST", "")


def _get_sandbox_instance_id() -> str:
    """
    Get sandbox EC2 instance ID with dynamic discovery support.

    Priority order:
    1. Static env var SANDBOX_EC2_INSTANCE_ID (if set and not empty)
    2. SSM Parameter Store (always tries if static not set)

    This supports Spot instances with ASG where the instance ID changes on replacement.

    Returns:
        EC2 instance ID (e.g., "i-0abc123def456")
    """
    import time

    # 1. Try static env var first
    static_id = os.environ.get("SANDBOX_EC2_INSTANCE_ID", "")
    if static_id:
        return static_id

    # 2. Try SSM Parameter Store (always, not just when flag is set)
    ssm_param = os.environ.get("SANDBOX_SSM_PARAM_INSTANCE_ID", "/bharatbuild/sandbox/instance-id")

    # Check cache first
    if ssm_param in _ssm_cache:
        cached_value, cached_time = _ssm_cache[ssm_param]
        if time.time() - cached_time < _SSM_CACHE_TTL:
            return cached_value

    # Fetch from SSM
    try:
        import boto3
        ssm = boto3.client('ssm', region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        response = ssm.get_parameter(Name=ssm_param)
        value = response['Parameter']['Value']

        # Cache the result
        _ssm_cache[ssm_param] = (value, time.time())
        logger.info(f"[ContainerExecutor] Instance ID from SSM: {value}")
        return value
    except Exception as e:
        logger.warning(f"[ContainerExecutor] Failed to get instance ID from SSM: {e}")

    # No fallback - return empty string
    return ""


# =============================================================================
# SYSTEM PORTS - Blocked from host port allocation
# =============================================================================
# These ports are reserved for system services and MUST be remapped
# to high ports (35000+) to avoid conflicts.
SYSTEM_PORTS = {
    80,      # HTTP (nginx, apache)
    443,     # HTTPS (nginx, apache)
    8080,    # Common web server (nginx, jenkins, tomcat)
    3000,    # Common dev server (node, react, next.js)
    5432,    # PostgreSQL
    3306,    # MySQL
    6379,    # Redis
    27017,   # MongoDB
    22,      # SSH
    21,      # FTP
    25,      # SMTP
    53,      # DNS
}


class Technology(Enum):
    """Supported technology stacks - Universal Preview Architecture"""
    # Frontend Frameworks
    NODEJS = "nodejs"
    NODEJS_VITE = "nodejs_vite"  # Vite-based projects (React, Vue, Svelte with Vite)
    REACT_NATIVE = "react_native"  # React Native (Metro bundler - web preview)
    FLUTTER = "flutter"  # Flutter (web preview)
    ANGULAR = "angular"

    # Backend Frameworks
    JAVA = "java"  # Spring Boot (Maven)
    JAVA_GRADLE = "java_gradle"  # Spring Boot (Gradle)
    PYTHON = "python"  # FastAPI, Django, Flask
    PYTHON_ML = "python_ml"  # AI/ML/DL with Jupyter
    GO = "go"
    RUST = "rust"  # Rust (Actix, Rocket, Axum)
    DOTNET = "dotnet"  # ASP.NET Core

    # Blockchain
    BLOCKCHAIN = "blockchain"  # Solidity, Hardhat, Truffle
    BLOCKCHAIN_RUST = "blockchain_rust"  # Solana (Anchor), Substrate

    # Databases (with web UI)
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    MYSQL = "mysql"

    # Specialized
    JUPYTER = "jupyter"  # Jupyter notebooks for AI/ML/DL
    STREAMLIT = "streamlit"  # Streamlit for ML dashboards

    # Full-Stack (Multi-Container)
    FULLSTACK = "fullstack"  # Frontend + Backend in separate containers

    UNKNOWN = "unknown"


# Database Technology Enum
class DatabaseType(Enum):
    """Supported database types for full-stack projects"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"
    NONE = "none"


# Gap #15: Container State Tracking Enum
class ContainerState(Enum):
    """Container lifecycle states for tracking"""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERRORED = "errored"
    UNKNOWN = "unknown"


# Database Container Configurations
@dataclass
class DatabaseConfig:
    """Configuration for database containers"""
    db_type: DatabaseType
    image: str
    port: int
    env_vars: Dict[str, str]
    health_check_cmd: List[str]
    connection_string_template: str


DATABASE_CONFIGS: Dict[DatabaseType, DatabaseConfig] = {
    DatabaseType.POSTGRESQL: DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        image="postgres:15-alpine",
        port=5432,
        env_vars={
            "POSTGRES_USER": "bharatbuild",
            "POSTGRES_PASSWORD": "bharatbuild123",
            "POSTGRES_DB": "app_db"
        },
        health_check_cmd=["pg_isready", "-U", "bharatbuild"],
        connection_string_template="postgresql://bharatbuild:bharatbuild123@{host}:5432/app_db"
    ),
    DatabaseType.MYSQL: DatabaseConfig(
        db_type=DatabaseType.MYSQL,
        image="mysql:8.0",
        port=3306,
        env_vars={
            "MYSQL_ROOT_PASSWORD": "bharatbuild123",
            "MYSQL_DATABASE": "app_db",
            "MYSQL_USER": "bharatbuild",
            "MYSQL_PASSWORD": "bharatbuild123"
        },
        health_check_cmd=["mysqladmin", "ping", "-h", "localhost", "-ubharatbuild", "-pbharatbuild123"],
        connection_string_template="mysql://bharatbuild:bharatbuild123@{host}:3306/app_db"
    ),
    DatabaseType.MONGODB: DatabaseConfig(
        db_type=DatabaseType.MONGODB,
        image="mongo:7.0",
        port=27017,
        env_vars={
            "MONGO_INITDB_ROOT_USERNAME": "bharatbuild",
            "MONGO_INITDB_ROOT_PASSWORD": "bharatbuild123",
            "MONGO_INITDB_DATABASE": "app_db"
        },
        health_check_cmd=["mongosh", "--eval", "db.adminCommand('ping')"],
        connection_string_template="mongodb://bharatbuild:bharatbuild123@{host}:27017/app_db?authSource=admin"
    ),
    DatabaseType.REDIS: DatabaseConfig(
        db_type=DatabaseType.REDIS,
        image="redis:7-alpine",
        port=6379,
        env_vars={},
        health_check_cmd=["redis-cli", "ping"],
        connection_string_template="redis://{host}:6379"
    ),
}


# Full-Stack Project Configuration
@dataclass
class FullStackConfig:
    """Configuration for full-stack projects with frontend + backend + database"""
    frontend_tech: Technology
    backend_tech: Technology
    frontend_port: int = 3000
    backend_port: int = 8080
    frontend_path: str = "frontend"
    backend_path: str = "backend"
    # Database support (NEW)
    database_type: DatabaseType = DatabaseType.NONE
    database_config: Optional[DatabaseConfig] = None


# Backend technology detection patterns
BACKEND_PATTERNS = {
    Technology.JAVA: ["pom.xml", "build.gradle", "build.gradle.kts"],
    Technology.PYTHON: ["requirements.txt", "pyproject.toml", "main.py", "app.py"],
    Technology.GO: ["go.mod", "main.go"],
    Technology.DOTNET: ["*.csproj", "*.fsproj"],
}

# Frontend technology detection patterns
FRONTEND_PATTERNS = {
    Technology.NODEJS_VITE: ["vite.config.ts", "vite.config.js", "vite.config.mjs"],
    Technology.NODEJS: ["package.json"],
    Technology.ANGULAR: ["angular.json"],
}

# Database detection patterns (file content patterns)
DATABASE_DETECTION_PATTERNS = {
    DatabaseType.POSTGRESQL: [
        "postgresql", "postgres", "org.postgresql", "psycopg2", "pg8000",
        "spring.datasource.url=jdbc:postgresql", "DATABASE_URL.*postgres"
    ],
    DatabaseType.MYSQL: [
        "mysql", "mariadb", "com.mysql", "pymysql", "mysql-connector",
        "spring.datasource.url=jdbc:mysql"
    ],
    DatabaseType.MONGODB: [
        "mongodb", "mongo", "org.mongodb", "pymongo", "mongoose",
        "spring.data.mongodb"
    ],
    DatabaseType.REDIS: [
        "redis", "spring.redis", "redis-py", "ioredis"
    ],
}


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


# MEDIUM #8: Default memory limit for containers - configurable via env
import os as _os
DEFAULT_CONTAINER_MEMORY = _os.environ.get("CONTAINER_MEMORY_LIMIT", "768m")

# npm cache path - shared across all containers for faster installs
NPM_CACHE_PATH = "/tmp/sandbox/npm-cache"

# Pre-built images for each technology - Universal Preview Architecture
TECHNOLOGY_CONFIGS: Dict[Technology, ContainerConfig] = {
    # ==================== FRONTEND FRAMEWORKS ====================
    Technology.NODEJS: ContainerConfig(
        image="node:20-alpine",
        # Use npm (pre-installed) - simpler and works with generated package-lock.json
        build_command="npm install --legacy-peer-deps",
        # Kill any existing node/vite processes before starting to prevent duplicates
        run_command="pkill -f 'node|vite' 2>/dev/null || true; npm run dev -- --host 0.0.0.0 --no-open",
        port=3000,
        memory_limit=DEFAULT_CONTAINER_MEMORY  # MEDIUM #8: Increased from 512m
    ),
    Technology.NODEJS_VITE: ContainerConfig(
        image="node:20-alpine",
        # Use npm (pre-installed) - simpler and works with generated package-lock.json
        # IMPORTANT: Run "npx vite optimize" after install to pre-bundle dependencies
        # This creates .vite/deps BEFORE dev server starts, preventing 504 timeouts on first request
        build_command="npm install --legacy-peer-deps && npx vite optimize",
        run_command="pkill -f vite 2>/dev/null || true; npm run dev -- --host 0.0.0.0 --no-open",
        port=3000,  # Vite port (changed from 5173 for consistency)
        memory_limit=DEFAULT_CONTAINER_MEMORY  # MEDIUM #8: Increased from 512m
    ),
    Technology.ANGULAR: ContainerConfig(
        image="node:20-alpine",
        # Use npm (pre-installed) - simpler and works with generated package-lock.json
        build_command="npm install --legacy-peer-deps",
        run_command="npm run start -- --host 0.0.0.0 --port 4200 --disable-host-check",
        port=4200,
        memory_limit=DEFAULT_CONTAINER_MEMORY  # MEDIUM #8: Increased from 512m
    ),
    Technology.REACT_NATIVE: ContainerConfig(
        image="node:20-alpine",
        # Use npm (pre-installed) - simpler and works with generated package-lock.json
        build_command="npm install --legacy-peer-deps && npx expo export:web",
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
        build_command="mvn clean install -DskipTests -Dcheckstyle.skip=true",
        run_command="mvn spring-boot:run -Dcheckstyle.skip=true",
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
    Technology.RUST: ContainerConfig(
        image="rust:1.75-slim",
        build_command="cargo build --release",
        run_command="./target/release/$(ls target/release/ | grep -v '\\.' | head -1)",
        port=8080,
        memory_limit="1g",
        cpu_limit=1.0
    ),
    Technology.JAVA_GRADLE: ContainerConfig(
        image="gradle:8.5-jdk17",
        build_command="gradle build -x test --no-daemon",
        run_command="java -jar build/libs/*.jar",
        port=8080,
        memory_limit="1g",
        cpu_limit=1.0
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
        # Use npm (pre-installed) - simpler and works with generated package-lock.json
        build_command="npm install --legacy-peer-deps",
        run_command="npx hardhat node",  # Local Ethereum node
        port=8545,
        memory_limit="1g"
    ),
    Technology.BLOCKCHAIN_RUST: ContainerConfig(
        image="rust:1.75-slim",
        # Solana/Anchor blockchain development
        build_command="cargo build-bpf || cargo build --release",
        run_command="solana-test-validator",
        port=8899,  # Solana RPC port
        memory_limit="2g",
        cpu_limit=2.0
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

    # Gap #15: Container state tracking methods
    def _update_container_state(self, project_id: str, state: ContainerState, error: str = None):
        """Update container state with timestamp for tracking"""
        if project_id in self.active_containers:
            self.active_containers[project_id]["state"] = state.value
            self.active_containers[project_id]["state_updated_at"] = datetime.utcnow()
            if error:
                self.active_containers[project_id]["last_error"] = error
            logger.debug(f"[ContainerExecutor] Container {project_id} state: {state.value}")

    def get_container_state(self, project_id: str) -> Dict[str, Any]:
        """Get container state info for debugging"""
        if project_id in self.active_containers:
            info = self.active_containers[project_id]
            return {
                "state": info.get("state", "unknown"),
                "state_updated_at": info.get("state_updated_at"),
                "last_error": info.get("last_error"),
                "created_at": info.get("created_at"),
                "host_port": info.get("host_port"),
            }
        return {"state": "not_found"}

    async def initialize(self):
        """Initialize Docker client"""
        # High #7: Docker API timeout for remote mode (prevents indefinite hangs)
        DOCKER_API_TIMEOUT = 30  # 30 seconds timeout for Docker API calls

        try:
            # First, try sandbox Docker host (supports dynamic IP discovery for Spot/ASG)
            sandbox_docker_host = _get_sandbox_docker_host()
            # Try TLS-enabled docker client helper first (supports Secrets Manager certs)
            try:
                from app.services.docker_client_helper import get_docker_client
                self.docker_client = get_docker_client(timeout=DOCKER_API_TIMEOUT)
                if self.docker_client:
                    logger.info(f"[ContainerExecutor] Docker client initialized via docker_client_helper (TLS-enabled)")
            except Exception as helper_err:
                logger.warning(f"[ContainerExecutor] docker_client_helper failed: {helper_err}")
                self.docker_client = None

            # Fallback to direct connection if helper failed
            if not self.docker_client and sandbox_docker_host:
                try:
                    self.docker_client = docker.DockerClient(
                        base_url=sandbox_docker_host,
                        timeout=DOCKER_API_TIMEOUT  # High #7: Add timeout
                    )
                    self.docker_client.ping()
                    logger.info(f"[ContainerExecutor] Docker client initialized via sandbox host: {sandbox_docker_host} (timeout={DOCKER_API_TIMEOUT}s)")
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
                        self.docker_client = docker.DockerClient(
                            base_url=socket_path,
                            timeout=DOCKER_API_TIMEOUT  # High #7: Add timeout
                        )
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

    # =========================================================================
    # PRE-RUN VALIDATION - Ensures workspace is ready before container starts
    # =========================================================================

    async def validate_workspace(
        self,
        project_path: str,
        technology: "Technology"
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate that workspace has all required files before running.

        GUARANTEES:
        - Critical files (package.json, etc.) exist
        - Workspace directory is accessible
        - Required dependencies file exists

        Args:
            project_path: Path to project workspace
            technology: Detected technology type

        Returns:
            Tuple of (is_valid, message, missing_files)
        """
        path = Path(project_path)
        missing = []

        # =====================================================================
        # CRITICAL: Remote Docker mode - check filesystem on remote EC2 sandbox
        # When SANDBOX_DOCKER_HOST is set, local path.exists() will always fail
        # because files are on the remote sandbox, not local ECS container.
        #
        # NOTE: In remote mode, files are stored in database/S3 and synced at
        # container runtime. Validation failures are NON-BLOCKING (warnings only)
        # because the directory may not exist yet on EC2.
        # =====================================================================
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        if sandbox_docker_host and self.docker_client:
            logger.info(f"[ContainerExecutor] Remote mode: validating workspace via Docker on {project_path}")
            try:
                # Check if directory exists on remote sandbox
                check_result = self.docker_client.containers.run(
                    "alpine:latest",
                    ["-c", f"test -d {project_path} && echo 'EXISTS' || echo 'MISSING'"],
                    entrypoint="/bin/sh",
                    volumes={_get_sandbox_base(): {"bind": _get_sandbox_base(), "mode": "ro"}},
                    remove=True,
                    detach=False
                )
                if b"MISSING" in check_result:
                    # NON-BLOCKING: Files are in storage, will sync at container runtime
                    logger.warning(f"[ContainerExecutor] Remote workspace not found yet (will sync at runtime): {project_path}")
                    return True, "Remote mode: workspace will be created at container runtime", []

                # Check for frontend subdirectory on remote
                frontend_check = self.docker_client.containers.run(
                    "alpine:latest",
                    ["-c", f"test -d {project_path}/frontend && test -f {project_path}/frontend/package.json && echo 'FRONTEND' || echo 'ROOT'"],
                    entrypoint="/bin/sh",
                    volumes={_get_sandbox_base(): {"bind": _get_sandbox_base(), "mode": "ro"}},
                    remove=True,
                    detach=False
                )
                is_frontend_subdir = b"FRONTEND" in frontend_check
                check_path_str = f"{project_path}/frontend" if is_frontend_subdir else project_path

                # Check required files on remote
                required_files = {
                    Technology.NODEJS: ["package.json"],
                    Technology.NODEJS_VITE: ["package.json"],
                    Technology.REACT_NATIVE: ["package.json"],
                    Technology.ANGULAR: ["package.json", "angular.json"],
                    Technology.JAVA: [],
                    Technology.PYTHON: [],
                    Technology.PYTHON_ML: [],
                    Technology.GO: ["go.mod"],
                    Technology.FLUTTER: ["pubspec.yaml"],
                    Technology.DOTNET: [],
                }

                for required_file in required_files.get(technology, []):
                    file_check = self.docker_client.containers.run(
                        "alpine:latest",
                        ["-c", f"test -f {check_path_str}/{required_file} && echo 'EXISTS' || echo 'MISSING'"],
                        entrypoint="/bin/sh",
                        volumes={_get_sandbox_base(): {"bind": _get_sandbox_base(), "mode": "ro"}},
                        remove=True,
                        detach=False
                    )
                    if b"MISSING" in file_check:
                        missing.append(required_file)

                if missing:
                    # NON-BLOCKING: Log warning but continue - files may sync at runtime
                    logger.warning(f"[ContainerExecutor] Missing files on remote (may sync at runtime): {missing}")
                    return True, f"Remote mode: missing files will be synced at runtime", missing

                logger.info(f"[ContainerExecutor] Remote workspace validation passed for {project_path}")
                return True, "Workspace validated successfully on remote sandbox", []

            except Exception as remote_err:
                # NON-BLOCKING: Validation failed but continue anyway
                logger.warning(f"[ContainerExecutor] Remote validation error (continuing): {remote_err}")
                return True, "Remote mode: validation skipped due to error, continuing", []

        # Local filesystem check (non-remote mode)
        # Check if path exists
        if not path.exists():
            return False, f"Workspace path does not exist: {project_path}", ["workspace_directory"]

        # Check if path is directory
        if not path.is_dir():
            return False, f"Workspace path is not a directory: {project_path}", ["workspace_directory"]

        # Check for frontend subdirectory (multi-folder projects)
        frontend_path = path / "frontend"
        is_frontend_subdir = frontend_path.exists() and (frontend_path / "package.json").exists()
        check_path = frontend_path if is_frontend_subdir else path

        # Define required files by technology
        required_files = {
            Technology.NODEJS: ["package.json"],
            Technology.NODEJS_VITE: ["package.json"],
            Technology.REACT_NATIVE: ["package.json"],
            Technology.ANGULAR: ["package.json", "angular.json"],
            Technology.JAVA: [],  # any_of handled below
            Technology.PYTHON: [],  # any_of handled below
            Technology.PYTHON_ML: [],
            Technology.GO: ["go.mod"],
            Technology.FLUTTER: ["pubspec.yaml"],
            Technology.DOTNET: [],  # .csproj or .fsproj
        }

        # Define any_of files (at least one must exist)
        any_of_files = {
            Technology.JAVA: ["pom.xml", "build.gradle", "build.gradle.kts"],
            Technology.PYTHON: ["requirements.txt", "pyproject.toml", "setup.py"],
            Technology.PYTHON_ML: ["requirements.txt", "pyproject.toml", "setup.py"],
            Technology.DOTNET: [],  # Will check for .csproj files
        }

        # Check required files
        for required_file in required_files.get(technology, []):
            file_path = check_path / required_file
            if not file_path.exists():
                missing.append(required_file)

        # Check any_of files
        any_of = any_of_files.get(technology, [])
        if any_of:
            has_any = any((check_path / f).exists() for f in any_of)
            if not has_any:
                missing.append(f"one of: {', '.join(any_of)}")

        # Check for .csproj files for .NET
        if technology == Technology.DOTNET:
            csproj_files = list(check_path.glob("**/*.csproj")) + list(check_path.glob("**/*.fsproj"))
            if not csproj_files:
                missing.append(".csproj or .fsproj file")

        if missing:
            return False, f"Missing critical files: {', '.join(missing)}", missing

        # All validations passed
        logger.info(f"[ContainerExecutor] Workspace validation passed for {project_path}")
        return True, "Workspace validated successfully", []

    async def health_check_container(
        self,
        container,
        timeout: int = 30
    ) -> Tuple[bool, str]:
        """
        Check if container is healthy and ready to run commands.

        CHECKS:
        1. Container is running
        2. Container can execute basic commands
        3. Working directory exists
        4. Node/Python/etc. runtime is available

        Args:
            container: Docker container object
            timeout: Timeout in seconds for health check

        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            # Check 1: Container is running
            container.reload()
            status = container.status
            if status != "running":
                return False, f"Container is not running (status: {status})"

            # Check 2: Can execute basic command
            try:
                result = container.exec_run(
                    cmd=["sh", "-c", "echo 'health_check_ok'"],
                    demux=True,
                    workdir="/app"
                )
                stdout, stderr = result.output
                if result.exit_code != 0:
                    return False, f"Health check command failed: {stderr.decode() if stderr else 'unknown error'}"
                if b"health_check_ok" not in (stdout or b""):
                    return False, "Health check command produced unexpected output"
            except Exception as e:
                return False, f"Failed to execute health check command: {e}"

            # Check 3: Working directory exists
            try:
                result = container.exec_run(
                    cmd=["sh", "-c", "test -d /app && echo 'dir_exists'"],
                    demux=True
                )
                stdout, _ = result.output
                if b"dir_exists" not in (stdout or b""):
                    return False, "Working directory /app does not exist in container"
            except Exception as e:
                return False, f"Failed to check working directory: {e}"

            logger.info(f"[ContainerExecutor] Container health check passed: {container.id[:12]}")
            return True, "Container is healthy"

        except Exception as e:
            logger.error(f"[ContainerExecutor] Container health check failed: {e}")
            return False, f"Health check failed: {str(e)}"

    def is_container_running(self, project_id: str, user_id: str) -> bool:
        """
        Check if a container EXISTS for this project (running OR stopped).

        CRITICAL: This checks for ANY container, not just running ones.
        If a container exists (even if stopped), files are already in its volume,
        so we should skip file restoration to prevent Vite restart loops.

        Checks for multiple container naming patterns:
        - Standard: bharatbuild_{user_id[:8]}_{project_id[:8]}
        - Docker Compose: bharatbuild_{project_id[:8]}-backend, bharatbuild_{project_id[:8]}-frontend

        Returns:
            True if container exists (running or stopped), False otherwise
        """
        if not self.docker_client:
            return False

        try:
            # Check multiple naming patterns
            container_patterns = [
                f"bharatbuild_{user_id[:8]}_{project_id[:8]}",  # Standard pattern
                f"bharatbuild_{project_id[:8]}",  # Docker Compose pattern (prefix)
            ]

            for pattern in container_patterns:
                # IMPORTANT: all=True to check for stopped containers too
                containers = self.docker_client.containers.list(
                    filters={"name": pattern},
                    all=True  # Include stopped containers
                )

                for container in containers:
                    # Container exists (running, exited, paused, etc.)
                    logger.info(f"[ContainerExecutor] Found existing container for {project_id}: {container.name} (status: {container.status})")
                    return True

            return False
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Error checking container status: {e}")
            return False

    def detect_technology(self, project_path: str) -> Technology:
        """
        Detect project technology based on files present.

        Detection priority:
        1. package.json -> Node.js
        2. frontend/package.json -> Multi-folder project (frontend subdir)
        3. pom.xml or build.gradle -> Java
        4. requirements.txt or pyproject.toml -> Python
        5. go.mod -> Go
        """
        files = []
        path_str = str(project_path)

        # Check if we're using remote Docker (files are on EC2, not local ECS)
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        if sandbox_docker_host and self.docker_client:
            # Remote mode: use Docker to list files on EC2
            try:
                logger.info(f"[ContainerExecutor] Remote mode: listing files via Docker on {path_str}")

                # Use shell script to handle errors gracefully and list files
                # Also check parent directory to debug path issues
                list_script = f"""
                    echo "=== Checking path: {path_str} ===" >&2
                    if [ -d "{path_str}" ]; then
                        echo "Directory exists" >&2
                        ls -1 "{path_str}"
                    else
                        echo "Directory does NOT exist" >&2
                        echo "Parent contents:" >&2
                        ls -la "$(dirname "{path_str}")" >&2 2>/dev/null || echo "Parent also missing" >&2
                        exit 0
                    fi
                """

                # Mount the parent sandbox directory to ensure we can see the project
                parent_mount = _get_sandbox_base()

                # Use create + start + logs pattern instead of run() for better TCP reliability
                # The run() method with remove=True has race condition issues over TCP
                container = self.docker_client.containers.create(
                    "alpine:latest",
                    command=["-c", list_script],
                    entrypoint="/bin/sh",
                    volumes={parent_mount: {"bind": parent_mount, "mode": "ro"}},
                )
                try:
                    container.start()
                    container.wait(timeout=30)  # Wait for completion
                    # Get logs after container has finished
                    output = container.logs(stdout=True, stderr=True).decode('utf-8').strip()
                finally:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass
                # Filter out debug lines (starting with ===) to get just filenames
                files = [f for f in output.split('\n') if f and not f.startswith('===') and not f.startswith('Directory') and not f.startswith('Parent')]
                logger.info(f"[ContainerExecutor] Found {len(files)} files: {files[:5]}")
                if not files:
                    logger.warning(f"[ContainerExecutor] No files found. Full output: {output[:500]}")
            except Exception as e:
                logger.warning(f"[ContainerExecutor] Failed to list remote files: {e}")
                files = []
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
                pkg_path = os.path.join(path_str, "package.json")
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

        # Multi-folder project detection: check frontend/ subdirectory
        # This handles fullstack projects where frontend is in a subdirectory
        if "frontend" in files or not files:
            logger.info(f"[ContainerExecutor] Checking for multi-folder project (files empty or has frontend/)")
            # Check if frontend has package.json (full-stack project with separate frontend)
            # If file listing failed (empty), still try to detect frontend/ structure
            try:
                frontend_pkg_path = os.path.join(path_str, "frontend", "package.json")
                frontend_detected = False

                # For remote mode, check via Docker
                if sandbox_docker_host and self.docker_client:
                    try:
                        # Check for frontend/package.json using a simple test command
                        check_script = f'test -f "{path_str}/frontend/package.json" && echo "frontend_exists" && test -f "{path_str}/frontend/vite.config.ts" && echo "vite_exists" || true'
                        logger.info(f"[ContainerExecutor] Running frontend check: {check_script[:80]}...")

                        # Use create + start + logs pattern for TCP reliability
                        container = self.docker_client.containers.create(
                            "alpine:latest",
                            command=["-c", check_script],
                            entrypoint="/bin/sh",
                            volumes={_get_sandbox_base(): {"bind": _get_sandbox_base(), "mode": "ro"}}
                        )
                        try:
                            container.start()
                            container.wait(timeout=30)
                            output = container.logs(stdout=True, stderr=True).decode('utf-8').strip()
                        finally:
                            try:
                                container.remove(force=True)
                            except Exception:
                                pass
                        logger.info(f"[ContainerExecutor] Frontend check output: '{output}'")
                        if "frontend_exists" in output:
                            frontend_detected = True
                            logger.info(f"[ContainerExecutor] Detected multi-folder project with frontend/package.json")
                            # Store subdirectory info for container creation
                            self._frontend_subdir = True
                            if "vite_exists" in output:
                                return Technology.NODEJS_VITE
                            return Technology.NODEJS
                        elif not output and not files:
                            # Docker SDK might be returning empty - assume multi-folder as fallback
                            logger.warning(f"[ContainerExecutor] Docker SDK returned empty, assuming multi-folder project")
                            self._frontend_subdir = True
                            return Technology.NODEJS_VITE
                    except Exception as e:
                        logger.warning(f"[ContainerExecutor] Failed to check frontend/package.json via Docker: {e}")
                        # Fallback: assume multi-folder if Docker commands fail and no files detected
                        if not files:
                            logger.info(f"[ContainerExecutor] Docker check failed, assuming multi-folder project as fallback")
                            self._frontend_subdir = True
                            return Technology.NODEJS_VITE
                elif os.path.exists(frontend_pkg_path):
                    logger.info(f"[ContainerExecutor] Detected multi-folder project with frontend/package.json (local)")
                    self._frontend_subdir = True
                    # Check for vite config in frontend/
                    if os.path.exists(os.path.join(path_str, "frontend", "vite.config.ts")) or \
                       os.path.exists(os.path.join(path_str, "frontend", "vite.config.js")):
                        return Technology.NODEJS_VITE
                    return Technology.NODEJS
            except Exception as e:
                logger.warning(f"[ContainerExecutor] Error checking frontend subdirectory: {e}")

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

    def _remote_files_exist(self, project_path: str, paths_to_check: list) -> dict:
        """
        Check if files/directories exist on remote EC2 Docker host.

        Args:
            project_path: Base project path on EC2
            paths_to_check: List of relative paths to check (e.g., ["frontend", "frontend/package.json"])

        Returns:
            Dict mapping path to existence boolean
        """
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        if not sandbox_docker_host or not self.docker_client:
            # Local mode - use Path.exists()
            result = {}
            for p in paths_to_check:
                full_path = Path(project_path) / p
                result[p] = full_path.exists()
            return result

        # Remote mode - use Docker to check
        try:
            # Build a shell script that checks all paths
            checks = []
            for p in paths_to_check:
                full_path = f"{project_path}/{p}"
                checks.append(f'[ -e "{full_path}" ] && echo "{p}:EXISTS" || echo "{p}:MISSING"')

            check_script = " && ".join(checks)

            parent_mount = _get_sandbox_base()
            container = self.docker_client.containers.create(
                "alpine:latest",
                command=["-c", check_script],
                entrypoint="/bin/sh",
                volumes={parent_mount: {"bind": parent_mount, "mode": "ro"}},
            )
            try:
                container.start()
                container.wait(timeout=30)
                output = container.logs(stdout=True, stderr=False).decode('utf-8').strip()
            finally:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

            # Parse output
            result = {}
            for line in output.split('\n'):
                if ':EXISTS' in line:
                    path = line.replace(':EXISTS', '')
                    result[path] = True
                elif ':MISSING' in line:
                    path = line.replace(':MISSING', '')
                    result[path] = False

            logger.info(f"[ContainerExecutor] Remote file check: {result}")
            return result

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Remote file check failed: {e}")
            return {p: False for p in paths_to_check}

    def detect_fullstack_project(self, project_path: str) -> Optional[FullStackConfig]:
        """
        Detect if project is a full-stack project with separate frontend and backend.

        Full-stack project structure:
        project/
        ├── frontend/    # React, Vue, Angular
        │   └── package.json
        └── backend/     # Java, Python, Go
            └── pom.xml / requirements.txt / go.mod

        Also detects database requirements by scanning backend config files.

        Now remote-aware: works with files on EC2 Docker host.

        Returns:
            FullStackConfig if full-stack project detected, None otherwise
        """
        path = Path(project_path)

        # Check paths needed for fullstack detection (remote-aware)
        paths_to_check = [
            "frontend",
            "backend",
            "frontend/package.json",
            "frontend/vite.config.ts",
            "frontend/vite.config.js",
            "frontend/vite.config.mjs",
            "frontend/angular.json",
            "backend/pom.xml",
            "backend/build.gradle",
            "backend/build.gradle.kts",
            "backend/requirements.txt",
            "backend/pyproject.toml",
            "backend/go.mod",
        ]

        file_exists = self._remote_files_exist(project_path, paths_to_check)

        # Check if both frontend/ and backend/ directories exist
        if not (file_exists.get("frontend", False) and file_exists.get("backend", False)):
            logger.info(f"[ContainerExecutor] Fullstack detection: frontend={file_exists.get('frontend')}, backend={file_exists.get('backend')}")
            return None

        # Detect frontend technology
        frontend_tech = None
        frontend_port = 3000

        if file_exists.get("frontend/package.json", False):
            if file_exists.get("frontend/vite.config.ts", False) or \
               file_exists.get("frontend/vite.config.js", False) or \
               file_exists.get("frontend/vite.config.mjs", False):
                frontend_tech = Technology.NODEJS_VITE
                frontend_port = 3000
            elif file_exists.get("frontend/angular.json", False):
                frontend_tech = Technology.ANGULAR
                frontend_port = 4200
            else:
                frontend_tech = Technology.NODEJS
                frontend_port = 3000

        if not frontend_tech:
            logger.info(f"[ContainerExecutor] Fullstack detection: no frontend tech detected")
            return None

        # Detect backend technology
        backend_tech = None
        backend_port = 8080

        if file_exists.get("backend/pom.xml", False) or \
           file_exists.get("backend/build.gradle", False) or \
           file_exists.get("backend/build.gradle.kts", False):
            backend_tech = Technology.JAVA
            backend_port = 8080
        elif file_exists.get("backend/requirements.txt", False) or \
             file_exists.get("backend/pyproject.toml", False):
            backend_tech = Technology.PYTHON
            backend_port = 8000
        elif file_exists.get("backend/go.mod", False):
            backend_tech = Technology.GO
            backend_port = 8080
        # Note: .NET detection with glob not supported in remote mode for now

        if not backend_tech:
            logger.info(f"[ContainerExecutor] Fullstack detection: no backend tech detected")
            return None

        # Detect database type by scanning backend config files
        backend_path = path / "backend"
        database_type = self._detect_database_type(backend_path, backend_tech)
        database_config = DATABASE_CONFIGS.get(database_type) if database_type != DatabaseType.NONE else None

        logger.info(f"[ContainerExecutor] Detected full-stack project: frontend={frontend_tech.value}, backend={backend_tech.value}, database={database_type.value}")

        return FullStackConfig(
            frontend_tech=frontend_tech,
            backend_tech=backend_tech,
            frontend_port=frontend_port,
            backend_port=backend_port,
            frontend_path="frontend",
            backend_path="backend",
            database_type=database_type,
            database_config=database_config
        )

    def _detect_database_type(self, backend_path: Path, backend_tech: Technology) -> DatabaseType:
        """
        Detect database type by scanning backend configuration files.

        Scans:
        - Java: pom.xml, application.properties, application.yml
        - Python: requirements.txt, pyproject.toml
        - Go: go.mod
        - .NET: *.csproj, appsettings.json

        Returns:
            DatabaseType enum value
        """
        files_to_scan = []

        # Determine files to scan based on backend technology
        if backend_tech == Technology.JAVA:
            files_to_scan = [
                backend_path / "pom.xml",
                backend_path / "build.gradle",
                backend_path / "src" / "main" / "resources" / "application.properties",
                backend_path / "src" / "main" / "resources" / "application.yml",
                backend_path / "src" / "main" / "resources" / "application.yaml",
            ]
        elif backend_tech == Technology.PYTHON:
            files_to_scan = [
                backend_path / "requirements.txt",
                backend_path / "pyproject.toml",
                backend_path / "setup.py",
                backend_path / ".env",
                backend_path / "config.py",
            ]
        elif backend_tech == Technology.GO:
            files_to_scan = [
                backend_path / "go.mod",
                backend_path / ".env",
                backend_path / "config.yaml",
            ]
        elif backend_tech == Technology.DOTNET:
            files_to_scan = list(backend_path.glob("*.csproj")) + [
                backend_path / "appsettings.json",
                backend_path / "appsettings.Development.json",
            ]

        # Scan files for database patterns
        combined_content = ""
        for file_path in files_to_scan:
            if isinstance(file_path, Path) and file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    combined_content += content.lower() + "\n"
                except Exception as e:
                    logger.debug(f"[ContainerExecutor] Could not read {file_path}: {e}")

        if not combined_content:
            return DatabaseType.NONE

        # Check for database patterns (in priority order)
        for db_type, patterns in DATABASE_DETECTION_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in combined_content:
                    logger.info(f"[ContainerExecutor] Detected database: {db_type.value} (pattern: {pattern})")
                    return db_type

        return DatabaseType.NONE

    async def create_project_network(self, project_id: str) -> str:
        """
        Create a Docker network for full-stack project communication.

        Args:
            project_id: Project identifier

        Returns:
            Network name
        """
        network_name = f"bharatbuild_{project_id[:8]}_network"

        try:
            # Check if network already exists
            existing_networks = self.docker_client.networks.list(names=[network_name])
            if existing_networks:
                logger.info(f"[ContainerExecutor] Network {network_name} already exists")
                return network_name

            # Create new network
            self.docker_client.networks.create(
                network_name,
                driver="bridge",
                labels={"project_id": project_id, "managed_by": "bharatbuild"}
            )
            logger.info(f"[ContainerExecutor] Created network: {network_name}")
            return network_name

        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to create network: {e}")
            raise

    async def run_fullstack_project(
        self,
        project_id: str,
        project_path: str,
        fullstack_config: FullStackConfig
    ) -> AsyncGenerator[str, None]:
        """
        Run a full-stack project using Docker Compose.

        Architecture (Docker Compose):
        1. Check if docker-compose.yml exists
        2. If not, generate one from detected config
        3. Run docker-compose up
        4. FixerAgent handles any errors automatically

        Benefits:
        - Industry standard approach
        - Supports any stack (React, Vue, Java, Python, Node, Go, etc.)
        - Supports microservices
        - FixerAgent can fix docker-compose issues

        Args:
            project_id: Project identifier
            project_path: Path to project root
            fullstack_config: Full-stack configuration

        Yields:
            Progress messages and preview URL
        """
        yield f"🚀 Starting full-stack project (Docker Compose Mode)...\n"
        yield f"  📦 Frontend: {fullstack_config.frontend_tech.value}\n"
        yield f"  📦 Backend: {fullstack_config.backend_tech.value}\n"
        if fullstack_config.database_type != DatabaseType.NONE:
            yield f"  🗄️ Database: {fullstack_config.database_type.value}\n"
        yield f"\n"

        # ALWAYS use .yml extension - we generate with .yml
        compose_file = os.path.join(project_path, "docker-compose.yml")
        compose_yaml_file = os.path.join(project_path, "docker-compose.yaml")
        generated_compose = False

        # Check if docker-compose file exists (handles both local and remote sandbox)
        yml_exists = self._file_exists_on_sandbox(compose_file)
        yaml_exists = self._file_exists_on_sandbox(compose_yaml_file)
        has_compose = yml_exists or yaml_exists

        if has_compose:
            # Use the existing file
            if yml_exists:
                compose_file = os.path.join(project_path, "docker-compose.yml")
            else:
                compose_file = os.path.join(project_path, "docker-compose.yaml")
            yield f"📋 Found {os.path.basename(compose_file)}, using it directly...\n"
        else:
            yield f"📝 Generating docker-compose.yml for your project...\n"
            async for msg in self._generate_docker_compose(project_path, fullstack_config):
                yield msg
            # We just generated it - ALWAYS use .yml extension
            compose_file = os.path.join(project_path, "docker-compose.yml")
            generated_compose = True

        # Run docker-compose - pass the exact compose file path we're using
        async for msg in self._run_docker_compose(project_id, project_path, fullstack_config, compose_file, generated_compose):
            yield msg

    async def _generate_docker_compose(
        self,
        project_path: str,
        fullstack_config: FullStackConfig
    ) -> AsyncGenerator[str, None]:
        """Generate docker-compose.yml for the project."""
        import yaml

        compose_config = {
            "version": "3.8",
            "services": {}
        }

        # Get available ports
        frontend_port = self._get_available_port(fullstack_config.frontend_port)
        backend_port = self._get_available_port(fullstack_config.backend_port)

        # Frontend service
        frontend_config = TECHNOLOGY_CONFIGS.get(fullstack_config.frontend_tech)
        if frontend_config:
            # Detect package manager (npm, yarn, pnpm)
            frontend_full_path = os.path.join(project_path, fullstack_config.frontend_path)
            if os.path.exists(os.path.join(frontend_full_path, "pnpm-lock.yaml")):
                pkg_manager = "pnpm"
                install_cmd = "pnpm install"
                dev_cmd = "pnpm run dev"
            elif os.path.exists(os.path.join(frontend_full_path, "yarn.lock")):
                pkg_manager = "yarn"
                install_cmd = "yarn install"
                dev_cmd = "yarn dev"
            else:
                pkg_manager = "npm"
                install_cmd = "npm install"
                dev_cmd = "npm run dev"

            compose_config["services"]["frontend"] = {
                "image": frontend_config.image,
                "working_dir": "/app",
                "volumes": [f"./{fullstack_config.frontend_path}:/app", f"./{fullstack_config.frontend_path}/node_modules:/app/node_modules"],
                "ports": [f"{frontend_port}:{fullstack_config.frontend_port}"],
                "command": f"/bin/sh -c '{install_cmd} && {dev_cmd} -- --host 0.0.0.0 --port {fullstack_config.frontend_port}'",
                "environment": {
                    "VITE_API_URL": f"http://backend:{fullstack_config.backend_port}",
                    "REACT_APP_API_URL": f"http://backend:{fullstack_config.backend_port}"
                },
                "depends_on": ["backend"]
            }

        # Backend service
        backend_config = TECHNOLOGY_CONFIGS.get(fullstack_config.backend_tech)
        if backend_config:
            compose_config["services"]["backend"] = {
                "image": backend_config.image,
                "working_dir": "/app",
                "volumes": [f"./{fullstack_config.backend_path}:/app"],
                "ports": [f"{backend_port}:{fullstack_config.backend_port}"],
                "command": f"/bin/sh -c '{backend_config.build_command} && {backend_config.run_command}'",
                "environment": {
                    "PORT": str(fullstack_config.backend_port),
                    "SERVER_PORT": str(fullstack_config.backend_port)
                }
            }

        # Database service (if needed)
        if fullstack_config.database_type != DatabaseType.NONE and fullstack_config.database_config:
            db_config = fullstack_config.database_config
            db_port = self._get_available_port(db_config.port)

            # Determine volume path based on database type
            if "postgres" in db_config.image:
                db_volume = "db_data:/var/lib/postgresql/data"
            elif "mysql" in db_config.image or "mariadb" in db_config.image:
                db_volume = "db_data:/var/lib/mysql"
            elif "mongo" in db_config.image:
                db_volume = "db_data:/data/db"
            elif "redis" in db_config.image:
                db_volume = "db_data:/data"
            else:
                db_volume = None

            compose_config["services"]["database"] = {
                "image": db_config.image,
                "ports": [f"{db_port}:{db_config.port}"],
                "environment": db_config.env_vars,
                "volumes": [db_volume] if db_volume else []
            }

            # Add database dependency to backend
            if "backend" in compose_config["services"]:
                compose_config["services"]["backend"]["depends_on"] = ["database"]
                compose_config["services"]["backend"]["environment"].update({
                    "DATABASE_URL": db_config.connection_string_template.format(host="database"),
                    "DB_HOST": "database"
                })

            # Add volumes section
            compose_config["volumes"] = {"db_data": {}}

        # Write docker-compose.yml (handles both local and remote sandbox)
        compose_file = os.path.join(project_path, "docker-compose.yml")
        try:
            compose_content = yaml.dump(compose_config, default_flow_style=False, sort_keys=False)
            if self._write_file_to_sandbox(compose_file, compose_content):
                yield f"  ✅ Generated docker-compose.yml\n"
            else:
                raise Exception("Failed to write docker-compose.yml to sandbox")
        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to write docker-compose.yml: {e}")
            yield f"  ❌ Failed to generate docker-compose.yml: {e}\n"
            raise

    async def _run_docker_compose(
        self,
        project_id: str,
        project_path: str,
        fullstack_config: FullStackConfig,
        compose_file: str = None,
        just_generated: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Run docker-compose up and stream output.

        Handles both local and remote sandbox modes:
        - Local: Uses subprocess directly
        - Remote: Uses helper containers with docker-compose

        Args:
            project_id: Project identifier
            project_path: Path to project
            fullstack_config: Full-stack configuration
            compose_file: Path to compose file (if known from caller)
            just_generated: True if we just generated the file (skip existence check)
        """
        import yaml

        yield f"\n━━━ Running Docker Compose ━━━\n"

        # Use provided compose_file, or detect it
        if compose_file is None:
            compose_file = os.path.join(project_path, "docker-compose.yml")

        # In remote sandbox, add a small delay to ensure file sync after generation
        if self._is_remote_sandbox() and just_generated:
            await asyncio.sleep(0.5)

        # If we just generated the file, trust that it exists with .yml extension
        # Only do existence check if we didn't just generate it
        if not just_generated:
            yml_file = os.path.join(project_path, "docker-compose.yml")
            yaml_file = os.path.join(project_path, "docker-compose.yaml")
            yml_exists = self._file_exists_on_sandbox(yml_file)
            yaml_exists = self._file_exists_on_sandbox(yaml_file)

            if yml_exists:
                compose_file = yml_file
            elif yaml_exists:
                compose_file = yaml_file
                yield f"  📄 Using docker-compose.yaml\n"
            else:
                yield f"  ⚠️ Could not verify docker-compose file exists, using {os.path.basename(compose_file)}\n"

        yield f"  📄 Compose file: {os.path.basename(compose_file)}\n"

        frontend_port = fullstack_config.frontend_port
        backend_port = fullstack_config.backend_port

        try:
            compose_content = self._read_file_from_sandbox(compose_file)
            if compose_content:
                compose_config = yaml.safe_load(compose_content)

                # Validate compose_config is a dict
                if not isinstance(compose_config, dict):
                    logger.warning(f"[ContainerExecutor] Compose file parsed but not a dict: {type(compose_config)}")
                    yield f"  ⚠️ Compose file format invalid, using default ports\n"
                else:
                    # Extract ports from compose file
                    services = compose_config.get("services", {})
                    if isinstance(services, dict):
                        for name, service in services.items():
                            if not isinstance(service, dict):
                                continue
                            ports = service.get("ports", [])
                            for port_mapping in ports:
                                if isinstance(port_mapping, str) and ":" in port_mapping:
                                    try:
                                        host_port = int(port_mapping.split(":")[0])
                                        if "frontend" in name.lower() or "web" in name.lower() or "ui" in name.lower():
                                            frontend_port = host_port
                                        elif "backend" in name.lower() or "api" in name.lower() or "server" in name.lower():
                                            backend_port = host_port
                                    except ValueError:
                                        pass  # Skip invalid port mappings

                        # Normalize depends_on format for docker-compose compatibility
                        # AI sometimes generates dict format which older docker-compose doesn't support
                        try:
                            if self._normalize_depends_on_format(compose_file, compose_content):
                                yield f"  ✅ Normalized depends_on format for compatibility\n"
                        except Exception as e:
                            logger.warning(f"[ContainerExecutor] Failed to normalize depends_on: {e}")
            else:
                yield f"  ⚠️ Could not read compose file, using default ports\n"
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Could not parse compose file: {e}")
            yield f"  ⚠️ Could not parse compose file: {e}\n"

        # Stop any existing containers for this project
        project_name = f"bharatbuild_{project_id[:8]}"
        yield f"  🧹 Cleaning up existing containers...\n"

        try:
            cleanup_cmd = f"docker-compose -p {project_name} -f {compose_file} down --remove-orphans"
            exit_code, output = self._run_shell_on_sandbox(cleanup_cmd, working_dir=project_path, timeout=30)
            if exit_code != 0:
                logger.warning(f"[ContainerExecutor] Cleanup had issues: {output}")
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Cleanup failed: {e}")

        # =================================================================
        # GLOBAL CLEANUP - Remove containers IDLE for 30+ minutes
        # =================================================================
        # Only removes STOPPED/EXITED containers that have been idle for 30+ min
        # Running containers are NOT touched (they may be in active use)
        try:
            global_cleanup_cmd = (
                "for container in $(docker ps -a --filter 'status=exited' --format '{{.ID}}' 2>/dev/null); do "
                "  name=$(docker inspect --format '{{.Name}}' $container 2>/dev/null | sed 's/^\\///'); "
                "  if echo \"$name\" | grep -qE 'bharatbuild_'; then "
                "    finished=$(docker inspect --format '{{.State.FinishedAt}}' $container 2>/dev/null); "
                "    finished_ts=$(date -d \"$finished\" +%s 2>/dev/null || echo 0); "
                "    now_ts=$(date +%s); "
                "    idle_min=$(( (now_ts - finished_ts) / 60 )); "
                "    if [ $idle_min -gt 30 ]; then "
                "      docker rm -f $container 2>/dev/null || true; "
                "      echo \"Removed $name (idle: ${idle_min}min)\"; "
                "    fi; "
                "  fi; "
                "done"
            )
            exit_code, cleanup_output = self._run_shell_on_sandbox(global_cleanup_cmd, working_dir=project_path, timeout=60)
            if cleanup_output and "Removed" in cleanup_output:
                removed_count = cleanup_output.count("Removed")
                yield f"  🗑️ Cleaned up {removed_count} idle container(s)\n"
                logger.info(f"[ContainerExecutor] Removed idle containers: {cleanup_output}")
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Global cleanup failed: {e}")

        # Run Docker Infrastructure Fixer pre-flight checks
        # This prevents "Pool overlaps", port conflicts, and other infra issues
        # Also validates and fixes Dockerfile and docker-compose.yml
        yield f"  🔧 Running infrastructure pre-flight checks...\n"
        try:
            preflight_fixes = await docker_infra_fixer.preflight_check(
                project_id=project_id,
                sandbox_runner=lambda cmd, wd, timeout: self._run_shell_on_sandbox(cmd, working_dir=project_path, timeout=timeout),
                project_name=project_name,
                project_path=str(project_path)
            )
            for fix in preflight_fixes:
                if fix.success:
                    yield f"  ✅ {fix.message}\n"
                else:
                    yield f"  ⚠️ {fix.message}\n"
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Pre-flight check failed: {e}")
            yield f"  ⚠️ Pre-flight check skipped: {e}\n"

        # Verify Dockerfiles exist before running docker-compose
        yield f"  🔍 Verifying build files...\n"

        # Debug: Show actual directory structure
        yield f"  📂 Directory structure:\n"
        ls_cmd = "ls -la"
        exit_code, ls_output = self._run_shell_on_sandbox(ls_cmd, working_dir=project_path, timeout=10)
        if exit_code == 0:
            for line in ls_output.split('\n')[:15]:
                if line.strip():
                    yield f"     {line}\n"

        # Debug: Show docker-compose.yml build sections
        yield f"  📄 docker-compose.yml build config:\n"
        grep_cmd = f'grep -A2 "build:" "{compose_file}" | head -20'
        exit_code, grep_output = self._run_shell_on_sandbox(grep_cmd, working_dir=project_path, timeout=10)
        if exit_code == 0 and grep_output:
            for line in grep_output.split('\n'):
                yield f"     {line}\n"

        dockerfile_locations = {}  # Map service type to actual Dockerfile path
        dockerfile_paths = ["Dockerfile", "frontend/Dockerfile", "backend/Dockerfile"]
        for df_path in dockerfile_paths:
            check_cmd = f'test -f "{df_path}" && head -1 "{df_path}"'
            exit_code, output = self._run_shell_on_sandbox(check_cmd, working_dir=project_path, timeout=10)
            if exit_code == 0:
                yield f"     ✅ {df_path}: exists\n"
                # Track where Dockerfiles actually are
                if df_path == "frontend/Dockerfile":
                    dockerfile_locations["frontend"] = "./frontend"
                elif df_path == "backend/Dockerfile":
                    dockerfile_locations["backend"] = "./backend"
                elif df_path == "Dockerfile":
                    dockerfile_locations["root"] = "."
            else:
                yield f"     ⚠️ {df_path}: not found\n"

        # Auto-fix docker-compose.yml if Dockerfiles are in subdirectories but compose points to root
        if dockerfile_locations and "root" not in dockerfile_locations:
            yield f"  🔧 Auto-fixing docker-compose.yml build paths...\n"
            try:
                # Read current compose file
                read_cmd = f'cat "{compose_file}"'
                exit_code, compose_content = self._run_shell_on_sandbox(read_cmd, working_dir=project_path, timeout=10)
                if exit_code == 0 and compose_content:
                    import yaml
                    compose_data = yaml.safe_load(compose_content)

                    if compose_data and 'services' in compose_data:
                        modified = False
                        for service_name, service in compose_data['services'].items():
                            if not isinstance(service, dict):
                                continue

                            # Check if service has build configuration
                            if 'build' in service:
                                build_config = service['build']

                                # Handle string format: build: .
                                if isinstance(build_config, str) and build_config in ['.', './']:
                                    # Need to fix - determine correct path based on service name
                                    if 'frontend' in service_name.lower() and 'frontend' in dockerfile_locations:
                                        service['build'] = {'context': './frontend', 'dockerfile': 'Dockerfile'}
                                        modified = True
                                        yield f"     ✅ Fixed {service_name}: context -> ./frontend\n"
                                    elif 'backend' in service_name.lower() and 'backend' in dockerfile_locations:
                                        service['build'] = {'context': './backend', 'dockerfile': 'Dockerfile'}
                                        modified = True
                                        yield f"     ✅ Fixed {service_name}: context -> ./backend\n"
                                    elif 'nginx' in service_name.lower():
                                        # Nginx should use pre-built image, not build from Dockerfile
                                        # This fixes corrupted docker-compose where AI changed 'image:' to 'build:'
                                        del service['build']
                                        service['image'] = 'nginx:alpine'
                                        # Ensure nginx.conf volume mount exists
                                        if 'volumes' not in service:
                                            service['volumes'] = []
                                        nginx_conf_mounts = [
                                            './nginx.conf:/etc/nginx/nginx.conf:ro',
                                            './nginx/nginx.conf:/etc/nginx/nginx.conf:ro'
                                        ]
                                        has_nginx_conf = any(
                                            'nginx.conf' in str(v) for v in service.get('volumes', [])
                                        )
                                        if not has_nginx_conf:
                                            service['volumes'].append('./nginx.conf:/etc/nginx/nginx.conf:ro')
                                        modified = True
                                        yield f"     ✅ Fixed {service_name}: using image nginx:alpine (removed invalid build)\n"

                                # Handle dict format: build: { context: . }
                                elif isinstance(build_config, dict):
                                    context = build_config.get('context', '.')
                                    if context in ['.', './']:
                                        if 'frontend' in service_name.lower() and 'frontend' in dockerfile_locations:
                                            build_config['context'] = './frontend'
                                            modified = True
                                            yield f"     ✅ Fixed {service_name}: context -> ./frontend\n"
                                        elif 'backend' in service_name.lower() and 'backend' in dockerfile_locations:
                                            build_config['context'] = './backend'
                                            modified = True
                                            yield f"     ✅ Fixed {service_name}: context -> ./backend\n"
                                        elif 'nginx' in service_name.lower():
                                            # Nginx should use pre-built image
                                            del service['build']
                                            service['image'] = 'nginx:alpine'
                                            if 'volumes' not in service:
                                                service['volumes'] = []
                                            has_nginx_conf = any(
                                                'nginx.conf' in str(v) for v in service.get('volumes', [])
                                            )
                                            if not has_nginx_conf:
                                                service['volumes'].append('./nginx.conf:/etc/nginx/nginx.conf:ro')
                                            modified = True
                                            yield f"     ✅ Fixed {service_name}: using image nginx:alpine (removed invalid build)\n"

                        # Write fixed compose file
                        if modified:
                            fixed_yaml = yaml.dump(compose_data, default_flow_style=False, sort_keys=False)
                            # Write using base64 to avoid escaping issues
                            import base64
                            encoded = base64.b64encode(fixed_yaml.encode()).decode()
                            write_cmd = f'echo "{encoded}" | base64 -d > "{compose_file}"'
                            exit_code, _ = self._run_shell_on_sandbox(write_cmd, working_dir=project_path, timeout=10)
                            if exit_code == 0:
                                yield f"     ✅ docker-compose.yml updated\n"
                            else:
                                yield f"     ⚠️ Failed to update docker-compose.yml\n"

            except Exception as e:
                logger.warning(f"[ContainerExecutor] Failed to auto-fix compose: {e}")
                yield f"     ⚠️ Auto-fix skipped: {e}\n"

        # =================================================================
        # DYNAMIC PORT ALLOCATION - Prevents port conflicts automatically
        # =================================================================
        yield f"  🔌 Allocating dynamic ports...\n"
        try:
            port_mapping, dynamic_frontend_port, dynamic_backend_port = self._allocate_dynamic_ports(
                compose_file=compose_file,
                project_path=project_path
            )

            if port_mapping:
                yield f"  ✅ Dynamic port allocation:\n"
                for original, new in port_mapping.items():
                    yield f"     {original} → {new}\n"

                # Update frontend/backend ports with dynamically allocated ones
                if dynamic_frontend_port:
                    frontend_port = dynamic_frontend_port
                    yield f"  📱 Frontend will be available on port {frontend_port}\n"
                if dynamic_backend_port:
                    backend_port = dynamic_backend_port
                    yield f"  🖥️ Backend will be available on port {backend_port}\n"
            else:
                yield f"  ℹ️ No port remapping needed\n"

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Dynamic port allocation failed: {e}")
            yield f"  ⚠️ Dynamic port allocation skipped: {e}\n"

        # =================================================================
        # PREFLIGHT PORT CLEANUP - Free common ports before docker-compose
        # =================================================================
        # This prevents port conflicts by proactively killing old processes
        yield f"  🔌 Cleaning up potentially blocked ports...\n"
        try:
            # Get ports from docker-compose.yml that will be used
            ports_to_check = set()
            # Re-read compose content to ensure we have the latest (after any normalization)
            preflight_compose = self._read_file_from_sandbox(compose_file) if compose_file else None
            if preflight_compose:
                import yaml
                compose_data = yaml.safe_load(preflight_compose)
                if compose_data and 'services' in compose_data:
                    for service_name, service_config in compose_data.get('services', {}).items():
                        if isinstance(service_config, dict) and 'ports' in service_config:
                            for port_mapping in service_config.get('ports', []):
                                # Extract host port from "host:container" or just "port"
                                port_str = str(port_mapping).split(':')[0]
                                if port_str.isdigit():
                                    ports_to_check.add(port_str)

            # Add common ports that are frequently blocked
            common_ports = {'3000', '3001', '5173', '5174', '8080', '8081', '5432', '6379'}
            ports_to_check.update(common_ports)

            freed_any = False
            for port in ports_to_check:
                # Check if port is in use and kill if needed
                check_code, check_output = self._run_shell_on_sandbox(
                    f"fuser {port}/tcp 2>/dev/null && echo 'IN_USE' || true",
                    working_dir=project_path, timeout=5
                )
                if 'IN_USE' in check_output:
                    self._run_shell_on_sandbox(f"fuser -k {port}/tcp 2>/dev/null || true", working_dir=project_path, timeout=10)
                    self._run_shell_on_sandbox(f"docker ps --filter 'publish={port}' -q | xargs -r docker rm -f 2>/dev/null || true", working_dir=project_path, timeout=10)
                    logger.info(f"[ContainerExecutor] Preflight: Freed port {port}")
                    freed_any = True

            if freed_any:
                yield f"  ✅ Freed blocked ports\n"
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Preflight port cleanup failed: {e}")

        # =================================================================
        # PRE-BUILD VALIDATION - Fix issues BEFORE building
        # =================================================================
        try:
            from app.services.pre_build_validator import pre_build_validator

            yield f"\n📋 Pre-build validation...\n"

            validation_result = await pre_build_validator.validate_and_fix(
                project_id=project_id,
                project_path=project_path,
                technology=fullstack_config.frontend_tech if fullstack_config else None,
                sandbox_file_reader=self._read_file_from_sandbox,
                sandbox_file_writer=self._write_file_to_sandbox,
                sandbox_runner=self._run_shell_on_sandbox
            )

            if validation_result.files_scanned > 0:
                yield f"  📂 Scanned {validation_result.files_scanned} files\n"

            if validation_result.issues:
                yield f"  ⚠️ Found {len(validation_result.issues)} issues\n"

            if validation_result.files_fixed > 0:
                yield f"  ✅ Auto-fixed {validation_result.files_fixed} files:\n"
                for fix in validation_result.fixes_applied[:5]:
                    yield f"     • {fix}\n"

            if validation_result.is_valid:
                yield f"  ✅ Validation passed\n"
            else:
                yield f"  ⚠️ Some issues could not be auto-fixed\n"

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Pre-build validation failed: {e}")
            yield f"  ⚠️ Pre-build validation skipped: {e}\n"

        # =================================================================
        # JAVA STATIC ANALYZER - Fix Lombok, imports, duplicates BEFORE build
        # This catches 100+ compile errors BEFORE Docker build starts
        # =================================================================
        try:
            from app.services.java_analyzer import java_analyzer

            # Check if this is a Java project by looking for Java files
            java_files = self._list_files_from_sandbox(str(project_path), "*.java")
            if java_files:
                yield f"\n☕ Running Java analyzer on {len(java_files)} files...\n"

                analysis = java_analyzer.analyze_project(
                    project_path=project_path,
                    file_reader=self._read_file_from_sandbox,
                    file_writer=self._write_file_to_sandbox,
                    file_lister=self._list_files_from_sandbox,
                    auto_fix=True
                )

                if analysis.fixes_applied:
                    yield f"  ✅ Auto-fixed {len(analysis.fixes_applied)} issues:\n"
                    for fix in analysis.fixes_applied[:5]:
                        yield f"     • {fix}\n"
                    if len(analysis.fixes_applied) > 5:
                        yield f"     • ... and {len(analysis.fixes_applied) - 5} more\n"

                if analysis.issues:
                    unfixed = [i for i in analysis.issues if not i.auto_fixable]
                    if unfixed:
                        yield f"  ⚠️ {len(unfixed)} issues need manual review\n"
                        for issue in unfixed[:3]:
                            yield f"     • {issue.file_path}: {issue.message}\n"

                logger.info(f"[JavaAnalyzer] Pre-build: {len(analysis.fixes_applied)} fixes, {len(analysis.issues)} issues")

                # PERSIST JAVA ANALYZER FIXES TO DATABASE - so they survive retry
                if analysis.fixes_applied:
                    try:
                        from app.services.bolt_fixer import BoltFixer
                        from pathlib import Path
                        fixer = BoltFixer()
                        project_path_obj = Path(project_path) if isinstance(project_path, str) else project_path
                        persisted_count = 0
                        for fix_desc in analysis.fixes_applied:
                            # Extract file path from fix description
                            # Format: "Added @Slf4j to backend/src/.../File.java"
                            # or "Fixed imports in backend/src/.../File.java"
                            if " to " in fix_desc:
                                file_path = fix_desc.split(" to ")[-1].strip()
                            elif " in " in fix_desc:
                                file_path = fix_desc.split(" in ")[-1].strip()
                            else:
                                continue  # Can't extract path

                            # Only process .java files
                            if not file_path.endswith(".java"):
                                continue

                            full_path = project_path_obj / file_path
                            try:
                                content = self._read_file_from_sandbox(str(full_path))
                                if content:
                                    await fixer._persist_single_fix(project_id, project_path, file_path, content)
                                    persisted_count += 1
                            except Exception as pe:
                                logger.warning(f"[JavaAnalyzer] Failed to persist {file_path}: {pe}")

                        if persisted_count > 0:
                            logger.info(f"[JavaAnalyzer] Persisted {persisted_count} fixes to database")
                    except Exception as e:
                        logger.warning(f"[JavaAnalyzer] Failed to persist fixes: {e}")

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Java analyzer failed (continuing): {e}")
            # Don't yield error - Java projects will be built anyway

        # =================================================================
        # COMPREHENSIVE TECHNOLOGY VALIDATION - Fix ALL issues before build
        # Validates: React/Vite, Python, Java, Docker configs
        # Auto-creates: missing tsconfig.node.json, postcss.config.js, etc.
        # Auto-fixes: npm ci, --only=production, python- package names
        # =================================================================
        try:
            yield f"\n🔍 Running comprehensive technology validation...\n"

            validation_result = technology_validator.validate_and_fix(
                project_path=project_path,
                file_reader=self._read_file_from_sandbox,
                file_writer=self._write_file_to_sandbox
            )

            # Report created files
            if validation_result.files_created:
                for f in validation_result.files_created:
                    yield f"  ✅ Created: {f}\n"

            # Report fixed files
            if validation_result.files_fixed:
                for f in validation_result.files_fixed:
                    yield f"  🔧 Fixed: {f}\n"

            # Report warnings
            if validation_result.warnings:
                for w in validation_result.warnings:
                    yield f"  ⚠️ {w}\n"

            # Report errors (but don't stop - let Docker try)
            if validation_result.errors:
                for e in validation_result.errors:
                    yield f"  ❌ {e}\n"

            if validation_result.is_valid:
                yield f"  ✅ Technology validation passed\n"
            else:
                yield f"  ⚠️ Some issues found - build may fail\n"

            # PERSIST FIXES TO DATABASE - so they survive retry
            if validation_result.files_fixed:
                try:
                    from app.services.bolt_fixer import BoltFixer
                    from pathlib import Path
                    fixer = BoltFixer()
                    project_path_obj = Path(project_path) if isinstance(project_path, str) else project_path
                    for fix_info in validation_result.files_fixed:
                        # Extract file path from fix info (e.g., "backend/Dockerfile (mvnw → mvn)")
                        file_path = fix_info.split(" (")[0] if " (" in fix_info else fix_info
                        # Handle relative paths
                        if "/" in file_path:
                            full_path = project_path_obj / file_path
                        else:
                            full_path = project_path_obj / file_path
                        # Read the fixed content and persist
                        try:
                            content = self._read_file_from_sandbox(str(full_path))
                            if content:
                                await fixer._persist_single_fix(project_id, project_path, file_path, content)
                                logger.info(f"[ContainerExecutor] Persisted tech validation fix: {file_path}")
                        except Exception as pe:
                            logger.warning(f"[ContainerExecutor] Failed to persist {file_path}: {pe}")
                except Exception as e:
                    logger.warning(f"[ContainerExecutor] Failed to persist tech validation fixes: {e}")

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Technology validation failed: {e}")
            yield f"  ⚠️ Technology validation skipped: {e}\n"

        # Run docker-compose up
        yield f"\n  $ docker-compose up -d\n"

        # Track ALL files modified by auto-fix for S3 sync AFTER build succeeds
        # This is initialized here to cover both docker-compose build fixes AND health check fixes
        all_files_modified = []

        max_compose_attempts = 4  # Allow multiple retries for cascading fixes (port conflicts, etc.)
        compose_attempt = 0

        fixes_applied_this_cycle = False  # Track if fixes were applied, so retry uses --no-cache
        while compose_attempt < max_compose_attempts:
            compose_attempt += 1
            try:
                # Use legacy build mode (buildx 0.17+ not available on EC2)
                # CRITICAL: After fixes are applied, use --no-cache to pick up new files
                # Otherwise Docker's cached COPY layers will have OLD unfixed code!
                if fixes_applied_this_cycle:
                    cmd = f"COMPOSE_DOCKER_CLI_BUILD=0 DOCKER_BUILDKIT=0 docker-compose -p {project_name} -f {compose_file} build --no-cache && COMPOSE_DOCKER_CLI_BUILD=0 DOCKER_BUILDKIT=0 docker-compose -p {project_name} -f {compose_file} up -d"
                    logger.info(f"[ContainerExecutor] Using --no-cache after fixes were applied")
                else:
                    cmd = f"COMPOSE_DOCKER_CLI_BUILD=0 DOCKER_BUILDKIT=0 docker-compose -p {project_name} -f {compose_file} up -d --build"
                exit_code, output = self._run_shell_on_sandbox(cmd, working_dir=project_path, timeout=300)

                # Stream output lines
                for line in output.split('\n'):
                    if line.strip():
                        yield f"  {line}\n"

                if exit_code != 0:
                    # Try to fix errors automatically using chained agents
                    if compose_attempt < max_compose_attempts:
                        yield f"\n⚠️ Docker Compose failed, attempting auto-fix...\n"

                        # Step 1: Try DockerInfraFixer (fast, deterministic)
                        yield f"  🔧 Step 1: Trying infrastructure fixes...\n"
                        fix_result = await docker_infra_fixer.fix_error(
                            error_message=output,
                            project_id=project_id,
                            sandbox_runner=lambda cmd, wd, timeout: self._run_shell_on_sandbox(cmd, working_dir=project_path, timeout=timeout),
                            project_name=project_name,
                            project_path=str(project_path)
                        )

                        if fix_result.success:
                            yield f"  ✅ Infrastructure fix applied: {fix_result.message}\n"
                            yield f"  🔄 Retrying docker-compose...\n"
                            fixes_applied_this_cycle = True  # Force --no-cache on retry
                            continue  # Retry
                        else:
                            yield f"  ⚠️ Infrastructure fix not applicable: {fix_result.message}\n"

                            # Check for SYSTEM errors that should NOT be sent to AI fixer
                            # These are internal platform issues, not user code problems
                            system_error_patterns = [
                                "no such image: docker/compose",
                                "no such image: python:",
                                "no such image: node:",
                                "no such image: alpine",
                                "helper container",
                                "failed to create helper container",
                            ]
                            is_system_error = any(p in output.lower() for p in system_error_patterns)

                            if is_system_error:
                                yield f"  ⚠️ System error detected - this is a platform issue, not your code\n"
                                yield f"  💡 The platform helper container image is missing. Please try again.\n"
                                break  # Don't retry with AI fixer

                            # Step 2: Use BoltFixer for ALL errors (batch, cascade, dependency graph)
                            # =================================================================
                            # SMART FIXER SELECTION:
                            # - Java errors (cannot find symbol, getter/setter) → SDK Fixer (primary)
                            # - Other errors (syntax, config, etc.) → BoltFixer
                            # - If SDK Fixer fails → BoltFixer as fallback
                            # =================================================================
                            is_java_error = '.java' in output or 'cannot find symbol' in output or 'mvn' in output.lower()
                            sdk_fixer_handled = False

                            if is_java_error:
                                # SDK Fixer is PRIMARY for Java errors (simpler, tool-based approach)
                                yield f"  🔧 Step 2: Trying SDK Agent Fixer (Java errors)...\n"
                                try:
                                    from app.services.sdk_fixer import sdk_fix_errors
                                    sdk_result = await sdk_fix_errors(
                                        project_path=Path(project_path),
                                        build_errors=output,
                                        sandbox_reader=self._read_file_from_sandbox,
                                        sandbox_writer=self._write_file_to_sandbox,
                                        sandbox_lister=self._list_files_from_sandbox
                                    )
                                    # Check both modified and created files
                                    total_fixed = len(sdk_result.files_modified) + len(sdk_result.files_created)
                                    if sdk_result.success and total_fixed > 0:
                                        yield f"  ✅ SDK Fixer fixed {total_fixed} files:\n"
                                        for f in sdk_result.files_modified:
                                            yield f"     📝 {f}\n"
                                        all_files_modified.extend(sdk_result.files_modified)
                                        all_files_modified.extend(sdk_result.files_created)

                                        # PERSIST SDK FIXER FIXES TO DATABASE IMMEDIATELY
                                        # So they survive container removal and re-runs
                                        try:
                                            from app.services.bolt_fixer import BoltFixer
                                            persist_fixer = BoltFixer()
                                            all_sdk_files = sdk_result.files_modified + sdk_result.files_created
                                            persisted_count = 0
                                            for file_path in all_sdk_files:
                                                try:
                                                    full_path = Path(project_path) / file_path
                                                    content = self._read_file_from_sandbox(str(full_path))
                                                    if content:
                                                        await persist_fixer._persist_single_fix(project_id, project_path, file_path, content)
                                                        persisted_count += 1
                                                except Exception as pe:
                                                    logger.warning(f"[SDKFixer] Failed to persist {file_path}: {pe}")
                                            if persisted_count > 0:
                                                yield f"  💾 Persisted {persisted_count} fixes to database\n"
                                                logger.info(f"[SDKFixer] Persisted {persisted_count} fixes to database")
                                        except Exception as persist_err:
                                            logger.warning(f"[SDKFixer] Failed to persist fixes: {persist_err}")

                                        # VERIFY files were written before retrying
                                        yield f"  🔍 Verifying fixes were written to EC2...\n"
                                        verified_count = 0
                                        for file_path in all_sdk_files:
                                            full_path = Path(project_path) / file_path
                                            if self._file_exists_on_sandbox(str(full_path)):
                                                verified_count += 1
                                                logger.info(f"[SDKFixer] ✅ Verified file exists: {file_path}")
                                            else:
                                                logger.error(f"[SDKFixer] ❌ File NOT found after write: {file_path}")
                                                yield f"     ❌ {file_path} NOT FOUND!\n"

                                        if verified_count == len(all_sdk_files):
                                            yield f"  ✅ All {verified_count} files verified on EC2\n"
                                        else:
                                            yield f"  ⚠️ Only {verified_count}/{len(all_sdk_files)} files verified!\n"

                                        yield f"  🔄 Retrying docker-compose...\n"
                                        sdk_fixer_handled = True
                                        fixes_applied_this_cycle = True  # Force --no-cache on retry
                                        continue  # Retry build
                                    else:
                                        yield f"  ⚠️ SDK Fixer: {sdk_result.message}\n"
                                        yield f"  🔧 Step 3: Falling back to BoltFixer...\n"
                                except Exception as sdk_err:
                                    logger.warning(f"[ContainerExecutor] SDK Fixer error: {sdk_err}")
                                    yield f"  ⚠️ SDK Fixer error: {sdk_err}\n"
                                    yield f"  🔧 Step 3: Falling back to BoltFixer...\n"

                            # BoltFixer handles: syntax, import, type, config, dependency, build errors
                            # Also used as fallback when SDK Fixer fails for Java
                            if not sdk_fixer_handled:
                                if not is_java_error:
                                    yield f"  🔧 Step 2: Trying BoltFixer (batch + cascade)...\n"

                            if not sdk_fixer_handled:
                                try:
                                    from app.services.bolt_fixer import BoltFixer
                                    bolt_fixer_instance = BoltFixer()

                                    # Build payload for BoltFixer
                                    bolt_payload = {
                                        "stderr": output,
                                        "stdout": "",
                                        "exit_code": exit_code,
                                    }

                                    fix_result = await bolt_fixer_instance.fix_from_backend(
                                        project_id=project_id,
                                        project_path=Path(project_path),
                                        payload=bolt_payload,
                                        sandbox_file_writer=self._write_file_to_sandbox,
                                        sandbox_file_reader=self._read_file_from_sandbox,
                                        sandbox_file_lister=self._list_files_from_sandbox
                                    )

                                    if fix_result.success and fix_result.files_modified:
                                        yield f"  ✅ BoltFixer fixed {len(fix_result.files_modified)} files:\n"
                                        for f in fix_result.files_modified:
                                            yield f"     📝 {f}\n"

                                        # Track files for S3 sync
                                        all_files_modified.extend(fix_result.files_modified)

                                        # PERSIST BOLTFIXER FIXES TO DATABASE IMMEDIATELY
                                        # So they survive container removal and re-runs
                                        try:
                                            persisted_count = 0
                                            for file_path in fix_result.files_modified:
                                                try:
                                                    full_path = Path(project_path) / file_path
                                                    content = self._read_file_from_sandbox(str(full_path))
                                                    if content:
                                                        await bolt_fixer_instance._persist_single_fix(project_id, project_path, file_path, content)
                                                        persisted_count += 1
                                                except Exception as pe:
                                                    logger.warning(f"[BoltFixer] Failed to persist {file_path}: {pe}")
                                            if persisted_count > 0:
                                                yield f"  💾 Persisted {persisted_count} fixes to database\n"
                                                logger.info(f"[BoltFixer] Persisted {persisted_count} fixes to database")
                                        except Exception as persist_err:
                                            logger.warning(f"[BoltFixer] Failed to persist fixes: {persist_err}")

                                        # Check if more passes needed (cascading errors)
                                        if fix_result.needs_another_pass:
                                            yield f"  🔄 Pass {fix_result.current_pass} complete, {fix_result.remaining_errors} errors remaining...\n"

                                        yield f"  🔄 Retrying docker-compose...\n"
                                        fixes_applied_this_cycle = True  # Force --no-cache on retry
                                        continue  # Retry
                                    else:
                                        yield f"  ⚠️ BoltFixer: {fix_result.message if hasattr(fix_result, 'message') else 'No fix generated'}\n"

                                except Exception as bolt_err:
                                    logger.warning(f"[ContainerExecutor] BoltFixer error: {bolt_err}")
                                    yield f"  ⚠️ BoltFixer error: {bolt_err}\n"

                    yield f"\n❌ Docker Compose failed with exit code {exit_code}\n"
                    return

                # Build/up command succeeded, but we need to verify containers are actually running
                yield f"\n  📦 Docker Compose build completed, verifying services...\n"
                break  # Success, exit loop

            except Exception as e:
                if compose_attempt < max_compose_attempts:
                    yield f"\n⚠️ Error: {str(e)}, attempting recovery...\n"
                    continue
                yield f"\n❌ Error: {str(e)}\n"
                return

        # Wait for services to be ready and verify they stay running
        yield f"\n  ⏳ Verifying services are healthy...\n"

        # Simple command - just list all containers, filter in Python
        check_cmd = "docker ps -a --format 'table {{.Names}}\t{{.Status}}'"

        # Quick initial check (5s) to catch immediate startup failures
        yield f"  ⏳ Initial startup check (5s)...\n"
        await asyncio.sleep(5)

        exit_code, ps_output = self._run_shell_on_sandbox(check_cmd, working_dir=project_path, timeout=30)
        project_lines = [line for line in (ps_output.strip().split('\n') if ps_output else [])
                        if project_name.lower() in line.lower()]

        if not project_lines:
            yield f"  ⚠️ No containers started for project {project_name}\n"
            yield f"  ⚠️ Checking docker-compose logs...\n"
            # Get docker-compose logs for debugging
            logs_cmd = f"docker-compose -p {project_name} -f {compose_file} logs --tail=50"
            _, compose_logs = self._run_shell_on_sandbox(logs_cmd, working_dir=project_path, timeout=30)
            if compose_logs:
                for line in compose_logs.split('\n')[-20:]:
                    if line.strip():
                        yield f"     {line}\n"
            yield f"\n❌ Docker Compose failed - no containers running\n"
            return
        else:
            # Show initial status
            yield f"  📦 Initial container status:\n"
            running_count = 0
            exited_count = 0
            for line in project_lines:
                parts = line.split()
                if parts:
                    container_name = parts[0]
                    service_name = container_name.replace(f"{project_name}_", "").rsplit("_", 1)[0]
                    if "Up" in line:
                        yield f"     ✅ {service_name}: Running\n"
                        running_count += 1
                    elif "Exit" in line:
                        yield f"     ❌ {service_name}: Exited\n"
                        exited_count += 1
                    else:
                        yield f"     ⏳ {service_name}: Starting...\n"

            # If all containers already exited, fail fast
            if exited_count > 0 and running_count == 0:
                yield f"\n  ❌ All containers exited immediately after start\n"
                # Get logs from exited containers
                for line in project_lines:
                    if "Exit" in line:
                        container_name = line.split()[0]
                        logs_cmd = f"docker logs {container_name} 2>&1 | tail -30"
                        _, container_logs = self._run_shell_on_sandbox(logs_cmd, working_dir=project_path, timeout=30)
                        if container_logs:
                            yield f"\n  📋 Logs from {container_name}:\n"
                            for log_line in container_logs.split('\n')[-15:]:
                                if log_line.strip():
                                    yield f"     {log_line}\n"

        # Health check with auto-fix
        # Java/Maven projects need time to compile - check multiple times over 60s
        fix_attempt = 0
        containers_healthy = False
        # NOTE: all_files_modified is initialized earlier (before docker-compose loop)

        # Check schedule depends on project type
        # Java/Maven projects need longer waits due to slow compilation (60-120 seconds)
        is_java_project = False
        try:
            pom_check = f"test -f {project_path}/pom.xml -o -f {project_path}/backend/pom.xml && echo 'java'"
            _, pom_result = self._run_shell_on_sandbox(pom_check, working_dir=project_path, timeout=5)
            is_java_project = pom_result and 'java' in pom_result.lower()
            if is_java_project:
                logger.info(f"[ContainerExecutor] Java project detected - using extended stability checks")
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Error detecting Java project: {e}")

        # Java projects often have multi-file consistency errors (Entity, DTO, Service, Controller)
        # Need more fix attempts to fix all related files
        max_fix_attempts = 6 if is_java_project else 3
        logger.info(f"[ContainerExecutor] Max fix attempts: {max_fix_attempts} (Java={is_java_project})")

        # Service health check configuration
        # Order: infrastructure → backend → frontend → proxy
        SERVICE_CONFIG = {
            'db': {'timeout': 20, 'order': 1, 'success': ['ready to accept connections', 'database system is ready'], 'errors': []},
            'postgres': {'timeout': 20, 'order': 1, 'success': ['ready to accept connections', 'database system is ready'], 'errors': []},
            'mysql': {'timeout': 20, 'order': 1, 'success': ['ready for connections', 'mysqld: ready'], 'errors': []},
            'mongodb': {'timeout': 20, 'order': 1, 'success': ['Waiting for connections', 'listening on'], 'errors': []},
            'redis': {'timeout': 15, 'order': 1, 'success': ['Ready to accept connections', 'ready to accept connections'], 'errors': []},
            'backend': {'timeout': 120 if is_java_project else 60, 'order': 2,
                       'success': ['Started', 'Tomcat started', 'Application startup complete', 'Uvicorn running', 'Listening on port', 'Server is running'],
                       'errors': ['BUILD FAILURE', 'COMPILATION ERROR', '[ERROR]', 'Error:', 'Exception:', 'FATAL', 'cannot find symbol', 'package does not exist']},
            'frontend': {'timeout': 45, 'order': 3,
                        'success': ['VITE', 'ready in', 'compiled successfully', 'Local:', 'Compiled', 'webpack compiled'],
                        'errors': ['npm ERR!', 'Error:', 'ELIFECYCLE', 'Cannot find module']},
            'nginx': {'timeout': 15, 'order': 4, 'success': ['start worker process'], 'errors': ['emerg', 'error']},
        }
        DEFAULT_CONFIG = {'timeout': 30, 'order': 5, 'success': [], 'errors': ['Error:', 'error:', 'FATAL']}

        while fix_attempt < max_fix_attempts and not containers_healthy:
            failure_detected = False
            failed_service = None
            project_lines = []

            # Initial wait for containers to initialize
            yield f"\n  ⏳ Initializing containers...\n"
            await asyncio.sleep(5)

            # Get all containers for this project
            exit_code, ps_output = self._run_shell_on_sandbox(check_cmd, working_dir=project_path, timeout=30)
            if exit_code != 0 or not ps_output:
                yield f"  ⚠️ Failed to get container status\n"
                failure_detected = True
            else:
                output_lines = ps_output.strip().split('\n') if ps_output else []
                project_lines = [line for line in output_lines if project_name.lower() in line.lower()]

            if not project_lines and not failure_detected:
                yield f"  ⚠️ No containers found for {project_name}\n"
                failure_detected = True

            if not failure_detected:
                # Build service list with configs
                services = []
                for line in project_lines:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    container_name = parts[0]
                    service_name = container_name.replace(f"{project_name}_", "").rsplit("_", 1)[0]

                    # Find matching config
                    config = DEFAULT_CONFIG.copy()
                    for key, cfg in SERVICE_CONFIG.items():
                        if key in service_name.lower():
                            config = cfg.copy()
                            break

                    services.append({
                        'container': container_name,
                        'service': service_name,
                        'config': config,
                        'line': line
                    })

                # Sort by order (infrastructure first, then backend, then frontend, then nginx)
                services.sort(key=lambda x: x['config']['order'])

                yield f"\n  📦 Checking {len(services)} services in dependency order:\n"

                # Check each service
                for svc in services:
                    container_name = svc['container']
                    service_name = svc['service']
                    config = svc['config']
                    max_wait = config['timeout']
                    success_indicators = config['success']
                    error_indicators = config['errors']

                    yield f"\n     ⏳ {service_name}: Checking (timeout: {max_wait}s)...\n"

                    service_healthy = False
                    service_error = None
                    elapsed = 0
                    poll_interval = 5

                    while elapsed < max_wait:
                        # Get container status
                        status_cmd = f"docker ps -a --filter 'name=^{container_name}$' --format '{{{{.Status}}}}'"
                        _, status = self._run_shell_on_sandbox(status_cmd, working_dir=project_path, timeout=10)
                        status = (status or "").strip()

                        # Get container logs
                        logs_cmd = f"docker logs {container_name} 2>&1 | tail -50"
                        _, logs = self._run_shell_on_sandbox(logs_cmd, working_dir=project_path, timeout=10)
                        logs = logs or ""

                        # FAIL FAST: Check for failure states
                        if "Exit" in status:
                            service_error = "Container exited"
                            break
                        if "Restarting" in status:
                            service_error = "Container crash-looping"
                            break

                        # FAIL FAST: Check logs for error indicators
                        for err in error_indicators:
                            if err in logs:
                                service_error = f"Error in logs: {err}"
                                logger.warning(f"[HealthCheck] {service_name}: Found error '{err}' in logs")
                                break
                        if service_error:
                            break

                        # SUCCESS: Check if container is up and healthy
                        if "Up" in status:
                            # If no success indicators defined, just being "Up" is enough
                            if not success_indicators:
                                service_healthy = True
                                break
                            # Check for success indicators in logs
                            for indicator in success_indicators:
                                if indicator.lower() in logs.lower():
                                    service_healthy = True
                                    logger.info(f"[HealthCheck] {service_name}: Found success indicator '{indicator}'")
                                    break
                            if service_healthy:
                                break

                        # Wait and retry
                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval
                        if elapsed < max_wait:
                            yield f"        ... waiting ({elapsed}s/{max_wait}s)\n"

                    # Evaluate final status
                    if service_error:
                        yield f"     ❌ {service_name}: FAILED - {service_error}\n"
                        failure_detected = True
                        failed_service = svc
                        break
                    elif service_healthy:
                        yield f"     ✅ {service_name}: Healthy\n"
                    else:
                        # Timeout - do final check
                        status_cmd = f"docker ps -a --filter 'name=^{container_name}$' --format '{{{{.Status}}}}'"
                        _, final_status = self._run_shell_on_sandbox(status_cmd, working_dir=project_path, timeout=10)

                        # Also check logs one more time for errors
                        logs_cmd = f"docker logs {container_name} 2>&1 | tail -100"
                        _, final_logs = self._run_shell_on_sandbox(logs_cmd, working_dir=project_path, timeout=10)
                        final_logs = final_logs or ""

                        # Check for errors in final logs
                        has_error_in_logs = False
                        for err in error_indicators:
                            if err in final_logs:
                                has_error_in_logs = True
                                service_error = f"Error in logs after timeout: {err}"
                                logger.warning(f"[HealthCheck] {service_name}: Found error '{err}' in final logs")
                                break

                        if has_error_in_logs:
                            yield f"     ❌ {service_name}: Build/startup failed - {service_error}\n"
                            failure_detected = True
                            failed_service = svc
                            break
                        elif final_status and "Up" in final_status and "Restarting" not in final_status and "health: starting" not in final_status:
                            yield f"     ⚠️ {service_name}: Running (unconfirmed)\n"
                        else:
                            # Still "health: starting" after timeout = likely failing
                            yield f"     ❌ {service_name}: Timeout - health check never passed\n"
                            failure_detected = True
                            failed_service = svc
                            break

            # All services healthy
            if not failure_detected:
                containers_healthy = True
                yield f"\n  ✅ All services running and healthy!\n"
                break

            # Failure detected - trigger auto-fix
            fix_attempt += 1
            yield f"\n⚠️ Service failure detected. Collecting error logs...\n"

            # Get logs from failed service (we know exactly which one failed)
            logs_output = ""
            if failed_service:
                container_name = failed_service['container']
                service_name = failed_service['service']
                logs_cmd = f"docker logs {container_name} 2>&1 | tail -150"
                _, container_logs = self._run_shell_on_sandbox(logs_cmd, working_dir=project_path, timeout=30)
                if container_logs:
                    logs_output = f"\n=== {service_name} ({container_name}) LOGS ===\n{container_logs}\n"
            else:
                # Fallback: get logs from any failed containers
                for line in project_lines:
                    parts = line.split()
                    if not parts:
                        continue
                    container_name = parts[0]
                    if "Exit" in line or "Restarting" in line:
                        logs_cmd = f"docker logs {container_name} 2>&1 | tail -100"
                        _, container_logs = self._run_shell_on_sandbox(logs_cmd, working_dir=project_path, timeout=30)
                        if container_logs:
                            logs_output += f"\n=== {container_name} ===\n{container_logs}\n"

            # Show error logs
            log_lines = logs_output.strip().split('\n')[-50:]
            for line in log_lines:
                if line.strip():
                    yield f"  {line}\n"

            # Try auto-fix if we have attempts left
            if fix_attempt <= max_fix_attempts:
                yield f"\n🔧 AUTO-FIX: Attempt {fix_attempt}/{max_fix_attempts}\n"
                yield f"__FIX_STARTING__\n"

                # Import BoltFixer
                from app.services.bolt_fixer import BoltFixer
                bolt_fixer = BoltFixer()

                # Prepare payload for fixer
                payload = {
                    "stderr": logs_output,
                    "stdout": "",
                    "exit_code": 1,
                    "primary_error_type": "container_crash"
                }

                try:
                    fix_result = await bolt_fixer.fix_from_backend(
                        project_id=project_id,
                        project_path=Path(project_path),
                        payload=payload,
                        sandbox_file_writer=self._write_file_to_sandbox,  # Write directly to sandbox
                        sandbox_file_reader=self._read_file_from_sandbox,  # Read from sandbox
                        sandbox_file_lister=self._list_files_from_sandbox  # List files from sandbox
                    )

                    if fix_result.success and fix_result.files_modified:
                        yield f"✅ Fixed {len(fix_result.files_modified)} file(s):\n"
                        for f in fix_result.files_modified:
                            yield f"   📝 {f}\n"

                        # Track files for S3 sync after build succeeds
                        # NOTE: S3 sync is DEFERRED until build succeeds (see below)
                        # This ensures we don't persist broken fixes to S3
                        # Changes remain on EC2 sandbox for subsequent fix attempts
                        all_files_modified.extend(fix_result.files_modified)

                        # Rebuild and restart docker-compose
                        yield f"\n🔄 Rebuilding containers with fixes...\n"

                        # Stop containers
                        down_cmd = f"docker-compose -p {project_name} -f {compose_file} down --remove-orphans"
                        self._run_shell_on_sandbox(down_cmd, working_dir=project_path, timeout=30)

                        # Rebuild and start (use legacy build mode, force no-cache to pick up new files)
                        up_cmd = f"COMPOSE_DOCKER_CLI_BUILD=0 DOCKER_BUILDKIT=0 docker-compose -p {project_name} -f {compose_file} build --no-cache && COMPOSE_DOCKER_CLI_BUILD=0 DOCKER_BUILDKIT=0 docker-compose -p {project_name} -f {compose_file} up -d"
                        exit_code, output = self._run_shell_on_sandbox(up_cmd, working_dir=project_path, timeout=300)

                        if exit_code == 0:
                            yield f"  ✅ Containers rebuilt successfully\n"
                            yield f"  ⏳ Waiting for services to start...\n"
                            continue  # Loop back to check health again
                        else:
                            yield f"  ❌ Rebuild failed: {output[:200]}\n"
                    else:
                        yield f"❌ Could not generate fix: {fix_result.message}\n"
                        yield f"__FIX_FAILED__:{fix_result.message}\n"

                except Exception as fix_err:
                    logger.error(f"[ContainerExecutor] Auto-fix error: {fix_err}")
                    yield f"❌ Fix error: {fix_err}\n"
                    yield f"__FIX_FAILED__:{fix_err}\n"

            # If we've exhausted all attempts
            if fix_attempt >= max_fix_attempts:
                yield f"\n❌ Containers failed after {fix_attempt} fix attempts.\n"
                return

        if not containers_healthy:
            yield f"\n❌ Failed to start containers after {max_fix_attempts} attempts.\n"
            return

        # Sync fixed files to S3 AFTER build succeeds
        # This ensures we only persist fixes that actually work
        # NOTE: S3 sync ALWAYS happens for long-term archive (retrieval after months)
        # EFS benefit: Files are safe during build, even if S3 sync fails or user disconnects
        if all_files_modified:
            from app.core.config import settings as app_settings

            # Log EFS status
            if getattr(app_settings, 'EFS_ENABLED', False):
                yield f"\n💾 EFS: {len(all_files_modified)} file(s) already safe on shared storage\n"
                logger.info(f"[ContainerExecutor] EFS mode - files safe, now archiving to S3")

            # ALWAYS sync to S3 for long-term archive (user may return after months)
            yield f"📤 Archiving {len(all_files_modified)} fixed file(s) to S3...\n"
            try:
                from app.services.storage_service import storage_service

                synced_count = 0
                for file_path in all_files_modified:
                    full_path = f"{project_path}/{file_path}"
                    # Read file content from sandbox (handles remote mode)
                    cat_cmd = f"cat '{full_path}'"
                    exit_code, content = self._run_shell_on_sandbox(cat_cmd, working_dir=project_path, timeout=10)
                    if exit_code == 0 and content:
                        # upload_file expects bytes, not str
                        content_bytes = content.encode('utf-8') if isinstance(content, str) else content
                        await storage_service.upload_file(
                            project_id=project_id,
                            file_path=file_path,
                            content=content_bytes
                        )
                        synced_count += 1
                yield f"  ✅ {synced_count} file(s) archived to S3\n"
                logger.info(f"[ContainerExecutor] Archived {synced_count} fixed files to S3")
            except Exception as sync_err:
                logger.error(f"[ContainerExecutor] S3 archive error: {sync_err}")
                yield f"  ⚠️ S3 archive failed: {sync_err}\n"
                # With EFS, files are still safe even if S3 sync fails
                if getattr(app_settings, 'EFS_ENABLED', False):
                    yield f"  💾 Files still safe on EFS (will retry S3 archive later)\n"

        # Generate preview URL
        preview_url = _get_preview_url(frontend_port, project_id)

        # Store container info with activity tracking
        now = datetime.utcnow()
        self.active_containers[project_id] = {
            "compose_project": project_name,
            "compose_file": compose_file,
            "project_path": project_path,
            "frontend_port": frontend_port,
            "backend_port": backend_port,
            "technology": Technology.FULLSTACK,
            "fullstack_config": fullstack_config,
            "started_at": now,
            "last_activity": now,  # Track last user activity for idle detection
            "preview_url": preview_url,
            "docker_compose": True  # Flag for compose-based deployment
        }

        yield f"\n━━━ Full-Stack Application Running ━━━\n"
        yield f"  🌐 Frontend: http://localhost:{frontend_port}\n"
        yield f"  🔧 Backend: http://localhost:{backend_port}\n"
        yield f"\n🚀 Preview URL: {preview_url}\n"
        yield f"_PREVIEW_URL_:{preview_url}\n"

        # GAP 10 FIX: Health check before emitting __PREVIEW_READY__
        yield f"🔍 Verifying preview accessibility...\n"
        health_passed = False
        for attempt in range(5):
            try:
                await asyncio.sleep(1.0 + attempt * 0.5)
                health_ok = await check_preview_health(f"http://localhost:{frontend_port}", timeout=5.0)
                if health_ok:
                    health_passed = True
                    break
            except Exception:
                pass

        if health_passed:
            yield f"✅ Preview verified and ready!\n"
            yield f"__PREVIEW_READY__:{preview_url}\n"
        else:
            yield f"⏳ Preview may still be initializing...\n"
            yield f"__PREVIEW_READY__:{preview_url}\n"  # Still emit for frontend, but with warning

    async def _run_fullstack_legacy(
        self,
        project_id: str,
        project_path: str,
        fullstack_config: FullStackConfig
    ) -> AsyncGenerator[str, None]:
        """Legacy method - kept for reference. Uses individual container spawning."""
        database_container = None
        backend_container = None
        network_name = None
        db_container_name = None

        try:
            # Step 1: Create Docker network (only needed if database exists)
            if fullstack_config.database_type != DatabaseType.NONE:
                yield f"📡 Creating Docker network for database communication...\n"
                network_name = await self.create_project_network(project_id)

            # Step 2: Start database container (if needed)
            if fullstack_config.database_type != DatabaseType.NONE and fullstack_config.database_config:
                db_config = fullstack_config.database_config
                yield f"\n━━━ Starting Database ({fullstack_config.database_type.value}) ━━━\n"

                db_container_name = f"bharatbuild_{project_id[:8]}_db"
                db_host_port = self._get_available_port(db_config.port)

                yield f"  🗄️ Image: {db_config.image}\n"
                yield f"  🔌 Port: {db_host_port}\n"

                # Remove existing container with same name to avoid 409 Conflict
                self._remove_container_by_name(db_container_name)

                database_container = self.docker_client.containers.run(
                    db_config.image,
                    name=db_container_name,
                    detach=True,
                    remove=False,
                    ports={f"{db_config.port}/tcp": db_host_port},
                    environment=db_config.env_vars,
                    mem_limit="512m",
                    network=network_name,
                    labels={
                        "project_id": project_id,
                        "service": "database",
                        "managed_by": "bharatbuild"
                    }
                )

                yield f"  ✅ Database container started: {db_container_name}\n"

                # Wait for database to be healthy
                yield f"  ⏳ Waiting for database to be ready...\n"
                db_ready = await self._wait_for_database_ready(
                    database_container,
                    db_config,
                    timeout=60
                )

                if db_ready:
                    yield f"  ✅ Database is ready!\n"
                else:
                    yield f"  ⚠️ Database may still be starting (continuing anyway)...\n"

            # Step 3: Build frontend and copy to backend
            yield f"\n━━━ Building Frontend ({fullstack_config.frontend_tech.value}) ━━━\n"
            frontend_path = os.path.join(project_path, fullstack_config.frontend_path)
            backend_path = os.path.join(project_path, fullstack_config.backend_path)

            yield f"  📂 Frontend path: {frontend_path}\n"
            yield f"  🔧 Building frontend for production...\n"

            # Determine static folder path based on backend technology
            if fullstack_config.backend_tech == Technology.JAVA:
                static_folder = os.path.join(backend_path, "src", "main", "resources", "static")
            elif fullstack_config.backend_tech in [Technology.PYTHON, Technology.PYTHON_ML]:
                static_folder = os.path.join(backend_path, "static")
            elif fullstack_config.backend_tech == Technology.NODEJS:
                static_folder = os.path.join(backend_path, "public")
            elif fullstack_config.backend_tech == Technology.GO:
                static_folder = os.path.join(backend_path, "static")
            else:
                static_folder = os.path.join(backend_path, "static")

            # Create static folder if it doesn't exist
            os.makedirs(static_folder, exist_ok=True)
            yield f"  📁 Static folder: {static_folder}\n"

            # Build frontend using a temporary container
            frontend_config = TECHNOLOGY_CONFIGS.get(fullstack_config.frontend_tech)
            if not frontend_config:
                yield f"❌ Unsupported frontend technology: {fullstack_config.frontend_tech.value}\n"
                return

            build_container_name = f"bharatbuild_{project_id[:8]}_build"
            self._remove_container_by_name(build_container_name)

            # Backend URL for frontend build (will be relative in production)
            # Use relative path so frontend can call backend on same origin
            frontend_env = {
                "VITE_API_URL": "/api",
                "VITE_BACKEND_URL": "/api",
                "REACT_APP_API_URL": "/api",
                "NEXT_PUBLIC_API_URL": "/api",
                "NODE_ENV": "production",
            }

            yield f"  $ npm install && npm run build\n"

            # Run frontend build
            try:
                build_result = self.docker_client.containers.run(
                    frontend_config.image,
                    command="/bin/sh -c 'npm install && npm run build'",
                    name=build_container_name,
                    remove=False,  # Keep for copying files
                    working_dir="/app",
                    volumes={frontend_path: {"bind": "/app", "mode": "rw"}},
                    environment=frontend_env,
                    mem_limit="1g",
                    stdout=True,
                    stderr=True,
                )
                yield f"  ✅ Frontend build completed\n"
            except docker.errors.ContainerError as e:
                yield f"  ❌ Frontend build failed: {e.stderr.decode() if e.stderr else str(e)}\n"
                # Try to clean up
                try:
                    build_container = self.docker_client.containers.get(build_container_name)
                    build_container.remove(force=True)
                except:
                    pass
                raise

            # Clean up build container
            try:
                build_container = self.docker_client.containers.get(build_container_name)
                build_container.remove(force=True)
            except:
                pass

            # Copy built files from frontend/dist to backend's static folder
            frontend_dist = os.path.join(frontend_path, "dist")
            if not os.path.exists(frontend_dist):
                # Try 'build' folder (Create React App)
                frontend_dist = os.path.join(frontend_path, "build")

            if os.path.exists(frontend_dist):
                yield f"  📦 Copying build output to backend static folder...\n"
                import shutil
                # Clear existing static files
                if os.path.exists(static_folder):
                    for item in os.listdir(static_folder):
                        item_path = os.path.join(static_folder, item)
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                # Copy new files
                for item in os.listdir(frontend_dist):
                    src = os.path.join(frontend_dist, item)
                    dst = os.path.join(static_folder, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                yield f"  ✅ Frontend files copied to backend\n"
            else:
                yield f"  ⚠️ No dist/build folder found, skipping copy\n"

            # Step 4: Start backend container (serves both API and static files)
            yield f"\n━━━ Starting Backend ({fullstack_config.backend_tech.value}) ━━━\n"
            backend_config = TECHNOLOGY_CONFIGS.get(fullstack_config.backend_tech)

            if not backend_config:
                yield f"❌ Unsupported backend technology: {fullstack_config.backend_tech.value}\n"
                return

            backend_container_name = f"bharatbuild_{project_id[:8]}_app"
            backend_host_port = self._get_available_port(fullstack_config.backend_port)

            yield f"  📂 Backend path: {backend_path}\n"
            yield f"  🔌 Port: {backend_host_port}\n"
            yield f"  🔧 Building and starting backend...\n"

            if backend_config.build_command:
                yield f"  $ {backend_config.build_command}\n"

            # Prepare backend environment variables
            backend_env = {
                "PORT": str(fullstack_config.backend_port),
                "SERVER_PORT": str(fullstack_config.backend_port),
            }

            # Add database connection string if database is configured
            if fullstack_config.database_type != DatabaseType.NONE and fullstack_config.database_config and db_container_name:
                db_config = fullstack_config.database_config
                db_connection_string = db_config.connection_string_template.format(host=db_container_name)

                backend_env.update({
                    "DATABASE_URL": db_connection_string,
                    "DB_URL": db_connection_string,
                    "DB_HOST": db_container_name,
                    "DB_PORT": str(db_config.port),
                    "DB_NAME": "app_db",
                    "DB_USER": "bharatbuild",
                    "DB_PASSWORD": "bharatbuild123",
                })

                if fullstack_config.backend_tech == Technology.JAVA:
                    if fullstack_config.database_type == DatabaseType.POSTGRESQL:
                        backend_env["SPRING_DATASOURCE_URL"] = f"jdbc:postgresql://{db_container_name}:5432/app_db"
                        backend_env["SPRING_DATASOURCE_USERNAME"] = "bharatbuild"
                        backend_env["SPRING_DATASOURCE_PASSWORD"] = "bharatbuild123"
                    elif fullstack_config.database_type == DatabaseType.MYSQL:
                        backend_env["SPRING_DATASOURCE_URL"] = f"jdbc:mysql://{db_container_name}:3306/app_db"
                        backend_env["SPRING_DATASOURCE_USERNAME"] = "bharatbuild"
                        backend_env["SPRING_DATASOURCE_PASSWORD"] = "bharatbuild123"
                    elif fullstack_config.database_type == DatabaseType.MONGODB:
                        backend_env["SPRING_DATA_MONGODB_URI"] = db_connection_string

                yield f"  🔗 Database connection configured\n"

            # Remove existing container with same name
            self._remove_container_by_name(backend_container_name)

            # Build the run command
            run_command = f"/bin/sh -c '{backend_config.build_command} && {backend_config.run_command}'"

            backend_container = self.docker_client.containers.run(
                backend_config.image,
                command=run_command,
                name=backend_container_name,
                detach=True,
                remove=False,
                working_dir="/app",
                volumes={backend_path: {"bind": "/app", "mode": "rw"}},
                ports={f"{fullstack_config.backend_port}/tcp": backend_host_port},
                environment=backend_env,
                mem_limit="1g",  # Increased memory since serving both
                cpu_quota=int(backend_config.cpu_limit * 100000),
                network=network_name if network_name else None,
                labels={
                    "project_id": project_id,
                    "service": "fullstack",
                    "managed_by": "bharatbuild"
                }
            )

            yield f"  ✅ Application container started: {backend_container_name}\n"

            # Wait for backend to be healthy
            yield f"  ⏳ Waiting for application to be ready...\n"
            backend_ready = await self._wait_for_container_ready(
                backend_container,
                backend_host_port,
                timeout=180
            )

            if not backend_ready:
                yield f"  ⚠️ Application may still be starting...\n"
            else:
                yield f"  ✅ Application is ready on port {backend_host_port}\n"

            # Generate preview URL
            preview_url = _get_preview_url(backend_host_port, project_id)

            # Store container info
            self.active_containers[project_id] = {
                "backend_container": backend_container,
                "database_container": database_container,
                "host_port": backend_host_port,
                "backend_port": backend_host_port,
                "network": network_name,
                "technology": Technology.FULLSTACK,
                "fullstack_config": fullstack_config,
                "started_at": datetime.utcnow(),
                "preview_url": preview_url,
                "single_container": True  # Flag for new architecture
            }

            yield f"\n━━━ Full-Stack Application Running ━━━\n"
            yield f"  🌐 Application: http://localhost:{backend_host_port}\n"
            yield f"  📁 Frontend: Served from /static\n"
            yield f"  🔧 Backend API: Available at /api/*\n"
            if network_name:
                yield f"  📡 Network: {network_name}\n"
            yield f"\n🚀 Preview URL: {preview_url}\n"
            yield f"_PREVIEW_URL_:{preview_url}\n"

            # GAP 10 FIX: Health check before emitting __PREVIEW_READY__
            yield f"🔍 Verifying preview accessibility...\n"
            health_passed = False
            for attempt in range(5):
                try:
                    await asyncio.sleep(1.0 + attempt * 0.5)
                    health_ok = await check_preview_health(f"http://localhost:{backend_host_port}", timeout=5.0)
                    if health_ok:
                        health_passed = True
                        break
                except Exception:
                    pass

            if health_passed:
                yield f"✅ Preview verified and ready!\n"
            else:
                yield f"⏳ Preview may still be initializing...\n"
            yield f"__PREVIEW_READY__:{preview_url}\n"

        except Exception as e:
            logger.error(f"[ContainerExecutor] Full-stack project failed: {e}")
            yield f"\n❌ Error: {str(e)}\n"

            # Cleanup on failure
            if backend_container:
                try:
                    backend_container.stop(timeout=5)
                    backend_container.remove(force=True)
                except Exception:
                    pass

            if database_container:
                try:
                    database_container.stop(timeout=5)
                    database_container.remove(force=True)
                except Exception:
                    pass

            if network_name:
                try:
                    network = self.docker_client.networks.get(network_name)
                    network.remove()
                except Exception:
                    pass

    async def _wait_for_database_ready(
        self,
        container,
        db_config: DatabaseConfig,
        timeout: int = 60
    ) -> bool:
        """
        Wait for database container to be ready by running health check command.

        Args:
            container: Docker container object
            db_config: Database configuration with health check command
            timeout: Maximum seconds to wait

        Returns:
            True if database is ready, False if timeout
        """
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).seconds < timeout:
            try:
                # Check container is still running
                container.reload()
                if container.status != "running":
                    logger.warning(f"[ContainerExecutor] Database container stopped unexpectedly")
                    return False

                # Run health check command inside container
                exit_code, output = container.exec_run(
                    db_config.health_check_cmd,
                    demux=True
                )

                if exit_code == 0:
                    logger.info(f"[ContainerExecutor] Database {db_config.db_type.value} is ready")
                    return True

            except Exception as e:
                logger.debug(f"[ContainerExecutor] Database health check failed: {e}")

            await asyncio.sleep(2)

        logger.warning(f"[ContainerExecutor] Database health check timeout after {timeout}s")
        return False

    async def _wait_for_container_ready(
        self,
        container,
        port: int,
        timeout: int = 60
    ) -> bool:
        """Wait for container's service to be ready on specified port."""
        import aiohttp

        start_time = datetime.utcnow()
        check_url = f"http://localhost:{port}"

        while (datetime.utcnow() - start_time).seconds < timeout:
            try:
                # Check container is still running
                container.reload()
                if container.status != "running":
                    logger.warning(f"[ContainerExecutor] Container stopped unexpectedly")
                    return False

                # Try to connect to the service
                async with aiohttp.ClientSession() as session:
                    async with session.get(check_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status < 500:
                            return True
            except Exception:
                pass

            await asyncio.sleep(2)

        return False

    def _is_port_free(self, port: int) -> bool:
        """Check if a port is actually free on the host (not just Docker)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('0.0.0.0', port))
                return result != 0  # 0 means connection succeeded (port in use)
        except Exception:
            return True  # Assume free if check fails

    def _is_remote_sandbox(self) -> bool:
        """Check if we're using a remote Docker sandbox (EC2)."""
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        return bool(sandbox_docker_host and self.docker_client)

    def _normalize_depends_on_format(self, compose_file: str, compose_content: str) -> bool:
        """
        Convert dict-style depends_on to array format for docker-compose compatibility.

        AI sometimes generates depends_on in dict format:
            depends_on:
              db:
                condition: service_healthy
        OR just:
            depends_on:
              db:

        This method converts to array format:
            depends_on:
              - db

        Args:
            compose_file: Path to docker-compose.yml
            compose_content: Current content of the file

        Returns:
            True if file was modified, False otherwise
        """
        import re

        lines = compose_content.split('\n')
        new_lines = []
        i = 0
        modified = False

        while i < len(lines):
            line = lines[i]

            # Check if this is a depends_on line (with nothing after the colon)
            depends_match = re.match(r'^(\s*)depends_on:\s*$', line)
            if depends_match:
                depends_indent = len(depends_match.group(1))
                new_lines.append(line)
                i += 1

                # Collect all service names in this depends_on block
                services = []
                service_indent = None

                while i < len(lines):
                    next_line = lines[i]

                    # Empty line - skip
                    if not next_line.strip():
                        i += 1
                        continue

                    next_indent = len(next_line) - len(next_line.lstrip())

                    # If we're back to same or less indent, depends_on block is done
                    if next_indent <= depends_indent:
                        break

                    # Check if this line is already array format (starts with -)
                    if re.match(r'^\s+-\s+\w', next_line):
                        # Already array format, keep as-is
                        new_lines.append(next_line)
                        i += 1
                        continue

                    # Check if this is a service name line (key with colon, nothing after)
                    service_match = re.match(r'^(\s+)([\w][\w-]*):\s*$', next_line)
                    if service_match:
                        indent = service_match.group(1)
                        service_name = service_match.group(2)

                        # First service determines the indent level
                        if service_indent is None:
                            service_indent = len(indent)
                            services.append((indent, service_name))
                            modified = True
                        elif len(indent) == service_indent:
                            services.append((indent, service_name))
                        # Deeper indent = nested property (condition:), skip
                        i += 1
                    else:
                        # Other line (like condition: service_healthy), skip
                        i += 1

                # Add collected services in array format
                if services:
                    for indent, svc in services:
                        new_lines.append(f"{indent}- {svc}")
                continue
            else:
                new_lines.append(line)
            i += 1

        if modified:
            new_content = '\n'.join(new_lines)
            if self._write_file_to_sandbox(compose_file, new_content):
                logger.info(f"[ContainerExecutor] Normalized depends_on format in {compose_file}")
                return True
            else:
                logger.warning(f"[ContainerExecutor] Failed to write normalized compose file")
                return False

        return False

    # =============================================================================
    # DYNAMIC PORT ALLOCATION
    # =============================================================================
    # Prevents port conflicts by automatically assigning available ports at runtime
    # Works with any docker-compose.yml regardless of what ports are specified

    def _find_available_ports_on_sandbox(self, count: int = 5, start_port: int = 35000, end_port: int = 39999) -> List[int]:
        """
        Find available ports on the sandbox that are not in use.

        Uses `ss -tlnp` to check which ports are currently in use, then returns
        a list of available ports in the specified range.

        IMPORTANT: This function:
        1. Uses high port range (35000+) to avoid system port conflicts
        2. Pre-blocks all SYSTEM_PORTS (80, 443, 8080, etc.)

        Args:
            count: Number of available ports to find
            start_port: Start of port range to search (default 35000)
            end_port: End of port range to search (default 39999)

        Returns:
            List of available port numbers
        """
        try:
            # Ensure start_port is above system ports
            if start_port < 1024:
                start_port = 35000
                logger.warning(f"[ContainerExecutor] Sandbox start_port adjusted to {start_port} to avoid system ports")

            # Get list of ports currently in use
            cmd = "ss -tlnp 2>/dev/null | grep LISTEN | awk '{print $4}' | grep -oE '[0-9]+$' | sort -u"
            exit_code, output = self._run_shell_on_sandbox(cmd, timeout=10)

            # Pre-block all system ports for safety
            used_ports = set(SYSTEM_PORTS)
            if exit_code == 0 and output:
                for line in output.strip().split('\n'):
                    try:
                        port = int(line.strip())
                        used_ports.add(port)
                    except ValueError:
                        pass

            # Also check Docker containers for exposed ports
            docker_cmd = "docker ps --format '{{.Ports}}' 2>/dev/null | grep -oE ':[0-9]+' | tr -d ':' | sort -u"
            exit_code, docker_output = self._run_shell_on_sandbox(docker_cmd, timeout=10)
            if exit_code == 0 and docker_output:
                for line in docker_output.strip().split('\n'):
                    try:
                        port = int(line.strip())
                        used_ports.add(port)
                    except ValueError:
                        pass

            logger.info(f"[ContainerExecutor] Found {len(used_ports)} ports in use on sandbox")

            # Find available ports
            available = []
            for port in range(start_port, end_port + 1):
                if port not in used_ports:
                    available.append(port)
                    if len(available) >= count:
                        break

            logger.info(f"[ContainerExecutor] Found {len(available)} available ports: {available}")
            return available

        except Exception as e:
            logger.error(f"[ContainerExecutor] Error finding available ports: {e}")
            # Fallback: return sequential ports and hope for the best
            return list(range(start_port, start_port + count))

    def _allocate_dynamic_ports(
        self,
        compose_file: str,
        project_path: str
    ) -> Tuple[Dict[int, int], Optional[int], Optional[int]]:
        """
        Allocate dynamic ports for all services in docker-compose.yml.

        Reads the compose file, finds all port mappings, allocates available ports,
        and rewrites the compose file with the new port mappings.

        Args:
            compose_file: Path to docker-compose.yml
            project_path: Project directory path

        Returns:
            Tuple of (port_mapping, frontend_port, backend_port)
            - port_mapping: Dict mapping original host ports to new dynamic ports
            - frontend_port: The dynamic port allocated for frontend (or None)
            - backend_port: The dynamic port allocated for backend (or None)
        """
        import yaml
        import base64

        port_mapping = {}  # original_port -> new_port
        frontend_port = None
        backend_port = None

        try:
            # Read compose file
            logger.info(f"[ContainerExecutor] Reading compose file for port allocation: {compose_file}")
            compose_content = self._read_file_from_sandbox(compose_file)
            if not compose_content:
                logger.warning(f"[ContainerExecutor] Could not read compose file for port allocation: {compose_file}")
                return port_mapping, frontend_port, backend_port

            logger.info(f"[ContainerExecutor] Compose file read successfully, {len(compose_content)} bytes")
            compose_data = yaml.safe_load(compose_content)
            if not compose_data or 'services' not in compose_data:
                logger.warning(f"[ContainerExecutor] Invalid compose data or no services found")
                return port_mapping, frontend_port, backend_port

            logger.info(f"[ContainerExecutor] Found {len(compose_data.get('services', {}))} services in compose file")

            # Collect all port mappings that need dynamic allocation
            ports_needed = []  # List of (service_name, port_index, original_host_port, container_port)

            for service_name, service in compose_data.get('services', {}).items():
                if not isinstance(service, dict):
                    continue

                ports = service.get('ports', [])
                for idx, port_mapping_str in enumerate(ports):
                    if isinstance(port_mapping_str, str) and ':' in port_mapping_str:
                        parts = port_mapping_str.split(':')
                        if len(parts) >= 2:
                            try:
                                # Handle formats: "80:80", "3000:3000", "0.0.0.0:80:80"
                                if len(parts) == 3:
                                    # Format: "0.0.0.0:80:80"
                                    host_port_str = parts[1]
                                    container_port = parts[2]
                                else:
                                    # Format: "80:80" or "${PORT:-8080}:8080"
                                    host_port_str = parts[0]
                                    container_port = parts[1]

                                # Handle environment variable syntax: ${VAR:-default}
                                # Extract the default value after :-
                                if ':-' in host_port_str:
                                    # ${PORT:-8080} -> extract 8080
                                    default_match = host_port_str.split(':-')[-1].rstrip('}')
                                    host_port = int(default_match)
                                    logger.info(f"[ContainerExecutor] Parsed env var port: {host_port_str} -> {host_port}")
                                elif host_port_str.startswith('${'):
                                    # ${PORT} without default - use container port as fallback
                                    container_port_clean = container_port.split('/')[0]
                                    host_port = int(container_port_clean)
                                    logger.info(f"[ContainerExecutor] Env var without default, using container port: {host_port}")
                                else:
                                    host_port = int(host_port_str)

                                ports_needed.append((service_name, idx, host_port, container_port))
                                logger.info(f"[ContainerExecutor] Found port mapping: {service_name} -> {host_port}:{container_port}")
                            except ValueError as e:
                                logger.warning(f"[ContainerExecutor] Could not parse port: {port_mapping_str} - {e}")
                    elif isinstance(port_mapping_str, int):
                        # Single port number (same for host and container)
                        ports_needed.append((service_name, idx, port_mapping_str, str(port_mapping_str)))
                        logger.info(f"[ContainerExecutor] Found single port: {service_name} -> {port_mapping_str}")

            if not ports_needed:
                logger.info("[ContainerExecutor] No port mappings found in compose file")
                return port_mapping, frontend_port, backend_port

            # Check for system ports that MUST be remapped
            system_ports_found = [p for _, _, p, _ in ports_needed if p in SYSTEM_PORTS]
            if system_ports_found:
                logger.warning(f"[ContainerExecutor] Found SYSTEM PORTS that must be remapped: {system_ports_found}")

            # Find available ports - request extra to ensure system ports get remapped
            available_ports = self._find_available_ports_on_sandbox(count=len(ports_needed) + 5)

            if len(available_ports) < len(ports_needed):
                logger.warning(f"[ContainerExecutor] Not enough available ports: need {len(ports_needed)}, found {len(available_ports)}")
                # Generate fallback ports for any remaining (especially system ports)
                fallback_start = 36000
                while len(available_ports) < len(ports_needed):
                    if fallback_start not in available_ports:
                        available_ports.append(fallback_start)
                    fallback_start += 1

            # Allocate ports and update compose data
            modified = False
            for i, (service_name, port_idx, original_port, container_port) in enumerate(ports_needed):
                if i < len(available_ports):
                    new_port = available_ports[i]
                    port_mapping[original_port] = new_port

                    # Update compose data
                    service = compose_data['services'][service_name]
                    # Remove /tcp or /udp suffix if present for container port
                    container_port_clean = container_port.split('/')[0]
                    service['ports'][port_idx] = f"{new_port}:{container_port}"
                    modified = True

                    # Log system port remapping explicitly
                    if original_port in SYSTEM_PORTS:
                        logger.info(f"[ContainerExecutor] SYSTEM PORT REMAPPED: {service_name}: {original_port}:{container_port} -> {new_port}:{container_port}")
                    else:
                        logger.info(f"[ContainerExecutor] {service_name}: {original_port}:{container_port} -> {new_port}:{container_port}")

                    # Track frontend/backend ports
                    if any(name in service_name.lower() for name in ['frontend', 'web', 'ui', 'nginx', 'app']):
                        if frontend_port is None:  # First match
                            frontend_port = new_port
                    elif any(name in service_name.lower() for name in ['backend', 'api', 'server']):
                        if backend_port is None:  # First match
                            backend_port = new_port
                else:
                    # CRITICAL: System ports MUST be remapped - fail loudly if we can't
                    if original_port in SYSTEM_PORTS:
                        logger.error(f"[ContainerExecutor] CRITICAL: Could not remap system port {original_port} for {service_name}")
                        # Generate emergency fallback port
                        emergency_port = 37000 + i
                        port_mapping[original_port] = emergency_port
                        service = compose_data['services'][service_name]
                        container_port_clean = container_port.split('/')[0]
                        service['ports'][port_idx] = f"{emergency_port}:{container_port}"
                        modified = True
                        logger.warning(f"[ContainerExecutor] EMERGENCY: {service_name}: {original_port} -> {emergency_port}")

            # Write updated compose file
            if modified:
                updated_yaml = yaml.dump(compose_data, default_flow_style=False, sort_keys=False)
                encoded = base64.b64encode(updated_yaml.encode()).decode()
                write_cmd = f'echo "{encoded}" | base64 -d > "{compose_file}"'
                exit_code, _ = self._run_shell_on_sandbox(write_cmd, working_dir=project_path, timeout=10)

                if exit_code == 0:
                    logger.info(f"[ContainerExecutor] Updated compose file with dynamic ports: {port_mapping}")
                else:
                    logger.error("[ContainerExecutor] Failed to write updated compose file")
                    return {}, None, None

            return port_mapping, frontend_port, backend_port

        except Exception as e:
            logger.error(f"[ContainerExecutor] Error allocating dynamic ports: {e}")
            return {}, None, None

    def _write_file_to_sandbox(self, file_path: str, content: str) -> bool:
        """
        Write a file to the sandbox filesystem.

        Handles both local and remote modes:
        - Local: Uses standard open() to write
        - Remote: Uses a helper container to write via echo/cat

        Args:
            file_path: Absolute path to the file (e.g., /tmp/sandbox/workspace/.../file.txt)
            content: Content to write to the file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._is_remote_sandbox():
                # Local mode - direct write
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content)
                logger.info(f"[ContainerExecutor] Wrote file locally: {file_path}")
                return True

            # Remote mode - use helper container
            # Escape content for shell (use base64 to handle special chars)
            import base64
            encoded_content = base64.b64encode(content.encode()).decode()

            # Create directory and write file
            script = f'''
mkdir -p "$(dirname {file_path})"
echo "{encoded_content}" | base64 -d > "{file_path}"
'''

            sandbox_base = _get_sandbox_base()
            logger.info(f"[ContainerExecutor] Writing file to sandbox: {file_path} (sandbox_base: {sandbox_base})")

            self.docker_client.containers.run(
                "alpine:latest",
                ["-c", script],
                entrypoint="/bin/sh",
                volumes={sandbox_base: {"bind": sandbox_base, "mode": "rw"}},
                remove=True,
                detach=False
            )

            # Verify file was written using separate check
            if self._file_exists_on_sandbox(file_path):
                logger.info(f"[ContainerExecutor] ✅ Wrote file via helper container: {file_path}")
                return True
            else:
                logger.error(f"[ContainerExecutor] ❌ Write failed - file not found: {file_path}")
                return False

        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to write file {file_path}: {e}")
            return False

    def _run_shell_on_sandbox(
        self,
        command: str,
        working_dir: str = None,
        timeout: int = 60
    ) -> Tuple[int, str]:
        """
        Run a shell command on the sandbox filesystem.

        Handles both local and remote modes:
        - Local: Uses subprocess
        - Remote: Uses a helper container

        Args:
            command: Shell command to run
            working_dir: Working directory for the command
            timeout: Timeout in seconds

        Returns:
            Tuple of (exit_code, output)
        """
        try:
            if not self._is_remote_sandbox():
                # Local mode - use subprocess
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                output = result.stdout + result.stderr
                return result.returncode, output

            # Remote mode - use helper container with docker/docker-compose from host
            cd_cmd = f'cd "{working_dir}" && ' if working_dir else ''

            # If command uses docker-compose, wrap with fallback to handle binary compatibility
            if "docker-compose" in command:
                # Try mounted binary first, fallback to docker compose v2 syntax
                wrapped_cmd = f'''
if /usr/local/bin/docker-compose --version >/dev/null 2>&1; then
    {command}
elif docker compose version >/dev/null 2>&1; then
    {command.replace("docker-compose", "docker compose")}
else
    echo "ERROR: docker-compose not available" && exit 1
fi
'''
                script = f'{cd_cmd}{wrapped_cmd}'
            else:
                script = f'{cd_cmd}{command}'

            logger.info(f"[ContainerExecutor] Running via helper container: {script[:100]}...")

            # Use alpine image with host's docker-compose binary mounted
            # EC2 has docker-compose at /usr/local/bin/docker-compose and alpine is pre-pulled
            sandbox_base = _get_sandbox_base()

            # Volume mounts: workspace, docker socket, and host's docker-compose binary
            volumes = {
                sandbox_base: {"bind": sandbox_base, "mode": "rw"},
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
                "/usr/local/bin/docker-compose": {"bind": "/usr/local/bin/docker-compose", "mode": "ro"},
                "/usr/bin/docker": {"bind": "/usr/bin/docker", "mode": "ro"},
            }

            # Try glibc-based images first (better binary compatibility with host binaries)
            # python:3.11-slim is Debian-based (glibc), alpine uses musl which may not work
            helper_images = ["python:3.11-slim", "node:18-alpine", "alpine:latest"]
            container = None
            last_error = None

            for helper_image in helper_images:
                try:
                    logger.info(f"[ContainerExecutor] Trying helper image: {helper_image}")
                    container = self.docker_client.containers.create(
                        helper_image,
                        ["-c", script],
                        entrypoint="/bin/sh",
                        volumes=volumes,
                        network_mode="host"
                    )
                    break  # Success, exit loop
                except (docker.errors.ImageNotFound, docker.errors.NotFound, docker.errors.APIError) as e:
                    last_error = e
                    err_msg = str(e).lower()
                    if "no such image" in err_msg or "not found" in err_msg:
                        logger.warning(f"[ContainerExecutor] Image {helper_image} not found, trying next...")
                        continue
                    else:
                        raise  # Re-raise if it's not an image error

            if container is None:
                raise RuntimeError(f"Failed to create helper container with any available image: {last_error}")

            try:
                # Start and wait for completion
                container.start()
                exit_result = container.wait(timeout=timeout)
                exit_code = exit_result.get('StatusCode', 0)

                # Get logs (both stdout and stderr)
                output = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')

                logger.info(f"[ContainerExecutor] Ran command via helper: {command[:50]}... exit_code={exit_code}, output_len={len(output)}")
                logger.debug(f"[ContainerExecutor] Full output: {output[:500]}")

                return exit_code, output

            finally:
                # Always cleanup
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        except subprocess.TimeoutExpired:
            return 1, "Command timed out"
        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to run command: {e}")
            return 1, str(e)

    async def _apply_ai_fix_for_compose(
        self,
        project_id: str,
        project_path: str,
        error_message: str
    ) -> bool:
        """
        Use AI (ProductionFixerAgent) to fix docker-compose.yml or Dockerfile issues.

        This is called when DockerInfraFixer cannot fix the issue (code/config problem).

        PROTECTION: Backs up docker-compose.yml before AI fix and validates after.
        If AI corrupts the file, backup is restored.

        Args:
            project_id: Project identifier
            project_path: Path to project directory
            error_message: Docker Compose error output

        Returns:
            True if fix was applied, False otherwise
        """
        from pathlib import Path
        import yaml

        try:
            logger.info(f"[ContainerExecutor] Attempting AI fix for compose error")

            # Use sandbox file reader for remote sandbox support
            # This works both locally and on remote EC2 sandbox
            def read_file(rel_path: str) -> Optional[str]:
                abs_path = f"{project_path}/{rel_path}"
                content = self._read_file_from_sandbox(abs_path)
                if content:
                    logger.info(f"[ContainerExecutor] Read file from sandbox: {rel_path}")
                return content

            # Read docker-compose.yml and Dockerfile(s)
            dockerfile_rel_paths = [
                "Dockerfile",
                "frontend/Dockerfile",
                "backend/Dockerfile",
            ]

            file_contents = {}
            original_compose_content = None
            original_compose_services = set()

            # Read docker-compose.yml and create backup
            original_compose_content = read_file("docker-compose.yml")
            if original_compose_content:
                file_contents["docker-compose.yml"] = original_compose_content
                # Parse to get original service names for validation
                try:
                    original_data = yaml.safe_load(original_compose_content)
                    if original_data and 'services' in original_data:
                        original_compose_services = set(original_data['services'].keys())
                        logger.info(f"[ContainerExecutor] Original compose has {len(original_compose_services)} services: {original_compose_services}")
                except yaml.YAMLError:
                    pass

            # Read Dockerfiles
            for df_rel_path in dockerfile_rel_paths:
                content = read_file(df_rel_path)
                if content:
                    file_contents[df_rel_path] = content

            # Detect build errors across ALL technologies and read relevant config files
            # This enables AI fixer to see and fix build configuration issues

            # Build error patterns for ALL supported technologies
            build_error_patterns = [
                # JavaScript/TypeScript
                'error TS', 'tsc &&', 'npm run build', 'vite build', 'webpack',
                'tsconfig', 'Cannot find module', 'Module not found',
                # Java/Kotlin
                'BUILD FAILURE', 'COMPILATION ERROR', 'cannot find symbol',
                'package does not exist', 'mvn ', 'gradle', 'pom.xml',
                'java.lang.', 'ClassNotFoundException', 'NoClassDefFoundError',
                # Python
                'ModuleNotFoundError', 'ImportError', 'SyntaxError', 'pip install',
                'requirements.txt', 'setup.py', 'pyproject.toml',
                # Go
                'go build', 'go.mod', 'go.sum', 'undefined:', 'cannot find package',
                # Rust
                'cargo build', 'Cargo.toml', 'error[E', 'cannot find',
                # Ruby
                'Gemfile', 'bundle install', 'LoadError',
                # PHP
                'composer', 'Fatal error:', 'Class .* not found',
                # .NET/C#
                'dotnet build', 'MSBuild', 'error CS', '.csproj',
                # AI/ML (Python-based)
                'tensorflow', 'torch', 'keras', 'sklearn', 'numpy', 'pandas',
                'CUDA', 'cudnn', 'GPU', 'environment.yml', 'conda',
                'model', 'training', 'inference',
                # Blockchain/Web3
                'solidity', 'hardhat', 'truffle', 'foundry', 'ethers',
                'web3', 'contract', 'deploy', 'compile',
                'ParserError', 'DeclarationError', 'TypeError',
                # Cybersecurity tools
                'cryptography', 'ssl', 'certificate', 'authentication',
                'authorization', 'jwt', 'oauth',
                # Mobile (Flutter/React Native)
                'flutter', 'dart', 'pubspec.yaml', 'react-native', 'expo',
                'android', 'ios', 'xcode', 'gradle',
            ]
            is_build_error = any(p in error_message for p in build_error_patterns)

            if is_build_error:
                logger.info("[ContainerExecutor] Detected build error, reading config files for all technologies...")

                # Config files for ALL technologies (relative paths)
                build_config_rel_paths = [
                    # JavaScript/TypeScript (frontend and root)
                    "frontend/tsconfig.json",
                    "frontend/tsconfig.node.json",
                    "frontend/vite.config.ts",
                    "frontend/package.json",
                    "frontend/webpack.config.js",
                    "tsconfig.json",
                    "tsconfig.node.json",
                    "vite.config.ts",
                    "package.json",
                    "webpack.config.js",
                    # Java/Maven/Gradle (backend)
                    "backend/pom.xml",
                    "backend/build.gradle",
                    "backend/build.gradle.kts",
                    "pom.xml",
                    "build.gradle",
                    # Python
                    "backend/requirements.txt",
                    "backend/pyproject.toml",
                    "backend/setup.py",
                    "requirements.txt",
                    "pyproject.toml",
                    # Go
                    "backend/go.mod",
                    "backend/go.sum",
                    "go.mod",
                    # Rust
                    "backend/Cargo.toml",
                    "Cargo.toml",
                    # Ruby
                    "Gemfile",
                    "backend/Gemfile",
                    # PHP
                    "composer.json",
                    "backend/composer.json",
                    # AI/ML (Python + Conda)
                    "environment.yml",
                    "conda.yaml",
                    "model/config.yaml",
                    "model/config.json",
                    "config/model.yaml",
                    "training/config.yaml",
                    # Blockchain/Web3
                    "hardhat.config.js",
                    "hardhat.config.ts",
                    "truffle-config.js",
                    "foundry.toml",
                    "brownie-config.yaml",
                    # Mobile (Flutter)
                    "pubspec.yaml",
                    "pubspec.lock",
                    "android/build.gradle",
                    "ios/Podfile",
                    # Mobile (React Native)
                    "app.json",
                    "metro.config.js",
                    "babel.config.js",
                ]

                # Read config files using sandbox reader
                for rel_path in build_config_rel_paths:
                    if rel_path not in file_contents:  # Avoid duplicates
                        content = read_file(rel_path)
                        if content:
                            file_contents[rel_path] = content

                # Also extract and read files mentioned directly in error message
                # e.g., "src/App.tsx:15:3: error TS..." -> read src/App.tsx
                error_file_pattern = r'([a-zA-Z0-9_\-./\\]+\.(?:tsx?|jsx?|py|java|go|rs|rb|php|cs|vue|svelte))(?::\d+|[\(\[])'
                import re
                error_files = re.findall(error_file_pattern, error_message)
                for ef in error_files:
                    ef_clean = ef.strip().replace('\\', '/')
                    if ef_clean.startswith('./'):
                        ef_clean = ef_clean[2:]
                    if ef_clean not in file_contents:
                        content = read_file(ef_clean)
                        # Limit file size to prevent token overflow
                        if content and len(content) < 50000:
                            file_contents[ef_clean] = content

                # CRITICAL FIX: For type/model errors, include relevant type definition files
                # Supports ALL common technologies students use
                type_error_patterns = [
                    # TypeScript/JavaScript
                    'TS2339', 'does not exist on type', 'Property',
                    # Java
                    'cannot find symbol', 'incompatible types', 'cannot resolve',
                    # Python
                    'has no attribute', 'missing required argument', 'TypeError', 'NameError',
                    # Go
                    'undefined:', 'has no field or method',
                    # C#/.NET
                    'does not contain a definition', 'CS0117',
                    # Ruby
                    'undefined method', 'NoMethodError',
                    # PHP
                    'Undefined property', 'Call to undefined method',
                ]
                is_type_error = any(err in error_message for err in type_error_patterns)

                if is_type_error:
                    # Try to find type definition files for ALL technologies
                    # These must be actual FILES, not directories
                    types_paths = [
                        # TypeScript/React/Vue/Angular
                        'src/types/index.ts', 'src/types.ts', 'src/interfaces/index.ts',
                        'frontend/src/types/index.ts', 'frontend/src/types.ts',
                        # Python (FastAPI/Django)
                        'app/models.py', 'app/schemas.py', 'models.py', 'schemas.py',
                        'backend/app/models.py', 'backend/app/schemas.py',
                        # Go
                        'models/models.go', 'internal/models/models.go',
                        # Node.js/Express
                        'src/models/index.js', 'models/index.js', 'src/models/index.ts',
                    ]
                    types_found = False
                    for types_path in types_paths:
                        if types_path not in file_contents:
                            content = read_file(types_path)
                            if content:
                                file_contents[types_path] = content
                                logger.info(f"[ContainerExecutor] Included types/model file: {types_path}")
                                types_found = True
                                break

                    # If no types file found, try to find from error message paths
                    # Java/C#/Ruby/PHP models are often in the error path itself
                    if not types_found:
                        logger.debug("[ContainerExecutor] No standard types file found, relying on error file extraction")

            if not file_contents:
                logger.warning("[ContainerExecutor] No docker files found to fix")
                return False

            # Create context for ProductionFixerAgent
            # Determine error type for better AI understanding
            error_type = "build_error" if is_build_error else "docker_compose_error"
            request_msg = (
                f"Fix the build/compilation error. Check config files (tsconfig.json, pom.xml, requirements.txt, etc):\n\n{error_message}"
                if is_build_error
                else f"Fix the docker-compose or Dockerfile error:\n\n{error_message}"
            )

            context = AgentContext(
                project_id=project_id,
                user_request=request_msg,
                metadata={
                    "error_message": error_message,
                    "error_type": error_type,
                    "stack_trace": error_message,
                    "file_contents": file_contents,
                    "affected_files": list(file_contents.keys()),
                    "project_files": file_contents,
                    "project_path": project_path,  # For extracting user_id
                }
            )

            # Call ProductionFixerAgent
            logger.info(f"[ContainerExecutor] Calling ProductionFixerAgent for docker files")
            result = await production_fixer_agent.process(context)

            if not result or not result.get("success"):
                logger.warning(f"[ContainerExecutor] AI fixer returned no success: {result}")
                return False

            # Apply fixes
            fixed_files = result.get("fixed_files", [])
            patches = result.get("patches", [])

            if not fixed_files and not patches:
                logger.warning("[ContainerExecutor] AI fixer returned no fixes")
                return False

            applied_any = False

            # PROTECTION: Block full file replacement for docker-compose.yml
            # The AI fixer has corrupted docker-compose.yml by replacing it entirely.
            # Only allow patches (targeted changes) for docker-compose.yml
            docker_compose_in_fixed = any(
                "docker-compose" in f.get("path", "").lower()
                for f in fixed_files
            )
            if docker_compose_in_fixed and original_compose_content:
                logger.warning(
                    "[ContainerExecutor] BLOCKING full docker-compose.yml replacement - "
                    "AI must use patches for docker-compose.yml, not full file replacement"
                )
                # Remove docker-compose.yml from fixed_files
                fixed_files = [
                    f for f in fixed_files
                    if "docker-compose" not in f.get("path", "").lower()
                ]

            # Apply full file replacements with VALIDATION for docker-compose.yml
            for file_info in fixed_files:
                file_path = file_info.get("path", "")
                content = file_info.get("content", "")

                if not file_path or not content:
                    continue

                # Determine absolute path
                if file_path.startswith("/"):
                    abs_path = Path(file_path)
                else:
                    abs_path = Path(project_path) / file_path

                # SAFETY VALIDATION for docker-compose.yml - STRICT PROTECTION
                # The AI fixer has been known to CORRUPT docker-compose.yml by:
                # - Deleting services (frontend, backend, db, redis)
                # - Changing 'image:' to 'build: .' incorrectly
                # - Removing networks, volumes, healthchecks
                # We MUST be extremely strict here.
                if "docker-compose" in file_path.lower():
                    try:
                        new_data = yaml.safe_load(content)
                        if not new_data:
                            logger.warning(f"[ContainerExecutor] AI returned empty docker-compose.yml - REJECTING")
                            continue
                        if 'services' not in new_data:
                            logger.warning(f"[ContainerExecutor] AI docker-compose.yml missing 'services' key - REJECTING")
                            continue

                        new_services = set(new_data.get('services', {}).keys())

                        # STRICT CHECK 1: No service removal allowed
                        # AI must preserve ALL original services
                        if original_compose_services:
                            missing_services = original_compose_services - new_services
                            if missing_services:
                                logger.warning(
                                    f"[ContainerExecutor] AI DELETED services: {missing_services} - REJECTING"
                                    f" (Original: {original_compose_services}, New: {new_services})"
                                )
                                continue

                        # STRICT CHECK 2: No drastic service reduction (catches edge cases)
                        if original_compose_services and len(new_services) < len(original_compose_services):
                            logger.warning(
                                f"[ContainerExecutor] AI reduced services from {len(original_compose_services)} to {len(new_services)} - REJECTING"
                            )
                            continue

                        # STRICT CHECK 3: Don't allow 'build: .' if original used 'image:'
                        # This catches the nginx corruption where 'image: nginx:alpine' became 'build: .'
                        for service_name, service_config in new_data.get('services', {}).items():
                            if isinstance(service_config, dict) and 'build' in service_config:
                                build_val = service_config.get('build')
                                # Check if original service used 'image:' instead of 'build:'
                                if original_compose_content:
                                    try:
                                        orig_data = yaml.safe_load(original_compose_content)
                                        orig_service = orig_data.get('services', {}).get(service_name, {})
                                        if 'image' in orig_service and 'build' not in orig_service:
                                            logger.warning(
                                                f"[ContainerExecutor] AI changed {service_name} from 'image:' to 'build:' - REJECTING"
                                            )
                                            continue
                                    except:
                                        pass

                        # STRICT CHECK 4: File size sanity check (more aggressive)
                        if original_compose_content:
                            size_ratio = len(content) / len(original_compose_content)
                            if size_ratio < 0.5:  # New file is less than 50% of original
                                logger.warning(
                                    f"[ContainerExecutor] AI docker-compose.yml too small ({len(content)} vs {len(original_compose_content)} bytes, ratio {size_ratio:.2f}) - REJECTING"
                                )
                                continue

                        logger.info(f"[ContainerExecutor] AI docker-compose.yml passed STRICT validation (services: {new_services})")

                    except yaml.YAMLError as yaml_err:
                        logger.warning(f"[ContainerExecutor] AI returned invalid YAML for docker-compose.yml - REJECTING: {yaml_err}")
                        continue

                # Write fix to sandbox using sandbox file writer
                abs_path_str = f"{project_path}/{file_path}" if not file_path.startswith("/") else file_path
                if self._write_file_to_sandbox(abs_path_str, content):
                    logger.info(f"[ContainerExecutor] AI fix applied to sandbox: {file_path}")
                    applied_any = True
                else:
                    logger.error(f"[ContainerExecutor] Failed to write AI fix to sandbox: {file_path}")

            # Apply patches (unified diff format)
            for patch_info in patches:
                file_path = patch_info.get("path", "")
                patch_content = patch_info.get("patch", "")

                if not file_path or not patch_content:
                    continue

                # Determine absolute path for sandbox
                abs_path_str = f"{project_path}/{file_path}" if not file_path.startswith("/") else file_path

                try:
                    # Read original content from sandbox
                    original_content = self._read_file_from_sandbox(abs_path_str)
                    if original_content:
                        patched_content = self._apply_unified_diff(original_content, patch_content)
                        if patched_content and patched_content != original_content:
                            if self._write_file_to_sandbox(abs_path_str, patched_content):
                                logger.info(f"[ContainerExecutor] Applied patch to sandbox: {file_path}")
                                applied_any = True
                            else:
                                logger.error(f"[ContainerExecutor] Failed to write patch to sandbox: {file_path}")
                        else:
                            logger.warning(f"[ContainerExecutor] Patch produced no changes for {file_path}")
                    else:
                        logger.warning(f"[ContainerExecutor] Cannot patch - file not found on sandbox: {file_path}")
                except Exception as e:
                    logger.error(f"[ContainerExecutor] Failed to apply patch to {file_path}: {e}")

            return applied_any

        except Exception as e:
            logger.error(f"[ContainerExecutor] AI fix error: {e}", exc_info=True)
            return False

    def _apply_unified_diff(self, original: str, patch: str) -> Optional[str]:
        """
        Apply a unified diff patch to original content.

        Args:
            original: Original file content
            patch: Unified diff patch content

        Returns:
            Patched content or None if patch failed
        """
        import re

        try:
            lines = original.splitlines(keepends=True)
            # Ensure last line has newline for consistent handling
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'

            # Parse unified diff hunks
            # Format: @@ -start,count +start,count @@
            hunk_pattern = r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@'
            hunks = list(re.finditer(hunk_pattern, patch))

            if not hunks:
                # No hunks found - try simple line replacement
                logger.warning("[ContainerExecutor] No unified diff hunks found in patch")
                return None

            # Apply hunks in reverse order to preserve line numbers
            patch_lines = patch.splitlines(keepends=True)
            result_lines = lines.copy()
            offset = 0

            for hunk_match in hunks:
                old_start = int(hunk_match.group(1)) - 1  # Convert to 0-indexed
                old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_start = int(hunk_match.group(3)) - 1
                new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1

                # Find hunk content (lines after @@ header until next @@ or end)
                hunk_start_pos = patch.find(hunk_match.group(0))
                next_hunk_pos = len(patch)
                for next_hunk in hunks:
                    next_pos = patch.find(next_hunk.group(0))
                    if next_pos > hunk_start_pos:
                        next_hunk_pos = min(next_hunk_pos, next_pos)
                        break

                hunk_content = patch[hunk_start_pos:next_hunk_pos]
                hunk_lines = hunk_content.splitlines(keepends=True)[1:]  # Skip @@ line

                # Extract additions and removals
                new_lines = []
                for line in hunk_lines:
                    if line.startswith('+') and not line.startswith('+++'):
                        new_lines.append(line[1:])  # Remove + prefix
                    elif line.startswith(' '):
                        new_lines.append(line[1:])  # Context line, remove space prefix
                    # Lines starting with - are removed (not added to new_lines)

                # Apply the hunk
                adjusted_start = old_start + offset
                result_lines[adjusted_start:adjusted_start + old_count] = new_lines
                offset += len(new_lines) - old_count

            return ''.join(result_lines)

        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to apply unified diff: {e}")
            return None

    def _file_exists_on_sandbox(self, file_path: str) -> bool:
        """
        Check if a file exists on the sandbox filesystem.

        Args:
            file_path: Absolute path to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            if not self._is_remote_sandbox():
                exists = os.path.exists(file_path)
                logger.debug(f"[ContainerExecutor] Local file check: {file_path} -> {exists}")
                return exists

            # Remote mode - use helper container with multiple checks
            logger.info(f"[ContainerExecutor] Checking file in remote sandbox: {file_path}")

            # First try: use test -f
            try:
                result = self.docker_client.containers.run(
                    "alpine:latest",
                    ["-c", f'test -f "{file_path}" && echo "EXISTS" || echo "MISSING"'],
                    entrypoint="/bin/sh",
                    volumes={_get_sandbox_base(): {"bind": _get_sandbox_base(), "mode": "ro"}},
                    remove=True,
                    detach=False
                )

                output = result.decode() if isinstance(result, bytes) else str(result)
                exists = "EXISTS" in output
                logger.info(f"[ContainerExecutor] File check result: {file_path} -> {exists} (output: {output.strip()})")

                if exists:
                    return True

            except Exception as e1:
                logger.warning(f"[ContainerExecutor] test -f check failed: {e1}")

            # Second try: use ls to check
            try:
                result = self.docker_client.containers.run(
                    "alpine:latest",
                    ["-c", f'ls -la "{file_path}" 2>&1'],
                    entrypoint="/bin/sh",
                    volumes={_get_sandbox_base(): {"bind": _get_sandbox_base(), "mode": "ro"}},
                    remove=True,
                    detach=False
                )

                output = result.decode() if isinstance(result, bytes) else str(result)
                # If ls succeeds, the file exists
                exists = "No such file" not in output and "cannot access" not in output
                logger.info(f"[ContainerExecutor] ls check result: {file_path} -> {exists}")

                if exists:
                    return True

            except Exception as e2:
                logger.warning(f"[ContainerExecutor] ls check failed: {e2}")

            # Third try: list directory to see what files exist
            try:
                dir_path = os.path.dirname(file_path)
                result = self.docker_client.containers.run(
                    "alpine:latest",
                    ["-c", f'ls -la "{dir_path}" 2>&1 | head -20'],
                    entrypoint="/bin/sh",
                    volumes={_get_sandbox_base(): {"bind": _get_sandbox_base(), "mode": "ro"}},
                    remove=True,
                    detach=False
                )
                output = result.decode() if isinstance(result, bytes) else str(result)
                logger.info(f"[ContainerExecutor] Directory listing for {dir_path}:\n{output[:500]}")

                # Check if the filename is in the listing
                filename = os.path.basename(file_path)
                if filename in output:
                    logger.info(f"[ContainerExecutor] Found {filename} in directory listing!")
                    return True

            except Exception as e3:
                logger.warning(f"[ContainerExecutor] Directory listing failed: {e3}")

            logger.warning(f"[ContainerExecutor] File not found in remote sandbox: {file_path}")
            return False

        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to check file existence: {e}")
            return False

    def _read_file_from_sandbox(self, file_path: str) -> Optional[str]:
        """
        Read a file from the sandbox filesystem.

        Args:
            file_path: Absolute path to the file

        Returns:
            File content as string, or None if failed
        """
        try:
            if not self._is_remote_sandbox():
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        return f.read()
                return None

            # Remote mode - use _run_shell_on_sandbox which is more reliable
            exit_code, output = self._run_shell_on_sandbox(
                f'cat "{file_path}" 2>/dev/null',
                timeout=30
            )

            if exit_code != 0 or not output.strip():
                logger.warning(f"[ContainerExecutor] File read failed: {file_path}, exit_code={exit_code}")
                return None

            logger.debug(f"[ContainerExecutor] Read file {file_path}: {len(output)} bytes")
            return output

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Failed to read file {file_path}: {e}")
            return None

    def _list_files_from_sandbox(self, directory: str, pattern: str) -> List[str]:
        """
        List files matching a pattern from the sandbox filesystem.

        Uses 'find' command for remote sandbox, local glob for local mode.

        Args:
            directory: Directory to search in
            pattern: File pattern (e.g., "*.java")

        Returns:
            List of absolute file paths matching the pattern
        """
        try:
            if not self._is_remote_sandbox():
                # Local mode - use glob
                import glob
                files = glob.glob(f"{directory}/**/{pattern}", recursive=True)
                return files

            # Remote mode - use find command
            # Convert glob pattern to find -name pattern
            exit_code, output = self._run_shell_on_sandbox(
                f'find "{directory}" -type f -name "{pattern}" 2>/dev/null',
                timeout=30
            )

            if exit_code != 0 or not output.strip():
                logger.warning(f"[ContainerExecutor] File listing failed for {directory}/{pattern}")
                return []

            files = [f.strip() for f in output.strip().split('\n') if f.strip()]
            logger.info(f"[ContainerExecutor] Found {len(files)} files matching {pattern}")
            return files

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Failed to list files {directory}/{pattern}: {e}")
            return []

    def _get_available_port(self, preferred_port: int) -> int:
        """
        Get an available port, starting from preferred port.

        IMPORTANT:
        1. Queries Docker daemon for used ports
        2. Also checks if port is actually bindable on host (non-Docker processes)
        3. NEVER returns a system port (80, 443, 8080, etc.)
        """
        # If preferred port is a system port, immediately jump to safe range
        if preferred_port in SYSTEM_PORTS or preferred_port < 1024:
            logger.warning(f"[ContainerExecutor] Preferred port {preferred_port} is a SYSTEM PORT - using safe range")
            preferred_port = 10000  # Start from safe range

        # Get all used ports from Docker containers
        used_ports = set(SYSTEM_PORTS)  # Pre-block all system ports

        # Add in-memory tracked ports
        for info in self.active_containers.values():
            port = info.get("host_port") or info.get("port", 0)
            if port:
                used_ports.add(port)

        # Query Docker daemon for ALL containers with port mappings
        if self.docker_client:
            try:
                all_containers = self.docker_client.containers.list(all=True)
                for container in all_containers:
                    ports = container.attrs.get('NetworkSettings', {}).get('Ports', {}) or {}
                    for port_binding in ports.values():
                        if port_binding:
                            for binding in port_binding:
                                host_port = binding.get('HostPort')
                                if host_port:
                                    used_ports.add(int(host_port))
            except Exception as e:
                logger.warning(f"[ContainerExecutor] Failed to query Docker for ports: {e}")

        # Find an available port starting from preferred
        port = preferred_port
        max_attempts = 100

        for _ in range(max_attempts):
            # Double-check: never return system ports
            if port not in SYSTEM_PORTS and port >= 1024 and port not in used_ports and self._is_port_free(port):
                logger.info(f"[ContainerExecutor] Selected port {port} (preferred: {preferred_port})")
                return port
            port += 1

        # Fallback: use _find_available_port for wider range
        return self._find_available_port()

    async def stop_fullstack_project(self, project_id: str) -> Tuple[bool, str]:
        """
        Stop a full-stack project.

        Supports multiple architectures:
        - Docker Compose mode: Uses docker-compose down
        - Single container mode: Only backend container
        - Legacy mode: Separate frontend + backend containers

        Args:
            project_id: Project identifier

        Returns:
            Tuple of (success, message)
        """
        import subprocess

        container_info = self.active_containers.get(project_id)
        if not container_info:
            return False, "No running full-stack project found"

        errors = []
        is_docker_compose = container_info.get("docker_compose", False)
        is_single_container = container_info.get("single_container", False)

        # Docker Compose mode - use docker-compose down
        if is_docker_compose:
            compose_project = container_info.get("compose_project")
            compose_file = container_info.get("compose_file")
            project_path = container_info.get("project_path")

            try:
                cmd = f"docker-compose -p {compose_project} -f {compose_file} down --remove-orphans"
                exit_code, output = self._run_shell_on_sandbox(cmd, working_dir=project_path, timeout=60)
                if exit_code == 0:
                    logger.info(f"[ContainerExecutor] Stopped docker-compose project for {project_id}")
                else:
                    errors.append(f"docker-compose down failed: {output}")
            except Exception as e:
                errors.append(f"Docker Compose: {e}")

            # Remove from active containers
            del self.active_containers[project_id]

            if errors:
                return True, f"Stopped with warnings: {', '.join(errors)}"
            return True, "Full-stack project stopped successfully (docker-compose mode)"

        # Stop frontend (only in legacy mode)
        frontend_container = container_info.get("frontend_container")
        if frontend_container and not is_single_container:
            try:
                frontend_container.stop(timeout=10)
                frontend_container.remove(force=True)
                logger.info(f"[ContainerExecutor] Stopped frontend container for {project_id}")
            except Exception as e:
                errors.append(f"Frontend: {e}")

        # Stop backend/app container
        backend_container = container_info.get("backend_container")
        if backend_container:
            try:
                backend_container.stop(timeout=10)
                backend_container.remove(force=True)
                container_type = "application" if is_single_container else "backend"
                logger.info(f"[ContainerExecutor] Stopped {container_type} container for {project_id}")
            except Exception as e:
                errors.append(f"Backend: {e}")

        # Stop database (if present)
        database_container = container_info.get("database_container")
        if database_container:
            try:
                database_container.stop(timeout=10)
                database_container.remove(force=True)
                logger.info(f"[ContainerExecutor] Stopped database container for {project_id}")
            except Exception as e:
                errors.append(f"Database: {e}")

        # Remove network
        network_name = container_info.get("network")
        if network_name:
            try:
                network = self.docker_client.networks.get(network_name)
                network.remove()
                logger.info(f"[ContainerExecutor] Removed network {network_name}")
            except Exception as e:
                errors.append(f"Network: {e}")

        # Remove from active containers
        del self.active_containers[project_id]

        if errors:
            return True, f"Stopped with warnings: {', '.join(errors)}"

        mode = "single container" if is_single_container else "multi-container"
        return True, f"Full-stack project stopped successfully ({mode} mode)"

    async def health_check_compose(self, project_id: str) -> Tuple[bool, Dict[str, str]]:
        """
        Health check for docker-compose services.

        Returns:
            Tuple of (all_healthy, service_status_dict)
        """
        container_info = self.active_containers.get(project_id)
        if not container_info or not container_info.get("docker_compose"):
            return False, {"error": "Not a docker-compose project"}

        compose_project = container_info.get("compose_project")
        compose_file = container_info.get("compose_file")
        project_path = container_info.get("project_path")

        try:
            cmd = f"docker-compose -p {compose_project} -f {compose_file} ps --format json"
            exit_code, output = self._run_shell_on_sandbox(cmd, working_dir=project_path, timeout=30)

            if exit_code != 0:
                return False, {"error": output}

            # Parse service status
            import json
            services_status = {}
            all_healthy = True

            for line in output.strip().split('\n'):
                if line:
                    try:
                        service = json.loads(line)
                        name = service.get("Service", service.get("Name", "unknown"))
                        state = service.get("State", "unknown")
                        services_status[name] = state
                        if state != "running":
                            all_healthy = False
                    except json.JSONDecodeError:
                        pass

            logger.info(f"[ContainerExecutor] Compose health check: {services_status}")
            return all_healthy, services_status

        except Exception as e:
            logger.error(f"[ContainerExecutor] Compose health check failed: {e}")
            return False, {"error": str(e)}

    async def restart_compose_project(self, project_id: str) -> Tuple[bool, str]:
        """
        Restart all services in a docker-compose project.

        Returns:
            Tuple of (success, message)
        """
        container_info = self.active_containers.get(project_id)
        if not container_info or not container_info.get("docker_compose"):
            return False, "Not a docker-compose project"

        compose_project = container_info.get("compose_project")
        compose_file = container_info.get("compose_file")
        project_path = container_info.get("project_path")

        try:
            # Restart all services
            cmd = f"docker-compose -p {compose_project} -f {compose_file} restart"
            exit_code, output = self._run_shell_on_sandbox(cmd, working_dir=project_path, timeout=120)

            if exit_code == 0:
                logger.info(f"[ContainerExecutor] Restarted compose project: {project_id}")
                return True, "All services restarted successfully"
            else:
                logger.error(f"[ContainerExecutor] Compose restart failed: {output}")
                return False, f"Restart failed: {output}"

        except Exception as e:
            logger.error(f"[ContainerExecutor] Compose restart error: {e}")
            return False, str(e)

    async def restart_compose_service(self, project_id: str, service_name: str) -> Tuple[bool, str]:
        """
        Restart a specific service in a docker-compose project.

        Args:
            project_id: Project identifier
            service_name: Name of the service to restart (e.g., 'frontend', 'backend')

        Returns:
            Tuple of (success, message)
        """
        container_info = self.active_containers.get(project_id)
        if not container_info or not container_info.get("docker_compose"):
            return False, "Not a docker-compose project"

        compose_project = container_info.get("compose_project")
        compose_file = container_info.get("compose_file")
        project_path = container_info.get("project_path")

        try:
            cmd = f"docker-compose -p {compose_project} -f {compose_file} restart {service_name}"
            exit_code, output = self._run_shell_on_sandbox(cmd, working_dir=project_path, timeout=60)

            if exit_code == 0:
                logger.info(f"[ContainerExecutor] Restarted service {service_name} for {project_id}")
                return True, f"Service '{service_name}' restarted successfully"
            else:
                return False, f"Restart failed: {output}"

        except Exception as e:
            logger.error(f"[ContainerExecutor] Service restart error: {e}")
            return False, str(e)

    def get_container_exit_logs(self, container, tail: int = 100) -> str:
        """
        Get the last N lines of container logs (useful on exit/crash).

        Args:
            container: Docker container object
            tail: Number of lines to retrieve

        Returns:
            Log string
        """
        try:
            logs = container.logs(tail=tail, timestamps=True)
            if isinstance(logs, bytes):
                return logs.decode('utf-8', errors='replace')
            return str(logs)
        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to get exit logs: {e}")
            return f"Failed to retrieve logs: {e}"

    async def handle_container_exit(
        self,
        project_id: str,
        container,
        auto_restart: bool = False
    ) -> Tuple[str, int, str]:
        """
        Handle container exit - capture logs, exit code, and optionally restart.

        Args:
            project_id: Project identifier
            container: Docker container object
            auto_restart: Whether to automatically restart on non-zero exit

        Returns:
            Tuple of (status, exit_code, logs)
        """
        try:
            container.reload()
            status = container.status
            exit_code = container.attrs.get('State', {}).get('ExitCode', -1)

            # Capture exit logs
            logs = self.get_container_exit_logs(container, tail=100)

            logger.info(f"[ContainerExecutor] Container {project_id} exited with code {exit_code}")

            # Auto-restart on failure if enabled
            if auto_restart and exit_code != 0 and status == "exited":
                logger.info(f"[ContainerExecutor] Auto-restarting container {project_id}")
                try:
                    container.restart(timeout=10)
                    return "restarted", exit_code, logs
                except Exception as e:
                    logger.error(f"[ContainerExecutor] Auto-restart failed: {e}")
                    return "restart_failed", exit_code, logs

            return status, exit_code, logs

        except Exception as e:
            logger.error(f"[ContainerExecutor] Handle exit error: {e}")
            return "error", -1, str(e)

    async def force_kill_container(self, container, timeout: int = 10) -> bool:
        """
        Force kill a container if graceful stop fails.

        Args:
            container: Docker container object
            timeout: Seconds to wait for graceful stop before force kill

        Returns:
            True if container was killed successfully
        """
        try:
            # Try graceful stop first
            try:
                container.stop(timeout=timeout)
                logger.info(f"[ContainerExecutor] Container stopped gracefully")
                return True
            except Exception:
                pass

            # Force kill if still running
            container.reload()
            if container.status == "running":
                container.kill()
                logger.info(f"[ContainerExecutor] Container force killed")

            # Remove the container
            container.remove(force=True)
            return True

        except Exception as e:
            logger.error(f"[ContainerExecutor] Force kill failed: {e}")
            return False

    def validate_technology_detection(
        self,
        technology: "Technology",
        project_path: str
    ) -> Tuple[bool, str, float]:
        """
        Validate that detected technology matches the actual project files.

        This helps prevent running Node.js for Python projects, etc.

        Args:
            technology: The detected technology
            project_path: Path to the project

        Returns:
            Tuple of (is_valid, message, confidence_score)
            - is_valid: True if technology matches project files
            - message: Description of validation result
            - confidence_score: 0.0-1.0 confidence in detection
        """
        path = Path(project_path)

        # Check for frontend subdirectory
        frontend_path = path / "frontend"
        is_frontend_subdir = frontend_path.exists() and (frontend_path / "package.json").exists()
        check_path = frontend_path if is_frontend_subdir else path

        # Define expected files for each technology
        expected_files = {
            Technology.NODEJS: {
                "required": ["package.json"],
                "indicators": ["node_modules", "package-lock.json", "yarn.lock"],
            },
            Technology.NODEJS_VITE: {
                "required": ["package.json"],
                "indicators": ["vite.config.ts", "vite.config.js", "vite.config.mjs"],
            },
            Technology.PYTHON: {
                "required": [],
                "any_of": ["requirements.txt", "pyproject.toml", "setup.py"],
                "indicators": [".venv", "venv", "__pycache__"],
            },
            Technology.JAVA: {
                "required": [],
                "any_of": ["pom.xml", "build.gradle", "build.gradle.kts"],
                "indicators": ["target", "build", ".gradle"],
            },
            Technology.GO: {
                "required": ["go.mod"],
                "indicators": ["go.sum", "vendor"],
            },
            Technology.ANGULAR: {
                "required": ["package.json", "angular.json"],
                "indicators": ["src/app"],
            },
        }

        config = expected_files.get(technology, {})
        if not config:
            logger.warning(f"[ContainerExecutor] No validation config for {technology.value}")
            return True, f"No validation available for {technology.value}", 0.5

        confidence = 0.0
        issues = []

        # Check required files
        required = config.get("required", [])
        for req_file in required:
            if (check_path / req_file).exists():
                confidence += 0.3
            else:
                issues.append(f"Missing required file: {req_file}")

        # Check any_of files
        any_of = config.get("any_of", [])
        if any_of:
            has_any = any((check_path / f).exists() for f in any_of)
            if has_any:
                confidence += 0.3
            else:
                issues.append(f"Missing one of: {', '.join(any_of)}")

        # Check indicator files (bonus confidence)
        indicators = config.get("indicators", [])
        indicator_count = sum(1 for ind in indicators if (check_path / ind).exists())
        if indicators:
            confidence += 0.2 * (indicator_count / len(indicators))

        # Normalize confidence
        confidence = min(1.0, confidence)

        if issues:
            is_valid = False
            message = f"Technology validation issues: {'; '.join(issues)}"
            logger.warning(f"[ContainerExecutor] {message}")
        else:
            is_valid = True
            message = f"Technology {technology.value} validated with {confidence:.0%} confidence"
            logger.info(f"[ContainerExecutor] {message}")

        return is_valid, message, confidence

    def calculate_adaptive_timeout(
        self,
        project_path: str,
        technology: "Technology"
    ) -> int:
        """
        Calculate adaptive timeout based on project size and complexity.

        Base timeouts by technology (npm install is fast, Maven is slow):
        - Node.js: 60s base
        - Node.js Vite: 60s base
        - Java (Maven): 180s base (Maven is slow)
        - Java (Gradle): 120s base
        - Python: 90s base
        - Go: 60s base

        Adjustments:
        - +30s for every 10 dependencies (Node.js)
        - +60s for every 10 dependencies (Python)
        - +30s for projects with >50 files
        - Max: 300s (5 minutes)
        - Min: 60s (1 minute)

        Args:
            project_path: Path to the project
            technology: Detected technology type

        Returns:
            Timeout in seconds
        """
        import json

        # Base timeouts by technology (increased for health check time)
        base_timeouts = {
            Technology.NODEJS: 90,  # Increased from 60s for health check
            Technology.NODEJS_VITE: 90,  # Increased from 60s for health check
            Technology.ANGULAR: 120,  # Increased from 90s
            Technology.JAVA: 180,  # Maven is slow
            Technology.PYTHON: 120,  # Increased from 90s
            Technology.PYTHON_ML: 180,  # ML deps are large
            Technology.GO: 90,  # Increased from 60s
            Technology.FLUTTER: 120,
            Technology.DOTNET: 120,
        }

        timeout = base_timeouts.get(technology, 120)
        path = Path(project_path)

        # Check for frontend subdirectory
        frontend_path = path / "frontend"
        is_frontend_subdir = frontend_path.exists() and (frontend_path / "package.json").exists()
        check_path = frontend_path if is_frontend_subdir else path

        # Count files (rough complexity measure)
        try:
            file_count = sum(1 for _ in check_path.rglob("*") if _.is_file())
            if file_count > 50:
                timeout += 30
                logger.debug(f"[ContainerExecutor] +30s for {file_count} files")
            if file_count > 100:
                timeout += 30
                logger.debug(f"[ContainerExecutor] +30s for {file_count} files (100+)")
        except Exception:
            pass

        # Check Node.js dependencies
        if technology in [Technology.NODEJS, Technology.NODEJS_VITE, Technology.ANGULAR]:
            try:
                pkg_path = check_path / "package.json"
                if pkg_path.exists():
                    with open(pkg_path, 'r') as f:
                        pkg = json.load(f)
                        deps = len(pkg.get("dependencies", {}))
                        dev_deps = len(pkg.get("devDependencies", {}))
                        total_deps = deps + dev_deps
                        # +30s for every 10 deps
                        timeout += (total_deps // 10) * 30
                        logger.debug(f"[ContainerExecutor] +{(total_deps // 10) * 30}s for {total_deps} deps")
            except Exception:
                pass

        # Check Python dependencies
        if technology in [Technology.PYTHON, Technology.PYTHON_ML]:
            try:
                req_path = check_path / "requirements.txt"
                if req_path.exists():
                    lines = req_path.read_text().strip().split('\n')
                    dep_count = len([l for l in lines if l.strip() and not l.startswith('#')])
                    # +60s for every 10 deps (Python deps are larger)
                    timeout += (dep_count // 10) * 60
                    logger.debug(f"[ContainerExecutor] +{(dep_count // 10) * 60}s for {dep_count} Python deps")
            except Exception:
                pass

        # Clamp to min/max
        timeout = max(60, min(300, timeout))

        logger.info(f"[ContainerExecutor] Adaptive timeout: {timeout}s for {technology.value}")
        return timeout

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

        # Auto-detect technology FIRST (before container reuse check)
        # This ensures _frontend_subdir flag is set correctly
        if technology is None:
            technology = self.detect_technology(project_path)

        # Fix common project issues before container starts (vite open:true, missing configs, etc.)
        try:
            from app.services.workspace_restore import workspace_restore
            fix_result = await workspace_restore.fix_common_issues(Path(project_path), project_id=project_id)
            if fix_result.get("fixes_applied"):
                logger.info(f"[ContainerExecutor] Applied pre-start fixes for {project_id}: {fix_result['fixes_applied']}")
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Error applying pre-start fixes: {e}")

        # CRITICAL: Apply import fixes to REMOTE SANDBOX files
        # Files restored from S3 may have wrong import paths
        try:
            await self._apply_sandbox_import_fixes(project_id, user_id)
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Sandbox import fixes failed: {e}")

        # Check if multi-folder project - need to force recreate container with correct working_dir
        is_frontend_subdir = getattr(self, '_frontend_subdir', False)

        # ===== OPTIMIZATION: Try to reuse existing container =====
        # BUT: Skip reuse if multi-folder project detected (needs correct working_dir)
        existing_container = await self._get_existing_container(project_id)
        if existing_container and not is_frontend_subdir:
            reused, message, port = await self._reuse_container(existing_container, project_id, user_id)
            if reused:
                return True, message, port
            # If reuse failed, CLEANUP old container before creating new one
            # This prevents port conflicts where old container holds the port
            logger.info(f"[ContainerExecutor] Container reuse failed, cleaning up before creating new: {message}")
            await self._cleanup_project_container(project_id)
        elif existing_container and is_frontend_subdir:
            # Multi-folder project needs correct working_dir - remove old container
            logger.info(f"[ContainerExecutor] Multi-folder project: removing old container for fresh start")
            try:
                if existing_container.status == "running":
                    existing_container.stop(timeout=5)
                existing_container.remove(force=True)
            except Exception as e:
                logger.warning(f"[ContainerExecutor] Failed to remove old container: {e}")

        if technology == Technology.UNKNOWN:
            return False, "Could not detect project technology", None

        config = TECHNOLOGY_CONFIGS.get(technology)
        if not config:
            return False, f"Unsupported technology: {technology.value}", None

        # Generate unique container name
        container_name = f"bharatbuild_{user_id[:8]}_{project_id[:8]}_{uuid.uuid4().hex[:6]}"

        # Find available port
        host_port = self._find_available_port()

        # Ensure bharatbuild-sandbox network exists (auto-create if missing)
        try:
            existing_networks = self.docker_client.networks.list(names=["bharatbuild-sandbox"])
            if not existing_networks:
                logger.info("[ContainerExecutor] Creating bharatbuild-sandbox network...")
                self.docker_client.networks.create(
                    "bharatbuild-sandbox",
                    driver="bridge",
                    labels={"managed_by": "bharatbuild"}
                )
                logger.info("[ContainerExecutor] Network bharatbuild-sandbox created successfully")
        except Exception as net_err:
            logger.warning(f"[ContainerExecutor] Network check/create failed: {net_err}")

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
            # nginx gateway routing: /sandbox/{port}/* -> localhost:{port}/*
            # Container receives requests at root path, no --base needed

            # Build run command with correct base path for preview URL routing
            run_command = config.run_command

            # Critical #2: Fix Vite base path
            # The proxy handles all path stripping (/api/v1/preview/{project_id}/ → /)
            # So Vite should ALWAYS use --base=/ to generate root-relative URLs
            # The nginx sub_filter rules handle any remaining path rewrites
            #
            # Flow:
            # 1. Vite generates: <script src="/@vite/client">
            # 2. Browser requests: /api/v1/preview/{project_id}/@vite/client
            # 3. FastAPI proxy extracts: path = @vite/client
            # 4. Proxy sends to nginx: /sandbox/{port}/@vite/client
            # 5. nginx proxies to container: /@vite/client
            # 6. Vite serves the file (expects root-relative paths)

            if technology == Technology.NODEJS_VITE:
                # Vite: Use --base=/ (root) since proxy handles path translation
                # This ensures HMR WebSocket and asset loading work correctly
                run_command = f"npm run dev -- --host 0.0.0.0 --port 3000"
                logger.info(f"[ContainerExecutor] Using Vite with default --base=/ (proxy handles path translation)")

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

            # Create container WITH port mapping for nginx gateway routing
            # nginx on port 8080 routes /sandbox/{port}/ to localhost:{port}
            # This allows ECS to reach container via EC2_IP:8080/sandbox/{host_port}/
            # CRITICAL: Convert Path to string for Docker SDK compatibility
            path_str = str(project_path)

            # Determine working directory - use /app/frontend for multi-folder projects
            working_dir = "/app"
            if getattr(self, '_frontend_subdir', False):
                working_dir = "/app/frontend"
                self._frontend_subdir = False  # Reset for next project
                logger.info(f"[ContainerExecutor] Using frontend subdirectory: {working_dir}")

            # Build volumes - project path + npm cache for faster installs
            container_volumes = {
                path_str: {"bind": "/app", "mode": "rw"},
                NPM_CACHE_PATH: {"bind": "/root/.npm", "mode": "rw"}
            }

            # Gap #1: Validate volume mount path exists before creating container
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
            if sandbox_docker_host:
                try:
                    # Verify the project path exists on remote sandbox
                    verify_result = self.docker_client.containers.run(
                        "alpine:latest",
                        ["-c", f"test -d '{path_str}' && ls '{path_str}' | wc -l"],
                        entrypoint="/bin/sh",
                        volumes={_get_sandbox_base(): {"bind": _get_sandbox_base(), "mode": "ro"}},
                        remove=True,
                        detach=False
                    )
                    file_count = verify_result.decode().strip() if verify_result else "0"
                    if file_count == "0" or not file_count.isdigit():
                        logger.warning(f"[ContainerExecutor] Volume path may be empty: {path_str} (files: {file_count})")
                    else:
                        logger.info(f"[ContainerExecutor] Volume mount validated: {path_str} ({file_count} files)")
                except Exception as vol_err:
                    logger.warning(f"[ContainerExecutor] Volume validation failed (continuing): {vol_err}")

            container = self.docker_client.containers.run(
                image=config.image,
                name=container_name,
                detach=True,
                working_dir=working_dir,
                volumes=container_volumes,
                ports={f"{config.port}/tcp": host_port},  # Map container port to host port
                network="bharatbuild-sandbox",
                mem_limit=config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(config.cpu_limit * 100000),
                environment={
                    "NODE_ENV": "development",
                    "JAVA_OPTS": "-Xmx512m",
                    "PYTHONUNBUFFERED": "1",
                    # Critical: CI=true for non-interactive npm install
                    "CI": "true",
                    # Critical #2: No custom base paths needed
                    # Proxy handles path translation, so frameworks use default root paths
                    "PUBLIC_URL": "",  # CRA: empty = use relative paths
                    "VITE_BASE_PATH": "/",  # Vite: root path (proxy strips prefix)
                    # npm cache for faster installs (shared across containers)
                    "npm_config_cache": "/root/.npm",
                },
                command=f"sh -c '{config.build_command} && {run_command}'" if config.build_command else run_command,
                labels=all_labels
            )

            # Track container with host_port for nginx gateway routing
            self.active_containers[project_id] = {
                "container_id": container.id,
                "container_name": container_name,
                "user_id": user_id,
                "technology": technology.value,
                "internal_port": config.port,  # Container's internal port (5173, 3000, etc.)
                "host_port": host_port,  # EC2 host port for nginx routing
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(seconds=config.timeout_seconds)
            }

            logger.info(f"[ContainerExecutor] Container {container_name} started (host_port: {host_port}, internal: {config.port})")

            # Return host_port for nginx gateway routing
            return True, f"Container started successfully", host_port

        except APIError as e:
            logger.error(f"[ContainerExecutor] Docker API error: {e}")
            return False, f"Failed to create container: {str(e)}", None
        except Exception as e:
            logger.error(f"[ContainerExecutor] Error creating container: {e}")
            return False, f"Error: {str(e)}", None

    async def stop_container(self, project_id: str, user_id: str = None) -> Tuple[bool, str]:
        """
        Stop and remove a project's container.

        This method now finds containers by name pattern (not just in-memory tracking),
        which allows stopping containers even after backend restart.
        Also handles full-stack projects with multiple containers.
        """
        if not self.docker_client:
            return False, "Docker client not available"

        stopped_any = False
        container_name_prefix = f"bharatbuild_"

        try:
            # Check for full-stack project first (has frontend_container and backend_container)
            if project_id in self.active_containers:
                container_info = self.active_containers[project_id]
                if container_info.get("technology") == Technology.FULLSTACK:
                    # Use dedicated full-stack stop method
                    return await self.stop_fullstack_project(project_id)

            # Method 1: Try in-memory tracking first (single container)
            if project_id in self.active_containers:
                container_info = self.active_containers[project_id]
                try:
                    container = self.docker_client.containers.get(container_info["container_id"])
                    container.stop(timeout=10)
                    container.remove(force=True)
                    del self.active_containers[project_id]
                    logger.info(f"[ContainerExecutor] Stopped tracked container for {project_id}")
                    stopped_any = True
                except NotFound:
                    del self.active_containers[project_id]
                except Exception as e:
                    logger.warning(f"[ContainerExecutor] Error stopping tracked container: {e}")

            # Method 2: Find containers by name pattern (handles backend restart case)
            # Container naming: bharatbuild_{user_id[:8]}_{project_id[:8]}_{port}
            project_prefix = project_id[:8] if len(project_id) >= 8 else project_id

            containers = self.docker_client.containers.list(all=True)
            for container in containers:
                name = container.name
                # Check if container name contains the project ID prefix
                if container_name_prefix in name and project_prefix in name:
                    try:
                        logger.info(f"[ContainerExecutor] Found container by name: {name}")
                        if container.status == "running":
                            container.stop(timeout=10)
                        container.remove(force=True)
                        logger.info(f"[ContainerExecutor] Stopped and removed container: {name}")
                        stopped_any = True
                    except Exception as e:
                        logger.warning(f"[ContainerExecutor] Error stopping container {name}: {e}")

            # Clean up tracking
            if project_id in self.active_containers:
                del self.active_containers[project_id]

            if stopped_any:
                return True, "Container stopped successfully"
            else:
                return False, "No container found for project"

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
        """
        Find an available port for container mapping on the Docker host.

        IMPORTANT:
        1. This queries the REMOTE Docker daemon to get actual used ports,
           not local ports on the ECS task container.
        2. NEVER returns system ports (80, 443, 8080, etc.)
        3. Preview Gap #1: Uses lock to prevent race conditions
        """
        import random

        # Preview Gap #1: Acquire lock to prevent race condition during port allocation
        with _port_allocation_lock:
            # Ensure start is in safe range (above system ports)
            if start < 1024:
                start = 10000
                logger.warning(f"[ContainerExecutor] Start port adjusted to {start} to avoid system ports")

            # Get all used ports from Docker containers (not just in-memory tracking)
            # Pre-block all system ports
            used_ports = set(SYSTEM_PORTS)

            # Add in-memory tracked ports (from current session)
            for info in self.active_containers.values():
                port = info.get("host_port") or info.get("port", 0)
                if port:
                    used_ports.add(port)

            # Query Docker daemon for ALL containers with port mappings
            # This catches containers from previous ECS task sessions
            if self.docker_client:
                try:
                    all_containers = self.docker_client.containers.list(all=True)
                    for container in all_containers:
                        # Get port mappings from container
                        ports = container.attrs.get('NetworkSettings', {}).get('Ports', {}) or {}
                        for port_binding in ports.values():
                            if port_binding:  # May be None if not mapped
                                for binding in port_binding:
                                    host_port = binding.get('HostPort')
                                    if host_port:
                                        used_ports.add(int(host_port))
                    logger.debug(f"[ContainerExecutor] Docker reports used ports: {sorted(used_ports)}")
                except Exception as e:
                    logger.warning(f"[ContainerExecutor] Failed to query Docker for ports: {e}")

            # Find an available port, starting from a random offset to reduce collisions
            # This helps when multiple requests come in simultaneously
            offset = random.randint(0, 1000)
            search_start = start + offset

            for port in range(search_start, end):
                # Double-check: never return system ports
                if port not in used_ports and port not in SYSTEM_PORTS and port >= 1024:
                    logger.info(f"[ContainerExecutor] Selected available port: {port}")
                    return port

            # Wrap around if we started with an offset
            for port in range(start, search_start):
                # Double-check: never return system ports
                if port not in used_ports and port not in SYSTEM_PORTS and port >= 1024:
                    logger.info(f"[ContainerExecutor] Selected available port (wrap): {port}")
                    return port

            raise RuntimeError(f"No available ports in range {start}-{end}. Used ports: {len(used_ports)}")

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

    async def _clear_vite_cache_on_restart(self, project_id: str, user_id: str) -> bool:
        """
        Clear Vite cache on the sandbox before restarting a container.

        This prevents corrupted cache issues that cause double-path problems like:
        /node_modules/.vite/deps/node_modules/.vite/deps/chunk-XXX.js

        The cache is at: {SANDBOX_PATH}/{user_id}/{project_id}/node_modules/.vite
        """
        try:
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
            if not sandbox_docker_host:
                # Local sandbox - clear directly
                sandbox_path = Path(_get_sandbox_base()) / user_id / project_id / "node_modules" / ".vite"
                if sandbox_path.exists():
                    import shutil
                    shutil.rmtree(sandbox_path)
                    logger.info(f"[ContainerExecutor] Cleared local Vite cache for {project_id}")
                return True

            # Remote sandbox - use Docker to clear the cache
            import docker
            # TLS-enabled docker client
            from app.services.docker_client_helper import get_docker_client as get_tls_client
            docker_client = get_tls_client(timeout=30)
            if not docker_client:
                docker_client = docker.DockerClient(base_url=sandbox_docker_host, timeout=30)

            sandbox_base = _get_sandbox_base()
            workspace_path = f"{sandbox_base}/{user_id}/{project_id}"
            vite_cache_path = f"{workspace_path}/node_modules/.vite"

            # Run a quick container to clear the cache
            try:
                result = docker_client.containers.run(
                    image="alpine:latest",
                    command=f"sh -c 'rm -rf {vite_cache_path} && echo CLEARED || echo SKIPPED'",
                    volumes={sandbox_base: {"bind": sandbox_base, "mode": "rw"}},
                    remove=True,
                    detach=False,
                )
                output = result.decode().strip() if result else "UNKNOWN"
                logger.info(f"[ContainerExecutor] Vite cache clear result for {project_id}: {output}")
                return True
            except Exception as e:
                logger.warning(f"[ContainerExecutor] Could not clear Vite cache: {e}")
                return False

        except Exception as e:
            logger.warning(f"[ContainerExecutor] Error clearing Vite cache for {project_id}: {e}")
            return False


    async def _apply_sandbox_import_fixes(self, project_id: str, user_id: str) -> bool:
        """Apply import path fixes to files on the remote sandbox."""
        try:
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
            if not sandbox_docker_host:
                return True

            import docker
            # TLS-enabled docker client
            from app.services.docker_client_helper import get_docker_client as get_tls_client
            docker_client = get_tls_client(timeout=60)
            if not docker_client:
                docker_client = docker.DockerClient(base_url=sandbox_docker_host, timeout=60)
            sandbox_base = _get_sandbox_base()
            workspace_path = f"{sandbox_base}/{user_id}/{project_id}"

            # Note: Using .format() instead of f-string because the script contains backslashes
            fix_script = """#!/bin/sh
WORKSPACE="{workspace_path}"
echo "Workspace: $WORKSPACE"
""".format(workspace_path=workspace_path) + """
# Clear Vite cache
if [ -d "$WORKSPACE/node_modules/.vite" ]; then
    rm -rf "$WORKSPACE/node_modules/.vite"
    echo "Cleared .vite cache"
fi
# Fix vite.config: open:true -> false, add hmr:false, host:0.0.0.0
for cfg in "$WORKSPACE/vite.config.ts" "$WORKSPACE/vite.config.js"; do
    if [ -f "$cfg" ]; then
        CHANGED=0
        # Disable open:true
        if grep -q 'open *: *true' "$cfg"; then
            sed -i 's/open *: *true/open: false/g' "$cfg"
            CHANGED=1
        fi
        # CRITICAL: Disable HMR for subdomain preview (WebSocket proxying is unreliable)
        # Check if hmr: false already exists
        if ! grep -q 'hmr *: *false' "$cfg"; then
            # Check if there's an existing hmr block to replace (hmr: { ... })
            if grep -q 'hmr *: *{' "$cfg"; then
                # Replace hmr: { ... } block with hmr: false using perl for multi-line
                perl -i -0pe 's/hmr\s*:\s*\{[^}]*\}/hmr: false/g' "$cfg"
                echo "Replaced HMR block with hmr: false"
                CHANGED=1
            elif grep -q 'server *:' "$cfg" && ! grep -q 'hmr *:' "$cfg"; then
                # No hmr config at all, add hmr: false
                sed -i 's/server *: *{/server: { hmr: false,/g' "$cfg"
                CHANGED=1
            fi
        fi
        # Add host if server block exists but no host
        if grep -q 'server *:' "$cfg" && ! grep -q "host *:" "$cfg"; then
            sed -i "s/server *: *{/server: { host: '0.0.0.0',/g" "$cfg"
            CHANGED=1
        fi
        if [ $CHANGED -eq 1 ]; then
            echo "Fixed vite.config in $cfg"
        fi
    fi
done
# Fix PostCSS config: Remove conflicting .cjs/.mjs files and ensure proper ESM config
# This fixes Tailwind CSS not compiling (raw @tailwind directives showing in browser)
if [ -f "$WORKSPACE/package.json" ]; then
    # Remove conflicting PostCSS configs that confuse Vite
    rm -f "$WORKSPACE/postcss.config.cjs" "$WORKSPACE/postcss.config.mjs" 2>/dev/null

    # Check if postcss.config.js exists and has correct ESM syntax
    if [ ! -f "$WORKSPACE/postcss.config.js" ] || grep -q 'module.exports' "$WORKSPACE/postcss.config.js" 2>/dev/null; then
        cat > "$WORKSPACE/postcss.config.js" << 'POSTCSS_EOF'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
POSTCSS_EOF
        echo "Fixed postcss.config.js (ESM format)"
    fi

    # Fix tailwind.config.js if it uses CJS in an ESM project
    if grep -q '"type".*:.*"module"' "$WORKSPACE/package.json" 2>/dev/null; then
        if [ -f "$WORKSPACE/tailwind.config.js" ] && grep -q 'module.exports' "$WORKSPACE/tailwind.config.js" 2>/dev/null; then
            sed -i 's/module\.exports *= */export default /g' "$WORKSPACE/tailwind.config.js"
            echo "Fixed tailwind.config.js (converted to ESM)"
        fi
    fi

    # PROACTIVE DEPENDENCY VALIDATION: Ensure tailwindcss is installed if postcss.config.js references it
    if [ -f "$WORKSPACE/postcss.config.js" ] && grep -q 'tailwindcss' "$WORKSPACE/postcss.config.js" 2>/dev/null; then
        if ! grep -q '"tailwindcss"' "$WORKSPACE/package.json" 2>/dev/null; then
            echo "Adding missing tailwindcss dependency..."
            # Use node to add to devDependencies
            node -e "
                const fs = require('fs');
                const pkg = JSON.parse(fs.readFileSync('$WORKSPACE/package.json', 'utf8'));
                if (!pkg.devDependencies) pkg.devDependencies = {};
                if (!pkg.devDependencies.tailwindcss && !pkg.dependencies?.tailwindcss) {
                    pkg.devDependencies.tailwindcss = '^3.3.6';
                    pkg.devDependencies.autoprefixer = pkg.devDependencies.autoprefixer || '^10.4.16';
                    pkg.devDependencies.postcss = pkg.devDependencies.postcss || '^8.4.32';
                    fs.writeFileSync('$WORKSPACE/package.json', JSON.stringify(pkg, null, 2));
                    console.log('Added tailwindcss, autoprefixer, postcss to devDependencies');
                }
            " 2>/dev/null || echo "Could not auto-add tailwindcss"
        fi
    fi
fi
# Fix import paths in src/ files - NOTE: parentheses fix operator precedence!
if [ -d "$WORKSPACE/src" ]; then
    FIXED=0
    for f in $(find "$WORKSPACE/src" -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" -o -name "*.js" \) 2>/dev/null); do
        if grep -q "from './src/" "$f" 2>/dev/null || grep -q "from '/src/" "$f" 2>/dev/null; then
            sed -i "s|from './src/|from './|g" "$f"
            sed -i "s|from '/src/|from './|g" "$f"
            FIXED=$((FIXED+1))
        fi
    done
    echo "Fixed imports in $FIXED files"
else
    echo "No src/ dir found"
fi
echo "Done"
"""

            result = docker_client.containers.run(
                "node:20-alpine", ["-c", fix_script], entrypoint="/bin/sh",
                volumes={sandbox_base: {"bind": sandbox_base, "mode": "rw"}},
                remove=True, detach=False, stdout=True, stderr=True
            )
            output = result.decode().strip() if result else "No output"
            logger.info(f"[ContainerExecutor] Sandbox fixes output: {output[:500] if output else 'Empty'}")
            return True
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Sandbox fixes failed: {e}")
            return False

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
                # Check if container has CI=true env before reusing (old containers don't have it)
                try:
                    container_env = container.attrs.get('Config', {}).get('Env', [])
                    has_ci_true = any(env.startswith('CI=') for env in container_env)
                    if not has_ci_true:
                        logger.info(f"[ContainerExecutor] Container {container_name} missing CI=true, removing for fresh start")
                        try:
                            container.remove(force=True)
                        except Exception:
                            pass
                        return False, "Container missing CI=true environment variable", None
                except Exception as env_check_err:
                    logger.warning(f"[ContainerExecutor] Could not check container env: {env_check_err}")

                # Container has CI=true (or check failed), safe to restart
                logger.info(f"[ContainerExecutor] Starting stopped container {container_name} for {project_id}")

                # CRITICAL: Clear Vite cache before restarting to prevent corrupted cache issues
                # The cache at node_modules/.vite can cause double-path problems like:
                # /node_modules/.vite/deps/node_modules/.vite/deps/chunk-XXX.js
                await self._clear_vite_cache_on_restart(project_id, user_id)

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

    def _remove_container_by_name(self, container_name: str) -> None:
        """
        Remove an existing container by name before creating a new one.
        Handles the 409 Conflict error when container name is already in use.
        """
        if not self.docker_client:
            return

        try:
            existing = self.docker_client.containers.get(container_name)
            logger.info(f"[ContainerExecutor] Found existing container '{container_name}', removing it...")
            if existing.status == "running":
                existing.stop(timeout=5)
            existing.remove(force=True)
            logger.info(f"[ContainerExecutor] Successfully removed container '{container_name}'")
        except docker.errors.NotFound:
            pass  # Container doesn't exist, good
        except Exception as e:
            logger.warning(f"[ContainerExecutor] Error removing container '{container_name}': {e}")

    def update_activity(self, project_id: str):
        """Update last_activity timestamp for a project (call on user interaction)"""
        if project_id in self.active_containers:
            self.active_containers[project_id]["last_activity"] = datetime.utcnow()
            logger.debug(f"[ContainerExecutor] Updated activity for project {project_id}")

    async def _cleanup_loop(self):
        """Background task to cleanup idle containers (30 min idle timeout)"""
        from app.core.config import settings
        idle_timeout_seconds = settings.CONTAINER_IDLE_TIMEOUT_SECONDS  # 1800 = 30 min

        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                # 1. Clean up in-memory tracked containers that are IDLE for 30+ min
                now = datetime.utcnow()
                idle_projects = []

                for project_id, info in self.active_containers.items():
                    last_activity = info.get("last_activity") or info.get("started_at")
                    if last_activity:
                        idle_seconds = (now - last_activity).total_seconds()
                        if idle_seconds > idle_timeout_seconds:
                            idle_projects.append(project_id)
                            logger.info(f"[ContainerExecutor] Project {project_id} idle for {idle_seconds/60:.1f} min")

                for project_id in idle_projects:
                    logger.info(f"[ContainerExecutor] Auto-cleanup idle container: {project_id}")
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
        Clean up bharatbuild containers that have been IDLE for 30+ minutes.
        - Running containers: Check if tracked and idle (no activity for 30 min)
        - Stopped containers: Remove if stopped for 30+ min
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
            idle_timeout_minutes = settings.CONTAINER_IDLE_TIMEOUT_SECONDS / 60  # 30 min

            for container in containers:
                try:
                    project_id = container.labels.get("project_id", "unknown")
                    should_remove = False
                    idle_minutes = 0

                    if container.status == "running":
                        # For running containers, check if we're tracking activity
                        if project_id in self.active_containers:
                            # Use tracked last_activity
                            last_activity = self.active_containers[project_id].get("last_activity")
                            if last_activity:
                                idle_minutes = (now - last_activity).total_seconds() / 60
                                if idle_minutes > idle_timeout_minutes:
                                    should_remove = True
                        else:
                            # Not tracked - check creation time as fallback
                            created_str = container.attrs.get("Created", "")
                            if created_str:
                                created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00").split(".")[0])
                                created_at = created_at.replace(tzinfo=None)
                                idle_minutes = (now - created_at).total_seconds() / 60
                                if idle_minutes > idle_timeout_minutes:
                                    should_remove = True
                    else:
                        # Stopped/exited containers - check FinishedAt time
                        state = container.attrs.get("State", {})
                        finished_str = state.get("FinishedAt", "")
                        if finished_str and finished_str != "0001-01-01T00:00:00Z":
                            finished_at = datetime.fromisoformat(finished_str.replace("Z", "+00:00").split(".")[0])
                            finished_at = finished_at.replace(tzinfo=None)
                            idle_minutes = (now - finished_at).total_seconds() / 60
                            if idle_minutes > idle_timeout_minutes:
                                should_remove = True

                    if should_remove:
                        logger.info(f"[ContainerExecutor] Removing idle container {container.name} "
                                   f"(project: {project_id}, idle: {idle_minutes:.1f} min)")

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

    # =========================================================================
    # BACKEND-FIRST AUTO-FIX: File Sync & Retry Loop
    # =========================================================================

    async def _sync_files_to_container(
        self,
        container,
        project_path: str,
        files_modified: list
    ) -> bool:
        """
        Sync fixed files from local filesystem to running container.

        This copies the fixed files into the container's /app directory
        so that the dev server can pick up the changes via HMR or restart.
        """
        import tarfile
        import io

        if not files_modified:
            return True

        try:
            # Create a tar archive with the modified files
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                for rel_path in files_modified:
                    # Normalize path - AI sometimes returns container absolute paths like /app/frontend/file.ts
                    if rel_path.startswith("/app/"):
                        rel_path = rel_path[5:]  # Remove "/app/" prefix
                        logger.info(f"[ContainerExecutor] Normalized container path for sync: {rel_path}")
                    elif rel_path.startswith("/"):
                        rel_path = rel_path.lstrip("/")
                        logger.info(f"[ContainerExecutor] Stripped leading slash for sync: {rel_path}")

                    local_path = Path(project_path) / rel_path
                    if local_path.exists():
                        # Add file to tar with correct path in container
                        tar.add(str(local_path), arcname=rel_path)
                        logger.info(f"[ContainerExecutor] Adding to sync: {rel_path}")
                    else:
                        logger.warning(f"[ContainerExecutor] File not found for sync: {local_path}")

            tar_buffer.seek(0)

            # Copy tar to container
            container.put_archive('/app', tar_buffer.read())
            logger.info(f"[ContainerExecutor] Synced {len(files_modified)} files to container")
            return True

        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to sync files to container: {e}")
            return False

    async def _kill_dev_server(self, container) -> bool:
        """
        Kill the running dev server process inside the container.

        This is needed before restarting to avoid port conflicts.
        """
        try:
            # Kill node/python processes
            kill_commands = [
                "pkill -f 'node' || true",
                "pkill -f 'npm' || true",
                "pkill -f 'vite' || true",
                "pkill -f 'python' || true",
                "pkill -f 'uvicorn' || true",
                "pkill -f 'java' || true",
            ]

            for cmd in kill_commands:
                try:
                    container.exec_run(f"sh -c '{cmd}'", detach=True)
                except Exception:
                    pass

            # Wait a moment for processes to die
            await asyncio.sleep(1)
            logger.info(f"[ContainerExecutor] Killed dev server processes")
            return True

        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to kill dev server: {e}")
            return False

    async def _restart_dev_server(
        self,
        container,
        run_command: str,
        working_dir: str = "/app"
    ) -> bool:
        """
        Restart the dev server inside the container.

        Returns True if the command was started successfully.
        The actual server readiness is checked by log streaming.
        """
        try:
            # Check if container is still running
            container.reload()

            if container.status == "exited":
                # Container crashed - restart it (entrypoint will run npm run dev automatically)
                logger.warning(f"[ContainerExecutor] Container exited, restarting it (entrypoint will run)")
                try:
                    container.start()
                    await asyncio.sleep(2.0)  # Give container time to start
                    container.reload()
                    if container.status == "running":
                        logger.info(f"[ContainerExecutor] Container restarted successfully")
                        return True
                    else:
                        logger.error(f"[ContainerExecutor] Container still not running: {container.status}")
                        return False
                except Exception as start_err:
                    logger.error(f"[ContainerExecutor] Failed to start container: {start_err}")
                    return False

            elif container.status == "running":
                # Container is running - exec the dev server command
                exec_result = container.exec_run(
                    f"sh -c 'cd {working_dir} && {run_command}'",
                    detach=True,
                    workdir=working_dir
                )
                logger.info(f"[ContainerExecutor] Restarted dev server via exec: {run_command}")
                return True

            else:
                logger.error(f"[ContainerExecutor] Container in unexpected state: {container.status}")
                return False

        except Exception as e:
            logger.error(f"[ContainerExecutor] Failed to restart dev server: {e}")
            return False

    async def _run_fix_retry_loop(
        self,
        project_id: str,
        project_path: str,
        container,
        exec_ctx: ExecutionContext,
        run_command: str,
        working_dir: str,
        error_patterns: list,
        start_patterns: list,
    ) -> AsyncGenerator[str, None]:
        """
        Backend-first auto-fix retry loop.

        Flow:
        1. Fix error using AI
        2. Sync fixed files to container
        3. Kill existing dev server
        4. Restart dev server
        5. Stream logs and check for success/error
        6. Repeat up to max_fix_attempts times

        Yields log lines for streaming to UI.
        """
        from app.services.bolt_fixer import bolt_fixer

        while exec_ctx.should_attempt_fix():
            attempt = exec_ctx.fix_attempt + 1
            yield f"\n{'='*50}\n"
            yield f"🔧 AUTO-FIX: Attempt {attempt}/{exec_ctx.max_fix_attempts}\n"
            yield f"{'='*50}\n"
            yield f"__FIX_STARTING__\n"

            # Step 1: Get fix from AI (Bolt.new architecture)
            yield f"📊 Analyzing error...\n"
            payload = exec_ctx.get_fixer_payload()

            try:
                fix_result = await bolt_fixer.fix_from_backend(
                    project_id=project_id,
                    project_path=Path(project_path),
                    payload=payload,
                    sandbox_file_writer=self._write_file_to_sandbox,  # Write directly to sandbox
                    sandbox_file_reader=self._read_file_from_sandbox,  # Read from sandbox
                    sandbox_file_lister=self._list_files_from_sandbox  # List files from sandbox
                )
            except Exception as fix_err:
                logger.error(f"[ContainerExecutor] Fix error: {fix_err}")
                yield f"❌ Fix failed: {fix_err}\n"
                yield f"__FIX_FAILED__:{fix_err}\n"
                exec_ctx.mark_fixing()  # Increment attempt counter
                continue

            if not fix_result.success:
                yield f"❌ Could not generate fix: {fix_result.message}\n"
                yield f"__FIX_FAILED__:{fix_result.message}\n"
                exec_ctx.mark_fixing()
                continue

            # Step 2: Apply fix
            exec_ctx.mark_fixing()
            exec_ctx.mark_fixed(fix_result.files_modified)
            yield f"✅ Generated fixes for {len(fix_result.files_modified)} file(s):\n"
            for f in fix_result.files_modified:
                yield f"   📝 {f}\n"

            # Step 3: Sync files to container (GAP 6 FIX: Retry on failure)
            yield f"📦 Syncing fixes to container...\n"
            sync_success = False
            max_sync_retries = 3

            for sync_attempt in range(max_sync_retries):
                sync_success = await self._sync_files_to_container(
                    container=container,
                    project_path=project_path,
                    files_modified=fix_result.files_modified
                )
                if sync_success:
                    yield f"  ✅ Files synced successfully\n"
                    break
                else:
                    if sync_attempt < max_sync_retries - 1:
                        yield f"  ⚠️ Sync attempt {sync_attempt + 1} failed, retrying...\n"
                        await asyncio.sleep(1.0 * (sync_attempt + 1))
                    else:
                        yield f"  ❌ Sync failed after {max_sync_retries} attempts\n"

            if not sync_success:
                yield f"⚠️ Failed to sync fixes to container - fix may not take effect.\n"
                yield f"__FIX_FAILED__:Sync to container failed\n"
                # GAP 6 FIX: Don't continue with broken sync - try next fix attempt
                continue

            # Step 4: Kill existing dev server
            yield f"🔄 Restarting dev server...\n"
            await self._kill_dev_server(container)

            # Step 5: Restart dev server
            restart_success = await self._restart_dev_server(
                container=container,
                run_command=run_command,
                working_dir=working_dir
            )

            if not restart_success:
                yield f"❌ Failed to restart dev server.\n"
                yield f"__FIX_FAILED__:Failed to restart server\n"
                continue

            # Step 6: Stream new logs and check for success/error
            yield f"📜 Checking if fix worked...\n\n"
            exec_ctx.reset_for_retry()

            # Wait for logs with timeout
            server_started = False
            has_new_error = False
            check_timeout = 30  # 30 seconds to check if fix worked
            check_start = asyncio.get_event_loop().time()

            # Create log queue for streaming
            log_queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def stream_check_logs():
                try:
                    for log in container.logs(stream=True, follow=True, since=int(check_start), timestamps=False):
                        line = log.decode('utf-8', errors='ignore').strip()
                        if line:
                            asyncio.run_coroutine_threadsafe(log_queue.put(line), loop)
                except Exception as e:
                    logger.debug(f"[ContainerExecutor] Log stream ended: {e}")
                finally:
                    asyncio.run_coroutine_threadsafe(log_queue.put(None), loop)

            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            log_future = executor.submit(stream_check_logs)

            try:
                while True:
                    elapsed = loop.time() - check_start
                    if elapsed > check_timeout:
                        yield f"⏱️ Timeout waiting for server restart.\n"
                        break

                    try:
                        line = await asyncio.wait_for(log_queue.get(), timeout=2.0)

                        if line is None:
                            break

                        yield f"{line}\n"
                        exec_ctx.add_output(line)

                        # Check for success
                        for pattern in start_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                server_started = True
                                exec_ctx.server_started = True
                                exec_ctx.complete(exit_code=0)
                                yield f"\n🎉 SUCCESS! Server started after fix.\n"
                                yield f"__FIX_SUCCESS__\n"
                                break

                        if server_started:
                            break

                        # Check for new error
                        for pattern in error_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                has_new_error = True
                                exec_ctx.add_stderr(line)
                                break

                    except asyncio.TimeoutError:
                        continue

            finally:
                executor.shutdown(wait=False)

            if server_started:
                # Fix worked!
                return

            if has_new_error:
                yield f"\n⚠️ Fix applied but new error detected. Retrying...\n"
                exec_ctx.complete(exit_code=1)
                # Continue to next iteration
            else:
                yield f"\n⚠️ Server did not start. Retrying...\n"
                exec_ctx.complete(exit_code=1)

        # Exhausted all attempts
        exec_ctx.mark_exhausted()
        yield f"\n{'='*50}\n"
        yield f"❌ AUTO-FIX EXHAUSTED: Could not fix after {exec_ctx.max_fix_attempts} attempts.\n"
        yield f"{'='*50}\n"
        yield f"💡 Please fix the error manually and try again.\n"
        yield f"__FIX_EXHAUSTED__\n"

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
        Logs are also stored in LogBus for auto-fixer context.
        """
        import re
        import asyncio
        from app.services.log_bus import get_log_bus

        user_id = user_id or "anonymous"

        # Get LogBus for this project to store logs for auto-fixer
        log_bus = get_log_bus(project_id)

        # Ensure Docker client is initialized
        if not self.docker_client:
            yield f"🔧 Initializing Docker client...\n"
            initialized = await self.initialize()
            if not initialized or not self.docker_client:
                yield f"ERROR: Docker client not available\n"
                return

        yield f"🔍 Detecting project technology...\n"

        # DEBUG: Log exact path being used
        path_str = str(project_path)
        logger.info(f"[ContainerExecutor] run_project called with project_path={path_str}, user_id={user_id}")
        yield f"  📁 Using path: {path_str}\n"

        # =====================================================================
        # FULL-STACK DETECTION: Check if project has both frontend/ and backend/
        # If so, run both containers with network communication
        # =====================================================================
        fullstack_config = self.detect_fullstack_project(project_path)
        if fullstack_config:
            yield f"  🎯 Full-stack project detected!\n"
            yield f"     Frontend: {fullstack_config.frontend_tech.value}\n"
            yield f"     Backend: {fullstack_config.backend_tech.value}\n\n"

            # Run full-stack project with multi-container orchestration
            async for msg in self.run_fullstack_project(project_id, project_path, fullstack_config):
                yield msg
            return  # Exit after full-stack handling

        # Reset frontend subdir flag before detection
        self._frontend_subdir = False

        # Detect technology (this will set self._frontend_subdir if frontend/ exists)
        technology = self.detect_technology(project_path)

        # Log detection result
        if technology == Technology.UNKNOWN:
            # Default to Node.js for unknown projects
            technology = Technology.NODEJS
            yield f"  ⚠️ Could not detect technology, defaulting to Node.js\n"
        else:
            yield f"  📦 Detected: {technology.value}\n"

        # Show if multi-folder project detected
        if getattr(self, '_frontend_subdir', False):
            yield f"  📂 Multi-folder project detected - using frontend/ subdirectory\n"
            logger.info(f"[ContainerExecutor] Multi-folder project: will use /app/frontend as working dir")

        # =====================================================================
        # TECHNOLOGY VALIDATION: Verify detection matches project files
        # =====================================================================
        is_tech_valid, tech_msg, tech_confidence = self.validate_technology_detection(technology, project_path)
        if not is_tech_valid:
            yield f"  ⚠️ {tech_msg}\n"
            # Don't fail, just warn - we'll try to run anyway
        else:
            yield f"  ✓ Technology confidence: {tech_confidence:.0%}\n"

        # =====================================================================
        # ADAPTIVE TIMEOUT: Calculate based on project size and complexity
        # =====================================================================
        adaptive_timeout = self.calculate_adaptive_timeout(project_path, technology)
        yield f"  ⏱️ Adaptive timeout: {adaptive_timeout}s\n"

        config = TECHNOLOGY_CONFIGS.get(technology)
        if not config:
            yield f"ERROR: Unsupported technology: {technology.value}\n"
            return

        # =====================================================================
        # PRE-RUN FILE SYNC: Ensure files are synced from S3 BEFORE container starts
        # This prevents race conditions where container runs before files exist
        # =====================================================================
        yield f"📥 Ensuring files are synced...\n"
        try:
            from app.services.workspace_restore import workspace_restore
            from app.core.database import get_db

            async for db in get_db():
                # Get project type string for workspace restore
                tech_type_map = {
                    Technology.NODEJS: "node",
                    Technology.NODEJS_VITE: "vite",
                    Technology.PYTHON: "python",
                    Technology.PYTHON_ML: "python",
                    Technology.JAVA: "java",
                    Technology.GO: "go",
                }
                project_type = tech_type_map.get(technology, "node")

                # Check workspace status and auto-restore if needed
                # FIX: Keep user_id as "anonymous" instead of None to maintain path consistency
                # execution.py uses "anonymous" -> /tmp/sandbox/workspace/anonymous/{project_id}
                # This must match here to avoid path mismatch bugs
                restore_result = await workspace_restore.auto_restore(
                    project_id=project_id,
                    db=db,
                    user_id=user_id,  # Keep as "anonymous" if that's what execution.py used
                    project_type=project_type
                )

                if restore_result.get("success"):
                    method = restore_result.get("method", "unknown")
                    if method == "already_exists":
                        yield f"  ✓ Files already synced\n"
                    elif method == "restore_from_storage":
                        restored_count = restore_result.get("restored_files", 0)
                        yield f"  ✓ Restored {restored_count} files from storage\n"
                    else:
                        yield f"  ✓ Workspace ready ({method})\n"
                else:
                    error_msg = restore_result.get("error", "Unknown error")
                    yield f"  ⚠️ File sync warning: {error_msg}\n"
                    logger.warning(f"[ContainerExecutor] File sync warning: {error_msg}")
                break
        except Exception as sync_err:
            logger.warning(f"[ContainerExecutor] Pre-run file sync error: {sync_err}")
            yield f"  ⚠️ File sync check failed (continuing): {sync_err}\n"

        # =====================================================================
        # PRE-RUN VALIDATION: Ensure workspace has all critical files
        # =====================================================================
        yield f"✅ Validating workspace...\n"
        is_valid, validation_msg, missing_files = await self.validate_workspace(project_path, technology)

        if not is_valid:
            yield f"❌ WORKSPACE VALIDATION FAILED\n"
            yield f"  {validation_msg}\n"
            if missing_files:
                yield f"  Missing files:\n"
                for f in missing_files:
                    yield f"    - {f}\n"

            # =====================================================================
            # AUTO-RECOVERY: Attempt to restore/regenerate missing files
            # =====================================================================
            yield f"🔄 Attempting automatic recovery...\n"
            try:
                from app.services.error_recovery import error_recovery, RecoveryType
                from app.core.database import get_db

                # Get database session for recovery
                async for db in get_db():
                    recovery_result = await error_recovery.recover(
                        error_type=RecoveryType.MISSING_FILES,
                        context={
                            "project_id": project_id,
                            "project_path": project_path,
                            "missing_files": missing_files,
                        },
                        db=db
                    )

                    if recovery_result.success:
                        yield f"  ✓ {recovery_result.message}\n"
                        # Re-validate after recovery
                        is_valid, _, _ = await self.validate_workspace(project_path, technology)
                        if is_valid:
                            yield f"  ✓ Workspace now valid - continuing...\n"
                            break  # Continue with run
                        else:
                            yield f"  ✗ Workspace still invalid after recovery\n"
                    else:
                        yield f"  ✗ {recovery_result.message}\n"
                        for step in recovery_result.next_steps:
                            yield f"    → {step}\n"
                        yield f"__VALIDATION_FAILED__:{','.join(missing_files)}\n"
                        return
                    break
            except Exception as recovery_error:
                logger.error(f"[ContainerExecutor] Validation recovery failed: {recovery_error}")
                yield f"  ✗ Recovery error: {recovery_error}\n"
                yield f"__VALIDATION_FAILED__:{','.join(missing_files)}\n"
                return
        else:
            yield f"  ✓ Workspace validation passed\n"

        yield f"🐳 Preparing container...\n"
        yield f"  📁 Project path: {project_path}\n"
        working_dir = "/app/frontend" if getattr(self, '_frontend_subdir', False) else "/app"
        yield f"  📂 Working dir: {working_dir}\n"
        yield f"  🔌 Container port: {config.port}\n"

        # Map Technology to RuntimeType for ExecutionContext
        tech_to_runtime = {
            Technology.NODEJS: RuntimeType.NODE,
            Technology.NODEJS_VITE: RuntimeType.NODE,
            Technology.REACT_NATIVE: RuntimeType.NODE,
            Technology.ANGULAR: RuntimeType.NODE,
            Technology.JAVA: RuntimeType.JAVA,
            Technology.PYTHON: RuntimeType.PYTHON,
            Technology.PYTHON_ML: RuntimeType.PYTHON,
            Technology.GO: RuntimeType.GO,
            Technology.DOTNET: RuntimeType.DOTNET,
            Technology.FLUTTER: RuntimeType.UNKNOWN,
        }
        runtime_type = tech_to_runtime.get(technology, RuntimeType.UNKNOWN)

        # Create ExecutionContext for backend-first error capture
        # This is the SINGLE SOURCE OF TRUTH for error context - NO FRONTEND INVOLVEMENT
        build_cmd = config.build_command or ""
        run_cmd = config.run_command or ""
        full_command = f"{build_cmd} && {run_cmd}" if build_cmd else run_cmd

        exec_ctx = create_execution_context(
            project_id=project_id,
            user_id=user_id,
            command=full_command,
            runtime=runtime_type,
            working_dir=working_dir,
        )
        exec_ctx.start()
        logger.info(f"[ContainerExecutor] Created ExecutionContext for {project_id}: runtime={runtime_type.value}")

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

        # Stream container logs
        container_info = self.active_containers.get(project_id)
        if not container_info:
            yield f"ERROR: Container not found\n"
            return

        try:
            container = self.docker_client.containers.get(container_info["container_id"])

            # Store container ID in execution context
            exec_ctx.container_id = container_info["container_id"]
            exec_ctx.container_name = container_info.get("container_name")

            # =====================================================================
            # HEALTH CHECK: Verify container is ready before running commands
            # =====================================================================
            yield f"🏥 Running container health check...\n"
            is_healthy, health_msg = await self.health_check_container(container)

            if not is_healthy:
                yield f"❌ CONTAINER HEALTH CHECK FAILED\n"
                yield f"  {health_msg}\n"

                # =====================================================================
                # AUTO-RECOVERY: Attempt to restart container
                # =====================================================================
                yield f"🔄 Attempting automatic recovery...\n"
                try:
                    from app.services.error_recovery import error_recovery, RecoveryType

                    recovery_result = await error_recovery.recover(
                        error_type=RecoveryType.CONTAINER_CRASH,
                        context={
                            "project_id": project_id,
                            "container_id": container_info["container_id"],
                        }
                    )

                    if recovery_result.success:
                        yield f"  ✓ {recovery_result.message}\n"
                        # Refresh container reference after restart
                        container = self.docker_client.containers.get(container_info["container_id"])
                    else:
                        yield f"  ✗ Recovery failed: {recovery_result.message}\n"
                        for step in recovery_result.next_steps:
                            yield f"    → {step}\n"
                        yield f"__HEALTH_CHECK_FAILED__:{health_msg}\n"
                        return
                except Exception as recovery_error:
                    logger.error(f"[ContainerExecutor] Recovery failed: {recovery_error}")
                    yield f"  ✗ Recovery error: {recovery_error}\n"
                    yield f"__HEALTH_CHECK_FAILED__:{health_msg}\n"
                    return
            else:
                yield f"  ✓ Container health check passed\n"

            yield f"📜 Streaming container logs...\n\n"

            # Generate preview URL upfront
            preview_url = _get_preview_url(host_port, project_id)
            logger.info(f"[ContainerExecutor] Preview URL generated: {preview_url}")
            yield f"📍 Preview URL: {preview_url}\n\n"

            # Stream logs using async-compatible approach
            # The Docker SDK's logs() is synchronous, so we use a queue-based async pattern
            server_started = False
            has_fatal_error = False

            # Gap #9: Improved port detection patterns for complex URLs
            # These patterns capture ports from various URL formats and log messages
            start_patterns = [
                # Vite/React patterns
                r"Local:\s*https?://[^:\s]+:(\d+)",
                r"VITE.*Local:\s*https?://[^:\s]+:(\d+)",
                r"ready in \d+",  # Vite ready message (no port capture)
                # Generic HTTP URLs with ports (handles IPv4, IPv6, hostnames)
                r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\d+\.\d+\.\d+\.\d+):(\d+)",
                r"https?://\[[^\]]+\]:(\d+)",  # IPv6: http://[::1]:3000, http://[::1%eth0]:3000
                # Explicit port messages
                r"listening on port (\d+)",
                r"listening on.*:(\d+)",
                r"Server running at https?://[^:\s]+:(\d+)",
                r"Started.*on port (\d+)",
                r"started on port (\d+)",  # lowercase variant
                r"ready.*https?://[^:\s]+:(\d+)",
                # Generic patterns
                r"running on.*:(\d+)",
                r"available at.*:(\d+)",
                r"serving on.*:(\d+)",
                r"bound to.*:(\d+)",
                r"Listening on tcp://.*:(\d+)",  # Rails Puma
                # Express.js patterns
                r"Express server listening on (\d+)",
                r"Server listening on (\d+)",
                r"app listening on port (\d+)",
                # Spring Boot/Java patterns
                r"Tomcat started on port\(s\):\s*(\d+)",
                r"Netty started on port\(s\):\s*(\d+)",
                r"Started.*on port (\d+)",
                # Python patterns
                r"Uvicorn running on https?://[^:\s]+:(\d+)",
                r"Running on https?://[^:\s]+:(\d+)",  # Flask
                r"Application startup complete",  # FastAPI/Uvicorn (no port)
                # Compilation success (no port capture)
                r"compiled successfully",  # Webpack
                r"compiled client and server",  # Next.js
            ]

            # Gap #6: Improved error detection patterns - comprehensive across technologies
            # Gap #8: Patterns classified as BUILD or RUNTIME errors
            # BUILD errors: happen during compilation/bundling (npm install, build)
            # RUNTIME errors: happen when server is running (syntax, type errors in execution)
            build_error_patterns = [
                r"npm ERR!",
                r"npm error",  # npm 10+ uses lowercase "error" instead of "ERR!"
                r"404 Not Found",  # npm registry 404
                r"E404",  # npm error code E404
                r"ENOENT: no such file",  # Missing file during build
                r"ERESOLVE",  # npm dependency resolution failed
                r"peer dep missing",  # npm peer dependency
                r"BUILD FAILURE",  # Maven/Gradle
                r"COMPILATION ERROR",  # Java compilation
                r"cannot find symbol",  # Java
                r"package does not exist",  # Java
                r"\[ERROR\].*\.java:\[\d+",  # Maven error format
                r"error\[E\d+\]",  # Rust compilation
                r"error: cannot find",  # Generic compilation
                r"Failed to compile",  # Webpack/Vite
                r"Bundler error",  # esbuild/rollup
                r"Build failed with",  # Generic build
                r"pip install.*failed",  # Python pip
                r"Could not find a version",  # pip/npm version error
            ]
            runtime_error_patterns = [
                r"Error: Cannot find module",  # Node.js runtime
                r"Module not found",  # Module import at runtime
                r"SyntaxError:",
                r"ReferenceError:",
                r"TypeError:",
                r"EADDRINUSE",  # Port already in use
                r"Address already in use",
                r"Permission denied",
                r"Traceback \(most recent call last\)",  # Python runtime
                r"ImportError:",  # Python import
                r"ModuleNotFoundError:",  # Python module
                r"NameError:",  # Python undefined
                r"ValueError:",  # Python value
                r"AttributeError:",  # Python attribute
                r"KeyError:",  # Python key
                r"NullPointerException",  # Java runtime
                r"IllegalArgumentException",  # Java
                r"RuntimeException",  # Java
                r"ClassNotFoundException",  # Java classloader
                r"No such property",  # Groovy/Grails
                r"undefined is not",  # JavaScript runtime
                r"is not defined",  # JavaScript reference
                r"Cannot read properties of",  # JavaScript null access
                # OOM (Out of Memory) detection
                r"JavaScript heap out of memory",
                r"FATAL ERROR.*allocation failed",
                r"Killed",  # Linux OOM killer
                r"out of memory",
                r"Cannot allocate memory",
                r"MemoryError",  # Python OOM
                r"java\.lang\.OutOfMemoryError",  # Java OOM
                r"ENOMEM",  # Node.js memory error
            ]
            # Combined for backward compatibility
            error_patterns = build_error_patterns + runtime_error_patterns

            # Use asyncio queue for thread-safe async log streaming
            log_queue: asyncio.Queue = asyncio.Queue()

            # Get the current event loop BEFORE starting thread
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()

            # ANSI escape code pattern for stripping colors from pattern matching
            ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\r')

            def stream_logs_sync():
                """Synchronous log streaming in separate thread"""
                try:
                    for log in container.logs(stream=True, follow=True, timestamps=False):
                        try:
                            # Decode the chunk
                            chunk = log.decode('utf-8', errors='ignore')
                            # Split by newlines to handle multi-line chunks
                            # Docker logs can send multiple lines in one chunk
                            lines = chunk.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line:
                                    # Put each line in queue separately (thread-safe)
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

            # Process logs from queue asynchronously (Bolt-style health gate)
            # Preview is ONLY enabled after server start is confirmed
            timeout_seconds = adaptive_timeout  # Use adaptive timeout based on project size
            start_time = loop.time()
            error_lines = []  # Collect error lines for context

            while True:
                try:
                    # Wait for log with timeout
                    line = await asyncio.wait_for(log_queue.get(), timeout=5.0)

                    if line is None:
                        # Stream ended
                        break

                    yield f"{line}\n"

                    # Store log in LogBus for auto-fixer context
                    log_bus.add_docker_log(line)

                    # Strip ANSI escape codes for pattern matching (keep original for display)
                    # This fixes Vite detection: "\x1b[32mVITE\x1b[0m ready in 1089 ms" -> "VITE ready in 1089 ms"
                    clean_line = ansi_escape_pattern.sub('', line)

                    # BACKEND-FIRST: Buffer into ExecutionContext (SINGLE SOURCE OF TRUTH)
                    # Detect if line is stderr by checking for error patterns
                    is_stderr_line = any(re.search(p, clean_line, re.IGNORECASE) for p in error_patterns)
                    if is_stderr_line:
                        exec_ctx.add_stderr(line)
                    else:
                        exec_ctx.add_stdout(line)

                    # Check for FATAL ERROR patterns first (Bolt-style)
                    if not has_fatal_error and not server_started:
                        for pattern in error_patterns:
                            if re.search(pattern, clean_line, re.IGNORECASE):
                                has_fatal_error = True
                                error_lines.append(line)
                                # Mark as error in LogBus
                                log_bus.add_docker_error(line)
                                # Also mark in ExecutionContext
                                exec_ctx.add_stderr(line)
                                logger.error(f"[ContainerExecutor] Fatal error detected: {pattern}")

                                # High #10: Special handling for port conflict errors
                                if re.search(r"EADDRINUSE|Address already in use", clean_line, re.IGNORECASE):
                                    yield f"\n⚠️ PORT CONFLICT DETECTED\n"
                                    yield f"The port is already in use. Possible solutions:\n"
                                    yield f"  1. Stop other running projects first\n"
                                    yield f"  2. Wait a moment and try again\n"
                                    yield f"  3. The previous container may still be shutting down\n"
                                    yield f"__PORT_CONFLICT__:{host_port}\n"
                                    log_bus.add_docker_error(f"Port conflict on {host_port}")

                                # Medium #15: Special handling for OOM errors
                                if re.search(r"out of memory|heap out of memory|ENOMEM|MemoryError|OutOfMemoryError|Killed|allocation failed", clean_line, re.IGNORECASE):
                                    yield f"\n⚠️ OUT OF MEMORY DETECTED\n"
                                    yield f"The container ran out of memory. Possible solutions:\n"
                                    yield f"  1. Reduce the number of dependencies\n"
                                    yield f"  2. Optimize your code to use less memory\n"
                                    yield f"  3. Add NODE_OPTIONS=--max-old-space-size=2048 for Node.js\n"
                                    yield f"  4. Try running with fewer concurrent operations\n"
                                    yield f"__OOM_ERROR__:{config.memory_limit}\n"
                                    log_bus.add_docker_error(f"OOM with limit {config.memory_limit}")

                                # Continue collecting a few more error lines for context
                                break

                    # Collect error context (next 3 lines after error)
                    if has_fatal_error and len(error_lines) < 5:
                        if line not in error_lines:
                            error_lines.append(line)
                            # Store error context lines
                            log_bus.add_docker_error(line)
                            exec_ctx.add_stderr(line)

                    # Check for server start patterns (only if no fatal error)
                    # Use clean_line (ANSI stripped) for reliable pattern matching
                    if not server_started and not has_fatal_error:
                        for pattern in start_patterns:
                            match = re.search(pattern, clean_line, re.IGNORECASE)
                            if match:
                                logger.info(f"[ContainerExecutor] Server start pattern matched: {pattern} in: {clean_line[:100]}")
                                yield f"\n🔍 Server start detected, verifying accessibility...\n"

                                # ================================================================
                                # HEALTH CHECK: Verify URL is actually reachable before enabling
                                # Critical #1 & #3: Extended retries with fallback on failure
                                # ================================================================
                                # Use nginx gateway (port 8080) for health check - direct ports are blocked
                                sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST", "")
                                sandbox_ip = "localhost"
                                if sandbox_docker_host and "://" in sandbox_docker_host:
                                    from urllib.parse import urlparse
                                    parsed = urlparse(sandbox_docker_host)
                                    sandbox_ip = parsed.hostname or "localhost"
                                # Route through nginx gateway (port 8080) instead of direct container port
                                # Direct ports are blocked by security groups
                                internal_url = f"http://{sandbox_ip}:8080/sandbox/{host_port}/"
                                health_check_passed = False
                                max_health_attempts = 8  # Critical #3: More retries for slow servers

                                # Try health check with extended retries
                                for attempt in range(max_health_attempts):
                                    try:
                                        # Progressive backoff: 1s, 1.5s, 2s, 2.5s, 3s, 3s, 3s, 3s
                                        wait_time = min(1.0 + (attempt * 0.5), 3.0)
                                        await asyncio.sleep(wait_time)

                                        health_ok = await check_preview_health(internal_url, timeout=5.0)
                                        if health_ok:
                                            health_check_passed = True
                                            logger.info(f"[ContainerExecutor] ✅ Health check passed on attempt {attempt+1}: {internal_url}")
                                            break
                                        else:
                                            logger.warning(f"[ContainerExecutor] Health check attempt {attempt+1}/{max_health_attempts} failed")
                                    except Exception as health_err:
                                        logger.warning(f"[ContainerExecutor] Health check error on attempt {attempt+1}: {health_err}")

                                # Always mark as started and show preview
                                server_started = True
                                exec_ctx.server_started = True
                                exec_ctx.server_url = preview_url

                                if health_check_passed:
                                    exec_ctx.complete(exit_code=0)
                                    logger.info(f"[ContainerExecutor] ✅ Server READY! Health check verified")
                                    yield f"\n{'='*50}\n"
                                    yield f"🚀 SERVER READY - PREVIEW ENABLED!\n"
                                    yield f"Preview URL: {preview_url}\n"
                                    yield f"{'='*50}\n\n"
                                    # Emit markers for frontend - only navigate when READY
                                    yield f"__SERVER_STARTED__:{preview_url}\n"
                                    yield f"_PREVIEW_URL_:{preview_url}\n"
                                    yield f"__PREVIEW_READY__:{preview_url}\n"
                                else:
                                    # Health check failed - show URL but don't auto-navigate
                                    logger.warning(f"[ContainerExecutor] Health check failed after {max_health_attempts} attempts")
                                    yield f"\n{'='*50}\n"
                                    yield f"⏳ SERVER STARTING - Please wait...\n"
                                    yield f"Preview URL: {preview_url}\n"
                                    yield f"Note: Server is still initializing. Will auto-navigate when ready.\n"
                                    yield f"{'='*50}\n\n"
                                    # Keep trying health check in background
                                    yield f"_PREVIEW_URL_:{preview_url}\n"
                                    # Continue health check loop
                                    for retry in range(5):
                                        await asyncio.sleep(3)
                                        try:
                                            if await check_preview_health(internal_url, timeout=5.0):
                                                logger.info(f"[ContainerExecutor] ✅ Delayed health check passed on retry {retry+1}")
                                                yield f"🚀 Server is now ready!\n"
                                                yield f"__PREVIEW_READY__:{preview_url}\n"
                                                exec_ctx.complete(exit_code=0)
                                                break
                                        except Exception:
                                            pass
                                log_bus.add_docker_log(f"Server started - Preview URL: {preview_url}")
                                break

                except asyncio.TimeoutError:
                    # No log for 5 seconds - check if we've timed out or server started
                    elapsed = loop.time() - start_time
                    if elapsed > timeout_seconds and not server_started:
                        logger.warning(f"[ContainerExecutor] Timeout waiting for server start")
                        yield f"\n⚠️ Timeout waiting for server. Container may still be starting...\n"
                        yield f"__ERROR__:Server startup timeout after {timeout_seconds}s\n"
                        log_bus.add_docker_error(f"Server startup timeout after {timeout_seconds}s")
                        break
                    # Server is ready - stop the keepalive loop (BUG FIX: was looping forever)
                    if server_started:
                        logger.info(f"[ContainerExecutor] Server ready, stopping log monitor loop")
                        break
                    # Send keepalive (only if server not yet started)
                    yield f"  ⏳ Waiting for server... ({int(elapsed)}s)\n"
                    continue

            # Cleanup
            executor.shutdown(wait=False)

            # Check if container crashed (for auto-fixer to catch errors)
            if not server_started and not has_fatal_error:
                try:
                    container.reload()
                    container_status = container.status
                    logger.info(f"[ContainerExecutor] Container status after stream end: {container_status}")

                    if container_status == "exited":
                        # Container crashed - get exit code and logs
                        exit_code = container.attrs.get('State', {}).get('ExitCode', -1)
                        logger.error(f"[ContainerExecutor] Container exited with code {exit_code}")

                        if exit_code != 0:
                            # Fetch container logs (even from stopped container)
                            try:
                                crash_logs = container.logs(tail=100).decode('utf-8', errors='ignore')
                                if crash_logs:
                                    logger.error(f"[ContainerExecutor] Container crash logs:\n{crash_logs[:1000]}")

                                    # Parse logs for error lines
                                    for log_line in crash_logs.split('\n'):
                                        log_line = log_line.strip()
                                        if log_line:
                                            # Check for npm/build errors
                                            if any(err in log_line.lower() for err in ['error', 'err!', 'failed', 'not found', '404']):
                                                error_lines.append(log_line)
                                                log_bus.add_docker_error(log_line)
                                            else:
                                                log_bus.add_docker_log(log_line)

                                    # Mark as fatal error if we found error lines
                                    if error_lines:
                                        has_fatal_error = True
                                        log_bus.add_build_error(f"Container crashed (exit code {exit_code}): {error_lines[0]}")
                                        yield f"\n❌ Container crashed with exit code {exit_code}\n"
                                        for err_line in error_lines[:10]:  # Show first 10 error lines
                                            yield f"🔴 {err_line}\n"
                            except Exception as log_err:
                                logger.error(f"[ContainerExecutor] Failed to get crash logs: {log_err}")
                except Exception as reload_err:
                    logger.warning(f"[ContainerExecutor] Failed to check container status: {reload_err}")

            # Handle fatal error - do NOT enable preview (Bolt-style health gate)
            if has_fatal_error:
                logger.error(f"[ContainerExecutor] Preview BLOCKED due to fatal error")

                # Mark failure in ExecutionContext
                exec_ctx.complete(exit_code=1)

                yield f"\n{'='*50}\n"
                yield f"❌ PREVIEW BLOCKED - Fatal Error Detected\n"
                yield f"{'='*50}\n"
                for err_line in error_lines:
                    yield f"🔴 {err_line}\n"

                # Store fatal error summary in LogBus for auto-fixer
                log_bus.add_build_error(f"Fatal error: {error_lines[0] if error_lines else 'Unknown error'}")

                # ================================================================
                # BACKEND-FIRST AUTO-FIX WITH RETRY LOOP
                # Fix → Sync → Restart → Check → Repeat (up to 3 times)
                # NO FRONTEND INVOLVEMENT - this is the correct architecture
                # ================================================================
                if exec_ctx.should_attempt_fix():
                    # Run the fix retry loop
                    async for fix_log in self._run_fix_retry_loop(
                        project_id=project_id,
                        project_path=project_path,
                        container=container,
                        exec_ctx=exec_ctx,
                        run_command=config.run_command,
                        working_dir=working_dir,
                        error_patterns=error_patterns,
                        start_patterns=start_patterns,
                    ):
                        yield fix_log

                    # Check if fix succeeded
                    if exec_ctx.server_started:
                        # Success! Server is running after fix
                        yield f"\n🚀 Preview is now available at: {preview_url}\n"
                        yield f"__SERVER_STARTED__:{preview_url}\n"
                        yield f"_PREVIEW_URL_:{preview_url}\n"
                    else:
                        yield f"__ERROR__:Fatal error detected - preview not available\n"
                else:
                    yield f"\n💡 Fix the error and try again.\n"
                    yield f"__ERROR__:Fatal error detected - preview not available\n"

            # If we exited the loop without detecting server start and no error
            elif not server_started and preview_url:
                logger.warning(f"[ContainerExecutor] Server start not detected, checking if ready...")
                yield f"\n📍 Container running - checking if preview is ready...\n"
                # Try health check before enabling preview
                internal_url = f"http://localhost:{host_port}" if host_port else None
                if internal_url:
                    for attempt in range(5):
                        try:
                            await asyncio.sleep(2)
                            if await check_preview_health(internal_url, timeout=5.0):
                                logger.info(f"[ContainerExecutor] ✅ Server ready on fallback check")
                                yield f"🚀 Server is ready!\n"
                                yield f"_PREVIEW_URL_:{preview_url}\n"
                                yield f"__PREVIEW_READY__:{preview_url}\n"
                                break
                        except Exception:
                            pass
                    else:
                        # All attempts failed - show URL but don't auto-navigate
                        yield f"⏳ Server may still be starting. Preview URL: {preview_url}\n"
                        yield f"_PREVIEW_URL_:{preview_url}\n"

        except Exception as e:
            logger.error(f"[ContainerExecutor] Error streaming logs: {e}")
            log_bus.add_docker_error(f"Error streaming logs: {e}")
            exec_ctx.add_stderr(str(e))
            exec_ctx.complete(exit_code=1)
            yield f"ERROR: Failed to stream logs: {e}\n"

        finally:
            # Cleanup execution context if completed
            if exec_ctx.state in [ExecutionState.SUCCESS, ExecutionState.EXHAUSTED]:
                # Keep context for a while for debugging, but mark as inactive
                logger.info(f"[ContainerExecutor] Execution completed: {exec_ctx.state.value}")


# Global instance
container_executor = ContainerExecutor()
