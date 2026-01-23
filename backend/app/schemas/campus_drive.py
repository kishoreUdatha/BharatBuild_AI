"""
Campus Drive Schemas - Pydantic models for API validation
"""

from pydantic import BaseModel, EmailStr, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.campus_drive import QuestionCategory, QuestionDifficulty, RegistrationStatus


# ============================================
# Campus Drive Schemas
# ============================================

class CampusDriveCreate(BaseModel):
    """Create a new campus drive"""
    name: str = Field(..., min_length=3, max_length=255)
    company_name: Optional[str] = None
    description: Optional[str] = None
    registration_end: Optional[datetime] = None
    quiz_date: Optional[datetime] = None
    quiz_duration_minutes: int = Field(default=60, ge=10, le=180)
    passing_percentage: float = Field(default=60.0, ge=0, le=100)
    total_questions: int = Field(default=30, ge=10, le=100)
    logical_questions: int = Field(default=5, ge=0)
    technical_questions: int = Field(default=10, ge=0)
    ai_ml_questions: int = Field(default=10, ge=0)
    english_questions: int = Field(default=5, ge=0)
    coding_questions: int = Field(default=5, ge=0)


class CampusDriveUpdate(BaseModel):
    """Update campus drive"""
    name: Optional[str] = None
    company_name: Optional[str] = None
    description: Optional[str] = None
    registration_end: Optional[datetime] = None
    quiz_date: Optional[datetime] = None
    quiz_duration_minutes: Optional[int] = None
    passing_percentage: Optional[float] = None
    is_active: Optional[bool] = None


class CampusDriveResponse(BaseModel):
    """Campus drive response"""
    id: UUID
    name: str
    company_name: Optional[str] = None
    description: Optional[str] = None
    registration_start: datetime
    registration_end: Optional[datetime] = None
    quiz_date: Optional[datetime] = None
    quiz_duration_minutes: int
    passing_percentage: float
    total_questions: int
    logical_questions: int
    technical_questions: int
    ai_ml_questions: int
    english_questions: int
    coding_questions: int = 0
    is_active: bool
    created_at: datetime

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    class Config:
        from_attributes = True


# ============================================
# Registration Schemas
# ============================================

class StudentRegistrationCreate(BaseModel):
    """Student registration for campus drive"""
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., pattern=r'^[6-9]\d{9}$', description="10-digit Indian mobile number")
    college_name: str = Field(..., min_length=2, max_length=255)
    department: str = Field(..., min_length=2, max_length=255)
    year_of_study: str = Field(..., min_length=1, max_length=50)
    roll_number: Optional[str] = None
    cgpa: Optional[float] = Field(None, ge=0, le=10)


class RegistrationResponse(BaseModel):
    """Registration response"""
    id: UUID
    campus_drive_id: UUID
    full_name: str
    email: str
    phone: str
    college_name: str
    department: str
    year_of_study: str
    roll_number: Optional[str] = None
    cgpa: Optional[float] = None
    status: RegistrationStatus
    quiz_score: Optional[float] = None
    percentage: Optional[float] = None
    is_qualified: bool
    logical_score: float
    technical_score: float
    ai_ml_score: float
    english_score: float
    coding_score: float = 0
    created_at: datetime

    @field_serializer('id', 'campus_drive_id')
    def serialize_uuid(self, value: UUID) -> str:
        return str(value)

    class Config:
        from_attributes = True


class RegistrationWithDrive(RegistrationResponse):
    """Registration response with drive details"""
    drive_name: str
    drive_company: Optional[str] = None
    quiz_duration_minutes: int
    passing_percentage: float


# ============================================
# Question Schemas
# ============================================

class QuestionCreate(BaseModel):
    """Create a quiz question"""
    question_text: str = Field(..., min_length=10)
    category: QuestionCategory
    difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_option: int = Field(..., ge=0, le=3)
    marks: float = Field(default=1.0, ge=0.5, le=5)
    is_global: bool = True
    campus_drive_id: Optional[UUID] = None


class QuestionResponse(BaseModel):
    """Question response (for admin)"""
    id: UUID
    question_text: str
    category: QuestionCategory
    difficulty: QuestionDifficulty
    options: List[str]
    correct_option: int
    marks: float
    is_global: bool
    created_at: datetime

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    class Config:
        from_attributes = True


class QuestionForQuiz(BaseModel):
    """Question for quiz (without correct answer)"""
    id: UUID
    question_text: str
    category: QuestionCategory
    options: List[str]
    marks: float

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    class Config:
        from_attributes = True


# ============================================
# Quiz Schemas
# ============================================

class QuizStartResponse(BaseModel):
    """Response when starting quiz"""
    registration_id: UUID
    drive_name: str
    duration_minutes: int
    total_questions: int
    questions: List[QuestionForQuiz]
    start_time: datetime

    @field_serializer('registration_id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)


class QuestionAnswer(BaseModel):
    """Single question answer"""
    question_id: UUID
    selected_option: Optional[int] = Field(None, ge=0, le=3)

    @field_serializer('question_id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)


class QuizSubmission(BaseModel):
    """Quiz submission with all answers"""
    answers: List[QuestionAnswer]


class QuizResultResponse(BaseModel):
    """Quiz result after submission"""
    registration_id: UUID
    total_questions: int
    attempted: int
    correct: int
    wrong: int
    total_marks: float
    marks_obtained: float
    percentage: float
    is_qualified: bool
    passing_percentage: float

    # Section-wise results
    logical_score: float
    logical_total: float
    technical_score: float
    technical_total: float
    ai_ml_score: float
    ai_ml_total: float
    english_score: float
    english_total: float
    coding_score: float = 0
    coding_total: float = 0

    @field_serializer('registration_id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)


# ============================================
# Admin Schemas
# ============================================

class CampusDriveStats(BaseModel):
    """Statistics for a campus drive"""
    total_registrations: int
    quiz_completed: int
    qualified: int
    not_qualified: int
    average_score: float
    highest_score: float
    lowest_score: float


class AdminRegistrationResponse(RegistrationResponse):
    """Admin view of registration with more details"""
    quiz_start_time: Optional[datetime] = None
    quiz_end_time: Optional[datetime] = None


class BulkQuestionCreate(BaseModel):
    """Create multiple questions at once"""
    questions: List[QuestionCreate]


# ============================================
# Quiz Progress/Resume Schemas
# ============================================

class SavedAnswer(BaseModel):
    """Saved answer for a question"""
    question_id: str
    selected_option: Optional[int] = None

    class Config:
        from_attributes = True


class QuizProgressSave(BaseModel):
    """Save quiz progress (partial answers)"""
    answers: List[QuestionAnswer]


class QuizProgressResponse(BaseModel):
    """Response after saving progress"""
    saved_count: int
    message: str


class QuizResumeResponse(BaseModel):
    """Response for quiz resume - includes questions and saved answers"""
    registration_id: UUID
    drive_name: str
    duration_minutes: int
    total_questions: int
    questions: List[QuestionForQuiz]
    start_time: datetime
    time_remaining_seconds: int
    saved_answers: List[SavedAnswer]
    can_resume: bool
    message: str

    @field_serializer('registration_id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)
