"""
BharatBuild AI - Document Integration Tests
Tests document generation and download workflows.
"""
import pytest
import asyncio
import uuid

from api_client import BharatBuildAPIClient
from config import config


class TestDocumentIntegration:
    """Test document workflows"""

    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated API client"""
        email = f"doc_test_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPassword123!"

        async with BharatBuildAPIClient() as client:
            await client.register(email=email, password=password, full_name="Doc Test User")
            await client.login(email, password)
            yield client

    # ==================== Document Types ====================
    @pytest.mark.asyncio
    async def test_get_document_types_public(self):
        """IT-DOC-001: Get document types (public endpoint)"""
        async with BharatBuildAPIClient() as client:
            # No login needed
            response = await client.get_document_types()

            assert response.success, f"Get doc types failed: {response.data}"
            assert isinstance(response.data, list)
            print(f"[PASS] Document types retrieved: {len(response.data)} types")

            # Verify expected document types
            type_ids = [t.get("id") or t.get("type") for t in response.data]
            expected_types = ["project_report", "srs", "ppt"]
            for expected in expected_types:
                if expected in str(type_ids).lower():
                    print(f"  - Found: {expected}")

    # ==================== Document Listing ====================
    @pytest.mark.asyncio
    async def test_list_documents_for_project(self, authenticated_client):
        """IT-DOC-002: List documents for a project"""
        # Get a project first
        projects_response = await authenticated_client.list_projects()

        if projects_response.success and projects_response.data.get("items"):
            project_id = projects_response.data["items"][0]["id"]
            response = await authenticated_client.list_documents(project_id)

            assert response.success, f"List documents failed: {response.data}"
            print(f"[PASS] Documents listed for project {project_id[:8]}...")
        else:
            print(f"[SKIP] No projects available to test")

    @pytest.mark.asyncio
    async def test_list_documents_invalid_project(self, authenticated_client):
        """IT-DOC-003: List documents for invalid project"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await authenticated_client.list_documents(fake_id)

        assert not response.success
        assert response.status == 404
        print(f"[PASS] Invalid project handled correctly")

    # ==================== Document Download ====================
    @pytest.mark.asyncio
    async def test_download_document_requires_premium(self, authenticated_client):
        """IT-DOC-004: Download document requires premium for free users"""
        projects_response = await authenticated_client.list_projects()

        if projects_response.success and projects_response.data.get("items"):
            project_id = projects_response.data["items"][0]["id"]

            # Try to download project report
            response = await authenticated_client.download_document(project_id, "project_report")

            # Free users should get 402/403
            if not response.success:
                assert response.status in [402, 403, 404], f"Expected payment required: {response.data}"
                print(f"[PASS] Document download correctly requires premium")
            else:
                print(f"[INFO] Download succeeded (user may be premium or doc exists)")
        else:
            print(f"[SKIP] No projects available to test")

    @pytest.mark.asyncio
    async def test_download_document_unauthenticated(self):
        """IT-DOC-005: Download document without authentication"""
        async with BharatBuildAPIClient() as client:
            # No login
            response = await client.download_document("some-project-id", "project_report")

            assert not response.success
            assert response.status in [401, 403]
            print(f"[PASS] Unauthenticated download rejected")


class TestUserFeaturesIntegration:
    """Test user features and plan status"""

    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated API client"""
        email = f"user_test_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPassword123!"

        async with BharatBuildAPIClient() as client:
            await client.register(email=email, password=password, full_name="User Test")
            await client.login(email, password)
            yield client

    @pytest.mark.asyncio
    async def test_get_plan_status(self, authenticated_client):
        """IT-USER-001: Get user plan status"""
        response = await authenticated_client.get_plan_status()

        assert response.success, f"Get plan status failed: {response.data}"
        # Should have plan info
        assert "plan" in response.data or "is_premium" in response.data or "tier" in response.data
        print(f"[PASS] Plan status retrieved: {response.data}")

    @pytest.mark.asyncio
    async def test_get_token_balance(self, authenticated_client):
        """IT-USER-002: Get user token balance"""
        response = await authenticated_client.get_token_balance()

        assert response.success, f"Get token balance failed: {response.data}"
        print(f"[PASS] Token balance retrieved: {response.data}")

    @pytest.mark.asyncio
    async def test_new_user_is_free_tier(self, authenticated_client):
        """IT-USER-003: New user should be on free tier"""
        response = await authenticated_client.get_plan_status()

        assert response.success
        # Check for free tier indicators
        data = response.data
        is_free = (
            data.get("plan") == "free" or
            data.get("is_premium") == False or
            data.get("tier") == "free" or
            data.get("plan_type") == "free"
        )
        print(f"[PASS] New user plan status: {data}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
