"""
NAAC Criterion 3: Research, Innovations and Extension - Pydantic Schemas

This module defines request/response schemas for Criterion 3 API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== ENUMS ====================

class ProjectType(str, Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    COLLABORATIVE = "collaborative"
    SPONSORED = "sponsored"
    CONSULTANCY = "consultancy"


class ProjectStatus(str, Enum):
    PROPOSED = "proposed"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    EXTENDED = "extended"
    TERMINATED = "terminated"


class PublicationType(str, Enum):
    JOURNAL_INTERNATIONAL = "journal_international"
    JOURNAL_NATIONAL = "journal_national"
    CONFERENCE_INTERNATIONAL = "conference_international"
    CONFERENCE_NATIONAL = "conference_national"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    PATENT = "patent"
    THESIS = "thesis"
    OTHER = "other"


class PublicationIndexing(str, Enum):
    SCOPUS = "scopus"
    WEB_OF_SCIENCE = "web_of_science"
    UGC_CARE = "ugc_care"
    PUBMED = "pubmed"
    IEEE = "ieee"
    ACM = "acm"
    OTHER = "other"
    NONE = "none"


class PatentStatus(str, Enum):
    FILED = "filed"
    PUBLISHED = "published"
    GRANTED = "granted"
    REJECTED = "rejected"
    ABANDONED = "abandoned"


class PatentType(str, Enum):
    INDIAN = "indian"
    INTERNATIONAL = "international"
    US = "us"
    EUROPEAN = "european"
    PCT = "pct"


class StartupStage(str, Enum):
    IDEATION = "ideation"
    PROTOTYPE = "prototype"
    MVP = "mvp"
    EARLY_STAGE = "early_stage"
    GROWTH = "growth"
    ESTABLISHED = "established"


class StartupStatus(str, Enum):
    INCUBATED = "incubated"
    REGISTERED = "registered"
    OPERATIONAL = "operational"
    FUNDED = "funded"
    ACQUIRED = "acquired"
    CLOSED = "closed"


class EventType(str, Enum):
    HACKATHON = "hackathon"
    IDEATHON = "ideathon"
    WORKSHOP = "workshop"
    SEMINAR = "seminar"
    CONFERENCE = "conference"
    COMPETITION = "competition"
    EXHIBITION = "exhibition"
    BOOTCAMP = "bootcamp"


class ExtensionType(str, Enum):
    NSS = "nss"
    NCC = "ncc"
    COMMUNITY_SERVICE = "community_service"
    AWARENESS_PROGRAM = "awareness_program"
    HEALTH_CAMP = "health_camp"
    LITERACY_DRIVE = "literacy_drive"
    ENVIRONMENT = "environment"
    SKILL_DEVELOPMENT = "skill_development"
    VILLAGE_ADOPTION = "village_adoption"
    OTHER = "other"


class FundingAgency(str, Enum):
    DST = "dst"
    DBT = "dbt"
    SERB = "serb"
    CSIR = "csir"
    UGC = "ugc"
    AICTE = "aicte"
    ICMR = "icmr"
    DRDO = "drdo"
    ISRO = "isro"
    INDUSTRY = "industry"
    INTERNATIONAL = "international"
    OTHER = "other"


# ==================== RESEARCH PROJECT SCHEMAS ====================

class ResearchProjectCreate(BaseModel):
    """Schema for creating research project"""
    title: str = Field(..., min_length=5, max_length=500)
    project_type: ProjectType
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    methodology: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = None
    keywords: Optional[List[str]] = None
    start_date: date
    end_date: Optional[date] = None
    duration_months: Optional[int] = Field(None, ge=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    principal_investigator: str = Field(..., min_length=1, max_length=255)
    pi_designation: Optional[str] = None
    pi_email: Optional[str] = None
    co_investigators: Optional[List[Dict[str, str]]] = None
    student_researchers: Optional[List[Dict[str, str]]] = None
    funding_agency: Optional[FundingAgency] = None
    funding_agency_name: Optional[str] = None
    sanctioned_amount: Optional[float] = Field(None, ge=0)
    grant_number: Optional[str] = None


class ResearchProjectUpdate(BaseModel):
    """Schema for updating research project"""
    title: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    methodology: Optional[str] = None
    domain: Optional[str] = None
    keywords: Optional[List[str]] = None
    end_date: Optional[date] = None
    duration_months: Optional[int] = None
    status: Optional[ProjectStatus] = None
    co_investigators: Optional[List[Dict[str, str]]] = None
    student_researchers: Optional[List[Dict[str, str]]] = None
    received_amount: Optional[float] = None
    publications: Optional[List[str]] = None
    patents: Optional[List[str]] = None
    products_developed: Optional[List[str]] = None
    awards_received: Optional[List[str]] = None


class ResearchProjectResponse(BaseModel):
    """Schema for research project response"""
    id: str
    title: str
    project_type: str
    description: Optional[str]
    objectives: Optional[List[str]]
    methodology: Optional[str]
    department: str
    domain: Optional[str]
    keywords: Optional[List[str]]
    start_date: date
    end_date: Optional[date]
    duration_months: Optional[int]
    academic_year: str
    status: str
    principal_investigator: str
    pi_designation: Optional[str]
    pi_email: Optional[str]
    co_investigators: Optional[List[Dict[str, str]]]
    student_researchers: Optional[List[Dict[str, str]]]
    funding_agency: Optional[str]
    funding_agency_name: Optional[str]
    sanctioned_amount: Optional[float]
    received_amount: Optional[float]
    grant_number: Optional[str]
    publications: Optional[List[str]]
    patents: Optional[List[str]]
    products_developed: Optional[List[str]]
    awards_received: Optional[List[str]]
    proposal_path: Optional[str]
    sanction_letter_path: Optional[str]
    completion_report_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ResearchProjectListResponse(BaseModel):
    """Schema for paginated research project list"""
    items: List[ResearchProjectResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None
    by_status: Optional[Dict[str, int]] = None


# ==================== PUBLICATION SCHEMAS ====================

class PublicationAuthor(BaseModel):
    """Schema for publication author"""
    name: str
    affiliation: Optional[str] = None
    is_corresponding: bool = False


class PublicationCreate(BaseModel):
    """Schema for creating publication"""
    title: str = Field(..., min_length=5, max_length=1000)
    publication_type: PublicationType
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    authors: List[PublicationAuthor]
    corresponding_author: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    journal_name: Optional[str] = None
    conference_name: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publication_year: int = Field(..., ge=1900, le=2100)
    publication_date: Optional[date] = None
    indexing: PublicationIndexing = PublicationIndexing.NONE
    impact_factor: Optional[float] = Field(None, ge=0)
    doi: Optional[str] = None
    issn: Optional[str] = None
    isbn: Optional[str] = None
    paper_url: Optional[str] = None
    project_id: Optional[str] = None


class PublicationUpdate(BaseModel):
    """Schema for updating publication"""
    title: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    indexing: Optional[PublicationIndexing] = None
    impact_factor: Optional[float] = None
    citations: Optional[int] = Field(None, ge=0)
    doi: Optional[str] = None
    paper_url: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_by: Optional[str] = None


class PublicationResponse(BaseModel):
    """Schema for publication response"""
    id: str
    title: str
    publication_type: str
    abstract: Optional[str]
    keywords: Optional[List[str]]
    authors: List[Dict[str, Any]]
    corresponding_author: Optional[str]
    department: str
    journal_name: Optional[str]
    conference_name: Optional[str]
    publisher: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    publication_year: int
    publication_date: Optional[date]
    indexing: str
    impact_factor: Optional[float]
    h_index: Optional[int]
    citations: int
    doi: Optional[str]
    issn: Optional[str]
    isbn: Optional[str]
    paper_url: Optional[str]
    pdf_path: Optional[str]
    project_id: Optional[str]
    is_verified: bool
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PublicationListResponse(BaseModel):
    """Schema for paginated publication list"""
    items: List[PublicationResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None
    by_indexing: Optional[Dict[str, int]] = None


# ==================== PATENT SCHEMAS ====================

class PatentInventor(BaseModel):
    """Schema for patent inventor"""
    name: str
    designation: Optional[str] = None
    department: Optional[str] = None


class PatentCreate(BaseModel):
    """Schema for creating patent"""
    title: str = Field(..., min_length=5, max_length=1000)
    patent_type: PatentType
    description: Optional[str] = None
    claims: Optional[str] = None
    application_number: Optional[str] = None
    filing_date: date
    inventors: List[PatentInventor]
    applicant: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    ipc_class: Optional[str] = None
    technology_area: Optional[str] = None
    project_id: Optional[str] = None


class PatentUpdate(BaseModel):
    """Schema for updating patent"""
    status: Optional[PatentStatus] = None
    patent_number: Optional[str] = None
    publication_date: Optional[date] = None
    grant_date: Optional[date] = None
    is_commercialized: Optional[bool] = None
    commercialization_details: Optional[str] = None
    revenue_generated: Optional[float] = None


class PatentResponse(BaseModel):
    """Schema for patent response"""
    id: str
    title: str
    patent_type: str
    status: str
    description: Optional[str]
    claims: Optional[str]
    application_number: Optional[str]
    patent_number: Optional[str]
    filing_date: date
    filing_year: int
    publication_date: Optional[date]
    grant_date: Optional[date]
    inventors: List[Dict[str, Any]]
    applicant: Optional[str]
    department: str
    ipc_class: Optional[str]
    technology_area: Optional[str]
    is_commercialized: bool
    commercialization_details: Optional[str]
    revenue_generated: Optional[float]
    application_path: Optional[str]
    certificate_path: Optional[str]
    project_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PatentListResponse(BaseModel):
    """Schema for paginated patent list"""
    items: List[PatentResponse]
    total: int
    page: int
    page_size: int
    by_status: Optional[Dict[str, int]] = None
    by_type: Optional[Dict[str, int]] = None


# ==================== STARTUP SCHEMAS ====================

class StartupFounder(BaseModel):
    """Schema for startup founder"""
    name: str
    role: Optional[str] = None
    is_student: bool = False


class StartupCreate(BaseModel):
    """Schema for creating startup"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    problem_statement: Optional[str] = None
    solution: Optional[str] = None
    industry_sector: Optional[str] = None
    technology_used: Optional[List[str]] = None
    stage: StartupStage = StartupStage.IDEATION
    founders: List[StartupFounder]
    department: str = Field(..., min_length=1, max_length=255)
    incubated_at: Optional[str] = None
    founded_date: Optional[date] = None
    website: Optional[str] = None
    email: Optional[str] = None


