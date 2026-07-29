"""
Temporary Session Storage - Ephemeral file storage for project generation

Architecture (Like Bolt.new):
- Files stored temporarily during generation
- Auto-deleted after download or 1 hour timeout
- Zero permanent storage cost
- GDPR compliant (no data retention)

Usage:
    storage = TempSessionStorage()

    # Create session
    session_id = storage.create_session()

    # Store files during generation
    storage.write_file(session_id, "src/App.tsx", content)
    storage.write_file(session_id, "package.json", content)

    # Store plan
    storage.write_plan(session_id, plan_dict)

    # Generate ZIP for download
    zip_path = storage.create_zip(session_id)

    # Cleanup after download
    storage.delete_session(session_id)
"""

import os
import json
import shutil
import uuid
import zipfile
import asyncio
import aiofiles
import aiofiles.os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import threading
from app.core.config import settings
from app.core.logging_config import logger

# Configuration - loaded from settings (can be overridden via .env)
TEMP_BASE_DIR = Path("/tmp/bharatbuild_sessions")
SESSION_TTL_SECONDS = settings.SESSION_TTL_SECONDS
CLEANUP_INTERVAL_SECONDS = settings.SESSION_CLEANUP_INTERVAL


@dataclass
class SessionMetadata:
    """Metadata for a generation session"""
    session_id: str
    created_at: datetime
    last_accessed: datetime
    user_id: Optional[str] = None
    project_name: Optional[str] = None
    file_count: int = 0
    total_size_bytes: int = 0
    status: str = "active"  # active, completed, expired


