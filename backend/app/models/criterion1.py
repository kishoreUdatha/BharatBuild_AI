"""
NAAC Criterion 1: Curricular Aspects - Database Models

This module defines database models for managing NAAC Criterion 1 requirements:
- Curriculum Feedback (from students, alumni, employers, teachers)
- Curriculum Evidence (syllabus, CO-PO matrices, MoUs, reports)
- Industry Partners (MoUs and collaborations)
- Advisory Board Meetings (IAB/BOG records)
- Value-Added Courses (skill certification programs)
- Internship Records (internship tracking)
"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== ENUMS ====================

class FeedbackType(str, enum.Enum):
    """Types of curriculum feedback sources"""
    STUDENT = "student"
    ALUMNI = "alumni"
    EMPLOYER = "employer"
    TEACHER = "teacher"
    INDUSTRY_EXPERT = "industry_expert"
    PARENT = "parent"


class FeedbackStatus(str, enum.Enum):
    """Status of feedback processing"""
    PENDING = "pending"
    REVIEWED = "reviewed"
    ACTION_TAKEN = "action_taken"
    CLOSED = "closed"


class EvidenceType(str, enum.Enum):
    """Types of curriculum evidence"""
    SYLLABUS = "syllabus"
    CO_PO_MATRIX = "co_po_matrix"
    MOU = "mou"
    FEEDBACK_REPORT = "feedback_report"
    MEETING_MINUTES = "meeting_minutes"
    COURSE_FILE = "course_file"
    ATTAINMENT_REPORT = "attainment_report"
    CURRICULUM_REVISION = "curriculum_revision"
    BOARD_RESOLUTION = "board_resolution"
    OTHER = "other"


class PartnerType(str, enum.Enum):
    """Types of industry partners"""
    CORPORATE = "corporate"
    STARTUP = "startup"
    GOVERNMENT = "government"
    RESEARCH_INSTITUTION = "research_institution"
    NGO = "ngo"
    PROFESSIONAL_BODY = "professional_body"


class MoUStatus(str, enum.Enum):
    """Status of MoU agreements"""
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    RENEWED = "renewed"
    TERMINATED = "terminated"


class CourseType(str, enum.Enum):
    """Types of value-added courses"""
    SKILL_DEVELOPMENT = "skill_development"
    SOFT_SKILLS = "soft_skills"
    LANGUAGE = "language"
    ICT = "ict"
    EMPLOYABILITY = "employability"
    ENTREPRENEURSHIP = "entrepreneurship"
    CERTIFICATION = "certification"
    BRIDGE_COURSE = "bridge_course"


class CourseMode(str, enum.Enum):
    """Mode of course delivery"""
    OFFLINE = "offline"
    ONLINE = "online"
    HYBRID = "hybrid"


class InternshipType(str, enum.Enum):
    """Types of internships"""
    INDUSTRY = "industry"
    RESEARCH = "research"
    GOVERNMENT = "government"
    NGO = "ngo"
    STARTUP = "startup"
    INTERNATIONAL = "international"


class InternshipStatus(str, enum.Enum):
    """Status of internship"""
    ONGOING = "ongoing"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


# ==================== MODELS ====================

class CurriculumFeedback(Base):
    """
    Feedback on curriculum from various stakeholders.
    Key Indicator 1.4: Feedback from stakeholders on curriculum
    """
    __tablename__ = "curriculum_feedback"

    __table_args__ = (
        Index('ix_curriculum_feedback_type', 'feedback_type'),
        Index('ix_curriculum_feedback_status', 'status'),
        Index('ix_curriculum_feedback_academic_year', 'academic_year'),
        Index('ix_curriculum_feedback_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Source information
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)
    respondent_name = Column(String(255), nullable=True)  # Optional for anonymity
    respondent_email = Column(String(255), nullable=True)
    respondent_organization = Column(String(255), nullable=True)
    respondent_designation = Column(String(255), nullable=True)

    # Feedback context
    department = Column(String(255), nullable=False)
    program = Column(String(255), nullable=True)
    course_code = Column(String(50), nullable=True)
    course_name = Column(String(255), nullable=True)
    academic_year = Column(String(20), nullable=False)  # e.g., "2024-25"
    semester = Column(Integer, nullable=True)

    # Feedback content
    feedback_content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 scale
    suggestions = Column(Text, nullable=True)

    # Structured feedback (JSON for flexibility)
    structured_responses = Column(JSON, nullable=True)  # {question_id: response, ...}

    # Processing
    status = Column(SQLEnum(FeedbackStatus), default=FeedbackStatus.PENDING)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Action taken
    action_taken = Column(Text, nullable=True)
    action_date = Column(DateTime, nullable=True)
    action_evidence = Column(String(500), nullable=True)  # Path to evidence file

    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CurriculumFeedback {self.feedback_type.value} - {self.department}>"


class CurriculumEvidence(Base):
    """
    Evidence documents for NAAC Criterion 1 compliance.
    Supports all key indicators (1.1-1.4)
    """
    __tablename__ = "curriculum_evidence"

    __table_args__ = (
        Index('ix_curriculum_evidence_type', 'evidence_type'),
        Index('ix_curriculum_evidence_key_indicator', 'key_indicator'),
        Index('ix_curriculum_evidence_academic_year', 'academic_year'),
        Index('ix_curriculum_evidence_verified', 'is_verified'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Classification
    evidence_type = Column(SQLEnum(EvidenceType), nullable=False)
    key_indicator = Column(String(10), nullable=False)  # e.g., "1.1", "1.2", "1.3", "1.4"

    # Document information
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    file_type = Column(String(50), nullable=True)  # e.g., "pdf", "docx"

    # Context
    department = Column(String(255), nullable=True)
    program = Column(String(255), nullable=True)
    course_code = Column(String(50), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Verification
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_remarks = Column(Text, nullable=True)

    # Metadata
    uploaded_by = Column(String(255), nullable=False)
    extra_data = Column(JSON, nullable=True)  # Additional flexible metadata

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CurriculumEvidence {self.title}>"


class IndustryPartner(Base):
    """
    Industry partners for MoUs and collaborations.
    Key Indicator 1.3: Integration of cross-cutting issues
    """
    __tablename__ = "industry_partners"

    __table_args__ = (
        Index('ix_industry_partners_type', 'partner_type'),
        Index('ix_industry_partners_status', 'mou_status'),
        Index('ix_industry_partners_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Partner information
    name = Column(String(500), nullable=False)
    partner_type = Column(SQLEnum(PartnerType), nullable=False)
    industry_sector = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)

    # Contact details
    contact_person = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)

    # MoU details
    mou_number = Column(String(100), nullable=True)
    mou_status = Column(SQLEnum(MoUStatus), default=MoUStatus.DRAFT)
    mou_signed_date = Column(Date, nullable=True)
    mou_expiry_date = Column(Date, nullable=True)
    mou_document_path = Column(String(500), nullable=True)

    # Collaboration details
    department = Column(String(255), nullable=True)  # Primary department
    collaboration_areas = Column(JSON, nullable=True)  # ["internships", "projects", "workshops"]
    activities_conducted = Column(JSON, nullable=True)  # [{activity, date, description}, ...]

    # Benefits tracking
    students_benefited = Column(Integer, default=0)
    projects_completed = Column(Integer, default=0)
    placements_provided = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meetings = relationship("AdvisoryBoardMeeting", back_populates="partner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<IndustryPartner {self.name}>"


class AdvisoryBoardMeeting(Base):
    """
    Industry Advisory Board (IAB) and Board of Governors (BOG) meeting records.
    Key Indicator 1.1: Curriculum design and development
    """
    __tablename__ = "advisory_board_meetings"

    __table_args__ = (
        Index('ix_advisory_board_meetings_date', 'meeting_date'),
        Index('ix_advisory_board_meetings_type', 'meeting_type'),
        Index('ix_advisory_board_meetings_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Meeting details
    title = Column(String(500), nullable=False)
    meeting_type = Column(String(50), nullable=False)  # "IAB", "BOG", "BOS", "Academic Council"
    meeting_date = Column(Date, nullable=False)
    venue = Column(String(255), nullable=True)

    # Context
    department = Column(String(255), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Partner association (optional)
    partner_id = Column(GUID, ForeignKey("industry_partners.id", ondelete="SET NULL"), nullable=True)

    # Participants
    attendees = Column(JSON, nullable=True)  # [{name, designation, organization}, ...]
    external_experts = Column(JSON, nullable=True)

    # Agenda and minutes
    agenda = Column(Text, nullable=True)
    minutes = Column(Text, nullable=True)
    resolutions = Column(JSON, nullable=True)  # [{resolution, action_by, deadline}, ...]

    # Documents
    minutes_document_path = Column(String(500), nullable=True)
    attendance_sheet_path = Column(String(500), nullable=True)

    # Action tracking
    action_items = Column(JSON, nullable=True)  # [{item, responsible, status, completion_date}, ...]

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    partner = relationship("IndustryPartner", back_populates="meetings")

    def __repr__(self):
        return f"<AdvisoryBoardMeeting {self.title} - {self.meeting_date}>"


class ValueAddedCourse(Base):
    """
    Value-added courses and skill development programs.
    Key Indicator 1.3: Value-added courses
    """
    __tablename__ = "value_added_courses"

    __table_args__ = (
        Index('ix_value_added_courses_type', 'course_type'),
        Index('ix_value_added_courses_academic_year', 'academic_year'),
        Index('ix_value_added_courses_department', 'department'),
        Index('ix_value_added_courses_status', 'is_active'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Course information
    course_name = Column(String(500), nullable=False)
    course_code = Column(String(50), nullable=True)
    course_type = Column(SQLEnum(CourseType), nullable=False)
    course_mode = Column(SQLEnum(CourseMode), default=CourseMode.OFFLINE)

    # Academic context
    department = Column(String(255), nullable=False)
    academic_year = Column(String(20), nullable=False)
    semester = Column(Integer, nullable=True)

    # Course details
    description = Column(Text, nullable=True)
    objectives = Column(JSON, nullable=True)  # ["obj1", "obj2", ...]
    outcomes = Column(JSON, nullable=True)  # ["CO1", "CO2", ...]
    duration_hours = Column(Integer, nullable=False)
    credits = Column(Float, nullable=True)

    # CO-PO Mapping
    co_po_mapping = Column(JSON, nullable=True)  # {CO1: {PO1: 3, PO2: 2, ...}, ...}

    # Instructor details
    instructor_name = Column(String(255), nullable=True)
    instructor_qualification = Column(String(255), nullable=True)
    instructor_organization = Column(String(255), nullable=True)  # For external experts

    # Schedule
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    schedule = Column(JSON, nullable=True)  # [{day, time, duration}, ...]

    # Enrollment and completion
    max_enrollment = Column(Integer, nullable=True)
    current_enrollment = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)

    # Certification
    certification_provided = Column(Boolean, default=False)
    certifying_body = Column(String(255), nullable=True)

    # Documents
    syllabus_path = Column(String(500), nullable=True)
    materials_path = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    enrollments = relationship("ValueAddedCourseEnrollment", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ValueAddedCourse {self.course_name}>"


class ValueAddedCourseEnrollment(Base):
    """
    Enrollment records for value-added courses.
    """
    __tablename__ = "value_added_course_enrollments"

    __table_args__ = (
        Index('ix_vac_enrollments_course_id', 'course_id'),
        Index('ix_vac_enrollments_student_id', 'student_id'),
        Index('ix_vac_enrollments_status', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    course_id = Column(GUID, ForeignKey("value_added_courses.id", ondelete="CASCADE"), nullable=False)

    # Student details
    student_id = Column(String(50), nullable=False)  # Roll number or ID
    student_name = Column(String(255), nullable=False)
    student_email = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    batch = Column(String(20), nullable=True)  # e.g., "2024"

    # Enrollment
    enrollment_date = Column(Date, nullable=False)
    status = Column(String(50), default="enrolled")  # enrolled, completed, dropped

    # Completion
    completion_date = Column(Date, nullable=True)
    grade = Column(String(10), nullable=True)
    score = Column(Float, nullable=True)
    certificate_issued = Column(Boolean, default=False)
    certificate_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("ValueAddedCourse", back_populates="enrollments")

    def __repr__(self):
        return f"<ValueAddedCourseEnrollment {self.student_name} - {self.course_id}>"


class InternshipRecord(Base):
    """
    Internship tracking for students.
    Key Indicator 1.3: Integration with employability
    """
    __tablename__ = "internship_records"

    __table_args__ = (
        Index('ix_internship_records_type', 'internship_type'),
        Index('ix_internship_records_status', 'status'),
        Index('ix_internship_records_department', 'department'),
        Index('ix_internship_records_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Student details
    student_id = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    student_email = Column(String(255), nullable=True)
    department = Column(String(255), nullable=False)
    batch = Column(String(20), nullable=True)
    semester = Column(Integer, nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Internship details
    internship_type = Column(SQLEnum(InternshipType), nullable=False)
    company_name = Column(String(500), nullable=False)
    company_website = Column(String(500), nullable=True)
    industry_sector = Column(String(255), nullable=True)

    # Location
    location = Column(String(255), nullable=True)
    is_remote = Column(Boolean, default=False)

    # Duration
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    duration_weeks = Column(Integer, nullable=True)

    # Role and project
    role_title = Column(String(255), nullable=True)
    project_title = Column(String(500), nullable=True)
    project_description = Column(Text, nullable=True)
    skills_used = Column(JSON, nullable=True)  # ["Python", "Machine Learning", ...]

    # Mentorship
    company_mentor = Column(String(255), nullable=True)
    faculty_mentor = Column(String(255), nullable=True)

    # Stipend
    is_paid = Column(Boolean, default=False)
    stipend_amount = Column(Float, nullable=True)
    stipend_currency = Column(String(10), default="INR")

    # Status and outcome
    status = Column(SQLEnum(InternshipStatus), default=InternshipStatus.ONGOING)
    ppo_offered = Column(Boolean, default=False)  # Pre-Placement Offer
    converted_to_job = Column(Boolean, default=False)

    # Evaluation
    performance_rating = Column(Float, nullable=True)  # 1-10
    feedback = Column(Text, nullable=True)

    # Documents
    offer_letter_path = Column(String(500), nullable=True)
    completion_certificate_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InternshipRecord {self.student_name} @ {self.company_name}>"
