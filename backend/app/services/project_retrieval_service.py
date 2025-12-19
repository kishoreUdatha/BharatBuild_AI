"""
Project Retrieval Service - Orchestrates complete project reconstruction
Like Bolt.new: Loads metadata, file tree, messages, plan, and prepares sandbox
"""

from typing import Optional, Dict, Any, List, Union
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.models.project_message import ProjectMessage
from app.models.project_tree import ProjectFileTree, ProjectPlan, AgentState
from app.models.sandbox import SandboxInstance, SandboxLog, TerminalSession, LivePreviewSession
from app.models.snapshot import Snapshot
from app.models.project_file import ProjectFile
from app.core.logging_config import logger
from app.services.storage_service import storage_service


def to_str(value: Union[UUID, str, None]) -> Optional[str]:
    """Convert UUID to string if needed"""
    if value is None:
        return None
    return str(value) if isinstance(value, UUID) else value


@dataclass
class ProjectMetadata:
    """Step 1: Basic project info"""
    id: str
    title: str
    description: Optional[str]
    status: str
    mode: str
    tech_stack: Optional[List[str]]
    framework: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    s3_path: Optional[str]


@dataclass
class FileTreeData:
    """Step 2: File tree structure"""
    tree_json: Dict[str, Any]
    files_index: Optional[List[Dict[str, Any]]]
    total_files: int
    total_folders: int
    total_size_bytes: int


@dataclass
class PlanData:
    """Step 3: Project plan"""
    plan_json: Dict[str, Any]
    version: str
    status: str


@dataclass
class ConversationHistory:
    """Step 4: Chat history"""
    messages: List[Dict[str, Any]]
    total_tokens: int


@dataclass
class AgentStateData:
    """Agent states for resumption"""
    states: Dict[str, Dict[str, Any]]  # {agent_type: state_json}


@dataclass
class SandboxState:
    """Step 8-10: Sandbox reconstruction info"""
    last_instance: Optional[Dict[str, Any]]
    terminal_history: List[Dict[str, Any]]
    preview_sessions: List[Dict[str, Any]]
    recent_logs: List[Dict[str, Any]]


@dataclass
class SnapshotData:
    """Step 7: Latest snapshot info"""
    snapshot_id: Optional[str]
    snapshot_name: Optional[str]
    created_at: Optional[datetime]
    file_count: int


@dataclass
class ProjectRetrievalResult:
    """Complete project retrieval result - everything needed to reconstruct UI"""
    metadata: ProjectMetadata
    file_tree: Optional[FileTreeData]
    plan: Optional[PlanData]
    conversation: ConversationHistory
    agent_states: AgentStateData
    sandbox: SandboxState
    latest_snapshot: Optional[SnapshotData]
    retrieval_time_ms: float


