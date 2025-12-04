"""
File Version Model - Git-like file versioning
Used for: Undo/redo, file history, diff viewing
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class ProjectFileVersion(Base):
    """
    Stores historical versions of project files.

    Use cases:
    - Undo/Redo functionality
    - "View History" for any file
    - Restore previous version
    - Diff view between versions
    - Track who/what made changes

    Version tracking:
    - version 1: Initial creation
    - version 2+: Each save creates new version
    """
    __tablename__ = "project_file_versions"

    __table_args__ = (
        Index('ix_file_versions_file_id', 'file_id'),
        Index('ix_file_versions_project_id', 'project_id'),
        Index('ix_file_versions_version', 'version'),
        Index('ix_file_versions_created_at', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    file_id = Column(GUID, ForeignKey("project_files.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Version info
    version = Column(Integer, nullable=False)

    # Content storage
    content = Column(Text, nullable=True)  # Inline for small files
    s3_url = Column(String(500), nullable=True)  # S3 for large files
    content_hash = Column(String(64), nullable=True)  # SHA-256
    size_bytes = Column(Integer, default=0)

    # Diff from previous version (optional, saves space)
    diff_patch = Column(Text, nullable=True)  # Unified diff format

    # Change tracking
    created_by = Column(String(50), nullable=True)  # "user", "writer", "fixer"
    change_type = Column(String(50), nullable=True)  # "create", "edit", "fix", "refactor"
    change_summary = Column(String(500), nullable=True)  # "Fixed TypeScript error on line 42"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    file = relationship("ProjectFile", back_populates="versions")

    def __repr__(self):
        return f"<ProjectFileVersion v{self.version} ({self.change_type})>"

    @property
    def is_inline(self):
        """Check if content is stored inline"""
        return self.content is not None and self.s3_url is None
