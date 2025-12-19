"""
Quick script to check documents in database and test the flow.
Run: python check_documents.py
"""
import asyncio
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.models.document import Document
from app.models.project import Project


async def check_documents():
    print("=" * 60)
    print("DOCUMENT CHECK")
    print("=" * 60)

    async with async_session_factory() as db:
        # Count documents
        doc_count = await db.execute(select(func.count(Document.id)))
        total_docs = doc_count.scalar()
        print(f"\nTotal documents in database: {total_docs}")

        if total_docs == 0:
            print("\n⚠️  NO DOCUMENTS IN DATABASE!")
            print("   Documents must be saved to database to appear in the menu.")
            print("   Run: python migrate_documents_to_s3.py")
            return

        # List all documents
        result = await db.execute(
            select(Document, Project.title.label('project_title'))
            .join(Project, Document.project_id == Project.id)
            .order_by(Document.created_at.desc())
            .limit(20)
        )
        rows = result.all()

        print(f"\nDocuments found:")
        print("-" * 60)
        for doc, project_title in rows:
            print(f"  Project: {project_title}")
            print(f"    - {doc.file_name} ({doc.doc_type.value if doc.doc_type else 'unknown'})")
            print(f"    - S3 Key: {doc.file_path}")
            print(f"    - Size: {doc.file_size or 0} bytes")
            print()

        # List projects with document counts
        print("\nDocuments per project:")
        print("-" * 60)
        project_docs = await db.execute(
            select(
                Project.id,
                Project.title,
                func.count(Document.id).label('doc_count')
            )
            .outerjoin(Document, Document.project_id == Project.id)
            .group_by(Project.id, Project.title)
            .order_by(func.count(Document.id).desc())
            .limit(10)
        )
        for project_id, title, count in project_docs.all():
            print(f"  {title}: {count} documents")


if __name__ == "__main__":
    asyncio.run(check_documents())
