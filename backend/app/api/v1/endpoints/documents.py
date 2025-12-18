"""
DOCUMENT GENERATION API
=======================
Streaming endpoints for generating large documents (60-80 pages).

Features:
- SSE streaming for progress updates
- Section-by-section generation
- Download endpoints for generated files
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import json
import asyncio
import os

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.document import Document
from app.models.document import DocumentType as DBDocumentType
from app.modules.auth.dependencies import get_current_user
from app.modules.agents.chunked_document_agent import (
    chunked_document_agent,
    DocumentType
)
from app.core.logging_config import logger
from app.utils.pagination import create_paginated_response
from app.modules.auth.feature_flags import require_document_generation, require_feature


router = APIRouter()


# Required documents for project completion
REQUIRED_DOCUMENTS_FOR_COMPLETION = [
    DBDocumentType.REPORT,    # Project Report
    DBDocumentType.SRS,       # SRS Document
    DBDocumentType.PPT,       # Presentation
    DBDocumentType.VIVA_QA    # Viva Q&A
]


async def check_and_mark_project_completed(
    db: AsyncSession,
    project_id: str,
    user_id: str
) -> bool:
    """
    Check if all required documents are generated and mark project as COMPLETED.

    Returns True if project is now COMPLETED, False otherwise.
    """
    try:
        # Get the project
        project_result = await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.user_id == str(user_id)
            )
        )
        project = project_result.scalar_one_or_none()

        if not project:
            logger.warning(f"Project {project_id} not found for completion check")
            return False

        # Check if project can be marked as completed (not already completed)
        if project.status == ProjectStatus.COMPLETED:
            logger.info(f"Project {project_id} is already COMPLETED")
            return True

        # Allow completion check for PARTIAL_COMPLETED, PROCESSING, or IN_PROGRESS
        if project.status not in [ProjectStatus.PARTIAL_COMPLETED, ProjectStatus.PROCESSING, ProjectStatus.IN_PROGRESS]:
            logger.info(f"Project {project_id} status is {project.status.value}, skipping completion check")
            return False

        # Count existing documents by type
        doc_count_result = await db.execute(
            select(Document.doc_type, func.count(Document.id))
            .where(Document.project_id == str(project_id))
            .group_by(Document.doc_type)
        )
        existing_docs = {row[0]: row[1] for row in doc_count_result.all()}

        # Check if all required documents exist
        all_docs_generated = all(
            doc_type in existing_docs and existing_docs[doc_type] > 0
            for doc_type in REQUIRED_DOCUMENTS_FOR_COMPLETION
        )

        if all_docs_generated:
            # Mark project as fully COMPLETED
            project.status = ProjectStatus.COMPLETED
            project.completed_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Project {project_id} marked as COMPLETED (all documents generated)")
            return True
        else:
            # Log which documents are still missing
            missing = [
                doc_type.value for doc_type in REQUIRED_DOCUMENTS_FOR_COMPLETION
                if doc_type not in existing_docs or existing_docs[doc_type] == 0
            ]
            logger.info(f"Project {project_id} still missing documents: {missing}")
            return False

    except Exception as e:
        logger.error(f"Error checking project completion: {e}", exc_info=True)
        return False


# ========== Request/Response Schemas ==========

class DocumentGenerationRequest(BaseModel):
    project_id: str
    document_type: str  # "project_report", "srs", "sds", "ppt", "viva_qa"
    project_name: str
    project_type: Optional[str] = "Software Project"
    author: Optional[str] = "Student Name"
    institution: Optional[str] = "University Name"
    department: Optional[str] = "Computer Science"
    guide: Optional[str] = "Guide Name"
    technologies: Optional[dict] = {}
    features: Optional[List[str]] = []
    api_endpoints: Optional[List[dict]] = []
    database_tables: Optional[List[str]] = []
    code_files: Optional[List[dict]] = []


class DocumentStatusResponse(BaseModel):
    status: str
    progress: float
    current_section: Optional[str]
    message: Optional[str]


# ========== Streaming Document Generation ==========

@router.post("/generate/stream")
async def generate_document_stream(
    request: DocumentGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_document_generation)
):
    """
    Stream document generation progress via SSE.

    This endpoint generates large documents (60-80 pages) by:
    1. Breaking into sections
    2. Generating each section with Claude
    3. Assembling final document

    Returns SSE stream with progress updates.
    """
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == str(request.project_id),
            Project.user_id == str(current_user.id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Store user info for the generator
    user_id = str(current_user.id)
    project_id = request.project_id

    async def event_generator():
        try:
            # Convert request to document type
            try:
                doc_type = DocumentType(request.document_type)
            except ValueError:
                yield f"data: {json.dumps({'type': 'error', 'error': f'Invalid document type: {request.document_type}'})}\n\n"
                return

            # Build project data - use user profile data as defaults
            project_data = {
                "project_name": request.project_name,
                "project_type": request.project_type,
                "author": request.author if request.author != "Student Name" else (current_user.full_name or current_user.username or "Student"),
                "institution": request.institution if request.institution != "University Name" else (current_user.college_name or "University"),
                "department": request.department if request.department != "Computer Science" else (current_user.department or "Computer Science and Engineering"),
                "guide": request.guide if request.guide != "Guide Name" else (current_user.guide_name or "Project Guide"),
                "technologies": request.technologies,
                "features": request.features,
                "api_endpoints": request.api_endpoints,
                "database_tables": request.database_tables,
                "code_files": request.code_files,
                # Additional user profile data for documents
                "roll_number": current_user.roll_number,
                "university_name": current_user.university_name,
                "guide_designation": current_user.guide_designation,
                "hod_name": current_user.hod_name,
                "course": current_user.course,
                "year_semester": current_user.year_semester,
                "batch": current_user.batch
            }

            # Create agent context with user_id for isolation
            from app.modules.agents.base_agent import AgentContext
            context = AgentContext(
                project_id=project_id,
                user_id=user_id,  # IMPORTANT: Include user_id for S3/DB isolation
                user_request=f"Generate {request.document_type} for {request.project_name}"
            )

            # Stream generation progress
            async for event in chunked_document_agent.generate_document(
                context=context,
                document_type=doc_type,
                project_data=project_data
            ):
                yield f"data: {json.dumps(event)}\n\n"

                # Check if document generation is complete
                if event.get("type") == "complete":
                    # Save token transaction for document generation
                    token_usage = event.get("token_usage", {})
                    if token_usage and token_usage.get("total_tokens", 0) > 0:
                        try:
                            from app.services.token_tracker import token_tracker
                            from app.models.usage import AgentType, OperationType

                            # Map document type to operation type
                            doc_type_map = {
                                "srs": OperationType.GENERATE_SRS,
                                "project_report": OperationType.GENERATE_REPORT,
                                "ppt": OperationType.GENERATE_PPT,
                                "viva_qa": OperationType.GENERATE_VIVA,
                            }
                            operation = doc_type_map.get(request.document_type, OperationType.OTHER)

                            await token_tracker.log_transaction_simple(
                                user_id=str(user_id),
                                project_id=str(project_id),
                                agent_type=AgentType.DOCUMENT,
                                operation=operation,
                                model=token_usage.get("model", "haiku"),
                                input_tokens=token_usage.get("input_tokens", 0),
                                output_tokens=token_usage.get("output_tokens", 0),
                                metadata={
                                    "document_type": request.document_type,
                                    "call_count": token_usage.get("call_count", 0)
                                }
                            )
                            logger.info(f"[DocumentAPI] Token usage saved: {token_usage.get('total_tokens', 0)} tokens for {request.document_type}")
                        except Exception as token_err:
                            logger.warning(f"[DocumentAPI] Failed to save token usage: {token_err}")

                    # Check if all required documents are now generated
                    # and mark project as COMPLETED if so
                    from app.core.database import async_session
                    async with async_session() as check_db:
                        is_completed = await check_and_mark_project_completed(
                            check_db, project_id, user_id
                        )
                        if is_completed:
                            yield f"data: {json.dumps({'type': 'project_completed', 'message': 'All documents generated! Project is now fully completed.'})}\n\n"

                await asyncio.sleep(0.1)  # Small delay for smooth streaming

        except Exception as e:
            logger.error(f"[DocumentAPI] Error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/generate")
async def generate_document(
    request: DocumentGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_document_generation)
):
    """
    Start document generation (non-streaming).

    Returns immediately with task ID for polling status.
    """
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == str(request.project_id),
            Project.user_id == str(current_user.id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # For now, redirect to streaming endpoint
    # In production, use Celery for background processing

    return {
        "message": "Document generation started",
        "project_id": request.project_id,
        "document_type": request.document_type,
        "status": "processing",
        "hint": "Use /generate/stream for real-time progress"
    }


# ========== Download Endpoints ==========

@router.get("/download/{project_id}/{document_type}")
async def download_document(
    project_id: str,
    document_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_feature("download_files"))
):
    """
    Download generated document.

    Args:
        project_id: Project ID
        document_type: Type of document (project_report, srs, ppt, etc.)

    Returns:
        Document file (docx or pptx)
    """
    # Verify project ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.user_id == str(current_user.id)
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )

    from app.core.config import settings
    from app.services.storage_service import storage_service

    logger.info(f"[DocDownload] Downloading {document_type} for project {project_id}")

    # Map document_type parameter to database doc_type
    doc_type_map = {
        "project_report": DBDocumentType.REPORT,
        "srs": DBDocumentType.SRS,
        "ppt": DBDocumentType.PPT,
        "viva_qa": DBDocumentType.VIVA_QA,
    }

    # First, try to find document in database (S3 stored)
    target_doc_type = doc_type_map.get(document_type)
    if target_doc_type:
        doc_result = await db.execute(
            select(Document).where(
                Document.project_id == str(project_id),
                Document.doc_type == target_doc_type
            ).order_by(Document.created_at.desc())
        )
        document = doc_result.scalar_one_or_none()

        if document and document.file_path:
            logger.info(f"[DocDownload] Found document in DB: {document.file_name}, path: {document.file_path}")
            # If file_path is an S3 key, redirect to presigned URL
            if document.file_path.startswith('documents/'):
                try:
                    presigned_url = await storage_service.get_presigned_url(document.file_path)
                    from fastapi.responses import RedirectResponse
                    return RedirectResponse(url=presigned_url)
                except Exception as e:
                    logger.error(f"[DocDownload] Failed to get presigned URL: {e}")

    # Search in project docs folder (local files)
    project_docs_dir = settings.get_project_docs_dir(project_id)
    logger.info(f"[DocDownload] Checking docs dir: {project_docs_dir}")

    if project_docs_dir.exists():
        # First try exact filename match (document_type is the file stem)
        for ext in ['.docx', '.pptx', '.pdf', '.md']:
            exact_path = project_docs_dir / f"{document_type}{ext}"
            if exact_path.exists():
                content_type = _get_content_type(ext)
                logger.info(f"[DocDownload] Found exact match: {exact_path}")
                return FileResponse(
                    path=str(exact_path),
                    filename=exact_path.name,
                    media_type=content_type
                )

        # Then try pattern matching
        for file_path in project_docs_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('~$'):
                # Match by stem (filename without extension)
                if document_type in file_path.stem or file_path.stem == document_type:
                    content_type = _get_content_type(file_path.suffix)
                    logger.info(f"[DocDownload] Found pattern match: {file_path}")
                    return FileResponse(
                        path=str(file_path),
                        filename=file_path.name,
                        media_type=content_type
                    )

    # Fallback: Search in generated directories (legacy location)
    search_dirs = [
        settings.GENERATED_DIR / "documents",
        settings.GENERATED_DIR / "presentations"
    ]

    for search_dir in search_dirs:
        if search_dir.exists():
            for file_path in search_dir.iterdir():
                if file_path.is_file() and not file_path.name.startswith('~$'):
                    if document_type in file_path.stem or project_id in file_path.name:
                        content_type = _get_content_type(file_path.suffix)
                        logger.info(f"[DocDownload] Found legacy match: {file_path}")
                        return FileResponse(
                            path=str(file_path),
                            filename=file_path.name,
                            media_type=content_type
                        )

    logger.warning(f"[DocDownload] Document not found: {document_type} for project {project_id}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document not found for project {project_id}"
    )


@router.get("/download-by-id/{document_id}")
async def download_document_by_id(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_feature("download_files"))
):
    """
    Download document by its database ID.
    Supports both local files and S3 stored files.
    """
    from pathlib import Path

    # Get document from database
    try:
        doc_result = await db.execute(
            select(Document).where(Document.id == str(document_id))
        )
        document = doc_result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Verify project ownership
        project_result = await db.execute(
            select(Project).where(
                Project.id == document.project_id,
                Project.user_id == str(current_user.id)
            )
        )
        if not project_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")

        # If file_path is a local path, serve directly
        if document.file_path and Path(document.file_path).exists():
            return FileResponse(
                path=document.file_path,
                filename=document.file_name,
                media_type=document.mime_type or 'application/octet-stream'
            )

        # If file_path is S3 key, redirect to presigned URL
        if document.file_path and document.file_path.startswith('documents/'):
            from app.services.storage_service import storage_service
            presigned_url = await storage_service.get_presigned_url(document.file_path)
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=presigned_url)

        # Fallback: try file_url
        if document.file_url:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=document.file_url)

        raise HTTPException(status_code=404, detail="Document file not found")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")


def _get_content_type(extension: str) -> str:
    """Get MIME content type for file extension"""
    content_types = {
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.pdf': 'application/pdf',
        '.md': 'text/markdown'
    }
    return content_types.get(extension.lower(), 'application/octet-stream')


@router.get("/download-all/{project_id}")
async def download_all_documents(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_feature("download_files"))
):
    """
    Download all generated documents for a project as a ZIP file.

    Includes: Project Report, SRS, PPT, Viva Q&A (if available)
    """
    import zipfile
    from io import BytesIO

    # Verify project ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.user_id == str(current_user.id)
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )

    from app.core.config import settings

    # Create in-memory ZIP file
    zip_buffer = BytesIO()
    files_added = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Search in project docs folder (preferred location)
        project_docs_dir = settings.get_project_docs_dir(project_id)
        if project_docs_dir.exists():
            for file_path in project_docs_dir.iterdir():
                if file_path.is_file() and file_path.suffix in ['.docx', '.pptx', '.pdf']:
                    zip_file.write(file_path, file_path.name)
                    files_added += 1

        # Also search in legacy generated directories
        search_dirs = [
            settings.GENERATED_DIR / "documents",
            settings.GENERATED_DIR / "presentations"
        ]

        for search_dir in search_dirs:
            if search_dir.exists():
                for file_path in search_dir.glob(f"*{project_id}*"):
                    if file_path.is_file() and file_path.suffix in ['.docx', '.pptx', '.pdf']:
                        # Avoid duplicates
                        if file_path.name not in [info.filename for info in zip_file.filelist]:
                            zip_file.write(file_path, file_path.name)
                            files_added += 1

    if files_added == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found for this project"
        )

    zip_buffer.seek(0)

    # Generate filename with project name
    project_name = project.title.replace(' ', '_')[:30] if project.title else project_id[:8]
    zip_filename = f"{project_name}_documents.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"'
        }
    )


@router.get("/list/{project_id}")
async def list_project_documents(
    project_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all generated documents for a project with pagination.

    Documents are stored in S3 with metadata in PostgreSQL.
    Returns S3 URLs for direct download.
    """
    # Verify project ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.user_id == str(current_user.id)
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )

    from app.services.document_storage_service import document_storage
    from app.services.storage_service import storage_service

    documents = []

    # Get documents from database (primary source)
    db_docs_result = await db.execute(
        select(Document).where(Document.project_id == str(project_id)).order_by(Document.created_at.desc())
    )
    db_documents = db_docs_result.scalars().all()

    for doc in db_documents:
        # If file_url is expired or missing, refresh from S3
        download_url = doc.file_url
        if doc.file_path and (not download_url or 'expired' in str(download_url).lower()):
            # file_path stores the S3 key
            try:
                download_url = await storage_service.get_presigned_url(doc.file_path)
            except Exception as e:
                logger.warning(f"[DocList] Failed to get presigned URL for {doc.file_name}: {e}")
                download_url = f"/documents/download/{project_id}/{doc.id}"

        documents.append({
            "id": str(doc.id),
            "name": doc.file_name or doc.title,
            "title": doc.title,
            "type": doc.doc_type.value if doc.doc_type else "unknown",
            "status": "completed",
            "size_bytes": doc.file_size or 0,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "download_url": download_url,
            "s3_key": doc.file_path,  # S3 key for reference
            "source": "s3"
        })
        logger.info(f"[DocList] Found document: {doc.file_name or doc.title}")

    # Apply pagination
    total = len(documents)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    paginated_docs = documents[offset:offset + page_size]

    logger.info(f"[DocList] Project {project_id}: Found {total} documents in database")

    return {
        "project_id": project_id,
        "items": paginated_docs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    }


