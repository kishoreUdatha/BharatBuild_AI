"""
Writer Agent - Step-by-Step File Writing Agent (Bolt.new Architecture)

This agent processes ONE step at a time from the plan, writes files incrementally,
executes terminal commands, and provides real-time progress updates.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import subprocess
import os

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.utils.response_parser import PlainTextParser
from app.modules.automation import file_manager


class WriterAgent(BaseAgent):
    """
    Writer Agent - Bolt.new Style Step-by-Step Execution

    Responsibilities:
    - Execute ONE step from the plan at a time
    - Parse <file> tags and write files to disk
    - Parse <terminal> tags and execute commands
    - Parse <explain> tags for UI updates
    - Mark steps as complete in real-time
    - Provide incremental progress updates
    """

    SYSTEM_PROMPT = """You are the WRITER AGENT (AGENT 2 - Dynamic Code Generator).

YOUR JOB:
1. Take ONE task at a time from the Planner Agent.
2. Generate COMPLETE, CLEAN CODE for that task.
3. Create or update files dynamically.
4. Follow the tech stack defined in <plan>.
5. Maintain consistent architecture across all tasks.
6. Automatically fix missing imports, outdated syntax, or mismatched folders.
7. Never explain code.

OUTPUT RULES:
- ALWAYS output using <file path="..."> CODE </file>
- You may output multiple <file> blocks.
- If updating a file, output the FULL file.
- NEVER output plan.
- NEVER output comments or text outside <file> blocks.

EXAMPLE INPUT:
Task: "Create database models"
Tech Stack: FastAPI + SQLAlchemy + PostgreSQL

EXAMPLE OUTPUT:
<file path="backend/app/models/user.py">
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
</file>

<file path="backend/app/models/todo.py">
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .user import Base

class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    completed = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="todos")
</file>

