"""
NBA (National Board of Accreditation) - Pydantic Schemas

This module defines request/response schemas for NBA accreditation API endpoints.
NBA focuses on program-level accreditation with Outcome Based Education (OBE).
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== ENUMS ====================

class ProgramType(str, Enum):
    UG = "ug"
    PG = "pg"
    DIPLOMA = "diploma"
    PHD = "phd"


class AttainmentLevel(str, Enum):
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    NOT_ATTAINED = "not_attained"


class AssessmentMethod(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"


class FeedbackSource(str, Enum):
    STUDENT = "student"
    ALUMNI = "alumni"
    EMPLOYER = "employer"
    PARENT = "parent"
    FACULTY = "faculty"
    INDUSTRY = "industry"


class ActionStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"


# ==================== PROGRAM VISION MISSION SCHEMAS ====================

class ProgramVisionMissionCreate(BaseModel):
    """Schema for creating program vision/mission"""
    program_name: str = Field(..., min_length=1, max_length=255)
    program_code: str = Field(..., min_length=1, max_length=50)
    program_type: ProgramType
    department: str = Field(..., min_length=1, max_length=255)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    vision_statement: str = Field(..., min_length=10)
    mission_statements: List[str] = Field(..., min_items=1)
    peos: List[Dict[str, str]] = Field(..., min_items=1)


class ProgramVisionMissionUpdate(BaseModel):
    """Schema for updating program vision/mission"""
    vision_statement: Optional[str] = None
    mission_statements: Optional[List[str]] = None
    peos: Optional[List[Dict[str, str]]] = None
    psos: Optional[List[Dict[str, str]]] = None
    peo_pso_mapping: Optional[Dict[str, List[str]]] = None
    stakeholder_consultation: Optional[List[Dict[str, Any]]] = None
    review_history: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None


class ProgramVisionMissionResponse(BaseModel):
    """Schema for program vision/mission response"""
    id: str
    program_name: str
    program_code: str
    program_type: str
    department: str
    academic_year: str
    vision_statement: str
    mission_statements: List[str]
    peos: List[Dict[str, str]]
    psos: Optional[List[Dict[str, str]]]
    peo_pso_mapping: Optional[Dict[str, List[str]]]
    stakeholder_consultation: Optional[List[Dict[str, Any]]]
    review_history: Optional[List[Dict[str, Any]]]
    document_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ProgramVisionMissionListResponse(BaseModel):
    """Schema for paginated program vision/mission list"""
    items: List[ProgramVisionMissionResponse]
    total: int
    page: int
    page_size: int
    by_program_type: Optional[Dict[str, int]] = None


# ==================== PROGRAM OUTCOME SCHEMAS ====================

class ProgramOutcomeCreate(BaseModel):
    """Schema for creating program outcome"""
    program_id: str
    po_number: str = Field(..., pattern=r"^PO\d{1,2}$")
    po_statement: str = Field(..., min_length=10)
    bloom_level: Optional[str] = None
    nba_graduate_attribute: Optional[str] = None


class ProgramOutcomeUpdate(BaseModel):
    """Schema for updating program outcome"""
    po_statement: Optional[str] = None
    bloom_level: Optional[str] = None
    nba_graduate_attribute: Optional[str] = None
    peo_mapping: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ProgramOutcomeResponse(BaseModel):
    """Schema for program outcome response"""
    id: str
    program_id: str
    po_number: str
    po_statement: str
    bloom_level: Optional[str]
    nba_graduate_attribute: Optional[str]
    peo_mapping: Optional[List[str]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ProgramOutcomeListResponse(BaseModel):
    """Schema for paginated program outcome list"""
    items: List[ProgramOutcomeResponse]
    total: int
    page: int
    page_size: int


# ==================== COURSE OUTCOME SCHEMAS ====================

class CourseOutcomeCreate(BaseModel):
    """Schema for creating course outcome"""
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    program_id: str
    semester: int = Field(..., ge=1, le=8)
    co_number: str = Field(..., pattern=r"^CO\d{1,2}$")
    co_statement: str = Field(..., min_length=10)
    bloom_level: str = Field(..., min_length=1, max_length=50)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")


class CourseOutcomeUpdate(BaseModel):
    """Schema for updating course outcome"""
    co_statement: Optional[str] = None
    bloom_level: Optional[str] = None
    po_mapping: Optional[Dict[str, int]] = None
    pso_mapping: Optional[Dict[str, int]] = None
    teaching_methods: Optional[List[str]] = None
    assessment_methods: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CourseOutcomeResponse(BaseModel):
    """Schema for course outcome response"""
    id: str
    course_code: str
    course_name: str
    program_id: str
    semester: int
    co_number: str
    co_statement: str
    bloom_level: str
    academic_year: str
    po_mapping: Optional[Dict[str, int]]
    pso_mapping: Optional[Dict[str, int]]
    teaching_methods: Optional[List[str]]
    assessment_methods: Optional[List[str]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CourseOutcomeListResponse(BaseModel):
    """Schema for paginated course outcome list"""
    items: List[CourseOutcomeResponse]
    total: int
    page: int
    page_size: int
    by_course: Optional[Dict[str, int]] = None


# ==================== CO ATTAINMENT SCHEMAS ====================

class COAttainmentCreate(BaseModel):
    """Schema for creating CO attainment record"""
    course_outcome_id: str
    course_code: str = Field(..., min_length=1, max_length=50)
    co_number: str = Field(..., pattern=r"^CO\d{1,2}$")
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    semester: int = Field(..., ge=1, le=8)
    batch: str = Field(..., min_length=1, max_length=50)
    section: Optional[str] = None


class COAttainmentUpdate(BaseModel):
    """Schema for updating CO attainment"""
    direct_attainment: Optional[float] = Field(None, ge=0, le=100)
    indirect_attainment: Optional[float] = Field(None, ge=0, le=100)
    overall_attainment: Optional[float] = Field(None, ge=0, le=100)
    attainment_level: Optional[AttainmentLevel] = None
    target_attainment: Optional[float] = None
    cie_attainment: Optional[float] = None
    see_attainment: Optional[float] = None
    assignment_attainment: Optional[float] = None
    quiz_attainment: Optional[float] = None
    lab_attainment: Optional[float] = None
    survey_attainment: Optional[float] = None
    students_above_target: Optional[int] = None
    total_students: Optional[int] = None
    gap_analysis: Optional[str] = None
    action_taken: Optional[str] = None


class COAttainmentResponse(BaseModel):
    """Schema for CO attainment response"""
    id: str
    course_outcome_id: str
    course_code: str
    co_number: str
    academic_year: str
    semester: int
    batch: str
    section: Optional[str]
    direct_attainment: Optional[float]
    indirect_attainment: Optional[float]
    overall_attainment: Optional[float]
    attainment_level: Optional[str]
    target_attainment: Optional[float]
    cie_attainment: Optional[float]
    see_attainment: Optional[float]
    assignment_attainment: Optional[float]
    quiz_attainment: Optional[float]
    lab_attainment: Optional[float]
    survey_attainment: Optional[float]
    students_above_target: Optional[int]
    total_students: Optional[int]
    gap_analysis: Optional[str]
    action_taken: Optional[str]
    evidence_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class COAttainmentListResponse(BaseModel):
    """Schema for paginated CO attainment list"""
    items: List[COAttainmentResponse]
    total: int
    page: int
    page_size: int
    average_attainment: Optional[float] = None
    by_level: Optional[Dict[str, int]] = None


# ==================== PO ATTAINMENT SCHEMAS ====================

class POAttainmentCreate(BaseModel):
    """Schema for creating PO attainment record"""
    program_id: str
    po_number: str = Field(..., pattern=r"^PO\d{1,2}$")
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    batch: str = Field(..., min_length=1, max_length=50)


class POAttainmentUpdate(BaseModel):
    """Schema for updating PO attainment"""
    direct_attainment: Optional[float] = Field(None, ge=0, le=100)
    indirect_attainment: Optional[float] = Field(None, ge=0, le=100)
    overall_attainment: Optional[float] = Field(None, ge=0, le=100)
    attainment_level: Optional[AttainmentLevel] = None
    target_attainment: Optional[float] = None
    course_contributions: Optional[List[Dict[str, Any]]] = None
    co_po_matrix: Optional[Dict[str, Dict[str, float]]] = None
    alumni_feedback_score: Optional[float] = None
    employer_feedback_score: Optional[float] = None
    exit_survey_score: Optional[float] = None
    gap_analysis: Optional[str] = None
    improvement_actions: Optional[List[str]] = None


class POAttainmentResponse(BaseModel):
    """Schema for PO attainment response"""
    id: str
    program_id: str
    po_number: str
    academic_year: str
    batch: str
    direct_attainment: Optional[float]
    indirect_attainment: Optional[float]
    overall_attainment: Optional[float]
    attainment_level: Optional[str]
    target_attainment: Optional[float]
    course_contributions: Optional[List[Dict[str, Any]]]
    co_po_matrix: Optional[Dict[str, Dict[str, float]]]
    alumni_feedback_score: Optional[float]
    employer_feedback_score: Optional[float]
    exit_survey_score: Optional[float]
    gap_analysis: Optional[str]
    improvement_actions: Optional[List[str]]
    evidence_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class POAttainmentListResponse(BaseModel):
    """Schema for paginated PO attainment list"""
    items: List[POAttainmentResponse]
    total: int
    page: int
    page_size: int
    average_attainment: Optional[float] = None
    by_po: Optional[Dict[str, float]] = None


# ==================== STUDENT RESULT ANALYSIS SCHEMAS ====================

class StudentResultAnalysisCreate(BaseModel):
    """Schema for creating student result analysis"""
    program_id: str
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    semester: int = Field(..., ge=1, le=8)
    batch: str = Field(..., min_length=1, max_length=50)
    section: Optional[str] = None
    exam_type: Optional[str] = None
    total_students: int = Field(..., ge=0)


class StudentResultAnalysisUpdate(BaseModel):
    """Schema for updating student result analysis"""
    students_appeared: Optional[int] = None
    students_passed: Optional[int] = None
    pass_percentage: Optional[float] = None
    average_marks: Optional[float] = None
    highest_marks: Optional[float] = None
    lowest_marks: Optional[float] = None
    grade_distribution: Optional[Dict[str, int]] = None
    distinction_count: Optional[int] = None
    first_class_count: Optional[int] = None
    second_class_count: Optional[int] = None
    failed_count: Optional[int] = None
    absent_count: Optional[int] = None
    co_wise_analysis: Optional[Dict[str, Dict[str, Any]]] = None
    question_wise_analysis: Optional[List[Dict[str, Any]]] = None
    remarks: Optional[str] = None


class StudentResultAnalysisResponse(BaseModel):
    """Schema for student result analysis response"""
    id: str
    program_id: str
    course_code: str
    course_name: str
    academic_year: str
    semester: int
    batch: str
    section: Optional[str]
    exam_type: Optional[str]
    total_students: int
    students_appeared: int
    students_passed: int
    pass_percentage: Optional[float]
    average_marks: Optional[float]
    highest_marks: Optional[float]
    lowest_marks: Optional[float]
    grade_distribution: Optional[Dict[str, int]]
    distinction_count: int
    first_class_count: int
    second_class_count: int
    failed_count: int
    absent_count: int
    co_wise_analysis: Optional[Dict[str, Dict[str, Any]]]
    question_wise_analysis: Optional[List[Dict[str, Any]]]
    result_sheet_path: Optional[str]
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StudentResultAnalysisListResponse(BaseModel):
    """Schema for paginated student result analysis list"""
    items: List[StudentResultAnalysisResponse]
    total: int
    page: int
    page_size: int
    overall_pass_percentage: Optional[float] = None
    by_course: Optional[Dict[str, float]] = None


# ==================== NBA CONTINUOUS IMPROVEMENT SCHEMAS ====================

class NBAContinuousImprovementCreate(BaseModel):
    """Schema for creating continuous improvement action"""
    program_id: str
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    improvement_area: str = Field(..., min_length=1, max_length=255)
    issue_identified: str = Field(..., min_length=10)
    source_of_identification: Optional[str] = None
    po_affected: Optional[List[str]] = None
    co_affected: Optional[List[str]] = None


class NBAContinuousImprovementUpdate(BaseModel):
    """Schema for updating continuous improvement action"""
    action_planned: Optional[str] = None
    action_taken: Optional[str] = None
    resources_required: Optional[List[str]] = None
    responsible_person: Optional[str] = None
    target_date: Optional[date] = None
    completion_date: Optional[date] = None
    status: Optional[ActionStatus] = None
    outcome: Optional[str] = None
    impact_on_attainment: Optional[str] = None
    next_review_date: Optional[date] = None


class NBAContinuousImprovementResponse(BaseModel):
    """Schema for continuous improvement response"""
    id: str
    program_id: str
    academic_year: str
    improvement_area: str
    issue_identified: str
    source_of_identification: Optional[str]
    po_affected: Optional[List[str]]
    co_affected: Optional[List[str]]
    action_planned: Optional[str]
    action_taken: Optional[str]
    resources_required: Optional[List[str]]
    responsible_person: Optional[str]
    target_date: Optional[date]
    completion_date: Optional[date]
    status: str
    outcome: Optional[str]
    impact_on_attainment: Optional[str]
    evidence_path: Optional[str]
    next_review_date: Optional[date]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class NBAContinuousImprovementListResponse(BaseModel):
    """Schema for paginated continuous improvement list"""
    items: List[NBAContinuousImprovementResponse]
    total: int
    page: int
    page_size: int
    by_status: Optional[Dict[str, int]] = None
    by_area: Optional[Dict[str, int]] = None


# ==================== NBA FACULTY CONTRIBUTION SCHEMAS ====================

class NBAFacultyContributionCreate(BaseModel):
    """Schema for creating faculty contribution record"""
    program_id: str
    faculty_name: str = Field(..., min_length=1, max_length=255)
    faculty_id: Optional[str] = None
    faculty_email: Optional[str] = None
    designation: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")


class NBAFacultyContributionUpdate(BaseModel):
    """Schema for updating faculty contribution"""
    qualification: Optional[str] = None
    experience_years: Optional[int] = None
    courses_taught: Optional[List[Dict[str, str]]] = None
    average_result: Optional[float] = None
    co_attainment_average: Optional[float] = None
    publications_count: Optional[int] = None
    fdps_attended: Optional[int] = None
    certifications: Optional[List[str]] = None
    industry_experience: Optional[int] = None
    projects_guided: Optional[int] = None
    research_projects: Optional[int] = None
    consultancy_amount: Optional[float] = None
    professional_memberships: Optional[List[str]] = None
    awards: Optional[List[Dict[str, Any]]] = None


class NBAFacultyContributionResponse(BaseModel):
    """Schema for faculty contribution response"""
    id: str
    program_id: str
    faculty_name: str
    faculty_id: Optional[str]
    faculty_email: Optional[str]
    designation: Optional[str]
    academic_year: str
    qualification: Optional[str]
    experience_years: Optional[int]
    courses_taught: Optional[List[Dict[str, str]]]
    average_result: Optional[float]
    co_attainment_average: Optional[float]
    publications_count: int
    fdps_attended: int
    certifications: Optional[List[str]]
    industry_experience: int
    projects_guided: int
    research_projects: int
    consultancy_amount: Optional[float]
    professional_memberships: Optional[List[str]]
    awards: Optional[List[Dict[str, Any]]]
    resume_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class NBAFacultyContributionListResponse(BaseModel):
    """Schema for paginated faculty contribution list"""
    items: List[NBAFacultyContributionResponse]
    total: int
    page: int
    page_size: int
    total_publications: Optional[int] = None
    average_experience: Optional[float] = None


# ==================== NBA LAB FACILITY SCHEMAS ====================

class NBALabFacilityCreate(BaseModel):
    """Schema for creating lab facility record"""
    program_id: str
    lab_name: str = Field(..., min_length=1, max_length=255)
    lab_code: Optional[str] = None
    lab_type: Optional[str] = None
    location: Optional[str] = None
    area_sqft: Optional[float] = Field(None, gt=0)
    established_year: Optional[int] = None


class NBALabFacilityUpdate(BaseModel):
    """Schema for updating lab facility"""
    equipment_list: Optional[List[Dict[str, Any]]] = None
    software_available: Optional[List[str]] = None
    total_equipment_value: Optional[float] = None
    seating_capacity: Optional[int] = None
    courses_supported: Optional[List[str]] = None
    cos_addressed: Optional[List[str]] = None
    pos_addressed: Optional[List[str]] = None
    utilization_percentage: Optional[float] = None
    weekly_hours: Optional[float] = None
    maintenance_budget: Optional[float] = None
    last_upgrade_date: Optional[date] = None
    is_active: Optional[bool] = None


class NBALabFacilityResponse(BaseModel):
    """Schema for lab facility response"""
    id: str
    program_id: str
    lab_name: str
    lab_code: Optional[str]
    lab_type: Optional[str]
    location: Optional[str]
    area_sqft: Optional[float]
    established_year: Optional[int]
    equipment_list: Optional[List[Dict[str, Any]]]
    software_available: Optional[List[str]]
    total_equipment_value: Optional[float]
    seating_capacity: Optional[int]
    courses_supported: Optional[List[str]]
    cos_addressed: Optional[List[str]]
    pos_addressed: Optional[List[str]]
    utilization_percentage: Optional[float]
    weekly_hours: Optional[float]
    maintenance_budget: Optional[float]
    last_upgrade_date: Optional[date]
    layout_path: Optional[str]
    photos_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class NBALabFacilityListResponse(BaseModel):
    """Schema for paginated lab facility list"""
    items: List[NBALabFacilityResponse]
    total: int
    page: int
    page_size: int
    total_value: Optional[float] = None
    average_utilization: Optional[float] = None


# ==================== DASHBOARD & REPORT SCHEMAS ====================

class NBADashboardStats(BaseModel):
    """Dashboard statistics for NBA accreditation"""
    # Program Info
    program_name: str
    program_code: str
    total_students: int
    total_faculty: int

    # Criterion 1: Vision, Mission, PEOs
    vision_mission_defined: bool
    peos_count: int
    pso_count: int
    stakeholder_consultations: int

    # Criterion 2: Program Curriculum
    total_courses: int
    co_count: int
    po_count: int
    co_po_mapping_percentage: float

    # Criterion 3: COs and POs
    average_co_attainment: float
    average_po_attainment: float
    pos_above_target: int
    attainment_by_po: Dict[str, float]

    # Criterion 4: Students Performance
    pass_percentage: float
    placement_percentage: float
    higher_studies_percentage: float
    average_salary: Optional[float]

    # Criterion 5: Faculty
    faculty_count: int
    phd_faculty_percentage: float
    industry_experienced_percentage: float
    total_publications: int

    # Criterion 6: Facilities
    labs_count: int
    total_equipment_value: float
    average_lab_utilization: float
    software_licenses: int

    # Criterion 7-10: Continuous Improvement
    improvement_actions_total: int
    improvement_actions_completed: int
    feedback_collected: Dict[str, int]
    audit_observations_resolved: int

    # Overall readiness
    completion_percentage: float
    pending_items: List[Dict[str, Any]]


class NBAReportRequest(BaseModel):
    """Request schema for generating NBA report"""
    program_name: str = Field(..., min_length=1)
    program_code: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    batch: Optional[str] = None
    include_criteria: Optional[List[int]] = None
    format: str = Field(default="docx", pattern=r"^(docx|pdf)$")
    include_analytics: bool = True


class NBAReportResponse(BaseModel):
    """Response schema for generated report"""
    success: bool
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    criteria_included: List[int]
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==================== CO-PO MATRIX SCHEMAS ====================

class COPOMatrixCreate(BaseModel):
    """Schema for creating CO-PO mapping matrix"""
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    program_id: str
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    matrix: Dict[str, Dict[str, int]]  # {CO1: {PO1: 3, PO2: 2, ...}, ...}


class COPOMatrixResponse(BaseModel):
    """Schema for CO-PO matrix response"""
    course_code: str
    course_name: str
    program_id: str
    academic_year: str
    matrix: Dict[str, Dict[str, int]]
    average_mapping: Dict[str, float]
    strong_mappings: List[Dict[str, Any]]


class AttainmentCalculationRequest(BaseModel):
    """Request schema for calculating attainment"""
    program_id: str
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    batch: str
    direct_weight: float = Field(default=0.8, ge=0, le=1)
    indirect_weight: float = Field(default=0.2, ge=0, le=1)
    target_attainment: float = Field(default=60, ge=0, le=100)


class AttainmentCalculationResponse(BaseModel):
    """Response schema for attainment calculation"""
    program_id: str
    academic_year: str
    batch: str
    co_attainments: List[Dict[str, Any]]
    po_attainments: List[Dict[str, Any]]
    pso_attainments: Optional[List[Dict[str, Any]]]
    overall_attainment: float
    gaps_identified: List[Dict[str, Any]]
    recommendations: List[str]
    calculated_at: datetime
