"""
Campus Drive API - Student registration and quiz endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import random

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.campus_drive import (
    CampusDrive,
    CampusDriveRegistration,
    CampusDriveQuestion,
    CampusDriveResponse,
    QuestionCategory,
    RegistrationStatus,
)
from app.schemas.campus_drive import (
    CampusDriveResponse as CampusDriveResponseSchema,
    StudentRegistrationCreate,
    RegistrationResponse,
    QuestionForQuiz,
    QuizStartResponse,
    QuizSubmission,
    QuizResultResponse,
)

router = APIRouter(prefix="/campus-drive", tags=["Campus Drive"])


# ============================================
# Public Endpoints
# ============================================

@router.get("/drives", response_model=List[CampusDriveResponseSchema])
async def list_active_drives(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active campus drives.
    Public endpoint - no authentication required.
    """
    try:
        result = await db.execute(
            select(CampusDrive)
            .where(CampusDrive.is_active == True)
            .order_by(CampusDrive.created_at.desc())
        )
        drives = result.scalars().all()
        return drives

    except Exception as e:
        logger.error(f"Error fetching campus drives: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch campus drives"
        )


@router.get("/drives/{drive_id}", response_model=CampusDriveResponseSchema)
async def get_drive(
    drive_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific campus drive by ID"""
    try:
        result = await db.execute(
            select(CampusDrive).where(CampusDrive.id == drive_id)
        )
        drive = result.scalar_one_or_none()

        if not drive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campus drive not found"
            )

        return drive

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching drive {drive_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch campus drive"
        )


@router.post("/drives/{drive_id}/register", response_model=RegistrationResponse)
async def register_student(
    drive_id: str,
    registration: StudentRegistrationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a student for a campus drive.
    Public endpoint - no authentication required.
    """
    try:
        # Check if drive exists and is active
        drive_result = await db.execute(
            select(CampusDrive).where(CampusDrive.id == drive_id)
        )
        drive = drive_result.scalar_one_or_none()

        if not drive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campus drive not found"
            )

        if not drive.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is closed for this drive"
            )

        # Check registration deadline
        if drive.registration_end and datetime.utcnow() > drive.registration_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration deadline has passed"
            )

        # Check if already registered
        existing = await db.execute(
            select(CampusDriveRegistration).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.email == registration.email
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already registered for this drive"
            )

        # Create registration
        db_registration = CampusDriveRegistration(
            campus_drive_id=drive_id,
            full_name=registration.full_name,
            email=registration.email,
            phone=registration.phone,
            college_name=registration.college_name,
            department=registration.department,
            year_of_study=registration.year_of_study,
            roll_number=registration.roll_number,
            cgpa=registration.cgpa,
            status=RegistrationStatus.REGISTERED
        )

        db.add(db_registration)
        await db.commit()
        await db.refresh(db_registration)

        logger.info(f"New campus drive registration: {registration.email} for drive {drive_id}")

        return db_registration

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering student: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register. Please try again."
        )


