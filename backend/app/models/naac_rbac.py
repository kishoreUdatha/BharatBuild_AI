"""
NAAC Role-Based Access Control (RBAC) Models
Implements hierarchical roles, permissions, tasks, and approval workflows
for NAAC accreditation management.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey,
    Enum as SQLEnum, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== Enums ====================

class NAACRoleType(str, enum.Enum):
    """NAAC role types with hierarchy levels"""
    HEAD_OF_INSTITUTION = "head_of_institution"
    IQAC_COORDINATOR = "iqac_coordinator"
    CRITERION_COORDINATOR = "criterion_coordinator"
    DEPARTMENT_COORDINATOR = "department_coordinator"
    DOCUMENTATION_TEAM = "documentation_team"
    IT_DATA_ANALYTICS = "it_data_analytics"
    SSR_DRAFTING_COMMITTEE = "ssr_drafting_committee"
    STUDENT_REPRESENTATIVE = "student_representative"
    ADMINISTRATIVE_OFFICER = "administrative_officer"
    ALUMNI_COORDINATOR = "alumni_coordinator"
    PLACEMENT_OFFICER = "placement_officer"


class NAACPermissionType(str, enum.Enum):
    """Permission types for NAAC resources"""
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    APPROVE = "approve"
    SUBMIT = "submit"
    EXPORT = "export"
    ASSIGN = "assign"


class ApprovalStatus(str, enum.Enum):
    """Approval workflow statuses"""
    DRAFT = "draft"
    PENDING_DEPARTMENT = "pending_department"
    PENDING_CRITERION = "pending_criterion"
    PENDING_IQAC = "pending_iqac"
    PENDING_HEAD = "pending_head"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class TaskStatus(str, enum.Enum):
    """Task statuses"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class TaskPriority(str, enum.Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, enum.Enum):
    """Notification types"""
    TASK_ASSIGNED = "task_assigned"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_ACTION = "approval_action"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    DEADLINE_REMINDER = "deadline_reminder"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


# ==================== Models ====================

class NAACRole(Base):
    """
    NAAC role definitions with hierarchy and permissions.
    Seeded with 11 default roles during migration.
    """
    __tablename__ = "naac_roles"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    role_type = Column(SQLEnum(NAACRoleType), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    hierarchy_level = Column(Integer, nullable=False, default=5)  # 1 = highest (Head), 6 = lowest (Student)

    # Access scope defaults
    can_access_all_criteria = Column(Boolean, default=False)
    can_access_all_departments = Column(Boolean, default=False)
    allowed_criteria = Column(JSON, nullable=True)  # List of criterion numbers [1,2,3,...]

    # Approval capabilities
    can_approve_level = Column(Integer, nullable=True)  # 1=dept, 2=criterion, 3=iqac, 4=head

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_roles = relationship("UserNAACRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NAACRole {self.role_type.value}>"


class UserNAACRole(Base):
    """
    Many-to-many assignment of NAAC roles to users with scope.
    A user can have multiple roles (e.g., Criterion 1 Coordinator AND Documentation Team).
    """
    __tablename__ = "user_naac_roles"
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', 'criterion_number', 'department',
                        name='uq_user_role_scope'),
        Index('ix_user_naac_roles_user', 'user_id'),
        Index('ix_user_naac_roles_role', 'role_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(GUID, ForeignKey('naac_roles.id', ondelete='CASCADE'), nullable=False)

    # Scope restrictions (optional, depends on role type)
    criterion_number = Column(Integer, nullable=True)  # 1-7 for criterion-specific roles
    department = Column(String(100), nullable=True)  # Department code/name for dept-specific roles

    # Assignment metadata
    assigned_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)  # Optional expiry
    is_active = Column(Boolean, default=True)

    # Notes
    assignment_notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="naac_roles")
    role = relationship("NAACRole", back_populates="user_roles")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self):
        return f"<UserNAACRole user={self.user_id} role={self.role_id}>"


