"""
NAAC Accreditation Framework 2025 Models
Implements Binary Accreditation and Maturity-Based Graded Levels (MBGL)

Based on NAAC Reforms 2024-2025:
- Binary Accreditation: Accredited / Not Accredited
- MBGL Levels: 1-5 (Basic to Excellence)
- 3-Year Validity Cycle
- 10 Attributes Framework (expanded from 7 criteria)
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey,
    Enum as SQLEnum, JSON, Float, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== Enums ====================

class BinaryAccreditationStatus(str, enum.Enum):
    """Binary Accreditation Status (NAAC 2025)"""
    NOT_APPLIED = "not_applied"
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    ACCREDITED = "accredited"
    NOT_ACCREDITED = "not_accredited"
    EXPIRED = "expired"


class MBGLLevel(str, enum.Enum):
    """Maturity-Based Graded Levels (NAAC 2025)"""
    NOT_ASSESSED = "not_assessed"
    LEVEL_1 = "level_1"  # Basic Compliance
    LEVEL_2 = "level_2"  # Developing
    LEVEL_3 = "level_3"  # Established
    LEVEL_4 = "level_4"  # Advanced
    LEVEL_5 = "level_5"  # Excellence


class AccreditationCycle(str, enum.Enum):
    """Accreditation Cycle Type"""
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"
    FIFTH_PLUS = "fifth_plus"


class AttributeCategory(str, enum.Enum):
    """10 Attributes Framework (NAAC 2025)"""
    # Original 7 Criteria mapped + 3 new
    CURRICULAR_ASPECTS = "curricular_aspects"
    TEACHING_LEARNING = "teaching_learning"
    RESEARCH_INNOVATION = "research_innovation"
    INFRASTRUCTURE = "infrastructure"
    STUDENT_SUPPORT = "student_support"
    GOVERNANCE = "governance"
    INSTITUTIONAL_VALUES = "institutional_values"
    # New Attributes for 2025
    NEP_ALIGNMENT = "nep_alignment"
    DIGITAL_INFRASTRUCTURE = "digital_infrastructure"
    SUSTAINABILITY = "sustainability"


class AssessmentPhase(str, enum.Enum):
    """Assessment Phases"""
    SELF_STUDY = "self_study"
    DOCUMENT_VERIFICATION = "document_verification"
    AI_ASSESSMENT = "ai_assessment"
    STAKEHOLDER_VALIDATION = "stakeholder_validation"
    FINAL_REVIEW = "final_review"
    COMPLETED = "completed"


# ==================== Models ====================

class AccreditationApplication(Base):
    """
    Accreditation Application tracking for Binary and MBGL.
    Tracks the complete accreditation journey of an institution.
    """
    __tablename__ = "accreditation_applications"

    id = Column(GUID(), primary_key=True, default=generate_uuid)
    institution_id = Column(GUID(), ForeignKey("institutions.id"), nullable=True)

    # Application Details
    application_number = Column(String(50), unique=True, nullable=False)
    application_date = Column(DateTime, default=datetime.utcnow)

    # Cycle Information
    cycle = Column(SQLEnum(AccreditationCycle), default=AccreditationCycle.FIRST)
    cycle_number = Column(Integer, default=1)

    # Binary Accreditation Status
    binary_status = Column(
        SQLEnum(BinaryAccreditationStatus),
        default=BinaryAccreditationStatus.NOT_APPLIED
    )
    binary_assessment_date = Column(DateTime, nullable=True)
    binary_validity_start = Column(DateTime, nullable=True)
    binary_validity_end = Column(DateTime, nullable=True)  # 3 years from start

    # MBGL Status (only for already accredited institutions)
    mbgl_level = Column(SQLEnum(MBGLLevel), default=MBGLLevel.NOT_ASSESSED)
    mbgl_assessment_date = Column(DateTime, nullable=True)
    mbgl_score = Column(Float, nullable=True)  # 0-100 score
    mbgl_validity_start = Column(DateTime, nullable=True)
    mbgl_validity_end = Column(DateTime, nullable=True)

    # Previous Accreditation (for cycles 2+)
    previous_grade = Column(String(10), nullable=True)  # A++, A+, A, B++, etc.
    previous_cgpa = Column(Float, nullable=True)
    previous_validity_end = Column(DateTime, nullable=True)

    # Current Assessment Phase
    current_phase = Column(SQLEnum(AssessmentPhase), default=AssessmentPhase.SELF_STUDY)
    phase_started_at = Column(DateTime, nullable=True)

    # Scores
    self_study_score = Column(Float, nullable=True)
    ai_assessment_score = Column(Float, nullable=True)
    stakeholder_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attribute_scores = relationship("AttributeScore", back_populates="application", cascade="all, delete-orphan")
    mbgl_assessments = relationship("MBGLAssessment", back_populates="application", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_accreditation_binary_status', 'binary_status'),
        Index('idx_accreditation_mbgl_level', 'mbgl_level'),
    )


class AttributeScore(Base):
    """
    Scores for each of the 10 Attributes (NAAC 2025 Framework).
    Replaces the old 7 criteria scoring.
    """
    __tablename__ = "attribute_scores"

    id = Column(GUID(), primary_key=True, default=generate_uuid)
    application_id = Column(GUID(), ForeignKey("accreditation_applications.id"), nullable=False)

    # Attribute Details
    attribute = Column(SQLEnum(AttributeCategory), nullable=False)
    attribute_number = Column(Integer, nullable=False)  # 1-10
    attribute_name = Column(String(200), nullable=False)

    # Scoring
    max_score = Column(Float, default=100.0)
    self_assessment_score = Column(Float, nullable=True)
    verified_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    weightage = Column(Float, default=10.0)  # % weightage in total score

    # Evidence & Documentation
    evidence_count = Column(Integer, default=0)
    evidence_verified = Column(Integer, default=0)
    documentation_complete = Column(Boolean, default=False)

    # AI Assessment
    ai_score = Column(Float, nullable=True)
    ai_confidence = Column(Float, nullable=True)  # 0-1 confidence level
    ai_feedback = Column(Text, nullable=True)

    # Status
    is_complete = Column(Boolean, default=False)
    reviewed_by = Column(String(200), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("AccreditationApplication", back_populates="attribute_scores")

    __table_args__ = (
        UniqueConstraint('application_id', 'attribute', name='uq_app_attribute'),
        Index('idx_attribute_score_attribute', 'attribute'),
    )


class MBGLAssessment(Base):
    """
    MBGL (Maturity-Based Graded Level) Assessment tracking.
    Detailed maturity assessment across multiple dimensions.
    """
    __tablename__ = "mbgl_assessments"

    id = Column(GUID(), primary_key=True, default=generate_uuid)
    application_id = Column(GUID(), ForeignKey("accreditation_applications.id"), nullable=False)

    # Assessment Details
    assessment_year = Column(String(10), nullable=False)  # e.g., "2024-25"
    assessment_date = Column(DateTime, default=datetime.utcnow)

    # Maturity Dimensions (each scored 1-5)
    leadership_maturity = Column(Integer, default=1)  # 1-5
    process_maturity = Column(Integer, default=1)
    people_maturity = Column(Integer, default=1)
    technology_maturity = Column(Integer, default=1)
    outcome_maturity = Column(Integer, default=1)
    innovation_maturity = Column(Integer, default=1)
    stakeholder_maturity = Column(Integer, default=1)
    sustainability_maturity = Column(Integer, default=1)

    # Calculated Scores
    average_maturity = Column(Float, nullable=True)
    weighted_score = Column(Float, nullable=True)

    # MBGL Level Determination
    recommended_level = Column(SQLEnum(MBGLLevel), nullable=True)
    final_level = Column(SQLEnum(MBGLLevel), nullable=True)

    # Level Criteria Met
    level_1_criteria_met = Column(Boolean, default=False)
    level_2_criteria_met = Column(Boolean, default=False)
    level_3_criteria_met = Column(Boolean, default=False)
    level_4_criteria_met = Column(Boolean, default=False)
    level_5_criteria_met = Column(Boolean, default=False)

    # Strengths & Improvements
    strengths = Column(JSON, nullable=True)  # List of strength areas
    improvements_needed = Column(JSON, nullable=True)  # List of improvement areas
    action_plan = Column(Text, nullable=True)

    # Assessor Information
    assessed_by = Column(String(200), nullable=True)
    verified_by = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("AccreditationApplication", back_populates="mbgl_assessments")


class MBGLLevelCriteria(Base):
    """
    Criteria definitions for each MBGL Level.
    Used to determine if an institution qualifies for a specific level.
    """
    __tablename__ = "mbgl_level_criteria"

    id = Column(GUID(), primary_key=True, default=generate_uuid)

    # Level Details
    level = Column(SQLEnum(MBGLLevel), nullable=False)
    level_number = Column(Integer, nullable=False)  # 1-5
    level_name = Column(String(100), nullable=False)
    level_description = Column(Text, nullable=True)

    # Minimum Requirements
    min_binary_status = Column(Boolean, default=True)  # Must be accredited
    min_maturity_score = Column(Float, nullable=False)
    min_attribute_scores = Column(JSON, nullable=True)  # Min score per attribute

    # Mandatory Criteria
    mandatory_criteria = Column(JSON, nullable=True)  # List of must-have criteria
    optional_criteria = Column(JSON, nullable=True)  # Choose N from list
    optional_criteria_min = Column(Integer, default=0)

    # Benefits
    validity_years = Column(Integer, default=3)
    recognition_benefits = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    effective_from = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('level', name='uq_mbgl_level'),
    )


class AccreditationTimeline(Base):
    """
    Timeline tracking for accreditation milestones.
    """
    __tablename__ = "accreditation_timelines"

    id = Column(GUID(), primary_key=True, default=generate_uuid)
    application_id = Column(GUID(), ForeignKey("accreditation_applications.id"), nullable=False)

    # Milestone Details
    milestone_name = Column(String(200), nullable=False)
    milestone_description = Column(Text, nullable=True)
    milestone_type = Column(String(50), nullable=False)  # binary, mbgl, document, etc.

    # Dates
    planned_date = Column(DateTime, nullable=True)
    actual_date = Column(DateTime, nullable=True)

    # Status
    is_completed = Column(Boolean, default=False)
    completed_by = Column(String(200), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Helper Functions ====================

def calculate_mbgl_level(maturity_scores: dict) -> MBGLLevel:
    """
    Calculate MBGL level based on maturity scores.

    Level 1 (Basic): Average 1.0-1.9
    Level 2 (Developing): Average 2.0-2.9
    Level 3 (Established): Average 3.0-3.9
    Level 4 (Advanced): Average 4.0-4.4
    Level 5 (Excellence): Average 4.5-5.0
    """
    scores = list(maturity_scores.values())
    if not scores:
        return MBGLLevel.NOT_ASSESSED

    avg = sum(scores) / len(scores)

    if avg >= 4.5:
        return MBGLLevel.LEVEL_5
    elif avg >= 4.0:
        return MBGLLevel.LEVEL_4
    elif avg >= 3.0:
        return MBGLLevel.LEVEL_3
    elif avg >= 2.0:
        return MBGLLevel.LEVEL_2
    elif avg >= 1.0:
        return MBGLLevel.LEVEL_1
    else:
        return MBGLLevel.NOT_ASSESSED


def get_binary_status_display(status: BinaryAccreditationStatus) -> str:
    """Get display name for binary status"""
    display_names = {
        BinaryAccreditationStatus.NOT_APPLIED: "Not Applied",
        BinaryAccreditationStatus.APPLIED: "Applied",
        BinaryAccreditationStatus.UNDER_REVIEW: "Under Review",
        BinaryAccreditationStatus.ACCREDITED: "Accredited",
        BinaryAccreditationStatus.NOT_ACCREDITED: "Not Accredited",
        BinaryAccreditationStatus.EXPIRED: "Expired",
    }
    return display_names.get(status, str(status))


def get_mbgl_level_display(level: MBGLLevel) -> dict:
    """Get display information for MBGL level"""
    level_info = {
        MBGLLevel.NOT_ASSESSED: {
            "name": "Not Assessed",
            "number": 0,
            "description": "MBGL assessment not yet completed",
            "color": "gray"
        },
        MBGLLevel.LEVEL_1: {
            "name": "Level 1 - Basic Compliance",
            "number": 1,
            "description": "Institution meets basic accreditation requirements",
            "color": "red"
        },
        MBGLLevel.LEVEL_2: {
            "name": "Level 2 - Developing",
            "number": 2,
            "description": "Institution shows developing quality practices",
            "color": "orange"
        },
        MBGLLevel.LEVEL_3: {
            "name": "Level 3 - Established",
            "number": 3,
            "description": "Institution has established quality systems",
            "color": "yellow"
        },
        MBGLLevel.LEVEL_4: {
            "name": "Level 4 - Advanced",
            "number": 4,
            "description": "Institution demonstrates advanced quality practices",
            "color": "blue"
        },
        MBGLLevel.LEVEL_5: {
            "name": "Level 5 - Excellence",
            "number": 5,
            "description": "Institution achieves excellence in all dimensions",
            "color": "green"
        },
    }
    return level_info.get(level, level_info[MBGLLevel.NOT_ASSESSED])
