"""
NAAC Criterion 7: Institutional Values & Best Practices - Database Models

This module defines database models for managing NAAC Criterion 7 requirements:
- Gender Equity and Sensitization
- Environmental Consciousness and Sustainability
- Inclusiveness and Sensitivity
- Code of Conduct and Ethics
- Best Practices
- Institutional Distinctiveness
"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index, Float, Date
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== ENUMS ====================

class GreenInitiativeType(str, enum.Enum):
    """Types of green/sustainability initiatives"""
    SOLAR_ENERGY = "solar_energy"
    RAINWATER_HARVESTING = "rainwater_harvesting"
    WASTE_MANAGEMENT = "waste_management"
    E_WASTE = "e_waste"
    TREE_PLANTATION = "tree_plantation"
    WATER_CONSERVATION = "water_conservation"
    ENERGY_CONSERVATION = "energy_conservation"
    PLASTIC_FREE = "plastic_free"
    GREEN_AUDIT = "green_audit"
    CARBON_FOOTPRINT = "carbon_footprint"
    BIODIVERSITY = "biodiversity"
    ORGANIC_FARMING = "organic_farming"
    OTHER = "other"


class InclusivityType(str, enum.Enum):
    """Types of inclusivity programs"""
    DIVYANGJAN = "divyangjan"  # Differently abled
    SC_ST = "sc_st"
    OBC = "obc"
    MINORITY = "minority"
    WOMEN = "women"
    ECONOMICALLY_WEAKER = "economically_weaker"
    FIRST_GENERATION = "first_generation"
    TRANSGENDER = "transgender"
    RURAL = "rural"
    OTHER = "other"


class EthicsType(str, enum.Enum):
    """Types of ethics/value programs"""
    PROFESSIONAL_ETHICS = "professional_ethics"
    ACADEMIC_INTEGRITY = "academic_integrity"
    SOCIAL_RESPONSIBILITY = "social_responsibility"
    HUMAN_VALUES = "human_values"
    CONSTITUTION_VALUES = "constitution_values"
    ANTI_CORRUPTION = "anti_corruption"
    ENVIRONMENTAL_ETHICS = "environmental_ethics"
    DIGITAL_ETHICS = "digital_ethics"
    OTHER = "other"


class BestPracticeCategory(str, enum.Enum):
    """Categories of best practices"""
    TEACHING_LEARNING = "teaching_learning"
    RESEARCH_INNOVATION = "research_innovation"
    STUDENT_SUPPORT = "student_support"
    GOVERNANCE = "governance"
    INFRASTRUCTURE = "infrastructure"
    COMMUNITY_ENGAGEMENT = "community_engagement"
    SUSTAINABILITY = "sustainability"
    INCLUSIVITY = "inclusivity"
    TECHNOLOGY = "technology"
    OTHER = "other"


class AwardCategory(str, enum.Enum):
    """Categories of institutional awards"""
    NATIONAL = "national"
    STATE = "state"
    UNIVERSITY = "university"
    INDUSTRY = "industry"
    MEDIA = "media"
    GOVERNMENT = "government"
    INTERNATIONAL = "international"
    OTHER = "other"


# ==================== MODELS ====================

class GenderEquityProgram(Base):
    """
    Gender Equity and Sensitization Programs.
    Key Indicator 7.1: Institutional Values and Social Responsibilities
    """
    __tablename__ = "gender_equity_programs"

    __table_args__ = (
        Index('ix_gender_equity_programs_type', 'program_type'),
        Index('ix_gender_equity_programs_date', 'program_date'),
        Index('ix_gender_equity_programs_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_title = Column(String(500), nullable=False)
    program_type = Column(String(100), nullable=False)  # awareness, workshop, seminar, campaign
    description = Column(Text, nullable=True)
    objectives = Column(JSON, nullable=True)
    themes = Column(JSON, nullable=True)  # ["women_safety", "gender_sensitization"]

    # Date and venue
    program_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    duration_hours = Column(Float, nullable=True)
    venue = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)

    # Academic context
    academic_year = Column(String(20), nullable=False)
    organized_by = Column(String(255), nullable=True)  # Women's Cell, ICC, etc.

    # Participation
    target_group = Column(String(255), nullable=True)
    participants_count = Column(Integer, default=0)
    male_participants = Column(Integer, default=0)
    female_participants = Column(Integer, default=0)

    # Resource person
    resource_person = Column(String(255), nullable=True)
    resource_person_designation = Column(String(255), nullable=True)
    resource_person_organization = Column(String(255), nullable=True)

    # Outcomes
    outcomes = Column(JSON, nullable=True)
    impact_description = Column(Text, nullable=True)
    feedback_summary = Column(Text, nullable=True)

    # Facilities mentioned
    facilities_for_women = Column(JSON, nullable=True)  # ["ladies_room", "sanitary_pad_dispenser"]
    safety_measures = Column(JSON, nullable=True)  # ["cctv", "help_desk", "escorts"]

    # Documents
    brochure_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GenderEquityProgram {self.program_title}>"


class GreenInitiative(Base):
    """
    Environmental Sustainability Initiatives.
    Key Indicator 7.1: Institutional Values and Social Responsibilities
    """
    __tablename__ = "green_initiatives"

    __table_args__ = (
        Index('ix_green_initiatives_type', 'initiative_type'),
        Index('ix_green_initiatives_status', 'status'),
        Index('ix_green_initiatives_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Initiative details
    initiative_name = Column(String(500), nullable=False)
    initiative_type = Column(SQLEnum(GreenInitiativeType), nullable=False)
    description = Column(Text, nullable=True)
    objectives = Column(JSON, nullable=True)

    # Implementation
    start_date = Column(Date, nullable=True)
    completion_date = Column(Date, nullable=True)
    academic_year = Column(String(20), nullable=False)
    location = Column(String(255), nullable=True)

    # Investment
    investment_amount = Column(Float, nullable=True)
    funding_source = Column(String(255), nullable=True)
    annual_savings = Column(Float, nullable=True)

    # Impact metrics
    capacity_installed = Column(String(255), nullable=True)  # e.g., "100 kW solar"
    units_generated = Column(Float, nullable=True)  # e.g., energy in kWh
    water_harvested = Column(Float, nullable=True)  # in kiloliters
    waste_recycled = Column(Float, nullable=True)  # in kg/tons
    trees_planted = Column(Integer, nullable=True)
    carbon_offset = Column(Float, nullable=True)  # in tons CO2

    # Certifications
    certifications_obtained = Column(JSON, nullable=True)  # ["ISO 14001", "Green Campus"]
    audit_conducted = Column(Boolean, default=False)
    audit_agency = Column(String(255), nullable=True)
    audit_score = Column(Float, nullable=True)

    # Status
    status = Column(String(50), default="active")  # proposed, in_progress, completed, active

    # Collaboration
    partners = Column(JSON, nullable=True)  # NGOs, Govt bodies
    student_participation = Column(Integer, default=0)

    # Documents
    proposal_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)
    certificate_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GreenInitiative {self.initiative_name}>"


class InclusivityProgram(Base):
    """
    Programs for Inclusivity and Sensitivity.
    Key Indicator 7.1: Institutional Values and Social Responsibilities
    """
    __tablename__ = "inclusivity_programs"

    __table_args__ = (
        Index('ix_inclusivity_programs_type', 'inclusivity_type'),
        Index('ix_inclusivity_programs_date', 'program_date'),
        Index('ix_inclusivity_programs_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_title = Column(String(500), nullable=False)
    inclusivity_type = Column(SQLEnum(InclusivityType), nullable=False)
    description = Column(Text, nullable=True)
    objectives = Column(JSON, nullable=True)

    # Date
    program_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    academic_year = Column(String(20), nullable=False)
    venue = Column(String(255), nullable=True)

    # Organizer
    organized_by = Column(String(255), nullable=True)
    sponsoring_body = Column(String(255), nullable=True)

    # Target beneficiaries
    target_group = Column(String(255), nullable=True)
    beneficiaries_count = Column(Integer, default=0)
    beneficiary_details = Column(JSON, nullable=True)

    # Facilities/Support provided
    facilities_provided = Column(JSON, nullable=True)  # ["ramp", "screen_reader", "scribe"]
    financial_support = Column(Float, nullable=True)
    material_support = Column(JSON, nullable=True)

    # Outcomes
    outcomes = Column(JSON, nullable=True)
    impact_description = Column(Text, nullable=True)
    success_stories = Column(JSON, nullable=True)

    # Documents
    report_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InclusivityProgram {self.program_title}>"


class EthicsProgram(Base):
    """
    Ethics and Value Education Programs.
    Key Indicator 7.1: Institutional Values and Social Responsibilities
    """
    __tablename__ = "ethics_programs"

    __table_args__ = (
        Index('ix_ethics_programs_type', 'ethics_type'),
        Index('ix_ethics_programs_date', 'program_date'),
        Index('ix_ethics_programs_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_title = Column(String(500), nullable=False)
    ethics_type = Column(SQLEnum(EthicsType), nullable=False)
    description = Column(Text, nullable=True)
    topics_covered = Column(JSON, nullable=True)

    # Date
    program_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    duration_hours = Column(Float, nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Organizer
    organized_by = Column(String(255), nullable=True)
    venue = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)

    # Participation
    target_group = Column(String(255), nullable=True)  # students, faculty, staff
    participants_count = Column(Integer, default=0)
    departments_covered = Column(JSON, nullable=True)

    # Resource persons
    resource_persons = Column(JSON, nullable=True)

    # Integration in curriculum
    is_curriculum_based = Column(Boolean, default=False)
    course_code = Column(String(50), nullable=True)
    course_name = Column(String(255), nullable=True)

    # Outcomes
    outcomes = Column(JSON, nullable=True)
    feedback_summary = Column(Text, nullable=True)

    # Code of conduct
    code_of_conduct_signed = Column(Integer, default=0)

    # Documents
    material_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EthicsProgram {self.program_title}>"


class BestPractice(Base):
    """
    Institutional Best Practices.
    Key Indicator 7.2: Best Practices
    """
    __tablename__ = "best_practices"

    __table_args__ = (
        Index('ix_best_practices_category', 'category'),
        Index('ix_best_practices_status', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Practice details
    practice_title = Column(String(500), nullable=False)
    practice_number = Column(Integer, nullable=True)  # Best Practice 1, 2
    category = Column(SQLEnum(BestPracticeCategory), nullable=False)

    # Context
    context = Column(Text, nullable=True)
    need_addressed = Column(Text, nullable=True)
    objectives = Column(JSON, nullable=True)

    # Implementation
    the_practice = Column(Text, nullable=True)  # Detailed description
    uniqueness = Column(Text, nullable=True)
    methodology = Column(Text, nullable=True)
    resources_required = Column(JSON, nullable=True)
    stakeholders = Column(JSON, nullable=True)
    implementation_year = Column(String(20), nullable=True)

    # Evidence of success
    evidence_of_success = Column(Text, nullable=True)
    quantitative_evidence = Column(JSON, nullable=True)
    qualitative_evidence = Column(JSON, nullable=True)
    beneficiaries_count = Column(Integer, nullable=True)

    # Challenges and solutions
    challenges = Column(JSON, nullable=True)
    solutions = Column(JSON, nullable=True)
    limitations = Column(Text, nullable=True)

    # Recognition
    awards_received = Column(JSON, nullable=True)
    media_coverage = Column(JSON, nullable=True)
    replicated_by = Column(JSON, nullable=True)  # Other institutions

    # Impact
    impact_on_students = Column(Text, nullable=True)
    impact_on_institution = Column(Text, nullable=True)
    impact_on_society = Column(Text, nullable=True)

    # Status
    status = Column(String(50), default="active")  # active, discontinued, evolved

    # Documents
    detailed_document_path = Column(String(500), nullable=True)
    supporting_documents = Column(JSON, nullable=True)
    photos_path = Column(String(500), nullable=True)
    videos_path = Column(String(500), nullable=True)

    # Web link
    web_link = Column(String(500), nullable=True)

    # Academic years
    academic_year_start = Column(String(20), nullable=True)
    academic_year_current = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<BestPractice {self.practice_title}>"


class InstitutionalDistinctiveness(Base):
    """
    Institutional Distinctiveness.
    Key Indicator 7.3: Institutional Distinctiveness
    """
    __tablename__ = "institutional_distinctiveness"

    __table_args__ = (
        Index('ix_institutional_distinctiveness_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Distinctiveness details
    title = Column(String(500), nullable=False)
    theme = Column(String(255), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Description
    introduction = Column(Text, nullable=True)
    detailed_description = Column(Text, nullable=True)
    historical_context = Column(Text, nullable=True)
    vision_alignment = Column(Text, nullable=True)

    # Key features
    key_features = Column(JSON, nullable=True)
    unique_aspects = Column(JSON, nullable=True)
    flagship_programs = Column(JSON, nullable=True)

    # Impact
    impact_on_students = Column(Text, nullable=True)
    impact_on_community = Column(Text, nullable=True)
    impact_on_region = Column(Text, nullable=True)
    national_contribution = Column(Text, nullable=True)

    # Evidence
    quantitative_evidence = Column(JSON, nullable=True)
    qualitative_evidence = Column(JSON, nullable=True)
    testimonials = Column(JSON, nullable=True)

    # Recognition
    awards_recognition = Column(JSON, nullable=True)
    media_mentions = Column(JSON, nullable=True)
    rankings = Column(JSON, nullable=True)

    # Future plans
    future_plans = Column(Text, nullable=True)
    sustainability = Column(Text, nullable=True)

    # Documents
    document_path = Column(String(500), nullable=True)
    supporting_docs = Column(JSON, nullable=True)
    photos_path = Column(String(500), nullable=True)
    videos_path = Column(String(500), nullable=True)

    # Web link
    web_link = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InstitutionalDistinctiveness {self.title}>"


class InstitutionalAward(Base):
    """
    Institutional Awards and Recognition.
    Key Indicator 7.1: Institutional Values
    """
    __tablename__ = "institutional_awards"

    __table_args__ = (
        Index('ix_institutional_awards_category', 'award_category'),
        Index('ix_institutional_awards_year', 'award_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Award details
    award_name = Column(String(500), nullable=False)
    award_category = Column(SQLEnum(AwardCategory), nullable=False)
    awarding_body = Column(String(255), nullable=False)
    award_year = Column(Integer, nullable=False)
    award_date = Column(Date, nullable=True)

    # Context
    award_for = Column(Text, nullable=True)  # What the award was given for
    category = Column(String(255), nullable=True)  # Specific category if any
    level = Column(String(100), nullable=True)  # State, National, International

    # Recipient
    recipient_type = Column(String(50), nullable=True)  # institution, department, faculty, student
    recipient_name = Column(String(255), nullable=True)
    recipient_department = Column(String(255), nullable=True)

    # Value
    cash_prize = Column(Float, nullable=True)
    trophy_medal = Column(String(100), nullable=True)
    citation = Column(Text, nullable=True)

    # Impact
    media_coverage = Column(JSON, nullable=True)
    impact_description = Column(Text, nullable=True)

    # Documents
    certificate_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)
    news_clippings_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InstitutionalAward {self.award_name} - {self.award_year}>"
