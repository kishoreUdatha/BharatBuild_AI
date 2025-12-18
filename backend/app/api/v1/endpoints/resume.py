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
from app.models.project import Project, ProjectStatus
from app.models.project_file import ProjectFile, FileGenerationStatus
from app.models.document import Document, DocumentType as DBDocumentType
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.feature_flags import require_feature, check_feature_access
from app.services.checkpoint_service import checkpoint_service, CheckpointStatus


router = APIRouter()


# Document types to generate in order
DOCUMENT_GENERATION_ORDER = [
    ("report", DBDocumentType.REPORT, "Project Report"),
    ("srs", DBDocumentType.SRS, "SRS Document"),
    ("ppt", DBDocumentType.PPT, "Presentation"),
    ("viva", DBDocumentType.VIVA_QA, "Viva Q&A"),
]


async def check_files_complete(db: AsyncSession, project_id: str) -> tuple[bool, int, int]:
    """
    Check if all planned files are generated.
    Returns: (all_complete, completed_count, total_count)
    """
    result = await db.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.is_folder == False
        )
    )
    files = result.scalars().all()

    if not files:
        return False, 0, 0

    completed = sum(1 for f in files if f.generation_status == FileGenerationStatus.COMPLETED)
    return completed == len(files), completed, len(files)


async def get_pending_documents(db: AsyncSession, project_id: str) -> list:
    """Get list of documents that haven't been generated yet."""
    result = await db.execute(
        select(Document.doc_type).where(Document.project_id == project_id)
    )
    existing_types = {row[0] for row in result.all()}

    pending = []
    for doc_key, doc_type, doc_name in DOCUMENT_GENERATION_ORDER:
        if doc_type not in existing_types:
            pending.append({"key": doc_key, "type": doc_type, "name": doc_name})

    return pending


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
    Smart Resume - Continues file generation OR starts document generation.

    This endpoint:
    1. Checks if all code files are generated
    2. If files incomplete → resume file generation
    3. If files complete → start document generation
    4. Streams progress via SSE

    Requires: Premium plan for document generation

    Returns:
        SSE stream with generation progress
    """
    user_id = str(current_user.id)

    # Check file generation status first
    files_complete, completed_count, total_count = await check_files_complete(db, project_id)

    # If files are complete and we need to generate documents, check feature access
    if files_complete:
        doc_access = await check_feature_access(db, current_user, "document_generation")
        if not doc_access["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_available",
                    "message": "Document generation requires Premium plan. Upgrade to generate SRS, reports, and presentations.",
                    "feature": "document_generation",
                    "current_plan": doc_access["current_plan"],
                    "upgrade_to": "Premium"
                }
            )

    # Get pending documents
    pending_docs = await get_pending_documents(db, project_id)

    logger.info(f"[SmartResume] Project {project_id}: files={completed_count}/{total_count}, pending_docs={len(pending_docs)}")

    async def smart_resume_generator():
        """Smart generator that handles both file and document generation"""
        try:
            # PHASE 1: Check and complete file generation if needed
            if not files_complete and total_count > 0:
                # Files still pending - resume file generation
                checkpoint = await checkpoint_service.get_checkpoint(project_id)

                if checkpoint and checkpoint.get("user_id") == user_id:
                    resume_info = await checkpoint_service.get_resume_point(project_id)
                    await checkpoint_service.mark_resumed(project_id)

                    yield f"data: {json.dumps({'type': 'resume_started', 'data': {'phase': 'files', 'project_id': project_id, 'completed': completed_count, 'total': total_count}})}\n\n"

                    from app.modules.orchestrator.dynamic_orchestrator import dynamic_orchestrator

                    async for event in dynamic_orchestrator.resume_workflow(
                        project_id=project_id,
                        resume_info=resume_info,
                        checkpoint_service=checkpoint_service
                    ):
                        yield f"data: {json.dumps(event)}\n\n"
                        await asyncio.sleep(0.01)

                    await checkpoint_service.mark_completed(project_id)

                    yield f"data: {json.dumps({'type': 'files_completed', 'data': {'project_id': project_id, 'message': 'All files generated'}})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'info', 'data': {'message': 'No checkpoint found, checking file status...'}})}\n\n"

            # Re-check files after generation
            files_complete_now, _, _ = await check_files_complete(db, project_id)

            # PHASE 2: Generate documents if files are complete
            if files_complete_now or files_complete:
                # Update project status to PARTIAL_COMPLETED if not already
                project_result = await db.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = project_result.scalar_one_or_none()

                if project and project.status == ProjectStatus.PROCESSING:
                    project.status = ProjectStatus.PARTIAL_COMPLETED
                    await db.commit()
                    logger.info(f"[SmartResume] Updated project {project_id} to PARTIAL_COMPLETED")

                # Get fresh list of pending documents
                pending_docs_now = await get_pending_documents(db, project_id)

                if pending_docs_now:
                    yield f"data: {json.dumps({'type': 'documents_starting', 'data': {'project_id': project_id, 'pending_count': len(pending_docs_now), 'documents': [d['name'] for d in pending_docs_now]}})}\n\n"

                    # Import document generator
                    from app.modules.agents.chunked_document_agent import chunked_document_agent, DocumentType

                    # Map string keys to DocumentType enum
                    doc_type_map = {
                        "report": DocumentType.REPORT,
                        "srs": DocumentType.SRS,
                        "ppt": DocumentType.PPT,
                        "viva": DocumentType.VIVA_QA,
                    }

                    for doc_info in pending_docs_now:
                        doc_key = doc_info["key"]
                        doc_name = doc_info["name"]

                        yield f"data: {json.dumps({'type': 'document_start', 'data': {'document': doc_name, 'key': doc_key}})}\n\n"

                        try:
                            doc_type_enum = doc_type_map.get(doc_key)
                            if doc_type_enum:
                                async for event in chunked_document_agent.generate_document_streaming(
                                    project_id=project_id,
                                    doc_type=doc_type_enum,
                                    db=db
                                ):
                                    yield f"data: {json.dumps(event)}\n\n"
                                    await asyncio.sleep(0.01)

                                yield f"data: {json.dumps({'type': 'document_complete', 'data': {'document': doc_name, 'key': doc_key}})}\n\n"
                        except Exception as doc_err:
                            logger.error(f"[SmartResume] Document generation error for {doc_key}: {doc_err}")
                            yield f"data: {json.dumps({'type': 'document_error', 'data': {'document': doc_name, 'error': str(doc_err)}})}\n\n"

                    # Check if all documents are now generated
                    final_pending = await get_pending_documents(db, project_id)
                    if not final_pending and project:
                        project.status = ProjectStatus.COMPLETED
                        from datetime import datetime
                        project.completed_at = datetime.utcnow()
                        await db.commit()
                        logger.info(f"[SmartResume] Project {project_id} marked as COMPLETED")

                    yield f"data: {json.dumps({'type': 'all_documents_completed', 'data': {'project_id': project_id}})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'info', 'data': {'message': 'All documents already generated'}})}\n\n"

            yield f"data: {json.dumps({'type': 'resume_completed', 'data': {'project_id': project_id, 'message': 'Project fully completed'}})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected
            logger.warning(f"[SmartResume] Client disconnected during resume of {project_id}")
            raise

        except Exception as e:
            logger.error(f"[SmartResume] Error resuming project {project_id}: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"

    return StreamingResponse(
        smart_resume_generator(),
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
