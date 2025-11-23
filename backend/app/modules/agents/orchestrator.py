"""
Multi-Agent Orchestrator
Coordinates the workflow between specialized agents
"""

from typing import Dict, List, Optional, Any, AsyncGenerator
import json
from datetime import datetime
from enum import Enum

from app.core.logging_config import logger
from app.modules.agents.base_agent import AgentContext
from app.modules.agents import (
    planner_agent,
    architect_agent,
    coder_agent,
    tester_agent,
    debugger_agent,
    explainer_agent,
    document_generator_agent
)


class WorkflowMode(str, Enum):
    """Workflow execution modes"""
    FULL = "full"  # All agents: Plan → Architect → Code → Test → Document
    CODE_ONLY = "code_only"  # Code → Test
    DEBUG_ONLY = "debug_only"  # Debugger only
    EXPLAIN_ONLY = "explain_only"  # Explainer only
    CUSTOM = "custom"  # User-specified agents


class MultiAgentOrchestrator:
    """
    Multi-Agent Orchestrator

    Responsibilities:
    - Route requests to appropriate agents
    - Manage agent workflow and dependencies
    - Pass context between agents
    - Stream progress events to frontend
    - Handle errors and retry logic
    - Coordinate parallel agent execution where possible
    """

    def __init__(self):
        self.agents = {
            "planner": planner_agent,
            "architect": architect_agent,
            "coder": coder_agent,
            "tester": tester_agent,
            "debugger": debugger_agent,
            "explainer": explainer_agent,
            "document_generator": document_generator_agent
        }

    async def execute_workflow(
        self,
        project_id: str,
        user_request: str,
        mode: WorkflowMode = WorkflowMode.FULL,
        custom_agents: Optional[List[str]] = None,
        context_metadata: Optional[Dict] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute multi-agent workflow

        Args:
            project_id: Project identifier
            user_request: User's request
            mode: Workflow mode (full, code_only, debug_only, etc.)
            custom_agents: List of agent names for custom workflow
            context_metadata: Additional context metadata

        Yields:
            Progress events for each agent step
        """
        try:
            logger.info(f"[Orchestrator] Starting {mode} workflow for project {project_id}")

            # Create base context
            context = AgentContext(
                user_request=user_request,
                project_id=project_id,
                metadata=context_metadata or {}
            )

            # Determine agent execution order based on mode
            agent_sequence = self._get_agent_sequence(mode, custom_agents)

            # Shared state between agents
            workflow_state = {
                "plan": None,
                "architecture": None,
                "code_files": None,
                "test_results": None,
                "documentation": None
            }

            # Execute agents in sequence
            for agent_name in agent_sequence:
                try:
                    # Emit agent start event
                    yield {
                        "type": "agent_start",
                        "agent": agent_name,
                        "status": f"Starting {agent_name}...",
                        "timestamp": datetime.utcnow().isoformat()
                    }

                    # Execute agent
                    result = await self._execute_agent(
                        agent_name,
                        context,
                        workflow_state
                    )

                    # Update workflow state
                    workflow_state = self._update_workflow_state(
                        workflow_state,
                        agent_name,
                        result
                    )

                    # Emit agent completion event
                    yield {
                        "type": "agent_complete",
                        "agent": agent_name,
                        "result": result,
                        "status": f"Completed {agent_name}",
                        "timestamp": datetime.utcnow().isoformat()
                    }

                except Exception as e:
                    logger.error(f"[Orchestrator] Error in {agent_name}: {e}", exc_info=True)

                    # Emit error event
                    yield {
                        "type": "agent_error",
                        "agent": agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }

                    # Decide whether to continue or stop
                    if agent_name in ["planner", "coder"]:
                        # Critical agents - stop workflow
                        raise
                    else:
                        # Non-critical - continue with warning
                        continue

            # Emit workflow completion
            yield {
                "type": "workflow_complete",
                "status": "All agents completed successfully",
                "workflow_state": workflow_state,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Orchestrator] Workflow error: {e}", exc_info=True)
            yield {
                "type": "workflow_error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _get_agent_sequence(
        self,
        mode: WorkflowMode,
        custom_agents: Optional[List[str]] = None
    ) -> List[str]:
        """Determine agent execution order based on mode"""

        sequences = {
            WorkflowMode.FULL: [
                "planner",             # Understand request
                "architect",           # Design system
                "coder",               # Generate code
                "tester",              # Create tests
                "explainer",           # Code documentation
                "document_generator"   # Academic documentation (SRS, SDS, Reports)
            ],
            WorkflowMode.CODE_ONLY: [
                "coder",
                "tester"
            ],
            WorkflowMode.DEBUG_ONLY: [
                "debugger"
            ],
            WorkflowMode.EXPLAIN_ONLY: [
                "explainer"
            ],
            WorkflowMode.CUSTOM: custom_agents or []
        }

        return sequences.get(mode, sequences[WorkflowMode.FULL])

    async def _execute_agent(
        self,
        agent_name: str,
        context: AgentContext,
        workflow_state: Dict
    ) -> Dict:
        """
        Execute a single agent with proper context

        Args:
            agent_name: Name of agent to execute
            context: Base agent context
            workflow_state: Current workflow state

        Returns:
            Agent execution result
        """
        agent = self.agents[agent_name]

        # Prepare agent-specific arguments
        if agent_name == "planner":
            result = await agent.process(context)

        elif agent_name == "architect":
            result = await agent.process(
                context,
                plan=workflow_state.get("plan")
            )

        elif agent_name == "coder":
            result = await agent.process(
                context,
                plan=workflow_state.get("plan"),
                architecture=workflow_state.get("architecture")
            )

        elif agent_name == "tester":
            result = await agent.process(
                context,
                code_files=workflow_state.get("code_files"),
                architecture=workflow_state.get("architecture")
            )

        elif agent_name == "debugger":
            # Debugger needs error context
            error_message = context.metadata.get("error_message", "")
            stack_trace = context.metadata.get("stack_trace")
            result = await agent.process(
                context,
                error_message=error_message,
                stack_trace=stack_trace,
                relevant_files=workflow_state.get("code_files")
            )

        elif agent_name == "explainer":
            result = await agent.process(
                context,
                code_files=workflow_state.get("code_files"),
                architecture=workflow_state.get("architecture")
            )

        elif agent_name == "document_generator":
            result = await agent.process(
                context,
                plan=workflow_state.get("plan"),
                architecture=workflow_state.get("architecture"),
                code_files=workflow_state.get("code_files"),
                test_results=workflow_state.get("test_results")
            )

        else:
            raise ValueError(f"Unknown agent: {agent_name}")

        return result

    def _update_workflow_state(
        self,
        workflow_state: Dict,
        agent_name: str,
        agent_result: Dict
    ) -> Dict:
        """Update workflow state with agent results"""

        if agent_name == "planner":
            workflow_state["plan"] = agent_result.get("plan")

        elif agent_name == "architect":
            workflow_state["architecture"] = agent_result.get("architecture")

        elif agent_name == "coder":
            workflow_state["code_files"] = agent_result.get("files_created")

        elif agent_name == "tester":
            workflow_state["test_results"] = agent_result.get("test_results")

        elif agent_name == "explainer":
            workflow_state["documentation"] = agent_result.get("documentation")

        return workflow_state

    async def debug_error(
        self,
        project_id: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        file_context: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Quick debug workflow - just run debugger agent

        Args:
            project_id: Project identifier
            error_message: Error to debug
            stack_trace: Stack trace if available
            file_context: Relevant files

        Returns:
            Debug result with fixes
        """
        context = AgentContext(
            user_request=f"Debug: {error_message}",
            project_id=project_id,
            metadata={
                "error_message": error_message,
                "stack_trace": stack_trace
            }
        )

        result = await debugger_agent.process(
            context=context,
            error_message=error_message,
            stack_trace=stack_trace,
            relevant_files=file_context
        )

        return result

    async def explain_code(
        self,
        project_id: str,
        code_files: List[Dict],
        specific_request: Optional[str] = None
    ) -> Dict:
        """
        Quick explain workflow - just run explainer agent

        Args:
            project_id: Project identifier
            code_files: Files to explain
            specific_request: Specific explanation request

        Returns:
            Documentation and explanations
        """
        context = AgentContext(
            user_request=specific_request or "Explain this code",
            project_id=project_id
        )

        result = await explainer_agent.process(
            context=context,
            code_files=code_files,
            specific_request=specific_request
        )

        return result

    async def generate_project(
        self,
        project_id: str,
        user_request: str,
        include_tests: bool = True,
        include_docs: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """
        Complete project generation workflow

        This is the main workflow for generating a full project from scratch.

        Args:
            project_id: Project identifier
            user_request: What the user wants to build
            include_tests: Whether to generate tests
            include_docs: Whether to generate documentation

        Yields:
            Progress events
        """
        # Determine agents to run
        agents = ["planner", "architect", "coder"]

        if include_tests:
            agents.append("tester")

        if include_docs:
            agents.append("explainer")

        # Execute workflow
        async for event in self.execute_workflow(
            project_id=project_id,
            user_request=user_request,
            mode=WorkflowMode.CUSTOM,
            custom_agents=agents
        ):
            yield event

    def get_agent_status(self, agent_name: str) -> Dict:
        """Get status information about an agent"""
        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"Agent {agent_name} not found"}

        return {
            "name": agent.name,
            "role": agent.role,
            "capabilities": agent.capabilities,
            "available": True
        }

    def list_agents(self) -> List[Dict]:
        """List all available agents and their capabilities"""
        return [
            {
                "name": name,
                "agent_name": agent.name,
                "role": agent.role,
                "capabilities": agent.capabilities
            }
            for name, agent in self.agents.items()
        ]


# Singleton instance
orchestrator = MultiAgentOrchestrator()
