"""
Migration Script: Upload existing documents from filesystem to S3 and save metadata to database.

This script:
1. Scans C:/tmp/documents/{project_id}/ folders
2. Uploads each document to S3
3. Creates records in the documents table
4. Optionally deletes local files after successful upload

Usage:
    cd backend
    python migrate_documents_to_s3.py
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.project import Project
from app.models.document import Document, DocumentType
from app.services.document_storage_service import document_storage
from app.services.storage_service import storage_service
from app.core.logging_config import logger


DOCUMENTS_PATH = Path("C:/tmp/documents")
DELETE_AFTER_UPLOAD = False  # Set to True to delete local files after S3 upload


def get_doc_type(filename: str) -> str:
    """Determine document type from filename"""
    name_lower = filename.lower()
    if 'srs' in name_lower:
        return 'srs'
    elif 'ppt' in name_lower or filename.endswith('.pptx'):
        return 'ppt'
    elif 'viva' in name_lower or 'q&a' in name_lower or 'qa' in name_lower:
        return 'viva_qa'
    elif 'report' in name_lower:
        return 'report'
    elif 'readme' in name_lower:
        return 'other'
    else:
        return 'other'


def get_title_from_filename(filename: str) -> str:
    """Generate a nice title from filename"""
    name = Path(filename).stem
    # Remove common prefixes/timestamps
    name = name.replace('_', ' ').replace('-', ' ')
    # Capitalize words
    return name.title()


async def migrate_documents():
    """Migrate documents from filesystem to S3 + Database"""

    if not DOCUMENTS_PATH.exists():
        print(f"Documents path not found: {DOCUMENTS_PATH}")
        return

    print("=" * 60)
    print("DOCUMENT MIGRATION: Filesystem → S3 + Database")
    print("=" * 60)

    async with async_session_factory() as db:
        # Get all projects with their user_ids
        result = await db.execute(select(Project))
        projects = {str(p.id): p for p in result.scalars().all()}

        print(f"\nFound {len(projects)} projects in database")

        # Stats
        total_uploaded = 0
        total_skipped = 0
        total_failed = 0

        # Scan document folders
        for folder in DOCUMENTS_PATH.iterdir():
            if not folder.is_dir():
                continue

            project_id = folder.name
            print(f"\n{'─' * 50}")
            print(f"Processing folder: {project_id}")

            # Check if project exists in database
            if project_id not in projects:
                print(f"  ⚠ WARNING: No project found with ID {project_id} - SKIPPING")
                continue

            project = projects[project_id]
            user_id = str(project.user_id)
            print(f"  Project: {project.title}")
            print(f"  User ID: {user_id}")

            # Check existing documents for this project in DB
            existing_docs = await db.execute(
                select(Document).where(Document.project_id == UUID(project_id))
            )
            existing_files = {doc.file_name for doc in existing_docs.scalars().all()}
            print(f"  Existing documents in DB: {len(existing_files)}")

            # Scan files in folder
            for file_path in folder.iterdir():
                # Skip temp files, directories, subdirectories
                if not file_path.is_file():
                    continue
                if file_path.name.startswith('~$'):
                    continue
                if file_path.suffix.lower() not in ['.docx', '.pptx', '.pdf', '.md']:
                    continue

                # Check if already in database
                if file_path.name in existing_files:
                    print(f"  ⏭ SKIP (exists in DB): {file_path.name}")
                    total_skipped += 1
                    continue

                # Determine document type and title
                doc_type = get_doc_type(file_path.name)
                title = get_title_from_filename(file_path.name)

                print(f"  📤 Uploading: {file_path.name} ({doc_type})")

                try:
                    # Upload to S3 and save to database
                    result = await document_storage.save_document(
                        user_id=user_id,
                        project_id=project_id,
                        local_file_path=str(file_path),
                        title=title,
                        doc_type=doc_type,
                        extra_metadata={
                            'migrated_from': str(file_path),
                            'migration_date': datetime.utcnow().isoformat(),
                            'original_filename': file_path.name
                        }
                    )

                    if result and result.get('db_saved'):
                        print(f"     ✅ SUCCESS: Uploaded to S3 and saved to DB")
                        print(f"        S3 Key: {result.get('s3_key')}")
                        total_uploaded += 1

                        # Optionally delete local file
                        if DELETE_AFTER_UPLOAD:
                            file_path.unlink()
                            print(f"        🗑 Deleted local file")
                    else:
                        print(f"     ⚠ PARTIAL: Uploaded to S3 but DB save failed")
                        total_failed += 1

                except Exception as e:
                    print(f"     ❌ FAILED: {e}")
                    total_failed += 1

        # Summary
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"  ✅ Uploaded: {total_uploaded}")
        print(f"  ⏭ Skipped:  {total_skipped} (already in DB)")
        print(f"  ❌ Failed:   {total_failed}")
        print("=" * 60)


if __name__ == "__main__":
    print("\n🚀 Starting Document Migration...\n")
    asyncio.run(migrate_documents())
