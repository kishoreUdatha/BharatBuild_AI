"""
NAAC Criterion 5: Student Support and Progression - Pydantic Schemas

This module defines request/response schemas for Criterion 5 API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== ENUMS ====================

class ScholarshipType(str, Enum):
    GOVERNMENT = "government"
    INSTITUTIONAL = "institutional"
    PRIVATE = "private"
    CORPORATE = "corporate"
    MERIT = "merit"
    NEED_BASED = "need_based"
    SC_ST = "sc_st"
    OBC = "obc"
    MINORITY = "minority"
    SPORTS = "sports"
    OTHER = "other"


class PlacementStatus(str, Enum):
    PLACED = "placed"
    HIGHER_STUDIES = "higher_studies"
    ENTREPRENEUR = "entrepreneur"
    UNPLACED = "unplaced"
    NOT_INTERESTED = "not_interested"


class CompanyType(str, Enum):
    MNC = "mnc"
    STARTUP = "startup"
    PSU = "psu"
    GOVERNMENT = "government"
    PRIVATE = "private"
    DREAM = "dream"
    SUPER_DREAM = "super_dream"


class GrievanceCategory(str, Enum):
    ACADEMIC = "academic"
    HOSTEL = "hostel"
    TRANSPORTATION = "transportation"
    RAGGING = "ragging"
    HARASSMENT = "harassment"
    FINANCIAL = "financial"
    INFRASTRUCTURE = "infrastructure"
    FACULTY = "faculty"
    EXAMINATION = "examination"
    OTHER = "other"


class GrievanceStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class AlumniStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


# ==================== SCHOLARSHIP SCHEMAS ====================

class ScholarshipCreate(BaseModel):
    """Schema for creating scholarship record"""
    scholarship_name: str = Field(..., min_length=1, max_length=500)
    scholarship_type: ScholarshipType
    awarding_body: str = Field(..., min_length=1, max_length=255)
    student_name: str = Field(..., min_length=1, max_length=255)
    student_usn: str = Field(..., min_length=1, max_length=50)
    department: str = Field(..., min_length=1, max_length=255)
    semester: Optional[int] = Field(None, ge=1, le=8)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    amount: float = Field(..., gt=0)
    application_date: Optional[date] = None
    sanction_date: Optional[date] = None


class ScholarshipUpdate(BaseModel):
    """Schema for updating scholarship record"""
    amount: Optional[float] = None
    amount_received: Optional[float] = None
    disbursement_date: Optional[date] = None
    is_disbursed: Optional[bool] = None
    bank_details: Optional[Dict[str, str]] = None
    remarks: Optional[str] = None


class ScholarshipResponse(BaseModel):
    """Schema for scholarship response"""
    id: str
    scholarship_name: str
    scholarship_type: str
    awarding_body: str
    student_name: str
    student_usn: str
    department: str
    semester: Optional[int]
    academic_year: str
    amount: float
    amount_received: Optional[float]
    application_date: Optional[date]
    sanction_date: Optional[date]
    disbursement_date: Optional[date]
    is_disbursed: bool
    bank_details: Optional[Dict[str, str]]
    sanction_letter_path: Optional[str]
    receipt_path: Optional[str]
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ScholarshipListResponse(BaseModel):
    """Schema for paginated scholarship list"""
    items: List[ScholarshipResponse]
    total: int
    page: int
    page_size: int
    total_amount: Optional[float] = None
    by_type: Optional[Dict[str, int]] = None
    by_department: Optional[Dict[str, int]] = None


# ==================== PLACEMENT SCHEMAS ====================

class PlacementRecordCreate(BaseModel):
    """Schema for creating placement record"""
    student_name: str = Field(..., min_length=1, max_length=255)
    student_usn: str = Field(..., min_length=1, max_length=50)
    student_email: Optional[str] = None
    student_phone: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    batch: str = Field(..., min_length=1, max_length=50)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    status: PlacementStatus
    company_name: Optional[str] = None
    company_type: Optional[CompanyType] = None
    job_role: Optional[str] = None
    job_location: Optional[str] = None
    package_lpa: Optional[float] = Field(None, ge=0)
    offer_date: Optional[date] = None
    joining_date: Optional[date] = None
    higher_study_institution: Optional[str] = None
    higher_study_course: Optional[str] = None
    higher_study_country: Optional[str] = None
    startup_name: Optional[str] = None
    startup_domain: Optional[str] = None


class PlacementRecordUpdate(BaseModel):
    """Schema for updating placement record"""
    status: Optional[PlacementStatus] = None
    company_name: Optional[str] = None
    job_role: Optional[str] = None
    package_lpa: Optional[float] = None
    joining_date: Optional[date] = None
    is_verified: Optional[bool] = None
    verified_by: Optional[str] = None
    remarks: Optional[str] = None


class PlacementRecordResponse(BaseModel):
    """Schema for placement record response"""
    id: str
    student_name: str
    student_usn: str
    student_email: Optional[str]
    student_phone: Optional[str]
    department: str
    batch: str
    academic_year: str
    status: str
    company_name: Optional[str]
    company_type: Optional[str]
    job_role: Optional[str]
    job_location: Optional[str]
    package_lpa: Optional[float]
    offer_date: Optional[date]
    joining_date: Optional[date]
    higher_study_institution: Optional[str]
    higher_study_course: Optional[str]
    higher_study_country: Optional[str]
    startup_name: Optional[str]
    startup_domain: Optional[str]
    offer_letter_path: Optional[str]
    joining_letter_path: Optional[str]
    is_verified: bool
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PlacementListResponse(BaseModel):
    """Schema for paginated placement list"""
    items: List[PlacementRecordResponse]
    total: int
    page: int
    page_size: int
    placement_percentage: Optional[float] = None
    average_package: Optional[float] = None
    highest_package: Optional[float] = None
    by_status: Optional[Dict[str, int]] = None
    by_company_type: Optional[Dict[str, int]] = None


# ==================== CAREER COUNSELING SCHEMAS ====================

class CareerCounselingCreate(BaseModel):
    """Schema for creating career counseling session"""
    session_type: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    session_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_hours: Optional[float] = Field(None, gt=0)
    venue: Optional[str] = None
    mode: Optional[str] = None
    department: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    target_audience: Optional[str] = None
    resource_person: Optional[str] = None
    resource_person_designation: Optional[str] = None
    resource_person_organization: Optional[str] = None
    topics_covered: Optional[List[str]] = None


class CareerCounselingUpdate(BaseModel):
    """Schema for updating career counseling session"""
    students_attended: Optional[int] = None
    feedback_received: Optional[int] = None
    average_rating: Optional[float] = None
    outcomes: Optional[List[str]] = None
    remarks: Optional[str] = None


class CareerCounselingResponse(BaseModel):
    """Schema for career counseling response"""
    id: str
    session_type: str
    title: str
    description: Optional[str]
    session_date: date
    start_time: Optional[str]
    end_time: Optional[str]
    duration_hours: Optional[float]
    venue: Optional[str]
    mode: Optional[str]
    department: Optional[str]
    academic_year: str
    target_audience: Optional[str]
    resource_person: Optional[str]
    resource_person_designation: Optional[str]
    resource_person_organization: Optional[str]
    topics_covered: Optional[List[str]]
    students_attended: int
    feedback_received: int
    average_rating: Optional[float]
    outcomes: Optional[List[str]]
    brochure_path: Optional[str]
    attendance_path: Optional[str]
    report_path: Optional[str]
    photos_path: Optional[str]
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CareerCounselingListResponse(BaseModel):
    """Schema for paginated career counseling list"""
    items: List[CareerCounselingResponse]
    total: int
    page: int
    page_size: int
    total_students: Optional[int] = None
    by_type: Optional[Dict[str, int]] = None


# ==================== STUDENT GRIEVANCE SCHEMAS ====================

class StudentGrievanceCreate(BaseModel):
    """Schema for creating student grievance"""
    student_name: str = Field(..., min_length=1, max_length=255)
    student_usn: Optional[str] = None
    student_email: Optional[str] = None
    student_phone: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    semester: Optional[int] = Field(None, ge=1, le=8)
    category: GrievanceCategory
    subject: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=10)
    is_anonymous: bool = False


class StudentGrievanceUpdate(BaseModel):
    """Schema for updating student grievance"""
    status: Optional[GrievanceStatus] = None
    assigned_to: Optional[str] = None
    action_taken: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_date: Optional[date] = None
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)


class StudentGrievanceResponse(BaseModel):
    """Schema for student grievance response"""
    id: str
    grievance_number: str
    student_name: str
    student_usn: Optional[str]
    student_email: Optional[str]
    student_phone: Optional[str]
    department: str
    semester: Optional[int]
    category: str
    subject: str
    description: str
    is_anonymous: bool
    status: str
    submitted_date: date
    assigned_to: Optional[str]
    assigned_date: Optional[date]
    action_taken: Optional[str]
    resolution_notes: Optional[str]
    resolved_date: Optional[date]
    resolution_days: Optional[int]
    satisfaction_rating: Optional[int]
    attachment_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StudentGrievanceListResponse(BaseModel):
    """Schema for paginated student grievance list"""
    items: List[StudentGrievanceResponse]
    total: int
    page: int
    page_size: int
    by_status: Optional[Dict[str, int]] = None
    by_category: Optional[Dict[str, int]] = None
    average_resolution_days: Optional[float] = None


# ==================== ALUMNI SCHEMAS ====================

class AlumniRecordCreate(BaseModel):
    """Schema for creating alumni record"""
    name: str = Field(..., min_length=1, max_length=255)
    usn: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    batch: str = Field(..., min_length=1, max_length=50)
    graduation_year: int = Field(..., ge=1900, le=2100)
    degree: Optional[str] = None
    current_organization: Optional[str] = None
    current_designation: Optional[str] = None
    current_location: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry_sector: Optional[str] = None


class AlumniRecordUpdate(BaseModel):
    """Schema for updating alumni record"""
    email: Optional[str] = None
    phone: Optional[str] = None
    current_organization: Optional[str] = None
    current_designation: Optional[str] = None
    current_location: Optional[str] = None
    linkedin_url: Optional[str] = None
    experience_years: Optional[int] = None
    is_entrepreneur: Optional[bool] = None
    company_founded: Optional[str] = None
    achievements: Optional[List[Dict[str, Any]]] = None
    contributions_to_institution: Optional[List[Dict[str, Any]]] = None
    is_donor: Optional[bool] = None
    donation_amount: Optional[float] = None
    status: Optional[AlumniStatus] = None
    is_active: Optional[bool] = None


class AlumniRecordResponse(BaseModel):
    """Schema for alumni record response"""
    id: str
    name: str
    usn: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    department: str
    batch: str
    graduation_year: int
    degree: Optional[str]
    current_organization: Optional[str]
    current_designation: Optional[str]
    current_location: Optional[str]
    linkedin_url: Optional[str]
    industry_sector: Optional[str]
    experience_years: Optional[int]
    is_entrepreneur: bool
    company_founded: Optional[str]
    achievements: Optional[List[Dict[str, Any]]]
    contributions_to_institution: Optional[List[Dict[str, Any]]]
    is_donor: bool
    donation_amount: Optional[float]
    profile_photo_path: Optional[str]
    status: str
    is_active: bool
    last_updated: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class AlumniListResponse(BaseModel):
    """Schema for paginated alumni list"""
    items: List[AlumniRecordResponse]
    total: int
    page: int
    page_size: int
    by_batch: Optional[Dict[str, int]] = None
    by_industry: Optional[Dict[str, int]] = None
    entrepreneurs_count: Optional[int] = None


# ==================== STUDENT MENTORING SCHEMAS ====================

class StudentMentoringCreate(BaseModel):
    """Schema for creating student mentoring record"""
    mentor_name: str = Field(..., min_length=1, max_length=255)
    mentor_designation: Optional[str] = None
    mentor_email: Optional[str] = None
    mentor_department: str = Field(..., min_length=1, max_length=255)
    student_name: str = Field(..., min_length=1, max_length=255)
    student_usn: str = Field(..., min_length=1, max_length=50)
    student_email: Optional[str] = None
    student_department: str = Field(..., min_length=1, max_length=255)
    semester: Optional[int] = Field(None, ge=1, le=8)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")


class MentoringSessionCreate(BaseModel):
    """Schema for creating mentoring session"""
    mentoring_id: str
    session_date: date
    session_type: Optional[str] = None
    topics_discussed: Optional[List[str]] = None
    issues_identified: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    follow_up_required: bool = False
    next_session_date: Optional[date] = None
    remarks: Optional[str] = None


class StudentMentoringUpdate(BaseModel):
    """Schema for updating student mentoring"""
    sessions: Optional[List[Dict[str, Any]]] = None
    total_sessions: Optional[int] = None
    academic_progress: Optional[str] = None
    attendance_percentage: Optional[float] = None
    cgpa: Optional[float] = None
    backlogs: Optional[int] = None
    career_guidance_provided: Optional[bool] = None
    counseling_required: Optional[bool] = None
    parent_interaction: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None


class StudentMentoringResponse(BaseModel):
    """Schema for student mentoring response"""
    id: str
    mentor_name: str
    mentor_designation: Optional[str]
    mentor_email: Optional[str]
    mentor_department: str
    student_name: str
    student_usn: str
    student_email: Optional[str]
    student_department: str
    semester: Optional[int]
    academic_year: str
    sessions: Optional[List[Dict[str, Any]]]
    total_sessions: int
    academic_progress: Optional[str]
    attendance_percentage: Optional[float]
    cgpa: Optional[float]
    backlogs: Optional[int]
    career_guidance_provided: bool
    counseling_required: bool
    parent_interaction: Optional[List[Dict[str, Any]]]
    mentoring_report_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StudentMentoringListResponse(BaseModel):
    """Schema for paginated student mentoring list"""
    items: List[StudentMentoringResponse]
    total: int
    page: int
    page_size: int
    total_sessions: Optional[int] = None
    by_mentor: Optional[Dict[str, int]] = None


# ==================== COMPETITIVE EXAM SCHEMAS ====================

class CompetitiveExamCreate(BaseModel):
    """Schema for creating competitive exam record"""
    student_name: str = Field(..., min_length=1, max_length=255)
    student_usn: str = Field(..., min_length=1, max_length=50)
    student_email: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    batch: str = Field(..., min_length=1, max_length=50)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    exam_name: str = Field(..., min_length=1, max_length=255)
    exam_type: Optional[str] = None
    exam_date: Optional[date] = None
    registration_number: Optional[str] = None


class CompetitiveExamUpdate(BaseModel):
    """Schema for updating competitive exam record"""
    result_status: Optional[str] = None
    score: Optional[float] = None
    percentile: Optional[float] = None
    rank: Optional[int] = None
    is_qualified: Optional[bool] = None
    admission_secured: Optional[bool] = None
    institution_admitted: Optional[str] = None
    course_admitted: Optional[str] = None


class CompetitiveExamResponse(BaseModel):
    """Schema for competitive exam response"""
    id: str
    student_name: str
    student_usn: str
    student_email: Optional[str]
    department: str
    batch: str
    academic_year: str
    exam_name: str
    exam_type: Optional[str]
    exam_date: Optional[date]
    registration_number: Optional[str]
    result_status: Optional[str]
    score: Optional[float]
    percentile: Optional[float]
    rank: Optional[int]
    is_qualified: bool
    admission_secured: bool
    institution_admitted: Optional[str]
    course_admitted: Optional[str]
    scorecard_path: Optional[str]
    admit_card_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CompetitiveExamListResponse(BaseModel):
    """Schema for paginated competitive exam list"""
    items: List[CompetitiveExamResponse]
    total: int
    page: int
    page_size: int
    qualified_count: Optional[int] = None
    by_exam: Optional[Dict[str, int]] = None


# ==================== DASHBOARD & REPORT SCHEMAS ====================

class Criterion5DashboardStats(BaseModel):
    """Dashboard statistics for Criterion 5"""
    # Key Indicator 5.1: Student Support
    total_scholarships: int
    total_scholarship_amount: float
    scholarships_by_type: Dict[str, int]
    beneficiary_students: int

    # Key Indicator 5.2: Student Progression
    placement_percentage: float
    average_package: float
    highest_package: float
    students_in_higher_studies: int
    students_qualified_competitive_exams: int
    students_placed: int

    # Key Indicator 5.3: Student Participation
    career_counseling_sessions: int
    students_attended_counseling: int
    mentoring_sessions: int
    students_under_mentoring: int

    # Key Indicator 5.4: Alumni Engagement
    total_alumni: int
    active_alumni: int
    alumni_contributions: int
    alumni_donors: int
    total_donations: float

    # Grievance Redressal
    total_grievances: int
    resolved_grievances: int
    average_resolution_days: float
    pending_grievances: int

    # Overall readiness
    completion_percentage: float
    pending_items: List[Dict[str, Any]]


class Criterion5ReportRequest(BaseModel):
    """Request schema for generating Criterion 5 report"""
    institution_name: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    department: Optional[str] = None
    include_sections: Optional[List[str]] = None
    format: str = Field(default="docx", pattern=r"^(docx|pdf)$")
    include_analytics: bool = True


class Criterion5ReportResponse(BaseModel):
    """Response schema for generated report"""
    success: bool
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    sections_included: List[str]
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
