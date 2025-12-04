"""
Orchestration Event Bus - Central Communication Hub

Provides pub/sub messaging between orchestration components:
- State machines emit events
- Auto-fixer listens for error events
- Docker manager listens for lifecycle events
- Frontend receives SSE events

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                        EVENT BUS                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Publishers:                    Subscribers:                     │
│  ├─ State Machine      ──────►  ├─ Auto Fixer                   │
│  ├─ File Manager       ──────►  ├─ Docker Manager               │
│  ├─ Build System       ──────►  ├─ Preview Server               │
│  ├─ Log Bus            ──────►  ├─ WebSocket Handler            │
│  └─ Fixer Agent        ──────►  └─ SSE Streamer                 │
│                                                                  │
│  Event Types:                                                    │
│  • state_changed       • file_created      • error_detected     │
│  • build_started       • build_completed   • fix_applied        │
│  • docker_started      • docker_stopped    • preview_ready      │
│  • project_complete    • project_failed    • user_notification  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
"""

from typing import Dict, Any, List, Optional, Callable, Set, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
import asyncio
import threading
from collections import defaultdict
import json

from app.core.logging_config import logger


class EventType(str, Enum):
    """All event types in the orchestration system"""

    # State events
    STATE_CHANGED = "state_changed"
    PROJECT_STARTED = "project_started"
    PROJECT_COMPLETE = "project_complete"
    PROJECT_FAILED = "project_failed"
    PROJECT_CANCELLED = "project_cancelled"

    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    THINKING_STEP = "thinking_step"

    # Planning events
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"

    # File events
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    FILE_CONTENT = "file_content"

    # Build events
    BUILD_STARTED = "build_started"
    BUILD_OUTPUT = "build_output"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"

    # Error events
    ERROR_DETECTED = "error_detected"
    ERROR_BROWSER = "error_browser"
    ERROR_BUILD = "error_build"
    ERROR_BACKEND = "error_backend"
    ERROR_DOCKER = "error_docker"

    # Fix events
    FIX_STARTED = "fix_started"
    FIX_PATCH_GENERATED = "fix_patch_generated"
    FIX_PATCH_APPLIED = "fix_patch_applied"
    FIX_COMPLETED = "fix_completed"
    FIX_FAILED = "fix_failed"
    FIX_MAX_RETRIES = "fix_max_retries"

    # Docker events
    DOCKER_CREATING = "docker_creating"
    DOCKER_STARTED = "docker_started"
    DOCKER_RUNNING = "docker_running"
    DOCKER_STOPPING = "docker_stopping"
    DOCKER_STOPPED = "docker_stopped"
    DOCKER_RESTARTING = "docker_restarting"
    DOCKER_FAILED = "docker_failed"
    DOCKER_LOGS = "docker_logs"

    # Preview events
    PREVIEW_STARTING = "preview_starting"
    PREVIEW_READY = "preview_ready"
    PREVIEW_RELOADING = "preview_reloading"
    PREVIEW_STOPPED = "preview_stopped"
    PREVIEW_FAILED = "preview_failed"

    # Command events
    COMMAND_EXECUTE = "command_execute"
    COMMAND_OUTPUT = "command_output"
    COMMAND_COMPLETED = "command_completed"

    # Document events
    DOCUMENT_GENERATING = "document_generating"
    DOCUMENT_GENERATED = "document_generated"

    # User notifications
    USER_NOTIFICATION = "user_notification"
    STATUS = "status"
    PROGRESS = "progress"
    WARNING = "warning"


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class OrchestratorEvent:
    """An event in the orchestration system"""
    type: EventType
    project_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None  # Component that emitted the event
    correlation_id: Optional[str] = None  # For tracking related events

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "project_id": self.project_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "source": self.source,
            "correlation_id": self.correlation_id
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_sse(self) -> str:
        """Format for Server-Sent Events"""
        return f"data: {self.to_json()}\n\n"


# Type alias for event handlers
EventHandler = Callable[[OrchestratorEvent], None]
AsyncEventHandler = Callable[[OrchestratorEvent], Any]  # Coroutine


