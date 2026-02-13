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
    TeamRoleEnum, TeamStatusEnum, InvitationStatusEnum, TaskStatusEnum, TaskPriorityEnum
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
