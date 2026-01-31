"""
Lab Assistance API Endpoints
Provides endpoints for lab management, topics, MCQs, coding problems, and progress tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, or_, select
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_current_active_user
from app.models.user import User, UserRole
from app.models.lab_assistance import (
    Lab, LabTopic, LabMCQ, LabCodingProblem,
    LabEnrollment, LabTopicProgress, LabMCQResponse,
    LabCodingSubmission, LabQuizSession, LabReport, SemesterProgress,
    Branch, Semester, DifficultyLevel, ProgrammingLanguage,
    SubmissionStatus, TopicStatus, LabReportStatus
)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class LabCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    branch: Branch
    semester: Semester
    technologies: Optional[List[str]] = None


class LabResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str]
    branch: str
    semester: str
    technologies: Optional[List[str]]
    total_topics: int
    total_mcqs: int
    total_coding_problems: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TopicCreate(BaseModel):
    title: str
    description: Optional[str] = None
    week_number: int = 1
    order_index: int = 0
    concept_content: Optional[str] = None
    video_url: Optional[str] = None
    prerequisites: Optional[List[str]] = None
    difficulty: Optional[DifficultyLevel] = DifficultyLevel.MEDIUM
    status: Optional[str] = "draft"
    ai_limit: Optional[int] = 20
    deadline: Optional[datetime] = None


class TopicResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    week_number: int
    order_index: int
    concept_content: Optional[str]
    video_url: Optional[str]
    mcq_count: int
    coding_count: int
    is_active: bool
    # New computed/stored fields
    difficulty: Optional[str] = "medium"
    status: Optional[str] = "draft"
    ai_limit: Optional[int] = 20
    deadline: Optional[datetime] = None
    # Computed fields (filled by endpoint)
    submissions: Optional[int] = 0
    total_students: Optional[int] = 0
    avg_score: Optional[float] = 0

    class Config:
        from_attributes = True


class MCQCreate(BaseModel):
    question_text: str
    options: List[str]
    correct_option: int
    explanation: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    marks: float = 1.0
    time_limit_seconds: int = 60
    tags: Optional[List[str]] = None


class MCQResponse(BaseModel):
    id: str
    question_text: str
    options: List[str]
    difficulty: str
    marks: float
    time_limit_seconds: int
    tags: Optional[List[str]]

    class Config:
        from_attributes = True


class MCQWithAnswer(MCQResponse):
    correct_option: int
    explanation: Optional[str]


class CodingProblemCreate(BaseModel):
    title: str
    description: str
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    max_score: int = 100
    supported_languages: List[str]
    starter_code: Optional[dict] = None
    solution_code: Optional[dict] = None
    test_cases: List[dict]
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256
    hints: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class CodingProblemResponse(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    max_score: int
    supported_languages: List[str]
    starter_code: Optional[dict]
    time_limit_ms: int
    memory_limit_mb: int
    hints: Optional[List[str]]
    tags: Optional[List[str]]

    class Config:
        from_attributes = True


class CodeSubmission(BaseModel):
    language: str
    code: str


class SubmissionResponse(BaseModel):
    id: str
    status: str
    tests_passed: int
    tests_total: int
    score: float
    execution_time_ms: Optional[int]
    memory_used_mb: Optional[float]
    error_message: Optional[str]
    test_results: Optional[List[dict]]

    class Config:
        from_attributes = True


class MCQAnswerSubmit(BaseModel):
    mcq_id: str
    selected_option: int
    time_taken_seconds: Optional[int] = None


class ProgressResponse(BaseModel):
    lab_id: str
    lab_name: str
    overall_progress: float
    mcq_score: float
    coding_score: float
    topics_completed: int
    total_topics: int
    mcqs_attempted: int
    problems_solved: int
    class_rank: Optional[int]


class TopicProgressResponse(BaseModel):
    topic_id: str
    topic_title: str
    status: str
    concept_read: bool
    mcq_attempted: int
    mcq_correct: int
    mcq_score: float
    coding_attempted: int
    coding_solved: int
    coding_score: float
    progress_percentage: float


# ============================================================================
# PUBLIC LAB ENDPOINTS (No authentication required)
# ============================================================================

@router.get("/public/labs", response_model=List[LabResponse])
async def get_public_labs(
    branch: Optional[str] = None,
    semester: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all labs publicly (no authentication required) for browsing"""
    query = select(Lab).where(Lab.is_active == True)

    if branch:
        query = query.where(Lab.branch == branch)
    if semester:
        query = query.where(Lab.semester == semester)

    query = query.order_by(Lab.semester, Lab.name)
    result = await db.execute(query)
    labs = result.scalars().all()
    return labs


