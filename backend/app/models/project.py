from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

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

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.title}>"