class StartupUpdate(BaseModel):
    """Schema for updating startup"""
    description: Optional[str] = None
    stage: Optional[StartupStage] = None
    status: Optional[StartupStatus] = None
    registration_number: Optional[str] = None
    registration_date: Optional[date] = None
    dpiit_recognized: Optional[bool] = None
    dpiit_number: Optional[str] = None
    seed_funding: Optional[float] = None
    total_funding: Optional[float] = None
    funding_rounds: Optional[List[Dict[str, Any]]] = None
    investors: Optional[List[str]] = None
    revenue: Optional[float] = None
    employees_count: Optional[int] = None
    products_services: Optional[List[str]] = None
    awards: Optional[List[Dict[str, Any]]] = None
    website: Optional[str] = None


class StartupResponse(BaseModel):
    """Schema for startup response"""
    id: str
    name: str
    description: Optional[str]
    problem_statement: Optional[str]
    solution: Optional[str]
    industry_sector: Optional[str]
    technology_used: Optional[List[str]]
    stage: str
    status: str
    founders: List[Dict[str, Any]]
    department: str
    incubated_at: Optional[str]
    registration_number: Optional[str]
    registration_date: Optional[date]
    dpiit_recognized: bool
    dpiit_number: Optional[str]
    seed_funding: Optional[float]
    total_funding: Optional[float]
    funding_rounds: Optional[List[Dict[str, Any]]]
    investors: Optional[List[str]]
    revenue: Optional[float]
    employees_count: Optional[int]
    products_services: Optional[List[str]]
    awards: Optional[List[Dict[str, Any]]]
    website: Optional[str]
    email: Optional[str]
    founded_date: Optional[date]
    pitch_deck_path: Optional[str]
    registration_certificate_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StartupListResponse(BaseModel):
    """Schema for paginated startup list"""
    items: List[StartupResponse]
    total: int
    page: int
    page_size: int
    by_stage: Optional[Dict[str, int]] = None
    by_status: Optional[Dict[str, int]] = None


