from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Boolean, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class FileGenerationStatus(str, enum.Enum):
    """Status of file generation - enables resume after disconnect"""
    PLANNED = "planned"       # In plan, not yet generated
    GENERATING = "generating" # Currently being generated
    COMPLETED = "completed"   # Successfully generated
    FAILED = "failed"         # Generation failed
    SKIPPED = "skipped"       # Skipped (exists or not needed)


class ProjectFile(Base):
    """
    Project File model - stores file metadata in PostgreSQL
    Actual file content is stored in S3/MinIO for scalability

    Generation Tracking:
    - Planner creates plan → files saved with status=PLANNED
    - File being generated → status=GENERATING
    - File complete → status=COMPLETED (with content)
    - Internet drops → backend continues, user reconnects to see progress
    """
    __tablename__ = "project_files"

    # Database indexes for performance
    __table_args__ = (
        Index('ix_project_files_project_id', 'project_id'),  # Most queries filter by project
        Index('ix_project_files_path', 'path'),  # File lookups by path
        Index('ix_project_files_project_path', 'project_id', 'path', unique=True),  # Unique path per project
        Index('ix_project_files_content_hash', 'content_hash'),  # For deduplication lookups
        Index('ix_project_files_status', 'generation_status'),  # For resume queries
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    # Note: index defined explicitly in __table_args__ as 'ix_project_files_project_id', no need for index=True here
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # File info
    path = Column(String(1000), nullable=False)  # e.g., "src/components/App.tsx"
    name = Column(String(255), nullable=False)   # e.g., "App.tsx"
    language = Column(String(50), nullable=True)  # e.g., "typescript"

    # Storage
    s3_key = Column(String(1000), nullable=True)  # S3 object key for content
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication
    size_bytes = Column(Integer, default=0)

    # Legacy: For small files, content was stored directly (deprecated)
    # New approach: ALL content stored in S3, only metadata in database
    # content_inline kept for backward compatibility with existing data
    content_inline = Column(Text, nullable=True)
    is_inline = Column(Boolean, default=False)  # Default to False (S3)

    # Metadata
    is_folder = Column(Boolean, default=False)
    parent_path = Column(String(1000), nullable=True)  # Parent folder path

    # Generation tracking - for resume after disconnect
    generation_status = Column(
        SQLEnum(FileGenerationStatus),
        default=FileGenerationStatus.COMPLETED,  # Default for backward compatibility
        nullable=False
    )
    generation_order = Column(Integer, nullable=True)  # Order in generation plan (1, 2, 3...)

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
