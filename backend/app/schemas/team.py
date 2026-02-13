"""Pydantic schemas for team collaboration"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums for validation
class TeamRoleEnum(str, Enum):
    LEADER = "leader"
    MEMBER = "member"
    VIEWER = "viewer"


class TeamStatusEnum(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISBANDED = "disbanded"


class InvitationStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskStatusEnum(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ==================== Team Schemas ====================

class TeamCreate(BaseModel):
    """Create a new team for a project"""
    project_id: str = Field(..., description="Project ID to create team for")
    name: str = Field(..., min_length=2, max_length=255, description="Team name")
    description: Optional[str] = Field(None, max_length=1000)
    max_members: int = Field(default=3, ge=2, le=10)
    allow_member_invite: bool = Field(default=False)


class TeamUpdate(BaseModel):
    """Update team settings"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    max_members: Optional[int] = Field(None, ge=2, le=10)
    allow_member_invite: Optional[bool] = None
    status: Optional[TeamStatusEnum] = None


class TeamMemberResponse(BaseModel):
    """Team member details"""
    id: str
    user_id: str
    role: TeamRoleEnum
    is_active: bool
    workspace_branch: Optional[str] = None
    joined_at: datetime
    last_active: Optional[datetime] = None

    # User info (populated from relationship)
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TeamResponse(BaseModel):
    """Team details response"""
    id: str
    project_id: str
    created_by: str
    name: str
    description: Optional[str] = None
    status: TeamStatusEnum
    max_members: int
    allow_member_invite: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Relationships
    members: List[TeamMemberResponse] = []
    member_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TeamListResponse(BaseModel):
    """List of teams response"""
    teams: List[TeamResponse]
    total: int


# ==================== Invitation Schemas ====================

class InvitationCreate(BaseModel):
    """Create a team invitation"""
    invitee_email: EmailStr = Field(..., description="Email of person to invite")
    role: TeamRoleEnum = Field(default=TeamRoleEnum.MEMBER)
    message: Optional[str] = Field(None, max_length=500, description="Personal message with invitation")


class InvitationAccept(BaseModel):
    """Accept a team invitation"""
    token: str = Field(..., min_length=10, description="Invitation token")


class InvitationDecline(BaseModel):
    """Decline a team invitation"""
    token: str = Field(..., min_length=10, description="Invitation token")


class InvitationResponse(BaseModel):
    """Invitation details response"""
    id: str
    team_id: str
    inviter_id: str
    invitee_id: Optional[str] = None
    invitee_email: str
    role: TeamRoleEnum
    status: InvitationStatusEnum
    message: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    responded_at: Optional[datetime] = None
    is_expired: bool = False

    # Team info
    team_name: Optional[str] = None
    project_title: Optional[str] = None

    # Inviter info
    inviter_name: Optional[str] = None
    inviter_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InvitationListResponse(BaseModel):
    """List of invitations"""
    invitations: List[InvitationResponse]
    total: int


# ==================== Task Schemas ====================

class TaskCreate(BaseModel):
    """Create a new team task"""
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    assignee_id: Optional[str] = Field(None, description="Team member ID to assign")
    priority: TaskPriorityEnum = Field(default=TaskPriorityEnum.MEDIUM)
    estimated_hours: Optional[int] = Field(None, ge=1, le=100)
    file_paths: Optional[List[str]] = Field(None, description="Files associated with this task")
    due_date: Optional[datetime] = None
    order_index: Optional[int] = Field(None, ge=0)


class TaskUpdate(BaseModel):
    """Update a team task"""
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    estimated_hours: Optional[int] = Field(None, ge=1, le=100)
    actual_hours: Optional[int] = Field(None, ge=0, le=200)
    file_paths: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    order_index: Optional[int] = Field(None, ge=0)


class TaskResponse(BaseModel):
    """Task details response"""
    id: str
    team_id: str
    assignee_id: Optional[str] = None
    created_by: str
    title: str
    description: Optional[str] = None
    status: TaskStatusEnum
    priority: TaskPriorityEnum
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    order_index: int = 0
    file_paths: Optional[List[str]] = None
    ai_generated: bool = False
    ai_complexity_score: Optional[int] = None
    ai_dependencies: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None

    # Assignee info
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """List of tasks with filters"""
    tasks: List[TaskResponse]
    total: int
    by_status: Dict[str, int] = {}  # Count per status
    by_assignee: Dict[str, int] = {}  # Count per assignee