class ProjectRetrievalService:
    """
    Orchestrates complete project reconstruction like Bolt.new.

    Flow:
    1. Load project metadata (projects table)
    2. Load file tree (project_file_trees table)
    3. Load plan.json (project_plans table)
    4. Load conversation history (project_messages table)
    5. Load file metadata - NOT content (project_files table)
    6. Prepare sandbox reconstruction info (sandbox_instances, logs, terminal)
    7. Load latest snapshot info (snapshots table)

    File content is loaded on-demand via separate endpoint (lazy loading).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve_project(self, project_id: UUID) -> Optional[ProjectRetrievalResult]:
        """
        Complete project retrieval - returns everything needed for UI reconstruction.

        This is called when user clicks "Open Project" on dashboard.
        """
        start_time = datetime.utcnow()

        # Step 1: Load project metadata
        metadata = await self._load_metadata(project_id)
        if not metadata:
            logger.warning(f"Project {project_id} not found")
            return None

        # Step 2-7: Load all project data in parallel conceptually
        file_tree = await self._load_file_tree(project_id)
        plan = await self._load_plan(project_id)
        conversation = await self._load_conversation(project_id)
        agent_states = await self._load_agent_states(project_id)
        sandbox = await self._load_sandbox_state(project_id)
        snapshot = await self._load_latest_snapshot(project_id)

        # Calculate retrieval time
        end_time = datetime.utcnow()
        retrieval_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.info(f"Project {project_id} retrieved in {retrieval_time_ms:.2f}ms")

        return ProjectRetrievalResult(
            metadata=metadata,
            file_tree=file_tree,
            plan=plan,
            conversation=conversation,
            agent_states=agent_states,
            sandbox=sandbox,
            latest_snapshot=snapshot,
            retrieval_time_ms=retrieval_time_ms
        )

    # ========== Step 1: Load Project Metadata ==========

    async def _load_metadata(self, project_id: UUID) -> Optional[ProjectMetadata]:
        """Load basic project info from projects table"""
        result = await self.db.execute(
            select(Project).where(Project.id == to_str(project_id))
        )
        project = result.scalar_one_or_none()

        if not project:
            return None

        return ProjectMetadata(
            id=str(project.id),
            title=project.title,
            description=project.description,
            status=project.status.value if hasattr(project.status, 'value') else str(project.status),
            mode=project.mode.value if hasattr(project.mode, 'value') else str(project.mode),
            tech_stack=project.tech_stack,
            framework=project.framework,
            created_at=project.created_at,
            updated_at=project.updated_at,
            s3_path=project.s3_path
        )

    # ========== Step 2: Load File Tree ==========

    async def _load_file_tree(self, project_id: UUID) -> Optional[FileTreeData]:
        """Load file tree structure - enables instant file explorer rendering"""
        result = await self.db.execute(
            select(ProjectFileTree).where(ProjectFileTree.project_id == to_str(project_id))
        )
        tree = result.scalar_one_or_none()

        if not tree:
            # Fallback: Build tree from project_files if no cached tree exists
            return await self._build_tree_from_files(project_id)

        return FileTreeData(
            tree_json=tree.tree_json or {},
            files_index=tree.files_index,
            total_files=int(tree.total_files or 0),
            total_folders=int(tree.total_folders or 0),
            total_size_bytes=int(tree.total_size_bytes or 0)
        )

    async def _build_tree_from_files(self, project_id: UUID) -> Optional[FileTreeData]:
        """Build file tree from project_files table if no cached tree"""
        result = await self.db.execute(
            select(ProjectFile).where(ProjectFile.project_id == to_str(project_id))
        )
        files = result.scalars().all()

        if not files:
            return None

        # Build tree structure
        tree = {}
        files_index = []
        total_size = 0

        for f in files:
            path_parts = f.path.split('/')
            current = tree

            # Navigate/create folder structure
            for i, part in enumerate(path_parts[:-1]):
                if part not in current:
                    current[part] = {"_type": "folder"}
                current = current[part]

            # Add file
            filename = path_parts[-1]
            current[filename] = {
                "_type": "file",
                "size": f.size_bytes or 0,
                "language": f.language
            }

            files_index.append({
                "path": f.path,
                "size": f.size_bytes or 0,
                "language": f.language,
                "s3_key": f.s3_key
            })
            total_size += f.size_bytes or 0

        return FileTreeData(
            tree_json=tree,
            files_index=files_index,
            total_files=len(files),
            total_folders=self._count_folders(tree),
            total_size_bytes=total_size
        )

    def _count_folders(self, tree: dict) -> int:
        """Count folders in tree"""
        count = 0
        for key, value in tree.items():
            if isinstance(value, dict) and value.get("_type") == "folder":
                count += 1
                count += self._count_folders(value)
        return count

    # ========== Step 3: Load Plan ==========

    async def _load_plan(self, project_id: UUID) -> Optional[PlanData]:
        """Load project plan (plan.json)"""
        result = await self.db.execute(
            select(ProjectPlan).where(ProjectPlan.project_id == to_str(project_id))
        )
        plan = result.scalar_one_or_none()

        if not plan:
            return None

        return PlanData(
            plan_json=plan.plan_json or {},
            version=plan.version or "1.0",
            status=plan.status or "draft"
        )

    # ========== Step 4: Load Conversation ==========

    async def _load_conversation(self, project_id: UUID, limit: int = 100) -> ConversationHistory:
        """Load chat history between user and AI agents"""
        result = await self.db.execute(
            select(ProjectMessage)
            .where(ProjectMessage.project_id == to_str(project_id))
            .order_by(ProjectMessage.created_at)
            .limit(limit)
        )
        messages = result.scalars().all()

        total_tokens = 0
        message_list = []

        for msg in messages:
            message_list.append({
                "id": str(msg.id),
                "role": msg.role,
                "agent_type": msg.agent_type,
                "content": msg.content,
                "tokens_used": msg.tokens_used or 0,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
            total_tokens += msg.tokens_used or 0

        return ConversationHistory(
            messages=message_list,
            total_tokens=total_tokens
        )

    # ========== Step 5: Load Agent States ==========

    async def _load_agent_states(self, project_id: UUID) -> AgentStateData:
        """Load state of each agent for resumption"""
        result = await self.db.execute(
            select(AgentState).where(AgentState.project_id == to_str(project_id))
        )
        states = result.scalars().all()

        state_dict = {}
        for state in states:
            state_dict[state.agent_type] = {
                "status": state.status,
                "progress": int(state.progress or 0),
                "current_action": state.current_action,
                "state_json": state.state_json or {},
                "last_error": state.last_error,
                "updated_at": state.updated_at.isoformat() if state.updated_at else None
            }

        return AgentStateData(states=state_dict)

    # ========== Step 6-8: Load Sandbox State ==========

    async def _load_sandbox_state(self, project_id: UUID) -> SandboxState:
        """Load sandbox reconstruction info"""

        # Get last sandbox instance
        result = await self.db.execute(
            select(SandboxInstance)
            .where(SandboxInstance.project_id == to_str(project_id))
            .order_by(SandboxInstance.created_at.desc())
            .limit(1)
        )
        instance = result.scalar_one_or_none()

        last_instance = None
        terminal_history = []
        recent_logs = []
        preview_sessions = []

        if instance:
            last_instance = {
                "id": str(instance.id),
                "status": instance.status,
                "docker_container_id": instance.docker_container_id,
                "port_mappings": instance.port_mappings,
                "node_version": instance.node_version,
                "python_version": instance.python_version,
                "working_directory": instance.working_directory,
                "created_at": instance.created_at.isoformat() if instance.created_at else None
            }

            # Get terminal history
            terminal_result = await self.db.execute(
                select(TerminalSession)
                .where(TerminalSession.sandbox_id == to_str(instance.id))
                .order_by(TerminalSession.created_at.desc())
                .limit(5)
            )
            terminals = terminal_result.scalars().all()

            for t in terminals:
                terminal_history.append({
                    "id": str(t.id),
                    "shell_type": t.shell_type,
                    "is_active": t.is_active,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                })

            # Get recent logs
            log_result = await self.db.execute(
                select(SandboxLog)
                .where(SandboxLog.sandbox_id == to_str(instance.id))
                .order_by(SandboxLog.created_at.desc())
                .limit(50)
            )
            logs = log_result.scalars().all()

            for log in reversed(logs):  # Chronological order
                recent_logs.append({
                    "log_type": log.log_type,
                    "content": log.content,
                    "source": log.source,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                })

            # Get preview sessions
            preview_result = await self.db.execute(
                select(LivePreviewSession)
                .where(LivePreviewSession.sandbox_id == to_str(instance.id))
                .where(LivePreviewSession.is_active == True)
            )
            previews = preview_result.scalars().all()

            for p in previews:
                preview_sessions.append({
                    "id": str(p.id),
                    "local_port": p.local_port,
                    "host_port": p.host_port,
                    "public_url": p.public_url,
                    "local_url": p.local_url
                })

        return SandboxState(
            last_instance=last_instance,
            terminal_history=terminal_history,
            preview_sessions=preview_sessions,
            recent_logs=recent_logs
        )

    # ========== Step 7: Load Latest Snapshot ==========

    async def _load_latest_snapshot(self, project_id: UUID) -> Optional[SnapshotData]:
        """Load latest snapshot info for restore capability"""
        result = await self.db.execute(
            select(Snapshot)
            .where(Snapshot.project_id == to_str(project_id))
            .order_by(Snapshot.created_at.desc())
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            return None

        return SnapshotData(
            snapshot_id=str(snapshot.id),
            snapshot_name=snapshot.name,
            created_at=snapshot.created_at,
            file_count=snapshot.file_count or 0
        )

    # ========== File Content Lazy Loading ==========

    async def get_file_content(self, project_id: UUID, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Lazy load file content - called when user clicks a file.
        This fetches from S3 or local storage.
        """
        result = await self.db.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == to_str(project_id))
            .where(ProjectFile.path == file_path)
        )
        file = result.scalar_one_or_none()

        if not file:
            return None

        # Get content - prioritize S3, fallback to inline for legacy data
        content = None
        if file.s3_key:
            try:
                content_bytes = await storage_service.download_file(file.s3_key)
                content = content_bytes.decode('utf-8') if content_bytes else None
            except Exception:
                content = file.content_inline
        elif file.content_inline:
            content = file.content_inline

        return {
            "path": file.path,
            "content": content,
            "language": file.language,
            "size": file.size_bytes,
            "s3_key": file.s3_key,
            "updated_at": file.updated_at.isoformat() if file.updated_at else None
        }

    async def get_files_batch(self, project_id: UUID, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Batch load multiple file contents - for efficient loading.
        """
        results = []
        for path in file_paths:
            content = await self.get_file_content(project_id, path)
            if content:
                results.append(content)
        return results
