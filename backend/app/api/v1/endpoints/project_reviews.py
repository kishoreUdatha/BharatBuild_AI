"""
Project Review System API

Endpoints for managing student project reviews:
- Project registration
- Review scheduling
- Panel assignment
- Scoring and feedback
- Review history
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project_review import (
    ReviewProject, ProjectTeamMember, ProjectReview,
    ReviewPanelMember, ReviewScore, ReviewType, ReviewStatus,
    ProjectType, REVIEW_CRITERIA, SCORING_CRITERIA, get_tech_criteria
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
    github_url: Optional[str] = None
    guide_name: Optional[str] = None
    team_members: Optional[List[TeamMemberCreate]] = []


class TeamMemberResponse(BaseModel):
    id: str
    name: str
    roll_number: Optional[str]
    email: Optional[str]
    role: Optional[str]

    class Config:
        from_attributes = True


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
    total_score: float
    average_score: float
    is_approved: bool
    is_completed: bool
    created_at: datetime
    team_members: Optional[List[TeamMemberResponse]] = []
    student_name: Optional[str] = None
    roll_number: Optional[str] = None

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
    review_type: str  # review_1, review_2, review_3, final_review
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


class ReviewFeedbackSubmit(BaseModel):
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    suggestions: Optional[str] = None
    overall_feedback: Optional[str] = None
    action_items: Optional[str] = None


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
    total_score: float
    innovation_score: float
    technical_score: float
    implementation_score: float
    documentation_score: float
    presentation_score: float
    overall_feedback: Optional[str]
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
    """Register a new student project for reviews"""
    # Create project
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
        github_url=project_data.github_url,
        guide_name=project_data.guide_name,
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
        total_score=project.total_score,
        average_score=project.average_score,
        is_approved=project.is_approved,
        is_completed=project.is_completed,
        created_at=project.created_at,
    )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    project_type: Optional[str] = None,
    semester: Optional[int] = None,
    batch: Optional[str] = None,
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List all registered projects with team members"""
    query = select(ReviewProject).options(selectinload(ReviewProject.team_members))

    if project_type:
        query = query.where(ReviewProject.project_type == ProjectType(project_type))
    if semester:
        query = query.where(ReviewProject.semester == semester)
    if batch:
        query = query.where(ReviewProject.batch == batch)
    if department:
        query = query.where(ReviewProject.department.ilike(f"%{department}%"))

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
            total_score=p.total_score,
            average_score=p.average_score,
            is_approved=p.is_approved,
            is_completed=p.is_completed,
            created_at=p.created_at,
            team_members=[
                TeamMemberResponse(
                    id=str(m.id),
                    name=m.name,
                    roll_number=m.roll_number,
                    email=m.email,
                    role=m.role
                ) for m in p.team_members
            ] if p.team_members else [],
            student_name=p.team_members[0].name if p.team_members else p.team_name,
            roll_number=p.team_members[0].roll_number if p.team_members else None,
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
            selectinload(ReviewProject.team_members)
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
        "total_score": project.total_score,
        "average_score": project.average_score,
        "is_approved": project.is_approved,
        "is_completed": project.is_completed,
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
                "total_score": r.total_score,
                "panel_count": len(r.panel_members),
            }
            for r in sorted(project.reviews, key=lambda x: x.review_number)
        ],
    }


# ==================== Review Endpoints ====================

@router.post("/reviews", response_model=ReviewResponse)
async def schedule_review(
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """Schedule a new project review"""
    # Verify project exists
    result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == UUID(review_data.project_id))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Determine review number
    review_type = ReviewType(review_data.review_type)
    review_number_map = {
        ReviewType.review_1: 1,
        ReviewType.review_2: 2,
        ReviewType.review_3: 3,
        ReviewType.final_review: 4,
    }
    review_number = review_number_map[review_type]

    # Check if this review already exists
    existing = await db.execute(
        select(ProjectReview).where(
            and_(
                ProjectReview.project_id == UUID(review_data.project_id),
                ProjectReview.review_type == review_type
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Review {review_number} already scheduled for this project"
        )

    # Create review
    review = ProjectReview(
        project_id=UUID(review_data.project_id),
        review_type=review_type,
        review_number=review_number,
        scheduled_date=review_data.scheduled_date,
        scheduled_time=review_data.scheduled_time,
        venue=review_data.venue,
        duration_minutes=review_data.duration_minutes,
        status=ReviewStatus.scheduled,
    )
    db.add(review)
    await db.flush()

    # Add panel members
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
        total_score=review.total_score,
        innovation_score=review.innovation_score,
        technical_score=review.technical_score,
        implementation_score=review.implementation_score,
        documentation_score=review.documentation_score,
        presentation_score=review.presentation_score,
        overall_feedback=review.overall_feedback,
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

    # Get project titles
    project_ids = [r.project_id for r in reviews]
    projects_result = await db.execute(
        select(ReviewProject).where(ReviewProject.id.in_(project_ids))
    )
    projects = {str(p.id): p.title for p in projects_result.scalars().all()}

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
            "total_score": r.total_score,
            "panel_count": len(r.panel_members),
        }
        for r in reviews
    ]


