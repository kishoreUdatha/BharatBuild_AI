"""
Campus Drive Models - Student Registration, Quiz, and Results for Campus Placement Drives
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class QuestionCategory(str, enum.Enum):
    """Categories of quiz questions"""
    LOGICAL = "logical"
    TECHNICAL = "technical"
    AI_ML = "ai_ml"
    ENGLISH = "english"
    CODING = "coding"


class QuestionDifficulty(str, enum.Enum):
    """Difficulty levels for questions"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RegistrationStatus(str, enum.Enum):
    """Status of student registration"""
    REGISTERED = "registered"
    QUIZ_IN_PROGRESS = "quiz_in_progress"
    QUIZ_COMPLETED = "quiz_completed"
    QUALIFIED = "qualified"
    NOT_QUALIFIED = "not_qualified"


class CampusDrive(Base):
    """Campus Drive - Main event entity"""
    __tablename__ = "campus_drives"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Drive Details
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Timeline
    registration_start = Column(DateTime, default=datetime.utcnow)
    registration_end = Column(DateTime, nullable=True)
    quiz_date = Column(DateTime, nullable=True)

    # Quiz Configuration
    quiz_duration_minutes = Column(Integer, default=60)  # 1 hour
    passing_percentage = Column(Float, default=60.0)  # 60% to pass
    total_questions = Column(Integer, default=30)

    # Questions per category
    logical_questions = Column(Integer, default=5)
    technical_questions = Column(Integer, default=10)
    ai_ml_questions = Column(Integer, default=10)
    english_questions = Column(Integer, default=5)
    coding_questions = Column(Integer, default=5)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    registrations = relationship("CampusDriveRegistration", back_populates="campus_drive", cascade="all, delete-orphan")
    questions = relationship("CampusDriveQuestion", back_populates="campus_drive", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CampusDrive {self.name}>"


class CampusDriveRegistration(Base):
    """Student registration for a campus drive"""
    __tablename__ = "campus_drive_registrations"
    __table_args__ = (
        # Composite index for fast lookups by drive + email (most common query)
        {'sqlite_autoincrement': True}
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    campus_drive_id = Column(GUID, ForeignKey("campus_drives.id", ondelete="CASCADE"), nullable=False, index=True)

    # Personal Information
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False)

    # Academic Information
    college_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    year_of_study = Column(String(50), nullable=False)
    roll_number = Column(String(50), nullable=True)
    cgpa = Column(Float, nullable=True)

    # Status
    status = Column(Enum(RegistrationStatus), default=RegistrationStatus.REGISTERED)

    # Quiz Results
    quiz_start_time = Column(DateTime, nullable=True)
    quiz_end_time = Column(DateTime, nullable=True)
    quiz_score = Column(Float, nullable=True)
    total_marks = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    is_qualified = Column(Boolean, default=False)

    # Section-wise scores
    logical_score = Column(Float, default=0)
    technical_score = Column(Float, default=0)
    ai_ml_score = Column(Float, default=0)
    english_score = Column(Float, default=0)
    coding_score = Column(Float, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campus_drive = relationship("CampusDrive", back_populates="registrations")
    responses = relationship("CampusDriveResponse", back_populates="registration", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CampusDriveRegistration {self.full_name} - {self.email}>"


class CampusDriveQuestion(Base):
    """Quiz questions for campus drive"""
    __tablename__ = "campus_drive_questions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    campus_drive_id = Column(GUID, ForeignKey("campus_drives.id", ondelete="CASCADE"), nullable=True, index=True)

    # Question Details
    question_text = Column(Text, nullable=False)
    category = Column(Enum(QuestionCategory), nullable=False, index=True)
    difficulty = Column(Enum(QuestionDifficulty), default=QuestionDifficulty.MEDIUM)

    # Options (JSON array of 4 options)
    options = Column(JSON, nullable=False)  # ["Option A", "Option B", "Option C", "Option D"]
    correct_option = Column(Integer, nullable=False)  # Index 0-3

    # Marks
    marks = Column(Float, default=1.0)

    # Is this a global question (not tied to specific drive)
    is_global = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campus_drive = relationship("CampusDrive", back_populates="questions")

    def __repr__(self):
        return f"<CampusDriveQuestion {self.category.value} - {self.question_text[:50]}>"


class CampusDriveResponse(Base):
    """Student's response to a quiz question"""
    __tablename__ = "campus_drive_responses"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    registration_id = Column(GUID, ForeignKey("campus_drive_registrations.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(GUID, ForeignKey("campus_drive_questions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Response
    selected_option = Column(Integer, nullable=True)  # Index 0-3, null if not answered
    is_correct = Column(Boolean, default=False)
    marks_obtained = Column(Float, default=0)

    # Timestamps
    answered_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    registration = relationship("CampusDriveRegistration", back_populates="responses")
    question = relationship("CampusDriveQuestion")

    def __repr__(self):
        return f"<CampusDriveResponse reg={self.registration_id} q={self.question_id}>"
