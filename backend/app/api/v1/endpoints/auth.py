from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import secrets
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.logging_config import logger, set_user_id
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    LoginResponse,
    UserResponse,
    GoogleAuthRequest,
    OAuthCallbackRequest,
    OAuthUrlResponse,
    OAuthTokenResponse,
)
from app.modules.auth.dependencies import get_current_user
from app.modules.oauth.google_provider import google_oauth
from app.modules.oauth.github_provider import github_oauth
from app.services.email_service import email_service
from app.core.rate_limiter import limiter, auth_rate_limit, strict_rate_limit


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ResendVerificationRequest(BaseModel):
    email: str


class VerifyEmailRequest(BaseModel):
    token: str


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register new user (rate limited: 3/min)"""
    client_ip = request.client.host if request.client else "unknown"

    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.log_auth_event(
            event="register",
            success=False,
            user_email=user_data.email,
            reason="Email already registered",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if phone number already exists (if provided)
    if user_data.phone:
        result = await db.execute(
            select(User).where(User.phone == user_data.phone)
        )
        existing_phone_user = result.scalar_one_or_none()

        if existing_phone_user:
            logger.log_auth_event(
                event="register",
                success=False,
                user_email=user_data.email,
                reason="Phone number already registered",
                client_ip=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

    # Create user - convert role string to UserRole enum
    try:
        user_role = UserRole(user_data.role)
    except ValueError:
        user_role = UserRole.STUDENT  # Default to student if invalid role

    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_role,
        # Student Academic Details
        roll_number=user_data.roll_number,
        college_name=user_data.college_name,
        university_name=user_data.university_name,
        department=user_data.department,
        course=user_data.course,
        year_semester=user_data.year_semester,
        batch=user_data.batch,
        # Guide/Mentor Details
        guide_name=user_data.guide_name,
        guide_designation=user_data.guide_designation,
        hod_name=user_data.hod_name
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.log_auth_event(
        event="register",
        success=True,
        user_email=user_data.email,
        client_ip=client_ip,
        user_role=user_role.value
    )

    # Send verification email (async, don't block registration)
    try:
        from jose import jwt
        verification_token_data = {
            "sub": str(user.id),
            "email": user.email,
            "type": "email_verification",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        verification_token = jwt.encode(
            verification_token_data,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        # Send email in background (don't wait)
        import asyncio
        asyncio.create_task(
            email_service.send_verification_email(
                to_email=user.email,
                user_name=user.full_name,
                verification_token=verification_token
            )
        )
        logger.info(f"[Auth] Verification email queued for {user.email}")
    except Exception as e:
        # Don't fail registration if email fails
        logger.warning(f"[Auth] Failed to send verification email: {e}")

    return user


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email address using token from email.

    Token is valid for 24 hours.
    """
    try:
        from jose import jwt, JWTError

        payload = jwt.decode(
            request.token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != "email_verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )

        user_id = payload.get("sub")
        email = payload.get("email")

        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if email matches (security check)
        if user.email != email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token email mismatch"
            )

        # Already verified?
        if user.is_verified:
            return {
                "success": True,
                "message": "Email already verified",
                "already_verified": True
            }

        # Mark as verified
        user.is_verified = True
        await db.commit()

        logger.log_auth_event(
            event="email_verified",
            success=True,
            user_email=user.email
        )

        # Send welcome email
        try:
            import asyncio
            asyncio.create_task(
                email_service.send_welcome_email(
                    to_email=user.email,
                    user_name=user.full_name
                )
            )
        except Exception:
            pass  # Don't fail verification if welcome email fails

        return {
            "success": True,
            "message": "Email verified successfully! You can now log in.",
            "already_verified": False
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )


