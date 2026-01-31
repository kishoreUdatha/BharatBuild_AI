"""
Project Guidance & Review System Models (Merged)

Comprehensive project lifecycle management for student mini/major projects:
- Guide assignment & workload tracking
- Phase-wise reviews (4 reviews per project)
- Rubric-based scoring
- Phase locking mechanism
- Viva preparation
- NAAC evidence generation
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class ReviewType(str, enum.Enum):
    """Type of review (phase)"""
    review_1 = "review_1"  # Problem Statement, Literature Survey
    review_2 = "review_2"  # System Design, Architecture
    review_3 = "review_3"  # Implementation Progress (50%)
    final_review = "final_review"  # Complete Project Demo


class ReviewStatus(str, enum.Enum):
    """Status of review"""
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    rescheduled = "rescheduled"
    cancelled = "cancelled"


class PhaseStatus(str, enum.Enum):
    """Status of a phase"""
    not_started = "not_started"
    in_progress = "in_progress"
    submitted = "submitted"
    under_review = "under_review"
    approved = "approved"
    revision_needed = "revision_needed"
    locked = "locked"


class ProjectType(str, enum.Enum):
    """Type of student project"""
    mini_project = "mini_project"  # 5th/6th semester
    major_project = "major_project"  # 7th/8th semester


class ReviewDecision(str, enum.Enum):
    """Review decision"""
    approved = "approved"
    revision_needed = "revision_needed"
    rejected = "rejected"


class VivaReadiness(str, enum.Enum):
    """Viva readiness level"""
    not_ready = "not_ready"
    needs_preparation = "needs_preparation"
    ready = "ready"
    excellent = "excellent"


class ReviewProject(Base):
    """Student project registration for reviews"""
    __tablename__ = "review_projects"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Project details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    project_type = Column(SQLEnum(ProjectType, values_callable=lambda obj: [e.value for e in obj]), default=ProjectType.mini_project)
    technology_stack = Column(String(500), nullable=True)
    domain = Column(String(255), nullable=True)

    # Team details
    team_name = Column(String(255), nullable=True)
    team_size = Column(Integer, default=1)

    # Student (team lead)
    student_id = Column(GUID, ForeignKey("users.id"), nullable=False)

    # Guide details
    guide_id = Column(GUID, ForeignKey("users.id"), nullable=True)
    guide_name = Column(String(255), nullable=True)
    guide_assigned_at = Column(DateTime, nullable=True)

    # Academic details
    batch = Column(String(50), nullable=True)
    semester = Column(Integer, nullable=True)
    department = Column(String(255), nullable=True)
    academic_year = Column(String(20), nullable=True)

    # Project URLs
    github_url = Column(String(500), nullable=True)
    demo_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)

    # Overall scores (updated after each review)
    current_review = Column(Integer, default=0)
    total_score = Column(Float, default=0.0)
    average_score = Column(Float, default=0.0)

    # Phase tracking
    current_phase = Column(Integer, default=1)
    phase_1_locked = Column(Boolean, default=False)
    phase_2_locked = Column(Boolean, default=False)
    phase_3_locked = Column(Boolean, default=False)
    phase_4_locked = Column(Boolean, default=False)

    # AI/Plagiarism tracking
    ai_usage_percentage = Column(Float, default=0.0)
    plagiarism_percentage = Column(Float, default=0.0)
    last_integrity_check = Column(DateTime, nullable=True)

    # Viva readiness
    viva_readiness = Column(SQLEnum(VivaReadiness, values_callable=lambda obj: [e.value for e in obj]), default=VivaReadiness.not_ready)
    viva_score = Column(Float, default=0.0)

    # Status
    is_approved = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reviews = relationship("ProjectReview", back_populates="project", cascade="all, delete-orphan")
    team_members = relationship("ProjectTeamMember", back_populates="project", cascade="all, delete-orphan")
    viva_questions = relationship("VivaQuestion", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("ProjectAuditLog", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReviewProject {self.title}>"

    def is_phase_locked(self, phase_number: int) -> bool:
        """Check if a phase is locked"""
        return getattr(self, f"phase_{phase_number}_locked", False)

    def lock_phase(self, phase_number: int):
        """Lock a phase"""
        setattr(self, f"phase_{phase_number}_locked", True)

    def unlock_phase(self, phase_number: int):
        """Unlock a phase"""
        setattr(self, f"phase_{phase_number}_locked", False)


class ProjectTeamMember(Base):
    """Team members for a project"""
    __tablename__ = "project_team_members"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("review_projects.id"), nullable=False)
    student_id = Column(GUID, ForeignKey("users.id"), nullable=True)

    # Student details
    name = Column(String(255), nullable=False)
    roll_number = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("ReviewProject", back_populates="team_members")

    def __repr__(self):
        return f"<ProjectTeamMember {self.name}>"


class ProjectReview(Base):
    """Project review session"""
    __tablename__ = "project_reviews"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("review_projects.id"), nullable=False)

    # Review details
    review_type = Column(SQLEnum(ReviewType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    review_number = Column(Integer, nullable=False)

    # Phase status
    phase_status = Column(SQLEnum(PhaseStatus, values_callable=lambda obj: [e.value for e in obj]), default=PhaseStatus.not_started)

    # Schedule
    scheduled_date = Column(DateTime, nullable=False)
    scheduled_time = Column(String(20), nullable=True)
    venue = Column(String(255), nullable=True)
    duration_minutes = Column(Integer, default=30)

    # Status
    status = Column(SQLEnum(ReviewStatus, values_callable=lambda obj: [e.value for e in obj]), default=ReviewStatus.scheduled)

    # Decision
    decision = Column(SQLEnum(ReviewDecision, values_callable=lambda obj: [e.value for e in obj]), nullable=True)

    # Scores (calculated from panel scores)
    innovation_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    implementation_score = Column(Float, default=0.0)
    documentation_score = Column(Float, default=0.0)
    presentation_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)

    # Rubric scores (JSON for flexibility)
    rubric_scores = Column(JSON, nullable=True)

    # Feedback
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    overall_feedback = Column(Text, nullable=True)

    # Next steps
    action_items = Column(Text, nullable=True)
    next_review_focus = Column(Text, nullable=True)

    # Submission details
    submission_url = Column(String(500), nullable=True)
    submission_notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    # Attendance
    student_present = Column(Boolean, default=True)

    # Phase locking
    is_locked = Column(Boolean, default=False)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(GUID, ForeignKey("users.id"), nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Created by
    created_by = Column(GUID, ForeignKey("users.id"), nullable=True)
    reviewed_by = Column(GUID, ForeignKey("users.id"), nullable=True)

    # Relationships
    project = relationship("ReviewProject", back_populates="reviews")
    panel_members = relationship("ReviewPanelMember", back_populates="review", cascade="all, delete-orphan")
    scores = relationship("ReviewScore", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProjectReview {self.review_type.value} for project {self.project_id}>"

    def calculate_total_score(self):
        """Calculate total score from individual scores"""
        self.total_score = (
            self.innovation_score +
            self.technical_score +
            self.implementation_score +
            self.documentation_score +
            self.presentation_score
        )
        return self.total_score


class ReviewPanelMember(Base):
    """Panel members assigned to a review"""
    __tablename__ = "review_panel_members"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    review_id = Column(GUID, ForeignKey("project_reviews.id"), nullable=False)
    faculty_id = Column(GUID, ForeignKey("users.id"), nullable=True)

    # Faculty details
    name = Column(String(255), nullable=False)
    designation = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    # Role in panel
    role = Column(String(50), default="member")
    is_lead = Column(Boolean, default=False)

    # Attendance
    is_present = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    review = relationship("ProjectReview", back_populates="panel_members")

    def __repr__(self):
        return f"<ReviewPanelMember {self.name}>"


class ReviewScore(Base):
    """Individual scores given by each panel member"""
    __tablename__ = "review_scores"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    review_id = Column(GUID, ForeignKey("project_reviews.id"), nullable=False)
    panel_member_id = Column(GUID, ForeignKey("review_panel_members.id"), nullable=False)
    faculty_id = Column(GUID, ForeignKey("users.id"), nullable=True)

    # Individual scores
    innovation_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    implementation_score = Column(Float, default=0.0)
    documentation_score = Column(Float, default=0.0)
    presentation_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)

    # Rubric scores (JSON)
    rubric_scores = Column(JSON, nullable=True)

    # Individual feedback
    comments = Column(Text, nullable=True)
    private_notes = Column(Text, nullable=True)

    # Timestamps
    scored_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    review = relationship("ProjectReview", back_populates="scores")

    def __repr__(self):
        return f"<ReviewScore {self.total_score} for review {self.review_id}>"

    def calculate_total(self):
        """Calculate total score"""
        self.total_score = (
            self.innovation_score +
            self.technical_score +
            self.implementation_score +
            self.documentation_score +
            self.presentation_score
        )
        return self.total_score


class VivaQuestion(Base):
    """Viva questions for a project"""
    __tablename__ = "viva_questions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("review_projects.id"), nullable=False)

    # Question details
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # concept, implementation, architecture, etc.
    difficulty = Column(String(50), default="medium")  # easy, medium, hard

    # Student's answer (if practicing)
    student_answer = Column(Text, nullable=True)
    answer_score = Column(Float, nullable=True)
    answer_feedback = Column(Text, nullable=True)

    # Source
    is_ai_generated = Column(Boolean, default=False)
    source_phase = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(GUID, ForeignKey("users.id"), nullable=True)

    # Relationships
    project = relationship("ReviewProject", back_populates="viva_questions")

    def __repr__(self):
        return f"<VivaQuestion {self.question[:50]}>"


class ProjectAuditLog(Base):
    """Audit log for project changes"""
    __tablename__ = "project_audit_logs"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("review_projects.id"), nullable=False)

    # Action details
    action = Column(String(100), nullable=False)  # phase_locked, phase_unlocked, review_completed, etc.
    details = Column(JSON, nullable=True)
    phase_number = Column(Integer, nullable=True)

    # Actor
    performed_by = Column(GUID, ForeignKey("users.id"), nullable=True)
    performer_name = Column(String(255), nullable=True)
    performer_role = Column(String(100), nullable=True)

    # IP and metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("ReviewProject", back_populates="audit_logs")

    def __repr__(self):
        return f"<ProjectAuditLog {self.action} on {self.project_id}>"


class GuideAllocation(Base):
    """Guide allocation tracking"""
    __tablename__ = "guide_allocations"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Guide details
    guide_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    guide_name = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)

    # Allocation limits
    max_mini_projects = Column(Integer, default=5)
    max_major_projects = Column(Integer, default=3)
    current_mini_projects = Column(Integer, default=0)
    current_major_projects = Column(Integer, default=0)

    # Academic year
    academic_year = Column(String(20), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GuideAllocation {self.guide_name}>"

    @property
    def total_projects(self):
        return self.current_mini_projects + self.current_major_projects

    @property
    def available_mini_slots(self):
        return max(0, self.max_mini_projects - self.current_mini_projects)

    @property
    def available_major_slots(self):
        return max(0, self.max_major_projects - self.current_major_projects)


# Review criteria/rubric for reference
REVIEW_CRITERIA = {
    "review_1": {
        "name": "Review 1 - Problem Definition",
        "focus": ["Problem Statement", "Literature Survey", "Objectives", "Scope", "Feasibility"],
        "deliverables": ["Abstract", "Problem Statement Document", "Literature Survey Report"],
        "rubric": {
            "problem_clarity": {"max": 20, "desc": "Clear problem definition and scope"},
            "literature_quality": {"max": 20, "desc": "Quality of literature survey"},
            "objectives": {"max": 20, "desc": "Clear and achievable objectives"},
            "feasibility": {"max": 20, "desc": "Technical and timeline feasibility"},
            "presentation": {"max": 20, "desc": "Presentation and communication"}
        }
    },
    "review_2": {
        "name": "Review 2 - System Design",
        "focus": ["System Architecture", "Database Design", "UI/UX Design", "Tech Stack Selection"],
        "deliverables": ["SRS Document", "DFD/UML Diagrams", "ER Diagram", "Wireframes"],
        "rubric": {
            "architecture": {"max": 25, "desc": "System architecture design"},
            "database_design": {"max": 20, "desc": "Database schema and relationships"},
            "ui_design": {"max": 20, "desc": "UI/UX wireframes and flow"},
            "tech_justification": {"max": 20, "desc": "Technology stack justification"},
            "presentation": {"max": 15, "desc": "Presentation and clarity"}
        }
    },
    "review_3": {
        "name": "Review 3 - Implementation",
        "focus": ["Code Quality", "Module Integration", "Testing", "50% Implementation"],
        "deliverables": ["Working Modules", "Code Repository", "Test Cases"],
        "rubric": {
            "code_quality": {"max": 25, "desc": "Code structure and best practices"},
            "functionality": {"max": 25, "desc": "Working features implementation"},
            "integration": {"max": 20, "desc": "Module integration"},
            "testing": {"max": 15, "desc": "Test coverage and quality"},
            "progress": {"max": 15, "desc": "Progress vs timeline"}
        }
    },
    "final_review": {
        "name": "Final Review - Complete Project",
        "focus": ["Full Demo", "Documentation", "Presentation", "Viva"],
        "deliverables": ["Complete Project", "Final Documentation", "Demo Video", "PPT"],
        "rubric": {
            "completeness": {"max": 25, "desc": "Feature completeness"},
            "demo_quality": {"max": 20, "desc": "Demo and presentation"},
            "documentation": {"max": 20, "desc": "Documentation quality"},
            "viva": {"max": 20, "desc": "Viva performance"},
            "innovation": {"max": 15, "desc": "Innovation and creativity"}
        }
    },
}

SCORING_CRITERIA = {
    "innovation": {"max_score": 20, "description": "Innovation & Novelty of the idea"},
    "technical": {"max_score": 25, "description": "Technical Complexity & Implementation"},
    "implementation": {"max_score": 25, "description": "Code Quality & Functionality"},
    "documentation": {"max_score": 15, "description": "Documentation Quality"},
    "presentation": {"max_score": 15, "description": "Presentation & Communication"},
}

# Technology-specific evaluation criteria
TECH_SPECIFIC_CRITERIA = {
    "react": {
        "name": "React/Frontend",
        "evaluation_points": [
            "Component architecture & reusability",
            "State management (Redux/Context)",
            "Responsive design & mobile-first",
            "Performance optimization",
            "API integration & error handling",
        ],
    },
    "node": {
        "name": "Node.js/Backend",
        "evaluation_points": [
            "REST API design & structure",
            "Authentication & authorization",
            "Error handling & validation",
            "Database queries optimization",
            "Security best practices",
        ],
    },
    "python": {
        "name": "Python/Backend",
        "evaluation_points": [
            "Code structure & modularity",
            "API endpoint design",
            "Database ORM usage",
            "Input validation & sanitization",
            "Exception handling",
        ],
    },
    "fastapi": {
        "name": "FastAPI",
        "evaluation_points": [
            "Async/await implementation",
            "Pydantic models & validation",
            "OpenAPI documentation",
            "Dependency injection usage",
            "Background task handling",
        ],
    },
    "django": {
        "name": "Django",
        "evaluation_points": [
            "MVT architecture adherence",
            "Django ORM optimization",
            "Admin panel customization",
            "Form handling & validation",
            "Template inheritance & DRY",
        ],
    },
    "spring": {
        "name": "Spring Boot/Java",
        "evaluation_points": [
            "MVC pattern implementation",
            "Dependency injection usage",
            "JPA/Hibernate queries",
            "REST controller design",
            "Exception handling strategy",
        ],
    },
    "mongodb": {
        "name": "MongoDB",
        "evaluation_points": [
            "Schema design & denormalization",
            "Indexing strategy",
            "Aggregation pipeline usage",
            "Data validation",
            "Query optimization",
        ],
    },
    "postgresql": {
        "name": "PostgreSQL",
        "evaluation_points": [
            "Normalized schema design",
            "Index optimization",
            "Query performance",
            "Constraints & relations",
            "Transaction handling",
        ],
    },
    "mysql": {
        "name": "MySQL",
        "evaluation_points": [
            "Table design & normalization",
            "Index usage",
            "Query optimization",
            "Foreign key constraints",
            "Stored procedures (if used)",
        ],
    },
    "flutter": {
        "name": "Flutter/Mobile",
        "evaluation_points": [
            "Widget tree organization",
            "State management approach",
            "Platform-specific handling",
            "Offline capability",
            "App performance & UX",
        ],
    },
    "android": {
        "name": "Android Native",
        "evaluation_points": [
            "Activity/Fragment lifecycle",
            "MVVM architecture",
            "Local data persistence",
            "API integration",
            "Material Design guidelines",
        ],
    },
    "ml": {
        "name": "Machine Learning",
        "evaluation_points": [
            "Dataset quality & preprocessing",
            "Model selection justification",
            "Training & validation approach",
            "Accuracy/performance metrics",
            "Model deployment strategy",
        ],
    },
    "ai": {
        "name": "AI/Deep Learning",
        "evaluation_points": [
            "Neural network architecture",
            "Training optimization",
            "Overfitting prevention",
            "Model interpretability",
            "Inference performance",
        ],
    },
    "blockchain": {
        "name": "Blockchain",
        "evaluation_points": [
            "Smart contract design",
            "Gas optimization",
            "Security considerations",
            "Decentralization approach",
            "Testing methodology",
        ],
    },
    "iot": {
        "name": "IoT",
        "evaluation_points": [
            "Sensor integration",
            "Data transmission protocol",
            "Edge processing",
            "Cloud connectivity",
            "Power management",
        ],
    },
}


def get_tech_criteria(technology_stack: str) -> list:
    """Get technology-specific evaluation criteria based on tech stack"""
    if not technology_stack:
        return []

    tech_lower = technology_stack.lower()
    matched_criteria = []

    for tech_key, criteria in TECH_SPECIFIC_CRITERIA.items():
        if tech_key in tech_lower:
            matched_criteria.append(criteria)

    return matched_criteria
