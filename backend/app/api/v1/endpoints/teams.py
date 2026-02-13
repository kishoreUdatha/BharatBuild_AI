"""
Team Collaboration API

Endpoints for team management, invitations, tasks, and code merging.
Enables up to 3 students to collaborate on a single project with
AI-powered task splitting and isolated workspaces.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User
from app.models.project import Project
from app.models.team import (
    Team, TeamMember, TeamTask, TeamInvitation,
    TeamRole, TeamStatus, InvitationStatus, TaskStatus, TaskPriority
)
from app.modules.auth.dependencies import get_current_user
from app.schemas.team import (
    TeamCreate, TeamUpdate, TeamResponse, TeamListResponse, TeamMemberResponse,
    InvitationCreate, InvitationAccept, InvitationDecline, InvitationResponse, InvitationListResponse,
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    TaskSplitRequest, TaskSplitResponse, ApplyTaskSplitRequest,
    MergeRequest, MergeResponse, MergeResolveRequest, MergeResolveResponse,
    TeamRoleEnum, TeamStatusEnum, InvitationStatusEnum, TaskStatusEnum, TaskPriorityEnum,
    # Extended features
    CommentCreate, CommentUpdate, CommentResponse,
    ActivityResponse, ActivityListResponse, ActivityTypeEnum,
    ChatMessageCreate, ChatMessageResponse, ChatHistoryResponse,
    CodeReviewCreate, CodeReviewUpdate, CodeReviewResponse, CodeReviewListResponse, ReviewStatusEnum,
    TimeLogStart, TimeLogStop, TimeLogResponse, TaskTimeStats,
    MilestoneCreate, MilestoneUpdate, MilestoneResponse, MilestoneListResponse, MilestoneStatusEnum,
    SkillCreate, SkillUpdate, SkillResponse, MemberSkillsResponse,
    NotificationResponse, NotificationListResponse, NotificationTypeEnum, MarkNotificationsRead,
    TeamAnalytics, MemberContribution
)


router = APIRouter()


# ==================== Helper Functions ====================

async def get_team_or_404(team_id: str, db: AsyncSession) -> Team:
    """Get team by ID or raise 404"""
    result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(TeamMember.user))
        .where(Team.id == team_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


async def get_team_member(team_id: str, user_id: str, db: AsyncSession) -> Optional[TeamMember]:
    """Get team membership for a user"""
    result = await db.execute(
        select(TeamMember).where(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
                TeamMember.is_active == True
            )
        )
    )
    return result.scalar_one_or_none()


async def require_team_member(team_id: str, user: User, db: AsyncSession) -> TeamMember:
    """Require user to be an active team member"""
    member = await get_team_member(team_id, str(user.id), db)
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return member


async def require_team_leader(team_id: str, user: User, db: AsyncSession) -> TeamMember:
    """Require user to be the team leader"""
    member = await require_team_member(team_id, user, db)
    if member.role != TeamRole.LEADER:
        raise HTTPException(status_code=403, detail="Only team leader can perform this action")
    return member


def build_team_response(team: Team) -> TeamResponse:
    """Build TeamResponse from Team model"""
    members = []
    for m in team.members:
        if m.is_active:
            members.append(TeamMemberResponse(
                id=str(m.id),
                user_id=str(m.user_id),
                role=TeamRoleEnum(m.role.value),
                is_active=m.is_active,
                workspace_branch=m.workspace_branch,
                joined_at=m.joined_at,
                last_active=m.last_active,
                user_email=m.user.email if m.user else None,
                user_name=m.user.full_name if m.user else None,
                user_avatar=m.user.avatar_url if m.user else None
            ))

    return TeamResponse(
        id=str(team.id),
        project_id=str(team.project_id),
        created_by=str(team.created_by),
        name=team.name,
        description=team.description,
        status=TeamStatusEnum(team.status.value),
        max_members=team.max_members,
        allow_member_invite=team.allow_member_invite,
        created_at=team.created_at,
        updated_at=team.updated_at,
        members=members,
        member_count=len(members)
    )


# ==================== Team CRUD ====================

@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new team for a project.

    The creator automatically becomes the team leader.
    """
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            and_(
                Project.id == team_data.project_id,
                Project.user_id == current_user.id
            )
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or not owned by you")

    # Check if team already exists for this project
    existing = await db.execute(
        select(Team).where(Team.project_id == team_data.project_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Team already exists for this project")

    # Create team
    team = Team(
        project_id=team_data.project_id,
        created_by=str(current_user.id),
        name=team_data.name,
        description=team_data.description,
        max_members=team_data.max_members,
        allow_member_invite=team_data.allow_member_invite
    )
    db.add(team)
    await db.flush()  # Get team ID

    # Add creator as leader
    leader = TeamMember(
        team_id=str(team.id),
        user_id=str(current_user.id),
        role=TeamRole.LEADER,
        workspace_branch=f"main"  # Leader uses main branch
    )
    db.add(leader)

    await db.commit()
    await db.refresh(team)

    # Reload with relationships
    team = await get_team_or_404(str(team.id), db)

    logger.info(f"Created team {team.id} for project {team_data.project_id} by user {current_user.id}")

    return build_team_response(team)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get team details. Requires team membership."""
    team = await get_team_or_404(team_id, db)
    await require_team_member(team_id, current_user, db)
    return build_team_response(team)


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update team settings. Leader only."""
    team = await get_team_or_404(team_id, db)
    await require_team_leader(team_id, current_user, db)

    # Update fields
    if team_data.name is not None:
        team.name = team_data.name
    if team_data.description is not None:
        team.description = team_data.description
    if team_data.max_members is not None:
        # Validate new max doesn't go below current member count
        active_count = sum(1 for m in team.members if m.is_active)
        if team_data.max_members < active_count:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reduce max_members below current count ({active_count})"
            )
        team.max_members = team_data.max_members
    if team_data.allow_member_invite is not None:
        team.allow_member_invite = team_data.allow_member_invite
    if team_data.status is not None:
        team.status = TeamStatus(team_data.status.value)

    await db.commit()
    await db.refresh(team)

    team = await get_team_or_404(team_id, db)
    return build_team_response(team)


@router.get("/by-project/{project_id}", response_model=TeamResponse)
async def get_team_by_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get team for a specific project."""
    result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(TeamMember.user))
        .where(Team.project_id == project_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="No team exists for this project")

    await require_team_member(str(team.id), current_user, db)
    return build_team_response(team)


@router.delete("/{team_id}/members/{member_id}")
async def remove_team_member(
    team_id: str,
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a member from team. Leader only, cannot remove self."""
    await require_team_leader(team_id, current_user, db)

    # Get the member to remove
    result = await db.execute(
        select(TeamMember).where(
            and_(
                TeamMember.id == member_id,
                TeamMember.team_id == team_id
            )
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.role == TeamRole.LEADER:
        raise HTTPException(status_code=400, detail="Cannot remove team leader")

    # Soft delete - mark as inactive
    member.is_active = False
    await db.commit()

    logger.info(f"Removed member {member_id} from team {team_id}")

    return {"success": True, "message": "Member removed from team"}


# ==================== Invitations ====================

@router.post("/{team_id}/invite", response_model=InvitationResponse)
async def send_invitation(
    team_id: str,
    invitation_data: InvitationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a team invitation to a user by email.

    Leader only, unless allow_member_invite is True.
    """
    team = await get_team_or_404(team_id, db)
    member = await require_team_member(team_id, current_user, db)

    # Check permission
    if member.role != TeamRole.LEADER and not team.allow_member_invite:
        raise HTTPException(status_code=403, detail="Only team leader can send invitations")

    # Check if team is full
    active_count = sum(1 for m in team.members if m.is_active)
    if active_count >= team.max_members:
        raise HTTPException(status_code=400, detail=f"Team is full ({team.max_members} members max)")

    # Check if user is already a member
    result = await db.execute(
        select(User).where(User.email == invitation_data.invitee_email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        existing_member = await get_team_member(team_id, str(existing_user.id), db)
        if existing_member:
            raise HTTPException(status_code=400, detail="User is already a team member")

    # Check for pending invitation
    result = await db.execute(
        select(TeamInvitation).where(
            and_(
                TeamInvitation.team_id == team_id,
                TeamInvitation.invitee_email == invitation_data.invitee_email,
                TeamInvitation.status == InvitationStatus.PENDING
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Pending invitation already exists for this email")

    # Create invitation
    invitation = TeamInvitation(
        team_id=team_id,
        inviter_id=str(current_user.id),
        invitee_id=str(existing_user.id) if existing_user else None,
        invitee_email=invitation_data.invitee_email,
        role=TeamRole(invitation_data.role.value),
        message=invitation_data.message
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    logger.info(f"Invitation {invitation.id} sent to {invitation_data.invitee_email} for team {team_id}")

    # TODO: Send email notification

    return InvitationResponse(
        id=str(invitation.id),
        team_id=str(invitation.team_id),
        inviter_id=str(invitation.inviter_id),
        invitee_id=str(invitation.invitee_id) if invitation.invitee_id else None,
        invitee_email=invitation.invitee_email,
        role=TeamRoleEnum(invitation.role.value),
        status=InvitationStatusEnum(invitation.status.value),
        message=invitation.message,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        responded_at=invitation.responded_at,
        is_expired=invitation.is_expired,
        team_name=team.name
    )


@router.post("/invitations/accept", response_model=TeamMemberResponse)
async def accept_invitation(
    accept_data: InvitationAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept a team invitation using the token."""
    # Find invitation by token
    result = await db.execute(
        select(TeamInvitation)
        .options(selectinload(TeamInvitation.team))
        .where(TeamInvitation.token == accept_data.token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Invitation is {invitation.status.value}")

    if invitation.is_expired:
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # Verify email matches
    if invitation.invitee_email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="This invitation is for a different email address")

    # Check if team is still accepting members
    team = invitation.team
    active_count = len([m for m in team.members if m.is_active])
    if active_count >= team.max_members:
        raise HTTPException(status_code=400, detail="Team is now full")

    # Create team membership
    member = TeamMember(
        team_id=str(team.id),
        user_id=str(current_user.id),
        role=invitation.role,
        workspace_branch=f"member-{current_user.id}"  # Isolated branch
    )
    db.add(member)

    # Update invitation
    invitation.status = InvitationStatus.ACCEPTED
    invitation.invitee_id = str(current_user.id)
    invitation.responded_at = datetime.utcnow()

    await db.commit()
    await db.refresh(member)

    logger.info(f"User {current_user.id} accepted invitation to team {team.id}")

    return TeamMemberResponse(
        id=str(member.id),
        user_id=str(member.user_id),
        role=TeamRoleEnum(member.role.value),
        is_active=member.is_active,
        workspace_branch=member.workspace_branch,
        joined_at=member.joined_at,
        last_active=member.last_active,
        user_email=current_user.email,
        user_name=current_user.full_name
    )


@router.post("/invitations/decline")
async def decline_invitation(
    decline_data: InvitationDecline,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Decline a team invitation."""
    result = await db.execute(
        select(TeamInvitation).where(TeamInvitation.token == decline_data.token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Invitation is already {invitation.status.value}")

    # Verify email matches
    if invitation.invitee_email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="This invitation is for a different email address")

    invitation.status = InvitationStatus.DECLINED
    invitation.responded_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "Invitation declined"}


@router.get("/invitations/my", response_model=InvitationListResponse)
async def get_my_invitations(
    status_filter: Optional[InvitationStatusEnum] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all invitations for the current user."""
    query = select(TeamInvitation).options(
        selectinload(TeamInvitation.team),
        selectinload(TeamInvitation.inviter)
    ).where(
        TeamInvitation.invitee_email == current_user.email
    )

    if status_filter:
        query = query.where(TeamInvitation.status == InvitationStatus(status_filter.value))

    result = await db.execute(query.order_by(TeamInvitation.created_at.desc()))
    invitations = result.scalars().all()

    return InvitationListResponse(
        invitations=[
            InvitationResponse(
                id=str(inv.id),
                team_id=str(inv.team_id),
                inviter_id=str(inv.inviter_id),
                invitee_id=str(inv.invitee_id) if inv.invitee_id else None,
                invitee_email=inv.invitee_email,
                role=TeamRoleEnum(inv.role.value),
                status=InvitationStatusEnum(inv.status.value),
                message=inv.message,
                created_at=inv.created_at,
                expires_at=inv.expires_at,
                responded_at=inv.responded_at,
                is_expired=inv.is_expired,
                team_name=inv.team.name if inv.team else None,
                project_title=None,  # Would need another join
                inviter_name=inv.inviter.full_name if inv.inviter else None,
                inviter_email=inv.inviter.email if inv.inviter else None
            )
            for inv in invitations
        ],
        total=len(invitations)
    )


@router.delete("/{team_id}/invitations/{invitation_id}")
async def cancel_invitation(
    team_id: str,
    invitation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending invitation. Leader only."""
    await require_team_leader(team_id, current_user, db)

    result = await db.execute(
        select(TeamInvitation).where(
            and_(
                TeamInvitation.id == invitation_id,
                TeamInvitation.team_id == team_id,
                TeamInvitation.status == InvitationStatus.PENDING
            )
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Pending invitation not found")

    invitation.status = InvitationStatus.CANCELLED
    await db.commit()

    return {"success": True, "message": "Invitation cancelled"}


# ==================== Tasks ====================

@router.get("/{team_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    team_id: str,
    status_filter: Optional[TaskStatusEnum] = None,
    assignee_id: Optional[str] = None,
    priority: Optional[TaskPriorityEnum] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all tasks for a team with optional filters."""
    await require_team_member(team_id, current_user, db)

    query = select(TeamTask).where(TeamTask.team_id == team_id)

    if status_filter:
        query = query.where(TeamTask.status == TaskStatus(status_filter.value))
    if assignee_id:
        query = query.where(TeamTask.assignee_id == assignee_id)
    if priority:
        query = query.where(TeamTask.priority == TaskPriority(priority.value))

    result = await db.execute(
        query.order_by(TeamTask.order_index, TeamTask.created_at)
    )
    tasks = result.scalars().all()

    # Build response with stats
    by_status = {}
    by_assignee = {}
    task_responses = []

    for task in tasks:
        status_key = task.status.value
        by_status[status_key] = by_status.get(status_key, 0) + 1

        if task.assignee_id:
            by_assignee[task.assignee_id] = by_assignee.get(task.assignee_id, 0) + 1

        task_responses.append(TaskResponse(
            id=str(task.id),
            team_id=str(task.team_id),
            assignee_id=str(task.assignee_id) if task.assignee_id else None,
            created_by=str(task.created_by),
            title=task.title,
            description=task.description,
            status=TaskStatusEnum(task.status.value),
            priority=TaskPriorityEnum(task.priority.value),
            estimated_hours=task.estimated_hours,
            actual_hours=task.actual_hours,
            order_index=task.order_index or 0,
            file_paths=task.file_paths,
            ai_generated=task.ai_generated,
            ai_complexity_score=task.ai_complexity_score,
            ai_dependencies=task.ai_dependencies,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            due_date=task.due_date
        ))

    return TaskListResponse(
        tasks=task_responses,
        total=len(tasks),
        by_status=by_status,
        by_assignee=by_assignee
    )


@router.post("/{team_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    team_id: str,
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task for the team."""
    await require_team_member(team_id, current_user, db)

    # Validate assignee if provided
    if task_data.assignee_id:
        result = await db.execute(
            select(TeamMember).where(
                and_(
                    TeamMember.id == task_data.assignee_id,
                    TeamMember.team_id == team_id,
                    TeamMember.is_active == True
                )
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Invalid assignee_id")

    task = TeamTask(
        team_id=team_id,
        created_by=str(current_user.id),
        assignee_id=task_data.assignee_id,
        title=task_data.title,
        description=task_data.description,
        priority=TaskPriority(task_data.priority.value),
        estimated_hours=task_data.estimated_hours,
        file_paths=task_data.file_paths,
        due_date=task_data.due_date,
        order_index=task_data.order_index or 0
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"Created task {task.id} in team {team_id}")

    return TaskResponse(
        id=str(task.id),
        team_id=str(task.team_id),
        assignee_id=str(task.assignee_id) if task.assignee_id else None,
        created_by=str(task.created_by),
        title=task.title,
        description=task.description,
        status=TaskStatusEnum(task.status.value),
        priority=TaskPriorityEnum(task.priority.value),
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours,
        order_index=task.order_index or 0,
        file_paths=task.file_paths,
        ai_generated=task.ai_generated,
        ai_complexity_score=task.ai_complexity_score,
        ai_dependencies=task.ai_dependencies,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        due_date=task.due_date
    )


@router.put("/{team_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    team_id: str,
    task_id: str,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a task. Any team member can update tasks."""
    await require_team_member(team_id, current_user, db)

    result = await db.execute(
        select(TeamTask).where(
            and_(
                TeamTask.id == task_id,
                TeamTask.team_id == team_id
            )
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update fields
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.assignee_id is not None:
        # Validate assignee
        if task_data.assignee_id:
            result = await db.execute(
                select(TeamMember).where(
                    and_(
                        TeamMember.id == task_data.assignee_id,
                        TeamMember.team_id == team_id,
                        TeamMember.is_active == True
                    )
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Invalid assignee_id")
        task.assignee_id = task_data.assignee_id if task_data.assignee_id else None
    if task_data.status is not None:
        new_status = TaskStatus(task_data.status.value)
        # Track status transitions
        if new_status == TaskStatus.IN_PROGRESS and task.status == TaskStatus.TODO:
            task.started_at = datetime.utcnow()
        elif new_status == TaskStatus.COMPLETED and task.status != TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        task.status = new_status
    if task_data.priority is not None:
        task.priority = TaskPriority(task_data.priority.value)
    if task_data.estimated_hours is not None:
        task.estimated_hours = task_data.estimated_hours
    if task_data.actual_hours is not None:
        task.actual_hours = task_data.actual_hours
    if task_data.file_paths is not None:
        task.file_paths = task_data.file_paths
    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    if task_data.order_index is not None:
        task.order_index = task_data.order_index

    await db.commit()
    await db.refresh(task)

    return TaskResponse(
        id=str(task.id),
        team_id=str(task.team_id),
        assignee_id=str(task.assignee_id) if task.assignee_id else None,
        created_by=str(task.created_by),
        title=task.title,
        description=task.description,
        status=TaskStatusEnum(task.status.value),
        priority=TaskPriorityEnum(task.priority.value),
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours,
        order_index=task.order_index or 0,
        file_paths=task.file_paths,
        ai_generated=task.ai_generated,
        ai_complexity_score=task.ai_complexity_score,
        ai_dependencies=task.ai_dependencies,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        due_date=task.due_date
    )


@router.delete("/{team_id}/tasks/{task_id}")
async def delete_task(
    team_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task. Leader or task creator only."""
    member = await require_team_member(team_id, current_user, db)

    result = await db.execute(
        select(TeamTask).where(
            and_(
                TeamTask.id == task_id,
                TeamTask.team_id == team_id
            )
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check permission
    if member.role != TeamRole.LEADER and task.created_by != str(current_user.id):
        raise HTTPException(status_code=403, detail="Only leader or task creator can delete tasks")

    await db.delete(task)
    await db.commit()

    return {"success": True, "message": "Task deleted"}


# ==================== AI Task Split ====================

@router.post("/{team_id}/tasks/split", response_model=TaskSplitResponse)
async def split_project_tasks(
    team_id: str,
    split_request: TaskSplitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Use AI to split the project into tasks for team members.

    Analyzes the project and suggests tasks based on:
    - Project description and tech stack
    - Number of team members
    - Workload balancing preference
    """
    team = await get_team_or_404(team_id, db)
    await require_team_leader(team_id, current_user, db)

    # Get project details
    result = await db.execute(
        select(Project).where(Project.id == team.project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Import the AI task splitter service
    from app.services.team_task_splitter import split_project_into_tasks

    # Get active members
    active_members = [m for m in team.members if m.is_active]

    # Call AI service
    split_result = await split_project_into_tasks(
        project=project,
        team_members=active_members,
        balance_workload=split_request.balance_workload,
        max_tasks=split_request.max_tasks,
        include_file_mapping=split_request.include_file_mapping
    )

    return split_result


@router.post("/{team_id}/tasks/apply-split", response_model=TaskListResponse)
async def apply_task_split(
    team_id: str,
    apply_request: ApplyTaskSplitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Apply AI-suggested task split to create actual tasks.

    Takes the output from /tasks/split and creates tasks in the database.
    """
    await require_team_leader(team_id, current_user, db)

    created_tasks = []

    for idx, suggested in enumerate(apply_request.suggested_tasks):
        # Determine assignee
        assignee_id = None
        if apply_request.member_assignments and idx in apply_request.member_assignments:
            assignee_id = apply_request.member_assignments[idx]

        task = TeamTask(
            team_id=team_id,
            created_by=str(current_user.id),
            assignee_id=assignee_id,
            title=suggested.title,
            description=suggested.description,
            priority=TaskPriority(suggested.priority.value),
            estimated_hours=suggested.estimated_hours,
            file_paths=suggested.file_paths,
            ai_generated=True,
            ai_complexity_score=suggested.complexity_score,
            ai_dependencies=[str(d) for d in suggested.dependencies] if suggested.dependencies else None,
            order_index=idx
        )
        db.add(task)
        created_tasks.append(task)

    await db.commit()

    # Refresh all tasks
    for task in created_tasks:
        await db.refresh(task)

    logger.info(f"Applied AI task split: created {len(created_tasks)} tasks for team {team_id}")

    return TaskListResponse(
        tasks=[
            TaskResponse(
                id=str(t.id),
                team_id=str(t.team_id),
                assignee_id=str(t.assignee_id) if t.assignee_id else None,
                created_by=str(t.created_by),
                title=t.title,
                description=t.description,
                status=TaskStatusEnum(t.status.value),
                priority=TaskPriorityEnum(t.priority.value),
                estimated_hours=t.estimated_hours,
                actual_hours=t.actual_hours,
                order_index=t.order_index or 0,
                file_paths=t.file_paths,
                ai_generated=t.ai_generated,
                ai_complexity_score=t.ai_complexity_score,
                ai_dependencies=t.ai_dependencies,
                created_at=t.created_at,
                updated_at=t.updated_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
                due_date=t.due_date
            )
            for t in created_tasks
        ],
        total=len(created_tasks),
        by_status={"todo": len(created_tasks)},
        by_assignee={}
    )


# ==================== Code Merge ====================

@router.post("/{team_id}/merge", response_model=MergeResponse)
async def merge_member_code(
    team_id: str,
    merge_request: MergeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Merge a team member's code into the main project.

    Leader only. Performs 3-way merge:
    - Base: Original state when member started
    - Member: Member's changes
    - Main: Current main project state
    """
    await require_team_leader(team_id, current_user, db)

    team = await get_team_or_404(team_id, db)

    # Get the member whose code to merge
    result = await db.execute(
        select(TeamMember).where(
            and_(
                TeamMember.id == merge_request.member_id,
                TeamMember.team_id == team_id,
                TeamMember.is_active == True
            )
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    # Import merge service
    from app.services.team_code_merger import merge_member_changes

    merge_result = await merge_member_changes(
        team=team,
        member=member,
        file_paths=merge_request.file_paths,
        commit_message=merge_request.commit_message
    )

    return merge_result


@router.post("/{team_id}/merge/resolve", response_model=MergeResolveResponse)
async def resolve_merge_conflicts(
    team_id: str,
    resolve_request: MergeResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve merge conflicts.

    For each conflict, choose:
    - keep_main: Keep main project version
    - keep_member: Keep member's version
    - merged_content: Use manually merged content
    """
    await require_team_leader(team_id, current_user, db)

    team = await get_team_or_404(team_id, db)

    from app.services.team_code_merger import resolve_conflicts

    result = await resolve_conflicts(
        team=team,
        resolutions=resolve_request.resolutions
    )

    return result


# ==================== Task Comments ====================

@router.get("/{team_id}/tasks/{task_id}/comments")
async def list_task_comments(
    team_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all comments on a task."""
    from app.models.team import TaskComment
    from app.schemas.team import CommentResponse

    await require_team_member(team_id, current_user, db)

    result = await db.execute(
        select(TaskComment)
        .options(selectinload(TaskComment.author))
        .where(and_(TaskComment.task_id == task_id, TaskComment.parent_id == None))
        .order_by(TaskComment.created_at)
    )
    comments = result.scalars().all()

    def build_comment_response(comment):
        return CommentResponse(
            id=str(comment.id),
            task_id=str(comment.task_id),
            author_id=str(comment.author_id),
            parent_id=str(comment.parent_id) if comment.parent_id else None,
            content=comment.content,
            mentions=comment.mentions,
            is_edited=comment.is_edited,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            author_name=comment.author.full_name if comment.author else None,
            author_email=comment.author.email if comment.author else None,
            author_avatar=comment.author.avatar_url if comment.author else None,
            replies=[build_comment_response(r) for r in comment.replies] if hasattr(comment, 'replies') else []
        )

    return {"comments": [build_comment_response(c) for c in comments], "total": len(comments)}


@router.post("/{team_id}/tasks/{task_id}/comments", status_code=status.HTTP_201_CREATED)
async def create_task_comment(
    team_id: str,
    task_id: str,
    comment_data: "CommentCreate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a comment to a task."""
    from app.models.team import TaskComment, TeamActivity, ActivityType
    from app.schemas.team import CommentCreate, CommentResponse

    await require_team_member(team_id, current_user, db)

    # Parse mentions from content
    import re
    mentions = re.findall(r'@\[([^\]]+)\]\(([^)]+)\)', comment_data.content)
    mention_ids = [m[1] for m in mentions] if mentions else None

    comment = TaskComment(
        task_id=task_id,
        author_id=str(current_user.id),
        parent_id=comment_data.parent_id,
        content=comment_data.content,
        mentions=mention_ids
    )
    db.add(comment)

    # Log activity
    activity = TeamActivity(
        team_id=team_id,
        actor_id=str(current_user.id),
        activity_type=ActivityType.TASK_COMMENTED,
        description=f"commented on task",
        target_type="task",
        target_id=task_id
    )
    db.add(activity)

    await db.commit()
    await db.refresh(comment)

    return CommentResponse(
        id=str(comment.id),
        task_id=str(comment.task_id),
        author_id=str(comment.author_id),
        parent_id=str(comment.parent_id) if comment.parent_id else None,
        content=comment.content,
        mentions=comment.mentions,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author_name=current_user.full_name,
        author_email=current_user.email,
        replies=[]
    )


@router.delete("/{team_id}/tasks/{task_id}/comments/{comment_id}")
async def delete_task_comment(
    team_id: str,
    task_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a comment. Author or leader only."""
    from app.models.team import TaskComment

    member = await require_team_member(team_id, current_user, db)

    result = await db.execute(
        select(TaskComment).where(TaskComment.id == comment_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.author_id != str(current_user.id) and member.role != TeamRole.LEADER:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    await db.delete(comment)
    await db.commit()

    return {"success": True, "message": "Comment deleted"}


# ==================== Activity Feed ====================

@router.get("/{team_id}/activities")
async def list_team_activities(
    team_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    activity_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get team activity feed."""
    from app.models.team import TeamActivity, ActivityType
    from app.schemas.team import ActivityResponse, ActivityListResponse, ActivityTypeEnum

    await require_team_member(team_id, current_user, db)

    query = select(TeamActivity).options(selectinload(TeamActivity.actor)).where(TeamActivity.team_id == team_id)

    if activity_type:
        query = query.where(TeamActivity.activity_type == ActivityType(activity_type))

    query = query.order_by(TeamActivity.created_at.desc()).offset(offset).limit(limit + 1)

    result = await db.execute(query)
    activities = result.scalars().all()

    has_more = len(activities) > limit
    activities = activities[:limit]

    return ActivityListResponse(
        activities=[
            ActivityResponse(
                id=str(a.id),
                team_id=str(a.team_id),
                actor_id=str(a.actor_id) if a.actor_id else None,
                activity_type=ActivityTypeEnum(a.activity_type.value),
                description=a.description,
                target_type=a.target_type,
                target_id=str(a.target_id) if a.target_id else None,
                metadata=a.metadata,
                created_at=a.created_at,
                actor_name=a.actor.full_name if a.actor else None,
                actor_avatar=a.actor.avatar_url if a.actor else None
            )
            for a in activities
        ],
        total=len(activities),
        has_more=has_more
    )


# ==================== Chat History ====================

@router.get("/{team_id}/chat")
async def get_chat_history(
    team_id: str,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat message history."""
    from app.models.team import TeamChatMessage
    from app.schemas.team import ChatMessageResponse, ChatHistoryResponse

    await require_team_member(team_id, current_user, db)

    query = (
        select(TeamChatMessage)
        .options(selectinload(TeamChatMessage.sender))
        .where(and_(TeamChatMessage.team_id == team_id, TeamChatMessage.is_deleted == False))
    )

    if before:
        query = query.where(TeamChatMessage.id < before)

    query = query.order_by(TeamChatMessage.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    messages = result.scalars().all()

    has_more = len(messages) > limit
    messages = list(reversed(messages[:limit]))  # Return in chronological order

    return ChatHistoryResponse(
        messages=[
            ChatMessageResponse(
                id=str(m.id),
                team_id=str(m.team_id),
                sender_id=str(m.sender_id) if m.sender_id else None,
                content=m.content,
                mentions=m.mentions,
                message_type=m.message_type,
                attachment_url=m.attachment_url,
                attachment_name=m.attachment_name,
                is_edited=m.is_edited,
                is_deleted=m.is_deleted,
                created_at=m.created_at,
                updated_at=m.updated_at,
                sender_name=m.sender.full_name if m.sender else None,
                sender_avatar=m.sender.avatar_url if m.sender else None
            )
            for m in messages
        ],
        total=len(messages),
        has_more=has_more
    )


@router.post("/{team_id}/chat", status_code=status.HTTP_201_CREATED)
async def send_chat_message(
    team_id: str,
    message_data: "ChatMessageCreate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message (persisted)."""
    from app.models.team import TeamChatMessage
    from app.schemas.team import ChatMessageCreate, ChatMessageResponse

    await require_team_member(team_id, current_user, db)

    # Parse mentions
    import re
    mentions = re.findall(r'@\[([^\]]+)\]\(([^)]+)\)', message_data.content)
    mention_ids = [m[1] for m in mentions] if mentions else None

    message = TeamChatMessage(
        team_id=team_id,
        sender_id=str(current_user.id),
        content=message_data.content,
        message_type=message_data.message_type,
        mentions=mention_ids
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return ChatMessageResponse(
        id=str(message.id),
        team_id=str(message.team_id),
        sender_id=str(message.sender_id),
        content=message.content,
        mentions=message.mentions,
        message_type=message.message_type,
        is_edited=False,
        is_deleted=False,
        created_at=message.created_at,
        sender_name=current_user.full_name,
        sender_avatar=current_user.avatar_url
    )


# ==================== Code Reviews ====================

@router.get("/{team_id}/reviews")
async def list_code_reviews(
    team_id: str,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List code reviews for a team."""
    from app.models.team import CodeReview, ReviewStatus
    from app.schemas.team import CodeReviewResponse, CodeReviewListResponse, ReviewStatusEnum

    await require_team_member(team_id, current_user, db)

    query = select(CodeReview).where(CodeReview.team_id == team_id)

    if status_filter:
        query = query.where(CodeReview.status == ReviewStatus(status_filter))

    query = query.order_by(CodeReview.created_at.desc())

    result = await db.execute(query)
    reviews = result.scalars().all()

    return CodeReviewListResponse(
        reviews=[
            CodeReviewResponse(
                id=str(r.id),
                team_id=str(r.team_id),
                requester_id=str(r.requester_id),
                reviewer_id=str(r.reviewer_id) if r.reviewer_id else None,
                title=r.title,
                description=r.description,
                status=ReviewStatusEnum(r.status.value),
                file_paths=r.file_paths,
                feedback=r.feedback,
                task_id=str(r.task_id) if r.task_id else None,
                created_at=r.created_at,
                updated_at=r.updated_at,
                reviewed_at=r.reviewed_at
            )
            for r in reviews
        ],
        total=len(reviews)
    )


@router.post("/{team_id}/reviews", status_code=status.HTTP_201_CREATED)
async def create_code_review(
    team_id: str,
    review_data: "CodeReviewCreate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a code review request."""
    from app.models.team import CodeReview, TeamActivity, ActivityType, TeamNotification, NotificationType
    from app.schemas.team import CodeReviewCreate, CodeReviewResponse, ReviewStatusEnum

    member = await require_team_member(team_id, current_user, db)

    review = CodeReview(
        team_id=team_id,
        requester_id=str(member.id),
        reviewer_id=review_data.reviewer_id,
        title=review_data.title,
        description=review_data.description,
        file_paths=review_data.file_paths,
        task_id=review_data.task_id
    )
    db.add(review)

    # Log activity
    activity = TeamActivity(
        team_id=team_id,
        actor_id=str(current_user.id),
        activity_type=ActivityType.REVIEW_REQUESTED,
        description=f"requested code review: {review_data.title}",
        target_type="review",
        target_id=str(review.id)
    )
    db.add(activity)

    # Create notification for reviewer
    if review_data.reviewer_id:
        reviewer_result = await db.execute(
            select(TeamMember).where(TeamMember.id == review_data.reviewer_id)
        )
        reviewer = reviewer_result.scalar_one_or_none()
        if reviewer:
            notification = TeamNotification(
                user_id=str(reviewer.user_id),
                team_id=team_id,
                actor_id=str(current_user.id),
                notification_type=NotificationType.REVIEW_REQUESTED,
                title="Code review requested",
                message=f"{current_user.full_name} requested your review on: {review_data.title}",
                target_type="review",
                target_id=str(review.id)
            )
            db.add(notification)

    await db.commit()
    await db.refresh(review)

    return CodeReviewResponse(
        id=str(review.id),
        team_id=str(review.team_id),
        requester_id=str(review.requester_id),
        reviewer_id=str(review.reviewer_id) if review.reviewer_id else None,
        title=review.title,
        description=review.description,
        status=ReviewStatusEnum(review.status.value),
        file_paths=review.file_paths,
        task_id=str(review.task_id) if review.task_id else None,
        created_at=review.created_at
    )


@router.put("/{team_id}/reviews/{review_id}")
async def update_code_review(
    team_id: str,
    review_id: str,
    review_data: "CodeReviewUpdate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a code review (add feedback, change status)."""
    from app.models.team import CodeReview, ReviewStatus, TeamActivity, ActivityType
    from app.schemas.team import CodeReviewUpdate, CodeReviewResponse, ReviewStatusEnum

    await require_team_member(team_id, current_user, db)

    result = await db.execute(
        select(CodeReview).where(and_(CodeReview.id == review_id, CodeReview.team_id == team_id))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Code review not found")

    if review_data.status:
        review.status = ReviewStatus(review_data.status.value)
        if review_data.status in [ReviewStatusEnum.APPROVED, ReviewStatusEnum.REJECTED, ReviewStatusEnum.CHANGES_REQUESTED]:
            review.reviewed_at = datetime.utcnow()

    if review_data.feedback:
        review.feedback = review_data.feedback

    if review_data.reviewer_id is not None:
        review.reviewer_id = review_data.reviewer_id

    await db.commit()
    await db.refresh(review)

    return CodeReviewResponse(
        id=str(review.id),
        team_id=str(review.team_id),
        requester_id=str(review.requester_id),
        reviewer_id=str(review.reviewer_id) if review.reviewer_id else None,
        title=review.title,
        description=review.description,
        status=ReviewStatusEnum(review.status.value),
        file_paths=review.file_paths,
        feedback=review.feedback,
        task_id=str(review.task_id) if review.task_id else None,
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewed_at=review.reviewed_at
    )


# ==================== Time Tracking ====================

@router.post("/{team_id}/tasks/{task_id}/time/start")
async def start_time_tracking(
    team_id: str,
    task_id: str,
    time_data: Optional["TimeLogStart"] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start tracking time on a task."""
    from app.models.team import TaskTimeLog
    from app.schemas.team import TimeLogStart, TimeLogResponse

    member = await require_team_member(team_id, current_user, db)

    # Check if there's already a running timer
    result = await db.execute(
        select(TaskTimeLog).where(
            and_(
                TaskTimeLog.member_id == str(member.id),
                TaskTimeLog.is_running == True
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="You already have a running timer. Stop it first.")

    log = TaskTimeLog(
        task_id=task_id,
        member_id=str(member.id),
        description=time_data.description if time_data else None
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    return TimeLogResponse(
        id=str(log.id),
        task_id=str(log.task_id),
        member_id=str(log.member_id),
        description=log.description,
        started_at=log.started_at,
        is_running=True,
        created_at=log.created_at,
        member_name=current_user.full_name
    )


@router.post("/{team_id}/tasks/{task_id}/time/stop")
async def stop_time_tracking(
    team_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stop tracking time on a task."""
    from app.models.team import TaskTimeLog
    from app.schemas.team import TimeLogResponse

    member = await require_team_member(team_id, current_user, db)

    result = await db.execute(
        select(TaskTimeLog).where(
            and_(
                TaskTimeLog.task_id == task_id,
                TaskTimeLog.member_id == str(member.id),
                TaskTimeLog.is_running == True
            )
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="No running timer found for this task")

    log.stop()
    await db.commit()
    await db.refresh(log)

    return TimeLogResponse(
        id=str(log.id),
        task_id=str(log.task_id),
        member_id=str(log.member_id),
        description=log.description,
        started_at=log.started_at,
        ended_at=log.ended_at,
        duration_minutes=log.duration_minutes,
        is_running=False,
        created_at=log.created_at,
        member_name=current_user.full_name
    )


@router.get("/{team_id}/tasks/{task_id}/time")
async def get_task_time_logs(
    team_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all time logs for a task."""
    from app.models.team import TaskTimeLog
    from app.schemas.team import TimeLogResponse, TaskTimeStats

    await require_team_member(team_id, current_user, db)

    result = await db.execute(
        select(TaskTimeLog)
        .options(selectinload(TaskTimeLog.member).selectinload(TeamMember.user))
        .where(TaskTimeLog.task_id == task_id)
        .order_by(TaskTimeLog.started_at.desc())
    )
    logs = result.scalars().all()

    total_minutes = sum(l.duration_minutes or 0 for l in logs)
    by_member = {}
    for log in logs:
        member_id = str(log.member_id)
        by_member[member_id] = by_member.get(member_id, 0) + (log.duration_minutes or 0)

    return {
        "logs": [
            TimeLogResponse(
                id=str(l.id),
                task_id=str(l.task_id),
                member_id=str(l.member_id),
                description=l.description,
                started_at=l.started_at,
                ended_at=l.ended_at,
                duration_minutes=l.duration_minutes,
                is_running=l.is_running,
                created_at=l.created_at,
                member_name=l.member.user.full_name if l.member and l.member.user else None
            )
            for l in logs
        ],
        "stats": TaskTimeStats(
            task_id=task_id,
            total_minutes=total_minutes,
            total_logs=len(logs),
            by_member=by_member
        )
    }


# ==================== Milestones ====================

@router.get("/{team_id}/milestones")
async def list_milestones(
    team_id: str,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all milestones for a team."""
    from app.models.team import TeamMilestone, MilestoneStatus
    from app.schemas.team import MilestoneResponse, MilestoneListResponse, MilestoneStatusEnum

    await require_team_member(team_id, current_user, db)

    query = select(TeamMilestone).where(TeamMilestone.team_id == team_id)

    if status_filter:
        query = query.where(TeamMilestone.status == MilestoneStatus(status_filter))

    query = query.order_by(TeamMilestone.order_index, TeamMilestone.created_at)

    result = await db.execute(query)
    milestones = result.scalars().all()

    # Get task counts per milestone
    milestone_responses = []
    for m in milestones:
        total_result = await db.execute(
            select(func.count(TeamTask.id)).where(TeamTask.milestone_id == str(m.id))
        )
        total_tasks = total_result.scalar() or 0

        completed_result = await db.execute(
            select(func.count(TeamTask.id)).where(
                and_(TeamTask.milestone_id == str(m.id), TeamTask.status == TaskStatus.COMPLETED)
            )
        )
        completed_tasks = completed_result.scalar() or 0

        milestone_responses.append(MilestoneResponse(
            id=str(m.id),
            team_id=str(m.team_id),
            created_by=str(m.created_by),
            title=m.title,
            description=m.description,
            status=MilestoneStatusEnum(m.status.value),
            start_date=m.start_date,
            due_date=m.due_date,
            completed_at=m.completed_at,
            progress=m.progress,
            order_index=m.order_index,
            created_at=m.created_at,
            updated_at=m.updated_at,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks
        ))

    return MilestoneListResponse(milestones=milestone_responses, total=len(milestones))


@router.post("/{team_id}/milestones", status_code=status.HTTP_201_CREATED)
async def create_milestone(
    team_id: str,
    milestone_data: "MilestoneCreate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new milestone. Leader only."""
    from app.models.team import TeamMilestone, TeamActivity, ActivityType
    from app.schemas.team import MilestoneCreate, MilestoneResponse, MilestoneStatusEnum

    await require_team_leader(team_id, current_user, db)

    milestone = TeamMilestone(
        team_id=team_id,
        created_by=str(current_user.id),
        title=milestone_data.title,
        description=milestone_data.description,
        start_date=milestone_data.start_date,
        due_date=milestone_data.due_date
    )
    db.add(milestone)

    activity = TeamActivity(
        team_id=team_id,
        actor_id=str(current_user.id),
        activity_type=ActivityType.MILESTONE_CREATED,
        description=f"created milestone: {milestone_data.title}",
        target_type="milestone",
        target_id=str(milestone.id)
    )
    db.add(activity)

    await db.commit()
    await db.refresh(milestone)

    return MilestoneResponse(
        id=str(milestone.id),
        team_id=str(milestone.team_id),
        created_by=str(milestone.created_by),
        title=milestone.title,
        description=milestone.description,
        status=MilestoneStatusEnum(milestone.status.value),
        start_date=milestone.start_date,
        due_date=milestone.due_date,
        progress=0,
        order_index=milestone.order_index,
        created_at=milestone.created_at,
        total_tasks=0,
        completed_tasks=0
    )


@router.put("/{team_id}/milestones/{milestone_id}")
async def update_milestone(
    team_id: str,
    milestone_id: str,
    milestone_data: "MilestoneUpdate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a milestone. Leader only."""
    from app.models.team import TeamMilestone, MilestoneStatus
    from app.schemas.team import MilestoneUpdate, MilestoneResponse, MilestoneStatusEnum

    await require_team_leader(team_id, current_user, db)

    result = await db.execute(
        select(TeamMilestone).where(and_(TeamMilestone.id == milestone_id, TeamMilestone.team_id == team_id))
    )
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if milestone_data.title is not None:
        milestone.title = milestone_data.title
    if milestone_data.description is not None:
        milestone.description = milestone_data.description
    if milestone_data.status is not None:
        milestone.status = MilestoneStatus(milestone_data.status.value)
        if milestone_data.status == MilestoneStatusEnum.COMPLETED:
            milestone.completed_at = datetime.utcnow()
    if milestone_data.start_date is not None:
        milestone.start_date = milestone_data.start_date
    if milestone_data.due_date is not None:
        milestone.due_date = milestone_data.due_date
    if milestone_data.order_index is not None:
        milestone.order_index = milestone_data.order_index

    await db.commit()
    await db.refresh(milestone)

    return MilestoneResponse(
        id=str(milestone.id),
        team_id=str(milestone.team_id),
        created_by=str(milestone.created_by),
        title=milestone.title,
        description=milestone.description,
        status=MilestoneStatusEnum(milestone.status.value),
        start_date=milestone.start_date,
        due_date=milestone.due_date,
        completed_at=milestone.completed_at,
        progress=milestone.progress,
        order_index=milestone.order_index,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
        total_tasks=0,
        completed_tasks=0
    )


# ==================== Member Skills ====================

@router.get("/{team_id}/members/{member_id}/skills")
async def get_member_skills(
    team_id: str,
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get skills for a team member."""
    from app.models.team import MemberSkill
    from app.schemas.team import SkillResponse, MemberSkillsResponse

    await require_team_member(team_id, current_user, db)

    result = await db.execute(
        select(MemberSkill).where(MemberSkill.member_id == member_id).order_by(MemberSkill.is_primary.desc())
    )
    skills = result.scalars().all()

    return MemberSkillsResponse(
        member_id=member_id,
        skills=[
            SkillResponse(
                id=str(s.id),
                member_id=str(s.member_id),
                skill_name=s.skill_name,
                proficiency_level=s.proficiency_level,
                is_primary=s.is_primary,
                created_at=s.created_at
            )
            for s in skills
        ]
    )


@router.post("/{team_id}/members/{member_id}/skills", status_code=status.HTTP_201_CREATED)
async def add_member_skill(
    team_id: str,
    member_id: str,
    skill_data: "SkillCreate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a skill to a team member. Member or leader only."""
    from app.models.team import MemberSkill
    from app.schemas.team import SkillCreate, SkillResponse

    member = await require_team_member(team_id, current_user, db)

    # Check permission: member can only edit their own, leader can edit anyone
    if str(member.id) != member_id and member.role != TeamRole.LEADER:
        raise HTTPException(status_code=403, detail="Can only add skills to your own profile")

    skill = MemberSkill(
        member_id=member_id,
        skill_name=skill_data.skill_name,
        proficiency_level=skill_data.proficiency_level,
        is_primary=skill_data.is_primary
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    return SkillResponse(
        id=str(skill.id),
        member_id=str(skill.member_id),
        skill_name=skill.skill_name,
        proficiency_level=skill.proficiency_level,
        is_primary=skill.is_primary,
        created_at=skill.created_at
    )


@router.delete("/{team_id}/members/{member_id}/skills/{skill_id}")
async def remove_member_skill(
    team_id: str,
    member_id: str,
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a skill from a team member."""
    from app.models.team import MemberSkill

    member = await require_team_member(team_id, current_user, db)

    if str(member.id) != member_id and member.role != TeamRole.LEADER:
        raise HTTPException(status_code=403, detail="Can only remove your own skills")

    result = await db.execute(
        select(MemberSkill).where(and_(MemberSkill.id == skill_id, MemberSkill.member_id == member_id))
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    await db.delete(skill)
    await db.commit()

    return {"success": True, "message": "Skill removed"}


# ==================== Notifications ====================

@router.get("/{team_id}/notifications")
async def get_notifications(
    team_id: str,
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for the current user in a team."""
    from app.models.team import TeamNotification
    from app.schemas.team import NotificationResponse, NotificationListResponse, NotificationTypeEnum

    await require_team_member(team_id, current_user, db)

    query = select(TeamNotification).where(
        and_(TeamNotification.team_id == team_id, TeamNotification.user_id == str(current_user.id))
    )

    if unread_only:
        query = query.where(TeamNotification.is_read == False)

    query = query.order_by(TeamNotification.created_at.desc()).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    # Get unread count
    unread_result = await db.execute(
        select(func.count(TeamNotification.id)).where(
            and_(
                TeamNotification.team_id == team_id,
                TeamNotification.user_id == str(current_user.id),
                TeamNotification.is_read == False
            )
        )
    )
    unread_count = unread_result.scalar() or 0

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=str(n.id),
                user_id=str(n.user_id),
                team_id=str(n.team_id),
                actor_id=str(n.actor_id) if n.actor_id else None,
                notification_type=NotificationTypeEnum(n.notification_type.value),
                title=n.title,
                message=n.message,
                target_type=n.target_type,
                target_id=str(n.target_id) if n.target_id else None,
                is_read=n.is_read,
                read_at=n.read_at,
                created_at=n.created_at
            )
            for n in notifications
        ],
        total=len(notifications),
        unread_count=unread_count
    )


@router.post("/{team_id}/notifications/read")
async def mark_notifications_read(
    team_id: str,
    mark_data: "MarkNotificationsRead",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark notifications as read."""
    from app.models.team import TeamNotification
    from app.schemas.team import MarkNotificationsRead

    await require_team_member(team_id, current_user, db)

    query = select(TeamNotification).where(
        and_(
            TeamNotification.team_id == team_id,
            TeamNotification.user_id == str(current_user.id),
            TeamNotification.is_read == False
        )
    )

    if mark_data.notification_ids:
        query = query.where(TeamNotification.id.in_(mark_data.notification_ids))

    result = await db.execute(query)
    notifications = result.scalars().all()

    for n in notifications:
        n.is_read = True
        n.read_at = datetime.utcnow()

    await db.commit()

    return {"success": True, "marked_count": len(notifications)}


# ==================== Team Analytics ====================

@router.get("/{team_id}/analytics")
async def get_team_analytics(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get team analytics and dashboard data."""
    from app.models.team import TeamMilestone, TaskTimeLog, TeamActivity, MilestoneStatus
    from app.schemas.team import TeamAnalytics, ActivityResponse, ActivityTypeEnum

    team = await get_team_or_404(team_id, db)
    await require_team_member(team_id, current_user, db)

    # Member count
    active_members = [m for m in team.members if m.is_active]

    # Task stats
    result = await db.execute(select(TeamTask).where(TeamTask.team_id == team_id))
    tasks = result.scalars().all()

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    in_progress_tasks = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
    overdue_tasks = sum(1 for t in tasks if t.due_date and t.due_date < datetime.utcnow() and t.status != TaskStatus.COMPLETED)

    tasks_by_status = {}
    tasks_by_priority = {}
    for t in tasks:
        tasks_by_status[t.status.value] = tasks_by_status.get(t.status.value, 0) + 1
        tasks_by_priority[t.priority.value] = tasks_by_priority.get(t.priority.value, 0) + 1

    # Time tracking
    result = await db.execute(select(TaskTimeLog).where(TaskTimeLog.task_id.in_([str(t.id) for t in tasks])))
    time_logs = result.scalars().all()
    total_minutes = sum(l.duration_minutes or 0 for l in time_logs)

    # This week's hours
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_logs = [l for l in time_logs if l.started_at >= week_ago]
    week_minutes = sum(l.duration_minutes or 0 for l in week_logs)

    # Milestones
    result = await db.execute(select(TeamMilestone).where(TeamMilestone.team_id == team_id))
    milestones = result.scalars().all()
    active_milestones = sum(1 for m in milestones if m.status == MilestoneStatus.ACTIVE)
    completed_milestones = sum(1 for m in milestones if m.status == MilestoneStatus.COMPLETED)

    # Workload distribution
    workload = []
    for member in active_members:
        member_tasks = [t for t in tasks if t.assignee_id == str(member.id)]
        member_hours = sum(l.duration_minutes or 0 for l in time_logs if l.member_id == str(member.id)) / 60
        workload.append({
            "member_id": str(member.id),
            "name": member.user.full_name if member.user else "Unknown",
            "task_count": len(member_tasks),
            "hours": round(member_hours, 1)
        })

    # Recent activities
    result = await db.execute(
        select(TeamActivity)
        .options(selectinload(TeamActivity.actor))
        .where(TeamActivity.team_id == team_id)
        .order_by(TeamActivity.created_at.desc())
        .limit(10)
    )
    recent_activities = result.scalars().all()

    # Progress
    overall_progress = int((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)

    return TeamAnalytics(
        team_id=team_id,
        total_members=len(active_members),
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        overdue_tasks=overdue_tasks,
        total_hours_logged=round(total_minutes / 60, 1),
        hours_this_week=round(week_minutes / 60, 1),
        overall_progress=overall_progress,
        active_milestones=active_milestones,
        completed_milestones=completed_milestones,
        workload_distribution=workload,
        recent_activities=[
            ActivityResponse(
                id=str(a.id),
                team_id=str(a.team_id),
                actor_id=str(a.actor_id) if a.actor_id else None,
                activity_type=ActivityTypeEnum(a.activity_type.value),
                description=a.description,
                target_type=a.target_type,
                target_id=str(a.target_id) if a.target_id else None,
                metadata=a.metadata,
                created_at=a.created_at,
                actor_name=a.actor.full_name if a.actor else None
            )
            for a in recent_activities
        ],
        tasks_by_status=tasks_by_status,
        tasks_by_priority=tasks_by_priority
    )
