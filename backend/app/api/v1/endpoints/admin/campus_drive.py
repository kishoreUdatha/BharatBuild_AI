"""
Admin Campus Drive API - Manage campus drives, view registrations, and results
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.logging_config import logger
from app.models import User
from app.models.campus_drive import (
    CampusDrive,
    CampusDriveRegistration,
    CampusDriveQuestion,
    CampusDriveResponse,
    QuestionCategory,
    QuestionDifficulty,
    RegistrationStatus,
)
from app.modules.auth.dependencies import get_current_admin
from app.schemas.campus_drive import (
    CampusDriveCreate,
    CampusDriveUpdate,
    CampusDriveResponse as CampusDriveResponseSchema,
    RegistrationResponse,
    QuestionCreate,
    QuestionResponse,
    CampusDriveStats,
    BulkQuestionCreate,
)

router = APIRouter()


# ============================================
# Campus Drive CRUD
# ============================================

@router.get("/", response_model=List[CampusDriveResponseSchema])
async def list_all_drives(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all campus drives (admin only)"""
    try:
        query = select(CampusDrive).order_by(CampusDrive.created_at.desc())

        if is_active is not None:
            query = query.where(CampusDrive.is_active == is_active)

        result = await db.execute(query)
        drives = result.scalars().all()
        return drives

    except Exception as e:
        logger.error(f"Error fetching campus drives: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch campus drives"
        )


@router.post("/", response_model=CampusDriveResponseSchema)
async def create_drive(
    drive: CampusDriveCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create a new campus drive"""
    try:
        db_drive = CampusDrive(
            name=drive.name,
            company_name=drive.company_name,
            description=drive.description,
            registration_end=drive.registration_end,
            quiz_date=drive.quiz_date,
            quiz_duration_minutes=drive.quiz_duration_minutes,
            passing_percentage=drive.passing_percentage,
            total_questions=drive.total_questions,
            logical_questions=drive.logical_questions,
            technical_questions=drive.technical_questions,
            ai_ml_questions=drive.ai_ml_questions,
            english_questions=drive.english_questions,
        )

        db.add(db_drive)
        await db.commit()
        await db.refresh(db_drive)

        logger.info(f"Admin {current_admin.email} created campus drive: {drive.name}")
        return db_drive

    except Exception as e:
        logger.error(f"Error creating campus drive: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create campus drive"
        )


@router.put("/{drive_id}", response_model=CampusDriveResponseSchema)
async def update_drive(
    drive_id: str,
    drive_update: CampusDriveUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update a campus drive"""
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

        # Update fields
        for field, value in drive_update.model_dump(exclude_unset=True).items():
            setattr(drive, field, value)

        await db.commit()
        await db.refresh(drive)

        logger.info(f"Admin {current_admin.email} updated campus drive: {drive_id}")
        return drive

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campus drive: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update campus drive"
        )