# ========== Regenerate Documents for Existing Project ==========

@router.post("/regenerate/{project_id}")
async def regenerate_all_documents(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate ALL academic documents for an existing project.

    This endpoint is for projects that were created BEFORE the document
    generation was properly configured. It reads project files from the
    database/sandbox and generates:
    - Project Report (60-80 pages)
    - SRS Document (IEEE 830 compliant)
    - PPT Presentation (20-25 slides)
    - Viva Q&A (comprehensive)

    Returns SSE stream with progress updates.
    """
    from app.models.project_file import ProjectFile
    from app.modules.agents.docspack_agent import DocsPackAgent
    from app.core.config import settings
    from sqlalchemy import cast, String
    import re

    # Verify project ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == str(project_id),
                Project.user_id == str(current_user.id)
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID"
        )

    # Get project files from database
    db_result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == cast(project_id, String(36)))
    )
    project_files = db_result.scalars().all()

    if not project_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files found for this project. Generate the project first."
        )

    # Build file list with content summary - fetch from S3 or inline
    from app.services.storage_service import storage_service as storage_svc

    files_list = []
    files_with_content = []  # For API/database extraction
    code_content = []
    for pf in project_files:
        if not pf.is_folder:
            # Get content - prioritize S3, fallback to inline for legacy data
            content = None
            if pf.s3_key:
                try:
                    content_bytes = await storage_svc.download_file(pf.s3_key)
                    content = content_bytes.decode('utf-8') if content_bytes else None
                except Exception:
                    content = pf.content_inline
            elif pf.content_inline:
                content = pf.content_inline

            if content:
                files_list.append({
                    "path": pf.path,
                    "type": "file",
                    "language": pf.language or "plaintext"
                })
                # Store file with content for API/database extraction
                files_with_content.append({
                    "path": pf.path,
                    "content": content
                })
                # Collect code content for analysis (limit to avoid token overflow)
                if len(code_content) < 20:
                    content_preview = content[:2000] if len(content) > 2000 else content
                    code_content.append(f"### {pf.path}\n```\n{content_preview}\n```")

    # Build project analysis from project metadata
    project_analysis = {
        "project_name": project.title,
        "project_purpose": project.description or f"A {project.domain or 'software'} project",
        "domain": project.domain or "Software Engineering",
        "technology_stack": {
            "backend": project.tech_stack.get("backend", {}) if project.tech_stack else {},
            "frontend": project.tech_stack.get("frontend", {}) if project.tech_stack else {},
            "database": project.tech_stack.get("database", {}) if project.tech_stack else {}
        },
        "architecture": "Modern web application architecture",
        "features": project.requirements if project.requirements else [],
        "file_structure": {"files": [f["path"] for f in files_list[:50]]}
    }

    # Build plan from project description and files
    plan = f"""
# Project: {project.title}

## Description
{project.description or 'No description provided'}

## Domain
{project.domain or 'Software'}

## Technology Stack
{json.dumps(project.tech_stack or {}, indent=2)}

## Requirements/Features
{json.dumps(project.requirements or [], indent=2)}

## Files Created
{chr(10).join([f"- {f['path']}" for f in files_list[:50]])}

## Code Overview
{chr(10).join(code_content[:10])}
"""

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting document generation...', 'progress': 0})}\n\n"

            # Initialize DocsPackAgent
            agent = DocsPackAgent(model="sonnet")

            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing project structure...', 'progress': 10})}\n\n"

            # Generate all documents
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating documentation (this may take 2-3 minutes)...', 'progress': 20})}\n\n"

            result = await agent.generate_all_documents(
                plan=plan,
                project_id=project_id,
                files=files_list,
                doc_type="academic"
            )

            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing generated content...', 'progress': 70})}\n\n"

            # Parse and save documents
            response_content = result.get("response", "")

            # Extract files from <file path="...">content</file> format
            file_pattern = r'<file path="([^"]+)">(.*?)</file>'
            matches = re.findall(file_pattern, response_content, re.DOTALL)

            # Create project docs directory
            docs_dir = settings.get_project_docs_dir(project_id)
            docs_dir.mkdir(parents=True, exist_ok=True)

            saved_docs = []
            for file_path, content in matches:
                # Save to project docs directory
                full_path = docs_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)

                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())

                saved_docs.append(file_path)
                logger.info(f"[DocRegen] Saved {file_path} for project {project_id}")

            yield f"data: {json.dumps({'type': 'status', 'message': f'Saved {len(saved_docs)} documents', 'progress': 90})}\n\n"

            # Generate Word/PPT documents using chunked_document_agent
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating Word and PPT documents...', 'progress': 92})}\n\n"

            try:
                # Extract API endpoints and database tables from generated files
                api_endpoints = chunked_document_agent._extract_api_endpoints(files_with_content)
                database_tables = chunked_document_agent._extract_database_tables(files_with_content)

                logger.info(f"[DocRegen] Extracted {len(api_endpoints)} API endpoints and {len(database_tables)} database tables")

                # Generate project report with properly extracted data
                project_data = {
                    "project_name": project.title,
                    "project_type": project.domain or "Software Project",
                    "author": current_user.full_name or current_user.email.split('@')[0],
                    "institution": current_user.college_name or "University",
                    "department": current_user.department or "Computer Science",
                    "guide": current_user.guide_name or "Guide Name",
                    "roll_number": current_user.roll_number,
                    "university_name": current_user.university_name,
                    "hod_name": current_user.hod_name,
                    "batch": current_user.batch,
                    "technologies": project.tech_stack or {},
                    "features": project.requirements or [],
                    "api_endpoints": api_endpoints,
                    "database_tables": database_tables,
                    "code_files": files_with_content[:20]  # Include content for code snippets
                }

                from app.modules.agents.base_agent import AgentContext
                context = AgentContext(
                    project_id=project_id,
                    user_id=str(current_user.id),  # IMPORTANT: Include user_id for S3/DB isolation
                    user_request=f"Generate documentation for {project.title}"
                )

                # Generate each document type
                doc_types_to_generate = [
                    (DocumentType.PROJECT_REPORT, "Project Report"),
                    (DocumentType.SRS, "SRS Document"),
                    (DocumentType.PPT, "Presentation"),
                    (DocumentType.VIVA_QA, "Viva Q&A")
                ]

                for doc_type, doc_name in doc_types_to_generate:
                    yield f"data: {json.dumps({'type': 'status', 'message': f'Generating {doc_name}...', 'progress': 93})}\n\n"
                    try:
                        async for event in chunked_document_agent.generate_document(
                            context=context,
                            document_type=doc_type,
                            project_data=project_data
                        ):
                            if event.get("type") == "complete":
                                saved_docs.append(f"{doc_name}.docx")
                                logger.info(f"[DocRegen] Generated {doc_name} for project {project_id}")
                            # Stream progress events
                            yield f"data: {json.dumps(event)}\n\n"
                            await asyncio.sleep(0.05)
                    except Exception as doc_err:
                        logger.warning(f"[DocRegen] Error generating {doc_name}: {doc_err}")
                        yield f"data: {json.dumps({'type': 'warning', 'message': f'Could not generate {doc_name}: {str(doc_err)}'})}\n\n"

            except Exception as e:
                logger.warning(f"[DocRegen] Error generating Word/PPT docs: {e}")
                yield f"data: {json.dumps({'type': 'warning', 'message': f'Word/PPT generation error: {str(e)}'})}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'message': 'Document generation complete!', 'progress': 100, 'documents': saved_docs})}\n\n"

        except Exception as e:
            logger.error(f"[DocRegen] Error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ========== Document Types Info ==========

@router.get("/types")
async def get_document_types():
    """
    Get available document types and their structure.
    """
    return {
        "document_types": [
            {
                "id": "project_report",
                "name": "Project Report",
                "description": "Complete 60-80 page academic project report",
                "estimated_pages": 70,
                "format": "docx",
                "sections": [
                    "Cover Page", "Certificate", "Declaration", "Acknowledgement",
                    "Abstract", "Table of Contents", "Introduction", "Literature Review",
                    "Requirement Analysis", "System Design", "Implementation",
                    "Testing", "Results", "Conclusion", "References", "Appendix"
                ]
            },
            {
                "id": "srs",
                "name": "Software Requirements Specification",
                "description": "IEEE 830 compliant SRS document",
                "estimated_pages": 25,
                "format": "docx",
                "sections": [
                    "Introduction", "Overall Description", "Specific Requirements",
                    "External Interfaces", "Functional Requirements",
                    "Non-Functional Requirements", "Appendix"
                ]
            },
            {
                "id": "sds",
                "name": "Software Design Specification",
                "description": "Detailed system design document",
                "estimated_pages": 30,
                "format": "docx",
                "sections": [
                    "Architecture Overview", "Database Design", "API Design",
                    "UI/UX Design", "Security Design", "Deployment Architecture"
                ]
            },
            {
                "id": "ppt",
                "name": "Project Presentation",
                "description": "Professional 20-25 slide presentation",
                "estimated_slides": 25,
                "format": "pptx",
                "sections": [
                    "Title", "Agenda", "Introduction", "Problem Statement",
                    "Objectives", "Methodology", "Architecture", "Implementation",
                    "Demo", "Testing", "Conclusion", "Future Scope", "Thank You"
                ]
            },
            {
                "id": "viva_qa",
                "name": "Viva Questions & Answers",
                "description": "Comprehensive viva preparation document with Q&A",
                "estimated_pages": 15,
                "format": "docx",
                "sections": [
                    "Project Introduction Questions", "Technology Stack Questions",
                    "System Architecture Questions", "Implementation Questions",
                    "Testing Questions", "Future Scope Questions", "General Technical Questions"
                ]
            }
        ]
    }
