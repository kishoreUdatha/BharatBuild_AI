"""
Builds API - APK/IPA build endpoints using Expo EAS Build

Endpoints:
- POST /builds/{project_id}/apk - Trigger Android APK build
- POST /builds/{project_id}/ipa - Trigger iOS IPA build
- GET /builds/{project_id}/status - Get current build status
- GET /builds/{project_id}/download - Get download URL for completed build
- DELETE /builds/{project_id}/cancel - Cancel active build
- GET /builds/{project_id}/history - Get build history for project
- GET /builds/quota - Get user's build quota status
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import logger
from app.models.user import User
from app.models.project import Project
from app.models.build import Build, BuildStatus, BuildPlatform
from app.modules.auth.dependencies import get_current_user
from app.modules.builds.tasks import build_mobile_app, cancel_mobile_build
from app.services.eas_build_service import eas_build_service
from app.schemas.build import (
    BuildAPKRequest,
    BuildIPARequest,
    BuildResponse,
    BuildStatusResponse,
    BuildDownloadResponse,
    BuildHistoryResponse,
    BuildTriggerResponse,
    BuildQuotaResponse,
    CancelBuildRequest,
)

router = APIRouter(prefix="/builds", tags=["Mobile Builds"])


# ==================== Helper Functions ====================

async def get_project_for_user(
    project_id: str,
    user: User,
    db: AsyncSession
) -> Project:
    """Get project and verify ownership"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


async def check_build_quota(user: User, db: AsyncSession) -> BuildQuotaResponse:
    """Check if user can create more builds this month"""
    # Get builds this month
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(Build.id)).where(
            Build.user_id == user.id,
            Build.created_at >= start_of_month
        )
    )
    builds_this_month = result.scalar() or 0

    # Determine limit based on plan
    # TODO: Integrate with actual subscription system
    is_premium = getattr(user, 'is_premium', False) or user.role.value in ['admin', 'premium']
    builds_limit = settings.PREMIUM_BUILDS_PER_MONTH if is_premium else settings.FREE_TIER_BUILDS_PER_MONTH

    return BuildQuotaResponse(
        builds_this_month=builds_this_month,
        builds_limit=builds_limit,
        builds_remaining=max(0, builds_limit - builds_this_month),
        can_build=builds_this_month < builds_limit,
        plan_type="premium" if is_premium else "free"
    )


async def get_active_build(
    project_id: str,
    user_id: str,
    db: AsyncSession
) -> Optional[Build]:
    """Get any active build for the project"""
    result = await db.execute(
        select(Build).where(
            Build.project_id == project_id,
            Build.user_id == user_id,
            Build.status.in_([
                BuildStatus.PENDING,
                BuildStatus.CONFIGURING,
                BuildStatus.QUEUED,
                BuildStatus.IN_PROGRESS
            ])
        )
    )
    return result.scalar_one_or_none()


# ==================== Endpoints ====================

@router.get("/quota", response_model=BuildQuotaResponse)
async def get_build_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's build quota status"""
    return await check_build_quota(current_user, db)


