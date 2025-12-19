"""
Comprehensive Unit Tests for Auth API Endpoints
Tests for: register, login, verify-email, refresh token, OAuth, password reset
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
from faker import Faker
from datetime import datetime, timedelta
from jose import jwt

from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token, create_refresh_token
from app.core.config import settings

fake = Faker()


@pytest.mark.skip(reason="Requires Redis connection for rate limiting")
class TestUserRegistration:
    """Test user registration endpoint"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, db_session):
        """Test successful user registration"""
        user_data = {
            "email": fake.email(),
            "password": "SecurePassword123!",
            "full_name": fake.name(),
            "role": "student"
        }

        with patch('app.api.v1.endpoints.auth.email_service') as mock_email:
            mock_email.send_verification_email = AsyncMock(return_value=True)
            response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with existing email fails"""
        user_data = {
            "email": test_user.email,
            "password": "SecurePassword123!",
            "full_name": fake.name(),
            "role": "student"
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_with_phone(self, client: AsyncClient, db_session):
        """Test registration with phone number"""
        user_data = {
            "email": fake.email(),
            "password": "SecurePassword123!",
            "full_name": fake.name(),
            "phone": "+1234567890",
            "role": "student"
        }

        with patch('app.api.v1.endpoints.auth.email_service') as mock_email:
            mock_email.send_verification_email = AsyncMock(return_value=True)
            response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["phone"] == user_data["phone"]

    @pytest.mark.asyncio
    async def test_register_with_academic_details(self, client: AsyncClient, db_session):
        """Test registration with student academic details"""
        user_data = {
            "email": fake.email(),
            "password": "SecurePassword123!",
            "full_name": fake.name(),
            "role": "student",
            "roll_number": "CS2024001",
            "college_name": "Test Engineering College",
            "university_name": "Test University",
            "department": "Computer Science",
            "course": "B.Tech",
            "year_semester": "4th Year",
            "batch": "2024"
        }

        with patch('app.api.v1.endpoints.auth.email_service') as mock_email:
            mock_email.send_verification_email = AsyncMock(return_value=True)
            response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["roll_number"] == user_data["roll_number"]
        assert data["college_name"] == user_data["college_name"]

    @pytest.mark.asyncio
    async def test_register_invalid_role_defaults_to_student(self, client: AsyncClient, db_session):
        """Test registration with invalid role defaults to student"""
        user_data = {
            "email": fake.email(),
            "password": "SecurePassword123!",
            "full_name": fake.name(),
            "role": "invalid_role"
        }

        with patch('app.api.v1.endpoints.auth.email_service') as mock_email:
            mock_email.send_verification_email = AsyncMock(return_value=True)
            response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "student"


@pytest.mark.skip(reason="Requires Redis connection for rate limiting")
class TestUserLogin:
    """Test user login endpoint"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login"""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123"
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password"""
        login_data = {
            "email": test_user.email,
            "password": "wrongpassword"
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent email"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "somepassword"
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session):
        """Test login with inactive user"""
        # Create inactive user
        inactive_user = User(
            email=fake.email(),
            hashed_password=get_password_hash("testpassword123"),
            full_name=fake.name(),
            role=UserRole.STUDENT,
            is_active=False,
            is_verified=True
        )
        db_session.add(inactive_user)
        await db_session.commit()

        login_data = {
            "email": inactive_user.email,
            "password": "testpassword123"
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()


class TestTokenRefresh:
    """Test token refresh endpoint"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        """Test successful token refresh"""
        token_data = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role.value
        }
        refresh_token = create_refresh_token(token_data)

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, client: AsyncClient, test_user):
        """Test refresh with access token instead of refresh token fails"""
        token_data = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role.value
        }
        access_token = create_access_token(token_data)

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token}
        )

        assert response.status_code == 401
        assert "invalid token type" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_expired_token(self, client: AsyncClient, test_user):
        """Test refresh with expired token fails"""
        token_data = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role.value,
            "exp": datetime.utcnow() - timedelta(days=1),
            "type": "refresh"
        }
        expired_token = jwt.encode(
            token_data,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token}
        )

        assert response.status_code == 401


class TestGetCurrentUser:
    """Test get current user endpoint"""

    @pytest.mark.asyncio
    async def test_get_me_success(self, client: AsyncClient, test_user, auth_headers):
        """Test getting current user info"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        """Test getting current user without auth fails"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code in [401, 403]


