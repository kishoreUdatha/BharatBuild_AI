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
from app.models.project import Project
from app.models.document import Document
from app.modules.auth.dependencies import get_current_user
from app.modules.agents.chunked_document_agent import (
    chunked_document_agent,
    DocumentType
)
from app.core.logging_config import logger
from app.utils.pagination import create_paginated_response


router = APIRouter()


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
    db: AsyncSession = Depends(get_db)
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
            Project.id == UUID(request.project_id),
            Project.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    async def event_generator():
        try:
            # Convert request to document type
            try:
                doc_type = DocumentType(request.document_type)
            except ValueError:
                yield f"data: {json.dumps({'type': 'error', 'error': f'Invalid document type: {request.document_type}'})}\n\n"
                return

            # Build project data
            project_data = {
                "project_name": request.project_name,
                "project_type": request.project_type,
                "author": request.author,
                "institution": request.institution,
                "department": request.department,
                "guide": request.guide,
                "technologies": request.technologies,
                "features": request.features,
                "api_endpoints": request.api_endpoints,
                "database_tables": request.database_tables,
                "code_files": request.code_files
            }

            # Create agent context
            from app.modules.agents.base_agent import AgentContext
            context = AgentContext(
                project_id=request.project_id,
                user_request=f"Generate {request.document_type} for {request.project_name}"
            )

            # Stream generation progress
            async for event in chunked_document_agent.generate_document(
                context=context,
                document_type=doc_type,
                project_data=project_data
            ):
                yield f"data: {json.dumps(event)}\n\n"
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
    db: AsyncSession = Depends(get_db)
):
    """
    Start document generation (non-streaming).

    Returns immediately with task ID for polling status.
    """
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == UUID(request.project_id),
            Project.user_id == current_user.id
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
    db: AsyncSession = Depends(get_db)
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
                Project.id == UUID(project_id),
                Project.user_id == current_user.id
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

    # Find document in generated directory
    if document_type == "ppt":
        file_pattern = f"*{project_id}*.pptx"
        content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    else:
        file_pattern = f"*{project_id}*{document_type}*.docx"
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # Search in project docs folder first (preferred location)
    project_docs_dir = settings.get_project_docs_dir(project_id)
    if project_docs_dir.exists():
        for file_path in project_docs_dir.glob(file_pattern):
            if file_path.exists():
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
            for file_path in search_dir.glob(file_pattern):
                if file_path.exists():
                    return FileResponse(
                        path=str(file_path),
                        filename=file_path.name,
                        media_type=content_type
                    )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document not found for project {project_id}"
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
    """
    # Verify project ownership
    try:
        result = await db.execute(
            select(Project).where(
                Project.id == UUID(project_id),
                Project.user_id == current_user.id
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

    documents = []

    # First, get documents from database
    db_docs_result = await db.execute(
        select(Document).where(Document.project_id == UUID(project_id))
    )
    db_documents = db_docs_result.scalars().all()

    for doc in db_documents:
        documents.append({
            "id": str(doc.id),
            "name": doc.title,
            "type": doc.document_type.value if doc.document_type else "unknown",
            "status": doc.status,
            "size_bytes": doc.file_size or 0,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "download_url": f"/api/v1/documents/download/{project_id}/{doc.document_type.value if doc.document_type else 'unknown'}",
            "source": "database"
        })

    # Search in project docs folder (file system)
    project_docs_dir = settings.get_project_docs_dir(project_id)
    if project_docs_dir.exists():
        for file_path in project_docs_dir.iterdir():
            if file_path.is_file():
                doc_type = "presentations" if file_path.suffix == ".pptx" else "documents"
                # Avoid duplicates with database entries
                if not any(d.get("name") == file_path.name for d in documents):
                    documents.append({
                        "id": None,
                        "name": file_path.name,
                        "type": doc_type,
                        "status": "completed",
                        "size_bytes": file_path.stat().st_size,
                        "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                        "download_url": f"/api/v1/documents/download/{project_id}/{file_path.stem}",
                        "source": "filesystem"
                    })

    # Also search in legacy generated directories
    search_dirs = [
        ("documents", settings.GENERATED_DIR / "documents"),
        ("presentations", settings.GENERATED_DIR / "presentations")
    ]

    for doc_type, search_dir in search_dirs:
        if search_dir.exists():
            for file_path in search_dir.glob(f"*{project_id}*"):
                if file_path.is_file():
                    # Avoid duplicates
                    if not any(d.get("name") == file_path.name for d in documents):
                        documents.append({
                            "id": None,
                            "name": file_path.name,
                            "type": doc_type,
                            "status": "completed",
                            "size_bytes": file_path.stat().st_size,
                            "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                            "download_url": f"/api/v1/documents/download/{project_id}/{file_path.stem}",
                            "source": "filesystem"
                        })

    # Sort by created_at descending
    documents.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    # Apply pagination
    total = len(documents)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    paginated_docs = documents[offset:offset + page_size]

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
