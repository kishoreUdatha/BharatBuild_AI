"""
Project Retrieval API - Endpoints for loading saved projects
Like Bolt.new: Reconstructs workspace from stored metadata
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from dataclasses import asdict

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.services.project_retrieval_service import ProjectRetrievalService
from app.core.logging_config import logger


router = APIRouter(prefix="/retrieval", tags=["Project Retrieval"])


# ========== Response Models ==========

class ProjectMetadataResponse(BaseModel):
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


class FileTreeResponse(BaseModel):
    tree_json: dict
    files_index: Optional[List[dict]]
    total_files: int
    total_folders: int
    total_size_bytes: int


class PlanResponse(BaseModel):
    plan_json: dict
    version: str
    status: str


class MessageResponse(BaseModel):
    id: str
    role: str
    agent_type: Optional[str]
    content: str
    tokens_used: int
    created_at: Optional[str]


class ConversationResponse(BaseModel):
    messages: List[dict]
    total_tokens: int


class SandboxStateResponse(BaseModel):
    last_instance: Optional[dict]
    terminal_history: List[dict]
    preview_sessions: List[dict]
    recent_logs: List[dict]


class SnapshotResponse(BaseModel):
    snapshot_id: Optional[str]
    snapshot_name: Optional[str]
    created_at: Optional[datetime]
    file_count: int


class FullProjectResponse(BaseModel):
    """Complete project retrieval response - everything for UI reconstruction"""
    metadata: dict
    file_tree: Optional[dict]
    plan: Optional[dict]
    conversation: dict
    agent_states: dict
    sandbox: dict
    latest_snapshot: Optional[dict]
    retrieval_time_ms: float

    class Config:
        from_attributes = True


class FileContentResponse(BaseModel):
    path: str
    content: Optional[str]
    language: Optional[str]
    size: Optional[int]
    s3_key: Optional[str]
    updated_at: Optional[str]


# ========== API Endpoints ==========

@router.get("/{project_id}", response_model=FullProjectResponse)
async def retrieve_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **STEP 1-10: Complete project retrieval**

    Called when user clicks "Open Project" on dashboard.
    Returns all metadata needed to reconstruct the workspace UI.

    This loads:
    - Project metadata (name, status, tech stack)
    - File tree structure (instant file explorer)
    - Plan.json (generation plan)
    - Conversation history (user <-> AI messages)
    - Agent states (for resumption)
    - Sandbox reconstruction info
    - Latest snapshot info

    File content is NOT loaded here (lazy loading via /files endpoint).
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    service = ProjectRetrievalService(db)
    result = await service.retrieve_project(project_uuid)

    if not result:
        raise HTTPException(status_code=404, detail="Project not found")

    # Convert dataclasses to dicts
    return FullProjectResponse(
        metadata=asdict(result.metadata),
        file_tree=asdict(result.file_tree) if result.file_tree else None,
        plan=asdict(result.plan) if result.plan else None,
        conversation=asdict(result.conversation),
        agent_states=asdict(result.agent_states),
        sandbox=asdict(result.sandbox),
        latest_snapshot=asdict(result.latest_snapshot) if result.latest_snapshot else None,
        retrieval_time_ms=result.retrieval_time_ms
    )


@router.get("/{project_id}/file-tree", response_model=FileTreeResponse)
async def get_file_tree(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **STEP 2: Load file tree only**

    For incremental loading or file explorer refresh.
    Returns the complete directory structure as JSON.
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    service = ProjectRetrievalService(db)
    file_tree = await service._load_file_tree(project_uuid)

    if not file_tree:
        raise HTTPException(status_code=404, detail="File tree not found")

    return FileTreeResponse(
        tree_json=file_tree.tree_json,
        files_index=file_tree.files_index,
        total_files=file_tree.total_files,
        total_folders=file_tree.total_folders,
        total_size_bytes=file_tree.total_size_bytes
    )


@router.get("/{project_id}/conversation", response_model=ConversationResponse)
async def get_conversation(
    project_id: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **STEP 4: Load conversation history**

    Returns all messages between user and AI agents.
    Used for chat history panel.
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    service = ProjectRetrievalService(db)
    conversation = await service._load_conversation(project_uuid, limit=limit)

    return ConversationResponse(
        messages=conversation.messages,
        total_tokens=conversation.total_tokens
    )


@router.get("/{project_id}/files/{file_path:path}", response_model=FileContentResponse)
async def get_file_content(
    project_id: str,
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **STEP 5: Lazy load file content**

    Called when user clicks a file in the explorer.
    Returns the actual file content from S3/storage.

    This is the key to handling huge projects - we don't load
    all file contents upfront, only on demand.
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    service = ProjectRetrievalService(db)
    content = await service.get_file_content(project_uuid, file_path)

    if not content:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    return FileContentResponse(**content)


@router.post("/{project_id}/files/batch")
async def get_files_batch(
    project_id: str,
    file_paths: List[str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **Batch load multiple files**

    For efficient loading when opening multiple tabs.
    Returns content for all requested files.
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    if len(file_paths) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 files per batch")

    service = ProjectRetrievalService(db)
    files = await service.get_files_batch(project_uuid, file_paths)

    return {"files": files}


@router.get("/{project_id}/sandbox-state", response_model=SandboxStateResponse)
async def get_sandbox_state(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **STEP 8-10: Get sandbox reconstruction info**

    Returns info needed to recreate sandbox:
    - Last container configuration
    - Terminal history
    - Preview sessions
    - Recent logs
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    service = ProjectRetrievalService(db)
    sandbox = await service._load_sandbox_state(project_uuid)

    return SandboxStateResponse(
        last_instance=sandbox.last_instance,
        terminal_history=sandbox.terminal_history,
        preview_sessions=sandbox.preview_sessions,
        recent_logs=sandbox.recent_logs
    )


@router.get("/{project_id}/plan", response_model=PlanResponse)
async def get_project_plan(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **STEP 3: Load project plan**

    Returns the AI-generated project plan (plan.json).
    """
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    service = ProjectRetrievalService(db)
    plan = await service._load_plan(project_uuid)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return PlanResponse(
        plan_json=plan.plan_json,
        version=plan.version,
        status=plan.status
    )
