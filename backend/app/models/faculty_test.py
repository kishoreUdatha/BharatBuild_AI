"""
Faculty Test Models for Lab Practice & Tests
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
import uuid


class TestStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    EVALUATING = "evaluating"


class AIControlLevel(str, enum.Enum):
    BLOCKED = "blocked"
    LIMITED = "limited"
    HINTS_ONLY = "hints_only"


class QuestionType(str, enum.Enum):
    CODING = "coding"
    SQL = "sql"
    ML = "ml"
    ANALYTICS = "analytics"
    MCQ = "mcq"


class QuestionDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class StudentSessionStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPICIOUS = "suspicious"
    SUBMITTED = "submitted"
    FORCE_SUBMITTED = "force_submitted"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FacultyTest(Base):
    """Test/Exam created by faculty"""
    __tablename__ = "faculty_tests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Lab/Subject association
    lab_id = Column(String(36), ForeignKey("labs.id"), nullable=True)
    lab_name = Column(String(100), nullable=True)  # Denormalized for quick access

    # Faculty who created the test
    faculty_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Test configuration
    duration_minutes = Column(Integer, default=60)
    max_marks = Column(Integer, default=100)
    passing_marks = Column(Integer, default=40)

    # AI Control
    ai_control = Column(Enum(AIControlLevel), default=AIControlLevel.BLOCKED)
    ai_usage_limit = Column(Integer, default=0)  # Percentage limit if LIMITED

    # Proctoring settings
    enable_tab_switch_detection = Column(Boolean, default=True)
    max_tab_switches = Column(Integer, default=5)
    enable_copy_paste_block = Column(Boolean, default=True)
    randomize_questions = Column(Boolean, default=False)
    randomize_options = Column(Boolean, default=True)

    # Scheduling
    status = Column(Enum(TestStatus), default=TestStatus.DRAFT)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Assignment
    assigned_sections = Column(JSON, default=list)  # List of section IDs

    # Stats (updated periodically)
    total_participants = Column(Integer, default=0)
    submitted_count = Column(Integer, default=0)
    avg_score = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    questions = relationship("TestQuestion", back_populates="test", cascade="all, delete-orphan")
    sessions = relationship("TestSession", back_populates="test", cascade="all, delete-orphan")

    @property
    def questions_count(self):
        return len(self.questions) if self.questions else 0


class TestQuestion(Base):
    """Questions in a test - can be from question bank or custom"""
    __tablename__ = "test_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_id = Column(String(36), ForeignKey("faculty_tests.id", ondelete="CASCADE"), nullable=False)

    # Question details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    question_type = Column(Enum(QuestionType), default=QuestionType.CODING)
    difficulty = Column(Enum(QuestionDifficulty), default=QuestionDifficulty.MEDIUM)

    # Scoring
    marks = Column(Integer, default=10)
    time_estimate_minutes = Column(Integer, default=15)
    partial_credit = Column(Boolean, default=True)

    # For MCQ
    options = Column(JSON, nullable=True)  # List of options
    correct_answer = Column(String(500), nullable=True)

    # For Coding/SQL
    starter_code = Column(Text, nullable=True)
    solution_code = Column(Text, nullable=True)
    test_cases = Column(JSON, nullable=True)  # List of test cases
    hidden_test_cases = Column(JSON, nullable=True)

    # Metadata
    topic = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    order_index = Column(Integer, default=0)

    # Reference to question bank (optional)
    source_question_id = Column(String(36), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    test = relationship("FacultyTest", back_populates="questions")
    responses = relationship("TestResponse", back_populates="question", cascade="all, delete-orphan")


class TestSession(Base):
    """Student's test session - tracks their attempt"""
    __tablename__ = "test_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_id = Column(String(36), ForeignKey("faculty_tests.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Student info (denormalized for quick access)
    student_name = Column(String(100), nullable=True)
    student_roll = Column(String(50), nullable=True)
    student_email = Column(String(255), nullable=True)

    # Session status
    status = Column(Enum(StudentSessionStatus), default=StudentSessionStatus.NOT_STARTED)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    time_spent_seconds = Column(Integer, default=0)

    # Progress
    current_question_index = Column(Integer, default=0)
    questions_attempted = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)

    # Proctoring metrics
    tab_switches = Column(Integer, default=0)
    copy_paste_attempts = Column(Integer, default=0)
    ai_usage_count = Column(Integer, default=0)
    ai_usage_percentage = Column(Float, default=0.0)
    suspicious_activities = Column(JSON, default=list)

    # Scoring
    auto_score = Column(Float, nullable=True)
    manual_score = Column(Float, nullable=True)
    total_score = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)

    # Evaluation
    is_evaluated = Column(Boolean, default=False)
    evaluated_by = Column(String(36), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    feedback = Column(Text, nullable=True)

    # Last activity description
    last_activity_description = Column(String(255), default="Not started")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    test = relationship("FacultyTest", back_populates="sessions")
    responses = relationship("TestResponse", back_populates="session", cascade="all, delete-orphan")
    alerts = relationship("TestAlert", back_populates="session", cascade="all, delete-orphan")


class TestResponse(Base):
    """Student's response to a question"""
    __tablename__ = "test_responses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(36), ForeignKey("test_questions.id", ondelete="CASCADE"), nullable=False)

    # Response
    answer = Column(Text, nullable=True)  # For MCQ or short answer
    code = Column(Text, nullable=True)  # For coding questions
    language = Column(String(50), nullable=True)  # Programming language

    # Execution results (for coding)
    execution_output = Column(Text, nullable=True)
    test_cases_passed = Column(Integer, default=0)
    test_cases_total = Column(Integer, default=0)
    execution_time_ms = Column(Integer, nullable=True)
    memory_used_kb = Column(Integer, nullable=True)

    # Scoring
    is_correct = Column(Boolean, nullable=True)
    auto_score = Column(Float, nullable=True)
    manual_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    # Time tracking
    time_spent_seconds = Column(Integer, default=0)
    attempts = Column(Integer, default=1)

    # AI detection
    ai_similarity_score = Column(Float, nullable=True)
    plagiarism_score = Column(Float, nullable=True)

    # Timestamps
    first_viewed_at = Column(DateTime(timezone=True), nullable=True)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("TestSession", back_populates="responses")
    question = relationship("TestQuestion", back_populates="responses")


class TestAlert(Base):
    """Proctoring alerts during test"""
    __tablename__ = "test_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False)

    # Alert details
    alert_type = Column(String(50), nullable=False)  # tab_switch, ai_usage, idle, copy_paste, etc.
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.MEDIUM)
    message = Column(String(500), nullable=False)
    details = Column(JSON, nullable=True)

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(36), nullable=True)
    resolution_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("TestSession", back_populates="alerts")


class QuestionBank(Base):
    """Reusable question bank for faculty"""
    __tablename__ = "question_bank"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Question details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    question_type = Column(Enum(QuestionType), default=QuestionType.CODING)
    difficulty = Column(Enum(QuestionDifficulty), default=QuestionDifficulty.MEDIUM)

    # Ownership
    faculty_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    lab_id = Column(String(36), nullable=True)

    # Scoring
    suggested_marks = Column(Integer, default=10)
    time_estimate_minutes = Column(Integer, default=15)

    # For MCQ
    options = Column(JSON, nullable=True)
    correct_answer = Column(String(500), nullable=True)

    # For Coding/SQL
    starter_code = Column(Text, nullable=True)
    solution_code = Column(Text, nullable=True)
    test_cases = Column(JSON, nullable=True)
    hidden_test_cases = Column(JSON, nullable=True)

    # Metadata
    topic = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)

    # Usage stats
    times_used = Column(Integer, default=0)
    avg_score = Column(Float, nullable=True)
    avg_time_taken = Column(Float, nullable=True)

    # Visibility
    is_public = Column(Boolean, default=False)  # Shared with other faculty

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