class NAACPermission(Base):
    """
    Permission definitions for NAAC resources.
    Combines resource (e.g., 'criterion1', 'evidence') with action (e.g., 'view', 'edit').
    """
    __tablename__ = "naac_permissions"
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_permission_resource_action'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    resource = Column(String(100), nullable=False, index=True)  # e.g., 'criterion1', 'evidence', 'task'
    action = Column(SQLEnum(NAACPermissionType), nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NAACPermission {self.resource}:{self.action.value}>"


class RolePermission(Base):
    """
    Maps roles to permissions.
    """
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    role_id = Column(GUID, ForeignKey('naac_roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(GUID, ForeignKey('naac_permissions.id', ondelete='CASCADE'), nullable=False)

    # Scope modifiers (optional)
    criterion_scope = Column(JSON, nullable=True)  # Restrict to specific criteria
    department_scope = Column(JSON, nullable=True)  # Restrict to specific departments

    # Relationships
    role = relationship("NAACRole", back_populates="role_permissions")
    permission = relationship("NAACPermission", back_populates="role_permissions")

    def __repr__(self):
        return f"<RolePermission role={self.role_id} permission={self.permission_id}>"


class NAACTask(Base):
    """
    Task assignment and tracking for NAAC preparation work.
    """
    __tablename__ = "naac_tasks"
    __table_args__ = (
        Index('ix_naac_tasks_assignee', 'assigned_to'),
        Index('ix_naac_tasks_status', 'status'),
        Index('ix_naac_tasks_criterion', 'criterion_number'),
        Index('ix_naac_tasks_due', 'due_date'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Task details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=True)  # e.g., 'data_entry', 'evidence_upload', 'review'

    # Scope
    criterion_number = Column(Integer, nullable=True)  # 1-7
    key_indicator = Column(String(20), nullable=True)  # e.g., '1.1.1', '2.3.2'
    department = Column(String(100), nullable=True)
    academic_year = Column(String(20), nullable=True)  # e.g., '2024-25'

    # Assignment
    created_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    assigned_to = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    assigned_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    # Status and priority
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)

    # Dates
    due_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Progress
    progress_percentage = Column(Integer, default=0)  # 0-100

    # Related records
    related_record_type = Column(String(50), nullable=True)  # e.g., 'evidence', 'feedback'
    related_record_id = Column(GUID, nullable=True)

    # Attachments and extra data
    attachments = Column(JSON, nullable=True)  # List of file URLs
    extra_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="created_naac_tasks")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_naac_tasks")
    assigner = relationship("User", foreign_keys=[assigned_by])
    comments = relationship("NAACTaskComment", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NAACTask {self.title[:30]}>"


class NAACTaskComment(Base):
    """
    Comments on NAAC tasks for collaboration.
    """
    __tablename__ = "naac_task_comments"
    __table_args__ = (
        Index('ix_naac_task_comments_task', 'task_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    task_id = Column(GUID, ForeignKey('naac_tasks.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    content = Column(Text, nullable=False)
    attachments = Column(JSON, nullable=True)  # List of file URLs

    # Comment type
    is_system_comment = Column(Boolean, default=False)  # Auto-generated status changes

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    task = relationship("NAACTask", back_populates="comments")
    user = relationship("User", backref="naac_task_comments")

    def __repr__(self):
        return f"<NAACTaskComment task={self.task_id}>"


class NAACApprovalWorkflow(Base):
    """
    Approval workflow state machine for NAAC records.
    Tracks the approval journey from draft to final approval.
    """
    __tablename__ = "naac_approval_workflows"
    __table_args__ = (
        Index('ix_naac_approvals_record', 'record_type', 'record_id'),
        Index('ix_naac_approvals_status', 'status'),
        Index('ix_naac_approvals_criterion', 'criterion_number'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Record reference
    record_type = Column(String(100), nullable=False)  # e.g., 'evidence', 'feedback', 'report'
    record_id = Column(GUID, nullable=False)

    # Scope
    criterion_number = Column(Integer, nullable=True)
    department = Column(String(100), nullable=True)
    academic_year = Column(String(20), nullable=True)

    # Current status
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.DRAFT, nullable=False)

    # Submitter info
    submitted_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    submission_remarks = Column(Text, nullable=True)

    # Approval chain tracking
    department_approved_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    department_approved_at = Column(DateTime, nullable=True)
    department_remarks = Column(Text, nullable=True)

    criterion_approved_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    criterion_approved_at = Column(DateTime, nullable=True)
    criterion_remarks = Column(Text, nullable=True)

    iqac_approved_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    iqac_approved_at = Column(DateTime, nullable=True)
    iqac_remarks = Column(Text, nullable=True)

    head_approved_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    head_approved_at = Column(DateTime, nullable=True)
    head_remarks = Column(Text, nullable=True)

    # Rejection/Revision info
    rejected_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    revision_requested_by = Column(GUID, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    revision_requested_at = Column(DateTime, nullable=True)
    revision_remarks = Column(Text, nullable=True)

    # History
    approval_history = Column(JSON, nullable=True)  # List of {action, user_id, timestamp, remarks}

    # Extra data
    extra_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submitter = relationship("User", foreign_keys=[submitted_by])
    dept_approver = relationship("User", foreign_keys=[department_approved_by])
    criterion_approver = relationship("User", foreign_keys=[criterion_approved_by])
    iqac_approver = relationship("User", foreign_keys=[iqac_approved_by])
    head_approver = relationship("User", foreign_keys=[head_approved_by])
    rejector = relationship("User", foreign_keys=[rejected_by])
    revision_requester = relationship("User", foreign_keys=[revision_requested_by])

    def __repr__(self):
        return f"<NAACApprovalWorkflow {self.record_type}:{self.record_id} status={self.status.value}>"


class NAACNotification(Base):
    """
    User notifications for NAAC activities.
    """
    __tablename__ = "naac_notifications"
    __table_args__ = (
        Index('ix_naac_notifications_user', 'user_id'),
        Index('ix_naac_notifications_read', 'is_read'),
        Index('ix_naac_notifications_created', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Notification content
    notification_type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Related entity
    related_entity_type = Column(String(50), nullable=True)  # 'task', 'approval', 'role'
    related_entity_id = Column(GUID, nullable=True)

    # Action URL
    action_url = Column(String(500), nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    # Priority for sorting
    is_important = Column(Boolean, default=False)

    # Extra data
    extra_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="naac_notifications")

    def __repr__(self):
        return f"<NAACNotification {self.notification_type.value} for user={self.user_id}>"
