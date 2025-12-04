from fastapi import APIRouter, Depends, HTTPException, status, Query
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
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserResponse,
    GoogleAuthRequest,
    OAuthCallbackRequest,
    OAuthUrlResponse,
    OAuthTokenResponse,
)
from app.modules.auth.dependencies import get_current_user
from app.modules.oauth.google_provider import google_oauth
from app.modules.oauth.github_provider import github_oauth


class RefreshTokenRequest(BaseModel):
    refresh_token: str

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register new user"""

    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
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
        role=user_role
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user"""

    # Get user
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user info"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Decode the refresh token
        payload = decode_token(request.refresh_token)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type - expected refresh token"
            )

        # Get user from database
        user_id = payload.get("sub")
        try:
            uuid.UUID(user_id)  # Just validate format
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format"
            )
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
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

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
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


# ============================================
# OAuth Endpoints - Google
# ============================================

@router.get("/google/url", response_model=OAuthUrlResponse)
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


@router.post("/google/callback", response_model=OAuthTokenResponse)
async def google_oauth_callback(
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback with authorization code."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    # Authenticate with Google
    user_data = await google_oauth.authenticate(request.code)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with Google"
        )

    google_id = user_data.get("google_id")
    email = user_data.get("email")

    if not email:
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

    if user:
        # Update Google ID if not set (linking existing account)
        if not user.google_id:
            user.google_id = google_id
            user.oauth_provider = "google"
            if user_data.get("avatar_url") and not user.avatar_url:
                user.avatar_url = user_data.get("avatar_url")
        user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user
        is_new_user = True
        user = User(
            email=email,
            google_id=google_id,
            full_name=user_data.get("full_name", ""),
            avatar_url=user_data.get("avatar_url", ""),
            oauth_provider="google",
            is_verified=user_data.get("email_verified", False),
            role=request.role,
            hashed_password="",  # No password for OAuth users
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

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        is_new_user=is_new_user
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
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback with authorization code."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured"
        )

    # Authenticate with GitHub
    user_data = await github_oauth.authenticate(request.code)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with GitHub"
        )

    github_id = user_data.get("github_id")
    email = user_data.get("email")

    if not email:
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

    if user:
        # Update GitHub ID if not set (linking existing account)
        if not user.github_id:
            user.github_id = github_id
            user.oauth_provider = "github"
            if user_data.get("avatar_url") and not user.avatar_url:
                user.avatar_url = user_data.get("avatar_url")
        user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user
        is_new_user = True
        user = User(
            email=email,
            github_id=github_id,
            full_name=user_data.get("full_name", ""),
            username=user_data.get("username", ""),
            avatar_url=user_data.get("avatar_url", ""),
            bio=user_data.get("bio", ""),
            oauth_provider="github",
            is_verified=True,  # GitHub emails are verified
            role=request.role,
            hashed_password="",  # No password for OAuth users
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

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        is_new_user=is_new_user
    )