@router.post("/{project_id}/apk", response_model=BuildTriggerResponse)
async def trigger_apk_build(
    project_id: str,
    request: BuildAPKRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger Android APK build for a project.

    The project must be a React Native or Expo project.
    Build progress can be monitored via the /status endpoint or WebSocket.
    """
    # Verify project ownership
    project = await get_project_for_user(project_id, current_user, db)

    # Check quota
    quota = await check_build_quota(current_user, db)
    if not quota.can_build:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "build_limit_reached",
                "message": f"Build limit reached ({quota.builds_limit}/month). Upgrade to premium for more builds.",
                "builds_this_month": quota.builds_this_month,
                "builds_limit": quota.builds_limit
            }
        )

    # Check for existing active build
    active_build = await get_active_build(project_id, str(current_user.id), db)
    if active_build:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "build_in_progress",
                "message": "A build is already in progress for this project",
                "build_id": str(active_build.id),
                "status": active_build.status.value
            }
        )

    # Create build record
    build = Build(
        project_id=project_id,
        user_id=str(current_user.id),
        platform=BuildPlatform.ANDROID,
        status=BuildStatus.PENDING,
        build_config={
            "app_name": request.app_name or project.title,
            "version": request.version,
            "build_number": request.build_number,
            "bundle_id": request.bundle_id
        }
    )
    db.add(build)
    await db.commit()
    await db.refresh(build)

    # Trigger Celery task
    task = build_mobile_app.delay(
        str(build.id),
        project_id,
        "android",
        build.build_config
    )

    # Update with task ID
    build.celery_task_id = task.id
    await db.commit()

    logger.info(f"Triggered APK build {build.id} for project {project_id}")

    return BuildTriggerResponse(
        build_id=str(build.id),
        message="APK build started. Use /builds/{project_id}/status to check progress.",
        status=BuildStatus.PENDING
    )


@router.post("/{project_id}/ipa", response_model=BuildTriggerResponse)
async def trigger_ipa_build(
    project_id: str,
    request: BuildIPARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger iOS IPA build for a project.

    Requires Apple Developer credentials to be configured.
    The project must be a React Native or Expo project.
    """
    # Check if Apple credentials are configured
    if not settings.APPLE_TEAM_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ios_not_configured",
                "message": "iOS builds require Apple Developer account. Please contact support."
            }
        )

    # Verify project ownership
    project = await get_project_for_user(project_id, current_user, db)

    # Check quota
    quota = await check_build_quota(current_user, db)
    if not quota.can_build:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "build_limit_reached",
                "message": f"Build limit reached ({quota.builds_limit}/month). Upgrade to premium for more builds.",
                "builds_this_month": quota.builds_this_month,
                "builds_limit": quota.builds_limit
            }
        )

    # Check for existing active build
    active_build = await get_active_build(project_id, str(current_user.id), db)
    if active_build:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "build_in_progress",
                "message": "A build is already in progress for this project",
                "build_id": str(active_build.id),
                "status": active_build.status.value
            }
        )

    # Create build record
    build = Build(
        project_id=project_id,
        user_id=str(current_user.id),
        platform=BuildPlatform.IOS,
        status=BuildStatus.PENDING,
        build_config={
            "app_name": request.app_name or project.title,
            "version": request.version,
            "build_number": request.build_number,
            "bundle_id": request.bundle_id
        }
    )
    db.add(build)
    await db.commit()
    await db.refresh(build)

    # Trigger Celery task
    task = build_mobile_app.delay(
        str(build.id),
        project_id,
        "ios",
        build.build_config
    )

    # Update with task ID
    build.celery_task_id = task.id
    await db.commit()

    logger.info(f"Triggered IPA build {build.id} for project {project_id}")

    return BuildTriggerResponse(
        build_id=str(build.id),
        message="IPA build started. Use /builds/{project_id}/status to check progress.",
        status=BuildStatus.PENDING
    )