CRITICAL RULES:
1. ONE task at a time
2. COMPLETE, working code only
3. NO placeholders, NO TODOs
4. Output ONLY <file> blocks
5. Fix imports automatically
6. Follow the tech stack from plan
7. NO explanations outside <file> tags
"""

    def __init__(self):
        super().__init__(
            name="Writer Agent",
            role="step_by_step_file_writer",
            capabilities=[
                "incremental_file_writing",
                "terminal_command_execution",
                "real_time_progress",
                "step_by_step_execution",
                "bolt_new_architecture"
            ],
            model="haiku"  # Fast model for quick iterations
        )
    def __init__(self):
        super().__init__(
            name="Writer Agent",
            role="step_by_step_file_writer",
            capabilities=[
                "incremental_file_writing",
                "terminal_command_execution",
                "real_time_progress",
                "step_by_step_execution",
                "bolt_new_architecture"
            ],
            model="haiku"  # Fast model for quick iterations
        )

    async def process(
        self,
        context: AgentContext,
        step_number: int,
        step_data: Dict[str, Any],
        previous_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single step from the plan

        Args:
            context: Agent context with project info
            step_number: Current step number (1-indexed)
            step_data: Step information from plan
            previous_context: Context from previous steps

        Returns:
            Dict with execution results
        """
        try:
            logger.info(f"[Writer Agent] Executing Step {step_number}: {step_data.get('name', 'Unnamed Step')}")

            # Build prompt for this specific step
            step_prompt = self._build_step_prompt(
                step_number=step_number,
                step_data=step_data,
                previous_context=previous_context,
                context=context
            )

            # Call Claude with Bolt.new format
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=step_prompt,
                max_tokens=4096,
                temperature=0.3  # Lower temperature for consistent code
            )

            # Parse Bolt.new response
            parsed = PlainTextParser.parse_bolt_response(response)

            # Execute the parsed actions
            execution_result = await self._execute_actions(
                parsed=parsed,
                project_id=context.project_id,
                step_number=step_number
            )

            logger.info(f"[Writer Agent] Step {step_number} completed successfully")

            return {
                "success": True,
                "agent": self.name,
                "step_number": step_number,
                "step_name": step_data.get("name"),
                "thinking": parsed.get("thinking"),
                "explanation": parsed.get("explain"),
                "files_created": execution_result["files_created"],
                "commands_executed": execution_result["commands_executed"],
                "errors": execution_result.get("errors", []),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Writer Agent] Step {step_number} failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "step_number": step_number,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_step_prompt(
        self,
        step_number: int,
        step_data: Dict[str, Any],
        previous_context: Optional[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for the current step"""

        prompt_parts = [
            f"CURRENT STEP: Step {step_number}",
            f"STEP NAME: {step_data.get('name', 'Unnamed Step')}",
            f"STEP DESCRIPTION: {step_data.get('description', 'No description')}",
            ""
        ]

        # Add tasks if available
        if "tasks" in step_data and step_data["tasks"]:
            prompt_parts.append("TASKS TO COMPLETE:")
            for i, task in enumerate(step_data["tasks"], 1):
                prompt_parts.append(f"{i}. {task}")
            prompt_parts.append("")

        # Add deliverables if available
        if "deliverables" in step_data and step_data["deliverables"]:
            prompt_parts.append("DELIVERABLES:")
            for deliverable in step_data["deliverables"]:
                prompt_parts.append(f"- {deliverable}")
            prompt_parts.append("")

        # Add context from previous steps
        if previous_context:
            prompt_parts.append("CONTEXT FROM PREVIOUS STEPS:")
            if "files_created" in previous_context:
                prompt_parts.append(f"Files created so far: {len(previous_context['files_created'])} files")
            if "last_explanation" in previous_context:
                prompt_parts.append(f"Previous step: {previous_context['last_explanation']}")
            prompt_parts.append("")

        # Add project metadata
        metadata = context.metadata or {}
        if "tech_stack" in metadata:
            prompt_parts.append(f"TECH STACK: {metadata['tech_stack']}")
        if "features" in metadata:
            prompt_parts.append(f"FEATURES: {', '.join(metadata.get('features', []))}")

        prompt_parts.append("")
        prompt_parts.append("TASK:")
        prompt_parts.append(f"Execute Step {step_number} completely. Generate files, commands, and explanations using Bolt.new XML tags.")
        prompt_parts.append("Focus ONLY on this step. Do not generate files for future steps.")
        prompt_parts.append("")
        prompt_parts.append("Output format: <thinking>, <explain>, <file>, <terminal> tags")

        return "\n".join(prompt_parts)

    async def _execute_actions(
        self,
        parsed: Dict[str, Any],
        project_id: str,
        step_number: int
    ) -> Dict[str, Any]:
        """
        Execute parsed actions from Bolt.new response

        Args:
            parsed: Parsed response with files, commands, etc.
            project_id: Project identifier
            step_number: Current step number

        Returns:
            Dict with execution results
        """
        result = {
            "files_created": [],
            "commands_executed": [],
            "errors": []
        }

        # 1. Write files
        if "files" in parsed and parsed["files"]:
            for file_info in parsed["files"]:
                try:
                    file_path = file_info.get("path")
                    content = file_info.get("content")

                    if not file_path or not content:
                        logger.warning(f"[Writer Agent] Skipping file with missing path or content")
                        continue

                    # Write file using file_manager
                    write_result = await file_manager.create_file(
                        project_id=project_id,
                        file_path=file_path,
                        content=content
                    )

                    if write_result["success"]:
                        result["files_created"].append({
                            "path": file_path,
                            "size": len(content),
                            "step": step_number
                        })
                        logger.info(f"[Writer Agent] Created file: {file_path}")
                    else:
                        result["errors"].append(f"Failed to create {file_path}: {write_result.get('error')}")

                except Exception as e:
                    logger.error(f"[Writer Agent] Error writing file: {e}")
                    result["errors"].append(f"File write error: {str(e)}")

        # 2. Execute terminal commands
        if "terminal" in parsed:
            commands = parsed["terminal"]
            # Handle both single command (string) and multiple commands (list)
            if isinstance(commands, str):
                commands = [commands]

            for command in commands:
                try:
                    # Execute command safely
                    exec_result = await self._execute_terminal_command(
                        command=command,
                        project_id=project_id
                    )

                    result["commands_executed"].append({
                        "command": command,
                        "success": exec_result["success"],
                        "output": exec_result.get("output", ""),
                        "step": step_number
                    })

                    if not exec_result["success"]:
                        result["errors"].append(f"Command failed: {command}")

                except Exception as e:
                    logger.error(f"[Writer Agent] Error executing command: {e}")
                    result["errors"].append(f"Command error: {str(e)}")

        return result

    async def _execute_terminal_command(
        self,
        command: str,
        project_id: str,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Execute a terminal command safely

        Args:
            command: Command to execute
            project_id: Project identifier
            timeout: Command timeout in seconds

        Returns:
            Dict with execution result
        """
        try:
            logger.info(f"[Writer Agent] Executing command: {command}")

            # Get project directory
            project_dir = os.path.join("generated", project_id)

            # Security: Validate command is safe
            dangerous_commands = ["rm -rf", "sudo", "chmod 777", "dd if=", "> /dev/"]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                logger.warning(f"[Writer Agent] Blocked dangerous command: {command}")
                return {
                    "success": False,
                    "error": "Command blocked for security reasons"
                }

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "output": stdout.decode() if stdout else "",
                    "error": stderr.decode() if stderr else ""
                }

            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout}s"
                }

        except Exception as e:
            logger.error(f"[Writer Agent] Command execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_plan_steps(
        self,
        context: AgentContext,
        plan: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute all steps from a plan sequentially

        Args:
            context: Agent context
            plan: Complete plan with steps
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with all execution results
        """
        results = {
            "steps_completed": [],
            "total_files_created": 0,
            "total_commands_executed": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat()
        }

        # Extract steps from plan
        steps = self._extract_steps_from_plan(plan)
        total_steps = len(steps)

        logger.info(f"[Writer Agent] Starting execution of {total_steps} steps")

        previous_context = None

        for i, step_data in enumerate(steps, 1):
            # Update progress
            if progress_callback:
                progress_percent = int((i / total_steps) * 100)
                await progress_callback(
                    progress_percent,
                    f"Step {i}/{total_steps}: {step_data.get('name', 'Processing...')}"
                )

            # Execute step
            step_result = await self.process(
                context=context,
                step_number=i,
                step_data=step_data,
                previous_context=previous_context
            )

            results["steps_completed"].append(step_result)

            if step_result["success"]:
                results["total_files_created"] += len(step_result.get("files_created", []))
                results["total_commands_executed"] += len(step_result.get("commands_executed", []))

                # Update context for next step
                previous_context = {
                    "files_created": step_result.get("files_created", []),
                    "last_explanation": step_result.get("explanation")
                }
            else:
                results["errors"].append(f"Step {i} failed: {step_result.get('error')}")
                # Continue with next step even if current fails
                logger.warning(f"[Writer Agent] Step {i} failed, continuing with next step")

        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"[Writer Agent] Completed all steps. Files: {results['total_files_created']}, Commands: {results['total_commands_executed']}")

        return results

    def _extract_steps_from_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract steps from plan structure"""
        steps = []

        # Check for implementation_steps or phases
        if "implementation_steps" in plan:
            for phase_key, phase_data in plan["implementation_steps"].items():
                if isinstance(phase_data, dict):
                    steps.append({
                        "name": phase_data.get("name", phase_key),
                        "description": phase_data.get("description", ""),
                        "tasks": phase_data.get("tasks", []),
                        "deliverables": phase_data.get("deliverables", []),
                        "duration": phase_data.get("duration", "")
                    })

        # Fallback: if no steps found, create a single step
        if not steps:
            steps.append({
                "name": "Project Implementation",
                "description": "Implement the complete project",
                "tasks": ["Generate all required files", "Setup dependencies"],
                "deliverables": ["Complete working application"]
            })

        return steps


# Singleton instance
writer_agent = WriterAgent()
