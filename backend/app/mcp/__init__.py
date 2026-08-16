"""
BharatBuild MCP Integration

Provides MCP Client capabilities for:
- GitHub: Create repos, push code
- Vercel: Deploy and get live URLs
- Netlify: Alternative deployment
"""

from app.mcp.client import mcp_client

__all__ = ["mcp_client"]
