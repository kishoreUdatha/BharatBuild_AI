"""
Snapshot Service - Manages project checkpoints/snapshots (snapshots table)
Provides save/restore functionality like Bolt.new's checkpoint feature.
"""

import json
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.models.snapshot import Snapshot
from app.models.project_file import ProjectFile
from app.services.storage_service import storage_service
from app.core.logging_config import logger


class SnapshotService:
    """
    Service for creating and restoring project snapshots.

    Use cases:
    - "Save Checkpoint" feature - save current state before big changes
    - "Restore" feature - go back to a previous state
    - Automatic snapshots before fixer agent runs
    - Share specific versions of a project
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_snapshot(
        self,
        project_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        trigger: str = "manual",
        created_by: str = "user"
    ) -> Snapshot:
        """
        Create a full snapshot of current project state.

        Args:
            project_id: Project UUID
            name: Optional snapshot name (e.g., "Before adding auth")
            description: Optional description
            trigger: What triggered this snapshot (manual, before_fix, auto_save)
            created_by: Who created it (user, agent, auto)

        Returns:
            Created Snapshot instance
        """
        # Get all project files with content
        result = await self.db.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .where(ProjectFile.is_folder == False)
            .order_by(ProjectFile.path)
        )
        files = result.scalars().all()

        # Build snapshot JSON
        snapshot_data = {
            "files": [],
            "file_tree": {},
            "created_at": datetime.utcnow().isoformat()
        }

        total_size = 0

        for f in files:
            # Get content - prioritize S3, fallback to inline for legacy data
            if f.s3_key:
                content_bytes = await storage_service.download_file(f.s3_key)
                content = content_bytes.decode('utf-8') if content_bytes else ""
            elif f.content_inline:
                # Legacy fallback for old inline content
                content = f.content_inline
            else:
                content = ""

            file_data = {
                "path": f.path,
                "name": f.name,
                "language": f.language,
                "content": content,
                "size_bytes": f.size_bytes,
                "content_hash": f.content_hash
            }

            snapshot_data["files"].append(file_data)
            total_size += f.size_bytes

            # Build file tree
            self._add_to_tree(snapshot_data["file_tree"], f.path)

        # Generate name if not provided
        if not name:
            name = f"Snapshot {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

        # Create snapshot record
        snapshot = Snapshot(
            project_id=project_id,
            name=name,
            description=description,
            snapshot_json=snapshot_data,
            file_count=len(files),
            total_size_bytes=total_size,
            created_by=created_by,
            trigger=trigger,
            created_at=datetime.utcnow()
        )

        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)

        logger.info(f"Created snapshot '{name}' for project {project_id} ({len(files)} files)")
        return snapshot

    async def create_auto_snapshot(
        self,
        project_id: UUID,
        trigger: str = "auto_save"
    ) -> Snapshot:
        """Create an automatic snapshot (before fixes, etc.)"""
        return await self.create_snapshot(
            project_id=project_id,
            name=f"Auto-save ({trigger})",
            trigger=trigger,
            created_by="auto"
        )

    async def restore_snapshot(
        self,
        snapshot_id: UUID,
        project_id: UUID
    ) -> Dict[str, Any]:
        """
        Restore a project to a snapshot state.

        Returns:
            Dict with restored file count and details
        """
        # Get snapshot
        result = await self.db.execute(
            select(Snapshot)
            .where(Snapshot.id == snapshot_id)
            .where(Snapshot.project_id == project_id)
        )
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found for project {project_id}")

        snapshot_data = snapshot.snapshot_json

        # Delete current files
        await self.db.execute(
            delete(ProjectFile)
            .where(ProjectFile.project_id == project_id)
        )

        # Restore files from snapshot - upload to S3, metadata to DB
        restored_count = 0
        for file_data in snapshot_data.get("files", []):
            content = file_data.get("content", "")
            content_bytes = content.encode('utf-8')

            # Upload to S3
            upload_result = await storage_service.upload_file(
                str(project_id),
                file_data["path"],
                content_bytes
            )
            s3_key = upload_result.get('s3_key')

            file_record = ProjectFile(
                project_id=project_id,
                path=file_data["path"],
                name=file_data["name"],
                language=file_data.get("language"),
                s3_key=s3_key,
                content_inline=None,  # Never store content inline
                is_inline=False,  # Always use S3
                size_bytes=file_data.get("size_bytes", len(content_bytes)),
                content_hash=file_data.get("content_hash"),
                is_folder=False
            )
            self.db.add(file_record)
            restored_count += 1

        await self.db.commit()

        logger.info(f"Restored snapshot '{snapshot.name}' for project {project_id}")

        return {
            "snapshot_id": str(snapshot_id),
            "snapshot_name": snapshot.name,
            "files_restored": restored_count,
            "restored_at": datetime.utcnow().isoformat()
        }

    async def get_snapshots(
        self,
        project_id: UUID,
        limit: int = 20
    ) -> List[Snapshot]:
        """Get all snapshots for a project"""
        result = await self.db.execute(
            select(Snapshot)
            .where(Snapshot.project_id == project_id)
            .order_by(Snapshot.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_snapshot(self, snapshot_id: UUID) -> Optional[Snapshot]:
        """Get a specific snapshot"""
        result = await self.db.execute(
            select(Snapshot).where(Snapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    async def get_snapshot_summary(
        self,
        snapshot_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get snapshot summary (without full file contents)"""
        snapshot = await self.get_snapshot(snapshot_id)

        if not snapshot:
            return None

        return {
            "id": str(snapshot.id),
            "name": snapshot.name,
            "description": snapshot.description,
            "file_count": snapshot.file_count,
            "total_size_bytes": snapshot.total_size_bytes,
            "created_by": snapshot.created_by,
            "trigger": snapshot.trigger,
            "created_at": snapshot.created_at.isoformat(),
            "file_list": snapshot.file_list
        }

    async def delete_snapshot(self, snapshot_id: UUID) -> bool:
        """Delete a snapshot"""
        result = await self.db.execute(
            delete(Snapshot).where(Snapshot.id == snapshot_id)
        )
        await self.db.commit()

        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted snapshot {snapshot_id}")

        return deleted

    async def delete_project_snapshots(self, project_id: UUID) -> int:
        """Delete all snapshots for a project"""
        result = await self.db.execute(
            delete(Snapshot).where(Snapshot.project_id == project_id)
        )
        await self.db.commit()

        logger.info(f"Deleted {result.rowcount} snapshots for project {project_id}")
        return result.rowcount

    async def get_snapshot_count(self, project_id: UUID) -> int:
        """Get number of snapshots for a project"""
        result = await self.db.execute(
            select(func.count(Snapshot.id))
            .where(Snapshot.project_id == project_id)
        )
        return result.scalar() or 0

    async def compare_snapshots(
        self,
        snapshot_id_1: UUID,
        snapshot_id_2: UUID
    ) -> Dict[str, Any]:
        """
        Compare two snapshots and return differences.

        Returns:
            Dict with added, removed, and modified files
        """
        snap1 = await self.get_snapshot(snapshot_id_1)
        snap2 = await self.get_snapshot(snapshot_id_2)

        if not snap1 or not snap2:
            raise ValueError("One or both snapshots not found")

        files1 = {f["path"]: f for f in snap1.snapshot_json.get("files", [])}
        files2 = {f["path"]: f for f in snap2.snapshot_json.get("files", [])}

        paths1 = set(files1.keys())
        paths2 = set(files2.keys())

        added = paths2 - paths1
        removed = paths1 - paths2
        common = paths1 & paths2

        modified = []
        for path in common:
            if files1[path].get("content_hash") != files2[path].get("content_hash"):
                modified.append(path)

        return {
            "snapshot_1": {"id": str(snapshot_id_1), "name": snap1.name},
            "snapshot_2": {"id": str(snapshot_id_2), "name": snap2.name},
            "added": list(added),
            "removed": list(removed),
            "modified": modified,
            "unchanged": len(common) - len(modified)
        }

    def _add_to_tree(self, tree: Dict, path: str):
        """Helper to build file tree structure"""
        parts = path.split('/')
        current = tree

        for i, part in enumerate(parts[:-1]):  # Directories
            if part not in current:
                current[part] = {"_type": "folder", "_children": {}}
            current = current[part].get("_children", current[part])

        # Add file
        file_name = parts[-1]
        current[file_name] = {"_type": "file"}
