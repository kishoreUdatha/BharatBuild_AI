"""
Execution Module - Container-based Code Execution

This module provides isolated execution environments for user projects,
similar to how Bolt.new, Replit, and CodeSandbox work.

Key Components:
- ContainerManager: Creates and manages per-project Docker containers
- CommandValidator: Security layer to prevent command injection
- HealthMonitor: Auto-restart and crash recovery
- ProjectExecutor: Bridges AI generation to container execution
"""

from .container_manager import (
    ContainerManager,
    ContainerConfig,
    ContainerStatus,
    ProjectContainer,
    get_container_manager,
    cleanup_loop,
)

from .command_validator import (
    CommandValidator,
    CommandRisk,
    ValidationResult,
    get_command_validator,
)

from .health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheck,
    RestartPolicy,
    ContainerHealth,
    get_health_monitor,
    start_health_monitoring,
)

from .project_executor import (
    ProjectExecutor,
    ExecutionStep,
    execute_ai_output,
)

__all__ = [
    # Container Management
    "ContainerManager",
    "ContainerConfig",
    "ContainerStatus",
    "ProjectContainer",
    "get_container_manager",
    "cleanup_loop",

    # Command Validation
    "CommandValidator",
    "CommandRisk",
    "ValidationResult",
    "get_command_validator",

    # Health Monitoring
    "HealthMonitor",
    "HealthStatus",
    "HealthCheck",
    "RestartPolicy",
    "ContainerHealth",
    "get_health_monitor",
    "start_health_monitoring",

    # Project Execution
    "ProjectExecutor",
    "ExecutionStep",
    "execute_ai_output",
]
