"""
Admin API Keys Management endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime
from typing import Optional
import math

from app.core.database import get_db
from app.models import User, APIKey, APIKeyStatus, AuditLog
from app.modules.auth.dependencies import get_current_admin
from app.schemas.admin import AdminApiKeyResponse, AdminApiKeysResponse

router = APIRouter()


@router.get("", response_model=AdminApiKeysResponse)
async def list_api_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all API keys across users"""
    query = select(APIKey, User).join(User, APIKey.user_id == User.id)

    conditions = []
    if search:
        search_term = f"%{search}%"
        conditions.append(or_(
            APIKey.name.ilike(search_term),
            User.email.ilike(search_term)
        ))

    if status:
        try:
            status_enum = APIKeyStatus(status)
            conditions.append(APIKey.status == status_enum)
        except ValueError:
            pass

    if user_id:
        conditions.append(APIKey.user_id == user_id)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(
        select(APIKey).join(User, APIKey.user_id == User.id)
        .where(and_(*conditions) if conditions else True)
        .subquery()
    )
    total = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(APIKey.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for api_key, user in rows:
        items.append(AdminApiKeyResponse(
            id=str(api_key.id),
            user_id=str(api_key.user_id),
            user_email=user.email,
            name=api_key.name,
            key_prefix=api_key.key[:8] if api_key.key else "bb_****",
            status=api_key.status.value if api_key.status else "active",
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            rate_limit_per_hour=api_key.rate_limit_per_hour,
            rate_limit_per_day=api_key.rate_limit_per_day,
            token_limit=api_key.token_limit,
            tokens_used=api_key.tokens_used or 0,
            requests_count=api_key.request_count or 0,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at
        ))

    return AdminApiKeysResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=math.ceil((total or 0) / page_size) if total and total > 0 else 1
    )


@router.get("/stats")
async def get_api_key_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get API key usage statistics"""
    # Total keys
    total_keys = await db.scalar(select(func.count(APIKey.id)))

    # Keys by status
    status_counts = {}
    for status in APIKeyStatus:
        count = await db.scalar(
            select(func.count(APIKey.id)).where(APIKey.status == status)
        )
        status_counts[status.value] = count or 0

    # Total tokens used via API keys
    total_tokens = await db.scalar(
        select(func.coalesce(func.sum(APIKey.tokens_used), 0))
    )

    # Total requests
    total_requests = await db.scalar(
        select(func.coalesce(func.sum(APIKey.request_count), 0))
    )

    # Top API keys by usage
    top_keys_query = (
        select(APIKey.name, APIKey.key, User.email, APIKey.request_count, APIKey.tokens_used)
        .join(User, APIKey.user_id == User.id)
        .where(APIKey.status == APIKeyStatus.ACTIVE)
        .order_by(APIKey.request_count.desc().nullslast())
        .limit(10)
    )
    result = await db.execute(top_keys_query)
    top_keys = [
        {
            "name": row.name,
            "key_prefix": row.key[:8] if row.key else "bb_****",
            "user_email": row.email,
            "requests": row.request_count or 0,
            "tokens_used": row.tokens_used or 0
        }
        for row in result
    ]

    return {
        "total_keys": total_keys or 0,
        "keys_by_status": status_counts,
        "total_tokens_used": total_tokens or 0,
        "total_requests": total_requests or 0,
        "top_keys": top_keys
    }


@router.get("/{key_id}")
async def get_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get details of a specific API key"""
    result = await db.execute(
        select(APIKey, User)
        .join(User, APIKey.user_id == User.id)
        .where(APIKey.id == key_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key, user = row

    return {
        "id": str(api_key.id),
        "user_id": str(api_key.user_id),
        "user_email": user.email,
        "user_name": user.full_name,
        "name": api_key.name,
        "key_prefix": api_key.key[:8] if api_key.key else "bb_****",
        "status": api_key.status.value if api_key.status else "active",
        "rate_limit_per_minute": api_key.rate_limit_per_minute,
        "rate_limit_per_hour": api_key.rate_limit_per_hour,
        "rate_limit_per_day": api_key.rate_limit_per_day,
        "token_limit": api_key.token_limit,
        "tokens_used": api_key.tokens_used or 0,
        "requests_count": api_key.request_count or 0,
        "allowed_modes": api_key.allowed_modes,
        "allowed_ips": api_key.allowed_ips,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None
    }


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    request: Request,
    reason: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Revoke an API key"""
    api_key = await db.get(APIKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if api_key.status == APIKeyStatus.REVOKED:
        raise HTTPException(status_code=400, detail="API key already revoked")

    api_key.status = APIKeyStatus.REVOKED
    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="api_key_revoked",
        target_type="api_key",
        target_id=key_id,
        details={"name": api_key.name, "reason": reason},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"API key '{api_key.name}' has been revoked"}


@router.post("/{key_id}/activate")
async def activate_api_key(
    key_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Reactivate a revoked or inactive API key"""
    api_key = await db.get(APIKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if api_key.status == APIKeyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="API key is already active")

    api_key.status = APIKeyStatus.ACTIVE
    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="api_key_activated",
        target_type="api_key",
        target_id=key_id,
        details={"name": api_key.name},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"API key '{api_key.name}' has been activated"}


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Permanently delete an API key"""
    api_key = await db.get(APIKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    key_name = api_key.name
    await db.delete(api_key)
    await db.commit()

    # Log action
    log = AuditLog(
        admin_id=str(current_admin.id),
        action="api_key_deleted",
        target_type="api_key",
        target_id=key_id,
        details={"name": key_name},
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(log)
    await db.commit()

    return {"message": f"API key '{key_name}' has been deleted"}
