"""
NAAC Criterion 6: Governance, Leadership and Management - Pydantic Schemas

This module defines request/response schemas for Criterion 6 API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== ENUMS ====================

class MeetingType(str, Enum):
    GOVERNING_BODY = "governing_body"
    ACADEMIC_COUNCIL = "academic_council"
    BOARD_OF_STUDIES = "board_of_studies"
    FINANCE_COMMITTEE = "finance_committee"
    IQAC = "iqac"
    DEPARTMENT = "department"
    FACULTY = "faculty"
    CDC = "cdc"
    EXAMINATION = "examination"
    GRIEVANCE = "grievance"
    OTHER = "other"


class PolicyType(str, Enum):
    ACADEMIC = "academic"
    ADMINISTRATIVE = "administrative"
    HR = "hr"
    FINANCIAL = "financial"
    STUDENT = "student"
    RESEARCH = "research"
    IT = "it"
    SAFETY = "safety"
    ENVIRONMENT = "environment"
    ETHICS = "ethics"
    OTHER = "other"


class QualityInitiativeType(str, Enum):
    AQAR = "aqar"
    IIQA = "iiqa"
    SSR = "ssr"
    NAAC_VISIT = "naac_visit"
    NBA_VISIT = "nba_visit"
    ISO_AUDIT = "iso_audit"
    NIRF = "nirf"
    ACADEMIC_AUDIT = "academic_audit"
    FEEDBACK_ANALYSIS = "feedback_analysis"
    CURRICULUM_REVIEW = "curriculum_review"
    OTHER = "other"


class FDPType(str, Enum):
    WORKSHOP = "workshop"
    SEMINAR = "seminar"
    CONFERENCE = "conference"
    FDP = "fdp"
    STTP = "sttp"
    ONLINE_COURSE = "online_course"
    CERTIFICATION = "certification"
    INDUSTRIAL_TRAINING = "industrial_training"
    SABBATICAL = "sabbatical"
    OTHER = "other"


class AuditType(str, Enum):
    STATUTORY = "statutory"
    INTERNAL = "internal"
    EXTERNAL = "external"
    CAG = "cag"
    ISO = "iso"
    ACADEMIC = "academic"
    OTHER = "other"


# ==================== INSTITUTIONAL GOVERNANCE SCHEMAS ====================

class InstitutionalGovernanceCreate(BaseModel):
    """Schema for creating institutional governance record"""
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    vision_statement: Optional[str] = None
    mission_statement: Optional[str] = None
    core_values: Optional[List[str]] = None
    quality_policy: Optional[str] = None
    organogram_path: Optional[str] = None
    governance_committees: Optional[List[Dict[str, Any]]] = None


class InstitutionalGovernanceUpdate(BaseModel):
    """Schema for updating institutional governance"""
    vision_statement: Optional[str] = None
    mission_statement: Optional[str] = None
    core_values: Optional[List[str]] = None
    quality_policy: Optional[str] = None
    leadership_details: Optional[Dict[str, Any]] = None
    governance_committees: Optional[List[Dict[str, Any]]] = None
    e_governance_modules: Optional[List[str]] = None
    decentralization_practices: Optional[List[str]] = None
    participative_management: Optional[List[str]] = None


class InstitutionalGovernanceResponse(BaseModel):
    """Schema for institutional governance response"""
    id: str
    academic_year: str
    vision_statement: Optional[str]
    mission_statement: Optional[str]
    core_values: Optional[List[str]]
    quality_policy: Optional[str]
    leadership_details: Optional[Dict[str, Any]]
    governance_committees: Optional[List[Dict[str, Any]]]
    organogram_path: Optional[str]
    e_governance_modules: Optional[List[str]]
    decentralization_practices: Optional[List[str]]
    participative_management: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ==================== GOVERNANCE MEETING SCHEMAS ====================

class GovernanceMeetingCreate(BaseModel):
    """Schema for creating governance meeting"""
    meeting_type: MeetingType
    title: str = Field(..., min_length=1, max_length=500)
    meeting_number: Optional[str] = None
    meeting_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue: Optional[str] = None
    mode: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    chairperson: Optional[str] = None
    convener: Optional[str] = None


class GovernanceMeetingUpdate(BaseModel):
    """Schema for updating governance meeting"""
    agenda_items: Optional[List[str]] = None
    attendees: Optional[List[Dict[str, str]]] = None
    members_present: Optional[int] = None
    members_absent: Optional[int] = None
    decisions_taken: Optional[List[str]] = None
    action_items: Optional[List[Dict[str, Any]]] = None


class GovernanceMeetingResponse(BaseModel):
    """Schema for governance meeting response"""
    id: str
    meeting_type: str
    title: str
    meeting_number: Optional[str]
    meeting_date: date
    start_time: Optional[str]
    end_time: Optional[str]
    venue: Optional[str]
    mode: Optional[str]
    academic_year: str
    chairperson: Optional[str]
    convener: Optional[str]
    agenda_items: Optional[List[str]]
    attendees: Optional[List[Dict[str, str]]]
    members_present: int
    members_absent: int
    decisions_taken: Optional[List[str]]
    action_items: Optional[List[Dict[str, Any]]]
    notice_path: Optional[str]
    agenda_path: Optional[str]
    minutes_path: Optional[str]
    attendance_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class GovernanceMeetingListResponse(BaseModel):
    """Schema for paginated governance meeting list"""
    items: List[GovernanceMeetingResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None


# ==================== INSTITUTIONAL POLICY SCHEMAS ====================

class InstitutionalPolicyCreate(BaseModel):
    """Schema for creating institutional policy"""
    policy_name: str = Field(..., min_length=1, max_length=500)
    policy_type: PolicyType
    policy_number: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    scope: Optional[str] = None
    effective_date: Optional[date] = None
    approved_by: Optional[str] = None
    approval_date: Optional[date] = None


class InstitutionalPolicyUpdate(BaseModel):
    """Schema for updating institutional policy"""
    description: Optional[str] = None
    key_provisions: Optional[List[str]] = None
    implementation_guidelines: Optional[str] = None
    responsible_authority: Optional[str] = None
    review_frequency: Optional[str] = None
    last_reviewed_date: Optional[date] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None


class InstitutionalPolicyResponse(BaseModel):
    """Schema for institutional policy response"""
    id: str
    policy_name: str
    policy_type: str
    policy_number: Optional[str]
    description: Optional[str]
    objectives: Optional[List[str]]
    scope: Optional[str]
    key_provisions: Optional[List[str]]
    implementation_guidelines: Optional[str]
    responsible_authority: Optional[str]
    effective_date: Optional[date]
    approved_by: Optional[str]
    approval_date: Optional[date]
    review_frequency: Optional[str]
    last_reviewed_date: Optional[date]
    version: Optional[str]
    policy_document_path: Optional[str]
    approval_document_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InstitutionalPolicyListResponse(BaseModel):
    """Schema for paginated institutional policy list"""
    items: List[InstitutionalPolicyResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None


# ==================== IQAC ACTIVITY SCHEMAS ====================

class IQACActivityCreate(BaseModel):
    """Schema for creating IQAC activity"""
    activity_name: str = Field(..., min_length=1, max_length=500)
    activity_type: QualityInitiativeType
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    start_date: date
    end_date: Optional[date] = None
    coordinator: Optional[str] = None
    committee_members: Optional[List[Dict[str, str]]] = None


class IQACActivityUpdate(BaseModel):
    """Schema for updating IQAC activity"""
    key_initiatives: Optional[List[str]] = None
    outcomes: Optional[List[str]] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None
    implementation_status: Optional[str] = None
    is_completed: Optional[bool] = None


class IQACActivityResponse(BaseModel):
    """Schema for IQAC activity response"""
    id: str
    activity_name: str
    activity_type: str
    description: Optional[str]
    objectives: Optional[List[str]]
    academic_year: str
    start_date: date
    end_date: Optional[date]
    coordinator: Optional[str]
    committee_members: Optional[List[Dict[str, str]]]
    key_initiatives: Optional[List[str]]
    outcomes: Optional[List[str]]
    action_items: Optional[List[Dict[str, Any]]]
    recommendations: Optional[List[str]]
    implementation_status: Optional[str]
    report_path: Optional[str]
    evidence_path: Optional[str]
    is_completed: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class IQACActivityListResponse(BaseModel):
    """Schema for paginated IQAC activity list"""
    items: List[IQACActivityResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None
    completed_count: Optional[int] = None


# ==================== FACULTY DEVELOPMENT SCHEMAS ====================

class FacultyDevelopmentCreate(BaseModel):
    """Schema for creating faculty development record"""
    faculty_name: str = Field(..., min_length=1, max_length=255)
    faculty_id: Optional[str] = None
    faculty_email: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    designation: Optional[str] = None
    program_type: FDPType
    program_name: str = Field(..., min_length=1, max_length=500)
    organizing_body: Optional[str] = None
    venue: Optional[str] = None
    mode: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    duration_days: Optional[int] = Field(None, ge=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")


class FacultyDevelopmentUpdate(BaseModel):
    """Schema for updating faculty development"""
    topics_covered: Optional[List[str]] = None
    skills_acquired: Optional[List[str]] = None
    is_sponsored: Optional[bool] = None
    sponsorship_amount: Optional[float] = None
    certificate_received: Optional[bool] = None
    certificate_path: Optional[str] = None


class FacultyDevelopmentResponse(BaseModel):
    """Schema for faculty development response"""
    id: str
    faculty_name: str
    faculty_id: Optional[str]
    faculty_email: Optional[str]
    department: str
    designation: Optional[str]
    program_type: str
    program_name: str
    organizing_body: Optional[str]
    venue: Optional[str]
    mode: Optional[str]
    start_date: date
    end_date: Optional[date]
    duration_days: Optional[int]
    academic_year: str
    topics_covered: Optional[List[str]]
    skills_acquired: Optional[List[str]]
    is_sponsored: bool
    sponsorship_amount: Optional[float]
    certificate_received: bool
    certificate_path: Optional[str]
    report_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class FacultyDevelopmentListResponse(BaseModel):
    """Schema for paginated faculty development list"""
    items: List[FacultyDevelopmentResponse]
    total: int
    page: int
    page_size: int
    total_programs: Optional[int] = None
    by_type: Optional[Dict[str, int]] = None
    by_department: Optional[Dict[str, int]] = None


# ==================== FINANCIAL AUDIT SCHEMAS ====================

class FinancialAuditCreate(BaseModel):
    """Schema for creating financial audit record"""
    audit_type: AuditType
    audit_name: str = Field(..., min_length=1, max_length=255)
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    auditor_name: Optional[str] = None
    auditor_firm: Optional[str] = None
    audit_start_date: Optional[date] = None
    audit_end_date: Optional[date] = None


class FinancialAuditUpdate(BaseModel):
    """Schema for updating financial audit"""
    total_income: Optional[float] = None
    total_expenditure: Optional[float] = None
    surplus_deficit: Optional[float] = None
    audit_observations: Optional[List[str]] = None
    compliance_status: Optional[str] = None
    action_taken: Optional[List[str]] = None
    is_completed: Optional[bool] = None


class FinancialAuditResponse(BaseModel):
    """Schema for financial audit response"""
    id: str
    audit_type: str
    audit_name: str
    financial_year: str
    auditor_name: Optional[str]
    auditor_firm: Optional[str]
    audit_start_date: Optional[date]
    audit_end_date: Optional[date]
    total_income: Optional[float]
    total_expenditure: Optional[float]
    surplus_deficit: Optional[float]
    audit_observations: Optional[List[str]]
    compliance_status: Optional[str]
    action_taken: Optional[List[str]]
    audit_report_path: Optional[str]
    financial_statements_path: Optional[str]
    utilization_certificate_path: Optional[str]
    is_completed: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class FinancialAuditListResponse(BaseModel):
    """Schema for paginated financial audit list"""
    items: List[FinancialAuditResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None


# ==================== STRATEGIC PLAN SCHEMAS ====================

class StrategicPlanCreate(BaseModel):
    """Schema for creating strategic plan"""
    plan_name: str = Field(..., min_length=1, max_length=500)
    plan_period: str = Field(..., min_length=1, max_length=50)
    start_year: int = Field(..., ge=2000, le=2100)
    end_year: int = Field(..., ge=2000, le=2100)
    vision_2030: Optional[str] = None
    mission_goals: Optional[List[str]] = None
    strategic_objectives: Optional[List[Dict[str, Any]]] = None


class StrategicPlanUpdate(BaseModel):
    """Schema for updating strategic plan"""
    key_initiatives: Optional[List[Dict[str, Any]]] = None
    kpis: Optional[List[Dict[str, Any]]] = None
    resource_allocation: Optional[Dict[str, float]] = None
    implementation_progress: Optional[float] = None
    milestones_achieved: Optional[List[Dict[str, Any]]] = None
    challenges: Optional[List[str]] = None
    is_active: Optional[bool] = None


class StrategicPlanResponse(BaseModel):
    """Schema for strategic plan response"""
    id: str
    plan_name: str
    plan_period: str
    start_year: int
    end_year: int
    vision_2030: Optional[str]
    mission_goals: Optional[List[str]]
    strategic_objectives: Optional[List[Dict[str, Any]]]
    key_initiatives: Optional[List[Dict[str, Any]]]
    kpis: Optional[List[Dict[str, Any]]]
    resource_allocation: Optional[Dict[str, float]]
    implementation_progress: Optional[float]
    milestones_achieved: Optional[List[Dict[str, Any]]]
    challenges: Optional[List[str]]
    plan_document_path: Optional[str]
    progress_report_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StrategicPlanListResponse(BaseModel):
    """Schema for paginated strategic plan list"""
    items: List[StrategicPlanResponse]
    total: int
    page: int
    page_size: int


# ==================== DASHBOARD & REPORT SCHEMAS ====================

class Criterion6DashboardStats(BaseModel):
    """Dashboard statistics for Criterion 6"""
    # Key Indicator 6.1: Vision and Leadership
    vision_mission_defined: bool
    governance_committees_count: int
    e_governance_modules: int
    decentralization_practices: int

    # Key Indicator 6.2: Strategy Development
    strategic_plan_active: bool
    implementation_progress: float
    kpis_defined: int
    milestones_achieved: int

    # Key Indicator 6.3: Faculty Empowerment
    fdp_conducted: int
    faculty_trained: int
    average_training_days: float
    certifications_received: int

    # Key Indicator 6.4: Financial Management
    audits_completed: int
    total_income: float
    total_expenditure: float
    utilization_percentage: float

    # Key Indicator 6.5: Quality Assurance
    iqac_meetings: int
    quality_initiatives: int
    aqar_submitted: bool
    academic_audits: int

    # Governance Meetings
    governing_body_meetings: int
    academic_council_meetings: int
    bos_meetings: int
    total_policies: int

    # Overall readiness
    completion_percentage: float
    pending_items: List[Dict[str, Any]]


class Criterion6ReportRequest(BaseModel):
    """Request schema for generating Criterion 6 report"""
    institution_name: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    include_sections: Optional[List[str]] = None
    format: str = Field(default="docx", pattern=r"^(docx|pdf)$")
    include_analytics: bool = True


class Criterion6ReportResponse(BaseModel):
    """Response schema for generated report"""
    success: bool
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    sections_included: List[str]
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
