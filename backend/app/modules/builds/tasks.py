"""
Celery tasks for APK/IPA builds via Expo EAS

Build flow:
1. Receive build request with project_id and platform
2. Copy project files to temp directory
3. Configure project (app.json, eas.json)
4. Trigger EAS build (non-blocking)
5. Poll EAS build status until completion
6. Download artifact and store in S3
7. Update build record with download URL
"""
import asyncio
import tempfile
import shutil
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from celery import Task
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.logging_config import logger
from app.models.build import Build, BuildStatus, BuildPlatform
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.services.eas_build_service import eas_build_service, EASBuildError
from app.schemas.build import EASBuildConfig, BuildPlatform as SchemaBuildPlatform


class BuildTask(Task):
    """Custom Celery task with proper async support"""
    abstract = True

    def run_async(self, coro):
        """Run async coroutine in sync context"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@celery_app.task(
    bind=True,
    base=BuildTask,
    max_retries=3,
    default_retry_delay=60,
    time_limit=settings.EAS_BUILD_TIMEOUT + 300,  # Build timeout + buffer
    soft_time_limit=settings.EAS_BUILD_TIMEOUT
)
def build_mobile_app(
    self,
    build_id: str,
    project_id: str,
    platform: str,
    config: Dict[str, Any]
):
    """
    Celery task to build APK/IPA via EAS

    Args:
        build_id: UUID of the Build record
        project_id: UUID of the Project to build
        platform: 'android' or 'ios'
        config: Build configuration (app_name, version, etc.)
    """
    return self.run_async(_async_build_mobile_app(
        self, build_id, project_id, platform, config
    ))


async def _async_build_mobile_app(
    task: BuildTask,
    build_id: str,
    project_id: str,
    platform: str,
    config: Dict[str, Any]
):
    """Async implementation of mobile app build"""
    temp_dir = None

    async with AsyncSessionLocal() as db:
        try:
            # Get build record
            result = await db.execute(
                select(Build).where(Build.id == build_id)
            )
            build = result.scalar_one_or_none()

            if not build:
                logger.error(f"Build not found: {build_id}")
                return {"error": "Build not found"}

            # Get project
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()

            if not project:
                await _update_build_status(db, build, BuildStatus.FAILED, "Project not found")
                return {"error": "Project not found"}

            # Update status to CONFIGURING
            await _update_build_status(db, build, BuildStatus.CONFIGURING, progress=5)
            logger.info(f"Starting build {build_id} for project {project_id} ({platform})")

            # Create temp directory and copy project files
            temp_dir = tempfile.mkdtemp(prefix=f"bharatbuild_build_{build_id}_")
            await _copy_project_files(db, project_id, temp_dir)
            await _update_build_status(db, build, BuildStatus.CONFIGURING, progress=15)

            # Configure project (app.json, eas.json)
            build_platform = BuildPlatform.ANDROID if platform == "android" else BuildPlatform.IOS

            # Generate bundle ID if not provided
            bundle_id = config.get("bundle_id")
            if not bundle_id:
                safe_name = config.get("app_name", "app").lower().replace(" ", "").replace("-", "")
                bundle_id = f"com.bharatbuild.{safe_name}"

            eas_config = EASBuildConfig(
                project_path=temp_dir,
                platform=SchemaBuildPlatform(platform),
                profile="production",
                app_name=config.get("app_name", project.title or "BharatBuild App"),
                version=config.get("version", "1.0.0"),
                build_number=config.get("build_number", 1),
                bundle_id=bundle_id
            )

            await eas_build_service.configure_project(temp_dir, eas_config)
            await _update_build_status(db, build, BuildStatus.CONFIGURING, progress=25)

            # Ensure package.json has required dependencies
            await _ensure_expo_deps(temp_dir)
            await _update_build_status(db, build, BuildStatus.CONFIGURING, progress=30)

            # Trigger EAS build
            eas_build_id, eas_status = await eas_build_service.trigger_build(
                temp_dir, build_platform, "production"
            )

            build.eas_build_id = eas_build_id
            build.status = BuildStatus.QUEUED
            build.progress = 35
            build.started_at = datetime.utcnow()
            await db.commit()
            logger.info(f"EAS build triggered: {eas_build_id}")

            # Poll for build completion
            poll_count = 0
            max_polls = settings.EAS_BUILD_TIMEOUT // settings.EAS_POLL_INTERVAL

            while poll_count < max_polls:
                await asyncio.sleep(settings.EAS_POLL_INTERVAL)
                poll_count += 1

                try:
                    eas_status = await eas_build_service.poll_status(eas_build_id)
                    our_status, progress = eas_build_service.map_eas_status_to_progress(
                        eas_status.status
                    )

                    # Scale progress (35-95% range for polling phase)
                    scaled_progress = 35 + int((progress / 100) * 60)
                    await _update_build_status(
                        db, build,
                        BuildStatus(our_status) if our_status != "in_progress" else BuildStatus.IN_PROGRESS,
                        progress=scaled_progress
                    )

                    logger.info(f"Build {build_id} status: {eas_status.status} ({scaled_progress}%)")

                    # Check for completion
                    if eas_status.status == "finished":
                        # Download artifact
                        s3_prefix = f"builds/{build.user_id}/{project_id}"
                        s3_key, file_size = await eas_build_service.download_artifact(
                            eas_build_id, eas_status, s3_prefix
                        )

                        # Update build record
                        build.status = BuildStatus.COMPLETED
                        build.progress = 100
                        build.s3_key = s3_key
                        build.artifact_url = await eas_build_service.get_download_url(s3_key)
                        build.completed_at = datetime.utcnow()
                        build.build_config = {
                            **config,
                            "file_size_bytes": file_size,
                            "eas_build_id": eas_build_id
                        }
                        await db.commit()

                        logger.info(f"Build {build_id} completed successfully!")
                        return {
                            "status": "completed",
                            "build_id": build_id,
                            "s3_key": s3_key,
                            "file_size": file_size
                        }

                    elif eas_status.status in ["errored", "cancelled"]:
                        error_msg = "Build cancelled by user" if eas_status.status == "cancelled" else \
                            (eas_status.error.get("message", "Unknown error") if eas_status.error else "Build failed")

                        await _update_build_status(
                            db, build,
                            BuildStatus.CANCELLED if eas_status.status == "cancelled" else BuildStatus.FAILED,
                            error_message=error_msg
                        )
                        return {"error": error_msg}

                except EASBuildError as e:
                    logger.warning(f"Error polling build status: {e}")
                    # Continue polling, might be temporary

            # Timeout
            await _update_build_status(
                db, build, BuildStatus.FAILED,
                error_message="Build timed out"
            )
            return {"error": "Build timed out"}

        except EASBuildError as e:
            logger.error(f"EAS build error: {e}")
            await _update_build_status(db, build, BuildStatus.FAILED, error_message=str(e))
            raise task.retry(exc=e, countdown=60)

        except Exception as e:
            logger.exception(f"Unexpected error in build task: {e}")
            if build:
                await _update_build_status(db, build, BuildStatus.FAILED, error_message=str(e))
            raise

        finally:
            # Cleanup temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp dir: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp dir: {e}")


async def _update_build_status(
    db,
    build: Build,
    status: BuildStatus,
    error_message: Optional[str] = None,
    progress: Optional[int] = None
):
    """Helper to update build status"""
    build.status = status
    if error_message:
        build.error_message = error_message
    if progress is not None:
        build.progress = progress
    if status in [BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.CANCELLED]:
        build.completed_at = datetime.utcnow()
    await db.commit()


async def _copy_project_files(db, project_id: str, dest_dir: str):
    """Copy project files to temp directory"""
    result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = result.scalars().all()

    for file in files:
        if file.content:
            file_path = os.path.join(dest_dir, file.path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file.content)

    logger.info(f"Copied {len(files)} files to {dest_dir}")


async def _ensure_expo_deps(project_dir: str):
    """Ensure package.json has Expo dependencies for EAS build"""
    package_json_path = os.path.join(project_dir, "package.json")

    if not os.path.exists(package_json_path):
        # Create minimal package.json for Expo
        package_json = {
            "name": "bharatbuild-app",
            "version": "1.0.0",
            "main": "node_modules/expo/AppEntry.js",
            "scripts": {
                "start": "expo start",
                "android": "expo run:android",
                "ios": "expo run:ios"
            },
            "dependencies": {
                "expo": "~50.0.0",
                "expo-status-bar": "~1.11.1",
                "react": "18.2.0",
                "react-native": "0.73.4"
            },
            "devDependencies": {
                "@babel/core": "^7.20.0"
            },
            "private": True
        }
    else:
        with open(package_json_path, 'r') as f:
            package_json = json.load(f)

        # Ensure expo dependency exists
        if "dependencies" not in package_json:
            package_json["dependencies"] = {}

        if "expo" not in package_json["dependencies"]:
            package_json["dependencies"]["expo"] = "~50.0.0"

    with open(package_json_path, 'w') as f:
        json.dump(package_json, f, indent=2)


@celery_app.task(bind=True, base=BuildTask)
def cancel_mobile_build(self, build_id: str):
    """Cancel an active build"""
    return self.run_async(_async_cancel_build(build_id))


async def _async_cancel_build(build_id: str):
    """Async implementation of build cancellation"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Build).where(Build.id == build_id)
        )
        build = result.scalar_one_or_none()

        if not build:
            return {"error": "Build not found"}

        if not build.is_active:
            return {"error": "Build is not active"}

        # Cancel EAS build if running
        if build.eas_build_id:
            await eas_build_service.cancel_build(build.eas_build_id)

        # Update status
        build.status = BuildStatus.CANCELLED
        build.completed_at = datetime.utcnow()
        build.error_message = "Cancelled by user"
        await db.commit()

        return {"status": "cancelled", "build_id": build_id}
