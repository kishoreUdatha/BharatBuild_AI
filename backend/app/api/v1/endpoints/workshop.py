"""
Workshop Enrollment API - Handles student registration for workshops
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.models.workshop_enrollment import WorkshopEnrollment
from app.core.logging_config import logger

router = APIRouter(prefix="/workshop", tags=["Workshop"])


class EnrollmentCreate(BaseModel):
    """Schema for creating a workshop enrollment"""
    full_name: str
    email: EmailStr
    phone: str
    college_name: str
    department: str
    year_of_study: str
    roll_number: Optional[str] = None
    workshop_name: str = "AI Workshop"
    workshop_date: Optional[str] = None
    previous_experience: Optional[str] = None
    expectations: Optional[str] = None
    how_did_you_hear: Optional[str] = None


class EnrollmentResponse(BaseModel):
    """Schema for enrollment response"""
    id: str
    full_name: str
    email: str
    phone: str
    college_name: str
    department: str
    year_of_study: str
    roll_number: Optional[str]
    workshop_name: str
    is_confirmed: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/enroll", response_model=EnrollmentResponse)
async def enroll_student(
    enrollment: EnrollmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a student for a workshop.

    This endpoint is public and doesn't require authentication.
    """
    try:
        # Check if email already registered for this workshop
        existing = await db.execute(
            select(WorkshopEnrollment).where(
                WorkshopEnrollment.email == enrollment.email,
                WorkshopEnrollment.workshop_name == enrollment.workshop_name
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is already registered for this workshop"
            )

        # Create enrollment
        db_enrollment = WorkshopEnrollment(
            full_name=enrollment.full_name,
            email=enrollment.email,
            phone=enrollment.phone,
            college_name=enrollment.college_name,
            department=enrollment.department,
            year_of_study=enrollment.year_of_study,
            roll_number=enrollment.roll_number,
            workshop_name=enrollment.workshop_name,
            workshop_date=enrollment.workshop_date,
            previous_experience=enrollment.previous_experience,
            expectations=enrollment.expectations,
            how_did_you_hear=enrollment.how_did_you_hear
        )

        db.add(db_enrollment)
        await db.commit()
        await db.refresh(db_enrollment)

        logger.info(f"New workshop enrollment: {enrollment.email} for {enrollment.workshop_name}")

        return EnrollmentResponse(
            id=str(db_enrollment.id),
            full_name=db_enrollment.full_name,
            email=db_enrollment.email,
            phone=db_enrollment.phone,
            college_name=db_enrollment.college_name,
            department=db_enrollment.department,
            year_of_study=db_enrollment.year_of_study,
            roll_number=db_enrollment.roll_number,
            workshop_name=db_enrollment.workshop_name,
            is_confirmed=db_enrollment.is_confirmed,
            created_at=db_enrollment.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enrolling student: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register. Please try again."
        )


@router.get("/enrollments", response_model=List[EnrollmentResponse])
async def get_enrollments(
    workshop_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all workshop enrollments.

    Optional filter by workshop_name.
    """
    try:
        query = select(WorkshopEnrollment).order_by(WorkshopEnrollment.created_at.desc())

        if workshop_name:
            query = query.where(WorkshopEnrollment.workshop_name == workshop_name)

        result = await db.execute(query)
        enrollments = result.scalars().all()

        return [
            EnrollmentResponse(
                id=str(e.id),
                full_name=e.full_name,
                email=e.email,
                phone=e.phone,
                college_name=e.college_name,
                department=e.department,
                year_of_study=e.year_of_study,
                roll_number=e.roll_number,
                workshop_name=e.workshop_name,
                is_confirmed=e.is_confirmed,
                created_at=e.created_at
            )
            for e in enrollments
        ]

    except Exception as e:
        logger.error(f"Error fetching enrollments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch enrollments"
        )


@router.get("/enrollments/count")
async def get_enrollment_count(
    workshop_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get total enrollment count"""
    try:
        from sqlalchemy import func

        query = select(func.count(WorkshopEnrollment.id))

        if workshop_name:
            query = query.where(WorkshopEnrollment.workshop_name == workshop_name)

        result = await db.execute(query)
        count = result.scalar()

        return {"count": count, "workshop_name": workshop_name or "all"}

    except Exception as e:
        logger.error(f"Error counting enrollments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to count enrollments"
        )
