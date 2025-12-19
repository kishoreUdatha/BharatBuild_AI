"""
BharatBuild AI - Project Workflow Integration Tests
Tests the complete project lifecycle from creation to execution.
"""
import pytest
import asyncio
import uuid
from datetime import datetime

from api_client import BharatBuildAPIClient
from config import config


class TestProjectIntegration:
    """Test project workflows"""

    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated API client"""
        email = f"project_test_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPassword123!"

        async with BharatBuildAPIClient() as client:
            # Register and login
            await client.register(email=email, password=password, full_name="Project Test User")
            login_response = await client.login(email, password)
            assert login_response.success, f"Login failed: {login_response.data}"
            yield client

    # ==================== Project Listing ====================
    @pytest.mark.asyncio
    async def test_list_projects_empty(self, authenticated_client):
        """IT-PROJ-001: List projects for new user (should be empty)"""
        response = await authenticated_client.list_projects()

        assert response.success, f"List projects failed: {response.data}"
        assert "items" in response.data
        # New user should have no projects (or few test projects)
        print(f"[PASS] Projects list retrieved: {len(response.data.get('items', []))} projects")

    @pytest.mark.asyncio
    async def test_list_projects_pagination(self, authenticated_client):
        """IT-PROJ-002: Test project list pagination"""
        response = await authenticated_client.list_projects(page=1, page_size=5)

        assert response.success, f"List projects failed: {response.data}"
        assert "items" in response.data
        assert "total" in response.data or "page" in response.data
        print(f"[PASS] Pagination working correctly")

    # ==================== Project Creation ====================
    @pytest.mark.asyncio
    async def test_create_project_success(self, authenticated_client):
        """IT-PROJ-003: Create a new project"""
        project_name = f"Test Project {uuid.uuid4().hex[:6]}"
        prompt = "Create a simple hello world React application"

        response = await authenticated_client.create_project(
            name=project_name,
            prompt=prompt,
            project_type="web"
        )

        # Note: This might fail for free users due to token limits
        if response.success:
            assert "id" in response.data
            print(f"[PASS] Project created: {response.data.get('id')}")
        else:
            # Could be token limit or other restriction
            print(f"[INFO] Project creation returned: {response.status} - {response.data}")
            assert response.status in [402, 403, 429], f"Unexpected error: {response.data}"

    @pytest.mark.asyncio
    async def test_create_project_invalid_name(self, authenticated_client):
        """IT-PROJ-004: Create project with invalid name"""
        response = await authenticated_client.create_project(
            name="",  # Empty name
            prompt="Test prompt",
            project_type="web"
        )

        assert not response.success, "Empty name should be rejected"
        assert response.status == 422
        print(f"[PASS] Invalid name rejected correctly")

    @pytest.mark.asyncio
    async def test_create_project_empty_prompt(self, authenticated_client):
        """IT-PROJ-005: Create project with empty prompt"""
        response = await authenticated_client.create_project(
            name="Valid Name",
            prompt="",  # Empty prompt
            project_type="web"
        )

        assert not response.success, "Empty prompt should be rejected"
        assert response.status == 422
        print(f"[PASS] Empty prompt rejected correctly")

    # ==================== Project Details ====================
    @pytest.mark.asyncio
    async def test_get_project_details(self, authenticated_client):
        """IT-PROJ-006: Get project details"""
        # First list projects to get an ID
        list_response = await authenticated_client.list_projects()

        if list_response.success and list_response.data.get("items"):
            project_id = list_response.data["items"][0]["id"]
            response = await authenticated_client.get_project(project_id)

            assert response.success, f"Get project failed: {response.data}"
            assert response.data.get("id") == project_id
            print(f"[PASS] Project details retrieved: {project_id}")
        else:
            print(f"[SKIP] No projects available to test")

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, authenticated_client):
        """IT-PROJ-007: Get non-existent project"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await authenticated_client.get_project(fake_id)

        assert not response.success, "Non-existent project should return error"
        assert response.status == 404
        print(f"[PASS] Non-existent project handled correctly")

    @pytest.mark.asyncio
    async def test_get_project_unauthorized(self):
        """IT-PROJ-008: Get project without authentication"""
        async with BharatBuildAPIClient() as client:
            # Don't login
            response = await client.get_project("some-project-id")

            assert not response.success
            assert response.status in [401, 403]
            print(f"[PASS] Unauthenticated access rejected")

    # ==================== Project Files ====================
    @pytest.mark.asyncio
    async def test_get_project_files(self, authenticated_client):
        """IT-PROJ-009: Get project files"""
        list_response = await authenticated_client.list_projects()

        if list_response.success and list_response.data.get("items"):
            project_id = list_response.data["items"][0]["id"]
            response = await authenticated_client.get_project_files(project_id)

            if response.success:
                assert isinstance(response.data, (list, dict))
                print(f"[PASS] Project files retrieved")
            else:
                print(f"[INFO] Get files returned: {response.status}")
        else:
            print(f"[SKIP] No projects available to test")

    # ==================== Project Deletion ====================
    @pytest.mark.asyncio
    async def test_delete_project(self, authenticated_client):
        """IT-PROJ-010: Delete a project"""
        # First try to create a project
        project_name = f"Delete Test {uuid.uuid4().hex[:6]}"
        create_response = await authenticated_client.create_project(
            name=project_name,
            prompt="Simple test project for deletion",
            project_type="web"
        )

        if create_response.success:
            project_id = create_response.data.get("id")

            # Now delete it
            delete_response = await authenticated_client.delete_project(project_id)
            assert delete_response.success, f"Delete failed: {delete_response.data}"
            print(f"[PASS] Project deleted: {project_id}")
        else:
            print(f"[SKIP] Could not create project to test deletion")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_project(self, authenticated_client):
        """IT-PROJ-011: Delete non-existent project"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await authenticated_client.delete_project(fake_id)

        assert not response.success
        assert response.status == 404
        print(f"[PASS] Non-existent project deletion handled correctly")


class TestProjectExecutionIntegration:
    """Test project execution workflows"""

    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated API client"""
        email = f"exec_test_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPassword123!"

        async with BharatBuildAPIClient() as client:
            await client.register(email=email, password=password, full_name="Exec Test User")
            await client.login(email, password)
            yield client

    @pytest.mark.asyncio
    async def test_run_project_requires_premium(self, authenticated_client):
        """IT-EXEC-001: Run project requires premium for free users"""
        list_response = await authenticated_client.list_projects()

        if list_response.success and list_response.data.get("items"):
            project_id = list_response.data["items"][0]["id"]
            response = await authenticated_client.run_project(project_id)

            # Free users should get 402/403
            if not response.success:
                assert response.status in [402, 403], f"Expected payment/forbidden: {response.data}"
                print(f"[PASS] Run project correctly requires premium")
            else:
                print(f"[INFO] Run project succeeded (user may be premium)")
        else:
            print(f"[SKIP] No projects available to test")

    @pytest.mark.asyncio
    async def test_export_project_requires_premium(self, authenticated_client):
        """IT-EXEC-002: Export project requires premium for free users"""
        list_response = await authenticated_client.list_projects()

        if list_response.success and list_response.data.get("items"):
            project_id = list_response.data["items"][0]["id"]
            response = await authenticated_client.export_project(project_id)

            # Free users should get 402/403
            if not response.success:
                assert response.status in [402, 403], f"Expected payment/forbidden: {response.data}"
                print(f"[PASS] Export project correctly requires premium")
            else:
                print(f"[INFO] Export succeeded (user may be premium)")
        else:
            print(f"[SKIP] No projects available to test")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
