from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid

from app.core.database import Base


class Session(Base):
    """User session model for workspace persistence"""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    # Session data
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    workspace_state = Column(JSON, nullable=True)  # Stores file tree, open files, cursor positions
    editor_state = Column(JSON, nullable=True)  # Monaco editor state
    chat_history = Column(JSON, nullable=True)  # Conversation history
    active_file = Column(String(500), nullable=True)  # Currently open file

    # Session metadata
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Device/browser info
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")
    project = relationship("Project")

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at

    def extend(self, days: int = 7):
        """Extend session expiration"""
        self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.last_activity = datetime.utcnow()

    def __repr__(self):
        return f"<Session {self.id} user={self.user_id}>"