# ==================== INNOVATION CELL SCHEMAS ====================

class InnovationCellCreate(BaseModel):
    """Schema for creating innovation cell"""
    name: str = Field(..., min_length=1, max_length=255)
    cell_type: str = Field(..., min_length=1, max_length=100)
    registration_number: Optional[str] = None
    establishment_date: Optional[date] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    coordinator_name: str = Field(..., min_length=1, max_length=255)
    coordinator_designation: Optional[str] = None
    coordinator_email: Optional[str] = None
    coordinator_phone: Optional[str] = None
    faculty_members: Optional[List[Dict[str, str]]] = None
    student_members: Optional[List[Dict[str, str]]] = None
    external_mentors: Optional[List[Dict[str, str]]] = None
    annual_budget: Optional[float] = Field(None, ge=0)


class InnovationCellUpdate(BaseModel):
    """Schema for updating innovation cell"""
    coordinator_name: Optional[str] = None
    coordinator_email: Optional[str] = None
    faculty_members: Optional[List[Dict[str, str]]] = None
    student_members: Optional[List[Dict[str, str]]] = None
    external_mentors: Optional[List[Dict[str, str]]] = None
    activities_conducted: Optional[List[Dict[str, Any]]] = None
    workshops_count: Optional[int] = None
    seminars_count: Optional[int] = None
    hackathons_count: Optional[int] = None
    ideas_generated: Optional[int] = None
    prototypes_developed: Optional[int] = None
    startups_incubated: Optional[int] = None
    patents_filed: Optional[int] = None
    iic_star_rating: Optional[int] = Field(None, ge=1, le=5)
    mhrd_points: Optional[float] = None
    funds_utilized: Optional[float] = None
    is_active: Optional[bool] = None


