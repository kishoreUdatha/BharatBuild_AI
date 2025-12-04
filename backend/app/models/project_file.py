from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class ProjectFile(Base):
    """
    Project File model - stores file metadata in PostgreSQL
    Actual file content is stored in S3/MinIO for scalability
    """
    __tablename__ = "project_files"

    # Database indexes for performance
    __table_args__ = (
        Index('ix_project_files_project_id', 'project_id'),  # Most queries filter by project
        Index('ix_project_files_path', 'path'),  # File lookups by path
        Index('ix_project_files_project_path', 'project_id', 'path', unique=True),  # Unique path per project
        Index('ix_project_files_content_hash', 'content_hash'),  # For deduplication lookups
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # File info
    path = Column(String(1000), nullable=False)  # e.g., "src/components/App.tsx"
    name = Column(String(255), nullable=False)   # e.g., "App.tsx"
    language = Column(String(50), nullable=True)  # e.g., "typescript"

    # Storage
    s3_key = Column(String(1000), nullable=True)  # S3 object key for content
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication
    size_bytes = Column(Integer, default=0)

    # For small files, store content directly (optimization)
    # Files < 10KB stored here, larger files in S3
    content_inline = Column(Text, nullable=True)
    is_inline = Column(Boolean, default=True)

    # Metadata
    is_folder = Column(Boolean, default=False)
    parent_path = Column(String(1000), nullable=True)  # Parent folder path

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="files")
    versions = relationship("ProjectFileVersion", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProjectFile {self.path}>"

    @property
    def is_small_file(self):
        """Files under 10KB can be stored inline"""
        return self.size_bytes < 10240
