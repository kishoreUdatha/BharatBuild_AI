"""
NAAC Criterion 3: Research, Innovations and Extension - Database Models

This module defines database models for managing NAAC Criterion 3 requirements:
- Research Projects (Student & Faculty)
- Publications (Journals, Conferences)
- Patents (Filed/Granted)
- Startups & Spin-offs
- Innovation Cell / IIC
- Hackathons & Competitions
- Extension Activities (Community Outreach)
- Consultancy Projects
- Research Funding
"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== ENUMS ====================

class ProjectType(str, enum.Enum):
    """Research project types"""
    STUDENT = "student"
    FACULTY = "faculty"
    COLLABORATIVE = "collaborative"
    SPONSORED = "sponsored"
    CONSULTANCY = "consultancy"


class ProjectStatus(str, enum.Enum):
    """Project status"""
    PROPOSED = "proposed"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    EXTENDED = "extended"
    TERMINATED = "terminated"


class PublicationType(str, enum.Enum):
    """Publication types"""
    JOURNAL_INTERNATIONAL = "journal_international"
    JOURNAL_NATIONAL = "journal_national"
    CONFERENCE_INTERNATIONAL = "conference_international"
    CONFERENCE_NATIONAL = "conference_national"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    PATENT = "patent"
    THESIS = "thesis"
    OTHER = "other"


class PublicationIndexing(str, enum.Enum):
    """Publication indexing"""
    SCOPUS = "scopus"
    WEB_OF_SCIENCE = "web_of_science"
    UGC_CARE = "ugc_care"
    PUBMED = "pubmed"
    IEEE = "ieee"
    ACM = "acm"
    OTHER = "other"
    NONE = "none"


class PatentStatus(str, enum.Enum):
    """Patent status"""
    FILED = "filed"
    PUBLISHED = "published"
    GRANTED = "granted"
    REJECTED = "rejected"
    ABANDONED = "abandoned"


class PatentType(str, enum.Enum):
    """Patent type"""
    INDIAN = "indian"
    INTERNATIONAL = "international"
    US = "us"
    EUROPEAN = "european"
    PCT = "pct"


class StartupStage(str, enum.Enum):
    """Startup stage"""
    IDEATION = "ideation"
    PROTOTYPE = "prototype"
    MVP = "mvp"
    EARLY_STAGE = "early_stage"
    GROWTH = "growth"
    ESTABLISHED = "established"


class StartupStatus(str, enum.Enum):
    """Startup status"""
    INCUBATED = "incubated"
    REGISTERED = "registered"
    OPERATIONAL = "operational"
    FUNDED = "funded"
    ACQUIRED = "acquired"
    CLOSED = "closed"


class EventType(str, enum.Enum):
    """Event/competition type"""
    HACKATHON = "hackathon"
    IDEATHON = "ideathon"
    WORKSHOP = "workshop"
    SEMINAR = "seminar"
    CONFERENCE = "conference"
    COMPETITION = "competition"
    EXHIBITION = "exhibition"
    BOOTCAMP = "bootcamp"


class ExtensionType(str, enum.Enum):
    """Extension activity types"""
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


class FundingAgency(str, enum.Enum):
    """Major funding agencies"""
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


# ==================== MODELS ====================

class ResearchProject(Base):
    """
    Research Projects - Student and Faculty.
    Key Indicator 3.1: Resource Mobilization for Research
    """
    __tablename__ = "research_projects"

    __table_args__ = (
        Index('ix_research_projects_type', 'project_type'),
        Index('ix_research_projects_status', 'status'),
        Index('ix_research_projects_department', 'department'),
        Index('ix_research_projects_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Project details
    title = Column(String(500), nullable=False)
    project_type = Column(SQLEnum(ProjectType), nullable=False)
    description = Column(Text, nullable=True)
    objectives = Column(JSON, nullable=True)  # ["obj1", "obj2"]
    methodology = Column(Text, nullable=True)

    # Department and domain
    department = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)  # AI, IoT, Healthcare, etc.
    keywords = Column(JSON, nullable=True)

    # Duration
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    duration_months = Column(Integer, nullable=True)
    academic_year = Column(String(20), nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PROPOSED)

    # Team
    principal_investigator = Column(String(255), nullable=False)
    pi_designation = Column(String(100), nullable=True)
    pi_email = Column(String(255), nullable=True)
    co_investigators = Column(JSON, nullable=True)  # [{"name": "", "affiliation": ""}]
    student_researchers = Column(JSON, nullable=True)  # [{"name": "", "roll_no": ""}]

    # Funding
    funding_agency = Column(SQLEnum(FundingAgency), nullable=True)
    funding_agency_name = Column(String(255), nullable=True)
    sanctioned_amount = Column(Float, nullable=True)
    received_amount = Column(Float, nullable=True)
    grant_number = Column(String(100), nullable=True)

    # Outcomes
    publications = Column(JSON, nullable=True)  # List of publication IDs or references
    patents = Column(JSON, nullable=True)
    products_developed = Column(JSON, nullable=True)
    awards_received = Column(JSON, nullable=True)

    # Documents
    proposal_path = Column(String(500), nullable=True)
    sanction_letter_path = Column(String(500), nullable=True)
    completion_report_path = Column(String(500), nullable=True)
    utilization_certificate_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ResearchProject {self.title[:50]}>"


class Publication(Base):
    """
    Research Publications.
    Key Indicator 3.3: Research Publications
    """
    __tablename__ = "publications"

    __table_args__ = (
        Index('ix_publications_type', 'publication_type'),
        Index('ix_publications_department', 'department'),
        Index('ix_publications_year', 'publication_year'),
        Index('ix_publications_indexing', 'indexing'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Publication details
    title = Column(String(1000), nullable=False)
    publication_type = Column(SQLEnum(PublicationType), nullable=False)
    abstract = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)

    # Authors
    authors = Column(JSON, nullable=False)  # [{"name": "", "affiliation": "", "is_corresponding": false}]
    corresponding_author = Column(String(255), nullable=True)
    department = Column(String(255), nullable=False)

    # Publication venue
    journal_name = Column(String(500), nullable=True)
    conference_name = Column(String(500), nullable=True)
    publisher = Column(String(255), nullable=True)
    volume = Column(String(50), nullable=True)
    issue = Column(String(50), nullable=True)
    pages = Column(String(50), nullable=True)
    publication_year = Column(Integer, nullable=False)
    publication_date = Column(Date, nullable=True)

    # Indexing and metrics
    indexing = Column(SQLEnum(PublicationIndexing), default=PublicationIndexing.NONE)
    impact_factor = Column(Float, nullable=True)
    h_index = Column(Integer, nullable=True)
    citations = Column(Integer, default=0)
    doi = Column(String(255), nullable=True)
    issn = Column(String(50), nullable=True)
    isbn = Column(String(50), nullable=True)

    # URLs
    paper_url = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)

    # Project linkage
    project_id = Column(GUID, ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True)

    # Verification
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Publication {self.title[:50]}>"


class Patent(Base):
    """
    Patents - Filed and Granted.
    Key Indicator 3.2: Innovation Ecosystem
    """
    __tablename__ = "patents"

    __table_args__ = (
        Index('ix_patents_status', 'status'),
        Index('ix_patents_type', 'patent_type'),
        Index('ix_patents_department', 'department'),
        Index('ix_patents_year', 'filing_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Patent details
    title = Column(String(1000), nullable=False)
    patent_type = Column(SQLEnum(PatentType), nullable=False)
    status = Column(SQLEnum(PatentStatus), default=PatentStatus.FILED)
    description = Column(Text, nullable=True)
    claims = Column(Text, nullable=True)

    # Application details
    application_number = Column(String(100), nullable=True)
    patent_number = Column(String(100), nullable=True)
    filing_date = Column(Date, nullable=False)
    filing_year = Column(Integer, nullable=False)
    publication_date = Column(Date, nullable=True)
    grant_date = Column(Date, nullable=True)

    # Inventors
    inventors = Column(JSON, nullable=False)  # [{"name": "", "designation": "", "department": ""}]
    applicant = Column(String(500), nullable=True)  # Usually institution name
    department = Column(String(255), nullable=False)

    # Classification
    ipc_class = Column(String(100), nullable=True)  # International Patent Classification
    technology_area = Column(String(255), nullable=True)

    # Commercial aspects
    is_commercialized = Column(Boolean, default=False)
    commercialization_details = Column(Text, nullable=True)
    revenue_generated = Column(Float, nullable=True)

    # Documents
    application_path = Column(String(500), nullable=True)
    certificate_path = Column(String(500), nullable=True)

    # Project linkage
    project_id = Column(GUID, ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Patent {self.title[:50]}>"


class Startup(Base):
    """
    Startups and Spin-offs.
    Key Indicator 3.2: Innovation Ecosystem
    """
    __tablename__ = "startups"

    __table_args__ = (
        Index('ix_startups_stage', 'stage'),
        Index('ix_startups_status', 'status'),
        Index('ix_startups_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Startup details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    problem_statement = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)
    industry_sector = Column(String(255), nullable=True)
    technology_used = Column(JSON, nullable=True)

    # Stage and status
    stage = Column(SQLEnum(StartupStage), default=StartupStage.IDEATION)
    status = Column(SQLEnum(StartupStatus), default=StartupStatus.INCUBATED)

    # Founders
    founders = Column(JSON, nullable=False)  # [{"name": "", "role": "", "is_student": true}]
    department = Column(String(255), nullable=False)
    incubated_at = Column(String(255), nullable=True)  # Incubator name

    # Registration
    registration_number = Column(String(100), nullable=True)
    registration_date = Column(Date, nullable=True)
    dpiit_recognized = Column(Boolean, default=False)
    dpiit_number = Column(String(100), nullable=True)

    # Funding
    seed_funding = Column(Float, nullable=True)
    total_funding = Column(Float, nullable=True)
    funding_rounds = Column(JSON, nullable=True)  # [{"round": "Seed", "amount": 100000, "date": ""}]
    investors = Column(JSON, nullable=True)

    # Performance
    revenue = Column(Float, nullable=True)
    employees_count = Column(Integer, nullable=True)
    products_services = Column(JSON, nullable=True)
    awards = Column(JSON, nullable=True)

    # Contact
    website = Column(String(500), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)

    # Documents
    pitch_deck_path = Column(String(500), nullable=True)
    registration_certificate_path = Column(String(500), nullable=True)
    mou_path = Column(String(500), nullable=True)

    # Timestamps
    founded_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Startup {self.name}>"


class InnovationCell(Base):
    """
    Innovation Cell / IIC Records.
    Key Indicator 3.2: Innovation Ecosystem
    """
    __tablename__ = "innovation_cells"

    __table_args__ = (
        Index('ix_innovation_cells_type', 'cell_type'),
        Index('ix_innovation_cells_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Cell details
    name = Column(String(255), nullable=False)
    cell_type = Column(String(100), nullable=False)  # IIC, EDC, IPR Cell, etc.
    registration_number = Column(String(100), nullable=True)
    establishment_date = Column(Date, nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Coordinator
    coordinator_name = Column(String(255), nullable=False)
    coordinator_designation = Column(String(100), nullable=True)
    coordinator_email = Column(String(255), nullable=True)
    coordinator_phone = Column(String(50), nullable=True)

    # Members
    faculty_members = Column(JSON, nullable=True)  # [{"name": "", "department": ""}]
    student_members = Column(JSON, nullable=True)
    external_mentors = Column(JSON, nullable=True)

    # Activities
    activities_conducted = Column(JSON, nullable=True)  # [{"name": "", "date": "", "participants": 0}]
    workshops_count = Column(Integer, default=0)
    seminars_count = Column(Integer, default=0)
    hackathons_count = Column(Integer, default=0)
    ideas_generated = Column(Integer, default=0)
    prototypes_developed = Column(Integer, default=0)
    startups_incubated = Column(Integer, default=0)
    patents_filed = Column(Integer, default=0)

    # IIC specific
    iic_star_rating = Column(Integer, nullable=True)  # 1-5 stars
    mhrd_points = Column(Float, nullable=True)

    # Funding
    annual_budget = Column(Float, nullable=True)
    funds_utilized = Column(Float, nullable=True)

    # Documents
    annual_report_path = Column(String(500), nullable=True)
    registration_certificate_path = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InnovationCell {self.name}>"


class Hackathon(Base):
    """
    Hackathons and Competitions.
    Key Indicator 3.2: Innovation Ecosystem
    """
    __tablename__ = "hackathons"

    __table_args__ = (
        Index('ix_hackathons_type', 'event_type'),
        Index('ix_hackathons_date', 'event_date'),
        Index('ix_hackathons_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Event details
    name = Column(String(500), nullable=False)
    event_type = Column(SQLEnum(EventType), nullable=False)
    description = Column(Text, nullable=True)
    theme = Column(String(255), nullable=True)
    problem_statements = Column(JSON, nullable=True)

    # Organizer
    organized_by = Column(String(255), nullable=False)  # College/External
    is_internal = Column(Boolean, default=True)
    department = Column(String(255), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Event timing
    event_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    duration_hours = Column(Integer, nullable=True)
    venue = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)  # online/offline/hybrid

    # Participation
    registrations_count = Column(Integer, default=0)
    participants_count = Column(Integer, default=0)
    teams_count = Column(Integer, default=0)
    submissions_count = Column(Integer, default=0)

    # Winners (if organized by college)
    winners = Column(JSON, nullable=True)  # [{"position": 1, "team": "", "project": "", "prize": ""}]

    # College participation (if external event)
    college_participants = Column(JSON, nullable=True)  # [{"name": "", "roll_no": "", "team": ""}]
    college_achievements = Column(JSON, nullable=True)  # [{"position": "", "project": ""}]

    # Prizes
    total_prize_pool = Column(Float, nullable=True)
    prizes = Column(JSON, nullable=True)

    # Sponsors
    sponsors = Column(JSON, nullable=True)

    # Documents
    brochure_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Hackathon {self.name}>"


class ExtensionActivity(Base):
    """
    Extension Activities and Community Outreach.
    Key Indicator 3.4: Extension Activities
    """
    __tablename__ = "extension_activities"

    __table_args__ = (
        Index('ix_extension_activities_type', 'activity_type'),
        Index('ix_extension_activities_date', 'activity_date'),
        Index('ix_extension_activities_department', 'department'),
        Index('ix_extension_activities_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Activity details
    title = Column(String(500), nullable=False)
    activity_type = Column(SQLEnum(ExtensionType), nullable=False)
    description = Column(Text, nullable=True)
    objectives = Column(JSON, nullable=True)
    outcomes = Column(JSON, nullable=True)

    # Organizer
    organized_by = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Location
    venue = Column(String(255), nullable=True)
    village_adopted = Column(String(255), nullable=True)
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)

    # Timing
    activity_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    duration_days = Column(Integer, default=1)

    # Participation
    faculty_involved = Column(JSON, nullable=True)  # [{"name": "", "department": ""}]
    students_participated = Column(Integer, default=0)
    student_list = Column(JSON, nullable=True)
    beneficiaries_count = Column(Integer, default=0)
    beneficiaries_type = Column(String(255), nullable=True)  # Farmers, Women, Students, etc.

    # Collaboration
    collaborating_agencies = Column(JSON, nullable=True)  # NGOs, Govt bodies
    funding_received = Column(Float, nullable=True)
    funding_source = Column(String(255), nullable=True)

    # Impact
    impact_description = Column(Text, nullable=True)
    sdg_goals_addressed = Column(JSON, nullable=True)  # [1, 3, 4] - UN SDG numbers
    media_coverage = Column(JSON, nullable=True)

    # Awards
    awards_received = Column(JSON, nullable=True)

    # Documents
    report_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)
    certificate_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ExtensionActivity {self.title[:50]}>"


class Consultancy(Base):
    """
    Consultancy Projects.
    Key Indicator 3.5: Collaboration
    """
    __tablename__ = "consultancies"

    __table_args__ = (
        Index('ix_consultancies_department', 'department'),
        Index('ix_consultancies_status', 'status'),
        Index('ix_consultancies_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Project details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    scope_of_work = Column(Text, nullable=True)
    deliverables = Column(JSON, nullable=True)

    # Client
    client_name = Column(String(500), nullable=False)
    client_type = Column(String(100), nullable=True)  # Industry, Govt, NGO
    client_contact = Column(String(255), nullable=True)
    client_email = Column(String(255), nullable=True)

    # Department and consultant
    department = Column(String(255), nullable=False)
    academic_year = Column(String(20), nullable=False)
    consultant_name = Column(String(255), nullable=False)
    consultant_designation = Column(String(100), nullable=True)
    team_members = Column(JSON, nullable=True)

    # Duration
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.ONGOING)

    # Financial
    consultancy_amount = Column(Float, nullable=False)
    amount_received = Column(Float, nullable=True)
    institute_share = Column(Float, nullable=True)

    # MoU
    mou_number = Column(String(100), nullable=True)
    mou_date = Column(Date, nullable=True)

    # Documents
    mou_path = Column(String(500), nullable=True)
    completion_certificate_path = Column(String(500), nullable=True)
    payment_receipt_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Consultancy {self.title[:50]}>"


class ResearchFunding(Base):
    """
    Research Funding and Grants.
    Key Indicator 3.1: Resource Mobilization for Research
    """
    __tablename__ = "research_funding"

    __table_args__ = (
        Index('ix_research_funding_agency', 'funding_agency'),
        Index('ix_research_funding_department', 'department'),
        Index('ix_research_funding_year', 'financial_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Grant details
    scheme_name = Column(String(500), nullable=False)
    funding_agency = Column(SQLEnum(FundingAgency), nullable=False)
    agency_name = Column(String(255), nullable=True)

    # Project linkage
    project_id = Column(GUID, ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True)
    project_title = Column(String(500), nullable=True)

    # Principal Investigator
    pi_name = Column(String(255), nullable=False)
    pi_designation = Column(String(100), nullable=True)
    department = Column(String(255), nullable=False)

    # Financial details
    financial_year = Column(String(20), nullable=False)  # 2024-25
    sanctioned_amount = Column(Float, nullable=False)
    received_amount = Column(Float, nullable=True)
    utilized_amount = Column(Float, nullable=True)

    # Grant details
    grant_number = Column(String(100), nullable=True)
    sanction_date = Column(Date, nullable=True)
    duration_years = Column(Integer, nullable=True)

    # Documents
    sanction_letter_path = Column(String(500), nullable=True)
    utilization_certificate_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ResearchFunding {self.scheme_name}>"
