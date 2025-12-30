"""
Preview URL Generation - Single Source of Truth

This module provides THE ONLY way to generate preview URLs.
DO NOT create preview URLs anywhere else in the codebase.

ARCHITECTURE:
- Local development: http://localhost:{port}
- Production (subdomain): https://{project_id}.bharatbuild.ai/
- Production (path-based fallback): /api/v1/preview/{project_id}/

The URL strategy depends on:
1. ENVIRONMENT variable (development/production)
2. SANDBOX_PUBLIC_URL for direct container access
3. FRONTEND_URL for API proxy path
4. USE_SUBDOMAIN_PREVIEW for subdomain-based routing (production)
"""

import os
from typing import Optional
from urllib.parse import urlparse

from app.core.logging_config import logger


# =============================================================================
# CONFIGURATION
# =============================================================================

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"

# URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL", os.getenv("SANDBOX_PREVIEW_BASE_URL", ""))
API_BASE_PATH = "/api/v1"

# Subdomain-based preview (Vercel/Netlify style)
# Format: https://{project_id}.bharatbuild.ai/
USE_SUBDOMAIN_PREVIEW = os.getenv("USE_SUBDOMAIN_PREVIEW", "true").lower() == "true"
PREVIEW_DOMAIN = os.getenv("PREVIEW_DOMAIN", "bharatbuild.ai")

# Preview path template (fallback for path-based routing)
PREVIEW_PATH_TEMPLATE = f"{API_BASE_PATH}/preview/{{project_id}}/"


# =============================================================================
# URL GENERATION
# =============================================================================

def get_preview_url(
    port: int,
    project_id: str,
    force_direct: bool = False
) -> str:
    """
    Generate the preview URL for a project.

    THIS IS THE ONLY FUNCTION TO USE FOR PREVIEW URLs.

    Args:
        port: The port the dev server is running on inside the container
        project_id: The project ID
        force_direct: If True, always return direct URL (for internal use)

    Returns:
        The preview URL to use

    Examples:
        Local dev:    http://localhost:3000
        Production:   https://app.bharatbuild.ai/api/v1/preview/abc123/
        Direct:       http://192.168.1.100:3000
    """
    # Force direct mode (for internal health checks, etc.)
    if force_direct:
        return _get_direct_url(port)

    # Production mode: Use API proxy
    if IS_PRODUCTION:
        return _get_proxy_url(project_id)

    # Development mode with sandbox URL configured
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL not in ("", "http://localhost"):
        return _get_sandbox_url(port)

    # Default: localhost
    return f"http://localhost:{port}"


def get_preview_url_internal(port: int) -> str:
    """
    Get the internal URL for health checks.

    This is the URL to use when checking if the server is running
    from WITHIN the backend (not from the browser).
    """
    return f"http://localhost:{port}"


def get_websocket_url(port: int, project_id: str, path: str = "") -> str:
    """
    Generate WebSocket URL for HMR (Hot Module Replacement).

    Args:
        port: The port the dev server is running on
        project_id: The project ID
        path: The WebSocket path (e.g., "/@vite/hmr")

    Returns:
        The WebSocket URL
    """
    if IS_PRODUCTION:
        # Use subdomain-based WebSocket (Vercel/Netlify style)
        if USE_SUBDOMAIN_PREVIEW:
            return f"wss://{project_id}.{PREVIEW_DOMAIN}/{path.lstrip('/')}"

        # Fallback: WSS through API proxy
        frontend_parsed = urlparse(FRONTEND_URL)
        protocol = "wss" if frontend_parsed.scheme == "https" else "ws"
        host = frontend_parsed.netloc
        return f"{protocol}://{host}{API_BASE_PATH}/preview/{project_id}/{path.lstrip('/')}"

    # Development: Direct WebSocket
    return f"ws://localhost:{port}/{path.lstrip('/')}"


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _get_proxy_url(project_id: str) -> str:
    """Get URL through API proxy (production mode)"""
    # Use subdomain-based preview (Vercel/Netlify style)
    if USE_SUBDOMAIN_PREVIEW:
        return f"https://{project_id}.{PREVIEW_DOMAIN}/"

    # Fallback: path-based routing
    base = FRONTEND_URL.rstrip("/")
    return f"{base}{PREVIEW_PATH_TEMPLATE.format(project_id=project_id)}"


def _get_sandbox_url(port: int) -> str:
    """Get URL to sandbox server (direct container access)"""
    base = SANDBOX_PUBLIC_URL.rstrip("/")

    # Remove any existing port from the URL
    parsed = urlparse(base)
    if parsed.port:
        # Reconstruct without port
        base = f"{parsed.scheme}://{parsed.hostname}"

    return f"{base}:{port}"


def _get_direct_url(port: int) -> str:
    """Get direct localhost URL"""
    return f"http://localhost:{port}"


# =============================================================================
# URL PARSING (for extracting from logs)
# =============================================================================

def parse_server_url(log_output: str) -> Optional[str]:
    """
    Parse server URL from log output.

    Looks for common patterns like:
    - "Local: http://localhost:5173"
    - "Server running at http://0.0.0.0:3000"
    - "ready on http://localhost:3000"

    Returns:
        The port number if found, None otherwise
    """
    import re

    # Patterns to match (in priority order)
    patterns = [
        # Vite: "Local:   http://localhost:5173/"
        r"Local:\s*https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)",
        # Next.js: "ready on http://localhost:3000"
        r"ready\s+(?:on|at)\s+https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)",
        # Express: "Server listening on port 3000"
        r"(?:listening|running)\s+(?:on\s+)?port\s+(\d+)",
        # Generic: "http://localhost:3000"
        r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, log_output, re.IGNORECASE)
        if match:
            port = int(match.group(1))
            logger.debug(f"[PreviewURL] Parsed port {port} from log output")
            return port

    return None


def is_server_ready(log_output: str) -> bool:
    """
    Check if server ready message is in log output.

    This checks for "ready" patterns WITHOUT extracting the port.
    Use this for confirmation that server has started.
    """
    import re

    ready_patterns = [
        r"ready in \d+",                    # Vite
        r"compiled successfully",           # Webpack
        r"compiled client and server",      # Next.js
        r"Server listening",                # Express
        r"Application startup complete",    # Uvicorn
        r"Started \w+ in \d+",              # Spring Boot
    ]

    for pattern in ready_patterns:
        if re.search(pattern, log_output, re.IGNORECASE):
            return True

    return False


# =============================================================================
# VALIDATION
# =============================================================================

async def check_preview_health(url: str, timeout: float = 5.0) -> bool:
    """
    Check if a preview URL is reachable.

    Args:
        url: The preview URL to check
        timeout: Timeout in seconds

    Returns:
        True if the URL is reachable and returns 2xx/3xx
    """
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                # Accept any success or redirect status
                return response.status < 400
    except Exception as e:
        logger.debug(f"[PreviewURL] Health check failed for {url}: {e}")
        return False


def validate_preview_url(url: str) -> bool:
    """
    Validate that a URL looks like a valid preview URL.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is valid
    """
    try:
        parsed = urlparse(url)
        return all([
            parsed.scheme in ("http", "https"),
            parsed.netloc,
        ])
    except Exception:
        return False