@router.get("/{project_id}/status", response_model=BuildStatusResponse)
async def get_build_status(
    project_id: str,
    build_id: Optional[str] = Query(None, description="Specific build ID to check"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the status of the current or specified build.

    If no build_id is provided, returns the most recent build for the project.
    """
    # Verify project ownership
    await get_project_for_user(project_id, current_user, db)

    # Get build
    if build_id:
        result = await db.execute(
            select(Build).where(
                Build.id == build_id,
                Build.project_id == project_id,
                Build.user_id == current_user.id
            )
        )
    else:
        result = await db.execute(
            select(Build).where(
                Build.project_id == project_id,
                Build.user_id == current_user.id
            ).order_by(Build.created_at.desc()).limit(1)
        )

    build = result.scalar_one_or_none()

    if not build:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No build found for this project"
        )

    # Map status to human-readable phase
    phase_map = {
        BuildStatus.PENDING: "Preparing build",
        BuildStatus.CONFIGURING: "Configuring project",
        BuildStatus.QUEUED: "Waiting in EAS queue",
        BuildStatus.IN_PROGRESS: "Compiling native code",
        BuildStatus.COMPLETED: "Build complete",
        BuildStatus.FAILED: "Build failed",
        BuildStatus.CANCELLED: "Build cancelled"
    }

    # Calculate artifact size if available
    artifact_size_mb = None
    if build.build_config and "file_size_bytes" in build.build_config:
        artifact_size_mb = round(build.build_config["file_size_bytes"] / (1024 * 1024), 2)

    return BuildStatusResponse(
        id=str(build.id),
        platform=build.platform,
        status=build.status,
        progress=build.progress,
        phase=phase_map.get(build.status, "Unknown"),
        error_message=build.error_message,
        artifact_url=build.artifact_url if build.is_downloadable else None,
        artifact_filename=build.artifact_filename if build.is_downloadable else None,
        artifact_size_mb=artifact_size_mb
    )


@router.get("/{project_id}/download", response_model=BuildDownloadResponse)
async def get_download_url(
    project_id: str,
    build_id: Optional[str] = Query(None, description="Specific build ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a presigned download URL for the build artifact.

    The URL expires in 1 hour. Can only download completed builds.
    """
    # Verify project ownership
    await get_project_for_user(project_id, current_user, db)

    # Get build
    if build_id:
        result = await db.execute(
            select(Build).where(
                Build.id == build_id,
                Build.project_id == project_id,
                Build.user_id == current_user.id
            )
        )
    else:
        result = await db.execute(
            select(Build).where(
                Build.project_id == project_id,
                Build.user_id == current_user.id,
                Build.status == BuildStatus.COMPLETED
            ).order_by(Build.created_at.desc()).limit(1)
        )

    build = result.scalar_one_or_none()

    if not build:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed build found"
        )

    if not build.is_downloadable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "build_not_ready",
                "message": "Build is not ready for download",
                "status": build.status.value
            }
        )

    # Generate presigned URL (valid for 1 hour)
    expiry_seconds = 3600
    download_url = await eas_build_service.get_download_url(build.s3_key, expiry_seconds)

    # Get file size
    size_bytes = None
    if build.build_config and "file_size_bytes" in build.build_config:
        size_bytes = build.build_config["file_size_bytes"]

    return BuildDownloadResponse(
        download_url=download_url,
        filename=build.artifact_filename,
        size_bytes=size_bytes,
        expires_at=datetime.utcnow() + timedelta(seconds=expiry_seconds)
    )


@router.delete("/{project_id}/cancel")
async def cancel_build(
    project_id: str,
    request: Optional[CancelBuildRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an active build.

    Can only cancel builds that are in PENDING, CONFIGURING, QUEUED, or IN_PROGRESS status.
    """
    # Verify project ownership
    await get_project_for_user(project_id, current_user, db)

    # Get active build
    active_build = await get_active_build(project_id, str(current_user.id), db)

    if not active_build:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active build found to cancel"
        )

    # Trigger cancellation task
    cancel_mobile_build.delay(str(active_build.id))

    # Update status immediately for UI
    active_build.status = BuildStatus.CANCELLED
    active_build.error_message = request.reason if request else "Cancelled by user"
    active_build.completed_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Cancelled build {active_build.id} for project {project_id}")

    return {
        "message": "Build cancellation initiated",
        "build_id": str(active_build.id)
    }


@router.get("/{project_id}/history", response_model=BuildHistoryResponse)
async def get_build_history(
    project_id: str,
    platform: Optional[str] = Query(None, description="Filter by platform: android or ios"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get build history for a project.

    Returns the most recent builds, optionally filtered by platform.
    """
    # Verify project ownership
    await get_project_for_user(project_id, current_user, db)

    # Build query
    query = select(Build).where(
        Build.project_id == project_id,
        Build.user_id == current_user.id
    )

    if platform:
        try:
            build_platform = BuildPlatform(platform)
            query = query.where(Build.platform == build_platform)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid platform. Must be 'android' or 'ios'"
            )

    query = query.order_by(Build.created_at.desc()).limit(limit)

    result = await db.execute(query)
    builds = result.scalars().all()

    # Get total count
    count_query = select(func.count(Build.id)).where(
        Build.project_id == project_id,
        Build.user_id == current_user.id
    )
    if platform:
        count_query = count_query.where(Build.platform == BuildPlatform(platform))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return BuildHistoryResponse(
        builds=[
            BuildResponse(
                id=str(b.id),
                project_id=str(b.project_id),
                user_id=str(b.user_id),
                platform=b.platform,
                status=b.status,
                progress=b.progress,
                eas_build_id=b.eas_build_id,
                artifact_url=b.artifact_url if b.is_downloadable else None,
                error_message=b.error_message,
                build_config=b.build_config,
                started_at=b.started_at,
                completed_at=b.completed_at,
                created_at=b.created_at
            )
            for b in builds
        ],
        total=total
    )
