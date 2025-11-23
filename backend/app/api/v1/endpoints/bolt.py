"""
Bolt.new-style AI Code Editor Endpoints
Streaming chat, file operations, and code execution
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
import json
import asyncio
from datetime import datetime

from app.core.database import get_db
from app.core.logging_config import logger
from app.utils.claude_client import claude_client
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.bolt import (
    BoltChatRequest,
    BoltChatResponse,
    ApplyPatchRequest,
    ApplyPatchResponse,
    CreateFileRequest,
    UpdateFileRequest,
    DeleteFileRequest,
    FileOperationResponse,
    ExecuteCodeRequest,
    ExecuteCodeResponse,
    StreamEvent,
    ProjectFileSchema,
    GenerateProjectRequest,
    GenerateProjectResponse,
    GenerateProjectStreamEvent
)
from app.modules.bolt.prompts import BOLT_SYSTEM_PROMPT
from app.modules.bolt.context_builder import context_builder
from app.modules.orchestrator.bolt_orchestrator import bolt_orchestrator


router = APIRouter(prefix="/bolt", tags=["Bolt AI Editor"])


@router.post("/chat/stream")
async def stream_bolt_chat(
    request: BoltChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream AI responses for Bolt.new-style chat
    Uses Server-Sent Events (SSE) for real-time streaming
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send status event
            yield f"data: {json.dumps({'type': 'status', 'data': {'message': 'Building context...'}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Build context from project files
            files_dict = [f.model_dump() for f in request.files]

            context = context_builder.build_context(
                user_prompt=request.message,
                files=files_dict,
                project_name=request.project_name,
                selected_file_path=request.selected_file,
                max_files=10,
                max_tokens=50000
            )

            # Format context for Claude
            formatted_context = context_builder.format_for_claude(context)

            # Send status event
            yield f"data: {json.dumps({'type': 'status', 'data': {'message': 'Generating response...', 'files_analyzed': len(context.selected_files)}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Build messages for Claude
            messages = []
            for msg in request.conversation_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Stream response from Claude
            full_response = ""
            async for chunk in claude_client.generate_stream(
                prompt=formatted_context,
                system_prompt=BOLT_SYSTEM_PROMPT,
                model="sonnet",
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                messages=messages if messages else None
            ):
                full_response += chunk

                # Send content event
                yield f"data: {json.dumps({'type': 'content', 'data': {'chunk': chunk}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Parse response for file changes (unified diffs)
            file_changes = _extract_file_changes(full_response)

            if file_changes:
                yield f"data: {json.dumps({'type': 'file_changes', 'data': {'changes': file_changes}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Send done event
            yield f"data: {json.dumps({'type': 'done', 'data': {'message': 'Response complete'}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        except Exception as e:
            logger.error(f"Bolt streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/chat", response_model=BoltChatResponse)
async def bolt_chat(
    request: BoltChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Non-streaming Bolt chat endpoint
    Returns complete response at once
    """
    try:
        # Build context
        files_dict = [f.model_dump() for f in request.files]

        context = context_builder.build_context(
            user_prompt=request.message,
            files=files_dict,
            project_name=request.project_name,
            selected_file_path=request.selected_file,
            max_files=10,
            max_tokens=50000
        )

        formatted_context = context_builder.format_for_claude(context)

        # Build messages
        messages = []
        for msg in request.conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Generate response
        response = await claude_client.generate(
            prompt=formatted_context,
            system_prompt=BOLT_SYSTEM_PROMPT,
            model="sonnet",
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=messages if messages else None
        )

        return BoltChatResponse(**response)

    except Exception as e:
        logger.error(f"Bolt chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/apply-patch", response_model=ApplyPatchResponse)
