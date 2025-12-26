"""
Preview Proxy - Bolt.new Style Reverse Proxy for Preview URLs

This implements the production-grade approach used by Bolt.new, Replit, and Codespaces:
- Path-based routing: /preview/{project_id}/{path}
- No public port mapping needed
- Infinite scaling (100k+ concurrent users)
- Complete isolation between sandboxes

Architecture (Updated - uses Traefik Gateway on EC2):
    Browser Request: GET /preview/abc123/index.html
           ↓
    FastAPI Reverse Proxy (this module - runs in ECS)
           ↓
    Traefik Gateway (runs on EC2 sandbox, port 8080)
           ↓
    Docker Internal Network (no host ports!)
           ↓
    Container (localhost:5173/3000/etc)
           ↓
    Return Response to Browser

Key: The Traefik gateway runs ON the EC2 and can reach container internal IPs.
ECS only needs to reach EC2:8080 (the gateway port).
"""

import asyncio
import httpx
import re
import os
import docker
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.modules.execution import get_container_manager
from app.services.container_executor import container_executor
from app.core.logging_config import logger

router = APIRouter(prefix="/preview", tags=["Preview Proxy"])

# Check if using remote Docker (EC2 sandbox)
SANDBOX_DOCKER_HOST = os.environ.get("SANDBOX_DOCKER_HOST", "")
IS_REMOTE_DOCKER = bool(SANDBOX_DOCKER_HOST)

# Preview Gateway port (Traefik on EC2)
PREVIEW_GATEWAY_PORT = int(os.environ.get("PREVIEW_GATEWAY_PORT", "8080"))

# HTTP client for proxying requests
_http_client: Optional[httpx.AsyncClient] = None

# Docker client for querying remote containers
_docker_client: Optional[docker.DockerClient] = None


def get_docker_client() -> Optional[docker.DockerClient]:
    """Get or create Docker client for querying remote containers"""
    global _docker_client
    if _docker_client is None and SANDBOX_DOCKER_HOST:
        try:
            logger.info(f"[Preview] Attempting Docker connection to {SANDBOX_DOCKER_HOST}")
            _docker_client = docker.DockerClient(base_url=SANDBOX_DOCKER_HOST, timeout=5)
            _docker_client.ping()
            logger.info(f"[Preview] Docker client connected successfully to {SANDBOX_DOCKER_HOST}")
        except Exception as e:
            logger.error(f"[Preview] Failed to connect to Docker at {SANDBOX_DOCKER_HOST}: {type(e).__name__}: {e}")
            _docker_client = None
            return None
    elif not SANDBOX_DOCKER_HOST:
        logger.warning("[Preview] SANDBOX_DOCKER_HOST not set, cannot connect to remote Docker")
    return _docker_client


def container_exists_on_docker(project_id: str) -> bool:
    """
    Check if a container exists on EC2 Docker for the project.

    This handles the case where ECS backend restarted and lost in-memory container tracking.
    Containers are discovered by their 'project_id' label.

    Returns:
        True if container exists and is running, False otherwise
    """
    if not IS_REMOTE_DOCKER:
        return False

    docker_client = get_docker_client()
    if not docker_client:
        return False

    try:
        # Query containers by project_id label
        containers = docker_client.containers.list(
            filters={"label": f"project_id={project_id}", "status": "running"}
        )

        if containers:
            container = containers[0]
            logger.info(f"[Preview] Container found on Docker: {project_id} -> {container.name}")
            return True
        else:
            logger.debug(f"[Preview] No running container found for project {project_id}")
            return False

    except Exception as e:
        logger.error(f"[Preview] Error checking container on Docker: {e}")
        return False


def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client for proxying"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,  # Let browser handle redirects
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    return _http_client


