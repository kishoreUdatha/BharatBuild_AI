# Re-export all models for convenient imports
# Colleges first: every portal table now carries a foreign key to it,
# so the table has to be in the metadata before those models load.
from app.models.college import College
from app.models.user import User, UserRole
from app.models.milestones import (
    ApprovalState,
    EvidenceStatus,
    MilestoneChecklistItem,
    MilestoneDependency,
    MilestoneEvidence,
    MilestonePriority,
    MilestoneStatus,
    ProjectMilestone,
)
from app.models.project_tracking import (
    BatchIntegration,
    BlockerCategory,
    BlockerSeverity,
    BlockerStatus,
    ProjectBlocker,
    TaskAttachment,
    TaskComment,
    TaskDependency,
    DeliverableStatus,
    IntegrationKind,
    IntegrationState,
    ProjectDeliverable,
    ProjectTask,
    TaskPriority,
    TaskStatus,
)
from app.models.files import StoredFile
from app.models.project import Project, ProjectStatus
from app.models.file_version import ProjectFileVersion
from app.models.project_file import ProjectFile, FileGenerationStatus
from app.models.document import Document
from app.models.billing import Plan, Subscription, SubscriptionStatus, Transaction, PlanType
from app.models.usage import UsageLog, TokenUsage, TokenUsageLog, AgentType, OperationType
from app.models.api_key import APIKey, APIKeyStatus
from app.models.audit_log import AuditLog
from app.models.system_setting import SystemSetting
from app.models.workspace import Workspace
from app.models.token_balance import TokenBalance, TokenTransaction, TokenPurchase
from app.models.sandbox import SandboxInstance, SandboxStatus
from app.models.session import Session
from app.models.snapshot import Snapshot
from app.models.agent_task import AgentTask
from app.models.project_message import ProjectMessage
from app.models.workshop_enrollment import WorkshopEnrollment
from app.models.campus_drive import (
    CampusDrive,
    CampusDriveRegistration,
    CampusDriveQuestion,
    CampusDriveResponse,
    QuestionCategory,
    QuestionDifficulty,
    RegistrationStatus,
)
from app.models.faculty import (
    StudentEnrollment,
    ProjectBatch,
    ProjectBatchMember,
    BatchStageProgress,
    ProjectReview,
    AttendanceRecord,
    BasePaper,
    ProjectSubmission,
    ProjectStage,
    AttendanceStatus,
    ReviewStatus,
    BasePaperStatus,
    BatchRegistrationStatus,
    StudentProfileStatus,
    SubmissionStatus,
    MemberInviteStatus,
    PaymentStatus,
    RegistrationPayment,
)
from app.models.batch_detail import (
    ProjectObjective,
    ProjectMethodologyStep,
    ProjectScopeItem,
    ProjectTechnology,
    SupportingPaper,
    PaperMetric,
    PaperKeyMethod,
    NovelContribution,
    BatchDocument,
    ApprovalEvent,
    ActivityLog,
    ItemStatus,
    ScopeKind,
    DocumentStatus,
    ApprovalEventKind,
    ActivitySeverity,
)
from app.models.backlog import (
    ProjectSprint,
    StoryAttachment,
    SprintState,
    StoryComment,
    StoryEvent,
    StoryEventKind,
    StoryType,
    StoryWorkflowStatus,
)
from app.models.ai_planning import (
    AiPlanningRun,
    ProjectEpic,
    ProjectUserStory,
    StoryCriterion,
    StoryRevisionRequest,
    StoryReviewStatus,
    StoryPriority,
    CriterionKind,
)
from app.models.verification import (
    VerificationCode,
    VerificationChannel,
    VerificationPurpose,
)
from app.models.academics import (
    AcademicDepartment,
    AcademicSection,
    SectionFacultyAssignment,
    SectionSubject,
    DepartmentNotice,
    SectionUpdateRequest,
    SectionStatus,
    SubjectKind,
    NoticeSeverity,
    UpdateRequestStatus,
)
from app.models.faculty_import import (
    ImportRun,
    ImportRowIssue,
    ImportEvent,
    ImportType,
    ImportStatus,
    IssueSeverity,
)
from app.models.story_commit import StoryCommit
from app.models.student_git_identity import StudentGitIdentity
from app.models.faculty import AttendanceSessionLog
from app.models.coupon import (
    Coupon,
    CouponUsage,
    CouponCategory,
    CouponStatus,
    Wallet,
    WalletTransaction,
    WalletTransactionType,
    WalletTransactionSource,
)

