"""
NAAC Criterion 2: Teaching-Learning and Evaluation - Pydantic Schemas

This module defines request/response schemas for Criterion 2 API endpoints (200 marks).
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== ENUMS ====================

class LMSPlatform(str, Enum):
    MOODLE = "moodle"
    GOOGLE_CLASSROOM = "google_classroom"
    MICROSOFT_TEAMS = "microsoft_teams"
    CANVAS = "canvas"
    BLACKBOARD = "blackboard"
    CUSTOM = "custom"
    OTHER = "other"


class BloomsLevel(str, Enum):
    REMEMBER = "L1_remember"
    UNDERSTAND = "L2_understand"
    APPLY = "L3_apply"
    ANALYZE = "L4_analyze"
    EVALUATE = "L5_evaluate"
    CREATE = "L6_create"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    ON_DUTY = "on_duty"


class AssessmentType(str, Enum):
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    MID_TERM = "mid_term"
    END_TERM = "end_term"
    PROJECT = "project"
    PRESENTATION = "presentation"
    LAB = "lab"
    VIVA = "viva"
    SEMINAR = "seminar"
    OTHER = "other"


class TeachingMethod(str, Enum):
    LECTURE = "lecture"
    FLIPPED_CLASSROOM = "flipped_classroom"
    PROJECT_BASED = "project_based"
    PROBLEM_BASED = "problem_based"
    CASE_STUDY = "case_study"
    GROUP_DISCUSSION = "group_discussion"
    EXPERIENTIAL = "experiential"
    PEER_LEARNING = "peer_learning"
    ICT_ENABLED = "ict_enabled"
    BLENDED = "blended"
    SIMULATION = "simulation"
    FIELD_VISIT = "field_visit"


class ContentType(str, Enum):
    VIDEO = "video"
    PDF = "pdf"
    PPT = "ppt"
    INTERACTIVE = "interactive"
    SIMULATION = "simulation"
    E_BOOK = "e_book"
    MOOC = "mooc"
    QUIZ = "quiz"
    ANIMATION = "animation"
    OTHER = "other"


class TeacherDesignation(str, Enum):
    PROFESSOR = "professor"
    ASSOCIATE_PROFESSOR = "associate_professor"
    ASSISTANT_PROFESSOR = "assistant_professor"
    LECTURER = "lecturer"
    GUEST_FACULTY = "guest_faculty"
    ADJUNCT_FACULTY = "adjunct_faculty"
    VISITING_FACULTY = "visiting_faculty"


class PerformanceLevel(str, Enum):
    OUTSTANDING = "outstanding"
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    POOR = "poor"


# ==================== LMS ADOPTION SCHEMAS ====================

class LMSAdoptionCreate(BaseModel):
    """Schema for creating LMS adoption record"""
    platform: LMSPlatform
    platform_name: Optional[str] = None
    platform_url: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    total_courses: int = Field(default=0, ge=0)
    active_courses: int = Field(default=0, ge=0)
    total_faculty_registered: int = Field(default=0, ge=0)
    total_students_registered: int = Field(default=0, ge=0)


class LMSAdoptionUpdate(BaseModel):
    """Schema for updating LMS adoption"""
    platform_name: Optional[str] = None
    platform_url: Optional[str] = None
    total_courses: Optional[int] = Field(None, ge=0)
    active_courses: Optional[int] = Field(None, ge=0)
    total_faculty_registered: Optional[int] = Field(None, ge=0)
    total_students_registered: Optional[int] = Field(None, ge=0)
    active_users_monthly: Optional[int] = Field(None, ge=0)
    total_resources_uploaded: Optional[int] = Field(None, ge=0)
    total_assignments_created: Optional[int] = Field(None, ge=0)
    total_quizzes_created: Optional[int] = Field(None, ge=0)
    total_discussion_forums: Optional[int] = Field(None, ge=0)
    avg_login_frequency: Optional[float] = Field(None, ge=0)
    assignment_submission_rate: Optional[float] = Field(None, ge=0, le=100)
    quiz_completion_rate: Optional[float] = Field(None, ge=0, le=100)
    screenshots_path: Optional[str] = None
    usage_report_path: Optional[str] = None
    is_active: Optional[bool] = None


class LMSAdoptionResponse(BaseModel):
    """Schema for LMS adoption response"""
    id: str
    platform: str
    platform_name: Optional[str]
    platform_url: Optional[str]
    department: str
    academic_year: str
    total_courses: int
    active_courses: int
    total_faculty_registered: int
    total_students_registered: int
    active_users_monthly: int
    total_resources_uploaded: int
    total_assignments_created: int
    total_quizzes_created: int
    total_discussion_forums: int
    avg_login_frequency: Optional[float]
    assignment_submission_rate: Optional[float]
    quiz_completion_rate: Optional[float]
    screenshots_path: Optional[str]
    usage_report_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class LMSAdoptionListResponse(BaseModel):
    """Schema for paginated LMS adoption list"""
    items: List[LMSAdoptionResponse]
    total: int
    page: int
    page_size: int
    by_platform: Optional[Dict[str, int]] = None


# ==================== LESSON PLAN SCHEMAS ====================

class LessonPlanCreate(BaseModel):
    """Schema for creating lesson plan"""
    course_name: str = Field(..., min_length=1, max_length=500)
    course_code: str = Field(..., min_length=1, max_length=50)
    department: str = Field(..., min_length=1, max_length=255)
    program: Optional[str] = None
    semester: int = Field(..., ge=1, le=8)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    credits: Optional[int] = Field(None, ge=1)
    faculty_name: str = Field(..., min_length=1, max_length=255)
    faculty_email: Optional[str] = None
    unit_number: Optional[int] = Field(None, ge=1)
    unit_name: Optional[str] = None
    topic: str = Field(..., min_length=1, max_length=500)
    subtopics: Optional[List[str]] = None
    planned_hours: float = Field(..., gt=0)
    session_date: Optional[date] = None
    learning_objectives: Optional[List[str]] = None
    course_outcomes_mapped: Optional[List[str]] = None
    blooms_levels: Optional[List[BloomsLevel]] = None
    teaching_methods: Optional[List[TeachingMethod]] = None
    teaching_aids: Optional[List[str]] = None
    ict_tools_used: Optional[List[str]] = None
    assessment_methods: Optional[List[AssessmentType]] = None
    assessment_blooms_level: Optional[BloomsLevel] = None
    reference_materials: Optional[List[str]] = None
    additional_resources: Optional[str] = None


class LessonPlanUpdate(BaseModel):
    """Schema for updating lesson plan"""
    unit_number: Optional[int] = None
    unit_name: Optional[str] = None
    topic: Optional[str] = None
    subtopics: Optional[List[str]] = None
    planned_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    session_date: Optional[date] = None
    learning_objectives: Optional[List[str]] = None
    course_outcomes_mapped: Optional[List[str]] = None
    blooms_levels: Optional[List[str]] = None
    teaching_methods: Optional[List[str]] = None
    teaching_aids: Optional[List[str]] = None
    ict_tools_used: Optional[List[str]] = None
    assessment_methods: Optional[List[str]] = None
    assessment_blooms_level: Optional[BloomsLevel] = None
    reference_materials: Optional[List[str]] = None
    additional_resources: Optional[str] = None
    is_completed: Optional[bool] = None
    completion_date: Optional[date] = None
    remarks: Optional[str] = None


class LessonPlanResponse(BaseModel):
    """Schema for lesson plan response"""
    id: str
    course_name: str
    course_code: str
    department: str
    program: Optional[str]
    semester: int
    academic_year: str
    credits: Optional[int]
    faculty_name: str
    faculty_email: Optional[str]
    unit_number: Optional[int]
    unit_name: Optional[str]
    topic: str
    subtopics: Optional[List[str]]
    planned_hours: float
    actual_hours: Optional[float]
    session_date: Optional[date]
    learning_objectives: Optional[List[str]]
    course_outcomes_mapped: Optional[List[str]]
    blooms_levels: Optional[List[str]]
    teaching_methods: Optional[List[str]]
    teaching_aids: Optional[List[str]]
    ict_tools_used: Optional[List[str]]
    assessment_methods: Optional[List[str]]
    assessment_blooms_level: Optional[str]
    reference_materials: Optional[List[str]]
    additional_resources: Optional[str]
    is_completed: bool
    completion_date: Optional[date]
    remarks: Optional[str]
    document_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class LessonPlanListResponse(BaseModel):
    """Schema for paginated lesson plan list"""
    items: List[LessonPlanResponse]
    total: int
    page: int
    page_size: int
    by_course: Optional[Dict[str, int]] = None


# ==================== ATTENDANCE SCHEMAS ====================

class AttendanceCreate(BaseModel):
    """Schema for creating attendance record"""
    student_id: str = Field(..., min_length=1, max_length=50)
    student_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    batch: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=8)
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    attendance_date: date
    period: Optional[int] = Field(None, ge=1)
    status: AttendanceStatus
    marked_by: Optional[str] = None
    remarks: Optional[str] = None
    is_makeup_class: bool = False


class AttendanceBulkCreate(BaseModel):
    """Schema for bulk attendance marking"""
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    attendance_date: date
    period: Optional[int] = None
    marked_by: Optional[str] = None
    records: List[Dict[str, Any]]  # [{"student_id": "...", "student_name": "...", "status": "present"}]


class AttendanceUpdate(BaseModel):
    """Schema for updating attendance"""
    status: Optional[AttendanceStatus] = None
    remarks: Optional[str] = None
    is_makeup_class: Optional[bool] = None


class AttendanceResponse(BaseModel):
    """Schema for attendance response"""
    id: str
    student_id: str
    student_name: str
    department: str
    batch: Optional[str]
    semester: Optional[int]
    course_code: str
    course_name: str
    academic_year: str
    attendance_date: date
    period: Optional[int]
    status: str
    marked_by: Optional[str]
    remarks: Optional[str]
    is_makeup_class: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class AttendanceListResponse(BaseModel):
    """Schema for paginated attendance list"""
    items: List[AttendanceResponse]
    total: int
    page: int
    page_size: int


class AttendanceSummary(BaseModel):
    """Schema for attendance summary"""
    student_id: str
    student_name: str
    total_classes: int
    present: int
    absent: int
    late: int
    excused: int
    on_duty: int
    attendance_percentage: float


# ==================== CIE SCHEMAS ====================

class CIECreate(BaseModel):
    """Schema for creating CIE record"""
    student_id: str = Field(..., min_length=1, max_length=50)
    student_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    batch: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=8)
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    assessment_type: AssessmentType
    assessment_name: str = Field(..., min_length=1, max_length=255)
    assessment_date: date
    max_marks: float = Field(..., gt=0)
    marks_obtained: Optional[float] = Field(None, ge=0)
    course_outcomes_assessed: Optional[List[str]] = None
    blooms_level: Optional[BloomsLevel] = None
    rubric_id: Optional[str] = None


class CIEUpdate(BaseModel):
    """Schema for updating CIE record"""
    marks_obtained: Optional[float] = Field(None, ge=0)
    grade: Optional[str] = None
    course_outcomes_assessed: Optional[List[str]] = None
    blooms_level: Optional[BloomsLevel] = None
    feedback: Optional[str] = None
    evaluated_by: Optional[str] = None


class CIEResponse(BaseModel):
    """Schema for CIE response"""
    id: str
    student_id: str
    student_name: str
    department: str
    batch: Optional[str]
    semester: Optional[int]
    course_code: str
    course_name: str
    academic_year: str
    assessment_type: str
    assessment_name: str
    assessment_date: date
    max_marks: float
    marks_obtained: Optional[float]
    percentage: Optional[float]
    grade: Optional[str]
    course_outcomes_assessed: Optional[List[str]]
    blooms_level: Optional[str]
    rubric_id: Optional[str]
    feedback: Optional[str]
    evaluated_by: Optional[str]
    evaluated_at: Optional[datetime]
    answer_sheet_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CIEListResponse(BaseModel):
    """Schema for paginated CIE list"""
    items: List[CIEResponse]
    total: int
    page: int
    page_size: int
    by_assessment_type: Optional[Dict[str, int]] = None


class CIEBulkCreate(BaseModel):
    """Schema for bulk CIE entry"""
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    assessment_type: AssessmentType
    assessment_name: str = Field(..., min_length=1, max_length=255)
    assessment_date: date
    max_marks: float = Field(..., gt=0)
    course_outcomes_assessed: Optional[List[str]] = None
    blooms_level: Optional[BloomsLevel] = None
    records: List[Dict[str, Any]]  # [{"student_id": "...", "student_name": "...", "marks_obtained": 75}]


# ==================== EVALUATION RUBRIC SCHEMAS ====================

class RubricCriterion(BaseModel):
    """Schema for rubric criterion"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    max_points: float = Field(..., gt=0)
    levels: Dict[str, Any]  # {"excellent": {"points": 20, "description": "..."}, ...}
    co_mapped: Optional[List[str]] = None
    blooms_level: Optional[BloomsLevel] = None