class InnovationCellResponse(BaseModel):
    """Schema for innovation cell response"""
    id: str
    name: str
    cell_type: str
    registration_number: Optional[str]
    establishment_date: Optional[date]
    academic_year: str
    coordinator_name: str
    coordinator_designation: Optional[str]
    coordinator_email: Optional[str]
    coordinator_phone: Optional[str]
    faculty_members: Optional[List[Dict[str, str]]]
    student_members: Optional[List[Dict[str, str]]]
    external_mentors: Optional[List[Dict[str, str]]]
    activities_conducted: Optional[List[Dict[str, Any]]]
    workshops_count: int
    seminars_count: int
    hackathons_count: int
    ideas_generated: int
    prototypes_developed: int
    startups_incubated: int
    patents_filed: int
    iic_star_rating: Optional[int]
    mhrd_points: Optional[float]
    annual_budget: Optional[float]
    funds_utilized: Optional[float]
    annual_report_path: Optional[str]
    registration_certificate_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InnovationCellListResponse(BaseModel):
    """Schema for paginated innovation cell list"""
    items: List[InnovationCellResponse]
    total: int
    page: int
    page_size: int


# ==================== HACKATHON SCHEMAS ====================

class HackathonCreate(BaseModel):
    """Schema for creating hackathon"""
    name: str = Field(..., min_length=1, max_length=500)
    event_type: EventType
    description: Optional[str] = None
    theme: Optional[str] = None
    problem_statements: Optional[List[str]] = None
    organized_by: str = Field(..., min_length=1, max_length=255)
    is_internal: bool = True
    department: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    event_date: date
    end_date: Optional[date] = None
    duration_hours: Optional[int] = Field(None, ge=1)
    venue: Optional[str] = None
    mode: Optional[str] = None
    total_prize_pool: Optional[float] = Field(None, ge=0)
    sponsors: Optional[List[str]] = None


class HackathonUpdate(BaseModel):
    """Schema for updating hackathon"""
    description: Optional[str] = None
    registrations_count: Optional[int] = None
    participants_count: Optional[int] = None
    teams_count: Optional[int] = None
    submissions_count: Optional[int] = None
    winners: Optional[List[Dict[str, Any]]] = None
    college_participants: Optional[List[Dict[str, str]]] = None
    college_achievements: Optional[List[Dict[str, Any]]] = None
    prizes: Optional[List[Dict[str, Any]]] = None


