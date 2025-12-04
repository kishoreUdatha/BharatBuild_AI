"""
File Version Service - Git-like file versioning (project_file_versions table)
Provides undo/redo, file history, and diff viewing.
"""

import difflib
import hashlib
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.models.file_version import ProjectFileVersion
from app.models.project_file import ProjectFile
from app.core.logging_config import logger


class FileVersionService:
    """
    Service for managing file version history.

    Use cases:
    - Track every file change
    - Undo/redo functionality
    - View file history
    - Diff between versions
    - Restore previous versions
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_version(
        self,
        file_id: UUID,
        project_id: UUID,
        content: str,
        created_by: str = "user",
        change_type: str = "edit",
        change_summary: Optional[str] = None,
        previous_content: Optional[str] = None
    ) -> ProjectFileVersion:
        """
        Create a new version of a file.

        Args:
            file_id: File UUID
            project_id: Project UUID
            content: File content
            created_by: Who made the change (user, writer, fixer, etc.)
            change_type: Type of change (create, edit, fix, refactor)
            change_summary: Brief description of changes
            previous_content: Previous content (for diff generation)

        Returns:
            Created ProjectFileVersion instance
        """
        # Get next version number
        result = await self.db.execute(
            select(func.max(ProjectFileVersion.version))
            .where(ProjectFileVersion.file_id == file_id)
        )
        max_version = result.scalar() or 0
        new_version = max_version + 1

        # Calculate content hash
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        size_bytes = len(content.encode('utf-8'))

        # Generate diff patch if previous content provided
        diff_patch = None
        if previous_content and change_type != "create":
            diff_patch = self._generate_diff(previous_content, content)

        # Create version record
        version = ProjectFileVersion(
            file_id=file_id,
            project_id=project_id,
            version=new_version,
            content=content,
            content_hash=content_hash,
            size_bytes=size_bytes,
            diff_patch=diff_patch,
            created_by=created_by,
            change_type=change_type,
            change_summary=change_summary,
            created_at=datetime.utcnow()
        )

        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)

        logger.debug(f"Created version {new_version} for file {file_id} ({change_type})")
        return version

    async def create_initial_version(
        self,
        file_id: UUID,
        project_id: UUID,
        content: str,
        created_by: str = "writer"
    ) -> ProjectFileVersion:
        """Create the first version of a file"""
        return await self.create_version(
            file_id=file_id,
            project_id=project_id,
            content=content,
            created_by=created_by,
            change_type="create",
            change_summary="File created"
        )

    async def get_version(
        self,
        file_id: UUID,
        version_number: Optional[int] = None
    ) -> Optional[ProjectFileVersion]:
        """
        Get a specific version of a file.
        If version_number is None, returns the latest version.
        """
        query = select(ProjectFileVersion).where(
            ProjectFileVersion.file_id == file_id
        )

        if version_number:
            query = query.where(ProjectFileVersion.version == version_number)
        else:
            query = query.order_by(ProjectFileVersion.version.desc()).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_version(self, file_id: UUID) -> Optional[ProjectFileVersion]:
        """Get the latest version of a file"""
        return await self.get_version(file_id)

    async def get_file_history(
        self,
        file_id: UUID,
        limit: int = 20
    ) -> List[ProjectFileVersion]:
        """Get version history for a file"""
        result = await self.db.execute(
            select(ProjectFileVersion)
            .where(ProjectFileVersion.file_id == file_id)
            .order_by(ProjectFileVersion.version.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_project_history(
        self,
        project_id: UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent version changes across all files in a project.
        Useful for activity feed.
        """
        result = await self.db.execute(
            select(ProjectFileVersion, ProjectFile)
            .join(ProjectFile, ProjectFileVersion.file_id == ProjectFile.id)
            .where(ProjectFileVersion.project_id == project_id)
            .order_by(ProjectFileVersion.created_at.desc())
            .limit(limit)
        )

        history = []
        for version, file in result.fetchall():
            history.append({
                "version_id": str(version.id),
                "file_id": str(file.id),
                "file_path": file.path,
                "file_name": file.name,
                "version": version.version,
                "change_type": version.change_type,
                "change_summary": version.change_summary,
                "created_by": version.created_by,
                "created_at": version.created_at.isoformat()
            })

        return history

    async def restore_version(
        self,
        file_id: UUID,
        version_number: int,
        project_id: UUID
    ) -> Optional[ProjectFileVersion]:
        """
        Restore a file to a previous version.
        This creates a new version with the old content.
        """
        # Get the version to restore
        target_version = await self.get_version(file_id, version_number)
        if not target_version:
            return None

        # Get current content for diff
        current_version = await self.get_latest_version(file_id)
        current_content = current_version.content if current_version else ""

        # Create new version with restored content
        restored_version = await self.create_version(
            file_id=file_id,
            project_id=project_id,
            content=target_version.content,
            created_by="user",
            change_type="restore",
            change_summary=f"Restored to version {version_number}",
            previous_content=current_content
        )

        # Update the actual file record
        result = await self.db.execute(
            select(ProjectFile).where(ProjectFile.id == file_id)
        )
        file_record = result.scalar_one_or_none()

        if file_record:
            file_record.content_inline = target_version.content
            file_record.content_hash = target_version.content_hash
            file_record.size_bytes = target_version.size_bytes
            await self.db.commit()

        logger.info(f"Restored file {file_id} to version {version_number}")
        return restored_version

    async def undo(self, file_id: UUID, project_id: UUID) -> Optional[ProjectFileVersion]:
        """
        Undo the last change (restore to version n-1).
        """
        versions = await self.get_file_history(file_id, limit=2)

        if len(versions) < 2:
            logger.warning(f"Cannot undo: file {file_id} has only {len(versions)} version(s)")
            return None

        # versions[0] is current, versions[1] is previous
        previous_version = versions[1]

        return await self.restore_version(
            file_id=file_id,
            version_number=previous_version.version,
            project_id=project_id
        )

    async def get_diff(
        self,
        file_id: UUID,
        version_1: int,
        version_2: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get diff between two versions.

        Returns:
            Dict with unified diff and statistics
        """
        v1 = await self.get_version(file_id, version_1)
        v2 = await self.get_version(file_id, version_2)

        if not v1 or not v2:
            return None

        diff = self._generate_diff(v1.content, v2.content)

        # Count changes
        lines_added = 0
        lines_removed = 0
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                lines_added += 1
            elif line.startswith('-') and not line.startswith('---'):
                lines_removed += 1

        return {
            "file_id": str(file_id),
            "version_1": version_1,
            "version_2": version_2,
            "diff": diff,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "total_changes": lines_added + lines_removed
        }

    async def get_version_count(self, file_id: UUID) -> int:
        """Get total version count for a file"""
        result = await self.db.execute(
            select(func.count(ProjectFileVersion.id))
            .where(ProjectFileVersion.file_id == file_id)
        )
        return result.scalar() or 0

    async def delete_file_versions(self, file_id: UUID) -> int:
        """Delete all versions for a file"""
        result = await self.db.execute(
            delete(ProjectFileVersion)
            .where(ProjectFileVersion.file_id == file_id)
        )
        await self.db.commit()
        return result.rowcount

    async def delete_project_versions(self, project_id: UUID) -> int:
        """Delete all versions for a project"""
        result = await self.db.execute(
            delete(ProjectFileVersion)
            .where(ProjectFileVersion.project_id == project_id)
        )
        await self.db.commit()

        logger.info(f"Deleted {result.rowcount} file versions for project {project_id}")
        return result.rowcount

    async def prune_old_versions(
        self,
        file_id: UUID,
        keep_count: int = 20
    ) -> int:
        """
        Delete old versions, keeping the most recent N versions.
        Useful for storage optimization.
        """
        # Get versions to keep
        result = await self.db.execute(
            select(ProjectFileVersion.id)
            .where(ProjectFileVersion.file_id == file_id)
            .order_by(ProjectFileVersion.version.desc())
            .limit(keep_count)
        )
        keep_ids = [row[0] for row in result.fetchall()]

        if not keep_ids:
            return 0

        # Delete older versions
        result = await self.db.execute(
            delete(ProjectFileVersion)
            .where(ProjectFileVersion.file_id == file_id)
            .where(ProjectFileVersion.id.notin_(keep_ids))
        )
        await self.db.commit()

        if result.rowcount > 0:
            logger.info(f"Pruned {result.rowcount} old versions for file {file_id}")

        return result.rowcount

    def _generate_diff(self, old_content: str, new_content: str) -> str:
        """Generate unified diff between two content strings"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile='a/file',
            tofile='b/file',
            lineterm=''
        )

        return ''.join(diff)

    async def get_version_by_hash(
        self,
        file_id: UUID,
        content_hash: str
    ) -> Optional[ProjectFileVersion]:
        """Find a version by its content hash (for deduplication)"""
        result = await self.db.execute(
            select(ProjectFileVersion)
            .where(ProjectFileVersion.file_id == file_id)
            .where(ProjectFileVersion.content_hash == content_hash)
            .limit(1)
        )
        return result.scalar_one_or_none()
