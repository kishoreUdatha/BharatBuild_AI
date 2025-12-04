"""
FastAPI endpoints for Dynamic Orchestrator (Bolt.new-style)

This module provides REST API endpoints for:
- Executing workflows with SSE streaming
- Managing agents (update prompts/models dynamically)
- Managing workflows (list, create, update)
- Real-time event streaming to frontend
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import json
import logging
import uuid

from app.modules.orchestrator.dynamic_orchestrator import (
    DynamicOrchestrator,
    AgentType,
    AgentConfig,
    WorkflowStep,
    OrchestratorEvent
)
from app.core.database import get_db
from app.models.project import Project, ProjectStatus, ProjectMode
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.services.sandbox_cleanup import touch_project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

# Global orchestrator instance
orchestrator = DynamicOrchestrator()

# Optional security for SSE endpoints (auth is optional but recommended)
optional_security = HTTPBearer(auto_error=False)


# ==================== Helper Functions ====================

async def get_or_create_project(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    title: str = None
) -> Project:
    """
    Get existing project or create a new one.

    - If project_id is a valid UUID and exists, validate ownership
    - If project_id is a timestamp format (project-XXX), create new project
    - Returns the Project record
    """
    # Check if project_id looks like a UUID
    try:
        uuid.UUID(project_id)
        is_uuid = True
    except ValueError:
        is_uuid = False

    if is_uuid:
        # Try to find existing project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        existing_project = result.scalar_one_or_none()

        if existing_project:
            # Validate ownership
            if str(existing_project.user_id) != str(user_id):
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this project"
                )
            return existing_project

    # Create new project with the given project_id as title reference
    new_project = Project(
        user_id=user_id,
        title=title or f"Project {project_id}",
        description=f"Auto-created project from orchestrator",
        mode=ProjectMode.DEVELOPER,
        status=ProjectStatus.IN_PROGRESS
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    logger.info(f"Created new project {new_project.id} for user {user_id}")
    return new_project


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: AsyncSession
) -> Optional[User]:
    """Get user from token if provided, otherwise return None"""
    # DETAILED LOGGING FOR DEBUG
    logger.info(f"[Auth Debug] get_optional_user called, credentials={credentials is not None}")

    if not credentials:
        logger.warning("[Auth Debug] No credentials provided - user will be anonymous")
        return None

    try:
        from app.core.security import decode_token
        token = credentials.credentials
        logger.info(f"[Auth Debug] Token received (first 20 chars): {token[:20] if token else 'None'}...")

        payload = decode_token(token)
        logger.info(f"[Auth Debug] Token decoded, payload keys: {list(payload.keys()) if payload else 'None'}")

        if payload.get("type") != "access":
            logger.warning(f"[Auth Debug] Invalid token type: {payload.get('type')}")
            return None

        user_id = payload.get("sub")
        logger.info(f"[Auth Debug] User ID from token: {user_id}")

        if not user_id:
            logger.warning("[Auth Debug] No user_id in token payload")
            return None

        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        logger.info(f"[Auth Debug] User lookup result: {user.email if user else 'None'}")

        if user and user.is_active:
            logger.info(f"[Auth Debug] SUCCESS - User authenticated: {user.id} ({user.email})")
            return user

        logger.warning(f"[Auth Debug] User not found or inactive")
        return None
    except Exception as e:
        logger.error(f"[Auth Debug] EXCEPTION in get_optional_user: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[Auth Debug] Traceback: {traceback.format_exc()}")
        return None


# ==================== Pydantic Models ====================

class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow"""
    user_request: str = Field(..., description="User's request for code generation")
    project_id: str = Field(..., description="Project ID to work on")
    workflow_name: str = Field(default="bolt_standard", description="Workflow to execute")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class AgentUpdatePromptRequest(BaseModel):
    """Request to update agent's system prompt"""
    system_prompt: str = Field(..., description="New system prompt for the agent")


class AgentUpdateModelRequest(BaseModel):
    """Request to update agent's model"""
    model: str = Field(..., description="Model name (haiku, sonnet, opus)")


class WorkflowCreateRequest(BaseModel):
    """Request to create a custom workflow"""
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    steps: List[Dict[str, Any]] = Field(..., description="List of workflow steps")


