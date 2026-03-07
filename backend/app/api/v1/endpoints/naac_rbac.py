"""
NAAC RBAC API Endpoints
Provides role management, task management, approval workflows, and dashboards.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_current_admin
from app.models.user import User
from app.models.naac_rbac import (
    NAACRole,
    UserNAACRole,
    NAACPermission,
    RolePermission,
    NAACTask,
    NAACTaskComment,
    NAACApprovalWorkflow,
    NAACNotification,
    NAACRoleType,
    NAACPermissionType,
    ApprovalStatus,
    TaskStatus,
    TaskPriority,
    NotificationType,
)
from app.schemas.naac_rbac import (
    NAACRoleResponse,
    NAACRoleListResponse,
    UserNAACRoleAssign,
    UserNAACRoleUpdate,
    UserNAACRoleResponse,
    UserNAACRoleListResponse,
    UserWithRolesResponse,
    NAACTaskCreate,
    NAACTaskUpdate,
    NAACTaskResponse,
    NAACTaskListResponse,
    NAACTaskCommentCreate,
    NAACTaskCommentResponse,
    ApprovalSubmit,
    ApprovalAction,
    ApprovalWorkflowResponse,
    ApprovalWorkflowListResponse,
    PendingApprovalResponse,
    NAACNotificationResponse,
    NAACNotificationListResponse,
    NotificationMarkRead,
    NAACDashboardResponse,
    RoleDashboardResponse,
    TaskSummary,
    ApprovalSummary,
    CriterionProgress,
    PermissionCheckRequest,
    PermissionCheckResponse,
    AccessibleScopeResponse,
    BulkRoleAssign,
    BulkRoleAssignResponse,
    NAACRoleTypeEnum,
    TaskStatusEnum,
    TaskPriorityEnum,
)
from app.modules.naac.rbac_dependencies import (
    get_current_naac_roles,
    get_naac_permission_checker,
    NAACPermissionChecker,
    require_naac_permission,
    require_naac_role,
)
from app.services.naac_workflow_service import (
    WorkflowService,
    TaskService,
    NotificationService,
)
from app.core.types import generate_uuid

router = APIRouter(prefix="/naac/rbac", tags=["NAAC RBAC"])


# ==================== Role Management ====================

@router.get("/roles", response_model=NAACRoleListResponse)
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all NAAC roles"""
    result = await db.execute(
        select(NAACRole)
        .where(NAACRole.is_active == True)
        .order_by(NAACRole.hierarchy_level)
    )
    roles = result.scalars().all()

    return NAACRoleListResponse(
        roles=[NAACRoleResponse(
            id=str(r.id),
            role_type=NAACRoleTypeEnum(r.role_type.value),
            display_name=r.display_name,
            description=r.description,
            hierarchy_level=r.hierarchy_level,
            can_access_all_criteria=r.can_access_all_criteria,
            can_access_all_departments=r.can_access_all_departments,
            allowed_criteria=r.allowed_criteria,
            can_approve_level=r.can_approve_level,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at
        ) for r in roles],
        total=len(roles)
    )


@router.get("/my-roles", response_model=List[UserNAACRoleResponse])
async def get_my_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's NAAC roles"""
    user_roles = await get_current_naac_roles(db, current_user)

    return [_user_role_to_response(ur) for ur in user_roles]