class HackathonResponse(BaseModel):
    """Schema for hackathon response"""
    id: str
    name: str
    event_type: str
    description: Optional[str]
    theme: Optional[str]
    problem_statements: Optional[List[str]]
    organized_by: str
    is_internal: bool
    department: Optional[str]
    academic_year: str
    event_date: date
    end_date: Optional[date]
    duration_hours: Optional[int]
    venue: Optional[str]
    mode: Optional[str]
    registrations_count: int
    participants_count: int
    teams_count: int
    submissions_count: int
    winners: Optional[List[Dict[str, Any]]]
    college_participants: Optional[List[Dict[str, str]]]
    college_achievements: Optional[List[Dict[str, Any]]]
    total_prize_pool: Optional[float]
    prizes: Optional[List[Dict[str, Any]]]
    sponsors: Optional[List[str]]
    brochure_path: Optional[str]
    report_path: Optional[str]
    photos_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class HackathonListResponse(BaseModel):
    """Schema for paginated hackathon list"""
    items: List[HackathonResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None


# ==================== EXTENSION ACTIVITY SCHEMAS ====================

class ExtensionActivityCreate(BaseModel):
    """Schema for creating extension activity"""
    title: str = Field(..., min_length=1, max_length=500)
    activity_type: ExtensionType
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    organized_by: str = Field(..., min_length=1, max_length=255)
    department: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    venue: Optional[str] = None
    village_adopted: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    activity_date: date
    end_date: Optional[date] = None
    duration_days: int = Field(default=1, ge=1)
    faculty_involved: Optional[List[Dict[str, str]]] = None
    students_participated: int = Field(default=0, ge=0)
    beneficiaries_count: int = Field(default=0, ge=0)
    beneficiaries_type: Optional[str] = None
    collaborating_agencies: Optional[List[str]] = None
    funding_received: Optional[float] = Field(None, ge=0)
    funding_source: Optional[str] = None


class ExtensionActivityUpdate(BaseModel):
    """Schema for updating extension activity"""
    description: Optional[str] = None
    outcomes: Optional[List[str]] = None
    student_list: Optional[List[Dict[str, str]]] = None
    beneficiaries_count: Optional[int] = None
    impact_description: Optional[str] = None
    sdg_goals_addressed: Optional[List[int]] = None
    media_coverage: Optional[List[Dict[str, str]]] = None
    awards_received: Optional[List[Dict[str, Any]]] = None


class ExtensionActivityResponse(BaseModel):
    """Schema for extension activity response"""
    id: str
    title: str
    activity_type: str
    description: Optional[str]
    objectives: Optional[List[str]]
    outcomes: Optional[List[str]]
    organized_by: str
    department: Optional[str]
    academic_year: str
    venue: Optional[str]
    village_adopted: Optional[str]
    district: Optional[str]
    state: Optional[str]
    activity_date: date
    end_date: Optional[date]
    duration_days: int
    faculty_involved: Optional[List[Dict[str, str]]]
    students_participated: int
    student_list: Optional[List[Dict[str, str]]]
    beneficiaries_count: int
    beneficiaries_type: Optional[str]
    collaborating_agencies: Optional[List[str]]
    funding_received: Optional[float]
    funding_source: Optional[str]
    impact_description: Optional[str]
    sdg_goals_addressed: Optional[List[int]]
    media_coverage: Optional[List[Dict[str, str]]]
    awards_received: Optional[List[Dict[str, Any]]]
    report_path: Optional[str]
    photos_path: Optional[str]
    certificate_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ExtensionActivityListResponse(BaseModel):
    """Schema for paginated extension activity list"""
    items: List[ExtensionActivityResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None


# ==================== CONSULTANCY SCHEMAS ====================

class ConsultancyCreate(BaseModel):
    """Schema for creating consultancy"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    scope_of_work: Optional[str] = None
    deliverables: Optional[List[str]] = None
    client_name: str = Field(..., min_length=1, max_length=500)
    client_type: Optional[str] = None
    client_contact: Optional[str] = None
    client_email: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    consultant_name: str = Field(..., min_length=1, max_length=255)
    consultant_designation: Optional[str] = None
    team_members: Optional[List[Dict[str, str]]] = None
    start_date: date
    end_date: Optional[date] = None
    consultancy_amount: float = Field(..., gt=0)
    mou_number: Optional[str] = None
    mou_date: Optional[date] = None


class ConsultancyUpdate(BaseModel):
    """Schema for updating consultancy"""
    description: Optional[str] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatus] = None
    amount_received: Optional[float] = None
    institute_share: Optional[float] = None


class ConsultancyResponse(BaseModel):
    """Schema for consultancy response"""
    id: str
    title: str
    description: Optional[str]
    scope_of_work: Optional[str]
    deliverables: Optional[List[str]]
    client_name: str
    client_type: Optional[str]
    client_contact: Optional[str]
    client_email: Optional[str]
    department: str
    academic_year: str
    consultant_name: str
    consultant_designation: Optional[str]
    team_members: Optional[List[Dict[str, str]]]
    start_date: date
    end_date: Optional[date]
    status: str
    consultancy_amount: float
    amount_received: Optional[float]
    institute_share: Optional[float]
    mou_number: Optional[str]
    mou_date: Optional[date]
    mou_path: Optional[str]
    completion_certificate_path: Optional[str]
    payment_receipt_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ConsultancyListResponse(BaseModel):
    """Schema for paginated consultancy list"""
    items: List[ConsultancyResponse]
    total: int
    page: int
    page_size: int
    total_amount: Optional[float] = None


# ==================== RESEARCH FUNDING SCHEMAS ====================

class ResearchFundingCreate(BaseModel):
    """Schema for creating research funding"""
    scheme_name: str = Field(..., min_length=1, max_length=500)
    funding_agency: FundingAgency
    agency_name: Optional[str] = None
    project_id: Optional[str] = None
    project_title: Optional[str] = None
    pi_name: str = Field(..., min_length=1, max_length=255)
    pi_designation: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    sanctioned_amount: float = Field(..., gt=0)
    grant_number: Optional[str] = None
    sanction_date: Optional[date] = None
    duration_years: Optional[int] = Field(None, ge=1)


class ResearchFundingUpdate(BaseModel):
    """Schema for updating research funding"""
    received_amount: Optional[float] = None
    utilized_amount: Optional[float] = None


class ResearchFundingResponse(BaseModel):
    """Schema for research funding response"""
    id: str
    scheme_name: str
    funding_agency: str
    agency_name: Optional[str]
    project_id: Optional[str]
    project_title: Optional[str]
    pi_name: str
    pi_designation: Optional[str]
    department: str
    financial_year: str
    sanctioned_amount: float
    received_amount: Optional[float]
    utilized_amount: Optional[float]
    grant_number: Optional[str]
    sanction_date: Optional[date]
    duration_years: Optional[int]
    sanction_letter_path: Optional[str]
    utilization_certificate_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ResearchFundingListResponse(BaseModel):
    """Schema for paginated research funding list"""
    items: List[ResearchFundingResponse]
    total: int
    page: int
    page_size: int
    total_sanctioned: Optional[float] = None
    total_received: Optional[float] = None
    by_agency: Optional[Dict[str, float]] = None


# ==================== DASHBOARD & REPORT SCHEMAS ====================

class Criterion3DashboardStats(BaseModel):
    """Dashboard statistics for Criterion 3"""
    # Key Indicator 3.1: Resource Mobilization
    total_projects: int
    ongoing_projects: int
    completed_projects: int
    total_funding_sanctioned: float
    total_funding_received: float
    funding_by_agency: Dict[str, float]

    # Key Indicator 3.2: Innovation Ecosystem
    total_patents_filed: int
    patents_granted: int
    total_startups: int
    startups_funded: int
    innovation_cells: int
    iic_star_rating: Optional[int]

    # Key Indicator 3.3: Research Publications
    total_publications: int
    publications_by_type: Dict[str, int]
    publications_by_indexing: Dict[str, int]
    total_citations: int
    average_impact_factor: float

    # Key Indicator 3.4: Extension Activities
    total_extension_activities: int
    students_participated: int
    beneficiaries_reached: int
    extension_by_type: Dict[str, int]

    # Key Indicator 3.5: Collaboration
    total_consultancies: int
    consultancy_revenue: float
    hackathons_conducted: int

    # Overall readiness
    completion_percentage: float
    pending_items: List[Dict[str, Any]]


class Criterion3ReportRequest(BaseModel):
    """Request schema for generating Criterion 3 report"""
    institution_name: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    department: Optional[str] = None
    include_sections: Optional[List[str]] = None
    format: str = Field(default="docx", pattern=r"^(docx|pdf)$")
    include_analytics: bool = True


class Criterion3ReportResponse(BaseModel):
    """Response schema for generated report"""
    success: bool
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    sections_included: List[str]
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