class AgentConfigResponse(BaseModel):
    """Response containing agent configuration"""
    name: str
    agent_type: str
    model: str
    temperature: float
    max_tokens: int
    capabilities: List[str]
    enabled: bool
    has_custom_prompt: bool


class WorkflowResponse(BaseModel):
    """Response containing workflow details"""
    name: str
    steps: List[Dict[str, Any]]


# ==================== SSE Event Streaming ====================

async def event_generator(
    user_request: str,
    project_id: str,
    workflow_name: str,
    metadata: Optional[Dict[str, Any]]
):
    """
    Generator for Server-Sent Events (SSE) streaming.

    Yields events in SSE format:
    data: {"type": "status", "message": "Starting workflow..."}

    IMPORTANT: Each yield MUST be followed by an await to allow the event loop
    to flush the data to the client. Without this, events get buffered.
    """
    try:
        logger.info("[SSE Generator] Starting event generator...")

        # Send initial connection event to ensure stream is open
        initial_event = {
            "type": "connected",
            "data": {"message": "Stream connected"},
            "step": None,
            "agent": None,
            "timestamp": None
        }
        logger.info("[SSE Generator] Sending initial connected event")
        yield f"data: {json.dumps(initial_event)}\n\n"
        # CRITICAL: Allow event loop to flush
        await asyncio.sleep(0)

        logger.info("[SSE Generator] Starting workflow execution...")

        # Execute workflow and stream events
        async for event in orchestrator.execute_workflow(
            user_request=user_request,
            project_id=project_id,
            workflow_name=workflow_name,
            metadata=metadata
        ):
            # Log all events for debugging
            event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
            logger.info(f"[SSE Generator] Yielding event: {event_type}")

            # Log plan_created events for debugging
            if event_type == "plan_created":
                logger.info(f"[SSE] Sending plan_created event to client with {len(event.data.get('tasks', []))} tasks")

            # Convert OrchestratorEvent to SSE format
            # Use event.type.value to ensure enum is serialized as string
            event_data = {
                "type": event_type,
                "data": event.data,
                "step": event.step,
                "agent": event.agent,
                "timestamp": event.timestamp
            }

            # SSE format: "data: {json}\n\n"
            event_message = f"data: {json.dumps(event_data)}\n\n"
            yield event_message

            # CRITICAL: Allow event loop to flush after each yield
            # This ensures the event is sent to the client immediately
            await asyncio.sleep(0.01)

            # Log after yielding for plan_created
            if event_type == "plan_created":
                logger.info(f"[SSE] plan_created event sent to client")

    except Exception as e:
        logger.error(f"Error in event streaming: {e}", exc_info=True)
        error_event = {
            "type": "error",
            "data": {"error": str(e)},
            "step": None,
            "agent": None,
            "timestamp": None
        }
        yield f"data: {json.dumps(error_event)}\n\n"
        await asyncio.sleep(0)

    finally:
        # Send completion event
        logger.info("[SSE Generator] Sending completion event")
        complete_event = {
            "type": "complete",
            "data": {"status": "finished"},
            "step": None,
            "agent": None,
            "timestamp": None
        }
        yield f"data: {json.dumps(complete_event)}\n\n"
        await asyncio.sleep(0)


# ==================== Workflow Execution Endpoints ====================