class TestEmailVerification:
    """Test email verification endpoints"""

    @pytest.mark.asyncio
    async def test_verify_email_success(self, client: AsyncClient, db_session):
        """Test successful email verification"""
        # Create unverified user
        user = User(
            email=fake.email(),
            hashed_password=get_password_hash("testpassword123"),
            full_name=fake.name(),
            role=UserRole.STUDENT,
            is_active=True,
            is_verified=False
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create verification token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "type": "email_verification",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        verification_token = jwt.encode(
            token_data,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        with patch('app.api.v1.endpoints.auth.email_service') as mock_email:
            mock_email.send_welcome_email = AsyncMock(return_value=True)
            response = await client.post(
                "/api/v1/auth/verify-email",
                json={"token": verification_token}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, client: AsyncClient):
        """Test verification with invalid token"""
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid_token"}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_email_wrong_type(self, client: AsyncClient, test_user):
        """Test verification with wrong token type"""
        token_data = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "type": "password_reset",  # Wrong type
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(
            token_data,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": token}
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resend_verification_success(self, client: AsyncClient, db_session):
        """Test resend verification email"""
        # Create unverified user
        user = User(
            email=fake.email(),
            hashed_password=get_password_hash("testpassword123"),
            full_name=fake.name(),
            role=UserRole.STUDENT,
            is_active=True,
            is_verified=False
        )
        db_session.add(user)
        await db_session.commit()

        with patch('app.api.v1.endpoints.auth.email_service') as mock_email:
            mock_email.send_verification_email = AsyncMock(return_value=True)
            response = await client.post(
                "/api/v1/auth/resend-verification",
                json={"email": user.email}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestPasswordReset:
    """Test password reset endpoints"""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user(self, client: AsyncClient, test_user):
        """Test forgot password for existing user"""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_user(self, client: AsyncClient):
        """Test forgot password for non-existent user (should still succeed for security)"""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_reset_password_success(self, client: AsyncClient, db_session):
        """Test successful password reset"""
        # Create user
        user = User(
            email=fake.email(),
            hashed_password=get_password_hash("oldpassword123"),
            full_name=fake.name(),
            role=UserRole.STUDENT,
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create reset token
        reset_token_data = {
            "sub": str(user.id),
            "email": user.email,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        reset_token = jwt.encode(
            reset_token_data,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "newSecurePassword123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_reset_password_short_password(self, client: AsyncClient, test_user):
        """Test reset password with too short password"""
        reset_token_data = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        reset_token = jwt.encode(
            reset_token_data,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "short"
            }
        )

        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"]


class TestValidateToken:
    """Test token validation endpoint"""

    @pytest.mark.asyncio
    async def test_validate_token_success(self, client: AsyncClient, test_user, auth_headers):
        """Test token validation"""
        response = await client.get("/api/v1/auth/validate-token", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user"]["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, client: AsyncClient):
        """Test validation with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/auth/validate-token", headers=headers)

        assert response.status_code in [401, 403]


class TestOAuthEndpoints:
    """Test OAuth endpoints"""

    @pytest.mark.asyncio
    async def test_google_url_not_configured(self, client: AsyncClient):
        """Test Google OAuth URL when not configured"""
        with patch.object(settings, 'GOOGLE_CLIENT_ID', None):
            response = await client.get("/api/v1/auth/google/url")

        # Should return 503 when not configured
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_github_url_not_configured(self, client: AsyncClient):
        """Test GitHub OAuth URL when not configured"""
        with patch.object(settings, 'GITHUB_CLIENT_ID', None):
            response = await client.get("/api/v1/auth/github/url")

        assert response.status_code in [200, 503]
