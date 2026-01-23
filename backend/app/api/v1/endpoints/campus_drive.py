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
    QuizProgressSave,
    QuizProgressResponse,
    QuizResumeResponse,
    SavedAnswer,
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

        # Get all questions in one query (optimized for performance)
        q_result = await db.execute(
            select(CampusDriveQuestion).where(
                (CampusDriveQuestion.campus_drive_id == drive_id) |
                (CampusDriveQuestion.is_global == True)
            )
        )
        all_questions = list(q_result.scalars().all())

        # Group by category
        questions_by_category = {
            QuestionCategory.LOGICAL: [],
            QuestionCategory.TECHNICAL: [],
            QuestionCategory.AI_ML: [],
            QuestionCategory.ENGLISH: [],
            QuestionCategory.CODING: [],
        }
        for q in all_questions:
            if q.category in questions_by_category:
                questions_by_category[q.category].append(q)

        # Select required number from each category
        questions = []
        category_counts = [
            (QuestionCategory.LOGICAL, drive.logical_questions),
            (QuestionCategory.TECHNICAL, drive.technical_questions),
            (QuestionCategory.AI_ML, drive.ai_ml_questions),
            (QuestionCategory.ENGLISH, drive.english_questions),
            (QuestionCategory.CODING, getattr(drive, 'coding_questions', 0) or 0),
        ]

        for category, count in category_counts:
            if count <= 0:
                continue
            category_questions = questions_by_category.get(category, [])
            if len(category_questions) >= count:
                selected = random.sample(category_questions, count)
            else:
                selected = category_questions
            questions.extend(selected)

        # Shuffle all questions using registration-specific seed
        # This ensures same user gets same order if they refresh, but different users get different orders
        user_seed = hash(str(registration.id) + str(drive_id))
        rng = random.Random(user_seed)
        rng.shuffle(questions)

        # Update registration status
        registration.status = RegistrationStatus.QUIZ_IN_PROGRESS
        registration.quiz_start_time = datetime.utcnow()
        await db.commit()

        # Convert to response format with shuffled options per question
        # Each user gets different option order based on their registration + question ID
        quiz_questions = []
        for q in questions:
            # Create a seed unique to this user + question combination
            option_seed = hash(str(registration.id) + str(q.id))
            option_rng = random.Random(option_seed)

            # Create shuffled indices and shuffle options
            original_options = list(q.options)
            indices = list(range(len(original_options)))
            option_rng.shuffle(indices)

            shuffled_options = [original_options[i] for i in indices]

            quiz_questions.append(
                QuestionForQuiz(
                    id=q.id,
                    question_text=q.question_text,
                    category=q.category,
                    options=shuffled_options,
                    marks=q.marks
                )
            )

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

        # Batch fetch all questions at once (fixes N+1 query problem)
        question_ids = [str(answer.question_id) for answer in submission.answers]
        q_result = await db.execute(
            select(CampusDriveQuestion).where(CampusDriveQuestion.id.in_(question_ids))
        )
        questions_list = q_result.scalars().all()
        questions_map = {str(q.id): q for q in questions_list}

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
            QuestionCategory.CODING: {"obtained": 0, "total": 0},
        }

        # Prepare bulk responses list
        responses_to_add = []

        for answer in submission.answers:
            question = questions_map.get(str(answer.question_id))

            if not question:
                continue

            total_marks += question.marks
            section_scores[question.category]["total"] += question.marks

            is_correct = False
            marks = 0

            if answer.selected_option is not None:
                attempted += 1

                # Recreate the same option shuffle to map user's selection back to original index
                # This uses the same seed as when the quiz was started
                option_seed = hash(str(registration.id) + str(question.id))
                option_rng = random.Random(option_seed)

                # Get the shuffle mapping: indices[shuffled_pos] = original_pos
                indices = list(range(len(question.options)))
                option_rng.shuffle(indices)

                # Map user's selected shuffled index back to original index
                # User selected shuffled position -> we need original position
                # indices[i] gives original index that is now at shuffled position i
                original_selected = indices[answer.selected_option] if answer.selected_option < len(indices) else -1

                if original_selected == question.correct_option:
                    is_correct = True
                    marks = question.marks
                    correct_count += 1
                else:
                    wrong_count += 1

            marks_obtained += marks
            section_scores[question.category]["obtained"] += marks

            # Prepare response for bulk insert
            responses_to_add.append(CampusDriveResponse(
                registration_id=registration.id,
                question_id=question.id,
                selected_option=answer.selected_option,
                is_correct=is_correct,
                marks_obtained=marks
            ))

        # Bulk add all responses
        db.add_all(responses_to_add)

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
        registration.coding_score = section_scores[QuestionCategory.CODING]["obtained"]

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
            coding_score=section_scores[QuestionCategory.CODING]["obtained"],
            coding_total=section_scores[QuestionCategory.CODING]["total"],
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


