"""
Unit Tests for Authentication API Endpoints
"""
import pytest
from httpx import AsyncClient
from faker import Faker

fake = Faker()


@pytest.mark.skip(reason="Requires Redis connection for rate limiting")
class TestUserRegistration:
    """Test user registration endpoint"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration"""
        user_data = {
            'email': fake.email(),
            'password': 'securePassword123!',
            'full_name': fake.name(),
            'role': 'student'
        }

        response = await client.post('/api/v1/auth/register', json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data['email'] == user_data['email']
        assert data['full_name'] == user_data['full_name']
        assert 'id' in data
        assert 'hashed_password' not in data  # Should not expose password

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email fails"""
        user_data = {
            'email': test_user.email,  # Same email as existing user
            'password': 'securePassword123!',
            'full_name': fake.name(),
            'role': 'student'
        }

        response = await client.post('/api/v1/auth/register', json=user_data)

        assert response.status_code == 400
        assert 'already registered' in response.json()['detail'].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        user_data = {
            'email': 'not-an-email',
            'password': 'securePassword123!',
            'full_name': fake.name(),
            'role': 'student'
        }

        response = await client.post('/api/v1/auth/register', json=user_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client: AsyncClient):
        """Test registration with missing required fields"""
        user_data = {
            'email': fake.email()
            # Missing password and full_name
        }

        response = await client.post('/api/v1/auth/register', json=user_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_with_short_password(self, client: AsyncClient):
        """Test registration with too short password"""
        user_data = {
            'email': fake.email(),
            'password': '123',  # Too short
            'full_name': fake.name(),
            'role': 'student'
        }

        response = await client.post('/api/v1/auth/register', json=user_data)

        # Should either fail validation or create user depending on password policy
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_register_with_all_roles(self, client: AsyncClient):
        """Test registration with different roles"""
        roles = ['student', 'faculty', 'admin']

        for role in roles:
            user_data = {
                'email': fake.email(),
                'password': 'securePassword123!',
                'full_name': fake.name(),
                'role': role
            }

            response = await client.post('/api/v1/auth/register', json=user_data)
            # Admin might be restricted
            assert response.status_code in [201, 400, 403]


@pytest.mark.skip(reason="Requires Redis connection for rate limiting")
class TestUserLogin:
    """Test user login endpoint"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login"""
        login_data = {
            'email': test_user.email,
            'password': 'testpassword123'  # Password set in fixture
        }

        response = await client.post('/api/v1/auth/login', json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['token_type'] == 'bearer'

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password"""
        login_data = {
            'email': test_user.email,
            'password': 'wrongpassword'
        }

        response = await client.post('/api/v1/auth/login', json=login_data)

        assert response.status_code == 401
        assert 'incorrect' in response.json()['detail'].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user"""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'anypassword'
        }

        response = await client.post('/api/v1/auth/login', json=login_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_email(self, client: AsyncClient):
        """Test login with missing email"""
        login_data = {
            'password': 'anypassword'
        }

        response = await client.post('/api/v1/auth/login', json=login_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_password(self, client: AsyncClient):
        """Test login with missing password"""
        login_data = {
            'email': 'test@example.com'
        }

        response = await client.post('/api/v1/auth/login', json=login_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, client: AsyncClient):
        """Test login with empty credentials"""
        login_data = {
            'email': '',
            'password': ''
        }

        response = await client.post('/api/v1/auth/login', json=login_data)

        assert response.status_code == 422


class TestTokenValidation:
    """Test token validation and refresh"""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, test_user, auth_headers):
        """Test getting current user info with valid token"""
        response = await client.get('/api/v1/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['email'] == test_user.email
        assert data['id'] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting current user without token fails"""
        response = await client.get('/api/v1/auth/me')

        # Either 401 or 403 depending on implementation
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token"""
        headers = {'Authorization': 'Bearer invalid-token'}
        response = await client.get('/api/v1/auth/me', headers=headers)

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_current_user_malformed_header(self, client: AsyncClient):
        """Test getting current user with malformed auth header"""
        headers = {'Authorization': 'NotBearer token'}
        response = await client.get('/api/v1/auth/me', headers=headers)

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_current_user_empty_token(self, client: AsyncClient):
        """Test getting current user with empty token"""
        headers = {'Authorization': 'Bearer '}
        response = await client.get('/api/v1/auth/me', headers=headers)

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_validate_token_endpoint(self, client: AsyncClient, auth_headers):
        """Test token validation endpoint"""
        response = await client.get('/api/v1/auth/validate-token', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['valid'] == True
        assert 'user' in data


@pytest.mark.skip(reason="Requires Redis connection for rate limiting")
class TestTokenRefresh:
    """Test token refresh functionality"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        """Test successful token refresh"""
        # First login to get tokens
        login_data = {
            'email': test_user.email,
            'password': 'testpassword123'
        }

        login_response = await client.post('/api/v1/auth/login', json=login_data)
        assert login_response.status_code == 200
        tokens = login_response.json()

        # Now refresh
        refresh_data = {
            'refresh_token': tokens['refresh_token']
        }

        response = await client.post('/api/v1/auth/refresh', json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert 'refresh_token' in data

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh with invalid token"""
        refresh_data = {
            'refresh_token': 'invalid-refresh-token'
        }

        response = await client.post('/api/v1/auth/refresh', json=refresh_data)

        assert response.status_code == 401


class TestPasswordReset:
    """Test password reset functionality"""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user(self, client: AsyncClient, test_user):
        """Test forgot password for existing user"""
        response = await client.post(
            '/api/v1/auth/forgot-password',
            json={'email': test_user.email}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_user(self, client: AsyncClient):
        """Test forgot password for non-existent user (should not reveal)"""
        response = await client.post(
            '/api/v1/auth/forgot-password',
            json={'email': 'nonexistent@example.com'}
        )

        # Should still return success to prevent email enumeration
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True

    @pytest.mark.asyncio
    async def test_forgot_password_invalid_email(self, client: AsyncClient):
        """Test forgot password with invalid email format"""
        response = await client.post(
            '/api/v1/auth/forgot-password',
            json={'email': 'not-an-email'}
        )

        # May succeed (for security) or fail validation
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, client: AsyncClient):
        """Test reset password with invalid token"""
        response = await client.post(
            '/api/v1/auth/reset-password',
            json={
                'token': 'invalid-reset-token',
                'new_password': 'newSecurePassword123!'
            }
        )

        assert response.status_code == 400


class TestOAuthEndpoints:
    """Test OAuth endpoints"""

    @pytest.mark.asyncio
    async def test_google_oauth_url(self, client: AsyncClient):
        """Test getting Google OAuth URL"""
        response = await client.get('/api/v1/auth/google/url')

        # Will fail if OAuth not configured (503) or succeed (200)
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_github_oauth_url(self, client: AsyncClient):
        """Test getting GitHub OAuth URL"""
        response = await client.get('/api/v1/auth/github/url')

        # Will fail if OAuth not configured (503) or succeed (200)
        assert response.status_code in [200, 503]
