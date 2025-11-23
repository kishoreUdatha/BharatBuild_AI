"""
S3-Based File Manager - Production-ready cloud storage
Stores project files in AWS S3 (similar to Bolt.new)
"""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Optional
import json
from datetime import datetime
from io import BytesIO
import mimetypes

from app.core.logging_config import logger
from app.core.config import settings


class S3FileManager:
    """
    Manages project files in AWS S3

    Storage Structure:
    s3://bucket-name/
        └── projects/
            └── {user_id}/
                └── {project_id}/
                    ├── backend/
                    ├── frontend/
                    └── documentation/
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize S3 client

        Args:
            bucket_name: S3 bucket name (defaults to settings.S3_BUCKET_NAME)
            aws_access_key: AWS access key (defaults to settings.AWS_ACCESS_KEY_ID)
            aws_secret_key: AWS secret key (defaults to settings.AWS_SECRET_ACCESS_KEY)
            region: AWS region (defaults to settings.AWS_REGION)
        """
        self.bucket_name = bucket_name or getattr(settings, 'S3_BUCKET_NAME', 'bharatbuild-projects')
        self.region = region or getattr(settings, 'AWS_REGION', 'ap-south-1')  # Mumbai region for India

        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key or getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=aws_secret_key or getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
            region_name=self.region
        )

        # Ensure bucket exists
        self._ensure_bucket_exists()

        logger.info(f"S3FileManager initialized with bucket: {self.bucket_name}")

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )

                    # Enable versioning for backup/recovery
                    self.s3_client.put_bucket_versioning(
                        Bucket=self.bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )

                    logger.info(f"Created bucket: {self.bucket_name}")
                except Exception as create_error:
                    logger.warning(f"Could not create bucket: {create_error}")
            else:
                logger.error(f"Error checking bucket: {e}")

    def _get_s3_key(self, user_id: str, project_id: str, file_path: str = "") -> str:
        """
        Generate S3 key for a file

        Args:
            user_id: User ID
            project_id: Project ID
            file_path: Relative file path within project

        Returns:
            Full S3 key: projects/{user_id}/{project_id}/{file_path}
        """
        base_key = f"projects/{user_id}/{project_id}"
        if file_path:
            return f"{base_key}/{file_path}"
        return base_key

    def _detect_content_type(self, file_path: str) -> str:
        """Detect MIME type from file extension"""
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or 'application/octet-stream'

    async def create_project(self, user_id: str, project_id: str, name: str) -> Dict:
        """
        Create a new project in S3

        Args:
            user_id: User ID
            project_id: Project ID
            name: Project name

        Returns:
            Dict with success status and project info
        """
        try:
            # Create metadata file
            metadata = {
                "id": project_id,
                "user_id": user_id,
                "name": name,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            metadata_key = self._get_s3_key(user_id, project_id, ".project_metadata.json")

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json',
                Metadata={
                    'project-id': project_id,
                    'user-id': user_id,
                    'project-name': name
                }
            )

            logger.info(f"Created project in S3: {project_id} for user {user_id}")

            return {
                "success": True,
                "project_id": project_id,
                "user_id": user_id,
                "s3_path": f"s3://{self.bucket_name}/{self._get_s3_key(user_id, project_id)}"
            }

        except Exception as e:
            logger.error(f"Error creating project in S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_file(
        self,
        user_id: str,
        project_id: str,
        file_path: str,
        content: str
    ) -> Dict:
        """
        Create/upload a file to S3

        Args:
            user_id: User ID
            project_id: Project ID
            file_path: Relative file path (e.g., "backend/app/main.py")
            content: File content

        Returns:
            Dict with success status and file info
        """
        try:
            s3_key = self._get_s3_key(user_id, project_id, file_path)
            content_type = self._detect_content_type(file_path)

            # Upload file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType=content_type,
                Metadata={
                    'project-id': project_id,
                    'user-id': user_id,
                    'file-path': file_path
                }
            )

            logger.info(f"Created file in S3: {file_path} for project {project_id}")

            return {
                "success": True,
                "path": file_path,
                "size": len(content),
                "s3_key": s3_key,
                "url": f"s3://{self.bucket_name}/{s3_key}"
            }

        except Exception as e:
            logger.error(f"Error creating file in S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def read_file(self, user_id: str, project_id: str, file_path: str) -> Optional[str]:
        """
        Read file content from S3

        Args:
            user_id: User ID
            project_id: Project ID
            file_path: Relative file path

        Returns:
            File content as string, or None if not found
        """
        try:
            s3_key = self._get_s3_key(user_id, project_id, file_path)

            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            content = response['Body'].read().decode('utf-8')

            return content

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"File not found in S3: {file_path}")
                return None
            else:
                logger.error(f"Error reading file from S3: {e}")
                return None
        except Exception as e:
            logger.error(f"Error reading file from S3: {e}")
            return None

    async def update_file(
        self,
        user_id: str,
        project_id: str,
        file_path: str,
        content: str
    ) -> Dict:
        """
        Update file content in S3 (S3 automatically handles versioning)

        Args:
            user_id: User ID
            project_id: Project ID
            file_path: Relative file path
            content: New file content

        Returns:
            Dict with success status
        """
        return await self.create_file(user_id, project_id, file_path, content)

    async def delete_file(self, user_id: str, project_id: str, file_path: str) -> Dict:
        """
        Delete a file from S3

        Args:
            user_id: User ID
            project_id: Project ID
            file_path: Relative file path

        Returns:
            Dict with success status
        """
        try:
            s3_key = self._get_s3_key(user_id, project_id, file_path)

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            logger.info(f"Deleted file from S3: {file_path}")

            return {
                "success": True,
                "path": file_path
            }

        except Exception as e:
            logger.error(f"Error deleting file from S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_file_tree(self, user_id: str, project_id: str) -> List[Dict]:
        """
        Get file tree structure from S3

        Args:
            user_id: User ID
            project_id: Project ID

        Returns:
            List of file/directory objects
        """
        try:
            prefix = self._get_s3_key(user_id, project_id, "")

            # List all objects with prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            files = []

            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    s3_key = obj['Key']

                    # Skip metadata files
                    if '.project_metadata.json' in s3_key:
                        continue

                    # Extract relative path
                    relative_path = s3_key.replace(prefix + '/', '')

                    if not relative_path:
                        continue

                    # Detect language
                    ext = relative_path.split('.')[-1].lower() if '.' in relative_path else ''
                    language_map = {
                        'js': 'javascript',
                        'jsx': 'javascript',
                        'ts': 'typescript',
                        'tsx': 'typescript',
                        'py': 'python',
                        'java': 'java',
                        'go': 'go',
                        'rs': 'rust',
                        'html': 'html',
                        'css': 'css',
                        'json': 'json',
                        'md': 'markdown',
                        'yml': 'yaml',
                        'yaml': 'yaml',
                    }

                    files.append({
                        "path": relative_path,
                        "name": relative_path.split('/')[-1],
                        "type": "file",
                        "language": language_map.get(ext, 'plaintext'),
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat()
                    })

            return files

        except Exception as e:
            logger.error(f"Error getting file tree from S3: {e}")
            return []

    async def delete_project(self, user_id: str, project_id: str) -> Dict:
        """
        Delete entire project from S3

        Args:
            user_id: User ID
            project_id: Project ID

        Returns:
            Dict with success status
        """
        try:
            prefix = self._get_s3_key(user_id, project_id, "")

            # List all objects with prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            # Delete all objects
            delete_count = 0
            for page in pages:
                if 'Contents' not in page:
                    continue

                objects = [{'Key': obj['Key']} for obj in page['Contents']]

                if objects:
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': objects}
                    )
                    delete_count += len(objects)

            logger.info(f"Deleted project from S3: {project_id} ({delete_count} files)")

            return {
                "success": True,
                "project_id": project_id,
                "files_deleted": delete_count
            }

        except Exception as e:
            logger.error(f"Error deleting project from S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_presigned_url(
        self,
        user_id: str,
        project_id: str,
        file_path: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for direct file access
        Useful for frontend to download/view files directly

        Args:
            user_id: User ID
            project_id: Project ID
            file_path: Relative file path
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL or None if error
        """
        try:
            s3_key = self._get_s3_key(user_id, project_id, file_path)

            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )

            return url

        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

    async def copy_file(
        self,
        user_id: str,
        source_project_id: str,
        target_project_id: str,
        file_path: str
    ) -> Dict:
        """
        Copy file from one project to another

        Args:
            user_id: User ID
            source_project_id: Source project ID
            target_project_id: Target project ID
            file_path: Relative file path

        Returns:
            Dict with success status
        """
        try:
            source_key = self._get_s3_key(user_id, source_project_id, file_path)
            target_key = self._get_s3_key(user_id, target_project_id, file_path)

            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': source_key},
                Key=target_key
            )

            logger.info(f"Copied file in S3: {file_path} from {source_project_id} to {target_project_id}")

            return {
                "success": True,
                "source_project": source_project_id,
                "target_project": target_project_id,
                "path": file_path
            }

        except Exception as e:
            logger.error(f"Error copying file in S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
s3_file_manager = S3FileManager()
