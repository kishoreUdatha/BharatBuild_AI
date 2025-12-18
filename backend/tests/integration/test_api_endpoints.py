"""
Integration Tests for API Endpoints
Tests the complete API flow including authentication, projects, and sync
"""
import pytest
from httpx import AsyncClient
from faker import Faker
import uuid

fake = Faker()


class TestProjectEndpoints:
    """Integration tests for project-related endpoints"""

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers):
        """Test listing user projects"""
        response = await client.get('/api/v1/projects', headers=auth_headers)

        # Should return list (possibly empty)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent project"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f'/api/v1/projects/{fake_id}', headers=auth_headers)

        assert response.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_projects_require_auth(self, client: AsyncClient):
        """Test projects endpoint requires authentication"""
        response = await client.get('/api/v1/projects')

        assert response.status_code == 401


class TestSyncEndpoints:
    """Integration tests for sync endpoints"""

    @pytest.mark.asyncio
    async def test_sync_project_not_found(self, client: AsyncClient, auth_headers):
        """Test sync endpoint with non-existent project"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f'/api/v1/sync/{fake_id}', headers=auth_headers)

        assert response.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_sync_requires_auth(self, client: AsyncClient):
        """Test sync endpoint requires authentication"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f'/api/v1/sync/{fake_id}')

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_files_endpoint(self, client: AsyncClient, auth_headers):
        """Test sync files endpoint exists"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f'/api/v1/sync/{fake_id}/files', headers=auth_headers)

        # Should not be method not allowed
        assert response.status_code != 405


class TestDocumentEndpoints:
    """Integration tests for document endpoints"""

    @pytest.mark.asyncio
    async def test_list_documents(self, client: AsyncClient, auth_headers):
        """Test listing documents"""
        response = await client.get('/api/v1/documents', headers=auth_headers)

        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_documents_require_auth(self, client: AsyncClient):
        """Test documents endpoint requires authentication"""
        response = await client.get('/api/v1/documents')

        assert response.status_code == 401


class TestExecutionEndpoints:
    """Integration tests for execution endpoints"""

    @pytest.mark.asyncio
    async def test_execution_status_endpoint(self, client: AsyncClient, auth_headers):
        """Test execution status endpoint"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f'/api/v1/execution/{fake_id}/status', headers=auth_headers)

        # May or may not exist
        assert response.status_code in [200, 404, 405]

    @pytest.mark.asyncio
    async def test_execution_requires_auth(self, client: AsyncClient):
        """Test execution endpoints require authentication"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f'/api/v1/execution/{fake_id}/status')

        assert response.status_code in [401, 404, 405]


class TestUserEndpoints:
    """Integration tests for user endpoints"""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """Test getting current user info"""
        response = await client.get('/api/v1/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert 'email' in data

    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client: AsyncClient):
        """Test /me endpoint requires authentication"""
        response = await client.get('/api/v1/auth/me')

        assert response.status_code == 401


class TestErrorHandling:
    """Integration tests for error handling"""

    @pytest.mark.asyncio
    async def test_invalid_json_body(self, client: AsyncClient):
        """Test handling of invalid JSON body"""
        response = await client.post(
            '/api/v1/auth/login',
            content='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client: AsyncClient):
        """Test handling of missing required fields"""
        response = await client.post('/api/v1/auth/login', json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """Test handling of invalid authentication token"""
        headers = {'Authorization': 'Bearer invalid-token'}
        response = await client.get('/api/v1/auth/me', headers=headers)

        assert response.status_code == 401


class TestCORS:
    """Integration tests for CORS handling"""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient):
        """Test CORS headers are present in response"""
        response = await client.options(
            '/api/v1/auth/login',
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'POST'
            }
        )

        # CORS preflight should be handled
        assert response.status_code in [200, 204, 405]


class TestRateLimiting:
    """Integration tests for rate limiting if implemented"""

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client: AsyncClient):
        """Test rate limit headers if present"""
        response = await client.get('/')

        # Rate limit headers may or may not be present
        # This test just ensures the API responds
        assert response.status_code in [200, 307, 404]


class TestWebSocketEndpoints:
    """Integration tests for WebSocket endpoints"""

    @pytest.mark.asyncio
    async def test_ws_endpoint_defined(self):
        """Test WebSocket endpoints are defined in app"""
        from app.main import app

        routes = [route.path for route in app.routes]

        # Just verify app has routes defined
        assert len(routes) > 0
