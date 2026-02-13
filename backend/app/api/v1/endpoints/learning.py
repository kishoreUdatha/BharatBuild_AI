"""
Learning Endpoints - API for learning checkpoints, quizzes, and certificates
Gates project download until student demonstrates understanding
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.logging_config import logger
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.learning import (
    ProjectLearningProgress,
    LearningQuizQuestion,
    LearningFileExplanation,
    LearningCertificate
)
from app.services.learning_quiz_service import learning_quiz_service
from app.services.certificate_service import certificate_service
from app.modules.agents.explainer_agent import ExplainerAgent

router = APIRouter(prefix="/learning", tags=["Learning Mode"])


# ============================================================================
# Request/Response Models
# ============================================================================

class MarkFileUnderstoodRequest(BaseModel):
    file_path: str


class QuizSubmitRequest(BaseModel):
    answers: Dict[str, int] = Field(..., description="Map of question_id to selected_option index")


class VivaReviewRequest(BaseModel):
    question_index: int = Field(..., description="Index of the viva question being marked as reviewed")


class LearningProgressResponse(BaseModel):
    project_id: str
    user_id: str

    # Checkpoint 1
    checkpoint_1_completed: bool
    files_reviewed: List[str]
    files_reviewed_count: int

    # Checkpoint 2
    checkpoint_2_score: Optional[float]
    checkpoint_2_passed: bool
    checkpoint_2_attempts: int

    # Checkpoint 3
    checkpoint_3_completed: bool
    viva_questions_reviewed: int
    viva_total_questions: int

    # Overall
    overall_progress: int
    can_download: bool
    certificate_generated: bool
    certificate_id: Optional[str]


class QuizQuestionResponse(BaseModel):
    id: str
    question_text: str
    options: List[str]
    concept: Optional[str]
    difficulty: str
    related_file: Optional[str]


class QuizResultResponse(BaseModel):
    total_questions: int
    correct_answers: int
    score: float
    passing_score: float
    passed: bool
    feedback: str
    results: List[Dict[str, Any]]


class FileExplanationResponse(BaseModel):
    file_path: str
    simple_explanation: Optional[str]
    technical_explanation: Optional[str]
    key_concepts: List[str]
    analogies: List[str]
    best_practices: List[str]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/projects/{project_id}/progress", response_model=LearningProgressResponse)
async def get_learning_progress(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current learning progress for a project"""
    # Get or create learning progress
    progress = await _get_or_create_progress(db, project_id, current_user.id)

    return LearningProgressResponse(
        project_id=str(progress.project_id),
        user_id=str(progress.user_id),
        checkpoint_1_completed=progress.checkpoint_1_completed,
        files_reviewed=progress.files_reviewed or [],
        files_reviewed_count=len(progress.files_reviewed or []),
        checkpoint_2_score=progress.checkpoint_2_score,
        checkpoint_2_passed=progress.checkpoint_2_passed,
        checkpoint_2_attempts=progress.checkpoint_2_attempts,
        checkpoint_3_completed=progress.checkpoint_3_completed,
        viva_questions_reviewed=progress.viva_questions_reviewed,
        viva_total_questions=progress.viva_total_questions,
        overall_progress=progress.overall_progress,
        can_download=progress.can_download,
        certificate_generated=progress.certificate_generated,
        certificate_id=progress.certificate_id
    )


