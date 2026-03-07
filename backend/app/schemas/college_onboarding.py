"""
College Onboarding Schemas
Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CollegeTypeEnum(str, Enum):
    AUTONOMOUS = "autonomous"
    AFFILIATED = "affiliated"
    DEEMED = "deemed"
    CENTRAL = "central"
    STATE = "state"
    PRIVATE = "private"


class SubscriptionPlanEnum(str, Enum):
    FREE_TRIAL = "free_trial"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class OnboardingStepEnum(str, Enum):
    REGISTRATION = "registration"
    PROFILE_SETUP = "profile_setup"
    DEPARTMENTS = "departments"
    PROGRAMS = "programs"
    TEAM_SETUP = "team_setup"
    ROLE_ASSIGNMENT = "role_assignment"
    COMPLETED = "completed"


# ============== College Registration ==============

class CollegeRegistrationRequest(BaseModel):
    """Initial college registration"""
    # College Details
    name: str = Field(..., min_length=3, max_length=500)
    short_name: Optional[str] = Field(None, max_length=100)
    aishe_code: Optional[str] = Field(None, max_length=50)
    college_type: CollegeTypeEnum = CollegeTypeEnum.AFFILIATED
    university_affiliation: Optional[str] = None
    year_established: Optional[int] = Field(None, ge=1800, le=2030)

    # Address
    address: Optional[str] = None
    city: str = Field(..., min_length=2)
    state: str = Field(..., min_length=2)
    pincode: Optional[str] = Field(None, max_length=10)

    # Contact
    phone: Optional[str] = None
    email: EmailStr
    website: Optional[str] = None

    # Principal Details
    principal_name: str = Field(..., min_length=2)
    principal_email: EmailStr
    principal_phone: Optional[str] = None

    # Admin Account
    admin_password: str = Field(..., min_length=8)

    # Subscription
    subscription_plan: SubscriptionPlanEnum = SubscriptionPlanEnum.FREE_TRIAL


class CollegeRegistrationResponse(BaseModel):
    id: str
    name: str
    aishe_code: Optional[str]
    admin_user_id: str
    onboarding_step: str
    message: str
    access_token: Optional[str] = None

    class Config:
        from_attributes = True


# ============== College Profile ==============

class CollegeProfileUpdate(BaseModel):
    """Update college profile"""
    name: Optional[str] = None
    short_name: Optional[str] = None
    aishe_code: Optional[str] = None
    college_type: Optional[CollegeTypeEnum] = None
    university_affiliation: Optional[str] = None
    year_established: Optional[int] = None

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None

    principal_name: Optional[str] = None
    principal_email: Optional[EmailStr] = None
    principal_phone: Optional[str] = None
    iqac_coordinator_name: Optional[str] = None
    iqac_coordinator_email: Optional[EmailStr] = None

    aicte_approval_number: Optional[str] = None
    ugc_recognition: Optional[bool] = None
    naac_application_id: Optional[str] = None

    total_students: Optional[int] = None
    total_faculty: Optional[int] = None


class CollegeProfileResponse(BaseModel):
    id: str
    name: str
    short_name: Optional[str]
    aishe_code: Optional[str]
    college_type: str
    university_affiliation: Optional[str]
    year_established: Optional[int]

    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]

    principal_name: Optional[str]
    principal_email: Optional[str]
    iqac_coordinator_name: Optional[str]
    iqac_coordinator_email: Optional[str]

    accreditation_status: str
    naac_grade: Optional[str]
    subscription_plan: str
    onboarding_step: str
    onboarding_completed: bool

    total_students: int
    total_faculty: int
    total_programs: int
    total_departments: int

    created_at: datetime

    class Config:
        from_attributes = True


# ============== Departments ==============

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2)
    code: Optional[str] = None
    hod_name: Optional[str] = None
    hod_email: Optional[EmailStr] = None


class DepartmentResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    hod_name: Optional[str]
    hod_email: Optional[str]
    faculty_count: int
    student_count: int
    is_active: bool

    class Config:
        from_attributes = True


class DepartmentBulkCreate(BaseModel):
    """Create multiple departments at once"""
    departments: List[DepartmentCreate]


# ============== Programs ==============

class ProgramCreate(BaseModel):
    name: str = Field(..., min_length=2)
    code: Optional[str] = None
    department_id: Optional[str] = None
    degree_type: str = Field(..., min_length=2)  # B.Tech, M.Tech, MBA
    duration_years: int = Field(4, ge=1, le=7)
    intake: int = Field(60, ge=1)


class ProgramResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    department_id: Optional[str]
    degree_type: str
    duration_years: int
    intake: int
    nba_accredited: bool
    is_active: bool

    class Config:
        from_attributes = True


class ProgramBulkCreate(BaseModel):
    """Create multiple programs at once"""
    programs: List[ProgramCreate]


# ============== Team Invitations ==============

class TeamInviteRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    naac_role: str  # head_of_institution, iqac_coordinator, criterion_coordinator, etc.
    department_id: Optional[str] = None
    criterion_number: Optional[int] = Field(None, ge=1, le=7)


class TeamInviteBulkRequest(BaseModel):
    """Send multiple invitations"""
    invitations: List[TeamInviteRequest]


class TeamInviteResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    naac_role: str
    status: str
    invite_link: str
    expires_at: datetime

    class Config:
        from_attributes = True


class InvitationAcceptRequest(BaseModel):
    """Accept an invitation"""
    token: str
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)


# ============== Onboarding Progress ==============

class OnboardingProgressResponse(BaseModel):
    current_step: str
    completion_percentage: int

    registration_completed: bool
    profile_completed: bool
    departments_added: bool
    programs_added: bool
    team_invited: bool
    roles_assigned: bool

    departments_count: int
    programs_count: int
    team_members_count: int
    invitations_sent: int
    invitations_accepted: int

    next_action: str
    checklist: List[dict]

    class Config:
        from_attributes = True


# ============== Onboarding Checklist ==============

class ChecklistItem(BaseModel):
    id: str
    title: str
    description: str
    completed: bool
    required: bool
    link: Optional[str] = None


class OnboardingChecklist(BaseModel):
    total_items: int
    completed_items: int
    completion_percentage: int
    items: List[ChecklistItem]
