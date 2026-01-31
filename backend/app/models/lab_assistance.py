"""
Lab Assistance Models - Complete lab practice system for B.Tech students
Includes: Labs, Topics, Concepts, MCQs, Coding Problems, Submissions, Progress Tracking
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey, Enum, JSON, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ============================================================================
# ENUMS
# ============================================================================

class Branch(str, enum.Enum):
    """B.Tech Branches"""
    CSE = "cse"
    IT = "it"
    ECE = "ece"
    EEE = "eee"
    ME = "me"
    CE = "ce"
    AI_ML = "ai_ml"
    DATA_SCIENCE = "data_science"


class Semester(str, enum.Enum):
    """Semesters"""
    SEM_1 = "sem_1"
    SEM_2 = "sem_2"
    SEM_3 = "sem_3"
    SEM_4 = "sem_4"
    SEM_5 = "sem_5"
    SEM_6 = "sem_6"
    SEM_7 = "sem_7"
    SEM_8 = "sem_8"


class DifficultyLevel(str, enum.Enum):
    """Difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(str, enum.Enum):
    """Types of questions"""
    MCQ = "mcq"
    CODING = "coding"
    SHORT_ANSWER = "short_answer"


class ProgrammingLanguage(str, enum.Enum):
    """Supported programming languages"""
    C = "c"
    CPP = "cpp"
    JAVA = "java"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    SQL = "sql"
    SHELL = "shell"
    ASSEMBLY = "assembly"
    VERILOG = "verilog"
    MATLAB = "matlab"
    R = "r"
    GO = "go"
    RUST = "rust"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    DART = "dart"
    PHP = "php"
    RUBY = "ruby"
    TYPESCRIPT = "typescript"
    HTML_CSS = "html_css"


class SubmissionStatus(str, enum.Enum):
    """Submission status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class TopicStatus(str, enum.Enum):
    """Topic completion status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class LabReportStatus(str, enum.Enum):
    """Lab report submission status"""
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESUBMIT_REQUIRED = "resubmit_required"


# ============================================================================
# LAB MODEL
# ============================================================================

