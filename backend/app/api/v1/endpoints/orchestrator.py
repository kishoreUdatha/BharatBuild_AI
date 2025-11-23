"""
FastAPI endpoints for Dynamic Orchestrator (Bolt.new-style)

This module provides REST API endpoints for:
- Executing workflows with SSE streaming
- Managing agents (update prompts/models dynamically)
- Managing workflows (list, create, update)
- Real-time event streaming to frontend
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
import json
import logging

from app.modules.orchestrator.dynamic_orchestrator import (
    DynamicOrchestrator,
    AgentType,
    AgentConfig,
    WorkflowStep,
    OrchestratorEvent
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

# Global orchestrator instance
orchestrator = DynamicOrchestrator()


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

    """
    try:
        # Send initial connection event to ensure stream is open
        initial_event = {
            "type": "connected",
            "data": {"message": "Stream connected"},
            "step": None,
            "agent": None,
            "timestamp": None
        }
        yield f"data: {json.dumps(initial_event)}\n\n"

        # Execute workflow and stream events
        async for event in orchestrator.execute_workflow(
            user_request=user_request,
            project_id=project_id,
            workflow_name=workflow_name,
            metadata=metadata
        ):
            # Convert OrchestratorEvent to SSE format
            event_data = {
                "type": event.type,
                "data": event.data,
                "step": event.step,
                "agent": event.agent,
                "timestamp": event.timestamp
            }

            # SSE format: "data: {json}\n\n"
            event_message = f"data: {json.dumps(event_data)}\n\n"
            yield event_message

            # Small delay to ensure proper flushing and prevent overwhelming the client
            await asyncio.sleep(0.05)  # Increased from 0.01 to 0.05

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

    finally:
        # Send completion event
        complete_event = {
            "type": "complete",
            "data": {"status": "finished"},
            "step": None,
            "agent": None,
            "timestamp": None
        }
        yield f"data: {json.dumps(complete_event)}\n\n"


# ==================== Workflow Execution Endpoints ====================

@router.post("/execute")
async def execute_workflow(request: WorkflowExecuteRequest):
    """
    Execute a workflow with real-time SSE streaming.

    This endpoint returns a Server-Sent Events (SSE) stream that sends
    real-time updates as the workflow executes.

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
        return StreamingResponse(
            event_generator(
                user_request=request.user_request,
                project_id=request.project_id,
                workflow_name=request.workflow_name,
                metadata=request.metadata
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Transfer-Encoding": "chunked",  # Enable chunked encoding
                "Content-Type": "text/event-stream; charset=utf-8"
            }
        )
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
