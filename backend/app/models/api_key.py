from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class APIKeyStatus(str, enum.Enum):
    """API Key status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class APIKey(Base):
    """API Key model"""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    key = Column(String(255), unique=True, index=True, nullable=False)
    secret_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)

    status = Column(SQLEnum(APIKeyStatus), default=APIKeyStatus.ACTIVE, nullable=False)

    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)

    # Token limits
    token_limit = Column(Integer, nullable=True)  # Total token limit (null = unlimited)
    tokens_used = Column(Integer, default=0)

    # Permissions
    allowed_modes = Column(JSON, default=list)  # List of allowed project modes
    allowed_ips = Column(JSON, default=list)  # IP whitelist (empty = all allowed)

    # Metadata
    last_used_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("UsageLog", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey {self.name}>"
