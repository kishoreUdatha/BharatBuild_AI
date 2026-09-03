"""
Stage deliverables: handing work in, and answering it.

Distinct from registration documents. A registration document proves the batch
is properly formed; a submission is the work itself - the SRS, the design, the
report - handed in against one of the eight tracked stages. Accepting one is
what moves that stage's progress, which is the only reason the tracking screens
have ever had numbers to show.

Both portals go through here, for the reason `batch_files` and `project_details`
do. Authority is the caller's job.
"""

from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging_config import logger
from app.models.batch_detail import ActivitySeverity
from app.models.faculty import (
    BatchStageProgress,
    ProjectBatch,
    ProjectStage,
    ProjectSubmission,
    STAGE_LABELS,
    STAGE_ORDER,
    SubmissionStatus,
)
from app.models.user import User
from app.services import activity_log, file_store
from app.services.file_store import FileStoreError

# What a batch is expected to hand in, and the stage each belongs to. Kept as
# one table so a screen listing the types and a submission recording a stage
# cannot disagree about which goes with which.
DELIVERABLES = [
    ("Synopsis", ProjectStage.TOPIC_APPROVAL),
    ("Literature Survey", ProjectStage.BASE_PAPER),
    ("SRS", ProjectStage.REQUIREMENTS),
    ("System Design", ProjectStage.SYSTEM_DESIGN),
    ("Source Code", ProjectStage.DEVELOPMENT),
    ("Test Report", ProjectStage.TESTING),
    ("Project Report", ProjectStage.DOCUMENTATION),
    ("Presentation", ProjectStage.FINAL_REVIEW),
]

STAGE_FOR_TYPE = {name: stage for name, stage in DELIVERABLES}

# A link is accepted instead of a file when the work genuinely lives elsewhere -
# a repository, a shared drive. Only these schemes: anything else is either not
# fetchable or is a way to smuggle a script past the upload allowlist.
ALLOWED_SCHEMES = {"http", "https"}

MAX_NOTE = 2000


class SubmissionError(Exception):
    """A refusal the caller can show the user as-is."""


def _next_version(previous: Optional[ProjectSubmission]) -> str:
    if previous is None:
        return "v1.0"
    raw = (previous.version or "v1.0").lstrip("vV")
    try:
        major, minor = raw.split(".")[:2]
        return f"v{int(major)}.{int(minor) + 1}"
    except (ValueError, IndexError):
        return "v1.1"


def _clean_url(raw: Optional[str]) -> Optional[str]:
    if not raw or not raw.strip():
        return None
    value = raw.strip()
    parsed = urlparse(value)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES or not parsed.netloc:
        raise SubmissionError("A link has to be a full http or https address.")
    if len(value) > 2000:
        raise SubmissionError("That link is too long.")
    return value


async def load(db: AsyncSession, batch_id) -> List[ProjectSubmission]:
    return list((await db.execute(
        select(ProjectSubmission)
        .where(ProjectSubmission.batch_id == batch_id)
        .options(
            selectinload(ProjectSubmission.file),
            selectinload(ProjectSubmission.submitted_by),
            selectinload(ProjectSubmission.reviewed_by),
        )
        .order_by(ProjectSubmission.submitted_at.desc())
    )).scalars().all())


def row(submission: ProjectSubmission, *, can_manage: bool = False) -> dict:
    stage = submission.stage
    return {
        "id": str(submission.id),
        "document_type": submission.document_type,
        "title": submission.title,
        "stage": stage.value if stage else None,
        "stage_label": STAGE_LABELS.get(stage) if stage else None,
        "version": submission.version,
        "status": submission.status.value,
        "status_label": submission.status.value.title(),
        "submitted_by": (submission.submitted_by.full_name
                         if submission.submitted_by else None),
        "submitted_at": submission.submitted_at,
        "reviewed_by": (submission.reviewed_by.full_name
                        if submission.reviewed_by else None),
        "reviewed_at": submission.reviewed_at,
        "faculty_note": submission.faculty_note,
        "superseded": submission.superseded_by_id is not None,
        "file": file_store.describe(submission.file),
        "link": submission.file_url,
        # A pending submission can be taken back by the team; once it has been
        # judged, withdrawing it would erase the judgement.
        "can_withdraw": (submission.status == SubmissionStatus.PENDING
                         and submission.superseded_by_id is None),
        "can_decide": (can_manage
                       and submission.status == SubmissionStatus.PENDING
                       and submission.superseded_by_id is None),
    }


def options(submissions: List[ProjectSubmission]) -> dict:
    """
    What may be submitted, and where each type currently stands.

    Reported per deliverable rather than as a flat list so a team can see the
    eight things expected of them and which are still outstanding.
    """
    current = {}
    for s in submissions:
        if s.superseded_by_id is None:
            current.setdefault(s.document_type, s)

    return {
        "deliverables": [
            {
                "document_type": name,
                "stage": stage.value,
                "stage_label": STAGE_LABELS[stage],
                "position": STAGE_ORDER.index(stage) + 1,
                "status": (current[name].status.value if name in current else "not_submitted"),
                "version": (current[name].version if name in current else None),
            }
            for name, stage in DELIVERABLES
        ],
        "limits": file_store.limits(),
    }


