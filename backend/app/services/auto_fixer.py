"""
AutoFixer Service - Bolt.new Style Automatic Error Fixing

Monitors LogBus for errors and automatically triggers Fixer Agent.
User doesn't need to click "Fix" - system detects and fixes automatically.

Trigger conditions:
1. Build error detected (Vite/Webpack/tsc)
2. Runtime error in browser console
3. Backend API returns 500
4. Docker container fails to start
5. Preview fails to load
6. Unhandled promise rejection
7. Network error (CORS, timeout)
"""

import asyncio
from typing import Dict, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import threading

from app.core.logging_config import logger
from app.services.log_bus import get_log_bus, LogBus


@dataclass
class AutoFixConfig:
    """Configuration for auto-fix behavior"""
    enabled: bool = True
    # Minimum errors before triggering auto-fix
    min_errors_to_trigger: int = 1
    # Debounce time (wait for errors to accumulate)
    debounce_seconds: float = 2.0
    # Cooldown between auto-fix attempts (prevent infinite loops)
    cooldown_seconds: float = 10.0
    # Max auto-fix attempts per error pattern
    max_attempts_per_error: int = 3
    # Error types that trigger auto-fix
    trigger_on_build_error: bool = True
    trigger_on_runtime_error: bool = True
    trigger_on_backend_error: bool = True
    trigger_on_docker_error: bool = True
    trigger_on_network_error: bool = False  # Usually not fixable by code


@dataclass
class FixAttempt:
    """Track fix attempts to prevent infinite loops"""
    error_hash: str
    attempts: int = 0
    last_attempt: datetime = field(default_factory=datetime.utcnow)
    fixed: bool = False


