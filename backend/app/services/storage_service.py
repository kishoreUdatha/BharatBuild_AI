"""
Storage Service - Handles file storage in S3/MinIO
Optimized for 100K+ users with intelligent caching
With retry logic for resilient operations
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import hashlib
from typing import Optional, BinaryIO
import io
import asyncio
import time
from functools import wraps

from app.core.config import settings
from app.core.logging_config import logger


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    Decorator for retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (ClientError, ConnectionError, TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(f"[S3-Retry] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"[S3-Retry] All {max_retries} attempts failed: {e}")
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ClientError, ConnectionError, TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(f"[S3-Retry] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"[S3-Retry] All {max_retries} attempts failed: {e}")
            raise last_exception

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


class StorageService:
    """
    Unified storage service supporting S3 and MinIO
    - Small files (<10KB): Stored inline in PostgreSQL
    - Large files: Stored in S3/MinIO
    - Content deduplication via SHA-256 hashing
    """

    def __init__(self):
        self._client = None
        self._public_client = None  # Separate client for presigned URLs with public endpoint
        self._bucket_name = settings.effective_bucket_name
        self._initialized = False
        logger.info(f"StorageService initialized with bucket: {self._bucket_name}")

    def _get_client(self):
        """Lazy initialization of S3/MinIO client"""
        if self._client is None:
            if settings.USE_MINIO:
                # MinIO configuration
                self._client = boto3.client(
                    's3',
                    endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    config=Config(
                        signature_version='s3v4',
                        s3={'addressing_style': 'path'}
                    ),
                    region_name=settings.AWS_REGION
                )
            else:
                # AWS S3 configuration
                # In ECS/Fargate, use IAM role (no explicit credentials needed)
                # For local dev, use explicit credentials if provided
                if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                    self._client = boto3.client(
                        's3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_REGION
                    )
                else:
                    # Use IAM role credentials (automatic in ECS/EC2)
                    self._client = boto3.client(
                        's3',
                        region_name=settings.AWS_REGION
                    )
                    logger.info("S3 client using IAM role credentials")

            # Ensure bucket exists
            self._ensure_bucket()

        return self._client

    def _get_public_client(self):
        """Get client configured with public endpoint for presigned URLs"""
        if self._public_client is None:
            if settings.USE_MINIO:
                # Use public endpoint for presigned URLs (browser accessible)
                public_endpoint = getattr(settings, 'MINIO_PUBLIC_ENDPOINT', None)
                if not public_endpoint and 'minio:' in settings.MINIO_ENDPOINT:
                    public_endpoint = "localhost:9002"
                else:
                    public_endpoint = settings.MINIO_ENDPOINT

                self._public_client = boto3.client(
                    's3',
                    endpoint_url=f"http://{public_endpoint}",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    config=Config(
                        signature_version='s3v4',
                        s3={'addressing_style': 'path'}
                    ),
                    region_name=settings.AWS_REGION
                )
            else:
                # For AWS S3, use the same client
                self._public_client = self._get_client()

        return self._public_client

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist"""
        if self._initialized:
            return

        try:
            self._client.head_bucket(Bucket=self._bucket_name)
            logger.info(f"Bucket '{self._bucket_name}' exists")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['404', 'NoSuchBucket']:
                try:
                    if settings.USE_MINIO:
                        self._client.create_bucket(Bucket=self._bucket_name)
                    else:
                        # AWS S3 requires LocationConstraint for non-us-east-1
                        if settings.AWS_REGION != 'us-east-1':
                            self._client.create_bucket(
                                Bucket=self._bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': settings.AWS_REGION
                                }
                            )
                        else:
                            self._client.create_bucket(Bucket=self._bucket_name)
                    logger.info(f"Created bucket '{self._bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
            else:
                logger.error(f"Error checking bucket: {e}")

        self._initialized = True

    @staticmethod
    def calculate_hash(content: bytes) -> str:
        """Calculate SHA-256 hash for content deduplication"""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def generate_s3_key(project_id: str, file_path: str, content_hash: str = None) -> str:
        """
        Generate S3 key with simple path-based structure.
        Format: projects/{project_id}/{file_path}

        Benefits of path-based storage:
        - Simple to understand and debug
        - Easy to browse in S3 console
        - Direct mapping: file path = S3 key
        - Updates naturally overwrite (same path = same key)
        - Industry standard (GitHub, Replit, Bolt.new use this)

        Note: content_hash kept for backwards compatibility but not used in key.
        """
        # Normalize path separators
        normalized_path = file_path.replace("\\", "/")
        # Remove leading slash if present
        if normalized_path.startswith("/"):
            normalized_path = normalized_path[1:]
        return f"projects/{project_id}/{normalized_path}"

    async def upload_file(
        self,
        project_id: str,
        file_path: str,
        content: bytes,
        content_type: str = 'text/plain',
        max_retries: int = 3
    ) -> dict:
        """
        Upload file to S3/MinIO with retry logic.

        Uses path-based storage: projects/{project_id}/{file_path}
        Updates naturally overwrite existing files at the same path.

        Returns:
            dict with s3_key, content_hash, size_bytes

        Retry behavior:
            - Retries on ClientError, ConnectionError, TimeoutError
            - Exponential backoff: 1s, 2s, 4s...
            - Max 3 retries by default
        """
        content_hash = self.calculate_hash(content)
        s3_key = self.generate_s3_key(project_id, file_path)
        size_bytes = len(content)

        client = self._get_client()

        # Path-based storage: just upload (overwrites if exists)
        # No deduplication check needed - same path = same file

        # Upload file with retry logic
        last_exception = None
        for attempt in range(max_retries):
            try:
                client.put_object(
                    Bucket=self._bucket_name,
                    Key=s3_key,
                    Body=content,
                    ContentType=content_type,
                    Metadata={
                        'project_id': project_id,
                        'file_path': file_path,
                        'content_hash': content_hash
                    }
                )

                logger.info(f"[S3-Upload] ✓ Uploaded: {s3_key} ({size_bytes} bytes)")

                return {
                    's3_key': s3_key,
                    'content_hash': content_hash,
                    'size_bytes': size_bytes,
                    'deduplicated': False
                }

            except (ClientError, ConnectionError, TimeoutError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)  # 1s, 2s, 4s
                    logger.warning(f"[S3-Upload] Attempt {attempt + 1}/{max_retries} failed for {file_path}: {e}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[S3-Upload] ✗ All {max_retries} attempts failed for {file_path}: {e}")

            except Exception as e:
                logger.error(f"[S3-Upload] ✗ Unexpected error uploading {file_path}: {e}")
                raise

        # If we get here, all retries failed
        raise last_exception

    async def download_file(self, s3_key: str, max_retries: int = 3) -> Optional[bytes]:
        """
        Download file from S3/MinIO with retry logic.

        Retry behavior:
            - Retries on transient errors (ConnectionError, TimeoutError)
            - Does NOT retry on NoSuchKey (file doesn't exist)
            - Exponential backoff: 1s, 2s, 4s...
        """
        client = self._get_client()
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = client.get_object(Bucket=self._bucket_name, Key=s3_key)
                content = response['Body'].read()
                logger.debug(f"[S3-Download] ✓ Downloaded: {s3_key}")
                return content

            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.warning(f"[S3-Download] File not found: {s3_key}")
                    return None  # Don't retry - file doesn't exist
                last_exception = e
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(f"[S3-Download] Attempt {attempt + 1}/{max_retries} failed for {s3_key}: {e}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[S3-Download] ✗ All {max_retries} attempts failed for {s3_key}: {e}")

            except (ConnectionError, TimeoutError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(f"[S3-Download] Attempt {attempt + 1}/{max_retries} failed for {s3_key}: {e}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[S3-Download] ✗ All {max_retries} attempts failed for {s3_key}: {e}")

        if last_exception:
            raise last_exception
        return None

    async def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3/MinIO"""
        try:
            client = self._get_client()
            client.delete_object(Bucket=self._bucket_name, Key=s3_key)
            logger.info(f"Deleted file from S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False

    async def delete_project_files(self, project_id: str) -> int:
        """Delete all files for a project"""
        try:
            client = self._get_client()
            prefix = f"projects/{project_id}/"

            # List all objects with prefix
            paginator = client.get_paginator('list_objects_v2')
            deleted_count = 0

            for page in paginator.paginate(Bucket=self._bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects:
                        client.delete_objects(
                            Bucket=self._bucket_name,
                            Delete={'Objects': objects}
                        )
                        deleted_count += len(objects)

            logger.info(f"Deleted {deleted_count} files for project {project_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete project files: {e}")
            raise

    async def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for direct file download"""
        try:
            # Use public client so signature is valid for browser access
            client = self._get_public_client()
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self._bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise


# Singleton instance
storage_service = StorageService()