# ------------------------------------------------------------------- submit

async def submit(
    db: AsyncSession,
    batch: ProjectBatch,
    user: Optional[User],
    *,
    document_type: str,
    upload: Optional[UploadFile] = None,
    link: Optional[str] = None,
    title: Optional[str] = None,
    actor_role: Optional[str] = None,
    source: str = "Web",
) -> dict:
    """
    Hand in a deliverable, as a file or as a link.

    Resubmitting supersedes the previous attempt rather than replacing it: what
    was rejected, and the reason given, is what the team is working from.
    """
    if document_type not in STAGE_FOR_TYPE:
        raise SubmissionError(
            "Unknown deliverable. Expected one of: "
            + ", ".join(name for name, _ in DELIVERABLES) + ".")

    cleaned_link = _clean_url(link)
    has_upload = upload is not None and (upload.filename or "").strip()
    if not has_upload and not cleaned_link:
        raise SubmissionError("Attach a file or give a link to the work.")
    if has_upload and cleaned_link:
        raise SubmissionError("Give either a file or a link, not both.")

    stored = None
    if has_upload:
        try:
            stored = await file_store.save(db, upload, user)
        except FileStoreError as exc:
            raise SubmissionError(str(exc))

    previous = (await db.execute(
        select(ProjectSubmission)
        .where(ProjectSubmission.batch_id == batch.id)
        .where(ProjectSubmission.document_type == document_type)
        .where(ProjectSubmission.superseded_by_id.is_(None))
        .order_by(ProjectSubmission.submitted_at.desc())
    )).scalars().first()

    if previous is not None and previous.status == SubmissionStatus.VERIFIED:
        raise SubmissionError(
            f"Your {document_type} has already been accepted. "
            "Ask your guide to reopen it if it needs to change.")

    submission = ProjectSubmission(
        batch_id=batch.id,
        document_type=document_type,
        stage=STAGE_FOR_TYPE[document_type],
        title=(title or "").strip()[:500] or (
            file_store.upload_name(stored) if stored else document_type),
        file_id=stored.id if stored else None,
        file_url=cleaned_link,
        version=_next_version(previous),
        status=SubmissionStatus.PENDING,
        submitted_by_id=user.id if user else None,
        submitted_at=datetime.utcnow(),
    )
    db.add(submission)
    await db.flush()

    if previous is not None:
        previous.superseded_by_id = submission.id

    await activity_log.record(
        db,
        batch_id=batch.id,
        activity=f"Submitted {document_type} {submission.version}",
        module="Documents",
        actor=user,
        actor_role=actor_role,
        details=(f"Replaces {previous.version}" if previous
                 else (file_store.human_size(stored.byte_size) if stored else "Link submission")),
        status_label="Submitted",
        severity=ActivitySeverity.INFO,
        source=source,
    )
    await db.commit()
    submission = await _of_batch(db, batch, str(submission.id))

    logger.info(f"[Submissions] {getattr(user, 'email', 'system')} submitted "
                f"{document_type} {submission.version} for {batch.batch_code}")
    return {
        **row(submission),
        "replaced_version": previous.version if previous else None,
        "message": (f"Submitted as {submission.version}, replacing {previous.version}."
                    if previous else f"Submitted as {submission.version}."),
    }


async def withdraw(
    db: AsyncSession, batch: ProjectBatch, submission_id: str, user: Optional[User],
    *, actor_role: Optional[str] = None, source: str = "Web",
) -> dict:
    """Take back a submission a guide has not judged yet."""
    submission = await _of_batch(db, batch, submission_id)
    if submission.status != SubmissionStatus.PENDING:
        raise SubmissionError(
            "That submission has already been reviewed and cannot be taken back.")
    if submission.superseded_by_id is not None:
        raise SubmissionError("That attempt has already been replaced.")

    restored = (await db.execute(
        select(ProjectSubmission)
        .where(ProjectSubmission.superseded_by_id == submission.id)
    )).scalars().first()
    if restored is not None:
        restored.superseded_by_id = None

    label, version = submission.document_type, submission.version
    await db.delete(submission)
    await activity_log.record(
        db,
        batch_id=batch.id,
        activity=f"Withdrew {label} {version}",
        module="Documents",
        actor=user,
        actor_role=actor_role,
        details=(f"{restored.version} stands again" if restored else "Nothing submitted now"),
        status_label="Withdrawn",
        severity=ActivitySeverity.WARNING,
        source=source,
    )
    await db.commit()
    return {
        "withdrawn": str(submission_id),
        "restored_version": restored.version if restored else None,
        "message": (f"Withdrew {version}. {restored.version} stands again."
                    if restored else f"Withdrew {version}."),
    }


# ------------------------------------------------------------------- decide

