"""
College Onboarding API Endpoints
Handles college registration, profile setup, team invitations, and onboarding progress
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta
import secrets
import uuid

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, UserRole
from app.models.college_onboarding import (
    CollegeProfile, CollegeDepartment, CollegeProgram,
    CollegeInvitation, OnboardingProgress,
    CollegeType, SubscriptionPlan, OnboardingStep, InvitationStatus
)
from app.schemas.college_onboarding import (
    CollegeRegistrationRequest, CollegeRegistrationResponse,
    CollegeProfileUpdate, CollegeProfileResponse,
    DepartmentCreate, DepartmentResponse, DepartmentBulkCreate,
    ProgramCreate, ProgramResponse, ProgramBulkCreate,
    TeamInviteRequest, TeamInviteBulkRequest, TeamInviteResponse,
    InvitationAcceptRequest, OnboardingProgressResponse, OnboardingChecklist, ChecklistItem
)

router = APIRouter()


# ============== College Registration ==============

@router.post("/register", response_model=CollegeRegistrationResponse)
async def register_college(
    request: CollegeRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new college for NAAC/NBA accreditation.
    Creates college profile and admin user (Principal).
    """
    # Check if college already exists
    existing = await db.execute(
        select(CollegeProfile).where(
            (CollegeProfile.email == request.email) |
            (CollegeProfile.aishe_code == request.aishe_code if request.aishe_code else False)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="College with this email or AISHE code already exists"
        )

    # Check if admin email already exists
    existing_user = await db.execute(
        select(User).where(User.email == request.principal_email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists. Please login instead."
        )

    # Create admin user (Principal)
    admin_user = User(
        email=request.principal_email,
        username=request.principal_email.split("@")[0],
        full_name=request.principal_name,
        hashed_password=get_password_hash(request.admin_password),
        role=UserRole.ADMIN,
        organization=request.name,
        is_active=True,
        is_verified=True
    )
    db.add(admin_user)
    await db.flush()

    # Create college profile (convert enum values to uppercase for DB)
    college = CollegeProfile(
        name=request.name,
        short_name=request.short_name,
        aishe_code=request.aishe_code,
        college_type=CollegeType(request.college_type.value.upper()),
        university_affiliation=request.university_affiliation,
        year_established=request.year_established,
        address=request.address,
        city=request.city,
        state=request.state,
        pincode=request.pincode,
        phone=request.phone,
        email=request.email,
        website=request.website,
        principal_name=request.principal_name,
        principal_email=request.principal_email,
        principal_phone=request.principal_phone,
        subscription_plan=SubscriptionPlan(request.subscription_plan.value.upper()),
        subscription_start=datetime.utcnow(),
        subscription_end=datetime.utcnow() + timedelta(days=30 if request.subscription_plan.value == "free_trial" else 365),
        admin_user_id=admin_user.id,
        onboarding_step=OnboardingStep.DEPARTMENTS
    )
    db.add(college)
    await db.flush()

    # Create onboarding progress tracker
    # Mark profile as completed since registration form collects basic profile info
    progress = OnboardingProgress(
        college_id=college.id,
        registration_completed=True,
        registration_at=datetime.utcnow(),
        profile_completed=True,
        profile_at=datetime.utcnow(),
        current_step=OnboardingStep.DEPARTMENTS,
        completion_percentage=30
    )
    db.add(progress)

    await db.commit()
    await db.refresh(college)

    # Generate access token for the admin user
    access_token = create_access_token(data={"sub": admin_user.email})

    return CollegeRegistrationResponse(
        id=str(college.id),
        name=college.name,
        aishe_code=college.aishe_code,
        admin_user_id=str(admin_user.id),
        onboarding_step=college.onboarding_step.value,
        message="College registered successfully! Please complete your profile setup.",
        access_token=access_token
    )


# ============== College Profile ==============

@router.get("/profile/{college_id}", response_model=CollegeProfileResponse)
async def get_college_profile(
    college_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get college profile by ID"""
    result = await db.execute(
        select(CollegeProfile).where(CollegeProfile.id == college_id)
    )
    college = result.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return college


@router.put("/profile/{college_id}", response_model=CollegeProfileResponse)
async def update_college_profile(
    college_id: str,
    request: CollegeProfileUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update college profile"""
    result = await db.execute(
        select(CollegeProfile).where(CollegeProfile.id == college_id)
    )
    college = result.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(college, field, value)

    # Update onboarding progress
    progress_result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.college_id == college_id)
    )
    progress = progress_result.scalar_one_or_none()
    if progress and not progress.profile_completed:
        progress.profile_completed = True
        progress.profile_at = datetime.utcnow()
        progress.current_step = OnboardingStep.DEPARTMENTS
        college.onboarding_step = OnboardingStep.DEPARTMENTS
        progress.calculate_completion()

    await db.commit()
    await db.refresh(college)
    return college


# ============== Departments ==============

@router.post("/profile/{college_id}/departments", response_model=List[DepartmentResponse])
async def add_departments(
    college_id: str,
    request: DepartmentBulkCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add departments to college"""
    # Verify college exists
    result = await db.execute(
        select(CollegeProfile).where(CollegeProfile.id == college_id)
    )
    college = result.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    departments = []
    for dept_data in request.departments:
        dept = CollegeDepartment(
            college_id=college_id,
            name=dept_data.name,
            code=dept_data.code,
            hod_name=dept_data.hod_name,
            hod_email=dept_data.hod_email
        )
        db.add(dept)
        departments.append(dept)

    # Update counts and progress
    college.total_departments += len(departments)

    progress_result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.college_id == college_id)
    )
    progress = progress_result.scalar_one_or_none()
    if progress:
        progress.departments_count = college.total_departments
        if not progress.departments_added and college.total_departments >= 1:
            progress.departments_added = True
            progress.departments_at = datetime.utcnow()
            progress.current_step = OnboardingStep.PROGRAMS
            college.onboarding_step = OnboardingStep.PROGRAMS
        progress.calculate_completion()

    await db.commit()
    for dept in departments:
        await db.refresh(dept)

    return departments


@router.get("/profile/{college_id}/departments", response_model=List[DepartmentResponse])
async def get_departments(
    college_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all departments for a college"""
    result = await db.execute(
        select(CollegeDepartment).where(CollegeDepartment.college_id == college_id)
    )
    return result.scalars().all()


# ============== Programs ==============

@router.post("/profile/{college_id}/programs", response_model=List[ProgramResponse])
async def add_programs(
    college_id: str,
    request: ProgramBulkCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add programs to college"""
    result = await db.execute(
        select(CollegeProfile).where(CollegeProfile.id == college_id)
    )
    college = result.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    programs = []
    for prog_data in request.programs:
        program = CollegeProgram(
            college_id=college_id,
            department_id=prog_data.department_id,
            name=prog_data.name,
            code=prog_data.code,
            degree_type=prog_data.degree_type,
            duration_years=prog_data.duration_years,
            intake=prog_data.intake
        )
        db.add(program)
        programs.append(program)

    # Update counts and progress
    college.total_programs += len(programs)

    progress_result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.college_id == college_id)
    )
    progress = progress_result.scalar_one_or_none()
    if progress:
        progress.programs_count = college.total_programs
        if not progress.programs_added and college.total_programs >= 1:
            progress.programs_added = True
            progress.programs_at = datetime.utcnow()
            progress.current_step = OnboardingStep.TEAM_SETUP
            college.onboarding_step = OnboardingStep.TEAM_SETUP
        progress.calculate_completion()

    await db.commit()
    for prog in programs:
        await db.refresh(prog)

    return programs


@router.get("/profile/{college_id}/programs", response_model=List[ProgramResponse])
async def get_programs(
    college_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all programs for a college"""
    result = await db.execute(
        select(CollegeProgram).where(CollegeProgram.college_id == college_id)
    )
    return result.scalars().all()


# ============== Team Invitations ==============

@router.post("/profile/{college_id}/invite", response_model=List[TeamInviteResponse])
async def invite_team_members(
    college_id: str,
    request: TeamInviteBulkRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Send invitations to team members"""
    result = await db.execute(
        select(CollegeProfile).where(CollegeProfile.id == college_id)
    )
    college = result.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    invitations = []
    for inv_data in request.invitations:
        # Generate unique token
        token = secrets.token_urlsafe(32)

        invitation = CollegeInvitation(
            college_id=college_id,
            email=inv_data.email,
            name=inv_data.name,
            naac_role=inv_data.naac_role,
            department_id=inv_data.department_id,
            criterion_number=inv_data.criterion_number,
            invite_token=token,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(invitation)
        invitations.append(invitation)

        # TODO: Send email in background
        # background_tasks.add_task(send_invite_email, inv_data.email, token, college.name)

    # Update progress
    progress_result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.college_id == college_id)
    )
    progress = progress_result.scalar_one_or_none()
    if progress:
        progress.invitations_sent += len(invitations)
        if not progress.team_invited and progress.invitations_sent >= 1:
            progress.team_invited = True
            progress.team_at = datetime.utcnow()
            progress.current_step = OnboardingStep.ROLE_ASSIGNMENT
            college.onboarding_step = OnboardingStep.ROLE_ASSIGNMENT
        progress.calculate_completion()

    await db.commit()

    # Build response with invite links
    response = []
    for inv in invitations:
        await db.refresh(inv)
        response.append(TeamInviteResponse(
            id=str(inv.id),
            email=inv.email,
            name=inv.name,
            naac_role=inv.naac_role,
            status=inv.status.value,
            invite_link=f"/onboarding/accept-invite?token={inv.invite_token}",
            expires_at=inv.expires_at
        ))

    return response


@router.get("/profile/{college_id}/invitations", response_model=List[TeamInviteResponse])
async def get_invitations(
    college_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all invitations for a college"""
    result = await db.execute(
        select(CollegeInvitation).where(CollegeInvitation.college_id == college_id)
    )
    invitations = result.scalars().all()

    return [
        TeamInviteResponse(
            id=str(inv.id),
            email=inv.email,
            name=inv.name,
            naac_role=inv.naac_role,
            status=inv.status.value,
            invite_link=f"/onboarding/accept-invite?token={inv.invite_token}",
            expires_at=inv.expires_at
        )
        for inv in invitations
    ]


@router.post("/accept-invite")
async def accept_invitation(
    request: InvitationAcceptRequest,
    db: AsyncSession = Depends(get_db)
):
    """Accept an invitation and create user account"""
    # Find invitation
    result = await db.execute(
        select(CollegeInvitation).where(CollegeInvitation.invite_token == request.token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invitation already used or expired")

    if invitation.expires_at < datetime.utcnow():
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(User.email == invitation.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Create user
    user = User(
        email=invitation.email,
        username=invitation.email.split("@")[0],
        full_name=request.full_name,
        hashed_password=get_password_hash(request.password),
        role=UserRole.FACULTY,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.flush()

    # Update invitation
    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_by_id = user.id
    invitation.accepted_at = datetime.utcnow()

    # Update progress
    progress_result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.college_id == invitation.college_id)
    )
    progress = progress_result.scalar_one_or_none()
    if progress:
        progress.invitations_accepted += 1
        progress.team_members_count += 1

    # TODO: Assign NAAC role to user
    # This would involve creating a UserNAACRole entry

    await db.commit()

    # Generate access token
    access_token = create_access_token(data={"sub": user.email})

    return {
        "message": "Invitation accepted successfully",
        "user_id": str(user.id),
        "access_token": access_token,
        "token_type": "bearer"
    }


# ============== Onboarding Progress ==============

@router.get("/profile/{college_id}/progress", response_model=OnboardingProgressResponse)
async def get_onboarding_progress(
    college_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get onboarding progress for a college"""
    result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.college_id == college_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        raise HTTPException(status_code=404, detail="Onboarding progress not found")

    # Determine next action
    next_action = "Complete registration"
    if progress.registration_completed and not progress.profile_completed:
        next_action = "Complete college profile"
    elif progress.profile_completed and not progress.departments_added:
        next_action = "Add departments"
    elif progress.departments_added and not progress.programs_added:
        next_action = "Add programs"
    elif progress.programs_added and not progress.team_invited:
        next_action = "Invite team members"
    elif progress.team_invited and not progress.roles_assigned:
        next_action = "Assign NAAC roles"
    elif progress.roles_assigned:
        next_action = "Start entering accreditation data"

    # Build checklist
    checklist = [
        {"id": "registration", "title": "College Registration", "completed": progress.registration_completed, "required": True},
        {"id": "profile", "title": "Complete Profile", "completed": progress.profile_completed, "required": True},
        {"id": "departments", "title": "Add Departments", "completed": progress.departments_added, "required": True},
        {"id": "programs", "title": "Add Programs", "completed": progress.programs_added, "required": True},
        {"id": "team", "title": "Invite Team", "completed": progress.team_invited, "required": True},
        {"id": "roles", "title": "Assign Roles", "completed": progress.roles_assigned, "required": True},
    ]

    return OnboardingProgressResponse(
        current_step=progress.current_step.value,
        completion_percentage=progress.completion_percentage,
        registration_completed=progress.registration_completed,
        profile_completed=progress.profile_completed,
        departments_added=progress.departments_added,
        programs_added=progress.programs_added,
        team_invited=progress.team_invited,
        roles_assigned=progress.roles_assigned,
        departments_count=progress.departments_count,
        programs_count=progress.programs_count,
        team_members_count=progress.team_members_count,
        invitations_sent=progress.invitations_sent,
        invitations_accepted=progress.invitations_accepted,
        next_action=next_action,
        checklist=checklist
    )


@router.post("/profile/{college_id}/complete-onboarding")
async def complete_onboarding(
    college_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Mark onboarding as completed"""
    result = await db.execute(
        select(CollegeProfile).where(CollegeProfile.id == college_id)
    )
    college = result.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")

    progress_result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.college_id == college_id)
    )
    progress = progress_result.scalar_one_or_none()

    # Check if all required steps are completed
    if not all([
        progress.registration_completed,
        progress.profile_completed,
        progress.departments_added,
        progress.programs_added
    ]):
        raise HTTPException(
            status_code=400,
            detail="Please complete all required steps before finishing onboarding"
        )

    # Mark as completed
    college.onboarding_completed = True
    college.onboarding_completed_at = datetime.utcnow()
    college.onboarding_step = OnboardingStep.COMPLETED

    progress.current_step = OnboardingStep.COMPLETED
    progress.completed_at = datetime.utcnow()
    progress.completion_percentage = 100

    await db.commit()

    return {
        "message": "Onboarding completed successfully! You can now start entering accreditation data.",
        "redirect": "/accreditation/dashboard"
    }