class EventBus:
    """
    Central event bus for orchestration system.

    Features:
    - Pub/sub messaging
    - Wildcard subscriptions (subscribe to all events)
    - Project-scoped subscriptions
    - Async and sync handlers
    - Event history
    - Event filtering
    """

    def __init__(self, max_history: int = 1000):
        self._lock = threading.Lock()
        self._handlers: Dict[EventType, List[AsyncEventHandler]] = defaultdict(list)
        self._wildcard_handlers: List[AsyncEventHandler] = []
        self._project_handlers: Dict[str, Dict[EventType, List[AsyncEventHandler]]] = defaultdict(lambda: defaultdict(list))
        self._history: List[OrchestratorEvent] = []
        self._max_history = max_history
        self._event_count = 0

        # SSE queues for streaming to clients
        self._sse_queues: Dict[str, asyncio.Queue] = {}  # project_id -> Queue

    def subscribe(
        self,
        event_type: Union[EventType, str],
        handler: AsyncEventHandler,
        project_id: Optional[str] = None
    ):
        """
        Subscribe to events.

        Args:
            event_type: Event type to subscribe to, or "*" for all
            handler: Async function to call when event occurs
            project_id: Optional project filter
        """
        with self._lock:
            if event_type == "*":
                self._wildcard_handlers.append(handler)
                logger.debug("[EventBus] Registered wildcard handler")
            elif project_id:
                if isinstance(event_type, str):
                    event_type = EventType(event_type)
                self._project_handlers[project_id][event_type].append(handler)
                logger.debug(f"[EventBus] Registered handler for {event_type.value} on project {project_id}")
            else:
                if isinstance(event_type, str):
                    event_type = EventType(event_type)
                self._handlers[event_type].append(handler)
                logger.debug(f"[EventBus] Registered handler for {event_type.value}")

    def unsubscribe(
        self,
        event_type: Union[EventType, str],
        handler: AsyncEventHandler,
        project_id: Optional[str] = None
    ):
        """Unsubscribe from events"""
        with self._lock:
            if event_type == "*":
                if handler in self._wildcard_handlers:
                    self._wildcard_handlers.remove(handler)
            elif project_id:
                if isinstance(event_type, str):
                    event_type = EventType(event_type)
                handlers = self._project_handlers[project_id][event_type]
                if handler in handlers:
                    handlers.remove(handler)
            else:
                if isinstance(event_type, str):
                    event_type = EventType(event_type)
                if handler in self._handlers[event_type]:
                    self._handlers[event_type].remove(handler)

    async def publish(self, event: OrchestratorEvent):
        """
        Publish an event to all subscribers.

        Handlers are called in order:
        1. Project-specific handlers
        2. Event-type handlers
        3. Wildcard handlers
        """
        self._event_count += 1

        # Store in history
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        logger.debug(f"[EventBus] Publishing {event.type.value} for {event.project_id}")

        # Collect all handlers
        handlers = []

        with self._lock:
            # Project-specific handlers first
            if event.project_id in self._project_handlers:
                handlers.extend(self._project_handlers[event.project_id][event.type])

            # Event-type handlers
            handlers.extend(self._handlers[event.type])

            # Wildcard handlers
            handlers.extend(self._wildcard_handlers)

        # Call all handlers
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"[EventBus] Handler error for {event.type.value}: {e}")

        # Push to SSE queue if exists
        if event.project_id in self._sse_queues:
            try:
                self._sse_queues[event.project_id].put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"[EventBus] SSE queue full for {event.project_id}")

    def publish_sync(self, event: OrchestratorEvent):
        """
        Synchronous publish - schedules async publish.
        Use when calling from non-async context.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(event))
            else:
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # No event loop - create one
            asyncio.run(self.publish(event))

    def emit(
        self,
        event_type: EventType,
        project_id: str,
        data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None
    ):
        """
        Convenience method to emit an event synchronously.
        """
        event = OrchestratorEvent(
            type=event_type,
            project_id=project_id,
            data=data or {},
            source=source,
            priority=priority,
            correlation_id=correlation_id
        )
        self.publish_sync(event)

    async def emit_async(
        self,
        event_type: EventType,
        project_id: str,
        data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None
    ):
        """
        Convenience method to emit an event asynchronously.
        """
        event = OrchestratorEvent(
            type=event_type,
            project_id=project_id,
            data=data or {},
            source=source,
            priority=priority,
            correlation_id=correlation_id
        )
        await self.publish(event)

    # ========== SSE Streaming ==========

    def create_sse_queue(self, project_id: str, max_size: int = 100) -> asyncio.Queue:
        """Create SSE queue for a project"""
        queue = asyncio.Queue(maxsize=max_size)
        self._sse_queues[project_id] = queue
        logger.info(f"[EventBus] Created SSE queue for {project_id}")
        return queue

    def remove_sse_queue(self, project_id: str):
        """Remove SSE queue for a project"""
        if project_id in self._sse_queues:
            del self._sse_queues[project_id]
            logger.info(f"[EventBus] Removed SSE queue for {project_id}")

    async def sse_stream(self, project_id: str):
        """
        Async generator for SSE streaming.
        Use with FastAPI StreamingResponse.
        """
        queue = self._sse_queues.get(project_id)
        if not queue:
            queue = self.create_sse_queue(project_id)

        try:
            while True:
                event = await queue.get()
                yield event.to_sse()
        except asyncio.CancelledError:
            self.remove_sse_queue(project_id)
            raise

    # ========== History & Debugging ==========

    def get_history(
        self,
        project_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[OrchestratorEvent]:
        """Get event history with optional filters"""
        with self._lock:
            events = self._history

            if project_id:
                events = [e for e in events if e.project_id == project_id]

            if event_type:
                events = [e for e in events if e.type == event_type]

            return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self._lock:
            event_counts = defaultdict(int)
            for event in self._history:
                event_counts[event.type.value] += 1

            return {
                "total_events": self._event_count,
                "history_size": len(self._history),
                "handler_count": sum(len(h) for h in self._handlers.values()),
                "wildcard_handlers": len(self._wildcard_handlers),
                "active_sse_streams": len(self._sse_queues),
                "event_counts": dict(event_counts)
            }

    def clear_history(self):
        """Clear event history"""
        with self._lock:
            self._history.clear()


# ========== Event Factory Functions ==========

def create_status_event(
    project_id: str,
    message: str,
    step: Optional[int] = None,
    total_steps: Optional[int] = None,
    source: Optional[str] = None
) -> OrchestratorEvent:
    """Create a status event"""
    data = {"message": message}
    if step is not None:
        data["step"] = step
    if total_steps is not None:
        data["total_steps"] = total_steps
    return OrchestratorEvent(
        type=EventType.STATUS,
        project_id=project_id,
        data=data,
        source=source
    )


def create_file_event(
    project_id: str,
    path: str,
    operation: str,  # "create", "modify", "delete"
    content: Optional[str] = None,
    size: Optional[int] = None,
    source: Optional[str] = None
) -> OrchestratorEvent:
    """Create a file operation event"""
    event_types = {
        "create": EventType.FILE_CREATED,
        "modify": EventType.FILE_MODIFIED,
        "delete": EventType.FILE_DELETED
    }
    data = {
        "path": path,
        "operation": operation
    }
    if content:
        data["content"] = content
    if size is not None:
        data["size"] = size

    return OrchestratorEvent(
        type=event_types.get(operation, EventType.FILE_MODIFIED),
        project_id=project_id,
        data=data,
        source=source
    )


def create_error_event(
    project_id: str,
    error_type: str,  # "browser", "build", "backend", "docker"
    message: str,
    file: Optional[str] = None,
    line: Optional[int] = None,
    stack: Optional[str] = None,
    source: Optional[str] = None
) -> OrchestratorEvent:
    """Create an error event"""
    event_types = {
        "browser": EventType.ERROR_BROWSER,
        "build": EventType.ERROR_BUILD,
        "backend": EventType.ERROR_BACKEND,
        "docker": EventType.ERROR_DOCKER
    }
    data = {
        "error_type": error_type,
        "message": message
    }
    if file:
        data["file"] = file
    if line:
        data["line"] = line
    if stack:
        data["stack"] = stack

    return OrchestratorEvent(
        type=event_types.get(error_type, EventType.ERROR_DETECTED),
        project_id=project_id,
        data=data,
        priority=EventPriority.HIGH,
        source=source
    )


def create_fix_event(
    project_id: str,
    event_type: EventType,
    patches: Optional[List[Dict]] = None,
    files_modified: Optional[List[str]] = None,
    attempt: Optional[int] = None,
    error: Optional[str] = None,
    source: Optional[str] = None
) -> OrchestratorEvent:
    """Create a fix-related event"""
    data = {}
    if patches:
        data["patches"] = patches
    if files_modified:
        data["files_modified"] = files_modified
    if attempt:
        data["attempt"] = attempt
    if error:
        data["error"] = error

    return OrchestratorEvent(
        type=event_type,
        project_id=project_id,
        data=data,
        source=source
    )


def create_docker_event(
    project_id: str,
    event_type: EventType,
    container_id: Optional[str] = None,
    port: Optional[int] = None,
    url: Optional[str] = None,
    logs: Optional[str] = None,
    error: Optional[str] = None,
    source: Optional[str] = None
) -> OrchestratorEvent:
    """Create a Docker-related event"""
    data = {}
    if container_id:
        data["container_id"] = container_id
    if port:
        data["port"] = port
    if url:
        data["url"] = url
    if logs:
        data["logs"] = logs
    if error:
        data["error"] = error

    return OrchestratorEvent(
        type=event_type,
        project_id=project_id,
        data=data,
        source=source
    )


# ========== Global Instance ==========

_event_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        with _bus_lock:
            if _event_bus is None:
                _event_bus = EventBus()
                logger.info("[EventBus] Global event bus initialized")
    return _event_bus


# ========== Convenience Functions ==========

async def emit(
    event_type: EventType,
    project_id: str,
    data: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None
):
    """Quick emit function"""
    await get_event_bus().emit_async(event_type, project_id, data, source)


def emit_sync(
    event_type: EventType,
    project_id: str,
    data: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None
):
    """Quick sync emit function"""
    get_event_bus().emit(event_type, project_id, data, source)


def subscribe(
    event_type: Union[EventType, str],
    handler: AsyncEventHandler,
    project_id: Optional[str] = None
):
    """Quick subscribe function"""
    get_event_bus().subscribe(event_type, handler, project_id)
