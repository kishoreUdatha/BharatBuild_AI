from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class AuditLog(Base):
    """Audit log for tracking admin actions"""
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    admin_id = Column(GUID, ForeignKey("users.id"), nullable=False, index=True)

    # Action details
    action = Column(String(100), nullable=False)  # e.g., 'user_updated', 'user_suspended', 'plan_created'
    target_type = Column(String(50), nullable=False)  # e.g., 'user', 'project', 'plan', 'setting'
    target_id = Column(GUID, nullable=True)  # ID of the affected entity

    # Change details
    details = Column(JSONB, nullable=True)  # Changed fields, old/new values, etc.

    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    admin = relationship("User", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.admin_id}>"
