"""
Simple script to add document records to database.
This adds metadata only - files remain in C:/tmp/documents/

Run from backend folder:
    python add_documents_to_db.py
"""
import asyncio
from pathlib import Path
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.project import Project
from app.models.document import Document, DocumentType

DOCUMENTS_PATH = Path("C:/tmp/documents")


def get_doc_type_enum(filename: str) -> DocumentType:
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
    else:
        return DocumentType.OTHER


def get_mime_type(filename: str) -> str:
    """Get MIME type from extension"""
    ext = filename.lower().split('.')[-1]
    types = {
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'pdf': 'application/pdf',
        'md': 'text/markdown'
    }
    return types.get(ext, 'application/octet-stream')


async def add_documents():
    print("=" * 60)
    print("ADD DOCUMENTS TO DATABASE")
    print("=" * 60)

    if not DOCUMENTS_PATH.exists():
        print(f"ERROR: Path not found: {DOCUMENTS_PATH}")
        return

    async with async_session_factory() as db:
        # Get all projects
        result = await db.execute(select(Project))
        projects = {str(p.id): p for p in result.scalars().all()}
        print(f"\nFound {len(projects)} projects in database")

        added = 0
        skipped = 0

        for folder in DOCUMENTS_PATH.iterdir():
            if not folder.is_dir():
                continue

            project_id = folder.name
            print(f"\n--- Folder: {project_id} ---")

            if project_id not in projects:
                print(f"  SKIP: No matching project in DB")
                continue

            project = projects[project_id]
            user_id = str(project.user_id)
            print(f"  Project: {project.title}")
            print(f"  User: {user_id}")

            # Check existing docs
            existing = await db.execute(
                select(Document.file_name).where(Document.project_id == UUID(project_id))
            )
            existing_names = {row[0] for row in existing.all()}

            for file_path in folder.iterdir():
                if not file_path.is_file():
                    continue
                if file_path.name.startswith('~$'):
                    continue
                if file_path.suffix.lower() not in ['.docx', '.pptx', '.pdf', '.md']:
                    continue

                if file_path.name in existing_names:
                    print(f"  SKIP: {file_path.name} (exists)")
                    skipped += 1
                    continue

                # Create document record
                doc = Document(
                    project_id=UUID(project_id),
                    title=file_path.stem.replace('_', ' ').replace('-', ' ').title(),
                    doc_type=get_doc_type_enum(file_path.name),
                    file_name=file_path.name,
                    file_path=str(file_path),  # Local path for now
                    file_url=f"/documents/download/{project_id}/{file_path.stem}",
                    file_size=file_path.stat().st_size,
                    mime_type=get_mime_type(file_path.name),
                    agent_generated=True,
                    created_at=datetime.fromtimestamp(file_path.stat().st_ctime)
                )
                db.add(doc)
                print(f"  ADDED: {file_path.name}")
                added += 1

        await db.commit()

        print("\n" + "=" * 60)
        print(f"DONE! Added: {added}, Skipped: {skipped}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(add_documents())
