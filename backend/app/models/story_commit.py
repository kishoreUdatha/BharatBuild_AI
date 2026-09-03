"""
Commits pushed to a batch's repository.

Recorded from a push webhook, not typed in: the point is that the trail is
evidence, and evidence a student can edit is not evidence.

A commit reaches a story through its message - "US-101 parse the header row" -
which is the convention every issue tracker uses because it needs nothing from
the student beyond how they already write commits. Commits with no key are
still stored, unlinked: knowing the team pushed sixty commits and tied four of
them to stories is a more useful read than pretending the other fifty-six did
not happen.
"""

from datetime import datetime

from sqlalchemy import (
    Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class StoryCommit(Base):
    __tablename__ = "story_commits"
    __table_args__ = (
        # The same push can be delivered twice - webhooks retry, and a force
        # push replays history. The sha is the commit's identity, so the batch
        # plus the sha is what makes a redelivery a no-op.
        UniqueConstraint("batch_id", "sha", name="uq_commit_per_batch"),
        Index("ix_story_commits_story_time", "story_id", "committed_at"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    # Null when the message named no story: the commit still belongs to the
    # batch, and can be attached later.
    story_id = Column(GUID, ForeignKey("project_user_stories.id", ondelete="SET NULL"),
                      nullable=True, index=True)

    sha = Column(String(64), nullable=False, index=True)
    message = Column(Text, nullable=False)
    url = Column(String(500), nullable=True)
    branch = Column(String(200), nullable=True)

    # The author as git reports them. Kept as text rather than a user link:
    # the name on a commit is whatever the student configured locally, and
    # guessing which account that is would put the wrong name on the trail.
    author_name = Column(String(160), nullable=True)
    author_email = Column(String(200), nullable=True)
    # Set when the email matches a batch member, so the screen can show who it
    # was when it can be sure.
    author_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    provider = Column(String(30), nullable=True)      # github | gitlab | other
    committed_at = Column(DateTime, nullable=True, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("ProjectBatch")
    story = relationship("ProjectUserStory")
    author = relationship("User", foreign_keys=[author_id])

    def __repr__(self) -> str:
        return f"<StoryCommit {self.sha[:7]} story={self.story_id}>"
