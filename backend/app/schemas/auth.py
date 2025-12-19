from pydantic import BaseModel, EmailStr, Field, field_serializer, model_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone: Optional[str] = Field(None, pattern=r'^[6-9]\d{9}$', description="10-digit Indian mobile number")
    role: str = "student"

    # Student Academic Details
    roll_number: Optional[str] = None
    college_name: Optional[str] = None
    university_name: Optional[str] = None
    department: Optional[str] = None
    course: Optional[str] = None
    year_semester: Optional[str] = None
    batch: Optional[str] = None

    # Guide/Mentor Details
    guide_name: Optional[str] = None
    guide_designation: Optional[str] = None
    hod_name: Optional[str] = None

    @model_validator(mode='after')
    def validate_student_fields(self):
        """Validate required fields for student role"""
        if self.role == 'student':
            missing_fields = []

            # Required academic fields for students
            if not self.roll_number or not self.roll_number.strip():
                missing_fields.append('Roll Number')
            if not self.college_name or not self.college_name.strip():
                missing_fields.append('College Name')
            if not self.department or not self.department.strip():
                missing_fields.append('Department')
            if not self.course or not self.course.strip():
                missing_fields.append('Course')

            # Required guide field for students
            if not self.guide_name or not self.guide_name.strip():
                missing_fields.append('Guide Name')

            if missing_fields:
                raise ValueError(f"Required fields for students: {', '.join(missing_fields)}")

        return self


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
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    avatar_url: Optional[str] = None
    oauth_provider: Optional[str] = None

    # Student Academic Details
    roll_number: Optional[str] = None
    college_name: Optional[str] = None
    university_name: Optional[str] = None
    department: Optional[str] = None
    course: Optional[str] = None
    year_semester: Optional[str] = None
    batch: Optional[str] = None

    # Guide/Mentor Details
    guide_name: Optional[str] = None
    guide_designation: Optional[str] = None
    hod_name: Optional[str] = None

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


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