__all__ = [
    "ProjectSprint",
    "StoryAttachment",
    "SprintState",
    "StoryComment",
    "StoryEvent",
    "StoryEventKind",
    "StoryType",
    "StoryWorkflowStatus",
    "AiPlanningRun",
    "ProjectEpic",
    "ProjectUserStory",
    "StoryCriterion",
    "StoryRevisionRequest",
    "StoryReviewStatus",
    "StoryPriority",
    "CriterionKind",
    "VerificationCode",
    "VerificationChannel",
    "VerificationPurpose",
    "RegistrationPayment",
    "MemberInviteStatus",
    "PaymentStatus",
    "AcademicDepartment",
    "AcademicSection",
    "SectionFacultyAssignment",
    "SectionSubject",
    "DepartmentNotice",
    "SectionUpdateRequest",
    "SectionStatus",
    "SubjectKind",
    "NoticeSeverity",
    "UpdateRequestStatus",
    # Faculty portal
    "StudentEnrollment",
    "ProjectBatch",
    "ProjectBatchMember",
    "BatchStageProgress",
    "ProjectReview",
    "AttendanceRecord",
    "BasePaper",
    "ProjectSubmission",
    "ProjectStage",
    "AttendanceStatus",
    "ReviewStatus",
    "BasePaperStatus",
    "BatchRegistrationStatus",
    "StudentProfileStatus",
    "ProjectObjective",
    "ProjectMethodologyStep",
    "ProjectScopeItem",
    "ProjectTechnology",
    "SupportingPaper",
    "PaperMetric",
    "PaperKeyMethod",
    "NovelContribution",
    "BatchDocument",
    "ApprovalEvent",
    "ActivityLog",
    "ItemStatus",
    "ScopeKind",
    "DocumentStatus",
    "ApprovalEventKind",
    "ActivitySeverity",
    "ImportRun",
    "ImportRowIssue",
    "ImportEvent",
    "ImportType",
    "ImportStatus",
    "IssueSeverity",
    "SubmissionStatus",
    # User
    "User",
    "UserRole",
    # Project
    "Project",
    "ProjectStatus",
    "ProjectFile",
    "ProjectFileVersion",
    "FileGenerationStatus",
    "ProjectMessage",
    # Documents
    "Document",
    # Billing
    "Plan",
    "PlanType",
    "Subscription",
    "SubscriptionStatus",
    "Transaction",
    # Usage
    "UsageLog",
    "TokenUsage",
    "TokenUsageLog",
    "AgentType",
    "OperationType",
    # API Keys
    "APIKey",
    "APIKeyStatus",
    # Admin
    "AuditLog",
    "SystemSetting",
    # Workspace
    "Workspace",
    # Tokens
    "TokenBalance",
    "TokenTransaction",
    "TokenPurchase",
    # Sandbox
    "SandboxInstance",
    "SandboxStatus",
    # Session
    "Session",
    # Snapshot
    "Snapshot",
    # Agent
    "AgentTask",
    # Workshop
    "WorkshopEnrollment",
    # Campus Drive
    "CampusDrive",
    "CampusDriveRegistration",
    "CampusDriveQuestion",
    "CampusDriveResponse",
    "QuestionCategory",
    "QuestionDifficulty",
    "RegistrationStatus",
    # Coupon & Wallet
    "Coupon",
    "CouponUsage",
    "CouponCategory",
    "CouponStatus",
    "Wallet",
    "WalletTransaction",
    "WalletTransactionType",
    "WalletTransactionSource",
    # Git
    "StoryCommit",
    "StudentGitIdentity",
    "AttendanceSessionLog",
]

# Registered so metadata (and therefore Alembic) sees the table.
from app.models.trainer_assignment import TrainerAssignment  # noqa: E402,F401