@router.get("/drives/{drive_id}/registration/{email}", response_model=RegistrationResponse)
async def check_registration(
    drive_id: str,
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if a student is registered and get their status"""
    try:
        result = await db.execute(
            select(CampusDriveRegistration).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.email == email
            )
        )
        registration = result.scalar_one_or_none()

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )

        return registration

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check registration"
        )


# ============================================
# Quiz Endpoints
# ============================================

@router.post("/drives/{drive_id}/quiz/start")
async def start_quiz(
    drive_id: str,
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Start the quiz for a registered student.
    Returns questions without correct answers.
    """
    try:
        # Get registration
        result = await db.execute(
            select(CampusDriveRegistration).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.email == email
            )
        )
        registration = result.scalar_one_or_none()

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not registered for this drive"
            )

        # Check if quiz already completed
        if registration.status == RegistrationStatus.QUIZ_COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already completed the quiz"
            )

        # Get drive
        drive_result = await db.execute(
            select(CampusDrive).where(CampusDrive.id == drive_id)
        )
        drive = drive_result.scalar_one_or_none()

        if not drive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campus drive not found"
            )

        # Get questions for each category
        questions = []

        for category, count in [
            (QuestionCategory.LOGICAL, drive.logical_questions),
            (QuestionCategory.TECHNICAL, drive.technical_questions),
            (QuestionCategory.AI_ML, drive.ai_ml_questions),
            (QuestionCategory.ENGLISH, drive.english_questions),
        ]:
            # Get questions - either drive-specific or global
            q_result = await db.execute(
                select(CampusDriveQuestion).where(
                    CampusDriveQuestion.category == category,
                    (CampusDriveQuestion.campus_drive_id == drive_id) |
                    (CampusDriveQuestion.is_global == True)
                )
            )
            category_questions = list(q_result.scalars().all())

            # Randomly select required number of questions
            if len(category_questions) >= count:
                selected = random.sample(category_questions, count)
            else:
                selected = category_questions

            questions.extend(selected)

        # Shuffle all questions
        random.shuffle(questions)

        # Update registration status
        registration.status = RegistrationStatus.QUIZ_IN_PROGRESS
        registration.quiz_start_time = datetime.utcnow()
        await db.commit()

        # Convert to response format (without correct answers)
        quiz_questions = [
            QuestionForQuiz(
                id=q.id,
                question_text=q.question_text,
                category=q.category,
                options=q.options,
                marks=q.marks
            )
            for q in questions
        ]

        return QuizStartResponse(
            registration_id=registration.id,
            drive_name=drive.name,
            duration_minutes=drive.quiz_duration_minutes,
            total_questions=len(quiz_questions),
            questions=quiz_questions,
            start_time=registration.quiz_start_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting quiz: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start quiz"
        )


