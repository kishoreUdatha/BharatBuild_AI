"""
Unified Orchestrator - The Brain of BharatBuild AI (Bolt.new Style)

This is the CENTRAL COORDINATOR that ties together:
- State Machine (predictable state transitions)
- Event Bus (component communication)
- Auto-Fix Orchestrator (automatic error fixing)
- Docker Orchestrator (container lifecycle)
- Agent Workflow (plan → write → fix → docs)

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED ORCHESTRATOR                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    STATE MACHINE                         │    │
│  │  IDLE → PLANNING → WRITING → BUILDING → FIXING → DONE   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      EVENT BUS                           │    │
│  │  Publish events to all subscribers (SSE to frontend)     │    │
│  └─────────────────────────────────────────────────────────┘    │
│           │              │              │              │         │
│           ▼              ▼              ▼              ▼         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐  │
│  │ AUTO-FIX     │ │ DOCKER       │ │ PREVIEW      │ │ AGENTS │  │
│  │ ORCHESTRATOR │ │ ORCHESTRATOR │ │ SERVER       │ │        │  │
│  │              │ │              │ │              │ │ Planner│  │
│  │ Detect Error │ │ Start/Stop   │ │ Start/Reload │ │ Writer │  │
│  │ Call Fixer   │ │ Container    │ │ Preview      │ │ Fixer  │  │
│  │ Apply Patch  │ │ Restart      │ │              │ │ Runner │  │
│  │ Restart      │ │ Log Collect  │ │              │ │ Docs   │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘  │
│                                                                  │
│  User Request                                                    │
│       │                                                          │
│       ▼                                                          │
│  execute_workflow()                                              │
│       │                                                          │
│       ├─► 1. PLANNER AGENT → Create Plan                        │
│       ├─► 2. WRITER AGENT → Generate Files (streaming)          │
│       ├─► 3. Docker Start → Run Project                         │
│       ├─► 4. Auto-Fix Loop → Detect & Fix Errors                │
│       ├─► 5. RUNNER AGENT → Build & Test                        │
│       └─► 6. DOCUMENTER → Generate Docs                         │
│                                                                  │
│  All events stream to frontend via SSE                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Key Features:
- Single entry point for all orchestration
- Automatic error detection and fixing
- Real-time progress streaming
- Predictable state transitions
- Component coordination
"""

import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from app.core.logging_config import logger

# Import orchestration components
from app.modules.orchestrator.state_machine import (
    get_state_manager,
    ProjectState,
    DockerState,
    FixLoopState,
    OrchestratorState
)
from app.modules.orchestrator.event_bus import (
    get_event_bus,
    EventType,
    EventBus,
    OrchestratorEvent
)
from app.modules.orchestrator.auto_fix_orchestrator import (
    get_auto_fix_orchestrator,
    AutoFixConfig,
    AutoFixOrchestrator
)
from app.modules.orchestrator.docker_orchestrator import (
    get_docker_orchestrator,
    DockerOrchestrator
)


@dataclass
class WorkflowConfig:
    """Configuration for workflow execution"""
    # Workflow steps
    enable_planning: bool = True
    enable_writing: bool = True
    enable_verification: bool = True
    enable_docker: bool = True
    enable_auto_fix: bool = True
    enable_documentation: bool = True

    # Auto-fix settings
    auto_fix_enabled: bool = True
    max_fix_attempts: int = 3

    # Timeouts
    planning_timeout: float = 120.0
    writing_timeout: float = 300.0
    build_timeout: float = 180.0
    fix_timeout: float = 60.0

    # Streaming
    stream_file_content: bool = True
    stream_terminal_output: bool = True


@dataclass
class WorkflowContext:
    """Context maintained throughout workflow execution"""
    project_id: str
    user_request: str
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # State
    current_step: int = 0
    total_steps: int = 6

    # Plan
    plan: Optional[Dict[str, Any]] = None
    tech_stack: Optional[str] = None
    project_type: Optional[str] = None

    # Files
    files_created: List[Dict[str, Any]] = field(default_factory=list)
    files_modified: List[Dict[str, Any]] = field(default_factory=list)

    # Errors
    errors: List[Dict[str, Any]] = field(default_factory=list)
    fix_attempts: int = 0

    # Timestamps
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "workflow_id": self.workflow_id,
            "user_request": self.user_request[:100] + "..." if len(self.user_request) > 100 else self.user_request,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "files_created": len(self.files_created),
            "files_modified": len(self.files_modified),
            "errors": len(self.errors),
            "fix_attempts": self.fix_attempts,
            "duration_ms": (
                (self.completed_at or datetime.utcnow()) - self.started_at
            ).total_seconds() * 1000
        }


