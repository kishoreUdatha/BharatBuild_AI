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
from typing import Optional, Dict, Any, Tuple, AsyncGenerator, List
from dataclasses import dataclass
from enum import Enum
import uuid
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from app.core.logging_config import logger
from app.services.execution_context import (
    ExecutionContext,
    ExecutionState,
    RuntimeType,
    create_execution_context,
    get_execution_context,
    remove_execution_context,
)

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


# MEDIUM #8: Default memory limit for containers - configurable via env
import os as _os
DEFAULT_CONTAINER_MEMORY = _os.environ.get("CONTAINER_MEMORY_LIMIT", "768m")

# Pre-built images for each technology - Universal Preview Architecture
TECHNOLOGY_CONFIGS: Dict[Technology, ContainerConfig] = {
    # ==================== FRONTEND FRAMEWORKS ====================
    Technology.NODEJS: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install",
        run_command="npm run dev -- --host 0.0.0.0 --no-open",
        port=3000,
        memory_limit=DEFAULT_CONTAINER_MEMORY  # MEDIUM #8: Increased from 512m
    ),
    Technology.NODEJS_VITE: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install",
        run_command="npm run dev -- --host 0.0.0.0 --no-open",
        port=5173,  # Vite default port
        memory_limit=DEFAULT_CONTAINER_MEMORY  # MEDIUM #8: Increased from 512m
    ),
    Technology.ANGULAR: ContainerConfig(
        image="node:20-alpine",
        build_command="npm install",
        run_command="npm run start -- --host 0.0.0.0 --port 4200 --disable-host-check",
        port=4200,
        memory_limit=DEFAULT_CONTAINER_MEMORY  # MEDIUM #8: Increased from 512m
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
        # High #7: Docker API timeout for remote mode (prevents indefinite hangs)
        DOCKER_API_TIMEOUT = 30  # 30 seconds timeout for Docker API calls

        try:
            # First, try SANDBOX_DOCKER_HOST env var (for ECS -> EC2 sandbox connection)
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST") or os.environ.get("DOCKER_HOST")
            if sandbox_docker_host:
                try:
                    self.docker_client = docker.DockerClient(
                        base_url=sandbox_docker_host,
                        timeout=DOCKER_API_TIMEOUT  # High #7: Add timeout
                    )
                    self.docker_client.ping()
                    logger.info(f"[ContainerExecutor] Docker client initialized via SANDBOX_DOCKER_HOST: {sandbox_docker_host} (timeout={DOCKER_API_TIMEOUT}s)")
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
                parent_mount = "/tmp/sandbox/workspace"

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
                            volumes={"/tmp/sandbox/workspace": {"bind": "/tmp/sandbox/workspace", "mode": "ro"}}
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

        # Base timeouts by technology
        base_timeouts = {
            Technology.NODEJS: 60,
            Technology.NODEJS_VITE: 60,
            Technology.ANGULAR: 90,
            Technology.JAVA: 180,  # Maven is slow
            Technology.PYTHON: 90,
            Technology.PYTHON_ML: 180,  # ML deps are large
            Technology.GO: 60,
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

        # Check if multi-folder project - need to force recreate container with correct working_dir
        is_frontend_subdir = getattr(self, '_frontend_subdir', False)

        # ===== OPTIMIZATION: Try to reuse existing container =====
        # BUT: Skip reuse if multi-folder project detected (needs correct working_dir)
        existing_container = await self._get_existing_container(project_id)
        if existing_container and not is_frontend_subdir:
            reused, message, port = await self._reuse_container(existing_container, project_id, user_id)
            if reused:
                return True, message, port
            # If reuse failed, continue to create new container
            logger.info(f"[ContainerExecutor] Container reuse failed, creating new: {message}")
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
                run_command = f"npm run dev -- --host 0.0.0.0 --port 5173"
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

            container = self.docker_client.containers.run(
                image=config.image,
                name=container_name,
                detach=True,
                working_dir=working_dir,
                volumes={
                    path_str: {"bind": "/app", "mode": "rw"}
                },
                ports={f"{config.port}/tcp": host_port},  # Map container port to host port
                network="bharatbuild-sandbox",
                mem_limit=config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(config.cpu_limit * 100000),
                environment={
                    "NODE_ENV": "development",
                    "JAVA_OPTS": "-Xmx512m",
                    "PYTHONUNBUFFERED": "1",
                    # Critical #2: No custom base paths needed
                    # Proxy handles path translation, so frameworks use default root paths
                    "PUBLIC_URL": "",  # CRA: empty = use relative paths
                    "VITE_BASE_PATH": "/",  # Vite: root path (proxy strips prefix)
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

        # Get all used host ports from active containers (check both "host_port" and "port" keys)
        used_ports = {info.get("host_port") or info.get("port", 0) for info in self.active_containers.values()}

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
                    local_path = Path(project_path) / rel_path
                    if local_path.exists():
                        # Add file to tar with correct path in container
                        tar.add(str(local_path), arcname=rel_path)
                        logger.info(f"[ContainerExecutor] Adding to sync: {rel_path}")

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
            # Start the dev server in background
            exec_result = container.exec_run(
                f"sh -c 'cd {working_dir} && {run_command}'",
                detach=True,
                workdir=working_dir
            )
            logger.info(f"[ContainerExecutor] Restarted dev server: {run_command}")
            return True

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
        from app.services.simple_fixer import simple_fixer

        while exec_ctx.should_attempt_fix():
            attempt = exec_ctx.fix_attempt + 1
            yield f"\n{'='*50}\n"
            yield f"🔧 AUTO-FIX: Attempt {attempt}/{exec_ctx.max_fix_attempts}\n"
            yield f"{'='*50}\n"
            yield f"__FIX_STARTING__\n"

            # Step 1: Get fix from AI
            yield f"📊 Analyzing error...\n"
            payload = exec_ctx.get_fixer_payload()

            try:
                fix_result = await simple_fixer.fix_from_backend(
                    project_id=project_id,
                    project_path=Path(project_path),
                    payload=payload
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

            # Step 3: Sync files to container
            yield f"📦 Syncing fixes to container...\n"
            sync_success = await self._sync_files_to_container(
                container=container,
                project_path=project_path,
                files_modified=fix_result.files_modified
            )

            if not sync_success:
                yield f"⚠️ Failed to sync files, but fixes are saved locally.\n"

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
            from app.core.database import get_session

            async for db in get_session():
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
                restore_result = await workspace_restore.auto_restore(
                    project_id=project_id,
                    db=db,
                    user_id=user_id if user_id != "anonymous" else None,
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
                from app.core.database import get_session

                # Get database session for recovery
                async for db in get_session():
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

            # Gap #6: Flexible port detection patterns (not hardcoded to 3000/5173)
            # These patterns capture any port from logs dynamically
            start_patterns = [
                r"Local:\s*http://\S+:(\d+)",
                r"listening on port (\d+)",
                r"Server running at http://\S+:(\d+)",
                r"Started.*on port (\d+)",
                r"ready.*http://\S+:(\d+)",
                r"VITE.*Local:\s*http://\S+:(\d+)",
                r"http://(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)",  # Generic localhost URLs
                r"https?://\[?::1?\]?:(\d+)",  # IPv6 localhost
                r"running on.*:(\d+)",  # Generic "running on" patterns
                r"available at.*:(\d+)",  # "available at" patterns
                r"serving on.*:(\d+)",  # Python http.server
                r"bound to.*:(\d+)",  # Bound to port
                r"ready in \d+",  # Vite ready message (no port capture)
                r"compiled successfully",  # Webpack
                r"compiled client and server",  # Next.js
                r"Application startup complete",  # FastAPI/Uvicorn
                r"Listening on tcp://.*:(\d+)",  # Rails Puma
            ]

            # Fatal error patterns - stop and show error (Bolt-style)
            # Medium #15: Added OOM detection patterns
            error_patterns = [
                r"npm ERR!",
                r"npm error",  # npm 10+ uses lowercase "error" instead of "ERR!"
                r"Error: Cannot find module",
                r"Module not found",
                r"SyntaxError:",
                r"ReferenceError:",
                r"TypeError:",
                r"EADDRINUSE",
                r"Address already in use",
                r"ENOENT: no such file",
                r"Permission denied",
                r"Traceback \(most recent call last\)",
                r"ImportError:",
                r"ModuleNotFoundError:",
                r"404 Not Found",  # npm registry 404
                r"E404",  # npm error code E404
                # Medium #15: OOM (Out of Memory) detection
                r"JavaScript heap out of memory",
                r"FATAL ERROR.*allocation failed",
                r"Killed",  # Linux OOM killer
                r"out of memory",
                r"Cannot allocate memory",
                r"MemoryError",  # Python OOM
                r"java\.lang\.OutOfMemoryError",  # Java OOM
                r"ENOMEM",  # Node.js memory error
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

                    # BACKEND-FIRST: Buffer into ExecutionContext (SINGLE SOURCE OF TRUTH)
                    # Detect if line is stderr by checking for error patterns
                    is_stderr_line = any(re.search(p, line, re.IGNORECASE) for p in error_patterns)
                    if is_stderr_line:
                        exec_ctx.add_stderr(line)
                    else:
                        exec_ctx.add_stdout(line)

                    # Check for FATAL ERROR patterns first (Bolt-style)
                    if not has_fatal_error and not server_started:
                        for pattern in error_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                has_fatal_error = True
                                error_lines.append(line)
                                # Mark as error in LogBus
                                log_bus.add_docker_error(line)
                                # Also mark in ExecutionContext
                                exec_ctx.add_stderr(line)
                                logger.error(f"[ContainerExecutor] Fatal error detected: {pattern}")

                                # High #10: Special handling for port conflict errors
                                if re.search(r"EADDRINUSE|Address already in use", line, re.IGNORECASE):
                                    yield f"\n⚠️ PORT CONFLICT DETECTED\n"
                                    yield f"The port is already in use. Possible solutions:\n"
                                    yield f"  1. Stop other running projects first\n"
                                    yield f"  2. Wait a moment and try again\n"
                                    yield f"  3. The previous container may still be shutting down\n"
                                    yield f"__PORT_CONFLICT__:{host_port}\n"
                                    log_bus.add_docker_error(f"Port conflict on {host_port}")

                                # Medium #15: Special handling for OOM errors
                                if re.search(r"out of memory|heap out of memory|ENOMEM|MemoryError|OutOfMemoryError|Killed|allocation failed", line, re.IGNORECASE):
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
                    if not server_started and not has_fatal_error:
                        for pattern in start_patterns:
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                logger.info(f"[ContainerExecutor] Server start pattern matched: {pattern}")
                                yield f"\n🔍 Server start detected, verifying accessibility...\n"

                                # ================================================================
                                # HEALTH CHECK: Verify URL is actually reachable before enabling
                                # Critical #1 & #3: Extended retries with fallback on failure
                                # ================================================================
                                internal_url = f"http://localhost:{host_port}"
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
                                else:
                                    # Critical #1: FALLBACK - Show preview with warning instead of blocking
                                    logger.warning(f"[ContainerExecutor] Health check failed after {max_health_attempts} attempts, enabling preview anyway")
                                    yield f"\n{'='*50}\n"
                                    yield f"⚠️ SERVER DETECTED - PREVIEW ENABLED (unverified)\n"
                                    yield f"Preview URL: {preview_url}\n"
                                    yield f"Note: Server may still be starting. Refresh if blank.\n"
                                    yield f"{'='*50}\n\n"

                                # Emit markers for frontend to enable preview
                                yield f"__SERVER_STARTED__:{preview_url}\n"
                                yield f"_PREVIEW_URL_:{preview_url}\n"
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
                    # Send keepalive
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
                logger.warning(f"[ContainerExecutor] Server start not detected, emitting URL anyway")
                yield f"\n📍 Container running - Preview may be available at: {preview_url}\n"
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
