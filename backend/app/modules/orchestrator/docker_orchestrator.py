"""
Docker Lifecycle Orchestrator - Container Management for Bolt.new Style

Orchestrates Docker container lifecycle with proper ordering:

┌─────────────────────────────────────────────────────────────────┐
│                 DOCKER LIFECYCLE ORCHESTRATION                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CREATION SEQUENCE:                                              │
│  1. Validate project files exist                                 │
│  2. Detect project type (Node, Python, etc.)                     │
│  3. Pull/verify base image                                       │
│  4. Create container with proper config                          │
│  5. Mount project files                                          │
│  6. Start container                                              │
│  7. Wait for port to become available                            │
│  8. Start log collection                                         │
│  9. Emit DOCKER_RUNNING event                                    │
│                                                                  │
│  RESTART SEQUENCE (after auto-fix):                              │
│  1. Stop current container gracefully                            │
│  2. Wait for process termination                                 │
│  3. Start container again                                        │
│  4. Wait for port ready                                          │
│  5. Verify health check                                          │
│  6. Emit DOCKER_RUNNING event                                    │
│  7. Trigger preview reload in frontend                           │
│                                                                  │
│  CLEANUP SEQUENCE:                                               │
│  1. Stop container                                               │
│  2. Remove container                                             │
│  3. Release allocated port                                       │
│  4. Cleanup logs                                                 │
│  5. Emit DOCKER_STOPPED event                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Key Features:
- State machine controlled
- Event-driven notifications
- Log collection → LogBus integration
- Auto-recovery on failure
- Health monitoring
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from app.core.logging_config import logger
from app.modules.orchestrator.state_machine import (
    DockerStateMachine,
    DockerState,
    get_state_manager
)
from app.modules.orchestrator.event_bus import (
    get_event_bus,
    EventType,
    create_docker_event
)
from app.services.log_bus import get_log_bus


class ProjectType(str, Enum):
    """Project types for Docker configuration"""
    NODEJS = "nodejs"
    REACT = "react"
    NEXTJS = "nextjs"
    VUE = "vue"
    PYTHON = "python"
    FASTAPI = "fastapi"
    DJANGO = "django"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    STATIC = "static"
    UNKNOWN = "unknown"


@dataclass
class DockerConfig:
    """Docker container configuration"""
    image: str = "node:20-alpine"
    command: List[str] = field(default_factory=lambda: ["npm", "run", "dev"])
    port: int = 3000
    memory_limit: str = "512m"
    cpu_limit: float = 0.5
    environment: Dict[str, str] = field(default_factory=dict)
    working_dir: str = "/app"
    health_check_path: str = "/"
    startup_timeout: float = 60.0
    graceful_stop_timeout: float = 10.0


# Default configurations per project type
DEFAULT_CONFIGS: Dict[ProjectType, DockerConfig] = {
    ProjectType.NODEJS: DockerConfig(
        image="node:20-alpine",
        command=["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"],
        port=3000
    ),
    ProjectType.REACT: DockerConfig(
        image="node:20-alpine",
        command=["sh", "-c", "npm install && npm start"],
        port=3000
    ),
    ProjectType.NEXTJS: DockerConfig(
        image="node:20-alpine",
        command=["sh", "-c", "npm install && npm run dev"],
        port=3000
    ),
    ProjectType.VUE: DockerConfig(
        image="node:20-alpine",
        command=["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"],
        port=3000
    ),
    ProjectType.PYTHON: DockerConfig(
        image="python:3.11-slim",
        command=["sh", "-c", "pip install -r requirements.txt && python main.py"],
        port=8000
    ),
    ProjectType.FASTAPI: DockerConfig(
        image="python:3.11-slim",
        command=["sh", "-c", "pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"],
        port=8000
    ),
    ProjectType.DJANGO: DockerConfig(
        image="python:3.11-slim",
        command=["sh", "-c", "pip install -r requirements.txt && python manage.py runserver 0.0.0.0:8000"],
        port=8000
    ),
    ProjectType.GO: DockerConfig(
        image="golang:1.21-alpine",
        command=["sh", "-c", "go mod tidy && go run ."],
        port=8080
    ),
    ProjectType.RUST: DockerConfig(
        image="rust:1.74-slim",
        command=["cargo", "run"],
        port=8080
    ),
    ProjectType.JAVA: DockerConfig(
        image="eclipse-temurin:17-jdk-alpine",
        command=["sh", "-c", "./mvnw spring-boot:run"],
        port=8080
    ),
    ProjectType.STATIC: DockerConfig(
        image="nginx:alpine",
        command=["nginx", "-g", "daemon off;"],
        port=80
    ),
}


@dataclass
class ContainerInfo:
    """Information about a running container"""
    container_id: str
    project_id: str
    project_type: ProjectType
    internal_port: int
    external_port: int
    preview_url: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_restart: Optional[datetime] = None
    restart_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_id": self.container_id,
            "project_id": self.project_id,
            "project_type": self.project_type.value,
            "internal_port": self.internal_port,
            "external_port": self.external_port,
            "preview_url": self.preview_url,
            "created_at": self.created_at.isoformat(),
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "restart_count": self.restart_count
        }


class DockerOrchestrator:
    """
    Orchestrates Docker container lifecycle for a project.

    Integrates with:
    - State Machine (for state tracking)
    - Event Bus (for notifications)
    - LogBus (for log collection)
    - DockerSandboxManager (for actual Docker operations)
    """

    def __init__(self, project_id: str):
        self.project_id = project_id

        # State machine
        self._state_machine = get_state_manager().get_docker_machine(project_id)

        # Event bus
        self._event_bus = get_event_bus()

        # Container info
        self._container: Optional[ContainerInfo] = None

        # Log collection task
        self._log_task: Optional[asyncio.Task] = None

        # Health check task
        self._health_task: Optional[asyncio.Task] = None

        logger.info(f"[DockerOrchestrator:{project_id}] Initialized")

    @property
    def state(self) -> DockerState:
        """Get current Docker state"""
        return self._state_machine.state

    @property
    def is_running(self) -> bool:
        """Check if container is running"""
        return self._state_machine.state == DockerState.RUNNING

    async def start(
        self,
        files_path: str,
        project_type: Optional[ProjectType] = None,
        config_override: Optional[DockerConfig] = None
    ) -> Dict[str, Any]:
        """
        Start Docker container for the project.

        Args:
            files_path: Path to project files
            project_type: Type of project (auto-detect if None)
            config_override: Custom Docker config

        Returns:
            Result dict with container info
        """
        try:
            # ========== STEP 1: Validate & Detect ==========
            if project_type is None:
                project_type = await self._detect_project_type(files_path)

            config = config_override or DEFAULT_CONFIGS.get(
                project_type,
                DEFAULT_CONFIGS[ProjectType.NODEJS]
            )

            # ========== STEP 2: Create Container ==========
            self._state_machine.create()
            await self._emit_event(EventType.DOCKER_CREATING, {
                "project_type": project_type.value
            })

            from app.services.docker_sandbox import docker_sandbox, ProjectType as SandboxProjectType

            # Map to sandbox project type
            sandbox_type = getattr(SandboxProjectType, project_type.value.upper(), SandboxProjectType.NODEJS)

            sandbox = await docker_sandbox.create_sandbox(
                project_id=self.project_id,
                user_id="system",  # Will be set properly in production
                project_type=sandbox_type,
                files_path=files_path,
                environment=config.environment
            )

            # ========== STEP 3: Start Container ==========
            self._state_machine.start()
            await self._emit_event(EventType.DOCKER_STARTED, {
                "container_id": sandbox.container_id
            })

            # ========== STEP 4: Wait for Ready ==========
            ready = await self._wait_for_ready(
                sandbox.external_port,
                timeout=config.startup_timeout
            )

            if not ready:
                raise Exception("Container failed to become ready")

            # ========== STEP 5: Store Info ==========
            self._container = ContainerInfo(
                container_id=sandbox.container_id,
                project_id=self.project_id,
                project_type=project_type,
                internal_port=sandbox.internal_port,
                external_port=sandbox.external_port,
                preview_url=sandbox.preview_url
            )

            # ========== STEP 6: Start Log Collection ==========
            self._start_log_collection(sandbox.sandbox_id)

            # ========== STEP 7: Start Health Monitor ==========
            self._start_health_monitor()

            # ========== STEP 8: Mark Running ==========
            self._state_machine.running()
            await self._emit_event(EventType.DOCKER_RUNNING, {
                "container_id": sandbox.container_id,
                "port": sandbox.external_port,
                "url": sandbox.preview_url
            })

            logger.info(
                f"[DockerOrchestrator:{self.project_id}] "
                f"Container started: {sandbox.preview_url}"
            )

            return {
                "success": True,
                "container": self._container.to_dict()
            }

        except Exception as e:
            logger.error(f"[DockerOrchestrator:{self.project_id}] Start failed: {e}")
            self._state_machine.fail(str(e))
            await self._emit_event(EventType.DOCKER_FAILED, {
                "error": str(e),
                "stage": "start"
            })
            return {
                "success": False,
                "error": str(e)
            }

    async def stop(self, graceful: bool = True) -> Dict[str, Any]:
        """
        Stop Docker container.

        Args:
            graceful: Wait for graceful shutdown

        Returns:
            Result dict
        """
        try:
            if self._state_machine.state == DockerState.NONE:
                return {"success": True, "message": "Container not running"}

            # ========== STEP 1: Stop Log Collection ==========
            self._stop_log_collection()
            self._stop_health_monitor()

            # ========== STEP 2: Stop Container ==========
            self._state_machine.stop()
            await self._emit_event(EventType.DOCKER_STOPPING, {})

            if self._container:
                from app.services.docker_sandbox import docker_sandbox

                sandbox = await docker_sandbox.get_sandbox_by_project(self.project_id)
                if sandbox:
                    await docker_sandbox.stop_sandbox(sandbox.sandbox_id)

            # ========== STEP 3: Mark Stopped ==========
            self._state_machine.stopped()
            await self._emit_event(EventType.DOCKER_STOPPED, {})

            self._container = None

            logger.info(f"[DockerOrchestrator:{self.project_id}] Container stopped")

            return {"success": True}

        except Exception as e:
            logger.error(f"[DockerOrchestrator:{self.project_id}] Stop failed: {e}")
            return {"success": False, "error": str(e)}

    async def restart(self) -> Dict[str, Any]:
        """
        Restart Docker container (used after auto-fix).

        This is the critical operation that makes auto-fix work:
        1. Stop current container gracefully
        2. Wait for cleanup
        3. Start container again
        4. Wait for ready
        5. Notify frontend to reload preview

        Returns:
            Result dict
        """
        try:
            if not self._container:
                return {"success": False, "error": "No container to restart"}

            logger.info(f"[DockerOrchestrator:{self.project_id}] Restarting container...")

            # ========== STEP 1: Mark Restarting ==========
            self._state_machine.restart()
            await self._emit_event(EventType.DOCKER_RESTARTING, {
                "restart_count": self._container.restart_count + 1
            })

            # ========== STEP 2: Stop Log Collection Temporarily ==========
            self._stop_log_collection()

            # ========== STEP 3: Restart Container ==========
            from app.services.docker_sandbox import docker_sandbox

            sandbox = await docker_sandbox.get_sandbox_by_project(self.project_id)
            if sandbox:
                # Stop
                container = docker_sandbox._get_client().containers.get(sandbox.container_id)
                container.restart(timeout=10)

                # Wait for ready
                ready = await self._wait_for_ready(sandbox.external_port, timeout=30)
                if not ready:
                    raise Exception("Container failed to become ready after restart")

            # ========== STEP 4: Restart Log Collection ==========
            if sandbox:
                self._start_log_collection(sandbox.sandbox_id)

            # ========== STEP 5: Update Info ==========
            self._container.last_restart = datetime.utcnow()
            self._container.restart_count += 1

            # ========== STEP 6: Mark Running ==========
            self._state_machine.running()
            await self._emit_event(EventType.DOCKER_RUNNING, {
                "container_id": self._container.container_id,
                "restart_count": self._container.restart_count,
                "restarted": True
            })

            # ========== STEP 7: Notify Preview Reload ==========
            await self._emit_event(EventType.PREVIEW_RELOADING, {
                "url": self._container.preview_url
            })

            logger.info(
                f"[DockerOrchestrator:{self.project_id}] "
                f"Container restarted (count: {self._container.restart_count})"
            )

            return {
                "success": True,
                "container": self._container.to_dict()
            }

        except Exception as e:
            logger.error(f"[DockerOrchestrator:{self.project_id}] Restart failed: {e}")
            self._state_machine.fail(str(e))
            await self._emit_event(EventType.DOCKER_FAILED, {
                "error": str(e),
                "stage": "restart"
            })
            return {"success": False, "error": str(e)}

    async def execute_command(
        self,
        command: List[str],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Execute command in container"""
        if not self._container:
            return {"success": False, "error": "No container running"}

        try:
            from app.services.docker_sandbox import docker_sandbox

            sandbox = await docker_sandbox.get_sandbox_by_project(self.project_id)
            if not sandbox:
                return {"success": False, "error": "Sandbox not found"}

            result = await asyncio.wait_for(
                docker_sandbox.execute_command(sandbox.sandbox_id, command),
                timeout=timeout
            )

            return result

        except asyncio.TimeoutError:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_logs(self, tail: int = 100) -> List[str]:
        """Get container logs"""
        if not self._container:
            return []

        try:
            from app.services.docker_sandbox import docker_sandbox

            sandbox = await docker_sandbox.get_sandbox_by_project(self.project_id)
            if sandbox:
                return await docker_sandbox.get_logs(sandbox.sandbox_id, tail=tail)
            return []

        except Exception as e:
            logger.error(f"[DockerOrchestrator:{self.project_id}] Get logs failed: {e}")
            return []

    # ========== Internal Methods ==========

    async def _detect_project_type(self, files_path: str) -> ProjectType:
        """Detect project type from files"""
        import os

        try:
            files = os.listdir(files_path)
            files_lower = [f.lower() for f in files]

            if "next.config.js" in files_lower or "next.config.ts" in files_lower:
                return ProjectType.NEXTJS
            if "vite.config.ts" in files_lower or "vite.config.js" in files_lower:
                return ProjectType.VUE
            if "manage.py" in files_lower:
                return ProjectType.DJANGO
            if "requirements.txt" in files_lower:
                # Check for FastAPI
                req_path = os.path.join(files_path, "requirements.txt")
                if os.path.exists(req_path):
                    with open(req_path) as f:
                        if "fastapi" in f.read().lower():
                            return ProjectType.FASTAPI
                return ProjectType.PYTHON
            if "go.mod" in files_lower:
                return ProjectType.GO
            if "Cargo.toml" in files_lower:
                return ProjectType.RUST
            if "pom.xml" in files_lower or "build.gradle" in files_lower:
                return ProjectType.JAVA
            if "package.json" in files_lower:
                # Check for React/Next
                pkg_path = os.path.join(files_path, "package.json")
                if os.path.exists(pkg_path):
                    import json
                    with open(pkg_path) as f:
                        pkg = json.load(f)
                        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                        if "next" in deps:
                            return ProjectType.NEXTJS
                        if "react" in deps:
                            return ProjectType.REACT
                return ProjectType.NODEJS
            if "index.html" in files_lower:
                return ProjectType.STATIC

            return ProjectType.UNKNOWN

        except Exception as e:
            logger.warning(f"[DockerOrchestrator:{self.project_id}] Type detection failed: {e}")
            return ProjectType.UNKNOWN

    async def _wait_for_ready(self, port: int, timeout: float = 60.0) -> bool:
        """Wait for container to become ready (port accepting connections)"""
        import socket

        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()

                if result == 0:
                    logger.debug(f"[DockerOrchestrator:{self.project_id}] Port {port} ready")
                    return True

            except Exception:
                pass

            await asyncio.sleep(1)

        logger.warning(f"[DockerOrchestrator:{self.project_id}] Port {port} not ready after {timeout}s")
        return False

    def _start_log_collection(self, sandbox_id: str):
        """Start collecting logs from container"""
        if self._log_task and not self._log_task.done():
            self._log_task.cancel()

        self._log_task = asyncio.create_task(
            self._collect_logs(sandbox_id)
        )

    def _stop_log_collection(self):
        """Stop log collection"""
        if self._log_task and not self._log_task.done():
            self._log_task.cancel()
        self._log_task = None

    async def _collect_logs(self, sandbox_id: str):
        """Background task to collect container logs"""
        import re

        log_bus = get_log_bus(self.project_id)

        # Error patterns
        error_patterns = [
            (r'error', 'error'),
            (r'Error:', 'error'),
            (r'ERROR', 'error'),
            (r'failed', 'error'),
            (r'FAILED', 'error'),
            (r'Module not found', 'error'),
            (r'Cannot find module', 'error'),
        ]

        try:
            from app.services.docker_sandbox import docker_sandbox

            while True:
                try:
                    sandbox = await docker_sandbox.get_sandbox(sandbox_id)
                    if not sandbox or not sandbox.container_id:
                        break

                    client = docker_sandbox._get_client()
                    container = client.containers.get(sandbox.container_id)

                    # Stream logs
                    for line in container.logs(stream=True, follow=True, since=1):
                        text = line.decode('utf-8', errors='ignore').strip()
                        if not text:
                            continue

                        # Determine level
                        level = "info"
                        for pattern, lvl in error_patterns:
                            if re.search(pattern, text, re.IGNORECASE):
                                level = lvl
                                break

                        # Add to LogBus
                        if level == "error":
                            log_bus.add_docker_error(text)
                            # Emit error event for auto-fix
                            await self._emit_event(EventType.ERROR_DOCKER, {
                                "message": text
                            })
                        else:
                            log_bus.add_docker_log(text, level=level)

                        # Emit log event
                        await self._emit_event(EventType.DOCKER_LOGS, {
                            "log": text,
                            "level": level
                        })

                except Exception as e:
                    logger.debug(f"[DockerOrchestrator:{self.project_id}] Log collection error: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.debug(f"[DockerOrchestrator:{self.project_id}] Log collection cancelled")

    def _start_health_monitor(self):
        """Start health monitoring"""
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()

        self._health_task = asyncio.create_task(
            self._monitor_health()
        )

    def _stop_health_monitor(self):
        """Stop health monitoring"""
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
        self._health_task = None

    async def _monitor_health(self):
        """Monitor container health"""
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds

                if not self._container:
                    break

                # Check if container is still running
                from app.services.docker_sandbox import docker_sandbox

                sandbox = await docker_sandbox.get_sandbox_by_project(self.project_id)
                if not sandbox or sandbox.status.value != "running":
                    logger.warning(
                        f"[DockerOrchestrator:{self.project_id}] "
                        f"Container unhealthy, triggering restart"
                    )
                    await self.restart()

        except asyncio.CancelledError:
            pass

    async def _emit_event(self, event_type: EventType, data: Dict[str, Any]):
        """Emit event to event bus"""
        await self._event_bus.emit_async(
            event_type,
            self.project_id,
            data,
            source="DockerOrchestrator"
        )

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "project_id": self.project_id,
            "state": self._state_machine.state.value,
            "container": self._container.to_dict() if self._container else None,
            "log_collection_active": self._log_task is not None and not self._log_task.done(),
            "health_monitor_active": self._health_task is not None and not self._health_task.done()
        }


# ========== Manager ==========

class DockerOrchestratorManager:
    """Manages DockerOrchestrator instances"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._orchestrators: Dict[str, DockerOrchestrator] = {}
        return cls._instance

    def get_or_create(self, project_id: str) -> DockerOrchestrator:
        """Get or create orchestrator for a project"""
        if project_id not in self._orchestrators:
            self._orchestrators[project_id] = DockerOrchestrator(project_id)
        return self._orchestrators[project_id]

    def remove(self, project_id: str):
        """Remove orchestrator for a project"""
        if project_id in self._orchestrators:
            del self._orchestrators[project_id]

    async def stop_all(self):
        """Stop all containers"""
        for orchestrator in self._orchestrators.values():
            await orchestrator.stop()


# Global manager
docker_orchestrator_manager = DockerOrchestratorManager()


def get_docker_orchestrator(project_id: str) -> DockerOrchestrator:
    """Get Docker orchestrator for a project"""
    return docker_orchestrator_manager.get_or_create(project_id)
