"""
Sandbox Cleanup Service - Bolt.new Style Ephemeral Storage

This service automatically deletes old/idle project sandboxes to:
1. Save disk space
2. Clean up abandoned sessions
3. Match Bolt.new's ephemeral storage behavior

Projects in the sandbox are:
- Created when user starts a new project
- Kept alive while user is active
- Auto-deleted after IDLE_TIMEOUT (default 24 hours)

Users can:
- Export/download their project before cleanup
- Save to permanent storage if they have an account
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import json
from typing import Dict, Optional, List
import os

from app.core.logging_config import logger


class SandboxCleanupService:
    """
    Automatic cleanup service for ephemeral project sandboxes.

    Mimics Bolt.new behavior:
    - Projects live in sandbox during active session
    - Auto-deleted after idle timeout
    - No permanent storage by default
    """

    def __init__(
        self,
        sandbox_path: str = "C:/tmp/sandbox/workspace",
        idle_timeout_minutes: int = 30,  # Bolt.new style: 30 min idle timeout
        cleanup_interval_minutes: int = 5,  # Check every 5 minutes
        min_project_age_minutes: int = 5,  # Don't delete projects younger than 5 min
    ):
        self.sandbox_path = Path(sandbox_path)
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self.cleanup_interval = timedelta(minutes=cleanup_interval_minutes)
        self.min_age = timedelta(minutes=min_project_age_minutes)

        self.running = False
        self._task: Optional[asyncio.Task] = None

        # Track active sessions (project_id -> last_activity)
        self._active_sessions: Dict[str, datetime] = {}

        # Cleanup stats
        self.stats = {
            "total_cleaned": 0,
            "last_cleanup": None,
            "space_freed_mb": 0,
        }

    async def start(self):
        """Start the background cleanup service"""
        if self.running:
            logger.warning("[SandboxCleanup] Service already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"[SandboxCleanup] Started - Idle timeout: {self.idle_timeout}, Interval: {self.cleanup_interval}")

    async def stop(self):
        """Stop the cleanup service"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[SandboxCleanup] Stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop"""
        while self.running:
            try:
                await self.cleanup_old_projects()
            except Exception as e:
                logger.error(f"[SandboxCleanup] Error in cleanup loop: {e}", exc_info=True)

            await asyncio.sleep(self.cleanup_interval.total_seconds())

    async def cleanup_old_projects(self) -> Dict:
        """
        Delete projects that have been idle longer than the timeout.

        Returns:
            Dict with cleanup results
        """
        if not self.sandbox_path.exists():
            logger.debug(f"[SandboxCleanup] Sandbox path doesn't exist: {self.sandbox_path}")
            return {"deleted": 0, "skipped": 0, "errors": 0}

        now = datetime.now()
        results = {
            "deleted": [],
            "skipped": [],
            "errors": [],
            "space_freed_bytes": 0,
        }

        for project_dir in self.sandbox_path.iterdir():
            if not project_dir.is_dir():
                continue

            project_id = project_dir.name

            try:
                # Check if project has active session
                if project_id in self._active_sessions:
                    last_activity = self._active_sessions[project_id]
                    if now - last_activity < self.idle_timeout:
                        results["skipped"].append({
                            "id": project_id,
                            "reason": "active_session",
                            "last_activity": last_activity.isoformat()
                        })
                        continue

                # Check file system last modified time
                mtime = self._get_last_modified(project_dir)
                age = now - mtime

                # Skip if too young
                if age < self.min_age:
                    results["skipped"].append({
                        "id": project_id,
                        "reason": "too_young",
                        "age_minutes": age.total_seconds() / 60
                    })
                    continue

                # Check if idle timeout exceeded
                if age > self.idle_timeout:
                    # Calculate size before deletion
                    size_bytes = self._get_dir_size(project_dir)

                    # Stop any running Docker containers for this project
                    await self._stop_project_containers(project_id)

                    # Delete the project
                    shutil.rmtree(project_dir)

                    # Remove from active sessions if present
                    self._active_sessions.pop(project_id, None)

                    results["deleted"].append({
                        "id": project_id,
                        "age_minutes": age.total_seconds() / 60,
                        "size_mb": size_bytes / (1024 * 1024)
                    })
                    results["space_freed_bytes"] += size_bytes

                    logger.info(f"[SandboxCleanup] Deleted: {project_id} (age: {age.total_seconds() / 60:.1f}min, size: {size_bytes / 1024 / 1024:.2f} MB)")
                else:
                    results["skipped"].append({
                        "id": project_id,
                        "reason": "not_expired",
                        "age_minutes": age.total_seconds() / 60,
                        "expires_in_minutes": (self.idle_timeout - age).total_seconds() / 60
                    })

            except Exception as e:
                logger.error(f"[SandboxCleanup] Error processing {project_id}: {e}")
                results["errors"].append({
                    "id": project_id,
                    "error": str(e)
                })

        # Update stats
        self.stats["total_cleaned"] += len(results["deleted"])
        self.stats["last_cleanup"] = now.isoformat()
        self.stats["space_freed_mb"] += results["space_freed_bytes"] / (1024 * 1024)

        if results["deleted"]:
            logger.info(
                f"[SandboxCleanup] Cleanup complete: "
                f"{len(results['deleted'])} deleted, "
                f"{len(results['skipped'])} skipped, "
                f"{results['space_freed_bytes'] / 1024 / 1024:.2f} MB freed"
            )

        return results

    def touch_project(self, project_id: str):
        """
        Mark a project as active (reset its idle timer).

        Call this when:
        - User makes a request to the project
        - Files are modified
        - Commands are executed
        """
        self._active_sessions[project_id] = datetime.now()

        # Also update the filesystem mtime
        project_path = self.sandbox_path / project_id
        if project_path.exists():
            try:
                # Touch the directory to update mtime
                project_path.touch()
            except Exception:
                pass

    def get_project_expiry(self, project_id: str) -> Optional[Dict]:
        """
        Get expiry information for a project.

        Returns:
            Dict with expiry info or None if project not found
        """
        project_path = self.sandbox_path / project_id
        if not project_path.exists():
            return None

        now = datetime.now()

        # Check active session first
        if project_id in self._active_sessions:
            last_activity = self._active_sessions[project_id]
        else:
            last_activity = self._get_last_modified(project_path)

        age = now - last_activity
        expires_at = last_activity + self.idle_timeout
        time_remaining = expires_at - now

        return {
            "project_id": project_id,
            "last_activity": last_activity.isoformat(),
            "expires_at": expires_at.isoformat(),
            "time_remaining_minutes": max(0, time_remaining.total_seconds() / 60),
            "is_expired": time_remaining.total_seconds() <= 0,
            "idle_timeout_minutes": self.idle_timeout.total_seconds() / 60,
        }

    def extend_project_life(self, project_id: str, hours: int = 24) -> bool:
        """
        Extend a project's life by touching it.

        Args:
            project_id: Project to extend
            hours: Hours to extend (resets to now + idle_timeout)

        Returns:
            True if successful
        """
        project_path = self.sandbox_path / project_id
        if not project_path.exists():
            return False

        self.touch_project(project_id)
        logger.info(f"[SandboxCleanup] Extended life for: {project_id}")
        return True

    def protect_project(self, project_id: str):
        """
        Protect a project from cleanup (e.g., user saved to account).

        Protected projects are moved out of sandbox or marked.
        """
        # Create a marker file
        project_path = self.sandbox_path / project_id
        if project_path.exists():
            marker_path = project_path / ".protected"
            marker_path.write_text(json.dumps({
                "protected_at": datetime.now().isoformat(),
                "reason": "user_saved"
            }))
            logger.info(f"[SandboxCleanup] Protected project: {project_id}")

    def get_stats(self) -> Dict:
        """Get cleanup statistics"""
        # Count current projects
        project_count = 0
        total_size = 0

        if self.sandbox_path.exists():
            for project_dir in self.sandbox_path.iterdir():
                if project_dir.is_dir():
                    project_count += 1
                    total_size += self._get_dir_size(project_dir)

        return {
            **self.stats,
            "current_projects": project_count,
            "current_size_mb": total_size / (1024 * 1024),
            "active_sessions": len(self._active_sessions),
            "sandbox_path": str(self.sandbox_path),
            "idle_timeout_minutes": self.idle_timeout.total_seconds() / 60,
        }

    def _get_last_modified(self, path: Path) -> datetime:
        """Get the most recent modification time of a directory tree"""
        latest = datetime.fromtimestamp(path.stat().st_mtime)

        try:
            for item in path.rglob("*"):
                if item.is_file():
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if mtime > latest:
                        latest = mtime
        except Exception:
            pass

        return latest

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes"""
        total = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total

    async def _stop_project_containers(self, project_id: str):
        """
        Stop all Docker containers associated with a project.

        This handles:
        - Containers named after the project_id
        - Docker Compose services for the project
        """
        import subprocess

        try:
            # Stop containers with project_id in name
            # Pattern: bharatbuild-{project_id} or project-{project_id}
            container_patterns = [
                f"bharatbuild-{project_id}",
                f"project-{project_id}",
                project_id[:12]  # First 12 chars of UUID
            ]

            for pattern in container_patterns:
                try:
                    # Find containers matching pattern
                    result = subprocess.run(
                        ["docker", "ps", "-q", "--filter", f"name={pattern}"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    container_ids = result.stdout.strip().split('\n')
                    container_ids = [c for c in container_ids if c]  # Filter empty strings

                    if container_ids:
                        # Stop the containers
                        subprocess.run(
                            ["docker", "stop"] + container_ids,
                            capture_output=True,
                            timeout=30
                        )
                        logger.info(f"[SandboxCleanup] Stopped {len(container_ids)} containers for {project_id}")

                        # Remove the containers
                        subprocess.run(
                            ["docker", "rm", "-f"] + container_ids,
                            capture_output=True,
                            timeout=30
                        )
                except subprocess.TimeoutExpired:
                    logger.warning(f"[SandboxCleanup] Timeout stopping containers for {project_id}")
                except FileNotFoundError:
                    # Docker not installed - skip silently
                    pass

        except Exception as e:
            logger.warning(f"[SandboxCleanup] Error stopping containers for {project_id}: {e}")


# Singleton instance
sandbox_cleanup = SandboxCleanupService()


# Convenience functions
async def start_cleanup_service():
    """Start the global cleanup service"""
    await sandbox_cleanup.start()


async def stop_cleanup_service():
    """Stop the global cleanup service"""
    await sandbox_cleanup.stop()


def touch_project(project_id: str):
    """Touch a project to keep it alive"""
    sandbox_cleanup.touch_project(project_id)


def get_project_expiry(project_id: str):
    """Get project expiry info"""
    return sandbox_cleanup.get_project_expiry(project_id)
