"""
Vercel Integration for BharatBuild MCP Client

Deploys projects to Vercel and returns live URLs.
"""

import logging
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

VERCEL_API = "https://api.vercel.com"


class VercelIntegration:
    """Deploy BharatBuild projects to Vercel"""
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def deploy(
        self,
        repo_url: str,
        project_name: str,
        custom_domain: Optional[str] = None,
        framework: str = "vite"
    ) -> Dict[str, Any]:
        """
        Deploy a GitHub repo to Vercel.
        
        Args:
            repo_url: GitHub repository URL
            project_name: Vercel project name
            custom_domain: Optional custom domain
            framework: Framework preset (vite, nextjs, etc.)
            
        Returns:
            {"success": True, "url": "https://project.vercel.app", "deploy_id": "..."}
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Extract owner/repo from URL
            # https://github.com/user/repo -> user/repo
            parts = repo_url.rstrip('/').split('/')
            github_repo = f"{parts[-2]}/{parts[-1]}"
            
            # Step 1: Create Vercel project linked to GitHub repo
            project_resp = await client.post(
                f"{VERCEL_API}/v10/projects",
                headers=self.headers,
                json={
                    "name": project_name,
                    "framework": framework,
                    "gitRepository": {
                        "repo": github_repo,
                        "type": "github"
                    },
                    "buildCommand": "npm run build" if framework == "vite" else None,
                    "outputDirectory": "dist" if framework == "vite" else None,
                    "installCommand": "npm install"
                }
            )
            
            if project_resp.status_code not in (200, 201):
                # Project might already exist - try to get it
                if project_resp.status_code == 409:
                    logger.info(f"[Vercel] Project {project_name} already exists, triggering deploy")
                else:
                    return {"success": False, "error": f"Failed to create Vercel project: {project_resp.text[:200]}"}
            
            # Step 2: Trigger deployment
            deploy_resp = await client.post(
                f"{VERCEL_API}/v13/deployments",
                headers=self.headers,
                json={
                    "name": project_name,
                    "gitSource": {
                        "repo": github_repo,
                        "ref": "main",
                        "type": "github"
                    },
                    "projectSettings": {
                        "framework": framework,
                        "buildCommand": "npm run build",
                        "outputDirectory": "dist",
                        "installCommand": "npm install"
                    }
                }
            )
            
            if deploy_resp.status_code not in (200, 201):
                return {"success": False, "error": f"Deployment failed: {deploy_resp.text[:200]}"}
            
            deploy_data = deploy_resp.json()
            deploy_id = deploy_data.get("id", "")
            deploy_url = deploy_data.get("url", "")
            
            # Vercel returns URL without https://
            if deploy_url and not deploy_url.startswith("http"):
                deploy_url = f"https://{deploy_url}"
            
            # Production URL (project-name.vercel.app)
            production_url = f"https://{project_name}.vercel.app"
            
            # Step 3: Set custom domain if provided
            if custom_domain:
                await self._add_domain(client, project_name, custom_domain)
                production_url = f"https://{custom_domain}"
            
            logger.info(f"[Vercel] Deployed successfully: {production_url}")
            
            return {
                "success": True,
                "url": production_url,
                "deploy_url": deploy_url,
                "deploy_id": deploy_id,
                "project_name": project_name
            }
    
    async def get_status(self, deploy_id: str) -> Dict[str, Any]:
        """Get deployment status"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{VERCEL_API}/v13/deployments/{deploy_id}",
                headers=self.headers
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": data.get("readyState", "UNKNOWN"),
                    "url": data.get("url", ""),
                    "created": data.get("createdAt", "")
                }
            
            return {"status": "unknown", "error": resp.text[:100]}
    
    async def _add_domain(self, client: httpx.AsyncClient, project_name: str, domain: str):
        """Add custom domain to Vercel project"""
        try:
            await client.post(
                f"{VERCEL_API}/v10/projects/{project_name}/domains",
                headers=self.headers,
                json={"name": domain}
            )
            logger.info(f"[Vercel] Added custom domain: {domain}")
        except Exception as e:
            logger.warning(f"[Vercel] Failed to add domain {domain}: {e}")
