from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class ProjectMode(str, enum.Enum):
    """Project modes"""
    STUDENT = "student"
    DEVELOPER = "developer"
    FOUNDER = "founder"
    COLLEGE = "college"


class ProjectStatus(str, enum.Enum):
    """Project status"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    # Database indexes for performance
    __table_args__ = (
        Index('ix_projects_user_id', 'user_id'),  # Most queries filter by user
        Index('ix_projects_workspace_id', 'workspace_id'),  # Workspace queries
        Index('ix_projects_status', 'status'),     # Status filters are common
        Index('ix_projects_created_at', 'created_at'),  # Ordering by date
        Index('ix_projects_user_status', 'user_id', 'status'),  # Compound for user + status queries
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(GUID, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    mode = Column(SQLEnum(ProjectMode), nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False)

    # Project configuration
    config = Column(JSON, nullable=True)  # Stores mode-specific configuration

    # Student mode specific
    domain = Column(String(255), nullable=True)
    tech_stack = Column(JSON, nullable=True)
    requirements = Column(Text, nullable=True)

    # Developer mode specific
    framework = Column(String(100), nullable=True)
    deployment_target = Column(String(100), nullable=True)

    # Founder mode specific
    industry = Column(String(255), nullable=True)
    target_market = Column(String(255), nullable=True)

    # Processing
    celery_task_id = Column(String(255), nullable=True)
    progress = Column(Integer, default=0)  # 0-100
    current_agent = Column(String(100), nullable=True)

    # Metadata
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Integer, default=0)  # in paise/cents

    # Ephemeral/Saved status
    is_saved = Column(Boolean, default=False)  # True = permanent, False = ephemeral (auto-delete)
    last_activity = Column(DateTime, default=datetime.utcnow)  # For cleanup tracking

    # ==================== LAYER 3: Storage Metadata ====================
    # These fields enable project reconstruction from S3 (Layer 2)

    # S3 path where project files live (Layer 2)
    s3_path = Column(String(500), nullable=True)  # e.g., "projects/<user-id>/<project-id>/"
    s3_zip_key = Column(String(500), nullable=True)  # Key for project.zip in S3

    # Plan JSON - stores the generation plan for reconstruction
    plan_json = Column(JSON, nullable=True)  # The AI-generated project plan

    # File index - list of all generated files with metadata
    file_index = Column(JSON, nullable=True)  # [{path, name, language, s3_key, size_bytes}, ...]

    # History - Claude/GPT conversation messages for reconstruction
    history = Column(JSON, nullable=True)  # [{role: "user"|"assistant", content: str}, ...]

    # Technology stack detected/used
    technology = Column(String(255), nullable=True)  # e.g., "Python, FastAPI, React"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="projects")
    workspace = relationship("Workspace", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", back_populates="project", cascade="all, delete-orphan")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")

    # Enterprise relationships
    messages = relationship("ProjectMessage", back_populates="project", cascade="all, delete-orphan")
    sandbox_instances = relationship("SandboxInstance", back_populates="project", cascade="all, delete-orphan")
    snapshots = relationship("Snapshot", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.title}>"
