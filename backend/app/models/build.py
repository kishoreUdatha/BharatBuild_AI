"""
Build model for tracking APK/IPA builds via Expo EAS Build
"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class BuildPlatform(str, enum.Enum):
    """Build platform types"""
    ANDROID = "android"
    IOS = "ios"


class BuildStatus(str, enum.Enum):
    """
    Build status flow:
    PENDING -> CONFIGURING -> QUEUED -> IN_PROGRESS -> COMPLETED/FAILED/CANCELLED
    """
    PENDING = "pending"           # Build request received
    CONFIGURING = "configuring"   # Generating app.json, eas.json
    QUEUED = "queued"            # Submitted to EAS, waiting in queue
    IN_PROGRESS = "in_progress"  # EAS is building
    COMPLETED = "completed"      # Build successful, artifact available
    FAILED = "failed"            # Build failed
    CANCELLED = "cancelled"      # User cancelled the build


class Build(Base):
    """Build model for tracking APK/IPA builds"""
    __tablename__ = "builds"

    # Database indexes for performance
    __table_args__ = (
        Index('ix_builds_project_id', 'project_id'),
        Index('ix_builds_user_id', 'user_id'),
        Index('ix_builds_status', 'status'),
        Index('ix_builds_platform', 'platform'),
        Index('ix_builds_created_at', 'created_at'),
        Index('ix_builds_user_platform', 'user_id', 'platform'),  # For quota checks
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Build configuration
    platform = Column(SQLEnum(BuildPlatform), nullable=False)
    status = Column(SQLEnum(BuildStatus), default=BuildStatus.PENDING, nullable=False)

    # EAS Build tracking
    eas_build_id = Column(String(255), nullable=True)  # EAS build UUID
    progress = Column(Integer, default=0)  # 0-100 progress percentage

    # Artifact storage
    artifact_url = Column(String(500), nullable=True)  # EAS download URL (temporary)
    s3_key = Column(String(500), nullable=True)        # Our S3 copy for persistence

    # Error handling
    error_message = Column(Text, nullable=True)

    # Build configuration (app name, version, etc.)
    build_config = Column(JSON, nullable=True)
    # Example: {
    #   "app_name": "MyApp",
    #   "version": "1.0.0",
    #   "build_number": 1,
    #   "bundle_id": "com.bharatbuild.myapp",
    #   "icon": "s3://...",
    #   "splash": "s3://..."
    # }

    # Celery task tracking
    celery_task_id = Column(String(255), nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)    # When EAS started building
    completed_at = Column(DateTime, nullable=True)  # When build finished
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="builds")
    user = relationship("User", backref="builds")

    def __repr__(self):
        return f"<Build {self.id} - {self.platform.value} - {self.status.value}>"

    @property
    def artifact_filename(self) -> str:
        """Generate artifact filename based on config"""
        config = self.build_config or {}
        app_name = config.get("app_name", "app").replace(" ", "_")
        version = config.get("version", "1.0.0")
        ext = "apk" if self.platform == BuildPlatform.ANDROID else "ipa"
        return f"{app_name}-{version}.{ext}"

    @property
    def is_active(self) -> bool:
        """Check if build is currently active (not finished)"""
        return self.status in [
            BuildStatus.PENDING,
            BuildStatus.CONFIGURING,
            BuildStatus.QUEUED,
            BuildStatus.IN_PROGRESS
        ]

    @property
    def is_downloadable(self) -> bool:
        """Check if build artifact is available for download"""
        return self.status == BuildStatus.COMPLETED and (self.artifact_url or self.s3_key)
