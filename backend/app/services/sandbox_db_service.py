"""
Sandbox Database Service - Manages container tracking in PostgreSQL
Handles: sandbox_instances, sandbox_logs, terminal_sessions, terminal_history, live_preview_sessions
"""

from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func

from app.models.sandbox import (
    SandboxInstance, SandboxStatus, SandboxLog, LogType,
    TerminalSession, TerminalHistory, LivePreviewSession
)
from app.core.logging_config import logger


def to_str(value: Union[UUID, str, None]) -> Optional[str]:
    """Convert UUID to string if needed"""
    if value is None:
        return None
    return str(value) if isinstance(value, UUID) else value


class SandboxDBService:
    """
    Service for persisting sandbox/container data to PostgreSQL.

    This complements the in-memory DockerSandboxManager by providing:
    - Persistence across server restarts
    - Historical data for analytics
    - Audit trail of container operations
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Sandbox Instance Operations ==========

    async def create_sandbox_instance(
        self,
        project_id: UUID,
        docker_container_id: Optional[str] = None,
        port_mappings: Optional[Dict[str, Any]] = None,
        environment: Optional[Dict[str, str]] = None,
        cpu_limit: str = "0.5",
        memory_limit: str = "512m"
    ) -> SandboxInstance:
        """Create a new sandbox instance record"""
        instance = SandboxInstance(
            project_id=to_str(project_id),
            docker_container_id=docker_container_id,
            status=SandboxStatus.PENDING.value,
            port_mappings=port_mappings,
            cpu_limit=cpu_limit,
            memory_limit=memory_limit,
            created_at=datetime.utcnow()
        )

        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)

        logger.info(f"Created sandbox instance {instance.id} for project {project_id}")
        return instance

    async def update_sandbox_status(
        self,
        sandbox_id: UUID,
        status: SandboxStatus,
        docker_container_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[SandboxInstance]:
        """Update sandbox status"""
        result = await self.db.execute(
            select(SandboxInstance).where(SandboxInstance.id == to_str(sandbox_id))
        )
        instance = result.scalar_one_or_none()

        if not instance:
            return None

        instance.status = status.value if isinstance(status, SandboxStatus) else status
        instance.updated_at = datetime.utcnow()

        if docker_container_id:
            instance.docker_container_id = docker_container_id

        if error_message:
            instance.last_error = error_message

        if status == SandboxStatus.TERMINATED:
            instance.stopped_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(instance)

        logger.debug(f"Updated sandbox {sandbox_id} status to {status.value}")
        return instance

    async def heartbeat(self, sandbox_id: UUID) -> bool:
        """Update updated_at timestamp as heartbeat"""
        result = await self.db.execute(
            update(SandboxInstance)
            .where(SandboxInstance.id == to_str(sandbox_id))
            .values(updated_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_sandbox_by_project(
        self,
        project_id: UUID,
        active_only: bool = True
    ) -> Optional[SandboxInstance]:
        """Get sandbox instance for a project"""
        query = select(SandboxInstance).where(
            SandboxInstance.project_id == to_str(project_id)
        )

        if active_only:
            query = query.where(
                SandboxInstance.status.in_([
                    SandboxStatus.PENDING,
                    SandboxStatus.CREATING,
                    SandboxStatus.RUNNING
                ])
            )

        query = query.order_by(SandboxInstance.created_at.desc()).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_sandbox(self, sandbox_id: UUID) -> Optional[SandboxInstance]:
        """Get sandbox instance by ID"""
        result = await self.db.execute(
            select(SandboxInstance).where(SandboxInstance.id == to_str(sandbox_id))
        )
        return result.scalar_one_or_none()

    async def list_active_sandboxes(self) -> List[SandboxInstance]:
        """List all active sandbox instances"""
        result = await self.db.execute(
            select(SandboxInstance)
            .where(SandboxInstance.status == SandboxStatus.RUNNING)
            .order_by(SandboxInstance.created_at.desc())
        )
        return list(result.scalars().all())

    # ========== Sandbox Logs Operations ==========

    async def add_log(
        self,
        sandbox_id: UUID,
        project_id: UUID,
        content: str,
        log_type: LogType = LogType.STDOUT,
        source: Optional[str] = None,
        command: Optional[str] = None
    ) -> SandboxLog:
        """Add a log entry for a sandbox"""
        log = SandboxLog(
            sandbox_id=to_str(sandbox_id),
            project_id=to_str(project_id),
            log_type=log_type.value if isinstance(log_type, LogType) else log_type,
            content=content,
            source=source,
            command=command,
            created_at=datetime.utcnow()
        )

        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        return log

    async def add_stdout(self, sandbox_id: UUID, project_id: UUID, content: str, source: Optional[str] = None) -> SandboxLog:
        """Add stdout log"""
        return await self.add_log(sandbox_id, project_id, content, LogType.STDOUT, source=source)

    async def add_stderr(self, sandbox_id: UUID, project_id: UUID, content: str, source: Optional[str] = None) -> SandboxLog:
        """Add stderr log"""
        return await self.add_log(sandbox_id, project_id, content, LogType.STDERR, source=source)

    async def add_build_log(self, sandbox_id: UUID, project_id: UUID, content: str, source: Optional[str] = None) -> SandboxLog:
        """Add build log"""
        return await self.add_log(sandbox_id, project_id, content, LogType.BUILD, source=source)

    async def get_logs(
        self,
        sandbox_id: UUID,
        log_type: Optional[LogType] = None,
        limit: int = 100
    ) -> List[SandboxLog]:
        """Get logs for a sandbox"""
        query = (
            select(SandboxLog)
            .where(SandboxLog.sandbox_id == to_str(sandbox_id))
            .order_by(SandboxLog.created_at.desc())
            .limit(limit)
        )

        if log_type:
            query = query.where(SandboxLog.log_type == log_type)

        result = await self.db.execute(query)
        return list(reversed(result.scalars().all()))  # Chronological order

    # ========== Terminal Session Operations ==========

    async def create_terminal_session(
        self,
        project_id: UUID,
        sandbox_id: Optional[UUID] = None,
        ws_session_id: Optional[str] = None,
        shell_type: str = "bash"
    ) -> TerminalSession:
        """Create a new terminal session"""
        session = TerminalSession(
            project_id=to_str(project_id),
            sandbox_id=to_str(sandbox_id),
            ws_session_id=ws_session_id,
            shell_type=shell_type,
            is_active=True,
            created_at=datetime.utcnow()
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.debug(f"Created terminal session {session.id} for project {project_id}")
        return session

    async def close_terminal_session(self, session_id: UUID) -> bool:
        """Close a terminal session"""
        result = await self.db.execute(
            update(TerminalSession)
            .where(TerminalSession.id == to_str(session_id))
            .values(is_active=False, closed_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_active_terminal_sessions(
        self,
        sandbox_id: UUID
    ) -> List[TerminalSession]:
        """Get active terminal sessions for a sandbox"""
        result = await self.db.execute(
            select(TerminalSession)
            .where(TerminalSession.sandbox_id == to_str(sandbox_id))
            .where(TerminalSession.is_active == True)
            .order_by(TerminalSession.created_at)
        )
        return list(result.scalars().all())

    async def get_terminal_session(self, session_id: UUID) -> Optional[TerminalSession]:
        """Get terminal session by ID"""
        result = await self.db.execute(
            select(TerminalSession).where(TerminalSession.id == to_str(session_id))
        )
        return result.scalar_one_or_none()

    # ========== Terminal History Operations ==========

    async def add_terminal_command(
        self,
        session_id: UUID,
        command: str,
        output: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> TerminalHistory:
        """Record a terminal command and its output"""
        history = TerminalHistory(
            session_id=to_str(session_id),
            command=command,
            output=output,
            exit_code=exit_code,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow() if output is not None else None
        )

        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)

        return history

    async def get_terminal_history(
        self,
        session_id: UUID,
        limit: int = 50
    ) -> List[TerminalHistory]:
        """Get command history for a terminal session"""
        result = await self.db.execute(
            select(TerminalHistory)
            .where(TerminalHistory.session_id == to_str(session_id))
            .order_by(TerminalHistory.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    # ========== Live Preview Session Operations ==========

    async def create_preview_session(
        self,
        project_id: UUID,
        sandbox_id: Optional[UUID] = None,
        local_port: Optional[int] = None,
        host_port: Optional[int] = None,
        public_url: Optional[str] = None,
        local_url: Optional[str] = None
    ) -> LivePreviewSession:
        """Create a live preview session record"""
        session = LivePreviewSession(
            project_id=to_str(project_id),
            sandbox_id=to_str(sandbox_id),
            local_port=local_port,
            host_port=host_port,
            public_url=public_url,
            local_url=local_url,
            is_active=True,
            created_at=datetime.utcnow()
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.debug(f"Created preview session for port {local_port}")
        return session

    async def update_preview_url(
        self,
        session_id: UUID,
        public_url: str,
        host_port: Optional[int] = None
    ) -> bool:
        """Update preview URL when available"""
        values = {"public_url": public_url, "updated_at": datetime.utcnow()}
        if host_port:
            values["host_port"] = host_port

        result = await self.db.execute(
            update(LivePreviewSession)
            .where(LivePreviewSession.id == to_str(session_id))
            .values(**values)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_active_preview(
        self,
        project_id: Optional[UUID] = None,
        sandbox_id: Optional[UUID] = None
    ) -> Optional[LivePreviewSession]:
        """Get active preview session for a project or sandbox"""
        query = select(LivePreviewSession).where(LivePreviewSession.is_active == True)

        if project_id:
            query = query.where(LivePreviewSession.project_id == to_str(project_id))
        if sandbox_id:
            query = query.where(LivePreviewSession.sandbox_id == to_str(sandbox_id))

        query = query.order_by(LivePreviewSession.created_at.desc()).limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def close_preview_session(self, session_id: UUID) -> bool:
        """Close a preview session"""
        result = await self.db.execute(
            update(LivePreviewSession)
            .where(LivePreviewSession.id == to_str(session_id))
            .values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0

    # ========== Cleanup Operations ==========

    async def cleanup_project_sandbox_data(self, project_id: UUID) -> Dict[str, int]:
        """Delete all sandbox data for a project"""
        # Get all sandbox instances for project
        result = await self.db.execute(
            select(SandboxInstance.id)
            .where(SandboxInstance.project_id == to_str(project_id))
        )
        sandbox_ids = [row[0] for row in result.fetchall()]

        deleted = {
            "sandbox_instances": 0,
            "sandbox_logs": 0,
            "terminal_sessions": 0,
            "terminal_history": 0,
            "preview_sessions": 0
        }

        for sandbox_id in sandbox_ids:
            # Get terminal sessions
            term_result = await self.db.execute(
                select(TerminalSession.id)
                .where(TerminalSession.sandbox_id == sandbox_id)
            )
            term_ids = [row[0] for row in term_result.fetchall()]

            # Delete terminal history
            for term_id in term_ids:
                result = await self.db.execute(
                    delete(TerminalHistory)
                    .where(TerminalHistory.session_id == term_id)
                )
                deleted["terminal_history"] += result.rowcount

            # Delete terminal sessions
            result = await self.db.execute(
                delete(TerminalSession)
                .where(TerminalSession.sandbox_id == sandbox_id)
            )
            deleted["terminal_sessions"] += result.rowcount

            # Delete logs
            result = await self.db.execute(
                delete(SandboxLog)
                .where(SandboxLog.sandbox_id == sandbox_id)
            )
            deleted["sandbox_logs"] += result.rowcount

            # Delete preview sessions
            result = await self.db.execute(
                delete(LivePreviewSession)
                .where(LivePreviewSession.sandbox_id == sandbox_id)
            )
            deleted["preview_sessions"] += result.rowcount

        # Delete sandbox instances
        result = await self.db.execute(
            delete(SandboxInstance)
            .where(SandboxInstance.project_id == to_str(project_id))
        )
        deleted["sandbox_instances"] = result.rowcount

        await self.db.commit()

        logger.info(f"Cleaned up sandbox data for project {project_id}: {deleted}")
        return deleted

    async def get_sandbox_stats(self) -> Dict[str, Any]:
        """Get sandbox statistics"""
        # Count by status
        result = await self.db.execute(
            select(SandboxInstance.status, func.count(SandboxInstance.id))
            .group_by(SandboxInstance.status)
        )
        status_counts = {row[0].value: row[1] for row in result.fetchall()}

        # Active terminals
        result = await self.db.execute(
            select(func.count(TerminalSession.id))
            .where(TerminalSession.is_active == True)
        )
        active_terminals = result.scalar() or 0

        # Active previews
        result = await self.db.execute(
            select(func.count(LivePreviewSession.id))
            .where(LivePreviewSession.is_active == True)
        )
        active_previews = result.scalar() or 0

        return {
            "sandbox_status_counts": status_counts,
            "active_terminals": active_terminals,
            "active_previews": active_previews
        }
