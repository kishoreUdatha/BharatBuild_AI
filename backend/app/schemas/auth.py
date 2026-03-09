from pydantic import BaseModel, EmailStr, Field, field_serializer, model_validator, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


# Password policy configuration
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True
PASSWORD_SPECIAL_CHARS = r'!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~'


def validate_password_strength(password: str) -> str:
    """
    Validate password against security policies.

    Requirements:
    - Minimum 8 characters
    - Maximum 128 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    errors = []

    # Length checks
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"at least {PASSWORD_MIN_LENGTH} characters")

    if len(password) > PASSWORD_MAX_LENGTH:
        errors.append(f"maximum {PASSWORD_MAX_LENGTH} characters")

    # Uppercase check
    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors.append("at least 1 uppercase letter")

    # Lowercase check
    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors.append("at least 1 lowercase letter")

    # Digit check
    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        errors.append("at least 1 number")

    # Special character check
    if PASSWORD_REQUIRE_SPECIAL and not re.search(f'[{re.escape(PASSWORD_SPECIAL_CHARS)}]', password):
        errors.append("at least 1 special character (!@#$%^&*)")

    if errors:
        raise ValueError(f"Password must contain: {', '.join(errors)}")

    return password


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
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

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets security requirements"""
        return validate_password_strength(v)

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