class AutoFixer:
    """
    Automatic error fixer for a project.

    Monitors LogBus and triggers Fixer Agent when errors are detected.
    Applies patches automatically and notifies frontend to reload.
    """

    def __init__(self, project_id: str, config: Optional[AutoFixConfig] = None):
        self.project_id = project_id
        self.config = config or AutoFixConfig()
        self._lock = threading.Lock()

        # Track fix attempts to prevent infinite loops
        self._fix_attempts: Dict[str, FixAttempt] = {}

        # Pending fix task (for debouncing)
        self._pending_fix_task: Optional[asyncio.Task] = None
        self._last_fix_time: Optional[datetime] = None

        # Callbacks for fix events
        self._on_fix_started: Optional[Callable] = None
        self._on_fix_completed: Optional[Callable] = None
        self._on_fix_failed: Optional[Callable] = None

        # Flag to track if fix is in progress
        self._fixing: bool = False

    def set_callbacks(
        self,
        on_started: Optional[Callable] = None,
        on_completed: Optional[Callable] = None,
        on_failed: Optional[Callable] = None
    ):
        """Set callbacks for fix events"""
        self._on_fix_started = on_started
        self._on_fix_completed = on_completed
        self._on_fix_failed = on_failed

    def _get_error_hash(self, error: Dict[str, Any]) -> str:
        """Generate hash for error to track fix attempts"""
        # Use message + file + line as unique identifier
        parts = [
            error.get("message", "")[:100],
            error.get("file", ""),
            str(error.get("line", ""))
        ]
        return "|".join(parts)

    def _should_trigger_fix(self, log_bus: LogBus) -> tuple[bool, str]:
        """
        Determine if auto-fix should be triggered.

        Returns (should_fix, reason)
        """
        if not self.config.enabled:
            return False, "Auto-fix disabled"

        if self._fixing:
            return False, "Fix already in progress"

        # Check cooldown
        if self._last_fix_time:
            elapsed = (datetime.utcnow() - self._last_fix_time).total_seconds()
            if elapsed < self.config.cooldown_seconds:
                return False, f"Cooldown ({self.config.cooldown_seconds - elapsed:.1f}s remaining)"

        # Get errors from LogBus
        payload = log_bus.get_fixer_payload()

        trigger_reasons = []

        # Check build errors
        if self.config.trigger_on_build_error and payload["build_errors"]:
            for error in payload["build_errors"]:
                error_hash = self._get_error_hash(error)
                attempt = self._fix_attempts.get(error_hash)
                if not attempt or attempt.attempts < self.config.max_attempts_per_error:
                    trigger_reasons.append(f"Build error: {error.get('message', '')[:50]}")

        # Check runtime errors
        if self.config.trigger_on_runtime_error and payload["browser_errors"]:
            for error in payload["browser_errors"]:
                error_hash = self._get_error_hash(error)
                attempt = self._fix_attempts.get(error_hash)
                if not attempt or attempt.attempts < self.config.max_attempts_per_error:
                    trigger_reasons.append(f"Runtime error: {error.get('message', '')[:50]}")

        # Check backend errors
        if self.config.trigger_on_backend_error and payload["backend_errors"]:
            for error in payload["backend_errors"]:
                error_hash = self._get_error_hash(error)
                attempt = self._fix_attempts.get(error_hash)
                if not attempt or attempt.attempts < self.config.max_attempts_per_error:
                    trigger_reasons.append(f"Backend error: {error.get('message', '')[:50]}")

        # Check Docker errors
        if self.config.trigger_on_docker_error and payload["docker_errors"]:
            for error in payload["docker_errors"]:
                error_hash = self._get_error_hash(error)
                attempt = self._fix_attempts.get(error_hash)
                if not attempt or attempt.attempts < self.config.max_attempts_per_error:
                    trigger_reasons.append(f"Docker error: {error.get('message', '')[:50]}")

        if len(trigger_reasons) >= self.config.min_errors_to_trigger:
            return True, "; ".join(trigger_reasons[:3])

        return False, "No fixable errors detected"

    async def check_and_trigger(self, fix_callback: Callable) -> bool:
        """
        Check LogBus for errors and trigger fix if needed.

        fix_callback: async function(project_id, log_payload) -> result
        Returns True if fix was triggered.
        """
        log_bus = get_log_bus(self.project_id)
        should_fix, reason = self._should_trigger_fix(log_bus)

        if not should_fix:
            logger.debug(f"[AutoFixer:{self.project_id}] Not triggering: {reason}")
            return False

        logger.info(f"[AutoFixer:{self.project_id}] Triggering auto-fix: {reason}")

        # Cancel any pending fix task
        if self._pending_fix_task and not self._pending_fix_task.done():
            self._pending_fix_task.cancel()

        # Schedule fix with debounce
        self._pending_fix_task = asyncio.create_task(
            self._debounced_fix(fix_callback, reason)
        )

        return True

    async def _debounced_fix(self, fix_callback: Callable, reason: str):
        """Execute fix after debounce period"""
        try:
            # Wait for debounce period (let errors accumulate)
            await asyncio.sleep(self.config.debounce_seconds)

            # Execute fix
            await self._execute_fix(fix_callback, reason)

        except asyncio.CancelledError:
            logger.debug(f"[AutoFixer:{self.project_id}] Fix cancelled (new errors detected)")
        except Exception as e:
            logger.error(f"[AutoFixer:{self.project_id}] Fix failed: {e}")
            if self._on_fix_failed:
                await self._on_fix_failed(self.project_id, str(e))

    async def _execute_fix(self, fix_callback: Callable, reason: str):
        """Execute the actual fix"""
        with self._lock:
            if self._fixing:
                return
            self._fixing = True

        try:
            log_bus = get_log_bus(self.project_id)
            payload = log_bus.get_fixer_payload()

            # Track which errors we're attempting to fix
            all_errors = (
                payload["build_errors"] +
                payload["browser_errors"] +
                payload["backend_errors"] +
                payload["docker_errors"]
            )

            for error in all_errors:
                error_hash = self._get_error_hash(error)
                if error_hash not in self._fix_attempts:
                    self._fix_attempts[error_hash] = FixAttempt(error_hash=error_hash)
                self._fix_attempts[error_hash].attempts += 1
                self._fix_attempts[error_hash].last_attempt = datetime.utcnow()

            # Notify fix started
            if self._on_fix_started:
                await self._on_fix_started(self.project_id, reason)

            logger.info(f"[AutoFixer:{self.project_id}] Executing fix for: {reason}")

            # Call the fix callback (this should call Fixer Agent)
            result = await fix_callback(self.project_id, payload)

            self._last_fix_time = datetime.utcnow()

            # Check if fix was successful
            if result and result.get("success"):
                logger.info(f"[AutoFixer:{self.project_id}] Fix successful!")

                # Mark errors as fixed
                for error in all_errors:
                    error_hash = self._get_error_hash(error)
                    if error_hash in self._fix_attempts:
                        self._fix_attempts[error_hash].fixed = True

                # Clear LogBus after successful fix
                log_bus.clear()

                if self._on_fix_completed:
                    await self._on_fix_completed(self.project_id, result)
            else:
                error_msg = result.get("error", "Unknown error") if result else "No result"
                logger.warning(f"[AutoFixer:{self.project_id}] Fix failed: {error_msg}")

                if self._on_fix_failed:
                    await self._on_fix_failed(self.project_id, error_msg)

        finally:
            with self._lock:
                self._fixing = False

    def reset_attempts(self, error_hash: Optional[str] = None):
        """Reset fix attempts (use after user makes manual changes)"""
        with self._lock:
            if error_hash:
                if error_hash in self._fix_attempts:
                    del self._fix_attempts[error_hash]
            else:
                self._fix_attempts.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get current auto-fixer status"""
        with self._lock:
            return {
                "enabled": self.config.enabled,
                "fixing": self._fixing,
                "last_fix_time": self._last_fix_time.isoformat() if self._last_fix_time else None,
                "pending_fix": self._pending_fix_task is not None and not self._pending_fix_task.done(),
                "tracked_errors": len(self._fix_attempts),
                "config": {
                    "debounce_seconds": self.config.debounce_seconds,
                    "cooldown_seconds": self.config.cooldown_seconds,
                    "max_attempts": self.config.max_attempts_per_error
                }
            }


class AutoFixerManager:
    """
    Manages AutoFixer instances for all projects.

    Singleton pattern.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._fixers: Dict[str, AutoFixer] = {}
                    cls._instance._fixer_lock = threading.Lock()
        return cls._instance

    def get_fixer(self, project_id: str, config: Optional[AutoFixConfig] = None) -> AutoFixer:
        """Get or create AutoFixer for a project"""
        with self._fixer_lock:
            if project_id not in self._fixers:
                self._fixers[project_id] = AutoFixer(project_id, config)
                logger.info(f"[AutoFixerManager] Created AutoFixer for project {project_id}")
            return self._fixers[project_id]

    def remove_fixer(self, project_id: str):
        """Remove AutoFixer for a project"""
        with self._fixer_lock:
            if project_id in self._fixers:
                del self._fixers[project_id]
                logger.info(f"[AutoFixerManager] Removed AutoFixer for project {project_id}")


# Global singleton
auto_fixer_manager = AutoFixerManager()


def get_auto_fixer(project_id: str, config: Optional[AutoFixConfig] = None) -> AutoFixer:
    """Convenience function to get AutoFixer for a project"""
    return auto_fixer_manager.get_fixer(project_id, config)
