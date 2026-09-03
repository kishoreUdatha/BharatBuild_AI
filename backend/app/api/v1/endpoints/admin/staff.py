"""
Creating staff accounts.

Reachable by the platform operator, who creates a newly onboarded college's
first administrator, and by a college's own admin, who creates their guides and
trainers. The service decides which college the account lands in - a college
admin cannot name one.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.modules.auth.dependencies import get_current_admin
from app.services.account_invites import AccountInviteService, InviteError

router = APIRouter(prefix="/staff", tags=["Admin - Staff"])


class StaffIn(BaseModel):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str
    college_id: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


@router.get("/options")
async def staff_options(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """The roles this admin may create, and the colleges they may create in."""
    return await AccountInviteService(db).options(current_user)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_staff(
    body: StaffIn,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an account and email its owner a link to set a password.

    No password is chosen here by anyone. Handing somebody a password to pass
    on is how shared credentials start.
    """
    try:
        return await AccountInviteService(db).create(
            current_user,
            email=body.email,
            full_name=body.full_name,
            role=body.role,
            college_id=body.college_id,
            department=body.department,
            phone=body.phone,
        )
    except InviteError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{user_id}/resend")
async def resend_invite(
    user_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Send the set-a-password link again."""
    try:
        return await AccountInviteService(db).resend(current_user, user_id)
    except InviteError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