class RubricCreate(BaseModel):
    """Schema for creating evaluation rubric"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    department: Optional[str] = None
    academic_year: Optional[str] = None
    assessment_type: Optional[AssessmentType] = None
    total_points: float = Field(..., gt=0)
    criteria: List[RubricCriterion]
    performance_levels: Optional[Dict[str, Any]] = None
    course_outcomes_mapped: Optional[List[str]] = None
    blooms_levels_covered: Optional[List[BloomsLevel]] = None
    is_template: bool = False


class RubricUpdate(BaseModel):
    """Schema for updating rubric"""
    name: Optional[str] = None
    description: Optional[str] = None
    total_points: Optional[float] = None
    criteria: Optional[List[Dict[str, Any]]] = None
    performance_levels: Optional[Dict[str, Any]] = None
    course_outcomes_mapped: Optional[List[str]] = None
    blooms_levels_covered: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_template: Optional[bool] = None


class RubricResponse(BaseModel):
    """Schema for rubric response"""
    id: str
    name: str
    description: Optional[str]
    course_code: Optional[str]
    course_name: Optional[str]
    department: Optional[str]
    academic_year: Optional[str]
    assessment_type: Optional[str]
    total_points: float
    criteria: List[Dict[str, Any]]
    performance_levels: Optional[Dict[str, Any]]
    course_outcomes_mapped: Optional[List[str]]
    blooms_levels_covered: Optional[List[str]]
    document_path: Optional[str]
    is_active: bool
    is_template: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RubricListResponse(BaseModel):
    """Schema for paginated rubric list"""
    items: List[RubricResponse]
    total: int
    page: int
    page_size: int


# ==================== STUDENT PERFORMANCE SCHEMAS ====================

class StudentPerformanceCreate(BaseModel):
    """Schema for creating student performance record"""
    student_id: str = Field(..., min_length=1, max_length=50)
    student_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    program: Optional[str] = None
    batch: Optional[str] = None
    semester: int = Field(..., ge=1, le=8)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    sgpa: Optional[float] = Field(None, ge=0, le=10)
    cgpa: Optional[float] = Field(None, ge=0, le=10)
    total_credits_earned: int = Field(default=0, ge=0)
    total_credits_attempted: int = Field(default=0, ge=0)
    percentage: Optional[float] = Field(None, ge=0, le=100)
    performance_level: Optional[PerformanceLevel] = None


class StudentPerformanceUpdate(BaseModel):
    """Schema for updating student performance"""
    sgpa: Optional[float] = Field(None, ge=0, le=10)
    cgpa: Optional[float] = Field(None, ge=0, le=10)
    total_credits_earned: Optional[int] = Field(None, ge=0)
    total_credits_attempted: Optional[int] = Field(None, ge=0)
    percentage: Optional[float] = Field(None, ge=0, le=100)
    performance_level: Optional[PerformanceLevel] = None
    course_performance: Optional[List[Dict[str, Any]]] = None
    co_attainment: Optional[Dict[str, float]] = None
    po_attainment: Optional[Dict[str, float]] = None
    pso_attainment: Optional[Dict[str, float]] = None
    overall_attendance_percentage: Optional[float] = None
    average_cie_score: Optional[float] = None
    cie_performance_trend: Optional[List[Dict[str, Any]]] = None
    strengths: Optional[List[str]] = None
    areas_for_improvement: Optional[List[str]] = None
    mentor_name: Optional[str] = None
    mentor_remarks: Optional[str] = None
    is_passed: Optional[bool] = None
    backlogs_count: Optional[int] = None


class StudentPerformanceResponse(BaseModel):
    """Schema for student performance response"""
    id: str
    student_id: str
    student_name: str
    department: str
    program: Optional[str]
    batch: Optional[str]
    semester: int
    academic_year: str
    sgpa: Optional[float]
    cgpa: Optional[float]
    total_credits_earned: int
    total_credits_attempted: int
    percentage: Optional[float]
    performance_level: Optional[str]
    course_performance: Optional[List[Dict[str, Any]]]
    co_attainment: Optional[Dict[str, float]]
    po_attainment: Optional[Dict[str, float]]
    pso_attainment: Optional[Dict[str, float]]
    overall_attendance_percentage: Optional[float]
    average_cie_score: Optional[float]
    cie_performance_trend: Optional[List[Dict[str, Any]]]
    strengths: Optional[List[str]]
    areas_for_improvement: Optional[List[str]]
    mentor_name: Optional[str]
    mentor_remarks: Optional[str]
    is_passed: Optional[bool]
    backlogs_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StudentPerformanceListResponse(BaseModel):
    """Schema for paginated student performance list"""
    items: List[StudentPerformanceResponse]
    total: int
    page: int
    page_size: int
    by_performance_level: Optional[Dict[str, int]] = None


class StudentPerformanceAnalytics(BaseModel):
    """Schema for performance analytics"""
    total_students: int
    average_sgpa: float
    average_cgpa: float
    pass_percentage: float
    performance_distribution: Dict[str, int]
    top_performers: List[Dict[str, Any]]
    at_risk_students: int
    average_attendance: float


# ==================== TEACHER PROFILE SCHEMAS ====================

class TeacherProfileCreate(BaseModel):
    """Schema for creating teacher profile"""
    employee_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    designation: TeacherDesignation
    highest_qualification: Optional[str] = None
    specialization: Optional[str] = None
    qualifications_list: Optional[List[Dict[str, Any]]] = None
    teaching_experience_years: float = Field(default=0, ge=0)
    industry_experience_years: float = Field(default=0, ge=0)
    research_experience_years: float = Field(default=0, ge=0)
    date_of_joining: Optional[date] = None


class TeacherProfileUpdate(BaseModel):
    """Schema for updating teacher profile"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[TeacherDesignation] = None
    highest_qualification: Optional[str] = None
    specialization: Optional[str] = None
    qualifications_list: Optional[List[Dict[str, Any]]] = None
    teaching_experience_years: Optional[float] = None
    industry_experience_years: Optional[float] = None
    research_experience_years: Optional[float] = None
    awards: Optional[List[Dict[str, Any]]] = None
    publications_count: Optional[int] = None
    patents_count: Optional[int] = None
    funded_projects_count: Optional[int] = None
    research_indices: Optional[Dict[str, Any]] = None
    fdp_attended: Optional[List[Dict[str, Any]]] = None
    workshops_conducted: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    current_courses: Optional[List[str]] = None
    teaching_hours_per_week: Optional[float] = None
    student_feedback_rating: Optional[float] = Field(None, ge=1, le=5)
    api_score: Optional[float] = None
    uses_lms: Optional[bool] = None
    digital_content_created: Optional[int] = None
    moocs_developed: Optional[int] = None
    is_active: Optional[bool] = None
    is_phd_guide: Optional[bool] = None
    phd_students_guided: Optional[int] = None


