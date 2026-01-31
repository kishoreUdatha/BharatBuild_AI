"""
Project Guidance & Review System API (Merged)

Comprehensive API for managing student project lifecycle:
- Project registration & guide assignment
- Phase-wise reviews with rubric scoring
- Phase locking mechanism
- Viva preparation
- NAAC evidence generation
- Dashboard endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project_review import (
    ReviewProject, ProjectTeamMember, ProjectReview,
    ReviewPanelMember, ReviewScore, VivaQuestion, ProjectAuditLog, GuideAllocation,
    ReviewType, ReviewStatus, PhaseStatus, ProjectType, ReviewDecision, VivaReadiness,
    REVIEW_CRITERIA, SCORING_CRITERIA, get_tech_criteria
)

router = APIRouter()


# ==================== Schemas ====================

class TeamMemberCreate(BaseModel):
    name: str
    roll_number: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = "Member"


class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    project_type: str = "mini_project"
    technology_stack: Optional[str] = None
    domain: Optional[str] = None
    team_name: Optional[str] = None
    semester: Optional[int] = None
    batch: Optional[str] = None
    department: Optional[str] = None
    academic_year: Optional[str] = None
    github_url: Optional[str] = None
    guide_name: Optional[str] = None
    guide_id: Optional[str] = None
    team_members: Optional[List[TeamMemberCreate]] = []


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    project_type: str
    technology_stack: Optional[str]
    domain: Optional[str]
    team_name: Optional[str]
    team_size: int
    semester: Optional[int]
    batch: Optional[str]
    department: Optional[str]
    guide_name: Optional[str]
    github_url: Optional[str]
    demo_url: Optional[str]
    current_review: int
    current_phase: int
    total_score: float
    average_score: float
    ai_usage_percentage: float
    plagiarism_percentage: float
    viva_readiness: str
    is_approved: bool
    is_completed: bool
    phase_1_locked: bool
    phase_2_locked: bool
    phase_3_locked: bool
    phase_4_locked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PanelMemberCreate(BaseModel):
    name: str
    designation: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    role: str = "member"
    is_lead: bool = False


class ReviewCreate(BaseModel):
    project_id: str
    review_type: str
    scheduled_date: datetime
    scheduled_time: Optional[str] = None
    venue: Optional[str] = None
    duration_minutes: int = 30
    panel_members: Optional[List[PanelMemberCreate]] = []


class ReviewScoreSubmit(BaseModel):
    innovation_score: float = Field(ge=0, le=20)
    technical_score: float = Field(ge=0, le=25)
    implementation_score: float = Field(ge=0, le=25)
    documentation_score: float = Field(ge=0, le=15)
    presentation_score: float = Field(ge=0, le=15)
    comments: Optional[str] = None
    rubric_scores: Optional[Dict[str, float]] = None


class ReviewFeedbackSubmit(BaseModel):
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    suggestions: Optional[str] = None
    overall_feedback: Optional[str] = None
    action_items: Optional[str] = None


class StudentSubmission(BaseModel):
    """Student submission for a review phase"""
    submission_url: Optional[str] = None
    submission_notes: Optional[str] = None
    github_url: Optional[str] = None
    demo_url: Optional[str] = None


class ReviewDecisionSubmit(BaseModel):
    decision: str  # approved, revision_needed, rejected
    feedback: Optional[str] = None
    action_items: Optional[str] = None


class GuideAssignRequest(BaseModel):
    project_id: str
    guide_id: str
    guide_name: str


class VivaQuestionCreate(BaseModel):
    question: str
    expected_answer: Optional[str] = None
    category: Optional[str] = None
    difficulty: str = "medium"


class ReviewResponse(BaseModel):
    id: str
    project_id: str
    project_title: Optional[str] = None
    review_type: str
    review_number: int
    scheduled_date: datetime
    scheduled_time: Optional[str]
    venue: Optional[str]
    status: str
    phase_status: str
    decision: Optional[str]
    total_score: float
    innovation_score: float
    technical_score: float
    implementation_score: float
    documentation_score: float
    presentation_score: float
    overall_feedback: Optional[str]
    is_locked: bool
    panel_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Project Endpoints ====================

@router.post("/projects", response_model=ProjectResponse)
async def register_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new student project"""
    # Get a default student ID (in production, this would come from auth)
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="No users found in system")

    project = ReviewProject(
        title=project_data.title,
        description=project_data.description,
        project_type=ProjectType(project_data.project_type),
        technology_stack=project_data.technology_stack,
        domain=project_data.domain,
        team_name=project_data.team_name,
        team_size=len(project_data.team_members) + 1 if project_data.team_members else 1,
        semester=project_data.semester,
        batch=project_data.batch,
        department=project_data.department,
        academic_year=project_data.academic_year,
        github_url=project_data.github_url,
        guide_name=project_data.guide_name,
        guide_id=UUID(project_data.guide_id) if project_data.guide_id else None,
        student_id=user.id,
    )
    db.add(project)
    await db.flush()

    # Add team members
    if project_data.team_members:
        for member in project_data.team_members:
            team_member = ProjectTeamMember(
                project_id=project.id,
                name=member.name,
                roll_number=member.roll_number,
                email=member.email,
                role=member.role,
            )
            db.add(team_member)

    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=str(project.id),
        title=project.title,
        description=project.description,
        project_type=project.project_type.value,
        technology_stack=project.technology_stack,
        domain=project.domain,
        team_name=project.team_name,
        team_size=project.team_size,
        semester=project.semester,
        batch=project.batch,
        department=project.department,
        guide_name=project.guide_name,
        github_url=project.github_url,
        demo_url=project.demo_url,
        current_review=project.current_review,
        current_phase=project.current_phase,
        total_score=project.total_score,
        average_score=project.average_score,
        ai_usage_percentage=project.ai_usage_percentage,
        plagiarism_percentage=project.plagiarism_percentage,
        viva_readiness=project.viva_readiness.value,
        is_approved=project.is_approved,
        is_completed=project.is_completed,
        phase_1_locked=project.phase_1_locked,
        phase_2_locked=project.phase_2_locked,
        phase_3_locked=project.phase_3_locked,
        phase_4_locked=project.phase_4_locked,
        created_at=project.created_at,
    )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    project_type: Optional[str] = None,
    semester: Optional[int] = None,
    batch: Optional[str] = None,
    department: Optional[str] = None,
    guide_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all registered projects"""
    query = select(ReviewProject)

    if project_type:
        query = query.where(ReviewProject.project_type == ProjectType(project_type))
    if semester:
        query = query.where(ReviewProject.semester == semester)
    if batch:
        query = query.where(ReviewProject.batch == batch)
    if department:
        query = query.where(ReviewProject.department.ilike(f"%{department}%"))
    if guide_id:
        query = query.where(ReviewProject.guide_id == UUID(guide_id))

    query = query.order_by(ReviewProject.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    projects = result.scalars().all()

    return [
        ProjectResponse(
            id=str(p.id),
            title=p.title,
            description=p.description,
            project_type=p.project_type.value,
            technology_stack=p.technology_stack,
            domain=p.domain,
            team_name=p.team_name,
            team_size=p.team_size,
            semester=p.semester,
            batch=p.batch,
            department=p.department,
            guide_name=p.guide_name,
            github_url=p.github_url,
            demo_url=p.demo_url,
            current_review=p.current_review,
            current_phase=p.current_phase,
            total_score=p.total_score,
            average_score=p.average_score,
            ai_usage_percentage=p.ai_usage_percentage,
            plagiarism_percentage=p.plagiarism_percentage,
            viva_readiness=p.viva_readiness.value,
            is_approved=p.is_approved,
            is_completed=p.is_completed,
            phase_1_locked=p.phase_1_locked,
            phase_2_locked=p.phase_2_locked,
            phase_3_locked=p.phase_3_locked,
            phase_4_locked=p.phase_4_locked,
            created_at=p.created_at,
        )
        for p in projects
    ]


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get project details with reviews and team members"""
    result = await db.execute(
        select(ReviewProject)
        .options(
            selectinload(ReviewProject.reviews).selectinload(ProjectReview.panel_members),
            selectinload(ReviewProject.team_members),
            selectinload(ReviewProject.viva_questions)
        )
        .where(ReviewProject.id == UUID(project_id))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": str(project.id),
        "title": project.title,
        "description": project.description,
        "project_type": project.project_type.value,
        "technology_stack": project.technology_stack,
        "domain": project.domain,
        "team_name": project.team_name,
        "team_size": project.team_size,
        "semester": project.semester,
        "batch": project.batch,
        "department": project.department,
        "guide_name": project.guide_name,
        "github_url": project.github_url,
        "demo_url": project.demo_url,
        "current_review": project.current_review,
        "current_phase": project.current_phase,
        "total_score": project.total_score,
        "average_score": project.average_score,
        "ai_usage_percentage": project.ai_usage_percentage,
        "plagiarism_percentage": project.plagiarism_percentage,
        "viva_readiness": project.viva_readiness.value,
        "is_approved": project.is_approved,
        "is_completed": project.is_completed,
        "phase_locked": {
            1: project.phase_1_locked,
            2: project.phase_2_locked,
            3: project.phase_3_locked,
            4: project.phase_4_locked,
        },
        "created_at": project.created_at,
        "team_members": [
            {
                "id": str(m.id),
                "name": m.name,
                "roll_number": m.roll_number,
                "email": m.email,
                "role": m.role,
            }
            for m in project.team_members
        ],
        "reviews": [
            {
                "id": str(r.id),
                "review_type": r.review_type.value,
                "review_number": r.review_number,
                "scheduled_date": r.scheduled_date,
                "status": r.status.value,
                "phase_status": r.phase_status.value if r.phase_status else "not_started",
                "decision": r.decision.value if r.decision else None,
                "total_score": r.total_score,
                "is_locked": r.is_locked,
                "panel_count": len(r.panel_members),
            }
            for r in sorted(project.reviews, key=lambda x: x.review_number)
        ],
        "viva_questions_count": len(project.viva_questions),
    }