@router.post("/projects/{project_id}/mark-understood")
async def mark_file_understood(
    project_id: str,
    request: MarkFileUnderstoodRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a file as understood by the student"""
    progress = await _get_or_create_progress(db, project_id, current_user.id)

    # Update files reviewed
    files_reviewed = progress.files_reviewed or []
    if request.file_path not in files_reviewed:
        files_reviewed.append(request.file_path)
        progress.files_reviewed = files_reviewed

        # Update explanations viewed
        explanations_viewed = progress.explanations_viewed or {}
        explanations_viewed[request.file_path] = {
            "viewed_at": datetime.utcnow().isoformat(),
            "understood": True
        }
        progress.explanations_viewed = explanations_viewed

    # Check if checkpoint 1 is complete (minimum 5 files)
    if len(files_reviewed) >= 5 and not progress.checkpoint_1_completed:
        progress.checkpoint_1_completed = True
        logger.info(f"[Learning] User {current_user.id} completed Checkpoint 1 for project {project_id}")

    progress.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(progress)

    return {
        "success": True,
        "files_reviewed": len(files_reviewed),
        "checkpoint_1_completed": progress.checkpoint_1_completed,
        "message": f"Marked {request.file_path} as understood"
    }


@router.get("/projects/{project_id}/file-explanation/{file_path:path}")
async def get_file_explanation(
    project_id: str,
    file_path: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get or generate explanation for a specific file"""
    # Check if explanation already exists
    result = await db.execute(
        select(LearningFileExplanation)
        .where(LearningFileExplanation.project_id == project_id)
        .where(LearningFileExplanation.file_path == file_path)
    )
    existing = result.scalar_one_or_none()

    if existing:
        return FileExplanationResponse(
            file_path=existing.file_path,
            simple_explanation=existing.simple_explanation,
            technical_explanation=existing.technical_explanation,
            key_concepts=existing.key_concepts or [],
            analogies=existing.analogies or [],
            best_practices=existing.best_practices or []
        )

    # Generate new explanation using ExplainerAgent
    # Note: In production, this would fetch the file content from storage
    return FileExplanationResponse(
        file_path=file_path,
        simple_explanation="Explanation will be generated when the file is loaded.",
        technical_explanation=None,
        key_concepts=[],
        analogies=[],
        best_practices=[]
    )


@router.get("/projects/{project_id}/quiz")
async def get_learning_quiz(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quiz questions for the project"""
    # Check if questions already exist
    result = await db.execute(
        select(LearningQuizQuestion)
        .where(LearningQuizQuestion.project_id == project_id)
        .limit(10)
    )
    existing_questions = result.scalars().all()

    if existing_questions:
        return {
            "project_id": project_id,
            "questions": [
                QuizQuestionResponse(
                    id=str(q.id),
                    question_text=q.question_text,
                    options=q.options,
                    concept=q.concept,
                    difficulty=q.difficulty,
                    related_file=q.related_file
                ).model_dump()
                for q in existing_questions
            ],
            "total_questions": len(existing_questions),
            "passing_score": 70.0
        }

    # Generate new questions
    # In production, fetch project files from storage
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate questions (using fallback for now)
    questions = await learning_quiz_service.generate_questions(
        project_id=project_id,
        files=[],  # Would be populated from project files in production
        project_context={
            "title": project.title,
            "domain": project.domain,
            "tech_stack": project.tech_stack or [],
            "description": project.description
        },
        num_questions=5
    )

    # Save questions to database
    for q_data in questions:
        question = LearningQuizQuestion(
            project_id=project_id,
            question_text=q_data["question_text"],
            options=q_data["options"],
            correct_option=q_data["correct_option"],
            explanation=q_data.get("explanation"),
            related_file=q_data.get("related_file"),
            concept=q_data.get("concept"),
            difficulty=q_data.get("difficulty", "medium")
        )
        db.add(question)

    await db.commit()

    return {
        "project_id": project_id,
        "questions": [
            QuizQuestionResponse(
                id=q["id"],
                question_text=q["question_text"],
                options=q["options"],
                concept=q.get("concept"),
                difficulty=q.get("difficulty", "medium"),
                related_file=q.get("related_file")
            ).model_dump()
            for q in questions
        ],
        "total_questions": len(questions),
        "passing_score": 70.0
    }


@router.post("/projects/{project_id}/quiz/submit", response_model=QuizResultResponse)
async def submit_quiz(
    project_id: str,
    request: QuizSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit quiz answers and check if passed"""
    # Get questions
    result = await db.execute(
        select(LearningQuizQuestion)
        .where(LearningQuizQuestion.project_id == project_id)
    )
    questions = result.scalars().all()

    if not questions:
        raise HTTPException(status_code=404, detail="No quiz found for this project")

    # Convert to dict format for evaluation
    questions_data = [
        {
            "id": str(q.id),
            "question_text": q.question_text,
            "options": q.options,
            "correct_option": q.correct_option,
            "explanation": q.explanation,
            "concept": q.concept
        }
        for q in questions
    ]

    # Evaluate quiz
    evaluation = await learning_quiz_service.evaluate_quiz(
        questions=questions_data,
        answers=request.answers,
        passing_score=70.0
    )

    # Update learning progress
    progress = await _get_or_create_progress(db, project_id, current_user.id)

    progress.checkpoint_2_attempts += 1
    progress.quiz_answers = request.answers
    progress.checkpoint_2_score = evaluation["score"]
    progress.checkpoint_2_passed = evaluation["passed"]
    progress.quiz_completed_at = datetime.utcnow()

    # Check download eligibility
    if evaluation["passed"]:
        progress.check_download_eligibility()
        logger.info(f"[Learning] User {current_user.id} passed quiz for project {project_id} with {evaluation['score']}%")

    progress.updated_at = datetime.utcnow()
    await db.commit()

    return QuizResultResponse(
        total_questions=evaluation["total_questions"],
        correct_answers=evaluation["correct_answers"],
        score=evaluation["score"],
        passing_score=evaluation["passing_score"],
        passed=evaluation["passed"],
        feedback=evaluation["feedback"],
        results=evaluation["results"]
    )


@router.post("/projects/{project_id}/viva/mark-reviewed")
async def mark_viva_reviewed(
    project_id: str,
    request: VivaReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a viva question as reviewed"""
    progress = await _get_or_create_progress(db, project_id, current_user.id)

    # Increment reviewed count (capped at total)
    if progress.viva_questions_reviewed < progress.viva_total_questions:
        progress.viva_questions_reviewed += 1

    # Check if checkpoint 3 is complete (reviewed at least 80% of questions)
    if progress.viva_total_questions > 0:
        review_ratio = progress.viva_questions_reviewed / progress.viva_total_questions
        if review_ratio >= 0.8 and not progress.checkpoint_3_completed:
            progress.checkpoint_3_completed = True
            logger.info(f"[Learning] User {current_user.id} completed Checkpoint 3 for project {project_id}")

    progress.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "success": True,
        "viva_questions_reviewed": progress.viva_questions_reviewed,
        "viva_total_questions": progress.viva_total_questions,
        "checkpoint_3_completed": progress.checkpoint_3_completed
    }


@router.get("/projects/{project_id}/can-download")
async def check_download_eligibility(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if student can download the project"""
    progress = await _get_or_create_progress(db, project_id, current_user.id)

    # Re-check eligibility
    can_download = progress.check_download_eligibility()

    return {
        "can_download": can_download,
        "reason": _get_download_block_reason(progress) if not can_download else None,
        "overall_progress": progress.overall_progress,
        "checkpoint_2_passed": progress.checkpoint_2_passed,
        "checkpoint_2_score": progress.checkpoint_2_score,
        "required_score": 70.0
    }


@router.post("/projects/{project_id}/certificate/generate")
async def generate_certificate(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate learning certificate (only if eligible)"""
    progress = await _get_or_create_progress(db, project_id, current_user.id)

    # Check eligibility
    if not progress.can_download:
        raise HTTPException(
            status_code=400,
            detail="Must pass the concept quiz to generate certificate"
        )

    # Check if certificate already exists
    if progress.certificate_generated and progress.certificate_id:
        # Fetch existing certificate
        result = await db.execute(
            select(LearningCertificate)
            .where(LearningCertificate.certificate_id == progress.certificate_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return {
                "success": True,
                "certificate_id": existing.certificate_id,
                "message": "Certificate already generated",
                "issued_at": existing.issued_at.isoformat()
            }

    # Get project details
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate certificate
    cert_result = await certificate_service.generate_certificate(
        student_name=current_user.full_name or current_user.email.split('@')[0],
        student_email=current_user.email,
        project_title=project.title,
        project_domain=project.domain or "Web Application",
        tech_stack=project.tech_stack or [],
        quiz_score=progress.checkpoint_2_score or 0,
        quiz_attempts=progress.checkpoint_2_attempts,
        files_reviewed=len(progress.files_reviewed or []),
        viva_questions_reviewed=progress.viva_questions_reviewed
    )

    if not cert_result["success"]:
        raise HTTPException(status_code=500, detail="Failed to generate certificate")

    # Save certificate to database
    certificate = LearningCertificate(
        certificate_id=cert_result["certificate_id"],
        project_id=project_id,
        user_id=current_user.id,
        student_name=current_user.full_name or current_user.email.split('@')[0],
        student_email=current_user.email,
        project_title=project.title,
        project_domain=project.domain,
        tech_stack=project.tech_stack or [],
        quiz_score=progress.checkpoint_2_score or 0,
        quiz_attempts=progress.checkpoint_2_attempts,
        files_reviewed=len(progress.files_reviewed or []),
        viva_questions_reviewed=progress.viva_questions_reviewed
    )
    db.add(certificate)

    # Update progress
    progress.certificate_generated = True
    progress.certificate_id = cert_result["certificate_id"]
    progress.certificate_generated_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "certificate_id": cert_result["certificate_id"],
        "message": "Certificate generated successfully",
        "issued_at": datetime.utcnow().isoformat()
    }


@router.get("/projects/{project_id}/certificate/download")
async def download_certificate(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download the learning certificate PDF"""
    progress = await _get_or_create_progress(db, project_id, current_user.id)

    if not progress.certificate_generated or not progress.certificate_id:
        raise HTTPException(status_code=404, detail="Certificate not generated yet")

    # Get certificate
    result = await db.execute(
        select(LearningCertificate)
        .where(LearningCertificate.certificate_id == progress.certificate_id)
    )
    certificate = result.scalar_one_or_none()

    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")

    # Generate fresh PDF
    cert_result = await certificate_service.generate_certificate(
        student_name=certificate.student_name,
        student_email=certificate.student_email,
        project_title=certificate.project_title,
        project_domain=certificate.project_domain,
        tech_stack=certificate.tech_stack or [],
        quiz_score=certificate.quiz_score,
        quiz_attempts=certificate.quiz_attempts,
        files_reviewed=certificate.files_reviewed,
        viva_questions_reviewed=certificate.viva_questions_reviewed,
        certificate_id=certificate.certificate_id
    )

    if not cert_result["success"] or not cert_result.get("pdf_content"):
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

    filename = certificate_service.generate_certificate_filename(
        certificate.project_title,
        certificate.student_name
    )

    return Response(
        content=cert_result["pdf_content"],
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/verify/{certificate_id}")
async def verify_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Public endpoint to verify a certificate"""
    result = await db.execute(
        select(LearningCertificate)
        .where(LearningCertificate.certificate_id == certificate_id)
    )
    certificate = result.scalar_one_or_none()

    if not certificate:
        return {
            "valid": False,
            "message": "Certificate not found"
        }

    return {
        "valid": True,
        "certificate_id": certificate.certificate_id,
        "student_name": certificate.student_name,
        "project_title": certificate.project_title,
        "quiz_score": certificate.quiz_score,
        "issued_at": certificate.issued_at.isoformat(),
        "message": "Certificate is valid and verified"
    }


# ============================================================================
# Helper Functions
# ============================================================================

async def _get_or_create_progress(
    db: AsyncSession,
    project_id: str,
    user_id: str
) -> ProjectLearningProgress:
    """Get existing progress or create new one"""
    result = await db.execute(
        select(ProjectLearningProgress)
        .where(ProjectLearningProgress.project_id == project_id)
        .where(ProjectLearningProgress.user_id == user_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = ProjectLearningProgress(
            project_id=project_id,
            user_id=user_id,
            files_reviewed=[],
            explanations_viewed={},
            quiz_answers={},
            viva_total_questions=25  # Default viva questions count
        )
        db.add(progress)
        await db.commit()
        await db.refresh(progress)

    return progress


def _get_download_block_reason(progress: ProjectLearningProgress) -> str:
    """Get reason why download is blocked"""
    if not progress.checkpoint_2_passed:
        if progress.checkpoint_2_score is None:
            return "Complete the concept quiz to unlock download"
        else:
            return f"Score {progress.checkpoint_2_score:.0f}% - Need 70% to pass"

    return "Unknown reason"
