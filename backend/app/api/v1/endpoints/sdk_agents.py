"""
SDK Agents API Endpoints

Provides REST and streaming endpoints for SDK-based agents.
These work alongside existing agents for a hybrid approach.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
import asyncio

from app.core.logging_config import logger
from app.modules.auth.dependencies import get_current_user
from app.modules.sdk_agents.sdk_fixer_agent import sdk_fixer_agent
from app.modules.sdk_agents.sdk_orchestrator import sdk_orchestrator


router = APIRouter(prefix="/sdk", tags=["SDK Agents"])


# ============================================
# Request/Response Models
# ============================================

class FixErrorRequest(BaseModel):
    """Request to fix an error"""
    project_id: str = Field(..., description="Project identifier")
    error_message: str = Field(..., description="Error message to fix")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    command: Optional[str] = Field(None, description="Command that caused the error")
    build_command: Optional[str] = Field("npm run build", description="Command to verify fix")
    max_retries: Optional[int] = Field(3, description="Maximum fix attempts")


class FixErrorResponse(BaseModel):
    """Response from fix attempt"""
    success: bool
    error_fixed: bool
    files_modified: List[str]
    message: str
    attempts: int


class OrchestrationRequest(BaseModel):
    """Request to orchestrate a project"""
    project_id: str = Field(..., description="Project identifier")
    user_request: str = Field(..., description="User's project request")
    build_command: Optional[str] = Field("npm run build", description="Build command")
    max_fix_attempts: Optional[int] = Field(5, description="Max fix attempts")


class ToolExecuteRequest(BaseModel):
    """Request to execute a single tool"""
    project_id: str = Field(..., description="Project identifier")
    tool_name: str = Field(..., description="Tool name to execute")
    tool_input: Dict[str, Any] = Field(..., description="Tool input parameters")


# ============================================
# Endpoints
# ============================================

@router.post("/fix", response_model=FixErrorResponse)
async def fix_error(
    request: FixErrorRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Fix an error using the SDK Fixer Agent.

    This endpoint uses Claude's tool use API to automatically:
    1. Read the error and locate the problematic file
    2. Analyze and fix the issue
    3. Verify the fix by running the build command

    The SDK Fixer provides better reliability and automatic retry
    compared to the standard fixer.
    """
    user_id = current_user.get("user_id", "anonymous")

    logger.info(f"[SDK API] Fix request for project {request.project_id}")

    try:
        result = await sdk_fixer_agent.fix_with_retry(
            project_id=request.project_id,
            user_id=user_id,
            error_message=request.error_message,
            stack_trace=request.stack_trace or "",
            command=request.command or "",
            build_command=request.build_command or "npm run build",
            max_retries=request.max_retries or 3
        )

        return FixErrorResponse(
            success=result.success,
            error_fixed=result.error_fixed,
            files_modified=result.files_modified,
            message=result.message,
            attempts=result.attempts
        )

    except Exception as e:
        logger.error(f"[SDK API] Fix error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix/stream")
async def fix_error_stream(
    request: FixErrorRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Fix an error with streaming progress updates.

    Returns Server-Sent Events (SSE) with progress updates
    as the fix is being applied.
    """
    user_id = current_user.get("user_id", "anonymous")

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting fix...'})}\n\n"

            result = await sdk_fixer_agent.fix_with_retry(
                project_id=request.project_id,
                user_id=user_id,
                error_message=request.error_message,
                stack_trace=request.stack_trace or "",
                command=request.command or "",
                build_command=request.build_command or "npm run build",
                max_retries=request.max_retries or 3
            )

            yield f"data: {json.dumps({'type': 'complete', 'result': {'success': result.success, 'error_fixed': result.error_fixed, 'files_modified': result.files_modified, 'message': result.message, 'attempts': result.attempts}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.post("/orchestrate/stream")
async def orchestrate_stream(
    request: OrchestrationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Orchestrate a project with streaming events.

    Streams progress events as the orchestrator:
    1. Plans the project
    2. Creates files
    3. Builds and fixes errors
    4. Completes the project
    """
    user_id = current_user.get("user_id", "anonymous")

    async def event_generator():
        try:
            async for event in sdk_orchestrator.stream_orchestration(
                project_id=request.project_id,
                user_id=user_id,
                user_request=request.user_request
            ):
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.post("/tool/execute")
async def execute_tool(
    request: ToolExecuteRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Execute a single SDK tool directly.

    Available tools:
    - bash: Execute shell commands
    - view_file: Read file contents
    - str_replace: Replace text in files
    - create_file: Create new files
    - insert_lines: Insert lines at position
    - glob: Find files by pattern
    - grep: Search file contents
    - list_directory: List directory contents

    This is useful for testing tools or building custom workflows.
    """
    user_id = current_user.get("user_id", "anonymous")

    logger.info(f"[SDK API] Tool execute: {request.tool_name} for project {request.project_id}")

    try:
        result = await sdk_fixer_agent._execute_tool(
            project_id=request.project_id,
            user_id=user_id,
            tool_name=request.tool_name,
            tool_input=request.tool_input
        )

        return {
            "success": True,
            "tool": request.tool_name,
            "result": result
        }

    except Exception as e:
        logger.error(f"[SDK API] Tool execute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """
    List all available SDK tools.

    Returns the tool definitions including:
    - name: Tool identifier
    - description: What the tool does
    - input_schema: Required and optional parameters
    """
    from app.modules.sdk_agents.sdk_tools import SDKToolManager

    return {
        "tools": SDKToolManager.get_fixer_tools(),
        "count": len(SDKToolManager.get_tool_names())
    }


@router.get("/health")
async def sdk_health():
    """Check SDK agents health status"""
    return {
        "status": "healthy",
        "sdk_fixer": "ready",
        "sdk_orchestrator": "ready",
        "tools_available": len(sdk_fixer_agent.tools)
    }
