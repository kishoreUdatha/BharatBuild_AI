"""
Preview Proxy API - Solves CORS for iframe previews

Problem:
    - Container runs on port 10001
    - Frontend iframe tries to load http://server:10001
    - CORS blocks it because different origin

Solution:
    - Proxy requests through backend: /api/v1/preview/{project_id}/*
    - Backend forwards to container port
    - No CORS issues because same origin

This is how Bolt.new handles previews.
"""

import asyncio
import httpx
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, HTMLResponse

from app.modules.execution import get_container_manager
from app.core.logging_config import logger

router = APIRouter(prefix="/preview", tags=["Preview Proxy"])


async def proxy_request(
    project_id: str,
    path: str,
    request: Request,
    port: int = 3000
) -> Response:
    """
    Proxy a request to the container's dev server.

    Args:
        project_id: Project identifier
        path: Path to request (e.g., "/", "/api/users")
        request: Original FastAPI request
        port: Container port to proxy to

    Returns:
        Proxied response
    """
    manager = get_container_manager()

    # Get container info
    if project_id not in manager.containers:
        raise HTTPException(status_code=404, detail="Project not found")

    container = manager.containers[project_id]
    host_port = container.port_mappings.get(port)

    if not host_port:
        raise HTTPException(status_code=404, detail=f"Port {port} not exposed")

    # Build target URL
    target_url = f"http://localhost:{host_port}/{path.lstrip('/')}"

    # Forward request
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Build headers (filter out hop-by-hop headers)
            headers = {}
            for key, value in request.headers.items():
                if key.lower() not in [
                    'host', 'connection', 'keep-alive',
                    'transfer-encoding', 'upgrade'
                ]:
                    headers[key] = value

            # Make request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body() if request.method in ['POST', 'PUT', 'PATCH'] else None,
                params=request.query_params,
                follow_redirects=True,
            )

            # Build response headers
            response_headers = {}
            for key, value in response.headers.items():
                if key.lower() not in [
                    'content-encoding', 'content-length',
                    'transfer-encoding', 'connection'
                ]:
                    response_headers[key] = value

            # Allow iframe embedding for preview (CRITICAL for bharatbuild.ai frontend)
            response_headers['Content-Security-Policy'] = 'frame-ancestors https://bharatbuild.ai https://*.bharatbuild.ai http://localhost:* http://127.0.0.1:*'
            # Remove X-Frame-Options if present (CSP frame-ancestors takes precedence)
            response_headers.pop('X-Frame-Options', None)
            response_headers.pop('x-frame-options', None)

            # Return proxied response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type')
            )

        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Dev server not running. Run 'npm run dev' first."
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Request timed out"
            )
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            raise HTTPException(status_code=502, detail=str(e))


@router.get("/{project_id}")
@router.get("/{project_id}/")
async def preview_root(project_id: str, request: Request):
    """
    Get preview root page.

    Usage:
        <iframe src="/api/v1/preview/abc123" />
    """
    return await proxy_request(project_id, "/", request)


@router.get("/{project_id}/{path:path}")
async def preview_path(project_id: str, path: str, request: Request):
    """
    Proxy any path to the container.

    Usage:
        /api/v1/preview/abc123/api/users → container:3000/api/users
        /api/v1/preview/abc123/static/app.js → container:3000/static/app.js
    """
    return await proxy_request(project_id, path, request)


@router.api_route(
    "/{project_id}/{path:path}",
    methods=["POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def preview_path_write(project_id: str, path: str, request: Request):
    """
    Proxy write requests (POST, PUT, etc.) to the container.

    Needed for:
        - API calls from preview app
        - Form submissions
        - WebSocket upgrades (partial support)
    """
    return await proxy_request(project_id, path, request)


# WebSocket proxy for hot reload
@router.websocket("/{project_id}/ws")
async def preview_websocket(project_id: str, websocket):
    """
    Proxy WebSocket connections for hot reload.

    Vite/Webpack use WebSocket for HMR (Hot Module Replacement).
    """
    import websockets

    manager = get_container_manager()

    if project_id not in manager.containers:
        await websocket.close(code=4004, reason="Project not found")
        return

    container = manager.containers[project_id]
    host_port = container.port_mappings.get(3000)

    if not host_port:
        await websocket.close(code=4004, reason="Port not exposed")
        return

    ws_url = f"ws://localhost:{host_port}/ws"

    try:
        await websocket.accept()

        async with websockets.connect(ws_url) as ws_container:
            async def forward_to_container():
                async for message in websocket.iter_text():
                    await ws_container.send(message)

            async def forward_to_client():
                async for message in ws_container:
                    await websocket.send_text(message)

            await asyncio.gather(
                forward_to_container(),
                forward_to_client()
            )

    except Exception as e:
        logger.error(f"WebSocket proxy error: {e}")
        await websocket.close(code=4000, reason=str(e))


# Special endpoints

@router.get("/{project_id}/_status")
async def preview_status(project_id: str):
    """
    Check if preview is available.

    Returns:
        {"ready": true, "url": "/api/v1/preview/abc123"}
    """
    manager = get_container_manager()

    if project_id not in manager.containers:
        return {"ready": False, "error": "Container not found"}

    container = manager.containers[project_id]
    host_port = container.port_mappings.get(3000)

    if not host_port:
        return {"ready": False, "error": "Port not exposed"}

    # Check if dev server is responding
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"http://localhost:{host_port}/")
            return {
                "ready": response.status_code < 500,
                "url": f"/api/v1/preview/{project_id}",
                "status_code": response.status_code
            }
        except Exception:
            return {"ready": False, "error": "Dev server not responding"}


@router.get("/{project_id}/_reload")
async def trigger_reload(project_id: str):
    """
    Trigger a browser reload for the preview.

    Returns HTML snippet that forces reload.
    Used by file watcher to refresh preview.
    """
    return HTMLResponse("""
    <script>
        window.parent.postMessage({type: 'reload'}, '*');
        window.location.reload();
    </script>
    """)
