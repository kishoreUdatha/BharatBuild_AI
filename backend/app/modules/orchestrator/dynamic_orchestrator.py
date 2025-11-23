"""
Central Dynamic Orchestrator (Bolt.new-style)

A flexible, event-driven orchestrator that:
- Routes requests to appropriate agents dynamically
- Supports configurable prompts and models (not hardcoded)
- Implements plan → write → run → fix → docs workflow loop
- Handles file patching and diffs
- Streams events to frontend via SSE

Architecture:
- Agent Registry: Dynamic agent discovery and routing
- Workflow Engine: Configurable multi-step workflows
- Event System: Real-time SSE streaming
- State Management: Track execution context across steps
"""

from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from datetime import datetime
from enum import Enum
import asyncio
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from app.core.logging_config import logger
from app.utils.claude_client import ClaudeClient
from app.modules.automation.file_manager import FileManager
from app.modules.agents.base_agent import AgentContext


class AgentType(str, Enum):
    """Available agent types"""
    PLANNER = "planner"
    WRITER = "writer"
    FIXER = "fixer"
    RUNNER = "runner"
    TESTER = "tester"
    DOCUMENTER = "documenter"
    ENHANCER = "enhancer"
    ANALYZER = "analyzer"


class EventType(str, Enum):
    """SSE Event types for frontend"""
    STATUS = "status"
    THINKING_STEP = "thinking_step"
    PLAN_CREATED = "plan_created"
    FILE_OPERATION = "file_operation"
    FILE_CONTENT = "file_content"
    COMMAND_EXECUTE = "command_execute"
    COMMAND_OUTPUT = "command_output"
    ERROR = "error"
    WARNING = "warning"
    COMPLETE = "complete"
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"


@dataclass
class OrchestratorEvent:
    """Event emitted by orchestrator"""
    type: EventType
    data: Dict[str, Any]
    timestamp: str = None
    agent: Optional[str] = None
    step: Optional[int] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    name: str
    agent_type: AgentType
    system_prompt: Optional[str] = None
    model: str = "sonnet"  # haiku, sonnet, opus
    temperature: float = 0.7
    max_tokens: int = 4096
    capabilities: List[str] = None
    enabled: bool = True

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


@dataclass
class WorkflowStep:
    """A step in the workflow"""
    agent_type: AgentType
    name: str
    description: str = ""
    condition: Optional[Callable] = None  # Optional condition to execute this step
    retry_count: int = 3
    timeout: int = 120  # seconds
    stream_output: bool = False  # Whether to stream output in real-time


