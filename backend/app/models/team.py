"""Team collaboration models for multi-user project work"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum
import secrets

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class TeamRole(str, enum.Enum):
    """Roles within a team"""
    LEADER = "leader"      # Full control: invite, remove, assign tasks, merge
    MEMBER = "member"      # Can edit assigned files, update tasks
    VIEWER = "viewer"      # Read-only access


class TeamStatus(str, enum.Enum):
    """Team status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISBANDED = "disbanded"


class InvitationStatus(str, enum.Enum):
    """Team invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskStatus(str, enum.Enum):
    """Team task status"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(str, enum.Enum):
    """Team task priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Team(Base):
    """Team model - links to a project for collaboration"""
    __tablename__ = "teams"

    __table_args__ = (
        Index('ix_teams_project_id', 'project_id'),
        Index('ix_teams_status', 'status'),
        Index('ix_teams_created_by', 'created_by'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_by = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TeamStatus), default=TeamStatus.ACTIVE, nullable=False)

    # Team settings
    max_members = Column(Integer, default=3, nullable=False)  # Max 3 members for student projects
    allow_member_invite = Column(Boolean, default=False)  # Only leader can invite by default

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="team")
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    tasks = relationship("TeamTask", back_populates="team", cascade="all, delete-orphan")
    invitations = relationship("TeamInvitation", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Team {self.name}>"


class TeamMember(Base):
    """Team member - links users to teams with roles"""
    __tablename__ = "team_members"

    __table_args__ = (
        Index('ix_team_members_team_id', 'team_id'),
        Index('ix_team_members_user_id', 'user_id'),
        Index('ix_team_members_team_user', 'team_id', 'user_id', unique=True),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    role = Column(SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Member workspace - isolated branch/folder for their work
    workspace_branch = Column(String(255), nullable=True)  # e.g., "member-<user_id>"

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")
    assigned_tasks = relationship("TeamTask", back_populates="assignee", foreign_keys="TeamTask.assignee_id")

    def __repr__(self):
        return f"<TeamMember {self.user_id} in {self.team_id}>"


class TeamTask(Base):
    """Team task - AI-split or manually created tasks"""
    __tablename__ = "team_tasks"

    __table_args__ = (
        Index('ix_team_tasks_team_id', 'team_id'),
        Index('ix_team_tasks_assignee_id', 'assignee_id'),
        Index('ix_team_tasks_status', 'status'),
        Index('ix_team_tasks_priority', 'priority'),
        Index('ix_team_tasks_team_status', 'team_id', 'status'),
        Index('ix_team_tasks_milestone_id', 'milestone_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    assignee_id = Column(GUID, ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True)
    milestone_id = Column(GUID, ForeignKey("team_milestones.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO, nullable=False)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)

    # Task details
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)
    order_index = Column(Integer, default=0)  # For ordering tasks

    # Associated files (which files this task involves)
    file_paths = Column(JSON, nullable=True)  # ["src/components/Header.tsx", "src/styles/header.css"]

    # AI-generated metadata
    ai_generated = Column(Boolean, default=False)
    ai_complexity_score = Column(Integer, nullable=True)  # 1-10 complexity
    ai_dependencies = Column(JSON, nullable=True)  # Task IDs this depends on

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)

    # Relationships
    team = relationship("Team", back_populates="tasks")
    assignee = relationship("TeamMember", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    milestone = relationship("TeamMilestone", backref="tasks")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<TeamTask {self.title}>"


def generate_invitation_token():
    """Generate a secure invitation token"""
    return secrets.token_urlsafe(32)


class TeamInvitation(Base):
    """Team invitation - pending invites with token and expiry"""
    __tablename__ = "team_invitations"

    __table_args__ = (
        Index('ix_team_invitations_team_id', 'team_id'),
        Index('ix_team_invitations_invitee_email', 'invitee_email'),
        Index('ix_team_invitations_invitee_id', 'invitee_id'),
        Index('ix_team_invitations_token', 'token', unique=True),
        Index('ix_team_invitations_status', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    inviter_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invitee_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # If existing user

    invitee_email = Column(String(255), nullable=False)
    token = Column(String(255), nullable=False, default=generate_invitation_token)
    role = Column(SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)

    # Message from inviter
    message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7), nullable=False)
    responded_at = Column(DateTime, nullable=True)

    # Relationships
    team = relationship("Team", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[inviter_id])
    invitee = relationship("User", foreign_keys=[invitee_id])

    def __repr__(self):
        return f"<TeamInvitation {self.invitee_email} to {self.team_id}>"

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# ==================== New Feature Models ====================

class ActivityType(str, enum.Enum):
    """Types of team activities"""
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


class ReviewStatus(str, enum.Enum):
    """Code review status"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class NotificationType(str, enum.Enum):
    """Notification types"""
    MENTION = "mention"
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE_SOON = "task_due_soon"
    TASK_OVERDUE = "task_overdue"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_COMPLETED = "review_completed"
    MILESTONE_DUE_SOON = "milestone_due_soon"
    INVITATION_RECEIVED = "invitation_received"
    MEMBER_JOINED = "member_joined"


