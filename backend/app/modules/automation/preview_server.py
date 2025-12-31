"""
Preview Server Manager
Manages dev servers for different tech stacks

Integrates with LogBus to collect build/dev server logs.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field

from app.core.logging_config import logger

# Preview URL Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip('/')
SANDBOX_PREVIEW_BASE_URL = os.getenv("SANDBOX_PREVIEW_BASE_URL", "")
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL", "http://localhost")


def get_preview_url(port: int, project_id: str = None) -> str:
    """
    Generate preview URL.

    Works in both local and production:
    - Local: http://localhost:{port}
    - Production with project_id: https://bharatbuild.ai/api/v1/preview/{project_id}/
    - Production without project_id: Uses SANDBOX_PUBLIC_URL with port

    Args:
        port: The container port
        project_id: Optional project ID for API-based preview URL (production)

    Returns:
        Preview URL string
    """
    # Check if we're in production
    is_production = (
        ENVIRONMENT == "production" or
        (FRONTEND_URL and "localhost" not in FRONTEND_URL and "127.0.0.1" not in FRONTEND_URL)
    )

    # Production with project_id: Use domain-based API preview proxy
    if is_production and project_id:
        return f"{FRONTEND_URL}/api/v1/preview/{project_id}/"

    # Prefer path-based URL if SANDBOX_PREVIEW_BASE_URL is set
    if SANDBOX_PREVIEW_BASE_URL and SANDBOX_PREVIEW_BASE_URL != "http://localhost":
        base = SANDBOX_PREVIEW_BASE_URL.rstrip('/')
        return f"{base}/{port}"

    # Fall back to IP:port based URL
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        # Remove any existing port from the base URL
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        return f"{base}:{port}"

    return f"http://localhost:{port}"


@dataclass
class ServerProcess:
    """Running server process information"""
    project_id: str
    port: int
    process: asyncio.subprocess.Process
    url: str
    build_tool: str
    log_task: Optional[asyncio.Task] = None  # Background task collecting logs


class PreviewServerManager:
    """Manages preview/dev servers for projects"""

    def __init__(self, base_path: str = None):
        if base_path is None:
            from app.core.config import settings
            base_path = str(settings.USER_PROJECTS_DIR)
        self.base_path = Path(base_path)
        self.running_servers: Dict[str, ServerProcess] = {}
        self.default_ports = {
            "vite": 3000,
            "next": 3000,
            "create-react-app": 3000,
            "webpack": 8080,
            "python": 8000,
            "go": 8080,
            "spring": 8080
        }

    def get_project_path(self, project_id: str) -> Path:
        """Get the full path for a project"""
        return self.base_path / project_id

    async def start_server(
        self,
        project_id: str,
        port: Optional[int] = None,
        build_tool: Optional[str] = None
    ) -> Dict:
        """
        Start a development server

        Args:
            project_id: Project ID
            port: Port to run on (auto-detect if None)
            build_tool: Build tool (auto-detect if None)

        Returns:
            Dict with success, url, port
        """
        try:
            # Check if already running
            if project_id in self.running_servers:
                server = self.running_servers[project_id]
                return {
                    "success": True,
                    "message": "Server already running",
                    "url": server.url,
                    "port": server.port
                }

            project_path = self.get_project_path(project_id)

            if not project_path.exists():
                return {
                    "success": False,
                    "error": f"Project {project_id} not found"
                }

            # Auto-detect build tool
            if build_tool is None:
                from app.modules.automation.build_system import build_system
                detected = build_system.detect_build_tool(project_id)
                build_tool = detected.value if detected else "vite"

            # Get port
            if port is None:
                port = self.default_ports.get(build_tool, 3000)

            # Check if port is available
            if not await self._is_port_available(port):
                # Try next available port
                port = await self._find_available_port(port)

            # Get dev command
            command = self._get_dev_command(build_tool, port)

            logger.info(f"Starting dev server for {project_id} on port {port}: {command}")

            # Start the server process
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            url = get_preview_url(port)

            # Start background task to collect logs and send to LogBus
            log_task = asyncio.create_task(
                self._collect_server_logs(project_id, process, build_tool)
            )

            # Store server info
            self.running_servers[project_id] = ServerProcess(
                project_id=project_id,
                port=port,
                process=process,
                url=url,
                build_tool=build_tool,
                log_task=log_task
            )

            # Wait a bit for server to start
            await asyncio.sleep(2)

            return {
                "success": True,
                "url": url,
                "port": port,
                "build_tool": build_tool,
                "message": f"Server started on {url}"
            }

        except Exception as e:
            logger.error(f"Error starting server: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def stop_server(self, project_id: str) -> Dict:
        """Stop a running dev server"""
        try:
            if project_id not in self.running_servers:
                return {
                    "success": False,
                    "error": "Server not running"
                }

            server = self.running_servers[project_id]

            # Cancel log collection task
            if server.log_task and not server.log_task.done():
                server.log_task.cancel()
                try:
                    await server.log_task
                except asyncio.CancelledError:
                    pass

            # Terminate the process
            server.process.terminate()
            await server.process.wait()

            # Remove from running servers
            del self.running_servers[project_id]

            logger.info(f"Stopped server for {project_id}")

            return {
                "success": True,
                "message": f"Server stopped"
            }

        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_server_status(self, project_id: str) -> Dict:
        """Get status of a server"""
        if project_id in self.running_servers:
            server = self.running_servers[project_id]
            return {
                "running": True,
                "url": server.url,
                "port": server.port,
                "build_tool": server.build_tool
            }
        else:
            return {
                "running": False
            }

    async def restart_server(self, project_id: str) -> Dict:
        """
        Restart a running dev server (stop + start)
        Used after file fixes to reload the application

        Args:
            project_id: Project ID

        Returns:
            Dict with success, url, port, message
        """
        try:
            logger.info(f"Restarting server for project {project_id}")

            # Get current server info (if running)
            current_port = None
            current_build_tool = None

            if project_id in self.running_servers:
                server = self.running_servers[project_id]
                current_port = server.port
                current_build_tool = server.build_tool

                # Stop the server
                stop_result = await self.stop_server(project_id)
                if not stop_result.get("success"):
                    logger.warning(f"Failed to stop server cleanly: {stop_result.get('error')}")

                # Small delay to ensure port is released
                await asyncio.sleep(1)

            # Start the server (will auto-detect if no previous info)
            start_result = await self.start_server(
                project_id,
                port=current_port,
                build_tool=current_build_tool
            )

            if start_result.get("success"):
                logger.info(f"Server restarted successfully on {start_result.get('url')}")
                return {
                    "success": True,
                    "url": start_result.get("url"),
                    "port": start_result.get("port"),
                    "build_tool": start_result.get("build_tool"),
                    "message": "Server restarted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": start_result.get("error", "Failed to restart server")
                }

        except Exception as e:
            logger.error(f"Error restarting server for {project_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def hot_reload_trigger(self, project_id: str) -> Dict:
        """
        Trigger a hot reload for the project (if server supports it)
        For Vite/webpack/Next.js, file changes trigger HMR automatically
        This method can be used to force a full page reload

        Args:
            project_id: Project ID

        Returns:
            Dict with success, message
        """
        try:
            if project_id not in self.running_servers:
                return {
                    "success": False,
                    "error": "Server not running"
                }

            server = self.running_servers[project_id]

            # For most modern dev servers (Vite, Next.js, webpack-dev-server),
            # file changes are detected automatically via file watchers
            # This method is for cases where we need to signal a reload

            logger.info(f"Hot reload triggered for {project_id} ({server.build_tool})")

            return {
                "success": True,
                "message": "Hot reload triggered",
                "url": server.url,
                "build_tool": server.build_tool
            }

        except Exception as e:
            logger.error(f"Error triggering hot reload: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_dev_command(self, build_tool: str, port: int) -> str:
        """Get the dev server command"""
        commands = {
            "vite": f"npm run dev -- --port {port}",
            "next": f"npm run dev -- -p {port}",
            "create-react-app": "npm start",
            "webpack": f"npm run dev -- --port {port}",
            "python": f"uvicorn main:app --reload --port {port}",
            "go": "go run .",
            "spring": "mvn spring-boot:run"
        }
        return commands.get(build_tool, "npm run dev")

    async def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result != 0
        except (socket.error, OSError) as e:
            logger.debug(f"Could not check port {port}: {e}")
            return False

    async def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + 100):
            if await self._is_port_available(port):
                return port
        return start_port

    async def _collect_server_logs(
        self,
        project_id: str,
        process: asyncio.subprocess.Process,
        build_tool: str
    ) -> None:
        """
        Background task that collects stdout/stderr from dev server
        and sends logs to LogBus.

        Parses build errors from Vite/Webpack/Next.js output.
        """
        try:
            from app.services.log_bus import get_log_bus
            log_bus = get_log_bus(project_id)

            # Error patterns for different build tools
            error_patterns = {
                "vite": [
                    (r'error:\s+(.+)', "error"),
                    (r'\[vite\]\s+(.+error.+)', "error"),
                    (r'Failed to resolve import', "error"),
                    (r'Pre-transform error', "error"),
                    (r'Internal server error', "error"),
                ],
                "next": [
                    (r'Error:\s+(.+)', "error"),
                    (r'Module not found', "error"),
                    (r'Failed to compile', "error"),
                    (r'Unhandled Runtime Error', "error"),
                ],
                "webpack": [
                    (r'ERROR in (.+)', "error"),
                    (r'Module build failed', "error"),
                    (r'Module not found', "error"),
                ],
                "default": [
                    (r'error', "error"),
                    (r'Error:', "error"),
                    (r'ERROR', "error"),
                    (r'failed', "error"),
                    (r'FAILED', "error"),
                ]
            }

            patterns = error_patterns.get(build_tool, error_patterns["default"])

            # File extraction pattern
            file_pattern = re.compile(r'([^\s:]+\.[jt]sx?)(?::(\d+))?(?::(\d+))?')

            while True:
                if process.stdout is None:
                    break

                line = await process.stdout.readline()
                if not line:
                    break

                text = line.decode('utf-8', errors='ignore').strip()
                if not text:
                    continue

                # Determine log level
                level = "info"
                for pattern, lvl in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        level = lvl
                        break

                # Extract file reference if present
                file_match = file_pattern.search(text)
                file_path = None
                line_num = None

                if file_match:
                    file_path = file_match.group(1)
                    if file_match.group(2):
                        line_num = int(file_match.group(2))

                # Send to LogBus
                if level == "error":
                    log_bus.add_build_error(
                        message=text,
                        file=file_path,
                        line=line_num
                    )
                else:
                    log_bus.add_build_log(text, level=level)

                # Also log to application logger
                if level == "error":
                    logger.warning(f"[{project_id}:{build_tool}] {text[:200]}")

        except asyncio.CancelledError:
            logger.debug(f"Log collection cancelled for {project_id}")
        except Exception as e:
            logger.error(f"Error collecting logs for {project_id}: {e}")

    def _parse_build_error(self, text: str, build_tool: str) -> Optional[Dict]:
        """
        Parse build error to extract file, line, message.
        Returns None if not an error or cannot parse.
        """
        # Vite error format: "src/App.jsx:10:5 error: ..."
        # Webpack format: "ERROR in ./src/App.jsx 10:5"
        # Next.js format: "Error: ... at src/App.jsx:10:5"

        patterns = [
            # Vite/ESBuild: "src/App.jsx:10:5"
            r'^([^\s:]+\.[jt]sx?):(\d+):(\d+)\s+(.+)',
            # Webpack: "./src/App.jsx 10:5"
            r'\.?/?([^\s]+\.[jt]sx?)\s+(\d+):(\d+)',
            # Next.js/Generic: "at file.jsx:10:5"
            r'at\s+([^\s:]+\.[jt]sx?):(\d+):(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return {
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)) if match.lastindex >= 3 else None,
                    "message": text
                }

        return None


# Singleton instance
preview_server_manager = PreviewServerManager()
