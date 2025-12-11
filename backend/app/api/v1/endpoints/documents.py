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


@router.get("/download-all/{project_id}")
async def download_all_documents(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
                Project.id == UUID(project_id),
                Project.user_id == current_user.id
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
                Project.id == UUID(project_id),
                Project.user_id == current_user.id
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

    # Build file list with content summary
    files_list = []
    code_content = []
    for pf in project_files:
        if not pf.is_folder and pf.content_inline:
            files_list.append({
                "path": pf.path,
                "type": "file",
                "language": pf.language or "plaintext"
            })
            # Collect code content for analysis (limit to avoid token overflow)
            if len(code_content) < 20:
                content_preview = pf.content_inline[:2000] if len(pf.content_inline) > 2000 else pf.content_inline
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
                # Generate project report
                project_data = {
                    "project_name": project.title,
                    "project_type": project.domain or "Software Project",
                    "author": current_user.full_name or current_user.email.split('@')[0],
                    "institution": "University",
                    "department": "Computer Science",
                    "guide": "Guide Name",
                    "technologies": project.tech_stack or {},
                    "features": project.requirements or [],
                    "api_endpoints": [],
                    "database_tables": [],
                    "code_files": [{"path": f["path"]} for f in files_list[:20]]
                }

                from app.modules.agents.base_agent import AgentContext
                context = AgentContext(
                    project_id=project_id,
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
