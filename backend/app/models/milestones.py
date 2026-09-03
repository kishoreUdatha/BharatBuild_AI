"""
Milestones: the plannable units inside a project, and their approval trail.

`BatchStageProgress` already tracks the eight fixed stages every project moves
through - a percentage and two dates per stage. That is the coarse shape of a
project and it stays.

This is finer and different in kind. The milestones a coordinator actually
plans around are named by the team ("API Integration", "Model Prototype",
"Dataset Preparation"), belong to a stage rather than being one, and carry
things a percentage cannot: somebody who owns delivering it, somebody who
reviews it, the evidence that it happened, a checklist of what "done" means,
and the other milestones it waits on.

The approval trail is the reason this is a table rather than a column. A
milestone that is 100% complete and a milestone a reviewer has accepted are
different states, and conflating them is how a project reaches its final
review with nothing signed off.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class MilestonePriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MilestoneStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    DELAYED = "delayed"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class ApprovalState(str, enum.Enum):
    """
    Where a milestone stands with its reviewer.

    Separate from status on purpose: work can be finished and unreviewed, or
    reviewed and sent back. NOT_READY is the resting state - nothing has been
    submitted yet and nobody is waiting on anybody.
    """
    NOT_READY = "not_ready"
    PENDING = "pending"
    REVIEW_READY = "review_ready"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class EvidenceStatus(str, enum.Enum):
    PENDING = "pending"        # asked for, nothing supplied
    UPLOADED = "uploaded"      # supplied, not yet looked at
    AVAILABLE = "available"    # a link rather than a file
    VERIFIED = "verified"      # a reviewer has accepted it


class ProjectMilestone(Base):
    """One planned, owned, reviewable milestone on a batch."""
    __tablename__ = "project_milestones"
    __table_args__ = (
        UniqueConstraint("batch_id", "name", name="uq_milestone_per_batch"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    name = Column(String(200), nullable=False)
    detail = Column(Text, nullable=True)

    # Which of the eight stages this milestone belongs to. Nullable because a
    # team may plan work that does not map neatly onto one.
    stage = Column(SQLEnum("TOPIC_APPROVAL", "BASE_PAPER", "REQUIREMENTS",
                           "SYSTEM_DESIGN", "DEVELOPMENT", "TESTING",
                           "DOCUMENTATION", "FINAL_REVIEW",
                           name="projectstage", create_type=False),
                   nullable=True, index=True)

    priority = Column(SQLEnum(MilestonePriority), nullable=False,
                      default=MilestonePriority.MEDIUM, index=True)
    status = Column(SQLEnum(MilestoneStatus), nullable=False,
                    default=MilestoneStatus.NOT_STARTED, index=True)
    approval = Column(SQLEnum(ApprovalState), nullable=False,
                      default=ApprovalState.NOT_READY, index=True)

    # The student delivering it, and the staff member who signs it off.
    owner_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"),
                      nullable=True, index=True)
    reviewer_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"),
                         nullable=True, index=True)

    planned_start = Column(Date, nullable=True)
    planned_date = Column(Date, nullable=True, index=True)
    # What the team now expects, as distinct from what was planned. Keeping
    # both is what makes a slipping milestone visible before the date passes.
    forecast_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    progress = Column(Integer, default=0, nullable=False)
    position = Column(Integer, default=0)

    approved_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    review_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch")
    owner = relationship("User", foreign_keys=[owner_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def __repr__(self) -> str:
        return f"<ProjectMilestone {self.name} {self.status}>"


class MilestoneChecklistItem(Base):
    """
    One condition of "done".

    A milestone at 65% says nothing about what is left. The checklist is what
    a reviewer reads before approving, and what the owner works down.
    """
    __tablename__ = "milestone_checklist_items"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    milestone_id = Column(GUID, ForeignKey("project_milestones.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    label = Column(String(300), nullable=False)
    is_done = Column(Integer, default=0, nullable=False)   # 0/1, sums cheaply
    position = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    milestone = relationship("ProjectMilestone", foreign_keys=[milestone_id])


class MilestoneEvidence(Base):
    """
    Proof that a milestone happened.

    Either a stored file or a link - a demo URL is evidence as much as a PDF
    is. The status is the reviewer's view of it, not the uploader's.
    """
    __tablename__ = "milestone_evidence"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    milestone_id = Column(GUID, ForeignKey("project_milestones.id", ondelete="CASCADE"),
                          nullable=False, index=True)

    label = Column(String(200), nullable=False)
    status = Column(SQLEnum(EvidenceStatus), nullable=False,
                    default=EvidenceStatus.PENDING, index=True)

    file_id = Column(GUID, ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True)
    url = Column(String(500), nullable=True)

    submitted_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    verified_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    position = Column(Integer, default=0)

    milestone = relationship("ProjectMilestone", foreign_keys=[milestone_id])


class MilestoneDependency(Base):
    """One milestone waiting on another. Directional, de-duplicated."""
    __tablename__ = "milestone_dependencies"
    __table_args__ = (
        UniqueConstraint("milestone_id", "depends_on_id", name="uq_milestone_dependency"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    milestone_id = Column(GUID, ForeignKey("project_milestones.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    depends_on_id = Column(GUID, ForeignKey("project_milestones.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
