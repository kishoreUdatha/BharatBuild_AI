"""
BharatBuild AI - Authentication Integration Tests
Tests the complete authentication flow from frontend to backend.
"""
import pytest
import asyncio
import uuid
from datetime import datetime

from api_client import BharatBuildAPIClient
from config import config


class TestAuthenticationIntegration:
    """Test authentication flows"""

    @pytest.fixture
    async def client(self):
        """Create API client"""
        async with BharatBuildAPIClient() as client:
            yield client

    @pytest.fixture
    def unique_email(self):
        """Generate unique email for testing"""
        return f"test_{uuid.uuid4().hex[:8]}@test.com"

    # ==================== Health Check ====================
    @pytest.mark.asyncio
    async def test_api_health_check(self, client):
        """IT-AUTH-001: API health check"""
        response = await client.health_check()

        assert response.success, f"Health check failed: {response.data}"
        assert response.status == 200
        assert response.data.get("status") == "healthy"
        print(f"[PASS] Health check: {response.data}")

    # ==================== Registration ====================
    @pytest.mark.asyncio
    async def test_user_registration_success(self, client, unique_email):
        """IT-AUTH-002: Successful user registration"""
        response = await client.register(
            email=unique_email,
            password="TestPassword123!",
            full_name="Test User",
            role="student"
        )

        assert response.success, f"Registration failed: {response.data}"
        assert response.status in [200, 201]
        assert "id" in response.data or "email" in response.data
        print(f"[PASS] Registration successful: {unique_email}")

    @pytest.mark.asyncio
    async def test_user_registration_duplicate_email(self, client):
        """IT-AUTH-003: Registration with duplicate email should fail"""
        email = f"duplicate_{uuid.uuid4().hex[:8]}@test.com"

        # First registration
        response1 = await client.register(
            email=email,
            password="TestPassword123!",
            full_name="First User"
        )
        assert response1.success, "First registration should succeed"

        # Wait a bit to avoid rate limiting
        await asyncio.sleep(1)

        # Second registration with same email
        response2 = await client.register(
            email=email,
            password="TestPassword123!",
            full_name="Second User"
        )

        assert not response2.success, "Duplicate registration should fail"
        assert response2.status == 400
        print(f"[PASS] Duplicate email rejected correctly")

    @pytest.mark.asyncio
    async def test_user_registration_invalid_email(self, client):
        """IT-AUTH-004: Registration with invalid email format"""
        response = await client.register(
            email="invalid-email",
            password="TestPassword123!",
            full_name="Test User"
        )

        assert not response.success, "Invalid email should be rejected"
        assert response.status == 422
        print(f"[PASS] Invalid email rejected correctly")

    @pytest.mark.asyncio
    async def test_user_registration_weak_password(self, client, unique_email):
        """IT-AUTH-005: Registration with weak password"""
        response = await client.register(
            email=unique_email,
            password="123",  # Too weak
            full_name="Test User"
        )

        assert not response.success, "Weak password should be rejected"
        assert response.status == 422
        print(f"[PASS] Weak password rejected correctly")

    # ==================== Login ====================
    @pytest.mark.asyncio
    async def test_user_login_success(self, client, unique_email):
        """IT-AUTH-006: Successful login flow"""
        password = "TestPassword123!"

        # Register first
        reg_response = await client.register(
            email=unique_email,
            password=password,
            full_name="Login Test User"
        )
        assert reg_response.success, f"Registration failed: {reg_response.data}"

        # Login
        login_response = await client.login(unique_email, password)

        assert login_response.success, f"Login failed: {login_response.data}"
        assert "access_token" in login_response.data
        assert "refresh_token" in login_response.data
        assert client.token is not None
        print(f"[PASS] Login successful, token received")

    @pytest.mark.asyncio
    async def test_user_login_invalid_credentials(self, client):
        """IT-AUTH-007: Login with invalid credentials"""
        response = await client.login(
            email="nonexistent@test.com",
            password="WrongPassword123!"
        )

        assert not response.success, "Invalid credentials should fail"
        assert response.status == 401
        print(f"[PASS] Invalid credentials rejected correctly")

    @pytest.mark.asyncio
    async def test_user_login_wrong_password(self, client, unique_email):
        """IT-AUTH-008: Login with wrong password"""
        # Register
        await client.register(
            email=unique_email,
            password="CorrectPassword123!",
            full_name="Test User"
        )

        # Login with wrong password
        response = await client.login(unique_email, "WrongPassword123!")

        assert not response.success, "Wrong password should fail"
        assert response.status == 401
        print(f"[PASS] Wrong password rejected correctly")

    # ==================== Get Current User ====================
    @pytest.mark.asyncio
    async def test_get_current_user_authenticated(self, client, unique_email):
        """IT-AUTH-009: Get current user when authenticated"""
        password = "TestPassword123!"

        # Register and login
        await client.register(email=unique_email, password=password, full_name="Test User")
        await client.login(unique_email, password)

        # Get current user
        response = await client.get_current_user()

        assert response.success, f"Get user failed: {response.data}"
        assert response.data.get("email") == unique_email
        print(f"[PASS] Current user retrieved: {response.data.get('email')}")

    @pytest.mark.asyncio
    async def test_get_current_user_unauthenticated(self, client):
        """IT-AUTH-010: Get current user without authentication"""
        # Don't login, just try to get user
        response = await client.get_current_user()

        assert not response.success, "Should require authentication"
        assert response.status in [401, 403]
        print(f"[PASS] Unauthenticated request rejected")

    # ==================== Token Refresh ====================
    @pytest.mark.asyncio
    async def test_token_refresh(self, client, unique_email):
        """IT-AUTH-011: Token refresh flow"""
        password = "TestPassword123!"

        # Register and login
        await client.register(email=unique_email, password=password, full_name="Test User")
        await client.login(unique_email, password)

        old_token = client.token
        assert old_token is not None

        # Refresh token
        response = await client.refresh_access_token()

        assert response.success, f"Token refresh failed: {response.data}"
        assert "access_token" in response.data
        # Token should be different (or same if implementation allows)
        print(f"[PASS] Token refresh successful")

    # ==================== Logout ====================
    @pytest.mark.asyncio
    async def test_logout(self, client, unique_email):
        """IT-AUTH-012: Logout flow"""
        password = "TestPassword123!"

        # Register and login
        await client.register(email=unique_email, password=password, full_name="Test User")
        await client.login(unique_email, password)

        assert client.token is not None

        # Logout
        response = await client.logout()

        assert client.token is None
        print(f"[PASS] Logout successful, token cleared")

    # ==================== Session Isolation ====================
    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """IT-AUTH-013: Different users have isolated sessions"""
        email1 = f"user1_{uuid.uuid4().hex[:8]}@test.com"
        email2 = f"user2_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPassword123!"

        async with BharatBuildAPIClient() as client1:
            async with BharatBuildAPIClient() as client2:
                # Register and login user 1
                await client1.register(email=email1, password=password, full_name="User 1")
                await client1.login(email1, password)

                await asyncio.sleep(1)  # Avoid rate limit

                # Register and login user 2
                await client2.register(email=email2, password=password, full_name="User 2")
                await client2.login(email2, password)

                # Get current user for each client
                user1_response = await client1.get_current_user()
                user2_response = await client2.get_current_user()

                assert user1_response.data.get("email") == email1
                assert user2_response.data.get("email") == email2
                print(f"[PASS] Sessions isolated correctly")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
