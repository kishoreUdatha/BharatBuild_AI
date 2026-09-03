"""
AI planning - epics and user stories drafted for a project batch.

The trainer reviews every AI-drafted story before any of it reaches the
product backlog. That review state lives here, on the story itself, so the
screen never has to infer whether something was actually looked at.

Nothing in this module lets the AI decide anything. A story becomes approved
only when a trainer sets it, and `reviewed_by_id` records who.

Once approved the same row carries the story through delivery - its sprint,
its assignee and its workflow status. That is one row rather than two because
a backlog item is the story, not a copy of it; see `app.models.backlog` for
the sprints, comments and events it gains on the way.
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
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid
# Delivery state is defined next to the sprints and events it belongs with;
# the columns live here because they belong to this row.
from app.models.backlog import StoryType, StoryWorkflowStatus


class StoryReviewStatus(str, enum.Enum):
    """Where a drafted story sits in the trainer's review."""
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class StoryPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CriterionKind(str, enum.Enum):
    ACCEPTANCE = "acceptance"
    DEFINITION_OF_DONE = "definition_of_done"


class AiPlanningRun(Base):
    """One generation pass over a batch's project details."""
    __tablename__ = "ai_planning_runs"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    model_label = Column(String(80), nullable=True)      # which model drafted it
    source_summary = Column(Text, nullable=True)          # what it read
    # Mean confidence across the stories this run produced. Stored rather than
    # recomputed so a later edit to one story does not rewrite history.
    quality_percent = Column(Integer, nullable=True)
    story_count = Column(Integer, default=0)
    epic_count = Column(Integer, default=0)

    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    generated_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_current = Column(Boolean, default=True, index=True)

    batch = relationship("ProjectBatch")
    generated_by = relationship("User", foreign_keys=[generated_by_id])

    def __repr__(self):
        return f"<AiPlanningRun {self.batch_id} {self.generated_at:%Y-%m-%d}>"


class ProjectEpic(Base):
    """A grouping of user stories, e.g. EP-01 Data Preparation."""
    __tablename__ = "project_epics"
    __table_args__ = (
        UniqueConstraint("batch_id", "key", name="uq_epic_batch_key"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    key = Column(String(20), nullable=False, index=True)   # "EP-01"
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("ProjectBatch")
    stories = relationship("ProjectUserStory", back_populates="epic")

    def __repr__(self):
        return f"<ProjectEpic {self.key} {self.title}>"


class ProjectUserStory(Base):
    """One AI-drafted story awaiting, or carrying, a trainer decision."""
    __tablename__ = "project_user_stories"
    __table_args__ = (
        UniqueConstraint("batch_id", "key", name="uq_story_batch_key"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    epic_id = Column(GUID, ForeignKey("project_epics.id", ondelete="SET NULL"),
                     nullable=True, index=True)
    run_id = Column(GUID, ForeignKey("ai_planning_runs.id", ondelete="SET NULL"), nullable=True)

    key = Column(String(20), nullable=False, index=True)    # "US-101"
    title = Column(String(240), nullable=False)
    narrative = Column(Text, nullable=True)                 # "As a ... I want ... so that ..."
    dependencies = Column(String(300), nullable=True)
    # Comma-separated tags, as the import template supplies them. A string
    # rather than a table: nothing joins on a label, and the screens that show
    # them only ever split on the comma.
    labels = Column(String(300), nullable=True)

    story_points = Column(Integer, default=0)
    priority = Column(SQLEnum(StoryPriority), default=StoryPriority.MEDIUM,
                      nullable=False, index=True)
    # The model's own confidence in this draft. Advisory only - it never gates
    # anything, because the trainer's decision is what counts.
    ai_confidence = Column(Float, nullable=True)

    review_status = Column(SQLEnum(StoryReviewStatus), default=StoryReviewStatus.NEEDS_REVIEW,
                           nullable=False, index=True)
    trainer_comment = Column(Text, nullable=True)
    reviewed_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    # Set when the approved set is moved across; until then the backlog is empty
    # and students cannot see any of this.
    moved_to_backlog_at = Column(DateTime, nullable=True)

    # ------------------------------------------------------------- delivery
    #
    # Everything below is set after approval, by a trainer, on the User
    # Stories screen. It is all nullable or defaulted because a story that
    # has just cleared review has none of it yet.

    story_type = Column(SQLEnum(StoryType), default=StoryType.STORY,
                        nullable=False, index=True)
    workflow_status = Column(SQLEnum(StoryWorkflowStatus),
                             default=StoryWorkflowStatus.TO_DO, nullable=False, index=True)
    assignee_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"),
                         nullable=True, index=True)
    sprint_id = Column(GUID, ForeignKey("project_sprints.id", ondelete="SET NULL"),
                       nullable=True, index=True)
    # Who put the story on the board. Null for the AI-drafted set, which is
    # what `run_id` records instead - the distinction is worth keeping, since
    # "Created By" on the screen must not credit a trainer with the model's work.
    created_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    # When the work is wanted by. Whether it is late is worked out from this
    # against today, every time it is asked for - never stored, because a
    # stored flag is wrong from the next morning onwards.
    due_date = Column(Date, nullable=True, index=True)

    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch")
    epic = relationship("ProjectEpic", back_populates="stories")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    criteria = relationship("StoryCriterion", back_populates="story",
                            cascade="all, delete-orphan")
    revisions = relationship("StoryRevisionRequest", back_populates="story",
                             cascade="all, delete-orphan")
    assignee = relationship("User", foreign_keys=[assignee_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    sprint = relationship("ProjectSprint", back_populates="stories")
    comments = relationship("StoryComment", back_populates="story",
                            cascade="all, delete-orphan")
    attachments = relationship("StoryAttachment", back_populates="story",
                               cascade="all, delete-orphan")
    events = relationship("StoryEvent", back_populates="story",
                          cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProjectUserStory {self.key} {self.review_status.value}>"


class StoryCriterion(Base):
    """An acceptance criterion or a definition-of-done item on one story."""
    __tablename__ = "story_criteria"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    story_id = Column(GUID, ForeignKey("project_user_stories.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    kind = Column(SQLEnum(CriterionKind), nullable=False, index=True)
    text = Column(Text, nullable=False)
    # Whether the trainer considers this item adequately specified. The
    # "5 / 6" figure on the list is a count of these, not a separate number.
    met = Column(Boolean, default=True, nullable=False)
    position = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    story = relationship("ProjectUserStory", back_populates="criteria")

    def __repr__(self):
        return f"<StoryCriterion {self.kind.value} met={self.met}>"


class StoryRevisionRequest(Base):
    """A trainer asking the model to redraft a story, and why."""
    __tablename__ = "story_revision_requests"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    story_id = Column(GUID, ForeignKey("project_user_stories.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    note = Column(Text, nullable=False)
    requested_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    story = relationship("ProjectUserStory", back_populates="revisions")
    requested_by = relationship("User", foreign_keys=[requested_by_id])

    def __repr__(self):
        return f"<StoryRevisionRequest {self.story_id}>"