class TempSessionStorage:
    """
    Ephemeral storage for project generation sessions.

    - Creates temp directory per session
    - Auto-cleans after TTL expires
    - Provides ZIP generation
    - Thread-safe operations
    """

    def __init__(self, base_dir: Optional[Path] = None, ttl_seconds: int = SESSION_TTL_SECONDS):
        self.base_dir = base_dir or TEMP_BASE_DIR
        self.ttl_seconds = ttl_seconds
        self._sessions: Dict[str, SessionMetadata] = {}
        self._lock = threading.Lock()

        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Start cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info(f"TempSessionStorage initialized at {self.base_dir}")

    def _get_session_path(self, session_id: str) -> Path:
        """Get path for a session directory (internal)"""
        return self.base_dir / session_id

    def get_session_path(self, session_id: str) -> Optional[Path]:
        """
        Get path for a session directory (public).

        Returns:
            Path to session directory if it exists, None otherwise
        """
        path = self._get_session_path(session_id)
        if path.exists():
            return path
        return None

    def _get_files_path(self, session_id: str) -> Path:
        """Get path for files within a session"""
        return self._get_session_path(session_id) / "files"

    def _get_plan_path(self, session_id: str) -> Path:
        """Get path for plan.json"""
        return self._get_session_path(session_id) / "plan.json"

    def _get_metadata_path(self, session_id: str) -> Path:
        """Get path for session metadata"""
        return self._get_session_path(session_id) / ".metadata.json"

    def _get_zip_path(self, session_id: str) -> Path:
        """Get path for output ZIP"""
        return self._get_session_path(session_id) / "project.zip"

    # ==================== Session Management ====================

    def create_session(self, user_id: Optional[str] = None, project_name: Optional[str] = None) -> str:
        """
        Create a new generation session.

        Returns:
            session_id: Unique identifier for this session
        """
        session_id = str(uuid.uuid4())
        session_path = self._get_session_path(session_id)
        files_path = self._get_files_path(session_id)

        # Create directories
        session_path.mkdir(parents=True, exist_ok=True)
        files_path.mkdir(parents=True, exist_ok=True)

        # Create metadata
        now = datetime.utcnow()
        metadata = SessionMetadata(
            session_id=session_id,
            created_at=now,
            last_accessed=now,
            user_id=user_id,
            project_name=project_name
        )

        with self._lock:
            self._sessions[session_id] = metadata

        # Save metadata to disk
        self._save_metadata(session_id, metadata)

        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id

    def session_exists(self, session_id: str) -> bool:
        """Check if session exists and is valid"""
        session_path = self._get_session_path(session_id)
        return session_path.exists()

    def touch_session(self, session_id: str) -> None:
        """Update last accessed time to prevent expiry"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].last_accessed = datetime.utcnow()

    def get_session_info(self, session_id: str) -> Optional[SessionMetadata]:
        """Get session metadata"""
        with self._lock:
            return self._sessions.get(session_id)

    def _save_metadata(self, session_id: str, metadata: SessionMetadata) -> None:
        """Save metadata to disk"""
        metadata_path = self._get_metadata_path(session_id)
        data = {
            "session_id": metadata.session_id,
            "created_at": metadata.created_at.isoformat(),
            "last_accessed": metadata.last_accessed.isoformat(),
            "user_id": metadata.user_id,
            "project_name": metadata.project_name,
            "file_count": metadata.file_count,
            "total_size_bytes": metadata.total_size_bytes,
            "status": metadata.status
        }
        with open(metadata_path, 'w') as f:
            json.dump(data, f)

    # ==================== File Operations ====================

    def write_file(self, session_id: str, file_path: str, content: str) -> bool:
        """
        Write a file to the session.

        Args:
            session_id: Session identifier
            file_path: Relative path (e.g., "src/App.tsx")
            content: File content

        Returns:
            True if successful
        """
        if not self.session_exists(session_id):
            logger.error(f"Session {session_id} does not exist")
            return False

        full_path = self._get_files_path(session_id) / file_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Update metadata
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].file_count += 1
                self._sessions[session_id].total_size_bytes += len(content.encode('utf-8'))
                self._sessions[session_id].last_accessed = datetime.utcnow()

        self.touch_session(session_id)
        return True

    async def write_file_async(self, session_id: str, file_path: str, content: str) -> bool:
        """Async version of write_file"""
        if not self.session_exists(session_id):
            logger.error(f"Session {session_id} does not exist")
            return False

        full_path = self._get_files_path(session_id) / file_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file asynchronously
        async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
            await f.write(content)

        # Update metadata
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].file_count += 1
                self._sessions[session_id].total_size_bytes += len(content.encode('utf-8'))
                self._sessions[session_id].last_accessed = datetime.utcnow()

        return True

    def read_file(self, session_id: str, file_path: str) -> Optional[str]:
        """Read a file from the session (sync)"""
        full_path = self._get_files_path(session_id) / file_path

        if not full_path.exists():
            return None

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.touch_session(session_id)
        return content

    async def read_file_async(self, session_id: str, file_path: str) -> Optional[str]:
        """Read a file from the session (async)"""
        full_path = self._get_files_path(session_id) / file_path

        if not full_path.exists():
            return None

        async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
            content = await f.read()

        self.touch_session(session_id)
        return content

    def list_files(self, session_id: str) -> List[str]:
        """List all files in the session"""
        files_path = self._get_files_path(session_id)

        if not files_path.exists():
            return []

        files = []
        for path in files_path.rglob('*'):
            if path.is_file():
                relative_path = path.relative_to(files_path)
                files.append(str(relative_path))

        return sorted(files)

    def get_file_tree(self, session_id: str) -> Dict[str, Any]:
        """Get file tree structure for UI"""
        files_path = self._get_files_path(session_id)

        if not files_path.exists():
            return {"name": "root", "type": "folder", "children": []}

        def build_tree(path: Path, name: str) -> Dict[str, Any]:
            if path.is_file():
                return {
                    "name": name,
                    "type": "file",
                    "path": str(path.relative_to(files_path))
                }

            children = []
            for child in sorted(path.iterdir()):
                children.append(build_tree(child, child.name))

            return {
                "name": name,
                "type": "folder",
                "children": children
            }

        return build_tree(files_path, "root")

    # ==================== Plan Operations ====================

    def write_plan(self, session_id: str, plan: Dict[str, Any]) -> bool:
        """Write planner output (sync)"""
        if not self.session_exists(session_id):
            return False

        plan_path = self._get_plan_path(session_id)
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2)

        self.touch_session(session_id)
        return True

    async def write_plan_async(self, session_id: str, plan: Dict[str, Any]) -> bool:
        """Write planner output (async)"""
        if not self.session_exists(session_id):
            return False

        plan_path = self._get_plan_path(session_id)
        plan_json = json.dumps(plan, indent=2)

        async with aiofiles.open(plan_path, 'w', encoding='utf-8') as f:
            await f.write(plan_json)

        self.touch_session(session_id)
        return True

    def read_plan(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Read planner output (sync)"""
        plan_path = self._get_plan_path(session_id)

        if not plan_path.exists():
            return None

        with open(plan_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def read_plan_async(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Read planner output (async)"""
        plan_path = self._get_plan_path(session_id)

        if not plan_path.exists():
            return None

        async with aiofiles.open(plan_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)

    # ==================== ZIP Operations ====================

    def create_zip(self, session_id: str, project_name: Optional[str] = None) -> Optional[Path]:
        """
        Create ZIP file of all session files.

        Returns:
            Path to ZIP file, or None if failed
        """
        files_path = self._get_files_path(session_id)

        if not files_path.exists():
            logger.error(f"No files found for session {session_id}")
            return None

        zip_path = self._get_zip_path(session_id)

        # Get project name for ZIP root folder
        if not project_name:
            metadata = self.get_session_info(session_id)
            project_name = metadata.project_name if metadata else "project"

        project_name = project_name or "project"
        # Sanitize project name for filesystem
        project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
        project_name = project_name or "project"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_path.rglob('*'):
                if file_path.is_file():
                    # Add with project name as root folder
                    arcname = f"{project_name}/{file_path.relative_to(files_path)}"
                    zipf.write(file_path, arcname)

        # Update status
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].status = "completed"

        logger.info(f"Created ZIP for session {session_id}: {zip_path}")
        return zip_path

    def get_zip_path(self, session_id: str) -> Optional[Path]:
        """Get path to existing ZIP file"""
        zip_path = self._get_zip_path(session_id)
        return zip_path if zip_path.exists() else None

    # ==================== Cleanup Operations ====================

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its files.
        Call this after ZIP download.
        """
        session_path = self._get_session_path(session_id)

        if session_path.exists():
            shutil.rmtree(session_path)
            logger.info(f"Deleted session {session_id}")

        with self._lock:
            self._sessions.pop(session_id, None)

        return True

    def cleanup_expired_sessions(self) -> int:
        """
        Delete all sessions older than TTL.

        Returns:
            Number of sessions deleted
        """
        now = datetime.utcnow()
        expired_sessions = []

        # Find expired sessions
        with self._lock:
            for session_id, metadata in self._sessions.items():
                age = (now - metadata.last_accessed).total_seconds()
                if age > self.ttl_seconds:
                    expired_sessions.append(session_id)

        # Also check filesystem for orphaned sessions
        if self.base_dir.exists():
            for session_dir in self.base_dir.iterdir():
                if session_dir.is_dir():
                    session_id = session_dir.name
                    metadata_path = session_dir / ".metadata.json"

                    if metadata_path.exists():
                        try:
                            with open(metadata_path) as f:
                                data = json.load(f)
                            last_accessed = datetime.fromisoformat(data.get("last_accessed", "2000-01-01"))
                            age = (now - last_accessed).total_seconds()
                            if age > self.ttl_seconds and session_id not in expired_sessions:
                                expired_sessions.append(session_id)
                        except Exception:
                            # If metadata is corrupted, delete the session
                            if session_id not in expired_sessions:
                                expired_sessions.append(session_id)
                    else:
                        # No metadata file - check directory age
                        dir_age = (now - datetime.fromtimestamp(session_dir.stat().st_mtime)).total_seconds()
                        if dir_age > self.ttl_seconds and session_id not in expired_sessions:
                            expired_sessions.append(session_id)

        # Delete expired sessions
        for session_id in expired_sessions:
            self.delete_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    async def start_cleanup_task(self) -> None:
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                try:
                    self.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started session cleanup background task")

    def stop_cleanup_task(self) -> None:
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    def cleanup_all(self) -> None:
        """Delete ALL sessions (use on server restart)"""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)

        with self._lock:
            self._sessions.clear()

        logger.info("Cleaned up all sessions")

    # ==================== Stats ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_size = 0
        total_files = 0

        if self.base_dir.exists():
            for path in self.base_dir.rglob('*'):
                if path.is_file():
                    total_size += path.stat().st_size
                    total_files += 1

        return {
            "active_sessions": len(self._sessions),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_dir": str(self.base_dir),
            "ttl_seconds": self.ttl_seconds
        }


# Singleton instance
temp_storage = TempSessionStorage()
