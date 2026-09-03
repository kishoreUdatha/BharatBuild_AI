"""
Decisions a batch's owner can record, shared by the faculty and trainer portals.

Both portals write to the same rows. The rules live here rather than in either
endpoint so the two cannot drift apart - a document that is locked in one place
must be locked in the other, and the moment that logic is copied it stops being
true.

Authority is the caller's job. Every function here assumes the caller has
already established the user may manage this batch.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_detail import ActivitySeverity, BatchDocument, DocumentStatus
from app.models.faculty import (
    BasePaperStatus,
    ProjectBatch,
    ProjectReview,
    ReviewStatus,
)
from app.services import activity_log
from app.models.user import User

MAX_SCORE = 100


class ActionError(Exception):
    """A refusal the caller can show the user as-is."""


# ------------------------------------------------------------------ documents

async def decide_document(
    db: AsyncSession,
    batch: ProjectBatch,
    document_id: str,
    decision: str,
    user: User,
    *,
    note: Optional[str] = None,
) -> dict:
    """
    Verify a document or send it back.

    A verified document is locked - correcting it means uploading a new
    version, which is why re-verifying one is refused rather than silently
    re-stamped.
    """
    doc = next((d for d in batch.documents if str(d.id) == str(document_id)), None)
    if doc is None:
        raise ActionError("That document is not part of this batch.")
    if doc.status == DocumentStatus.MISSING:
        raise ActionError("This document has not been uploaded yet.")

    if decision == "verify":
        if doc.status == DocumentStatus.VERIFIED:
            raise ActionError("Already verified; upload a new version to change it.")
        doc.status = DocumentStatus.VERIFIED
        doc.verified_by_id = user.id
        doc.verified_at = datetime.utcnow()
    elif decision == "request_changes":
        doc.status = DocumentStatus.CHANGES_REQUESTED
    else:
        raise ActionError("decision must be verify or request_changes.")

    if note is not None:
        doc.faculty_note = note.strip() or None
    await db.commit()
    return {"document_id": str(doc.id), "status": doc.status.value, "name": doc.name}


# ----------------------------------------------------------------- base paper

async def decide_base_paper(
    db: AsyncSession,
    batch: ProjectBatch,
    decision: str,
    user: User,
    *,
    note: Optional[str] = None,
) -> dict:
    """
    Verify the primary base paper, or send it back.

    Every screen reads this state - the approval checklist gates on it, the
    KPIs count it, the lifecycle strip draws it - but nothing could set it, so
    a batch registered through the app could never be approved. A paper is
    verified by a person reading it, which is why this is an action and not
    something the upload does for itself.
    """
    paper = batch.base_paper
    if paper is None or paper.status == BasePaperStatus.MISSING:
        raise ActionError("No base paper has been uploaded for this batch yet.")

    if decision == "verify":
        if paper.status == BasePaperStatus.VERIFIED:
            raise ActionError("This paper is already verified.")
        paper.status = BasePaperStatus.VERIFIED
        paper.verified_by_id = user.id
        paper.verified_at = datetime.utcnow()
    elif decision == "request_changes":
        if not (note or "").strip():
            raise ActionError("Say what is wrong with the paper before sending it back.")
        paper.status = BasePaperStatus.PENDING
        paper.verified_by_id = None
        paper.verified_at = None
    else:
        raise ActionError("decision must be verify or request_changes.")

    if note is not None:
        paper.faculty_note = note.strip() or None

    await activity_log.record(
        db,
        batch_id=batch.id,
        activity=("Verified the base paper" if decision == "verify"
                  else "Sent the base paper back"),
        module="Base Papers",
        actor=user,
        actor_role="Faculty",
        details=note or (paper.title or paper.file_name),
        status_label="Verified" if decision == "verify" else "Changes Requested",
        severity=(ActivitySeverity.SUCCESS if decision == "verify"
                  else ActivitySeverity.WARNING),
    )
    await db.commit()
    return {
        "status": paper.status.value,
        "verified_at": paper.verified_at,
        "message": ("Base paper verified." if decision == "verify"
                    else "Base paper sent back to the team."),
    }


# -------------------------------------------------------------------- reviews

def _review_of(batch: ProjectBatch, review_id: str) -> ProjectReview:
    review = next((r for r in batch.reviews if str(r.id) == str(review_id)), None)
    if review is None:
        raise ActionError("That review is not part of this batch.")
    return review


async def complete_review(
    db: AsyncSession,
    batch: ProjectBatch,
    review_id: str,
    user: User,
    *,
    score: Optional[float] = None,
    remarks: Optional[str] = None,
) -> dict:
    """
    Record that a review happened, with what came out of it.

    Only a scheduled review can be completed: re-completing one would overwrite
    the original outcome and the record of who signed it off.
    """
    review = _review_of(batch, review_id)
    if review.status == ReviewStatus.COMPLETED:
        raise ActionError(
            f"{review.review_type} was already completed on "
            f"{review.completed_at:%d %b %Y}." if review.completed_at
            else f"{review.review_type} was already completed."
        )
    if review.status == ReviewStatus.CANCELLED:
        raise ActionError("This review was cancelled. Schedule a new one instead.")

    if score is not None:
        if score < 0 or score > MAX_SCORE:
            raise ActionError(f"Score must be between 0 and {MAX_SCORE}.")
        review.score = float(score)
    if remarks is not None:
        review.remarks = remarks.strip() or None

    review.status = ReviewStatus.COMPLETED
    review.completed_at = datetime.utcnow()
    review.reviewer_id = user.id
    await db.commit()
    return {
        "review_id": str(review.id),
        "status": review.status.value,
        "review_type": review.review_type,
        "score": review.score,
    }


async def reschedule_review(
    db: AsyncSession, batch: ProjectBatch, review_id: str, when: datetime,
) -> dict:
    """Move a scheduled review. A completed one is history and stays put."""
    review = _review_of(batch, review_id)
    if review.status != ReviewStatus.SCHEDULED:
        raise ActionError(f"Only a scheduled review can be moved; this one is "
                          f"{review.status.value}.")
    if when <= datetime.utcnow():
        raise ActionError("Pick a date in the future.")
    review.scheduled_at = when
    await db.commit()
    return {"review_id": str(review.id), "scheduled_at": review.scheduled_at}


async def cancel_review(
    db: AsyncSession, batch: ProjectBatch, review_id: str, reason: str,
) -> dict:
    """
    Cancel a scheduled review.

    A reason is required: an unexplained cancellation on a student's record is
    worse than no record at all.
    """
    review = _review_of(batch, review_id)
    if review.status != ReviewStatus.SCHEDULED:
        raise ActionError(f"Only a scheduled review can be cancelled; this one is "
                          f"{review.status.value}.")
    if not (reason or "").strip():
        raise ActionError("Say why the review is being cancelled.")
    review.status = ReviewStatus.CANCELLED
    review.remarks = reason.strip()
    await db.commit()
    return {"review_id": str(review.id), "status": review.status.value}
