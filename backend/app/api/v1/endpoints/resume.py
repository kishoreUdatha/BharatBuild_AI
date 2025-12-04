"""
Resume API - Handles workflow resumption after disconnection

Endpoints:
- GET /resume/status/{project_id} - Check if project can be resumed
- POST /resume/{project_id} - Resume interrupted workflow
- GET /resume/list - List all resumable projects for user
- DELETE /resume/{project_id} - Cancel/delete checkpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
import json
import asyncio

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User
from app.models.project import Project
from app.modules.auth.dependencies import get_current_user
from app.services.checkpoint_service import checkpoint_service, CheckpointStatus


router = APIRouter()


@router.get("/status/{project_id}")
async def get_resume_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a project can be resumed.

    Returns:
        - can_resume: Whether project can be resumed
        - checkpoint: Current checkpoint status
        - resume_info: Information about where to resume from
    """
    # Verify ownership
    checkpoint = await checkpoint_service.get_checkpoint(project_id)

    if not checkpoint:
        return {
            "can_resume": False,
            "reason": "No checkpoint found",
            "checkpoint": None
        }

    if checkpoint.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    can_resume = await checkpoint_service.can_resume(project_id)
    resume_info = await checkpoint_service.get_resume_point(project_id) if can_resume else None

    return {
        "can_resume": can_resume,
        "checkpoint": {
            "status": checkpoint.get("status"),
            "current_step": checkpoint.get("current_step"),
            "completed_steps": checkpoint.get("completed_steps", []),
            "generated_files_count": len(checkpoint.get("generated_files", [])),
            "pending_files_count": len(checkpoint.get("pending_files", [])),
            "error_message": checkpoint.get("error_message"),
            "retry_count": checkpoint.get("retry_count", 0),
            "max_retries": checkpoint.get("max_retries", 3),
            "updated_at": checkpoint.get("updated_at")
        },
        "resume_info": resume_info
    }


@router.post("/{project_id}")
async def resume_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resume an interrupted project generation.

    This endpoint:
    1. Verifies the project can be resumed
    2. Loads the checkpoint state
    3. Continues from the last successful step
    4. Streams progress via SSE

    Returns:
        SSE stream with generation progress
    """
    # Verify ownership
    checkpoint = await checkpoint_service.get_checkpoint(project_id)

    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No checkpoint found for this project"
        )

    if checkpoint.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not await checkpoint_service.can_resume(project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project cannot be resumed. Status: {checkpoint.get('status')}, Retries: {checkpoint.get('retry_count')}/{checkpoint.get('max_retries')}"
        )

    # Get resume point
    resume_info = await checkpoint_service.get_resume_point(project_id)

    async def resume_generator():
        """Generate SSE events for resumed workflow"""
        try:
            # Mark as resumed
            await checkpoint_service.mark_resumed(project_id)

            # Send resume started event
            yield f"data: {json.dumps({'type': 'resume_started', 'data': {'project_id': project_id, 'resume_from': resume_info.get('next_step'), 'completed_steps': resume_info.get('completed_steps'), 'remaining_files': len(resume_info.get('remaining_files', []))}})}\n\n"

            # Import orchestrator
            from app.modules.orchestrator.dynamic_orchestrator import dynamic_orchestrator

            # Resume the workflow
            async for event in dynamic_orchestrator.resume_workflow(
                project_id=project_id,
                resume_info=resume_info,
                checkpoint_service=checkpoint_service
            ):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)

            # Mark completed
            await checkpoint_service.mark_completed(project_id)

            yield f"data: {json.dumps({'type': 'resume_completed', 'data': {'project_id': project_id, 'message': 'Project generation completed successfully'}})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected
            await checkpoint_service.mark_interrupted(project_id, "Client disconnected during resume")
            logger.warning(f"[Resume] Client disconnected during resume of {project_id}")
            raise

        except Exception as e:
            logger.error(f"[Resume] Error resuming project {project_id}: {e}", exc_info=True)
            await checkpoint_service.update_step(
                project_id,
                checkpoint.get("current_step", "unknown"),
                CheckpointStatus.FAILED,
                error=str(e)
            )
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e), 'can_retry': await checkpoint_service.can_resume(project_id)}})}\n\n"

    return StreamingResponse(
        resume_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/list")
async def list_resumable_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all projects that can be resumed for the current user.

    Returns:
        List of resumable project checkpoints
    """
    checkpoints = await checkpoint_service.get_user_checkpoints(str(current_user.id))

    # Filter to only resumable ones
    resumable = [
        cp for cp in checkpoints
        if cp.get("can_resume") and cp.get("status") in [
            CheckpointStatus.INTERRUPTED,
            CheckpointStatus.FAILED,
            CheckpointStatus.IN_PROGRESS
        ]
    ]

    return {
        "resumable_projects": resumable,
        "total": len(resumable)
    }


@router.delete("/{project_id}")
async def cancel_checkpoint(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel and delete a checkpoint.

    This removes the ability to resume the project.
    Generated files are NOT deleted.
    """
    checkpoint = await checkpoint_service.get_checkpoint(project_id)

    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkpoint not found"
        )

    if checkpoint.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    await checkpoint_service.delete_checkpoint(project_id)

    return {
        "message": "Checkpoint deleted",
        "project_id": project_id
    }


@router.post("/heartbeat/{project_id}")
async def heartbeat(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Heartbeat endpoint to keep connection alive and update checkpoint.

    Frontend should call this every 30 seconds during generation.
    """
    checkpoint = await checkpoint_service.get_checkpoint(project_id)

    if not checkpoint:
        return {"status": "no_checkpoint"}

    if checkpoint.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Update timestamp
    from datetime import datetime
    checkpoint["last_heartbeat"] = datetime.utcnow().isoformat()
    await checkpoint_service._save_checkpoint(project_id, checkpoint)

    return {
        "status": "ok",
        "checkpoint_status": checkpoint.get("status"),
        "current_step": checkpoint.get("current_step")
    }
