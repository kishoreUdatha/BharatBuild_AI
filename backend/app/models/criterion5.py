"""
NAAC Criterion 5: Student Support & Progression - Database Models

This module defines database models for managing NAAC Criterion 5 requirements:
- Scholarships and Financial Assistance
- Career Guidance and Counseling
- Placement Records
- Higher Education Progression
- Alumni Engagement
- Student Grievance Redressal
- Student Mentoring
"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index, Float, Date
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== ENUMS ====================

class ScholarshipType(str, enum.Enum):
    """Types of scholarships"""
    GOVERNMENT = "government"
    INSTITUTION = "institution"
    PRIVATE = "private"
    MERIT = "merit"
    NEED_BASED = "need_based"
    SPORTS = "sports"
    MINORITY = "minority"
    SC_ST = "sc_st"
    OBC = "obc"
    EWS = "ews"
    DISABILITY = "disability"
    OTHER = "other"


class PlacementStatus(str, enum.Enum):
    """Placement status"""
    PLACED = "placed"
    HIGHER_STUDIES = "higher_studies"
    ENTREPRENEUR = "entrepreneur"
    NOT_INTERESTED = "not_interested"
    SEARCHING = "searching"
    NOT_ELIGIBLE = "not_eligible"


class CompanyType(str, enum.Enum):
    """Company/Employer types"""
    MNC = "mnc"
    STARTUP = "startup"
    PSU = "psu"
    GOVERNMENT = "government"
    PRIVATE = "private"
    NGO = "ngo"
    RESEARCH = "research"
    OTHER = "other"


class GrievanceCategory(str, enum.Enum):
    """Student grievance categories"""
    ACADEMIC = "academic"
    EXAMINATION = "examination"
    HOSTEL = "hostel"
    LIBRARY = "library"
    TRANSPORT = "transport"
    SCHOLARSHIP = "scholarship"
    HARASSMENT = "harassment"
    INFRASTRUCTURE = "infrastructure"
    FACULTY = "faculty"
    ADMINISTRATION = "administration"
    OTHER = "other"


class GrievanceStatus(str, enum.Enum):
    """Grievance resolution status"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class AlumniStatus(str, enum.Enum):
    """Alumni engagement status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REGISTERED = "registered"
    CONTRIBUTOR = "contributor"
    MENTOR = "mentor"


# ==================== MODELS ====================

class Scholarship(Base):
    """
    Scholarships and Financial Assistance.
    Key Indicator 5.1: Student Support
    """
    __tablename__ = "scholarships"

    __table_args__ = (
        Index('ix_scholarships_type', 'scholarship_type'),
        Index('ix_scholarships_academic_year', 'academic_year'),
        Index('ix_scholarships_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Student details
    student_id = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    program = Column(String(255), nullable=True)
    semester = Column(Integer, nullable=True)
    batch = Column(String(20), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Scholarship details
    scholarship_name = Column(String(255), nullable=False)
    scholarship_type = Column(SQLEnum(ScholarshipType), nullable=False)
    provider = Column(String(255), nullable=True)  # Government body, company name
    scheme_code = Column(String(100), nullable=True)

    # Amount
    amount_sanctioned = Column(Float, nullable=False)
    amount_received = Column(Float, nullable=True)
    disbursement_date = Column(Date, nullable=True)

    # Status
    is_recurring = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Documents
    sanction_letter_path = Column(String(500), nullable=True)
    application_path = Column(String(500), nullable=True)

    # Timestamps
    applied_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Scholarship {self.student_name} - {self.scholarship_name}>"


class PlacementRecord(Base):
    """
    Placement Records.
    Key Indicator 5.2: Student Progression
    """
    __tablename__ = "placement_records"

    __table_args__ = (
        Index('ix_placement_records_status', 'placement_status'),
        Index('ix_placement_records_department', 'department'),
        Index('ix_placement_records_academic_year', 'academic_year'),
        Index('ix_placement_records_company', 'company_name'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Student details
    student_id = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    program = Column(String(255), nullable=True)
    batch = Column(String(20), nullable=False)
    academic_year = Column(String(20), nullable=False)
    cgpa = Column(Float, nullable=True)

    # Placement status
    placement_status = Column(SQLEnum(PlacementStatus), nullable=False)

    # Company details (if placed)
    company_name = Column(String(255), nullable=True)
    company_type = Column(SQLEnum(CompanyType), nullable=True)
    job_title = Column(String(255), nullable=True)
    job_location = Column(String(255), nullable=True)

    # Package details
    ctc_offered = Column(Float, nullable=True)  # Cost to Company in LPA
    joining_date = Column(Date, nullable=True)
    offer_date = Column(Date, nullable=True)

    # Placement drive details
    drive_date = Column(Date, nullable=True)
    is_on_campus = Column(Boolean, default=True)
    is_core_company = Column(Boolean, default=False)  # Related to student's domain

    # Higher studies (if applicable)
    university_name = Column(String(255), nullable=True)
    course_name = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)

    # Contact
    student_email = Column(String(255), nullable=True)
    student_phone = Column(String(50), nullable=True)

    # Documents
    offer_letter_path = Column(String(500), nullable=True)
    joining_letter_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PlacementRecord {self.student_name} - {self.company_name}>"


class CareerCounseling(Base):
    """
    Career Guidance and Counseling Sessions.
    Key Indicator 5.1: Student Support
    """
    __tablename__ = "career_counseling"

    __table_args__ = (
        Index('ix_career_counseling_type', 'session_type'),
        Index('ix_career_counseling_date', 'session_date'),
        Index('ix_career_counseling_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Session details
    session_title = Column(String(500), nullable=False)
    session_type = Column(String(100), nullable=False)  # workshop, seminar, one-on-one, webinar
    description = Column(Text, nullable=True)
    topics_covered = Column(JSON, nullable=True)

    # Date and venue
    session_date = Column(Date, nullable=False)
    duration_hours = Column(Float, nullable=True)
    venue = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)  # online/offline/hybrid

    # Target audience
    department = Column(String(255), nullable=True)
    target_batch = Column(String(50), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Participation
    registered_count = Column(Integer, default=0)
    attended_count = Column(Integer, default=0)
    student_list = Column(JSON, nullable=True)

    # Resource person
    resource_person = Column(String(255), nullable=True)
    resource_person_designation = Column(String(255), nullable=True)
    resource_person_organization = Column(String(255), nullable=True)

    # Feedback
    average_rating = Column(Float, nullable=True)
    feedback_summary = Column(Text, nullable=True)

    # Organized by
    organized_by = Column(String(255), nullable=True)  # Placement Cell, Department

    # Documents
    brochure_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CareerCounseling {self.session_title}>"


class StudentGrievance(Base):
    """
    Student Grievance Records.
    Key Indicator 5.1: Student Support
    """
    __tablename__ = "student_grievances"

    __table_args__ = (
        Index('ix_student_grievances_category', 'category'),
        Index('ix_student_grievances_status', 'status'),
        Index('ix_student_grievances_date', 'submitted_date'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Grievance details
    grievance_id = Column(String(50), nullable=True, unique=True)  # Auto-generated reference
    category = Column(SQLEnum(GrievanceCategory), nullable=False)
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(GrievanceStatus), default=GrievanceStatus.SUBMITTED)

    # Student details
    student_id = Column(String(50), nullable=True)
    student_name = Column(String(255), nullable=True)
    student_email = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    is_anonymous = Column(Boolean, default=False)

    # Dates
    submitted_date = Column(Date, nullable=False)
    acknowledged_date = Column(Date, nullable=True)
    resolved_date = Column(Date, nullable=True)
    resolution_days = Column(Integer, nullable=True)

    # Resolution
    assigned_to = Column(String(255), nullable=True)
    action_taken = Column(Text, nullable=True)
    resolution_remarks = Column(Text, nullable=True)
    student_feedback = Column(Text, nullable=True)
    is_satisfied = Column(Boolean, nullable=True)

    # Documents
    attachment_path = Column(String(500), nullable=True)
    resolution_document_path = Column(String(500), nullable=True)

    # Academic year
    academic_year = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StudentGrievance {self.grievance_id}>"


class AlumniRecord(Base):
    """
    Alumni Database.
    Key Indicator 5.3: Student Participation and Activities
    """
    __tablename__ = "alumni_records"

    __table_args__ = (
        Index('ix_alumni_records_department', 'department'),
        Index('ix_alumni_records_batch', 'batch'),
        Index('ix_alumni_records_status', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Basic details
    alumni_id = Column(String(50), nullable=True, unique=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)

    # Academic details
    department = Column(String(255), nullable=False)
    program = Column(String(255), nullable=True)
    batch = Column(String(20), nullable=False)  # Graduation year
    roll_number = Column(String(50), nullable=True)
    specialization = Column(String(255), nullable=True)

    # Current status
    current_organization = Column(String(255), nullable=True)
    current_designation = Column(String(255), nullable=True)
    current_location = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)

    # Higher education
    higher_degree = Column(String(255), nullable=True)
    higher_institution = Column(String(255), nullable=True)

    # Achievements
    achievements = Column(JSON, nullable=True)  # [{"title": "", "year": ""}]
    awards = Column(JSON, nullable=True)

    # Engagement
    status = Column(SQLEnum(AlumniStatus), default=AlumniStatus.REGISTERED)
    is_donor = Column(Boolean, default=False)
    donation_amount = Column(Float, nullable=True)
    contributions = Column(JSON, nullable=True)  # ["guest_lecture", "internship", "placement"]
    mentees_count = Column(Integer, default=0)

    # Events attended
    events_attended = Column(JSON, nullable=True)
    last_interaction_date = Column(Date, nullable=True)

    # Address
    address = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)

    # Photo
    photo_path = Column(String(500), nullable=True)

    # Registration
    registered_date = Column(Date, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AlumniRecord {self.name} - {self.batch}>"


class StudentMentoring(Base):
    """
    Student Mentoring Records.
    Key Indicator 5.1: Student Support
    """
    __tablename__ = "student_mentoring"

    __table_args__ = (
        Index('ix_student_mentoring_mentor', 'mentor_id'),
        Index('ix_student_mentoring_department', 'department'),
        Index('ix_student_mentoring_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Mentee (Student) details
    student_id = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    batch = Column(String(20), nullable=True)
    semester = Column(Integer, nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Mentor details
    mentor_id = Column(String(50), nullable=False)
    mentor_name = Column(String(255), nullable=False)
    mentor_email = Column(String(255), nullable=True)
    mentor_type = Column(String(50), nullable=True)  # faculty, alumni, industry

    # Session details
    session_date = Column(Date, nullable=False)
    session_number = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    mode = Column(String(50), nullable=True)  # in-person, online

    # Discussion
    topics_discussed = Column(JSON, nullable=True)
    issues_addressed = Column(JSON, nullable=True)
    advice_given = Column(Text, nullable=True)
    action_items = Column(JSON, nullable=True)

    # Student progress
    attendance_status = Column(Float, nullable=True)  # Percentage
    academic_performance = Column(String(50), nullable=True)  # Good, Average, Needs improvement
    cgpa = Column(Float, nullable=True)
    backlogs = Column(Integer, nullable=True)

    # Goals
    short_term_goals = Column(JSON, nullable=True)
    long_term_goals = Column(JSON, nullable=True)
    progress_notes = Column(Text, nullable=True)

    # Follow-up
    next_session_date = Column(Date, nullable=True)

    # Documents
    mentoring_form_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StudentMentoring {self.student_name} - {self.mentor_name}>"


class CompetitiveExam(Base):
    """
    Competitive Exam Coaching and Results.
    Key Indicator 5.1: Student Support
    """
    __tablename__ = "competitive_exams"

    __table_args__ = (
        Index('ix_competitive_exams_exam', 'exam_name'),
        Index('ix_competitive_exams_department', 'department'),
        Index('ix_competitive_exams_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Student details
    student_id = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    batch = Column(String(20), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Exam details
    exam_name = Column(String(255), nullable=False)  # GATE, GRE, CAT, UPSC, etc.
    exam_category = Column(String(100), nullable=True)  # National, State, International
    exam_date = Column(Date, nullable=True)
    exam_year = Column(Integer, nullable=True)

    # Results
    appeared = Column(Boolean, default=True)
    qualified = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)
    percentile = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    all_india_rank = Column(Integer, nullable=True)

    # Coaching support
    coaching_attended = Column(Boolean, default=False)
    coaching_provider = Column(String(255), nullable=True)  # Institute provided, External
    coaching_duration_months = Column(Integer, nullable=True)

    # Outcome
    admission_obtained = Column(Boolean, nullable=True)
    institution_admitted = Column(String(255), nullable=True)
    course_admitted = Column(String(255), nullable=True)

    # Documents
    result_path = Column(String(500), nullable=True)
    scorecard_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CompetitiveExam {self.student_name} - {self.exam_name}>"
