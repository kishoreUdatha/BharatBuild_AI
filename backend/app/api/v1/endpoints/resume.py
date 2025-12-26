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

    This function checks BOTH:
    1. Files in DB have status = COMPLETED with actual content (size_bytes > 0)
    2. All files from plan_json exist in DB

    Returns: (all_complete, completed_count, total_count)
    """
    from app.models.project import Project

    # Get files from database
    result = await db.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.is_folder == False
        )
    )
    db_files = result.scalars().all()

    # Get plan_json to check for missing files
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    plan_json = project.plan_json if project else None

    # Get files from plan
    plan_files = []
    if plan_json and isinstance(plan_json, dict):
        plan_files = plan_json.get('files', [])

    plan_file_paths = {f.get('path') for f in plan_files if f.get('path')}
    db_file_paths = {f.path for f in db_files}

    # Find files in plan but not in DB (missing files)
    missing_from_db = plan_file_paths - db_file_paths

    if not db_files and not plan_files:
        return False, 0, 0

    # Count completed files (must have COMPLETED status AND actual content)
    completed = sum(
        1 for f in db_files
        if f.generation_status == FileGenerationStatus.COMPLETED and f.size_bytes > 0
    )

    # Total = files in DB + files missing from DB
    total_count = len(db_files) + len(missing_from_db)

    # All complete only if no missing files AND all DB files are completed with content
    all_complete = len(missing_from_db) == 0 and completed == len(db_files) and len(db_files) > 0

    if missing_from_db:
        logger.warning(f"[Resume] Found {len(missing_from_db)} files in plan but missing from DB: {list(missing_from_db)[:5]}...")

    return all_complete, completed, total_count


async def get_incomplete_files(db: AsyncSession, project_id: str) -> list:
    """
    Get files that need to be generated.

    This includes:
    1. Files with status != COMPLETED
    2. Files with COMPLETED status but size_bytes = 0 (empty content)
    3. Files in plan_json but missing from database entirely

    Returns list of dicts with file info for regeneration.
    has_s3_key is only True if file has BOTH s3_key AND size_bytes > 0.
    """
    from app.models.project import Project

    # Get all non-folder files from database
    result = await db.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.is_folder == False
        ).order_by(ProjectFile.generation_order)
    )
    db_files = result.scalars().all()
    db_file_paths = {f.path for f in db_files}

    # Get plan_json to find missing files
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    plan_json = project.plan_json if project else None

    incomplete = []

    # 1. Check DB files for incomplete ones
    for f in db_files:
        needs_regeneration = False
        reason = ""

        if f.generation_status != FileGenerationStatus.COMPLETED:
            # Status is not COMPLETED
            needs_regeneration = True
            reason = f.generation_status.value if f.generation_status else "unknown"
        elif f.size_bytes == 0 or f.size_bytes is None:
            # COMPLETED but no content (empty file)
            needs_regeneration = True
            reason = "empty_content"
            logger.warning(f"[Resume] File {f.path} marked COMPLETED but has no content (size=0)")

        if needs_regeneration:
            # Only trust has_s3_key if size_bytes > 0
            has_valid_s3_content = bool(f.s3_key) and f.size_bytes and f.size_bytes > 0
            incomplete.append({
                "path": f.path,
                "name": f.name,
                "status": reason,
                "order": f.generation_order or 0,
                "has_s3_key": has_valid_s3_content,
                "s3_key": f.s3_key if has_valid_s3_content else None
            })

    # 2. Check for files in plan but missing from DB entirely
    if plan_json and isinstance(plan_json, dict):
        plan_files = plan_json.get('files', [])
        for idx, pf in enumerate(plan_files):
            file_path = pf.get('path')
            if file_path and file_path not in db_file_paths:
                logger.warning(f"[Resume] File {file_path} in plan but missing from DB - will regenerate")
                incomplete.append({
                    "path": file_path,
                    "name": file_path.split('/')[-1] if '/' in file_path else file_path,
                    "status": "missing_from_db",
                    "order": idx,
                    "has_s3_key": False,
                    "s3_key": None,
                    "description": pf.get('description', '')
                })

    # Sort by order
    incomplete.sort(key=lambda x: x.get('order', 0))

    return incomplete


async def fix_orphaned_s3_files(db: AsyncSession, project_id: str) -> int:
    """
    Fix files where S3 upload succeeded but DB status wasn't updated.
    These files have s3_key AND size_bytes > 0 (actual content) but status != COMPLETED.

    IMPORTANT: Only marks as COMPLETED if size_bytes > 0 to ensure content actually exists.
    Files with s3_key but size_bytes = 0 are likely incomplete/failed uploads.

    Returns number of files fixed.
    """
    from sqlalchemy import update

    # Only fix files that have BOTH s3_key AND actual content (size_bytes > 0)
    result = await db.execute(
        update(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .where(ProjectFile.is_folder == False)
        .where(ProjectFile.s3_key != None)
        .where(ProjectFile.size_bytes > 0)  # CRITICAL: Ensure content actually exists
        .where(ProjectFile.generation_status != FileGenerationStatus.COMPLETED)
        .values(generation_status=FileGenerationStatus.COMPLETED)
    )
    await db.commit()

    fixed_count = result.rowcount
    if fixed_count > 0:
        logger.info(f"[Resume] Fixed {fixed_count} orphaned S3 files for project {project_id}")

    return fixed_count


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

    # Verify project ownership
    try:
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        if str(project.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Check if project is currently being generated (prevent duplicate runs)
        if project.status == ProjectStatus.PROCESSING:
            from datetime import datetime, timedelta
            stale_threshold = timedelta(minutes=10)
            if project.updated_at:
                time_since_update = datetime.utcnow() - project.updated_at
                if time_since_update < stale_threshold:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "generation_in_progress",
                            "message": "Project generation is currently in progress. Please wait for it to complete.",
                            "can_resume": False
                        }
                    )
                else:
                    logger.warning(f"[SmartResume] Stale PROCESSING project {project_id}, allowing resume")
    except HTTPException:
        raise
    except Exception as db_err:
        logger.error(f"[SmartResume] Database error checking project: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify project"
        )

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
            # PHASE 0: Fix orphaned S3 files (S3 saved but status not updated)
            # This handles cases where S3 upload succeeded but DB commit failed
            fixed_count = await fix_orphaned_s3_files(db, project_id)
            if fixed_count > 0:
                yield f"data: {json.dumps({'type': 'info', 'data': {'message': f'Fixed {fixed_count} files already saved to S3'}})}\n\n"

            # PHASE 1: Check and complete file generation if needed
            if not files_complete and total_count > 0:
                # Get list of incomplete files (PLANNED, GENERATING, FAILED)
                incomplete_files = await get_incomplete_files(db, project_id)

                # Separate files that need regeneration from those already in S3
                files_with_s3 = [f for f in incomplete_files if f.get("has_s3_key")]
                files_need_generation = [f for f in incomplete_files if not f.get("has_s3_key")]

                if files_with_s3:
                    # These files are already in S3, just need status update
                    yield f"data: {json.dumps({'type': 'info', 'data': {'message': f'{len(files_with_s3)} files already in S3, updating status...'}})}\n\n"

                if files_need_generation:
                    yield f"data: {json.dumps({'type': 'resume_started', 'data': {'phase': 'files', 'project_id': project_id, 'completed': completed_count, 'total': total_count, 'pending_files': len(files_need_generation), 'already_in_s3': len(files_with_s3)}})}\n\n"

                    logger.info(f"[SmartResume] Found {len(files_need_generation)} files to regenerate ({len(files_with_s3)} already in S3)")

                    # Get project plan for context
                    project_result = await db.execute(
                        select(Project).where(Project.id == project_id)
                    )
                    project = project_result.scalar_one_or_none()
                    plan_json = project.plan_json if project else None

                    if plan_json:
                        # Use orchestrator to regenerate only files WITHOUT s3_key
                        from app.modules.orchestrator.dynamic_orchestrator import dynamic_orchestrator

                        async for event in dynamic_orchestrator.resume_incomplete_files(
                            project_id=project_id,
                            incomplete_files=files_need_generation,  # Only files without S3 content
                            plan=plan_json,
                            user_id=user_id
                        ):
                            yield f"data: {json.dumps(event)}\n\n"
                            await asyncio.sleep(0.01)

                        yield f"data: {json.dumps({'type': 'files_completed', 'data': {'project_id': project_id, 'message': 'All files generated'}})}\n\n"
                    else:
                        # No plan_json - check for checkpoint
                        checkpoint = await checkpoint_service.get_checkpoint(project_id)

                        if checkpoint and checkpoint.get("user_id") == user_id:
                            resume_info = await checkpoint_service.get_resume_point(project_id)
                            await checkpoint_service.mark_resumed(project_id)

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
                            yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'no_plan', 'message': 'No plan found. Please regenerate the project.'}})}\n\n"
                            return
                else:
                    yield f"data: {json.dumps({'type': 'info', 'data': {'message': 'No incomplete files found'}})}\n\n"

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
