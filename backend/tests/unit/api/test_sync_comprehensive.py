"""
Comprehensive Unit Tests for Sync API Endpoints
Tests for: sandbox operations, S3 operations, file sync
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
from faker import Faker
from uuid import uuid4

from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus, ProjectMode
from app.core.security import get_password_hash, create_access_token

fake = Faker()


class TestSandboxOperations:
    """Test sandbox file operations"""

    @pytest.mark.asyncio
    async def test_write_to_sandbox_success(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test writing file to sandbox"""
        project = Project(
            user_id=str(test_user.id),
            title="Sandbox Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        request_data = {
            "project_id": str(project.id),
            "path": "src/index.js",
            "content": "console.log('Hello World');",
            "language": "javascript"
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.create_sandbox = AsyncMock(return_value=True)
            mock_storage.write_to_sandbox = AsyncMock(return_value=True)
            with patch('app.services.storage_service.storage_service') as mock_s3:
                mock_s3.upload_file = AsyncMock(return_value={"s3_key": "test/key"})
                response = await client.post(
                    "/api/v1/sync/sandbox/file",
                    json=request_data,
                    headers=auth_headers
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_write_to_sandbox_failure(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test sandbox write failure"""
        project = Project(
            user_id=str(test_user.id),
            title="Sandbox Fail Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        request_data = {
            "project_id": str(project.id),
            "path": "src/index.js",
            "content": "test content"
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.create_sandbox = AsyncMock(return_value=True)
            mock_storage.write_to_sandbox = AsyncMock(return_value=False)
            response = await client.post(
                "/api/v1/sync/sandbox/file",
                json=request_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_write_multiple_to_sandbox(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test writing multiple files to sandbox"""
        project = Project(
            user_id=str(test_user.id),
            title="Bulk Sandbox Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        request_data = {
            "project_id": str(project.id),
            "files": [
                {"path": "src/index.js", "content": "console.log('A');"},
                {"path": "src/utils.js", "content": "export {};"},
                {"path": "package.json", "content": "{}"}
            ]
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.create_sandbox = AsyncMock(return_value=True)
            mock_storage.write_to_sandbox = AsyncMock(return_value=True)
            response = await client.post(
                "/api/v1/sync/sandbox/files",
                json=request_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["files_synced"] == 3

    @pytest.mark.asyncio
    async def test_get_sandbox_files(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting files from sandbox"""
        project = Project(
            user_id=str(test_user.id),
            title="Get Sandbox Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        mock_file_info = MagicMock()
        mock_file_info.type = "file"
        mock_file_info.path = "src/index.js"
        mock_file_info.children = None
        mock_file_info.to_dict = MagicMock(return_value={
            "path": "src/index.js",
            "name": "index.js",
            "type": "file"
        })

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.list_sandbox_files = AsyncMock(return_value=[mock_file_info])
            mock_storage.read_from_sandbox = AsyncMock(return_value="console.log('test');")
            mock_storage._flatten_tree = MagicMock(return_value=[mock_file_info])
            response = await client.get(
                f"/api/v1/sync/sandbox/{project.id}/files",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tree" in data

    @pytest.mark.asyncio
    async def test_get_sandbox_files_empty(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting files from empty sandbox"""
        project = Project(
            user_id=str(test_user.id),
            title="Empty Sandbox Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.list_sandbox_files = AsyncMock(return_value=[])
            response = await client.get(
                f"/api/v1/sync/sandbox/{project.id}/files",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tree"] == []

    @pytest.mark.asyncio
    async def test_delete_sandbox(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test deleting sandbox"""
        project = Project(
            user_id=str(test_user.id),
            title="Delete Sandbox Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.delete_sandbox = AsyncMock(return_value=True)
            response = await client.delete(
                f"/api/v1/sync/sandbox/{project.id}",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestS3Operations:
    """Test S3 storage operations"""

    @pytest.mark.asyncio
    async def test_save_to_s3_success(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test saving project to S3"""
        project = Project(
            user_id=str(test_user.id),
            title="S3 Save Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        request_data = {
            "project_id": str(project.id),
            "create_zip": True
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.sandbox_exists = AsyncMock(return_value=True)
            mock_storage.save_project = AsyncMock(return_value={
                "success": True,
                "s3_prefix": "projects/test",
                "zip_s3_key": "projects/test.zip",
                "file_index": [],
                "total_files": 5,
                "total_size_bytes": 1024
            })
            response = await client.post(
                "/api/v1/sync/s3/save",
                json=request_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_save_to_s3_sandbox_not_found(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test saving to S3 when sandbox doesn't exist"""
        project = Project(
            user_id=str(test_user.id),
            title="S3 No Sandbox Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        request_data = {
            "project_id": str(project.id),
            "create_zip": True
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.sandbox_exists = AsyncMock(return_value=False)
            response = await client.post(
                "/api/v1/sync/s3/save",
                json=request_data,
                headers=auth_headers
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_download_url(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting download URL"""
        project = Project(
            user_id=str(test_user.id),
            title="Download URL Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.get_download_url = AsyncMock(return_value="https://s3.example.com/download")
            response = await client.get(
                f"/api/v1/sync/s3/{project.id}/download-url",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "download_url" in data


class TestGetProjectFiles:
    """Test unified get project files endpoint"""

    @pytest.mark.asyncio
    async def test_get_files_from_sandbox(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting files - sandbox layer"""
        project = Project(
            user_id=str(test_user.id),
            title="Get Files Sandbox Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        mock_file_info = MagicMock()
        mock_file_info.type = "file"
        mock_file_info.path = "src/index.js"
        mock_file_info.children = None
        mock_file_info.to_dict = MagicMock(return_value={
            "path": "src/index.js",
            "name": "index.js",
            "type": "file"
        })

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.sandbox_exists = AsyncMock(return_value=True)
            mock_storage.list_sandbox_files = AsyncMock(return_value=[mock_file_info])
            mock_storage.read_from_sandbox = AsyncMock(return_value="test content")
            mock_storage._flatten_tree = MagicMock(return_value=[mock_file_info])
            response = await client.get(
                f"/api/v1/sync/files/{project.id}",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["layer"] == "sandbox"

    @pytest.mark.asyncio
    async def test_get_files_no_files(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting files when no files exist"""
        project = Project(
            user_id=str(test_user.id),
            title="No Files Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.sandbox_exists = AsyncMock(return_value=False)
            mock_storage.list_sandbox_files = AsyncMock(return_value=[])
            # Need to mock the internal session calls
            with patch('app.api.v1.endpoints.sync.AsyncSessionLocal'):
                response = await client.get(
                    f"/api/v1/sync/files/{project.id}",
                    headers=auth_headers
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestListProjects:
    """Test list projects endpoint in sync module"""

    @pytest.mark.asyncio
    async def test_list_sync_projects(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test listing projects from sync endpoint"""
        project = Project(
            user_id=str(test_user.id),
            title="Sync Project",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()

        response = await client.get(
            "/api/v1/sync/projects",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "projects" in data


class TestLegacyEndpoints:
    """Test legacy compatibility endpoints"""

    @pytest.mark.asyncio
    async def test_legacy_file_sync(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test legacy /file endpoint"""
        project = Project(
            user_id=str(test_user.id),
            title="Legacy Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        request_data = {
            "project_id": str(project.id),
            "path": "test.js",
            "content": "test"
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.create_sandbox = AsyncMock(return_value=True)
            mock_storage.write_to_sandbox = AsyncMock(return_value=True)
            with patch('app.services.storage_service.storage_service') as mock_s3:
                mock_s3.upload_file = AsyncMock(return_value={"s3_key": "test"})
                response = await client.post(
                    "/api/v1/sync/file",
                    json=request_data,
                    headers=auth_headers
                )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_legacy_files_sync(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test legacy /files endpoint"""
        project = Project(
            user_id=str(test_user.id),
            title="Legacy Files Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        request_data = {
            "project_id": str(project.id),
            "files": [{"path": "test.js", "content": "test"}]
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.create_sandbox = AsyncMock(return_value=True)
            mock_storage.write_to_sandbox = AsyncMock(return_value=True)
            response = await client.post(
                "/api/v1/sync/files",
                json=request_data,
                headers=auth_headers
            )

        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling in sync endpoints"""

    @pytest.mark.asyncio
    async def test_invalid_project_id_format(self, client: AsyncClient, auth_headers):
        """Test handling invalid project ID"""
        request_data = {
            "project_id": "not-a-valid-uuid",
            "path": "test.js",
            "content": "test"
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.create_sandbox = AsyncMock(return_value=True)
            mock_storage.write_to_sandbox = AsyncMock(return_value=True)
            response = await client.post(
                "/api/v1/sync/sandbox/file",
                json=request_data,
                headers=auth_headers
            )

        # Should handle gracefully
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_storage_exception_handling(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test handling storage exceptions"""
        project = Project(
            user_id=str(test_user.id),
            title="Exception Test",
            description="Test",
            mode=ProjectMode.STUDENT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        request_data = {
            "project_id": str(project.id),
            "path": "test.js",
            "content": "test"
        }

        with patch('app.services.unified_storage.unified_storage') as mock_storage:
            mock_storage.create_sandbox = AsyncMock(side_effect=Exception("Storage error"))
            response = await client.post(
                "/api/v1/sync/sandbox/file",
                json=request_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