class TeacherProfileResponse(BaseModel):
    """Schema for teacher profile response"""
    id: str
    employee_id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    department: str
    designation: str
    highest_qualification: Optional[str]
    specialization: Optional[str]
    qualifications_list: Optional[List[Dict[str, Any]]]
    teaching_experience_years: float
    industry_experience_years: float
    research_experience_years: float
    date_of_joining: Optional[date]
    awards: Optional[List[Dict[str, Any]]]
    publications_count: int
    patents_count: int
    funded_projects_count: int
    research_indices: Optional[Dict[str, Any]]
    fdp_attended: Optional[List[Dict[str, Any]]]
    workshops_conducted: Optional[List[Dict[str, Any]]]
    certifications: Optional[List[Dict[str, Any]]]
    current_courses: Optional[List[str]]
    teaching_hours_per_week: Optional[float]
    student_feedback_rating: Optional[float]
    api_score: Optional[float]
    uses_lms: bool
    digital_content_created: int
    moocs_developed: int
    is_active: bool
    is_phd_guide: bool
    phd_students_guided: int
    profile_document_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class TeacherProfileListResponse(BaseModel):
    """Schema for paginated teacher profile list"""
    items: List[TeacherProfileResponse]
    total: int
    page: int
    page_size: int
    by_designation: Optional[Dict[str, int]] = None


