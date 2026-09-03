"""
Academic structure - schools, departments, sections and who owns them.

Until now "department" and "section" were free-text columns on
`StudentEnrollment` and `ProjectBatch`. That is enough to group students, but
the Departments & Sections screen needs things a string cannot carry: a
section's capacity, its room and timetable, who coordinates it, which subjects
it runs and whether its allocation is published or still a draft.

These tables hold that metadata. They deliberately do NOT own the student
roster - a section's membership is still derived from `StudentEnrollment`, so
there is exactly one place a student's placement is recorded and the two can
never disagree.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
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


class SectionStatus(str, enum.Enum):
    """Whether a section's allocation has been published to students."""
    PUBLISHED = "published"
    DRAFT = "draft"
    ARCHIVED = "archived"


class SubjectKind(str, enum.Enum):
    CORE = "core"
    LAB = "lab"
    ELECTIVE = "elective"


class NoticeSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class UpdateRequestStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DECLINED = "declined"


class AcademicDepartment(Base):
    """
    A department within a school, for one academic year.

    Scoped per year because the HOD and coordinators change between years and
    the screen has to show who held the role in the year being viewed.
    """
    __tablename__ = "academic_departments"
    __table_args__ = (
        # Per college, not globally. Without the college in the key, the first
        # institution to create a "CSE" owned that code for the whole platform
        # and no second college could ever have one - which is every college.
        UniqueConstraint("code", "academic_year", "college_id",
                         name="uq_department_code_year_college"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    school = Column(String(120), nullable=False, index=True)   # "School of Engineering"
    code = Column(String(20), nullable=False, index=True)      # "CSE"
    name = Column(String(160), nullable=False)                 # "Computer Science & Engineering"
    # Which institution this department belongs to. The structure tree and
    # its CSV export are built from here, so this is what keeps one
    # college's departments, sections and capacities out of another's.
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False, index=True)
    academic_year = Column(String(20), nullable=False, index=True)

    hod_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    dept_coordinator_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project_coordinator_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hod = relationship("User", foreign_keys=[hod_id])
    dept_coordinator = relationship("User", foreign_keys=[dept_coordinator_id])
    project_coordinator = relationship("User", foreign_keys=[project_coordinator_id])
    sections = relationship("AcademicSection", back_populates="department",
                            cascade="all, delete-orphan")
    notices = relationship("DepartmentNotice", back_populates="department",
                           cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AcademicDepartment {self.code} {self.academic_year}>"


class AcademicSection(Base):
    """
    One section (A / B / C) of a department for a given year and semester.

    `capacity` is what the section is allowed to hold; the assigned count is
    read from enrollments, so an over- or under-filled section shows up as a
    difference rather than needing a second number kept in sync by hand.
    """
    __tablename__ = "academic_sections"
    __table_args__ = (
        UniqueConstraint("department_id", "year", "semester", "name",
                         name="uq_section_dept_year_sem_name"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    department_id = Column(GUID, ForeignKey("academic_departments.id", ondelete="CASCADE"),
                           nullable=False, index=True)

    year = Column(String(20), nullable=False, index=True)       # "4th Year"
    semester = Column(String(10), nullable=False, index=True)   # "I" / "II"
    name = Column(String(10), nullable=False, index=True)       # "A"

    capacity = Column(Integer, default=64, nullable=False)
    room = Column(String(40), nullable=True)                    # "CSE-401"
    schedule_days = Column(String(60), nullable=True)           # "Mon-Fri"
    schedule_time = Column(String(60), nullable=True)           # "09:00 AM-04:00 PM"

    coordinator_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status = Column(SQLEnum(SectionStatus), default=SectionStatus.DRAFT,
                    nullable=False, index=True)
    timetable_published = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("AcademicDepartment", back_populates="sections")
    coordinator = relationship("User", foreign_keys=[coordinator_id])
    faculty = relationship("SectionFacultyAssignment", back_populates="section",
                           cascade="all, delete-orphan")
    subjects = relationship("SectionSubject", back_populates="section",
                            cascade="all, delete-orphan")
    update_requests = relationship("SectionUpdateRequest", back_populates="section",
                                   cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AcademicSection {self.name} {self.year} sem {self.semester}>"


class SectionFacultyAssignment(Base):
    """A faculty member's role on one section."""
    __tablename__ = "section_faculty_assignments"
    __table_args__ = (
        UniqueConstraint("section_id", "faculty_id", "role", name="uq_section_faculty_role"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    section_id = Column(GUID, ForeignKey("academic_sections.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    faculty_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    # "Class Coordinator", "Project Guide", "Review Panel", "HOD"
    role = Column(String(60), nullable=False, index=True)
    responsibility = Column(String(160), nullable=True)
    display_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    section = relationship("AcademicSection", back_populates="faculty")
    faculty_member = relationship("User", foreign_keys=[faculty_id])

    def __repr__(self):
        return f"<SectionFacultyAssignment {self.section_id} {self.role}>"


class SectionSubject(Base):
    """A subject taught to one section."""
    __tablename__ = "section_subjects"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    section_id = Column(GUID, ForeignKey("academic_sections.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    code = Column(String(30), nullable=True)          # "CS401"
    title = Column(String(160), nullable=False)
    kind = Column(SQLEnum(SubjectKind), default=SubjectKind.CORE, nullable=False, index=True)
    credits = Column(Integer, nullable=True)
    faculty_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    display_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    section = relationship("AcademicSection", back_populates="subjects")
    faculty_member = relationship("User", foreign_keys=[faculty_id])

    def __repr__(self):
        return f"<SectionSubject {self.code} {self.title}>"


class DepartmentNotice(Base):
    """A dated notice shown on the department's notice strip."""
    __tablename__ = "department_notices"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    department_id = Column(GUID, ForeignKey("academic_departments.id", ondelete="CASCADE"),
                           nullable=False, index=True)

    title = Column(String(200), nullable=False)
    detail = Column(Text, nullable=True)
    # Free text because a notice window reads "22-26 Aug" or "due 20 Aug"
    # depending on the kind, and formatting it here keeps the API honest.
    window_label = Column(String(80), nullable=True)
    due_at = Column(DateTime, nullable=True, index=True)
    severity = Column(SQLEnum(NoticeSeverity), default=NoticeSeverity.INFO, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    department = relationship("AcademicDepartment", back_populates="notices")

    def __repr__(self):
        return f"<DepartmentNotice {self.title}>"


class SectionUpdateRequest(Base):
    """
    A faculty request to change section structure.

    Faculty cannot edit the structure directly - the HOD and coordinator own
    it - so "Request Section Update" records the ask here for them to action.
    """
    __tablename__ = "section_update_requests"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    section_id = Column(GUID, ForeignKey("academic_sections.id", ondelete="CASCADE"),
                        nullable=True, index=True)
    department_id = Column(GUID, ForeignKey("academic_departments.id", ondelete="CASCADE"),
                           nullable=False, index=True)

    requested_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # "Capacity", "Room", "Timetable", "Coordinator", "Allocation", "Other"
    kind = Column(String(60), nullable=False)
    note = Column(Text, nullable=False)

    status = Column(SQLEnum(UpdateRequestStatus), default=UpdateRequestStatus.OPEN,
                    nullable=False, index=True)
    resolution_note = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    section = relationship("AcademicSection", back_populates="update_requests")
    requested_by = relationship("User", foreign_keys=[requested_by_id])

    def __repr__(self):
        return f"<SectionUpdateRequest {self.kind} {self.status}>"
