"""Google OAuth provider for authentication."""

import httpx
from typing import Optional, Dict, Any
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.core.logging_config import logger


class GoogleOAuthProvider:
    """Handle Google OAuth authentication."""

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.GOOGLE_AUTH_URL}?{query_string}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    def verify_id_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Google ID token (for frontend Google Sign-In).

        This is used when the frontend uses Google Sign-In button
        and sends the credential token directly to the backend.
        """
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                self.client_id
            )

            # Verify the issuer
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                logger.warning("[GoogleOAuth] Invalid token issuer")
                return None

            return {
                "google_id": idinfo["sub"],
                "email": idinfo["email"],
                "email_verified": idinfo.get("email_verified", False),
                "full_name": idinfo.get("name", ""),
                "avatar_url": idinfo.get("picture", ""),
                "given_name": idinfo.get("given_name", ""),
                "family_name": idinfo.get("family_name", ""),
            }
        except ValueError as e:
            logger.error(f"[GoogleOAuth] Invalid ID token: {e}")
            return None
        except Exception as e:
            logger.error(f"[GoogleOAuth] Token verification error: {e}", exc_info=True)
            return None

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
                logger.error("[GoogleOAuth] No access token received from token exchange")
                return None

            # Get user info
            user_info = await self.get_user_info(access_token)

            return {
                "google_id": user_info.get("sub"),
                "email": user_info.get("email"),
                "email_verified": user_info.get("email_verified", False),
                "full_name": user_info.get("name", ""),
                "avatar_url": user_info.get("picture", ""),
                "given_name": user_info.get("given_name", ""),
                "family_name": user_info.get("family_name", ""),
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"[GoogleOAuth] HTTP error during authentication: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"[GoogleOAuth] Request error during authentication: {e}")
            return None
        except Exception as e:
            logger.error(f"[GoogleOAuth] Unexpected error during authentication: {e}", exc_info=True)
            return None


# Singleton instance
google_oauth = GoogleOAuthProvider()
