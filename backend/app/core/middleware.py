"""
BharatBuild AI - HTTP Middleware
Request/Response logging, timing, and context management
"""

import time
import uuid
from typing import Callable, Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp

from app.core.logging_config import (
    logger,
    set_request_id,
    set_user_id,
    set_project_id,
    generate_request_id,
)


# Paths that should skip detailed logging (health checks, static files)
SKIP_LOGGING_PATHS: Set[str] = {
    "/health",
    "/",
    "/favicon.ico",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Paths that use SSE/streaming and should not be buffered
STREAMING_PATHS: Set[str] = {
    "/api/v1/chat/stream",
    "/api/v1/generate/stream",
    "/api/v1/logs/stream",
    "/api/v1/preview/",
    "/api/v1/execution/run/",
}


def should_skip_logging(path: str) -> bool:
    """Check if path should skip detailed logging"""
    if path in SKIP_LOGGING_PATHS:
        return True
    # Skip static file requests
    if path.startswith("/static/") or path.endswith((".js", ".css", ".png", ".ico")):
        return True
    return False


def is_streaming_path(path: str) -> bool:
    """Check if path uses SSE/streaming responses"""
    for streaming_path in STREAMING_PATHS:
        if path.startswith(streaming_path):
            return True
    return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Features:
    - Generates and tracks request IDs for correlation
    - Logs request method, path, status, and duration
    - Sets context variables for downstream logging
    - Adds X-Request-ID header to responses
    - Handles streaming responses properly
    """

    def __init__(self, app: ASGIApp, log_request_body: bool = False, log_response_body: bool = False):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        set_request_id(request_id)

        # Extract user info from auth header if present (will be set properly after auth)
        # This is a placeholder - actual user_id comes from JWT token in auth dependency

        # Extract project_id from path if present
        path = request.url.path
        if "/projects/" in path:
            try:
                parts = path.split("/projects/")
                if len(parts) > 1:
                    project_id = parts[1].split("/")[0]
                    if project_id and project_id != "projects":
                        set_project_id(project_id)
            except Exception:
                pass

        # Skip detailed logging for certain paths
        skip_logging = should_skip_logging(path)
        is_streaming = is_streaming_path(path)

        # Record start time
        start_time = time.perf_counter()

        # Log request start (for non-skipped paths)
        if not skip_logging:
            client_ip = request.client.host if request.client else "unknown"
            logger.info(
                f"→ {request.method} {path}",
                extra={
                    "event_type": "http_request_start",
                    "http_method": request.method,
                    "http_path": path,
                    "client_ip": client_ip,
                    "user_agent": request.headers.get("user-agent", ""),
                    "content_length": request.headers.get("content-length", 0),
                }
            )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Log response (for non-skipped paths)
            if not skip_logging:
                status_code = response.status_code

                # Determine log level based on status code
                if status_code >= 500:
                    log_level = "error"
                elif status_code >= 400:
                    log_level = "warning"
                else:
                    log_level = "info"

                log_func = getattr(logger, log_level)
                log_func(
                    f"← {request.method} {path} - {status_code} ({duration_ms:.2f}ms)",
                    extra={
                        "event_type": "http_request_complete",
                        "http_method": request.method,
                        "http_path": path,
                        "http_status": status_code,
                        "duration_ms": duration_ms,
                        "is_streaming": is_streaming,
                    }
                )

                # Performance warning for slow requests
                if duration_ms > 1000 and not is_streaming:
                    logger.warning(
                        f"Slow request: {request.method} {path} took {duration_ms:.2f}ms",
                        extra={
                            "event_type": "slow_request",
                            "http_method": request.method,
                            "http_path": path,
                            "duration_ms": duration_ms,
                        }
                    )

            return response

        except Exception as exc:
            # Calculate duration even on error
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log error
            logger.error(
                f"✗ {request.method} {path} - Exception ({duration_ms:.2f}ms): {type(exc).__name__}",
                exc_info=True,
                extra={
                    "event_type": "http_request_error",
                    "http_method": request.method,
                    "http_path": path,
                    "duration_ms": duration_ms,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            raise

        finally:
            # Clear context variables
            set_request_id("")
            set_user_id("")
            set_project_id("")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        path = request.url.path

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Allow iframe embedding for preview routes (needed for preview iframe in bharatbuild.ai)
        # Preview subdomain URLs (*.bharatbuild.ai) need to be embeddable in main app (bharatbuild.ai)
        # X-Frame-Options doesn't support wildcards, so we remove it for preview and use CSP instead
        if path.startswith("/api/v1/preview/"):
            # Allow embedding from main bharatbuild.ai domain and its subdomains
            response.headers["Content-Security-Policy"] = "frame-ancestors https://bharatbuild.ai https://*.bharatbuild.ai"
            # Remove X-Frame-Options as CSP frame-ancestors takes precedence
        else:
            response.headers["X-Frame-Options"] = "DENY"

        # CSP is typically handled by frontend/nginx, but add basic one here
        # response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size
    """

    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")

        if content_length:
            if int(content_length) > self.max_size:
                logger.warning(
                    f"Request body too large: {content_length} bytes (max: {self.max_size})",
                    extra={
                        "event_type": "request_too_large",
                        "content_length": int(content_length),
                        "max_size": self.max_size,
                        "http_path": request.url.path,
                    }
                )
                from starlette.responses import JSONResponse
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Maximum size is {self.max_size // 1024 // 1024}MB"}
                )

        return await call_next(request)


class SubdomainPreviewMiddleware:
    """
    Pure ASGI Middleware to route subdomain-based preview requests.

    Enables production-grade preview URLs like Vercel/Netlify:
    - {project_id}.bharatbuild.ai/path -> /api/v1/preview/{project_id}/path

    This allows Vite/React to work at root "/" without base path hacks.

    NOTE: Uses pure ASGI instead of BaseHTTPMiddleware to properly modify the scope.
    BaseHTTPMiddleware's call_next doesn't respect modified requests.
    """

    # Domain suffix for preview subdomains
    PREVIEW_DOMAIN = ".bharatbuild.ai"

    # Subdomains to exclude (main site)
    EXCLUDED_SUBDOMAINS = {"www", "api", "app", "dashboard", "admin", ""}

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get host header from scope
        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode().lower()

        # Remove port if present
        if ":" in host:
            host = host.split(":")[0]

        # Check if this is a preview subdomain request
        if host.endswith(self.PREVIEW_DOMAIN):
            subdomain = host[:-len(self.PREVIEW_DOMAIN)]

            # Skip main domains (www.bharatbuild.ai, bharatbuild.ai)
            if subdomain and subdomain not in self.EXCLUDED_SUBDOMAINS:
                # This is a preview subdomain like abc123.bharatbuild.ai
                project_id = subdomain
                original_path = scope.get("path", "/")

                # Rewrite the request to go through preview proxy
                # /index.html -> /api/v1/preview/{project_id}/index.html
                new_path = f"/api/v1/preview/{project_id}{original_path}"

                logger.info(
                    f"[SubdomainPreview] Routing {host}{original_path} -> {new_path}",
                    extra={
                        "event_type": "subdomain_preview",
                        "subdomain": subdomain,
                        "project_id": project_id,
                        "original_path": original_path,
                        "new_path": new_path,
                    }
                )

                # Modify scope directly - this is the key difference from BaseHTTPMiddleware
                modified_scope = scope.copy()
                modified_scope["path"] = new_path
                modified_scope["raw_path"] = new_path.encode()

                # Pass modified scope to app
                await self.app(modified_scope, receive, send)
                return

        # Not a preview subdomain, proceed normally
        await self.app(scope, receive, send)


# Export all middleware
__all__ = [
    "RequestLoggingMiddleware",
    "SecurityHeadersMiddleware",
    "RequestSizeLimitMiddleware",
    "SubdomainPreviewMiddleware",
    "should_skip_logging",
    "is_streaming_path",
    "SKIP_LOGGING_PATHS",
    "STREAMING_PATHS",
]