# ==================== DIGITAL CONTENT SCHEMAS ====================

class DigitalContentCreate(BaseModel):
    """Schema for creating digital content"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    content_type: ContentType
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    semester: Optional[int] = Field(None, ge=1, le=8)
    topics: Optional[List[str]] = None
    learning_outcomes: Optional[List[str]] = None
    blooms_level: Optional[BloomsLevel] = None
    external_url: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1)
    created_by: str = Field(..., min_length=1, max_length=255)
    creator_email: Optional[str] = None


class DigitalContentUpdate(BaseModel):
    """Schema for updating digital content"""
    title: Optional[str] = None
    description: Optional[str] = None
    topics: Optional[List[str]] = None
    learning_outcomes: Optional[List[str]] = None
    blooms_level: Optional[BloomsLevel] = None
    external_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_accessible: Optional[bool] = None
    has_transcripts: Optional[bool] = None
    supported_languages: Optional[List[str]] = None
    is_published: Optional[bool] = None
    is_approved: Optional[bool] = None
    approved_by: Optional[str] = None


class DigitalContentResponse(BaseModel):
    """Schema for digital content response"""
    id: str
    title: str
    description: Optional[str]
    content_type: str
    course_code: Optional[str]
    course_name: Optional[str]
    department: str
    semester: Optional[int]
    topics: Optional[List[str]]
    learning_outcomes: Optional[List[str]]
    blooms_level: Optional[str]
    file_path: Optional[str]
    file_size: Optional[int]
    external_url: Optional[str]
    duration_minutes: Optional[int]
    created_by: str
    creator_email: Optional[str]
    view_count: int
    download_count: int
    average_rating: Optional[float]
    ratings_count: int
    is_accessible: bool
    has_transcripts: bool
    supported_languages: Optional[List[str]]
    is_published: bool
    is_approved: bool
    approved_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class DigitalContentListResponse(BaseModel):
    """Schema for paginated digital content list"""
    items: List[DigitalContentResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None


# ==================== LEARNING OUTCOME ATTAINMENT SCHEMAS ====================

class CourseOutcome(BaseModel):
    """Schema for course outcome"""
    id: str = Field(..., min_length=1)  # CO1, CO2, etc.
    statement: str = Field(..., min_length=1)
    blooms_level: BloomsLevel


class LOAttainmentCreate(BaseModel):
    """Schema for creating learning outcome attainment"""
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    semester: int = Field(..., ge=1, le=8)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    batch: Optional[str] = None
    total_students: int = Field(..., ge=1)
    students_appeared: Optional[int] = Field(None, ge=0)
    students_passed: Optional[int] = Field(None, ge=0)
    course_outcomes: List[CourseOutcome]
    co_po_mapping: Optional[Dict[str, Dict[str, int]]] = None
    direct_assessment_methods: Optional[List[str]] = None
    indirect_assessment_methods: Optional[List[str]] = None
    direct_weightage: float = Field(default=80, ge=0, le=100)
    indirect_weightage: float = Field(default=20, ge=0, le=100)
    attainment_threshold: float = Field(default=60, ge=0, le=100)
    course_coordinator: Optional[str] = None


class LOAttainmentUpdate(BaseModel):
    """Schema for updating LO attainment"""
    students_appeared: Optional[int] = None
    students_passed: Optional[int] = None
    pass_percentage: Optional[float] = None
    co_attainment_direct: Optional[Dict[str, float]] = None
    co_attainment_indirect: Optional[Dict[str, float]] = None
    co_attainment_overall: Optional[Dict[str, float]] = None
    co_attainment_target: Optional[Dict[str, float]] = None
    po_contribution: Optional[Dict[str, float]] = None
    gap_analysis: Optional[Dict[str, Any]] = None
    action_taken: Optional[str] = None
    verified_by: Optional[str] = None


class LOAttainmentResponse(BaseModel):
    """Schema for LO attainment response"""
    id: str
    course_code: str
    course_name: str
    department: str
    semester: int
    academic_year: str
    batch: Optional[str]
    total_students: int
    students_appeared: Optional[int]
    students_passed: Optional[int]
    pass_percentage: Optional[float]
    course_outcomes: List[Dict[str, Any]]
    co_attainment_direct: Optional[Dict[str, float]]
    co_attainment_indirect: Optional[Dict[str, float]]
    co_attainment_overall: Optional[Dict[str, float]]
    co_attainment_target: Optional[Dict[str, float]]
    co_po_mapping: Optional[Dict[str, Dict[str, int]]]
    po_contribution: Optional[Dict[str, float]]
    direct_assessment_methods: Optional[List[str]]
    indirect_assessment_methods: Optional[List[str]]
    direct_weightage: float
    indirect_weightage: float
    attainment_threshold: float
    gap_analysis: Optional[Dict[str, Any]]
    action_taken: Optional[str]
    attainment_report_path: Optional[str]
    course_coordinator: Optional[str]
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class LOAttainmentListResponse(BaseModel):
    """Schema for paginated LO attainment list"""
    items: List[LOAttainmentResponse]
    total: int
    page: int
    page_size: int


# ==================== BLENDED LEARNING SCHEMAS ====================

class BlendedLearningCreate(BaseModel):
    """Schema for creating blended learning session"""
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    semester: Optional[int] = Field(None, ge=1, le=8)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    session_title: str = Field(..., min_length=1, max_length=500)
    session_date: date
    duration_minutes: Optional[int] = Field(None, ge=1)
    teaching_method: TeachingMethod
    is_synchronous: bool = True
    online_component_percentage: Optional[float] = Field(None, ge=0, le=100)
    offline_component_percentage: Optional[float] = Field(None, ge=0, le=100)
    tools_used: Optional[List[str]] = None
    lms_platform: Optional[str] = None
    faculty_name: str = Field(..., min_length=1, max_length=255)
    faculty_email: Optional[str] = None
    students_enrolled: Optional[int] = Field(None, ge=0)


class BlendedLearningUpdate(BaseModel):
    """Schema for updating blended learning session"""
    session_title: Optional[str] = None
    duration_minutes: Optional[int] = None
    online_component_percentage: Optional[float] = None
    offline_component_percentage: Optional[float] = None
    tools_used: Optional[List[str]] = None
    pre_class_materials: Optional[List[str]] = None
    in_class_activities: Optional[List[str]] = None
    post_class_assignments: Optional[List[str]] = None
    students_attended_online: Optional[int] = None
    students_attended_offline: Optional[int] = None
    attendance_percentage: Optional[float] = None
    student_feedback_rating: Optional[float] = Field(None, ge=1, le=5)
    feedback_comments: Optional[str] = None
    learning_outcomes_covered: Optional[List[str]] = None
    blooms_levels_addressed: Optional[List[str]] = None


class BlendedLearningResponse(BaseModel):
    """Schema for blended learning response"""
    id: str
    course_code: str
    course_name: str
    department: str
    semester: Optional[int]
    academic_year: str
    session_title: str
    session_date: date
    duration_minutes: Optional[int]
    teaching_method: str
    is_synchronous: bool
    online_component_percentage: Optional[float]
    offline_component_percentage: Optional[float]
    tools_used: Optional[List[str]]
    lms_platform: Optional[str]
    pre_class_materials: Optional[List[str]]
    in_class_activities: Optional[List[str]]
    post_class_assignments: Optional[List[str]]
    students_enrolled: Optional[int]
    students_attended_online: Optional[int]
    students_attended_offline: Optional[int]
    attendance_percentage: Optional[float]
    faculty_name: str
    faculty_email: Optional[str]
    student_feedback_rating: Optional[float]
    feedback_comments: Optional[str]
    learning_outcomes_covered: Optional[List[str]]
    blooms_levels_addressed: Optional[List[str]]
    session_recording_path: Optional[str]
    screenshots_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class BlendedLearningListResponse(BaseModel):
    """Schema for paginated blended learning list"""
    items: List[BlendedLearningResponse]
    total: int
    page: int
    page_size: int
    by_method: Optional[Dict[str, int]] = None


# ==================== DASHBOARD & REPORT SCHEMAS ====================

class Criterion2DashboardStats(BaseModel):
    """Dashboard statistics for Criterion 2 (200 marks)"""
    # Key Indicator 2.1: Student Enrollment and Profile
    total_students: int
    student_diversity: Dict[str, int]

    # Key Indicator 2.2: Student-Teacher Ratio
    total_teachers: int
    student_teacher_ratio: float
    teachers_with_phd: int
    phd_percentage: float

    # Key Indicator 2.3: Teaching-Learning Process
    lms_adoption_rate: float
    total_digital_content: int
    blended_learning_sessions: int
    lesson_plans_created: int
    teaching_methods_used: Dict[str, int]

    # Key Indicator 2.4: Teacher Quality
    teachers_with_awards: int
    average_experience_years: float
    fdp_participation_rate: float
    average_feedback_rating: float

    # Key Indicator 2.5: Evaluation Process
    rubrics_created: int
    cie_assessments: int
    blooms_coverage: Dict[str, int]

    # Key Indicator 2.6: Student Performance
    average_pass_percentage: float
    students_with_distinction: int
    average_co_attainment: float
    average_po_attainment: float

    # Overall readiness
    completion_percentage: float
    pending_items: List[Dict[str, Any]]


class Criterion2ReportRequest(BaseModel):
    """Request schema for generating Criterion 2 report"""
    institution_name: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    department: Optional[str] = None
    include_sections: Optional[List[str]] = None  # ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6"]
    format: str = Field(default="docx", pattern=r"^(docx|pdf)$")
    include_analytics: bool = True
    include_evidence_list: bool = True


class Criterion2ReportResponse(BaseModel):
    """Response schema for generated report"""
    success: bool
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    sections_included: List[str]
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
