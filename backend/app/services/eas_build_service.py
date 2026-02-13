"""
EAS Build Service - Integration with Expo Application Services for APK/IPA builds

This service handles:
1. Project configuration (app.json, eas.json generation)
2. Build triggering via EAS CLI
3. Build status polling
4. Artifact downloading and S3 storage
"""
import asyncio
import json
import os
import tempfile
import shutil
import subprocess
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
import httpx
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.schemas.build import BuildPlatform, EASBuildConfig, EASBuildStatus

logger = logging.getLogger(__name__)


class EASBuildError(Exception):
    """Custom exception for EAS build errors"""
    pass


class EASBuildService:
    """Service for managing Expo EAS builds"""

    def __init__(self):
        self.expo_token = settings.EXPO_TOKEN
        self.poll_interval = settings.EAS_POLL_INTERVAL
        self.build_timeout = settings.EAS_BUILD_TIMEOUT
        self.s3_client = self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3 client"""
        if settings.USE_MINIO:
            return boto3.client(
                's3',
                endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        return boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

    async def configure_project(
        self,
        project_path: str,
        config: EASBuildConfig
    ) -> Dict[str, Any]:
        """
        Generate/update app.json and eas.json for EAS build

        Args:
            project_path: Path to the Expo/React Native project
            config: Build configuration

        Returns:
            Dict with configuration status
        """
        try:
            project_dir = Path(project_path)

            # Generate app.json
            app_json = self._generate_app_json(config)
            app_json_path = project_dir / "app.json"
            with open(app_json_path, 'w') as f:
                json.dump(app_json, f, indent=2)

            # Generate eas.json
            eas_json = self._generate_eas_json(config)
            eas_json_path = project_dir / "eas.json"
            with open(eas_json_path, 'w') as f:
                json.dump(eas_json, f, indent=2)

            logger.info(f"Configured project at {project_path} for {config.platform.value} build")

            return {
                "success": True,
                "app_json_path": str(app_json_path),
                "eas_json_path": str(eas_json_path),
                "config": app_json
            }

        except Exception as e:
            logger.error(f"Failed to configure project: {e}")
            raise EASBuildError(f"Failed to configure project: {str(e)}")

    def _generate_app_json(self, config: EASBuildConfig) -> Dict[str, Any]:
        """Generate Expo app.json configuration"""
        app_config = {
            "expo": {
                "name": config.app_name,
                "slug": config.bundle_id.split('.')[-1].lower(),
                "version": config.version,
                "orientation": "portrait",
                "userInterfaceStyle": "automatic",
                "assetBundlePatterns": ["**/*"],
                "ios": {
                    "supportsTablet": True,
                    "bundleIdentifier": config.bundle_id,
                    "buildNumber": str(config.build_number)
                },
                "android": {
                    "adaptiveIcon": {
                        "backgroundColor": "#ffffff"
                    },
                    "package": config.bundle_id,
                    "versionCode": config.build_number
                },
                "extra": {
                    "eas": {
                        "projectId": config.bundle_id
                    }
                }
            }
        }

        # Add icon if provided
        if config.icon_path:
            app_config["expo"]["icon"] = config.icon_path
            app_config["expo"]["android"]["adaptiveIcon"]["foregroundImage"] = config.icon_path

        # Add splash screen if provided
        if config.splash_path:
            app_config["expo"]["splash"] = {
                "image": config.splash_path,
                "resizeMode": "contain",
                "backgroundColor": "#ffffff"
            }

        # Merge extra config
        if config.extra_config:
            self._deep_merge(app_config, config.extra_config)

        return app_config

    def _generate_eas_json(self, config: EASBuildConfig) -> Dict[str, Any]:
        """Generate EAS build configuration (eas.json)"""
        return {
            "cli": {
                "version": ">= 5.0.0"
            },
            "build": {
                "development": {
                    "developmentClient": True,
                    "distribution": "internal"
                },
                "preview": {
                    "distribution": "internal"
                },
                "production": {
                    "android": {
                        "buildType": "apk"  # APK for direct installation
                    },
                    "ios": {
                        "resourceClass": "m1-medium"
                    }
                }
            },
            "submit": {
                "production": {}
            }
        }

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    async def trigger_build(
        self,
        project_path: str,
        platform: BuildPlatform,
        profile: str = "production"
    ) -> Tuple[str, str]:
        """
        Trigger EAS build and return build ID

        Args:
            project_path: Path to the configured Expo project
            platform: android or ios
            profile: Build profile (development, preview, production)

        Returns:
            Tuple of (eas_build_id, status_message)
        """
        try:
            # Prepare environment with EXPO_TOKEN
            env = os.environ.copy()
            env["EXPO_TOKEN"] = self.expo_token

            # Build command
            cmd = [
                "npx", "eas-cli", "build",
                "--platform", platform.value,
                "--profile", profile,
                "--non-interactive",
                "--json",
                "--no-wait"  # Don't wait for build to complete
            ]

            logger.info(f"Triggering EAS build: {' '.join(cmd)}")

            # Run EAS build command
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    cwd=project_path,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout for submission
                )
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"EAS build command failed: {error_msg}")
                raise EASBuildError(f"EAS build failed: {error_msg}")

            # Parse JSON output to get build ID
            try:
                output = json.loads(result.stdout)
                if isinstance(output, list) and len(output) > 0:
                    build_info = output[0]
                    eas_build_id = build_info.get("id")
                    status = build_info.get("status", "submitted")
                    return eas_build_id, status
                else:
                    raise EASBuildError("Unexpected EAS output format")
            except json.JSONDecodeError:
                # Try to extract build ID from text output
                logger.warning(f"Could not parse JSON, raw output: {result.stdout}")
                raise EASBuildError("Could not parse EAS build output")

        except subprocess.TimeoutExpired:
            raise EASBuildError("EAS build submission timed out")
        except Exception as e:
            logger.error(f"Failed to trigger EAS build: {e}")
            raise EASBuildError(f"Failed to trigger build: {str(e)}")

    async def poll_status(self, eas_build_id: str) -> EASBuildStatus:
        """
        Poll EAS build status

        Args:
            eas_build_id: EAS build UUID

        Returns:
            EASBuildStatus with current build state
        """
        try:
            # Prepare environment
            env = os.environ.copy()
            env["EXPO_TOKEN"] = self.expo_token

            # Build view command
            cmd = [
                "npx", "eas-cli", "build:view",
                eas_build_id,
                "--json"
            ]

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"EAS build:view failed: {error_msg}")
                raise EASBuildError(f"Failed to get build status: {error_msg}")

            # Parse status
            build_data = json.loads(result.stdout)

            return EASBuildStatus(
                id=build_data.get("id"),
                status=build_data.get("status", "unknown"),
                platform=build_data.get("platform", "unknown"),
                artifacts=build_data.get("artifacts"),
                error=build_data.get("error"),
                started_at=build_data.get("createdAt"),
                completed_at=build_data.get("completedAt")
            )

        except subprocess.TimeoutExpired:
            raise EASBuildError("EAS status check timed out")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse EAS status: {e}")
            raise EASBuildError("Failed to parse build status")
        except Exception as e:
            logger.error(f"Failed to poll EAS status: {e}")
            raise EASBuildError(f"Failed to get build status: {str(e)}")

    def map_eas_status_to_progress(self, eas_status: str) -> Tuple[str, int]:
        """
        Map EAS status to our BuildStatus and progress percentage

        Returns:
            Tuple of (our_status, progress_percentage)
        """
        status_map = {
            "new": ("queued", 5),
            "in-queue": ("queued", 10),
            "in-progress": ("in_progress", 50),
            "finished": ("completed", 100),
            "errored": ("failed", 0),
            "cancelled": ("cancelled", 0),
        }
        return status_map.get(eas_status, ("in_progress", 30))

    async def download_artifact(
        self,
        eas_build_id: str,
        eas_status: EASBuildStatus,
        s3_prefix: str
    ) -> Tuple[str, int]:
        """
        Download build artifact from EAS and upload to S3

        Args:
            eas_build_id: EAS build UUID
            eas_status: Current EAS build status (contains artifact URL)
            s3_prefix: S3 key prefix for storing the artifact

        Returns:
            Tuple of (s3_key, file_size_bytes)
        """
        try:
            # Get artifact URL from EAS status
            artifacts = eas_status.artifacts
            if not artifacts:
                raise EASBuildError("No artifacts found in build")

            artifact_url = artifacts.get("buildUrl") or artifacts.get("applicationArchiveUrl")
            if not artifact_url:
                raise EASBuildError("No artifact URL found")

            logger.info(f"Downloading artifact from {artifact_url}")

            # Download artifact
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.get(artifact_url)
                response.raise_for_status()
                artifact_data = response.content
                file_size = len(artifact_data)

            # Determine file extension
            platform = eas_status.platform
            ext = "apk" if platform == "android" else "ipa"
            s3_key = f"{s3_prefix}/{eas_build_id}.{ext}"

            # Upload to S3
            logger.info(f"Uploading artifact to S3: {s3_key}")
            self.s3_client.put_object(
                Bucket=settings.effective_bucket_name,
                Key=s3_key,
                Body=artifact_data,
                ContentType="application/octet-stream",
                Metadata={
                    "eas_build_id": eas_build_id,
                    "platform": platform,
                    "uploaded_at": datetime.utcnow().isoformat()
                }
            )

            logger.info(f"Artifact uploaded successfully: {s3_key} ({file_size} bytes)")
            return s3_key, file_size

        except httpx.HTTPError as e:
            logger.error(f"Failed to download artifact: {e}")
            raise EASBuildError(f"Failed to download artifact: {str(e)}")
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise EASBuildError(f"Failed to store artifact: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to process artifact: {e}")
            raise EASBuildError(f"Failed to process artifact: {str(e)}")

    async def get_download_url(self, s3_key: str, expiry: int = 3600) -> str:
        """
        Generate presigned S3 URL for artifact download

        Args:
            s3_key: S3 key of the artifact
            expiry: URL expiry time in seconds (default 1 hour)

        Returns:
            Presigned download URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.effective_bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiry
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise EASBuildError(f"Failed to generate download URL: {str(e)}")

    async def cancel_build(self, eas_build_id: str) -> bool:
        """
        Cancel an active EAS build

        Args:
            eas_build_id: EAS build UUID

        Returns:
            True if cancellation was successful
        """
        try:
            env = os.environ.copy()
            env["EXPO_TOKEN"] = self.expo_token

            cmd = [
                "npx", "eas-cli", "build:cancel",
                eas_build_id
            ]

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            )

            if result.returncode != 0:
                logger.warning(f"EAS build:cancel may have failed: {result.stderr}")
                return False

            logger.info(f"Cancelled EAS build: {eas_build_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel EAS build: {e}")
            return False

    async def cleanup_project_temp(self, project_path: str) -> None:
        """Clean up temporary project files after build"""
        try:
            if os.path.exists(project_path) and project_path.startswith(tempfile.gettempdir()):
                shutil.rmtree(project_path)
                logger.info(f"Cleaned up temp project: {project_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp project: {e}")


# Singleton instance
eas_build_service = EASBuildService()