async def get_container_internal_address(project_id: str) -> Optional[tuple[str, int, str]]:
    """
    Get the nginx gateway address for a project container.

    Returns:
        Tuple of (ec2_ip, nginx_port, host_port) or None if container not found

    Architecture:
        - nginx on EC2 port 8080 routes /sandbox/{host_port}/ to localhost:{host_port}
        - Container is mapped: internal_port -> host_port
        - ECS calls: EC2_IP:8080/sandbox/{host_port}/path
        - nginx proxies to: localhost:{host_port}/path -> container
    """
    # For remote Docker (EC2 sandbox), route via nginx gateway
    if IS_REMOTE_DOCKER:
        docker_client = get_docker_client()
        if not docker_client:
            logger.error("[Preview] Docker client not available")
            return None

        # Extract EC2 IP from SANDBOX_DOCKER_HOST
        ec2_ip = SANDBOX_DOCKER_HOST.replace("tcp://", "").split(":")[0]

        try:
            # Find container by project_id label
            containers = docker_client.containers.list(
                filters={"label": f"project_id={project_id}", "status": "running"}
            )

            if not containers:
                logger.warning(f"[Preview] No running container found for {project_id}")
                return None

            container = containers[0]
            logger.info(f"[Preview] Container found: {project_id} -> {container.name}")

            # Get host port from container's port bindings
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            host_port = None

            # Find the host port mapping
            for container_port, bindings in ports.items():
                if bindings:
                    host_port = int(bindings[0].get('HostPort', 0))
                    if host_port:
                        logger.info(f"[Preview] Found host port mapping: {container_port} -> {host_port}")
                        break

            if not host_port:
                logger.error(f"[Preview] No host port mapping found for container {container.name}")
                return None

            # Return EC2 IP, nginx port (8080), and host_port for /sandbox/{port}/ routing
            logger.info(f"[Preview] Routing via nginx gateway: {ec2_ip}:8080/sandbox/{host_port}/")
            return (ec2_ip, 8080, str(host_port))  # host_port as string for URL building

        except Exception as e:
            logger.error(f"[Preview] Error getting container address: {e}")
            return None

    # Local Docker mode only (not production - production uses remote Docker)
    manager = get_container_manager()

    # Check if container exists
    if project_id not in manager.containers:
        return None

    container_info = manager.containers[project_id]

    # Get active port (detected from logs) or default
    active_port = container_info.active_port or 3000

    # Get container IP from Docker
    try:
        container = manager.docker.containers.get(container_info.container_id)

        # Get IP address from the sandbox network
        networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})

        # Try bharatbuild-sandbox network first
        if 'bharatbuild-sandbox' in networks:
            ip = networks['bharatbuild-sandbox'].get('IPAddress')
            if ip:
                # Local mode: no gateway, direct to container IP
                return (ip, active_port, None)

        # Try bridge network
        if 'bridge' in networks:
            ip = networks['bridge'].get('IPAddress')
            if ip:
                return (ip, active_port, None)

        # Try any network
        for net_name, net_config in networks.items():
            ip = net_config.get('IPAddress')
            if ip:
                return (ip, active_port, None)

        # Fallback: use container name (Docker DNS)
        container_name = f"bb-{project_id[:12]}"
        return (container_name, active_port, None)

    except Exception as e:
        logger.error(f"Failed to get container address for {project_id}: {e}")
        return None