# ==================== Guide Assignment ====================

@router.post("/assign-guide")
async def assign_guide(
    request: GuideAssignRequest,
    db: AsyncSession = Depends(get_db)
):
    """Assign a guide to a project"""
    result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == UUID(request.project_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.guide_id = UUID(request.guide_id)
    project.guide_name = request.guide_name
    project.guide_assigned_at = datetime.utcnow()

    alloc_result = await db.execute(
        select(GuideAllocation).where(GuideAllocation.guide_id == UUID(request.guide_id))
    )
    allocation = alloc_result.scalar_one_or_none()
    if allocation:
        if project.project_type == ProjectType.mini_project:
            allocation.current_mini_projects += 1
        else:
            allocation.current_major_projects += 1

    audit = ProjectAuditLog(
        project_id=project.id,
        action="guide_assigned",
        details={"guide_name": request.guide_name, "guide_id": request.guide_id},
        performer_name=request.guide_name,
    )
    db.add(audit)

    await db.commit()

    return {"success": True, "message": f"Guide {request.guide_name} assigned successfully"}


@router.get("/guide-allocations")
async def get_guide_allocations(
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all guide allocations"""
    query = select(GuideAllocation).where(GuideAllocation.is_active == True)
    if department:
        query = query.where(GuideAllocation.department.ilike(f"%{department}%"))

    result = await db.execute(query)
    allocations = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "guide_id": str(a.guide_id),
            "guide_name": a.guide_name,
            "department": a.department,
            "max_mini_projects": a.max_mini_projects,
            "max_major_projects": a.max_major_projects,
            "current_mini_projects": a.current_mini_projects,
            "current_major_projects": a.current_major_projects,
            "available_mini_slots": a.available_mini_slots,
            "available_major_slots": a.available_major_slots,
        }
        for a in allocations
    ]


# ==================== Review Endpoints ====================

@router.post("/reviews", response_model=ReviewResponse)
async def schedule_review(
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """Schedule a new project review"""
    result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == UUID(review_data.project_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    review_type = ReviewType(review_data.review_type)
    review_number_map = {
        ReviewType.review_1: 1,
        ReviewType.review_2: 2,
        ReviewType.review_3: 3,
        ReviewType.final_review: 4,
    }
    review_number = review_number_map[review_type]

    existing = await db.execute(
        select(ProjectReview).where(
            and_(
                ProjectReview.project_id == UUID(review_data.project_id),
                ProjectReview.review_type == review_type
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Review {review_number} already scheduled")

    review = ProjectReview(
        project_id=UUID(review_data.project_id),
        review_type=review_type,
        review_number=review_number,
        scheduled_date=review_data.scheduled_date,
        scheduled_time=review_data.scheduled_time,
        venue=review_data.venue,
        duration_minutes=review_data.duration_minutes,
        status=ReviewStatus.scheduled,
        phase_status=PhaseStatus.not_started,
    )
    db.add(review)
    await db.flush()

    if review_data.panel_members:
        for member in review_data.panel_members:
            panel_member = ReviewPanelMember(
                review_id=review.id,
                name=member.name,
                designation=member.designation,
                department=member.department,
                email=member.email,
                role=member.role,
                is_lead=member.is_lead,
            )
            db.add(panel_member)

    await db.commit()
    await db.refresh(review)

    return ReviewResponse(
        id=str(review.id),
        project_id=str(review.project_id),
        project_title=project.title,
        review_type=review.review_type.value,
        review_number=review.review_number,
        scheduled_date=review.scheduled_date,
        scheduled_time=review.scheduled_time,
        venue=review.venue,
        status=review.status.value,
        phase_status=review.phase_status.value if review.phase_status else "not_started",
        decision=review.decision.value if review.decision else None,
        total_score=review.total_score,
        innovation_score=review.innovation_score,
        technical_score=review.technical_score,
        implementation_score=review.implementation_score,
        documentation_score=review.documentation_score,
        presentation_score=review.presentation_score,
        overall_feedback=review.overall_feedback,
        is_locked=review.is_locked,
        panel_count=len(review_data.panel_members) if review_data.panel_members else 0,
        created_at=review.created_at,
    )


@router.get("/reviews")
async def list_reviews(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all scheduled reviews"""
    query = (
        select(ProjectReview)
        .options(selectinload(ProjectReview.panel_members))
        .join(ReviewProject)
    )

    if status:
        query = query.where(ProjectReview.status == ReviewStatus(status))
    if project_id:
        query = query.where(ProjectReview.project_id == UUID(project_id))
    if from_date:
        query = query.where(ProjectReview.scheduled_date >= from_date)
    if to_date:
        query = query.where(ProjectReview.scheduled_date <= to_date)

    query = query.order_by(ProjectReview.scheduled_date.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    reviews = result.scalars().all()

    project_ids = [r.project_id for r in reviews]
    if project_ids:
        projects_result = await db.execute(
            select(ReviewProject).where(ReviewProject.id.in_(project_ids))
        )
        projects = {str(p.id): p.title for p in projects_result.scalars().all()}
    else:
        projects = {}

    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "project_title": projects.get(str(r.project_id), "Unknown"),
            "review_type": r.review_type.value,
            "review_number": r.review_number,
            "scheduled_date": r.scheduled_date,
            "scheduled_time": r.scheduled_time,
            "venue": r.venue,
            "status": r.status.value,
            "phase_status": r.phase_status.value if r.phase_status else "not_started",
            "decision": r.decision.value if r.decision else None,
            "total_score": r.total_score,
            "is_locked": r.is_locked,
            "panel_count": len(r.panel_members),
        }
        for r in reviews
    ]


@router.get("/reviews/{review_id}")
async def get_review(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get review details with scores and rubric"""
    result = await db.execute(
        select(ProjectReview)
        .options(
            selectinload(ProjectReview.panel_members),
            selectinload(ProjectReview.scores)
        )
        .where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    project_result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == review.project_id)
    )
    project = project_result.scalar_one_or_none()

    criteria = REVIEW_CRITERIA.get(review.review_type.value, {})
    tech_criteria = get_tech_criteria(project.technology_stack) if project else []

    return {
        "id": str(review.id),
        "project_id": str(review.project_id),
        "project_title": project.title if project else None,
        "technology_stack": project.technology_stack if project else None,
        "domain": project.domain if project else None,
        "review_type": review.review_type.value,
        "review_number": review.review_number,
        "review_name": criteria.get("name", f"Review {review.review_number}"),
        "focus_areas": criteria.get("focus", []),
        "deliverables": criteria.get("deliverables", []),
        "rubric": criteria.get("rubric", {}),
        "tech_specific_criteria": tech_criteria,
        "scheduled_date": review.scheduled_date,
        "scheduled_time": review.scheduled_time,
        "venue": review.venue,
        "duration_minutes": review.duration_minutes,
        "status": review.status.value,
        "phase_status": review.phase_status.value if review.phase_status else "not_started",
        "decision": review.decision.value if review.decision else None,
        "is_locked": review.is_locked,
        "scores": {
            "innovation": review.innovation_score,
            "technical": review.technical_score,
            "implementation": review.implementation_score,
            "documentation": review.documentation_score,
            "presentation": review.presentation_score,
            "total": review.total_score,
        },
        "rubric_scores": review.rubric_scores,
        "scoring_criteria": SCORING_CRITERIA,
        "feedback": {
            "strengths": review.strengths,
            "weaknesses": review.weaknesses,
            "suggestions": review.suggestions,
            "overall": review.overall_feedback,
            "action_items": review.action_items,
        },
        "panel_members": [
            {
                "id": str(m.id),
                "name": m.name,
                "designation": m.designation,
                "role": m.role,
                "is_lead": m.is_lead,
            }
            for m in review.panel_members
        ],
        "individual_scores": [
            {
                "id": str(s.id),
                "panel_member_id": str(s.panel_member_id),
                "innovation": s.innovation_score,
                "technical": s.technical_score,
                "implementation": s.implementation_score,
                "documentation": s.documentation_score,
                "presentation": s.presentation_score,
                "total": s.total_score,
                "rubric_scores": s.rubric_scores,
                "comments": s.comments,
            }
            for s in review.scores
        ],
        "started_at": review.started_at,
        "completed_at": review.completed_at,
    }


@router.post("/reviews/{review_id}/start")
async def start_review(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Start a review session"""
    result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.is_locked:
        raise HTTPException(status_code=400, detail="This phase is locked")

    review.status = ReviewStatus.in_progress
    review.phase_status = PhaseStatus.under_review
    review.started_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "Review started", "started_at": review.started_at}


@router.post("/reviews/{review_id}/scores")
async def submit_score(
    review_id: str,
    panel_member_id: str,
    score_data: ReviewScoreSubmit,
    db: AsyncSession = Depends(get_db)
):
    """Submit score by a panel member"""
    result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.is_locked:
        raise HTTPException(status_code=400, detail="This phase is locked")

    panel_result = await db.execute(
        select(ReviewPanelMember).where(ReviewPanelMember.id == UUID(panel_member_id))
    )
    panel_member = panel_result.scalar_one_or_none()
    if not panel_member:
        raise HTTPException(status_code=404, detail="Panel member not found")

    existing = await db.execute(
        select(ReviewScore).where(
            and_(
                ReviewScore.review_id == UUID(review_id),
                ReviewScore.panel_member_id == UUID(panel_member_id)
            )
        )
    )
    existing_score = existing.scalar_one_or_none()

    if existing_score:
        existing_score.innovation_score = score_data.innovation_score
        existing_score.technical_score = score_data.technical_score
        existing_score.implementation_score = score_data.implementation_score
        existing_score.documentation_score = score_data.documentation_score
        existing_score.presentation_score = score_data.presentation_score
        existing_score.comments = score_data.comments
        existing_score.rubric_scores = score_data.rubric_scores
        existing_score.calculate_total()
        existing_score.updated_at = datetime.utcnow()
    else:
        score = ReviewScore(
            review_id=UUID(review_id),
            panel_member_id=UUID(panel_member_id),
            innovation_score=score_data.innovation_score,
            technical_score=score_data.technical_score,
            implementation_score=score_data.implementation_score,
            documentation_score=score_data.documentation_score,
            presentation_score=score_data.presentation_score,
            comments=score_data.comments,
            rubric_scores=score_data.rubric_scores,
        )
        score.calculate_total()
        db.add(score)

    await db.commit()
    await _recalculate_review_scores(db, UUID(review_id))

    return {"success": True, "message": "Score submitted"}


@router.post("/reviews/{review_id}/feedback")
async def submit_feedback(
    review_id: str,
    feedback: ReviewFeedbackSubmit,
    db: AsyncSession = Depends(get_db)
):
    """Submit overall feedback for a review"""
    result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.strengths = feedback.strengths
    review.weaknesses = feedback.weaknesses
    review.suggestions = feedback.suggestions
    review.overall_feedback = feedback.overall_feedback
    review.action_items = feedback.action_items

    await db.commit()

    return {"success": True, "message": "Feedback submitted"}


@router.post("/reviews/{review_id}/decision")
async def submit_decision(
    review_id: str,
    decision_data: ReviewDecisionSubmit,
    db: AsyncSession = Depends(get_db)
):
    """Submit review decision (approve/revise)"""
    result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.decision = ReviewDecision(decision_data.decision)
    review.overall_feedback = decision_data.feedback
    review.action_items = decision_data.action_items

    if decision_data.decision == "approved":
        review.phase_status = PhaseStatus.approved
    else:
        review.phase_status = PhaseStatus.revision_needed

    await db.commit()

    return {"success": True, "message": f"Decision recorded: {decision_data.decision}"}


@router.post("/reviews/{review_id}/complete")
async def complete_review(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Complete a review and update project status"""
    result = await db.execute(
        select(ProjectReview)
        .options(selectinload(ProjectReview.scores))
        .where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.status = ReviewStatus.completed
    review.completed_at = datetime.utcnow()

    project_result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == review.project_id)
    )
    project = project_result.scalar_one_or_none()

    if project:
        project.current_review = review.review_number
        project.current_phase = review.review_number + 1 if review.review_number < 4 else 4

        if review.review_type == ReviewType.final_review:
            project.is_completed = True
            if review.total_score >= 50:
                project.is_approved = True

        all_reviews = await db.execute(
            select(ProjectReview).where(
                and_(
                    ProjectReview.project_id == project.id,
                    ProjectReview.status == ReviewStatus.completed
                )
            )
        )
        completed_reviews = all_reviews.scalars().all()
        if completed_reviews:
            total = sum(r.total_score for r in completed_reviews)
            project.total_score = total
            project.average_score = total / len(completed_reviews)

    audit = ProjectAuditLog(
        project_id=review.project_id,
        action="review_completed",
        details={
            "review_number": review.review_number,
            "total_score": review.total_score,
            "decision": review.decision.value if review.decision else None
        },
        phase_number=review.review_number,
    )
    db.add(audit)

    # Auto-schedule next review if not final review
    next_review_id = None
    next_review_type = None
    if review.review_type != ReviewType.final_review:
        next_review_map = {
            ReviewType.review_1: (ReviewType.review_2, 2),
            ReviewType.review_2: (ReviewType.review_3, 3),
            ReviewType.review_3: (ReviewType.final_review, 4),
        }

        next_type, next_number = next_review_map.get(review.review_type, (None, None))

        if next_type:
            # Check if next review already exists
            existing_next = await db.execute(
                select(ProjectReview).where(
                    and_(
                        ProjectReview.project_id == review.project_id,
                        ProjectReview.review_type == next_type
                    )
                )
            )

            if not existing_next.scalar_one_or_none():
                # Create next review - scheduled for 2 weeks from now
                next_review = ProjectReview(
                    project_id=review.project_id,
                    review_type=next_type,
                    review_number=next_number,
                    scheduled_date=datetime.utcnow() + timedelta(weeks=2),
                    scheduled_time="10:00 AM",
                    venue="To be assigned",
                    status=ReviewStatus.scheduled,
                    phase_status=PhaseStatus.not_started,
                )
                db.add(next_review)
                next_review_id = str(next_review.id)
                next_review_type = next_type.value

                # Log next review scheduling
                audit_next = ProjectAuditLog(
                    project_id=review.project_id,
                    action="review_auto_scheduled",
                    details={
                        "review_number": next_number,
                        "review_type": next_type.value,
                        "scheduled_after": review.review_type.value
                    },
                    phase_number=next_number,
                )
                db.add(audit_next)

    await db.commit()

    return {
        "success": True,
        "message": "Review completed",
        "total_score": review.total_score,
        "project_average": project.average_score if project else 0,
        "next_review_scheduled": next_review_id is not None,
        "next_review_type": next_review_type,
        "next_review_id": next_review_id,
    }


# ==================== Student Endpoints ====================

@router.post("/reviews/{review_id}/submit")
async def student_submit_for_review(
    review_id: str,
    submission: StudentSubmission,
    db: AsyncSession = Depends(get_db)
):
    """Student submits their work for a review phase"""
    result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status == ReviewStatus.completed:
        raise HTTPException(status_code=400, detail="Review already completed")

    if review.is_locked:
        raise HTTPException(status_code=400, detail="This phase is locked")

    # Update review with submission
    review.submission_url = submission.submission_url
    review.submission_notes = submission.submission_notes
    review.submitted_at = datetime.utcnow()
    review.phase_status = PhaseStatus.submitted

    # Update project URLs if provided
    project_result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == review.project_id)
    )
    project = project_result.scalar_one_or_none()
    if project:
        if submission.github_url:
            project.github_url = submission.github_url
        if submission.demo_url:
            project.demo_url = submission.demo_url

    # Log submission
    audit = ProjectAuditLog(
        project_id=review.project_id,
        action="student_submitted",
        details={
            "review_number": review.review_number,
            "submission_url": submission.submission_url
        },
        phase_number=review.review_number,
    )
    db.add(audit)

    await db.commit()

    return {
        "success": True,
        "message": f"Submitted for {review.review_type.value}",
        "submitted_at": review.submitted_at.isoformat(),
        "phase_status": review.phase_status.value
    }


@router.get("/student/my-project")
async def get_student_project(
    student_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get student's project with all reviews and feedback"""
    # For demo, get first project or by student_id
    if student_id:
        result = await db.execute(
            select(ReviewProject)
            .options(
                selectinload(ReviewProject.reviews).selectinload(ProjectReview.scores),
                selectinload(ReviewProject.team_members)
            )
            .where(ReviewProject.student_id == UUID(student_id))
        )
    else:
        # Get first project for demo
        result = await db.execute(
            select(ReviewProject)
            .options(
                selectinload(ReviewProject.reviews).selectinload(ProjectReview.scores),
                selectinload(ReviewProject.team_members)
            )
            .limit(1)
        )

    project = result.scalar_one_or_none()
    if not project:
        return None

    # Build reviews with feedback
    reviews_data = []
    for review in sorted(project.reviews, key=lambda r: r.review_number):
        reviews_data.append({
            "id": str(review.id),
            "review_type": review.review_type.value,
            "review_number": review.review_number,
            "status": review.status.value,
            "phase_status": review.phase_status.value,
            "scheduled_date": review.scheduled_date.isoformat() if review.scheduled_date else None,
            "scheduled_time": review.scheduled_time,
            "venue": review.venue,
            "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
            "submission_url": review.submission_url,
            "submission_notes": review.submission_notes,
            "completed_at": review.completed_at.isoformat() if review.completed_at else None,
            "total_score": review.total_score,
            "decision": review.decision.value if review.decision else None,
            "is_locked": review.is_locked,
            "feedback": {
                "strengths": review.strengths,
                "weaknesses": review.weaknesses,
                "suggestions": review.suggestions,
                "overall": review.overall_feedback,
                "action_items": review.action_items
            },
            "scores": {
                "innovation": review.innovation_score,
                "technical": review.technical_score,
                "implementation": review.implementation_score,
                "documentation": review.documentation_score,
                "presentation": review.presentation_score
            }
        })

    # Calculate progress
    total_phases = 4
    completed_phases = sum(1 for r in project.reviews if r.status == ReviewStatus.completed)
    progress_percent = (completed_phases / total_phases) * 100

    # Get current/next review
    current_review = None
    for review in sorted(project.reviews, key=lambda r: r.review_number):
        if review.status != ReviewStatus.completed:
            current_review = review.review_type.value
            break

    return {
        "id": str(project.id),
        "title": project.title,
        "description": project.description,
        "project_type": project.project_type.value,
        "technology_stack": project.technology_stack,
        "domain": project.domain,
        "team_name": project.team_name,
        "team_size": project.team_size,
        "semester": project.semester,
        "batch": project.batch,
        "department": project.department,
        "guide_name": project.guide_name,
        "github_url": project.github_url,
        "demo_url": project.demo_url,
        "current_phase": project.current_phase,
        "current_review": current_review,
        "total_score": project.total_score,
        "average_score": project.average_score,
        "is_approved": project.is_approved,
        "is_completed": project.is_completed,
        "progress_percent": progress_percent,
        "team_members": [
            {"name": m.name, "roll_number": m.roll_number, "role": m.role}
            for m in project.team_members
        ],
        "reviews": reviews_data
    }


@router.get("/faculty/pending-submissions")
async def get_pending_submissions(
    db: AsyncSession = Depends(get_db)
):
    """Get reviews that students have submitted but not yet reviewed by faculty"""
    result = await db.execute(
        select(ProjectReview)
        .options(selectinload(ProjectReview.project))
        .where(
            and_(
                ProjectReview.phase_status == PhaseStatus.submitted,
                ProjectReview.status != ReviewStatus.completed
            )
        )
        .order_by(ProjectReview.submitted_at.desc())
    )

    reviews = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "project_title": r.project.title if r.project else "Unknown",
            "team_name": r.project.team_name if r.project else "Unknown",
            "review_type": r.review_type.value,
            "review_number": r.review_number,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "submission_url": r.submission_url,
            "submission_notes": r.submission_notes,
            "status": r.status.value,
            "phase_status": r.phase_status.value
        }
        for r in reviews
    ]


