"""
API Keys Management Endpoint

Provides CRUD operations for user API keys with pagination support.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.core.database import get_db
from app.core.security import generate_api_key, generate_secret_key, get_password_hash
from app.models.user import User
from app.models.api_key import APIKey, APIKeyStatus
from app.modules.auth.dependencies import get_current_user
from app.utils.pagination import create_paginated_response

router = APIRouter()


# ==================== Schemas ====================

class APIKeyCreate(BaseModel):
    """Schema for creating a new API key"""
    name: str
    description: str = ""
    rate_limit: Optional[int] = 1000
    permissions: Optional[List[str]] = ["read"]


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key"""
    name: Optional[str] = None
    description: Optional[str] = None
    rate_limit: Optional[int] = None
    permissions: Optional[List[str]] = None
    status: Optional[str] = None


class APIKeyResponse(BaseModel):
    """Schema for API key response"""
    id: str
    name: str
    key_prefix: str
    description: Optional[str] = None
    status: str
    rate_limit: int
    permissions: List[str]
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    request_count: int = 0

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """Response for newly created API key (includes secret)"""
    key: str
    secret: str


class PaginatedAPIKeysResponse(BaseModel):
    """Paginated API keys response"""
    items: List[APIKeyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


# ==================== Endpoints ====================

@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key.

    The secret is only shown once upon creation - save it securely!
    """
    # Generate key and secret
    api_key = generate_api_key()
    secret_key = generate_secret_key()
    key_prefix = f"bb_{api_key[:8]}"

    # Create API key record
    key_record = APIKey(
        user_id=current_user.id,
        name=key_data.name,
        description=key_data.description,
        key_prefix=key_prefix,
        hashed_key=get_password_hash(api_key + secret_key),
        status=APIKeyStatus.ACTIVE,
        rate_limit=key_data.rate_limit,
        permissions=key_data.permissions
    )

    db.add(key_record)
    await db.commit()
    await db.refresh(key_record)

    # Return with plain secret (only time it's shown)
    return APIKeyCreateResponse(
        id=str(key_record.id),
        name=key_record.name,
        key_prefix=key_prefix,
        key=api_key,
        secret=secret_key,
        description=key_record.description,
        status=key_record.status.value,
        rate_limit=key_record.rate_limit,
        permissions=key_record.permissions or ["read"],
        last_used_at=key_record.last_used_at,
        expires_at=key_record.expires_at,
        created_at=key_record.created_at,
        request_count=key_record.request_count or 0
    )


@router.get("/", response_model=PaginatedAPIKeysResponse)
async def list_api_keys(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status (active, revoked, expired)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all API keys for the current user with pagination.
    """
    # Build base query
    query = select(APIKey).where(APIKey.user_id == current_user.id)
    count_query = select(func.count(APIKey.id)).where(APIKey.user_id == current_user.id)

    # Apply status filter
    if status_filter:
        try:
            status_enum = APIKeyStatus(status_filter)
            query = query.where(APIKey.status == status_enum)
            count_query = count_query.where(APIKey.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status filter

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(APIKey.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    keys = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedAPIKeysResponse(
        items=[
            APIKeyResponse(
                id=str(key.id),
                name=key.name,
                key_prefix=key.key_prefix or "bb_****",
                description=key.description,
                status=key.status.value if key.status else "unknown",
                rate_limit=key.rate_limit or 1000,
                permissions=key.permissions or ["read"],
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
                created_at=key.created_at,
                request_count=key.request_count or 0
            )
            for key in keys
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific API key by ID."""
    try:
        result = await db.execute(
            select(APIKey).where(
                APIKey.id == UUID(key_id),
                APIKey.user_id == current_user.id
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID"
        )

    return APIKeyResponse(
        id=str(key.id),
        name=key.name,
        key_prefix=key.key_prefix or "bb_****",
        description=key.description,
        status=key.status.value if key.status else "unknown",
        rate_limit=key.rate_limit or 1000,
        permissions=key.permissions or ["read"],
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
        created_at=key.created_at,
        request_count=key.request_count or 0
    )


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    key_data: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an API key."""
    try:
        result = await db.execute(
            select(APIKey).where(
                APIKey.id == UUID(key_id),
                APIKey.user_id == current_user.id
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID"
        )

    # Update fields
    if key_data.name is not None:
        key.name = key_data.name
    if key_data.description is not None:
        key.description = key_data.description
    if key_data.rate_limit is not None:
        key.rate_limit = key_data.rate_limit
    if key_data.permissions is not None:
        key.permissions = key_data.permissions
    if key_data.status is not None:
        try:
            key.status = APIKeyStatus(key_data.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )

    await db.commit()
    await db.refresh(key)

    return APIKeyResponse(
        id=str(key.id),
        name=key.name,
        key_prefix=key.key_prefix or "bb_****",
        description=key.description,
        status=key.status.value if key.status else "unknown",
        rate_limit=key.rate_limit or 1000,
        permissions=key.permissions or ["read"],
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
        created_at=key.created_at,
        request_count=key.request_count or 0
    )


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke (soft delete) an API key."""
    try:
        result = await db.execute(
            select(APIKey).where(
                APIKey.id == UUID(key_id),
                APIKey.user_id == current_user.id
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID"
        )

    # Soft delete - mark as revoked
    key.status = APIKeyStatus.REVOKED

    await db.commit()

    return {"success": True, "message": "API key revoked"}


@router.delete("/{key_id}/permanent")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete an API key."""
    try:
        result = await db.execute(
            select(APIKey).where(
                APIKey.id == UUID(key_id),
                APIKey.user_id == current_user.id
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID"
        )

    await db.delete(key)
    await db.commit()

    return {"success": True, "message": "API key permanently deleted"}
