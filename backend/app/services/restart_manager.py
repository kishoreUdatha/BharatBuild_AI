"""
Restart Manager - Restarts project after auto-fix (Bolt.new style)

After patches are applied, this component:
1. Restarts Docker containers (if running)
2. Restarts preview server (Vite/Next)
3. Triggers frontend preview reload
4. Notifies connected clients

This is the final step in the auto-fix loop.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.logging_config import logger


class RestartManager:
    """
    Manages project restarts after auto-fix.

    Coordinates Docker restart, preview server restart, and client notification.
    """

    def __init__(self):
        # Track restart state per project
        self._restart_in_progress: Dict[str, bool] = {}
        self._last_restart: Dict[str, datetime] = {}

    async def restart_project(
        self,
        project_id: str,
        restart_docker: bool = True,
        restart_preview: bool = True,
        notify_clients: bool = True
    ) -> Dict[str, Any]:
        """
        Restart a project after auto-fix.

        Args:
            project_id: Project to restart
            restart_docker: Whether to restart Docker container
            restart_preview: Whether to restart preview server
            notify_clients: Whether to notify connected WebSocket clients

        Returns:
            Result dict with restart status
        """
        if self._restart_in_progress.get(project_id):
            logger.warning(f"[RestartManager:{project_id}] Restart already in progress")
            return {"success": False, "error": "Restart already in progress"}

        self._restart_in_progress[project_id] = True
        results = {
            "project_id": project_id,
            "docker_restarted": False,
            "preview_restarted": False,
            "clients_notified": False
        }

        try:
            # 1. Restart Docker container if needed
            if restart_docker:
                docker_result = await self._restart_docker(project_id)
                results["docker_restarted"] = docker_result.get("success", False)
                if docker_result.get("error"):
                    results["docker_error"] = docker_result["error"]

            # 2. Restart preview server
            if restart_preview:
                preview_result = await self._restart_preview_server(project_id)
                results["preview_restarted"] = preview_result.get("success", False)
                if preview_result.get("error"):
                    results["preview_error"] = preview_result["error"]

            # 3. Notify connected clients
            if notify_clients:
                notify_result = await self._notify_clients(project_id)
                results["clients_notified"] = notify_result.get("success", False)

            self._last_restart[project_id] = datetime.utcnow()
            results["success"] = True

            logger.info(f"[RestartManager:{project_id}] Restart completed: {results}")

        except Exception as e:
            logger.error(f"[RestartManager:{project_id}] Restart failed: {e}")
            results["success"] = False
            results["error"] = str(e)

        finally:
            self._restart_in_progress[project_id] = False

        return results

    async def _restart_docker(self, project_id: str) -> Dict[str, Any]:
        """Restart Docker container for project"""
        try:
            # Import here to avoid circular imports
            from app.modules.execution.container_manager import ContainerManager

            container_manager = ContainerManager()

            # Check if container is running
            status = await container_manager.get_container_status(project_id)

            if status.get("running"):
                # Stop and restart
                logger.info(f"[RestartManager:{project_id}] Restarting Docker container")

                await container_manager.stop_container(project_id)
                await asyncio.sleep(0.5)  # Brief pause
                await container_manager.start_container(project_id)

                return {"success": True}
            else:
                # Container not running, try to start fresh
                logger.info(f"[RestartManager:{project_id}] Starting Docker container")
                await container_manager.start_container(project_id)
                return {"success": True}

        except ImportError:
            logger.debug(f"[RestartManager:{project_id}] ContainerManager not available")
            return {"success": False, "error": "Container manager not available"}
        except Exception as e:
            logger.error(f"[RestartManager:{project_id}] Docker restart failed: {e}")
            return {"success": False, "error": str(e)}

    async def _restart_preview_server(self, project_id: str) -> Dict[str, Any]:
        """Restart preview server (Vite/Next) for project"""
        try:
            # Import here to avoid circular imports
            from app.modules.automation.preview_server import PreviewServerManager

            preview_manager = PreviewServerManager()

            # Check if server is running
            if preview_manager.is_running(project_id):
                logger.info(f"[RestartManager:{project_id}] Restarting preview server")

                await preview_manager.stop(project_id)
                await asyncio.sleep(0.5)  # Brief pause
                await preview_manager.start(project_id)

                return {"success": True}
            else:
                # Server not running, just return success (nothing to restart)
                return {"success": True, "message": "Preview server not running"}

        except ImportError:
            logger.debug(f"[RestartManager:{project_id}] PreviewServerManager not available")
            return {"success": False, "error": "Preview server manager not available"}
        except Exception as e:
            logger.error(f"[RestartManager:{project_id}] Preview restart failed: {e}")
            return {"success": False, "error": str(e)}

    async def _notify_clients(self, project_id: str) -> Dict[str, Any]:
        """Notify connected WebSocket clients to reload"""
        try:
            from app.api.v1.endpoints.log_stream import log_stream_manager

            # Broadcast restart notification
            await log_stream_manager.broadcast_to_project(project_id, {
                "type": "project_restarted",
                "timestamp": datetime.utcnow().timestamp() * 1000,
                "message": "Project restarted after fix"
            })

            return {"success": True}

        except ImportError:
            logger.debug(f"[RestartManager:{project_id}] LogStreamManager not available")
            return {"success": False, "error": "Log stream manager not available"}
        except Exception as e:
            logger.error(f"[RestartManager:{project_id}] Client notification failed: {e}")
            return {"success": False, "error": str(e)}

    def get_status(self, project_id: str) -> Dict[str, Any]:
        """Get restart status for a project"""
        return {
            "restart_in_progress": self._restart_in_progress.get(project_id, False),
            "last_restart": self._last_restart.get(project_id, None)
        }


# Global singleton
restart_manager = RestartManager()


async def restart_project(project_id: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to restart a project"""
    return await restart_manager.restart_project(project_id, **kwargs)