@router.post("/assign-role", response_model=UserNAACRoleResponse)
async def assign_role(
    assignment: UserNAACRoleAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Assign a NAAC role to a user (admin only)"""
    # Get the role
    result = await db.execute(
        select(NAACRole).where(NAACRole.role_type == assignment.role_type.value)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role not found: {assignment.role_type}"
        )

    # Check if user exists
    result = await db.execute(
        select(User).where(User.id == assignment.user_id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check for duplicate
    result = await db.execute(
        select(UserNAACRole).where(
            UserNAACRole.user_id == assignment.user_id,
            UserNAACRole.role_id == str(role.id),
            UserNAACRole.criterion_number == assignment.criterion_number,
            UserNAACRole.department == assignment.department,
            UserNAACRole.is_active == True
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this role with same scope"
        )

    # Create assignment
    user_role = UserNAACRole(
        id=generate_uuid(),
        user_id=assignment.user_id,
        role_id=str(role.id),
        criterion_number=assignment.criterion_number,
        department=assignment.department,
        assigned_by=str(current_user.id),
        assigned_at=datetime.utcnow(),
        valid_from=assignment.valid_from or datetime.utcnow(),
        valid_until=assignment.valid_until,
        is_active=True,
        assignment_notes=assignment.assignment_notes
    )
    db.add(user_role)

    # Send notification
    notification_service = NotificationService(db)
    await notification_service.create_notification(
        user_id=assignment.user_id,
        notification_type=NotificationType.ROLE_ASSIGNED,
        title="NAAC Role Assigned",
        message=f"You have been assigned the role: {role.display_name}",
        action_url="/admin/accreditation"
    )

    await db.commit()

    # Refresh to get relationships
    await db.refresh(user_role)
    result = await db.execute(
        select(UserNAACRole)
        .options(selectinload(UserNAACRole.role))
        .where(UserNAACRole.id == str(user_role.id))
    )
    user_role = result.scalar_one()

    return _user_role_to_response(user_role)


@router.delete("/revoke-role/{assignment_id}")
async def revoke_role(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Revoke a NAAC role assignment (admin only)"""
    result = await db.execute(
        select(UserNAACRole)
        .options(selectinload(UserNAACRole.role))
        .where(UserNAACRole.id == assignment_id)
    )
    user_role = result.scalar_one_or_none()
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found"
        )

    user_role.is_active = False
    user_role.valid_until = datetime.utcnow()

    # Send notification
    notification_service = NotificationService(db)
    await notification_service.create_notification(
        user_id=str(user_role.user_id),
        notification_type=NotificationType.ROLE_REVOKED,
        title="NAAC Role Revoked",
        message=f"Your role has been revoked: {user_role.role.display_name}",
        action_url="/admin/accreditation"
    )

    await db.commit()

    return {"status": "success", "message": "Role revoked"}


@router.get("/users-with-roles", response_model=List[UserWithRolesResponse])
async def list_users_with_roles(
    role_type: Optional[str] = None,
    criterion: Optional[int] = None,
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """List users with their NAAC roles (admin only)"""
    # Get all active role assignments
    query = (
        select(UserNAACRole)
        .options(
            selectinload(UserNAACRole.role),
            selectinload(UserNAACRole.user)
        )
        .where(UserNAACRole.is_active == True)
    )

    if role_type:
        query = query.join(NAACRole).where(NAACRole.role_type == role_type)
    if criterion:
        query = query.where(UserNAACRole.criterion_number == criterion)
    if department:
        query = query.where(UserNAACRole.department == department)

    result = await db.execute(query)
    all_assignments = result.scalars().all()

    # Group by user
    users_dict = {}
    for ur in all_assignments:
        user_id = str(ur.user_id)
        if user_id not in users_dict:
            users_dict[user_id] = {
                'user': ur.user,
                'roles': []
            }
        users_dict[user_id]['roles'].append(ur)

    # Paginate
    users_list = list(users_dict.values())
    start = (page - 1) * page_size
    end = start + page_size
    paginated = users_list[start:end]

    return [
        UserWithRolesResponse(
            user_id=str(u['user'].id),
            email=u['user'].email,
            full_name=u['user'].full_name,
            department=u['user'].department,
            roles=[_user_role_to_response(ur) for ur in u['roles']]
        )
        for u in paginated
    ]


# ==================== Permission Check ====================

@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
):
    """Check if current user has a specific permission"""
    allowed = await checker.has_permission(
        request.resource,
        request.action.value,
        criterion=request.criterion_number,
        department=request.department
    )
    return PermissionCheckResponse(allowed=allowed)


@router.get("/accessible-scope", response_model=AccessibleScopeResponse)
async def get_accessible_scope(
    checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
):
    """Get user's accessible criteria and departments"""
    criteria = await checker.get_accessible_criteria()
    departments = await checker.get_accessible_departments()

    return AccessibleScopeResponse(
        criteria=criteria,
        departments=departments,
        can_access_all_criteria="*" in str(criteria) or len(criteria) == 7,
        can_access_all_departments="*" in departments
    )


