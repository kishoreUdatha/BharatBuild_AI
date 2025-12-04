"""GitHub OAuth provider for authentication."""

import httpx
from typing import Optional, Dict, Any, List

from app.core.config import settings


class GitHubOAuthProvider:
    """Handle GitHub OAuth authentication."""

    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"
    GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

    def __init__(self):
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.redirect_uri = settings.GITHUB_REDIRECT_URI

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate GitHub OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "read:user user:email",
        }
        if state:
            params["state"] = state

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.GITHUB_AUTH_URL}?{query_string}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GITHUB_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from GitHub."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_user_emails(self, access_token: str) -> List[Dict[str, Any]]:
        """Get user's email addresses from GitHub."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GITHUB_EMAILS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            response.raise_for_status()
            return response.json()

    def get_primary_email(self, emails: List[Dict[str, Any]]) -> Optional[str]:
        """Extract primary email from GitHub emails response."""
        # First try to find primary and verified email
        for email in emails:
            if email.get("primary") and email.get("verified"):
                return email.get("email")

        # Fall back to any verified email
        for email in emails:
            if email.get("verified"):
                return email.get("email")

        # Fall back to primary email even if not verified
        for email in emails:
            if email.get("primary"):
                return email.get("email")

        # Return first email if available
        return emails[0].get("email") if emails else None

    async def authenticate(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Complete OAuth flow: exchange code and get user info.

        Returns user data if successful, None otherwise.
        """
        try:
            # Exchange code for tokens
            tokens = await self.exchange_code_for_tokens(code)
            access_token = tokens.get("access_token")

            if not access_token:
                return None

            # Get user info
            user_info = await self.get_user_info(access_token)

            # Get email (GitHub may not return email in user info)
            email = user_info.get("email")
            if not email:
                emails = await self.get_user_emails(access_token)
                email = self.get_primary_email(emails)

            return {
                "github_id": str(user_info.get("id")),
                "email": email,
                "full_name": user_info.get("name") or user_info.get("login", ""),
                "avatar_url": user_info.get("avatar_url", ""),
                "username": user_info.get("login", ""),
                "bio": user_info.get("bio", ""),
                "company": user_info.get("company", ""),
                "location": user_info.get("location", ""),
            }
        except Exception:
            return None


# Singleton instance
github_oauth = GitHubOAuthProvider()
