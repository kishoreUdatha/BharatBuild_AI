"""
Pydantic schemas for NAAC Accreditation Framework 2025.
Supports Binary Accreditation and MBGL.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class BinaryAccreditationStatusEnum(str, Enum):
    NOT_APPLIED = "not_applied"
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    ACCREDITED = "accredited"
    NOT_ACCREDITED = "not_accredited"
    EXPIRED = "expired"


class MBGLLevelEnum(str, Enum):
    NOT_ASSESSED = "not_assessed"
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    LEVEL_4 = "level_4"
    LEVEL_5 = "level_5"


class AccreditationCycleEnum(str, Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    FIFTH_PLUS = "fifth_plus"


class AttributeCategoryEnum(str, Enum):
    CURRICULAR_ASPECTS = "curricular_aspects"
    TEACHING_LEARNING = "teaching_learning"
    RESEARCH_INNOVATION = "research_innovation"
    INFRASTRUCTURE = "infrastructure"
    STUDENT_SUPPORT = "student_support"
    GOVERNANCE = "governance"
    INSTITUTIONAL_VALUES = "institutional_values"
    NEP_ALIGNMENT = "nep_alignment"
    DIGITAL_INFRASTRUCTURE = "digital_infrastructure"
    SUSTAINABILITY = "sustainability"


class AssessmentPhaseEnum(str, Enum):
    SELF_STUDY = "self_study"
    DOCUMENT_VERIFICATION = "document_verification"
    AI_ASSESSMENT = "ai_assessment"
    STAKEHOLDER_VALIDATION = "stakeholder_validation"
    FINAL_REVIEW = "final_review"
    COMPLETED = "completed"


# ==================== Accreditation Application Schemas ====================

class AccreditationApplicationBase(BaseModel):
    cycle: AccreditationCycleEnum = AccreditationCycleEnum.FIRST
    cycle_number: int = Field(default=1, ge=1, le=10)
    previous_grade: Optional[str] = None
    previous_cgpa: Optional[float] = Field(None, ge=0, le=4)


class AccreditationApplicationCreate(AccreditationApplicationBase):
    institution_id: Optional[str] = None


class AccreditationApplicationUpdate(BaseModel):
    binary_status: Optional[BinaryAccreditationStatusEnum] = None
    mbgl_level: Optional[MBGLLevelEnum] = None
    current_phase: Optional[AssessmentPhaseEnum] = None
    notes: Optional[str] = None


class AccreditationApplicationResponse(AccreditationApplicationBase):
    id: str
    application_number: str
    application_date: datetime

    # Binary Accreditation
    binary_status: BinaryAccreditationStatusEnum
    binary_status_display: str
    binary_assessment_date: Optional[datetime] = None
    binary_validity_start: Optional[datetime] = None
    binary_validity_end: Optional[datetime] = None
    binary_days_remaining: Optional[int] = None

    # MBGL
    mbgl_level: MBGLLevelEnum
    mbgl_level_display: dict
    mbgl_assessment_date: Optional[datetime] = None
    mbgl_score: Optional[float] = None
    mbgl_validity_start: Optional[datetime] = None
    mbgl_validity_end: Optional[datetime] = None

    # Current Assessment
    current_phase: AssessmentPhaseEnum
    phase_started_at: Optional[datetime] = None

    # Scores
    self_study_score: Optional[float] = None
    ai_assessment_score: Optional[float] = None
    stakeholder_score: Optional[float] = None
    final_score: Optional[float] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Attribute Score Schemas ====================

class AttributeScoreBase(BaseModel):
    attribute: AttributeCategoryEnum
    attribute_number: int = Field(ge=1, le=10)
    attribute_name: str


class AttributeScoreCreate(AttributeScoreBase):
    application_id: str
    max_score: float = 100.0
    weightage: float = 10.0


class AttributeScoreUpdate(BaseModel):
    self_assessment_score: Optional[float] = Field(None, ge=0, le=100)
    verified_score: Optional[float] = Field(None, ge=0, le=100)
    evidence_count: Optional[int] = Field(None, ge=0)
    documentation_complete: Optional[bool] = None


class AttributeScoreResponse(AttributeScoreBase):
    id: str
    application_id: str
    max_score: float
    self_assessment_score: Optional[float] = None
    verified_score: Optional[float] = None
    final_score: Optional[float] = None
    weightage: float
    evidence_count: int
    evidence_verified: int
    documentation_complete: bool
    ai_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    ai_feedback: Optional[str] = None
    is_complete: bool
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== MBGL Assessment Schemas ====================

class MBGLMaturityScores(BaseModel):
    """Maturity scores for MBGL assessment (each 1-5)"""
    leadership_maturity: int = Field(default=1, ge=1, le=5)
    process_maturity: int = Field(default=1, ge=1, le=5)
    people_maturity: int = Field(default=1, ge=1, le=5)
    technology_maturity: int = Field(default=1, ge=1, le=5)
    outcome_maturity: int = Field(default=1, ge=1, le=5)
    innovation_maturity: int = Field(default=1, ge=1, le=5)
    stakeholder_maturity: int = Field(default=1, ge=1, le=5)
    sustainability_maturity: int = Field(default=1, ge=1, le=5)


class MBGLAssessmentCreate(MBGLMaturityScores):
    application_id: str
    assessment_year: str = Field(default="2024-25")
    strengths: Optional[List[str]] = None
    improvements_needed: Optional[List[str]] = None
    action_plan: Optional[str] = None


class MBGLAssessmentUpdate(BaseModel):
    leadership_maturity: Optional[int] = Field(None, ge=1, le=5)
    process_maturity: Optional[int] = Field(None, ge=1, le=5)
    people_maturity: Optional[int] = Field(None, ge=1, le=5)
    technology_maturity: Optional[int] = Field(None, ge=1, le=5)
    outcome_maturity: Optional[int] = Field(None, ge=1, le=5)
    innovation_maturity: Optional[int] = Field(None, ge=1, le=5)
    stakeholder_maturity: Optional[int] = Field(None, ge=1, le=5)
    sustainability_maturity: Optional[int] = Field(None, ge=1, le=5)
    strengths: Optional[List[str]] = None
    improvements_needed: Optional[List[str]] = None
    action_plan: Optional[str] = None


class MBGLAssessmentResponse(MBGLMaturityScores):
    id: str
    application_id: str
    assessment_year: str
    assessment_date: datetime

    # Calculated
    average_maturity: Optional[float] = None
    weighted_score: Optional[float] = None

    # Level
    recommended_level: Optional[MBGLLevelEnum] = None
    recommended_level_display: Optional[dict] = None
    final_level: Optional[MBGLLevelEnum] = None
    final_level_display: Optional[dict] = None

    # Criteria Met
    level_1_criteria_met: bool
    level_2_criteria_met: bool
    level_3_criteria_met: bool
    level_4_criteria_met: bool
    level_5_criteria_met: bool

    # Additional Info
    strengths: Optional[List[str]] = None
    improvements_needed: Optional[List[str]] = None
    action_plan: Optional[str] = None
    assessed_by: Optional[str] = None
    verified_by: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Dashboard Schemas ====================

class AccreditationDashboardStats(BaseModel):
    """Dashboard statistics for accreditation overview"""
    # Binary Accreditation
    binary_status: BinaryAccreditationStatusEnum
    binary_status_display: str
    is_accredited: bool
    binary_validity_days: Optional[int] = None
    binary_expiry_date: Optional[str] = None

    # MBGL
    mbgl_level: MBGLLevelEnum
    mbgl_level_number: int
    mbgl_level_name: str
    mbgl_score: Optional[float] = None
    mbgl_validity_days: Optional[int] = None

    # Progress
    current_phase: AssessmentPhaseEnum
    phase_display: str
    overall_progress: float  # 0-100%

    # Attribute Scores Summary
    attributes_completed: int
    attributes_total: int
    average_attribute_score: Optional[float] = None

    # Maturity Summary (if MBGL assessed)
    maturity_scores: Optional[Dict[str, int]] = None
    average_maturity: Optional[float] = None

    # Timeline
    application_date: Optional[str] = None
    last_assessment_date: Optional[str] = None
    next_renewal_date: Optional[str] = None


class MBGLLevelInfo(BaseModel):
    """Information about an MBGL level"""
    level: MBGLLevelEnum
    number: int
    name: str
    description: str
    color: str
    min_score: float
    benefits: List[str]
    is_current: bool = False
    is_achieved: bool = False


class AccreditationFrameworkInfo(BaseModel):
    """Complete information about the accreditation framework"""
    # Binary Accreditation Info
    binary_description: str = "Binary Accreditation determines if an institution meets basic quality standards. Result: Accredited or Not Accredited."
    binary_validity_years: int = 3

    # MBGL Info
    mbgl_description: str = "Maturity-Based Graded Levels (MBGL) assess the quality maturity of accredited institutions across 8 dimensions."
    mbgl_levels: List[MBGLLevelInfo]

    # 10 Attributes
    attributes: List[Dict[str, Any]]

    # Timeline
    binary_first_available: str = "July 2024"
    mbgl_available: str = "January 2025"


# ==================== Comparison Schemas ====================

class OldVsNewFramework(BaseModel):
    """Comparison between old RAF and new framework"""
    old_system: Dict[str, Any] = {
        "name": "Revised Accreditation Framework (RAF)",
        "grading": "CGPA-based (A++, A+, A, B++, B+, B, C)",
        "criteria": 7,
        "validity": "5 years",
        "assessment": "Physical Peer Team Visit"
    }
    new_system: Dict[str, Any] = {
        "name": "Binary + MBGL Framework",
        "grading": "Binary (Accredited/Not Accredited) + MBGL (Levels 1-5)",
        "attributes": 10,
        "validity": "3 years",
        "assessment": "AI-driven + Digital Verification"
    }


# ==================== API Request/Response ====================

class BinaryAssessmentRequest(BaseModel):
    """Request for binary accreditation assessment"""
    institution_id: Optional[str] = None
    cycle: AccreditationCycleEnum = AccreditationCycleEnum.FIRST
    previous_grade: Optional[str] = None
    submit_for_review: bool = False


class BinaryAssessmentResponse(BaseModel):
    """Response for binary accreditation assessment"""
    application_id: str
    application_number: str
    status: BinaryAccreditationStatusEnum
    status_display: str
    message: str
    next_steps: List[str]


class MBGLEligibilityCheck(BaseModel):
    """Check eligibility for MBGL assessment"""
    is_eligible: bool
    binary_status: BinaryAccreditationStatusEnum
    eligibility_message: str
    requirements_met: List[str]
    requirements_pending: List[str]


class MBGLLevelCalculation(BaseModel):
    """Request to calculate MBGL level"""
    maturity_scores: MBGLMaturityScores
    include_recommendations: bool = True


class MBGLLevelResult(BaseModel):
    """Result of MBGL level calculation"""
    calculated_level: MBGLLevelEnum
    level_display: dict
    average_maturity: float
    weighted_score: float
    dimension_scores: Dict[str, Dict[str, Any]]
    strengths: List[str]
    improvements: List[str]
    recommendations: Optional[List[str]] = None
