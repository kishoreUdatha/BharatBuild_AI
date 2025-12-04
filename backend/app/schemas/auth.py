from pydantic import BaseModel, EmailStr, Field, field_serializer
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: str = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str
    email: str
    role: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    avatar_url: Optional[str] = None
    oauth_provider: Optional[str] = None

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    class Config:
        from_attributes = True


# ============================================
# OAuth Schemas
# ============================================

class GoogleAuthRequest(BaseModel):
    """Request for Google OAuth with ID token (from Google Sign-In button)."""
    credential: str  # Google ID token from frontend


class OAuthCodeRequest(BaseModel):
    """Request for OAuth with authorization code."""
    code: str
    state: Optional[str] = None
    redirect_uri: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    """Request from OAuth callback with code and optional role."""
    code: str
    state: Optional[str] = None
    role: str = "student"  # Default role for new OAuth users


class OAuthUrlResponse(BaseModel):
    """Response containing OAuth authorization URL."""
    authorization_url: str
    state: Optional[str] = None


class OAuthTokenResponse(BaseModel):
    """Response after successful OAuth authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool = False
