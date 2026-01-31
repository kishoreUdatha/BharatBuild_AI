"""
Assessment & Marks Management Models
College-grade marks management with full audit trail, approval workflow, and ERP sync
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
import uuid


def generate_uuid():
    return str(uuid.uuid4())


# ==================== Enums ====================

class AssessmentType(str, enum.Enum):
    INTERNAL_TEST = "internal_test"
    ASSIGNMENT = "assignment"
    LAB = "lab"
    PROJECT_REVIEW = "project_review"
    VIVA = "viva"
    QUIZ = "quiz"
    MID_SEM = "mid_sem"
    END_SEM = "end_sem"
    PRACTICAL = "practical"


class MarksStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    LOCKED = "locked"
    REJECTED = "rejected"


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


# ==================== Assessment Configuration ====================

class AssessmentConfig(Base):
    """Configuration for assessment types per subject"""
    __tablename__ = "assessment_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Context
    academic_year = Column(String(20), nullable=False)  # e.g., "2025-26"
    semester = Column(Integer, nullable=False)
    subject_id = Column(String(36), nullable=True)
    subject_code = Column(String(20), nullable=True)
    subject_name = Column(String(255), nullable=True)
    department_id = Column(String(36), nullable=True)

    # Assessment details
    assessment_type = Column(Enum(AssessmentType), nullable=False)
    assessment_name = Column(String(255), nullable=False)  # e.g., "Internal Test 1"
    max_marks = Column(Integer, nullable=False)
    weightage = Column(Float, default=100.0)  # Percentage contribution to final

    # Dates
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    entry_deadline = Column(DateTime(timezone=True), nullable=True)

    # Configuration
    is_active = Column(Boolean, default=True)
    auto_populate = Column(Boolean, default=False)  # Auto-fetch from platform
    source_type = Column(String(50), nullable=True)  # quiz, lab_test, project, etc.

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LabMarksConfig(Base):
    """Lab marks component configuration (weightage breakdown)"""
    __tablename__ = "lab_marks_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    academic_year = Column(String(20), nullable=False)
    semester = Column(Integer, nullable=False)
    lab_id = Column(String(36), nullable=True)
    lab_name = Column(String(255), nullable=True)
    department_id = Column(String(36), nullable=True)

    # Weightage components (must sum to 100)
    experiment_completion_weightage = Column(Float, default=40.0)
    lab_test_weightage = Column(Float, default=30.0)
    record_documentation_weightage = Column(Float, default=20.0)
    viva_weightage = Column(Float, default=10.0)

    # Additional components (optional)
    additional_components = Column(JSON, default=list)  # [{name, weightage}]

    total_max_marks = Column(Integer, default=100)

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by = Column(String(36), nullable=True)  # HOD approval
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ==================== Marks Entry ====================

class MarksHeader(Base):
    """Marks sheet header - one per assessment per section"""
    __tablename__ = "marks_headers"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Context
    academic_year = Column(String(20), nullable=False)
    semester = Column(Integer, nullable=False)
    subject_id = Column(String(36), nullable=True)
    subject_code = Column(String(20), nullable=True)
    subject_name = Column(String(255), nullable=True)
    section_id = Column(String(36), nullable=True)
    section_name = Column(String(50), nullable=True)  # e.g., "CSE-3A"
    department_id = Column(String(36), nullable=True)

    # Assessment info
    assessment_type = Column(Enum(AssessmentType), nullable=False)
    assessment_name = Column(String(255), nullable=False)
    assessment_date = Column(DateTime(timezone=True), nullable=True)
    max_marks = Column(Integer, nullable=False)

    # Status
    status = Column(Enum(MarksStatus), default=MarksStatus.DRAFT)

    # Faculty who entered
    entered_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    entered_at = Column(DateTime(timezone=True), nullable=True)

    # Submission
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submitted_by = Column(String(36), nullable=True)

    # HOD Review
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_remarks = Column(Text, nullable=True)

    # Approval
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Lock
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(36), nullable=True)
    unlock_reason = Column(Text, nullable=True)

    # Stats (calculated)
    total_students = Column(Integer, default=0)
    students_present = Column(Integer, default=0)
    average_marks = Column(Float, nullable=True)
    highest_marks = Column(Float, nullable=True)
    lowest_marks = Column(Float, nullable=True)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)

    # ERP Sync
    erp_synced = Column(Boolean, default=False)
    erp_sync_status = Column(Enum(SyncStatus), nullable=True)
    erp_sync_at = Column(DateTime(timezone=True), nullable=True)
    erp_sync_reference = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    details = relationship("MarksDetail", back_populates="header", cascade="all, delete-orphan")
    audits = relationship("MarksAudit", back_populates="header", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_marks_header_context', 'academic_year', 'semester', 'subject_id', 'section_id'),
    )


class MarksDetail(Base):
    """Individual student marks"""
    __tablename__ = "marks_details"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    header_id = Column(String(36), ForeignKey("marks_headers.id", ondelete="CASCADE"), nullable=False)

    # Student info (denormalized for quick access)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    roll_number = Column(String(50), nullable=True)
    student_name = Column(String(100), nullable=True)

    # Marks
    obtained_marks = Column(Float, nullable=True)  # Null if absent
    is_absent = Column(Boolean, default=False)
    is_exempted = Column(Boolean, default=False)
    exemption_reason = Column(String(255), nullable=True)

    # Additional info
    attendance_percentage = Column(Float, nullable=True)
    remarks = Column(Text, nullable=True)

    # Grade (if applicable)
    grade = Column(String(5), nullable=True)
    grade_points = Column(Float, nullable=True)

    # Lab-specific breakdown
    lab_experiment_marks = Column(Float, nullable=True)
    lab_test_marks = Column(Float, nullable=True)
    lab_record_marks = Column(Float, nullable=True)
    lab_viva_marks = Column(Float, nullable=True)

    # Auto-populated marks sources
    auto_populated = Column(Boolean, default=False)
    source_type = Column(String(50), nullable=True)
    source_id = Column(String(36), nullable=True)

    # Moderation
    original_marks = Column(Float, nullable=True)  # Before moderation
    moderation_applied = Column(Float, nullable=True)  # +/- adjustment
    moderation_reason = Column(String(255), nullable=True)

    # Status
    is_finalized = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    header = relationship("MarksHeader", back_populates="details")

    __table_args__ = (
        Index('ix_marks_detail_student', 'header_id', 'student_id'),
    )


class MarksAudit(Base):
    """Complete audit trail for marks changes"""
    __tablename__ = "marks_audits"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    header_id = Column(String(36), ForeignKey("marks_headers.id", ondelete="CASCADE"), nullable=False)
    detail_id = Column(String(36), nullable=True)  # Null for header-level changes

    # Who made the change
    changed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    changed_by_name = Column(String(100), nullable=True)
    changed_by_role = Column(String(50), nullable=True)

    # Change details
    field_changed = Column(String(100), nullable=False)  # e.g., "obtained_marks", "status"
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    # Context
    action = Column(String(50), nullable=False)  # create, update, delete, submit, approve, lock, unlock
    reason = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    header = relationship("MarksHeader", back_populates="audits")

    __table_args__ = (
        Index('ix_marks_audit_header', 'header_id'),
        Index('ix_marks_audit_time', 'created_at'),
    )


# ==================== Approval Workflow ====================

class MarksApprovalRequest(Base):
    """Approval workflow for marks submission"""
    __tablename__ = "marks_approval_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    header_id = Column(String(36), ForeignKey("marks_headers.id", ondelete="CASCADE"), nullable=False)

    # Request details
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    request_remarks = Column(Text, nullable=True)

    # Current approver
    current_approver_id = Column(String(36), nullable=True)
    current_approver_role = Column(String(50), nullable=True)  # HOD, Admin

    # Response
    response_status = Column(String(20), nullable=True)  # approved, rejected, pending
    responded_by = Column(String(36), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    response_remarks = Column(Text, nullable=True)

    # Multi-level approval tracking
    approval_chain = Column(JSON, default=list)  # [{level, approver_id, status, timestamp}]
    current_level = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MarksUnlockRequest(Base):
    """Request to unlock approved/locked marks"""
    __tablename__ = "marks_unlock_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    header_id = Column(String(36), ForeignKey("marks_headers.id", ondelete="CASCADE"), nullable=False)

    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(Text, nullable=False)

    # Approval
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    is_approved = Column(Boolean, nullable=True)
    admin_remarks = Column(Text, nullable=True)

    # Tracking
    unlocked_until = Column(DateTime(timezone=True), nullable=True)  # Time-limited unlock
    was_relocked = Column(Boolean, default=False)
    relocked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==================== ERP Sync ====================

class ERPSyncLog(Base):
    """Log of all ERP sync attempts"""
    __tablename__ = "erp_sync_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    header_id = Column(String(36), ForeignKey("marks_headers.id", ondelete="CASCADE"), nullable=False)

    # Sync details
    sync_type = Column(String(50), nullable=False)  # push_api, csv_upload, db_sync
    sync_status = Column(Enum(SyncStatus), nullable=False)

    # Request/Response
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Reference
    erp_reference_id = Column(String(100), nullable=True)
    records_synced = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    initiated_by = Column(String(36), ForeignKey("users.id"), nullable=False)


# ==================== Analytics & Reports ====================

class MarksAnalytics(Base):
    """Pre-computed analytics for quick dashboard access"""
    __tablename__ = "marks_analytics"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Context
    academic_year = Column(String(20), nullable=False)
    semester = Column(Integer, nullable=False)
    department_id = Column(String(36), nullable=True)
    subject_id = Column(String(36), nullable=True)
    section_id = Column(String(36), nullable=True)
    assessment_type = Column(Enum(AssessmentType), nullable=True)

    # Aggregated metrics
    total_students = Column(Integer, default=0)
    students_appeared = Column(Integer, default=0)
    average_marks = Column(Float, nullable=True)
    median_marks = Column(Float, nullable=True)
    standard_deviation = Column(Float, nullable=True)
    highest_marks = Column(Float, nullable=True)
    lowest_marks = Column(Float, nullable=True)

    # Pass/Fail
    pass_percentage = Column(Float, nullable=True)
    fail_percentage = Column(Float, nullable=True)
    distinction_count = Column(Integer, default=0)  # >75%
    first_class_count = Column(Integer, default=0)  # 60-75%
    second_class_count = Column(Integer, default=0)  # 50-60%
    pass_count = Column(Integer, default=0)  # 40-50%
    fail_count = Column(Integer, default=0)  # <40%

    # Grade distribution
    grade_distribution = Column(JSON, default=dict)  # {A: 10, B: 20, ...}

    # Comparison
    section_rank = Column(Integer, nullable=True)
    department_rank = Column(Integer, nullable=True)

    # Top/Weak students
    top_students = Column(JSON, default=list)  # [{student_id, name, marks}]
    weak_students = Column(JSON, default=list)

    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_marks_analytics_context', 'academic_year', 'semester', 'department_id'),
    )
