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
import websockets
import re
import os
import docker
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.modules.execution import get_container_manager
from app.services.container_executor import container_executor
from app.core.logging_config import logger

router = APIRouter(prefix="/preview", tags=["Preview Proxy"])


# =============================================================================
# RESPONSE REWRITING - Fix absolute paths in HTML/JS for path-based proxying
# =============================================================================

def get_error_capture_script(project_id: str) -> str:
    """
    Generate the browser error capture script to inject into HTML responses.

    This script captures:
    - window.onerror (JS runtime errors)
    - window.onunhandledrejection (Promise rejections)
    - console.error (logged errors)
    - Resource load failures (img, script, css 404s)
    - Network errors (fetch failures)
    - React error boundaries (if React is detected)

    All errors are batched and sent to /api/v1/errors/browser for auto-fixing.
    """
    return f'''<script data-bb-error-capture="true">
(function() {{
  // Prevent double-injection
  if (window.__bbErrorCaptureLoaded) return;
  window.__bbErrorCaptureLoaded = true;

  var projectId = "{project_id}";
  var errorQueue = [];
  var flushTimer = null;
  var FLUSH_INTERVAL = 2000; // Send errors every 2 seconds
  var MAX_QUEUE_SIZE = 20;
  var ENDPOINT = "/api/v1/errors/browser";

  // Categorize error by message
  function categorizeError(message, type) {{
    var msg = (message || "").toLowerCase();

    if (type === "NETWORK_ERROR") return "NETWORK_ERROR";
    if (type === "RESOURCE_ERROR") return "RESOURCE_ERROR";

    if (msg.includes("is not defined") || msg.includes("is not a function")) return "REFERENCE_ERROR";
    if (msg.includes("cannot read") || msg.includes("null") || msg.includes("undefined")) return "TYPE_ERROR";
    if (msg.includes("unexpected token") || msg.includes("syntax")) return "SYNTAX_ERROR";
    if (msg.includes("cors") || msg.includes("cross-origin")) return "CORS_ERROR";
    if (msg.includes("chunk") || msg.includes("loading")) return "CHUNK_LOAD_ERROR";
    if (msg.includes("hook") || msg.includes("rendered more hooks")) return "HOOK_ERROR";
    if (msg.includes("hydrat")) return "HYDRATION_ERROR";
    if (msg.includes("module") || msg.includes("import")) return "MODULE_ERROR";

    return "RUNTIME_ERROR";
  }}

  // Add error to queue
  function queueError(error) {{
    // Skip error-capture script errors
    if (error.file && error.file.includes("error-capture")) return;
    if (error.message && error.message.includes("error-capture")) return;

    // Skip WebSocket errors (expected in preview mode)
    if (error.message && (error.message.includes("WebSocket") || error.message.includes("ws://"))) return;

    // Skip duplicate errors
    var isDupe = errorQueue.some(function(e) {{
      return e.message === error.message && e.file === error.file && e.line === error.line;
    }});
    if (isDupe) return;

    error.timestamp = Date.now();
    errorQueue.push(error);

    // Flush immediately if queue is full
    if (errorQueue.length >= MAX_QUEUE_SIZE) {{
      flushErrors();
    }} else if (!flushTimer) {{
      flushTimer = setTimeout(flushErrors, FLUSH_INTERVAL);
    }}
  }}

  // Send errors to backend
  function flushErrors() {{
    if (flushTimer) {{
      clearTimeout(flushTimer);
      flushTimer = null;
    }}

    if (errorQueue.length === 0) return;

    var errorsToSend = errorQueue.splice(0, MAX_QUEUE_SIZE);

    var payload = {{
      project_id: projectId,
      source: "browser",
      errors: errorsToSend,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent
    }};

    // Use fetch with keepalive for reliability
    // sendBeacon doesn't support Content-Type header, causing 403
    var jsonBody = JSON.stringify(payload);
    fetch(ENDPOINT, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: jsonBody,
      keepalive: true,
      mode: "same-origin",
      credentials: "same-origin"
    }}).catch(function(err) {{
      // Fallback to sendBeacon with Blob for page unload scenarios
      if (navigator.sendBeacon) {{
        var blob = new Blob([jsonBody], {{ type: "application/json" }});
        navigator.sendBeacon(ENDPOINT, blob);
      }}
    }});

    // Log to console for debugging
    console.log("[BharatBuild] Captured " + errorsToSend.length + " errors, sending to auto-fixer");
  }}

  // 1. window.onerror - JS runtime errors
  var originalOnError = window.onerror;
  window.onerror = function(message, source, lineno, colno, error) {{
    queueError({{
      type: "JS_RUNTIME",
      category: categorizeError(message, "JS_RUNTIME"),
      message: String(message),
      file: source,
      line: lineno,
      column: colno,
      stack: error ? error.stack : null,
      framework: detectFramework()
    }});

    if (originalOnError) {{
      return originalOnError.apply(window, arguments);
    }}
    return false;
  }};

  // 2. Unhandled promise rejections
  window.addEventListener("unhandledrejection", function(event) {{
    var message = event.reason ? (event.reason.message || String(event.reason)) : "Unhandled Promise Rejection";
    var stack = event.reason ? event.reason.stack : null;

    queueError({{
      type: "PROMISE_REJECTION",
      category: categorizeError(message, "PROMISE_REJECTION"),
      message: message,
      stack: stack,
      framework: detectFramework()
    }});
  }});

  // 3. Console.error capture
  var originalConsoleError = console.error;
  console.error = function() {{
    var args = Array.prototype.slice.call(arguments);
    var message = args.map(function(a) {{
      if (a instanceof Error) return a.message;
      if (typeof a === "object") try {{ return JSON.stringify(a); }} catch(e) {{ return String(a); }}
      return String(a);
    }}).join(" ");

    // Skip certain noise
    if (!message.includes("Warning:") && !message.includes("[HMR]") && !message.includes("WebSocket")) {{
      queueError({{
        type: "CONSOLE_ERROR",
        category: categorizeError(message, "CONSOLE_ERROR"),
        message: message.substring(0, 1000),
        framework: detectFramework()
      }});
    }}

    return originalConsoleError.apply(console, arguments);
  }};

  // 4. Resource load errors (img, script, css 404s)
  window.addEventListener("error", function(event) {{
    var target = event.target;
    if (target && target !== window && (target.tagName === "SCRIPT" || target.tagName === "LINK" || target.tagName === "IMG")) {{
      var resource = target.src || target.href || "";

      // Skip WebSocket and HMR resources
      if (resource.includes("/@vite") || resource.includes("ws://")) return;

      queueError({{
        type: "RESOURCE_ERROR",
        category: "RESOURCE_ERROR",
        message: "Failed to load " + target.tagName.toLowerCase() + ": " + resource,
        file: resource,
        tagName: target.tagName,
        resource: resource
      }});
    }}
  }}, true);

  // 5. Fetch/XHR network errors
  var originalFetch = window.fetch;
  window.fetch = function(url, options) {{
    return originalFetch.apply(window, arguments).then(function(response) {{
      if (!response.ok && response.status >= 400) {{
        // Skip certain endpoints
        var urlStr = typeof url === "string" ? url : url.url;
        if (!urlStr.includes("/api/v1/errors") && !urlStr.includes("/@vite")) {{
          queueError({{
            type: "NETWORK_ERROR",
            category: "NETWORK_ERROR",
            message: "HTTP " + response.status + ": " + urlStr,
            url: urlStr,
            method: (options && options.method) || "GET",
            status: response.status,
            statusText: response.statusText
          }});
        }}
      }}
      return response;
    }}).catch(function(error) {{
      var urlStr = typeof url === "string" ? url : (url && url.url) || "";
      if (!urlStr.includes("/api/v1/errors") && !urlStr.includes("/@vite")) {{
        queueError({{
          type: "NETWORK_ERROR",
          category: categorizeError(error.message, "NETWORK_ERROR"),
          message: error.message || "Network request failed",
          url: urlStr,
          method: (options && options.method) || "GET"
        }});
      }}
      throw error;
    }});
  }};

  // Detect framework
  function detectFramework() {{
    if (window.React || document.querySelector("[data-reactroot]")) return "react";
    if (window.Vue || document.querySelector("[data-v-]")) return "vue";
    if (window.angular || document.querySelector("[ng-version]")) return "angular";
    if (window.Svelte) return "svelte";
    return "unknown";
  }}

  // Flush on page unload
  window.addEventListener("beforeunload", flushErrors);
  window.addEventListener("pagehide", flushErrors);

  console.log("[BharatBuild] Error capture active for project: " + projectId);
}})();
</script>'''