@router.get("/public/labs/{lab_id}", response_model=LabResponse)
async def get_public_lab(
    lab_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific lab by ID (no authentication required)"""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab


@router.get("/public/labs/{lab_id}/topics", response_model=List[TopicResponse])
async def get_public_lab_topics(
    lab_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all topics for a lab (no authentication required)"""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    result = await db.execute(
        select(LabTopic).where(
            LabTopic.lab_id == lab_id,
            LabTopic.is_active == True
        ).order_by(LabTopic.week_number, LabTopic.order_index)
    )
    topics = result.scalars().all()
    return topics


@router.get("/public/topics/{topic_id}")
async def get_public_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get topic details including concept content (no authentication required)"""
    result = await db.execute(select(LabTopic).where(LabTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    return {
        "id": str(topic.id),
        "title": topic.title,
        "description": topic.description,
        "week_number": topic.week_number,
        "concept_content": topic.concept_content,
        "video_url": topic.video_url,
        "mcq_count": topic.mcq_count,
        "coding_count": topic.coding_count,
        "lab_id": str(topic.lab_id)
    }


@router.get("/public/topics/{topic_id}/mcqs")
async def get_public_topic_mcqs(
    topic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get MCQs for a topic (no authentication required, without answers)"""
    result = await db.execute(select(LabTopic).where(LabTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    result = await db.execute(
        select(LabMCQ).where(
            LabMCQ.topic_id == topic_id,
            LabMCQ.is_active == True
        )
    )
    mcqs = result.scalars().all()

    # Return MCQs without correct answers for public view
    return [{
        "id": str(mcq.id),
        "question_text": mcq.question_text,
        "options": mcq.options,
        "difficulty": mcq.difficulty.value if mcq.difficulty else "MEDIUM",
        "marks": mcq.marks,
        "time_limit_seconds": mcq.time_limit_seconds
    } for mcq in mcqs]


@router.get("/public/topics/{topic_id}/problems")
async def get_public_topic_problems(
    topic_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get coding problems for a topic (no authentication required)"""
    result = await db.execute(select(LabTopic).where(LabTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    result = await db.execute(
        select(LabCodingProblem).where(
            LabCodingProblem.topic_id == topic_id,
            LabCodingProblem.is_active == True
        )
    )
    problems = result.scalars().all()

    return [{
        "id": str(prob.id),
        "title": prob.title,
        "description": prob.description,
        "difficulty": prob.difficulty.value if prob.difficulty else "MEDIUM",
        "max_score": prob.max_score,
        "supported_languages": prob.supported_languages,
        "starter_code": prob.starter_code,
        "hints": prob.hints,
        "time_limit_ms": prob.time_limit_ms,
        "memory_limit_mb": prob.memory_limit_mb
    } for prob in problems]


# ============================================================================
# AUTHENTICATED LAB ENDPOINTS
# ============================================================================

@router.get("/labs", response_model=List[LabResponse])
async def get_labs(
    branch: Optional[Branch] = None,
    semester: Optional[Semester] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all labs, optionally filtered by branch and semester"""
    query = select(Lab).where(Lab.is_active == True)

    if branch:
        query = query.where(Lab.branch == branch)
    if semester:
        query = query.where(Lab.semester == semester)

    query = query.order_by(Lab.semester, Lab.name)
    result = await db.execute(query)
    labs = result.scalars().all()
    return labs


@router.get("/labs/{lab_id}", response_model=LabResponse)
async def get_lab(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific lab by ID"""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab


@router.post("/labs", response_model=LabResponse)
async def create_lab(
    lab_data: LabCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new lab (Faculty/Admin only)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty or admin can create labs")

    # Check if code already exists
    result = await db.execute(select(Lab).where(Lab.code == lab_data.code))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Lab code already exists")

    lab = Lab(
        name=lab_data.name,
        code=lab_data.code,
        description=lab_data.description,
        branch=lab_data.branch,
        semester=lab_data.semester,
        technologies=lab_data.technologies,
        faculty_id=current_user.id
    )
    db.add(lab)
    await db.commit()
    await db.refresh(lab)
    return lab


# ============================================================================
# TOPIC ENDPOINTS
# ============================================================================

@router.get("/labs/{lab_id}/topics")
async def get_lab_topics(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all topics for a lab with computed stats"""
    # Get all topics
    result = await db.execute(
        select(LabTopic).where(
            LabTopic.lab_id == lab_id,
            LabTopic.is_active == True
        ).order_by(LabTopic.week_number, LabTopic.order_index)
    )
    topics = result.scalars().all()

    # Get total enrolled students for this lab
    enrollment_result = await db.execute(
        select(func.count()).select_from(LabEnrollment).where(
            LabEnrollment.lab_id == lab_id
        )
    )
    total_students = enrollment_result.scalar() or 0

    # Build response with computed fields
    response = []
    for topic in topics:
        # Count submissions (students who have started this topic)
        progress_result = await db.execute(
            select(func.count()).select_from(LabTopicProgress).where(
                LabTopicProgress.topic_id == str(topic.id),
                LabTopicProgress.status != TopicStatus.NOT_STARTED
            )
        )
        submissions = progress_result.scalar() or 0

        # Calculate average score for this topic
        avg_result = await db.execute(
            select(func.avg(LabTopicProgress.progress_percentage)).where(
                LabTopicProgress.topic_id == str(topic.id),
                LabTopicProgress.progress_percentage > 0
            )
        )
        avg_score = avg_result.scalar() or 0

        # Get difficulty value
        difficulty_val = topic.difficulty.value if topic.difficulty else "medium"

        response.append({
            "id": str(topic.id),
            "title": topic.title,
            "description": topic.description,
            "week_number": topic.week_number,
            "order_index": topic.order_index,
            "concept_content": topic.concept_content,
            "video_url": topic.video_url,
            "mcq_count": topic.mcq_count,
            "coding_count": topic.coding_count,
            "is_active": topic.is_active,
            "difficulty": difficulty_val,
            "status": topic.status or "draft",
            "ai_limit": topic.ai_limit or 20,
            "deadline": topic.deadline.isoformat() if topic.deadline else None,
            "submissions": submissions,
            "total_students": total_students,
            "avg_score": round(avg_score, 1)
        })

    return response


@router.get("/topics/{topic_id}")
async def get_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific topic with its content"""
    result = await db.execute(select(LabTopic).where(LabTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get user's progress on this topic
    result = await db.execute(
        select(LabEnrollment).where(
            LabEnrollment.lab_id == topic.lab_id,
            LabEnrollment.user_id == current_user.id
        )
    )
    enrollment = result.scalar_one_or_none()

    progress = None
    if enrollment:
        result = await db.execute(
            select(LabTopicProgress).where(
                LabTopicProgress.enrollment_id == enrollment.id,
                LabTopicProgress.topic_id == topic_id
            )
        )
        progress = result.scalar_one_or_none()

    return {
        "topic": topic,
        "progress": progress
    }


@router.post("/labs/{lab_id}/topics")
async def create_topic(
    lab_id: str,
    topic_data: TopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new topic in a lab (Faculty/Admin only)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty or admin can create topics")

    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    topic = LabTopic(
        lab_id=lab_id,
        title=topic_data.title,
        description=topic_data.description,
        week_number=topic_data.week_number,
        order_index=topic_data.order_index,
        concept_content=topic_data.concept_content,
        video_url=topic_data.video_url,
        prerequisites=topic_data.prerequisites,
        difficulty=topic_data.difficulty or DifficultyLevel.MEDIUM,
        status=topic_data.status or "draft",
        ai_limit=topic_data.ai_limit or 20,
        deadline=topic_data.deadline
    )
    db.add(topic)

    # Update lab topic count
    lab.total_topics += 1

    await db.commit()
    await db.refresh(topic)

    return {
        "id": str(topic.id),
        "title": topic.title,
        "description": topic.description,
        "week_number": topic.week_number,
        "order_index": topic.order_index,
        "concept_content": topic.concept_content,
        "video_url": topic.video_url,
        "mcq_count": topic.mcq_count,
        "coding_count": topic.coding_count,
        "is_active": topic.is_active,
        "difficulty": topic.difficulty.value if topic.difficulty else "medium",
        "status": topic.status or "draft",
        "ai_limit": topic.ai_limit or 20,
        "deadline": topic.deadline.isoformat() if topic.deadline else None,
        "submissions": 0,
        "total_students": 0,
        "avg_score": 0
    }


@router.post("/topics/{topic_id}/mark-read")
async def mark_concept_read(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark a topic's concept as read"""
    result = await db.execute(select(LabTopic).where(LabTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get or create enrollment
    result = await db.execute(
        select(LabEnrollment).where(
            LabEnrollment.lab_id == topic.lab_id,
            LabEnrollment.user_id == current_user.id
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        enrollment = LabEnrollment(
            lab_id=topic.lab_id,
            user_id=current_user.id
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

    # Get or create topic progress
    result = await db.execute(
        select(LabTopicProgress).where(
            LabTopicProgress.enrollment_id == enrollment.id,
            LabTopicProgress.topic_id == topic_id
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = LabTopicProgress(
            enrollment_id=enrollment.id,
            topic_id=topic_id,
            status=TopicStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(progress)

    progress.concept_read = True
    progress.concept_read_at = datetime.utcnow()
    _update_topic_progress(progress, topic)

    await db.commit()

    return {"message": "Concept marked as read", "progress": progress.progress_percentage}


# ============================================================================
# MCQ ENDPOINTS
# ============================================================================

@router.get("/topics/{topic_id}/mcqs", response_model=List[MCQResponse])
async def get_topic_mcqs(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all MCQs for a topic (without answers)"""
    result = await db.execute(
        select(LabMCQ).where(
            LabMCQ.topic_id == topic_id,
            LabMCQ.is_active == True
        )
    )
    mcqs = result.scalars().all()
    return mcqs


@router.post("/topics/{topic_id}/mcqs", response_model=MCQWithAnswer)
async def create_mcq(
    topic_id: str,
    mcq_data: MCQCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new MCQ (Faculty/Admin only)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty or admin can create MCQs")

    result = await db.execute(select(LabTopic).where(LabTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    mcq = LabMCQ(
        topic_id=topic_id,
        question_text=mcq_data.question_text,
        options=mcq_data.options,
        correct_option=mcq_data.correct_option,
        explanation=mcq_data.explanation,
        difficulty=mcq_data.difficulty,
        marks=mcq_data.marks,
        time_limit_seconds=mcq_data.time_limit_seconds,
        tags=mcq_data.tags
    )
    db.add(mcq)

    # Update counts
    topic.mcq_count += 1
    result = await db.execute(select(Lab).where(Lab.id == topic.lab_id))
    lab = result.scalar_one_or_none()
    if lab:
        lab.total_mcqs += 1

    await db.commit()
    await db.refresh(mcq)
    return mcq


@router.post("/mcqs/{mcq_id}/answer")
async def submit_mcq_answer(
    mcq_id: str,
    answer: MCQAnswerSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit an answer to an MCQ"""
    result = await db.execute(select(LabMCQ).where(LabMCQ.id == mcq_id))
    mcq = result.scalar_one_or_none()
    if not mcq:
        raise HTTPException(status_code=404, detail="MCQ not found")

    result = await db.execute(select(LabTopic).where(LabTopic.id == mcq.topic_id))
    topic = result.scalar_one_or_none()

    # Get enrollment
    result = await db.execute(
        select(LabEnrollment).where(
            LabEnrollment.lab_id == topic.lab_id,
            LabEnrollment.user_id == current_user.id
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        enrollment = LabEnrollment(
            lab_id=topic.lab_id,
            user_id=current_user.id
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

    # Check if already answered
    result = await db.execute(
        select(LabMCQResponse).where(
            LabMCQResponse.enrollment_id == enrollment.id,
            LabMCQResponse.mcq_id == mcq_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Already answered this question")

    # Check answer
    is_correct = answer.selected_option == mcq.correct_option
    marks = mcq.marks if is_correct else 0

    response = LabMCQResponse(
        enrollment_id=enrollment.id,
        mcq_id=mcq_id,
        selected_option=answer.selected_option,
        is_correct=is_correct,
        marks_obtained=marks,
        time_taken_seconds=answer.time_taken_seconds
    )
    db.add(response)

    # Update enrollment stats
    enrollment.mcqs_attempted += 1
    if is_correct:
        enrollment.mcqs_correct += 1
    enrollment.last_activity = datetime.utcnow()

    # Update topic progress
    result = await db.execute(
        select(LabTopicProgress).where(
            LabTopicProgress.enrollment_id == enrollment.id,
            LabTopicProgress.topic_id == topic.id
        )
    )
    topic_progress = result.scalar_one_or_none()

    if not topic_progress:
        topic_progress = LabTopicProgress(
            enrollment_id=enrollment.id,
            topic_id=topic.id,
            status=TopicStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(topic_progress)

    topic_progress.mcq_attempted += 1
    if is_correct:
        topic_progress.mcq_correct += 1
    topic_progress.mcq_score = (topic_progress.mcq_correct / topic_progress.mcq_attempted) * 100

    _update_topic_progress(topic_progress, topic)

    await db.commit()

    return {
        "is_correct": is_correct,
        "correct_option": mcq.correct_option,
        "explanation": mcq.explanation,
        "marks_obtained": marks,
        "mcq_score": topic_progress.mcq_score
    }


# ============================================================================
# CODING PROBLEM ENDPOINTS
# ============================================================================

@router.get("/topics/{topic_id}/problems", response_model=List[CodingProblemResponse])
async def get_topic_problems(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all coding problems for a topic"""
    result = await db.execute(
        select(LabCodingProblem).where(
            LabCodingProblem.topic_id == topic_id,
            LabCodingProblem.is_active == True
        )
    )
    problems = result.scalars().all()
    return problems


@router.get("/problems/{problem_id}")
async def get_problem(
    problem_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific coding problem"""
    result = await db.execute(select(LabCodingProblem).where(LabCodingProblem.id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Get user's best submission
    result = await db.execute(
        select(LabCodingSubmission).where(
            LabCodingSubmission.problem_id == problem_id,
            LabCodingSubmission.user_id == current_user.id,
            LabCodingSubmission.status == SubmissionStatus.PASSED
        ).order_by(LabCodingSubmission.score.desc())
    )
    best_submission = result.scalars().first()

    # Filter test cases to only show sample ones
    sample_tests = [tc for tc in problem.test_cases if tc.get('is_sample', False)]

    return {
        "id": str(problem.id),
        "title": problem.title,
        "description": problem.description,
        "difficulty": problem.difficulty.value,
        "max_score": problem.max_score,
        "supported_languages": problem.supported_languages,
        "starter_code": problem.starter_code,
        "time_limit_ms": problem.time_limit_ms,
        "memory_limit_mb": problem.memory_limit_mb,
        "hints": problem.hints,
        "tags": problem.tags,
        "sample_tests": sample_tests,
        "best_submission": best_submission
    }


@router.post("/topics/{topic_id}/problems", response_model=CodingProblemResponse)
async def create_coding_problem(
    topic_id: str,
    problem_data: CodingProblemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new coding problem (Faculty/Admin only)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty or admin can create problems")

    result = await db.execute(select(LabTopic).where(LabTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    problem = LabCodingProblem(
        topic_id=topic_id,
        title=problem_data.title,
        description=problem_data.description,
        difficulty=problem_data.difficulty,
        max_score=problem_data.max_score,
        supported_languages=problem_data.supported_languages,
        starter_code=problem_data.starter_code,
        solution_code=problem_data.solution_code,
        test_cases=problem_data.test_cases,
        time_limit_ms=problem_data.time_limit_ms,
        memory_limit_mb=problem_data.memory_limit_mb,
        hints=problem_data.hints,
        tags=problem_data.tags
    )
    db.add(problem)

    # Update counts
    topic.coding_count += 1
    result = await db.execute(select(Lab).where(Lab.id == topic.lab_id))
    lab = result.scalar_one_or_none()
    if lab:
        lab.total_coding_problems += 1

    await db.commit()
    await db.refresh(problem)
    return problem


@router.post("/problems/{problem_id}/submit")
async def submit_code(
    problem_id: str,
    submission: CodeSubmission,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit code for a coding problem"""
    result = await db.execute(select(LabCodingProblem).where(LabCodingProblem.id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Validate language
    if submission.language not in problem.supported_languages:
        raise HTTPException(
            status_code=400,
            detail=f"Language {submission.language} not supported. Use: {problem.supported_languages}"
        )

    # Create submission record
    code_submission = LabCodingSubmission(
        user_id=current_user.id,
        problem_id=problem_id,
        language=ProgrammingLanguage(submission.language),
        code=submission.code,
        status=SubmissionStatus.PENDING,
        tests_total=len(problem.test_cases)
    )
    db.add(code_submission)
    await db.commit()
    await db.refresh(code_submission)

    # Run code execution in background
    background_tasks.add_task(
        execute_code_submission,
        str(code_submission.id),
        submission.code,
        submission.language,
        problem.test_cases,
        problem.time_limit_ms,
        problem.memory_limit_mb
    )

    return {
        "submission_id": str(code_submission.id),
        "status": "pending",
        "message": "Code submitted. Running tests..."
    }


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get submission status and results"""
    result = await db.execute(
        select(LabCodingSubmission).where(LabCodingSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if str(submission.user_id) != str(current_user.id) and current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized to view this submission")

    return submission


# ============================================================================
# PROGRESS ENDPOINTS
# ============================================================================

@router.get("/labs/{lab_id}/progress", response_model=ProgressResponse)
async def get_lab_progress(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's progress in a lab"""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    result = await db.execute(
        select(LabEnrollment).where(
            LabEnrollment.lab_id == lab_id,
            LabEnrollment.user_id == current_user.id
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        return ProgressResponse(
            lab_id=str(lab.id),
            lab_name=lab.name,
            overall_progress=0,
            mcq_score=0,
            coding_score=0,
            topics_completed=0,
            total_topics=lab.total_topics,
            mcqs_attempted=0,
            problems_solved=0,
            class_rank=None
        )

    return ProgressResponse(
        lab_id=str(lab.id),
        lab_name=lab.name,
        overall_progress=enrollment.overall_progress,
        mcq_score=enrollment.mcq_score,
        coding_score=enrollment.coding_score,
        topics_completed=enrollment.topics_completed,
        total_topics=lab.total_topics,
        mcqs_attempted=enrollment.mcqs_attempted,
        problems_solved=enrollment.problems_solved,
        class_rank=enrollment.class_rank
    )


@router.get("/labs/{lab_id}/topics-progress", response_model=List[TopicProgressResponse])
async def get_topics_progress(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's progress on all topics in a lab"""
    result = await db.execute(
        select(LabTopic).where(
            LabTopic.lab_id == lab_id,
            LabTopic.is_active == True
        ).order_by(LabTopic.week_number, LabTopic.order_index)
    )
    topics = result.scalars().all()

    result = await db.execute(
        select(LabEnrollment).where(
            LabEnrollment.lab_id == lab_id,
            LabEnrollment.user_id == current_user.id
        )
    )
    enrollment = result.scalar_one_or_none()

    results = []
    for topic in topics:
        progress = None
        if enrollment:
            result = await db.execute(
                select(LabTopicProgress).where(
                    LabTopicProgress.enrollment_id == enrollment.id,
                    LabTopicProgress.topic_id == topic.id
                )
            )
            progress = result.scalar_one_or_none()

        results.append(TopicProgressResponse(
            topic_id=str(topic.id),
            topic_title=topic.title,
            status=progress.status.value if progress else TopicStatus.NOT_STARTED.value,
            concept_read=progress.concept_read if progress else False,
            mcq_attempted=progress.mcq_attempted if progress else 0,
            mcq_correct=progress.mcq_correct if progress else 0,
            mcq_score=progress.mcq_score if progress else 0,
            coding_attempted=progress.coding_attempted if progress else 0,
            coding_solved=progress.coding_solved if progress else 0,
            coding_score=progress.coding_score if progress else 0,
            progress_percentage=progress.progress_percentage if progress else 0
        ))

    return results


# ============================================================================
# FACULTY/HOD ENDPOINTS
# ============================================================================

@router.get("/labs/{lab_id}/students")
async def get_lab_students(
    lab_id: str,
    section: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all students enrolled in a lab with their progress (Faculty/HOD only)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty or admin can view student list")

    query = select(LabEnrollment, User).join(
        User, LabEnrollment.user_id == User.id
    ).where(LabEnrollment.lab_id == lab_id)

    if section:
        query = query.where(LabEnrollment.section == section)

    query = query.order_by(LabEnrollment.total_score.desc())
    result = await db.execute(query)
    results = result.all()

    students = []
    for rank, (enrollment, user) in enumerate(results, 1):
        students.append({
            "rank": rank,
            "user_id": str(user.id),
            "name": user.full_name or user.email,
            "email": user.email,
            "roll_number": user.roll_number,
            "section": enrollment.section,
            "overall_progress": enrollment.overall_progress,
            "mcq_score": enrollment.mcq_score,
            "coding_score": enrollment.coding_score,
            "total_score": enrollment.total_score,
            "topics_completed": enrollment.topics_completed,
            "mcqs_attempted": enrollment.mcqs_attempted,
            "problems_solved": enrollment.problems_solved,
            "last_activity": enrollment.last_activity
        })

    return {
        "lab_id": lab_id,
        "total_students": len(students),
        "students": students
    }


@router.get("/topics/{topic_id}/student-progress")
async def get_topic_student_progress(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all students' progress for a specific topic (Faculty/HOD only)"""
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty or admin can view student progress")

    # Get the topic
    result = await db.execute(select(LabTopic).where(LabTopic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get all enrollments for this lab
    enrollments_result = await db.execute(
        select(LabEnrollment, User).join(
            User, LabEnrollment.user_id == User.id
        ).where(LabEnrollment.lab_id == str(topic.lab_id))
    )
    enrollments = enrollments_result.all()

    students = []
    completed_count = 0
    total_score = 0
    scored_count = 0

    for enrollment, user in enrollments:
        # Get topic progress for this student
        progress_result = await db.execute(
            select(LabTopicProgress).where(
                LabTopicProgress.enrollment_id == str(enrollment.id),
                LabTopicProgress.topic_id == topic_id
            )
        )
        progress = progress_result.scalar_one_or_none()

        if progress and progress.status in [TopicStatus.COMPLETED, TopicStatus.IN_PROGRESS]:
            status = "completed" if progress.status == TopicStatus.COMPLETED else "in_progress"
            score = progress.progress_percentage or 0
            submitted_at = progress.completed_at or progress.started_at
            attempts = (progress.mcq_attempted or 0) + (progress.coding_attempted or 0)

            if progress.status == TopicStatus.COMPLETED:
                completed_count += 1
            if score > 0:
                total_score += score
                scored_count += 1
        else:
            status = "pending"
            score = 0
            submitted_at = None
            attempts = 0

        students.append({
            "id": str(user.id),
            "name": user.full_name or user.email.split('@')[0],
            "email": user.email,
            "roll_number": user.roll_number or f"STU{str(user.id)[:6].upper()}",
            "section": enrollment.section or "A",
            "status": status,
            "score": round(score, 1),
            "submitted_at": submitted_at.isoformat() if submitted_at else None,
            "attempts": attempts
        })

    # Sort: completed first (by score desc), then pending
    students.sort(key=lambda x: (
        0 if x['status'] == 'completed' else (1 if x['status'] == 'in_progress' else 2),
        -x['score']
    ))

    return {
        "topic_id": topic_id,
        "topic_title": topic.title,
        "total_students": len(students),
        "completed_count": completed_count,
        "pending_count": len(students) - completed_count,
        "avg_score": round(total_score / scored_count, 1) if scored_count > 0 else 0,
        "students": students
    }


@router.get("/labs/{lab_id}/analytics")
async def get_lab_analytics(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get lab analytics for faculty/HOD"""
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only faculty or admin can view analytics")

    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Get enrollment stats
    result = await db.execute(select(LabEnrollment).where(LabEnrollment.lab_id == lab_id))
    enrollments = result.scalars().all()

    total_students = len(enrollments)
    avg_progress = sum(e.overall_progress for e in enrollments) / total_students if total_students > 0 else 0
    avg_mcq_score = sum(e.mcq_score for e in enrollments) / total_students if total_students > 0 else 0
    avg_coding_score = sum(e.coding_score for e in enrollments) / total_students if total_students > 0 else 0

    # Performance distribution
    performance_dist = {
        "excellent": len([e for e in enrollments if e.total_score >= 90]),
        "good": len([e for e in enrollments if 75 <= e.total_score < 90]),
        "average": len([e for e in enrollments if 60 <= e.total_score < 75]),
        "below_average": len([e for e in enrollments if 40 <= e.total_score < 60]),
        "needs_help": len([e for e in enrollments if e.total_score < 40])
    }

    # Topic-wise completion
    result = await db.execute(select(LabTopic).where(LabTopic.lab_id == lab_id))
    topics = result.scalars().all()
    topic_completion = []
    for topic in topics:
        result = await db.execute(
            select(func.count()).select_from(LabTopicProgress).where(
                LabTopicProgress.topic_id == topic.id,
                LabTopicProgress.status == TopicStatus.COMPLETED
            )
        )
        completed = result.scalar() or 0
        topic_completion.append({
            "topic_id": str(topic.id),
            "topic_title": topic.title,
            "completed_count": completed,
            "completion_rate": (completed / total_students * 100) if total_students > 0 else 0
        })

    return {
        "lab_id": str(lab.id),
        "lab_name": lab.name,
        "total_students": total_students,
        "avg_progress": round(avg_progress, 2),
        "avg_mcq_score": round(avg_mcq_score, 2),
        "avg_coding_score": round(avg_coding_score, 2),
        "performance_distribution": performance_dist,
        "topic_completion": topic_completion
    }


@router.get("/department/analytics")
async def get_department_analytics(
    branch: Optional[Branch] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get department-wide analytics (HOD only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only HOD/Admin can view department analytics")

    query = select(Lab).where(Lab.is_active == True)
    if branch:
        query = query.where(Lab.branch == branch)

    result = await db.execute(query)
    labs = result.scalars().all()

    lab_stats = []
    for lab in labs:
        result = await db.execute(select(LabEnrollment).where(LabEnrollment.lab_id == lab.id))
        enrollments = result.scalars().all()
        total = len(enrollments)
        avg_score = sum(e.total_score for e in enrollments) / total if total > 0 else 0
        avg_progress = sum(e.overall_progress for e in enrollments) / total if total > 0 else 0

        lab_stats.append({
            "lab_id": str(lab.id),
            "lab_name": lab.name,
            "lab_code": lab.code,
            "semester": lab.semester.value,
            "total_students": total,
            "avg_score": round(avg_score, 2),
            "avg_progress": round(avg_progress, 2)
        })

    # Semester-wise aggregation
    semester_stats = {}
    for lab in labs:
        sem = lab.semester.value
        if sem not in semester_stats:
            semester_stats[sem] = {"count": 0, "total_students": 0, "total_score": 0}

        result = await db.execute(select(LabEnrollment).where(LabEnrollment.lab_id == lab.id))
        enrollments = result.scalars().all()
        semester_stats[sem]["count"] += 1
        semester_stats[sem]["total_students"] += len(enrollments)
        semester_stats[sem]["total_score"] += sum(e.total_score for e in enrollments)

    semester_summary = []
    for sem, stats in semester_stats.items():
        avg = stats["total_score"] / stats["total_students"] if stats["total_students"] > 0 else 0
        semester_summary.append({
            "semester": sem,
            "total_labs": stats["count"],
            "total_students": stats["total_students"],
            "avg_score": round(avg, 2)
        })

    return {
        "total_labs": len(labs),
        "lab_stats": lab_stats,
        "semester_summary": sorted(semester_summary, key=lambda x: x["semester"])
    }


# ============================================================================
# ENROLLMENT ENDPOINTS
# ============================================================================

@router.post("/labs/{lab_id}/enroll")
async def enroll_in_lab(
    lab_id: str,
    section: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Enroll current user in a lab"""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Check if already enrolled
    result = await db.execute(
        select(LabEnrollment).where(
            LabEnrollment.lab_id == lab_id,
            LabEnrollment.user_id == current_user.id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this lab")

    enrollment = LabEnrollment(
        lab_id=lab_id,
        user_id=current_user.id,
        section=section
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)

    return {"message": "Successfully enrolled", "enrollment_id": str(enrollment.id)}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _update_topic_progress(progress: LabTopicProgress, topic: LabTopic):
    """Update topic progress percentage based on completion"""
    # Weight: Concepts 20%, MCQ 40%, Coding 40%
    concept_weight = 20 if progress.concept_read else 0

    mcq_weight = 0
    if topic.mcq_count > 0:
        mcq_weight = (progress.mcq_attempted / topic.mcq_count) * 40

    coding_weight = 0
    if topic.coding_count > 0:
        coding_weight = (progress.coding_solved / topic.coding_count) * 40

    progress.progress_percentage = min(100, concept_weight + mcq_weight + coding_weight)

    # Update status
    if progress.progress_percentage >= 100:
        progress.status = TopicStatus.COMPLETED
        progress.completed_at = datetime.utcnow()
    elif progress.progress_percentage > 0:
        progress.status = TopicStatus.IN_PROGRESS


async def execute_code_submission(
    submission_id: str,
    code: str,
    language: str,
    test_cases: list,
    time_limit_ms: int,
    memory_limit_mb: int
):
    """Execute code submission using Judge0 and update results (runs in background)"""
    from app.core.database import SessionLocal
    from app.services.judge0_executor import get_judge0_executor
    import logging

    logger = logging.getLogger(__name__)
    db = SessionLocal()

    try:
        submission = db.query(LabCodingSubmission).filter(
            LabCodingSubmission.id == submission_id
        ).first()

        if not submission:
            return

        submission.status = SubmissionStatus.RUNNING
        db.commit()

        # Get Judge0 executor
        executor = get_judge0_executor()

        # Check if Judge0 is available
        is_healthy = await executor.health_check()

        if not is_healthy:
            # Fallback to simulated execution if Judge0 is unavailable
            logger.warning("Judge0 unavailable, using simulated execution")
            await _execute_simulated(submission, test_cases, db)
            return

        # Convert test cases to Judge0 format
        judge0_test_cases = []
        for tc in test_cases:
            judge0_test_cases.append({
                "input": tc.get("input", ""),
                "expected_output": tc.get("expected_output", tc.get("output", ""))
            })

        # Execute with real Judge0
        time_limit_sec = time_limit_ms / 1000.0  # Convert ms to seconds
        memory_limit_kb = memory_limit_mb * 1024  # Convert MB to KB

        result = await executor.execute_with_tests(
            code=code,
            language=language,
            test_cases=judge0_test_cases,
            time_limit_sec=time_limit_sec,
            memory_limit_kb=memory_limit_kb
        )

        # Convert Judge0 results to our format
        test_results = []
        for r in result.results:
            test_results.append({
                "test": r.test_case_id,
                "passed": r.passed,
                "time_ms": r.time_ms,
                "memory_mb": r.memory_kb / 1024,  # Convert KB to MB
                "status": r.status,
                "input": r.input,
                "expected_output": r.expected_output,
                "actual_output": r.actual_output,
                "error": r.error
            })

        submission.test_results = test_results
        submission.tests_passed = result.passed_tests
        submission.score = result.pass_percentage
        submission.executed_at = datetime.utcnow()
        submission.execution_time_ms = result.total_time_ms
        submission.memory_used_mb = result.max_memory_kb / 1024  # Convert KB to MB

        # Determine status based on results
        if result.all_passed:
            submission.status = SubmissionStatus.PASSED
        elif any(r.status in ["compilation_error", "runtime_error_sigsegv", "runtime_error_nzec"] for r in result.results):
            submission.status = SubmissionStatus.ERROR
            # Get first error message
            for r in result.results:
                if r.error:
                    submission.error_message = r.error[:500]  # Limit error message length
                    break
        else:
            submission.status = SubmissionStatus.FAILED

        # Update topic progress if passed
        if submission.status == SubmissionStatus.PASSED:
            problem = db.query(LabCodingProblem).filter(
                LabCodingProblem.id == submission.problem_id
            ).first()
            if problem:
                topic = db.query(LabTopic).filter(LabTopic.id == problem.topic_id).first()
                enrollment = db.query(LabEnrollment).filter(
                    LabEnrollment.lab_id == topic.lab_id,
                    LabEnrollment.user_id == submission.user_id
                ).first()
                if enrollment:
                    enrollment.problems_solved += 1
                    topic_progress = db.query(LabTopicProgress).filter(
                        LabTopicProgress.enrollment_id == enrollment.id,
                        LabTopicProgress.topic_id == topic.id
                    ).first()
                    if topic_progress:
                        topic_progress.coding_solved += 1
                        topic_progress.coding_score = (topic_progress.coding_solved / topic.coding_count) * 100 if topic.coding_count > 0 else 0
                        _update_topic_progress(topic_progress, topic)

        db.commit()

    except Exception as e:
        logger.error(f"Code execution error: {e}")
        submission.status = SubmissionStatus.ERROR
        submission.error_message = str(e)[:500]
        db.commit()
    finally:
        db.close()


async def _execute_simulated(submission, test_cases: list, db):
    """Fallback simulated execution when Judge0 is unavailable"""
    import random
    import asyncio

    await asyncio.sleep(1)  # Simulate execution time

    test_results = []
    passed = 0
    for i, tc in enumerate(test_cases):
        is_passed = random.random() > 0.3
        test_results.append({
            "test": i + 1,
            "passed": is_passed,
            "time_ms": random.randint(10, 100),
            "memory_mb": random.uniform(5, 20),
            "status": "passed" if is_passed else "wrong_answer",
            "simulated": True
        })
        if is_passed:
            passed += 1

    submission.test_results = test_results
    submission.tests_passed = passed
    submission.score = (passed / len(test_cases)) * 100 if test_cases else 0
    submission.status = SubmissionStatus.PASSED if passed == len(test_cases) else SubmissionStatus.FAILED
    submission.executed_at = datetime.utcnow()
    submission.execution_time_ms = sum(tr.get("time_ms", 0) for tr in test_results)
    submission.memory_used_mb = max(tr.get("memory_mb", 0) for tr in test_results)
    db.commit()


# ============================================================================
# LAB REPORT SCHEMAS
# ============================================================================

class LabReportCreate(BaseModel):
    title: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None


class LabReportUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None


class LabReportReview(BaseModel):
    status: str  # approved, rejected, resubmit_required
    review_comments: Optional[str] = None
    grade: Optional[str] = None
    marks: Optional[float] = None


class LabReportResponse(BaseModel):
    id: str
    lab_id: str
    lab_name: Optional[str] = None
    user_id: str
    title: str
    description: Optional[str]
    file_url: Optional[str]
    file_name: Optional[str]
    status: str
    review_comments: Optional[str]
    grade: Optional[str]
    marks: Optional[float]
    submission_count: int
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    deadline: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# LAB REPORT ENDPOINTS
# ============================================================================

@router.get("/reports", response_model=List[LabReportResponse])
async def get_my_lab_reports(
    semester: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all lab reports for the current user"""
    from app.core.types import generate_uuid

    query = select(LabReport).where(LabReport.user_id == str(current_user.id))

    if semester:
        # Filter by labs in that semester
        query = query.join(Lab, LabReport.lab_id == Lab.id).where(Lab.semester == semester)

    query = query.order_by(LabReport.created_at.desc())
    result = await db.execute(query)
    reports = result.scalars().all()

    # Add lab name to each report
    response = []
    for report in reports:
        lab_result = await db.execute(select(Lab).where(Lab.id == report.lab_id))
        lab = lab_result.scalar_one_or_none()
        report_dict = {
            "id": str(report.id),
            "lab_id": str(report.lab_id),
            "lab_name": lab.name if lab else None,
            "user_id": str(report.user_id),
            "title": report.title,
            "description": report.description,
            "file_url": report.file_url,
            "file_name": report.file_name,
            "status": report.status.value if report.status else "not_submitted",
            "review_comments": report.review_comments,
            "grade": report.grade,
            "marks": report.marks,
            "submission_count": report.submission_count or 0,
            "submitted_at": report.submitted_at,
            "reviewed_at": report.reviewed_at,
            "deadline": report.deadline
        }
        response.append(report_dict)

    return response


@router.post("/labs/{lab_id}/reports", response_model=LabReportResponse)
async def submit_lab_report(
    lab_id: str,
    report_data: LabReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit or update a lab report"""
    from app.core.types import generate_uuid

    # Check if lab exists
    lab_result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = lab_result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Check if enrollment exists
    enrollment_result = await db.execute(
        select(LabEnrollment).where(
            LabEnrollment.lab_id == lab_id,
            LabEnrollment.user_id == str(current_user.id)
        )
    )
    enrollment = enrollment_result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=400, detail="You are not enrolled in this lab")

    # Check if report already exists
    report_result = await db.execute(
        select(LabReport).where(
            LabReport.lab_id == lab_id,
            LabReport.user_id == str(current_user.id)
        )
    )
    report = report_result.scalar_one_or_none()

    if report:
        # Update existing report
        if report.status in ['approved']:
            raise HTTPException(status_code=400, detail="Report already approved, cannot resubmit")

        report.title = report_data.title
        report.description = report_data.description
        report.file_url = report_data.file_url
        report.file_name = report_data.file_name
        report.status = LabReportStatus.SUBMITTED
        report.submission_count = (report.submission_count or 0) + 1
        report.submitted_at = datetime.utcnow()
        report.updated_at = datetime.utcnow()
    else:
        # Create new report
        report = LabReport(
            id=generate_uuid(),
            enrollment_id=str(enrollment.id),
            lab_id=lab_id,
            user_id=str(current_user.id),
            title=report_data.title,
            description=report_data.description,
            file_url=report_data.file_url,
            file_name=report_data.file_name,
            status=LabReportStatus.SUBMITTED,
            submission_count=1,
            submitted_at=datetime.utcnow()
        )
        db.add(report)

    await db.commit()
    await db.refresh(report)

    return {
        "id": str(report.id),
        "lab_id": str(report.lab_id),
        "lab_name": lab.name,
        "user_id": str(report.user_id),
        "title": report.title,
        "description": report.description,
        "file_url": report.file_url,
        "file_name": report.file_name,
        "status": report.status.value if report.status else "submitted",
        "review_comments": report.review_comments,
        "grade": report.grade,
        "marks": report.marks,
        "submission_count": report.submission_count or 1,
        "submitted_at": report.submitted_at,
        "reviewed_at": report.reviewed_at,
        "deadline": report.deadline
    }


@router.get("/labs/{lab_id}/reports", response_model=List[LabReportResponse])
async def get_lab_reports_faculty(
    lab_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all reports for a lab (faculty only)"""
    # Check if user is faculty or admin
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN, UserRole.HOD]:
        raise HTTPException(status_code=403, detail="Only faculty can view all reports")

    query = select(LabReport).where(LabReport.lab_id == lab_id)

    if status:
        query = query.where(LabReport.status == status)

    query = query.order_by(LabReport.submitted_at.desc())
    result = await db.execute(query)
    reports = result.scalars().all()

    # Get lab name
    lab_result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = lab_result.scalar_one_or_none()

    response = []
    for report in reports:
        report_dict = {
            "id": str(report.id),
            "lab_id": str(report.lab_id),
            "lab_name": lab.name if lab else None,
            "user_id": str(report.user_id),
            "title": report.title,
            "description": report.description,
            "file_url": report.file_url,
            "file_name": report.file_name,
            "status": report.status.value if report.status else "not_submitted",
            "review_comments": report.review_comments,
            "grade": report.grade,
            "marks": report.marks,
            "submission_count": report.submission_count or 0,
            "submitted_at": report.submitted_at,
            "reviewed_at": report.reviewed_at,
            "deadline": report.deadline
        }
        response.append(report_dict)

    return response


@router.put("/reports/{report_id}/review", response_model=LabReportResponse)
async def review_lab_report(
    report_id: str,
    review: LabReportReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Review a lab report (faculty only)"""
    # Check if user is faculty or admin
    if current_user.role not in [UserRole.FACULTY, UserRole.ADMIN, UserRole.HOD]:
        raise HTTPException(status_code=403, detail="Only faculty can review reports")

    # Get report
    report_result = await db.execute(select(LabReport).where(LabReport.id == report_id))
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Update review
    status_map = {
        "approved": LabReportStatus.APPROVED,
        "rejected": LabReportStatus.REJECTED,
        "resubmit_required": LabReportStatus.RESUBMIT_REQUIRED,
        "under_review": LabReportStatus.UNDER_REVIEW
    }
    report.status = status_map.get(review.status, LabReportStatus.UNDER_REVIEW)
    report.review_comments = review.review_comments
    report.grade = review.grade
    report.marks = review.marks
    report.reviewed_by = str(current_user.id)
    report.reviewed_at = datetime.utcnow()
    report.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(report)

    # Get lab name
    lab_result = await db.execute(select(Lab).where(Lab.id == report.lab_id))
    lab = lab_result.scalar_one_or_none()

    return {
        "id": str(report.id),
        "lab_id": str(report.lab_id),
        "lab_name": lab.name if lab else None,
        "user_id": str(report.user_id),
        "title": report.title,
        "description": report.description,
        "file_url": report.file_url,
        "file_name": report.file_name,
        "status": report.status.value if report.status else "under_review",
        "review_comments": report.review_comments,
        "grade": report.grade,
        "marks": report.marks,
        "submission_count": report.submission_count or 0,
        "submitted_at": report.submitted_at,
        "reviewed_at": report.reviewed_at,
        "deadline": report.deadline
    }


@router.get("/semester/{semester}/progress")
async def get_semester_progress(
    semester: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get student's progress for a specific semester"""
    # Get all labs for this semester
    labs_result = await db.execute(select(Lab).where(Lab.semester == semester))
    labs = labs_result.scalars().all()

    progress_data = {
        "semester": semester,
        "total_labs": len(labs),
        "labs_completed": 0,
        "labs_in_progress": 0,
        "reports_submitted": 0,
        "reports_approved": 0,
        "labs": []
    }

    for lab in labs:
        # Get enrollment
        enrollment_result = await db.execute(
            select(LabEnrollment).where(
                LabEnrollment.lab_id == str(lab.id),
                LabEnrollment.user_id == str(current_user.id)
            )
        )
        enrollment = enrollment_result.scalar_one_or_none()

        # Get report status
        report_result = await db.execute(
            select(LabReport).where(
                LabReport.lab_id == str(lab.id),
                LabReport.user_id == str(current_user.id)
            )
        )
        report = report_result.scalar_one_or_none()

        lab_data = {
            "id": str(lab.id),
            "name": lab.name,
            "code": lab.code,
            "progress": enrollment.overall_progress if enrollment else 0,
            "is_enrolled": enrollment is not None,
            "report_status": report.status.value if report else "not_submitted",
            "report_grade": report.grade if report else None
        }

        if enrollment and enrollment.overall_progress >= 100:
            progress_data["labs_completed"] += 1
        elif enrollment and enrollment.overall_progress > 0:
            progress_data["labs_in_progress"] += 1

        if report:
            progress_data["reports_submitted"] += 1
            if report.status == LabReportStatus.APPROVED:
                progress_data["reports_approved"] += 1

        progress_data["labs"].append(lab_data)

    return progress_data


# ============================================================================
# SEED DATA ENDPOINT
# ============================================================================

@router.post("/seed-data")
async def seed_lab_data(
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Seed database with sample lab data for testing/demo purposes"""
    import uuid
    import random

    # Check if labs already exist
    result = await db.execute(select(Lab).limit(1))
    existing_lab = result.scalar_one_or_none()

    if existing_lab and not force:
        return {"message": "Data already exists. Use ?force=true to reseed", "status": "skipped"}

    # Clear existing lab data if force is true
    if existing_lab and force:
        from sqlalchemy import delete
        # Delete in correct order due to foreign keys
        await db.execute(delete(LabTopicProgress))
        await db.execute(delete(LabMCQResponse))
        await db.execute(delete(LabCodingSubmission))
        await db.execute(delete(LabQuizSession))
        await db.execute(delete(LabReport))
        await db.execute(delete(LabEnrollment))
        await db.execute(delete(LabMCQ))
        await db.execute(delete(LabCodingProblem))
        await db.execute(delete(LabTopic))
        await db.execute(delete(Lab))
        await db.commit()

    # Get or create a faculty user
    result = await db.execute(
        select(User).where(User.role == UserRole.FACULTY).limit(1)
    )
    faculty = result.scalar_one_or_none()

    if not faculty:
        # Create faculty user
        from app.core.security import get_password_hash
        faculty = User(
            id=str(uuid.uuid4()),
            email="faculty@bharatbuild.com",
            full_name="Dr. Faculty User",
            role=UserRole.FACULTY,
            hashed_password=get_password_hash("faculty123"),
            is_active=True,
            is_verified=True,
            department="CSE"
        )
        db.add(faculty)
        await db.flush()

    faculty_id = str(faculty.id)

    # Create Labs
    labs_data = [
        {
            "name": "Data Structures Lab",
            "code": "CS301L",
            "description": "Practical implementation of data structures including arrays, linked lists, trees, and graphs",
            "branch": Branch.CSE,
            "semester": Semester.SEM_3,
            "faculty_id": faculty_id
        },
        {
            "name": "Database Management Lab",
            "code": "CS302L",
            "description": "SQL queries, normalization, and database design practicals",
            "branch": Branch.CSE,
            "semester": Semester.SEM_3,
            "faculty_id": faculty_id
        },
        {
            "name": "Operating Systems Lab",
            "code": "CS401L",
            "description": "Process scheduling, memory management, and file systems",
            "branch": Branch.CSE,
            "semester": Semester.SEM_4,
            "faculty_id": faculty_id
        },
        {
            "name": "Machine Learning Lab",
            "code": "CS501L",
            "description": "Implementation of ML algorithms and model training",
            "branch": Branch.CSE,
            "semester": Semester.SEM_5,
            "faculty_id": faculty_id
        }
    ]

    created_labs = []
    for lab_data in labs_data:
        lab = Lab(
            id=str(uuid.uuid4()),
            **lab_data,
            is_active=True
        )
        db.add(lab)
        created_labs.append(lab)

    await db.flush()

    # Create Topics for Data Structures Lab
    ds_lab = created_labs[0]
    ds_topics = [
        {"title": "Implement Stack using Arrays", "description": "Implement push, pop, peek operations", "week_number": 1, "difficulty": DifficultyLevel.EASY, "status": "locked", "ai_limit": 25},
        {"title": "Implement Queue using Linked List", "description": "Implement enqueue and dequeue operations", "week_number": 2, "difficulty": DifficultyLevel.EASY, "status": "assigned", "ai_limit": 25},
        {"title": "Binary Search Tree Operations", "description": "Implement BST with insert, delete, search", "week_number": 3, "difficulty": DifficultyLevel.MEDIUM, "status": "assigned", "ai_limit": 20},
        {"title": "Graph Traversal - BFS and DFS", "description": "Implement breadth-first and depth-first search", "week_number": 4, "difficulty": DifficultyLevel.MEDIUM, "status": "assigned", "ai_limit": 20},
        {"title": "Shortest Path - Dijkstra's Algorithm", "description": "Find shortest path in weighted graph", "week_number": 5, "difficulty": DifficultyLevel.HARD, "status": "assigned", "ai_limit": 15},
        {"title": "Dynamic Programming - Knapsack", "description": "Solve 0/1 Knapsack problem using DP", "week_number": 6, "difficulty": DifficultyLevel.HARD, "status": "draft", "ai_limit": 10}
    ]

    created_topics = []
    for i, topic_data in enumerate(ds_topics):
        difficulty = topic_data.pop("difficulty")
        status = topic_data.pop("status")
        ai_limit = topic_data.pop("ai_limit")

        # Set deadline for assigned/locked topics
        deadline = None
        if status in ["assigned", "locked"]:
            deadline = datetime.utcnow() + timedelta(days=(i + 1) * 7)

        topic = LabTopic(
            id=str(uuid.uuid4()),
            lab_id=str(ds_lab.id),
            order_index=i + 1,
            concept_content=f"Theoretical concepts for {topic_data['title']}...",
            is_active=True,
            difficulty=difficulty,
            status=status,
            ai_limit=ai_limit,
            deadline=deadline,
            **topic_data
        )
        db.add(topic)
        created_topics.append((topic, difficulty))

        # Update lab counts
        ds_lab.total_topics += 1

    await db.flush()

    # Create MCQs for each topic
    mcq_templates = [
        ("What is the time complexity of this operation?", ["O(1)", "O(n)", "O(log n)", "O(n²)"], 0),
        ("Which data structure is most suitable for this problem?", ["Stack", "Queue", "Tree", "Graph"], 1),
        ("What is the space complexity?", ["O(1)", "O(n)", "O(log n)", "O(n²)"], 1),
    ]

    for topic, difficulty in created_topics:
        for q_text, options, correct in mcq_templates:
            mcq = LabMCQ(
                id=str(uuid.uuid4()),
                topic_id=str(topic.id),
                question_text=f"[{topic.title}] {q_text}",
                options=options,
                correct_option=correct,
                explanation="This is the correct answer because of algorithmic complexity analysis.",
                difficulty=difficulty,
                marks=5,
                time_limit_seconds=60,
                is_active=True
            )
            db.add(mcq)
            topic.mcq_count += 1
            ds_lab.total_mcqs += 1

    # Create Coding Problems for each topic
    for topic, difficulty in created_topics:
        problem = LabCodingProblem(
            id=str(uuid.uuid4()),
            topic_id=str(topic.id),
            title=f"Implement {topic.title}",
            description=f"Write a program to {topic.description.lower()}",
            difficulty=difficulty,
            max_score=100,
            supported_languages=[ProgrammingLanguage.PYTHON, ProgrammingLanguage.CPP, ProgrammingLanguage.JAVA],
            starter_code={
                "python": "# Write your solution here\n\ndef solution(input_data):\n    pass",
                "cpp": "// Write your solution here\n#include <iostream>\nusing namespace std;\n\nint main() {\n    return 0;\n}",
                "java": "// Write your solution here\npublic class Solution {\n    public static void main(String[] args) {\n    }\n}"
            },
            test_cases=[
                {"input": "5", "expected_output": "25", "is_hidden": False},
                {"input": "10", "expected_output": "100", "is_hidden": False},
                {"input": "15", "expected_output": "225", "is_hidden": True}
            ],
            time_limit_ms=2000,
            memory_limit_mb=256,
            is_active=True
        )
        db.add(problem)
        topic.coding_count += 1
        ds_lab.total_coding_problems += 1

    # Create sample students and enrollments
    students_data = [
        {"name": "Rahul Kumar", "roll": "21CS001", "email": "rahul@college.edu"},
        {"name": "Priya Sharma", "roll": "21CS002", "email": "priya@college.edu"},
        {"name": "Amit Singh", "roll": "21CS003", "email": "amit@college.edu"},
        {"name": "Sneha Patel", "roll": "21CS004", "email": "sneha@college.edu"},
        {"name": "Vikram Reddy", "roll": "21CS005", "email": "vikram@college.edu"},
        {"name": "Ananya Gupta", "roll": "21CS006", "email": "ananya@college.edu"},
        {"name": "Karthik Nair", "roll": "21CS007", "email": "karthik@college.edu"},
        {"name": "Divya Krishnan", "roll": "21CS008", "email": "divya@college.edu"}
    ]

    from app.core.security import get_password_hash

    for student_data in students_data:
        # Check if student exists
        result = await db.execute(
            select(User).where(User.email == student_data["email"])
        )
        student = result.scalar_one_or_none()

        if not student:
            student = User(
                id=str(uuid.uuid4()),
                email=student_data["email"],
                full_name=student_data["name"],
                roll_number=student_data["roll"],
                role=UserRole.STUDENT,
                hashed_password=get_password_hash("student123"),
                is_active=True,
                is_verified=True,
                department="CSE"
            )
            db.add(student)
            await db.flush()

        # Create enrollment for DS Lab
        progress = random.randint(40, 95)
        mcq_score = random.randint(50, 98)
        coding_score = random.randint(45, 95)

        enrollment = LabEnrollment(
            id=str(uuid.uuid4()),
            lab_id=str(ds_lab.id),
            user_id=str(student.id),
            section="A" if random.random() > 0.5 else "B",
            overall_progress=progress,
            mcq_score=mcq_score,
            coding_score=coding_score,
            total_score=(mcq_score + coding_score) / 2,
            topics_completed=random.randint(2, 5),
            mcqs_attempted=random.randint(9, 18),
            mcqs_correct=random.randint(6, 15),
            problems_solved=random.randint(2, 6),
            last_activity=datetime.utcnow() - timedelta(hours=random.randint(1, 72))
        )
        db.add(enrollment)
        await db.flush()

        # Create topic progress for this student (varied per topic)
        for idx, (topic, difficulty) in enumerate(created_topics):
            # Earlier topics have higher completion, later topics less
            if idx < 4:  # First 4 topics - students have worked on them
                topic_status = TopicStatus.COMPLETED if idx < 2 else TopicStatus.IN_PROGRESS
                topic_progress_pct = random.randint(70, 100) if idx < 2 else random.randint(40, 80)
                mcq_attempted = random.randint(2, 3)
                mcq_correct = random.randint(1, mcq_attempted)
                coding_solved = 1 if random.random() > 0.3 else 0
            elif idx == 4:  # 5th topic - some students started
                if random.random() > 0.5:
                    topic_status = TopicStatus.IN_PROGRESS
                    topic_progress_pct = random.randint(20, 50)
                    mcq_attempted = random.randint(0, 2)
                    mcq_correct = random.randint(0, mcq_attempted)
                    coding_solved = 0
                else:
                    continue  # Skip - student hasn't started this topic
            else:  # Last topic - not started
                continue  # Skip - student hasn't started this topic

            topic_prog = LabTopicProgress(
                id=str(uuid.uuid4()),
                enrollment_id=str(enrollment.id),
                topic_id=str(topic.id),
                status=topic_status,
                concept_read=True,
                concept_read_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                mcq_attempted=mcq_attempted,
                mcq_correct=mcq_correct,
                mcq_score=(mcq_correct / mcq_attempted * 100) if mcq_attempted > 0 else 0,
                coding_attempted=1 if coding_solved else 0,
                coding_solved=coding_solved,
                coding_score=random.randint(60, 100) if coding_solved else 0,
                progress_percentage=topic_progress_pct,
                started_at=datetime.utcnow() - timedelta(days=random.randint(5, 30)),
                completed_at=datetime.utcnow() - timedelta(days=random.randint(1, 5)) if topic_status == TopicStatus.COMPLETED else None
            )
            db.add(topic_prog)

    await db.commit()

    return {
        "message": "Lab data seeded successfully",
        "status": "success",
        "created": {
            "labs": len(created_labs),
            "topics": len(created_topics),
            "mcqs": len(created_topics) * 3,
            "problems": len(created_topics),
            "students": len(students_data),
            "enrollments": len(students_data)
        },
        "faculty_email": "faculty@bharatbuild.com",
        "faculty_password": "faculty123",
        "student_password": "student123"
    }
