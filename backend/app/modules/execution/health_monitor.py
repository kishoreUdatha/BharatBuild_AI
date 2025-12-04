"""
Container Health Monitor - Auto-restart and Recovery

This module monitors container health and automatically:
1. Detects crashed/hung containers
2. Restarts failed containers
3. Cleans up zombie containers
4. Alerts on repeated failures
"""

import asyncio
import logging
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from app.core.config import settings

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Container health status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    DEAD = "dead"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result"""
    status: HealthStatus
    checked_at: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    consecutive_failures: int = 0


@dataclass
class RestartPolicy:
    """Container restart policy (loaded from settings)"""
    max_restarts: int = field(default_factory=lambda: settings.HEALTH_MAX_FAILURES)
    restart_delay_seconds: int = field(default_factory=lambda: settings.HEALTH_RESTART_DELAY)
    backoff_multiplier: float = 2.0    # Exponential backoff
    max_delay_seconds: int = 60        # Max delay between restarts
    reset_after_seconds: int = field(default_factory=lambda: settings.HEALTH_RESET_AFTER)


@dataclass
class ContainerHealth:
    """Health state for a container"""
    project_id: str
    container_id: str
    last_check: Optional[HealthCheck] = None
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    last_healthy: Optional[datetime] = None
    is_monitored: bool = True


class HealthMonitor:
    """
    Monitors container health and manages restarts.

    Features:
    - Periodic health checks (every 30s)
    - Automatic restart on failure
    - Exponential backoff for repeated failures
    - Alerts for persistent issues
    """

    def __init__(self,
                 container_manager,  # ContainerManager instance
                 check_interval: int = None,
                 restart_policy: Optional[RestartPolicy] = None):
        """
        Initialize health monitor.

        Args:
            container_manager: ContainerManager instance
            check_interval: Seconds between health checks (from settings if not provided)
            restart_policy: Restart configuration
        """
        self.container_manager = container_manager
        self.check_interval = check_interval or settings.HEALTH_CHECK_INTERVAL
        self.restart_policy = restart_policy or RestartPolicy()

        # Track health state per container
        self.health_states: Dict[str, ContainerHealth] = {}

        # Callbacks for events
        self.on_unhealthy: Optional[Callable[[str, HealthCheck], Any]] = None
        self.on_restart: Optional[Callable[[str, int], Any]] = None
        self.on_death: Optional[Callable[[str, str], Any]] = None

        # Running state
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the health monitoring loop"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")

    async def stop(self):
        """Stop the health monitoring loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_all_containers()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self.check_interval)

    async def _check_all_containers(self):
        """Check health of all monitored containers"""
        for project_id in list(self.container_manager.containers.keys()):
            if project_id not in self.health_states:
                self._register_container(project_id)

            health_state = self.health_states.get(project_id)
            if health_state and health_state.is_monitored:
                await self._check_container(project_id)

    def _register_container(self, project_id: str):
        """Register a container for health monitoring"""
        container = self.container_manager.containers.get(project_id)
        if container:
            self.health_states[project_id] = ContainerHealth(
                project_id=project_id,
                container_id=container.container_id,
                last_healthy=datetime.utcnow()
            )

    async def _check_container(self, project_id: str) -> HealthCheck:
        """
        Check health of a single container.

        Health check:
        1. Container exists and is running
        2. Can execute a simple command (echo test)
        3. Response time is reasonable
        """
        health_state = self.health_states.get(project_id)
        if not health_state:
            return HealthCheck(
                status=HealthStatus.UNKNOWN,
                checked_at=datetime.utcnow(),
                response_time_ms=0,
                error_message="Container not registered"
            )

        start_time = datetime.utcnow()

        try:
            container = self.container_manager.containers.get(project_id)
            if not container:
                return await self._handle_missing_container(project_id, health_state)

            # Get Docker container
            docker_container = self.container_manager.docker.containers.get(
                container.container_id
            )

            # Check container status
            docker_container.reload()
            status = docker_container.status

            if status != "running":
                return await self._handle_stopped_container(
                    project_id, health_state, status
                )

            # Execute health check command
            exec_result = docker_container.exec_run(
                "echo healthy",
                timeout=10
            )

            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            if exec_result.exit_code == 0:
                health_check = HealthCheck(
                    status=HealthStatus.HEALTHY,
                    checked_at=datetime.utcnow(),
                    response_time_ms=response_time,
                    consecutive_failures=0
                )
                health_state.last_check = health_check
                health_state.last_healthy = datetime.utcnow()

                # Reset restart count if healthy for a while
                if health_state.restart_count > 0:
                    if health_state.last_restart:
                        time_since_restart = (datetime.utcnow() - health_state.last_restart).total_seconds()
                        if time_since_restart > self.restart_policy.reset_after_seconds:
                            health_state.restart_count = 0
                            logger.info(f"Reset restart count for {project_id}")

                return health_check
            else:
                return await self._handle_unhealthy(
                    project_id, health_state,
                    f"Health check failed: exit code {exec_result.exit_code}"
                )

        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return await self._handle_unhealthy(
                project_id, health_state, str(e)
            )

    async def _handle_missing_container(self,
                                        project_id: str,
                                        health_state: ContainerHealth) -> HealthCheck:
        """Handle case where container is missing"""
        health_check = HealthCheck(
            status=HealthStatus.DEAD,
            checked_at=datetime.utcnow(),
            response_time_ms=0,
            error_message="Container not found"
        )
        health_state.last_check = health_check

        if self.on_death:
            await self._safe_callback(self.on_death, project_id, "Container not found")

        # Remove from monitoring
        health_state.is_monitored = False

        return health_check

    async def _handle_stopped_container(self,
                                        project_id: str,
                                        health_state: ContainerHealth,
                                        status: str) -> HealthCheck:
        """Handle stopped container - attempt restart"""
        health_check = HealthCheck(
            status=HealthStatus.DEAD,
            checked_at=datetime.utcnow(),
            response_time_ms=0,
            error_message=f"Container status: {status}"
        )
        health_state.last_check = health_check

        # Attempt restart
        await self._attempt_restart(project_id, health_state)

        return health_check

    async def _handle_unhealthy(self,
                                project_id: str,
                                health_state: ContainerHealth,
                                error: str) -> HealthCheck:
        """Handle unhealthy container"""
        consecutive = (health_state.last_check.consecutive_failures + 1
                      if health_state.last_check else 1)

        health_check = HealthCheck(
            status=HealthStatus.UNHEALTHY,
            checked_at=datetime.utcnow(),
            response_time_ms=0,
            error_message=error,
            consecutive_failures=consecutive
        )
        health_state.last_check = health_check

        logger.warning(f"Container {project_id} unhealthy: {error} (failures: {consecutive})")

        if self.on_unhealthy:
            await self._safe_callback(self.on_unhealthy, project_id, health_check)

        # Attempt restart after 3 consecutive failures
        if consecutive >= 3:
            await self._attempt_restart(project_id, health_state)

        return health_check

    async def _attempt_restart(self, project_id: str, health_state: ContainerHealth):
        """Attempt to restart a container with backoff"""
        # Check restart limit
        if health_state.restart_count >= self.restart_policy.max_restarts:
            logger.error(f"Container {project_id} exceeded max restarts, giving up")
            health_state.is_monitored = False

            if self.on_death:
                await self._safe_callback(
                    self.on_death, project_id,
                    f"Exceeded max restarts ({self.restart_policy.max_restarts})"
                )
            return

        # Calculate backoff delay
        delay = min(
            self.restart_policy.restart_delay_seconds *
            (self.restart_policy.backoff_multiplier ** health_state.restart_count),
            self.restart_policy.max_delay_seconds
        )

        # Check if enough time has passed since last restart
        if health_state.last_restart:
            time_since_restart = (datetime.utcnow() - health_state.last_restart).total_seconds()
            if time_since_restart < delay:
                logger.debug(f"Waiting {delay - time_since_restart:.0f}s before restart")
                return

        logger.info(f"Attempting restart of {project_id} (attempt {health_state.restart_count + 1})")

        try:
            container = self.container_manager.containers.get(project_id)
            if not container:
                return

            # Get Docker container and restart
            docker_container = self.container_manager.docker.containers.get(
                container.container_id
            )
            docker_container.restart(timeout=30)

            health_state.restart_count += 1
            health_state.last_restart = datetime.utcnow()

            if self.on_restart:
                await self._safe_callback(
                    self.on_restart, project_id, health_state.restart_count
                )

            logger.info(f"Container {project_id} restarted successfully")

        except Exception as e:
            logger.error(f"Failed to restart container {project_id}: {e}")
            health_state.restart_count += 1
            health_state.last_restart = datetime.utcnow()

    async def _safe_callback(self, callback: Callable, *args):
        """Execute callback safely"""
        try:
            result = callback(*args)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Callback error: {e}")

    def get_health(self, project_id: str) -> Optional[ContainerHealth]:
        """Get health state for a container"""
        return self.health_states.get(project_id)

    def get_all_health(self) -> Dict[str, ContainerHealth]:
        """Get health states for all containers"""
        return self.health_states.copy()

    def get_unhealthy_containers(self) -> List[str]:
        """Get list of unhealthy container project IDs"""
        unhealthy = []
        for project_id, health in self.health_states.items():
            if health.last_check and health.last_check.status != HealthStatus.HEALTHY:
                unhealthy.append(project_id)
        return unhealthy


# Global instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor(container_manager=None) -> Optional[HealthMonitor]:
    """Get or create the global health monitor"""
    global _health_monitor

    if _health_monitor is None and container_manager:
        _health_monitor = HealthMonitor(container_manager)

    return _health_monitor


async def start_health_monitoring(container_manager):
    """Start health monitoring for containers"""
    global _health_monitor

    if _health_monitor is None:
        _health_monitor = HealthMonitor(container_manager)

    await _health_monitor.start()
    return _health_monitor
