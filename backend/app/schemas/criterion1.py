"""
NAAC Criterion 1: Curricular Aspects - Pydantic Schemas

This module defines request/response schemas for Criterion 1 API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== ENUMS ====================

class FeedbackType(str, Enum):
    STUDENT = "student"
    ALUMNI = "alumni"
    EMPLOYER = "employer"
    TEACHER = "teacher"
    INDUSTRY_EXPERT = "industry_expert"
    PARENT = "parent"


class FeedbackStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    ACTION_TAKEN = "action_taken"
    CLOSED = "closed"


class EvidenceType(str, Enum):
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


class PartnerType(str, Enum):
    CORPORATE = "corporate"
    STARTUP = "startup"
    GOVERNMENT = "government"
    RESEARCH_INSTITUTION = "research_institution"
    NGO = "ngo"
    PROFESSIONAL_BODY = "professional_body"


class MoUStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    RENEWED = "renewed"
    TERMINATED = "terminated"


class CourseType(str, Enum):
    SKILL_DEVELOPMENT = "skill_development"
    SOFT_SKILLS = "soft_skills"
    LANGUAGE = "language"
    ICT = "ict"
    EMPLOYABILITY = "employability"
    ENTREPRENEURSHIP = "entrepreneurship"
    CERTIFICATION = "certification"
    BRIDGE_COURSE = "bridge_course"


class CourseMode(str, Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    HYBRID = "hybrid"


class InternshipType(str, Enum):
    INDUSTRY = "industry"
    RESEARCH = "research"
    GOVERNMENT = "government"
    NGO = "ngo"
    STARTUP = "startup"
    INTERNATIONAL = "international"


class InternshipStatus(str, Enum):
    ONGOING = "ongoing"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


# ==================== FEEDBACK SCHEMAS ====================

class FeedbackCreate(BaseModel):
    """Schema for creating curriculum feedback"""
    feedback_type: FeedbackType
    respondent_name: Optional[str] = None
    respondent_email: Optional[str] = None
    respondent_organization: Optional[str] = None
    respondent_designation: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    program: Optional[str] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # e.g., "2024-25"
    semester: Optional[int] = Field(None, ge=1, le=8)
    feedback_content: str = Field(..., min_length=10)
    rating: Optional[int] = Field(None, ge=1, le=5)
    suggestions: Optional[str] = None
    structured_responses: Optional[Dict[str, Any]] = None


class FeedbackUpdate(BaseModel):
    """Schema for updating feedback status and action"""
    status: Optional[FeedbackStatus] = None
    reviewed_by: Optional[str] = None
    action_taken: Optional[str] = None
    action_evidence: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Schema for feedback response"""
    id: str
    feedback_type: str
    respondent_name: Optional[str]
    respondent_email: Optional[str]
    respondent_organization: Optional[str]
    respondent_designation: Optional[str]
    department: str
    program: Optional[str]
    course_code: Optional[str]
    course_name: Optional[str]
    academic_year: str
    semester: Optional[int]
    feedback_content: str
    rating: Optional[int]
    suggestions: Optional[str]
    structured_responses: Optional[Dict[str, Any]]
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    action_taken: Optional[str]
    action_date: Optional[datetime]
    action_evidence: Optional[str]
    submitted_at: datetime
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(BaseModel):
    """Schema for paginated feedback list"""
    items: List[FeedbackResponse]
    total: int
    page: int
    page_size: int
    filters: Optional[Dict[str, Any]] = None


class FeedbackActionRequest(BaseModel):
    """Schema for recording action taken on feedback"""
    action_taken: str = Field(..., min_length=10)
    action_evidence: Optional[str] = None


class FeedbackReportRequest(BaseModel):
    """Schema for generating feedback action-taken report"""
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    department: Optional[str] = None
    feedback_types: Optional[List[FeedbackType]] = None
    include_pending: bool = False


# ==================== EVIDENCE SCHEMAS ====================

class EvidenceCreate(BaseModel):
    """Schema for creating evidence record (file upload handled separately)"""
    evidence_type: EvidenceType
    key_indicator: str = Field(..., pattern=r"^1\.[1-4]$")  # 1.1, 1.2, 1.3, 1.4
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    department: Optional[str] = None
    program: Optional[str] = None
    course_code: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    metadata: Optional[Dict[str, Any]] = None


