from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class UserRole(str, enum.Enum):
    """User roles"""
    STUDENT = "student"
    DEVELOPER = "developer"
    FOUNDER = "founder"
    FACULTY = "faculty"
    ADMIN = "admin"
    API_PARTNER = "api_partner"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)

    role = Column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    # OAuth fields
    google_id = Column(String(255), unique=True, nullable=True)
    github_id = Column(String(255), unique=True, nullable=True)
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'github', or None for email/password
    avatar_url = Column(Text, nullable=True)

    # Profile fields
    phone = Column(String(20), nullable=True)
    organization = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)

    # College fields (for students and faculty)
    college_id = Column(GUID, nullable=True)
    batch_id = Column(GUID, nullable=True)

    # Password reset fields
    reset_token_hash = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