class Lab(Base):
    """Lab - Main entity for a laboratory course"""
    __tablename__ = "labs"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Lab Details
    name = Column(String(255), nullable=False)  # e.g., "Computer Networks Lab"
    code = Column(String(50), nullable=False, unique=True)  # e.g., "CN-LAB"
    description = Column(Text, nullable=True)

    # Academic Info
    branch = Column(Enum(Branch), nullable=False, index=True)
    semester = Column(Enum(Semester), nullable=False, index=True)

    # Technologies covered
    technologies = Column(JSON, nullable=True)  # ["Python", "Socket", "Wireshark"]

    # Lab Configuration
    total_topics = Column(Integer, default=0)
    total_mcqs = Column(Integer, default=0)
    total_coding_problems = Column(Integer, default=0)

    # Faculty Assignment
    faculty_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    topics = relationship("LabTopic", back_populates="lab", cascade="all, delete-orphan")
    enrollments = relationship("LabEnrollment", back_populates="lab", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lab {self.name} ({self.code})>"


# ============================================================================
# TOPIC MODEL
# ============================================================================

class LabTopic(Base):
    """Topic within a Lab"""
    __tablename__ = "lab_topics"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    lab_id = Column(GUID, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Topic Details
    title = Column(String(255), nullable=False)  # e.g., "Socket Programming Basics"
    description = Column(Text, nullable=True)
    week_number = Column(Integer, default=1)  # Which week this topic belongs to
    order_index = Column(Integer, default=0)  # Order within the week

    # Difficulty level for the topic
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM)

    # Assignment status: draft, assigned, locked
    status = Column(String(20), default="draft")  # draft, assigned, locked

    # Content
    concept_content = Column(Text, nullable=True)  # Markdown content for concepts
    video_url = Column(String(500), nullable=True)  # Optional video tutorial link

    # Statistics
    mcq_count = Column(Integer, default=0)
    coding_count = Column(Integer, default=0)

    # AI usage limit percentage (0-100)
    ai_limit = Column(Integer, default=20)

    # Deadline for the topic (if assigned)
    deadline = Column(DateTime, nullable=True)

    # Prerequisites (topic IDs that must be completed first)
    prerequisites = Column(JSON, nullable=True)  # [topic_id1, topic_id2]

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lab = relationship("Lab", back_populates="topics")
    mcq_questions = relationship("LabMCQ", back_populates="topic", cascade="all, delete-orphan")
    coding_problems = relationship("LabCodingProblem", back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LabTopic {self.title}>"


# ============================================================================
# MCQ MODEL
# ============================================================================

class LabMCQ(Base):
    """Multiple Choice Questions for Lab Topics"""
    __tablename__ = "lab_mcqs"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    topic_id = Column(GUID, ForeignKey("lab_topics.id", ondelete="CASCADE"), nullable=False, index=True)

    # Question Details
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # ["Option A", "Option B", "Option C", "Option D"]
    correct_option = Column(Integer, nullable=False)  # Index 0-3
    explanation = Column(Text, nullable=True)  # Explanation for correct answer

    # Metadata
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    marks = Column(Float, default=1.0)
    time_limit_seconds = Column(Integer, default=60)  # Time limit per question

    # Tags for categorization
    tags = Column(JSON, nullable=True)  # ["socket", "tcp", "server"]

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic = relationship("LabTopic", back_populates="mcq_questions")

    def __repr__(self):
        return f"<LabMCQ {self.question_text[:50]}>"


# ============================================================================
# CODING PROBLEM MODEL
# ============================================================================

class LabCodingProblem(Base):
    """Coding Problems for Lab Topics"""
    __tablename__ = "lab_coding_problems"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    topic_id = Column(GUID, ForeignKey("lab_topics.id", ondelete="CASCADE"), nullable=False, index=True)

    # Problem Details
    title = Column(String(255), nullable=False)  # e.g., "TCP Echo Server"
    description = Column(Text, nullable=False)  # Full problem statement (Markdown)

    # Difficulty and Scoring
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.MEDIUM)
    max_score = Column(Integer, default=100)

    # Supported Languages
    supported_languages = Column(JSON, nullable=False)  # ["python", "c", "java"]

    # Starter Code (per language)
    starter_code = Column(JSON, nullable=True)  # {"python": "def solve():", "c": "int main()"}

    # Solution (hidden from students)
    solution_code = Column(JSON, nullable=True)  # {"python": "...", "c": "..."}

    # Test Cases
    test_cases = Column(JSON, nullable=False)  # [{"input": "...", "expected": "...", "is_sample": true}]

    # Constraints
    time_limit_ms = Column(Integer, default=2000)  # 2 seconds
    memory_limit_mb = Column(Integer, default=256)  # 256 MB

    # Hints
    hints = Column(JSON, nullable=True)  # ["Use bind()", "Use accept()"]

    # Tags
    tags = Column(JSON, nullable=True)  # ["socket", "tcp", "server"]

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    topic = relationship("LabTopic", back_populates="coding_problems")
    submissions = relationship("LabCodingSubmission", back_populates="problem", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LabCodingProblem {self.title}>"


# ============================================================================
# ENROLLMENT MODEL
# ============================================================================

class LabEnrollment(Base):
    """Student enrollment in a Lab"""
    __tablename__ = "lab_enrollments"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    lab_id = Column(GUID, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Section (for class division)
    section = Column(String(10), nullable=True)  # e.g., "A", "B", "C"

    # Overall Progress
    overall_progress = Column(Float, default=0.0)  # 0-100 percentage

    # Scores
    mcq_score = Column(Float, default=0.0)  # Average MCQ score
    coding_score = Column(Float, default=0.0)  # Average coding score
    total_score = Column(Float, default=0.0)  # Combined score

    # Counts
    topics_completed = Column(Integer, default=0)
    mcqs_attempted = Column(Integer, default=0)
    mcqs_correct = Column(Integer, default=0)
    problems_solved = Column(Integer, default=0)

    # Rank in class
    class_rank = Column(Integer, nullable=True)

    # Timestamps
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lab = relationship("Lab", back_populates="enrollments")
    topic_progress = relationship("LabTopicProgress", back_populates="enrollment", cascade="all, delete-orphan")
    mcq_responses = relationship("LabMCQResponse", back_populates="enrollment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LabEnrollment lab={self.lab_id} user={self.user_id}>"


# ============================================================================
# TOPIC PROGRESS MODEL
# ============================================================================

class LabTopicProgress(Base):
    """Student's progress on a specific topic"""
    __tablename__ = "lab_topic_progress"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    enrollment_id = Column(GUID, ForeignKey("lab_enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(GUID, ForeignKey("lab_topics.id", ondelete="CASCADE"), nullable=False, index=True)

    # Progress Status
    status = Column(Enum(TopicStatus), default=TopicStatus.NOT_STARTED)

    # Concept Reading
    concept_read = Column(Boolean, default=False)
    concept_read_at = Column(DateTime, nullable=True)

    # MCQ Progress
    mcq_attempted = Column(Integer, default=0)
    mcq_correct = Column(Integer, default=0)
    mcq_score = Column(Float, default=0.0)  # Percentage

    # Coding Progress
    coding_attempted = Column(Integer, default=0)
    coding_solved = Column(Integer, default=0)
    coding_score = Column(Float, default=0.0)  # Percentage

    # Overall Progress
    progress_percentage = Column(Float, default=0.0)  # 0-100

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    enrollment = relationship("LabEnrollment", back_populates="topic_progress")

    def __repr__(self):
        return f"<LabTopicProgress enrollment={self.enrollment_id} topic={self.topic_id}>"


# ============================================================================
# MCQ RESPONSE MODEL
# ============================================================================

class LabMCQResponse(Base):
    """Student's response to an MCQ"""
    __tablename__ = "lab_mcq_responses"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    enrollment_id = Column(GUID, ForeignKey("lab_enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    mcq_id = Column(GUID, ForeignKey("lab_mcqs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Response
    selected_option = Column(Integer, nullable=True)  # 0-3, null if skipped
    is_correct = Column(Boolean, default=False)
    marks_obtained = Column(Float, default=0.0)
    time_taken_seconds = Column(Integer, nullable=True)  # How long to answer

    # Timestamp
    answered_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    enrollment = relationship("LabEnrollment", back_populates="mcq_responses")

    def __repr__(self):
        return f"<LabMCQResponse enrollment={self.enrollment_id} mcq={self.mcq_id}>"


# ============================================================================
# CODING SUBMISSION MODEL
# ============================================================================

class LabCodingSubmission(Base):
    """Student's code submission for a coding problem"""
    __tablename__ = "lab_coding_submissions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id = Column(GUID, ForeignKey("lab_coding_problems.id", ondelete="CASCADE"), nullable=False, index=True)

    # Submission Details
    language = Column(Enum(ProgrammingLanguage), nullable=False)
    code = Column(Text, nullable=False)  # Submitted code

    # Execution Results
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.PENDING)

    # Test Results
    test_results = Column(JSON, nullable=True)  # [{"test": 1, "passed": true, "time": 0.02}]
    tests_passed = Column(Integer, default=0)
    tests_total = Column(Integer, default=0)

    # Scoring
    score = Column(Float, default=0.0)  # 0-100

    # Execution Metrics
    execution_time_ms = Column(Integer, nullable=True)
    memory_used_mb = Column(Float, nullable=True)

    # Error Info (if failed)
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)  # "compile_error", "runtime_error", etc.

    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)

    # Relationships
    problem = relationship("LabCodingProblem", back_populates="submissions")

    def __repr__(self):
        return f"<LabCodingSubmission user={self.user_id} problem={self.problem_id}>"


# ============================================================================
# QUIZ SESSION MODEL (for timed quizzes)
# ============================================================================

class LabQuizSession(Base):
    """A timed quiz session for a topic"""
    __tablename__ = "lab_quiz_sessions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    enrollment_id = Column(GUID, ForeignKey("lab_enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(GUID, ForeignKey("lab_topics.id", ondelete="CASCADE"), nullable=False, index=True)

    # Quiz Configuration
    total_questions = Column(Integer, nullable=False)
    time_limit_minutes = Column(Integer, default=15)

    # Question Order (randomized)
    question_ids = Column(JSON, nullable=False)  # [mcq_id1, mcq_id2, ...]

    # Progress
    current_question_index = Column(Integer, default=0)
    answers = Column(JSON, nullable=True)  # {mcq_id: selected_option}

    # Results
    score = Column(Float, nullable=True)
    correct_count = Column(Integer, nullable=True)

    # Status
    is_completed = Column(Boolean, default=False)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)  # When the quiz auto-submits

    def __repr__(self):
        return f"<LabQuizSession enrollment={self.enrollment_id} topic={self.topic_id}>"


# ============================================================================
# LAB REPORT MODEL - For semester-end lab report submissions
# ============================================================================

class LabReport(Base):
    """Lab Report submission for a lab in a semester"""
    __tablename__ = "lab_reports"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    enrollment_id = Column(GUID, ForeignKey("lab_enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    lab_id = Column(GUID, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Report Details
    title = Column(String(255), nullable=False)  # e.g., "C Programming Lab Report - Semester 3"
    description = Column(Text, nullable=True)  # Student's summary of lab work

    # File Upload
    file_url = Column(String(500), nullable=True)  # URL to uploaded PDF/document
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # in bytes

    # Status
    status = Column(Enum(LabReportStatus), default=LabReportStatus.NOT_SUBMITTED)

    # Faculty Review
    reviewed_by = Column(GUID, ForeignKey("users.id"), nullable=True)
    review_comments = Column(Text, nullable=True)
    grade = Column(String(10), nullable=True)  # A+, A, B+, B, C, etc.
    marks = Column(Float, nullable=True)  # Numeric marks out of 100

    # Submission tracking
    submission_count = Column(Integer, default=0)  # Number of times submitted
    max_submissions = Column(Integer, default=3)  # Maximum allowed submissions

    # Timestamps
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Deadline
    deadline = Column(DateTime, nullable=True)  # Report submission deadline

    # Relationships
    enrollment = relationship("LabEnrollment", backref="lab_reports")
    lab = relationship("Lab", backref="lab_reports")

    def __repr__(self):
        return f"<LabReport lab={self.lab_id} user={self.user_id} status={self.status}>"


# ============================================================================
# SEMESTER PROGRESS MODEL - Track overall semester completion
# ============================================================================

class SemesterProgress(Base):
    """Track student's overall progress in a semester"""
    __tablename__ = "semester_progress"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    semester = Column(Enum(Semester), nullable=False)
    branch = Column(Enum(Branch), nullable=False)

    # Progress metrics
    total_labs = Column(Integer, default=0)
    labs_completed = Column(Integer, default=0)
    labs_in_progress = Column(Integer, default=0)

    # Reports
    reports_submitted = Column(Integer, default=0)
    reports_approved = Column(Integer, default=0)

    # Overall scores
    average_mcq_score = Column(Float, default=0.0)
    average_coding_score = Column(Float, default=0.0)
    overall_grade = Column(String(10), nullable=True)

    # Status
    is_completed = Column(Boolean, default=False)  # All labs done + all reports approved
    completed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SemesterProgress user={self.user_id} semester={self.semester}>"
