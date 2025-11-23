from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class AgentTaskStatus(str, enum.Enum):
    """Agent task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, enum.Enum):
    """Agent types"""
    IDEA = "idea"
    SRS = "srs"
    UML = "uml"
    CODE = "code"
    REPORT = "report"
    PPT = "ppt"
    VIVA = "viva"
    REVIEW = "review"
    BUSINESS = "business"
    PRD = "prd"


class AgentTask(Base):
    """Agent task model for tracking individual agent executions"""
    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    agent_type = Column(SQLEnum(AgentType), nullable=False)
    status = Column(SQLEnum(AgentTaskStatus), default=AgentTaskStatus.PENDING, nullable=False)

    # Input/Output
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)

    # Execution details
    celery_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    # Metrics
    tokens_used = Column(Integer, default=0)
    cost = Column(Integer, default=0)  # in paise/cents
    execution_time = Column(Integer, nullable=True)  # in seconds

    # Model used
    model_used = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="agent_tasks")

    def __repr__(self):
        return f"<AgentTask {self.agent_type}>"
