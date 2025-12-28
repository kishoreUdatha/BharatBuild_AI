"""
Error Recovery Service - Auto-Recovery for Run Failures

Handles recovery from common run-time failures:
1. Missing critical files → Regenerate from plan or notify user
2. S3 download failures → Fallback to database inline content
3. Container crashes → Auto-restart with cleanup
4. Max fix attempts → Provide actionable user guidance

Architecture:
- Each recovery strategy is independent and composable
- Strategies are tried in order until one succeeds
- All recovery attempts are logged for debugging
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import logger


class RecoveryType(str, Enum):
    """Types of error recovery strategies"""
    MISSING_FILES = "missing_files"
    S3_FAILURE = "s3_failure"
    CONTAINER_CRASH = "container_crash"
    FIX_EXHAUSTED = "fix_exhausted"
    VALIDATION_FAILED = "validation_failed"


class RecoveryAction(str, Enum):
    """Actions that can be taken to recover"""
    REGENERATE_FROM_PLAN = "regenerate_from_plan"
    RESTORE_FROM_DATABASE = "restore_from_database"
    RESTART_CONTAINER = "restart_container"
    RECREATE_CONTAINER = "recreate_container"
    NOTIFY_USER = "notify_user"
    RETRY_WITH_BACKOFF = "retry_with_backoff"


@dataclass
class RecoveryResult:
    """Result of a recovery attempt"""
    success: bool
    action_taken: RecoveryAction
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "action_taken": self.action_taken.value,
            "message": self.message,
            "details": self.details,
            "next_steps": self.next_steps,
        }


class ErrorRecoveryService:
    """
    Central service for handling error recovery.

    Usage:
        recovery = ErrorRecoveryService()
        result = await recovery.recover(
            error_type=RecoveryType.MISSING_FILES,
            context={"project_id": "...", "missing_files": ["package.json"]}
        )
    """

    def __init__(self):
        self.max_restart_attempts = 3
        self.restart_delay = 2.0  # seconds

    async def recover(
        self,
        error_type: RecoveryType,
        context: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> RecoveryResult:
        """
        Main recovery entry point. Dispatches to appropriate recovery strategy.
        """
        logger.info(f"[ErrorRecovery] Starting recovery for {error_type.value}")

        try:
            if error_type == RecoveryType.MISSING_FILES:
                return await self._recover_missing_files(context, db)
            elif error_type == RecoveryType.S3_FAILURE:
                return await self._recover_s3_failure(context, db)
            elif error_type == RecoveryType.CONTAINER_CRASH:
                return await self._recover_container_crash(context)
            elif error_type == RecoveryType.FIX_EXHAUSTED:
                return await self._handle_fix_exhausted(context)
            elif error_type == RecoveryType.VALIDATION_FAILED:
                return await self._recover_validation_failed(context, db)
            else:
                return RecoveryResult(
                    success=False,
                    action_taken=RecoveryAction.NOTIFY_USER,
                    message=f"Unknown error type: {error_type}",
                    next_steps=["Please contact support"]
                )
        except Exception as e:
            logger.error(f"[ErrorRecovery] Recovery failed: {e}")
            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.NOTIFY_USER,
                message=f"Recovery failed: {str(e)}",
                next_steps=["Please try again or contact support"]
            )

    # =========================================================================
    # RECOVERY STRATEGY 1: Missing Critical Files
    # =========================================================================

    async def _recover_missing_files(
        self,
        context: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> RecoveryResult:
        """
        Recover from missing critical files.

        Strategy:
        1. Try to regenerate from saved plan (if available)
        2. Try to restore from database
        3. Notify user with specific instructions
        """
        project_id = context.get("project_id")
        missing_files = context.get("missing_files", [])
        project_path = context.get("project_path")

        logger.info(f"[ErrorRecovery] Recovering missing files for {project_id}: {missing_files}")

        # Strategy 1: Try regeneration from plan
        if db:
            try:
                from app.services.workspace_restore import workspace_restore

                status = await workspace_restore.check_workspace_status(project_id, db)

                if status.get("can_regenerate"):
                    logger.info(f"[ErrorRecovery] Attempting regeneration from plan")
                    regen_result = await workspace_restore.regenerate_from_plan(project_id, db)

                    if regen_result.get("success"):
                        return RecoveryResult(
                            success=True,
                            action_taken=RecoveryAction.REGENERATE_FROM_PLAN,
                            message="Successfully regenerated project from saved plan",
                            details={"regeneration_context": regen_result.get("regeneration_context")},
                            next_steps=["Run the project again"]
                        )
            except Exception as e:
                logger.warning(f"[ErrorRecovery] Regeneration failed: {e}")

        # Strategy 2: Try restore from database (with lenient mode)
        if db:
            try:
                from app.services.workspace_restore import workspace_restore

                restore_result = await workspace_restore.restore_from_storage(
                    project_id, db, strict_mode=False  # Try partial restore
                )

                if restore_result.get("success") and restore_result.get("restored_files", 0) > 0:
                    # Check if we now have the missing files
                    still_missing = []
                    workspace_path = Path(restore_result.get("workspace_path", ""))
                    for f in missing_files:
                        if not (workspace_path / f).exists():
                            still_missing.append(f)

                    if not still_missing:
                        return RecoveryResult(
                            success=True,
                            action_taken=RecoveryAction.RESTORE_FROM_DATABASE,
                            message="Successfully restored missing files from storage",
                            details={"restored_files": restore_result.get("restored_files")},
                            next_steps=["Run the project again"]
                        )
            except Exception as e:
                logger.warning(f"[ErrorRecovery] Restore failed: {e}")

        # Strategy 3: Provide actionable user guidance
        instructions = self._get_missing_file_instructions(missing_files)

        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.NOTIFY_USER,
            message=f"Could not automatically recover missing files: {', '.join(missing_files)}",
            details={"missing_files": missing_files},
            next_steps=instructions
        )

    def _get_missing_file_instructions(self, missing_files: List[str]) -> List[str]:
        """Generate specific instructions for missing files"""
        instructions = []

        for f in missing_files:
            if f == "package.json":
                instructions.append("Create package.json: Run 'npm init -y' or add manually")
            elif f == "requirements.txt":
                instructions.append("Create requirements.txt: Run 'pip freeze > requirements.txt'")
            elif f == "go.mod":
                instructions.append("Create go.mod: Run 'go mod init <module-name>'")
            elif "vite.config" in f:
                instructions.append("Create vite.config.ts: Run 'npm create vite@latest' or add manually")
            elif f == "index.html":
                instructions.append("Create index.html: Add a basic HTML file with your app entry point")
            elif "pom.xml" in f or "build.gradle" in f:
                instructions.append("Create build file: Use Maven or Gradle to initialize project")
            else:
                instructions.append(f"Create {f}: Add the required file to your project")

        instructions.append("After adding the files, click Run again")
        return instructions

    # =========================================================================
    # RECOVERY STRATEGY 2: S3 Download Failures
    # =========================================================================

    async def _recover_s3_failure(
        self,
        context: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> RecoveryResult:
        """
        Recover from S3 download failures.

        Strategy:
        1. Try database inline content (legacy fallback)
        2. Try regeneration from plan
        3. Notify user
        """
        project_id = context.get("project_id")
        failed_files = context.get("failed_files", [])

        logger.info(f"[ErrorRecovery] Recovering S3 failure for {project_id}")

        # Strategy 1: Check if files have inline content in database
        if db:
            try:
                from sqlalchemy import select
                from app.models.project_file import ProjectFile

                # Query files with inline content
                result = await db.execute(
                    select(ProjectFile).where(
                        ProjectFile.project_id == project_id,
                        ProjectFile.content_inline.isnot(None)
                    )
                )
                files_with_inline = result.scalars().all()

                if files_with_inline:
                    # Some files have inline content - partial recovery possible
                    return RecoveryResult(
                        success=True,
                        action_taken=RecoveryAction.RESTORE_FROM_DATABASE,
                        message=f"Recovered {len(files_with_inline)} files from database (S3 fallback)",
                        details={"recovered_count": len(files_with_inline)},
                        next_steps=["Run the project again"]
                    )
            except Exception as e:
                logger.warning(f"[ErrorRecovery] Database fallback failed: {e}")

        # Strategy 2: Try regeneration
        if db:
            try:
                from app.services.workspace_restore import workspace_restore

                status = await workspace_restore.check_workspace_status(project_id, db)
                if status.get("can_regenerate"):
                    return RecoveryResult(
                        success=True,
                        action_taken=RecoveryAction.REGENERATE_FROM_PLAN,
                        message="S3 unavailable - project can be regenerated from plan",
                        details={"regeneration_available": True},
                        next_steps=[
                            "Click 'Regenerate Project' to recreate files from plan",
                            "This will use AI to regenerate all project files"
                        ]
                    )
            except Exception as e:
                logger.warning(f"[ErrorRecovery] Regeneration check failed: {e}")

        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.NOTIFY_USER,
            message="Could not recover from S3 failure",
            details={"failed_files": failed_files},
            next_steps=[
                "Check your internet connection",
                "Try again in a few minutes",
                "If problem persists, contact support"
            ]
        )

    # =========================================================================
    # RECOVERY STRATEGY 3: Container Crashes
    # =========================================================================

    async def _recover_container_crash(
        self,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Recover from container crash or unhealthy state.

        Strategy:
        1. Try to restart the container
        2. If restart fails, recreate container
        3. Notify user if all fails
        """
        project_id = context.get("project_id")
        container_id = context.get("container_id")

        logger.info(f"[ErrorRecovery] Recovering container crash for {project_id}")

        try:
            from app.services.container_executor import container_executor

            if not container_executor.docker_client:
                await container_executor.initialize()

            if not container_executor.docker_client:
                return RecoveryResult(
                    success=False,
                    action_taken=RecoveryAction.NOTIFY_USER,
                    message="Docker is not available",
                    next_steps=["Ensure Docker is running", "Try again"]
                )

            # Strategy 1: Try to restart existing container
            try:
                container = container_executor.docker_client.containers.get(container_id)
                container.restart(timeout=10)

                # Wait for container to be ready
                await asyncio.sleep(self.restart_delay)
                container.reload()

                if container.status == "running":
                    # Verify health after restart
                    is_healthy, _ = await container_executor.health_check_container(container)
                    if is_healthy:
                        return RecoveryResult(
                            success=True,
                            action_taken=RecoveryAction.RESTART_CONTAINER,
                            message="Container restarted successfully",
                            next_steps=["Run the project again"]
                        )
            except Exception as e:
                logger.warning(f"[ErrorRecovery] Container restart failed: {e}")

            # Strategy 2: Remove and recreate container
            try:
                # Remove crashed container
                try:
                    container = container_executor.docker_client.containers.get(container_id)
                    container.remove(force=True)
                except:
                    pass  # Container might already be gone

                # Clear from active containers
                if project_id in container_executor.active_containers:
                    del container_executor.active_containers[project_id]

                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.RECREATE_CONTAINER,
                    message="Container removed. A new container will be created on next run.",
                    next_steps=["Click Run to create a fresh container"]
                )
            except Exception as e:
                logger.error(f"[ErrorRecovery] Container recreation failed: {e}")

        except Exception as e:
            logger.error(f"[ErrorRecovery] Container recovery failed: {e}")

        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.NOTIFY_USER,
            message="Could not recover crashed container",
            next_steps=[
                "Click 'Stop' to clean up the container",
                "Click 'Run' to create a fresh container",
                "If problem persists, try restarting Docker"
            ]
        )

    # =========================================================================
    # RECOVERY STRATEGY 4: Fix Attempts Exhausted
    # =========================================================================

    async def _handle_fix_exhausted(
        self,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Handle case when auto-fix has exhausted all attempts.

        This is NOT really a recovery - it's providing guidance to the user.
        """
        project_id = context.get("project_id")
        error_message = context.get("error_message", "Unknown error")
        fix_attempts = context.get("fix_attempts", 3)

        logger.info(f"[ErrorRecovery] Fix exhausted for {project_id} after {fix_attempts} attempts")

        # Analyze the error to provide specific guidance
        guidance = self._analyze_error_for_guidance(error_message)

        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.NOTIFY_USER,
            message=f"Auto-fix could not resolve the error after {fix_attempts} attempts",
            details={
                "error_summary": error_message[:200],
                "attempts": fix_attempts
            },
            next_steps=guidance
        )

    def _analyze_error_for_guidance(self, error_message: str) -> List[str]:
        """Analyze error message and provide specific guidance"""
        error_lower = error_message.lower()
        guidance = []

        # Module not found errors
        if "cannot find module" in error_lower or "module not found" in error_lower:
            guidance.append("Install missing dependencies: Run 'npm install' or 'pip install -r requirements.txt'")
            guidance.append("Check import paths are correct")

        # Syntax errors
        elif "syntaxerror" in error_lower:
            guidance.append("Fix syntax error in your code")
            guidance.append("Check for missing brackets, semicolons, or quotes")

        # Type errors
        elif "typeerror" in error_lower:
            guidance.append("Check variable types and function arguments")
            guidance.append("Ensure objects are properly initialized before use")

        # Port in use
        elif "eaddrinuse" in error_lower or "port" in error_lower:
            guidance.append("Stop any other services using the same port")
            guidance.append("Try restarting the project")

        # Memory errors
        elif "out of memory" in error_lower or "heap" in error_lower:
            guidance.append("Reduce memory usage in your code")
            guidance.append("Check for memory leaks or large data structures")

        # Permission errors
        elif "permission" in error_lower or "eacces" in error_lower:
            guidance.append("Check file permissions")
            guidance.append("Ensure you have write access to the project directory")

        # Generic guidance
        if not guidance:
            guidance.append("Review the error message for specific details")
            guidance.append("Check your code for common issues")

        guidance.append("Click 'Retry Fix' to try auto-fix again")
        guidance.append("Or manually fix the error and click Run")

        return guidance

    # =========================================================================
    # RECOVERY STRATEGY 5: Validation Failed
    # =========================================================================

    async def _recover_validation_failed(
        self,
        context: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> RecoveryResult:
        """
        Recover from workspace validation failure.

        This is similar to missing files but triggered earlier in the process.
        """
        return await self._recover_missing_files(context, db)


# Singleton instance
error_recovery = ErrorRecoveryService()
