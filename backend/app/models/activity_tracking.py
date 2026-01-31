"""
Activity Tracking Models
Track student activities for engagement monitoring
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON, Enum as SQLEnum
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class ActivityType(str, enum.Enum):
    """Types of trackable activities"""
    LOGIN = "login"
    LOGOUT = "logout"
    LAB_VIEW = "lab_view"
    TOPIC_VIEW = "topic_view"
    CONCEPT_READ = "concept_read"
    MCQ_START = "mcq_start"
    MCQ_SUBMIT = "mcq_submit"
    PROBLEM_VIEW = "problem_view"
    PROBLEM_START = "problem_start"
    PROBLEM_SUBMIT = "problem_submit"
    CODE_EDIT = "code_edit"
    REPORT_VIEW = "report_view"
    REPORT_SUBMIT = "report_submit"
    PROJECT_VIEW = "project_view"
    PROJECT_UPDATE = "project_update"


class ResourceType(str, enum.Enum):
    """Types of resources being accessed"""
    LAB = "lab"
    TOPIC = "topic"
    MCQ = "mcq"
    PROBLEM = "problem"
    REPORT = "report"
    PROJECT = "project"
    SUBMISSION = "submission"


class StudentActivity(Base):
    """Student activity tracking"""
    __tablename__ = "student_activities"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    student_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Activity details
    activity_type = Column(SQLEnum(ActivityType), nullable=False, index=True)

    # Resource being accessed
    resource_id = Column(GUID, nullable=True, index=True)
    resource_type = Column(SQLEnum(ResourceType), nullable=True)

    # Duration (for time-tracked activities)
    duration_seconds = Column(Integer, nullable=True)

    # Additional metadata (named activity_data to avoid SQLAlchemy reserved name conflict)
    activity_data = Column(JSON, nullable=True)  # {"ip": "...", "user_agent": "...", "score": 85}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<StudentActivity {self.student_id} {self.activity_type}>"


class EngagementAlert(Base):
    """Low engagement alerts for faculty"""
    __tablename__ = "engagement_alerts"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    student_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Alert details
    alert_type = Column(String(50), nullable=False)  # low_activity, no_submissions, declining_scores
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high
    message = Column(Text, nullable=False)

    # Related context
    lab_id = Column(GUID, nullable=True)
    class_id = Column(GUID, nullable=True)

    # Status
    is_read = Column(String(10), default="false")
    is_resolved = Column(String(10), default="false")
    resolved_by = Column(GUID, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EngagementAlert {self.student_id} {self.alert_type}>"


class ActivitySummary(Base):
    """Pre-computed daily activity summaries for faster queries"""
    __tablename__ = "activity_summaries"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    student_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_date = Column(DateTime, nullable=False, index=True)  # Date of the summary

    # Activity counts
    login_count = Column(Integer, default=0)
    lab_views = Column(Integer, default=0)
    topics_viewed = Column(Integer, default=0)
    mcq_attempts = Column(Integer, default=0)
    problems_attempted = Column(Integer, default=0)
    submissions_count = Column(Integer, default=0)

    # Time metrics (in seconds)
    total_time_seconds = Column(Integer, default=0)
    avg_session_seconds = Column(Integer, default=0)

    # Performance metrics
    mcq_correct_rate = Column(Integer, default=0)  # Percentage
    problem_pass_rate = Column(Integer, default=0)  # Percentage

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ActivitySummary {self.student_id} {self.summary_date}>"