async def apply_patch(
    request: ApplyPatchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Apply a unified diff patch to a file
    """
    try:
        from app.modules.bolt.patch_applier import apply_unified_patch

        result = apply_unified_patch(
            original_content=request.original_content,
            patch=request.patch
        )

        return ApplyPatchResponse(**result)

    except Exception as e:
        logger.error(f"Patch application error: {e}", exc_info=True)
        return ApplyPatchResponse(
            success=False,
            error=str(e)
        )


@router.post("/files/create", response_model=FileOperationResponse)
async def create_file(
    request: CreateFileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new file"""
    try:
        # TODO: Save to database if project_id provided

        file_schema = ProjectFileSchema(
            path=request.path,
            content=request.content,
            language=request.language,
            type="file"
        )

        return FileOperationResponse(
            success=True,
            message=f"File {request.path} created successfully",
            file=file_schema
        )

    except Exception as e:
        logger.error(f"File creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/update", response_model=FileOperationResponse)
async def update_file(
    request: UpdateFileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing file"""
    try:
        # TODO: Update in database if project_id provided

        return FileOperationResponse(
            success=True,
            message=f"File {request.path} updated successfully"
        )

    except Exception as e:
        logger.error(f"File update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/delete", response_model=FileOperationResponse)
async def delete_file(
    request: DeleteFileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a file"""
    try:
        # TODO: Delete from database if project_id provided

        return FileOperationResponse(
            success=True,
            message=f"File {request.path} deleted successfully"
        )

    except Exception as e:
        logger.error(f"File deletion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecuteCodeResponse)
async def execute_code(
    request: ExecuteCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute code in Docker sandbox
    """
    try:
        from app.modules.sandbox.docker_executor import docker_executor

        # Check if Docker is available
        if not docker_executor.check_docker_available():
            raise HTTPException(
                status_code=503,
                detail="Docker service is not available"
            )

        # Convert files to dict format
        files_dict = [f.model_dump() for f in request.files]

        # Execute code
        result = await docker_executor.execute(
            files=files_dict,
            command=request.command,
            environment=request.environment,
            timeout=request.timeout
        )

        return ExecuteCodeResponse(
            success=result.success,
            output=result.output,
            error=result.error,
            exit_code=result.exit_code,
            execution_time=result.execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/stream")
async def execute_code_stream(
    request: ExecuteCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute code and stream logs in real-time
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            from app.modules.sandbox.docker_executor import docker_executor

            if not docker_executor.check_docker_available():
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Docker not available'}})}\n\n"
                return

            files_dict = [f.model_dump() for f in request.files]

            yield f"data: {json.dumps({'type': 'status', 'data': {'message': 'Starting container...'}})}\n\n"

            async for log_line in docker_executor.execute_stream(
                files=files_dict,
                command=request.command,
                environment=request.environment,
                timeout=request.timeout
            ):
                yield f"data: {json.dumps({'type': 'log', 'data': {'line': log_line}})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'data': {'message': 'Execution complete'}})}\n\n"

        except Exception as e:
            logger.error(f"Stream execution error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/install-dependencies", response_model=ExecuteCodeResponse)
async def install_dependencies(
    request: ExecuteCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """Install project dependencies"""
    try:
        from app.modules.sandbox.docker_executor import docker_executor

        if not docker_executor.check_docker_available():
            raise HTTPException(
                status_code=503,
                detail="Docker service is not available"
            )

        files_dict = [f.model_dump() for f in request.files]

        result = await docker_executor.install_dependencies(
            files=files_dict,
            environment=request.environment
        )

        return ExecuteCodeResponse(
            success=result.success,
            output=result.output,
            error=result.error,
            exit_code=result.exit_code,
            execution_time=result.execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dependency installation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _extract_file_changes(response: str) -> list:
    """Extract unified diff patches from AI response"""
    import re

    # Pattern to match unified diffs
    diff_pattern = r'```diff\n(.*?)\n```'
    matches = re.findall(diff_pattern, response, re.DOTALL)

    changes = []
    for match in matches:
        # Extract file path from diff header
        file_match = re.search(r'\+\+\+ b/(.*)', match)
        if file_match:
            changes.append({
                'file_path': file_match.group(1),
                'patch': match
            })

    return changes


# ============================================================================
# PROJECT GENERATION ENDPOINTS (Bolt.new Workflow)
# ============================================================================

@router.post("/generate-project", response_model=GenerateProjectResponse)
async def generate_project(
    request: GenerateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a complete project using Bolt.new workflow

    This endpoint:
    1. Calls Planner Agent to create project plan
    2. Iterates through implementation steps
    3. Calls Writer Agent for each step to generate files
    4. Returns complete project with all files

    Non-streaming version - returns all results at once
    """
    try:
        import uuid

        # Generate project ID
        project_id = request.project_name or f"project_{uuid.uuid4().hex[:8]}"

        logger.info(f"[Generate Project] Starting for user {current_user.id}: {request.description[:100]}")

        # Execute Bolt workflow
        result = await bolt_orchestrator.execute_bolt_workflow(
            user_request=request.description,
            project_id=project_id,
            metadata=request.metadata or {}
        )

        if not result.get("success"):
            return GenerateProjectResponse(
                success=False,
                project_id=project_id,
                plan={},
                total_steps=0,
                steps_completed=0,
                total_files_created=0,
                total_commands_executed=0,
                files_created=[],
                commands_executed=[],
                started_at=result.get("started_at", datetime.utcnow().isoformat()),
                completed_at=result.get("completed_at", datetime.utcnow().isoformat()),
                error=result.get("error", "Unknown error")
            )

        # Return successful response
        return GenerateProjectResponse(
            success=True,
            project_id=result["project_id"],
            plan=result["plan"],
            total_steps=result["total_steps"],
            steps_completed=result["steps_completed"],
            total_files_created=result["total_files_created"],
            total_commands_executed=result["total_commands_executed"],
            files_created=result["files_created"],
            commands_executed=result["commands_executed"],
            started_at=result["started_at"],
            completed_at=result["completed_at"]
        )

    except Exception as e:
        logger.error(f"[Generate Project] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-project/stream")
async def generate_project_stream(
    request: GenerateProjectRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a complete project using Bolt.new workflow with streaming

    Streams progress updates in real-time:
    - progress: Overall progress percentage
    - step_start: When a step begins
    - step_complete: When a step finishes
    - file_created: When a file is created
    - command_executed: When a command is executed
    - done: When generation is complete
    - error: If an error occurs
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            import uuid

            # Generate project ID
            project_id = request.project_name or f"project_{uuid.uuid4().hex[:8]}"

            logger.info(f"[Generate Project Stream] Starting for user {current_user.id}")

            # Define progress callback
            async def progress_callback(percent: int, message: str):
                event = {
                    "type": "progress",
                    "data": {
                        "percent": percent,
                        "message": message
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(event)}\n\n"

            # Execute Bolt workflow with progress callback
            result = await bolt_orchestrator.execute_bolt_workflow(
                user_request=request.description,
                project_id=project_id,
                metadata=request.metadata or {},
                progress_callback=progress_callback
            )

            if result.get("success"):
                # Send completion event
                event = {
                    "type": "done",
                    "data": {
                        "project_id": result["project_id"],
                        "total_files_created": result["total_files_created"],
                        "total_commands_executed": result["total_commands_executed"],
                        "steps_completed": result["steps_completed"]
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(event)}\n\n"
            else:
                # Send error event
                event = {
                    "type": "error",
                    "data": {
                        "error": result.get("error", "Unknown error")
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error(f"[Generate Project Stream] Error: {e}", exc_info=True)
            event = {
                "type": "error",
                "data": {
                    "error": str(e)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
