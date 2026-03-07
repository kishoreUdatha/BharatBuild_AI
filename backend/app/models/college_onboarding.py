"""
College Onboarding Models
Handles college registration, team invitations, and onboarding progress
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class CollegeType(str, enum.Enum):
    """College types"""
    AUTONOMOUS = "AUTONOMOUS"
    AFFILIATED = "AFFILIATED"
    DEEMED = "DEEMED"
    CENTRAL = "CENTRAL"
    STATE = "STATE"
    PRIVATE = "PRIVATE"


class AccreditationStatus(str, enum.Enum):
    """Current accreditation status"""
    NOT_ACCREDITED = "NOT_ACCREDITED"
    NAAC_APPLIED = "NAAC_APPLIED"
    NAAC_ACCREDITED = "NAAC_ACCREDITED"
    NBA_APPLIED = "NBA_APPLIED"
    NBA_ACCREDITED = "NBA_ACCREDITED"
    BOTH_ACCREDITED = "BOTH_ACCREDITED"


class SubscriptionPlan(str, enum.Enum):
    """Subscription plans"""
    FREE_TRIAL = "FREE_TRIAL"
    BASIC = "BASIC"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class OnboardingStep(str, enum.Enum):
    """Onboarding steps"""
    REGISTRATION = "REGISTRATION"
    PROFILE_SETUP = "PROFILE_SETUP"
    DEPARTMENTS = "DEPARTMENTS"
    PROGRAMS = "PROGRAMS"
    TEAM_SETUP = "TEAM_SETUP"
    ROLE_ASSIGNMENT = "ROLE_ASSIGNMENT"
    COMPLETED = "COMPLETED"


class InvitationStatus(str, enum.Enum):
    """Invitation status"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class CollegeProfile(Base):
    """College profile for NAAC/NBA accreditation"""
    __tablename__ = "college_profiles"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Basic Information
    name = Column(String(500), nullable=False)
    short_name = Column(String(100), nullable=True)
    aishe_code = Column(String(50), unique=True, nullable=True)  # All India Survey on Higher Education

    # Type and Affiliation
    college_type = Column(SQLEnum(CollegeType), default=CollegeType.AFFILIATED)
    university_affiliation = Column(String(500), nullable=True)
    year_established = Column(Integer, nullable=True)

    # Contact Information
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), default="India")
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)

    # Leadership
    principal_name = Column(String(255), nullable=True)
    principal_email = Column(String(255), nullable=True)
    principal_phone = Column(String(20), nullable=True)
    iqac_coordinator_name = Column(String(255), nullable=True)
    iqac_coordinator_email = Column(String(255), nullable=True)

    # Accreditation Details
    accreditation_status = Column(SQLEnum(AccreditationStatus), default=AccreditationStatus.NOT_ACCREDITED)
    naac_grade = Column(String(10), nullable=True)  # A++, A+, A, B++, B+, B, C
    naac_cgpa = Column(String(10), nullable=True)
    naac_validity = Column(DateTime, nullable=True)
    nba_accredited_programs = Column(JSON, default=list)  # List of program IDs

    # Approval Documents
    aicte_approval_number = Column(String(100), nullable=True)
    ugc_recognition = Column(Boolean, default=False)
    naac_application_id = Column(String(100), nullable=True)

    # Subscription
    subscription_plan = Column(SQLEnum(SubscriptionPlan), default=SubscriptionPlan.FREE_TRIAL)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)

    # Onboarding
    onboarding_step = Column(SQLEnum(OnboardingStep), default=OnboardingStep.REGISTRATION)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_completed_at = Column(DateTime, nullable=True)

    # Admin User (Principal/IQAC who registered)
    admin_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Logo
    logo_url = Column(String(500), nullable=True)

    # Statistics (cached for performance)
    total_students = Column(Integer, default=0)
    total_faculty = Column(Integer, default=0)
    total_programs = Column(Integer, default=0)
    total_departments = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    admin_user = relationship("User", foreign_keys=[admin_user_id])
    departments = relationship("CollegeDepartment", back_populates="college", cascade="all, delete-orphan")
    programs = relationship("CollegeProgram", back_populates="college", cascade="all, delete-orphan")
    invitations = relationship("CollegeInvitation", back_populates="college", cascade="all, delete-orphan")
    onboarding_progress = relationship("OnboardingProgress", back_populates="college", uselist=False)

    def __repr__(self):
        return f"<CollegeProfile {self.name}>"


