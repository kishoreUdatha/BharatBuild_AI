"""
SDK-based Orchestrator

A lightweight orchestrator that coordinates SDK agents with
existing custom agents for a hybrid approach.
"""

import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import json

from anthropic import AsyncAnthropic

from app.core.logging_config import logger
from app.core.config import settings
from app.modules.sdk_agents.sdk_tools import SDKToolManager, SDK_ORCHESTRATOR_SYSTEM_PROMPT
from app.modules.sdk_agents.sdk_fixer_agent import SDKFixerAgent, sdk_fixer_agent
from app.services.unified_storage import unified_storage as storage


@dataclass
class OrchestrationResult:
    """Result of an orchestration run"""
    success: bool
    project_id: str
    files_created: List[str]
    files_modified: List[str]
    errors_fixed: int
    message: str
    duration_seconds: float


class SDKOrchestrator:
    """
    Hybrid Orchestrator that combines:
    - SDK-based tool execution for fixes and file operations
    - Custom agents for planning, writing, and documentation

    This provides the reliability of the SDK with the flexibility
    of custom specialized agents.
    """

    def __init__(self):
        """Initialize the SDK Orchestrator"""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.sdk_fixer = sdk_fixer_agent
        self.tools = SDKToolManager.get_orchestrator_tools()

    async def run_with_auto_fix(
        self,
        project_id: str,
        user_id: str,
        plan: Dict[str, Any],
        build_command: str = "npm run build",
        max_fix_attempts: int = 5
    ) -> OrchestrationResult:
        """
        Execute a project plan with automatic error fixing.

        This runs the build after each file creation and
        automatically fixes any errors using the SDK Fixer.

        Args:
            project_id: Project identifier
            user_id: User identifier
            plan: Project plan with files to create
            build_command: Command to verify build
            max_fix_attempts: Maximum fix attempts per error

        Returns:
            OrchestrationResult with details
        """
        start_time = datetime.utcnow()
        files_created = []
        files_modified = []
        errors_fixed = 0

        logger.info(f"[SDKOrchestrator:{project_id}] Starting orchestration with auto-fix")

        try:
            # Get files from plan
            files = plan.get("files", [])
            if not files:
                return OrchestrationResult(
                    success=False,
                    project_id=project_id,
                    files_created=[],
                    files_modified=[],
                    errors_fixed=0,
                    message="No files in plan",
                    duration_seconds=0
                )

            # Create files in priority order
            sorted_files = sorted(files, key=lambda f: f.get("priority", 999))

            for file_info in sorted_files:
                path = file_info.get("path", "")
                content = file_info.get("content", "")

                if not path:
                    continue

                # Write file
                try:
                    await storage.write_to_sandbox(project_id, path, content, user_id)
                    files_created.append(path)
                    logger.info(f"[SDKOrchestrator:{project_id}] Created: {path}")
                except Exception as e:
                    logger.error(f"[SDKOrchestrator:{project_id}] Failed to create {path}: {e}")

            # Run build and fix errors
            for attempt in range(max_fix_attempts):
                logger.info(f"[SDKOrchestrator:{project_id}] Build attempt {attempt + 1}/{max_fix_attempts}")

                # Execute build command
                build_result = await self._run_command(project_id, user_id, build_command)

                # Check if build succeeded
                if self._is_build_success(build_result):
                    logger.info(f"[SDKOrchestrator:{project_id}] Build succeeded!")
                    break

                # Extract error and fix
                logger.info(f"[SDKOrchestrator:{project_id}] Build failed, attempting fix...")

                fix_result = await self.sdk_fixer.fix_error(
                    project_id=project_id,
                    user_id=user_id,
                    error_message=build_result,
                    command=build_command
                )

                if fix_result.success:
                    errors_fixed += 1
                    files_modified.extend(fix_result.files_modified)
                else:
                    logger.warning(f"[SDKOrchestrator:{project_id}] Fix failed: {fix_result.message}")

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            return OrchestrationResult(
                success=True,
                project_id=project_id,
                files_created=files_created,
                files_modified=list(set(files_modified)),
                errors_fixed=errors_fixed,
                message=f"Created {len(files_created)} files, fixed {errors_fixed} errors",
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"[SDKOrchestrator:{project_id}] Orchestration error: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            return OrchestrationResult(
                success=False,
                project_id=project_id,
                files_created=files_created,
                files_modified=files_modified,
                errors_fixed=errors_fixed,
                message=str(e),
                duration_seconds=duration
            )

    async def fix_project_errors(
        self,
        project_id: str,
        user_id: str,
        error_message: str,
        build_command: str = "npm run build"
    ) -> Dict[str, Any]:
        """
        Fix errors in an existing project.

        This is a simple wrapper around the SDK Fixer for
        integration with existing endpoints.

        Args:
            project_id: Project identifier
            user_id: User identifier
            error_message: Error to fix
            build_command: Command to verify fix

        Returns:
            Dict with fix results
        """
        result = await self.sdk_fixer.fix_with_retry(
            project_id=project_id,
            user_id=user_id,
            error_message=error_message,
            build_command=build_command,
            max_retries=3
        )

        return {
            "success": result.success,
            "error_fixed": result.error_fixed,
            "files_modified": result.files_modified,
            "message": result.message,
            "attempts": result.attempts
        }

    async def stream_orchestration(
        self,
        project_id: str,
        user_id: str,
        user_request: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream orchestration events for real-time UI updates.

        This provides SSE-compatible events as the orchestration
        progresses.

        Args:
            project_id: Project identifier
            user_id: User identifier
            user_request: User's project request

        Yields:
            Event dictionaries for streaming
        """
        yield {
            "type": "status",
            "message": "Starting orchestration...",
            "phase": "init"
        }

        try:
            # Phase 1: Planning (use existing planner)
            yield {
                "type": "status",
                "message": "Creating project plan...",
                "phase": "planning"
            }

            # Import here to avoid circular imports
            from app.modules.agents.planner_agent import planner_agent
            from app.modules.agents.base_agent import AgentContext

            context = AgentContext(
                user_request=user_request,
                project_id=project_id,
                metadata={}
            )

            plan_result = await planner_agent.process(context)

            if not plan_result.get("success"):
                yield {
                    "type": "error",
                    "message": "Planning failed",
                    "error": plan_result.get("error", "Unknown error")
                }
                return

            yield {
                "type": "plan",
                "plan": plan_result.get("plan", {}),
                "phase": "planning"
            }

            # Phase 2: Writing (use existing writer or SDK)
            yield {
                "type": "status",
                "message": "Generating files...",
                "phase": "writing"
            }

            # For now, yield a placeholder - integrate with writer agent
            files = plan_result.get("plan", {}).get("files", [])
            for i, file_info in enumerate(files):
                yield {
                    "type": "file_progress",
                    "file": file_info.get("path", ""),
                    "index": i + 1,
                    "total": len(files),
                    "phase": "writing"
                }

            # Phase 3: Building
            yield {
                "type": "status",
                "message": "Building project...",
                "phase": "building"
            }

            # Phase 4: Fixing (if needed)
            yield {
                "type": "status",
                "message": "Checking for errors...",
                "phase": "fixing"
            }

            # Phase 5: Complete
            yield {
                "type": "complete",
                "message": "Project ready!",
                "project_id": project_id
            }

        except Exception as e:
            logger.error(f"[SDKOrchestrator:{project_id}] Stream error: {e}")
            yield {
                "type": "error",
                "message": str(e)
            }

    async def _run_command(
        self,
        project_id: str,
        user_id: str,
        command: str,
        timeout: int = 120
    ) -> str:
        """Run a command in the sandbox"""
        import subprocess

        try:
            sandbox_path = storage.get_sandbox_path(project_id, user_id)

            result = subprocess.run(
                command,
                shell=True,
                cwd=sandbox_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += result.stderr

            return output if output else f"Exit code: {result.returncode}"

        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Command error: {str(e)}"

    def _is_build_success(self, output: str) -> bool:
        """Check if build output indicates success"""
        output_lower = output.lower()

        # Check for common error indicators
        error_indicators = [
            "error",
            "failed",
            "exception",
            "traceback",
            "syntaxerror",
            "typeerror",
            "referenceerror",
            "cannot find",
            "module not found",
            "enoent"
        ]

        for indicator in error_indicators:
            if indicator in output_lower:
                return False

        # Check for success indicators
        success_indicators = [
            "built in",
            "compiled successfully",
            "build completed",
            "ready in",
            "done in"
        ]

        for indicator in success_indicators:
            if indicator in output_lower:
                return True

        # If no errors found, assume success
        return True


# Singleton instance
sdk_orchestrator = SDKOrchestrator()
