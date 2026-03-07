"""
Pydantic schemas for NAAC RBAC system.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Enums for API ====================

class NAACRoleTypeEnum(str, Enum):
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


class NAACPermissionTypeEnum(str, Enum):
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    APPROVE = "approve"
    SUBMIT = "submit"
    EXPORT = "export"
    ASSIGN = "assign"


class ApprovalStatusEnum(str, Enum):
    DRAFT = "draft"
    PENDING_DEPARTMENT = "pending_department"
    PENDING_CRITERION = "pending_criterion"
    PENDING_IQAC = "pending_iqac"
    PENDING_HEAD = "pending_head"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class TaskPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationTypeEnum(str, Enum):
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


# ==================== Role Schemas ====================

class NAACRoleBase(BaseModel):
    role_type: NAACRoleTypeEnum
    display_name: str
    description: Optional[str] = None
    hierarchy_level: int = 5
    can_access_all_criteria: bool = False
    can_access_all_departments: bool = False
    allowed_criteria: Optional[List[int]] = None
    can_approve_level: Optional[int] = None


class NAACRoleResponse(NAACRoleBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NAACRoleListResponse(BaseModel):
    roles: List[NAACRoleResponse]
    total: int


# ==================== User Role Assignment Schemas ====================

class UserNAACRoleAssign(BaseModel):
    """Schema for assigning a role to a user"""
    user_id: str
    role_type: NAACRoleTypeEnum
    criterion_number: Optional[int] = Field(None, ge=1, le=7)
    department: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    assignment_notes: Optional[str] = None


class UserNAACRoleUpdate(BaseModel):
    """Schema for updating a user role assignment"""
    criterion_number: Optional[int] = Field(None, ge=1, le=7)
    department: Optional[str] = None
    valid_until: Optional[datetime] = None
    assignment_notes: Optional[str] = None
    is_active: Optional[bool] = None


class UserNAACRoleResponse(BaseModel):
    id: str
    user_id: str
    role_id: str
    role_type: NAACRoleTypeEnum
    role_display_name: str
    criterion_number: Optional[int] = None
    department: Optional[str] = None
    assigned_by: Optional[str] = None
    assigned_by_name: Optional[str] = None
    assigned_at: datetime
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_active: bool
    assignment_notes: Optional[str] = None

    # Role capabilities
    hierarchy_level: int
    can_access_all_criteria: bool
    can_access_all_departments: bool
    allowed_criteria: Optional[List[int]] = None
    can_approve_level: Optional[int] = None

    class Config:
        from_attributes = True


class UserWithRolesResponse(BaseModel):
    """User info with their NAAC roles"""
    user_id: str
    email: str
    full_name: Optional[str] = None
    department: Optional[str] = None
    roles: List[UserNAACRoleResponse]


class UserNAACRoleListResponse(BaseModel):
    assignments: List[UserNAACRoleResponse]
    total: int


# ==================== Task Schemas ====================

class NAACTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: Optional[str] = None

    criterion_number: Optional[int] = Field(None, ge=1, le=7)
    key_indicator: Optional[str] = None
    department: Optional[str] = None
    academic_year: Optional[str] = None

    assigned_to: Optional[str] = None
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM
    due_date: Optional[datetime] = None

    related_record_type: Optional[str] = None
    related_record_id: Optional[str] = None
    attachments: Optional[List[str]] = None
    extra_data: Optional[Dict[str, Any]] = None


class NAACTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: Optional[str] = None

    assigned_to: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    due_date: Optional[datetime] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)

    attachments: Optional[List[str]] = None
    extra_data: Optional[Dict[str, Any]] = None


class NAACTaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    task_type: Optional[str] = None

    criterion_number: Optional[int] = None
    key_indicator: Optional[str] = None
    department: Optional[str] = None
    academic_year: Optional[str] = None

    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_by: Optional[str] = None
    assigned_at: Optional[datetime] = None

    status: TaskStatusEnum
    priority: TaskPriorityEnum
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    progress_percentage: int = 0
    is_overdue: bool = False

    related_record_type: Optional[str] = None
    related_record_id: Optional[str] = None
    attachments: Optional[List[str]] = None
    extra_data: Optional[Dict[str, Any]] = None

    comments_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NAACTaskListResponse(BaseModel):
    tasks: List[NAACTaskResponse]
    total: int
    page: int
    page_size: int


# ==================== Task Comment Schemas ====================

class NAACTaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    attachments: Optional[List[str]] = None


class NAACTaskCommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    content: str
    attachments: Optional[List[str]] = None
    is_system_comment: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Approval Workflow Schemas ====================

class ApprovalSubmit(BaseModel):
    """Submit a record for approval"""
    record_type: str
    record_id: str
    criterion_number: Optional[int] = Field(None, ge=1, le=7)
    department: Optional[str] = None
    academic_year: Optional[str] = None
    remarks: Optional[str] = None


class ApprovalAction(BaseModel):
    """Approve, reject, or request revision"""
    action: str = Field(..., pattern="^(approve|reject|revision)$")
    remarks: Optional[str] = None


class ApprovalWorkflowResponse(BaseModel):
    id: str
    record_type: str
    record_id: str
    criterion_number: Optional[int] = None
    department: Optional[str] = None
    academic_year: Optional[str] = None

    status: ApprovalStatusEnum

    submitted_by: Optional[str] = None
    submitted_by_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submission_remarks: Optional[str] = None

    department_approved_by: Optional[str] = None
    department_approved_at: Optional[datetime] = None
    department_remarks: Optional[str] = None

    criterion_approved_by: Optional[str] = None
    criterion_approved_at: Optional[datetime] = None
    criterion_remarks: Optional[str] = None

    iqac_approved_by: Optional[str] = None
    iqac_approved_at: Optional[datetime] = None
    iqac_remarks: Optional[str] = None

    head_approved_by: Optional[str] = None
    head_approved_at: Optional[datetime] = None
    head_remarks: Optional[str] = None

    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    revision_requested_by: Optional[str] = None
    revision_requested_at: Optional[datetime] = None
    revision_remarks: Optional[str] = None

    approval_history: Optional[List[Dict[str, Any]]] = None
    extra_data: Optional[Dict[str, Any]] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalWorkflowListResponse(BaseModel):
    workflows: List[ApprovalWorkflowResponse]
    total: int
    page: int
    page_size: int


class PendingApprovalResponse(BaseModel):
    """Pending approvals grouped by level"""
    pending_department: List[ApprovalWorkflowResponse]
    pending_criterion: List[ApprovalWorkflowResponse]
    pending_iqac: List[ApprovalWorkflowResponse]
    pending_head: List[ApprovalWorkflowResponse]
    total_pending: int


# ==================== Notification Schemas ====================

class NAACNotificationResponse(BaseModel):
    id: str
    notification_type: NotificationTypeEnum
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    action_url: Optional[str] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    is_important: bool = False
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NAACNotificationListResponse(BaseModel):
    notifications: List[NAACNotificationResponse]
    total: int
    unread_count: int


class NotificationMarkRead(BaseModel):
    notification_ids: List[str]


# ==================== Dashboard Schemas ====================

class TaskSummary(BaseModel):
    pending: int = 0
    assigned: int = 0
    in_progress: int = 0
    submitted: int = 0
    completed: int = 0
    overdue: int = 0


class ApprovalSummary(BaseModel):
    pending_department: int = 0
    pending_criterion: int = 0
    pending_iqac: int = 0
    pending_head: int = 0
    approved: int = 0
    rejected: int = 0
    revision_requested: int = 0


class CriterionProgress(BaseModel):
    criterion_number: int
    criterion_name: str
    total_tasks: int = 0
    completed_tasks: int = 0
    progress_percentage: float = 0.0
    pending_approvals: int = 0
    coordinator_name: Optional[str] = None


class NAACDashboardResponse(BaseModel):
    """Role-based dashboard data"""
    user_id: str
    user_name: str
    roles: List[UserNAACRoleResponse]
    highest_role: Optional[str] = None

    # Summary stats
    task_summary: TaskSummary
    approval_summary: ApprovalSummary

    # Recent items
    recent_tasks: List[NAACTaskResponse]
    pending_approvals: List[ApprovalWorkflowResponse]
    recent_notifications: List[NAACNotificationResponse]

    # Criteria progress (for IQAC/Head)
    criteria_progress: Optional[List[CriterionProgress]] = None

    # Quick stats
    unread_notifications: int = 0
    upcoming_deadlines: int = 0


class RoleDashboardResponse(BaseModel):
    """Specific role dashboard data"""
    role_type: NAACRoleTypeEnum
    role_display_name: str

    # Accessible scope
    accessible_criteria: List[int]
    accessible_departments: List[str]

    # Role-specific stats
    my_tasks: TaskSummary
    my_approvals: ApprovalSummary

    # Team stats (for coordinators)
    team_tasks: Optional[TaskSummary] = None
    team_members: Optional[List[UserWithRolesResponse]] = None

    # Recent activity
    recent_activity: List[Dict[str, Any]]


# ==================== Permission Check Schemas ====================

class PermissionCheckRequest(BaseModel):
    resource: str
    action: NAACPermissionTypeEnum
    criterion_number: Optional[int] = None
    department: Optional[str] = None


class PermissionCheckResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None


class AccessibleScopeResponse(BaseModel):
    criteria: List[int]
    departments: List[str]
    can_access_all_criteria: bool
    can_access_all_departments: bool


# ==================== Bulk Operations ====================

class BulkRoleAssign(BaseModel):
    """Assign roles to multiple users"""
    assignments: List[UserNAACRoleAssign]


class BulkTaskAssign(BaseModel):
    """Assign tasks to multiple users"""
    task_ids: List[str]
    assigned_to: str
    notify: bool = True


class BulkRoleAssignResponse(BaseModel):
    successful: int
    failed: int
    errors: List[Dict[str, str]]
