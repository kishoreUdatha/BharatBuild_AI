from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class College(Base):
    """College model"""
    __tablename__ = "colleges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

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
    Column('faculty_id', UUID(as_uuid=True), ForeignKey('faculties.id', ondelete="CASCADE"), primary_key=True),
    Column('batch_id', UUID(as_uuid=True), ForeignKey('batches.id', ondelete="CASCADE"), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False)
)
