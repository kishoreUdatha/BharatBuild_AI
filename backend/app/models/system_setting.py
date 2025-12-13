from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class SystemSetting(Base):
    """System settings for admin configuration"""
    __tablename__ = "system_settings"

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Setting key (unique identifier)
    key = Column(String(100), unique=True, nullable=False, index=True)

    # Setting value (stored as JSON for flexibility)
    value = Column(JSONB, nullable=False)

    # Metadata
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # 'general', 'features', 'limits', 'notifications'

    # Audit trail
    updated_by = Column(GUID, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SystemSetting {self.key}>"