@router.post("/execute")
async def execute_workflow(
    request: WorkflowExecuteRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a workflow with real-time SSE streaming.

    This endpoint returns a Server-Sent Events (SSE) stream that sends
    real-time updates as the workflow executes.

    **Authentication:** Optional but recommended. If authenticated:
    - Projects are linked to the user
    - Project ownership is validated
    - Database records are created

    **Event Types:**
    - `status`: Workflow status updates
    - `thinking_step`: AI thinking progress
    - `plan_created`: Plan generation complete
    - `file_operation`: File creation/modification started
    - `file_content`: File content chunk (streaming)
    - `file_complete`: File completed
    - `command_execute`: Command execution
    - `error`: Error occurred
    - `complete`: Workflow finished

    **Example Usage (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/api/v1/orchestrator/execute', {
        method: 'POST',
        body: JSON.stringify({
            user_request: "Build a todo app",
            project_id: "my-project",
            workflow_name: "bolt_standard"
        })
    });

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.type, data.message);
    };
    ```
    """
    try:
        logger.info(f"[Execute Workflow] Starting workflow: {request.workflow_name} for project: {request.project_id}")

        # Get user if authenticated
        current_user = await get_optional_user(credentials, db)

        # Determine the actual project_id to use for file storage
        actual_project_id = request.project_id
        db_project = None

        if current_user:
            # User is authenticated - create/validate project in database
            logger.info(f"[Execute Workflow] Authenticated user: {current_user.email}")

            # Get or create project record
            db_project = await get_or_create_project(
                db=db,
                project_id=request.project_id,
                user_id=str(current_user.id),
                title=request.metadata.get("project_name") if request.metadata else None
            )

            # Use the database project ID for file storage (consistent UUID)
            actual_project_id = str(db_project.id)
            logger.info(f"[Execute Workflow] Using database project ID: {actual_project_id}")

            # Update project status
            db_project.status = ProjectStatus.PROCESSING
            await db.commit()
        else:
            # Anonymous user - use the provided project_id as-is
            logger.info(f"[Execute Workflow] Anonymous user, using provided project_id: {actual_project_id}")

        # Add user context to metadata
        enhanced_metadata = request.metadata or {}
        if current_user:
            enhanced_metadata["user_id"] = str(current_user.id)
            enhanced_metadata["user_email"] = current_user.email
            enhanced_metadata["db_project_id"] = actual_project_id
            # Add user_role for academic project detection
            # If user role is "student" or "faculty", project will be treated as academic
            enhanced_metadata["user_role"] = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
            logger.info(f"[Execute Workflow] User role: {enhanced_metadata['user_role']}")
            logger.info(f"[Execute Workflow] Added user_id={enhanced_metadata['user_id']} to metadata")
        else:
            logger.warning(f"[Execute Workflow] No authenticated user - sandbox will NOT have user-scoped path!")

        # Create a wrapper that yields bytes to ensure proper streaming
        async def byte_generator():
            try:
                # Touch the project to reset its idle timer (keep alive during activity)
                touch_project(actual_project_id)
                logger.info(f"[Execute Workflow] Touched project {actual_project_id} to keep alive")

                # CRITICAL: Send project_id_updated event FIRST so frontend knows the actual DB project ID
                # This fixes the bug where frontend uses 'default-project' but files are saved to DB UUID
                if actual_project_id != request.project_id:
                    project_id_event = {
                        "type": "project_id_updated",
                        "data": {
                            "project_id": actual_project_id,
                            "original_project_id": request.project_id,
                            "message": "Project ID updated to database UUID"
                        },
                        "step": None,
                        "agent": None,
                        "timestamp": None
                    }
                    yield f"data: {json.dumps(project_id_event)}\n\n".encode('utf-8')
                    logger.info(f"[Execute Workflow] Sent project_id_updated event: {request.project_id} -> {actual_project_id}")

                async for event in event_generator(
                    user_request=request.user_request,
                    project_id=actual_project_id,
                    workflow_name=request.workflow_name,
                    metadata=enhanced_metadata
                ):
                    # Encode to bytes for proper streaming
                    yield event.encode('utf-8')

                # Update project status on completion if authenticated
                if db_project:
                    try:
                        db_project.status = ProjectStatus.COMPLETED
                        await db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to update project status: {e}")

            except Exception as e:
                logger.error(f"Error in workflow execution: {e}")
                # Update project status on failure
                if db_project:
                    try:
                        db_project.status = ProjectStatus.FAILED
                        await db.commit()
                    except Exception:
                        pass
                raise

        return StreamingResponse(
            byte_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start workflow execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Workflow Management Endpoints ====================

@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows():
    """
    List all available workflows.

    Returns workflows with their steps and configurations.

    **Default Workflows:**
    - `bolt_standard`: plan → write → run → fix → docs
    - `quick_iteration`: plan → write → test
    - `debug`: analyze → fix → verify
    """
    try:
        workflow_names = orchestrator.workflow_engine.list_workflows()

        response = []
        for name in workflow_names:
            try:
                steps = orchestrator.workflow_engine.get_workflow(name)
                workflow_data = {
                    "name": name,
                    "steps": [
                        {
                            "agent_type": step.agent_type.value,
                            "name": step.name,
                            "timeout": step.timeout,
                            "retry_count": step.retry_count,
                            "stream_output": step.stream_output
                        }
                        for step in steps
                    ]
                }
                response.append(workflow_data)
            except Exception as e:
                logger.warning(f"Failed to get workflow '{name}': {e}")
                continue

        return response
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows", response_model=Dict[str, str])
async def create_workflow(request: WorkflowCreateRequest):
    """
    Create a custom workflow.

    **Request Example:**
    ```json
    {
        "name": "my_custom_workflow",
        "description": "Custom workflow for specific use case",
        "steps": [
            {
                "agent_type": "planner",
                "name": "Create Plan",
                "timeout": 120,
                "retry_count": 2
            },
            {
                "agent_type": "writer",
                "name": "Generate Code",
                "stream_output": true
            }
        ]
    }
    ```
    """
    try:
        # Convert steps to WorkflowStep objects
        steps = []
        for step_data in request.steps:
            step = WorkflowStep(
                agent_type=AgentType(step_data["agent_type"]),
                name=step_data["name"],
                timeout=step_data.get("timeout", 300),
                retry_count=step_data.get("retry_count", 2),
                stream_output=step_data.get("stream_output", False)
            )
            steps.append(step)

        # Register workflow
        orchestrator.workflow_engine.register_workflow(request.name, steps)

        return {
            "message": f"Workflow '{request.name}' created successfully",
            "workflow_name": request.name
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_name}", response_model=WorkflowResponse)
async def get_workflow(workflow_name: str):
    """
    Get details of a specific workflow.
    """
    try:
        steps = orchestrator.workflow_engine.get_workflow(workflow_name)

        return {
            "name": workflow_name,
            "steps": [
                {
                    "agent_type": step.agent_type.value,
                    "name": step.name,
                    "timeout": step.timeout,
                    "retry_count": step.retry_count,
                    "stream_output": step.stream_output
                }
                for step in steps
            ]
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Configuration Endpoints ====================

@router.get("/agents", response_model=List[AgentConfigResponse])
async def list_agents():
    """
    List all registered agents with their configurations.

    Returns agent details including model, temperature, capabilities, etc.
    """
    try:
        agents = orchestrator.agent_registry.list_agents()

        response = []
        for agent_type, config in agents.items():
            agent_data = AgentConfigResponse(
                name=config.name,
                agent_type=config.agent_type.value,
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                capabilities=config.capabilities or [],
                enabled=config.enabled,
                has_custom_prompt=config.system_prompt is not None
            )
            response.append(agent_data)

        return response
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_type}", response_model=AgentConfigResponse)
async def get_agent(agent_type: str):
    """
    Get configuration for a specific agent.
    """
    try:
        config = orchestrator.agent_registry.get_agent(AgentType(agent_type))

        return AgentConfigResponse(
            name=config.name,
            agent_type=config.agent_type.value,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            capabilities=config.capabilities or [],
            enabled=config.enabled,
            has_custom_prompt=config.system_prompt is not None
        )
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to get agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_type}/prompt", response_model=Dict[str, str])
async def update_agent_prompt(agent_type: str, request: AgentUpdatePromptRequest):
    """
    Dynamically update an agent's system prompt.

    This allows you to customize agent behavior without restarting the server.

    **Example:**
    ```json
    {
        "system_prompt": "You are an expert Python developer specializing in FastAPI..."
    }
    ```
    """
    try:
        orchestrator.agent_registry.update_agent_prompt(
            AgentType(agent_type),
            request.system_prompt
        )

        return {
            "message": f"Agent '{agent_type}' prompt updated successfully",
            "agent_type": agent_type
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to update agent prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_type}/model", response_model=Dict[str, str])
async def update_agent_model(agent_type: str, request: AgentUpdateModelRequest):
    """
    Dynamically update an agent's model.

    **Valid models:**
    - `haiku`: Fast, cost-effective (Claude 3 Haiku)
    - `sonnet`: Balanced performance (Claude 3.5 Sonnet) - Default
    - `opus`: Most powerful (Claude 3 Opus)

    **Example:**
    ```json
    {
        "model": "opus"
    }
    ```
    """
    try:
        if request.model not in ["haiku", "sonnet", "opus"]:
            raise ValueError(f"Invalid model: {request.model}. Must be haiku, sonnet, or opus")

        orchestrator.agent_registry.update_agent_model(
            AgentType(agent_type),
            request.model
        )

        return {
            "message": f"Agent '{agent_type}' model updated to '{request.model}'",
            "agent_type": agent_type,
            "model": request.model
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to update agent model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_type}/enable", response_model=Dict[str, str])
async def enable_agent(agent_type: str):
    """Enable a disabled agent."""
    try:
        config = orchestrator.agent_registry.get_agent(AgentType(agent_type))
        config.enabled = True

        return {
            "message": f"Agent '{agent_type}' enabled",
            "agent_type": agent_type
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to enable agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_type}/disable", response_model=Dict[str, str])
async def disable_agent(agent_type: str):
    """Disable an agent (it will be skipped in workflows)."""
    try:
        config = orchestrator.agent_registry.get_agent(AgentType(agent_type))
        config.enabled = False

        return {
            "message": f"Agent '{agent_type}' disabled",
            "agent_type": agent_type
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to disable agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Regeneration (Bolt.new Style) ====================

class RegenerateRequest(BaseModel):
    """Request to regenerate a project from saved plan"""
    project_id: str = Field(..., description="Project ID to regenerate")


@router.post("/regenerate")
async def regenerate_project(
    request: RegenerateRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate a project by replaying Claude messages (Bolt.new style).

    This endpoint:
    1. Loads saved plan.json and history from database
    2. Creates new empty workspace
    3. Replays the plan to Claude's writer agent
    4. Claude generates ALL files fresh (not restored from storage)

    This is exactly how Bolt.new handles "opening old projects".
    """
    try:
        # Get user if authenticated
        current_user = await get_optional_user(credentials, db)

        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for regeneration"
            )

        # Get project from database
        result = await db.execute(
            select(Project).where(
                Project.id == request.project_id,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not project.plan_json:
            raise HTTPException(
                status_code=400,
                detail="No saved plan found - cannot regenerate"
            )

        logger.info(f"[Regenerate] Starting regeneration for project: {request.project_id}")

        # Touch project to keep it alive
        touch_project(request.project_id)

        # Create regeneration event generator
        async def regenerate_generator():
            try:
                # Send start event
                yield f"data: {json.dumps({'type': 'regenerate_start', 'data': {'project_id': request.project_id, 'message': 'Loading saved plan...'}})}\n\n"
                await asyncio.sleep(0.01)

                # Extract plan data
                plan_data = project.plan_json
                files_to_generate = []

                # Get files from plan
                if isinstance(plan_data, dict):
                    files_to_generate = plan_data.get("files", [])
                    if not files_to_generate:
                        # Try alternate structure
                        tasks = plan_data.get("tasks", [])
                        for task in tasks:
                            if task.get("files"):
                                files_to_generate.extend(task["files"])

                yield f"data: {json.dumps({'type': 'plan_loaded', 'data': {'file_count': len(files_to_generate), 'message': f'Found {len(files_to_generate)} files to regenerate'}})}\n\n"
                await asyncio.sleep(0.01)

                # Execute writer workflow with saved plan (skip planning)
                async for event in orchestrator.execute_workflow(
                    user_request=project.description or project.title or "Regenerate project",
                    project_id=request.project_id,
                    workflow_name="writer_only",  # Skip planning, just write
                    metadata={
                        "mode": "regenerate",
                        "saved_plan": plan_data,
                        "skip_planning": True,
                        "user_id": str(current_user.id)
                    }
                ):
                    event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
                    event_data = {
                        "type": event_type,
                        "data": event.data,
                        "step": event.step,
                        "agent": event.agent,
                        "timestamp": event.timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    await asyncio.sleep(0.01)

                yield f"data: {json.dumps({'type': 'regenerate_complete', 'data': {'project_id': request.project_id, 'message': 'Project regenerated successfully'}})}\n\n"

            except Exception as e:
                logger.error(f"[Regenerate] Error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"

        return StreamingResponse(
            regenerate_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Regenerate] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """
    Health check endpoint for the orchestrator.

    Returns orchestrator status and configuration.
    """
    try:
        agents = orchestrator.agent_registry.list_agents()
        workflows = orchestrator.workflow_engine.list_workflows()

        return {
            "status": "healthy",
            "agents_count": len(agents),
            "workflows_count": len(workflows),
            "default_workflow": "bolt_standard"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }
