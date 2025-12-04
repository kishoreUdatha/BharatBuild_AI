from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class UsageLog(Base):
    """Usage log model for tracking API usage"""
    __tablename__ = "usage_logs"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    api_key_id = Column(GUID, ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)

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

    id = Column(GUID, primary_key=True, default=generate_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

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
