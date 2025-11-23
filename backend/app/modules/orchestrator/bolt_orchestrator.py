"""
Bolt.new Style Orchestrator

Implements the exact Bolt.new workflow:
1. User Input → Backend
2. Backend calls Planner Agent
3. Planner returns <plan>
4. Backend iterates through steps
5. For each step, call Writer Agent
6. Writer Agent returns <file>, <terminal>, <explain>
7. Backend executes actions and updates UI
8. Mark step complete, move to next
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.planner_agent import planner_agent
from app.modules.agents.writer_agent import writer_agent
from app.modules.agents.base_agent import AgentContext
from app.utils.response_parser import PlainTextParser


class BoltOrchestrator:
    """
    Bolt.new Architecture Orchestrator

    Workflow:
    User Request → Planner Agent → Writer Agent (Step 1) → Writer Agent (Step 2) → ... → Complete
    """

    def __init__(self):
        self.planner = planner_agent
        self.writer = writer_agent

    async def execute_bolt_workflow(
        self,
        user_request: str,
        project_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute complete Bolt.new workflow

        Args:
            user_request: User's project request
            project_id: Unique project identifier
            metadata: Additional project metadata
            progress_callback: Callback for progress updates (percent, message)

        Returns:
            Complete execution results
        """
        try:
            logger.info(f"[Bolt Orchestrator] Starting workflow for project: {project_id}")

            # STEP 1: Call Planner Agent (0-20%)
            if progress_callback:
                await progress_callback(5, "Analyzing your request...")

            plan_result = await self._execute_planner(
                user_request=user_request,
                project_id=project_id,
                metadata=metadata
            )

            if not plan_result["success"]:
                raise Exception(f"Planner failed: {plan_result.get('error')}")

            if progress_callback:
                await progress_callback(20, "Project plan created!")

            # Parse plan
            plan = plan_result.get("plan", {})
            logger.info(f"[Bolt Orchestrator] Plan created with {len(plan)} sections")

            # STEP 2: Extract implementation steps
            steps = self._extract_steps_from_plan(plan)
            total_steps = len(steps)

            logger.info(f"[Bolt Orchestrator] Extracted {total_steps} implementation steps")

            # STEP 3: Execute each step with Writer Agent (20-95%)
            step_results = []
            all_files_created = []
            all_commands_executed = []

            for i, step_data in enumerate(steps, 1):
                # Calculate progress (20% to 95% range)
                step_progress = 20 + int(((i - 1) / total_steps) * 75)

                if progress_callback:
                    await progress_callback(
                        step_progress,
                        f"Step {i}/{total_steps}: {step_data.get('name', 'Processing...')}"
                    )

                # Execute step with Writer Agent
                step_result = await self._execute_step(
                    step_number=i,
                    step_data=step_data,
                    project_id=project_id,
                    user_request=user_request,
                    previous_context={
                        "files_created": all_files_created,
                        "commands_executed": all_commands_executed
                    }
                )

                step_results.append(step_result)

                # Collect files and commands
                if step_result["success"]:
                    all_files_created.extend(step_result.get("files_created", []))
                    all_commands_executed.extend(step_result.get("commands_executed", []))

                    logger.info(
                        f"[Bolt Orchestrator] Step {i} completed: "
                        f"{len(step_result.get('files_created', []))} files, "
                        f"{len(step_result.get('commands_executed', []))} commands"
                    )
                else:
                    logger.warning(f"[Bolt Orchestrator] Step {i} failed: {step_result.get('error')}")

            # STEP 4: Finalize (95-100%)
            if progress_callback:
                await progress_callback(95, "Finalizing project...")

            # Final result
            result = {
                "success": True,
                "project_id": project_id,
                "plan": plan,
                "total_steps": total_steps,
                "steps_completed": len([s for s in step_results if s["success"]]),
                "step_results": step_results,
                "total_files_created": len(all_files_created),
                "total_commands_executed": len(all_commands_executed),
                "files_created": all_files_created,
                "commands_executed": all_commands_executed,
                "started_at": plan_result.get("timestamp"),
                "completed_at": datetime.utcnow().isoformat()
            }

            if progress_callback:
                await progress_callback(100, "Project complete!")

            logger.info(
                f"[Bolt Orchestrator] Workflow completed successfully. "
                f"Files: {len(all_files_created)}, Commands: {len(all_commands_executed)}"
            )

            return result

        except Exception as e:
            logger.error(f"[Bolt Orchestrator] Workflow failed: {e}", exc_info=True)
            return {
                "success": False,
                "project_id": project_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _execute_planner(
        self,
        user_request: str,
        project_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute Planner Agent"""
        try:
            logger.info(f"[Bolt Orchestrator] Calling Planner Agent")

            # Create context
            context = AgentContext(
                user_request=user_request,
                project_id=project_id,
                metadata=metadata or {}
            )

            # Call planner
            result = await self.planner.process(context)

            # Check if planner succeeded
            if not result.get("success"):
                raise Exception(f"Planner failed: {result.get('error')}")

            # Get plan from result
            plan = result.get("plan", {})

            if not plan:
                raise Exception("Planner returned no plan")

            return {
                "success": True,
                "plan": plan,
                "timestamp": result.get("timestamp", datetime.utcnow().isoformat())
            }

        except Exception as e:
            logger.error(f"[Bolt Orchestrator] Planner execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_step(
        self,
        step_number: int,
        step_data: Dict[str, Any],
        project_id: str,
        user_request: str,
        previous_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single step with Writer Agent"""
        try:
            logger.info(f"[Bolt Orchestrator] Executing Step {step_number}: {step_data.get('name')}")

            # Create context
            context = AgentContext(
                user_request=user_request,
                project_id=project_id,
                metadata={
                    "step_number": step_number,
                    "step_name": step_data.get("name"),
                    "previous_context": previous_context
                }
            )

            # Call Writer Agent
            result = await self.writer.process(
                context=context,
                step_number=step_number,
                step_data=step_data,
                previous_context=previous_context
            )

            return result

        except Exception as e:
            logger.error(f"[Bolt Orchestrator] Step {step_number} execution failed: {e}")
            return {
                "success": False,
                "step_number": step_number,
                "error": str(e)
            }

    def _parse_plan_text(self, plan_text: str) -> Dict[str, Any]:
        """
        Parse plain text plan into structured format

        Args:
            plan_text: Plain text from <plan> tag

        Returns:
            Structured plan dict
        """
        # Use PlainTextParser to parse the structured plan
        parsed = PlainTextParser.parse_planner_response(f"<plan>{plan_text}</plan>")
        return parsed.get("plan", {})

    def _extract_steps_from_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract implementation steps from plan

        Args:
            plan: Structured plan from Planner Agent

        Returns:
            List of step dicts
        """
        steps = []

        # Check for implementation_steps or implementation_plan
        if "implementation_steps" in plan:
            implementation_steps = plan["implementation_steps"]

            if isinstance(implementation_steps, list):
                # Already a list
                steps = implementation_steps
            elif isinstance(implementation_steps, dict):
                # Convert dict to list
                for phase_key, phase_data in implementation_steps.items():
                    if isinstance(phase_data, dict):
                        steps.append({
                            "name": phase_data.get("name", phase_key),
                            "description": phase_data.get("description", ""),
                            "tasks": phase_data.get("tasks", []),
                            "deliverables": phase_data.get("deliverables", []),
                            "duration": phase_data.get("duration", "")
                        })

        # Fallback: create default steps
        if not steps:
            logger.warning("[Bolt Orchestrator] No implementation steps found, using defaults")
            steps = [
                {
                    "name": "Project Setup",
                    "description": "Initialize project structure and dependencies",
                    "tasks": ["Create project folders", "Setup configuration files"],
                    "deliverables": ["Project structure"]
                },
                {
                    "name": "Core Implementation",
                    "description": "Implement core features",
                    "tasks": ["Generate main application files"],
                    "deliverables": ["Working application"]
                },
                {
                    "name": "Finalization",
                    "description": "Final touches and documentation",
                    "tasks": ["Add README", "Final testing"],
                    "deliverables": ["Complete project"]
                }
            ]

        return steps

    async def get_step_status(
        self,
        project_id: str,
        step_number: int
    ) -> Dict[str, Any]:
        """
        Get status of a specific step

        Args:
            project_id: Project identifier
            step_number: Step number to check

        Returns:
            Step status information
        """
        # This would typically query a database or cache
        # For now, return a placeholder
        return {
            "project_id": project_id,
            "step_number": step_number,
            "status": "unknown",
            "message": "Status tracking not yet implemented"
        }


# Singleton instance
bolt_orchestrator = BoltOrchestrator()