def rewrite_absolute_paths(content: bytes, project_id: str, content_type: str) -> bytes:
    """
    Rewrite absolute paths in HTML/JS responses to include the preview prefix.

    Vite dev server generates absolute paths like:
    - /@vite/client
    - /src/main.tsx
    - /node_modules/.vite/deps/react.js

    These need to be rewritten to:
    - /api/v1/preview/{project_id}/@vite/client
    - /api/v1/preview/{project_id}/src/main.tsx
    - etc.
    """
    if not content:
        return content

    # Only rewrite HTML and JavaScript content
    is_html = 'text/html' in content_type
    is_js = 'javascript' in content_type or 'application/json' in content_type

    if not (is_html or is_js):
        return content

    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        return content  # Binary content, don't modify

    prefix = f"/api/v1/preview/{project_id}"

    # Patterns to rewrite (order matters - more specific first)
    rewrites = [
        # Vite HMR client
        ('src="/@vite/', f'src="{prefix}/@vite/'),
        ("src='/@vite/", f"src='{prefix}/@vite/"),
        ('"/@vite/', f'"{prefix}/@vite/'),
        ("'/@vite/", f"'{prefix}/@vite/"),

        # React refresh
        ('src="/@react-refresh', f'src="{prefix}/@react-refresh'),
        ("src='/@react-refresh", f"src='{prefix}/@react-refresh"),
        ('"/@react-refresh', f'"{prefix}/@react-refresh'),
        ("'/@react-refresh", f"'{prefix}/@react-refresh"),

        # Node modules (Vite deps)
        ('"/node_modules/', f'"{prefix}/node_modules/'),
        ("'/node_modules/", f"'{prefix}/node_modules/"),
        ('from "/node_modules/', f'from "{prefix}/node_modules/'),
        ("from '/node_modules/", f"from '{prefix}/node_modules/"),

        # Source files
        ('src="/src/', f'src="{prefix}/src/'),
        ("src='/src/", f"src='{prefix}/src/"),
        ('href="/src/', f'href="{prefix}/src/'),
        ("href='/src/", f"href='{prefix}/src/"),
        ('from "/src/', f'from "{prefix}/src/'),
        ("from '/src/", f"from '{prefix}/src/"),
        ('"/src/', f'"{prefix}/src/'),
        ("'/src/", f"'{prefix}/src/"),

        # Generic absolute paths in imports (be careful not to match URLs)
        # Only match paths that start with / but not //
    ]

    for old, new in rewrites:
        text = text.replace(old, new)

    # Special handling for HTML script/link tags with absolute paths
    if is_html:
        import re
        # Match src="/" or href="/" but not src="//" (URLs)
        text = re.sub(
            r'(src|href)="(/(?!/)[^"]*)"',
            lambda m: f'{m.group(1)}="{prefix}{m.group(2)}"' if not m.group(2).startswith(prefix) else m.group(0),
            text
        )
        text = re.sub(
            r"(src|href)='(/(?!/)[^']*)'",
            lambda m: f"{m.group(1)}='{prefix}{m.group(2)}'" if not m.group(2).startswith(prefix) else m.group(0),
            text
        )

        # BROWSER ERROR CAPTURE: Inject error capture script into HTML responses
        # This captures JS errors, 404s, network errors and sends them to the auto-fixer
        # Only inject if not already present (check for data-bb-error-capture attribute)
        if 'data-bb-error-capture' not in text:
            error_script = get_error_capture_script(project_id)
            # Inject at the end of <head> or beginning of <body>
            if '</head>' in text:
                text = text.replace('</head>', f'{error_script}</head>')
            elif '<body' in text:
                # Find the end of the body tag
                body_match = re.search(r'<body[^>]*>', text)
                if body_match:
                    insert_pos = body_match.end()
                    text = text[:insert_pos] + error_script + text[insert_pos:]
            else:
                # No head or body, prepend to content
                text = error_script + text

            logger.debug(f"[Preview] Injected error capture script for {project_id}")

    return text.encode('utf-8')

