"""OAuth providers module for Google and GitHub authentication."""

from .google_provider import GoogleOAuthProvider
from .github_provider import GitHubOAuthProvider

__all__ = ["GoogleOAuthProvider", "GitHubOAuthProvider"]
