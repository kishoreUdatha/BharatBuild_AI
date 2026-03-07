"""
NAAC Workflow Service
Handles approval workflows, task management, and notifications for NAAC accreditation.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.models.naac_rbac import (
    NAACApprovalWorkflow,
    NAACTask,
    NAACTaskComment,
    NAACNotification,
    UserNAACRole,
    NAACRole,
    ApprovalStatus,
    TaskStatus,
    TaskPriority,
    NotificationType,
    NAACRoleType,
)
from app.models.user import User
from app.core.types import generate_uuid


class WorkflowService:
    """Service for managing NAAC approval workflows"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workflow(
        self,
        record_type: str,
        record_id: str,
        criterion: Optional[int] = None,
        academic_year: Optional[str] = None,
        department: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> NAACApprovalWorkflow:
        """
        Create a new approval workflow for a record.
        """
        workflow = NAACApprovalWorkflow(
            id=generate_uuid(),
            record_type=record_type,
            record_id=record_id,
            criterion_number=criterion,
            academic_year=academic_year,
            department=department,
            status=ApprovalStatus.DRAFT,
            approval_history=[],
            extra_data=extra_data
        )
        self.db.add(workflow)
        await self.db.flush()
        return workflow

    async def get_workflow(
        self,
        record_type: str,
        record_id: str
    ) -> Optional[NAACApprovalWorkflow]:
        """Get existing workflow for a record"""
        result = await self.db.execute(
            select(NAACApprovalWorkflow)
            .where(
                NAACApprovalWorkflow.record_type == record_type,
                NAACApprovalWorkflow.record_id == record_id
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_workflow(
        self,
        record_type: str,
        record_id: str,
        criterion: Optional[int] = None,
        academic_year: Optional[str] = None,
        department: Optional[str] = None
    ) -> NAACApprovalWorkflow:
        """Get existing workflow or create new one"""
        workflow = await self.get_workflow(record_type, record_id)
        if workflow:
            return workflow
        return await self.create_workflow(
            record_type, record_id, criterion, academic_year, department
        )

    async def submit(
        self,
        workflow: NAACApprovalWorkflow,
        submitter: User,
        remarks: Optional[str] = None
    ) -> NAACApprovalWorkflow:
        """
        Submit record for approval.
        Determines next approval level based on user roles and workflow state.
        """
        if workflow.status not in [
            ApprovalStatus.DRAFT,
            ApprovalStatus.REVISION_REQUESTED,
            ApprovalStatus.REJECTED
        ]:
            raise ValueError(f"Cannot submit from status: {workflow.status.value}")

        # Determine starting approval level based on whether department approval is needed
        if workflow.department:
            workflow.status = ApprovalStatus.PENDING_DEPARTMENT
        elif workflow.criterion_number:
            workflow.status = ApprovalStatus.PENDING_CRITERION
        else:
            workflow.status = ApprovalStatus.PENDING_IQAC

        workflow.submitted_by = str(submitter.id)
        workflow.submitted_at = datetime.utcnow()
        workflow.submission_remarks = remarks

        # Add to history
        self._add_history(workflow, 'submit', submitter, remarks)

        await self.db.flush()

        # Send notification to approvers
        await self._notify_approvers(workflow)

        return workflow

    async def approve(
        self,
        workflow: NAACApprovalWorkflow,
        approver: User,
        remarks: Optional[str] = None
    ) -> NAACApprovalWorkflow:
        """
        Approve at current level and advance to next level.
        """
        now = datetime.utcnow()

        if workflow.status == ApprovalStatus.PENDING_DEPARTMENT:
            workflow.department_approved_by = str(approver.id)
            workflow.department_approved_at = now
            workflow.department_remarks = remarks
            workflow.status = ApprovalStatus.PENDING_CRITERION
            self._add_history(workflow, 'approve_department', approver, remarks)

        elif workflow.status == ApprovalStatus.PENDING_CRITERION:
            workflow.criterion_approved_by = str(approver.id)
            workflow.criterion_approved_at = now
            workflow.criterion_remarks = remarks
            workflow.status = ApprovalStatus.PENDING_IQAC
            self._add_history(workflow, 'approve_criterion', approver, remarks)

        elif workflow.status == ApprovalStatus.PENDING_IQAC:
            workflow.iqac_approved_by = str(approver.id)
            workflow.iqac_approved_at = now
            workflow.iqac_remarks = remarks
            workflow.status = ApprovalStatus.PENDING_HEAD
            self._add_history(workflow, 'approve_iqac', approver, remarks)

        elif workflow.status == ApprovalStatus.PENDING_HEAD:
            workflow.head_approved_by = str(approver.id)
            workflow.head_approved_at = now
            workflow.head_remarks = remarks
            workflow.status = ApprovalStatus.APPROVED
            self._add_history(workflow, 'approve_head', approver, remarks)

        else:
            raise ValueError(f"Cannot approve from status: {workflow.status.value}")

        await self.db.flush()

        # Notify submitter and next level
        await self._notify_approval_action(workflow, 'approved')

        return workflow

    async def reject(
        self,
        workflow: NAACApprovalWorkflow,
        rejector: User,
        reason: str
    ) -> NAACApprovalWorkflow:
        """
        Reject the record. Returns to draft status.
        """
        previous_status = workflow.status
        workflow.status = ApprovalStatus.REJECTED
        workflow.rejected_by = str(rejector.id)
        workflow.rejected_at = datetime.utcnow()
        workflow.rejection_reason = reason

        self._add_history(
            workflow, 'reject', rejector, reason,
            extra={'previous_status': previous_status.value}
        )

        await self.db.flush()

        # Notify submitter
        await self._notify_approval_action(workflow, 'rejected')

        return workflow

    async def request_revision(
        self,
        workflow: NAACApprovalWorkflow,
        reviewer: User,
        remarks: str
    ) -> NAACApprovalWorkflow:
        """
        Request revision. Returns to submitter for changes.
        """
        previous_status = workflow.status
        workflow.status = ApprovalStatus.REVISION_REQUESTED
        workflow.revision_requested_by = str(reviewer.id)
        workflow.revision_requested_at = datetime.utcnow()
        workflow.revision_remarks = remarks

        self._add_history(
            workflow, 'request_revision', reviewer, remarks,
            extra={'previous_status': previous_status.value}
        )

        await self.db.flush()

        # Notify submitter
        await self._notify_approval_action(workflow, 'revision_requested')

        return workflow

    def _add_history(
        self,
        workflow: NAACApprovalWorkflow,
        action: str,
        user: User,
        remarks: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Add entry to approval history"""
        history = workflow.approval_history or []
        entry = {
            'action': action,
            'user_id': str(user.id),
            'user_email': user.email,
            'user_name': user.full_name,
            'timestamp': datetime.utcnow().isoformat(),
            'remarks': remarks
        }
        if extra:
            entry.update(extra)
        history.append(entry)
        workflow.approval_history = history

    async def _notify_approvers(self, workflow: NAACApprovalWorkflow):
        """Send notifications to relevant approvers"""
        # Determine which role should approve based on status
        target_roles = []
        if workflow.status == ApprovalStatus.PENDING_DEPARTMENT:
            target_roles = [NAACRoleType.DEPARTMENT_COORDINATOR]
        elif workflow.status == ApprovalStatus.PENDING_CRITERION:
            target_roles = [NAACRoleType.CRITERION_COORDINATOR]
        elif workflow.status == ApprovalStatus.PENDING_IQAC:
            target_roles = [NAACRoleType.IQAC_COORDINATOR]
        elif workflow.status == ApprovalStatus.PENDING_HEAD:
            target_roles = [NAACRoleType.HEAD_OF_INSTITUTION]

        if not target_roles:
            return

        # Find users with these roles
        query = (
            select(UserNAACRole)
            .join(NAACRole)
            .where(
                NAACRole.role_type.in_(target_roles),
                UserNAACRole.is_active == True
            )
        )

        # Filter by criterion/department if applicable
        if workflow.criterion_number and NAACRoleType.CRITERION_COORDINATOR in target_roles:
            query = query.where(
                or_(
                    UserNAACRole.criterion_number == workflow.criterion_number,
                    UserNAACRole.criterion_number == None
                )
            )

        if workflow.department and NAACRoleType.DEPARTMENT_COORDINATOR in target_roles:
            query = query.where(
                or_(
                    UserNAACRole.department == workflow.department,
                    UserNAACRole.department == None
                )
            )

        result = await self.db.execute(query)
        user_roles = result.scalars().all()

        # Create notifications
        for ur in user_roles:
            notification = NAACNotification(
                id=generate_uuid(),
                user_id=str(ur.user_id),
                notification_type=NotificationType.APPROVAL_REQUESTED,
                title="New Approval Request",
                message=f"A {workflow.record_type} requires your approval.",
                related_entity_type='approval',
                related_entity_id=str(workflow.id),
                action_url=f"/admin/accreditation/approvals/{workflow.id}",
                is_important=True
            )
            self.db.add(notification)

    async def _notify_approval_action(self, workflow: NAACApprovalWorkflow, action: str):
        """Notify submitter of approval action"""
        if not workflow.submitted_by:
            return

        titles = {
            'approved': "Approval Progress",
            'rejected': "Submission Rejected",
            'revision_requested': "Revision Requested"
        }
        messages = {
            'approved': f"Your {workflow.record_type} has been approved and advanced to the next level.",
            'rejected': f"Your {workflow.record_type} has been rejected. Please review the feedback.",
            'revision_requested': f"Revision requested for your {workflow.record_type}. Please review the feedback."
        }

        notification = NAACNotification(
            id=generate_uuid(),
            user_id=workflow.submitted_by,
            notification_type=NotificationType.APPROVAL_ACTION,
            title=titles.get(action, "Approval Update"),
            message=messages.get(action, f"Status: {workflow.status.value}"),
            related_entity_type='approval',
            related_entity_id=str(workflow.id),
            action_url=f"/admin/accreditation/approvals/{workflow.id}",
            is_important=action in ['rejected', 'revision_requested']
        )
        self.db.add(notification)

    async def get_pending_approvals(
        self,
        user_id: str,
        user_roles: List[UserNAACRole]
    ) -> Dict[str, List[NAACApprovalWorkflow]]:
        """
        Get pending approvals organized by level for a user.
        """
        result = {
            'pending_department': [],
            'pending_criterion': [],
            'pending_iqac': [],
            'pending_head': []
        }

        for ur in user_roles:
            role = ur.role

            if role.role_type == NAACRoleType.DEPARTMENT_COORDINATOR:
                query = select(NAACApprovalWorkflow).where(
                    NAACApprovalWorkflow.status == ApprovalStatus.PENDING_DEPARTMENT
                )
                if ur.department:
                    query = query.where(NAACApprovalWorkflow.department == ur.department)
                if ur.criterion_number:
                    query = query.where(NAACApprovalWorkflow.criterion_number == ur.criterion_number)
                workflows = (await self.db.execute(query)).scalars().all()
                result['pending_department'].extend(workflows)

            elif role.role_type == NAACRoleType.CRITERION_COORDINATOR:
                query = select(NAACApprovalWorkflow).where(
                    NAACApprovalWorkflow.status == ApprovalStatus.PENDING_CRITERION
                )
                if ur.criterion_number:
                    query = query.where(NAACApprovalWorkflow.criterion_number == ur.criterion_number)
                workflows = (await self.db.execute(query)).scalars().all()
                result['pending_criterion'].extend(workflows)

            elif role.role_type == NAACRoleType.IQAC_COORDINATOR:
                query = select(NAACApprovalWorkflow).where(
                    NAACApprovalWorkflow.status == ApprovalStatus.PENDING_IQAC
                )
                workflows = (await self.db.execute(query)).scalars().all()
                result['pending_iqac'].extend(workflows)

            elif role.role_type == NAACRoleType.HEAD_OF_INSTITUTION:
                query = select(NAACApprovalWorkflow).where(
                    NAACApprovalWorkflow.status == ApprovalStatus.PENDING_HEAD
                )
                workflows = (await self.db.execute(query)).scalars().all()
                result['pending_head'].extend(workflows)

        # Remove duplicates
        for key in result:
            seen_ids = set()
            unique = []
            for w in result[key]:
                if str(w.id) not in seen_ids:
                    seen_ids.add(str(w.id))
                    unique.append(w)
            result[key] = unique

        return result


class TaskService:
    """Service for managing NAAC tasks"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        creator: User,
        title: str,
        description: Optional[str] = None,
        task_type: Optional[str] = None,
        criterion_number: Optional[int] = None,
        key_indicator: Optional[str] = None,
        department: Optional[str] = None,
        academic_year: Optional[str] = None,
        assigned_to: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[datetime] = None,
        related_record_type: Optional[str] = None,
        related_record_id: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> NAACTask:
        """Create a new task"""
        task = NAACTask(
            id=generate_uuid(),
            title=title,
            description=description,
            task_type=task_type,
            criterion_number=criterion_number,
            key_indicator=key_indicator,
            department=department,
            academic_year=academic_year,
            created_by=str(creator.id),
            assigned_to=assigned_to,
            assigned_by=str(creator.id) if assigned_to else None,
            assigned_at=datetime.utcnow() if assigned_to else None,
            status=TaskStatus.ASSIGNED if assigned_to else TaskStatus.PENDING,
            priority=priority,
            due_date=due_date,
            related_record_type=related_record_type,
            related_record_id=related_record_id,
            attachments=attachments or [],
            extra_data=extra_data or {}
        )
        self.db.add(task)
        await self.db.flush()

        # Notify assignee
        if assigned_to:
            await self._notify_task_assigned(task)

        return task

    async def update_task(
        self,
        task: NAACTask,
        updater: User,
        **updates
    ) -> NAACTask:
        """Update task fields"""
        status_changed = False
        old_status = task.status

        for key, value in updates.items():
            if hasattr(task, key) and value is not None:
                if key == 'status':
                    status_changed = True
                setattr(task, key, value)

        # Handle status transitions
        if status_changed:
            now = datetime.utcnow()
            if task.status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = now
            elif task.status == TaskStatus.SUBMITTED:
                task.submitted_at = now
            elif task.status == TaskStatus.COMPLETED:
                task.completed_at = now
                task.progress_percentage = 100

            # Add system comment
            await self.add_system_comment(
                task,
                f"Status changed from {old_status.value} to {task.status.value}"
            )

        # Handle reassignment
        if 'assigned_to' in updates and updates['assigned_to'] != str(task.assigned_to):
            task.assigned_by = str(updater.id)
            task.assigned_at = datetime.utcnow()
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.ASSIGNED

            if updates['assigned_to']:
                await self._notify_task_assigned(task)

        await self.db.flush()
        return task

    async def add_comment(
        self,
        task: NAACTask,
        user: User,
        content: str,
        attachments: Optional[List[str]] = None
    ) -> NAACTaskComment:
        """Add a comment to a task"""
        comment = NAACTaskComment(
            id=generate_uuid(),
            task_id=str(task.id),
            user_id=str(user.id),
            content=content,
            attachments=attachments or [],
            is_system_comment=False
        )
        self.db.add(comment)
        await self.db.flush()

        # Notify other participants
        await self._notify_task_comment(task, user, comment)

        return comment

    async def add_system_comment(
        self,
        task: NAACTask,
        content: str
    ) -> NAACTaskComment:
        """Add a system-generated comment"""
        comment = NAACTaskComment(
            id=generate_uuid(),
            task_id=str(task.id),
            user_id=None,
            content=content,
            is_system_comment=True
        )
        self.db.add(comment)
        return comment

    async def check_overdue_tasks(self) -> int:
        """Mark overdue tasks and return count"""
        now = datetime.utcnow()
        query = select(NAACTask).where(
            NAACTask.status.in_([
                TaskStatus.PENDING,
                TaskStatus.ASSIGNED,
                TaskStatus.IN_PROGRESS
            ]),
            NAACTask.due_date < now
        )
        result = await self.db.execute(query)
        tasks = result.scalars().all()

        count = 0
        for task in tasks:
            if task.status != TaskStatus.OVERDUE:
                task.status = TaskStatus.OVERDUE
                count += 1

                # Notify assignee
                if task.assigned_to:
                    notification = NAACNotification(
                        id=generate_uuid(),
                        user_id=task.assigned_to,
                        notification_type=NotificationType.TASK_OVERDUE,
                        title="Task Overdue",
                        message=f"Task '{task.title}' is overdue.",
                        related_entity_type='task',
                        related_entity_id=str(task.id),
                        action_url=f"/admin/accreditation/tasks/{task.id}",
                        is_important=True
                    )
                    self.db.add(notification)

        return count

    async def get_task_summary(
        self,
        user_id: Optional[str] = None,
        criterion: Optional[int] = None,
        department: Optional[str] = None
    ) -> Dict[str, int]:
        """Get task count summary"""
        base_query = select(func.count(NAACTask.id))

        if user_id:
            base_query = base_query.where(NAACTask.assigned_to == user_id)
        if criterion:
            base_query = base_query.where(NAACTask.criterion_number == criterion)
        if department:
            base_query = base_query.where(NAACTask.department == department)

        summary = {}
        for status in TaskStatus:
            query = base_query.where(NAACTask.status == status)
            result = await self.db.execute(query)
            summary[status.value] = result.scalar() or 0

        return summary

    async def _notify_task_assigned(self, task: NAACTask):
        """Notify user of task assignment"""
        if not task.assigned_to:
            return

        notification = NAACNotification(
            id=generate_uuid(),
            user_id=task.assigned_to,
            notification_type=NotificationType.TASK_ASSIGNED,
            title="New Task Assigned",
            message=f"You have been assigned: {task.title}",
            related_entity_type='task',
            related_entity_id=str(task.id),
            action_url=f"/admin/accreditation/tasks/{task.id}",
            is_important=task.priority in [TaskPriority.HIGH, TaskPriority.CRITICAL]
        )
        self.db.add(notification)

    async def _notify_task_comment(
        self,
        task: NAACTask,
        commenter: User,
        comment: NAACTaskComment
    ):
        """Notify task participants of new comment"""
        # Get all participants (creator, assignee, commenters)
        participants = set()
        if task.created_by:
            participants.add(task.created_by)
        if task.assigned_to:
            participants.add(task.assigned_to)

        # Exclude the commenter
        participants.discard(str(commenter.id))

        for user_id in participants:
            notification = NAACNotification(
                id=generate_uuid(),
                user_id=user_id,
                notification_type=NotificationType.TASK_UPDATED,
                title="New Comment on Task",
                message=f"{commenter.full_name or commenter.email} commented on: {task.title}",
                related_entity_type='task',
                related_entity_id=str(task.id),
                action_url=f"/admin/accreditation/tasks/{task.id}"
            )
            self.db.add(notification)


class NotificationService:
    """Service for managing NAAC notifications"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[NAACNotification]:
        """Get notifications for a user"""
        query = (
            select(NAACNotification)
            .where(NAACNotification.user_id == user_id)
            .order_by(NAACNotification.created_at.desc())
            .limit(limit)
        )

        if unread_only:
            query = query.where(NAACNotification.is_read == False)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(
        self,
        user_id: str,
        notification_ids: List[str]
    ) -> int:
        """Mark notifications as read"""
        from sqlalchemy import update

        stmt = (
            update(NAACNotification)
            .where(
                NAACNotification.user_id == user_id,
                NAACNotification.id.in_(notification_ids)
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        from sqlalchemy import update

        stmt = (
            update(NAACNotification)
            .where(
                NAACNotification.user_id == user_id,
                NAACNotification.is_read == False
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications"""
        result = await self.db.execute(
            select(func.count(NAACNotification.id))
            .where(
                NAACNotification.user_id == user_id,
                NAACNotification.is_read == False
            )
        )
        return result.scalar() or 0

    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        action_url: Optional[str] = None,
        is_important: bool = False,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> NAACNotification:
        """Create a notification"""
        notification = NAACNotification(
            id=generate_uuid(),
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            action_url=action_url,
            is_important=is_important,
            extra_data=extra_data
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def cleanup_old_notifications(self, days: int = 30) -> int:
        """Delete notifications older than specified days"""
        from sqlalchemy import delete

        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = delete(NAACNotification).where(
            NAACNotification.created_at < cutoff,
            NAACNotification.is_read == True
        )
        result = await self.db.execute(stmt)
        return result.rowcount
