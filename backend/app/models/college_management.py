"""
College Management Models
- College, Department, Section management
- Student-Faculty relationships
- Project tracking and oversight
"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class CollegeStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class DepartmentType(str, enum.Enum):
    CSE = "cse"
    ECE = "ece"
    EEE = "eee"
    MECH = "mech"
    CIVIL = "civil"
    IT = "it"
    AIDS = "aids"
    AIML = "aiml"
    OTHER = "other"


class ProjectPhase(str, enum.Enum):
    IDEATION = "ideation"
    PLANNING = "planning"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REVIEW = "review"
    COMPLETED = "completed"


class College(Base):
    """College/Institution model"""
    __tablename__ = "colleges"
    __table_args__ = {'extend_existing': True}

    id = Column(GUID, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)  # e.g., JNTUH, CBIT
    university = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    logo_url = Column(Text, nullable=True)

    status = Column(SQLEnum(CollegeStatus), default=CollegeStatus.ACTIVE)

    # Subscription details
    subscription_plan = Column(String(50), default="free")  # free, basic, premium, enterprise
    subscription_expires = Column(DateTime, nullable=True)
    max_students = Column(Integer, default=500)
    max_faculty = Column(Integer, default=50)

    # Principal details (quick reference)
    principal_id = Column(GUID, nullable=True)
    vice_principal_id = Column(GUID, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    departments = relationship("Department", back_populates="college", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="college", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<College {self.name}>"


class Department(Base):
    """Department model"""
    __tablename__ = "departments"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., Computer Science and Engineering
    code = Column(String(20), nullable=False)   # e.g., CSE
    type = Column(SQLEnum(DepartmentType), default=DepartmentType.OTHER)

    # HOD details
    hod_id = Column(GUID, nullable=True)
    hod_name = Column(String(255), nullable=True)

    # Department stats
    total_students = Column(Integer, default=0)
    total_faculty = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    college = relationship("College", back_populates="departments")
    sections = relationship("Section", back_populates="department", cascade="all, delete-orphan")
    faculty_assignments = relationship("FacultyAssignment", back_populates="department")

    def __repr__(self):
        return f"<Department {self.code}>"


class Section(Base):
    """Section/Class model"""
    __tablename__ = "sections"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    department_id = Column(GUID, ForeignKey("departments.id"), nullable=False)
    name = Column(String(50), nullable=False)  # e.g., A, B, C
    year = Column(Integer, nullable=False)      # 1, 2, 3, 4
    semester = Column(Integer, nullable=False)  # 1-8

    # Class teacher/coordinator
    coordinator_id = Column(GUID, nullable=True)

    student_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="sections")
    student_sections = relationship("StudentSection", back_populates="section")

    def __repr__(self):
        return f"<Section {self.name} Year-{self.year}>"


class Batch(Base):
    """Academic Batch model (e.g., 2021-2025)"""
    __tablename__ = "batches"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False)
    name = Column(String(50), nullable=False)  # e.g., 2021-2025
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    college = relationship("College", back_populates="batches")

    def __repr__(self):
        return f"<Batch {self.name}>"


class FacultyAssignment(Base):
    """Faculty assignment to departments"""
    __tablename__ = "faculty_assignments"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    department_id = Column(GUID, ForeignKey("departments.id"), nullable=False)
    designation = Column(String(100), nullable=True)  # Professor, Asst. Professor, etc.
    specialization = Column(String(255), nullable=True)
    is_guide = Column(Boolean, default=False)  # Can guide projects
    max_students = Column(Integer, default=5)  # Max students can guide
    current_students = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="faculty_assignments")

    def __repr__(self):
        return f"<FacultyAssignment {self.user_id}>"


class StudentSection(Base):
    """Student assignment to sections"""
    __tablename__ = "student_sections"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    section_id = Column(GUID, ForeignKey("sections.id"), nullable=False)
    roll_number = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    enrolled_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    section = relationship("Section", back_populates="student_sections")

    def __repr__(self):
        return f"<StudentSection {self.roll_number}>"


class StudentProject(Base):
    """Student project tracking with phases"""
    __tablename__ = "student_projects"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    student_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    project_id = Column(GUID, ForeignKey("projects.id"), nullable=True)

    # Project details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    technology_stack = Column(JSON, nullable=True)  # ["Python", "React", "PostgreSQL"]

    # Phase tracking
    current_phase = Column(SQLEnum(ProjectPhase), default=ProjectPhase.IDEATION)
    phase_progress = Column(JSON, nullable=True)  # {"ideation": 100, "planning": 50, ...}

    # Guide assignment
    guide_id = Column(GUID, nullable=True)
    guide_name = Column(String(255), nullable=True)

    # Review details
    last_review_date = Column(DateTime, nullable=True)
    last_review_comments = Column(Text, nullable=True)
    review_count = Column(Integer, default=0)

    # Scores
    plagiarism_score = Column(Float, nullable=True)  # 0-100
    ai_detection_score = Column(Float, nullable=True)  # 0-100
    guide_rating = Column(Float, nullable=True)  # 1-5

    # Status
    is_approved = Column(Boolean, default=False)
    approved_by = Column(GUID, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Deadlines
    submission_deadline = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StudentProject {self.title}>"


class ProjectMilestone(Base):
    """Project milestones/phases"""
    __tablename__ = "project_milestones"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    student_project_id = Column(GUID, ForeignKey("student_projects.id"), nullable=False)

    phase = Column(SQLEnum(ProjectPhase), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Progress
    progress = Column(Integer, default=0)  # 0-100
    status = Column(String(50), default="pending")  # pending, in_progress, completed, approved

    # Deliverables
    deliverables = Column(JSON, nullable=True)  # ["Document.pdf", "Code.zip"]

    # Review
    reviewed_by = Column(GUID, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comments = Column(Text, nullable=True)
    score = Column(Float, nullable=True)  # 0-100

    # Deadlines
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProjectMilestone {self.title}>"


class CollegeAnnouncement(Base):
    """College announcements"""
    __tablename__ = "college_announcements"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False)
    department_id = Column(GUID, nullable=True)  # If null, applies to all departments

    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent

    created_by = Column(GUID, nullable=False)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Announcement {self.title}>"
