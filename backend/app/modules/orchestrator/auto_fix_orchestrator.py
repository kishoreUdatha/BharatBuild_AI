"""
Auto-Fix Orchestrator - Bolt.new Style Automatic Error Fixing Loop

The complete auto-fix loop that makes Bolt.new feel "magical":

┌─────────────────────────────────────────────────────────────────┐
│                    AUTO-FIX LOOP                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. DETECT     Browser/Build/Backend/Docker Error               │
│       ↓                                                          │
│  2. ANALYZE    Collect logs, extract context, identify files    │
│       ↓                                                          │
│  3. FIX        Call Fixer Agent (Claude) → Generate patches     │
│       ↓                                                          │
│  4. APPLY      Apply unified diff patches to files              │
│       ↓                                                          │
│  5. RESTART    Restart Docker/Preview server                    │
│       ↓                                                          │
│  6. VERIFY     Check if error is fixed                          │
│       ↓                                                          │
│  ┌─────┴─────┐                                                   │
│  │ Fixed?    │                                                   │
│  └─────┬─────┘                                                   │
│    YES │ NO                                                      │
│    ↓   └───→ Retry (up to 3x) or notify user                    │
│  DONE                                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Key Features:
- Automatic detection (no user action needed)
- Debouncing (wait for errors to accumulate)
- Cooldown (prevent infinite loops)
- Max retries (escalate to user if needed)
- Event-driven (integrates with Event Bus)
- State machine controlled (predictable behavior)
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from app.core.logging_config import logger
from app.services.log_bus import get_log_bus, LogBus
from app.modules.orchestrator.state_machine import (
    FixLoopStateMachine,
    FixLoopState,
    get_state_manager
)
from app.modules.orchestrator.event_bus import (
    get_event_bus,
    EventType,
    EventPriority,
    create_fix_event,
    create_error_event
)


@dataclass
class AutoFixConfig:
    """Configuration for auto-fix behavior"""
    enabled: bool = True

    # Triggering
    min_errors_to_trigger: int = 1
    debounce_seconds: float = 2.0
    cooldown_seconds: float = 10.0

    # Retries
    max_attempts: int = 3
    retry_delay_seconds: float = 2.0

    # Error types
    fix_browser_errors: bool = True
    fix_build_errors: bool = True
    fix_backend_errors: bool = True
    fix_docker_errors: bool = True
    fix_network_errors: bool = False

    # Timeouts
    fix_timeout_seconds: float = 60.0
    restart_timeout_seconds: float = 30.0
    verify_timeout_seconds: float = 15.0


@dataclass
class FixContext:
    """Context for a fix operation"""
    project_id: str
    correlation_id: str
    errors: List[Dict[str, Any]] = field(default_factory=list)
    files_context: Dict[str, str] = field(default_factory=dict)
    patches: List[Dict[str, Any]] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    attempt: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "correlation_id": self.correlation_id,
            "error_count": len(self.errors),
            "files_modified": self.files_modified,
            "attempt": self.attempt,
            "duration_ms": (datetime.utcnow() - self.started_at).total_seconds() * 1000
        }


class AutoFixOrchestrator:
    """
    Orchestrates the complete auto-fix loop.

    This is the "brain" that makes Bolt.new's auto-fix work.
    It coordinates between LogBus, FixerAgent, FileManager,
    RestartManager, and sends events via EventBus.
    """

    def __init__(
        self,
        project_id: str,
        config: Optional[AutoFixConfig] = None
    ):
        self.project_id = project_id
        self.config = config or AutoFixConfig()

        # State machine
        self._state_machine = get_state_manager().get_fix_machine(project_id)
        self._state_machine.max_attempts = self.config.max_attempts

        # Event bus
        self._event_bus = get_event_bus()

        # Internal state
        self._pending_task: Optional[asyncio.Task] = None
        self._last_fix_time: Optional[datetime] = None
        self._current_context: Optional[FixContext] = None

        # Register event handlers
        self._register_event_handlers()

        logger.info(f"[AutoFixOrchestrator:{project_id}] Initialized")

    def _register_event_handlers(self):
        """Register handlers for error events"""
        event_bus = self._event_bus

        # Subscribe to error events for this project
        if self.config.fix_browser_errors:
            event_bus.subscribe(EventType.ERROR_BROWSER, self._on_error, self.project_id)
        if self.config.fix_build_errors:
            event_bus.subscribe(EventType.ERROR_BUILD, self._on_error, self.project_id)
        if self.config.fix_backend_errors:
            event_bus.subscribe(EventType.ERROR_BACKEND, self._on_error, self.project_id)
        if self.config.fix_docker_errors:
            event_bus.subscribe(EventType.ERROR_DOCKER, self._on_error, self.project_id)

    async def _on_error(self, event):
        """Handle incoming error event"""
        if not self.config.enabled:
            return

        logger.debug(f"[AutoFixOrchestrator:{self.project_id}] Error event received: {event.type}")

        # Check if we should trigger fix
        if await self._should_trigger():
            await self.trigger_fix()

    async def _should_trigger(self) -> bool:
        """Check if auto-fix should be triggered"""
        # Check cooldown
        if self._last_fix_time:
            elapsed = (datetime.utcnow() - self._last_fix_time).total_seconds()
            if elapsed < self.config.cooldown_seconds:
                logger.debug(
                    f"[AutoFixOrchestrator:{self.project_id}] "
                    f"Cooldown: {self.config.cooldown_seconds - elapsed:.1f}s remaining"
                )
                return False

        # Check state
        if self._state_machine.state not in [FixLoopState.IDLE, FixLoopState.COMPLETE]:
            logger.debug(
                f"[AutoFixOrchestrator:{self.project_id}] "
                f"Already in state: {self._state_machine.state}"
            )
            return False

        # Check error count
        log_bus = get_log_bus(self.project_id)
        errors = log_bus.get_errors()
        if len(errors) < self.config.min_errors_to_trigger:
            return False

        return True

    async def trigger_fix(self) -> bool:
        """
        Trigger the auto-fix loop with debouncing.

        Returns True if fix was scheduled.
        """
        # Cancel any pending fix
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()

        # Schedule with debounce
        self._pending_task = asyncio.create_task(
            self._debounced_fix()
        )
        return True

    async def _debounced_fix(self):
        """Execute fix after debounce period"""
        try:
            # Wait for debounce
            await asyncio.sleep(self.config.debounce_seconds)

            # Execute fix loop
            await self.execute_fix_loop()

        except asyncio.CancelledError:
            logger.debug(f"[AutoFixOrchestrator:{self.project_id}] Fix cancelled (debounce reset)")
        except Exception as e:
            logger.error(f"[AutoFixOrchestrator:{self.project_id}] Fix error: {e}")

    async def execute_fix_loop(self) -> Dict[str, Any]:
        """
        Execute the complete fix loop.

        Steps:
        1. Detect errors
        2. Analyze and build context
        3. Call Fixer Agent
        4. Apply patches
        5. Restart services
        6. Verify fix
        """
        import uuid
        correlation_id = str(uuid.uuid4())[:8]

        context = FixContext(
            project_id=self.project_id,
            correlation_id=correlation_id
        )
        self._current_context = context

        try:
            # ========== STEP 1: DETECT ==========
            self._state_machine.detect_error()
            await self._emit_event(EventType.STATUS, {
                "message": "Detecting errors...",
                "step": 1,
                "total_steps": 6
            })

            log_bus = get_log_bus(self.project_id)
            payload = log_bus.get_fixer_payload()

            # Collect all errors
            context.errors = (
                payload.get("browser_errors", []) +
                payload.get("build_errors", []) +
                payload.get("backend_errors", []) +
                payload.get("docker_errors", [])
            )

            if not context.errors:
                self._state_machine.transition(FixLoopState.IDLE, reason="No errors to fix")
                return {"success": False, "reason": "No errors detected"}

            logger.info(
                f"[AutoFixOrchestrator:{self.project_id}] "
                f"Detected {len(context.errors)} errors"
            )

            # ========== STEP 2: ANALYZE ==========
            self._state_machine.analyze()
            await self._emit_event(EventType.STATUS, {
                "message": f"Analyzing {len(context.errors)} errors...",
                "step": 2,
                "total_steps": 6
            })

            # Build file context
            context.files_context = await self._build_file_context(payload)

            # ========== STEP 3: FIX ==========
            self._state_machine.fix()
            context.attempt = self._state_machine.attempts

            await self._emit_event(EventType.FIX_STARTED, {
                "errors": len(context.errors),
                "attempt": context.attempt,
                "max_attempts": self.config.max_attempts
            })

            await self._emit_event(EventType.STATUS, {
                "message": f"Generating fix (attempt {context.attempt}/{self.config.max_attempts})...",
                "step": 3,
                "total_steps": 6
            })

            # Call Fixer Agent
            fix_result = await self._call_fixer_agent(context, payload)

            if not fix_result.get("success"):
                raise Exception(fix_result.get("error", "Fixer Agent failed"))

            context.patches = fix_result.get("patches", [])

            if not context.patches:
                raise Exception("No patches generated")

            await self._emit_event(EventType.FIX_PATCH_GENERATED, {
                "patch_count": len(context.patches)
            })

            # ========== STEP 4: APPLY ==========
            self._state_machine.apply_patches()
            await self._emit_event(EventType.STATUS, {
                "message": f"Applying {len(context.patches)} patches...",
                "step": 4,
                "total_steps": 6
            })

            apply_result = await self._apply_patches(context)
            context.files_modified = apply_result.get("files_modified", [])

            if not context.files_modified:
                raise Exception("No patches could be applied")

            for file_path in context.files_modified:
                await self._emit_event(EventType.FIX_PATCH_APPLIED, {
                    "file": file_path
                })

            # ========== STEP 5: RESTART ==========
            self._state_machine.restart()
            await self._emit_event(EventType.STATUS, {
                "message": "Restarting services...",
                "step": 5,
                "total_steps": 6
            })

            restart_result = await self._restart_services()

            if not restart_result.get("success"):
                logger.warning(
                    f"[AutoFixOrchestrator:{self.project_id}] "
                    f"Restart partial: {restart_result}"
                )

            # ========== STEP 6: VERIFY ==========
            self._state_machine.verify()
            await self._emit_event(EventType.STATUS, {
                "message": "Verifying fix...",
                "step": 6,
                "total_steps": 6
            })

            # Wait for potential new errors
            await asyncio.sleep(self.config.verify_timeout_seconds)

            # Check if new errors appeared
            log_bus.cleanup_old_logs()  # Clean old logs
            new_errors = log_bus.get_errors()

            if new_errors:
                # Still has errors - retry or fail
                if self._state_machine.retry_or_fail():
                    # Retry scheduled
                    await self._emit_event(EventType.STATUS, {
                        "message": f"Errors remain, retrying ({context.attempt + 1}/{self.config.max_attempts})..."
                    })
                    # Recurse with delay
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    return await self.execute_fix_loop()
                else:
                    # Max retries reached
                    await self._emit_event(EventType.FIX_MAX_RETRIES, {
                        "attempts": context.attempt,
                        "remaining_errors": len(new_errors)
                    })
                    return {
                        "success": False,
                        "reason": "Max retries reached",
                        "context": context.to_dict()
                    }

            # ========== SUCCESS ==========
            self._state_machine.complete()
            self._last_fix_time = datetime.utcnow()

            await self._emit_event(EventType.FIX_COMPLETED, {
                "files_modified": context.files_modified,
                "attempt": context.attempt,
                "duration_ms": context.to_dict()["duration_ms"]
            })

            # Clear log bus
            log_bus.clear()

            # Reset attempt counter for next time
            self._state_machine.reset_attempts()

            logger.info(
                f"[AutoFixOrchestrator:{self.project_id}] "
                f"Fix completed successfully in {context.to_dict()['duration_ms']:.0f}ms"
            )

            return {
                "success": True,
                "context": context.to_dict()
            }

        except Exception as e:
            logger.error(f"[AutoFixOrchestrator:{self.project_id}] Fix loop failed: {e}")

            self._state_machine.transition(FixLoopState.FAILED, reason=str(e))

            await self._emit_event(EventType.FIX_FAILED, {
                "error": str(e),
                "attempt": context.attempt if context else 0
            })

            return {
                "success": False,
                "error": str(e),
                "context": context.to_dict() if context else {}
            }

    async def _build_file_context(self, log_payload: Dict[str, Any]) -> Dict[str, str]:
        """Build file context for Fixer Agent"""
        from app.services.unified_storage import UnifiedStorageService as UnifiedStorageManager

        files = {}
        storage = UnifiedStorageManager()

        # Files mentioned in errors
        error_files = log_payload.get("error_files", [])

        # Key file patterns
        key_patterns = [".jsx", ".tsx", ".js", ".ts", ".py", ".css"]

        try:
            file_list = await storage.list_sandbox_files(self.project_id)

            # Priority 1: Files mentioned in errors
            files_to_read = set(error_files)

            # Priority 2: Key files
            for pattern in key_patterns:
                matching = [f for f in file_list if f.endswith(pattern)]
                files_to_read.update(matching[:5])  # Max 5 per pattern

            # Read files (max 20)
            for file_path in list(files_to_read)[:20]:
                try:
                    content = await storage.read_from_sandbox(self.project_id, file_path)
                    if content:
                        files[file_path] = content
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"[AutoFixOrchestrator:{self.project_id}] Failed to read files: {e}")

        return files

    async def _call_fixer_agent(
        self,
        context: FixContext,
        log_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call the Fixer Agent to generate patches"""
        from app.modules.agents.fixer_agent import FixerAgent

        try:
            fixer = FixerAgent()

            # Build error description
            error_desc = self._build_error_description(log_payload)

            # Build file context
            file_context = {
                "files": context.files_context,
                "file_tree": list(context.files_context.keys()),
                "tech_stack": self._detect_tech_stack(context.files_context),
                "log_payload": log_payload
            }

            # Call fixer with timeout
            result = await asyncio.wait_for(
                fixer.fix_error(
                    error={"description": error_desc, "source": "auto-fix"},
                    project_id=self.project_id,
                    file_context=file_context
                ),
                timeout=self.config.fix_timeout_seconds
            )

            # Parse patches from response if needed
            patches = result.get("patches", [])
            if not patches and result.get("response"):
                patches = self._parse_patches(result["response"])
                result["patches"] = patches

            return result

        except asyncio.TimeoutError:
            return {"success": False, "error": "Fixer Agent timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _apply_patches(self, context: FixContext) -> Dict[str, Any]:
        """Apply generated patches to files"""
        from app.services.unified_storage import UnifiedStorageService as UnifiedStorageManager

        storage = UnifiedStorageManager()
        files_modified = []

        for patch in context.patches:
            file_path = patch.get("file")
            patch_content = patch.get("content")

            if not file_path or not patch_content:
                continue

            try:
                # Read current content
                current = context.files_context.get(file_path)
                if current is None:
                    try:
                        current = await storage.read_from_sandbox(self.project_id, file_path)
                    except Exception:
                        current = ""

                # Apply patch
                new_content = self._apply_unified_patch(current or "", patch_content)

                if new_content and new_content != current:
                    await storage.save_to_sandbox(self.project_id, file_path, new_content)
                    files_modified.append(file_path)
                    logger.info(f"[AutoFixOrchestrator:{self.project_id}] Applied patch to {file_path}")

            except Exception as e:
                logger.error(f"[AutoFixOrchestrator:{self.project_id}] Patch failed for {file_path}: {e}")

        return {"files_modified": files_modified}

    async def _restart_services(self) -> Dict[str, Any]:
        """Restart Docker and preview services"""
        from app.services.restart_manager import restart_project

        try:
            result = await asyncio.wait_for(
                restart_project(
                    self.project_id,
                    restart_docker=True,
                    restart_preview=True,
                    notify_clients=True
                ),
                timeout=self.config.restart_timeout_seconds
            )
            return result

        except asyncio.TimeoutError:
            return {"success": False, "error": "Restart timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _emit_event(self, event_type: EventType, data: Dict[str, Any]):
        """Emit event to event bus"""
        await self._event_bus.emit_async(
            event_type,
            self.project_id,
            data,
            source="AutoFixOrchestrator"
        )

    def _build_error_description(self, log_payload: Dict[str, Any]) -> str:
        """Build error description from log payload"""
        parts = []

        for error in log_payload.get("browser_errors", [])[:5]:
            parts.append(f"Browser Error: {error.get('message', '')}")
            if error.get("file"):
                parts.append(f"  Location: {error['file']}:{error.get('line', '')}")

        for error in log_payload.get("build_errors", [])[:5]:
            parts.append(f"Build Error: {error.get('message', '')}")

        for error in log_payload.get("backend_errors", [])[:3]:
            parts.append(f"Backend Error: {error.get('message', '')}")

        for error in log_payload.get("docker_errors", [])[:2]:
            parts.append(f"Docker Error: {error.get('message', '')}")

        return "\n".join(parts)

    def _detect_tech_stack(self, files: Dict[str, str]) -> str:
        """Detect tech stack from files"""
        stack = []
        file_names = list(files.keys())
        all_content = "\n".join(files.values())

        if any(".jsx" in f or ".tsx" in f for f in file_names):
            stack.append("React")
        if "next.config" in str(file_names):
            stack.append("Next.js")
        if any(".ts" in f for f in file_names):
            stack.append("TypeScript")
        if any(".py" in f for f in file_names):
            stack.append("Python")
        if "tailwind" in all_content.lower():
            stack.append("Tailwind CSS")

        return ", ".join(stack) if stack else "Unknown"

    def _parse_patches(self, response: str) -> List[Dict[str, str]]:
        """Parse <patch> blocks from response"""
        import re

        patches = []
        pattern = r'<patch>\s*(.*?)\s*</patch>'

        for match in re.findall(pattern, response, re.DOTALL):
            file_match = re.search(r'^---\s+(\S+)', match, re.MULTILINE)
            if file_match:
                file_path = file_match.group(1)
                file_path = re.sub(r'^[ab]/', '', file_path)
                patches.append({
                    "file": file_path,
                    "content": match.strip()
                })

        return patches

    def _apply_unified_patch(self, original: str, patch: str) -> Optional[str]:
        """Apply unified diff patch"""
        import re

        try:
            lines = original.split('\n')
            result_lines = lines.copy()

            hunk_pattern = r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@'
            offset = 0

            for hunk_match in re.finditer(hunk_pattern, patch):
                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2) or 1)

                hunk_start = hunk_match.end()
                next_hunk = re.search(hunk_pattern, patch[hunk_start:])
                hunk_end = hunk_start + next_hunk.start() if next_hunk else len(patch)

                hunk_lines = patch[hunk_start:hunk_end].strip().split('\n')

                new_lines = []
                for line in hunk_lines:
                    if not line:
                        continue
                    prefix = line[0] if line else ' '
                    content = line[1:] if len(line) > 1 else ''

                    if prefix == ' ':
                        new_lines.append(content)
                    elif prefix == '+':
                        new_lines.append(content)

                actual_start = old_start - 1 + offset
                actual_end = actual_start + old_count

                actual_start = max(0, min(actual_start, len(result_lines)))
                actual_end = max(actual_start, min(actual_end, len(result_lines)))

                result_lines = result_lines[:actual_start] + new_lines + result_lines[actual_end:]
                offset += len(new_lines) - old_count

            return '\n'.join(result_lines)

        except Exception as e:
            logger.error(f"[AutoFixOrchestrator] Patch application failed: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            "project_id": self.project_id,
            "state": self._state_machine.state.value,
            "enabled": self.config.enabled,
            "attempts": self._state_machine.attempts,
            "max_attempts": self.config.max_attempts,
            "last_fix_time": self._last_fix_time.isoformat() if self._last_fix_time else None,
            "pending_fix": self._pending_task is not None and not self._pending_task.done(),
            "current_context": self._current_context.to_dict() if self._current_context else None
        }


# ========== Manager ==========

class AutoFixOrchestratorManager:
    """Manages AutoFixOrchestrator instances"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._orchestrators: Dict[str, AutoFixOrchestrator] = {}
        return cls._instance

    def get_or_create(
        self,
        project_id: str,
        config: Optional[AutoFixConfig] = None
    ) -> AutoFixOrchestrator:
        """Get or create orchestrator for a project"""
        if project_id not in self._orchestrators:
            self._orchestrators[project_id] = AutoFixOrchestrator(project_id, config)
        return self._orchestrators[project_id]

    def remove(self, project_id: str):
        """Remove orchestrator for a project"""
        if project_id in self._orchestrators:
            del self._orchestrators[project_id]


# Global manager
auto_fix_manager = AutoFixOrchestratorManager()


def get_auto_fix_orchestrator(
    project_id: str,
    config: Optional[AutoFixConfig] = None
) -> AutoFixOrchestrator:
    """Get auto-fix orchestrator for a project"""
    return auto_fix_manager.get_or_create(project_id, config)
