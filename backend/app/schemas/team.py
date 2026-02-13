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


# ==================== Extended Feature Enums ====================

class ActivityTypeEnum(str, Enum):
    TEAM_CREATED = "team_created"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MEMBER_REMOVED = "member_removed"
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_COMMENTED = "task_commented"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    CODE_MERGED = "code_merged"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_COMPLETED = "review_completed"
    MILESTONE_CREATED = "milestone_created"
    MILESTONE_COMPLETED = "milestone_completed"
    CHAT_MESSAGE = "chat_message"


class ReviewStatusEnum(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class NotificationTypeEnum(str, Enum):
    MENTION = "mention"
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE_SOON = "task_due_soon"
    TASK_OVERDUE = "task_overdue"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_COMPLETED = "review_completed"
    MILESTONE_DUE_SOON = "milestone_due_soon"
    INVITATION_RECEIVED = "invitation_received"
    MEMBER_JOINED = "member_joined"


class MilestoneStatusEnum(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ==================== Task Comments Schemas ====================

class CommentCreate(BaseModel):
    """Create a comment on a task"""
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[str] = Field(None, description="Parent comment ID for replies")


class CommentUpdate(BaseModel):
    """Update a comment"""
    content: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    """Comment response"""
    id: str
    task_id: str
    author_id: str
    parent_id: Optional[str] = None
    content: str
    mentions: Optional[List[str]] = None
    is_edited: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Author info
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    author_avatar: Optional[str] = None

    # Nested replies
    replies: List["CommentResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# ==================== Activity Feed Schemas ====================

class ActivityResponse(BaseModel):
    """Activity feed item"""
    id: str
    team_id: str
    actor_id: Optional[str] = None
    activity_type: ActivityTypeEnum
    description: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    # Actor info
    actor_name: Optional[str] = None
    actor_avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActivityListResponse(BaseModel):
    """Activity feed list"""
    activities: List[ActivityResponse]
    total: int
    has_more: bool = False


# ==================== Chat Message Schemas ====================

class ChatMessageCreate(BaseModel):
    """Create a chat message"""
    content: str = Field(..., min_length=1, max_length=2000)
    message_type: str = Field(default="text")


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    id: str
    team_id: str
    sender_id: Optional[str] = None
    content: str
    mentions: Optional[List[str]] = None
    message_type: str = "text"
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    is_edited: bool = False
    is_deleted: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Sender info
    sender_name: Optional[str] = None
    sender_avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    messages: List[ChatMessageResponse]
    total: int
    has_more: bool = False


# ==================== Code Review Schemas ====================

class CodeReviewCreate(BaseModel):
    """Create a code review request"""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    file_paths: List[str] = Field(..., min_length=1)
    reviewer_id: Optional[str] = Field(None, description="Specific reviewer to assign")
    task_id: Optional[str] = Field(None, description="Related task")


class CodeReviewUpdate(BaseModel):
    """Update a code review"""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    reviewer_id: Optional[str] = None
    status: Optional[ReviewStatusEnum] = None
    feedback: Optional[str] = None


class ReviewComment(BaseModel):
    """Inline comment on a file"""
    file_path: str
    line_number: int
    content: str


class CodeReviewResponse(BaseModel):
    """Code review response"""
    id: str
    team_id: str
    requester_id: str
    reviewer_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: ReviewStatusEnum
    file_paths: List[str]
    feedback: Optional[str] = None
    comments: Optional[List[ReviewComment]] = None
    task_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    # User info
    requester_name: Optional[str] = None
    reviewer_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CodeReviewListResponse(BaseModel):
    """Code review list"""
    reviews: List[CodeReviewResponse]
    total: int


# ==================== Time Tracking Schemas ====================

class TimeLogStart(BaseModel):
    """Start a time log"""
    description: Optional[str] = Field(None, max_length=500)


class TimeLogStop(BaseModel):
    """Stop a time log"""
    description: Optional[str] = Field(None, max_length=500)


class TimeLogResponse(BaseModel):
    """Time log response"""
    id: str
    task_id: str
    member_id: str
    description: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    is_running: bool = False
    created_at: datetime

    # Member info
    member_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TaskTimeStats(BaseModel):
    """Time stats for a task"""
    task_id: str
    total_minutes: int
    total_logs: int
    by_member: Dict[str, int] = {}  # member_id -> minutes


# ==================== Milestone Schemas ====================

class MilestoneCreate(BaseModel):
    """Create a milestone"""
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class MilestoneUpdate(BaseModel):
    """Update a milestone"""
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[MilestoneStatusEnum] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    order_index: Optional[int] = None


class MilestoneResponse(BaseModel):
    """Milestone response"""
    id: str
    team_id: str
    created_by: str
    title: str
    description: Optional[str] = None
    status: MilestoneStatusEnum
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0
    order_index: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Task counts
    total_tasks: int = 0
    completed_tasks: int = 0

    model_config = ConfigDict(from_attributes=True)


class MilestoneListResponse(BaseModel):
    """Milestone list"""
    milestones: List[MilestoneResponse]
    total: int


# ==================== Member Skills Schemas ====================

class SkillCreate(BaseModel):
    """Add a skill to a member"""
    skill_name: str = Field(..., min_length=1, max_length=100)
    proficiency_level: int = Field(default=3, ge=1, le=5)
    is_primary: bool = False


class SkillUpdate(BaseModel):
    """Update a skill"""
    proficiency_level: Optional[int] = Field(None, ge=1, le=5)
    is_primary: Optional[bool] = None


class SkillResponse(BaseModel):
    """Skill response"""
    id: str
    member_id: str
    skill_name: str
    proficiency_level: int
    is_primary: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberSkillsResponse(BaseModel):
    """Member with skills"""
    member_id: str
    user_name: Optional[str] = None
    skills: List[SkillResponse]


# ==================== Notification Schemas ====================

class NotificationResponse(BaseModel):
    """Notification response"""
    id: str
    user_id: str
    team_id: str
    actor_id: Optional[str] = None
    notification_type: NotificationTypeEnum
    title: str
    message: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime

    # Actor info
    actor_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Notification list"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class MarkNotificationsRead(BaseModel):
    """Mark notifications as read"""
    notification_ids: List[str] = Field(default=[], description="Specific IDs, or empty for all")


# ==================== Team Analytics Schemas ====================

class TeamAnalytics(BaseModel):
    """Team analytics/dashboard data"""
    team_id: str

    # Overview stats
    total_members: int
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    overdue_tasks: int

    # Time tracking
    total_hours_logged: float
    hours_this_week: float

    # Progress
    overall_progress: int  # 0-100

    # Milestones
    active_milestones: int
    completed_milestones: int

    # Member workload
    workload_distribution: List[Dict[str, Any]]  # [{member_id, name, task_count, hours}]

    # Recent activity
    recent_activities: List[ActivityResponse]

    # Task breakdown by status
    tasks_by_status: Dict[str, int]

    # Task breakdown by priority
    tasks_by_priority: Dict[str, int]


class MemberContribution(BaseModel):
    """Individual member contribution stats"""
    member_id: str
    user_name: str
    tasks_completed: int
    tasks_in_progress: int
    total_hours: float
    comments_made: int
    reviews_completed: int
    contribution_score: int  # Calculated score
