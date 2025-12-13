"""
Workspace Model - Organizes projects under user workspaces
Structure: workspaces/{user_id}/{project_id}/
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class Workspace(Base):
    """
    Workspace model - Each user has a default workspace
    All projects belong to a workspace

    Storage structure:
    - Local: /workspaces/{user_id}/{project_id}/
    - S3: s3://bucket/workspaces/{user_id}/{project_id}/
    """
    __tablename__ = "workspaces"

    # Database indexes
    __table_args__ = (
        Index('ix_workspaces_user_id', 'user_id'),
        Index('ix_workspaces_is_default', 'is_default'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    # Note: index defined explicitly in __table_args__ as 'ix_workspaces_user_id', no need for index=True here
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Workspace info
    name = Column(String(255), nullable=False, default="My Workspace")
    description = Column(Text, nullable=True)

    # Default workspace flag - each user has one default workspace
    is_default = Column(Boolean, default=True)

    # Storage paths
    # Local path: /workspaces/{user_id}/  (projects are subdirs)
    storage_path = Column(String(500), nullable=True)
    # S3 prefix: workspaces/{user_id}/
    s3_prefix = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="workspaces")
    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace {self.name} (user={self.user_id})>"

    @property
    def project_count(self):
        """Get number of projects in this workspace"""
        return len(self.projects) if self.projects else 0
