"""
Deploy API Endpoint

Provides one-click deployment from BharatBuild UI:
- Push to GitHub
- Deploy to Vercel/Netlify
- Return live URL
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.api.v1.endpoints.projects import get_current_user
from app.models.user import User
from app.mcp.client import mcp_client

router = APIRouter(prefix="/deploy", tags=["deploy"])


class DeployRequest(BaseModel):
    """Request to deploy a project"""
    project_id: str = Field(..., description="BharatBuild project ID")
    repo_name: str = Field(..., description="GitHub repository name")
    deploy_to: str = Field(default="vercel", description="Deployment platform: vercel or netlify")
    is_private: bool = Field(default=False, description="Make GitHub repo private")
    custom_domain: Optional[str] = Field(default=None, description="Custom domain (e.g., myapp.com)")
    description: Optional[str] = Field(default=None, description="Repository description")


class DeployResponse(BaseModel):
    """Deployment result"""
    success: bool
    github_url: Optional[str] = None
    live_url: Optional[str] = None
    deploy_id: Optional[str] = None
    errors: list = []
    message: str = ""


@router.post("", response_model=DeployResponse)
async def deploy_project(
    request: DeployRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Deploy a BharatBuild project to GitHub + Vercel/Netlify.
    
    One-click deployment:
    1. Creates GitHub repository
    2. Pushes all project files
    3. Deploys to Vercel (auto-build from GitHub)
    4. Returns live URL
    
    Requires GITHUB_TOKEN and VERCEL_TOKEN in environment.
    """
    user_id = str(current_user.id)
    
    # Check if tokens are configured
    if not mcp_client.github_available:
        raise HTTPException(
            status_code=400,
            detail="GitHub token not configured. Add GITHUB_TOKEN to your .env file."
        )
    
    # Deploy
    result = await mcp_client.deploy_project(
        project_id=request.project_id,
        user_id=user_id,
        repo_name=request.repo_name,
        deploy_to=request.deploy_to,
        is_private=request.is_private,
        custom_domain=request.custom_domain,
    )
    
    if result["success"]:
        message = f"Deployed successfully!"
        if result.get("live_url"):
            message += f" Live at: {result['live_url']}"
        elif result.get("github_url"):
            message += f" Code at: {result['github_url']}"
    else:
        message = f"Deployment failed: {', '.join(result.get('errors', []))}"
    
    return DeployResponse(
        success=result["success"],
        github_url=result.get("github_url"),
        live_url=result.get("live_url"),
        deploy_id=result.get("deploy_id"),
        errors=result.get("errors", []),
        message=message
    )


@router.get("/status/{deploy_id}")
async def get_deploy_status(
    deploy_id: str,
    platform: str = "vercel",
    current_user: User = Depends(get_current_user)
):
    """Check deployment status"""
    return await mcp_client.get_deploy_status(deploy_id, platform)


@router.get("/config")
async def get_deploy_config(
    current_user: User = Depends(get_current_user)
):
    """Check which deployment platforms are configured"""
    return {
        "github": mcp_client.github_available,
        "vercel": mcp_client.vercel_available,
        "netlify": bool(mcp_client.netlify_token),
        "message": "Add tokens to .env to enable platforms"
    }