@router.delete("/{drive_id}")
async def delete_drive(
    drive_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete a campus drive"""
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

        await db.delete(drive)
        await db.commit()

        logger.info(f"Admin {current_admin.email} deleted campus drive: {drive_id}")
        return {"message": "Campus drive deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campus drive: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete campus drive"
        )


# ============================================
# Registrations Management
# ============================================

@router.get("/{drive_id}/registrations", response_model=List[RegistrationResponse])
async def get_drive_registrations(
    drive_id: str,
    status_filter: Optional[RegistrationStatus] = None,
    qualified_only: bool = False,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all registrations for a campus drive"""
    try:
        query = select(CampusDriveRegistration).where(
            CampusDriveRegistration.campus_drive_id == drive_id
        ).order_by(CampusDriveRegistration.created_at.desc())

        if status_filter:
            query = query.where(CampusDriveRegistration.status == status_filter)

        if qualified_only:
            query = query.where(CampusDriveRegistration.is_qualified == True)

        result = await db.execute(query)
        registrations = result.scalars().all()

        # Apply search filter in Python (for simplicity)
        if search:
            search_lower = search.lower()
            registrations = [
                r for r in registrations
                if search_lower in r.full_name.lower()
                or search_lower in r.email.lower()
                or search_lower in r.college_name.lower()
                or (r.roll_number and search_lower in r.roll_number.lower())
            ]

        return registrations

    except Exception as e:
        logger.error(f"Error fetching registrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch registrations"
        )


@router.get("/{drive_id}/stats", response_model=CampusDriveStats)
async def get_drive_stats(
    drive_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get statistics for a campus drive"""
    try:
        # Total registrations
        total = await db.scalar(
            select(func.count(CampusDriveRegistration.id)).where(
                CampusDriveRegistration.campus_drive_id == drive_id
            )
        )

        # Quiz completed
        completed = await db.scalar(
            select(func.count(CampusDriveRegistration.id)).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.status.in_([
                    RegistrationStatus.QUIZ_COMPLETED,
                    RegistrationStatus.QUALIFIED,
                    RegistrationStatus.NOT_QUALIFIED
                ])
            )
        )

        # Qualified
        qualified = await db.scalar(
            select(func.count(CampusDriveRegistration.id)).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.is_qualified == True
            )
        )

        # Not qualified
        not_qualified = await db.scalar(
            select(func.count(CampusDriveRegistration.id)).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.is_qualified == False,
                CampusDriveRegistration.percentage.isnot(None)
            )
        )

        # Score stats
        avg_score = await db.scalar(
            select(func.avg(CampusDriveRegistration.percentage)).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.percentage.isnot(None)
            )
        )

        max_score = await db.scalar(
            select(func.max(CampusDriveRegistration.percentage)).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.percentage.isnot(None)
            )
        )

        min_score = await db.scalar(
            select(func.min(CampusDriveRegistration.percentage)).where(
                CampusDriveRegistration.campus_drive_id == drive_id,
                CampusDriveRegistration.percentage.isnot(None)
            )
        )

        return CampusDriveStats(
            total_registrations=total or 0,
            quiz_completed=completed or 0,
            qualified=qualified or 0,
            not_qualified=not_qualified or 0,
            average_score=round(avg_score or 0, 2),
            highest_score=round(max_score or 0, 2),
            lowest_score=round(min_score or 0, 2)
        )

    except Exception as e:
        logger.error(f"Error fetching drive stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics"
        )


@router.get("/{drive_id}/export")
async def export_registrations(
    drive_id: str,
    qualified_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Export registrations as CSV data"""
    try:
        query = select(CampusDriveRegistration).where(
            CampusDriveRegistration.campus_drive_id == drive_id
        ).order_by(CampusDriveRegistration.percentage.desc())

        if qualified_only:
            query = query.where(CampusDriveRegistration.is_qualified == True)

        result = await db.execute(query)
        registrations = result.scalars().all()

        # Convert to CSV format
        rows = []
        headers = [
            "Name", "Email", "Phone", "College", "Department",
            "Year", "Roll Number", "CGPA", "Status",
            "Quiz Score", "Percentage", "Qualified",
            "Logical Score", "Technical Score", "AI/ML Score", "English Score"
        ]
        rows.append(headers)

        for r in registrations:
            rows.append([
                r.full_name,
                r.email,
                r.phone,
                r.college_name,
                r.department,
                r.year_of_study,
                r.roll_number or "",
                str(r.cgpa) if r.cgpa else "",
                r.status.value if r.status else "",
                str(r.quiz_score) if r.quiz_score else "",
                f"{r.percentage:.2f}" if r.percentage else "",
                "Yes" if r.is_qualified else "No",
                str(r.logical_score),
                str(r.technical_score),
                str(r.ai_ml_score),
                str(r.english_score)
            ])

        return {"data": rows, "filename": f"campus_drive_{drive_id}_registrations.csv"}

    except Exception as e:
        logger.error(f"Error exporting registrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export registrations"
        )


# ============================================
# Questions Management
# ============================================

@router.get("/questions", response_model=List[QuestionResponse])
async def get_all_questions(
    category: Optional[QuestionCategory] = None,
    is_global: bool = True,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all questions (optionally filtered by category)"""
    try:
        query = select(CampusDriveQuestion).order_by(CampusDriveQuestion.created_at.desc())

        if category:
            query = query.where(CampusDriveQuestion.category == category)

        if is_global:
            query = query.where(CampusDriveQuestion.is_global == True)

        result = await db.execute(query)
        questions = result.scalars().all()
        return questions

    except Exception as e:
        logger.error(f"Error fetching questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch questions"
        )


@router.post("/questions", response_model=QuestionResponse)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create a new question"""
    try:
        db_question = CampusDriveQuestion(
            question_text=question.question_text,
            category=question.category,
            difficulty=question.difficulty,
            options=question.options,
            correct_option=question.correct_option,
            marks=question.marks,
            is_global=question.is_global,
            campus_drive_id=str(question.campus_drive_id) if question.campus_drive_id else None
        )

        db.add(db_question)
        await db.commit()
        await db.refresh(db_question)

        logger.info(f"Admin {current_admin.email} created question: {question.category.value}")
        return db_question

    except Exception as e:
        logger.error(f"Error creating question: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create question"
        )


@router.post("/questions/bulk", response_model=dict)
async def create_bulk_questions(
    bulk: BulkQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create multiple questions at once"""
    try:
        created = 0
        for q in bulk.questions:
            db_question = CampusDriveQuestion(
                question_text=q.question_text,
                category=q.category,
                difficulty=q.difficulty,
                options=q.options,
                correct_option=q.correct_option,
                marks=q.marks,
                is_global=q.is_global,
                campus_drive_id=str(q.campus_drive_id) if q.campus_drive_id else None
            )
            db.add(db_question)
            created += 1

        await db.commit()

        logger.info(f"Admin {current_admin.email} created {created} questions in bulk")
        return {"message": f"Created {created} questions successfully", "count": created}

    except Exception as e:
        logger.error(f"Error creating bulk questions: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create questions"
        )


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete a question"""
    try:
        result = await db.execute(
            select(CampusDriveQuestion).where(CampusDriveQuestion.id == question_id)
        )
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )

        await db.delete(question)
        await db.commit()

        logger.info(f"Admin {current_admin.email} deleted question: {question_id}")
        return {"message": "Question deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting question: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete question"
        )


@router.get("/questions/count")
async def get_question_counts(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get question counts by category"""
    try:
        counts = {}
        for category in QuestionCategory:
            count = await db.scalar(
                select(func.count(CampusDriveQuestion.id)).where(
                    CampusDriveQuestion.category == category,
                    CampusDriveQuestion.is_global == True
                )
            )
            counts[category.value] = count or 0

        total = sum(counts.values())
        return {"categories": counts, "total": total}

    except Exception as e:
        logger.error(f"Error fetching question counts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch question counts"
        )
