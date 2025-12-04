"""
State Machine for Orchestration - Bolt.new Style

Provides predictable, debuggable state transitions for:
- Project generation workflow
- Auto-fix loop
- Docker container lifecycle
- Preview server lifecycle

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                      STATE MACHINE                               │
├─────────────────────────────────────────────────────────────────┤
│  IDLE → PLANNING → WRITING → BUILDING → FIXING → COMPLETE       │
│                          ↑              ↓                        │
│                          └──── ERROR ───┘                        │
└─────────────────────────────────────────────────────────────────┘

States are immutable - transitions create new state objects.
All transitions are logged for debugging.
"""

from typing import Dict, Any, Optional, Callable, List, Set
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import threading
from collections import deque

from app.core.logging_config import logger


class ProjectState(str, Enum):
    """Project generation workflow states"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    PLANNING = "planning"
    WRITING = "writing"
    VERIFYING = "verifying"
    BUILDING = "building"
    RUNNING = "running"
    FIXING = "fixing"
    DOCUMENTING = "documenting"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DockerState(str, Enum):
    """Docker container lifecycle states"""
    NONE = "none"
    CREATING = "creating"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    FAILED = "failed"


class PreviewState(str, Enum):
    """Preview server lifecycle states"""
    NONE = "none"
    STARTING = "starting"
    READY = "ready"
    RELOADING = "reloading"
    STOPPED = "stopped"
    FAILED = "failed"


class FixLoopState(str, Enum):
    """Auto-fix loop states"""
    IDLE = "idle"
    DETECTING = "detecting"
    ANALYZING = "analyzing"
    FIXING = "fixing"
    APPLYING = "applying"
    RESTARTING = "restarting"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"
    MAX_RETRIES = "max_retries"


# Valid state transitions
PROJECT_TRANSITIONS: Dict[ProjectState, Set[ProjectState]] = {
    ProjectState.IDLE: {ProjectState.INITIALIZING, ProjectState.CANCELLED},
    ProjectState.INITIALIZING: {ProjectState.PLANNING, ProjectState.FAILED, ProjectState.CANCELLED},
    ProjectState.PLANNING: {ProjectState.WRITING, ProjectState.FAILED, ProjectState.CANCELLED},
    ProjectState.WRITING: {ProjectState.VERIFYING, ProjectState.BUILDING, ProjectState.FAILED, ProjectState.CANCELLED},
    ProjectState.VERIFYING: {ProjectState.BUILDING, ProjectState.WRITING, ProjectState.FAILED},
    ProjectState.BUILDING: {ProjectState.RUNNING, ProjectState.FIXING, ProjectState.FAILED, ProjectState.COMPLETE},
    ProjectState.RUNNING: {ProjectState.FIXING, ProjectState.DOCUMENTING, ProjectState.COMPLETE, ProjectState.FAILED},
    ProjectState.FIXING: {ProjectState.BUILDING, ProjectState.RUNNING, ProjectState.WRITING, ProjectState.FAILED},
    ProjectState.DOCUMENTING: {ProjectState.COMPLETE, ProjectState.FAILED},
    ProjectState.COMPLETE: {ProjectState.IDLE},  # Can restart
    ProjectState.FAILED: {ProjectState.IDLE, ProjectState.FIXING},  # Can retry
    ProjectState.CANCELLED: {ProjectState.IDLE},
}

DOCKER_TRANSITIONS: Dict[DockerState, Set[DockerState]] = {
    DockerState.NONE: {DockerState.CREATING},
    DockerState.CREATING: {DockerState.STARTING, DockerState.FAILED},
    DockerState.STARTING: {DockerState.RUNNING, DockerState.FAILED},
    DockerState.RUNNING: {DockerState.STOPPING, DockerState.RESTARTING, DockerState.FAILED},
    DockerState.STOPPING: {DockerState.STOPPED, DockerState.FAILED},
    DockerState.STOPPED: {DockerState.STARTING, DockerState.NONE},
    DockerState.RESTARTING: {DockerState.RUNNING, DockerState.FAILED},
    DockerState.FAILED: {DockerState.NONE, DockerState.STARTING},
}

FIX_LOOP_TRANSITIONS: Dict[FixLoopState, Set[FixLoopState]] = {
    FixLoopState.IDLE: {FixLoopState.DETECTING},
    FixLoopState.DETECTING: {FixLoopState.ANALYZING, FixLoopState.IDLE},
    FixLoopState.ANALYZING: {FixLoopState.FIXING, FixLoopState.IDLE},
    FixLoopState.FIXING: {FixLoopState.APPLYING, FixLoopState.FAILED},
    FixLoopState.APPLYING: {FixLoopState.RESTARTING, FixLoopState.FAILED},
    FixLoopState.RESTARTING: {FixLoopState.VERIFYING, FixLoopState.FAILED},
    FixLoopState.VERIFYING: {FixLoopState.COMPLETE, FixLoopState.DETECTING, FixLoopState.MAX_RETRIES},
    FixLoopState.COMPLETE: {FixLoopState.IDLE},
    FixLoopState.FAILED: {FixLoopState.IDLE, FixLoopState.DETECTING},
    FixLoopState.MAX_RETRIES: {FixLoopState.IDLE},
}


@dataclass
class StateTransition:
    """Record of a state transition"""
    from_state: str
    to_state: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_state,
            "to": self.to_state,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "metadata": self.metadata
        }


@dataclass
class OrchestratorState:
    """Complete orchestrator state snapshot"""
    project_id: str
    project_state: ProjectState = ProjectState.IDLE
    docker_state: DockerState = DockerState.NONE
    preview_state: PreviewState = PreviewState.NONE
    fix_loop_state: FixLoopState = FixLoopState.IDLE

    # Metadata
    current_agent: Optional[str] = None
    current_step: int = 0
    total_steps: int = 0
    progress: float = 0.0

    # Error tracking
    error_count: int = 0
    fix_attempts: int = 0
    max_fix_attempts: int = 3

    # Files
    files_created: int = 0
    files_modified: int = 0

    # Timestamps
    started_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # History
    transitions: List[StateTransition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_state": self.project_state.value,
            "docker_state": self.docker_state.value,
            "preview_state": self.preview_state.value,
            "fix_loop_state": self.fix_loop_state.value,
            "current_agent": self.current_agent,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress": self.progress,
            "error_count": self.error_count,
            "fix_attempts": self.fix_attempts,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat(),
            "recent_transitions": [t.to_dict() for t in self.transitions[-10:]]
        }


class StateMachine:
    """
    Generic state machine with validation and callbacks.

    Features:
    - Validates transitions against allowed transitions
    - Maintains transition history
    - Supports async callbacks on state change
    - Thread-safe
    """

    def __init__(
        self,
        name: str,
        initial_state: Enum,
        transitions: Dict[Enum, Set[Enum]],
        max_history: int = 100
    ):
        self.name = name
        self._state = initial_state
        self._transitions = transitions
        self._lock = threading.Lock()
        self._history: deque = deque(maxlen=max_history)
        self._callbacks: List[Callable] = []
        self._async_callbacks: List[Callable] = []

    @property
    def state(self) -> Enum:
        """Get current state"""
        with self._lock:
            return self._state

    def can_transition(self, to_state: Enum) -> bool:
        """Check if transition is valid"""
        with self._lock:
            allowed = self._transitions.get(self._state, set())
            return to_state in allowed

    def transition(
        self,
        to_state: Enum,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """
        Transition to new state.

        Args:
            to_state: Target state
            reason: Why the transition is happening
            metadata: Additional data about the transition
            force: Skip validation (use with caution)

        Returns:
            True if transition succeeded
        """
        with self._lock:
            if not force and not self.can_transition(to_state):
                allowed = self._transitions.get(self._state, set())
                logger.warning(
                    f"[{self.name}] Invalid transition: {self._state} → {to_state}. "
                    f"Allowed: {[s.value for s in allowed]}"
                )
                return False

            # Record transition
            transition = StateTransition(
                from_state=self._state.value,
                to_state=to_state.value,
                reason=reason,
                metadata=metadata or {}
            )
            self._history.append(transition)

            old_state = self._state
            self._state = to_state

            logger.info(
                f"[{self.name}] State transition: {old_state.value} → {to_state.value}"
                + (f" ({reason})" if reason else "")
            )

        # Call sync callbacks outside lock
        for callback in self._callbacks:
            try:
                callback(old_state, to_state, transition)
            except Exception as e:
                logger.error(f"[{self.name}] Callback error: {e}")

        return True

    async def transition_async(
        self,
        to_state: Enum,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """Async version of transition with async callbacks"""
        success = self.transition(to_state, reason, metadata, force)

        if success:
            # Call async callbacks
            for callback in self._async_callbacks:
                try:
                    await callback(self._state, to_state, self._history[-1])
                except Exception as e:
                    logger.error(f"[{self.name}] Async callback error: {e}")

        return success

    def on_transition(self, callback: Callable):
        """Register sync callback for state transitions"""
        self._callbacks.append(callback)

    def on_transition_async(self, callback: Callable):
        """Register async callback for state transitions"""
        self._async_callbacks.append(callback)

    def get_history(self, limit: int = 10) -> List[StateTransition]:
        """Get recent transition history"""
        with self._lock:
            return list(self._history)[-limit:]

    def reset(self, initial_state: Optional[Enum] = None):
        """Reset state machine"""
        with self._lock:
            self._state = initial_state or list(self._transitions.keys())[0]
            self._history.clear()


class ProjectStateMachine(StateMachine):
    """Specialized state machine for project workflow"""

    def __init__(self, project_id: str):
        super().__init__(
            name=f"Project:{project_id}",
            initial_state=ProjectState.IDLE,
            transitions=PROJECT_TRANSITIONS
        )
        self.project_id = project_id

    def start(self) -> bool:
        """Start project generation"""
        return self.transition(
            ProjectState.INITIALIZING,
            reason="Project generation started"
        )

    def plan(self) -> bool:
        """Move to planning phase"""
        return self.transition(
            ProjectState.PLANNING,
            reason="Starting planning phase"
        )

    def write(self) -> bool:
        """Move to writing phase"""
        return self.transition(
            ProjectState.WRITING,
            reason="Starting code generation"
        )

    def build(self) -> bool:
        """Move to build phase"""
        return self.transition(
            ProjectState.BUILDING,
            reason="Starting build process"
        )

    def fix(self, error: Optional[str] = None) -> bool:
        """Move to fix phase"""
        return self.transition(
            ProjectState.FIXING,
            reason=f"Fixing error: {error}" if error else "Entering fix mode"
        )

    def complete(self) -> bool:
        """Mark as complete"""
        return self.transition(
            ProjectState.COMPLETE,
            reason="Project generation complete"
        )

    def fail(self, error: str) -> bool:
        """Mark as failed"""
        return self.transition(
            ProjectState.FAILED,
            reason=f"Failed: {error}"
        )

    def cancel(self) -> bool:
        """Cancel project"""
        return self.transition(
            ProjectState.CANCELLED,
            reason="Cancelled by user",
            force=True  # Always allow cancel
        )


class FixLoopStateMachine(StateMachine):
    """Specialized state machine for auto-fix loop"""

    def __init__(self, project_id: str, max_attempts: int = 3):
        super().__init__(
            name=f"FixLoop:{project_id}",
            initial_state=FixLoopState.IDLE,
            transitions=FIX_LOOP_TRANSITIONS
        )
        self.project_id = project_id
        self.max_attempts = max_attempts
        self.attempts = 0

    def detect_error(self) -> bool:
        """Start error detection"""
        return self.transition(
            FixLoopState.DETECTING,
            reason="Checking for errors"
        )

    def analyze(self) -> bool:
        """Analyze detected errors"""
        return self.transition(
            FixLoopState.ANALYZING,
            reason="Analyzing errors"
        )

    def fix(self) -> bool:
        """Start fixing"""
        self.attempts += 1
        return self.transition(
            FixLoopState.FIXING,
            reason=f"Fix attempt {self.attempts}/{self.max_attempts}"
        )

    def apply_patches(self) -> bool:
        """Apply generated patches"""
        return self.transition(
            FixLoopState.APPLYING,
            reason="Applying patches"
        )

    def restart(self) -> bool:
        """Restart after fix"""
        return self.transition(
            FixLoopState.RESTARTING,
            reason="Restarting to apply fixes"
        )

    def verify(self) -> bool:
        """Verify fix worked"""
        return self.transition(
            FixLoopState.VERIFYING,
            reason="Verifying fix"
        )

    def complete(self) -> bool:
        """Fix complete"""
        return self.transition(
            FixLoopState.COMPLETE,
            reason="Fix verified successfully"
        )

    def retry_or_fail(self) -> bool:
        """Retry or fail based on attempts"""
        if self.attempts >= self.max_attempts:
            return self.transition(
                FixLoopState.MAX_RETRIES,
                reason=f"Max attempts ({self.max_attempts}) reached"
            )
        return self.transition(
            FixLoopState.DETECTING,
            reason="Retrying fix"
        )

    def reset_attempts(self):
        """Reset attempt counter"""
        self.attempts = 0


class DockerStateMachine(StateMachine):
    """Specialized state machine for Docker lifecycle"""

    def __init__(self, project_id: str):
        super().__init__(
            name=f"Docker:{project_id}",
            initial_state=DockerState.NONE,
            transitions=DOCKER_TRANSITIONS
        )
        self.project_id = project_id

    def create(self) -> bool:
        """Start container creation"""
        return self.transition(DockerState.CREATING, reason="Creating container")

    def start(self) -> bool:
        """Start container"""
        return self.transition(DockerState.STARTING, reason="Starting container")

    def running(self) -> bool:
        """Mark as running"""
        return self.transition(DockerState.RUNNING, reason="Container running")

    def stop(self) -> bool:
        """Stop container"""
        return self.transition(DockerState.STOPPING, reason="Stopping container")

    def stopped(self) -> bool:
        """Mark as stopped"""
        return self.transition(DockerState.STOPPED, reason="Container stopped")

    def restart(self) -> bool:
        """Restart container"""
        return self.transition(DockerState.RESTARTING, reason="Restarting container")

    def fail(self, error: str) -> bool:
        """Mark as failed"""
        return self.transition(DockerState.FAILED, reason=f"Failed: {error}")


class OrchestrationStateManager:
    """
    Central manager for all orchestration state machines.

    Creates and manages state machines for each project.
    Provides unified view of orchestration state.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._states: Dict[str, OrchestratorState] = {}
                    cls._instance._project_machines: Dict[str, ProjectStateMachine] = {}
                    cls._instance._docker_machines: Dict[str, DockerStateMachine] = {}
                    cls._instance._fix_machines: Dict[str, FixLoopStateMachine] = {}
                    cls._instance._state_lock = threading.Lock()
        return cls._instance

    def get_or_create(self, project_id: str) -> OrchestratorState:
        """Get or create orchestrator state for a project"""
        with self._state_lock:
            if project_id not in self._states:
                self._states[project_id] = OrchestratorState(project_id=project_id)
                self._project_machines[project_id] = ProjectStateMachine(project_id)
                self._docker_machines[project_id] = DockerStateMachine(project_id)
                self._fix_machines[project_id] = FixLoopStateMachine(project_id)
                logger.info(f"[StateManager] Created state for project {project_id}")
            return self._states[project_id]

    def get_project_machine(self, project_id: str) -> ProjectStateMachine:
        """Get project state machine"""
        self.get_or_create(project_id)
        return self._project_machines[project_id]

    def get_docker_machine(self, project_id: str) -> DockerStateMachine:
        """Get Docker state machine"""
        self.get_or_create(project_id)
        return self._docker_machines[project_id]

    def get_fix_machine(self, project_id: str) -> FixLoopStateMachine:
        """Get fix loop state machine"""
        self.get_or_create(project_id)
        return self._fix_machines[project_id]

    def update_state(self, project_id: str, **kwargs) -> OrchestratorState:
        """Update orchestrator state"""
        state = self.get_or_create(project_id)
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            state.updated_at = datetime.utcnow()
        return state

    def sync_state(self, project_id: str) -> OrchestratorState:
        """Sync state from individual state machines"""
        state = self.get_or_create(project_id)
        with self._state_lock:
            state.project_state = self._project_machines[project_id].state
            state.docker_state = self._docker_machines[project_id].state
            state.fix_loop_state = self._fix_machines[project_id].state
            state.updated_at = datetime.utcnow()
        return state

    def get_state(self, project_id: str) -> Optional[OrchestratorState]:
        """Get orchestrator state"""
        return self._states.get(project_id)

    def remove(self, project_id: str):
        """Remove state for a project"""
        with self._state_lock:
            self._states.pop(project_id, None)
            self._project_machines.pop(project_id, None)
            self._docker_machines.pop(project_id, None)
            self._fix_machines.pop(project_id, None)
            logger.info(f"[StateManager] Removed state for project {project_id}")

    def list_projects(self) -> List[str]:
        """List all tracked projects"""
        with self._state_lock:
            return list(self._states.keys())


# Global singleton
state_manager = OrchestrationStateManager()


def get_state_manager() -> OrchestrationStateManager:
    """Get the global state manager"""
    return state_manager