# ==================== Task Management ====================

@router.post("/tasks", response_model=NAACTaskResponse)
async def create_task(
    task_data: NAACTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
):
    """Create a new task"""
    # Check permission
    if not await checker.has_permission("task", "create", criterion=task_data.criterion_number):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to create tasks"
        )

    task_service = TaskService(db)
    task = await task_service.create_task(
        creator=current_user,
        title=task_data.title,
        description=task_data.description,
        task_type=task_data.task_type,
        criterion_number=task_data.criterion_number,
        key_indicator=task_data.key_indicator,
        department=task_data.department,
        academic_year=task_data.academic_year,
        assigned_to=task_data.assigned_to,
        priority=TaskPriority(task_data.priority.value),
        due_date=task_data.due_date,
        related_record_type=task_data.related_record_type,
        related_record_id=task_data.related_record_id,
        attachments=task_data.attachments,
        extra_data=task_data.extra_data
    )

    await db.commit()
    await db.refresh(task)

    return await _task_to_response(db, task)


@router.get("/tasks", response_model=NAACTaskListResponse)
async def list_tasks(
    status_filter: Optional[str] = None,
    priority: Optional[str] = None,
    criterion: Optional[int] = None,
    department: Optional[str] = None,
    assigned_to_me: bool = False,
    created_by_me: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
):
    """List tasks with filters"""
    query = select(NAACTask)

    # Apply filters
    if status_filter:
        query = query.where(NAACTask.status == status_filter)
    if priority:
        query = query.where(NAACTask.priority == priority)
    if criterion:
        query = query.where(NAACTask.criterion_number == criterion)
    if department:
        query = query.where(NAACTask.department == department)
    if assigned_to_me:
        query = query.where(NAACTask.assigned_to == str(current_user.id))
    if created_by_me:
        query = query.where(NAACTask.created_by == str(current_user.id))

    # If not admin, filter by accessible scope
    if not current_user.is_superuser and current_user.role.value != 'admin':
        accessible_criteria = await checker.get_accessible_criteria()
        if accessible_criteria and len(accessible_criteria) < 7:
            query = query.where(
                or_(
                    NAACTask.criterion_number.in_(accessible_criteria),
                    NAACTask.criterion_number == None
                )
            )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Order and paginate
    query = query.order_by(NAACTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return NAACTaskListResponse(
        tasks=[await _task_to_response(db, t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/tasks/{task_id}", response_model=NAACTaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task details"""
    result = await db.execute(
        select(NAACTask).where(NAACTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return await _task_to_response(db, task)


@router.put("/tasks/{task_id}", response_model=NAACTaskResponse)
async def update_task(
    task_id: str,
    update_data: NAACTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
):
    """Update a task"""
    result = await db.execute(
        select(NAACTask).where(NAACTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check permission
    is_creator = task.created_by == str(current_user.id)
    is_assignee = task.assigned_to == str(current_user.id)
    has_edit_perm = await checker.has_permission("task", "edit", criterion=task.criterion_number)

    if not (is_creator or is_assignee or has_edit_perm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to update this task"
        )

    task_service = TaskService(db)
    updates = update_data.model_dump(exclude_unset=True)

    # Convert enums
    if 'status' in updates and updates['status']:
        updates['status'] = TaskStatus(updates['status'].value)
    if 'priority' in updates and updates['priority']:
        updates['priority'] = TaskPriority(updates['priority'].value)

    task = await task_service.update_task(task, current_user, **updates)

    await db.commit()
    await db.refresh(task)

    return await _task_to_response(db, task)


@router.post("/tasks/{task_id}/comments", response_model=NAACTaskCommentResponse)
async def add_task_comment(
    task_id: str,
    comment_data: NAACTaskCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a comment to a task"""
    result = await db.execute(
        select(NAACTask).where(NAACTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task_service = TaskService(db)
    comment = await task_service.add_comment(
        task=task,
        user=current_user,
        content=comment_data.content,
        attachments=comment_data.attachments
    )

    await db.commit()

    return NAACTaskCommentResponse(
        id=str(comment.id),
        task_id=str(comment.task_id),
        user_id=str(comment.user_id) if comment.user_id else None,
        user_name=current_user.full_name,
        user_email=current_user.email,
        content=comment.content,
        attachments=comment.attachments,
        is_system_comment=comment.is_system_comment,
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )


@router.get("/tasks/{task_id}/comments", response_model=List[NAACTaskCommentResponse])
async def get_task_comments(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comments for a task"""
    result = await db.execute(
        select(NAACTaskComment)
        .options(selectinload(NAACTaskComment.user))
        .where(NAACTaskComment.task_id == task_id)
        .order_by(NAACTaskComment.created_at)
    )
    comments = result.scalars().all()

    return [
        NAACTaskCommentResponse(
            id=str(c.id),
            task_id=str(c.task_id),
            user_id=str(c.user_id) if c.user_id else None,
            user_name=c.user.full_name if c.user else None,
            user_email=c.user.email if c.user else None,
            content=c.content,
            attachments=c.attachments,
            is_system_comment=c.is_system_comment,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in comments
    ]


# ==================== Approval Workflow ====================

@router.post("/approval/submit", response_model=ApprovalWorkflowResponse)
async def submit_for_approval(
    submission: ApprovalSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
):
    """Submit a record for approval"""
    # Check permission
    if not await checker.has_permission("approval", "submit", criterion=submission.criterion_number):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to submit for approval"
        )

    workflow_service = WorkflowService(db)
    workflow = await workflow_service.get_or_create_workflow(
        record_type=submission.record_type,
        record_id=submission.record_id,
        criterion=submission.criterion_number,
        academic_year=submission.academic_year,
        department=submission.department
    )

    workflow = await workflow_service.submit(
        workflow=workflow,
        submitter=current_user,
        remarks=submission.remarks
    )

    await db.commit()

    return await _workflow_to_response(db, workflow)


@router.post("/approval/{workflow_id}/action", response_model=ApprovalWorkflowResponse)
async def approval_action(
    workflow_id: str,
    action_data: ApprovalAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    checker: NAACPermissionChecker = Depends(get_naac_permission_checker)
):
    """Perform approval action (approve/reject/revision)"""
    result = await db.execute(
        select(NAACApprovalWorkflow).where(NAACApprovalWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    # Determine required approval level
    level_map = {
        ApprovalStatus.PENDING_DEPARTMENT: 'department',
        ApprovalStatus.PENDING_CRITERION: 'criterion',
        ApprovalStatus.PENDING_IQAC: 'iqac',
        ApprovalStatus.PENDING_HEAD: 'head'
    }
    required_level = level_map.get(workflow.status)
    if not required_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot perform approval action on status: {workflow.status.value}"
        )

    # Check permission
    if not checker.can_approve(required_level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot approve at {required_level} level"
        )

    workflow_service = WorkflowService(db)

    if action_data.action == 'approve':
        workflow = await workflow_service.approve(workflow, current_user, action_data.remarks)
    elif action_data.action == 'reject':
        if not action_data.remarks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required"
            )
        workflow = await workflow_service.reject(workflow, current_user, action_data.remarks)
    elif action_data.action == 'revision':
        if not action_data.remarks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Revision remarks are required"
            )
        workflow = await workflow_service.request_revision(workflow, current_user, action_data.remarks)

    await db.commit()

    return await _workflow_to_response(db, workflow)


@router.get("/approval/pending", response_model=PendingApprovalResponse)
async def get_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending approvals for current user"""
    user_roles = await get_current_naac_roles(db, current_user)

    workflow_service = WorkflowService(db)
    pending = await workflow_service.get_pending_approvals(str(current_user.id), user_roles)

    return PendingApprovalResponse(
        pending_department=[await _workflow_to_response(db, w) for w in pending['pending_department']],
        pending_criterion=[await _workflow_to_response(db, w) for w in pending['pending_criterion']],
        pending_iqac=[await _workflow_to_response(db, w) for w in pending['pending_iqac']],
        pending_head=[await _workflow_to_response(db, w) for w in pending['pending_head']],
        total_pending=sum(len(v) for v in pending.values())
    )


@router.get("/approval/{workflow_id}", response_model=ApprovalWorkflowResponse)
async def get_workflow_details(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get workflow details"""
    result = await db.execute(
        select(NAACApprovalWorkflow).where(NAACApprovalWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    return await _workflow_to_response(db, workflow)


# ==================== Notifications ====================

@router.get("/notifications", response_model=NAACNotificationListResponse)
async def get_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user notifications"""
    notification_service = NotificationService(db)
    notifications = await notification_service.get_user_notifications(
        str(current_user.id),
        unread_only=unread_only,
        limit=limit
    )
    unread_count = await notification_service.get_unread_count(str(current_user.id))

    return NAACNotificationListResponse(
        notifications=[_notification_to_response(n) for n in notifications],
        total=len(notifications),
        unread_count=unread_count
    )


@router.post("/notifications/mark-read")
async def mark_notifications_read(
    data: NotificationMarkRead,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark notifications as read"""
    notification_service = NotificationService(db)
    count = await notification_service.mark_as_read(str(current_user.id), data.notification_ids)
    await db.commit()
    return {"marked_read": count}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read"""
    notification_service = NotificationService(db)
    count = await notification_service.mark_all_as_read(str(current_user.id))
    await db.commit()
    return {"marked_read": count}


# ==================== Dashboard ====================

@router.get("/dashboard", response_model=NAACDashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get role-based dashboard data"""
    user_roles = await get_current_naac_roles(db, current_user)
    checker = NAACPermissionChecker(db, current_user, user_roles)

    # Get task summary
    task_service = TaskService(db)
    task_summary_data = await task_service.get_task_summary(user_id=str(current_user.id))
    task_summary = TaskSummary(**task_summary_data)

    # Get approval summary
    workflow_service = WorkflowService(db)
    pending_approvals = await workflow_service.get_pending_approvals(str(current_user.id), user_roles)

    approval_summary = ApprovalSummary(
        pending_department=len(pending_approvals['pending_department']),
        pending_criterion=len(pending_approvals['pending_criterion']),
        pending_iqac=len(pending_approvals['pending_iqac']),
        pending_head=len(pending_approvals['pending_head'])
    )

    # Get recent tasks
    result = await db.execute(
        select(NAACTask)
        .where(NAACTask.assigned_to == str(current_user.id))
        .order_by(NAACTask.created_at.desc())
        .limit(5)
    )
    recent_tasks = [await _task_to_response(db, t) for t in result.scalars().all()]

    # Get recent notifications
    notification_service = NotificationService(db)
    notifications = await notification_service.get_user_notifications(str(current_user.id), limit=10)
    unread_count = await notification_service.get_unread_count(str(current_user.id))

    # Get highest role
    highest_role = checker.get_highest_role()

    # Criteria progress (for IQAC/Head)
    criteria_progress = None
    if highest_role and highest_role.role.hierarchy_level <= 2:
        criteria_progress = await _get_criteria_progress(db)

    # Flatten pending approvals for response
    all_pending = []
    for level in ['pending_department', 'pending_criterion', 'pending_iqac', 'pending_head']:
        all_pending.extend(pending_approvals[level])

    return NAACDashboardResponse(
        user_id=str(current_user.id),
        user_name=current_user.full_name or current_user.email,
        roles=[_user_role_to_response(ur) for ur in user_roles],
        highest_role=highest_role.role.role_type.value if highest_role else None,
        task_summary=task_summary,
        approval_summary=approval_summary,
        recent_tasks=recent_tasks,
        pending_approvals=[await _workflow_to_response(db, w) for w in all_pending[:10]],
        recent_notifications=[_notification_to_response(n) for n in notifications],
        criteria_progress=criteria_progress,
        unread_notifications=unread_count,
        upcoming_deadlines=task_summary.pending + task_summary.in_progress
    )


# ==================== Helper Functions ====================

def _user_role_to_response(ur: UserNAACRole) -> UserNAACRoleResponse:
    """Convert UserNAACRole to response"""
    return UserNAACRoleResponse(
        id=str(ur.id),
        user_id=str(ur.user_id),
        role_id=str(ur.role_id),
        role_type=NAACRoleTypeEnum(ur.role.role_type.value),
        role_display_name=ur.role.display_name,
        criterion_number=ur.criterion_number,
        department=ur.department,
        assigned_by=str(ur.assigned_by) if ur.assigned_by else None,
        assigned_by_name=None,  # Would need to join
        assigned_at=ur.assigned_at,
        valid_from=ur.valid_from,
        valid_until=ur.valid_until,
        is_active=ur.is_active,
        assignment_notes=ur.assignment_notes,
        hierarchy_level=ur.role.hierarchy_level,
        can_access_all_criteria=ur.role.can_access_all_criteria,
        can_access_all_departments=ur.role.can_access_all_departments,
        allowed_criteria=ur.role.allowed_criteria,
        can_approve_level=ur.role.can_approve_level
    )


async def _task_to_response(db: AsyncSession, task: NAACTask) -> NAACTaskResponse:
    """Convert NAACTask to response"""
    # Get comment count
    result = await db.execute(
        select(func.count(NAACTaskComment.id))
        .where(NAACTaskComment.task_id == str(task.id))
    )
    comments_count = result.scalar() or 0

    # Check if overdue
    is_overdue = (
        task.due_date is not None and
        task.due_date < datetime.utcnow() and
        task.status not in [TaskStatus.COMPLETED, TaskStatus.OVERDUE]
    )

    # Get user names
    creator_name = None
    assignee_name = None
    if task.created_by:
        result = await db.execute(select(User).where(User.id == task.created_by))
        creator = result.scalar_one_or_none()
        if creator:
            creator_name = creator.full_name or creator.email
    if task.assigned_to:
        result = await db.execute(select(User).where(User.id == task.assigned_to))
        assignee = result.scalar_one_or_none()
        if assignee:
            assignee_name = assignee.full_name or assignee.email

    return NAACTaskResponse(
        id=str(task.id),
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        criterion_number=task.criterion_number,
        key_indicator=task.key_indicator,
        department=task.department,
        academic_year=task.academic_year,
        created_by=task.created_by,
        created_by_name=creator_name,
        assigned_to=task.assigned_to,
        assigned_to_name=assignee_name,
        assigned_by=task.assigned_by,
        assigned_at=task.assigned_at,
        status=TaskStatusEnum(task.status.value),
        priority=TaskPriorityEnum(task.priority.value),
        due_date=task.due_date,
        started_at=task.started_at,
        submitted_at=task.submitted_at,
        completed_at=task.completed_at,
        progress_percentage=task.progress_percentage,
        is_overdue=is_overdue,
        related_record_type=task.related_record_type,
        related_record_id=task.related_record_id,
        attachments=task.attachments,
        extra_data=task.extra_data,
        comments_count=comments_count,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


async def _workflow_to_response(db: AsyncSession, workflow: NAACApprovalWorkflow) -> ApprovalWorkflowResponse:
    """Convert NAACApprovalWorkflow to response"""
    # Get submitter name
    submitter_name = None
    if workflow.submitted_by:
        result = await db.execute(select(User).where(User.id == workflow.submitted_by))
        submitter = result.scalar_one_or_none()
        if submitter:
            submitter_name = submitter.full_name or submitter.email

    from app.schemas.naac_rbac import ApprovalStatusEnum
    return ApprovalWorkflowResponse(
        id=str(workflow.id),
        record_type=workflow.record_type,
        record_id=str(workflow.record_id),
        criterion_number=workflow.criterion_number,
        department=workflow.department,
        academic_year=workflow.academic_year,
        status=ApprovalStatusEnum(workflow.status.value),
        submitted_by=workflow.submitted_by,
        submitted_by_name=submitter_name,
        submitted_at=workflow.submitted_at,
        submission_remarks=workflow.submission_remarks,
        department_approved_by=workflow.department_approved_by,
        department_approved_at=workflow.department_approved_at,
        department_remarks=workflow.department_remarks,
        criterion_approved_by=workflow.criterion_approved_by,
        criterion_approved_at=workflow.criterion_approved_at,
        criterion_remarks=workflow.criterion_remarks,
        iqac_approved_by=workflow.iqac_approved_by,
        iqac_approved_at=workflow.iqac_approved_at,
        iqac_remarks=workflow.iqac_remarks,
        head_approved_by=workflow.head_approved_by,
        head_approved_at=workflow.head_approved_at,
        head_remarks=workflow.head_remarks,
        rejected_by=workflow.rejected_by,
        rejected_at=workflow.rejected_at,
        rejection_reason=workflow.rejection_reason,
        revision_requested_by=workflow.revision_requested_by,
        revision_requested_at=workflow.revision_requested_at,
        revision_remarks=workflow.revision_remarks,
        approval_history=workflow.approval_history,
        extra_data=workflow.extra_data,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at
    )


def _notification_to_response(notification: NAACNotification) -> NAACNotificationResponse:
    """Convert NAACNotification to response"""
    from app.schemas.naac_rbac import NotificationTypeEnum
    return NAACNotificationResponse(
        id=str(notification.id),
        notification_type=NotificationTypeEnum(notification.notification_type.value),
        title=notification.title,
        message=notification.message,
        related_entity_type=notification.related_entity_type,
        related_entity_id=str(notification.related_entity_id) if notification.related_entity_id else None,
        action_url=notification.action_url,
        is_read=notification.is_read,
        read_at=notification.read_at,
        is_important=notification.is_important,
        extra_data=notification.extra_data,
        created_at=notification.created_at,
        expires_at=notification.expires_at
    )


async def _get_criteria_progress(db: AsyncSession) -> List[CriterionProgress]:
    """Get progress for all 7 NAAC criteria"""
    criteria_names = {
        1: "Curricular Aspects",
        2: "Teaching-Learning",
        3: "Research & Extension",
        4: "Infrastructure",
        5: "Student Support",
        6: "Governance",
        7: "Institutional Values"
    }

    progress = []
    for i in range(1, 8):
        # Count tasks
        total_result = await db.execute(
            select(func.count(NAACTask.id))
            .where(NAACTask.criterion_number == i)
        )
        total_tasks = total_result.scalar() or 0

        completed_result = await db.execute(
            select(func.count(NAACTask.id))
            .where(
                NAACTask.criterion_number == i,
                NAACTask.status == TaskStatus.COMPLETED
            )
        )
        completed_tasks = completed_result.scalar() or 0

        # Count pending approvals
        pending_result = await db.execute(
            select(func.count(NAACApprovalWorkflow.id))
            .where(
                NAACApprovalWorkflow.criterion_number == i,
                NAACApprovalWorkflow.status.in_([
                    ApprovalStatus.PENDING_DEPARTMENT,
                    ApprovalStatus.PENDING_CRITERION,
                    ApprovalStatus.PENDING_IQAC,
                    ApprovalStatus.PENDING_HEAD
                ])
            )
        )
        pending_approvals = pending_result.scalar() or 0

        # Get coordinator
        coordinator_result = await db.execute(
            select(UserNAACRole)
            .options(selectinload(UserNAACRole.user), selectinload(UserNAACRole.role))
            .join(NAACRole)
            .where(
                NAACRole.role_type == NAACRoleType.CRITERION_COORDINATOR,
                UserNAACRole.criterion_number == i,
                UserNAACRole.is_active == True
            )
            .limit(1)
        )
        coordinator_role = coordinator_result.scalar_one_or_none()
        coordinator_name = None
        if coordinator_role and coordinator_role.user:
            coordinator_name = coordinator_role.user.full_name or coordinator_role.user.email

        progress.append(CriterionProgress(
            criterion_number=i,
            criterion_name=criteria_names[i],
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            progress_percentage=(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            pending_approvals=pending_approvals,
            coordinator_name=coordinator_name
        ))

    return progress
