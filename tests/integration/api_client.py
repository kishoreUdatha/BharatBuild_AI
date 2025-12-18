"""
BharatBuild AI - API Client for Integration Testing
Direct API calls to test backend endpoints.
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json

from config import config


@dataclass
class APIResponse:
    """API Response wrapper"""
    status: int
    data: Any
    headers: Dict[str, str]
    success: bool

    @property
    def json(self) -> Any:
        return self.data


class BharatBuildAPIClient:
    """API Client for BharatBuild AI backend"""

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or config.api_base_url).rstrip('/')
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self, auth: bool = True) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        auth: bool = True,
        timeout: int = None
    ) -> APIResponse:
        """Make HTTP request"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(auth)
        timeout_obj = aiohttp.ClientTimeout(total=timeout or config.request_timeout)

        try:
            async with self.session.request(
                method, url, json=data, headers=headers, timeout=timeout_obj
            ) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()

                return APIResponse(
                    status=response.status,
                    data=response_data,
                    headers=dict(response.headers),
                    success=200 <= response.status < 300
                )
        except Exception as e:
            return APIResponse(
                status=0,
                data={"error": str(e)},
                headers={},
                success=False
            )

    # ==================== Health ====================
    async def health_check(self) -> APIResponse:
        """Check API health"""
        return await self._request("GET", "/health", auth=False)

    # ==================== Authentication ====================
    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        role: str = "student",
        **kwargs
    ) -> APIResponse:
        """Register a new user"""
        data = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
            "roll_number": kwargs.get("roll_number", "TEST001"),
            "college_name": kwargs.get("college_name", "Test College"),
            "university_name": kwargs.get("university_name", "Test University"),
            "department": kwargs.get("department", "Computer Science"),
            "course": kwargs.get("course", "B.Tech"),
            "year_semester": kwargs.get("year_semester", "4th Year"),
            "batch": kwargs.get("batch", "2021-2025"),
            "guide_name": kwargs.get("guide_name", "Dr. Test Guide"),
            "guide_designation": kwargs.get("guide_designation", "Professor"),
            "hod_name": kwargs.get("hod_name", "Dr. HOD Test")
        }
        return await self._request("POST", "/auth/register", data=data, auth=False)

    async def login(self, email: str, password: str) -> APIResponse:
        """Login user"""
        data = {"email": email, "password": password}
        response = await self._request("POST", "/auth/login", data=data, auth=False)

        if response.success and isinstance(response.data, dict):
            self.token = response.data.get("access_token")
            self.refresh_token = response.data.get("refresh_token")

        return response

    async def get_current_user(self) -> APIResponse:
        """Get current user info"""
        return await self._request("GET", "/auth/me")

    async def refresh_access_token(self) -> APIResponse:
        """Refresh access token"""
        data = {"refresh_token": self.refresh_token}
        response = await self._request("POST", "/auth/refresh", data=data, auth=False)

        if response.success and isinstance(response.data, dict):
            self.token = response.data.get("access_token")

        return response

    async def logout(self) -> APIResponse:
        """Logout user"""
        response = await self._request("POST", "/auth/logout")
        self.token = None
        self.refresh_token = None
        return response

    # ==================== Projects ====================
    async def list_projects(self, page: int = 1, page_size: int = 10) -> APIResponse:
        """List user projects"""
        return await self._request("GET", f"/projects?page={page}&page_size={page_size}")

    async def get_project(self, project_id: str) -> APIResponse:
        """Get project details"""
        return await self._request("GET", f"/projects/{project_id}")

    async def create_project(self, name: str, prompt: str, project_type: str = "web") -> APIResponse:
        """Create a new project"""
        data = {
            "name": name,
            "prompt": prompt,
            "project_type": project_type
        }
        return await self._request("POST", "/projects", data=data)

    async def delete_project(self, project_id: str) -> APIResponse:
        """Delete a project"""
        return await self._request("DELETE", f"/projects/{project_id}")

    async def get_project_files(self, project_id: str) -> APIResponse:
        """Get project files"""
        return await self._request("GET", f"/projects/{project_id}/files")

    async def get_file_content(self, project_id: str, file_path: str) -> APIResponse:
        """Get file content"""
        return await self._request("GET", f"/projects/{project_id}/files/{file_path}")

    # ==================== Documents ====================
    async def get_document_types(self) -> APIResponse:
        """Get available document types"""
        return await self._request("GET", "/documents/types", auth=False)

    async def list_documents(self, project_id: str) -> APIResponse:
        """List project documents"""
        return await self._request("GET", f"/documents/list/{project_id}")

    async def generate_document(self, project_id: str, doc_type: str) -> APIResponse:
        """Generate a document"""
        return await self._request("POST", f"/documents/generate/{project_id}/{doc_type}", timeout=120)

    async def download_document(self, project_id: str, doc_type: str) -> APIResponse:
        """Download a document"""
        return await self._request("GET", f"/documents/download/{project_id}/{doc_type}")

    # ==================== Users ====================
    async def get_plan_status(self) -> APIResponse:
        """Get user's plan status"""
        return await self._request("GET", "/users/plan-status")

    async def get_token_balance(self) -> APIResponse:
        """Get user's token balance"""
        return await self._request("GET", "/users/token-balance")

    async def update_profile(self, data: Dict) -> APIResponse:
        """Update user profile"""
        return await self._request("PUT", "/users/profile", data=data)

    # ==================== Execution ====================
    async def run_project(self, project_id: str) -> APIResponse:
        """Run/execute a project"""
        return await self._request("POST", f"/execution/run/{project_id}", timeout=60)

    async def stop_execution(self, project_id: str) -> APIResponse:
        """Stop project execution"""
        return await self._request("POST", f"/execution/stop/{project_id}")

    async def export_project(self, project_id: str) -> APIResponse:
        """Export project as ZIP"""
        return await self._request("GET", f"/execution/export/{project_id}")


# Synchronous wrapper for non-async contexts
class SyncAPIClient:
    """Synchronous wrapper for API client"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url

    def _run(self, coro):
        """Run coroutine synchronously"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def health_check(self):
        async def _call():
            async with BharatBuildAPIClient(self.base_url) as client:
                return await client.health_check()
        return self._run(_call())

    def login(self, email: str, password: str):
        async def _call():
            async with BharatBuildAPIClient(self.base_url) as client:
                return await client.login(email, password)
        return self._run(_call())

    def register(self, email: str, password: str, full_name: str, **kwargs):
        async def _call():
            async with BharatBuildAPIClient(self.base_url) as client:
                return await client.register(email, password, full_name, **kwargs)
        return self._run(_call())


if __name__ == "__main__":
    # Quick test
    async def test():
        async with BharatBuildAPIClient() as client:
            # Health check
            response = await client.health_check()
            print(f"Health: {response.status} - {response.data}")

            # Document types
            response = await client.get_document_types()
            print(f"Doc Types: {response.status} - {len(response.data) if isinstance(response.data, list) else response.data}")

    asyncio.run(test())
