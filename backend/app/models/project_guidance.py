"""
Project Guidance & Review Management Models

University-grade, NAAC/NBA-ready project tracking system.
Supports:
- Guide assignment
- Phase-wise reviews (Review-1 to Review-4)
- Rubric-based scoring
- Phase locking
- AI/Plagiarism tracking
- Complete audit trail
- Viva preparation
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, Enum as SQLEnum, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


# ==================== Enums ====================

class ProjectType(str, Enum):
    MINI = "mini"
    MAJOR = "major"
    INTERNSHIP = "internship"
    RESEARCH = "research"


class ProjectStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class PhaseStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REWORK = "rework"
    LOCKED = "locked"


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REWORK = "rework"
    PARTIAL_APPROVE = "partial_approve"


class ProjectDomain(str, Enum):
    AI_ML = "ai_ml"
    WEB_DEV = "web_dev"
    MOBILE = "mobile"
    DATA_ANALYTICS = "data_analytics"
    IOT = "iot"
    BLOCKCHAIN = "blockchain"
    CLOUD = "cloud"
    CYBERSECURITY = "cybersecurity"
    OTHER = "other"


class VivaReadiness(str, Enum):
    READY = "ready"
    NEEDS_PRACTICE = "needs_practice"
    NOT_READY = "not_ready"


# ==================== Models ====================

class StudentProject(Base):
    """Main project entity"""
    __tablename__ = "student_projects"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Student & Guide
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    guide_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    co_guide_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Academic context
    department = Column(String(100))
    semester = Column(Integer)
    academic_year = Column(String(20))  # e.g., "2025-26"
    section = Column(String(20))
    batch = Column(String(20))

    # Project details
    project_type = Column(SQLEnum(ProjectType), default=ProjectType.MINI)
    title = Column(String(500), nullable=False)
    domain = Column(SQLEnum(ProjectDomain), default=ProjectDomain.OTHER)
    problem_statement = Column(Text)
    objectives = Column(JSONB, default=list)  # List of objectives
    scope = Column(Text)
    limitations = Column(Text)
    tech_stack = Column(JSONB, default=list)  # ["Python", "React", "PostgreSQL"]
    dataset_source = Column(Text)

    # Status tracking
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.NOT_STARTED)
    current_phase = Column(Integer, default=1)  # 1-4

    # AI & Plagiarism
    overall_ai_usage_pct = Column(Float, default=0)
    overall_plagiarism_pct = Column(Float, default=0)

    # Viva
    viva_readiness = Column(SQLEnum(VivaReadiness), default=VivaReadiness.NOT_READY)
    viva_score = Column(Float, nullable=True)
    viva_date = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    phases = relationship("ProjectPhase", back_populates="project", cascade="all, delete-orphan")
    submissions = relationship("ProjectSubmission", back_populates="project", cascade="all, delete-orphan")
    reviews = relationship("ProjectReviewRecord", back_populates="project", cascade="all, delete-orphan")
    team_members = relationship("ProjectTeamMemberNew", back_populates="project", cascade="all, delete-orphan")
    viva_questions = relationship("VivaQuestion", back_populates="project", cascade="all, delete-orphan")


class ProjectPhase(Base):
    """Phase tracking for each project"""
    __tablename__ = "project_phases"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("student_projects.id"), nullable=False)

    phase_no = Column(Integer, nullable=False)  # 1, 2, 3, 4
    phase_name = Column(String(100))  # "Problem Definition", "Literature & Design", etc.

    status = Column(SQLEnum(PhaseStatus), default=PhaseStatus.PENDING)
    is_locked = Column(Boolean, default=False)

    # Review info
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Scores
    total_score = Column(Float, default=0)
    max_score = Column(Float, default=30)
    rubric_scores = Column(JSONB, default=dict)  # {"clarity": 8, "feasibility": 9}

    # Feedback
    remarks = Column(Text)
    action_items = Column(JSONB, default=list)  # ["Improve dataset explanation", ...]

    # Deadlines
    deadline = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    project = relationship("StudentProject", back_populates="phases")


class ProjectSubmission(Base):
    """Student submissions for each phase"""
    __tablename__ = "project_submissions"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("student_projects.id"), nullable=False)
    phase_no = Column(Integer, nullable=False)

    version = Column(Integer, default=1)

    # Documents
    documents = Column(JSONB, default=list)  # [{"name": "...", "url": "...", "type": "pdf"}]
    code_repository_url = Column(String(500))
    code_snapshot_id = Column(UUID(as_uuid=True), nullable=True)

    # Content
    problem_statement = Column(Text)
    objectives = Column(JSONB)
    literature_survey = Column(Text)
    references = Column(JSONB, default=list)  # IEEE format references
    architecture_diagram_url = Column(String(500))
    uml_diagrams = Column(JSONB, default=list)
    implementation_notes = Column(Text)
    results = Column(Text)
    conclusion = Column(Text)

    # AI/Plagiarism for this submission
    ai_usage_pct = Column(Float, default=0)
    plagiarism_pct = Column(Float, default=0)
    similarity_report_url = Column(String(500))

    # Status
    is_latest = Column(Boolean, default=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    project = relationship("StudentProject", back_populates="submissions")


class ProjectReviewRecord(Base):
    """Review records by faculty/panel"""
    __tablename__ = "project_review_records"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("student_projects.id"), nullable=False)
    phase_no = Column(Integer, nullable=False)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("project_submissions.id"), nullable=True)

    # Reviewer
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewer_role = Column(String(50))  # "guide", "co_guide", "hod", "panel"

    # Decision
    decision = Column(SQLEnum(ReviewDecision), nullable=False)

    # Scores
    total_score = Column(Float, default=0)
    rubric_scores = Column(JSONB, default=dict)

    # Feedback
    comments = Column(Text)
    inline_comments = Column(JSONB, default=list)  # [{"section": "...", "line": 10, "comment": "..."}]
    action_items = Column(JSONB, default=list)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("StudentProject", back_populates="reviews")


class ProjectTeamMemberNew(Base):
    """Team members for group projects"""
    __tablename__ = "project_team_members_new"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("student_projects.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    role = Column(String(50), default="member")  # "leader", "member"
    contribution_pct = Column(Float, default=0)

    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("StudentProject", back_populates="team_members")


class GuideAllocation(Base):
    """Guide allocation history"""
    __tablename__ = "guide_allocations"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    guide_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("student_projects.id"), nullable=True)

    academic_year = Column(String(20))
    semester = Column(Integer)
    department = Column(String(100))

    allocation_type = Column(String(50), default="primary")  # "primary", "co_guide"
    allocated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    allocated_at = Column(DateTime, default=datetime.utcnow)

    # If changed
    is_active = Column(Boolean, default=True)
    replaced_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    replaced_at = Column(DateTime, nullable=True)
    change_reason = Column(Text)


class ReviewRubricTemplate(Base):
    """Configurable rubric templates"""
    __tablename__ = "review_rubric_templates"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(200))
    phase_no = Column(Integer)  # 1-4
    project_type = Column(SQLEnum(ProjectType), nullable=True)  # null = all types
    department = Column(String(100), nullable=True)  # null = all departments

    # Rubric criteria
    criteria = Column(JSONB, default=list)
    # [{"name": "Problem Clarity", "max_score": 10, "description": "..."}, ...]

    total_max_score = Column(Float, default=30)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))


class VivaQuestion(Base):
    """Viva questions for projects"""
    __tablename__ = "viva_questions"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("student_projects.id"), nullable=False)

    question = Column(Text, nullable=False)
    expected_answer = Column(Text)
    category = Column(String(100))  # "technical", "conceptual", "implementation", "theory"
    difficulty = Column(String(20), default="medium")  # "easy", "medium", "hard"

    # Source
    source = Column(String(50), default="manual")  # "manual", "ai_generated", "review_based"
    generated_from = Column(String(50))  # "code", "review_comment", "domain"

    # Student response (mock viva)
    student_answer = Column(Text)
    answer_score = Column(Float, nullable=True)
    faculty_feedback = Column(Text)

    # Actual viva
    asked_in_viva = Column(Boolean, default=False)
    viva_response = Column(Text)
    viva_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    project = relationship("StudentProject", back_populates="viva_questions")


class ProjectAuditLog(Base):
    """Complete audit trail"""
    __tablename__ = "project_audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    actor_role = Column(String(50))

    action = Column(String(100), nullable=False)  # "submit", "review", "lock", "unlock", "edit"
    entity_type = Column(String(50))  # "project", "phase", "submission", "review"
    entity_id = Column(UUID(as_uuid=True))

    old_value = Column(JSONB)
    new_value = Column(JSONB)

    reason = Column(Text)
    ip_address = Column(String(50))

    timestamp = Column(DateTime, default=datetime.utcnow)


class NAACEvidence(Base):
    """NAAC/NBA evidence generation"""
    __tablename__ = "naac_evidence"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    evidence_type = Column(String(100))  # "project_allotment", "review_schedule", "review_minutes"
    academic_year = Column(String(20))
    semester = Column(Integer)
    department = Column(String(100))

    title = Column(String(500))
    description = Column(Text)

    # Generated content
    content = Column(JSONB)
    document_url = Column(String(500))

    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))


# ==================== Default Rubric Data ====================

DEFAULT_RUBRICS = {
    1: {  # Review-1: Problem Definition
        "name": "Problem Definition Review",
        "criteria": [
            {"name": "Problem Clarity", "max_score": 10, "description": "Clear articulation of the problem"},
            {"name": "Objectives Relevance", "max_score": 10, "description": "Well-defined, achievable objectives"},
            {"name": "Feasibility", "max_score": 10, "description": "Technical and time feasibility"}
        ],
        "total_max_score": 30
    },
    2: {  # Review-2: Literature & Design
        "name": "Literature & Design Review",
        "criteria": [
            {"name": "Literature Survey", "max_score": 10, "description": "Comprehensive review of existing work"},
            {"name": "Design Correctness", "max_score": 10, "description": "Appropriate system design"},
            {"name": "Architecture/UML", "max_score": 10, "description": "Clear architectural diagrams"}
        ],
        "total_max_score": 30
    },
    3: {  # Review-3: Implementation
        "name": "Implementation Review",
        "criteria": [
            {"name": "Code Quality", "max_score": 8, "description": "Clean, readable, well-structured code"},
            {"name": "Logic & Correctness", "max_score": 6, "description": "Correct implementation of requirements"},
            {"name": "Version History", "max_score": 6, "description": "Proper version control usage"}
        ],
        "total_max_score": 20
    },
    4: {  # Review-4: Final Review
        "name": "Final Review",
        "criteria": [
            {"name": "Results & Analysis", "max_score": 8, "description": "Comprehensive results with analysis"},
            {"name": "Documentation", "max_score": 6, "description": "Complete project documentation"},
            {"name": "Presentation Readiness", "max_score": 6, "description": "Ready for final presentation"}
        ],
        "total_max_score": 20
    }
}

PHASE_NAMES = {
    1: "Problem Definition",
    2: "Literature & Design",
    3: "Implementation",
    4: "Final Review"
}

PHASE_REVIEWERS = {
    1: ["guide"],
    2: ["guide", "hod"],
    3: ["guide", "panel"],
    4: ["hod", "panel"]
}
