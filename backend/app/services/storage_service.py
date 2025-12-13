"""
Storage Service - Handles file storage in S3/MinIO
Optimized for 100K+ users with intelligent caching
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import hashlib
from typing import Optional, BinaryIO
import io

from app.core.config import settings
from app.core.logging_config import logger


class StorageService:
    """
    Unified storage service supporting S3 and MinIO
    - Small files (<10KB): Stored inline in PostgreSQL
    - Large files: Stored in S3/MinIO
    - Content deduplication via SHA-256 hashing
    """

    def __init__(self):
        self._client = None
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
    def generate_s3_key(project_id: str, file_path: str, content_hash: str) -> str:
        """
        Generate S3 key with structure for efficient storage
        Format: projects/{project_id}/files/{content_hash[:2]}/{content_hash}
        """
        # Use hash prefix for better S3 partitioning (improves performance)
        hash_prefix = content_hash[:2]
        return f"projects/{project_id}/files/{hash_prefix}/{content_hash}"

    async def upload_file(
        self,
        project_id: str,
        file_path: str,
        content: bytes,
        content_type: str = 'text/plain'
    ) -> dict:
        """
        Upload file to S3/MinIO

        Returns:
            dict with s3_key, content_hash, size_bytes
        """
        content_hash = self.calculate_hash(content)
        s3_key = self.generate_s3_key(project_id, file_path, content_hash)
        size_bytes = len(content)

        try:
            client = self._get_client()

            # Check if file already exists (deduplication)
            try:
                client.head_object(Bucket=self._bucket_name, Key=s3_key)
                logger.debug(f"File already exists (deduplicated): {s3_key}")
                return {
                    's3_key': s3_key,
                    'content_hash': content_hash,
                    'size_bytes': size_bytes,
                    'deduplicated': True
                }
            except ClientError:
                pass  # File doesn't exist, proceed with upload

            # Upload file
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

            logger.info(f"Uploaded file to S3: {s3_key} ({size_bytes} bytes)")

            return {
                's3_key': s3_key,
                'content_hash': content_hash,
                'size_bytes': size_bytes,
                'deduplicated': False
            }

        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

    async def download_file(self, s3_key: str) -> Optional[bytes]:
        """Download file from S3/MinIO"""
        try:
            client = self._get_client()
            response = client.get_object(Bucket=self._bucket_name, Key=s3_key)
            content = response['Body'].read()
            logger.debug(f"Downloaded file from S3: {s3_key}")
            return content
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"File not found in S3: {s3_key}")
                return None
            logger.error(f"Failed to download file from S3: {e}")
            raise

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
            client = self._get_client()
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
