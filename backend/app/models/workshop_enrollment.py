"""
Workshop Enrollment Model - Stores student registrations for workshops
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from datetime import datetime

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class WorkshopEnrollment(Base):
    """Workshop enrollment model for student registrations"""
    __tablename__ = "workshop_enrollments"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Personal Information
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False)

    # Academic Information
    college_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    year_of_study = Column(String(50), nullable=False)  # e.g., "1st Year", "2nd Year"
    roll_number = Column(String(50), nullable=True)

    # Workshop Details
    workshop_name = Column(String(255), nullable=False, default="AI Workshop")
    workshop_date = Column(String(100), nullable=True)

    # Additional Info
    previous_experience = Column(Text, nullable=True)
    expectations = Column(Text, nullable=True)
    how_did_you_hear = Column(String(255), nullable=True)

    # Status
    is_confirmed = Column(Boolean, default=False)
    payment_status = Column(String(50), default="pending")  # pending, completed, waived

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<WorkshopEnrollment {self.full_name} - {self.email}>"
