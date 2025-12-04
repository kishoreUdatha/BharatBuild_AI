"""
Workspace Restoration Service - Bolt.new Style

When a user opens an old project and the sandbox has been cleaned up,
this service can restore the workspace in two ways:

1. RESTORE from Database/S3 (Fast)
   - Read files from ProjectFile table (content_inline for small files)
   - Download large files from S3
   - Write to sandbox

2. REGENERATE from Plan (Like Bolt.new)
   - Read plan_json from Project table
   - Re-run the writer agent to regenerate all files
   - Creates fresh files based on the original plan
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging_config import logger
from app.core.config import settings
from app.models.project import Project
from app.models.project_file import ProjectFile


class WorkspaceRestoreService:
    """
    Service to restore project workspace after sandbox cleanup.

    Two restoration modes:
    - RESTORE: Fast restore from database/S3 storage
    - REGENERATE: Re-run planner/writer from plan_json (Bolt.new style)
    """

    def __init__(self):
        self.sandbox_path = Path(settings.SANDBOX_PATH)

    async def check_workspace_status(
        self,
        project_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Check if a project's workspace exists and what restoration options are available.

        Returns:
            Dict with:
            - exists: bool - workspace exists in sandbox
            - can_restore: bool - can restore from database/S3
            - can_regenerate: bool - can regenerate from plan
            - file_count: int - number of files in database
            - has_plan: bool - has plan_json stored
        """
        workspace_path = self.sandbox_path / project_id

        # Check if workspace exists
        exists = workspace_path.exists() and any(workspace_path.iterdir())

        # Check database for restoration options
        project = await self._get_project(project_id, db)
        files = await self._get_project_files(project_id, db) if project else []

        has_plan = project and project.plan_json is not None
        file_count = len(files)
        can_restore = file_count > 0
        can_regenerate = has_plan

        return {
            "project_id": project_id,
            "workspace_exists": exists,
            "can_restore": can_restore,
            "can_regenerate": can_regenerate,
            "file_count": file_count,
            "has_plan": has_plan,
            "restoration_options": self._get_restoration_options(exists, can_restore, can_regenerate)
        }

    def _get_restoration_options(self, exists: bool, can_restore: bool, can_regenerate: bool) -> List[str]:
        """Get available restoration options"""
        options = []
        if exists:
            options.append("workspace_exists")  # No restoration needed
        if can_restore:
            options.append("restore_from_storage")  # Fast restore from DB/S3
        if can_regenerate:
            options.append("regenerate_from_plan")  # Re-run planner/writer
        return options

    async def restore_from_storage(
        self,
        project_id: str,
        db: AsyncSession,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Restore workspace from database/S3 storage.

        This is the FAST method - directly copies stored files to sandbox.

        Args:
            project_id: Project to restore
            db: Database session
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with restoration results
        """
        workspace_path = self.sandbox_path / project_id

        # Get files from database
        files = await self._get_project_files(project_id, db)

        if not files:
            return {
                "success": False,
                "error": "No files found in storage",
                "restored_files": 0
            }

        # Create workspace directory
        workspace_path.mkdir(parents=True, exist_ok=True)

        restored_count = 0
        errors = []

        for i, file in enumerate(files):
            try:
                file_path = workspace_path / file.path

                # Create parent directories
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Get content
                if file.is_inline and file.content_inline:
                    # Small file - content stored in database
                    content = file.content_inline
                elif file.s3_key:
                    # Large file - download from S3
                    content = await self._download_from_s3(file.s3_key)
                    if content is None:
                        errors.append(f"Failed to download {file.path} from S3")
                        continue
                else:
                    errors.append(f"No content available for {file.path}")
                    continue

                # Write file
                file_path.write_text(content, encoding='utf-8')
                restored_count += 1

                # Progress callback
                if progress_callback:
                    await progress_callback({
                        "type": "file_restored",
                        "file": file.path,
                        "progress": (i + 1) / len(files) * 100
                    })

            except Exception as e:
                errors.append(f"Error restoring {file.path}: {str(e)}")
                logger.error(f"[WorkspaceRestore] Error restoring {file.path}: {e}")

        logger.info(f"[WorkspaceRestore] Restored {restored_count}/{len(files)} files for {project_id}")

        return {
            "success": restored_count > 0,
            "restored_files": restored_count,
            "total_files": len(files),
            "errors": errors if errors else None,
            "workspace_path": str(workspace_path)
        }

    async def regenerate_from_plan(
        self,
        project_id: str,
        db: AsyncSession,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Regenerate workspace by replaying Claude messages (Bolt.new style).

        This is exactly how Bolt.new works:
        1. Load saved plan.json and chat history from DB
        2. Create new empty workspace
        3. Replay Claude messages to regenerate files
        4. Claude generates fresh files (NOT retrieved from storage)

        Args:
            project_id: Project to regenerate
            db: Database session
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with regeneration info for orchestrator
        """
        # Get project with plan and history
        project = await self._get_project(project_id, db)

        if not project:
            return {
                "success": False,
                "error": "Project not found"
            }

        if not project.plan_json and not project.history:
            return {
                "success": False,
                "error": "No plan or history found - cannot regenerate"
            }

        # Create new empty workspace (Bolt.new step 2)
        workspace_path = self.sandbox_path / project_id
        if workspace_path.exists():
            import shutil
            shutil.rmtree(workspace_path)  # Clear any leftover files
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Prepare regeneration context (Bolt.new step 3)
        # This will be sent to the orchestrator to replay
        regeneration_context = {
            "project_id": project_id,
            "plan_json": project.plan_json,
            "history": project.history,  # Claude messages to replay
            "original_request": project.description or project.title,
            "tech_stack": project.tech_stack,
            "framework": project.framework,
            "mode": "regenerate"  # Skip planning, go straight to writing
        }

        return {
            "success": True,
            "mode": "regenerate",
            "regeneration_context": regeneration_context,
            "workspace_path": str(workspace_path),
            "message": "Ready to regenerate - call orchestrator with this context",
            "instructions": {
                "endpoint": "/api/v1/orchestrator/regenerate",
                "method": "POST",
                "body": {
                    "project_id": project_id,
                    "skip_planning": True,
                    "use_saved_plan": True
                }
            }
        }

    async def auto_restore(
        self,
        project_id: str,
        db: AsyncSession,
        prefer_regenerate: bool = False
    ) -> Dict:
        """
        Automatically restore workspace using best available method.

        Args:
            project_id: Project to restore
            db: Database session
            prefer_regenerate: If True, prefer regeneration over restoration

        Returns:
            Dict with restoration results
        """
        status = await self.check_workspace_status(project_id, db)

        if status["workspace_exists"]:
            return {
                "success": True,
                "method": "already_exists",
                "message": "Workspace already exists"
            }

        if prefer_regenerate and status["can_regenerate"]:
            return await self.regenerate_from_plan(project_id, db)

        if status["can_restore"]:
            return await self.restore_from_storage(project_id, db)

        if status["can_regenerate"]:
            return await self.regenerate_from_plan(project_id, db)

        return {
            "success": False,
            "error": "No restoration method available",
            "status": status
        }

    async def _get_project(self, project_id: str, db: AsyncSession) -> Optional[Project]:
        """Get project from database"""
        try:
            from uuid import UUID
            result = await db.execute(
                select(Project).where(Project.id == UUID(project_id))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"[WorkspaceRestore] Error getting project: {e}")
            return None

    async def _get_project_files(self, project_id: str, db: AsyncSession) -> List[ProjectFile]:
        """Get all files for a project from database"""
        try:
            from uuid import UUID
            result = await db.execute(
                select(ProjectFile).where(ProjectFile.project_id == UUID(project_id))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"[WorkspaceRestore] Error getting project files: {e}")
            return []

    async def _download_from_s3(self, s3_key: str) -> Optional[str]:
        """Download file content from S3/MinIO"""
        try:
            # Import storage service
            from app.services.unified_storage import unified_storage
            content = await unified_storage.download_file(s3_key)
            return content.decode('utf-8') if isinstance(content, bytes) else content
        except Exception as e:
            logger.error(f"[WorkspaceRestore] Error downloading from S3: {e}")
            return None


# Singleton instance
workspace_restore = WorkspaceRestoreService()