async def decide(
    db: AsyncSession,
    batch: ProjectBatch,
    submission_id: str,
    decision: str,
    user: Optional[User],
    *,
    note: Optional[str] = None,
    actor_role: str = "Faculty",
    source: str = "Web",
) -> dict:
    """
    Accept a deliverable or send it back.

    Rejecting requires a reason. A verdict with no reason gives the team
    nothing to act on, and they cannot ask the system what was wrong.
    Accepting completes the stage the deliverable belongs to.
    """
    submission = await _of_batch(db, batch, submission_id)
    if submission.superseded_by_id is not None:
        raise SubmissionError("That attempt has been replaced by a newer one.")
    if submission.status != SubmissionStatus.PENDING:
        raise SubmissionError(
            f"That submission was already {submission.status.value}.")

    cleaned = (note or "").strip()[:MAX_NOTE] or None
    if decision == "verify":
        submission.status = SubmissionStatus.VERIFIED
    elif decision == "reject":
        if not cleaned:
            raise SubmissionError("Say what needs to change before sending this back.")
        submission.status = SubmissionStatus.REJECTED
    else:
        raise SubmissionError("decision must be verify or reject.")

    submission.faculty_note = cleaned
    submission.reviewed_by_id = user.id if user else None
    submission.reviewed_at = datetime.utcnow()

    stage_result = None
    if submission.status == SubmissionStatus.VERIFIED and submission.stage is not None:
        stage_result = await _complete_stage(db, batch, submission.stage)

    await activity_log.record(
        db,
        batch_id=batch.id,
        activity=("Accepted " if decision == "verify" else "Sent back ")
                 + f"{submission.document_type} {submission.version}",
        module="Documents",
        actor=user,
        actor_role=actor_role,
        details=cleaned or (f"{STAGE_LABELS.get(submission.stage, '')} stage completed"
                            if stage_result else None),
        status_label="Verified" if decision == "verify" else "Rejected",
        severity=(ActivitySeverity.SUCCESS if decision == "verify"
                  else ActivitySeverity.WARNING),
        source=source,
    )
    await db.commit()
    submission = await _of_batch(db, batch, submission_id)

    return {
        **row(submission),
        "stage_completed": stage_result,
        "overall_progress": int(round(batch.overall_progress or 0)),
        "message": (
            f"{submission.document_type} accepted."
            + (f" {STAGE_LABELS[submission.stage]} is now complete." if stage_result else "")
            if decision == "verify"
            else f"{submission.document_type} sent back to the team."),
    }


async def _complete_stage(db: AsyncSession, batch: ProjectBatch,
                          stage: ProjectStage) -> Optional[str]:
    """
    Mark a stage complete and recompute the cached roll-up.

    `overall_progress` is a cache the list views read instead of aggregating
    per row, so it has to be rewritten here or the tracking screens would keep
    showing the number from before the deliverable was accepted.
    """
    rows = (await db.execute(
        select(BatchStageProgress).where(BatchStageProgress.batch_id == batch.id)
    )).scalars().all()
    by_stage = {r.stage: r for r in rows}

    record = by_stage.get(stage)
    if record is None:
        record = BatchStageProgress(batch_id=batch.id, stage=stage)
        db.add(record)
        by_stage[stage] = record
    already = (record.percent or 0) >= 100
    record.percent = 100.0
    record.completed_at = record.completed_at or datetime.utcnow()

    await db.flush()
    total = sum((by_stage[s].percent or 0) if s in by_stage else 0 for s in STAGE_ORDER)
    batch.overall_progress = round(total / len(STAGE_ORDER), 2)
    return None if already else STAGE_LABELS[stage]


# ----------------------------------------------------------------- download

async def for_download(db: AsyncSession, batch: ProjectBatch, submission_id: str) -> tuple:
    submission = await _of_batch(db, batch, submission_id)
    if submission.file is None:
        raise SubmissionError(
            "That submission is a link, not a file." if submission.file_url
            else "No file was attached to that submission.")
    try:
        content = await file_store.read(submission.file)
    except FileStoreError as exc:
        raise SubmissionError(str(exc))
    return submission, content


async def _of_batch(db: AsyncSession, batch: ProjectBatch,
                    submission_id: str) -> ProjectSubmission:
    """
    Resolve a submission of THIS batch, with everything `row` reads.

    Scoped to the batch so changing an id in a URL cannot reach another team's
    work. Loaded eagerly because reading a relationship lazily inside async
    raises rather than fetching, and `row` touches three of them.
    """
    submission = (await db.execute(
        select(ProjectSubmission)
        .where(ProjectSubmission.id == submission_id)
        .where(ProjectSubmission.batch_id == batch.id)
        .options(
            selectinload(ProjectSubmission.file),
            selectinload(ProjectSubmission.submitted_by),
            selectinload(ProjectSubmission.reviewed_by),
        )
    )).scalar_one_or_none()
    if submission is None:
        raise SubmissionError("That submission is not part of this batch.")
    return submission