class CollegeDepartment(Base):
    """Departments within a college"""
    __tablename__ = "college_departments"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("college_profiles.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    hod_name = Column(String(255), nullable=True)
    hod_email = Column(String(255), nullable=True)
    hod_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    faculty_count = Column(Integer, default=0)
    student_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    college = relationship("CollegeProfile", back_populates="departments")
    programs = relationship("CollegeProgram", back_populates="department")

    def __repr__(self):
        return f"<CollegeDepartment {self.name}>"


class CollegeProgram(Base):
    """Academic programs offered by college"""
    __tablename__ = "college_programs"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("college_profiles.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(GUID, ForeignKey("college_departments.id", ondelete="SET NULL"), nullable=True)

    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    degree_type = Column(String(50), nullable=True)  # B.Tech, M.Tech, MBA, etc.
    duration_years = Column(Integer, default=4)
    intake = Column(Integer, default=60)

    # NBA specific
    nba_accredited = Column(Boolean, default=False)
    nba_validity = Column(DateTime, nullable=True)
    tier = Column(Integer, nullable=True)  # NBA Tier 1 or Tier 2

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    college = relationship("CollegeProfile", back_populates="programs")
    department = relationship("CollegeDepartment", back_populates="programs")

    def __repr__(self):
        return f"<CollegeProgram {self.name}>"


class CollegeInvitation(Base):
    """Team member invitations"""
    __tablename__ = "college_invitations"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("college_profiles.id", ondelete="CASCADE"), nullable=False)

    # Invitee details
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)

    # Role to assign
    naac_role = Column(String(100), nullable=True)  # head_of_institution, iqac_coordinator, etc.
    department_id = Column(GUID, ForeignKey("college_departments.id", ondelete="SET NULL"), nullable=True)
    criterion_number = Column(Integer, nullable=True)  # 1-7 for criterion coordinators

    # Invitation details
    invite_token = Column(String(255), unique=True, nullable=False)
    status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.PENDING)

    # Who invited
    invited_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # If accepted, which user
    accepted_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)

    # Relationships
    college = relationship("CollegeProfile", back_populates="invitations")
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_id])

    def __repr__(self):
        return f"<CollegeInvitation {self.email}>"


class OnboardingProgress(Base):
    """Track onboarding progress for each college"""
    __tablename__ = "onboarding_progress"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("college_profiles.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Step completion flags
    registration_completed = Column(Boolean, default=False)
    profile_completed = Column(Boolean, default=False)
    departments_added = Column(Boolean, default=False)
    programs_added = Column(Boolean, default=False)
    team_invited = Column(Boolean, default=False)
    roles_assigned = Column(Boolean, default=False)
    first_data_entered = Column(Boolean, default=False)

    # Counts
    departments_count = Column(Integer, default=0)
    programs_count = Column(Integer, default=0)
    team_members_count = Column(Integer, default=0)
    invitations_sent = Column(Integer, default=0)
    invitations_accepted = Column(Integer, default=0)

    # Completion percentage
    completion_percentage = Column(Integer, default=0)

    # Current step
    current_step = Column(SQLEnum(OnboardingStep), default=OnboardingStep.REGISTRATION)

    # Timestamps for each step
    registration_at = Column(DateTime, nullable=True)
    profile_at = Column(DateTime, nullable=True)
    departments_at = Column(DateTime, nullable=True)
    programs_at = Column(DateTime, nullable=True)
    team_at = Column(DateTime, nullable=True)
    roles_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    college = relationship("CollegeProfile", back_populates="onboarding_progress")

    def __repr__(self):
        return f"<OnboardingProgress {self.college_id} - {self.completion_percentage}%>"

    def calculate_completion(self):
        """Calculate completion percentage"""
        steps = [
            self.registration_completed,
            self.profile_completed,
            self.departments_added,
            self.programs_added,
            self.team_invited,
            self.roles_assigned
        ]
        completed = sum(1 for s in steps if s)
        self.completion_percentage = int((completed / len(steps)) * 100)
        return self.completion_percentage