# ==================== Phase Locking ====================

@router.post("/reviews/{review_id}/lock")
async def lock_phase(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Lock a phase after approval"""
    result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_locked = True
    review.locked_at = datetime.utcnow()
    review.phase_status = PhaseStatus.locked

    project_result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == review.project_id)
    )
    project = project_result.scalar_one_or_none()
    if project:
        project.lock_phase(review.review_number)

    audit = ProjectAuditLog(
        project_id=review.project_id,
        action="phase_locked",
        phase_number=review.review_number,
    )
    db.add(audit)

    await db.commit()

    return {"success": True, "message": f"Phase {review.review_number} locked"}


@router.post("/reviews/{review_id}/unlock")
async def unlock_phase(
    review_id: str,
    reason: str = Query(..., description="Reason for unlocking"),
    db: AsyncSession = Depends(get_db)
):
    """Unlock a phase (requires reason)"""
    result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_locked = False
    review.locked_at = None
    review.phase_status = PhaseStatus.in_progress

    project_result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == review.project_id)
    )
    project = project_result.scalar_one_or_none()
    if project:
        project.unlock_phase(review.review_number)

    audit = ProjectAuditLog(
        project_id=review.project_id,
        action="phase_unlocked",
        details={"reason": reason},
        phase_number=review.review_number,
    )
    db.add(audit)

    await db.commit()

    return {"success": True, "message": f"Phase {review.review_number} unlocked"}


# ==================== Viva Preparation ====================

@router.post("/projects/{project_id}/viva-questions")
async def add_viva_question(
    project_id: str,
    question_data: VivaQuestionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a viva question for a project"""
    result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == UUID(project_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    question = VivaQuestion(
        project_id=UUID(project_id),
        question=question_data.question,
        expected_answer=question_data.expected_answer,
        category=question_data.category,
        difficulty=question_data.difficulty,
    )
    db.add(question)
    await db.commit()

    return {"success": True, "message": "Viva question added", "id": str(question.id)}


@router.get("/projects/{project_id}/viva-questions")
async def get_viva_questions(
    project_id: str,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all viva questions for a project"""
    query = select(VivaQuestion).where(VivaQuestion.project_id == UUID(project_id))
    if category:
        query = query.where(VivaQuestion.category == category)

    result = await db.execute(query.order_by(VivaQuestion.created_at.desc()))
    questions = result.scalars().all()

    return [
        {
            "id": str(q.id),
            "question": q.question,
            "expected_answer": q.expected_answer,
            "category": q.category,
            "difficulty": q.difficulty,
            "student_answer": q.student_answer,
            "answer_score": q.answer_score,
            "answer_feedback": q.answer_feedback,
            "is_ai_generated": q.is_ai_generated,
        }
        for q in questions
    ]


@router.get("/projects/{project_id}/viva-readiness")
async def get_viva_readiness(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get viva readiness assessment"""
    result = await db.execute(
        select(ReviewProject)
        .options(
            selectinload(ReviewProject.reviews),
            selectinload(ReviewProject.viva_questions)
        )
        .where(ReviewProject.id == UUID(project_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    completed_reviews = [r for r in project.reviews if r.status == ReviewStatus.completed]
    questions_practiced = [q for q in project.viva_questions if q.student_answer]

    readiness_score = 0
    readiness_score += min(40, len(completed_reviews) * 10)
    readiness_score += min(30, len(questions_practiced) * 5)
    readiness_score += min(30, project.average_score * 0.3)

    if readiness_score >= 80:
        readiness = VivaReadiness.excellent
    elif readiness_score >= 60:
        readiness = VivaReadiness.ready
    elif readiness_score >= 40:
        readiness = VivaReadiness.needs_preparation
    else:
        readiness = VivaReadiness.not_ready

    project.viva_readiness = readiness
    project.viva_score = readiness_score
    await db.commit()

    return {
        "readiness": readiness.value,
        "score": readiness_score,
        "completed_reviews": len(completed_reviews),
        "total_reviews": 4,
        "questions_total": len(project.viva_questions),
        "questions_practiced": len(questions_practiced),
        "average_review_score": project.average_score,
        "recommendations": _get_viva_recommendations(readiness, completed_reviews, questions_practiced),
    }


def _get_viva_recommendations(readiness: VivaReadiness, reviews: list, practiced: list) -> list:
    """Get recommendations for viva preparation"""
    recommendations = []
    if len(reviews) < 4:
        recommendations.append("Complete all 4 reviews before the final viva")
    if len(practiced) < 10:
        recommendations.append("Practice more viva questions (minimum 10 recommended)")
    if readiness in [VivaReadiness.not_ready, VivaReadiness.needs_preparation]:
        recommendations.append("Review your project documentation thoroughly")
        recommendations.append("Prepare to explain your architecture decisions")
    return recommendations


# ==================== NAAC Evidence ====================

@router.get("/naac/project-allotment-list")
async def get_naac_project_allotment(
    academic_year: Optional[str] = None,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Generate NAAC project allotment list"""
    query = select(ReviewProject)
    if academic_year:
        query = query.where(ReviewProject.academic_year == academic_year)
    if department:
        query = query.where(ReviewProject.department.ilike(f"%{department}%"))

    result = await db.execute(query.order_by(ReviewProject.created_at))
    projects = result.scalars().all()

    return {
        "title": "Project Allotment List",
        "generated_at": datetime.utcnow().isoformat(),
        "academic_year": academic_year or "All",
        "department": department or "All",
        "total_projects": len(projects),
        "projects": [
            {
                "sl_no": i + 1,
                "title": p.title,
                "team_name": p.team_name,
                "guide_name": p.guide_name,
                "project_type": p.project_type.value,
                "semester": p.semester,
                "batch": p.batch,
                "domain": p.domain,
                "technology": p.technology_stack,
                "status": "Completed" if p.is_completed else "In Progress",
            }
            for i, p in enumerate(projects)
        ],
    }


@router.get("/naac/review-schedule")
async def get_naac_review_schedule(
    academic_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Generate NAAC review schedule report"""
    query = (
        select(ProjectReview)
        .options(selectinload(ProjectReview.panel_members))
        .join(ReviewProject)
    )

    if academic_year:
        query = query.where(ReviewProject.academic_year == academic_year)

    result = await db.execute(query.order_by(ProjectReview.scheduled_date))
    reviews = result.scalars().all()

    project_ids = list(set(r.project_id for r in reviews))
    if project_ids:
        projects_result = await db.execute(
            select(ReviewProject).where(ReviewProject.id.in_(project_ids))
        )
        projects = {str(p.id): p for p in projects_result.scalars().all()}
    else:
        projects = {}

    return {
        "title": "Project Review Schedule",
        "generated_at": datetime.utcnow().isoformat(),
        "academic_year": academic_year or "All",
        "total_reviews": len(reviews),
        "reviews": [
            {
                "project_title": projects.get(str(r.project_id)).title if str(r.project_id) in projects else "Unknown",
                "review_type": r.review_type.value,
                "scheduled_date": r.scheduled_date.isoformat() if r.scheduled_date else None,
                "venue": r.venue,
                "status": r.status.value,
                "panel": [m.name for m in r.panel_members],
                "score": r.total_score,
            }
            for r in reviews
        ],
    }


@router.get("/naac/approval-logs")
async def get_naac_approval_logs(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get approval/action logs for NAAC evidence"""
    query = select(ProjectAuditLog)
    if project_id:
        query = query.where(ProjectAuditLog.project_id == UUID(project_id))

    result = await db.execute(query.order_by(ProjectAuditLog.created_at.desc()).limit(100))
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "project_id": str(log.project_id),
            "action": log.action,
            "details": log.details,
            "phase_number": log.phase_number,
            "performed_by": log.performer_name,
            "role": log.performer_role,
            "timestamp": log.created_at.isoformat(),
        }
        for log in logs
    ]


# ==================== Dashboard Endpoints ====================

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics"""
    total_projects = await db.execute(select(func.count(ReviewProject.id)))
    total = total_projects.scalar() or 0

    mini_projects = await db.execute(
        select(func.count(ReviewProject.id))
        .where(ReviewProject.project_type == ProjectType.mini_project)
    )
    major_projects = await db.execute(
        select(func.count(ReviewProject.id))
        .where(ReviewProject.project_type == ProjectType.major_project)
    )

    scheduled = await db.execute(
        select(func.count(ProjectReview.id))
        .where(ProjectReview.status == ReviewStatus.scheduled)
    )
    completed = await db.execute(
        select(func.count(ProjectReview.id))
        .where(ProjectReview.status == ReviewStatus.completed)
    )

    avg_score = await db.execute(
        select(func.avg(ProjectReview.total_score))
        .where(ProjectReview.status == ReviewStatus.completed)
    )

    return {
        "total_projects": total,
        "mini_projects": mini_projects.scalar() or 0,
        "major_projects": major_projects.scalar() or 0,
        "scheduled_reviews": scheduled.scalar() or 0,
        "completed_reviews": completed.scalar() or 0,
        "average_score": round(avg_score.scalar() or 0, 2),
    }


@router.get("/dashboard/upcoming")
async def get_upcoming_reviews(
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming reviews for the next N days"""
    now = datetime.utcnow()
    end_date = now + timedelta(days=days)

    result = await db.execute(
        select(ProjectReview)
        .options(selectinload(ProjectReview.panel_members))
        .join(ReviewProject)
        .where(
            and_(
                ProjectReview.scheduled_date >= now,
                ProjectReview.scheduled_date <= end_date,
                ProjectReview.status == ReviewStatus.scheduled
            )
        )
        .order_by(ProjectReview.scheduled_date.asc())
    )
    reviews = result.scalars().all()

    project_ids = [r.project_id for r in reviews]
    if project_ids:
        projects_result = await db.execute(
            select(ReviewProject).where(ReviewProject.id.in_(project_ids))
        )
        projects = {str(p.id): p for p in projects_result.scalars().all()}
    else:
        projects = {}

    return [
        {
            "id": str(r.id),
            "project_id": str(r.project_id),
            "project_title": projects.get(str(r.project_id)).title if str(r.project_id) in projects else "Unknown",
            "team_name": projects.get(str(r.project_id)).team_name if str(r.project_id) in projects else None,
            "review_type": r.review_type.value,
            "review_number": r.review_number,
            "scheduled_date": r.scheduled_date,
            "scheduled_time": r.scheduled_time,
            "venue": r.venue,
            "panel_count": len(r.panel_members),
        }
        for r in reviews
    ]


@router.get("/criteria")
async def get_review_criteria():
    """Get review criteria and scoring rubric"""
    return {
        "review_types": REVIEW_CRITERIA,
        "scoring_criteria": SCORING_CRITERIA,
    }


# ==================== Helper Functions ====================

async def _recalculate_review_scores(db: AsyncSession, review_id: UUID):
    """Recalculate average scores from all panel member scores"""
    result = await db.execute(
        select(ReviewScore).where(ReviewScore.review_id == review_id)
    )
    scores = result.scalars().all()

    if not scores:
        return

    count = len(scores)
    avg_innovation = sum(s.innovation_score for s in scores) / count
    avg_technical = sum(s.technical_score for s in scores) / count
    avg_implementation = sum(s.implementation_score for s in scores) / count
    avg_documentation = sum(s.documentation_score for s in scores) / count
    avg_presentation = sum(s.presentation_score for s in scores) / count

    review_result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == review_id)
    )
    review = review_result.scalar_one_or_none()

    if review:
        review.innovation_score = round(avg_innovation, 2)
        review.technical_score = round(avg_technical, 2)
        review.implementation_score = round(avg_implementation, 2)
        review.documentation_score = round(avg_documentation, 2)
        review.presentation_score = round(avg_presentation, 2)
        review.calculate_total_score()
        await db.commit()
