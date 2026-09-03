"""
Attaching files to a batch.

Documents, base papers and submissions all arrive from two directions - the
team from the student portal, a guide from the faculty portal - and the rules
are the same from either. They live here for the reason `batch_actions` and
`project_details` do: a rule copied into two endpoints stops being one rule the
moment either is edited.

Authority is the caller's job. Every function assumes the caller has already
established this user may act on this batch.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging_config import logger
from app.models.batch_detail import ActivitySeverity, BatchDocument, DocumentStatus
from app.models.faculty import BasePaper, BasePaperStatus, ProjectBatch
from app.models.files import StoredFile
from app.models.user import User
from app.services import activity_log, file_store
from app.services.file_store import FileStoreError

# The vocabulary the Documents tab already files things under. Taken from the
# existing data rather than invented alongside it: a second list would put half
# the uploads in categories no screen filters by, and the two would drift.
CATEGORIES = [
    # Registration paperwork
    "Student Declaration",
    "Team Document",
    "Faculty Document",
    "Compliance",
    "Base Paper",
    # The project itself, in the order a project produces them
    "Synopsis",
    "Requirements (SRS)",
    "Design Document",
    "Implementation",
    "Testing",
    "User Manual",
    "Presentation",
    "Final Report",
    "Project Document",
    # Anything that fits nowhere above
    "Supporting Document",
    "Other",
]

# Categories that hold one live document, where a second upload is a new
# version of the same thing. Everything else is a folder: two files under
# "Other" are two files, and superseding one with the other would quietly
# hide a document somebody meant to keep.
VERSIONED = {
    "Student Declaration",
    "Team Document",
    "Faculty Document",
    "Compliance",
    "Base Paper",
    "Synopsis",
    "Requirements (SRS)",
    "Design Document",
    "Implementation",
    "Testing",
    "User Manual",
    "Presentation",
    "Final Report",
    "Project Document",
}

# Whether a document is required is a property of the document, not of its
# category - "Compliance" holds both an Ethics Approval that is required and a
# Similarity Report that is not. `BatchDocument.is_required` already records
# this and the checklist already reads it, so nothing new is needed here.


class BatchFileError(Exception):
    """A refusal the caller can show the user as-is."""


def _next_version(previous: Optional[BatchDocument]) -> str:
    """v1.0, then v1.1, v1.2 - minor bumps, because a re-upload is a revision."""
    if previous is None:
        return "v1.0"
    raw = (previous.version or "v1.0").lstrip("vV")
    try:
        major, minor = raw.split(".")[:2]
        return f"v{int(major)}.{int(minor) + 1}"
    except (ValueError, IndexError):
        return "v1.1"


async def load_batch_documents(db: AsyncSession, batch_id) -> List[BatchDocument]:
    return list((await db.execute(
        select(BatchDocument)
        .where(BatchDocument.batch_id == batch_id)
        .options(selectinload(BatchDocument.file), selectinload(BatchDocument.uploaded_by))
        .order_by(BatchDocument.uploaded_at.desc())
    )).scalars().all())


# --------------------------------------------------------------- documents

async def upload_document(
    db: AsyncSession,
    batch: ProjectBatch,
    upload: UploadFile,
    user: Optional[User],
    *,
    name: Optional[str] = None,
    category: str = "Project Document",
    actor_role: Optional[str] = None,
    source: str = "Web",
) -> dict:
    """
    Store a file and record it as a document of this batch.

    Re-uploading a category that already exists supersedes the old row rather
    than overwriting it: a verified document is evidence of what a guide
    approved, and history that can be edited is not history. The superseded row
    keeps its file, so an earlier version stays downloadable.
    """
    if category not in CATEGORIES:
        raise BatchFileError("Unknown document category: " + category)

    try:
        stored = await file_store.save(db, upload, user)
    except FileStoreError as exc:
        raise BatchFileError(str(exc))

    existing = (await db.execute(
        select(BatchDocument)
        .where(BatchDocument.batch_id == batch.id)
        .where(BatchDocument.category == category)
        .where(BatchDocument.superseded_by_id.is_(None))
        .order_by(BatchDocument.uploaded_at.desc())
    )).scalars().first() if category in VERSIONED else None

    # A "Missing" placeholder is a slot waiting to be filled, not a version to
    # supersede: filling it in is the first upload, so it stays v1.0.
    placeholder = existing if existing is not None and existing.status == DocumentStatus.MISSING else None
    previous = existing if (existing is not None and placeholder is None) else None

    # A brand-new document is not required unless someone says so; filling a
    # MISSING placeholder keeps whatever that slot was already marked as.
    document = placeholder or BatchDocument(
        batch_id=batch.id,
        category=category,
        is_required=False,
    )
    document.name = file_store.safe_name(name or file_store.upload_name(stored))
    document.version = _next_version(previous)
    document.file_id = stored.id
    document.file_size = stored.byte_size
    document.mime_type = stored.mime_type
    document.page_count = stored.page_count
    document.status = DocumentStatus.AWAITING_VERIFICATION
    document.uploaded_by_id = user.id if user else None
    document.uploaded_at = datetime.utcnow()
    # A new upload is not yet verified, and must not inherit the last
    # version's verification.
    document.verified_by_id = None
    document.verified_at = None
    document.superseded_by_id = None

    if placeholder is None:
        db.add(document)
    await db.flush()

    if previous is not None:
        previous.superseded_by_id = document.id

    await activity_log.record(
        db,
        batch_id=batch.id,
        activity=f"Uploaded {document.name} {document.version}",
        module="Documents",
        actor=user,
        actor_role=actor_role,
        details=(f"Replaced version {previous.version}" if previous
                 else f"{category}, {file_store.human_size(stored.byte_size)}"),
        status_label="Uploaded",
        severity=ActivitySeverity.INFO,
        source=source,
    )
    await db.commit()
    await db.refresh(document)

    logger.info(f"[Files] {getattr(user, 'email', 'system')} uploaded "
                f"{document.name} {document.version} to {batch.batch_code}")
    return {
        "id": str(document.id),
        "name": document.name,
        "category": document.category,
        "version": document.version,
        "status": document.status.value,
        "replaced_version": previous.version if previous else None,
        "file": file_store.describe(stored),
        "message": (f"Uploaded as {document.version}, replacing {previous.version}."
                    if previous else f"Uploaded as {document.version}."),
    }


async def document_for_download(
    db: AsyncSession, batch: ProjectBatch, document_id: str
) -> tuple:
    """
    Resolve a document of THIS batch and its bytes.

    Scoped to the batch on purpose: taking the id alone would let anyone who
    can read one batch fetch a document belonging to another just by changing
    the id in the URL.
    """
    document = (await db.execute(
        select(BatchDocument)
        .where(BatchDocument.id == document_id)
        .where(BatchDocument.batch_id == batch.id)
        .options(selectinload(BatchDocument.file))
    )).scalar_one_or_none()
    if document is None:
        raise BatchFileError("That document is not part of this batch.")
    if document.file is None:
        raise BatchFileError("No file has been uploaded for this document yet.")
    try:
        content = await file_store.read(document.file)
    except FileStoreError as exc:
        raise BatchFileError(str(exc))
    return document, content


async def delete_document(
    db: AsyncSession, batch: ProjectBatch, document_id: str, user: Optional[User],
    *, actor_role: Optional[str] = None, source: str = "Web",
) -> dict:
    """
    Remove a document that has not been verified.

    A verified document stays: it is what an approval was granted against.
    Correcting one means uploading a new version, which supersedes it.
    The stored blob is left alone - another version or another batch may hold
    the identical file.
    """
    document = (await db.execute(
        select(BatchDocument)
        .where(BatchDocument.id == document_id)
        .where(BatchDocument.batch_id == batch.id)
    )).scalar_one_or_none()
    if document is None:
        raise BatchFileError("That document is not part of this batch.")
    if document.status == DocumentStatus.VERIFIED:
        raise BatchFileError(
            "A verified document cannot be removed. Upload a new version instead.")
    if document.superseded_by_id is not None:
        raise BatchFileError("That version has already been replaced.")

    name, version = document.name, document.version
    # Whatever this superseded becomes current again, so the category is not
    # left with nothing after removing its newest version.
    restored = (await db.execute(
        select(BatchDocument).where(BatchDocument.superseded_by_id == document.id)
    )).scalars().first()
    if restored is not None:
        restored.superseded_by_id = None

    await db.delete(document)
    await activity_log.record(
        db,
        batch_id=batch.id,
        activity=f"Removed {name} {version}",
        module="Documents",
        actor=user,
        actor_role=actor_role,
        details=(f"Version {restored.version} is current again" if restored
                 else "No file remains for this document"),
        status_label="Removed",
        severity=ActivitySeverity.WARNING,
        source=source,
    )
    await db.commit()
    return {
        "removed": str(document_id),
        "restored_version": restored.version if restored else None,
        "message": (f"Removed {version}. {restored.version} is current again."
                    if restored else f"Removed {version}."),
    }


# -------------------------------------------------------------- base paper

async def upload_base_paper(
    db: AsyncSession,
    batch: ProjectBatch,
    upload: UploadFile,
    user: Optional[User],
    *,
    title: Optional[str] = None,
    actor_role: Optional[str] = None,
    source: str = "Web",
) -> dict:
    """
    Attach the primary paper's PDF.

    Replacing the file resets verification: a guide verified a specific paper,
    and a different one has not been looked at.
    """
    try:
        stored = await file_store.save(db, upload, user)
    except FileStoreError as exc:
        raise BatchFileError(str(exc))
    if stored.mime_type != "application/pdf":
        raise BatchFileError("A base paper has to be a PDF.")

    paper = (await db.execute(
        select(BasePaper).where(BasePaper.batch_id == batch.id)
    )).scalar_one_or_none()
    replaced = paper is not None and paper.file_id is not None

    if paper is None:
        paper = BasePaper(batch_id=batch.id)
        db.add(paper)

    if title and title.strip():
        paper.title = title.strip()[:500]
    paper.file_id = stored.id
    paper.file_name = file_store.upload_name(stored)
    paper.file_size = stored.byte_size
    paper.page_count = stored.page_count
    paper.uploaded_by_id = user.id if user else None
    paper.uploaded_at = datetime.utcnow()
    paper.status = BasePaperStatus.PENDING
    paper.verified_by_id = None
    paper.verified_at = None

    await db.flush()
    await activity_log.record(
        db,
        batch_id=batch.id,
        activity=("Replaced base paper PDF" if replaced else "Uploaded base paper PDF"),
        module="Base Papers",
        actor=user,
        actor_role=actor_role,
        details=f"{file_store.upload_name(stored)}, {file_store.human_size(stored.byte_size)}"
                + (f", {stored.page_count} pages" if stored.page_count else ""),
        status_label="Awaiting Verification",
        severity=ActivitySeverity.INFO,
        source=source,
    )
    await db.commit()

    return {
        "status": paper.status.value,
        "replaced": replaced,
        "file": file_store.describe(stored),
        "message": ("Replaced. Your guide has to verify the new paper."
                    if replaced else "Uploaded. Your guide will verify it."),
    }


async def base_paper_for_download(db: AsyncSession, batch: ProjectBatch) -> tuple:
    paper = (await db.execute(
        select(BasePaper)
        .where(BasePaper.batch_id == batch.id)
        .options(selectinload(BasePaper.file))
    )).scalar_one_or_none()
    if paper is None or paper.file is None:
        raise BatchFileError("No base paper PDF has been uploaded for this batch.")
    try:
        content = await file_store.read(paper.file)
    except FileStoreError as exc:
        raise BatchFileError(str(exc))
    return paper, content


def outstanding(documents: List[BatchDocument]) -> List[str]:
    """
    Required documents with nothing behind them.

    Read off `is_required` and the absence of a file, so a placeholder row that
    a coordinator marked required is listed by its own name rather than by a
    category guess.
    """
    return sorted(
        d.name for d in documents
        if d.is_required and d.file_id is None and d.superseded_by_id is None
    )


def options() -> dict:
    """What the upload controls may offer."""
    return {
        "categories": CATEGORIES,
        "limits": file_store.limits(),
    }
