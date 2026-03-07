"""
NAAC Criterion 7: Institutional Values and Best Practices - Pydantic Schemas

This module defines request/response schemas for Criterion 7 API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== ENUMS ====================

class GreenInitiativeType(str, Enum):
    SOLAR_ENERGY = "solar_energy"
    RAINWATER_HARVESTING = "rainwater_harvesting"
    WASTE_MANAGEMENT = "waste_management"
    E_WASTE = "e_waste"
    GREEN_AUDIT = "green_audit"
    PLANTATION = "plantation"
    CARBON_FOOTPRINT = "carbon_footprint"
    WATER_CONSERVATION = "water_conservation"
    ENERGY_AUDIT = "energy_audit"
    RECYCLING = "recycling"
    OTHER = "other"


class InclusivityType(str, Enum):
    DIVYANGJAN = "divyangjan"
    ECONOMICALLY_WEAKER = "economically_weaker"
    SC_ST = "sc_st"
    OBC = "obc"
    MINORITY = "minority"
    WOMEN = "women"
    FIRST_GENERATION = "first_generation"
    TRANSGENDER = "transgender"
    OTHER = "other"


class EthicsType(str, Enum):
    CODE_OF_CONDUCT = "code_of_conduct"
    ANTI_RAGGING = "anti_ragging"
    SEXUAL_HARASSMENT = "sexual_harassment"
    ACADEMIC_INTEGRITY = "academic_integrity"
    RESEARCH_ETHICS = "research_ethics"
    PROFESSIONAL_ETHICS = "professional_ethics"
    HUMAN_VALUES = "human_values"
    OTHER = "other"


class BestPracticeCategory(str, Enum):
    TEACHING_LEARNING = "teaching_learning"
    RESEARCH = "research"
    EXTENSION = "extension"
    STUDENT_SUPPORT = "student_support"
    GOVERNANCE = "governance"
    INFRASTRUCTURE = "infrastructure"
    INDUSTRY_COLLABORATION = "industry_collaboration"
    COMMUNITY_ENGAGEMENT = "community_engagement"
    INNOVATION = "innovation"
    SUSTAINABILITY = "sustainability"
    OTHER = "other"


class AwardCategory(str, Enum):
    NATIONAL = "national"
    STATE = "state"
    UNIVERSITY = "university"
    ACCREDITATION = "accreditation"
    RANKING = "ranking"
    INDUSTRY = "industry"
    MEDIA = "media"
    OTHER = "other"


# ==================== GENDER EQUITY PROGRAM SCHEMAS ====================

class GenderEquityProgramCreate(BaseModel):
    """Schema for creating gender equity program"""
    program_name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    program_type: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    start_date: date
    end_date: Optional[date] = None
    organized_by: Optional[str] = None
    target_group: Optional[str] = None


class GenderEquityProgramUpdate(BaseModel):
    """Schema for updating gender equity program"""
    activities_conducted: Optional[List[Dict[str, Any]]] = None
    participants_count: Optional[int] = None
    male_participants: Optional[int] = None
    female_participants: Optional[int] = None
    resource_persons: Optional[List[Dict[str, str]]] = None
    outcomes: Optional[List[str]] = None
    impact: Optional[str] = None
    budget: Optional[float] = None
    expenditure: Optional[float] = None


class GenderEquityProgramResponse(BaseModel):
    """Schema for gender equity program response"""
    id: str
    program_name: str
    description: Optional[str]
    objectives: Optional[List[str]]
    program_type: Optional[str]
    academic_year: str
    start_date: date
    end_date: Optional[date]
    organized_by: Optional[str]
    target_group: Optional[str]
    activities_conducted: Optional[List[Dict[str, Any]]]
    participants_count: int
    male_participants: int
    female_participants: int
    resource_persons: Optional[List[Dict[str, str]]]
    outcomes: Optional[List[str]]
    impact: Optional[str]
    budget: Optional[float]
    expenditure: Optional[float]
    report_path: Optional[str]
    photos_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class GenderEquityProgramListResponse(BaseModel):
    """Schema for paginated gender equity program list"""
    items: List[GenderEquityProgramResponse]
    total: int
    page: int
    page_size: int
    total_participants: Optional[int] = None


# ==================== GREEN INITIATIVE SCHEMAS ====================

class GreenInitiativeCreate(BaseModel):
    """Schema for creating green initiative"""
    initiative_name: str = Field(..., min_length=1, max_length=500)
    initiative_type: GreenInitiativeType
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    implementation_date: date
    location: Optional[str] = None
    responsible_department: Optional[str] = None
    coordinator: Optional[str] = None


class GreenInitiativeUpdate(BaseModel):
    """Schema for updating green initiative"""
    capacity: Optional[str] = None
    investment: Optional[float] = None
    annual_savings: Optional[float] = None
    carbon_reduction_kg: Optional[float] = None
    water_saved_liters: Optional[float] = None
    energy_saved_kwh: Optional[float] = None
    waste_recycled_kg: Optional[float] = None
    trees_planted: Optional[int] = None
    certifications: Optional[List[str]] = None
    awards_received: Optional[List[Dict[str, Any]]] = None
    sdg_goals_addressed: Optional[List[int]] = None
    impact_metrics: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class GreenInitiativeResponse(BaseModel):
    """Schema for green initiative response"""
    id: str
    initiative_name: str
    initiative_type: str
    description: Optional[str]
    objectives: Optional[List[str]]
    academic_year: str
    implementation_date: date
    location: Optional[str]
    responsible_department: Optional[str]
    coordinator: Optional[str]
    capacity: Optional[str]
    investment: Optional[float]
    annual_savings: Optional[float]
    carbon_reduction_kg: Optional[float]
    water_saved_liters: Optional[float]
    energy_saved_kwh: Optional[float]
    waste_recycled_kg: Optional[float]
    trees_planted: Optional[int]
    certifications: Optional[List[str]]
    awards_received: Optional[List[Dict[str, Any]]]
    sdg_goals_addressed: Optional[List[int]]
    impact_metrics: Optional[Dict[str, Any]]
    audit_report_path: Optional[str]
    photos_path: Optional[str]
    certificate_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class GreenInitiativeListResponse(BaseModel):
    """Schema for paginated green initiative list"""
    items: List[GreenInitiativeResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None
    total_investment: Optional[float] = None
    total_savings: Optional[float] = None


# ==================== INCLUSIVITY PROGRAM SCHEMAS ====================

class InclusivityProgramCreate(BaseModel):
    """Schema for creating inclusivity program"""
    program_name: str = Field(..., min_length=1, max_length=500)
    inclusivity_type: InclusivityType
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    implementation_date: date
    target_group: Optional[str] = None
    beneficiaries_count: int = Field(default=0, ge=0)


class InclusivityProgramUpdate(BaseModel):
    """Schema for updating inclusivity program"""
    facilities_provided: Optional[List[str]] = None
    financial_support: Optional[float] = None
    scholarships_provided: Optional[int] = None
    special_provisions: Optional[List[str]] = None
    accessibility_features: Optional[List[str]] = None
    sensitization_programs: Optional[List[Dict[str, Any]]] = None
    outcomes: Optional[List[str]] = None
    impact: Optional[str] = None
    is_active: Optional[bool] = None


class InclusivityProgramResponse(BaseModel):
    """Schema for inclusivity program response"""
    id: str
    program_name: str
    inclusivity_type: str
    description: Optional[str]
    objectives: Optional[List[str]]
    academic_year: str
    implementation_date: date
    target_group: Optional[str]
    beneficiaries_count: int
    facilities_provided: Optional[List[str]]
    financial_support: Optional[float]
    scholarships_provided: int
    special_provisions: Optional[List[str]]
    accessibility_features: Optional[List[str]]
    sensitization_programs: Optional[List[Dict[str, Any]]]
    outcomes: Optional[List[str]]
    impact: Optional[str]
    policy_document_path: Optional[str]
    report_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InclusivityProgramListResponse(BaseModel):
    """Schema for paginated inclusivity program list"""
    items: List[InclusivityProgramResponse]
    total: int
    page: int
    page_size: int
    total_beneficiaries: Optional[int] = None
    by_type: Optional[Dict[str, int]] = None


# ==================== ETHICS PROGRAM SCHEMAS ====================

class EthicsProgramCreate(BaseModel):
    """Schema for creating ethics program"""
    program_name: str = Field(..., min_length=1, max_length=500)
    ethics_type: EthicsType
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    implementation_date: date
    responsible_committee: Optional[str] = None
    coordinator: Optional[str] = None


class EthicsProgramUpdate(BaseModel):
    """Schema for updating ethics program"""
    activities_conducted: Optional[List[Dict[str, Any]]] = None
    participants_count: Optional[int] = None
    sessions_conducted: Optional[int] = None
    cases_handled: Optional[int] = None
    cases_resolved: Optional[int] = None
    awareness_programs: Optional[List[Dict[str, Any]]] = None
    outcomes: Optional[List[str]] = None
    is_active: Optional[bool] = None


class EthicsProgramResponse(BaseModel):
    """Schema for ethics program response"""
    id: str
    program_name: str
    ethics_type: str
    description: Optional[str]
    objectives: Optional[List[str]]
    academic_year: str
    implementation_date: date
    responsible_committee: Optional[str]
    coordinator: Optional[str]
    activities_conducted: Optional[List[Dict[str, Any]]]
    participants_count: int
    sessions_conducted: int
    cases_handled: int
    cases_resolved: int
    awareness_programs: Optional[List[Dict[str, Any]]]
    outcomes: Optional[List[str]]
    policy_document_path: Optional[str]
    committee_details_path: Optional[str]
    report_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class EthicsProgramListResponse(BaseModel):
    """Schema for paginated ethics program list"""
    items: List[EthicsProgramResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None
    total_cases_resolved: Optional[int] = None


# ==================== BEST PRACTICE SCHEMAS ====================

class BestPracticeCreate(BaseModel):
    """Schema for creating best practice"""
    title: str = Field(..., min_length=1, max_length=500)
    category: BestPracticeCategory
    objective: str = Field(..., min_length=10)
    context: Optional[str] = None
    the_practice: str = Field(..., min_length=50)
    evidence_of_success: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    introduced_year: Optional[int] = None
    department: Optional[str] = None


class BestPracticeUpdate(BaseModel):
    """Schema for updating best practice"""
    problems_encountered: Optional[str] = None
    resources_required: Optional[List[str]] = None
    notes: Optional[str] = None
    outcomes: Optional[List[str]] = None
    impact_metrics: Optional[Dict[str, Any]] = None
    beneficiaries: Optional[int] = None
    awards_recognition: Optional[List[Dict[str, Any]]] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class BestPracticeResponse(BaseModel):
    """Schema for best practice response"""
    id: str
    title: str
    category: str
    objective: str
    context: Optional[str]
    the_practice: str
    evidence_of_success: Optional[str]
    problems_encountered: Optional[str]
    resources_required: Optional[List[str]]
    notes: Optional[str]
    academic_year: str
    introduced_year: Optional[int]
    department: Optional[str]
    outcomes: Optional[List[str]]
    impact_metrics: Optional[Dict[str, Any]]
    beneficiaries: int
    awards_recognition: Optional[List[Dict[str, Any]]]
    documentation_path: Optional[str]
    photos_path: Optional[str]
    video_url: Optional[str]
    is_featured: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class BestPracticeListResponse(BaseModel):
    """Schema for paginated best practice list"""
    items: List[BestPracticeResponse]
    total: int
    page: int
    page_size: int
    by_category: Optional[Dict[str, int]] = None
    featured_count: Optional[int] = None


# ==================== INSTITUTIONAL DISTINCTIVENESS SCHEMAS ====================

class InstitutionalDistinctivenessCreate(BaseModel):
    """Schema for creating institutional distinctiveness"""
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=50)
    unique_features: Optional[List[str]] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    year_established: Optional[int] = None


class InstitutionalDistinctivenessUpdate(BaseModel):
    """Schema for updating institutional distinctiveness"""
    achievements: Optional[List[Dict[str, Any]]] = None
    impact_on_students: Optional[str] = None
    impact_on_society: Optional[str] = None
    national_recognition: Optional[List[str]] = None
    international_recognition: Optional[List[str]] = None
    media_coverage: Optional[List[Dict[str, str]]] = None
    is_active: Optional[bool] = None


class InstitutionalDistinctivenessResponse(BaseModel):
    """Schema for institutional distinctiveness response"""
    id: str
    title: str
    description: str
    unique_features: Optional[List[str]]
    academic_year: str
    year_established: Optional[int]
    achievements: Optional[List[Dict[str, Any]]]
    impact_on_students: Optional[str]
    impact_on_society: Optional[str]
    national_recognition: Optional[List[str]]
    international_recognition: Optional[List[str]]
    media_coverage: Optional[List[Dict[str, str]]]
    documentation_path: Optional[str]
    photos_path: Optional[str]
    video_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InstitutionalDistinctivenessListResponse(BaseModel):
    """Schema for paginated institutional distinctiveness list"""
    items: List[InstitutionalDistinctivenessResponse]
    total: int
    page: int
    page_size: int


# ==================== INSTITUTIONAL AWARD SCHEMAS ====================

class InstitutionalAwardCreate(BaseModel):
    """Schema for creating institutional award"""
    award_name: str = Field(..., min_length=1, max_length=500)
    category: AwardCategory
    awarding_body: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    award_date: date
    rank: Optional[str] = None
    score: Optional[float] = None


class InstitutionalAwardUpdate(BaseModel):
    """Schema for updating institutional award"""
    significance: Optional[str] = None
    selection_criteria: Optional[str] = None
    competition_details: Optional[str] = None
    media_coverage: Optional[List[Dict[str, str]]] = None


class InstitutionalAwardResponse(BaseModel):
    """Schema for institutional award response"""
    id: str
    award_name: str
    category: str
    awarding_body: str
    description: Optional[str]
    academic_year: str
    award_date: date
    rank: Optional[str]
    score: Optional[float]
    significance: Optional[str]
    selection_criteria: Optional[str]
    competition_details: Optional[str]
    media_coverage: Optional[List[Dict[str, str]]]
    certificate_path: Optional[str]
    photos_path: Optional[str]
    press_release_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InstitutionalAwardListResponse(BaseModel):
    """Schema for paginated institutional award list"""
    items: List[InstitutionalAwardResponse]
    total: int
    page: int
    page_size: int
    by_category: Optional[Dict[str, int]] = None


# ==================== DASHBOARD & REPORT SCHEMAS ====================

class Criterion7DashboardStats(BaseModel):
    """Dashboard statistics for Criterion 7"""
    # Key Indicator 7.1: Institutional Values
    gender_equity_programs: int
    sensitization_programs: int
    total_participants_gender: int
    women_empowerment_initiatives: int

    # Key Indicator 7.2: Best Practices
    total_best_practices: int
    featured_practices: int
    best_practices_by_category: Dict[str, int]

    # Key Indicator 7.3: Institutional Distinctiveness
    distinctiveness_items: int
    national_recognitions: int
    international_recognitions: int

    # Green Campus Initiatives
    total_green_initiatives: int
    solar_capacity_kw: float
    water_harvesting_capacity: float
    trees_planted: int
    carbon_footprint_reduced: float
    green_audit_completed: bool

    # Inclusivity
    inclusivity_programs: int
    total_beneficiaries: int
    scholarships_for_disadvantaged: int

    # Ethics & Values
    ethics_programs: int
    code_of_conduct_implemented: bool
    anti_ragging_measures: int
    cases_resolved: int

    # Awards & Recognition
    total_awards: int
    national_awards: int
    accreditation_status: Dict[str, Any]
    nirf_rank: Optional[int]

    # SDG Goals
    sdg_goals_addressed: List[int]
    sdg_initiatives: int

    # Overall readiness
    completion_percentage: float
    pending_items: List[Dict[str, Any]]


class Criterion7ReportRequest(BaseModel):
    """Request schema for generating Criterion 7 report"""
    institution_name: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    include_sections: Optional[List[str]] = None
    format: str = Field(default="docx", pattern=r"^(docx|pdf)$")
    include_analytics: bool = True


class Criterion7ReportResponse(BaseModel):
    """Response schema for generated report"""
    success: bool
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    sections_included: List[str]
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