# Check if using remote Docker (EC2 sandbox)
SANDBOX_DOCKER_HOST = os.environ.get("SANDBOX_DOCKER_HOST", "")
IS_REMOTE_DOCKER = bool(SANDBOX_DOCKER_HOST)

# Preview Gateway port (Traefik on EC2)
PREVIEW_GATEWAY_PORT = int(os.environ.get("PREVIEW_GATEWAY_PORT", "8080"))

# Gap #16: TTL-based address cache with invalidation
from dataclasses import dataclass
from time import time as current_time

@dataclass
class CachedAddress:
    address: tuple  # (ip, port, host_port)
    cached_at: float
    ttl_seconds: float = 10.0  # HIGH #1: Reduced from 30s to 10s for faster cache invalidation

    def is_valid(self) -> bool:
        return (current_time() - self.cached_at) < self.ttl_seconds

_address_cache: dict[str, CachedAddress] = {}

def invalidate_preview_cache(project_id: str = None):
    """
    Invalidate preview address cache.
    Gap #16: Call this when container restarts or IP changes.

    Args:
        project_id: Specific project to invalidate, or None for all
    """
    global _address_cache
    if project_id:
        if project_id in _address_cache:
            del _address_cache[project_id]
            logger.info(f"[Preview] Cache invalidated for {project_id}")
    else:
        _address_cache.clear()
        logger.info("[Preview] Cache cleared for all projects")

