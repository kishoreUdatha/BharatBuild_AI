"""
Project Messages Model - Stores chat history between user and AI agents
Used for: Chat history panel, conversation replay, context for agents
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class MessageRole(str, enum.Enum):
    """Message sender role"""
    USER = "user"
    SYSTEM = "system"
    PLANNER = "planner"
    WRITER = "writer"
    FIXER = "fixer"
    RUNNER = "runner"
    REVIEWER = "reviewer"
    ASSISTANT = "assistant"


class ProjectMessage(Base):
    """
    Stores all messages in a project conversation.

    Use cases:
    - Display chat history in UI
    - Provide context to agents
    - Conversation replay
    - Token usage tracking per message
    """
    __tablename__ = "project_messages"

    __table_args__ = (
        Index('ix_project_messages_project_id', 'project_id'),
        Index('ix_project_messages_created_at', 'created_at'),
        Index('ix_project_messages_role', 'role'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Message content - use String to match migration (not SQLEnum to avoid enum type creation)
    role = Column(String(50), nullable=False)
    agent_type = Column(String(50), nullable=True)  # planner/writer/fixer/runner
    content = Column(Text, nullable=False)

    # Token tracking
    tokens_used = Column(Integer, default=0)
    model_used = Column(String(100), nullable=True)  # claude-3.5-sonnet, gpt-4, etc.

    # Extra data
    extra_data = Column(Text, nullable=True)  # JSON string for extra data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="messages")

    def __repr__(self):
        return f"<ProjectMessage {self.role}: {self.content[:50]}...>"
