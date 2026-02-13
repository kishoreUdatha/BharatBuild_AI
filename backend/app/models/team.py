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
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    team_id = Column(GUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    assignee_id = Column(GUID, ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True)
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
