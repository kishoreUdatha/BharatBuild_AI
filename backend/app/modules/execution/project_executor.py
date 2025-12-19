"""
Project Executor - Connects AI Generation to Container Execution

This is the MISSING LINK between:
1. AI generates code (Claude)
2. Code runs in container (Docker)

Flow:
    User Prompt → Orchestrator → Writer Agent → PROJECT EXECUTOR → Container
                                                      ↓
                                              Writes files + Runs commands
                                                      ↓
                                              Streams output to frontend
"""

import asyncio
import json
from typing import Dict, Any, AsyncGenerator, List, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from app.modules.execution.container_manager import (
    ContainerManager,
    get_container_manager,
    ContainerConfig,
)
from app.modules.execution.command_validator import (
    CommandValidator,
    get_command_validator,
    CommandRisk,
)
from app.core.logging_config import logger


@dataclass
class ExecutionStep:
    """Represents a step in project execution"""
    step_type: str  # "file_write", "command", "verify"
    data: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    output: str = ""
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ProjectExecutor:
    """
    Executes AI-generated code in isolated containers.

    This bridges the gap between:
    - AI code generation (Writer Agent)
    - Container execution (ContainerManager)

    Usage:
        executor = ProjectExecutor(project_id, user_id)

        async for event in executor.execute(ai_output):
            # event = {"type": "file_written", "path": "src/App.tsx"}
            # event = {"type": "stdout", "data": "Installing..."}
            # event = {"type": "preview_ready", "url": "http://..."}
            yield event
    """

    # Default commands to run for each project type
    DEFAULT_COMMANDS = {
        "node": [
            "npm install",
            "npm run dev -- --host 0.0.0.0"
        ],
        "python": [
            "pip install -r requirements.txt",
            "python main.py"
        ],
        "python-flask": [
            "pip install -r requirements.txt",
            "flask run --host=0.0.0.0"
        ],
        "python-fastapi": [
            "pip install -r requirements.txt",
            "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
        ],
        "java-maven": [
            "mvn clean install -DskipTests",
            "mvn spring-boot:run"
        ],
        "java-gradle": [
            "gradle build -x test",
            "gradle bootRun"
        ],
        "go": [
            "go mod download",
            "go run ."
        ],
        "rust": [
            "cargo build",
            "cargo run"
        ],
        "static": [
            "npx serve -s . -p 3000"
        ]
    }

    def __init__(self,
                 project_id: str,
                 user_id: str,
                 project_type: str = "node",
                 container_manager: Optional[ContainerManager] = None,
                 command_validator: Optional[CommandValidator] = None):
        """
        Initialize project executor.

        Args:
            project_id: Unique project identifier
            user_id: User who owns the project
            project_type: Type of project (node, python, java, etc.)
            container_manager: Optional container manager instance
            command_validator: Optional command validator instance
        """
        self.project_id = project_id
        self.user_id = user_id
        self.project_type = project_type

        self.container_manager = container_manager or get_container_manager()
        self.command_validator = command_validator or get_command_validator()

        self.container = None
        self.steps: List[ExecutionStep] = []

    async def execute(self,
                      ai_output: Dict[str, Any],
                      auto_run: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute AI-generated code.

        Args:
            ai_output: Output from Writer Agent containing files and commands
                {
                    "files": [
                        {"path": "src/App.tsx", "content": "..."},
                        {"path": "package.json", "content": "..."}
                    ],
                    "commands": ["npm install", "npm run dev"]
                }
            auto_run: Whether to automatically run commands after writing files

        Yields:
            Execution events for frontend to display
        """
        try:
            # Step 1: Ensure container exists
            yield {"type": "status", "message": "Preparing execution environment..."}

            self.container = await self.container_manager.create_container(
                project_id=self.project_id,
                user_id=self.user_id,
                project_type=self.project_type,
            )

            yield {
                "type": "container_ready",
                "container_id": self.container.container_id[:12],
                "ports": self.container.port_mappings
            }

            # Step 2: Write all files
            files = ai_output.get("files", [])
            if files:
                yield {"type": "status", "message": f"Writing {len(files)} files..."}

                for file_info in files:
                    async for event in self._write_file(file_info):
                        yield event

            # Step 3: Run commands
            if auto_run:
                commands = ai_output.get("commands", [])

                # If no commands specified, use defaults
                if not commands:
                    commands = self._get_default_commands()

                if commands:
                    yield {"type": "status", "message": "Running commands..."}

                    for command in commands:
                        async for event in self._run_command(command):
                            yield event

                            # Check if command failed
                            if event.get("type") == "exit" and not event.get("success"):
                                yield {
                                    "type": "error",
                                    "message": f"Command failed: {command}"
                                }
                                # Continue with next command or stop?
                                # For now, continue

            # Step 4: Get preview URL
            preview_url = await self.container_manager.get_preview_url(
                self.project_id, 3000
            )

            if preview_url:
                yield {
                    "type": "preview_ready",
                    "url": preview_url,
                    "port": 3000
                }

            # Final status
            yield {
                "type": "complete",
                "message": "Project ready!",
                "files_written": len(files),
                "commands_executed": len(ai_output.get("commands", [])),
                "preview_url": preview_url
            }

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            yield {
                "type": "error",
                "message": str(e)
            }

    async def _write_file(self, file_info: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Write a single file to the container"""
        path = file_info.get("path", "")
        content = file_info.get("content", "")

        # Validate path
        validation = self.command_validator.validate_file_path(path)
        if not validation.is_valid:
            yield {
                "type": "error",
                "message": f"Invalid file path: {validation.error_message}"
            }
            return

        try:
            yield {
                "type": "file_start",
                "path": path
            }

            await self.container_manager.write_file(
                self.project_id, path, content
            )

            yield {
                "type": "file_written",
                "path": path,
                "size": len(content)
            }

        except Exception as e:
            yield {
                "type": "file_error",
                "path": path,
                "error": str(e)
            }

    async def _run_command(self, command: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Run a command in the container"""
        # Validate command
        validation = self.command_validator.validate(command)

        if not validation.is_valid:
            yield {
                "type": "command_blocked",
                "command": command,
                "reason": validation.error_message
            }
            return

        if validation.risk_level == CommandRisk.DANGEROUS:
            yield {
                "type": "command_warning",
                "command": command,
                "risk": "dangerous"
            }

        yield {
            "type": "command_start",
            "command": validation.sanitized_command
        }

        try:
            async for event in self.container_manager.execute_command(
                self.project_id,
                validation.sanitized_command
            ):
                yield event

        except Exception as e:
            yield {
                "type": "command_error",
                "command": command,
                "error": str(e)
            }

    def _get_default_commands(self) -> List[str]:
        """Get default commands for project type"""
        return self.DEFAULT_COMMANDS.get(self.project_type, [])

    async def run_command(self, command: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run a single command (for interactive use).

        Can be called from terminal when user types a command.
        """
        if not self.container:
            # Ensure container exists
            self.container = await self.container_manager.create_container(
                project_id=self.project_id,
                user_id=self.user_id,
                project_type=self.project_type,
            )

        async for event in self._run_command(command):
            yield event

    async def write_files(self, files: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Write multiple files (for manual file updates).

        Can be called when user saves file in editor.
        """
        for file_info in files:
            async for event in self._write_file(file_info):
                yield event

    async def get_preview_url(self, port: int = 3000) -> Optional[str]:
        """Get preview URL for the project"""
        return await self.container_manager.get_preview_url(self.project_id, port)

    async def stop(self):
        """Stop the project container"""
        await self.container_manager.stop_container(self.project_id)

    async def delete(self, delete_files: bool = False):
        """Delete the project container"""
        await self.container_manager.delete_container(self.project_id, delete_files)


async def execute_ai_output(
    project_id: str,
    user_id: str,
    ai_output: Dict[str, Any],
    project_type: str = "node"
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function to execute AI output.

    Usage in orchestrator:
        async for event in execute_ai_output(project_id, user_id, writer_output):
            yield event  # Forward to frontend
    """
    executor = ProjectExecutor(
        project_id=project_id,
        user_id=user_id,
        project_type=project_type
    )

    async for event in executor.execute(ai_output):
        yield event
