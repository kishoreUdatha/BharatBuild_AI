"""
Unit Tests for Project Schemas
Tests for: project creation, project responses
"""
import pytest
from pydantic import ValidationError
from datetime import datetime
from uuid import uuid4

from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse
)


class TestProjectCreate:
    """Test ProjectCreate schema"""

    def test_valid_project_create(self):
        """Test creating valid project"""
        data = {
            "title": "Test Project",
            "description": "A test project for unit testing",
            "mode": "student",
            "domain": "web",
            "tech_stack": {"frontend": "react", "backend": "nodejs"},
            "requirements": "Build a simple web app"
        }
        project = ProjectCreate(**data)

        assert project.title == "Test Project"
        assert project.description == "A test project for unit testing"
        assert project.mode == "student"

    def test_project_create_all_modes(self):
        """Test project creation with different modes"""
        modes = ["student", "developer", "founder", "college"]
        for mode in modes:
            data = {
                "title": f"{mode.title()} Project",
                "description": f"A {mode} mode project",
                "mode": mode
            }
            project = ProjectCreate(**data)
            assert project.mode == mode

    def test_project_create_invalid_mode(self):
        """Test project creation with invalid mode fails"""
        data = {
            "title": "Test Project",
            "description": "Test",
            "mode": "invalid_mode"
        }

        with pytest.raises(ValidationError):
            ProjectCreate(**data)

    def test_project_create_short_title_fails(self):
        """Test project creation with too short title fails"""
        data = {
            "title": "AB",  # Less than 3 chars
            "description": "Test description",
            "mode": "student"
        }

        with pytest.raises(ValidationError):
            ProjectCreate(**data)

    def test_project_create_long_title_fails(self):
        """Test project creation with too long title fails"""
        data = {
            "title": "A" * 501,  # More than 500 chars
            "description": "Test description",
            "mode": "student"
        }

        with pytest.raises(ValidationError):
            ProjectCreate(**data)

    def test_project_create_with_tech_stack(self):
        """Test project creation with tech stack dict"""
        data = {
            "title": "Tech Stack Project",
            "description": "Project with detailed tech stack",
            "mode": "developer",
            "tech_stack": {
                "frontend": "React",
                "backend": "FastAPI",
                "database": "PostgreSQL"
            }
        }
        project = ProjectCreate(**data)

        assert project.tech_stack["frontend"] == "React"
        assert project.tech_stack["backend"] == "FastAPI"

    def test_project_create_with_optional_fields(self):
        """Test project creation with all optional fields"""
        data = {
            "title": "Full Project",
            "description": "A complete project with all fields",
            "mode": "founder",
            "domain": "fintech",
            "framework": "Next.js",
            "deployment_target": "AWS",
            "industry": "Finance",
            "target_market": "B2B",
            "features": ["auth", "payments", "dashboard"]
        }
        project = ProjectCreate(**data)

        assert project.domain == "fintech"
        assert project.framework == "Next.js"
        assert project.features == ["auth", "payments", "dashboard"]


class TestProjectUpdate:
    """Test ProjectUpdate schema"""

    def test_valid_project_update(self):
        """Test valid project update"""
        data = {
            "title": "Updated Title",
            "description": "Updated description"
        }
        update = ProjectUpdate(**data)

        assert update.title == "Updated Title"
        assert update.description == "Updated description"

    def test_project_update_partial(self):
        """Test partial project update"""
        data = {
            "title": "Only Title Update"
        }
        update = ProjectUpdate(**data)

        assert update.title == "Only Title Update"
        assert update.description is None

    def test_project_update_empty(self):
        """Test empty project update"""
        data = {}
        update = ProjectUpdate(**data)

        assert update.title is None
        assert update.description is None
        assert update.status is None

    def test_project_update_status(self):
        """Test project status update"""
        data = {
            "status": "completed"
        }
        update = ProjectUpdate(**data)

        assert update.status == "completed"