# ============================================
# Quiz Progress Save & Resume Endpoints
# ============================================

@router.post("/drives/{drive_id}/quiz/save-progress", response_model=QuizProgressResponse)
async def save_quiz_progress(
    drive_id: str,
    email: str,
    progress: QuizProgressSave,
    db: AsyncSession = Depends(get_db)
):
    """
    Save quiz progress without submitting.
    Allows students to resume if browser crashes.
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

        # Only allow saving if quiz is in progress
        if registration.status != RegistrationStatus.QUIZ_IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz is not in progress"
            )

        # Check if quiz time has expired
        if registration.quiz_start_time:
            drive_result = await db.execute(
                select(CampusDrive).where(CampusDrive.id == drive_id)
            )
            drive = drive_result.scalar_one_or_none()

            elapsed = (datetime.utcnow() - registration.quiz_start_time).total_seconds()
            if elapsed > (drive.quiz_duration_minutes * 60):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quiz time has expired"
                )

        # Delete existing saved responses for this registration
        await db.execute(
            CampusDriveResponse.__table__.delete().where(
                CampusDriveResponse.registration_id == registration.id
            )
        )

        # Save new responses
        saved_count = 0
        for answer in progress.answers:
            if answer.selected_option is not None:
                response = CampusDriveResponse(
                    registration_id=registration.id,
                    question_id=str(answer.question_id),
                    selected_option=answer.selected_option,
                    is_correct=False,  # Will be calculated on final submit
                    marks_obtained=0
                )
                db.add(response)
                saved_count += 1

        await db.commit()

        logger.info(f"Quiz progress saved: {email} - {saved_count} answers")
        return QuizProgressResponse(
            saved_count=saved_count,
            message="Progress saved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving quiz progress: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save progress"
        )


@router.get("/drives/{drive_id}/quiz/resume", response_model=QuizResumeResponse)
async def resume_quiz(
    drive_id: str,
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check if student has an in-progress quiz and return saved answers.
    Returns questions with any previously saved answers.
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

        # Check if quiz is completed
        if registration.status in [RegistrationStatus.QUIZ_COMPLETED, RegistrationStatus.QUALIFIED, RegistrationStatus.NOT_QUALIFIED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz already completed"
            )

        # Check if quiz was started
        if registration.status != RegistrationStatus.QUIZ_IN_PROGRESS or not registration.quiz_start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz not started yet"
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

        # Calculate remaining time
        elapsed = (datetime.utcnow() - registration.quiz_start_time).total_seconds()
        total_seconds = drive.quiz_duration_minutes * 60
        remaining_seconds = max(0, int(total_seconds - elapsed))

        # Check if time expired
        if remaining_seconds <= 0:
            return QuizResumeResponse(
                registration_id=registration.id,
                drive_name=drive.name,
                duration_minutes=drive.quiz_duration_minutes,
                total_questions=0,
                questions=[],
                start_time=registration.quiz_start_time,
                time_remaining_seconds=0,
                saved_answers=[],
                can_resume=False,
                message="Quiz time has expired. Please submit your quiz."
            )

        # Get all questions (same logic as start_quiz)
        q_result = await db.execute(
            select(CampusDriveQuestion).where(
                (CampusDriveQuestion.campus_drive_id == drive_id) |
                (CampusDriveQuestion.is_global == True)
            )
        )
        all_questions = list(q_result.scalars().all())

        # Group by category
        questions_by_category = {
            QuestionCategory.LOGICAL: [],
            QuestionCategory.TECHNICAL: [],
            QuestionCategory.AI_ML: [],
            QuestionCategory.ENGLISH: [],
            QuestionCategory.CODING: [],
        }
        for q in all_questions:
            if q.category in questions_by_category:
                questions_by_category[q.category].append(q)

        # Select required number from each category using same seed
        questions = []
        category_counts = [
            (QuestionCategory.LOGICAL, drive.logical_questions),
            (QuestionCategory.TECHNICAL, drive.technical_questions),
            (QuestionCategory.AI_ML, drive.ai_ml_questions),
            (QuestionCategory.ENGLISH, drive.english_questions),
            (QuestionCategory.CODING, getattr(drive, 'coding_questions', 0) or 0),
        ]

        # Use same seed as original quiz start for consistent question selection
        user_seed = hash(str(registration.id) + str(drive_id))
        rng = random.Random(user_seed)

        for category, count in category_counts:
            category_questions = questions_by_category[category]
            if len(category_questions) >= count:
                # Use deterministic selection
                rng_cat = random.Random(user_seed + hash(category.value))
                indices = list(range(len(category_questions)))
                rng_cat.shuffle(indices)
                selected = [category_questions[i] for i in indices[:count]]
            else:
                selected = category_questions
            questions.extend(selected)

        # Shuffle questions with same seed
        rng.shuffle(questions)

        # Convert to response format with shuffled options
        quiz_questions = []
        for q in questions:
            option_seed = hash(str(registration.id) + str(q.id))
            option_rng = random.Random(option_seed)

            original_options = list(q.options)
            indices = list(range(len(original_options)))
            option_rng.shuffle(indices)

            shuffled_options = [original_options[i] for i in indices]

            quiz_questions.append(
                QuestionForQuiz(
                    id=q.id,
                    question_text=q.question_text,
                    category=q.category,
                    options=shuffled_options,
                    marks=q.marks
                )
            )

        # Get saved answers
        saved_result = await db.execute(
            select(CampusDriveResponse).where(
                CampusDriveResponse.registration_id == registration.id
            )
        )
        saved_responses = saved_result.scalars().all()

        saved_answers = [
            SavedAnswer(
                question_id=str(r.question_id),
                selected_option=r.selected_option
            )
            for r in saved_responses
        ]

        logger.info(f"Quiz resume: {email} - {len(saved_answers)} saved answers, {remaining_seconds}s remaining")

        return QuizResumeResponse(
            registration_id=registration.id,
            drive_name=drive.name,
            duration_minutes=drive.quiz_duration_minutes,
            total_questions=len(quiz_questions),
            questions=quiz_questions,
            start_time=registration.quiz_start_time,
            time_remaining_seconds=remaining_seconds,
            saved_answers=saved_answers,
            can_resume=True,
            message=f"Quiz resumed with {len(saved_answers)} saved answers"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming quiz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume quiz"
        )


# ============================================
# Seed Endpoint (One-time initialization)
# ============================================

@router.post("/seed")
async def seed_campus_drive_data(
    secret: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Seed campus drive and questions data.
    Requires secret key: 'bharatbuild2026'
    """
    if secret != "bharatbuild2026":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret key"
        )

    try:
        # Check if drive already exists
        existing = await db.execute(
            select(CampusDrive).where(CampusDrive.name == "Campus Placement Drive 2026")
        )
        existing_drive = existing.scalar_one_or_none()

        if existing_drive:
            # Check if coding questions already exist
            coding_q = await db.execute(
                select(CampusDriveQuestion).where(CampusDriveQuestion.category == QuestionCategory.CODING)
            )
            if coding_q.scalars().first():
                return {"message": "Data already seeded", "status": "exists"}

            # Add coding questions to existing drive
            existing_drive.coding_questions = 5
            existing_drive.total_questions = 35

            coding_questions_data = [
                ("What is the output of this Python code?\n\nx = [1, 2, 3]\ny = x\ny.append(4)\nprint(len(x))", QuestionCategory.CODING, ["3", "4", "Error", "None"], 1),
                ("What is the output of this code?\n\nfor i in range(3):\n    print(i, end=' ')", QuestionCategory.CODING, ["1 2 3", "0 1 2", "0 1 2 3", "1 2 3 4"], 1),
                ("Find the bug in this factorial function:\n\ndef factorial(n):\n    if n == 0:\n        return 0\n    return n * factorial(n-1)", QuestionCategory.CODING, ["Line 2: wrong condition", "Line 3: should return 1", "Line 4: wrong formula", "No bug"], 1),
                ("What is the output?\n\nprint(type([]) == type({}))", QuestionCategory.CODING, ["True", "False", "Error", "None"], 1),
                ("What will this print?\n\nx = 'hello'\nprint(x[1:4])", QuestionCategory.CODING, ["hel", "ell", "ello", "hell"], 1),
                ("What is the output?\n\na = [1, 2, 3]\nb = a.copy()\nb.append(4)\nprint(len(a))", QuestionCategory.CODING, ["3", "4", "Error", "None"], 0),
                ("Fill in the blank to reverse a string:\n\ns = 'hello'\nreversed_s = s[___]", QuestionCategory.CODING, ["::-1", "-1::", "::1", "1::"], 0),
                ("What is the output?\n\nprint(2 ** 3 ** 2)", QuestionCategory.CODING, ["64", "512", "8", "Error"], 1),
                ("What does this list comprehension return?\n\n[x*2 for x in range(4)]", QuestionCategory.CODING, ["[0, 2, 4, 6]", "[2, 4, 6, 8]", "[1, 2, 3, 4]", "[0, 1, 2, 3]"], 0),
                ("What is the output?\n\ndef foo(a, b=[]):\n    b.append(a)\n    return b\n\nprint(foo(1))\nprint(foo(2))", QuestionCategory.CODING, ["[1] and [2]", "[1] and [1, 2]", "[1, 2] and [1, 2]", "Error"], 1),
            ]

            for text, category, options, correct in coding_questions_data:
                question = CampusDriveQuestion(
                    question_text=text,
                    category=category,
                    options=options,
                    correct_option=correct,
                    marks=1.0,
                    is_global=True
                )
                db.add(question)

            await db.commit()
            return {"message": "Coding questions added to existing drive", "status": "updated", "questions_added": 10}

        # Create campus drive
        drive = CampusDrive(
            name="Campus Placement Drive 2026",
            company_name="BharatBuild",
            description="Annual campus placement drive for engineering students. Test your skills in logical reasoning, technical knowledge, AI/ML concepts, and English proficiency.",
            quiz_duration_minutes=60,
            passing_percentage=60.0,
            total_questions=35,
            logical_questions=5,
            technical_questions=10,
            ai_ml_questions=10,
            english_questions=5,
            coding_questions=5,
            is_active=True
        )
        db.add(drive)
        await db.flush()

        # Seed questions
        questions_data = [
            # Logical Questions
            ("If all Bloops are Razzies and all Razzies are Lazzies, then all Bloops are definitely Lazzies. Is this statement true?", QuestionCategory.LOGICAL, ["True", "False", "Cannot be determined", "Partially true"], 0),
            ("A is the brother of B. B is the sister of C. D is the father of A. How is C related to D?", QuestionCategory.LOGICAL, ["Daughter", "Son", "Granddaughter", "Cannot be determined"], 0),
            ("Complete the series: 2, 6, 12, 20, 30, ?", QuestionCategory.LOGICAL, ["40", "42", "44", "46"], 1),
            ("Find the odd one out: 8, 27, 64, 100, 125, 216", QuestionCategory.LOGICAL, ["27", "64", "100", "125"], 2),
            ("A clock shows 3:15. What is the angle between the hour and minute hands?", QuestionCategory.LOGICAL, ["0 degrees", "7.5 degrees", "15 degrees", "22.5 degrees"], 1),
            ("In a row of students, Ram is 7th from left and Shyam is 9th from right. If they interchange, Ram becomes 11th from left. How many students?", QuestionCategory.LOGICAL, ["17", "18", "19", "20"], 2),

            # Technical Questions
            ("What is the time complexity of binary search?", QuestionCategory.TECHNICAL, ["O(n)", "O(log n)", "O(n log n)", "O(1)"], 1),
            ("Which data structure uses LIFO (Last In First Out)?", QuestionCategory.TECHNICAL, ["Queue", "Stack", "Array", "Linked List"], 1),
            ("What is the output of: print(type([]) == type({}))?", QuestionCategory.TECHNICAL, ["True", "False", "Error", "None"], 1),
            ("Which HTTP method is idempotent?", QuestionCategory.TECHNICAL, ["POST", "GET", "PATCH", "None of the above"], 1),
            ("What does SQL stand for?", QuestionCategory.TECHNICAL, ["Structured Query Language", "Simple Query Language", "Standard Query Language", "Sequential Query Language"], 0),
            ("Which sorting algorithm has the best average case time complexity?", QuestionCategory.TECHNICAL, ["Bubble Sort", "Insertion Sort", "Quick Sort", "Selection Sort"], 2),
            ("What is the purpose of the finally block in exception handling?", QuestionCategory.TECHNICAL, ["Execute only if exception occurs", "Execute only if no exception", "Always execute regardless of exception", "Skip exception handling"], 2),
            ("Which of the following is NOT a valid JavaScript data type?", QuestionCategory.TECHNICAL, ["Boolean", "Undefined", "Integer", "Symbol"], 2),
            ("What is the difference between == and === in JavaScript?", QuestionCategory.TECHNICAL, ["No difference", "=== checks type also", "== checks type also", "=== is faster"], 1),
            ("Which CSS property is used to change the background color?", QuestionCategory.TECHNICAL, ["color", "bgcolor", "background-color", "background"], 2),
            ("What is Git primarily used for?", QuestionCategory.TECHNICAL, ["Database management", "Version control", "Web hosting", "Compilation"], 1),
            ("Which of the following is a NoSQL database?", QuestionCategory.TECHNICAL, ["MySQL", "PostgreSQL", "MongoDB", "Oracle"], 2),

            # AI/ML Questions
            ("What does CNN stand for in deep learning?", QuestionCategory.AI_ML, ["Central Neural Network", "Convolutional Neural Network", "Connected Neural Network", "Computed Neural Network"], 1),
            ("Which algorithm is commonly used for classification problems?", QuestionCategory.AI_ML, ["Linear Regression", "K-Means Clustering", "Random Forest", "PCA"], 2),
            ("What is overfitting in machine learning?", QuestionCategory.AI_ML, ["Model performs well on training data but poorly on test data", "Model performs poorly on training data", "Model takes too long to train", "Model uses too much memory"], 0),
            ("Which activation function is most commonly used in hidden layers of neural networks?", QuestionCategory.AI_ML, ["Sigmoid", "Tanh", "ReLU", "Softmax"], 2),
            ("What is the purpose of the learning rate in gradient descent?", QuestionCategory.AI_ML, ["Controls model complexity", "Controls step size in optimization", "Controls regularization", "Controls batch size"], 1),
            ("Which metric is used to evaluate classification models?", QuestionCategory.AI_ML, ["RMSE", "MAE", "Accuracy", "R-squared"], 2),
            ("What type of machine learning is used when we have labeled data?", QuestionCategory.AI_ML, ["Unsupervised Learning", "Supervised Learning", "Reinforcement Learning", "Semi-supervised Learning"], 1),
            ("Which library is commonly used for deep learning in Python?", QuestionCategory.AI_ML, ["NumPy", "Pandas", "TensorFlow", "Matplotlib"], 2),
            ("What is the purpose of dropout in neural networks?", QuestionCategory.AI_ML, ["Speed up training", "Prevent overfitting", "Increase accuracy", "Reduce memory usage"], 1),
            ("Which of the following is a clustering algorithm?", QuestionCategory.AI_ML, ["Linear Regression", "Decision Tree", "K-Means", "Naive Bayes"], 2),
            ("What does NLP stand for?", QuestionCategory.AI_ML, ["Neural Learning Process", "Natural Language Processing", "Network Layer Protocol", "Non-Linear Programming"], 1),
            ("Which optimizer is an improvement over standard gradient descent?", QuestionCategory.AI_ML, ["SGD", "Adam", "RMSprop", "All of the above"], 3),

            # English Questions
            ("Choose the correct sentence:", QuestionCategory.ENGLISH, ["He don't know nothing", "He doesn't know anything", "He don't know anything", "He doesn't know nothing"], 1),
            ("What is the synonym of Eloquent?", QuestionCategory.ENGLISH, ["Silent", "Articulate", "Humble", "Arrogant"], 1),
            ("Choose the antonym of Benevolent:", QuestionCategory.ENGLISH, ["Kind", "Generous", "Malevolent", "Caring"], 2),
            ("Fill in the blank: She ___ to the store yesterday.", QuestionCategory.ENGLISH, ["go", "goes", "went", "going"], 2),
            ("Which sentence is grammatically correct?", QuestionCategory.ENGLISH, ["Me and him went to the park", "Him and me went to the park", "He and I went to the park", "I and he went to the park"], 2),
            ("What does 'ubiquitous' mean?", QuestionCategory.ENGLISH, ["Rare", "Present everywhere", "Unique", "Unknown"], 1),

            # Coding Questions (Code Output, Debugging, Code Completion)
            ("What is the output of this Python code?\n\nx = [1, 2, 3]\ny = x\ny.append(4)\nprint(len(x))", QuestionCategory.CODING, ["3", "4", "Error", "None"], 1),
            ("What is the output of this code?\n\nfor i in range(3):\n    print(i, end=' ')", QuestionCategory.CODING, ["1 2 3", "0 1 2", "0 1 2 3", "1 2 3 4"], 1),
            ("Find the bug in this factorial function:\n\ndef factorial(n):\n    if n == 0:\n        return 0\n    return n * factorial(n-1)", QuestionCategory.CODING, ["Line 2: wrong condition", "Line 3: should return 1", "Line 4: wrong formula", "No bug"], 1),
            ("What is the output?\n\nprint(type([]) == type({}))", QuestionCategory.CODING, ["True", "False", "Error", "None"], 1),
            ("What will this print?\n\nx = 'hello'\nprint(x[1:4])", QuestionCategory.CODING, ["hel", "ell", "ello", "hell"], 1),
            ("What is the output?\n\na = [1, 2, 3]\nb = a.copy()\nb.append(4)\nprint(len(a))", QuestionCategory.CODING, ["3", "4", "Error", "None"], 0),
            ("Fill in the blank to reverse a string:\n\ns = 'hello'\nreversed_s = s[___]", QuestionCategory.CODING, ["::-1", "-1::", "::1", "1::"], 0),
            ("What is the output?\n\nprint(2 ** 3 ** 2)", QuestionCategory.CODING, ["64", "512", "8", "Error"], 1),
            ("What does this list comprehension return?\n\n[x*2 for x in range(4)]", QuestionCategory.CODING, ["[0, 2, 4, 6]", "[2, 4, 6, 8]", "[1, 2, 3, 4]", "[0, 1, 2, 3]"], 0),
            ("What is the output?\n\ndef foo(a, b=[]):\n    b.append(a)\n    return b\n\nprint(foo(1))\nprint(foo(2))", QuestionCategory.CODING, ["[1] and [2]", "[1] and [1, 2]", "[1, 2] and [1, 2]", "Error"], 1),
        ]

        for text, category, options, correct in questions_data:
            question = CampusDriveQuestion(
                question_text=text,
                category=category,
                options=options,
                correct_option=correct,
                marks=1.0,
                is_global=True
            )
            db.add(question)

        await db.commit()

        logger.info("Campus drive data seeded successfully")
        return {
            "message": "Campus drive data seeded successfully",
            "drive_name": drive.name,
            "questions_count": len(questions_data)
        }

    except Exception as e:
        logger.error(f"Error seeding campus drive data: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed data: {str(e)}"
        )