class UnifiedOrchestrator:
    """
    The central orchestrator that coordinates all components.

    This is what makes BharatBuild feel like Bolt.new:
    - Smooth project generation
    - Automatic error fixing
    - Real-time progress updates
    - Predictable behavior
    """

    def __init__(self, project_id: str, config: Optional[WorkflowConfig] = None):
        self.project_id = project_id
        self.config = config or WorkflowConfig()

        # Get component orchestrators
        self._state_manager = get_state_manager()
        self._event_bus = get_event_bus()
        self._auto_fix = get_auto_fix_orchestrator(
            project_id,
            AutoFixConfig(
                enabled=self.config.auto_fix_enabled,
                max_attempts=self.config.max_fix_attempts
            )
        )
        self._docker = get_docker_orchestrator(project_id)

        # State machines
        self._project_sm = self._state_manager.get_project_machine(project_id)

        # Current workflow context
        self._context: Optional[WorkflowContext] = None

        # SSE queue for streaming
        self._sse_queue = self._event_bus.create_sse_queue(project_id)

        logger.info(f"[UnifiedOrchestrator:{project_id}] Initialized")

    async def execute_workflow(
        self,
        user_request: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute the complete workflow with streaming.

        This is the main entry point for project generation.

        Args:
            user_request: User's project request
            initial_context: Optional context (files, history, etc.)

        Yields:
            OrchestratorEvent objects for SSE streaming
        """
        # Initialize context
        self._context = WorkflowContext(
            project_id=self.project_id,
            user_request=user_request
        )

        try:
            # ========== START ==========
            self._project_sm.start()
            yield await self._emit(EventType.PROJECT_STARTED, {
                "workflow_id": self._context.workflow_id,
                "request": user_request[:200]
            })

            # ========== STEP 1: PLANNING ==========
            if self.config.enable_planning:
                self._context.current_step = 1
                self._project_sm.plan()

                yield await self._emit(EventType.STATUS, {
                    "message": "Analyzing requirements and creating plan...",
                    "step": 1,
                    "total_steps": self._context.total_steps
                })

                async for event in self._execute_planning(user_request, initial_context):
                    yield event

            # ========== STEP 2: WRITING ==========
            if self.config.enable_writing and self._context.plan:
                self._context.current_step = 2
                self._project_sm.write()

                yield await self._emit(EventType.STATUS, {
                    "message": "Generating code files...",
                    "step": 2,
                    "total_steps": self._context.total_steps
                })

                async for event in self._execute_writing():
                    yield event

            # ========== STEP 3: DOCKER START ==========
            if self.config.enable_docker and self._context.files_created:
                self._context.current_step = 3

                yield await self._emit(EventType.STATUS, {
                    "message": "Starting development server...",
                    "step": 3,
                    "total_steps": self._context.total_steps
                })

                async for event in self._execute_docker_start():
                    yield event

            # ========== STEP 4: BUILD & FIX LOOP ==========
            if self.config.enable_auto_fix:
                self._context.current_step = 4
                self._project_sm.build()

                yield await self._emit(EventType.STATUS, {
                    "message": "Building and checking for errors...",
                    "step": 4,
                    "total_steps": self._context.total_steps
                })

                async for event in self._execute_build_and_fix():
                    yield event

            # ========== STEP 5: VERIFICATION ==========
            if self.config.enable_verification:
                self._context.current_step = 5

                yield await self._emit(EventType.STATUS, {
                    "message": "Verifying project...",
                    "step": 5,
                    "total_steps": self._context.total_steps
                })

                async for event in self._execute_verification():
                    yield event

            # ========== STEP 6: DOCUMENTATION ==========
            if self.config.enable_documentation:
                self._context.current_step = 6

                yield await self._emit(EventType.STATUS, {
                    "message": "Generating documentation...",
                    "step": 6,
                    "total_steps": self._context.total_steps
                })

                async for event in self._execute_documentation():
                    yield event

            # ========== COMPLETE ==========
            self._project_sm.complete()
            self._context.completed_at = datetime.utcnow()

            yield await self._emit(EventType.PROJECT_COMPLETE, {
                "workflow_id": self._context.workflow_id,
                "files_created": len(self._context.files_created),
                "files_modified": len(self._context.files_modified),
                "duration_ms": self._context.to_dict()["duration_ms"]
            })

            logger.info(
                f"[UnifiedOrchestrator:{self.project_id}] "
                f"Workflow complete: {len(self._context.files_created)} files, "
                f"{self._context.to_dict()['duration_ms']:.0f}ms"
            )

        except asyncio.CancelledError:
            self._project_sm.cancel()
            yield await self._emit(EventType.PROJECT_CANCELLED, {
                "workflow_id": self._context.workflow_id
            })
            raise

        except Exception as e:
            logger.error(f"[UnifiedOrchestrator:{self.project_id}] Workflow failed: {e}")
            self._project_sm.fail(str(e))
            yield await self._emit(EventType.PROJECT_FAILED, {
                "workflow_id": self._context.workflow_id,
                "error": str(e)
            })
            raise

    async def _execute_planning(
        self,
        user_request: str,
        initial_context: Optional[Dict[str, Any]]
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """Execute planning phase"""
        from app.modules.agents.planner_agent import PlannerAgent

        try:
            yield await self._emit(EventType.AGENT_STARTED, {
                "agent": "planner",
                "step": 1
            })

            planner = PlannerAgent()

            # Call planner with timeout
            result = await asyncio.wait_for(
                planner.create_plan(user_request, initial_context),
                timeout=self.config.planning_timeout
            )

            if result.get("success"):
                self._context.plan = result.get("plan")
                self._context.tech_stack = result.get("tech_stack")
                self._context.project_type = result.get("project_type")

                yield await self._emit(EventType.PLAN_CREATED, {
                    "plan": self._context.plan,
                    "tech_stack": self._context.tech_stack,
                    "project_type": self._context.project_type,
                    "file_count": len(self._context.plan.get("files", []))
                })

            yield await self._emit(EventType.AGENT_COMPLETED, {
                "agent": "planner",
                "success": result.get("success", False)
            })

        except asyncio.TimeoutError:
            yield await self._emit(EventType.AGENT_FAILED, {
                "agent": "planner",
                "error": "Planning timeout"
            })
        except Exception as e:
            yield await self._emit(EventType.AGENT_FAILED, {
                "agent": "planner",
                "error": str(e)
            })

    async def _execute_writing(self) -> AsyncGenerator[OrchestratorEvent, None]:
        """Execute writing phase"""
        from app.modules.agents.writer_agent import WriterAgent
        from app.modules.automation.file_manager import FileManager

        try:
            yield await self._emit(EventType.AGENT_STARTED, {
                "agent": "writer",
                "step": 2
            })

            writer = WriterAgent()
            file_manager = FileManager()

            # Get files from plan
            files = self._context.plan.get("files", [])
            total_files = len(files)

            for i, file_info in enumerate(files):
                file_path = file_info.get("path")
                description = file_info.get("description", "")

                yield await self._emit(EventType.STATUS, {
                    "message": f"Generating {file_path}...",
                    "progress": int((i / total_files) * 100)
                })

                # Generate file content
                result = await writer.generate_file(
                    file_path=file_path,
                    description=description,
                    context={
                        "plan": self._context.plan,
                        "tech_stack": self._context.tech_stack,
                        "existing_files": self._context.files_created
                    }
                )

                if result.get("success"):
                    content = result.get("content", "")

                    # Save file
                    await file_manager.create_file(
                        self.project_id,
                        file_path,
                        content
                    )

                    self._context.files_created.append({
                        "path": file_path,
                        "size": len(content)
                    })

                    yield await self._emit(EventType.FILE_CREATED, {
                        "path": file_path,
                        "size": len(content),
                        "progress": int(((i + 1) / total_files) * 100)
                    })

                    if self.config.stream_file_content:
                        yield await self._emit(EventType.FILE_CONTENT, {
                            "path": file_path,
                            "content": content
                        })

            yield await self._emit(EventType.AGENT_COMPLETED, {
                "agent": "writer",
                "files_created": len(self._context.files_created)
            })

        except Exception as e:
            yield await self._emit(EventType.AGENT_FAILED, {
                "agent": "writer",
                "error": str(e)
            })

    async def _execute_docker_start(self) -> AsyncGenerator[OrchestratorEvent, None]:
        """Start Docker container"""
        try:
            from app.core.config import settings

            files_path = f"{settings.USER_PROJECTS_DIR}/{self.project_id}"

            result = await self._docker.start(files_path)

            if result.get("success"):
                container = result.get("container", {})
                yield await self._emit(EventType.DOCKER_RUNNING, {
                    "container_id": container.get("container_id"),
                    "port": container.get("external_port"),
                    "url": container.get("preview_url")
                })

                yield await self._emit(EventType.PREVIEW_READY, {
                    "url": container.get("preview_url")
                })
            else:
                yield await self._emit(EventType.DOCKER_FAILED, {
                    "error": result.get("error")
                })

        except Exception as e:
            yield await self._emit(EventType.DOCKER_FAILED, {
                "error": str(e)
            })

    async def _execute_build_and_fix(self) -> AsyncGenerator[OrchestratorEvent, None]:
        """Execute build and auto-fix loop"""
        from app.modules.automation.build_system import build_system

        try:
            yield await self._emit(EventType.BUILD_STARTED, {})

            # Run build
            build_result = await build_system.build(self.project_id)

            if build_result.get("success"):
                yield await self._emit(EventType.BUILD_COMPLETED, {
                    "build_time": build_result.get("build_time")
                })
            else:
                yield await self._emit(EventType.BUILD_FAILED, {
                    "error": build_result.get("error")
                })

                # Trigger auto-fix
                if self.config.auto_fix_enabled:
                    yield await self._emit(EventType.STATUS, {
                        "message": "Errors detected, attempting auto-fix..."
                    })

                    fix_result = await self._auto_fix.execute_fix_loop()

                    if fix_result.get("success"):
                        self._context.fix_attempts = fix_result.get("context", {}).get("attempt", 0)
                        self._context.files_modified.extend([
                            {"path": f, "operation": "fix"}
                            for f in fix_result.get("context", {}).get("files_modified", [])
                        ])

                        yield await self._emit(EventType.FIX_COMPLETED, fix_result)

                        # Rebuild after fix
                        rebuild_result = await build_system.build(self.project_id)
                        if rebuild_result.get("success"):
                            yield await self._emit(EventType.BUILD_COMPLETED, {
                                "build_time": rebuild_result.get("build_time"),
                                "after_fix": True
                            })

        except Exception as e:
            yield await self._emit(EventType.BUILD_FAILED, {
                "error": str(e)
            })

    async def _execute_verification(self) -> AsyncGenerator[OrchestratorEvent, None]:
        """Execute verification phase"""
        from app.modules.agents.verification_agent import VerificationAgent

        try:
            yield await self._emit(EventType.AGENT_STARTED, {
                "agent": "verifier",
                "step": 5
            })

            verifier = VerificationAgent()

            result = await verifier.verify_project(
                project_id=self.project_id,
                expected_files=[f["path"] for f in self._context.files_created]
            )

            yield await self._emit(EventType.AGENT_COMPLETED, {
                "agent": "verifier",
                "success": result.get("success"),
                "issues": result.get("issues", [])
            })

        except Exception as e:
            yield await self._emit(EventType.AGENT_FAILED, {
                "agent": "verifier",
                "error": str(e)
            })

    async def _execute_documentation(self) -> AsyncGenerator[OrchestratorEvent, None]:
        """Execute documentation generation"""
        from app.modules.agents.document_generator_agent import DocumentGeneratorAgent

        try:
            yield await self._emit(EventType.AGENT_STARTED, {
                "agent": "documenter",
                "step": 6
            })

            yield await self._emit(EventType.DOCUMENT_GENERATING, {
                "types": ["SRS", "UML", "Report"]
            })

            documenter = DocumentGeneratorAgent()

            result = await documenter.generate_documentation(
                project_id=self.project_id,
                plan=self._context.plan,
                files=self._context.files_created
            )

            if result.get("success"):
                yield await self._emit(EventType.DOCUMENT_GENERATED, {
                    "documents": result.get("documents", [])
                })

            yield await self._emit(EventType.AGENT_COMPLETED, {
                "agent": "documenter",
                "success": result.get("success")
            })

        except Exception as e:
            yield await self._emit(EventType.AGENT_FAILED, {
                "agent": "documenter",
                "error": str(e)
            })

    async def _emit(
        self,
        event_type: EventType,
        data: Dict[str, Any]
    ) -> OrchestratorEvent:
        """Emit event and return it"""
        event = OrchestratorEvent(
            type=event_type,
            project_id=self.project_id,
            data=data,
            source="UnifiedOrchestrator"
        )
        await self._event_bus.publish(event)
        return event

    async def trigger_fix(self) -> Dict[str, Any]:
        """Manually trigger auto-fix"""
        return await self._auto_fix.execute_fix_loop()

    async def restart_docker(self) -> Dict[str, Any]:
        """Restart Docker container"""
        return await self._docker.restart()

    async def stop(self):
        """Stop all orchestration"""
        await self._docker.stop()
        self._event_bus.remove_sse_queue(self.project_id)

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        state = self._state_manager.get_state(self.project_id)
        return {
            "project_id": self.project_id,
            "state": state.to_dict() if state else None,
            "context": self._context.to_dict() if self._context else None,
            "docker": self._docker.get_status(),
            "auto_fix": self._auto_fix.get_status()
        }


# ========== Factory Function ==========

_orchestrators: Dict[str, UnifiedOrchestrator] = {}


def get_unified_orchestrator(
    project_id: str,
    config: Optional[WorkflowConfig] = None
) -> UnifiedOrchestrator:
    """Get or create unified orchestrator for a project"""
    if project_id not in _orchestrators:
        _orchestrators[project_id] = UnifiedOrchestrator(project_id, config)
    return _orchestrators[project_id]


def remove_orchestrator(project_id: str):
    """Remove orchestrator for a project"""
    if project_id in _orchestrators:
        del _orchestrators[project_id]