@dataclass
class ExecutionContext:
    """Shared context across workflow execution"""
    project_id: str
    user_request: str
    current_step: int = 0
    total_steps: int = 0
    files_created: List[Dict[str, Any]] = None
    files_modified: List[Dict[str, Any]] = None
    commands_executed: List[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    project_type: Optional[str] = None  # Commercial, Academic, Research, Prototype, etc.
    tech_stack: Optional[Dict[str, Any]] = None  # Detected tech stack from Planner

    def __post_init__(self):
        if self.files_created is None:
            self.files_created = []
        if self.files_modified is None:
            self.files_modified = []
        if self.commands_executed is None:
            self.commands_executed = []
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


class AgentRegistry:
    """
    Dynamic agent registry
    Agents can be registered, discovered, and configured at runtime
    Loads configurations from YAML files
    """

    def __init__(self, use_yaml: bool = True):
        """
        Initialize AgentRegistry

        Args:
            use_yaml: If True, load agents from YAML config. If False, use defaults.
        """
        self._agents: Dict[AgentType, AgentConfig] = {}
        self._use_yaml = use_yaml

        if use_yaml:
            self._load_from_yaml()
        else:
            self._load_default_agents()

    def _load_from_yaml(self):
        """Load agent configurations from YAML file"""
        try:
            from app.config.config_loader import get_config_loader

            config_loader = get_config_loader()
            self._agents = config_loader.load_agents()
            logger.info(f"Loaded {len(self._agents)} agents from YAML config")

        except Exception as e:
            logger.error(f"Failed to load agents from YAML: {e}")
            logger.warning("Falling back to default agent configurations")
            self._load_default_agents()

    def _load_default_agents(self):
        """Load default agent configurations (fallback)"""
        default_agents = [
            AgentConfig(
                name="Planner Agent",
                agent_type=AgentType.PLANNER,
                model="sonnet",
                temperature=0.7,
                max_tokens=4096,
                capabilities=["planning", "architecture_design", "task_breakdown"]
            ),
            AgentConfig(
                name="Writer Agent",
                agent_type=AgentType.WRITER,
                model="sonnet",
                temperature=0.3,
                max_tokens=8192,
                capabilities=["code_generation", "file_creation"]
            ),
            AgentConfig(
                name="Fixer Agent",
                agent_type=AgentType.FIXER,
                model="sonnet",
                temperature=0.5,
                max_tokens=4096,
                capabilities=["debugging", "error_fixing", "code_modification"]
            ),
            AgentConfig(
                name="Runner Agent",
                agent_type=AgentType.RUNNER,
                model="haiku",
                temperature=0.1,
                max_tokens=2048,
                capabilities=["command_execution", "testing"]
            ),
            AgentConfig(
                name="Tester Agent",
                agent_type=AgentType.TESTER,
                model="haiku",
                temperature=0.5,
                max_tokens=4096,
                capabilities=["test_generation", "quality_assurance"]
            ),
            AgentConfig(
                name="Documenter Agent",
                agent_type=AgentType.DOCUMENTER,
                model="haiku",
                temperature=0.5,
                max_tokens=4096,
                capabilities=["documentation", "readme_generation", "api_docs"]
            ),
        ]

        for agent_config in default_agents:
            self._agents[agent_config.agent_type] = agent_config

    def register_agent(self, config: AgentConfig):
        """Register or update an agent configuration"""
        self._agents[config.agent_type] = config
        logger.info(f"Registered agent: {config.name} ({config.agent_type})")

    def get_agent(self, agent_type: AgentType) -> Optional[AgentConfig]:
        """Get agent configuration"""
        return self._agents.get(agent_type)

    def update_agent_prompt(self, agent_type: AgentType, system_prompt: str):
        """Dynamically update agent's system prompt"""
        if agent_type in self._agents:
            self._agents[agent_type].system_prompt = system_prompt
            logger.info(f"Updated prompt for {agent_type}")

    def update_agent_model(self, agent_type: AgentType, model: str):
        """Dynamically update agent's model"""
        if agent_type in self._agents:
            self._agents[agent_type].model = model
            logger.info(f"Updated model for {agent_type} to {model}")

    def list_agents(self) -> Dict[AgentType, AgentConfig]:
        """List all registered agents"""
        return self._agents


class WorkflowEngine:
    """
    Configurable workflow engine
    Supports different workflow patterns (not hardcoded)
    """

    def __init__(self):
        self._workflows: Dict[str, List[WorkflowStep]] = {}
        self._load_default_workflows()

    def _load_default_workflows(self):
        """Load default workflow patterns"""

        # Bolt.new standard workflow with run → fix → run loop
        self._workflows["bolt_standard"] = [
            WorkflowStep(
                agent_type=AgentType.PLANNER,
                name="Create Plan",
                description="Analyze request and create implementation plan",
                timeout=120,
                retry_count=2
            ),
            WorkflowStep(
                agent_type=AgentType.WRITER,
                name="Generate Code",
                description="Write code based on plan",
                timeout=300,
                retry_count=2,
                stream_output=True
            ),
            WorkflowStep(
                agent_type=AgentType.RUNNER,
                name="Execute & Test (Initial)",
                description="Run code and check for errors",
                timeout=180,
                retry_count=1,
                stream_output=True,
                condition=lambda ctx: len(ctx.files_created) > 0
            ),
            WorkflowStep(
                agent_type=AgentType.FIXER,
                name="Fix Errors",
                description="Fix any errors found during execution",
                timeout=300,
                retry_count=2,
                stream_output=True,
                condition=lambda ctx: len(ctx.errors) > 0
            ),
            WorkflowStep(
                agent_type=AgentType.RUNNER,
                name="Execute & Test (After Fix)",
                description="Re-run code after fixes to verify",
                timeout=180,
                retry_count=1,
                stream_output=True,
                # Only run if we just fixed errors
                condition=lambda ctx: len(ctx.files_modified) > 0 and any(f.get("operation") == "fix" for f in ctx.files_modified)
            ),
            WorkflowStep(
                agent_type=AgentType.DOCUMENTER,
                name="Generate Academic Docs",
                description="Create SRS, UML, Reports (for academic projects only)",
                timeout=240,
                retry_count=1,
                # Only run for academic projects
                condition=lambda ctx: ctx.project_type == "Academic"
            ),
        ]

        # Quick iteration workflow (no docs)
        self._workflows["quick_iteration"] = [
            WorkflowStep(
                agent_type=AgentType.PLANNER,
                name="Quick Plan",
                description="Create simple plan"
            ),
            WorkflowStep(
                agent_type=AgentType.WRITER,
                name="Generate Code",
                description="Write code"
            ),
            WorkflowStep(
                agent_type=AgentType.RUNNER,
                name="Test",
                description="Quick test"
            ),
        ]

        # Debug workflow (fix existing code)
        self._workflows["debug"] = [
            WorkflowStep(
                agent_type=AgentType.ANALYZER,
                name="Analyze Error",
                description="Understand the error"
            ),
            WorkflowStep(
                agent_type=AgentType.FIXER,
                name="Fix Code",
                description="Apply fixes"
            ),
            WorkflowStep(
                agent_type=AgentType.RUNNER,
                name="Verify Fix",
                description="Test the fix"
            ),
        ]

    def register_workflow(self, name: str, steps: List[WorkflowStep]):
        """Register custom workflow"""
        self._workflows[name] = steps
        logger.info(f"Registered workflow: {name} with {len(steps)} steps")

    def get_workflow(self, name: str) -> List[WorkflowStep]:
        """Get workflow by name"""
        return self._workflows.get(name, self._workflows["bolt_standard"])

    def list_workflows(self) -> List[str]:
        """List available workflows"""
        return list(self._workflows.keys())


class DynamicOrchestrator:
    """
    Central Dynamic Orchestrator

    Features:
    - Multi-agent routing based on registry
    - Dynamic prompts and models (configurable)
    - Flexible workflow patterns
    - File patching support
    - Real-time event streaming
    - State management across steps
    """

    def __init__(self, project_root: str = "./user_projects"):
        self.agent_registry = AgentRegistry()
        self.workflow_engine = WorkflowEngine()
        self.claude_client = ClaudeClient()
        self.file_manager = FileManager(project_root)
        self._event_queue: asyncio.Queue = None

    async def execute_workflow(
        self,
        user_request: str,
        project_id: str,
        workflow_name: str = "bolt_standard",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute a workflow with real-time event streaming

        Args:
            user_request: User's request
            project_id: Project identifier
            workflow_name: Which workflow to execute
            metadata: Additional context

        Yields:
            OrchestratorEvent: Real-time events for SSE streaming
        """
        # Initialize execution context
        context = ExecutionContext(
            project_id=project_id,
            user_request=user_request,
            metadata=metadata or {}
        )

        # Get workflow steps
        workflow = self.workflow_engine.get_workflow(workflow_name)
        context.total_steps = len(workflow)

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={
                "message": f"Starting {workflow_name} workflow",
                "total_steps": context.total_steps
            }
        )

        try:
            # Execute each step in workflow
            for step_index, step in enumerate(workflow, 1):
                context.current_step = step_index

                # Check step condition (if any)
                if step.condition and not step.condition(context):
                    logger.info(f"Skipping step {step_index}: {step.name} (condition not met)")
                    yield OrchestratorEvent(
                        type=EventType.STATUS,
                        data={"message": f"Skipping {step.name} (not needed)"},
                        step=step_index
                    )
                    continue

                # Execute step with retries
                step_result = None
                for attempt in range(step.retry_count):
                    try:
                        yield OrchestratorEvent(
                            type=EventType.AGENT_START,
                            data={
                                "agent": step.agent_type,
                                "name": step.name,
                                "description": step.description,
                                "attempt": attempt + 1
                            },
                            agent=step.agent_type,
                            step=step_index
                        )

                        # Execute agent
                        async for event in self._execute_agent(step.agent_type, context):
                            event.step = step_index
                            event.agent = step.agent_type
                            yield event

                        yield OrchestratorEvent(
                            type=EventType.AGENT_COMPLETE,
                            data={
                                "agent": step.agent_type,
                                "name": step.name,
                                "success": True
                            },
                            agent=step.agent_type,
                            step=step_index
                        )

                        break  # Success, exit retry loop

                    except Exception as e:
                        logger.error(f"Step {step_index} attempt {attempt + 1} failed: {e}")

                        if attempt == step.retry_count - 1:
                            # Final attempt failed
                            context.errors.append({
                                "step": step_index,
                                "agent": step.agent_type,
                                "error": str(e)
                            })
                            yield OrchestratorEvent(
                                type=EventType.ERROR,
                                data={
                                    "message": f"Step {step.name} failed after {step.retry_count} attempts",
                                    "error": str(e)
                                },
                                agent=step.agent_type,
                                step=step_index
                            )
                        else:
                            # Retry
                            yield OrchestratorEvent(
                                type=EventType.WARNING,
                                data={
                                    "message": f"Retrying {step.name}...",
                                    "attempt": attempt + 2
                                },
                                step=step_index
                            )
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff

            # Workflow complete
            yield OrchestratorEvent(
                type=EventType.COMPLETE,
                data={
                    "message": "Workflow completed successfully",
                    "files_created": len(context.files_created),
                    "files_modified": len(context.files_modified),
                    "commands_executed": len(context.commands_executed),
                    "errors": len(context.errors)
                }
            )

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            yield OrchestratorEvent(
                type=EventType.ERROR,
                data={"message": "Workflow failed", "error": str(e)}
            )

    async def _execute_agent(
        self,
        agent_type: AgentType,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute a specific agent

        Args:
            agent_type: Which agent to execute
            context: Current execution context

        Yields:
            OrchestratorEvent: Events from agent execution
        """
        # Get agent configuration
        agent_config = self.agent_registry.get_agent(agent_type)

        if not agent_config or not agent_config.enabled:
            raise Exception(f"Agent {agent_type} not found or disabled")

        yield OrchestratorEvent(
            type=EventType.THINKING_STEP,
            data={
                "step": f"Calling {agent_config.name}",
                "status": "active"
            }
        )

        # Route to appropriate handler
        if agent_type == AgentType.PLANNER:
            async for event in self._execute_planner(agent_config, context):
                yield event
        elif agent_type == AgentType.WRITER:
            async for event in self._execute_writer(agent_config, context):
                yield event
        elif agent_type == AgentType.FIXER:
            async for event in self._execute_fixer(agent_config, context):
                yield event
        elif agent_type == AgentType.RUNNER:
            async for event in self._execute_runner(agent_config, context):
                yield event
        elif agent_type == AgentType.DOCUMENTER:
            async for event in self._execute_documenter(agent_config, context):
                yield event
        else:
            raise Exception(f"No handler for agent type: {agent_type}")

    async def _execute_planner(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """Execute planner agent"""

        # Build dynamic prompt
        system_prompt = config.system_prompt or self._get_default_planner_prompt()

        user_prompt = f"""
USER REQUEST:
{context.user_request}

PROJECT CONTEXT:
- Project ID: {context.project_id}
- Existing Files: {len(context.files_created)} files
- Previous Steps: {context.current_step - 1} completed

Create a detailed implementation plan with steps, tasks, and deliverables.
Output in <plan> XML tags.
"""

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Planning project structure..."}
        )

        # Call Claude
        response = await self.claude_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

        # Parse plan from response
        plan_text = response.get('content', '')

        # Extract plan (simplified - in production, use proper XML parsing)
        context.plan = {"raw": plan_text}

        # Extract project_type from plan
        project_type_match = re.search(r'<project_type>(.*?)</project_type>', plan_text, re.DOTALL)
        if project_type_match:
            project_type_text = project_type_match.group(1)
            # Detect project type
            if "Academic" in project_type_text or "Student" in project_type_text:
                context.project_type = "Academic"
            elif "Commercial" in project_type_text:
                context.project_type = "Commercial"
            elif "Research" in project_type_text:
                context.project_type = "Research"
            elif "Prototype" in project_type_text or "MVP" in project_type_text:
                context.project_type = "Prototype"
            else:
                context.project_type = "General"

            logger.info(f"Detected project type: {context.project_type}")

        # Extract tech_stack from plan
        tech_stack_match = re.search(r'<tech_stack>(.*?)</tech_stack>', plan_text, re.DOTALL)
        if tech_stack_match:
            context.tech_stack = {"raw": tech_stack_match.group(1)}

        yield OrchestratorEvent(
            type=EventType.PLAN_CREATED,
            data={
                "plan": context.plan,
                "project_type": context.project_type,
                "tech_stack": context.tech_stack
            }
        )

    async def _execute_writer(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """Execute writer agent with file streaming"""

        system_prompt = config.system_prompt or self._get_default_writer_prompt()

        user_prompt = f"""
TASK:
{context.user_request}

PLAN:
{context.plan.get('raw', 'No plan available') if context.plan else 'No plan available'}

Generate files using <file path="...">CONTENT</file> tags.
Stream code in chunks for real-time display.
"""

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Generating code..."}
        )

        # Stream response
        full_response = ""
        current_file_path = None
        import re

        async for chunk in self.claude_client.generate_stream(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        ):
            full_response += chunk

            # Detect file start
            if '<file path="' in chunk:
                match = re.search(r'<file path="([^"]+)">', chunk)
                if match:
                    current_file_path = match.group(1)

                    yield OrchestratorEvent(
                        type=EventType.FILE_OPERATION,
                        data={
                            "operation": "create",
                            "path": current_file_path,
                            "status": "in_progress"
                        }
                    )

            # Detect file end
            if '</file>' in chunk:
                current_file_path = None

            # Stream file content with path
            if current_file_path:
                yield OrchestratorEvent(
                    type=EventType.FILE_CONTENT,
                    data={
                        "path": current_file_path,
                        "content": chunk
                    }
                )

        # Parse and save files
        files = self._extract_files_from_response(full_response)

        for file_info in files:
            # Save file
            await self.file_manager.create_file(
                project_id=context.project_id,
                file_path=file_info['path'],
                content=file_info['content']
            )

            context.files_created.append(file_info)

            yield OrchestratorEvent(
                type=EventType.FILE_OPERATION,
                data={
                    "operation": "create",
                    "path": file_info['path'],
                    "status": "complete",
                    "file_content": file_info['content']
                }
            )

    async def _execute_fixer(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute fixer agent - apply patches for errors
        """
        from app.modules.agents.fixer_agent import FixerAgent
        from app.utils.response_parser import PlainTextParser

        if not context.errors:
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "No errors to fix"}
            )
            return

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": f"Fixing {len(context.errors)} error(s)..."}
        )

        # Initialize fixer
        fixer = FixerAgent(model=config.model)
        file_manager = FileManager()

        # Process each error
        for error_idx, error in enumerate(context.errors, 1):
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": f"Fixing error {error_idx}/{len(context.errors)}: {error.get('message', 'Unknown error')}"}
            )

            # Build context for fixer
            agent_context = AgentContext(
                user_request=f"Fix error: {error.get('message')}",
                project_id=context.project_id,
                metadata={
                    "error": error,
                    "files": [f["path"] for f in context.files_created],
                    "project_type": context.project_type
                }
            )

            # Call fixer to generate fix
            fix_result = await fixer.fix_error(
                error=error,
                project_id=context.project_id,
                file_context={
                    "files_created": context.files_created,
                    "tech_stack": context.tech_stack
                }
            )

            # Parse fixed files
            parsed = PlainTextParser.parse_bolt_response(fix_result.get("response", ""))

            # Apply fixes
            if "files" in parsed:
                for file_info in parsed["files"]:
                    file_path = file_info.get("path")
                    file_content = file_info.get("content")

                    if file_path and file_content:
                        # Update file
                        await file_manager.update_file(
                            project_id=context.project_id,
                            file_path=file_path,
                            content=file_content
                        )

                        yield OrchestratorEvent(
                            type=EventType.FILE_OPERATION,
                            data={
                                "path": file_path,
                                "operation": "fixed",
                                "status": "complete"
                            }
                        )

                        # Track modification
                        context.files_modified.append({
                            "path": file_path,
                            "operation": "fix",
                            "error": error.get("message")
                        })

            # Handle additional instructions (e.g., install missing deps)
            if "instructions" in parsed:
                for instruction in parsed.get("instructions", []):
                    yield OrchestratorEvent(
                        type=EventType.COMMAND_EXECUTE,
                        data={"command": instruction}
                    )

        # Clear errors after fixing
        fixed_count = len(context.errors)
        context.errors = []

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": f"Fixed {fixed_count} error(s) successfully"}
        )

    async def _execute_runner(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute runner agent - install dependencies and run preview/build
        """
        from app.modules.agents.runner_agent import RunnerAgent

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Executing install and build commands..."}
        )

        # Initialize runner
        runner = RunnerAgent(model=config.model)

        # Auto-detect commands from files created
        commands = self._detect_commands(context)

        if not commands:
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "No commands detected, skipping runner"}
            )
            return

        # Execute each command
        for command in commands:
            yield OrchestratorEvent(
                type=EventType.COMMAND_EXECUTE,
                data={"command": command}
            )

            # Build project context for runner
            project_context = {
                "tech_stack": context.tech_stack or {},
                "files": [f["path"] for f in context.files_created],
                "working_directory": f"./projects/{context.project_id}",
                "project_type": context.project_type
            }

            # Execute command using process method
            agent_context = AgentContext(
                user_request=command,
                project_id=context.project_id,
                metadata={
                    "project_context": project_context,
                    "execution_mode": "simulate"  # Use simulate for safety
                }
            )

            result = await runner.process(agent_context)

            # Stream output
            yield OrchestratorEvent(
                type=EventType.COMMAND_OUTPUT,
                data={
                    "command": command,
                    "output": result.get("terminal_output", ""),
                    "success": result.get("success", True)
                }
            )

            # Detect errors
            if result.get("has_errors") or not result.get("success"):
                # Parse errors from terminal output
                errors = self._parse_errors_from_output(
                    terminal_output=result.get("terminal_output", ""),
                    command=command
                )

                if errors:
                    context.errors.extend(errors)

                    yield OrchestratorEvent(
                        type=EventType.ERROR,
                        data={
                            "message": f"Command '{command}' failed",
                            "errors": errors
                        }
                    )

            # Detect preview URL
            preview_url = self._detect_preview_url(result.get("terminal_output", ""))
            if preview_url:
                yield OrchestratorEvent(
                    type=EventType.STATUS,
                    data={"message": f"Preview ready at {preview_url}", "preview_url": preview_url}
                )

            # Track command execution
            context.commands_executed.append({
                "command": command,
                "success": result.get("success", True),
                "output": result.get("terminal_output", "")
            })

    def _detect_commands(self, context: ExecutionContext) -> List[str]:
        """
        Auto-detect commands based on files created and tech stack
        """
        commands = []
        file_paths = [f["path"] for f in context.files_created]

        # Frontend (JavaScript/TypeScript)
        if any("package.json" in path for path in file_paths):
            commands.append("npm install")
            # Detect if it's a dev server project
            if any(path.endswith((".tsx", ".jsx")) for path in file_paths):
                # Check for common dev commands
                commands.append("npm run dev")  # Vite, Next.js, etc.

        # Backend (Python)
        if any("requirements.txt" in path for path in file_paths):
            commands.append("pip install -r requirements.txt")
            # Detect framework
            if any("main.py" in path or "app.py" in path for path in file_paths):
                # FastAPI/Flask
                commands.append("uvicorn app.main:app --reload --port 8000")

        # Full-stack (both frontend and backend)
        # Already handled by individual detection above

        return commands

    def _parse_errors_from_output(self, terminal_output: str, command: str) -> List[Dict[str, Any]]:
        """
        Parse errors from terminal output
        """
        errors = []

        # Common error patterns
        error_patterns = [
            r"Error: (.+)",
            r"ERROR: (.+)",
            r"TypeError: (.+)",
            r"ModuleNotFoundError: (.+)",
            r"SyntaxError: (.+)",
            r"Failed to compile",
            r"Command failed with exit code (\d+)"
        ]

        for pattern in error_patterns:
            matches = re.findall(pattern, terminal_output, re.MULTILINE)
            for match in matches:
                # Try to extract file path and line number
                file_match = re.search(r'File "([^"]+)", line (\d+)', terminal_output)
                file_path = file_match.group(1) if file_match else "unknown"
                line_number = int(file_match.group(2)) if file_match else 0

                errors.append({
                    "type": "runtime_error",
                    "message": match if isinstance(match, str) else match,
                    "file": file_path,
                    "line": line_number,
                    "command": command
                })

        return errors

    def _detect_preview_url(self, terminal_output: str) -> Optional[str]:
        """
        Detect preview URL from terminal output
        """
        # Common patterns for preview URLs
        url_patterns = [
            r"http://localhost:(\d+)",
            r"http://127\.0\.0\.1:(\d+)",
            r"https?://[^\s]+",
            r"Local:\s+(https?://[^\s]+)",
            r"ready at (https?://[^\s]+)"
        ]

        for pattern in url_patterns:
            match = re.search(pattern, terminal_output, re.IGNORECASE)
            if match:
                if match.groups():
                    # If port number matched
                    port = match.group(1)
                    return f"http://localhost:{port}"
                else:
                    # Full URL matched
                    return match.group(0)

        return None

    async def _execute_documenter(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute documenter agent (DocsPack) - Generate academic documentation
        """
        from app.modules.agents.docspack_agent import DocsPackAgent
        from app.utils.response_parser import PlainTextParser

        # Only run for academic projects
        if context.project_type != "Academic":
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "Skipping documentation (not an academic project)"}
            )
            return

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Generating academic documentation (SRS, UML, Reports)..."}
        )

        # Initialize DocsPack agent
        docspack = DocsPackAgent(model=config.model)

        # Build context for documentation
        agent_context = AgentContext(
            user_request=context.user_request,
            project_id=context.project_id,
            metadata={
                "plan": context.plan,
                "files_created": context.files_created,
                "tech_stack": context.tech_stack,
                "project_type": context.project_type
            }
        )

        # Generate all academic documents
        docs_result = await docspack.generate_all_documents(
            plan=context.plan.get("raw", "") if context.plan else "",
            project_id=context.project_id,
            files=context.files_created
        )

        # Parse generated documents
        parsed = PlainTextParser.parse_bolt_response(docs_result.get("response", ""))

        # Save each document
        if "files" in parsed:
            for doc_info in parsed["files"]:
                doc_path = doc_info.get("path")
                doc_content = doc_info.get("content")

                if doc_path and doc_content:
                    # Create document file
                    await self.file_manager.create_file(
                        project_id=context.project_id,
                        file_path=doc_path,
                        content=doc_content
                    )

                    yield OrchestratorEvent(
                        type=EventType.FILE_OPERATION,
                        data={
                            "path": doc_path,
                            "operation": "documentation",
                            "status": "complete"
                        }
                    )

                    context.files_created.append({
                        "path": doc_path,
                        "type": "documentation",
                        "content": doc_content
                    })

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Academic documentation generated successfully"}
        )

    def _extract_files_from_response(self, response: str) -> List[Dict[str, str]]:
        """Extract files from <file> tags"""
        import re

        files = []
        pattern = r'<file path="([^"]+)">(.*?)</file>'

        matches = re.findall(pattern, response, re.DOTALL)

        for path, content in matches:
            files.append({
                "path": path.strip(),
                "content": content.strip()
            })

        return files

    # Default prompts (can be overridden dynamically)
    def _get_default_planner_prompt(self) -> str:
        return """You are a Project Planner Agent.
Analyze user requests and create detailed implementation plans.
Output plans in <plan> XML tags with steps, tasks, and deliverables."""

    def _get_default_writer_prompt(self) -> str:
        return """You are a Code Writer Agent.
Generate clean, production-ready code based on plans.
Output files using <file path="...">CODE</file> tags."""

    def _get_default_fixer_prompt(self) -> str:
        return """You are an Error Fixer Agent.
Analyze errors and fix code issues.
Output patches or full file replacements."""

    def _get_default_documenter_prompt(self) -> str:
        return """You are a Documentation Agent.
Generate comprehensive documentation including README, API docs, and guides."""


# Singleton instance
dynamic_orchestrator = DynamicOrchestrator()
