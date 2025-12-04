from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class DocumentType(str, enum.Enum):
    """Document types"""
    SRS = "srs"  # Software Requirements Specification
    UML = "uml"  # UML Diagrams
    CODE = "code"  # Source Code
    REPORT = "report"  # Project Report
    PPT = "ppt"  # Presentation
    VIVA_QA = "viva_qa"  # Viva Q&A
    PRD = "prd"  # Product Requirements Document
    BUSINESS_PLAN = "business_plan"
    OTHER = "other"


class Document(Base):
    """Document model"""
    __tablename__ = "documents"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(500), nullable=False)
    doc_type = Column(SQLEnum(DocumentType), nullable=False)

    # File details
    file_name = Column(String(500), nullable=True)
    file_path = Column(Text, nullable=True)
    file_url = Column(Text, nullable=True)  # S3/MinIO URL
    file_size = Column(Integer, nullable=True)  # in bytes
    mime_type = Column(String(100), nullable=True)

    # Content (for text-based documents)
    content = Column(Text, nullable=True)

    # Metadata
    agent_generated = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    extra_metadata = Column(Text, nullable=True)  # JSON string

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.title}>"
