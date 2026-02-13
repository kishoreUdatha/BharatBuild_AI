"""
Build schemas for APK/IPA build requests and responses
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class BuildPlatform(str, Enum):
    """Build platform types"""
    ANDROID = "android"
    IOS = "ios"


class BuildStatus(str, Enum):
    """Build status types"""
    PENDING = "pending"
    CONFIGURING = "configuring"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==================== Request Schemas ====================

class BuildConfigBase(BaseModel):
    """Base build configuration"""
    app_name: Optional[str] = Field(None, min_length=1, max_length=100, description="App display name")
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$", description="Semantic version (e.g., 1.0.0)")
    build_number: int = Field(1, ge=1, description="Build number for store submission")
    bundle_id: Optional[str] = Field(None, description="Bundle identifier (e.g., com.company.app)")


class BuildAPKRequest(BuildConfigBase):
    """Request to build Android APK"""
    pass


class BuildIPARequest(BuildConfigBase):
    """Request to build iOS IPA"""
    pass


class CancelBuildRequest(BaseModel):
    """Request to cancel a build"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for cancellation")


# ==================== Response Schemas ====================

class BuildResponse(BaseModel):
    """Build status response"""
    id: str
    project_id: str
    user_id: str
    platform: BuildPlatform
    status: BuildStatus
    progress: int = Field(default=0, ge=0, le=100)
    eas_build_id: Optional[str] = None
    artifact_url: Optional[str] = None
    error_message: Optional[str] = None
    build_config: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuildStatusResponse(BaseModel):
    """Simplified build status for polling"""
    id: str
    platform: BuildPlatform
    status: BuildStatus
    progress: int
    phase: Optional[str] = None  # Human-readable phase description
    error_message: Optional[str] = None
    artifact_url: Optional[str] = None
    artifact_filename: Optional[str] = None
    artifact_size_mb: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class BuildDownloadResponse(BaseModel):
    """Response with download URL"""
    download_url: str
    filename: str
    size_bytes: Optional[int] = None
    expires_at: Optional[datetime] = None


class BuildHistoryResponse(BaseModel):
    """List of builds for a project"""
    builds: List[BuildResponse]
    total: int


class BuildTriggerResponse(BaseModel):
    """Response after triggering a build"""
    build_id: str
    message: str
    status: BuildStatus = BuildStatus.PENDING


class BuildQuotaResponse(BaseModel):
    """User's build quota status"""
    builds_this_month: int
    builds_limit: int
    builds_remaining: int
    can_build: bool
    plan_type: str


# ==================== WebSocket Event Schemas ====================

class BuildProgressEvent(BaseModel):
    """WebSocket event for build progress updates"""
    build_id: str
    project_id: str
    platform: BuildPlatform
    status: BuildStatus
    progress: int
    phase: Optional[str] = None
    message: Optional[str] = None
    artifact_url: Optional[str] = None
    error: Optional[str] = None


# ==================== Internal Schemas ====================

class EASBuildConfig(BaseModel):
    """Configuration for EAS build submission"""
    project_path: str
    platform: BuildPlatform
    profile: str = "production"
    app_name: str
    version: str
    build_number: int
    bundle_id: str
    icon_path: Optional[str] = None
    splash_path: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None


class EASBuildStatus(BaseModel):
    """Status response from EAS build:view command"""
    id: str
    status: str  # new, in-queue, in-progress, finished, errored, cancelled
    platform: str
    artifacts: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
