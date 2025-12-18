"""
Comprehensive Unit Tests for Projects API Endpoints
Tests for: create, list, get, delete, files, metadata, messages
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
from faker import Faker
from uuid import uuid4
from datetime import datetime

from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus, ProjectMode
from app.core.security import get_password_hash, create_access_token

fake = Faker()


class TestCreateProject:
    """Test project creation endpoint"""

    @pytest.mark.asyncio
    async def test_create_project_success(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test successful project creation"""
        project_data = {
            "title": "Test Project",
            "description": "A test project for unit testing",
            "mode": "instant",
            "domain": "web",
            "tech_stack": "react,nodejs",
            "requirements": "Build a simple web app"
        }

        with patch('app.api.v1.endpoints.projects.check_project_generation_allowed') as mock_check:
            mock_check.return_value = MagicMock(allowed=True, message="OK")
            response = await client.post(
                "/api/v1/projects/",
                json=project_data,
                headers=auth_headers
            )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == project_data["title"]
        assert data["description"] == project_data["description"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_project_unauthorized(self, client: AsyncClient):
        """Test project creation without auth fails"""
        project_data = {
            "title": "Test Project",
            "description": "Test",
            "mode": "instant"
        }

        response = await client.post("/api/v1/projects/", json=project_data)

        assert response.status_code in [401, 403]


class TestListProjects:
    """Test project listing endpoint"""

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, client: AsyncClient, test_user, auth_headers):
        """Test listing projects when user has none"""
        response = await client.get("/api/v1/projects/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_projects_with_data(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test listing projects with existing data"""
        # Create a project
        project = Project(
            user_id=str(test_user.id),
            title="Test Project",
            description="Test Description",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()

        response = await client.get("/api/v1/projects/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_projects_pagination(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test project listing with pagination"""
        # Create multiple projects
        for i in range(15):
            project = Project(
                user_id=str(test_user.id),
                title=f"Test Project {i}",
                description=f"Description {i}",
                mode=ProjectMode.INSTANT,
                status=ProjectStatus.DRAFT
            )
            db_session.add(project)
        await db_session.commit()

        # Test first page
        response = await client.get(
            "/api/v1/projects/?page=1&page_size=5",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) <= 5
        assert data["page"] == 1
        assert data["page_size"] == 5


class TestSearchProjects:
    """Test project search endpoint"""

    @pytest.mark.asyncio
    async def test_search_projects_by_title(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test searching projects by title"""
        # Create projects
        project1 = Project(
            user_id=str(test_user.id),
            title="React Dashboard",
            description="A dashboard project",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        project2 = Project(
            user_id=str(test_user.id),
            title="Python API",
            description="An API project",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add_all([project1, project2])
        await db_session.commit()

        response = await client.get(
            "/api/v1/projects/search?q=React",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "React"

    @pytest.mark.asyncio
    async def test_search_projects_with_status_filter(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test searching with status filter"""
        project = Project(
            user_id=str(test_user.id),
            title="Test Project",
            description="Test",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.COMPLETED
        )
        db_session.add(project)
        await db_session.commit()

        response = await client.get(
            "/api/v1/projects/search?q=Test&status_filter=completed",
            headers=auth_headers
        )

        assert response.status_code == 200


class TestGetProject:
    """Test get single project endpoint"""

    @pytest.mark.asyncio
    async def test_get_project_success(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting a specific project"""
        project = Project(
            user_id=str(test_user.id),
            title="Test Project",
            description="Test Description",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        response = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Project"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent project"""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/projects/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_other_user(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting another user's project fails"""
        # Create project for a different user
        other_user_id = str(uuid4())
        project = Project(
            user_id=other_user_id,
            title="Other User's Project",
            description="Not yours",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        response = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestProjectMetadata:
    """Test project metadata endpoint"""

    @pytest.mark.asyncio
    async def test_get_project_metadata(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting project metadata"""
        project = Project(
            user_id=str(test_user.id),
            title="Metadata Test Project",
            description="Testing metadata endpoint",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        response = await client.get(
            f"/api/v1/projects/{project.id}/metadata",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_title"] == "Metadata Test Project"
        assert "file_tree" in data
        assert "total_files" in data


class TestProjectFiles:
    """Test project files endpoints"""

    @pytest.mark.asyncio
    async def test_get_project_files_empty(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting files for project with no files"""
        project = Project(
            user_id=str(test_user.id),
            title="Empty Project",
            description="No files",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.project_service.ProjectService.get_project_files') as mock_files:
            mock_files.return_value = []
            response = await client.get(
                f"/api/v1/projects/{project.id}/files",
                headers=auth_headers
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_file(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test creating a file in project"""
        project = Project(
            user_id=str(test_user.id),
            title="File Test Project",
            description="Testing files",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        file_data = {
            "path": "src/index.js",
            "content": "console.log('Hello World');",
            "language": "javascript"
        }

        with patch('app.services.project_service.ProjectService.save_file') as mock_save:
            mock_save.return_value = {
                "id": str(uuid4()),
                "path": "src/index.js",
                "name": "index.js",
                "language": "javascript",
                "size_bytes": 27
            }
            response = await client.post(
                f"/api/v1/projects/{project.id}/files",
                json=file_data,
                headers=auth_headers
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_file_content(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting file content"""
        project = Project(
            user_id=str(test_user.id),
            title="File Content Project",
            description="Testing file content",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.project_service.ProjectService.get_file_content') as mock_content:
            mock_content.return_value = "console.log('Hello');"
            response = await client.get(
                f"/api/v1/projects/{project.id}/files/src/index.js",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting non-existent file"""
        project = Project(
            user_id=str(test_user.id),
            title="File Not Found Project",
            description="Testing",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.project_service.ProjectService.get_file_content') as mock_content:
            mock_content.return_value = None
            response = await client.get(
                f"/api/v1/projects/{project.id}/files/nonexistent.js",
                headers=auth_headers
            )

        assert response.status_code == 404


class TestDeleteProject:
    """Test project deletion endpoint"""

    @pytest.mark.asyncio
    async def test_delete_project_success(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test successful project deletion"""
        project = Project(
            user_id=str(test_user.id),
            title="Delete Me",
            description="Test",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.project_service.ProjectService.delete_project_files') as mock_delete:
            mock_delete.return_value = True
            response = await client.delete(
                f"/api/v1/projects/{project.id}",
                headers=auth_headers
            )

        assert response.status_code == 204


class TestProjectMessages:
    """Test project messages endpoint"""

    @pytest.mark.asyncio
    async def test_get_project_messages(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test getting project messages"""
        project = Project(
            user_id=str(test_user.id),
            title="Messages Test Project",
            description="Testing messages",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.services.message_service.MessageService.get_messages') as mock_msgs:
            mock_msgs.return_value = []
            response = await client.get(
                f"/api/v1/projects/{project.id}/messages",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "messages" in data


class TestBulkFileOperations:
    """Test bulk file operations"""

    @pytest.mark.asyncio
    async def test_bulk_create_files(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test bulk file creation"""
        project = Project(
            user_id=str(test_user.id),
            title="Bulk Files Project",
            description="Testing bulk files",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        bulk_data = {
            "files": [
                {"path": "src/index.js", "content": "console.log('A');"},
                {"path": "src/utils.js", "content": "export const util = () => {};"},
                {"path": "package.json", "content": "{}"}
            ]
        }

        with patch('app.services.project_service.ProjectService.save_multiple_files') as mock_save:
            mock_save.return_value = [
                {"path": "src/index.js", "id": str(uuid4())},
                {"path": "src/utils.js", "id": str(uuid4())},
                {"path": "package.json", "id": str(uuid4())}
            ]
            response = await client.post(
                f"/api/v1/projects/{project.id}/files/bulk",
                json=bulk_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 3


class TestProjectActivity:
    """Test project activity endpoint"""

    @pytest.mark.asyncio
    async def test_update_project_activity(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test updating project activity timestamp"""
        project = Project(
            user_id=str(test_user.id),
            title="Activity Test Project",
            description="Testing activity",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        with patch('app.api.v1.endpoints.projects.touch_project_activity') as mock_touch:
            response = await client.post(
                f"/api/v1/projects/{project.id}/activity",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestFixErrors:
    """Test error fixing endpoints"""

    @pytest.mark.asyncio
    async def test_fix_single_error(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test fixing a single error"""
        project = Project(
            user_id=str(test_user.id),
            title="Fix Error Project",
            description="Testing error fix",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        error_data = {
            "error": {
                "message": "Cannot read property 'x' of undefined",
                "file": "src/index.js",
                "line": 10,
                "source": "browser"
            }
        }

        with patch('app.modules.agents.fixer_agent.FixerAgent.fix_error') as mock_fix:
            mock_fix.return_value = {"success": False}
            response = await client.post(
                f"/api/v1/projects/{project.id}/fix-error",
                json=error_data,
                headers=auth_headers
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_fix_multiple_errors(self, client: AsyncClient, test_user, auth_headers, db_session):
        """Test fixing multiple errors"""
        project = Project(
            user_id=str(test_user.id),
            title="Fix Errors Project",
            description="Testing multiple error fix",
            mode=ProjectMode.INSTANT,
            status=ProjectStatus.DRAFT
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        errors_data = {
            "errors": [
                {"message": "Error 1", "source": "browser"},
                {"message": "Error 2", "source": "build"}
            ]
        }

        with patch('app.modules.agents.fixer_agent.FixerAgent.fix_error') as mock_fix:
            mock_fix.return_value = {"success": False}
            response = await client.post(
                f"/api/v1/projects/{project.id}/fix-errors",
                json=errors_data,
                headers=auth_headers
            )

        assert response.status_code == 200
