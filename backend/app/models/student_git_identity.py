"""
The git identity a student commits under, inside a shared batch repository.

One batch, one repository - but the commits in it come from several people, and
git only records whatever name and email each of them configured locally. That
is almost never the college address the portal knows them by, so a push carries
no reliable link back to a student on its own.

This is that link, and each student makes it themselves: they say which git
account and which commit emails are theirs, and every commit arriving under one
of those emails is credited to them. An email belongs to one student per batch,
so two teammates cannot both claim the same one and split the credit for a
piece of work between them.

Verification is optional and proves control rather than granting it: the
student puts a short code in any commit message and pushes, and seeing that
code arrive from the claimed email is proof the account is really theirs.
"""

from datetime import datetime

from sqlalchemy import (
    JSON, Column, DateTime, ForeignKey, Index, String, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class StudentGitIdentity(Base):
    __tablename__ = "student_git_identities"
    __table_args__ = (
        # One claim per student per batch. A student on two projects has two
        # rows, which is right: the repositories are different.
        UniqueConstraint("batch_id", "student_id", name="uq_git_identity_per_student"),
        Index("ix_git_identity_batch", "batch_id"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False)
    student_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    provider = Column(String(30), nullable=True)        # github | gitlab | other
    # Their handle on the host. Shown to the trainer so a roster of who has
    # connected reads as names rather than addresses.
    username = Column(String(120), nullable=True)
    # Every address they commit from - a laptop's git config and GitHub's
    # noreply address are commonly both in play for one person.
    emails = Column(JSON, default=list, nullable=False)

    # Cleared the moment a commit carrying it arrives.
    verify_code = Column(String(16), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_commit_at = Column(DateTime, nullable=True)

    batch = relationship("ProjectBatch")
    student = relationship("User")

    @property
    def verified(self) -> bool:
        return self.verified_at is not None

    def __repr__(self) -> str:
        return f"<StudentGitIdentity {self.username or '?'} student={self.student_id}>"
