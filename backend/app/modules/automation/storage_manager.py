"""
Unified Storage Manager
Automatically switches between local file system and S3 based on configuration
"""

from typing import Dict, List, Optional
from app.core.config import settings
from app.core.logging_config import logger


class StorageManager:
    """
    Unified interface for file storage

    Automatically uses local or S3 storage based on STORAGE_MODE setting:
    - "local": Local file system (./user_projects/)
    - "s3": AWS S3 cloud storage
    - "minio": MinIO (S3-compatible, self-hosted)

    Usage:
        storage = get_storage_manager()
        await storage.create_file(user_id, project_id, "backend/app/main.py", code)
    """

    def __init__(self):
        self.storage_mode = settings.STORAGE_MODE
        self._backend = None
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize storage backend based on configuration"""
        if self.storage_mode == "local":
            from app.modules.automation.file_manager import FileManager
            self._backend = FileManager()
            logger.info("StorageManager: Using LOCAL file system storage")

        elif self.storage_mode in ["s3", "minio"]:
            from app.modules.automation.s3_file_manager import S3FileManager

            if self.storage_mode == "minio":
                # MinIO configuration (S3-compatible)
                import boto3
                self._backend = S3FileManager(
                    bucket_name=settings.S3_BUCKET_NAME,
                    aws_access_key=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_key=settings.AWS_SECRET_ACCESS_KEY,
                    region=settings.AWS_REGION
                )
                # Override S3 client with MinIO endpoint
                self._backend.s3_client = boto3.client(
                    's3',
                    endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                logger.info(f"StorageManager: Using MinIO storage at {settings.MINIO_ENDPOINT}")
            else:
                # AWS S3 configuration
                self._backend = S3FileManager()
                logger.info(f"StorageManager: Using AWS S3 storage (bucket: {settings.S3_BUCKET_NAME})")
        else:
            raise ValueError(f"Invalid STORAGE_MODE: {self.storage_mode}. Must be 'local', 's3', or 'minio'")

    async def create_project(self, user_id: str, project_id: str, name: str) -> Dict:
        """Create a new project"""
        if self.storage_mode == "local":
            # Local storage doesn't need user_id in path
            return await self._backend.create_project(project_id, name)
        else:
            # S3 storage includes user_id in path
            return await self._backend.create_project(user_id, project_id, name)

    async def create_file(
        self,
        user_id: str,
        project_id: str,
        file_path: str,
        content: str
    ) -> Dict:
        """Create/upload a file"""
        if self.storage_mode == "local":
            return await self._backend.create_file(project_id, file_path, content)
        else:
            return await self._backend.create_file(user_id, project_id, file_path, content)

    async def read_file(
        self,
        user_id: str,
        project_id: str,
        file_path: str
    ) -> Optional[str]:
        """Read file content"""
        if self.storage_mode == "local":
            return await self._backend.read_file(project_id, file_path)
        else:
            return await self._backend.read_file(user_id, project_id, file_path)

    async def update_file(
        self,
        user_id: str,
        project_id: str,
        file_path: str,
        content: str
    ) -> Dict:
        """Update file content"""
        if self.storage_mode == "local":
            return await self._backend.update_file(project_id, file_path, content)
        else:
            return await self._backend.update_file(user_id, project_id, file_path, content)

    async def delete_file(
        self,
        user_id: str,
        project_id: str,
        file_path: str
    ) -> Dict:
        """Delete a file"""
        if self.storage_mode == "local":
            return await self._backend.delete_file(project_id, file_path)
        else:
            return await self._backend.delete_file(user_id, project_id, file_path)

    async def get_file_tree(
        self,
        user_id: str,
        project_id: str
    ) -> List[Dict]:
        """Get file tree structure"""
        if self.storage_mode == "local":
            return await self._backend.get_file_tree(project_id)
        else:
            return await self._backend.get_file_tree(user_id, project_id)

    async def delete_project(
        self,
        user_id: str,
        project_id: str
    ) -> Dict:
        """Delete entire project"""
        if self.storage_mode == "local":
            return await self._backend.delete_project(project_id)
        else:
            return await self._backend.delete_project(user_id, project_id)

    # S3-specific methods (only available when using S3/MinIO)

    async def get_presigned_url(
        self,
        user_id: str,
        project_id: str,
        file_path: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for direct file access (S3 only)
        Returns None for local storage
        """
        if self.storage_mode != "local" and hasattr(self._backend, 'get_presigned_url'):
            return await self._backend.get_presigned_url(
                user_id,
                project_id,
                file_path,
                expiration
            )
        return None

    async def copy_file(
        self,
        user_id: str,
        source_project_id: str,
        target_project_id: str,
        file_path: str
    ) -> Dict:
        """Copy file from one project to another (S3 optimized)"""
        if self.storage_mode != "local" and hasattr(self._backend, 'copy_file'):
            # Use S3's efficient copy operation
            return await self._backend.copy_file(
                user_id,
                source_project_id,
                target_project_id,
                file_path
            )
        else:
            # Fallback: read + write for local storage
            content = await self.read_file(user_id, source_project_id, file_path)
            if content is None:
                return {"success": False, "error": "Source file not found"}

            return await self.create_file(user_id, target_project_id, file_path, content)

    def get_storage_info(self) -> Dict:
        """Get information about current storage configuration"""
        info = {
            "storage_mode": self.storage_mode,
            "backend": self._backend.__class__.__name__
        }

        if self.storage_mode in ["s3", "minio"]:
            info["bucket"] = settings.S3_BUCKET_NAME
            info["region"] = settings.AWS_REGION
            if self.storage_mode == "minio":
                info["endpoint"] = settings.MINIO_ENDPOINT
        else:
            info["base_path"] = str(self._backend.base_path)

        return info


# Singleton instance
_storage_manager_instance = None


def get_storage_manager() -> StorageManager:
    """
    Get singleton storage manager instance

    Returns:
        StorageManager instance configured based on settings
    """
    global _storage_manager_instance

    if _storage_manager_instance is None:
        _storage_manager_instance = StorageManager()

    return _storage_manager_instance


# Convenience alias for backward compatibility
storage_manager = get_storage_manager()