class EvidenceUpdate(BaseModel):
    """Schema for updating evidence"""
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EvidenceVerifyRequest(BaseModel):
    """Schema for evidence verification"""
    verified_by: str = Field(..., min_length=1)
    verification_remarks: Optional[str] = None


class EvidenceResponse(BaseModel):
    """Schema for evidence response"""
    id: str
    evidence_type: str
    key_indicator: str
    title: str
    description: Optional[str]
    file_path: str
    file_name: str
    file_size: Optional[int]
    file_type: Optional[str]
    department: Optional[str]
    program: Optional[str]
    course_code: Optional[str]
    academic_year: str
    is_verified: bool
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    verification_remarks: Optional[str]
    uploaded_by: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class EvidenceListResponse(BaseModel):
    """Schema for paginated evidence list"""
    items: List[EvidenceResponse]
    total: int
    page: int
    page_size: int
    by_key_indicator: Optional[Dict[str, int]] = None


# ==================== INDUSTRY PARTNER SCHEMAS ====================

class PartnerCreate(BaseModel):
    """Schema for creating industry partner"""
    name: str = Field(..., min_length=2, max_length=500)
    partner_type: PartnerType
    industry_sector: Optional[str] = None
    website: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None
    collaboration_areas: Optional[List[str]] = None


class PartnerUpdate(BaseModel):
    """Schema for updating industry partner"""
    name: Optional[str] = None
    partner_type: Optional[PartnerType] = None
    industry_sector: Optional[str] = None
    website: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None
    collaboration_areas: Optional[List[str]] = None
    mou_status: Optional[MoUStatus] = None
    mou_signed_date: Optional[date] = None
    mou_expiry_date: Optional[date] = None


class PartnerMoUUpdate(BaseModel):
    """Schema for updating MoU details"""
    mou_number: str = Field(..., min_length=1)
    mou_status: MoUStatus
    mou_signed_date: date
    mou_expiry_date: Optional[date] = None


class PartnerActivityCreate(BaseModel):
    """Schema for adding activity to partner"""
    activity: str = Field(..., min_length=3)
    activity_date: date
    description: Optional[str] = None
    students_benefited: Optional[int] = Field(None, ge=0)


