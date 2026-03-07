"""
NAAC Criterion 6: Governance, Leadership & Management - Database Models

This module defines database models for managing NAAC Criterion 6 requirements:
- Vision, Mission, and Strategic Planning
- Institutional Governance
- IQAC Operations
- Quality Assurance
- Faculty Welfare and Development
- Financial Management
"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index, Float, Date
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== ENUMS ====================

class MeetingType(str, enum.Enum):
    """Types of institutional meetings"""
    GOVERNING_BODY = "governing_body"
    ACADEMIC_COUNCIL = "academic_council"
    BOARD_OF_STUDIES = "board_of_studies"
    IQAC = "iqac"
    FINANCE_COMMITTEE = "finance_committee"
    GRIEVANCE_CELL = "grievance_cell"
    ANTI_RAGGING = "anti_ragging"
    ICC = "icc"  # Internal Complaints Committee
    SC_ST_CELL = "sc_st_cell"
    DEPARTMENT = "department"
    FACULTY = "faculty"
    OTHER = "other"


class PolicyType(str, enum.Enum):
    """Types of institutional policies"""
    ACADEMIC = "academic"
    ADMISSION = "admission"
    EXAMINATION = "examination"
    RESEARCH = "research"
    HR = "hr"
    FINANCIAL = "financial"
    IT = "it"
    GRIEVANCE = "grievance"
    ANTI_RAGGING = "anti_ragging"
    SEXUAL_HARASSMENT = "sexual_harassment"
    ENVIRONMENT = "environment"
    ETHICS = "ethics"
    IPR = "ipr"
    OTHER = "other"


class QualityInitiativeType(str, enum.Enum):
    """Types of quality initiatives"""
    ACCREDITATION = "accreditation"
    CERTIFICATION = "certification"
    RANKING = "ranking"
    AUDIT = "audit"
    BENCHMARKING = "benchmarking"
    BEST_PRACTICE = "best_practice"
    INNOVATION = "innovation"
    OTHER = "other"


class FDPType(str, enum.Enum):
    """Faculty Development Program types"""
    WORKSHOP = "workshop"
    SEMINAR = "seminar"
    CONFERENCE = "conference"
    TRAINING = "training"
    REFRESHER_COURSE = "refresher_course"
    ORIENTATION = "orientation"
    STTP = "sttp"  # Short Term Training Program
    FDP = "fdp"
    WEBINAR = "webinar"
    CERTIFICATION = "certification"
    OTHER = "other"


class AuditType(str, enum.Enum):
    """Financial audit types"""
    INTERNAL = "internal"
    EXTERNAL = "external"
    STATUTORY = "statutory"
    SPECIAL = "special"
    CAG = "cag"


# ==================== MODELS ====================

class InstitutionalGovernance(Base):
    """
    Governance Body Records.
    Key Indicator 6.1: Institutional Vision and Leadership
    """
    __tablename__ = "institutional_governance"

    __table_args__ = (
        Index('ix_institutional_governance_type', 'body_type'),
        Index('ix_institutional_governance_active', 'is_active'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Body details
    body_name = Column(String(255), nullable=False)
    body_type = Column(SQLEnum(MeetingType), nullable=False)
    description = Column(Text, nullable=True)
    establishment_date = Column(Date, nullable=True)

    # Composition
    chairperson = Column(String(255), nullable=True)
    chairperson_designation = Column(String(255), nullable=True)
    secretary = Column(String(255), nullable=True)
    members = Column(JSON, nullable=True)  # [{"name": "", "designation": "", "role": ""}]
    total_members = Column(Integer, nullable=True)

    # Terms of reference
    terms_of_reference = Column(JSON, nullable=True)
    powers_and_functions = Column(Text, nullable=True)

    # Meeting frequency
    meeting_frequency = Column(String(100), nullable=True)  # Monthly, Quarterly, etc.
    last_meeting_date = Column(Date, nullable=True)
    next_meeting_date = Column(Date, nullable=True)

    # Documents
    constitution_path = Column(String(500), nullable=True)
    notification_path = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    tenure_start = Column(Date, nullable=True)
    tenure_end = Column(Date, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InstitutionalGovernance {self.body_name}>"


class GovernanceMeeting(Base):
    """
    Meeting Records for Governance Bodies.
    Key Indicator 6.1: Institutional Vision and Leadership
    """
    __tablename__ = "governance_meetings"

    __table_args__ = (
        Index('ix_governance_meetings_body_id', 'governance_body_id'),
        Index('ix_governance_meetings_date', 'meeting_date'),
        Index('ix_governance_meetings_type', 'meeting_type'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Body reference
    governance_body_id = Column(GUID, ForeignKey("institutional_governance.id", ondelete="CASCADE"), nullable=True)
    meeting_type = Column(SQLEnum(MeetingType), nullable=False)
    body_name = Column(String(255), nullable=False)

    # Meeting details
    meeting_number = Column(Integer, nullable=True)
    meeting_date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=True)
    end_time = Column(String(10), nullable=True)
    venue = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)  # in-person, online, hybrid

    # Attendance
    members_invited = Column(Integer, nullable=True)
    members_attended = Column(Integer, nullable=True)
    attendance_list = Column(JSON, nullable=True)
    quorum_present = Column(Boolean, nullable=True)

    # Agenda and minutes
    agenda = Column(JSON, nullable=True)  # [{"item": "", "description": ""}]
    discussions = Column(JSON, nullable=True)
    resolutions = Column(JSON, nullable=True)  # [{"resolution_no": "", "description": "", "status": ""}]
    action_items = Column(JSON, nullable=True)

    # Academic year
    academic_year = Column(String(20), nullable=True)

    # Documents
    agenda_path = Column(String(500), nullable=True)
    minutes_path = Column(String(500), nullable=True)
    attendance_sheet_path = Column(String(500), nullable=True)

    # Approval
    approved_by = Column(String(255), nullable=True)
    approved_date = Column(Date, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GovernanceMeeting {self.body_name} - {self.meeting_date}>"


class InstitutionalPolicy(Base):
    """
    Institutional Policies and SOPs.
    Key Indicator 6.1: Institutional Vision and Leadership
    """
    __tablename__ = "institutional_policies"

    __table_args__ = (
        Index('ix_institutional_policies_type', 'policy_type'),
        Index('ix_institutional_policies_status', 'is_active'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Policy details
    policy_name = Column(String(255), nullable=False)
    policy_number = Column(String(50), nullable=True)
    policy_type = Column(SQLEnum(PolicyType), nullable=False)
    description = Column(Text, nullable=True)

    # Content
    objectives = Column(JSON, nullable=True)
    scope = Column(Text, nullable=True)
    procedures = Column(Text, nullable=True)
    responsibilities = Column(JSON, nullable=True)

    # Approval
    approved_by = Column(String(255), nullable=True)
    approval_date = Column(Date, nullable=True)
    approval_body = Column(String(255), nullable=True)  # Governing Body, Academic Council

    # Version
    version = Column(String(20), nullable=True)
    effective_date = Column(Date, nullable=True)
    review_date = Column(Date, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)

    # Documents
    document_path = Column(String(500), nullable=True)
    supporting_documents = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<InstitutionalPolicy {self.policy_name}>"


class IQACActivity(Base):
    """
    IQAC Activities and Initiatives.
    Key Indicator 6.2: Strategy Development and Deployment
    """
    __tablename__ = "iqac_activities"

    __table_args__ = (
        Index('ix_iqac_activities_type', 'activity_type'),
        Index('ix_iqac_activities_date', 'activity_date'),
        Index('ix_iqac_activities_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Activity details
    title = Column(String(500), nullable=False)
    activity_type = Column(SQLEnum(QualityInitiativeType), nullable=False)
    description = Column(Text, nullable=True)
    objectives = Column(JSON, nullable=True)
    methodology = Column(Text, nullable=True)

    # Date and duration
    activity_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Target
    target_group = Column(String(255), nullable=True)  # Students, Faculty, Staff
    departments_involved = Column(JSON, nullable=True)
    participants_count = Column(Integer, nullable=True)

    # Resource person
    resource_person = Column(String(255), nullable=True)
    resource_person_affiliation = Column(String(255), nullable=True)

    # Outcomes
    outcomes = Column(JSON, nullable=True)
    impact_description = Column(Text, nullable=True)
    follow_up_actions = Column(JSON, nullable=True)

    # Quality metrics
    quality_parameters = Column(JSON, nullable=True)
    baseline_value = Column(Float, nullable=True)
    achieved_value = Column(Float, nullable=True)

    # Documents
    proposal_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<IQACActivity {self.title}>"


class FacultyDevelopment(Base):
    """
    Faculty Development Programs.
    Key Indicator 6.3: Faculty Empowerment Strategies
    """
    __tablename__ = "faculty_development"

    __table_args__ = (
        Index('ix_faculty_development_type', 'program_type'),
        Index('ix_faculty_development_date', 'start_date'),
        Index('ix_faculty_development_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_title = Column(String(500), nullable=False)
    program_type = Column(SQLEnum(FDPType), nullable=False)
    description = Column(Text, nullable=True)
    themes = Column(JSON, nullable=True)

    # Organizer
    organized_by = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)
    sponsoring_body = Column(String(255), nullable=True)

    # Venue and mode
    venue = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)  # online, offline, hybrid
    platform_used = Column(String(255), nullable=True)  # For online

    # Duration
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    duration_days = Column(Integer, nullable=True)
    total_hours = Column(Float, nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Participation
    external_participants = Column(Integer, default=0)
    internal_participants = Column(Integer, default=0)
    total_participants = Column(Integer, default=0)
    participant_list = Column(JSON, nullable=True)

    # Resource persons
    resource_persons = Column(JSON, nullable=True)  # [{"name": "", "affiliation": "", "topic": ""}]

    # Financial
    budget = Column(Float, nullable=True)
    expenditure = Column(Float, nullable=True)
    registration_fee = Column(Float, nullable=True)

    # Certificates
    certificates_issued = Column(Integer, default=0)
    certification_body = Column(String(255), nullable=True)

    # Feedback
    average_rating = Column(Float, nullable=True)
    feedback_summary = Column(Text, nullable=True)

    # Documents
    brochure_path = Column(String(500), nullable=True)
    schedule_path = Column(String(500), nullable=True)
    report_path = Column(String(500), nullable=True)
    certificate_template_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FacultyDevelopment {self.program_title}>"


class FinancialAudit(Base):
    """
    Financial Audit Records.
    Key Indicator 6.4: Financial Management and Resource Mobilization
    """
    __tablename__ = "financial_audits"

    __table_args__ = (
        Index('ix_financial_audits_type', 'audit_type'),
        Index('ix_financial_audits_year', 'financial_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Audit details
    audit_type = Column(SQLEnum(AuditType), nullable=False)
    financial_year = Column(String(20), nullable=False)
    audit_firm = Column(String(255), nullable=True)
    auditor_name = Column(String(255), nullable=True)

    # Dates
    audit_start_date = Column(Date, nullable=True)
    audit_end_date = Column(Date, nullable=True)
    report_date = Column(Date, nullable=True)

    # Financial summary
    total_income = Column(Float, nullable=True)
    total_expenditure = Column(Float, nullable=True)
    surplus_deficit = Column(Float, nullable=True)
    capital_expenditure = Column(Float, nullable=True)

    # Findings
    observations = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    compliance_status = Column(String(100), nullable=True)

    # Action taken
    action_taken_report = Column(Text, nullable=True)
    compliance_date = Column(Date, nullable=True)

    # Documents
    audit_report_path = Column(String(500), nullable=True)
    balance_sheet_path = Column(String(500), nullable=True)
    income_expenditure_path = Column(String(500), nullable=True)

    # Status
    is_finalized = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FinancialAudit {self.financial_year} - {self.audit_type}>"


class StrategicPlan(Base):
    """
    Strategic Planning and Perspective Plans.
    Key Indicator 6.2: Strategy Development and Deployment
    """
    __tablename__ = "strategic_plans"

    __table_args__ = (
        Index('ix_strategic_plans_type', 'plan_type'),
        Index('ix_strategic_plans_status', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Plan details
    plan_title = Column(String(500), nullable=False)
    plan_type = Column(String(100), nullable=False)  # Strategic, Perspective, Annual
    description = Column(Text, nullable=True)

    # Duration
    start_year = Column(String(20), nullable=False)
    end_year = Column(String(20), nullable=True)
    duration_years = Column(Integer, nullable=True)

    # Vision and mission alignment
    vision_statement = Column(Text, nullable=True)
    mission_statement = Column(Text, nullable=True)
    goals = Column(JSON, nullable=True)  # [{"goal": "", "description": ""}]

    # Key result areas
    key_result_areas = Column(JSON, nullable=True)
    performance_indicators = Column(JSON, nullable=True)
    targets = Column(JSON, nullable=True)

    # Implementation
    action_plan = Column(JSON, nullable=True)  # [{"action": "", "timeline": "", "responsible": ""}]
    milestones = Column(JSON, nullable=True)
    budget_allocation = Column(Float, nullable=True)

    # Progress
    status = Column(String(50), default="active")  # active, completed, revised
    progress_percentage = Column(Float, nullable=True)
    achievements = Column(JSON, nullable=True)
    challenges = Column(JSON, nullable=True)

    # Review
    review_frequency = Column(String(50), nullable=True)
    last_review_date = Column(Date, nullable=True)
    review_remarks = Column(Text, nullable=True)

    # Approval
    approved_by = Column(String(255), nullable=True)
    approval_date = Column(Date, nullable=True)

    # Documents
    plan_document_path = Column(String(500), nullable=True)
    progress_report_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StrategicPlan {self.plan_title}>"
