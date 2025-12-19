"""
Enterprise Tracker - Unified interface for enterprise services
Integrates: MessageService, SandboxDBService, SnapshotService, FileVersionService

This provides a simple API for the orchestrator to track:
- User/agent messages
- Sandbox lifecycle
- Project snapshots
- File version history
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_message import MessageRole
from app.models.sandbox import SandboxStatus, LogType
from app.services.message_service import MessageService
from app.services.sandbox_db_service import SandboxDBService
from app.services.snapshot_service import SnapshotService
from app.services.file_version_service import FileVersionService
from app.core.logging_config import logger
from app.core.config import settings


class EnterpriseTracker:
    """
    Unified tracker for enterprise features.

    Usage:
        tracker = EnterpriseTracker(db_session)

        # Track messages
        await tracker.track_user_message(project_id, "Create a todo app")
        await tracker.track_agent_response(project_id, "planner", plan_content, tokens=500)

        # Track file changes
        await tracker.track_file_created(project_id, file_id, content, "writer")
        await tracker.track_file_edited(project_id, file_id, new_content, old_content, "fixer")

        # Snapshots
        await tracker.create_checkpoint(project_id, "Before auth changes")

        # Sandbox
        sandbox = await tracker.start_sandbox(project_id)
        await tracker.log_sandbox_output(sandbox.id, "npm install output...")
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._message_service = MessageService(db)
        self._sandbox_service = SandboxDBService(db)
        self._snapshot_service = SnapshotService(db)
        self._file_version_service = FileVersionService(db)

    # ==================== Message Tracking ====================

    async def track_user_message(
        self,
        project_id: UUID,
        content: str,
        extra_data: Optional[str] = None
    ):
        """Track a user message/prompt"""
        try:
            await self._message_service.add_user_message(
                project_id=project_id,
                content=content,
                extra_data=extra_data
            )
            logger.debug(f"Tracked user message for project {project_id}")
        except Exception as e:
            logger.warning(f"Failed to track user message: {e}")

    async def track_agent_response(
        self,
        project_id: UUID,
        agent_type: str,
        content: str,
        tokens_used: int = 0,
        model_used: str = None
    ):
        """Track an agent's response"""
        try:
            await self._message_service.add_agent_message(
                project_id=project_id,
                agent_type=agent_type,
                content=content,
                tokens_used=tokens_used,
                model_used=model_used or settings.CLAUDE_SONNET_MODEL
            )
            logger.debug(f"Tracked {agent_type} response for project {project_id}")
        except Exception as e:
            logger.warning(f"Failed to track agent response: {e}")

    async def get_conversation_context(
        self,
        project_id: UUID,
        max_messages: int = 20
    ) -> List[dict]:
        """Get conversation history for LLM context"""
        try:
            return await self._message_service.get_conversation_context(
                project_id=project_id,
                max_messages=max_messages
            )
        except Exception as e:
            logger.warning(f"Failed to get conversation context: {e}")
            return []

    # ==================== File Version Tracking ====================

    async def track_file_created(
        self,
        project_id: UUID,
        file_id: UUID,
        content: str,
        created_by: str = "writer"
    ):
        """Track initial file creation"""
        try:
            await self._file_version_service.create_initial_version(
                file_id=file_id,
                project_id=project_id,
                content=content,
                created_by=created_by
            )
            logger.debug(f"Tracked file creation: {file_id}")
        except Exception as e:
            logger.warning(f"Failed to track file creation: {e}")

    async def track_file_edited(
        self,
        project_id: UUID,
        file_id: UUID,
        new_content: str,
        old_content: Optional[str] = None,
        edited_by: str = "user",
        change_summary: Optional[str] = None
    ):
        """Track file edit"""
        try:
            await self._file_version_service.create_version(
                file_id=file_id,
                project_id=project_id,
                content=new_content,
                created_by=edited_by,
                change_type="edit",
                change_summary=change_summary,
                previous_content=old_content
            )
            logger.debug(f"Tracked file edit: {file_id} by {edited_by}")
        except Exception as e:
            logger.warning(f"Failed to track file edit: {e}")

    async def track_file_fixed(
        self,
        project_id: UUID,
        file_id: UUID,
        new_content: str,
        old_content: Optional[str] = None,
        fix_summary: Optional[str] = None
    ):
        """Track file fix by fixer agent"""
        try:
            await self._file_version_service.create_version(
                file_id=file_id,
                project_id=project_id,
                content=new_content,
                created_by="fixer",
                change_type="fix",
                change_summary=fix_summary,
                previous_content=old_content
            )
            logger.debug(f"Tracked file fix: {file_id}")
        except Exception as e:
            logger.warning(f"Failed to track file fix: {e}")

    async def get_file_history(
        self,
        file_id: UUID,
        limit: int = 20
    ) -> List[Any]:
        """Get version history for a file"""
        try:
            return await self._file_version_service.get_file_history(file_id, limit)
        except Exception as e:
            logger.warning(f"Failed to get file history: {e}")
            return []

    async def undo_file_change(
        self,
        file_id: UUID,
        project_id: UUID
    ) -> bool:
        """Undo the last change to a file"""
        try:
            result = await self._file_version_service.undo(file_id, project_id)
            return result is not None
        except Exception as e:
            logger.warning(f"Failed to undo file change: {e}")
            return False

    # ==================== Snapshot/Checkpoint ====================

    async def create_checkpoint(
        self,
        project_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        trigger: str = "manual"
    ):
        """Create a project checkpoint/snapshot"""
        try:
            snapshot = await self._snapshot_service.create_snapshot(
                project_id=project_id,
                name=name,
                description=description,
                trigger=trigger
            )
            logger.info(f"Created checkpoint '{snapshot.name}' for project {project_id}")
            return snapshot
        except Exception as e:
            logger.warning(f"Failed to create checkpoint: {e}")
            return None

    async def create_auto_checkpoint(
        self,
        project_id: UUID,
        trigger: str = "before_fix"
    ):
        """Create an automatic checkpoint (e.g., before fixer runs)"""
        try:
            return await self._snapshot_service.create_auto_snapshot(
                project_id=project_id,
                trigger=trigger
            )
        except Exception as e:
            logger.warning(f"Failed to create auto checkpoint: {e}")
            return None

    async def restore_checkpoint(
        self,
        project_id: UUID,
        snapshot_id: UUID
    ) -> Dict[str, Any]:
        """Restore project to a checkpoint"""
        try:
            return await self._snapshot_service.restore_snapshot(
                snapshot_id=snapshot_id,
                project_id=project_id
            )
        except Exception as e:
            logger.error(f"Failed to restore checkpoint: {e}")
            raise

    async def list_checkpoints(
        self,
        project_id: UUID,
        limit: int = 20
    ) -> List[Any]:
        """List checkpoints for a project"""
        try:
            return await self._snapshot_service.get_snapshots(project_id, limit)
        except Exception as e:
            logger.warning(f"Failed to list checkpoints: {e}")
            return []

    # ==================== Sandbox Tracking ====================

    async def start_sandbox(
        self,
        project_id: UUID,
        docker_container_id: Optional[str] = None,
        port_mappings: Optional[Dict] = None
    ):
        """Record sandbox instance creation"""
        try:
            return await self._sandbox_service.create_sandbox_instance(
                project_id=project_id,
                docker_container_id=docker_container_id,
                port_mappings=port_mappings
            )
        except Exception as e:
            logger.warning(f"Failed to track sandbox start: {e}")
            return None

    async def update_sandbox_status(
        self,
        sandbox_id: UUID,
        status: SandboxStatus,
        container_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Update sandbox status"""
        try:
            return await self._sandbox_service.update_sandbox_status(
                sandbox_id=sandbox_id,
                status=status,
                docker_container_id=container_id,
                error_message=error
            )
        except Exception as e:
            logger.warning(f"Failed to update sandbox status: {e}")
            return None

    async def log_sandbox_output(
        self,
        sandbox_id: UUID,
        content: str,
        log_type: LogType = LogType.STDOUT
    ):
        """Log sandbox output (stdout/stderr/build)"""
        try:
            await self._sandbox_service.add_log(
                sandbox_id=sandbox_id,
                content=content,
                log_type=log_type
            )
        except Exception as e:
            logger.warning(f"Failed to log sandbox output: {e}")

    async def start_terminal_session(
        self,
        sandbox_id: UUID,
        session_name: str = "main"
    ):
        """Start a terminal session"""
        try:
            return await self._sandbox_service.create_terminal_session(
                sandbox_id=sandbox_id,
                session_name=session_name
            )
        except Exception as e:
            logger.warning(f"Failed to start terminal session: {e}")
            return None

    async def record_terminal_command(
        self,
        session_id: UUID,
        command: str,
        output: Optional[str] = None,
        exit_code: Optional[int] = None
    ):
        """Record a terminal command"""
        try:
            await self._sandbox_service.add_terminal_command(
                session_id=session_id,
                command=command,
                output=output,
                exit_code=exit_code
            )
        except Exception as e:
            logger.warning(f"Failed to record terminal command: {e}")

    async def start_preview_session(
        self,
        sandbox_id: UUID,
        internal_port: int,
        external_port: Optional[int] = None,
        preview_url: Optional[str] = None
    ):
        """Start a live preview session"""
        try:
            return await self._sandbox_service.create_preview_session(
                sandbox_id=sandbox_id,
                internal_port=internal_port,
                external_port=external_port,
                preview_url=preview_url
            )
        except Exception as e:
            logger.warning(f"Failed to start preview session: {e}")
            return None

    # ==================== Cleanup ====================

    async def cleanup_project_data(self, project_id: UUID) -> Dict[str, Any]:
        """Clean up all enterprise data for a project"""
        results = {
            "messages_deleted": 0,
            "file_versions_deleted": 0,
            "snapshots_deleted": 0,
            "sandbox_data": {}
        }

        try:
            results["messages_deleted"] = await self._message_service.delete_project_messages(project_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup messages: {e}")

        try:
            results["file_versions_deleted"] = await self._file_version_service.delete_project_versions(project_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup file versions: {e}")

        try:
            results["snapshots_deleted"] = await self._snapshot_service.delete_project_snapshots(project_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup snapshots: {e}")

        try:
            results["sandbox_data"] = await self._sandbox_service.cleanup_project_sandbox_data(project_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox data: {e}")

        logger.info(f"Cleaned up enterprise data for project {project_id}: {results}")
        return results
