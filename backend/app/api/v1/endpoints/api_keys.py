from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import generate_api_key, generate_secret_key, get_password_hash
from app.models.user import User
from app.models.api_key import APIKey, APIKeyStatus
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


class APIKeyCreate(BaseModel):
    name: str
    description: str = ""


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    secret: str = None  # Only shown on creation

    class Config:
        from_attributes = True


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create API key"""

    # Generate key and secret
    api_key = generate_api_key()
    secret_key = generate_secret_key()

    # Create API key record
    key_record = APIKey(
        user_id=current_user.id,
        key=api_key,
        secret_hash=get_password_hash(secret_key),
        name=key_data.name,
        description=key_data.description,
        status=APIKeyStatus.ACTIVE
    )

    db.add(key_record)
    await db.commit()
    await db.refresh(key_record)

    # Return with plain secret (only time it's shown)
    response = APIKeyResponse(
        id=str(key_record.id),
        name=key_record.name,
        key=api_key,
        secret=secret_key
    )

    return response


@router.get("/")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List API keys"""
    # Implementation here
    return {"keys": []}
