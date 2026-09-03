"""
Where a platform trainer is allowed to work.

Trainers are BharatBuild's own staff, not a college's. They carry no
`college_id`, so the ordinary tenant rule - "your college" - gives them
nothing, which is the right default: an unassigned trainer sees an empty
system rather than everyone's.

Their reach comes entirely from rows in this table. One per college they work
at: a trainer takes several branches and several sections there, and listing
those one by one is data entry that goes stale every term - a section is added
and the trainer silently cannot see it.

A branch or section may still be named to narrow an assignment, for the
occasional trainer brought in for one course. Null means the whole college,
which is the normal case.
"""

from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, String,
                        UniqueConstraint)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class TrainerAssignment(Base):
    """One trainer, one section, for one academic year."""
    __tablename__ = "trainer_assignments"
    __table_args__ = (
        # The same section twice would double every count built by joining
        # through this table.
        UniqueConstraint("trainer_id", "college_id", "department", "section",
                         "academic_year", name="uq_trainer_assignment"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    trainer_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    # Which college's section. Held explicitly rather than derived, because it
    # is the value every tenancy check compares against.
    college_id = Column(GUID, ForeignKey("colleges.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    # Optional narrowing. Null - the usual case - means every branch and
    # section at that college. When set, these match how batches record them
    # (`ProjectBatch.department` / `.section`) so the two join without a
    # lookup table in between.
    department = Column(String(100), nullable=True, index=True)
    section = Column(String(10), nullable=True, index=True)
    academic_year = Column(String(20), nullable=False, index=True)

    # Revoked rather than deleted: attendance and verifications a trainer
    # recorded stay explainable after they stop teaching a section.
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    assigned_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"),
                            nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    trainer = relationship("User", foreign_keys=[trainer_id])
    college = relationship("College", foreign_keys=[college_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])

    def __repr__(self):
        where = "whole college"
        if self.department:
            where = f"{self.department}-{self.section}" if self.section else self.department
        return f"<TrainerAssignment {self.trainer_id} {where} {self.academic_year}>"
