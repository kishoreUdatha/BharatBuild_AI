"""
Batch Detail Models - everything behind the Batch Registration Details screen.

The seven tabs there each need structure the core faculty models do not carry:
objectives and methodology (Project Details), extended paper metadata and
supporting papers (Base Papers), versioned documents (Documents), review cycles
(Approval History) and an immutable audit trail (Activity Log).
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# --------------------------------------------------------------- enumerations

class ItemStatus(str, enum.Enum):
    """Generic completion state for objectives, scope items and the like."""
    COMPLETE = "complete"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"


class ScopeKind(str, enum.Enum):
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    DELIVERABLE = "deliverable"
    OUTCOME = "outcome"


class DocumentStatus(str, enum.Enum):
    VERIFIED = "verified"
    AWAITING_VERIFICATION = "awaiting_verification"
    CHANGES_REQUESTED = "changes_requested"
    MISSING = "missing"


DOCUMENT_STATUS_LABELS = {
    DocumentStatus.VERIFIED: "Verified",
    DocumentStatus.AWAITING_VERIFICATION: "Awaiting Verification",
    DocumentStatus.CHANGES_REQUESTED: "Changes Requested",
    DocumentStatus.MISSING: "Missing",
}


class ApprovalEventKind(str, enum.Enum):
    SUBMITTED = "submitted"
    REVIEW_STARTED = "review_started"
    CHANGES_REQUESTED = "changes_requested"
    RESUBMITTED = "resubmitted"
    DOCUMENTS_VERIFIED = "documents_verified"
    FINAL_REVIEW = "final_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActivitySeverity(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"


# ------------------------------------------------------------ project details

class ProjectObjective(Base):
    """One numbered objective on the Project Details tab."""
    __tablename__ = "project_objectives"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    position = Column(Integer, default=0)
    text = Column(Text, nullable=False)
    status = Column(SQLEnum(ItemStatus), default=ItemStatus.PENDING, nullable=False)

    batch = relationship("ProjectBatch", back_populates="objectives")


class ProjectMethodologyStep(Base):
    """A step in the proposed methodology strip."""
    __tablename__ = "project_methodology_steps"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    position = Column(Integer, default=0)
    title = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)

    batch = relationship("ProjectBatch", back_populates="methodology")


class ProjectScopeItem(Base):
    """In scope / out of scope / deliverable / expected outcome, one line each."""
    __tablename__ = "project_scope_items"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    kind = Column(SQLEnum(ScopeKind), nullable=False, index=True)
    position = Column(Integer, default=0)
    text = Column(Text, nullable=False)

    batch = relationship("ProjectBatch", back_populates="scope_items")


class ProjectTechnology(Base):
    """One entry in the technology stack, grouped by layer."""
    __tablename__ = "project_technologies"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    layer = Column(String(60), nullable=False)   # Frontend, Backend, Machine Learning, ...
    name = Column(String(80), nullable=False)
    position = Column(Integer, default=0)

    batch = relationship("ProjectBatch", back_populates="technologies")


# ----------------------------------------------------------------- base papers

class SupportingPaper(Base):
    """A secondary reference listed alongside the primary base paper."""
    __tablename__ = "supporting_papers"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    authors = Column(String(255), nullable=True)
    source = Column(String(160), nullable=True)
    year = Column(Integer, nullable=True)
    doi = Column(String(160), nullable=True)
    purpose = Column(String(120), nullable=True)   # "Benchmark Comparison", ...
    url = Column(Text, nullable=True)

    batch = relationship("ProjectBatch", back_populates="supporting_papers")


class PaperMetric(Base):
    """A reported metric from the primary paper (MAE, RMSE, MAPE, ...)."""
    __tablename__ = "paper_metrics"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    base_paper_id = Column(GUID, ForeignKey("base_papers.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(40), nullable=False)
    value = Column(String(40), nullable=False)
    position = Column(Integer, default=0)

    base_paper = relationship("BasePaper", back_populates="metrics")


class PaperKeyMethod(Base):
    """A method chip under the base paper summary."""
    __tablename__ = "paper_key_methods"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    base_paper_id = Column(GUID, ForeignKey("base_papers.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(80), nullable=False)
    position = Column(Integer, default=0)

    base_paper = relationship("BasePaper", back_populates="key_methods")


class NovelContribution(Base):
    """A numbered novelty claim in 'Proposed Improvement Over Base Paper'."""
    __tablename__ = "novel_contributions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    position = Column(Integer, default=0)
    text = Column(Text, nullable=False)

    batch = relationship("ProjectBatch", back_populates="contributions")


# ------------------------------------------------------------------ documents

class BatchDocument(Base):
    """
    A registration document with its version and verification state.

    Verified documents are locked: a new upload creates a new row with a bumped
    version rather than mutating the verified one, so history is preserved.
    """
    __tablename__ = "batch_documents"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    category = Column(String(80), nullable=False, index=True)   # Student Declaration, Project Document, ...
    version = Column(String(16), default="v1.0")
    # The bytes. Nullable because a required-but-missing document is a real
    # row on the checklist - it is what "Missing" means.
    file_id = Column(GUID, ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True, index=True)
    file_size = Column(Integer, default=0)
    page_count = Column(Integer, nullable=True)
    mime_type = Column(String(120), nullable=True)

    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.AWAITING_VERIFICATION, nullable=False, index=True)
    is_required = Column(Boolean, default=False)
    faculty_note = Column(Text, nullable=True)
    similarity_percent = Column(Float, nullable=True)
    virus_scan_passed = Column(Boolean, default=True)

    uploaded_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    verified_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    superseded_by_id = Column(GUID, ForeignKey("batch_documents.id", ondelete="SET NULL"), nullable=True)

    batch = relationship("ProjectBatch", back_populates="documents")
    file = relationship("StoredFile", foreign_keys=[file_id])
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    def __repr__(self):
        return f"<BatchDocument {self.name} {self.version}>"


# ----------------------------------------------------------- approval history

class ApprovalEvent(Base):
    """One entry in the approval journey, grouped into review cycles."""
    __tablename__ = "approval_events"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    cycle = Column(Integer, default=1, index=True)
    kind = Column(SQLEnum(ApprovalEventKind), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=True)
    status_label = Column(String(60), nullable=True)   # "Submitted", "Changes Requested", ...

    actor_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_role = Column(String(60), nullable=True)     # Faculty Reviewer, Batch Leader, Coordinator
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=True)
    is_private = Column(Boolean, default=False)        # internal note: students never see it

    batch = relationship("ProjectBatch", back_populates="approval_events")
    actor = relationship("User", foreign_keys=[actor_id])


# --------------------------------------------------------------- activity log

class ActivityLog(Base):
    """
    Immutable audit record. Nothing in the app updates or deletes these rows -
    the Activity Log tab states they are retained for audit, so writes are
    append-only by convention and the service never exposes a mutation.
    """
    __tablename__ = "activity_logs"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    event_code = Column(String(32), nullable=False, index=True)   # ACT-2026-048
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=True, index=True)

    actor_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_name = Column(String(120), nullable=True)   # kept even if the user is removed
    actor_role = Column(String(60), nullable=True)    # Faculty, Student, Batch Leader, System

    activity = Column(String(255), nullable=False)
    module = Column(String(60), nullable=False, index=True)   # Approval, Documents, Registration, ...
    details = Column(Text, nullable=True)
    status_label = Column(String(60), nullable=True)
    severity = Column(SQLEnum(ActivitySeverity), default=ActivitySeverity.INFO, nullable=False, index=True)

    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    source = Column(String(80), nullable=True)        # Faculty Portal / Web
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Optional before/after for the change-summary panel.
    changed_field = Column(String(80), nullable=True)
    previous_value = Column(String(255), nullable=True)
    current_value = Column(String(255), nullable=True)

    batch = relationship("ProjectBatch", back_populates="activities")
    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self):
        return f"<ActivityLog {self.event_code} {self.activity[:40]}>"
