import pytest
from httpx import AsyncClient


@pytest.fixture
def project_data():
    """Test project data"""
    return {
        "title": "Test E-Commerce Platform",
        "description": "A test e-commerce platform",
        "mode": "student",
        "domain": "Web Development",
        "tech_stack": {
            "frontend": "React",
            "backend": "FastAPI",
            "database": "PostgreSQL"
        },
        "features": ["Shopping Cart", "Payment Integration", "Admin Panel"]
    }


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers, project_data):
    """Test project creation"""
    response = await client.post(
        "/api/v1/projects",
        json=project_data,
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == project_data["title"]
    assert data["mode"] == project_data["mode"]
    assert data["status"] == "draft"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, auth_headers, project_data):
    """Test listing projects"""
    # Create a project first
    await client.post("/api/v1/projects", json=project_data, headers=auth_headers)

    # List projects
    response = await client.get("/api/v1/projects", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert len(data["projects"]) > 0
    assert data["total"] > 0


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, auth_headers, project_data):
    """Test getting specific project"""
    # Create project
    create_response = await client.post(
        "/api/v1/projects",
        json=project_data,
        headers=auth_headers
    )
    project_id = create_response.json()["id"]

    # Get project
    response = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["title"] == project_data["title"]


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_headers, project_data):
    """Test project deletion"""
    # Create project
    create_response = await client.post(
        "/api/v1/projects",
        json=project_data,
        headers=auth_headers
    )
    project_id = create_response.json()["id"]

    # Delete project
    response = await client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify deletion
    get_response = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_project_unauthorized(client: AsyncClient, project_data):
    """Test creating project without authentication"""
    response = await client.post("/api/v1/projects", json=project_data)

    assert response.status_code == 403