class MilestoneStatus(str, enum.Enum):
    """Milestone status"""
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskComment(Base):
    """Comments on tasks for team discussions"""
    __tablename__ = "task_comments"

    __table_args__ = (
        Index('ix_task_comments_task_id', 'task_id'),
        Index('ix_task_comments_author_id', 'author_id'),
        Index('ix_task_comments_parent_id', 'parent_id'),
        Index('ix_task_comments_created_at', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    task_id = Column(GUID, ForeignKey("team_tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(GUID, ForeignKey("task_comments.id", ondelete="CASCADE"), nullable=True)  # For threading

    content = Column(Text, nullable=False)
    mentions = Column(JSON, nullable=True)  # ["user_id_1", "user_id_2"]
    is_edited = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    task = relationship("TeamTask", backref="comments")
    author = relationship("User", foreign_keys=[author_id])
    replies = relationship("TaskComment", backref="parent", remote_side=[id], cascade="all, delete-orphan", single_parent=True)

    def __repr__(self):
        return f"<TaskComment {self.id} on {self.task_id}>"


class TeamActivity(Base):
    """Activity feed for tracking team actions"""
    __tablename__ = "team_activities"

    __table_args__ = (
        Index('ix_team_activities_team_id', 'team_id'),
        Index('ix_team_activities_actor_id', 'actor_id'),
        Index('ix_team_activities_activity_type', 'activity_type'),
        Index('ix_team_activities_created_at', 'created_at'),
        Index('ix_team_activities_team_created', 'team_id', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    activity_type = Column(SQLEnum(ActivityType), nullable=False)
    description = Column(String(500), nullable=False)

    # Reference to related entities
    target_type = Column(String(50), nullable=True)  # "task", "member", "file", "milestone"
    target_id = Column(GUID, nullable=True)

    # Additional metadata
    metadata = Column(JSON, nullable=True)  # Flexible storage for activity details

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship("Team", backref="activities")
    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self):
        return f"<TeamActivity {self.activity_type.value} by {self.actor_id}>"


class TeamChatMessage(Base):
    """Persisted chat messages for team communication"""
    __tablename__ = "team_chat_messages"

    __table_args__ = (
        Index('ix_team_chat_messages_team_id', 'team_id'),
        Index('ix_team_chat_messages_sender_id', 'sender_id'),
        Index('ix_team_chat_messages_created_at', 'created_at'),
        Index('ix_team_chat_messages_team_created', 'team_id', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    content = Column(Text, nullable=False)
    mentions = Column(JSON, nullable=True)  # ["user_id_1", "user_id_2"]
    message_type = Column(String(20), default="text")  # "text", "file", "system"

    # For file attachments
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)

    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", backref="chat_messages")
    sender = relationship("User", foreign_keys=[sender_id])

    def __repr__(self):
        return f"<TeamChatMessage {self.id} in {self.team_id}>"


class CodeReview(Base):
    """Code review requests before merging"""
    __tablename__ = "code_reviews"

    __table_args__ = (
        Index('ix_code_reviews_team_id', 'team_id'),
        Index('ix_code_reviews_requester_id', 'requester_id'),
        Index('ix_code_reviews_reviewer_id', 'reviewer_id'),
        Index('ix_code_reviews_status', 'status'),
        Index('ix_code_reviews_created_at', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    requester_id = Column(GUID, ForeignKey("team_members.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(GUID, ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)

    # Files to review
    file_paths = Column(JSON, nullable=False)  # ["src/App.tsx", "src/utils.ts"]

    # Review feedback
    feedback = Column(Text, nullable=True)
    comments = Column(JSON, nullable=True)  # [{file_path, line, comment}, ...]

    # Related task (optional)
    task_id = Column(GUID, ForeignKey("team_tasks.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    team = relationship("Team", backref="code_reviews")
    requester = relationship("TeamMember", foreign_keys=[requester_id], backref="requested_reviews")
    reviewer = relationship("TeamMember", foreign_keys=[reviewer_id], backref="assigned_reviews")
    task = relationship("TeamTask", backref="code_reviews")

    def __repr__(self):
        return f"<CodeReview {self.title}>"


class TaskTimeLog(Base):
    """Time tracking logs for tasks"""
    __tablename__ = "task_time_logs"

    __table_args__ = (
        Index('ix_task_time_logs_task_id', 'task_id'),
        Index('ix_task_time_logs_member_id', 'member_id'),
        Index('ix_task_time_logs_started_at', 'started_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    task_id = Column(GUID, ForeignKey("team_tasks.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(GUID, ForeignKey("team_members.id", ondelete="CASCADE"), nullable=False)

    description = Column(String(500), nullable=True)  # What was worked on

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)  # Calculated when stopped

    is_running = Column(Boolean, default=True)  # True if timer is active

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    task = relationship("TeamTask", backref="time_logs")
    member = relationship("TeamMember", backref="time_logs")

    def __repr__(self):
        return f"<TaskTimeLog {self.id} for {self.task_id}>"

    def stop(self):
        """Stop the timer and calculate duration"""
        if self.is_running:
            self.ended_at = datetime.utcnow()
            self.is_running = False
            delta = self.ended_at - self.started_at
            self.duration_minutes = int(delta.total_seconds() / 60)


class TeamMilestone(Base):
    """Milestones/sprints for grouping tasks"""
    __tablename__ = "team_milestones"

    __table_args__ = (
        Index('ix_team_milestones_team_id', 'team_id'),
        Index('ix_team_milestones_status', 'status'),
        Index('ix_team_milestones_due_date', 'due_date'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(MilestoneStatus), default=MilestoneStatus.PLANNING, nullable=False)

    # Dates
    start_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Progress (calculated from tasks)
    progress = Column(Integer, default=0)  # 0-100

    # Order for display
    order_index = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", backref="milestones")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<TeamMilestone {self.title}>"


class MemberSkill(Base):
    """Skills associated with team members for AI task assignment"""
    __tablename__ = "member_skills"

    __table_args__ = (
        Index('ix_member_skills_member_id', 'member_id'),
        Index('ix_member_skills_skill_name', 'skill_name'),
        Index('ix_member_skills_member_skill', 'member_id', 'skill_name', unique=True),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    member_id = Column(GUID, ForeignKey("team_members.id", ondelete="CASCADE"), nullable=False)

    skill_name = Column(String(100), nullable=False)  # "React", "Python", "SQL", etc.
    proficiency_level = Column(Integer, default=3)  # 1-5 scale
    is_primary = Column(Boolean, default=False)  # Primary skills for this member

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    member = relationship("TeamMember", backref="skills")

    def __repr__(self):
        return f"<MemberSkill {self.skill_name} for {self.member_id}>"


class TeamNotification(Base):
    """Notifications for team members (mentions, deadlines, etc.)"""
    __tablename__ = "team_notifications"

    __table_args__ = (
        Index('ix_team_notifications_user_id', 'user_id'),
        Index('ix_team_notifications_team_id', 'team_id'),
        Index('ix_team_notifications_is_read', 'is_read'),
        Index('ix_team_notifications_created_at', 'created_at'),
        Index('ix_team_notifications_user_unread', 'user_id', 'is_read'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Who triggered it

    notification_type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)

    # Reference to related entity
    target_type = Column(String(50), nullable=True)  # "task", "comment", "review", "milestone"
    target_id = Column(GUID, nullable=True)

    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="team_notifications")
    team = relationship("Team", backref="notifications")
    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self):
        return f"<TeamNotification {self.notification_type.value} for {self.user_id}>"