class PartnerResponse(BaseModel):
    """Schema for industry partner response"""
    id: str
    name: str
    partner_type: str
    industry_sector: Optional[str]
    website: Optional[str]
    contact_person: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]
    mou_number: Optional[str]
    mou_status: str
    mou_signed_date: Optional[date]
    mou_expiry_date: Optional[date]
    mou_document_path: Optional[str]
    department: Optional[str]
    collaboration_areas: Optional[List[str]]
    activities_conducted: Optional[List[Dict[str, Any]]]
    students_benefited: int
    projects_completed: int
    placements_provided: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PartnerListResponse(BaseModel):
    """Schema for paginated partner list"""
    items: List[PartnerResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None


# ==================== ADVISORY BOARD MEETING SCHEMAS ====================

class MeetingCreate(BaseModel):
    """Schema for creating advisory board meeting"""
    title: str = Field(..., min_length=3, max_length=500)
    meeting_type: str = Field(..., pattern=r"^(IAB|BOG|BOS|Academic Council|Other)$")
    meeting_date: date
    venue: Optional[str] = None
    department: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    partner_id: Optional[str] = None
    attendees: Optional[List[Dict[str, str]]] = None
    external_experts: Optional[List[Dict[str, str]]] = None
    agenda: Optional[str] = None


class MeetingUpdate(BaseModel):
    """Schema for updating meeting"""
    title: Optional[str] = None
    venue: Optional[str] = None
    attendees: Optional[List[Dict[str, str]]] = None
    external_experts: Optional[List[Dict[str, str]]] = None
    agenda: Optional[str] = None
    minutes: Optional[str] = None
    resolutions: Optional[List[Dict[str, Any]]] = None
    action_items: Optional[List[Dict[str, Any]]] = None


class MeetingResponse(BaseModel):
    """Schema for meeting response"""
    id: str
    title: str
    meeting_type: str
    meeting_date: date
    venue: Optional[str]
    department: Optional[str]
    academic_year: str
    partner_id: Optional[str]
    attendees: Optional[List[Dict[str, str]]]
    external_experts: Optional[List[Dict[str, str]]]
    agenda: Optional[str]
    minutes: Optional[str]
    resolutions: Optional[List[Dict[str, Any]]]
    minutes_document_path: Optional[str]
    attendance_sheet_path: Optional[str]
    action_items: Optional[List[Dict[str, Any]]]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class MeetingListResponse(BaseModel):
    """Schema for paginated meeting list"""
    items: List[MeetingResponse]
    total: int
    page: int
    page_size: int


# ==================== VALUE-ADDED COURSE SCHEMAS ====================

class ValueAddedCourseCreate(BaseModel):
    """Schema for creating value-added course"""
    course_name: str = Field(..., min_length=3, max_length=500)
    course_code: Optional[str] = None
    course_type: CourseType
    course_mode: CourseMode = CourseMode.OFFLINE
    department: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    semester: Optional[int] = Field(None, ge=1, le=8)
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    outcomes: Optional[List[str]] = None
    duration_hours: int = Field(..., ge=1)
    credits: Optional[float] = Field(None, ge=0)
    co_po_mapping: Optional[Dict[str, Dict[str, int]]] = None
    instructor_name: Optional[str] = None
    instructor_qualification: Optional[str] = None
    instructor_organization: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    schedule: Optional[List[Dict[str, Any]]] = None
    max_enrollment: Optional[int] = Field(None, ge=1)
    certification_provided: bool = False
    certifying_body: Optional[str] = None


class ValueAddedCourseUpdate(BaseModel):
    """Schema for updating value-added course"""
    course_name: Optional[str] = None
    course_type: Optional[CourseType] = None
    course_mode: Optional[CourseMode] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    outcomes: Optional[List[str]] = None
    duration_hours: Optional[int] = None
    credits: Optional[float] = None
    co_po_mapping: Optional[Dict[str, Dict[str, int]]] = None
    instructor_name: Optional[str] = None
    instructor_qualification: Optional[str] = None
    instructor_organization: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    schedule: Optional[List[Dict[str, Any]]] = None
    max_enrollment: Optional[int] = None
    certification_provided: Optional[bool] = None
    certifying_body: Optional[str] = None
    is_active: Optional[bool] = None


class CourseEnrollmentCreate(BaseModel):
    """Schema for enrolling students in value-added course"""
    student_id: str = Field(..., min_length=1)
    student_name: str = Field(..., min_length=1)
    student_email: Optional[str] = None
    department: Optional[str] = None
    batch: Optional[str] = None
    enrollment_date: date


class CourseEnrollmentUpdate(BaseModel):
    """Schema for updating enrollment"""
    status: Optional[str] = Field(None, pattern=r"^(enrolled|completed|dropped)$")
    completion_date: Optional[date] = None
    grade: Optional[str] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    certificate_issued: Optional[bool] = None


class CourseEnrollmentResponse(BaseModel):
    """Schema for enrollment response"""
    id: str
    course_id: str
    student_id: str
    student_name: str
    student_email: Optional[str]
    department: Optional[str]
    batch: Optional[str]
    enrollment_date: date
    status: str
    completion_date: Optional[date]
    grade: Optional[str]
    score: Optional[float]
    certificate_issued: bool
    certificate_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ValueAddedCourseResponse(BaseModel):
    """Schema for value-added course response"""
    id: str
    course_name: str
    course_code: Optional[str]
    course_type: str
    course_mode: str
    department: str
    academic_year: str
    semester: Optional[int]
    description: Optional[str]
    objectives: Optional[List[str]]
    outcomes: Optional[List[str]]
    duration_hours: int
    credits: Optional[float]
    co_po_mapping: Optional[Dict[str, Dict[str, int]]]
    instructor_name: Optional[str]
    instructor_qualification: Optional[str]
    instructor_organization: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    schedule: Optional[List[Dict[str, Any]]]
    max_enrollment: Optional[int]
    current_enrollment: int
    completed_count: int
    certification_provided: bool
    certifying_body: Optional[str]
    syllabus_path: Optional[str]
    materials_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    enrollments: Optional[List[CourseEnrollmentResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class ValueAddedCourseListResponse(BaseModel):
    """Schema for paginated course list"""
    items: List[ValueAddedCourseResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None


# ==================== INTERNSHIP SCHEMAS ====================

class InternshipCreate(BaseModel):
    """Schema for creating internship record"""
    student_id: str = Field(..., min_length=1)
    student_name: str = Field(..., min_length=1)
    student_email: Optional[str] = None
    department: str = Field(..., min_length=1)
    batch: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=8)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    internship_type: InternshipType
    company_name: str = Field(..., min_length=1)
    company_website: Optional[str] = None
    industry_sector: Optional[str] = None
    location: Optional[str] = None
    is_remote: bool = False
    start_date: date
    end_date: Optional[date] = None
    duration_weeks: Optional[int] = Field(None, ge=1)
    role_title: Optional[str] = None
    project_title: Optional[str] = None
    project_description: Optional[str] = None
    skills_used: Optional[List[str]] = None
    company_mentor: Optional[str] = None
    faculty_mentor: Optional[str] = None
    is_paid: bool = False
    stipend_amount: Optional[float] = Field(None, ge=0)
    stipend_currency: str = "INR"


class InternshipUpdate(BaseModel):
    """Schema for updating internship"""
    end_date: Optional[date] = None
    duration_weeks: Optional[int] = None
    role_title: Optional[str] = None
    project_title: Optional[str] = None
    project_description: Optional[str] = None
    skills_used: Optional[List[str]] = None
    company_mentor: Optional[str] = None
    faculty_mentor: Optional[str] = None
    status: Optional[InternshipStatus] = None
    ppo_offered: Optional[bool] = None
    converted_to_job: Optional[bool] = None
    performance_rating: Optional[float] = Field(None, ge=1, le=10)
    feedback: Optional[str] = None


class InternshipResponse(BaseModel):
    """Schema for internship response"""
    id: str
    student_id: str
    student_name: str
    student_email: Optional[str]
    department: str
    batch: Optional[str]
    semester: Optional[int]
    academic_year: str
    internship_type: str
    company_name: str
    company_website: Optional[str]
    industry_sector: Optional[str]
    location: Optional[str]
    is_remote: bool
    start_date: date
    end_date: Optional[date]
    duration_weeks: Optional[int]
    role_title: Optional[str]
    project_title: Optional[str]
    project_description: Optional[str]
    skills_used: Optional[List[str]]
    company_mentor: Optional[str]
    faculty_mentor: Optional[str]
    is_paid: bool
    stipend_amount: Optional[float]
    stipend_currency: str
    status: str
    ppo_offered: bool
    converted_to_job: bool
    performance_rating: Optional[float]
    feedback: Optional[str]
    offer_letter_path: Optional[str]
    completion_certificate_path: Optional[str]
    report_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InternshipListResponse(BaseModel):
    """Schema for paginated internship list"""
    items: List[InternshipResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None
    by_status: Optional[Dict[str, int]] = None


class InternshipAnalytics(BaseModel):
    """Schema for internship analytics"""
    total_internships: int
    ongoing: int
    completed: int
    by_type: Dict[str, int]
    by_department: Dict[str, int]
    by_industry_sector: Dict[str, int]
    paid_internships: int
    ppo_offered: int
    converted_to_jobs: int
    average_duration_weeks: float
    average_stipend: Optional[float]
    top_companies: List[Dict[str, Any]]


# ==================== DASHBOARD & REPORT SCHEMAS ====================

class Criterion1DashboardStats(BaseModel):
    """Dashboard statistics for Criterion 1"""
    # Key Indicator 1.1: Curriculum design
    curriculum_revisions: int
    board_meetings: int
    industry_expert_inputs: int

    # Key Indicator 1.2: Academic flexibility
    elective_courses: int
    interdisciplinary_programs: int

    # Key Indicator 1.3: Value-added courses
    value_added_courses: int
    total_enrollments: int
    certifications_issued: int
    internships_total: int
    internships_ongoing: int

    # Key Indicator 1.4: Feedback
    total_feedback: int
    feedback_by_type: Dict[str, int]
    action_taken_percentage: float

    # Evidence tracking
    total_evidence: int
    verified_evidence: int
    evidence_by_indicator: Dict[str, int]

    # Industry partnerships
    active_mous: int
    total_partners: int
    students_benefited: int

    # Overall readiness
    completion_percentage: float
    pending_items: List[Dict[str, Any]]


class Criterion1ReportRequest(BaseModel):
    """Request schema for generating Criterion 1 report"""
    institution_name: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    include_sections: Optional[List[str]] = None  # ["1.1", "1.2", "1.3", "1.4"]
    format: str = Field(default="docx", pattern=r"^(docx|pdf)$")
    include_evidence_list: bool = True
    include_analytics: bool = True


class Criterion1ReportResponse(BaseModel):
    """Response schema for generated report"""
    success: bool
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    sections_included: List[str]
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
