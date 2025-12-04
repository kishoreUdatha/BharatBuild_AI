"""
Orchestration Module - The Brain of BharatBuild AI

This module provides the complete orchestration system for Bolt.new-style
project generation with automatic error detection and fixing.

Components:
- StateMachine: Predictable state transitions for workflows
- EventBus: Pub/sub messaging between components
- AutoFixOrchestrator: Automatic error detection and fixing loop
- DockerOrchestrator: Container lifecycle management
- UnifiedOrchestrator: Central coordinator tying everything together

Usage:
    from app.modules.orchestrator import get_unified_orchestrator

    # Get orchestrator for a project
    orchestrator = get_unified_orchestrator(project_id)

    # Execute workflow with streaming
    async for event in orchestrator.execute_workflow(user_request):
        yield event.to_sse()  # Stream to frontend

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED ORCHESTRATOR                          │
├─────────────────────────────────────────────────────────────────┤
│  State Machine ─► Event Bus ─► Components                        │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐│
│  │ AUTO-FIX   │  │ DOCKER     │  │ PREVIEW    │  │ AGENTS     ││
│  │ Detect     │  │ Start/Stop │  │ Start      │  │ Planner    ││
│  │ Fix        │  │ Restart    │  │ Reload     │  │ Writer     ││
│  │ Verify     │  │ Logs       │  │            │  │ Fixer      ││
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘│
└─────────────────────────────────────────────────────────────────┘
"""

# State Machine
from app.modules.orchestrator.state_machine import (
    # States
    ProjectState,
    DockerState,
    PreviewState,
    FixLoopState,
    # State machines
    StateMachine,
    ProjectStateMachine,
    DockerStateMachine,
    FixLoopStateMachine,
    # Manager
    OrchestrationStateManager,
    get_state_manager,
    # Data classes
    OrchestratorState,
    StateTransition,
)

# Event Bus
from app.modules.orchestrator.event_bus import (
    # Event types
    EventType,
    EventPriority,
    # Data classes
    OrchestratorEvent,
    # Event Bus
    EventBus,
    get_event_bus,
    # Convenience functions
    emit,
    emit_sync,
    subscribe,
    # Factory functions
    create_status_event,
    create_file_event,
    create_error_event,
    create_fix_event,
    create_docker_event,
)

# Auto-Fix Orchestrator
from app.modules.orchestrator.auto_fix_orchestrator import (
    AutoFixOrchestrator,
    AutoFixConfig,
    FixContext,
    get_auto_fix_orchestrator,
    auto_fix_manager,
)

# Docker Orchestrator
from app.modules.orchestrator.docker_orchestrator import (
    DockerOrchestrator,
    DockerConfig,
    ContainerInfo,
    ProjectType,
    get_docker_orchestrator,
    docker_orchestrator_manager,
)

# Unified Orchestrator
from app.modules.orchestrator.unified_orchestrator import (
    UnifiedOrchestrator,
    WorkflowConfig,
    WorkflowContext,
    get_unified_orchestrator,
    remove_orchestrator,
)

# Legacy/existing orchestrator (keep for backward compatibility)
from app.modules.orchestrator.dynamic_orchestrator import (
    DynamicOrchestrator,
    AgentRegistry,
    WorkflowEngine,
    ExecutionContext,
    AgentType,
)

__all__ = [
    # State Machine
    "ProjectState",
    "DockerState",
    "PreviewState",
    "FixLoopState",
    "StateMachine",
    "ProjectStateMachine",
    "DockerStateMachine",
    "FixLoopStateMachine",
    "OrchestrationStateManager",
    "get_state_manager",
    "OrchestratorState",
    "StateTransition",

    # Event Bus
    "EventType",
    "EventPriority",
    "OrchestratorEvent",
    "EventBus",
    "get_event_bus",
    "emit",
    "emit_sync",
    "subscribe",
    "create_status_event",
    "create_file_event",
    "create_error_event",
    "create_fix_event",
    "create_docker_event",

    # Auto-Fix Orchestrator
    "AutoFixOrchestrator",
    "AutoFixConfig",
    "FixContext",
    "get_auto_fix_orchestrator",
    "auto_fix_manager",

    # Docker Orchestrator
    "DockerOrchestrator",
    "DockerConfig",
    "ContainerInfo",
    "ProjectType",
    "get_docker_orchestrator",
    "docker_orchestrator_manager",

    # Unified Orchestrator
    "UnifiedOrchestrator",
    "WorkflowConfig",
    "WorkflowContext",
    "get_unified_orchestrator",
    "remove_orchestrator",

    # Legacy
    "DynamicOrchestrator",
    "AgentRegistry",
    "WorkflowEngine",
    "ExecutionContext",
    "AgentType",
]