class TestProjectResponse:
    """Test ProjectResponse schema"""

    def test_valid_project_response(self):
        """Test valid project response"""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "title": "Test Project",
            "description": "Test description",
            "mode": "student",
            "status": "draft",
            "created_at": datetime.utcnow()
        }
        response = ProjectResponse(**data)

        assert response.title == "Test Project"
        assert response.status == "draft"

    def test_project_response_with_progress(self):
        """Test project response with progress"""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "title": "In Progress Project",
            "description": "Test description",
            "mode": "developer",
            "status": "in_progress",
            "progress": 50,
            "current_agent": "writer",
            "created_at": datetime.utcnow()
        }
        response = ProjectResponse(**data)

        assert response.progress == 50
        assert response.current_agent == "writer"

    def test_project_response_with_tokens(self):
        """Test project response with token tracking"""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "title": "Token Project",
            "description": "Test description",
            "mode": "student",
            "status": "completed",
            "total_tokens": 5000,
            "total_cost": 100,
            "created_at": datetime.utcnow()
        }
        response = ProjectResponse(**data)

        assert response.total_tokens == 5000
        assert response.total_cost == 100

    def test_project_response_dates(self):
        """Test project response with date fields"""
        now = datetime.utcnow()
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "title": "Dated Project",
            "description": "Test description",
            "mode": "college",
            "status": "completed",
            "created_at": now,
            "updated_at": now,
            "completed_at": now
        }
        response = ProjectResponse(**data)

        assert response.created_at == now
        assert response.completed_at == now


class TestProjectListResponse:
    """Test ProjectListResponse schema"""

    def test_valid_project_list_response(self):
        """Test valid project list response"""
        data = {
            "projects": [
                {
                    "id": str(uuid4()),
                    "user_id": str(uuid4()),
                    "title": "Project 1",
                    "description": "Description 1",
                    "mode": "student",
                    "status": "draft",
                    "created_at": datetime.utcnow()
                },
                {
                    "id": str(uuid4()),
                    "user_id": str(uuid4()),
                    "title": "Project 2",
                    "description": "Description 2",
                    "mode": "developer",
                    "status": "completed",
                    "created_at": datetime.utcnow()
                }
            ],
            "total": 2,
            "page": 1,
            "page_size": 10
        }
        response = ProjectListResponse(**data)

        assert len(response.projects) == 2
        assert response.total == 2
        assert response.page == 1

    def test_empty_project_list(self):
        """Test empty project list response"""
        data = {
            "projects": [],
            "total": 0,
            "page": 1,
            "page_size": 10
        }
        response = ProjectListResponse(**data)

        assert len(response.projects) == 0
        assert response.total == 0

    def test_project_list_pagination(self):
        """Test project list with pagination"""
        data = {
            "projects": [],
            "total": 100,
            "page": 5,
            "page_size": 20
        }
        response = ProjectListResponse(**data)

        assert response.page == 5
        assert response.page_size == 20


class TestSchemaValidation:
    """Test schema validation edge cases"""

    def test_project_title_boundary_length(self):
        """Test project title at boundary lengths"""
        # Minimum length (3)
        min_data = {
            "title": "ABC",
            "description": "Test",
            "mode": "student"
        }
        project = ProjectCreate(**min_data)
        assert len(project.title) == 3

        # Maximum length (500)
        max_data = {
            "title": "A" * 500,
            "description": "Test",
            "mode": "student"
        }
        project = ProjectCreate(**max_data)
        assert len(project.title) == 500

    def test_project_with_config(self):
        """Test project with config dict"""
        data = {
            "title": "Config Project",
            "description": "Project with config",
            "mode": "developer",
            "config": {
                "auto_fix": True,
                "max_files": 100,
                "model": "sonnet"
            }
        }
        project = ProjectCreate(**data)

        assert project.config["auto_fix"] is True
        assert project.config["max_files"] == 100


class TestSchemaSerialization:
    """Test schema JSON serialization"""

    def test_project_response_serialization(self):
        """Test ProjectResponse serialization"""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "title": "Serialization Test",
            "description": "Test description",
            "mode": "student",
            "status": "draft",
            "created_at": datetime.utcnow()
        }
        response = ProjectResponse(**data)
        json_data = response.model_dump()

        assert "id" in json_data
        assert "title" in json_data
        assert json_data["title"] == "Serialization Test"

    def test_project_list_serialization(self):
        """Test ProjectListResponse serialization"""
        data = {
            "projects": [
                {
                    "id": str(uuid4()),
                    "user_id": str(uuid4()),
                    "title": "Test",
                    "description": "Test description",
                    "mode": "student",
                    "status": "draft",
                    "created_at": datetime.utcnow()
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 10
        }
        response = ProjectListResponse(**data)
        json_data = response.model_dump()

        assert "projects" in json_data
        assert "total" in json_data
        assert json_data["total"] == 1