@router.post("/drives/{drive_id}/quiz/submit", response_model=QuizResultResponse)
async def submit_quiz(
    drive_id: str,
    email: str,
    submission: QuizSubmission,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit quiz answers and get results.
    """
    try:
        # Get registration
        result = await db.execute(
            select(CampusDriveRegistration).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.email == email
            )
        )
        registration = result.scalar_one_or_none()

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )

        if registration.status == RegistrationStatus.QUIZ_COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz already submitted"
            )

        # Get drive for passing percentage
        drive_result = await db.execute(
            select(CampusDrive).where(CampusDrive.id == drive_id)
        )
        drive = drive_result.scalar_one_or_none()

        # Process answers
        total_marks = 0
        marks_obtained = 0
        correct_count = 0
        wrong_count = 0
        attempted = 0

        # Section-wise tracking
        section_scores = {
            QuestionCategory.LOGICAL: {"obtained": 0, "total": 0},
            QuestionCategory.TECHNICAL: {"obtained": 0, "total": 0},
            QuestionCategory.AI_ML: {"obtained": 0, "total": 0},
            QuestionCategory.ENGLISH: {"obtained": 0, "total": 0},
        }

        for answer in submission.answers:
            # Get question
            q_result = await db.execute(
                select(CampusDriveQuestion).where(CampusDriveQuestion.id == str(answer.question_id))
            )
            question = q_result.scalar_one_or_none()

            if not question:
                continue

            total_marks += question.marks
            section_scores[question.category]["total"] += question.marks

            is_correct = False
            marks = 0

            if answer.selected_option is not None:
                attempted += 1
                if answer.selected_option == question.correct_option:
                    is_correct = True
                    marks = question.marks
                    correct_count += 1
                else:
                    wrong_count += 1

            marks_obtained += marks
            section_scores[question.category]["obtained"] += marks

            # Save response
            response = CampusDriveResponse(
                registration_id=registration.id,
                question_id=question.id,
                selected_option=answer.selected_option,
                is_correct=is_correct,
                marks_obtained=marks
            )
            db.add(response)

        # Calculate percentage
        percentage = (marks_obtained / total_marks * 100) if total_marks > 0 else 0
        is_qualified = percentage >= drive.passing_percentage

        # Update registration
        registration.status = RegistrationStatus.QUIZ_COMPLETED
        registration.quiz_end_time = datetime.utcnow()
        registration.quiz_score = marks_obtained
        registration.total_marks = total_marks
        registration.percentage = percentage
        registration.is_qualified = is_qualified
        registration.logical_score = section_scores[QuestionCategory.LOGICAL]["obtained"]
        registration.technical_score = section_scores[QuestionCategory.TECHNICAL]["obtained"]
        registration.ai_ml_score = section_scores[QuestionCategory.AI_ML]["obtained"]
        registration.english_score = section_scores[QuestionCategory.ENGLISH]["obtained"]

        if is_qualified:
            registration.status = RegistrationStatus.QUALIFIED
        else:
            registration.status = RegistrationStatus.NOT_QUALIFIED

        await db.commit()

        logger.info(f"Quiz submitted: {email} scored {percentage}% - {'QUALIFIED' if is_qualified else 'NOT QUALIFIED'}")

        return QuizResultResponse(
            registration_id=registration.id,
            total_questions=len(submission.answers),
            attempted=attempted,
            correct=correct_count,
            wrong=wrong_count,
            total_marks=total_marks,
            marks_obtained=marks_obtained,
            percentage=round(percentage, 2),
            is_qualified=is_qualified,
            passing_percentage=drive.passing_percentage,
            logical_score=section_scores[QuestionCategory.LOGICAL]["obtained"],
            logical_total=section_scores[QuestionCategory.LOGICAL]["total"],
            technical_score=section_scores[QuestionCategory.TECHNICAL]["obtained"],
            technical_total=section_scores[QuestionCategory.TECHNICAL]["total"],
            ai_ml_score=section_scores[QuestionCategory.AI_ML]["obtained"],
            ai_ml_total=section_scores[QuestionCategory.AI_ML]["total"],
            english_score=section_scores[QuestionCategory.ENGLISH]["obtained"],
            english_total=section_scores[QuestionCategory.ENGLISH]["total"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting quiz: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit quiz"
        )


@router.get("/drives/{drive_id}/result/{email}", response_model=QuizResultResponse)
async def get_result(
    drive_id: str,
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """Get quiz result for a student"""
    try:
        # Get registration
        result = await db.execute(
            select(CampusDriveRegistration).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.email == email
            )
        )
        registration = result.scalar_one_or_none()

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )

        if registration.status not in [RegistrationStatus.QUIZ_COMPLETED, RegistrationStatus.QUALIFIED, RegistrationStatus.NOT_QUALIFIED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz not yet completed"
            )

        # Get drive
        drive_result = await db.execute(
            select(CampusDrive).where(CampusDrive.id == drive_id)
        )
        drive = drive_result.scalar_one_or_none()

        # Count responses
        responses_result = await db.execute(
            select(CampusDriveResponse).where(
                CampusDriveResponse.registration_id == registration.id
            )
        )
        responses = responses_result.scalars().all()

        attempted = sum(1 for r in responses if r.selected_option is not None)
        correct = sum(1 for r in responses if r.is_correct)
        wrong = attempted - correct

        return QuizResultResponse(
            registration_id=registration.id,
            total_questions=len(responses),
            attempted=attempted,
            correct=correct,
            wrong=wrong,
            total_marks=registration.total_marks or 0,
            marks_obtained=registration.quiz_score or 0,
            percentage=registration.percentage or 0,
            is_qualified=registration.is_qualified,
            passing_percentage=drive.passing_percentage,
            logical_score=registration.logical_score,
            logical_total=drive.logical_questions,
            technical_score=registration.technical_score,
            technical_total=drive.technical_questions,
            ai_ml_score=registration.ai_ml_score,
            ai_ml_total=drive.ai_ml_questions,
            english_score=registration.english_score,
            english_total=drive.english_questions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch result"
        )