@router.api_route("/{project_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_preview(project_id: str, path: str, request: Request):
    """
    Reverse proxy to container via Traefik gateway.

    This is the Bolt.new-style preview URL handler:
    - GET /preview/abc123/ → gateway → container abc123 port 3000/5173/etc
    - GET /preview/abc123/index.js → gateway → container
    - All HTTP methods supported (for HMR websockets, API calls, etc.)

    Architecture:
    - Remote mode: ECS → Traefik Gateway (EC2:8080) → Container
    - Local mode: Direct to container IP (for development)
    """
    logger.info(f"[Preview] Incoming request: {request.method} /preview/{project_id}/{path}")
    logger.info(f"[Preview] IS_REMOTE_DOCKER={IS_REMOTE_DOCKER}, SANDBOX_DOCKER_HOST={SANDBOX_DOCKER_HOST}")

    # Get container address (returns 3-tuple: ip, port, gateway_project_id)
    address = await get_container_internal_address(project_id)

    if not address:
        raise HTTPException(
            status_code=404,
            detail=f"Preview not available. Container for project {project_id} not found or not running."
        )

    gateway_ip, gateway_port, gateway_project_id = address

    # Build target URL
    # gateway_project_id is actually host_port for nginx /sandbox/{port}/ routing
    if gateway_project_id and IS_REMOTE_DOCKER:
        # Route via nginx gateway: /sandbox/{host_port}/{path}
        # nginx proxies /sandbox/{port}/* to localhost:{port}/*
        # Container receives request at root path (no prefix needed)
        host_port = gateway_project_id
        target_url = f"http://{gateway_ip}:{gateway_port}/sandbox/{host_port}/{path}"
    elif gateway_project_id:
        # Legacy Traefik mode (not used)
        target_url = f"http://{gateway_ip}:{gateway_port}/api/v1/preview/{gateway_project_id}/{path}"
    else:
        # Local mode: direct to container IP
        target_url = f"http://{gateway_ip}:{gateway_port}/{path}"

    # Add query string if present
    if request.url.query:
        target_url += f"?{request.url.query}"

    logger.info(f"[Preview] Proxying {request.method} /preview/{project_id}/{path} -> {target_url}")

    try:
        client = get_http_client()

        # Prepare headers (forward most, rewrite Host)
        headers = {}
        for key, value in request.headers.items():
            # Skip hop-by-hop headers
            if key.lower() not in ('host', 'connection', 'keep-alive', 'transfer-encoding',
                                   'te', 'trailers', 'upgrade'):
                headers[key] = value

        # Set correct Host header for gateway/container
        headers['Host'] = f"{gateway_ip}:{gateway_port}"
        headers['X-Forwarded-For'] = request.client.host if request.client else '127.0.0.1'
        headers['X-Forwarded-Proto'] = request.url.scheme
        headers['X-Real-IP'] = request.client.host if request.client else '127.0.0.1'

        # Get request body
        body = await request.body()

        # Make proxied request
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body if body else None,
        )

        # Build response headers
        response_headers = {}
        for key, value in response.headers.items():
            # Skip hop-by-hop headers
            if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding',
                                   'connection', 'keep-alive'):
                response_headers[key] = value

        # Handle CORS for dev
        response_headers['Access-Control-Allow-Origin'] = '*'
        response_headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        response_headers['Access-Control-Allow-Headers'] = '*'

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get('content-type')
        )

    except httpx.ConnectError as e:
        logger.warning(f"[Preview] Connection failed to {target_url}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Preview service starting... Gateway/Container at {gateway_ip}:{gateway_port} not ready yet."
        )
    except httpx.TimeoutException as e:
        logger.warning(f"[Preview] Timeout proxying to {target_url}: {e}")
        raise HTTPException(
            status_code=504,
            detail="Preview request timed out. The dev server might be starting up."
        )
    except Exception as e:
        logger.error(f"[Preview] Proxy error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Preview proxy error: {str(e)}"
        )


@router.get("/{project_id}")
async def preview_root(project_id: str, request: Request):
    """Redirect root preview URL to include trailing slash"""
    return await proxy_preview(project_id, "", request)


@router.websocket("/{project_id}/{path:path}")
async def websocket_proxy(project_id: str, path: str):
    """
    WebSocket proxy for HMR (Hot Module Replacement).

    Vite, Next.js, etc. use WebSockets for live reload.
    This proxies WS connections to the container.
    """
    # TODO: Implement WebSocket proxying for HMR
    # For now, HMR will work via the direct port mapping fallback
    pass


# Helper endpoint to get preview info
@router.get("/{project_id}/_status")
async def get_preview_status(project_id: str):
    """
    Get preview status and internal routing info.

    Useful for debugging and frontend status display.
    """
    address = await get_container_internal_address(project_id)

    if not address:
        return {
            "project_id": project_id,
            "available": False,
            "error": "Container not found or not running"
        }

    gateway_ip, gateway_port, gateway_project_id = address

    manager = get_container_manager()
    container_info = manager.containers.get(project_id)

    # Determine routing method and target
    if gateway_project_id:
        routing_method = "traefik_gateway"
        target = f"http://{gateway_ip}:{gateway_port}/{gateway_project_id}/{{path}}"
    else:
        routing_method = "direct_container"
        target = f"http://{gateway_ip}:{gateway_port}/{{path}}"

    return {
        "project_id": project_id,
        "available": True,
        "preview_url": f"/preview/{project_id}/",
        "gateway_address": f"{gateway_ip}:{gateway_port}",
        "uses_gateway": gateway_project_id is not None,
        "detected_port": container_info.active_port if container_info else None,
        "container_status": container_info.status.value if container_info else "unknown",
        "routing": {
            "method": routing_method,
            "path_pattern": f"/preview/{project_id}/{{path}}",
            "target": target
        }
    }
