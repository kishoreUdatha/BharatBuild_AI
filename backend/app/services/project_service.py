"""
Project Service - Unified service for project and file management
Combines PostgreSQL, S3/MinIO, and Redis for optimal performance
"""

import asyncio
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.project_file import ProjectFile
from app.services.storage_service import storage_service
from app.services.cache_service import cache_service
from app.core.logging_config import logger
from app.core.config import settings


# Size threshold for inline storage (from settings, default 10KB)
INLINE_THRESHOLD = getattr(settings, 'FILE_INLINE_THRESHOLD', 10240)

# Max concurrent file operations for parallel saves
MAX_CONCURRENT_FILES = getattr(settings, 'MAX_CONCURRENT_FILE_OPS', 10)


class ProjectService:
    """
    High-performance project management service

    Architecture:
    - PostgreSQL: Project metadata + file metadata + small files (inline)
    - S3/MinIO: Large file content
    - Redis: Caching layer for fast reads
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Project Operations ==========

    async def get_project(self, project_id: UUID) -> Optional[dict]:
        """Get project with caching"""
        project_id_str = str(project_id)

        # Try cache first
        cached = await cache_service.get_project(project_id_str)
        if cached:
            return cached

        # Fetch from database
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return None

        project_data = {
            'id': str(project.id),
            'title': project.title,
            'description': project.description,
            'status': project.status.value if project.status else None,
            'mode': project.mode.value if project.mode else None,
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'updated_at': project.updated_at.isoformat() if project.updated_at else None
        }

        # Cache for future requests
        await cache_service.set_project(project_id_str, project_data)

        return project_data

    async def get_project_with_files(self, project_id: UUID) -> Optional[dict]:
        """Get project with all files (optimized for frontend)"""
        project_id_str = str(project_id)

        # Get project metadata
        project_data = await self.get_project(project_id)
        if not project_data:
            return None

        # Get files (try cache first)
        files = await self.get_project_files(project_id)

        return {
            **project_data,
            'files': files
        }

    # ========== File Operations ==========

    async def get_project_files(self, project_id: UUID) -> List[dict]:
        """Get all files for a project with caching"""
        project_id_str = str(project_id)

        # Try cache first
        cached = await cache_service.get_project_files(project_id_str)
        if cached:
            return cached

        # Fetch from database
        result = await self.db.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .order_by(ProjectFile.path)
        )
        files = result.scalars().all()

        files_data = []
        for f in files:
            file_data = {
                'id': str(f.id),
                'path': f.path,
                'name': f.name,
                'language': f.language,
                'is_folder': f.is_folder,
                'size_bytes': f.size_bytes,
                'created_at': f.created_at.isoformat() if f.created_at else None
            }
            files_data.append(file_data)

        # Cache the file list
        await cache_service.set_project_files(project_id_str, files_data)

        return files_data

    async def get_file_content(self, project_id: UUID, file_path: str) -> Optional[str]:
        """Get file content with multi-layer caching"""
        project_id_str = str(project_id)

        # 1. Try Redis cache
        cached = await cache_service.get_file_content(project_id_str, file_path)
        if cached:
            return cached

        # 2. Fetch file metadata from DB
        result = await self.db.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .where(ProjectFile.path == file_path)
        )
        file_record = result.scalar_one_or_none()

        if not file_record:
            return None

        # 3. Get content based on storage location
        if file_record.is_inline and file_record.content_inline:
            content = file_record.content_inline
        elif file_record.s3_key:
            content_bytes = await storage_service.download_file(file_record.s3_key)
            content = content_bytes.decode('utf-8') if content_bytes else None
        else:
            return None

        # 4. Cache for future requests
        if content:
            await cache_service.set_file_content(project_id_str, file_path, content)

        return content

    async def save_file(
        self,
        project_id: UUID,
        file_path: str,
        content: str,
        language: Optional[str] = None
    ) -> dict:
        """
        Save file with intelligent storage selection
        - Small files (<10KB): Store inline in PostgreSQL
        - Large files: Store in S3/MinIO
        """
        project_id_str = str(project_id)
        content_bytes = content.encode('utf-8')
        size_bytes = len(content_bytes)
        file_name = file_path.split('/')[-1]
        parent_path = '/'.join(file_path.split('/')[:-1]) or None

        # Detect language from extension if not provided
        if not language:
            language = self._detect_language(file_name)

        # Check if file exists
        result = await self.db.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .where(ProjectFile.path == file_path)
        )
        existing_file = result.scalar_one_or_none()

        # Determine storage method
        is_inline = size_bytes < INLINE_THRESHOLD

        if is_inline:
            # Store inline in PostgreSQL
            s3_key = None
            content_hash = storage_service.calculate_hash(content_bytes)
            content_inline = content
        else:
            # Store in S3/MinIO
            upload_result = await storage_service.upload_file(
                project_id_str,
                file_path,
                content_bytes
            )
            s3_key = upload_result['s3_key']
            content_hash = upload_result['content_hash']
            content_inline = None

        if existing_file:
            # Update existing file
            old_s3_key = existing_file.s3_key

            existing_file.content_inline = content_inline
            existing_file.s3_key = s3_key
            existing_file.content_hash = content_hash
            existing_file.size_bytes = size_bytes
            existing_file.is_inline = is_inline
            existing_file.language = language

            # Delete old S3 file if it was stored there
            if old_s3_key and old_s3_key != s3_key:
                await storage_service.delete_file(old_s3_key)

            file_record = existing_file
        else:
            # Create new file
            file_record = ProjectFile(
                project_id=project_id,
                path=file_path,
                name=file_name,
                language=language,
                s3_key=s3_key,
                content_hash=content_hash,
                size_bytes=size_bytes,
                content_inline=content_inline,
                is_inline=is_inline,
                is_folder=False,
                parent_path=parent_path
            )
            self.db.add(file_record)

            # Create parent folders if needed
            await self._ensure_parent_folders(project_id, file_path)

        await self.db.commit()
        await self.db.refresh(file_record)

        # Invalidate cache
        await cache_service.invalidate_file(project_id_str, file_path)

        logger.info(f"Saved file: {file_path} ({'inline' if is_inline else 'S3'}, {size_bytes} bytes)")

        return {
            'id': str(file_record.id),
            'path': file_record.path,
            'name': file_record.name,
            'language': file_record.language,
            'size_bytes': file_record.size_bytes,
            'storage': 'inline' if is_inline else 's3'
        }

    async def delete_file(self, project_id: UUID, file_path: str) -> bool:
        """Delete a file from all storage layers"""
        project_id_str = str(project_id)

        # Get file record
        result = await self.db.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .where(ProjectFile.path == file_path)
        )
        file_record = result.scalar_one_or_none()

        if not file_record:
            return False

        # Delete from S3 if stored there
        if file_record.s3_key:
            await storage_service.delete_file(file_record.s3_key)

        # Delete from database
        await self.db.delete(file_record)
        await self.db.commit()

        # Invalidate cache
        await cache_service.invalidate_file(project_id_str, file_path)

        logger.info(f"Deleted file: {file_path}")
        return True

    async def save_multiple_files(
        self,
        project_id: UUID,
        files: List[dict]
    ) -> List[dict]:
        """
        Bulk save multiple files (optimized for AI-generated projects)
        Uses parallel processing with controlled concurrency.

        files format: [{'path': str, 'content': str, 'language': str?}, ...]
        """
        if not files:
            return []

        # Use semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_FILES)

        async def save_with_limit(file_data: dict) -> dict:
            async with semaphore:
                return await self.save_file(
                    project_id=project_id,
                    file_path=file_data['path'],
                    content=file_data['content'],
                    language=file_data.get('language')
                )

        # Process all files in parallel with controlled concurrency
        tasks = [save_with_limit(f) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error saving file {files[i]['path']}: {result}")
                processed_results.append({
                    'path': files[i]['path'],
                    'error': str(result),
                    'success': False
                })
            else:
                processed_results.append({**result, 'success': True})

        logger.info(f"Parallel saved {len(files)} files for project {project_id}")
        return processed_results

    async def delete_project_files(self, project_id: UUID) -> int:
        """Delete all files for a project"""
        project_id_str = str(project_id)

        # Delete from S3
        await storage_service.delete_project_files(project_id_str)

        # Delete from database
        result = await self.db.execute(
            delete(ProjectFile).where(ProjectFile.project_id == project_id)
        )
        await self.db.commit()

        # Clear all cache
        await cache_service.clear_all_project_cache(project_id_str)

        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} files for project: {project_id}")

        return deleted_count

    async def delete_project_complete(self, project_id: UUID) -> dict:
        """
        Complete project deletion including:
        - All project files (S3 + PostgreSQL)
        - Cache entries (Redis)
        - Project database/schema (if using shared infrastructure)
        - Container resources (if running)

        Returns summary of what was deleted.
        """
        project_id_str = str(project_id)
        summary = {
            "project_id": project_id_str,
            "files_deleted": 0,
            "database_deleted": False,
            "cache_cleared": True,
            "container_stopped": False
        }

        # 1. Stop any running containers
        try:
            from app.modules.execution.docker_executor import docker_compose_executor
            # Try to stop compose services if running
            # This is a soft attempt - won't fail if not running
            project_path = Path(f"/tmp/student_projects/{project_id_str}")
            if project_path.exists():
                await docker_compose_executor.stop_compose(project_id_str, project_path)
                summary["container_stopped"] = True
        except Exception as e:
            logger.debug(f"No container to stop for {project_id_str}: {e}")

        # 2. Delete all files
        try:
            files_deleted = await self.delete_project_files(project_id)
            summary["files_deleted"] = files_deleted
        except Exception as e:
            logger.error(f"Error deleting files for {project_id_str}: {e}")

        # 3. Delete project database (if using shared infrastructure)
        try:
            if getattr(settings, 'USE_SHARED_DB_INFRASTRUCTURE', False):
                from app.modules.execution.database_infrastructure import (
                    db_infrastructure,
                    DatabaseType
                )

                for db_type in DatabaseType:
                    try:
                        result = await db_infrastructure.deprovision_database(
                            project_id=project_id_str,
                            db_type=db_type,
                            keep_data=False
                        )
                        if result:
                            summary["database_deleted"] = True
                    except Exception:
                        pass  # This db type wasn't used by this project
        except Exception as e:
            logger.error(f"Error deleting database for {project_id_str}: {e}")

        # 4. Delete project record from main database
        try:
            result = await self.db.execute(
                delete(Project).where(Project.id == project_id)
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error deleting project record for {project_id_str}: {e}")

        logger.info(f"Complete project deletion: {summary}")
        return summary

    # ========== Helper Methods ==========

    async def _ensure_parent_folders(self, project_id: UUID, file_path: str):
        """Create parent folder records if they don't exist"""
        parts = file_path.split('/')
        if len(parts) <= 1:
            return

        current_path = ''
        for i, part in enumerate(parts[:-1]):  # Exclude the file itself
            current_path = f"{current_path}/{part}" if current_path else part

            # Check if folder exists
            result = await self.db.execute(
                select(ProjectFile)
                .where(ProjectFile.project_id == project_id)
                .where(ProjectFile.path == current_path)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                folder = ProjectFile(
                    project_id=project_id,
                    path=current_path,
                    name=part,
                    is_folder=True,
                    is_inline=True,
                    size_bytes=0
                )
                self.db.add(folder)

    def _detect_language(self, filename: str) -> str:
        """Detect language from file extension"""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        language_map = {
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'py': 'python',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'cs': 'csharp',
            'go': 'go',
            'rs': 'rust',
            'rb': 'ruby',
            'php': 'php',
            'html': 'html',
            'css': 'css',
            'scss': 'scss',
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sql': 'sql',
            'sh': 'shell',
            'r': 'r',
            'jl': 'julia',
            'm': 'matlab',
            'kt': 'kotlin',
            'swift': 'swift',
            'scala': 'scala'
        }
        return language_map.get(ext, 'plaintext')
