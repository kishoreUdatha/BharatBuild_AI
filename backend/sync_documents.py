"""
Script to sync documents from filesystem to database.
Run this to link existing documents in C:/tmp/documents/{project_id}/ to the database.
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


DOCUMENTS_PATH = Path("C:/tmp/documents")


def get_doc_type(filename: str) -> DocumentType:
    """Determine document type from filename"""
    name_lower = filename.lower()
    if 'srs' in name_lower:
        return DocumentType.SRS
    elif 'ppt' in name_lower or filename.endswith('.pptx'):
        return DocumentType.PPT
    elif 'viva' in name_lower or 'q&a' in name_lower or 'qa' in name_lower:
        return DocumentType.VIVA_QA
    elif 'report' in name_lower:
        return DocumentType.REPORT
    elif 'readme' in name_lower:
        return DocumentType.OTHER
    else:
        return DocumentType.OTHER


async def sync_documents():
    """Sync documents from filesystem to database"""

    if not DOCUMENTS_PATH.exists():
        print(f"Documents path not found: {DOCUMENTS_PATH}")
        return

    async with async_session_factory() as db:
        # Get all projects
        result = await db.execute(select(Project))
        projects = {str(p.id): p for p in result.scalars().all()}

        print(f"Found {len(projects)} projects in database")
        print(f"Project IDs: {list(projects.keys())}")

        # Scan document folders
        synced = 0
        skipped = 0

        for folder in DOCUMENTS_PATH.iterdir():
            if not folder.is_dir():
                continue

            project_id = folder.name
            print(f"\n--- Checking folder: {project_id} ---")

            # Check if project exists in database
            if project_id not in projects:
                print(f"  WARNING: No project found with ID {project_id}")
                continue

            project = projects[project_id]
            print(f"  Project: {project.title}")

            # Check existing documents for this project
            existing_docs = await db.execute(
                select(Document).where(Document.project_id == UUID(project_id))
            )
            existing_files = {doc.file_name for doc in existing_docs.scalars().all()}
            print(f"  Existing documents in DB: {len(existing_files)}")

            # Scan files in folder
            for file_path in folder.iterdir():
                # Skip temp files, directories
                if not file_path.is_file():
                    continue
                if file_path.name.startswith('~$'):
                    continue
                if file_path.suffix.lower() not in ['.docx', '.pptx', '.pdf', '.md']:
                    continue

                # Check if already in database
                if file_path.name in existing_files:
                    print(f"  SKIP (exists): {file_path.name}")
                    skipped += 1
                    continue

                # Determine document type
                doc_type = get_doc_type(file_path.name)

                # Create document record
                doc = Document(
                    project_id=UUID(project_id),
                    title=file_path.stem,
                    doc_type=doc_type,
                    file_name=file_path.name,
                    file_path=str(file_path),
                    file_size=file_path.stat().st_size,
                    mime_type=get_mime_type(file_path.suffix),
                    agent_generated=True,
                    created_at=datetime.fromtimestamp(file_path.stat().st_ctime)
                )

                db.add(doc)
                print(f"  ADDED: {file_path.name} ({doc_type.value})")
                synced += 1

        # Commit changes
        await db.commit()

        print(f"\n=== SYNC COMPLETE ===")
        print(f"Added: {synced} documents")
        print(f"Skipped: {skipped} (already exist)")


def get_mime_type(extension: str) -> str:
    """Get MIME type for file extension"""
    mime_types = {
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.pdf': 'application/pdf',
        '.md': 'text/markdown'
    }
    return mime_types.get(extension.lower(), 'application/octet-stream')


if __name__ == "__main__":
    print("=== Document Sync Script ===\n")
    asyncio.run(sync_documents())
