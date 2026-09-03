"""
One-time codes for verifying an email address or a mobile number.

Deliberately not tied to a user: verification happens on the registration
form, before the account exists. The row is keyed by the destination itself,
and registration later asks "was this address proven in the last N minutes?".

The code is never stored in the clear. Only a salted hash is kept, so a
database read cannot be replayed as a login.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class VerificationChannel(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"


class VerificationPurpose(str, enum.Enum):
    SIGNUP = "signup"
    PROFILE_UPDATE = "profile_update"


class VerificationCode(Base):
    """
    A single issued code, and everything needed to rate-limit it.

    `attempts` guards against guessing a 6-digit code; `send_count` guards
    against using the endpoint to spam somebody else's inbox or phone.
    """
    __tablename__ = "verification_codes"
    __table_args__ = (
        # The hot lookup is "latest live code for this destination".
        Index("ix_verification_lookup", "channel", "destination", "consumed_at"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    channel = Column(SQLEnum(VerificationChannel), nullable=False, index=True)
    # Normalised: email lower-cased, phone digits only.
    destination = Column(String(180), nullable=False, index=True)
    purpose = Column(SQLEnum(VerificationPurpose), default=VerificationPurpose.SIGNUP,
                     nullable=False)

    code_hash = Column(String(128), nullable=False)
    salt = Column(String(32), nullable=False)

    attempts = Column(Integer, default=0, nullable=False)
    send_count = Column(Integer, default=1, nullable=False)

    expires_at = Column(DateTime, nullable=False, index=True)
    last_sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    # Set when a registration actually uses the proof, so one verification
    # cannot be replayed to create several accounts.
    consumed_at = Column(DateTime, nullable=True)

    # Present only when re-verifying an existing account's contact details.
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Kept for abuse investigation, not shown to anyone.
    request_ip = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    def __repr__(self):
        return f"<VerificationCode {self.channel.value}:{self.destination} verified={bool(self.verified_at)}>"
