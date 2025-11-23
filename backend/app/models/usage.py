from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class UsageLog(Base):
    """Usage log model for tracking API usage"""
    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)

    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Usage metrics
    tokens_used = Column(Integer, default=0)
    cost = Column(Integer, default=0)  # in paise/cents

    # Response details
    status_code = Column(Integer, nullable=True)
    response_time = Column(Integer, nullable=True)  # in milliseconds

    # Model used
    model_used = Column(String(100), nullable=True)

    # Additional metadata
    extra_metadata = Column(JSON, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="usage_logs")
    api_key = relationship("APIKey", back_populates="usage_logs")

    def __repr__(self):
        return f"<UsageLog {self.endpoint}>"


class TokenUsage(Base):
    """Daily token usage aggregation"""
    __tablename__ = "token_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    date = Column(DateTime, nullable=False, index=True)

    # Aggregated metrics
    total_tokens = Column(Integer, default=0)
    total_requests = Column(Integer, default=0)
    total_cost = Column(Integer, default=0)  # in paise/cents

    # Model breakdown
    haiku_tokens = Column(Integer, default=0)
    sonnet_tokens = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TokenUsage {self.date}>"
