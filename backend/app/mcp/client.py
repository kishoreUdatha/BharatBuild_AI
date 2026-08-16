"""
BharatBuild MCP Client

Connects to external MCP servers (GitHub, Vercel, etc.) to perform
deployment and integration tasks on behalf of the user.

Usage:
    from app.mcp.client import mcp_client
    
    # Deploy to GitHub + Vercel
    result = await mcp_client.deploy_project(
        project_id="abc123",
        github_repo="my-quiz-app",
        deploy_to="vercel"
    )
    # result = {"github_url": "...", "live_url": "https://my-quiz-app.vercel.app"}
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP Client that connects to external tool servers.
    
    For BharatBuild, we use direct API integrations (GitHub API, Vercel API)
    rather than stdio-based MCP servers, since the backend is a web server.
    This provides the same functionality with simpler deployment.
    
    When MCP-over-HTTP (Streamable HTTP transport) becomes standard,
    this can be upgraded to use actual MCP protocol.
    """
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.vercel_token = os.getenv("VERCEL_TOKEN", "")
        self.netlify_token = os.getenv("NETLIFY_TOKEN", "")
        
    @property
    def github_available(self) -> bool:
        return bool(self.github_token)
    
    @property
    def vercel_available(self) -> bool:
        return bool(self.vercel_token)

    async def deploy_project(
        self,
        project_id: str,
        user_id: str,
        repo_name: str,
        deploy_to: str = "vercel",
        is_private: bool = False,
        custom_domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full deployment pipeline: GitHub + hosting platform.
        
        Steps:
        1. Create GitHub repo
        2. Push all project files
        3. Deploy to Vercel/Netlify
        4. Return live URL
        
        Args:
            project_id: BharatBuild project ID
            user_id: User ID
            repo_name: GitHub repository name
            deploy_to: "vercel" or "netlify"
            is_private: Make repo private
            custom_domain: Optional custom domain
            
        Returns:
            {
                "success": True,
                "github_url": "https://github.com/user/repo",
                "live_url": "https://repo.vercel.app",
                "deploy_id": "...",
            }
        """
        result = {
            "success": False,
            "github_url": None,
            "live_url": None,
            "errors": []
        }
        
        # Step 1: Push to GitHub
        if not self.github_available:
            result["errors"].append("GitHub token not configured. Add GITHUB_TOKEN to .env")
            return result
            
        from app.mcp.github_integration import GitHubIntegration
        github = GitHubIntegration(self.github_token)
        
        github_result = await github.create_and_push(
            project_id=project_id,
            user_id=user_id,
            repo_name=repo_name,
            is_private=is_private
        )
        
        if not github_result["success"]:
            result["errors"].append(f"GitHub: {github_result.get('error')}")
            return result
            
        result["github_url"] = github_result["repo_url"]
        logger.info(f"[MCP] GitHub push successful: {result['github_url']}")
        
        # Step 2: Deploy to hosting platform
        if deploy_to == "vercel":
            if not self.vercel_available:
                result["errors"].append("Vercel token not configured. Add VERCEL_TOKEN to .env")
                result["success"] = True  # GitHub succeeded
                return result
                
            from app.mcp.vercel_integration import VercelIntegration
            vercel = VercelIntegration(self.vercel_token)
            
            deploy_result = await vercel.deploy(
                repo_url=result["github_url"],
                project_name=repo_name,
                custom_domain=custom_domain
            )
            
            if deploy_result["success"]:
                result["live_url"] = deploy_result["url"]
                result["deploy_id"] = deploy_result.get("deploy_id")
                logger.info(f"[MCP] Vercel deploy successful: {result['live_url']}")
            else:
                result["errors"].append(f"Vercel: {deploy_result.get('error')}")
        
        elif deploy_to == "netlify":
            if not self.netlify_token:
                result["errors"].append("Netlify token not configured. Add NETLIFY_TOKEN to .env")
                result["success"] = True
                return result
                
            # Netlify integration (similar pattern)
            result["errors"].append("Netlify integration coming soon")
        
        result["success"] = True
        return result

    async def get_deploy_status(self, deploy_id: str, platform: str = "vercel") -> Dict[str, Any]:
        """Check deployment status"""
        if platform == "vercel" and self.vercel_available:
            from app.mcp.vercel_integration import VercelIntegration
            vercel = VercelIntegration(self.vercel_token)
            return await vercel.get_status(deploy_id)
        return {"status": "unknown"}


# Singleton instance
mcp_client = MCPClient()
