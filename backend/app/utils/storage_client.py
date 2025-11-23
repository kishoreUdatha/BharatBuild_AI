from typing import BinaryIO, Optional
import os
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.logging_config import logger


class StorageClient:
    """S3/MinIO storage client for file operations"""

    def __init__(self):
        if settings.USE_MINIO:
            # MinIO client
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.AWS_SECRET_ACCESS_KEY,
                secure=False  # Set True for HTTPS
            )
            self.is_minio = True
        else:
            # AWS S3 client
            self.client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.is_minio = False

        self.bucket_name = settings.S3_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if not"""
        try:
            if self.is_minio:
                if not self.client.bucket_exists(self.bucket_name):
                    self.client.make_bucket(self.bucket_name)
                    logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                self.client.head_bucket(Bucket=self.bucket_name)
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            if not self.is_minio:
                try:
                    self.client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': settings.AWS_REGION}
                    )
                    logger.info(f"Created S3 bucket: {self.bucket_name}")
                except Exception as create_error:
                    logger.error(f"Error creating bucket: {create_error}")

    def upload_file(
        self,
        file_path: str,
        object_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload file to storage

        Args:
            file_path: Local file path
            object_name: Object name in storage
            content_type: MIME type

        Returns:
            URL of uploaded file
        """
        try:
            if self.is_minio:
                self.client.fput_object(
                    self.bucket_name,
                    object_name,
                    file_path,
                    content_type=content_type
                )
            else:
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type

                self.client.upload_file(
                    file_path,
                    self.bucket_name,
                    object_name,
                    ExtraArgs=extra_args
                )

            url = self.get_file_url(object_name)
            logger.info(f"Uploaded file: {object_name}")
            return url

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise

    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> str:
        """
        Upload file object to storage

        Args:
            file_obj: File-like object
            object_name: Object name in storage
            content_type: MIME type
            file_size: File size in bytes (required for MinIO)

        Returns:
            URL of uploaded file
        """
        try:
            if self.is_minio:
                if file_size is None:
                    # Get file size
                    file_obj.seek(0, 2)
                    file_size = file_obj.tell()
                    file_obj.seek(0)

                self.client.put_object(
                    self.bucket_name,
                    object_name,
                    file_obj,
                    file_size,
                    content_type=content_type
                )
            else:
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type

                self.client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    object_name,
                    ExtraArgs=extra_args
                )

            url = self.get_file_url(object_name)
            logger.info(f"Uploaded file object: {object_name}")
            return url

        except Exception as e:
            logger.error(f"Error uploading file object: {e}")
            raise

    def download_file(self, object_name: str, file_path: str) -> bool:
        """Download file from storage"""
        try:
            if self.is_minio:
                self.client.fget_object(
                    self.bucket_name,
                    object_name,
                    file_path
                )
            else:
                self.client.download_file(
                    self.bucket_name,
                    object_name,
                    file_path
                )

            logger.info(f"Downloaded file: {object_name}")
            return True

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False

    def delete_file(self, object_name: str) -> bool:
        """Delete file from storage"""
        try:
            if self.is_minio:
                self.client.remove_object(self.bucket_name, object_name)
            else:
                self.client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_name
                )

            logger.info(f"Deleted file: {object_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def get_file_url(self, object_name: str, expiry: int = 3600) -> str:
        """
        Get presigned URL for file

        Args:
            object_name: Object name in storage
            expiry: URL expiry time in seconds (default 1 hour)

        Returns:
            Presigned URL
        """
        try:
            if self.is_minio:
                url = self.client.presigned_get_object(
                    self.bucket_name,
                    object_name,
                    expires=expiry
                )
            else:
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': object_name},
                    ExpiresIn=expiry
                )

            return url

        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            # Return a basic URL if presigned fails
            if self.is_minio:
                return f"http://{settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_name}"
            else:
                return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_name}"

    def list_files(self, prefix: str = "") -> list:
        """List files in storage with optional prefix"""
        try:
            files = []
            if self.is_minio:
                objects = self.client.list_objects(
                    self.bucket_name,
                    prefix=prefix,
                    recursive=True
                )
                files = [obj.object_name for obj in objects]
            else:
                response = self.client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )
                if 'Contents' in response:
                    files = [obj['Key'] for obj in response['Contents']]

            return files

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in storage"""
        try:
            if self.is_minio:
                self.client.stat_object(self.bucket_name, object_name)
            else:
                self.client.head_object(
                    Bucket=self.bucket_name,
                    Key=object_name
                )
            return True
        except:
            return False


# Create singleton instance
storage_client = StorageClient()
