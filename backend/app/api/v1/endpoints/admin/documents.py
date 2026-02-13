"""
Admin Document Management endpoints.
Allows admins to view and download user-generated academic documents.
Supports filtering by user name/email and project title.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc
from datetime import datetime, timedelta
from typing import Optional
import math

from app.core.database import get_db
from app.models import User, Project, Document
from app.models.document import DocumentType
from app.modules.auth.dependencies import get_current_admin
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("")
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    doc_type: Optional[str] = None,
    user_id: Optional[str] = None,
    user_search: Optional[str] = None,  # Search by user name/email
    project_id: Optional[str] = None,
    project_search: Optional[str] = None,  # Search by project title
    sort_by: str = Query("created_at", regex="^(created_at|title|doc_type|file_size)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    List all documents with filtering, sorting, and pagination.
    Admins can see documents from all users.
    """
    # Build query with joins to get user and project info
    query = (
        select(Document, Project, User)
        .join(Project, Document.project_id == Project.id)
        .join(User, Project.user_id == User.id)
    )

    # Apply filters
    conditions = []

    if search:
        search_term = f"%{search}%"
        conditions.append(or_(
            Document.title.ilike(search_term),
            Document.file_name.ilike(search_term),
            Project.title.ilike(search_term),
            User.email.ilike(search_term),
            User.full_name.ilike(search_term)
        ))

    if doc_type:
        try:
            doc_type_enum = DocumentType(doc_type)
            conditions.append(Document.doc_type == doc_type_enum)
        except ValueError:
            pass

    if user_id:
        conditions.append(Project.user_id == user_id)

    if user_search:
        user_term = f"%{user_search}%"
        conditions.append(or_(
            User.email.ilike(user_term),
            User.full_name.ilike(user_term)
        ))

    if project_id:
        conditions.append(Document.project_id == project_id)

    if project_search:
        project_term = f"%{project_search}%"
        conditions.append(Project.title.ilike(project_term))

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(
        select(Document.id)
        .join(Project, Document.project_id == Project.id)
        .join(User, Project.user_id == User.id)
        .where(and_(*conditions) if conditions else True)
        .subquery()
    )
    total = await db.scalar(count_query)

    # Apply sorting
    sort_column = getattr(Document, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Build response
    items = []
    for document, project, user in rows:
        items.append({
            "id": str(document.id),
            "title": document.title,
            "doc_type": document.doc_type.value if document.doc_type else None,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "project_id": str(project.id),
            "project_title": project.title,
            "user_id": str(user.id),
            "user_email": user.email,
            "user_name": user.full_name
        })

    return {
        "items": items,
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil((total or 0) / page_size) if total and total > 0 else 1
    }


@router.get("/stats")
async def get_document_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get document statistics"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start.replace(day=1)

    # Total documents
    total_documents = await db.scalar(select(func.count(Document.id)))

    # Documents by type
    type_counts = {}
    for doc_type in DocumentType:
        count = await db.scalar(
            select(func.count(Document.id)).where(Document.doc_type == doc_type)
        )
        type_counts[doc_type.value] = count or 0

    # Documents created today/week/month
    docs_today = await db.scalar(
        select(func.count(Document.id)).where(Document.created_at >= today_start)
    )
    docs_this_week = await db.scalar(
        select(func.count(Document.id)).where(Document.created_at >= week_start)
    )
    docs_this_month = await db.scalar(
        select(func.count(Document.id)).where(Document.created_at >= month_start)
    )

    # Total storage size
    total_size = await db.scalar(select(func.sum(Document.file_size)))

    return {
        "total_documents": total_documents or 0,
        "documents_by_type": type_counts,
        "documents_today": docs_today or 0,
        "documents_this_week": docs_this_week or 0,
        "documents_this_month": docs_this_month or 0,
        "total_storage_mb": round((total_size or 0) / (1024 * 1024), 2)
    }


@router.get("/types")
async def get_document_types(
    current_admin: User = Depends(get_current_admin)
):
    """Get all available document types"""
    return {
        "types": [
            {"value": doc_type.value, "label": doc_type.value.upper().replace("_", " ")}
            for doc_type in DocumentType
        ]
    }


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Download a specific document by ID.
    Admin can download any user's document.
    """
    # Get document with project and user info
    result = await db.execute(
        select(Document, Project, User)
        .join(Project, Document.project_id == Project.id)
        .join(User, Project.user_id == User.id)
        .where(Document.id == document_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    document, project, user = row

    # Try to get file from S3
    if document.file_path:
        try:
            content = await storage_service.download_file(document.file_path)
            if content:
                # Determine filename
                filename = document.file_name or f"{document.title}.docx"

                return StreamingResponse(
                    iter([content]),
                    media_type=document.mime_type or "application/octet-stream",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                        "Content-Length": str(len(content))
                    }
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

    # Fallback: if document has content stored inline
    if document.content:
        return StreamingResponse(
            iter([document.content.encode('utf-8')]),
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{document.title}.txt"'
            }
        )

    raise HTTPException(status_code=404, detail="Document file not found in storage")


@router.get("/user/{user_id}")
async def get_user_documents(
    user_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get all documents for a specific user.
    """
    # Verify user exists
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get documents for this user
    query = (
        select(Document, Project)
        .join(Project, Document.project_id == Project.id)
        .where(Project.user_id == user_id)
        .order_by(desc(Document.created_at))
    )

    # Get total count
    count_query = select(func.count()).select_from(
        select(Document.id)
        .join(Project, Document.project_id == Project.id)
        .where(Project.user_id == user_id)
        .subquery()
    )
    total = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for document, project in rows:
        items.append({
            "id": str(document.id),
            "title": document.title,
            "doc_type": document.doc_type.value if document.doc_type else None,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "project_id": str(project.id),
            "project_title": project.title
        })

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name
        },
        "items": items,
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil((total or 0) / page_size) if total and total > 0 else 1
    }
