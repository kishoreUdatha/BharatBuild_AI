from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class AgentType(str, enum.Enum):
    """Agent types for token tracking"""
    PLANNER = "planner"
    WRITER = "writer"
    FIXER = "fixer"
    VERIFIER = "verifier"
    RUNNER = "runner"
    DOCUMENT = "document"
    ENHANCER = "enhancer"
    CHAT = "chat"
    OTHER = "other"


class OperationType(str, enum.Enum):
    """Operation types for detailed tracking"""
    # Planning
    PLAN_PROJECT = "plan_project"
    PLAN_STRUCTURE = "plan_structure"

    # Code generation
    GENERATE_FILE = "generate_file"
    GENERATE_BATCH = "generate_batch"
    REGENERATE_FILE = "regenerate_file"

    # Fixing
    FIX_ERROR = "fix_error"
    FIX_IMPORTS = "fix_imports"
    AUTO_FIX = "auto_fix"

    # Verification
    VERIFY_CODE = "verify_code"
    VERIFY_IMPORTS = "verify_imports"

    # Documents
    GENERATE_SRS = "generate_srs"
    GENERATE_REPORT = "generate_report"
    GENERATE_PPT = "generate_ppt"
    GENERATE_VIVA = "generate_viva"
    GENERATE_UML = "generate_uml"

    # Chat
    CHAT_MESSAGE = "chat_message"
    CHAT_ENHANCE = "chat_enhance"

    # Other
    OTHER = "other"


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


class TokenUsageLog(Base):
    """
    Detailed token usage log for granular API call tracking.

    Tracks every Claude API call with:
    - User and project context
    - Agent and operation type
    - Model used
    - Input/output token breakdown
    - Cost in paise

    Use this for:
    - Per-project token usage reports
    - Agent-level cost analysis
    - Billing and invoicing
    - Optimization insights

    Note: This is separate from TokenTransaction in token_balance.py
    which tracks balance changes (purchases, refunds, etc.)
    """
    __tablename__ = "token_usage_logs"

    # Indexes for common queries
    __table_args__ = (
        Index('ix_token_usage_log_user_id', 'user_id'),
        Index('ix_token_usage_log_project_id', 'project_id'),
        Index('ix_token_usage_log_created_at', 'created_at'),
        Index('ix_token_usage_log_user_project', 'user_id', 'project_id'),
        Index('ix_token_usage_log_user_date', 'user_id', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # User and project context
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # Agent and operation tracking
    agent_type = Column(SQLEnum(AgentType), nullable=False, default=AgentType.OTHER)
    operation = Column(SQLEnum(OperationType), nullable=False, default=OperationType.OTHER)

    # Model used
    model = Column(String(50), nullable=False, default="haiku")  # haiku, sonnet, opus

    # Token breakdown
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    # Cost calculation (in paise for INR precision)
    cost_paise = Column(Integer, nullable=False, default=0)

    # Additional context
    file_path = Column(String(500), nullable=True)  # For file generation operations
    error_message = Column(Text, nullable=True)  # For error fixing operations
    extra_data = Column(JSON, nullable=True)  # Extra info (prompt length, response quality, etc.)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="token_usage_logs")
    project = relationship("Project", backref="token_usage_logs")

    def __repr__(self):
        return f"<TokenUsageLog {self.agent_type.value}:{self.operation.value} {self.total_tokens} tokens>"

    @classmethod
    def calculate_cost_paise(cls, input_tokens: int, output_tokens: int, model: str) -> int:
        """
        Calculate cost in paise based on model pricing.

        Pricing (per 1M tokens):
        - Haiku:  Input $0.25, Output $1.25  (approx ₹21, ₹104)
        - Sonnet: Input $3.00, Output $15.00 (approx ₹250, ₹1250)
        - Opus:   Input $15.00, Output $75.00 (approx ₹1250, ₹6250)

        Returns cost in paise (1/100 of rupee)
        """
        # Pricing in paise per 1000 tokens (for easier calculation)
        pricing = {
            "haiku": {"input": 0.021, "output": 0.104},      # ₹0.021/1K input, ₹0.104/1K output
            "sonnet": {"input": 0.25, "output": 1.25},       # ₹0.25/1K input, ₹1.25/1K output
            "opus": {"input": 1.25, "output": 6.25},         # ₹1.25/1K input, ₹6.25/1K output
            "claude-3-haiku-20240307": {"input": 0.021, "output": 0.104},
            "claude-3-5-sonnet-20241022": {"input": 0.25, "output": 1.25},
            "claude-sonnet-4-20250514": {"input": 0.25, "output": 1.25},
        }

        # Get pricing for model (default to haiku if unknown)
        model_lower = model.lower()
        model_pricing = pricing.get(model_lower, pricing["haiku"])

        # Calculate cost
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]

        # Convert to paise (multiply by 100)
        total_paise = int((input_cost + output_cost) * 100)

        return total_paise
