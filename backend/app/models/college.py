from sqlalchemy import JSON, Column, String, DateTime, Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
import uuid

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class College(Base):
    """College model"""
    __tablename__ = "colleges"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")

    # Contact
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # The tenant that individually signed-up students belong to.
    # Without one, a self-serve student lands in whichever paying
    # college's pool the portal happens to query, and shows up in
    # that college's rosters and exports.
    is_self_serve = Column(Boolean, default=False, nullable=False)

    # The mail domains this college owns, lowercase and without the "@"
    # ("sgit.ac.in", "students.sgit.ac.in"). Signing up from one of these
    # places the account in this college - which is the only claim a student
    # can make that they cannot simply type. Empty means the college onboards
    # by roster or batch code instead.
    email_domains = Column(JSON, default=list, nullable=False)

    # What a batch here charges unless it says otherwise. Held on the college
    # so a standard fee is entered once rather than on all 45 batches, each an
    # opportunity to mistype a number students then pay.
    #
    # The fallback for a project type this college has not priced.
    # Where this college's project repositories are created.
    #
    # An organisation per college rather than one shared namespace: a college
    # keeps its own students' work, its member list stays its own, and handing
    # the org over if they leave the platform is then a single transfer rather
    # than an extraction.
    github_org = Column(String(120), nullable=True)
    # The id of this college's installation of the BharatBuild GitHub App.
    # Nothing is created until the college installs it, so this is what says
    # whether repository creation is available here at all.
    github_installation_id = Column(String(40), nullable=True)

    default_project_fee = Column(Integer, default=15000, nullable=False)

    # The kinds of project this college runs, in the order it thinks of them
    # ("Major Project", "Minor Project"). A college offering only these two
    # should not be shown Capstone when creating batches.
    project_types = Column(JSON, default=list, nullable=False)

    # Fee per project type: {"Major Project": 15000, "Minor Project": 8000}.
    # A minor project rarely costs what a major one does, and a single number
    # would quietly overcharge one of them.
    project_fees = Column(JSON, default=dict, nullable=False)

    def fee_for(self, project_type: Optional[str]) -> int:
        """What a batch of this type costs here."""
        if project_type:
            priced = (self.project_fees or {}).get(project_type)
            if priced is not None:
                return int(priced)
        return int(self.default_project_fee or 0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    faculties = relationship("Faculty", back_populates="college", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="college", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<College {self.name}>"


class Faculty(Base):
    """Faculty model"""
    __tablename__ = "faculties"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Faculty details
    employee_id = Column(String(50), unique=True, nullable=True)
    department = Column(String(255), nullable=True)
    designation = Column(String(255), nullable=True)
    specialization = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    college = relationship("College", back_populates="faculties")
    batches = relationship("Batch", secondary="faculty_batches", back_populates="faculties")

    def __repr__(self):
        return f"<Faculty {self.employee_id}>"


class Batch(Base):
    """Batch model"""
    __tablename__ = "batches"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=True)
    department = Column(String(255), nullable=True)

    # Dates
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    college = relationship("College", back_populates="batches")
    students = relationship("Student", back_populates="batch", cascade="all, delete-orphan")
    faculties = relationship("Faculty", secondary="faculty_batches", back_populates="batches")

    def __repr__(self):
        return f"<Batch {self.name}>"


class Student(Base):
    """Student model"""
    __tablename__ = "students"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Student details
    roll_number = Column(String(50), unique=True, nullable=False)
    enrollment_number = Column(String(50), unique=True, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    batch = relationship("Batch", back_populates="students")

    def __repr__(self):
        return f"<Student {self.roll_number}>"


# Association table for faculty-batch many-to-many relationship
from sqlalchemy import Table

faculty_batches = Table(
    'faculty_batches',
    Base.metadata,
    Column('faculty_id', GUID, ForeignKey('faculties.id', ondelete="CASCADE"), primary_key=True),
    Column('batch_id', GUID, ForeignKey('batches.id', ondelete="CASCADE"), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False)
)
