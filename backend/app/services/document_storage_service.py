"""
Document Storage Service for BharatBuild AI

Handles saving documents (Word, PPT, UML diagrams) to:
- S3/MinIO for file storage
- PostgreSQL for metadata

Directory Structure in S3:
  documents/{user_id}/{project_id}/
    ├── word/
    │   └── Project_Report_20240101_120000.docx
    ├── ppt/
    │   └── Presentation_20240101_120000.pptx
    └── diagrams/
        ├── use_case_diagram_20240101_120000.png
        ├── class_diagram_20240101_120000.png
        └── ...
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from app.services.storage_service import storage_service
from app.core.config import settings
from app.core.logging_config import logger

# S3 prefix for documents
S3_DOCUMENTS_PREFIX = "documents"


class DocumentStorageService:
    """
    Service for storing documents and diagrams to S3 and PostgreSQL.
    """

    def __init__(self):
        self.s3_prefix = S3_DOCUMENTS_PREFIX
        logger.info("[DocStorage] Document Storage Service initialized")

    def get_s3_document_prefix(self, user_id: str, project_id: str, doc_type: str = "") -> str:
        """
        Get S3 prefix for documents.

        Structure: documents/{user_id}/{project_id}/{doc_type}/
        """
        if doc_type:
            return f"{self.s3_prefix}/{user_id}/{project_id}/{doc_type}"
        return f"{self.s3_prefix}/{user_id}/{project_id}"

    async def save_document_to_s3(
        self,
        user_id: str,
        project_id: str,
        file_path: str,
        doc_type: str = "word",
        content_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a document file from local path to S3 with USER ISOLATION.

        S3 Structure: documents/{user_id}/{project_id}/{doc_type}/{file_name}

        Args:
            user_id: User UUID (REQUIRED for isolation)
            project_id: Project UUID
            file_path: Local file path
            doc_type: Type of document (word, ppt, diagrams)
            content_type: MIME type (auto-detected if not provided)

        Returns:
            Dict with s3_key, file_url, size_bytes or None on failure
        """
        try:
            if not user_id:
                logger.error("[DocStorage] user_id is required for document upload")
                return None

            local_path = Path(file_path)
            if not local_path.exists():
                logger.error(f"[DocStorage] File not found: {file_path}")
                return None

            file_name = local_path.name

            # Auto-detect content type
            if not content_type:
                content_type = self._get_content_type(file_name)

            # Read file content
            with open(local_path, 'rb') as f:
                content = f.read()

            # Generate S3 key WITH USER ISOLATION
            # Structure: documents/{user_id}/{project_id}/{doc_type}/{file_name}
            s3_key = f"{self.s3_prefix}/{user_id}/{project_id}/{doc_type}/{file_name}"

            # Upload directly to S3 with custom key (not using storage_service.upload_file)
            await self._upload_to_s3_direct(s3_key, content, content_type)

            # Get presigned URL for access
            file_url = await storage_service.get_presigned_url(s3_key)

            logger.info(f"[DocStorage] Uploaded to S3 with user isolation: {s3_key} ({len(content)} bytes)")

            return {
                's3_key': s3_key,
                'file_url': file_url,
                'size_bytes': len(content),
                'file_name': file_name,
                'content_type': content_type
            }

        except Exception as e:
            logger.error(f"[DocStorage] Failed to upload to S3: {e}", exc_info=True)
            return None

    async def _upload_to_s3_direct(
        self,
        s3_key: str,
        content: bytes,
        content_type: str,
        max_retries: int = 3,
        base_delay: float = 1.0
    ):
        """
        Upload directly to S3 with custom key (bypasses storage_service key generation).
        This ensures user isolation in the S3 path.

        Includes retry logic with exponential backoff for transient failures.

        Args:
            s3_key: S3 object key
            content: File content as bytes
            content_type: MIME type
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        """
        import boto3
        import asyncio
        from botocore.config import Config
        from botocore.exceptions import ClientError, EndpointConnectionError, ConnectionClosedError
        from app.core.config import settings

        # Build S3 client
        if settings.USE_MINIO:
            client = boto3.client(
                's3',
                endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}),
                region_name=settings.AWS_REGION
            )
        else:
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
            else:
                client = boto3.client('s3', region_name=settings.AWS_REGION)

        bucket = settings.effective_bucket_name
        last_exception = None

        # Retry loop with exponential backoff
        for attempt in range(max_retries + 1):
            try:
                client.put_object(
                    Bucket=bucket,
                    Key=s3_key,
                    Body=content,
                    ContentType=content_type
                )
                logger.info(f"[DocStorage] Direct S3 upload: {bucket}/{s3_key} (attempt {attempt + 1})")
                return  # Success - exit the function

            except (EndpointConnectionError, ConnectionClosedError) as e:
                # Network-related errors - retry
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"[DocStorage] S3 upload network error (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.1f}s: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"[DocStorage] S3 upload failed after {max_retries + 1} attempts: "
                        f"{type(e).__name__}: {e}"
                    )

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                last_exception = e

                # Retryable error codes
                retryable_codes = ['RequestTimeout', 'ServiceUnavailable', 'ThrottlingException', 'SlowDown']

                if error_code in retryable_codes and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"[DocStorage] S3 upload error {error_code} (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-retryable error or out of retries
                    logger.error(
                        f"[DocStorage] S3 upload failed with {error_code}: {e}"
                    )
                    break

            except Exception as e:
                # Unexpected error - don't retry
                last_exception = e
                logger.error(f"[DocStorage] Unexpected S3 upload error: {type(e).__name__}: {e}")
                break

        # If we get here, all retries failed
        if last_exception:
            raise last_exception

    async def save_document_to_db(
        self,
        user_id: str,
        project_id: str,
        title: str,
        doc_type: str,
        file_name: str,
        file_path: str = None,
        file_url: str = None,
        s3_key: str = None,
        file_size: int = None,
        mime_type: str = None,
        extra_metadata: Dict = None
    ) -> Optional[str]:
        """
        Save document metadata to PostgreSQL.

        Args:
            user_id: User UUID
            project_id: Project UUID
            title: Document title
            doc_type: Document type (srs, uml, ppt, report, etc.)
            file_name: File name
            file_path: Local file path (optional)
            file_url: S3 presigned URL
            s3_key: S3 object key
            file_size: File size in bytes
            mime_type: MIME type
            extra_metadata: Additional metadata as dict

        Returns:
            Document ID or None on failure
        """
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.document import Document, DocumentType

            # Map doc_type string to enum
            doc_type_enum = self._map_doc_type(doc_type)

            async with AsyncSessionLocal() as session:
                document = Document(
                    project_id=str(UUID(project_id)),
                    title=title,
                    doc_type=doc_type_enum,
                    file_name=file_name,
                    file_path=s3_key,  # Store S3 key in file_path
                    file_url=file_url,
                    file_size=file_size,
                    mime_type=mime_type,
                    agent_generated=True,
                    extra_metadata=json.dumps(extra_metadata) if extra_metadata else None
                )
                session.add(document)
                await session.commit()
                await session.refresh(document)

                logger.info(f"[DocStorage] Saved to DB: {title} (ID: {document.id})")
                return str(document.id)

        except Exception as e:
            logger.error(f"[DocStorage] Failed to save to DB: {e}", exc_info=True)
            return None

    async def save_document(
        self,
        user_id: str,
        project_id: str,
        local_file_path: str,
        title: str,
        doc_type: str,
        extra_metadata: Dict = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save document to both S3 and PostgreSQL.

        This is the main method to use for saving documents.

        Args:
            user_id: User UUID
            project_id: Project UUID
            local_file_path: Path to local file
            title: Document title
            doc_type: Document type (word, ppt, diagrams, srs, etc.)
            extra_metadata: Additional metadata

        Returns:
            Dict with document_id, s3_key, file_url or None on failure
        """
        # Map doc_type to S3 folder
        s3_folder = self._map_doc_type_to_folder(doc_type)

        # 1. Upload to S3
        s3_result = await self.save_document_to_s3(
            user_id=user_id,
            project_id=project_id,
            file_path=local_file_path,
            doc_type=s3_folder
        )

        if not s3_result:
            return None

        # 2. Save metadata to PostgreSQL
        doc_id = await self.save_document_to_db(
            user_id=user_id,
            project_id=project_id,
            title=title,
            doc_type=doc_type,
            file_name=s3_result['file_name'],
            file_url=s3_result['file_url'],
            s3_key=s3_result['s3_key'],
            file_size=s3_result['size_bytes'],
            mime_type=s3_result['content_type'],
            extra_metadata=extra_metadata
        )

        if not doc_id:
            logger.warning(f"[DocStorage] S3 upload succeeded but DB save failed for {title}")
            return {
                's3_key': s3_result['s3_key'],
                'file_url': s3_result['file_url'],
                'size_bytes': s3_result['size_bytes'],
                'db_saved': False
            }

        # 3. Optionally delete local file after successful upload
        # (keeping local for now for debugging)

        return {
            'document_id': doc_id,
            's3_key': s3_result['s3_key'],
            'file_url': s3_result['file_url'],
            'size_bytes': s3_result['size_bytes'],
            'db_saved': True
        }

    async def save_document_from_bytes(
        self,
        user_id: str,
        project_id: str,
        content: bytes,
        file_name: str,
        title: str,
        doc_type: str,
        content_type: str = None,
        extra_metadata: Dict = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save document directly from bytes (in-memory) to S3 and PostgreSQL.
        No local file creation required.

        Args:
            user_id: User UUID
            project_id: Project UUID
            content: Document content as bytes
            file_name: File name (e.g., 'Report.docx')
            title: Document title
            doc_type: Document type (word, ppt, diagrams, srs, etc.)
            content_type: MIME type (auto-detected if not provided)
            extra_metadata: Additional metadata

        Returns:
            Dict with document_id, s3_key, file_url or None on failure
        """
        try:
            if not user_id:
                logger.error("[DocStorage] user_id is required for document upload")
                return None

            # Auto-detect content type
            if not content_type:
                content_type = self._get_content_type(file_name)

            # Map doc_type to S3 folder
            s3_folder = self._map_doc_type_to_folder(doc_type)

            # Generate S3 key WITH USER ISOLATION
            s3_key = f"{self.s3_prefix}/{user_id}/{project_id}/{s3_folder}/{file_name}"

            # 1. Upload directly to S3 from bytes
            await self._upload_to_s3_direct(s3_key, content, content_type)

            # Get presigned URL for access
            file_url = await storage_service.get_presigned_url(s3_key)

            logger.info(f"[DocStorage] Uploaded from bytes to S3: {s3_key} ({len(content)} bytes)")

            # 2. Save metadata to PostgreSQL
            doc_id = await self.save_document_to_db(
                user_id=user_id,
                project_id=project_id,
                title=title,
                doc_type=doc_type,
                file_name=file_name,
                file_url=file_url,
                s3_key=s3_key,
                file_size=len(content),
                mime_type=content_type,
                extra_metadata=extra_metadata
            )

            if not doc_id:
                logger.warning(f"[DocStorage] S3 upload succeeded but DB save failed for {title}")
                return {
                    's3_key': s3_key,
                    'file_url': file_url,
                    'size_bytes': len(content),
                    'db_saved': False
                }

            return {
                'document_id': doc_id,
                's3_key': s3_key,
                'file_url': file_url,
                'size_bytes': len(content),
                'db_saved': True
            }

        except Exception as e:
            logger.error(f"[DocStorage] Failed to save from bytes: {e}", exc_info=True)
            return None

    async def save_diagram(
        self,
        user_id: str,
        project_id: str,
        local_file_path: str,
        diagram_type: str,
        extra_metadata: Dict = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save UML diagram to S3 and PostgreSQL.

        Args:
            user_id: User UUID
            project_id: Project UUID
            local_file_path: Path to diagram PNG file
            diagram_type: Type of diagram (use_case, class, sequence, etc.)
            extra_metadata: Additional metadata

        Returns:
            Dict with document_id, s3_key, file_url or None on failure
        """
        title = f"{diagram_type.replace('_', ' ').title()} Diagram"

        metadata = extra_metadata or {}
        metadata['diagram_type'] = diagram_type

        return await self.save_document(
            user_id=user_id,
            project_id=project_id,
            local_file_path=local_file_path,
            title=title,
            doc_type='uml',
            extra_metadata=metadata
        )

    async def get_project_documents(
        self,
        project_id: str,
        doc_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get all documents for a project from PostgreSQL.

        Args:
            project_id: Project UUID
            doc_type: Optional filter by document type

        Returns:
            List of document metadata dicts
        """
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.document import Document, DocumentType
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                query = select(Document).where(
                    Document.project_id == str(UUID(project_id))
                )

                if doc_type:
                    doc_type_enum = self._map_doc_type(doc_type)
                    query = query.where(Document.doc_type == doc_type_enum)

                query = query.order_by(Document.created_at.desc())

                result = await session.execute(query)
                documents = result.scalars().all()

                return [
                    {
                        'id': str(doc.id),
                        'title': doc.title,
                        'doc_type': doc.doc_type.value,
                        'file_name': doc.file_name,
                        'file_url': doc.file_url,
                        'file_size': doc.file_size,
                        'created_at': doc.created_at.isoformat() if doc.created_at else None,
                        'extra_metadata': json.loads(doc.extra_metadata) if doc.extra_metadata else None
                    }
                    for doc in documents
                ]

        except Exception as e:
            logger.error(f"[DocStorage] Failed to get documents: {e}", exc_info=True)
            return []

    async def refresh_document_url(self, document_id: str) -> Optional[str]:
        """
        Get fresh presigned URL for a document.

        Presigned URLs expire, so use this to get a new one.

        Args:
            document_id: Document UUID

        Returns:
            Fresh presigned URL or None
        """
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.document import Document
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Document).where(Document.id == str(UUID(document_id)))
                )
                document = result.scalar_one_or_none()

                if not document or not document.file_path:
                    return None

                # file_path stores the S3 key
                new_url = await storage_service.get_presigned_url(document.file_path)

                # Update stored URL
                document.file_url = new_url
                await session.commit()

                return new_url

        except Exception as e:
            logger.error(f"[DocStorage] Failed to refresh URL: {e}", exc_info=True)
            return None

    def _get_content_type(self, file_name: str) -> str:
        """Get MIME type from file extension"""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        content_types = {
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'ppt': 'application/vnd.ms-powerpoint',
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'zip': 'application/zip',
        }
        return content_types.get(ext, 'application/octet-stream')

    def _map_doc_type(self, doc_type: str):
        """Map string doc_type to DocumentType enum"""
        from app.models.document import DocumentType

        mapping = {
            'srs': DocumentType.SRS,
            'uml': DocumentType.UML,
            'diagrams': DocumentType.UML,
            'code': DocumentType.CODE,
            'report': DocumentType.REPORT,
            'project_report': DocumentType.REPORT,
            'word': DocumentType.REPORT,
            'ppt': DocumentType.PPT,
            'presentation': DocumentType.PPT,
            'viva_qa': DocumentType.VIVA_QA,
            'prd': DocumentType.PRD,
            'business_plan': DocumentType.BUSINESS_PLAN,
        }
        return mapping.get(doc_type.lower(), DocumentType.OTHER)

    def _map_doc_type_to_folder(self, doc_type: str) -> str:
        """Map doc_type to S3 folder name"""
        mapping = {
            'srs': 'word',
            'report': 'word',
            'project_report': 'word',
            'word': 'word',
            'ppt': 'ppt',
            'presentation': 'ppt',
            'uml': 'diagrams',
            'diagrams': 'diagrams',
        }
        return mapping.get(doc_type.lower(), 'other')


# Singleton instance
document_storage = DocumentStorageService()
