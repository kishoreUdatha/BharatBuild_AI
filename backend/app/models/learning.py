"""
Learning Progress Models - Track student learning checkpoints for project understanding
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class LearningCheckpointType(str, enum.Enum):
    """Types of learning checkpoints"""
    CODE_EXPLANATION = "code_explanation"
    CONCEPT_QUIZ = "concept_quiz"
    VIVA_PREPARATION = "viva_preparation"


class ProjectLearningProgress(Base):
    """Track student's learning progress for a project"""
    __tablename__ = "project_learning_progress"
    __table_args__ = (
        Index('ix_learning_progress_project_user', 'project_id', 'user_id', unique=True),
        Index('ix_learning_progress_user_id', 'user_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Checkpoint 1: Code Understanding
    checkpoint_1_completed = Column(Boolean, default=False)
    files_reviewed = Column(JSON, default=list)  # List of file paths marked as understood
    explanations_viewed = Column(JSON, default=dict)  # {file_path: {viewed_at, understood: bool}}

    # Checkpoint 2: Concept Quiz
    checkpoint_2_score = Column(Float, nullable=True)  # Quiz score as percentage (0-100)
    checkpoint_2_passed = Column(Boolean, default=False)
    checkpoint_2_attempts = Column(Integer, default=0)  # Number of quiz attempts
    quiz_answers = Column(JSON, default=dict)  # {question_id: selected_option}
    quiz_completed_at = Column(DateTime, nullable=True)

    # Checkpoint 3: Viva Review
    checkpoint_3_completed = Column(Boolean, default=False)
    viva_questions_reviewed = Column(Integer, default=0)  # Count of Q&A pairs reviewed
    viva_total_questions = Column(Integer, default=0)  # Total viva questions generated

    # Download eligibility
    can_download = Column(Boolean, default=False)
    download_unlocked_at = Column(DateTime, nullable=True)

    # Certificate tracking
    certificate_generated = Column(Boolean, default=False)
    certificate_id = Column(String(100), nullable=True, unique=True)  # Unique ID for verification
    certificate_generated_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="learning_progress")
    user = relationship("User", backref="learning_progress")

    def __repr__(self):
        return f"<ProjectLearningProgress project={self.project_id} user={self.user_id}>"

    @property
    def overall_progress(self) -> int:
        """Calculate overall learning progress as percentage (0-100)"""
        progress = 0

        # Checkpoint 1: Code understanding (40% weight)
        if self.checkpoint_1_completed:
            progress += 40
        elif self.files_reviewed:
            # Partial credit based on files reviewed
            files_count = len(self.files_reviewed) if isinstance(self.files_reviewed, list) else 0
            # Assume minimum 5 files for full credit
            progress += min(40, int((files_count / 5) * 40))

        # Checkpoint 2: Quiz (40% weight)
        if self.checkpoint_2_passed:
            progress += 40
        elif self.checkpoint_2_score:
            # Partial credit based on quiz score
            progress += int((self.checkpoint_2_score / 100) * 40)

        # Checkpoint 3: Viva review (20% weight)
        if self.checkpoint_3_completed:
            progress += 20
        elif self.viva_total_questions > 0:
            # Partial credit based on questions reviewed
            review_ratio = self.viva_questions_reviewed / self.viva_total_questions
            progress += int(review_ratio * 20)

        return min(100, progress)

    def check_download_eligibility(self, passing_score: float = 70.0) -> bool:
        """Check if student is eligible to download the project"""
        # Must pass the concept quiz (Checkpoint 2) with minimum score
        if self.checkpoint_2_passed and self.checkpoint_2_score >= passing_score:
            if not self.can_download:
                self.can_download = True
                self.download_unlocked_at = datetime.utcnow()
            return True
        return False


class LearningQuizQuestion(Base):
    """Generated quiz questions for a specific project"""
    __tablename__ = "learning_quiz_questions"
    __table_args__ = (
        Index('ix_quiz_questions_project_id', 'project_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Question content
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), default="multiple_choice")  # multiple_choice, true_false

    # Options (JSON array of 4 options for multiple choice)
    options = Column(JSON, nullable=False)  # ["Option A", "Option B", "Option C", "Option D"]
    correct_option = Column(Integer, nullable=False)  # Index 0-3

    # Explanation for the answer
    explanation = Column(Text, nullable=True)

    # Code context
    related_file = Column(String(500), nullable=True)  # File path this question is about
    code_snippet = Column(Text, nullable=True)  # Relevant code snippet

    # Metadata
    concept = Column(String(255), nullable=True)  # e.g., "JWT Authentication", "Database Relationships"
    difficulty = Column(String(50), default="medium")  # easy, medium, hard

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="quiz_questions")

    def __repr__(self):
        return f"<LearningQuizQuestion {self.question_text[:50]}...>"


class LearningFileExplanation(Base):
    """Cached explanations for project files"""
    __tablename__ = "learning_file_explanations"
    __table_args__ = (
        Index('ix_file_explanations_project_file', 'project_id', 'file_path'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # File info
    file_path = Column(String(500), nullable=False)
    file_language = Column(String(50), nullable=True)  # python, typescript, etc.

    # Explanation content
    simple_explanation = Column(Text, nullable=True)  # Plain English explanation
    technical_explanation = Column(Text, nullable=True)  # Technical details
    key_concepts = Column(JSON, default=list)  # List of concepts used

    # Learning aids
    analogies = Column(JSON, default=list)  # Helpful analogies
    code_walkthrough = Column(JSON, default=list)  # Step-by-step walkthrough
    best_practices = Column(JSON, default=list)  # Best practices used
    common_pitfalls = Column(JSON, default=list)  # Things to avoid

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="file_explanations")

    def __repr__(self):
        return f"<LearningFileExplanation {self.file_path}>"


class LearningCertificate(Base):
    """Generated learning certificates"""
    __tablename__ = "learning_certificates"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    certificate_id = Column(String(100), unique=True, nullable=False)  # Unique verification ID

    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Student info (snapshot at time of generation)
    student_name = Column(String(255), nullable=False)
    student_email = Column(String(255), nullable=False)

    # Project info (snapshot)
    project_title = Column(String(500), nullable=False)
    project_domain = Column(String(255), nullable=True)
    tech_stack = Column(JSON, default=list)

    # Learning metrics
    quiz_score = Column(Float, nullable=False)
    quiz_attempts = Column(Integer, default=1)
    files_reviewed = Column(Integer, default=0)
    viva_questions_reviewed = Column(Integer, default=0)
    total_learning_time_minutes = Column(Integer, nullable=True)

    # Certificate file
    pdf_s3_key = Column(String(500), nullable=True)  # S3 path for PDF

    # Timestamps
    issued_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="certificates")
    user = relationship("User", backref="learning_certificates")

    def __repr__(self):
        return f"<LearningCertificate {self.certificate_id}>"