@router.get("/reviews/{review_id}")
async def get_review(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get review details with scores"""
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

    # Get project
    project_result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == review.project_id)
    )
    project = project_result.scalar_one_or_none()

    # Get criteria for this review type
    criteria = REVIEW_CRITERIA.get(review.review_type.value, {})

    # Get technology-specific evaluation criteria
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
        "tech_specific_criteria": tech_criteria,
        "scheduled_date": review.scheduled_date,
        "scheduled_time": review.scheduled_time,
        "venue": review.venue,
        "duration_minutes": review.duration_minutes,
        "status": review.status.value,
        "scores": {
            "innovation": review.innovation_score,
            "technical": review.technical_score,
            "implementation": review.implementation_score,
            "documentation": review.documentation_score,
            "presentation": review.presentation_score,
            "total": review.total_score,
        },
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

    review.status = ReviewStatus.in_progress
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
    # Verify review exists
    result = await db.execute(
        select(ProjectReview).where(ProjectReview.id == UUID(review_id))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Check if panel member exists
    panel_result = await db.execute(
        select(ReviewPanelMember).where(ReviewPanelMember.id == UUID(panel_member_id))
    )
    panel_member = panel_result.scalar_one_or_none()

    if not panel_member:
        raise HTTPException(status_code=404, detail="Panel member not found")

    # Check if already scored
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
        # Update existing score
        existing_score.innovation_score = score_data.innovation_score
        existing_score.technical_score = score_data.technical_score
        existing_score.implementation_score = score_data.implementation_score
        existing_score.documentation_score = score_data.documentation_score
        existing_score.presentation_score = score_data.presentation_score
        existing_score.comments = score_data.comments
        existing_score.calculate_total()
        existing_score.updated_at = datetime.utcnow()
    else:
        # Create new score
        score = ReviewScore(
            review_id=UUID(review_id),
            panel_member_id=UUID(panel_member_id),
            innovation_score=score_data.innovation_score,
            technical_score=score_data.technical_score,
            implementation_score=score_data.implementation_score,
            documentation_score=score_data.documentation_score,
            presentation_score=score_data.presentation_score,
            comments=score_data.comments,
        )
        score.calculate_total()
        db.add(score)

    await db.commit()

    # Recalculate average scores for the review
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

    # Update review status
    review.status = ReviewStatus.completed
    review.completed_at = datetime.utcnow()

    # Update project's current review number
    project_result = await db.execute(
        select(ReviewProject).where(ReviewProject.id == review.project_id)
    )
    project = project_result.scalar_one_or_none()

    if project:
        project.current_review = review.review_number

        # If final review, mark project as completed
        if review.review_type == ReviewType.final_review:
            project.is_completed = True
            if review.total_score >= 50:  # Pass threshold
                project.is_approved = True

        # Update project's average score
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

    await db.commit()

    return {
        "success": True,
        "message": "Review completed",
        "total_score": review.total_score,
        "project_average": project.average_score if project else 0,
    }


async def _recalculate_review_scores(db: AsyncSession, review_id: UUID):
    """Recalculate average scores from all panel member scores"""
    result = await db.execute(
        select(ReviewScore).where(ReviewScore.review_id == review_id)
    )
    scores = result.scalars().all()

    if not scores:
        return

    # Calculate averages
    count = len(scores)
    avg_innovation = sum(s.innovation_score for s in scores) / count
    avg_technical = sum(s.technical_score for s in scores) / count
    avg_implementation = sum(s.implementation_score for s in scores) / count
    avg_documentation = sum(s.documentation_score for s in scores) / count
    avg_presentation = sum(s.presentation_score for s in scores) / count

    # Update review
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


# ==================== Dashboard Endpoints ====================

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

    # Get project titles
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
            "project_title": projects.get(str(r.project_id), {}).title if str(r.project_id) in projects else "Unknown",
            "team_name": projects.get(str(r.project_id), {}).team_name if str(r.project_id) in projects else None,
            "review_type": r.review_type.value,
            "review_number": r.review_number,
            "scheduled_date": r.scheduled_date,
            "scheduled_time": r.scheduled_time,
            "venue": r.venue,
            "panel_count": len(r.panel_members),
        }
        for r in reviews
    ]


@router.get("/dashboard/stats")
async def get_review_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get review statistics"""
    # Total projects
    total_projects = await db.execute(select(func.count(ReviewProject.id)))
    total = total_projects.scalar() or 0

    # Projects by type
    mini_projects = await db.execute(
        select(func.count(ReviewProject.id))
        .where(ReviewProject.project_type == ProjectType.mini_project)
    )
    major_projects = await db.execute(
        select(func.count(ReviewProject.id))
        .where(ReviewProject.project_type == ProjectType.major_project)
    )

    # Reviews by status
    scheduled = await db.execute(
        select(func.count(ProjectReview.id))
        .where(ProjectReview.status == ReviewStatus.scheduled)
    )
    completed = await db.execute(
        select(func.count(ProjectReview.id))
        .where(ProjectReview.status == ReviewStatus.completed)
    )

    # Average scores
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


@router.get("/criteria")
async def get_review_criteria():
    """Get review criteria and scoring rubric"""
    return {
        "review_types": REVIEW_CRITERIA,
        "scoring_criteria": SCORING_CRITERIA,
    }