# ==================== AI Task Split Schemas ====================

class TaskSplitRequest(BaseModel):
    """Request AI to split project into tasks"""
    balance_workload: bool = Field(default=True, description="Try to balance work across members")
    consider_skills: bool = Field(default=False, description="Consider member skills if available")
    max_tasks: int = Field(default=20, ge=3, le=50, description="Maximum number of tasks to create")
    include_file_mapping: bool = Field(default=True, description="Map files to tasks")


class SuggestedTask(BaseModel):
    """AI-suggested task"""
    title: str
    description: str
    priority: TaskPriorityEnum
    estimated_hours: int
    complexity_score: int = Field(ge=1, le=10)
    file_paths: List[str] = []
    dependencies: List[int] = []  # Indices of tasks this depends on
    suggested_assignee_index: Optional[int] = None  # Index into member list


class TaskSplitResponse(BaseModel):
    """AI task split response"""
    suggested_tasks: List[SuggestedTask]
    total_estimated_hours: int
    workload_distribution: Dict[str, int] = {}  # Member ID -> hours
    analysis_summary: str
    split_strategy: str


class ApplyTaskSplitRequest(BaseModel):
    """Apply AI-suggested task split"""
    suggested_tasks: List[SuggestedTask]
    member_assignments: Optional[Dict[int, str]] = Field(
        None,
        description="Map task index to member_id for assignment"
    )


# ==================== Code Merge Schemas ====================

class MergeRequest(BaseModel):
    """Request to merge member code into main project"""
    member_id: str = Field(..., description="Team member whose code to merge")
    file_paths: Optional[List[str]] = Field(
        None,
        description="Specific files to merge. If None, merge all changed files"
    )
    commit_message: Optional[str] = Field(None, max_length=500)


class FileConflict(BaseModel):
    """A conflict in a single file"""
    file_path: str
    conflict_type: str = Field(description="Type: 'content', 'deleted', 'renamed'")
    base_content: Optional[str] = None
    member_content: Optional[str] = None
    main_content: Optional[str] = None
    conflict_markers: Optional[str] = Field(
        None,
        description="Content with conflict markers for manual resolution"
    )


class MergeResponse(BaseModel):
    """Merge operation response"""
    success: bool
    merged_files: List[str] = []
    conflicts: List[FileConflict] = []
    auto_resolved: List[str] = []  # Files that had conflicts but were auto-resolved
    message: str


class ConflictResolution(BaseModel):
    """Resolution for a single file conflict"""
    file_path: str
    resolution: str = Field(
        ...,
        description="'keep_main', 'keep_member', 'merged_content'"
    )
    merged_content: Optional[str] = Field(
        None,
        description="Required if resolution is 'merged_content'"
    )


class MergeResolveRequest(BaseModel):
    """Resolve merge conflicts"""
    resolutions: List[ConflictResolution]


class MergeResolveResponse(BaseModel):
    """Conflict resolution response"""
    success: bool
    resolved_files: List[str]
    remaining_conflicts: List[str]
    message: str


# ==================== WebSocket Event Schemas ====================

class WebSocketEvent(BaseModel):
    """Base WebSocket event"""
    event_type: str
    team_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender_id: Optional[str] = None


class MemberPresenceEvent(WebSocketEvent):
    """Member joined/left event"""
    event_type: str = "presence"
    user_id: str
    user_name: str
    action: str  # "joined" or "left"


class TaskUpdatedEvent(WebSocketEvent):
    """Task was updated"""
    event_type: str = "task_updated"
    task_id: str
    changes: Dict[str, Any]


class FileChangedEvent(WebSocketEvent):
    """File was changed by a member"""
    event_type: str = "file_changed"
    file_path: str
    change_type: str  # "created", "modified", "deleted"
    changed_by: str


class ChatMessageEvent(WebSocketEvent):
    """Chat message in team"""
    event_type: str = "chat_message"
    message_id: str
    content: str
    sender_name: str