@router.post("/resend-verification")
async def resend_verification_email(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend verification email.

    Rate limited to prevent abuse.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return {
            "success": True,
            "message": "If an account with that email exists, a verification email has been sent."
        }

    # Already verified?
    if user.is_verified:
        return {
            "success": True,
            "message": "This email is already verified. You can log in."
        }

    # Generate new verification token
    try:
        from jose import jwt
        verification_token_data = {
            "sub": str(user.id),
            "email": user.email,
            "type": "email_verification",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        verification_token = jwt.encode(
            verification_token_data,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        # Send verification email
        email_sent = await email_service.send_verification_email(
            to_email=user.email,
            user_name=user.full_name,
            verification_token=verification_token
        )

        if email_sent:
            logger.info(f"[Auth] Verification email resent to {user.email}")
        else:
            logger.warning(f"[Auth] Failed to resend verification email to {user.email}")

    except Exception as e:
        logger.error(f"[Auth] Error resending verification email: {e}")

    return {
        "success": True,
        "message": "If an account with that email exists, a verification email has been sent."
    }


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user (rate limited: 5/min)"""
    client_ip = request.client.host if request.client else "unknown"

    # Get user
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.log_auth_event(
            event="login",
            success=False,
            user_email=credentials.email,
            reason="Invalid credentials",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        logger.log_auth_event(
            event="login",
            success=False,
            user_email=credentials.email,
            reason="Account inactive",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Set user context for downstream logging
    set_user_id(str(user.id))

    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.log_auth_event(
        event="login",
        success=True,
        user_email=user.email,
        client_ip=client_ip,
        user_role=user.role.value
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            avatar_url=user.avatar_url,
            oauth_provider=user.oauth_provider,
            # Student Academic Details
            roll_number=user.roll_number,
            college_name=user.college_name,
            university_name=user.university_name,
            department=user.department,
            course=user.course,
            year_semester=user.year_semester,
            batch=user.batch,
            # Guide/Mentor Details
            guide_name=user.guide_name,
            guide_designation=user.guide_designation,
            hod_name=user.hod_name
        )
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user info"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_request: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    client_ip = request.client.host if request.client else "unknown"

    try:
        # Decode the refresh token
        payload = decode_token(token_request.refresh_token)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            logger.log_auth_event(
                event="token_refresh",
                success=False,
                reason="Invalid token type",
                client_ip=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type - expected refresh token"
            )

        # Get user from database
        user_id = payload.get("sub")
        try:
            uuid.UUID(user_id)  # Just validate format
        except ValueError:
            logger.log_auth_event(
                event="token_refresh",
                success=False,
                reason="Invalid user ID format",
                client_ip=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format"
            )
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.log_auth_event(
                event="token_refresh",
                success=False,
                reason="User not found",
                client_ip=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
            logger.log_auth_event(
                event="token_refresh",
                success=False,
                user_email=user.email,
                reason="Account inactive",
                client_ip=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )

        # Create new tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value
        }

        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        logger.log_auth_event(
            event="token_refresh",
            success=True,
            user_email=user.email,
            client_ip=client_ip
        )

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.log_auth_event(
            event="token_refresh",
            success=False,
            reason=f"Token error: {str(e)}",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.get("/validate-token")
async def validate_token(
    current_user: User = Depends(get_current_user)
):
    """
    Validate token for CLI authentication.

    CLI calls this endpoint to verify the token is valid
    and get user info for local storage.
    """
    return {
        "valid": True,
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.full_name,
            "role": current_user.role.value,
            "college_name": getattr(current_user, 'college_name', None),
            "department": getattr(current_user, 'department', None),
            "roll_number": getattr(current_user, 'roll_number', None)
        }
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout user.

    Note: JWT tokens are stateless, so this endpoint primarily:
    1. Logs the logout event
    2. Returns success for frontend to clear local storage

    For enhanced security, implement token blacklisting with Redis.
    """
    logger.log_auth_event(
        event="logout",
        success=True,
        user_email=current_user.email
    )
    return {"message": "Successfully logged out", "success": True}


# ============================================
# Profile Completion (for OAuth users)
# ============================================

class ProfileCompletionRequest(BaseModel):
    """Request to complete user profile after OAuth signup"""
    # Basic info
    full_name: Optional[str] = None
    phone: Optional[str] = None

    # Role selection
    role: Optional[str] = None

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


@router.patch("/me/profile", response_model=UserResponse)
async def complete_profile(
    profile_data: ProfileCompletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete or update user profile.

    Used after OAuth signup to collect additional information
    like student academic details, role selection, etc.
    """
    # Update basic info
    if profile_data.full_name:
        current_user.full_name = profile_data.full_name
    if profile_data.phone:
        current_user.phone = profile_data.phone

    # Update role (validate it's allowed)
    if profile_data.role:
        validated_role = validate_oauth_role(profile_data.role)
        current_user.role = validated_role

    # Update student academic details
    if profile_data.roll_number is not None:
        current_user.roll_number = profile_data.roll_number
    if profile_data.college_name is not None:
        current_user.college_name = profile_data.college_name
    if profile_data.university_name is not None:
        current_user.university_name = profile_data.university_name
    if profile_data.department is not None:
        current_user.department = profile_data.department
    if profile_data.course is not None:
        current_user.course = profile_data.course
    if profile_data.year_semester is not None:
        current_user.year_semester = profile_data.year_semester
    if profile_data.batch is not None:
        current_user.batch = profile_data.batch

    # Update guide/mentor details
    if profile_data.guide_name is not None:
        current_user.guide_name = profile_data.guide_name
    if profile_data.guide_designation is not None:
        current_user.guide_designation = profile_data.guide_designation
    if profile_data.hod_name is not None:
        current_user.hod_name = profile_data.hod_name

    # Mark profile as completed
    current_user.profile_completed = True
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)

    logger.info(f"[Auth] Profile completed for user {current_user.email}")

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role.value,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        avatar_url=current_user.avatar_url,
        oauth_provider=current_user.oauth_provider,
        roll_number=current_user.roll_number,
        college_name=current_user.college_name,
        university_name=current_user.university_name,
        department=current_user.department,
        course=current_user.course,
        year_semester=current_user.year_semester,
        batch=current_user.batch,
        guide_name=current_user.guide_name,
        guide_designation=current_user.guide_designation,
        hod_name=current_user.hod_name
    )


@router.get("/me/profile-status")
async def get_profile_status(
    current_user: User = Depends(get_current_user)
):
    """
    Check if user profile is complete.

    Returns whether the user needs to complete their profile
    (e.g., after OAuth signup).
    """
    # For students, check if academic details are filled
    is_student = current_user.role == UserRole.STUDENT

    profile_complete = True
    missing_fields = []

    if is_student:
        if not current_user.roll_number:
            profile_complete = False
            missing_fields.append("roll_number")
        if not current_user.college_name:
            profile_complete = False
            missing_fields.append("college_name")
        if not current_user.department:
            profile_complete = False
            missing_fields.append("department")

    return {
        "profile_complete": profile_complete,
        "missing_fields": missing_fields,
        "role": current_user.role.value,
        "is_oauth_user": current_user.oauth_provider is not None
    }


# ============================================
# OAuth Endpoints - Google
# ============================================

@router.get("/google/url", response_model=OAuthUrlResponse)
@router.get("/google/authorize", response_model=OAuthUrlResponse)
async def get_google_auth_url():
    """Get Google OAuth authorization URL."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    state = secrets.token_urlsafe(32)
    authorization_url = google_oauth.get_authorization_url(state=state)

    return OAuthUrlResponse(
        authorization_url=authorization_url,
        state=state
    )


# Allowed roles for OAuth registration (exclude admin)
ALLOWED_OAUTH_ROLES = {UserRole.STUDENT, UserRole.DEVELOPER, UserRole.FOUNDER, UserRole.FACULTY}


def validate_oauth_role(role_value: str) -> UserRole:
    """Validate and return a safe role for OAuth users."""
    try:
        role = UserRole(role_value)
        if role in ALLOWED_OAUTH_ROLES:
            return role
    except ValueError:
        pass
    return UserRole.STUDENT  # Default to student for invalid/admin roles


@router.post("/google/callback", response_model=OAuthTokenResponse)
async def google_oauth_callback(
    oauth_request: OAuthCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback with authorization code."""
    client_ip = request.client.host if request.client else "unknown"

    if not settings.GOOGLE_CLIENT_ID:
        logger.log_auth_event(
            event="google_oauth",
            success=False,
            reason="Google OAuth not configured",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    # Validate role before proceeding
    validated_role = validate_oauth_role(oauth_request.role)

    # Authenticate with Google
    user_data = await google_oauth.authenticate(oauth_request.code)

    if not user_data:
        logger.log_auth_event(
            event="google_oauth",
            success=False,
            reason="Google authentication failed",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with Google"
        )

    google_id = user_data.get("google_id")
    email = user_data.get("email")

    if not email:
        logger.log_auth_event(
            event="google_oauth",
            success=False,
            reason="Email not provided by Google",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Google"
        )

    # Check if user exists by Google ID or email
    result = await db.execute(
        select(User).where(
            or_(User.google_id == google_id, User.email == email)
        )
    )
    user = result.scalar_one_or_none()

    is_new_user = False
    needs_profile_completion = False

    if user:
        # Update Google ID if not set (linking existing account)
        if not user.google_id:
            user.google_id = google_id
            user.oauth_provider = "google"
            if user_data.get("avatar_url") and not user.avatar_url:
                user.avatar_url = user_data.get("avatar_url")
        user.last_login = datetime.utcnow()
        # Check if profile is incomplete
        needs_profile_completion = not user.profile_completed
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user with validated role
        is_new_user = True
        needs_profile_completion = True
        user = User(
            email=email,
            google_id=google_id,
            full_name=user_data.get("full_name", ""),
            avatar_url=user_data.get("avatar_url", ""),
            oauth_provider="google",
            is_verified=user_data.get("email_verified", False),
            role=validated_role,  # Use validated role
            hashed_password="",  # No password for OAuth users
            profile_completed=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.log_auth_event(
        event="google_oauth",
        success=True,
        user_email=email,
        client_ip=client_ip,
        is_new_user=is_new_user
    )

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        is_new_user=needs_profile_completion  # Redirect to profile completion if not completed
    )


@router.post("/google/token", response_model=OAuthTokenResponse)
async def google_id_token_login(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with Google ID token from frontend Google Sign-In.

    This endpoint is used when the frontend uses the Google Sign-In
    button and receives an ID token directly.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    # Verify the ID token
    user_data = google_oauth.verify_id_token(request.credential)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )

    google_id = user_data.get("google_id")
    email = user_data.get("email")

    # Check if user exists
    result = await db.execute(
        select(User).where(
            or_(User.google_id == google_id, User.email == email)
        )
    )
    user = result.scalar_one_or_none()

    is_new_user = False

    if user:
        if not user.google_id:
            user.google_id = google_id
            user.oauth_provider = "google"
            if user_data.get("avatar_url") and not user.avatar_url:
                user.avatar_url = user_data.get("avatar_url")
        user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
    else:
        is_new_user = True
        user = User(
            email=email,
            google_id=google_id,
            full_name=user_data.get("full_name", ""),
            avatar_url=user_data.get("avatar_url", ""),
            oauth_provider="google",
            is_verified=user_data.get("email_verified", False),
            role="student",
            hashed_password="",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        is_new_user=is_new_user
    )


# ============================================
# OAuth Endpoints - GitHub
# ============================================

@router.get("/github/url", response_model=OAuthUrlResponse)
@router.get("/github/authorize", response_model=OAuthUrlResponse)
async def get_github_auth_url():
    """Get GitHub OAuth authorization URL."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )

    state = secrets.token_urlsafe(32)
    authorization_url = github_oauth.get_authorization_url(state=state)

    return OAuthUrlResponse(
        authorization_url=authorization_url,
        state=state
    )


# ============================================
# Password Reset Endpoints
# ============================================

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetResponse(BaseModel):
    message: str
    success: bool


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset.

    For beta: Returns reset token directly (no email).
    In production: Would send email with reset link.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return PasswordResetResponse(
            message="If an account with that email exists, you will receive password reset instructions.",
            success=True
        )

    # Check if user is OAuth-only (no password)
    if user.oauth_provider and not user.hashed_password:
        return PasswordResetResponse(
            message=f"This account uses {user.oauth_provider} for login. Please use the '{user.oauth_provider.title()} Sign In' button.",
            success=False
        )

    # Generate reset token (valid for 1 hour)
    reset_token_data = {
        "sub": str(user.id),
        "email": user.email,
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }

    from jose import jwt
    reset_token = jwt.encode(
        reset_token_data,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    # Store token hash in user record (optional - for single-use tokens)
    user.reset_token_hash = get_password_hash(reset_token[:20])
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    await db.commit()

    # In production, send email here
    # For beta, we return the token in response (temporary)
    # TODO: Implement email sending

    return PasswordResetResponse(
        message=f"Password reset link has been sent to your email. Token (for beta testing): {reset_token[:50]}...",
        success=True
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password using token from forgot-password email.
    """
    try:
        # Decode and verify token
        from jose import jwt, JWTError

        payload = jwt.decode(
            request.token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )

        user_id = payload.get("sub")

        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if token is still valid (optional single-use check)
        if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )

        # Validate new password
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters"
            )

        # Update password
        user.hashed_password = get_password_hash(request.new_password)
        user.reset_token_hash = None
        user.reset_token_expires = None
        await db.commit()

        return PasswordResetResponse(
            message="Password has been reset successfully. You can now login with your new password.",
            success=True
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


@router.post("/github/callback", response_model=OAuthTokenResponse)
async def github_oauth_callback(
    oauth_request: OAuthCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback with authorization code."""
    client_ip = request.client.host if request.client else "unknown"

    if not settings.GITHUB_CLIENT_ID:
        logger.log_auth_event(
            event="github_oauth",
            success=False,
            reason="GitHub OAuth not configured",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )

    # Validate role before proceeding
    validated_role = validate_oauth_role(oauth_request.role)

    # Authenticate with GitHub
    user_data = await github_oauth.authenticate(oauth_request.code)

    if not user_data:
        logger.log_auth_event(
            event="github_oauth",
            success=False,
            reason="GitHub authentication failed",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with GitHub"
        )

    github_id = user_data.get("github_id")
    email = user_data.get("email")

    if not email:
        logger.log_auth_event(
            event="github_oauth",
            success=False,
            reason="Email not provided by GitHub",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by GitHub. Please make sure your email is public or verified on GitHub."
        )

    # Check if user exists by GitHub ID or email
    result = await db.execute(
        select(User).where(
            or_(User.github_id == github_id, User.email == email)
        )
    )
    user = result.scalar_one_or_none()

    is_new_user = False
    needs_profile_completion = False

    if user:
        # Update GitHub ID if not set (linking existing account)
        if not user.github_id:
            user.github_id = github_id
            user.oauth_provider = "github"
            if user_data.get("avatar_url") and not user.avatar_url:
                user.avatar_url = user_data.get("avatar_url")
        user.last_login = datetime.utcnow()
        # Check if profile is incomplete
        needs_profile_completion = not user.profile_completed
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user with validated role
        is_new_user = True
        needs_profile_completion = True
        user = User(
            email=email,
            github_id=github_id,
            full_name=user_data.get("full_name", ""),
            username=user_data.get("username", ""),
            avatar_url=user_data.get("avatar_url", ""),
            bio=user_data.get("bio", ""),
            oauth_provider="github",
            is_verified=True,  # GitHub emails are verified
            role=validated_role,  # Use validated role
            hashed_password="",  # No password for OAuth users
            profile_completed=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.log_auth_event(
        event="github_oauth",
        success=True,
        user_email=email,
        client_ip=client_ip,
        is_new_user=is_new_user
    )

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        is_new_user=needs_profile_completion  # Redirect to profile completion if not completed
    )
