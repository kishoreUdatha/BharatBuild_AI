"""
The product backlog - what happens to a story after the trainer approves it.

AI planning ends at approval: a story is drafted, reviewed and moved across,
and at that moment it is still unassigned, unscheduled and unstarted. This
module is the rest of that story's life - which sprint it sits in, who is
doing it, and what was said about it on the way.

Delivery state is deliberately not the same column as `StoryReviewStatus`.
The review status answers "did a trainer accept this draft"; the workflow
status answers "is the work done". Collapsing them would make it impossible
for a story to be both approved and unstarted, which is the state every
backlog item begins in.

Events are append-only. The Activity tab claims to show what happened to a
story, so it is written from the same code paths that change one rather than
inferred afterwards - a feed that guessed would be worse than no feed.
"""

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


class SprintState(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"


class StoryWorkflowStatus(str, enum.Enum):
    """
    How far the work has got, which is not the same as who approved it.

    TESTING sits between the writing and the guide's review: work that is
    built but not yet trusted. BLOCKED is not a stage on the way to done -
    it is where a story waits for something outside the team, and it can be
    entered from any of the others.
    """
    TO_DO = "to_do"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class StoryType(str, enum.Enum):
    STORY = "story"
    TASK = "task"
    BUG = "bug"
    SPIKE = "spike"


class StoryEventKind(str, enum.Enum):
    CREATED = "created"
    IMPORTED = "imported"
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status_changed"
    SPRINT_CHANGED = "sprint_changed"
    PRIORITY_CHANGED = "priority_changed"
    POINTS_CHANGED = "points_changed"
    EDITED = "edited"
    COMMENTED = "commented"
    ATTACHED = "attached"
    DETACHED = "detached"


class ProjectSprint(Base):
    """A time box on one batch, e.g. Sprint 3 (20 May - 02 Jun)."""
    __tablename__ = "project_sprints"
    __table_args__ = (
        UniqueConstraint("batch_id", "key", name="uq_sprint_batch_key"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    key = Column(String(20), nullable=False, index=True)     # "SP-03"
    name = Column(String(80), nullable=False)                # "Sprint 3"
    goal = Column(String(300), nullable=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    state = Column(SQLEnum(SprintState), nullable=False,
                   default=SprintState.PLANNED, index=True)
    position = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("ProjectBatch")
    stories = relationship("ProjectUserStory", back_populates="sprint")

    def __repr__(self):
        return f"<ProjectSprint {self.key} {self.name}>"


class StoryComment(Base):
    """A note on one story, from whoever wrote it."""
    __tablename__ = "story_comments"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    story_id = Column(GUID, ForeignKey("project_user_stories.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    author_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Kept alongside the id so a comment still reads correctly after the
    # account behind it is removed at the end of an academic year.
    author_name = Column(String(120), nullable=True)
    body = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    story = relationship("ProjectUserStory", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])

    def __repr__(self):
        return f"<StoryComment {self.story_id}>"


class StoryAttachment(Base):
    """
    A file hung on a story - the design PDF an acceptance criterion refers to,
    a screenshot of the bug, the sample output.

    The bytes live in `stored_files`, addressed by their own SHA-256, so this
    row is only the association: which story, what it was called, who put it
    there. Deleting the attachment leaves the blob alone; another story, or
    another team, may be pointing at the same content.
    """
    __tablename__ = "story_attachments"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    story_id = Column(GUID, ForeignKey("project_user_stories.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    file_id = Column(GUID, ForeignKey("stored_files.id"), nullable=False)

    # What to call it on screen and in the download. Never used to build a path.
    name = Column(String(255), nullable=False)

    uploaded_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    story = relationship("ProjectUserStory", back_populates="attachments")
    file = relationship("StoredFile")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f"<StoryAttachment {self.name}>"


class StoryEvent(Base):
    """One thing that happened to a story. Written, never edited."""
    __tablename__ = "story_events"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    story_id = Column(GUID, ForeignKey("project_user_stories.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    actor_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_name = Column(String(120), nullable=True)

    kind = Column(SQLEnum(StoryEventKind), nullable=False, index=True)
    summary = Column(String(300), nullable=False)
    # Before and after, for the changes where seeing both is the point
    # ("To Do -> In Progress"). Null for events that are not a transition.
    from_value = Column(String(120), nullable=True)
    to_value = Column(String(120), nullable=True)

    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    story = relationship("ProjectUserStory", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_id])

    def __repr__(self):
        return f"<StoryEvent {self.kind.value} {self.story_id}>"
