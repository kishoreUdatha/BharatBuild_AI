"""
The things a project tracker needs that the portal did not already model.

Most of the tracking screen can be derived from what exists: the eight
`ProjectStage` rows already carry percent-complete and a completion date, so
they are the milestone timeline; `ProjectReview` supplies reviews due;
`ActivityLog` supplies the activity feed; and progress, schedule and health all
follow from `overall_progress` against the batch's own dates.

Three things had no home at all:

* **Tasks and blockers.** Nothing recorded who is doing what by when, so
  "14 overdue tasks" and "Weather API key pending from faculty" could not be
  answered from the database.
* **Deliverables.** `BatchDocument` records a file that was uploaded and
  verified, which is not the same as an artefact that is 78% written. A team
  needs to see the gap before it becomes a missing submission.
* **Integrations.** Repository, build, deployment and review status are shown
  per project. These are recorded, not detected - there is no git or CI
  connection behind them, and a screen that implied otherwise would be lying.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class TaskPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class DeliverableStatus(str, enum.Enum):
    PENDING = "pending"
    AVAILABLE = "available"
    VERIFIED = "verified"


class IntegrationKind(str, enum.Enum):
    REPOSITORY = "repository"
    BUILD = "build"
    DEPLOYMENT = "deployment"
    REVIEW = "review"


class IntegrationState(str, enum.Enum):
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"
    PASSED = "passed"
    FAILED = "failed"
    LIVE = "live"
    SCHEDULED = "scheduled"


class ProjectTask(Base):
    """One piece of work on a batch, owned by one student."""
    __tablename__ = "project_tasks"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    title = Column(String(300), nullable=False)
    detail = Column(Text, nullable=True)

    # Nullable: work is often written down before anyone has picked it up.
    assignee_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"),
                         nullable=True, index=True)

    # The backlog item this work breaks down, when it breaks one down. Most
    # tasks belong to a stage rather than a story, so this stays nullable and
    # the tracker keeps working for batches with no backlog at all.
    story_id = Column(GUID, ForeignKey("project_user_stories.id", ondelete="SET NULL"),
                      nullable=True, index=True)

    priority = Column(SQLEnum(TaskPriority), nullable=False,
                      default=TaskPriority.MEDIUM, index=True)
    status = Column(SQLEnum(TaskStatus), nullable=False,
                    default=TaskStatus.OPEN, index=True)

    due_date = Column(Date, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Why the work cannot proceed. Held separately from `detail` so the
    # blockers panel can show the reason without the whole task description -
    # "Weather API key pending from faculty" is the useful sentence.
    blocked_reason = Column(String(300), nullable=True)

    # Which of the eight stages this work belongs to. The board card shows it
    # as a tag, and it is what lets a blocker be described as holding up a
    # milestone rather than just a task.
    stage = Column(SQLEnum("TOPIC_APPROVAL", "BASE_PAPER", "REQUIREMENTS",
                           "SYSTEM_DESIGN", "DEVELOPMENT", "TESTING",
                           "DOCUMENTATION", "FINAL_REVIEW",
                           name="projectstage", create_type=False),
                   nullable=True, index=True)

    # How far along, for work that is neither untouched nor finished.
    progress = Column(Integer, default=0, nullable=False)

    created_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch")
    assignee = relationship("User", foreign_keys=[assignee_id])
    story = relationship("ProjectUserStory", foreign_keys=[story_id])

    @property
    def is_blocked(self) -> bool:
        return self.status == TaskStatus.BLOCKED

    def __repr__(self) -> str:
        return f"<ProjectTask {self.title[:30]} {self.status}>"


class ProjectDeliverable(Base):
    """
    An artefact the batch owes, and how far along it is.

    Distinct from `BatchDocument`, which is a file that has been handed in.
    A deliverable exists from the start of the project at 0% and is what makes
    "60% of the presentation is written" visible before the deadline.
    """
    __tablename__ = "project_deliverables"
    __table_args__ = (
        UniqueConstraint("batch_id", "name", name="uq_deliverable_per_batch"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    name = Column(String(120), nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    status = Column(SQLEnum(DeliverableStatus), nullable=False,
                    default=DeliverableStatus.PENDING, index=True)

    # Where the evidence lives: a link for a demo or repository, or the
    # uploaded file when one exists.
    evidence_url = Column(String(500), nullable=True)
    file_id = Column(GUID, ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True)

    position = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch")

    def __repr__(self) -> str:
        return f"<ProjectDeliverable {self.name} {self.progress}%>"


class BatchIntegration(Base):
    """
    Repository, build, deployment and review state for one batch.

    Recorded by hand, not detected. Nothing here talks to git or to a CI
    system, and the screen says "recorded" rather than implying a live check -
    a green tick that nobody updated is worse than no tick at all.
    """
    __tablename__ = "batch_integrations"
    __table_args__ = (
        UniqueConstraint("batch_id", "kind", name="uq_integration_per_batch"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    kind = Column(SQLEnum(IntegrationKind), nullable=False, index=True)
    state = Column(SQLEnum(IntegrationState), nullable=False,
                   default=IntegrationState.NOT_CONNECTED)

    # "Last commit 2h ago", "Staging Live", "Review 3 on 23 Aug".
    detail = Column(String(200), nullable=True)
    url = Column(String(500), nullable=True)

    # What the repository signs its push webhooks with. Only the repository
    # integration uses it. It does reach the browser, for the one person
    # entitled to set the webhook up - they cannot paste what they cannot see.
    secret = Column(String(80), nullable=True)

    # Either the trainer or the batch leader can connect a repository - on a
    # student project the lead usually owns it - so the screen says which of
    # them did, rather than each wondering whether the other has.
    connected_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"),
                          nullable=True)
    connected_at = Column(DateTime, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    connected_by_user = relationship("User", foreign_keys=[connected_by])

    batch = relationship("ProjectBatch")

    def __repr__(self) -> str:
        return f"<BatchIntegration {self.kind} {self.state}>"


class BlockerCategory(str, enum.Enum):
    """
    Why work stopped. Fixed set, because the point of the category is to
    count it - free text would make the analysis panel meaningless.
    """
    TECHNICAL = "technical"        # API keys, environments, integration
    DATA = "data"                  # datasets, licences, access
    APPROVAL = "approval"          # waiting on a review or a sign-off
    TEAM = "team"                  # ownership, an absent member
    DOCUMENTATION = "documentation"


class BlockerSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BlockerStatus(str, enum.Enum):
    OPEN = "open"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class ProjectBlocker(Base):
    """
    Something stopping work, tracked through to resolution.

    A blocker was previously one sentence on a task. That is enough to show a
    red chip and nothing else: it cannot be assigned to whoever can clear it,
    it cannot be escalated, and nobody can be asked why resolution took eleven
    days. This carries the whole lifecycle - who reported it, what actually
    caused it, what it holds up, who owns clearing it, and when it cleared.
    """
    __tablename__ = "project_blockers"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    # The task it stops, when it stops one. A blocker can also sit against the
    # project as a whole - an unissued hardware kit blocks everything.
    task_id = Column(GUID, ForeignKey("project_tasks.id", ondelete="SET NULL"),
                     nullable=True, index=True)

    title = Column(String(300), nullable=False)
    category = Column(SQLEnum(BlockerCategory), nullable=False,
                      default=BlockerCategory.TECHNICAL, index=True)
    severity = Column(SQLEnum(BlockerSeverity), nullable=False,
                      default=BlockerSeverity.MEDIUM, index=True)
    status = Column(SQLEnum(BlockerStatus), nullable=False,
                    default=BlockerStatus.OPEN, index=True)

    # What is really wrong, as opposed to the symptom in the title.
    root_cause = Column(Text, nullable=True)
    # What it holds up, in the reporter's words.
    impact = Column(Text, nullable=True)

    reported_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reported_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Whoever has to clear it - usually staff, since most blockers are
    # somebody outside the team not having done something yet.
    resolution_owner_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"),
                                 nullable=True, index=True)
    target_resolution = Column(Date, nullable=True)

    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch")
    task = relationship("ProjectTask", foreign_keys=[task_id])
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    resolution_owner = relationship("User", foreign_keys=[resolution_owner_id])

    def __repr__(self) -> str:
        return f"<ProjectBlocker {self.title[:30]} {self.status}>"


class TaskComment(Base):
    """A note on a task. The count is what the board card shows."""
    __tablename__ = "task_comments"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    task_id = Column(GUID, ForeignKey("project_tasks.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    author_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("ProjectTask", foreign_keys=[task_id])
    author = relationship("User", foreign_keys=[author_id])


class TaskAttachment(Base):
    """A file on a task, pointing at the content-addressed store."""
    __tablename__ = "task_attachments"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    task_id = Column(GUID, ForeignKey("project_tasks.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    file_id = Column(GUID, ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("ProjectTask", foreign_keys=[task_id])


class TaskDependency(Base):
    """
    One task waiting on another.

    Directional and de-duplicated: the pair is unique, and a task depending on
    itself is rejected in the service rather than modelled away here.
    """
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_id", name="uq_task_dependency"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    task_id = Column(GUID, ForeignKey("project_tasks.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    depends_on_id = Column(GUID, ForeignKey("project_tasks.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
