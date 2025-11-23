"""
Preview Server Manager
Manages dev servers for different tech stacks
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

from app.core.logging_config import logger


@dataclass
class ServerProcess:
    """Running server process information"""
    project_id: str
    port: int
    process: asyncio.subprocess.Process
    url: str
    build_tool: str


class PreviewServerManager:
    """Manages preview/dev servers for projects"""

    def __init__(self, base_path: str = "./user_projects"):
        self.base_path = Path(base_path)
        self.running_servers: Dict[str, ServerProcess] = {}
        self.default_ports = {
            "vite": 5173,
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
                port = self.default_ports.get(build_tool, 5173)

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

            url = f"http://localhost:{port}"

            # Store server info
            self.running_servers[project_id] = ServerProcess(
                project_id=project_id,
                port=port,
                process=process,
                url=url,
                build_tool=build_tool
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
        except:
            return False

    async def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + 100):
            if await self._is_port_available(port):
                return port
        return start_port


# Singleton instance
preview_server_manager = PreviewServerManager()
