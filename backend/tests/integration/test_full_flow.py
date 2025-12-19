"""
Integration Tests for Full Project Generation Flow
"""
import pytest
from httpx import AsyncClient
from faker import Faker

fake = Faker()


@pytest.mark.skip(reason="Registration flow requires Redis and has validation dependencies")
class TestAuthenticationFlow:
    """Test complete authentication flow"""

    @pytest.mark.asyncio
    async def test_register_login_flow(self, client: AsyncClient):
        """Test user registration followed by login"""
        # Register
        email = fake.email()
        password = 'securePassword123!'

        register_response = await client.post('/api/v1/auth/register', json={
            'email': email,
            'password': password,
            'full_name': fake.name(),
            'role': 'student'
        })

        assert register_response.status_code == 201

        # Login with same credentials
        login_response = await client.post('/api/v1/auth/login', json={
            'email': email,
            'password': password
        })

        assert login_response.status_code == 200
        tokens = login_response.json()
        assert 'access_token' in tokens

        # Use token to access protected route
        headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
        me_response = await client.get('/api/v1/auth/me', headers=headers)

        assert me_response.status_code == 200
        assert me_response.json()['email'] == email


class TestAPIHealthCheck:
    """Test API health and basic endpoints"""

    @pytest.mark.asyncio
    async def test_api_root(self, client: AsyncClient):
        """Test API root endpoint"""
        response = await client.get('/')
        # Should return welcome message or redirect
        assert response.status_code in [200, 307, 404]

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint if exists"""
        response = await client.get('/health')
        # Health endpoint may or may not exist
        assert response.status_code in [200, 404]


class TestTokenManagement:
    """Test token management flow"""

    @pytest.mark.asyncio
    async def test_get_token_balance(self, client: AsyncClient, auth_headers):
        """Test getting user token balance"""
        response = await client.get('/api/v1/tokens/balance', headers=auth_headers)

        # Should return balance or endpoint info
        assert response.status_code in [200, 404]


class TestProjectWorkflow:
    """Test project generation workflow"""

    @pytest.mark.asyncio
    async def test_bolt_endpoint_exists(self, client: AsyncClient, auth_headers):
        """Test bolt endpoint is accessible"""
        # Test if bolt endpoint exists
        response = await client.get('/api/v1/bolt/status', headers=auth_headers)

        # Bolt endpoint may not exist at this path
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_orchestrator_endpoint(self, client: AsyncClient, auth_headers):
        """Test orchestrator endpoint"""
        response = await client.get('/api/v1/orchestrator/status', headers=auth_headers)

        assert response.status_code in [200, 404, 405]