def get_cached_address(project_id: str) -> Optional[tuple]:
    """Get cached address if valid."""
    if project_id in _address_cache:
        cached = _address_cache[project_id]
        if cached.is_valid():
            return cached.address
        else:
            # Expired, remove from cache
            del _address_cache[project_id]
    return None

def set_cached_address(project_id: str, address: tuple):
    """Cache container address."""
    _address_cache[project_id] = CachedAddress(
        address=address,
        cached_at=current_time()
    )

# HTTP client for proxying requests
_http_client: Optional[httpx.AsyncClient] = None

# Docker client for querying remote containers
_docker_client: Optional[docker.DockerClient] = None

# CRITICAL #3: Thread-safe lock for Docker client initialization
import threading
_docker_client_lock = threading.Lock()


def get_docker_client() -> Optional[docker.DockerClient]:
    """Get or create Docker client for querying remote containers.

    CRITICAL #3: Uses thread-safe singleton pattern to prevent race conditions
    when multiple concurrent requests try to create the Docker client.
    HIGH #7: Implements retry logic with exponential backoff.
    """
    global _docker_client

    # Fast path: client already initialized
    if _docker_client is not None:
        # HIGH #7: Verify client is still connected
        try:
            _docker_client.ping()
            return _docker_client
        except Exception:
            logger.warning("[Preview] Docker client ping failed, reconnecting...")
            _docker_client = None

    if not SANDBOX_DOCKER_HOST:
        logger.warning("[Preview] SANDBOX_DOCKER_HOST not set, cannot connect to remote Docker")
        return None

    # CRITICAL #3: Use lock to prevent race condition
    with _docker_client_lock:
        # Double-check after acquiring lock
        if _docker_client is not None:
            return _docker_client

        # HIGH #7: Retry logic with exponential backoff
        max_retries = 3
        base_delay = 0.5  # seconds

        for attempt in range(max_retries):
            try:
                logger.info(f"[Preview] Attempting Docker connection to {SANDBOX_DOCKER_HOST} (attempt {attempt + 1}/{max_retries})")
                # HIGH #5: Increased timeout from 5s to 30s for slow Docker hosts
                # Try TLS-enabled docker client helper first
                from app.services.docker_client_helper import get_docker_client as get_tls_client
                client = get_tls_client(timeout=30)
                if not client:
                    # Fallback to direct connection
                    client = docker.DockerClient(base_url=SANDBOX_DOCKER_HOST, timeout=30)
                client.ping()
                _docker_client = client
                logger.info(f"[Preview] Docker client connected successfully to {SANDBOX_DOCKER_HOST}")
                return _docker_client
            except Exception as e:
                logger.warning(f"[Preview] Docker connection attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 0.5s, 1s, 2s
                    import time
                    time.sleep(delay)

        logger.error(f"[Preview] Failed to connect to Docker at {SANDBOX_DOCKER_HOST} after {max_retries} attempts")
        return None


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

    Gap #16: Uses TTL-based caching to reduce Docker API calls
    """
    # Check cache first
    cached = get_cached_address(project_id)
    if cached:
        logger.debug(f"[Preview] Cache hit for {project_id}")
        return cached

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

            # Fallback: Search by container name pattern for docker-compose containers
            # Docker-compose creates containers like: bharatbuild_{project_id[:8]}_frontend_1
            if not containers:
                project_prefix = project_id[:8]
                logger.info(f"[Preview] No labeled container found, searching by name pattern: bharatbuild_{project_prefix}_*")
                all_containers = docker_client.containers.list(filters={"status": "running"})
                for c in all_containers:
                    if f"bharatbuild_{project_prefix}" in c.name:
                        # Prefer frontend container for preview
                        if "frontend" in c.name:
                            containers = [c]
                            logger.info(f"[Preview] Found docker-compose frontend container: {c.name}")
                            break
                        elif not containers:
                            containers = [c]
                            logger.info(f"[Preview] Found docker-compose container: {c.name}")

            if not containers:
                logger.warning(f"[Preview] No running container found for {project_id}")
                return None

            container = containers[0]
            logger.info(f"[Preview] Container found: {project_id} -> {container.name}")

            # Get host port from container's port bindings
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            host_port = None

            # Priority: frontend ports (3000, 5173) over backend ports (8080)
            # For fullstack projects, we want to show the frontend UI, not the API
            frontend_ports = ['3000/tcp', '5173/tcp', '5174/tcp', '3001/tcp']
            backend_ports = ['8080/tcp', '8000/tcp', '8081/tcp']

            # First, try to find a frontend port
            for port_key in frontend_ports:
                if port_key in ports and ports[port_key]:
                    host_port = int(ports[port_key][0].get('HostPort', 0))
                    if host_port:
                        logger.info(f"[Preview] Found frontend port mapping: {port_key} -> {host_port}")
                        break

            # If no frontend port, try any port except backend ports
            if not host_port:
                for container_port, bindings in ports.items():
                    if bindings and container_port not in backend_ports:
                        host_port = int(bindings[0].get('HostPort', 0))
                        if host_port:
                            logger.info(f"[Preview] Found port mapping: {container_port} -> {host_port}")
                            break

            # Last resort: any port
            if not host_port:
                for container_port, bindings in ports.items():
                    if bindings:
                        host_port = int(bindings[0].get('HostPort', 0))
                        if host_port:
                            logger.info(f"[Preview] Found fallback port mapping: {container_port} -> {host_port}")
                            break

            if not host_port:
                logger.error(f"[Preview] No host port mapping found for container {container.name}")
                return None

            # Return EC2 IP, nginx port (8080), and host_port for /sandbox/{port}/ routing
            logger.info(f"[Preview] Routing via nginx gateway: {ec2_ip}:8080/sandbox/{host_port}/")
            result = (ec2_ip, 8080, str(host_port))  # host_port as string for URL building
            set_cached_address(project_id, result)  # Gap #16: Cache the result
            return result

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

    # Fix double-src path issue: /src/src/App.tsx -> /src/App.tsx
    # This happens when AI generates imports like './src/App' when already in src/
    if "/src/src/" in path:
        original_path = path
        path = path.replace("/src/src/", "/src/")
        logger.info(f"[Preview] Fixed double-src path: {original_path} -> {path}")
    elif path.startswith("src/src/"):
        original_path = path
        path = path.replace("src/src/", "src/", 1)
        logger.info(f"[Preview] Fixed double-src path: {original_path} -> {path}")

    # Fix src/node_modules path issue: /src/node_modules/.vite/... -> /node_modules/.vite/...
    # This happens when Vite transforms imports with base path that incorrectly includes src/
    if "/src/node_modules/" in path:
        original_path = path
        path = path.replace("/src/node_modules/", "/node_modules/")
        logger.info(f"[Preview] Fixed src/node_modules path: {original_path} -> {path}")
    elif path.startswith("src/node_modules/"):
        original_path = path
        path = path.replace("src/node_modules/", "node_modules/", 1)
        logger.info(f"[Preview] Fixed src/node_modules path: {original_path} -> {path}")

    # Fix src/@vite path issue: /src/@vite/client -> /@vite/client
    # Vite internal paths should never have src/ prefix
    if "/src/@vite/" in path:
        original_path = path
        path = path.replace("/src/@vite/", "/@vite/")
        logger.info(f"[Preview] Fixed src/@vite path: {original_path} -> {path}")
    elif path.startswith("src/@vite/"):
        original_path = path
        path = path.replace("src/@vite/", "@vite/", 1)
        logger.info(f"[Preview] Fixed src/@vite path: {original_path} -> {path}")

    # Fix src/@react-refresh path issue: /src/@react-refresh -> /@react-refresh
    if "/src/@react-refresh" in path:
        original_path = path
        path = path.replace("/src/@react-refresh", "/@react-refresh")
        logger.info(f"[Preview] Fixed src/@react-refresh path: {original_path} -> {path}")
    elif path.startswith("src/@react-refresh"):
        original_path = path
        path = path.replace("src/@react-refresh", "@react-refresh", 1)
        logger.info(f"[Preview] Fixed src/@react-refresh path: {original_path} -> {path}")

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

        # Allow iframe embedding for preview (CRITICAL for bharatbuild.ai frontend)
        response_headers['Content-Security-Policy'] = 'frame-ancestors https://bharatbuild.ai https://*.bharatbuild.ai http://localhost:* http://127.0.0.1:*'
        # Remove X-Frame-Options if present (CSP frame-ancestors takes precedence)
        response_headers.pop('X-Frame-Options', None)
        response_headers.pop('x-frame-options', None)

        # Rewrite absolute paths in HTML/JS responses to include preview prefix
        content_type = response.headers.get('content-type', '')
        content = response.content
        if content_type and ('text/html' in content_type or 'javascript' in content_type):
            content = rewrite_absolute_paths(content, project_id, content_type)
            logger.debug(f"[Preview] Rewrote absolute paths in {content_type} response for {project_id}")

        return Response(
            content=content,
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
async def websocket_proxy(websocket: WebSocket, project_id: str, path: str):
    """
    WebSocket proxy for HMR (Hot Module Replacement).

    Vite, Next.js, etc. use WebSockets for live reload.
    This proxies WS connections to the container.

    Common WebSocket paths:
    - Vite: /@vite/client, /@hmr
    - Webpack: /sockjs-node, /ws
    - Next.js: /_next/webpack-hmr
    """
    logger.info(f"[Preview WS] Incoming WebSocket: /preview/{project_id}/{path}")

    # Get container address
    address = await get_container_internal_address(project_id)

    if not address:
        await websocket.close(code=1008, reason="Container not found")
        return

    gateway_ip, gateway_port, host_port = address

    # Build WebSocket target URL
    if host_port and IS_REMOTE_DOCKER:
        # Route via nginx gateway: ws://EC2:8080/sandbox/{host_port}/{path}
        target_ws_url = f"ws://{gateway_ip}:{gateway_port}/sandbox/{host_port}/{path}"
    else:
        # Local mode: direct to container
        target_ws_url = f"ws://{gateway_ip}:{gateway_port}/{path}"

    logger.info(f"[Preview WS] Proxying WebSocket to {target_ws_url}")

    # Accept the incoming WebSocket connection
    await websocket.accept()

    try:
        # Preview Gap #5: Add connect timeout to prevent hanging on dead endpoints
        try:
            async with asyncio.timeout(10):  # 10 second connect timeout
                target_ws = await websockets.connect(
                    target_ws_url,
                    ping_interval=20,
                    ping_timeout=5,
                    close_timeout=3
                )
        except asyncio.TimeoutError:
            logger.warning(f"[Preview WS] WebSocket connection timeout to {target_ws_url}")
            await websocket.close(code=1013, reason="WebSocket connection timeout")
            return

        async with target_ws:
            # Create tasks for bidirectional message forwarding
            async def forward_to_target():
                """Forward messages from client to target"""
                try:
                    while True:
                        # Receive from client
                        data = await websocket.receive()

                        if data.get("type") == "websocket.disconnect":
                            break

                        if "text" in data:
                            await target_ws.send(data["text"])
                        elif "bytes" in data:
                            await target_ws.send(data["bytes"])
                except WebSocketDisconnect:
                    logger.debug(f"[Preview WS] Client disconnected: {project_id}")
                except Exception as e:
                    logger.debug(f"[Preview WS] Forward to target error: {e}")

            async def forward_to_client():
                """Forward messages from target to client"""
                try:
                    async for message in target_ws:
                        if isinstance(message, str):
                            await websocket.send_text(message)
                        else:
                            await websocket.send_bytes(message)
                except websockets.exceptions.ConnectionClosed:
                    logger.debug(f"[Preview WS] Target disconnected: {project_id}")
                except Exception as e:
                    logger.debug(f"[Preview WS] Forward to client error: {e}")

            # Run both directions concurrently
            await asyncio.gather(
                forward_to_target(),
                forward_to_client(),
                return_exceptions=True
            )

    except websockets.exceptions.InvalidStatusCode as e:
        logger.warning(f"[Preview WS] Target WebSocket rejected connection: {e}")
        await websocket.close(code=1002, reason="Target rejected WebSocket")
    except websockets.exceptions.InvalidURI as e:
        logger.error(f"[Preview WS] Invalid WebSocket URI: {e}")
        await websocket.close(code=1008, reason="Invalid target URI")
    except ConnectionRefusedError:
        logger.warning(f"[Preview WS] Target WebSocket connection refused: {target_ws_url}")
        await websocket.close(code=1013, reason="Target not ready")
    except Exception as e:
        logger.error(f"[Preview WS] WebSocket proxy error: {type(e).__name__}: {e}")
        try:
            await websocket.close(code=1011, reason="Internal proxy error")
        except Exception:
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
