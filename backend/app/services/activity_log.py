"""
Writing the audit trail.

The Activity Log tab states these rows are retained for audit, and the Project
Details tab reads them for its revision history - but until now only the seeder
ever wrote one, so a real edit left no trace and both panels showed nothing but
demo data. Every mutation that changes what a batch has declared should call
`record`.

Rows are append-only by convention: nothing here updates or deletes.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_detail import ActivityLog, ActivitySeverity
from app.models.user import User, UserRole

# The modules the Activity Log tab groups by. Anything outside this set still
# writes, but will not be found by the panels that filter on a known module.
MODULES = {"Registration", "Team", "Approval", "Documents", "Base Papers"}


def actor_role_of(user: Optional[User], *, is_lead: bool = False) -> str:
    if user is None:
        return "System"
    if user.role == UserRole.FACULTY:
        return "Faculty"
    if user.role == UserRole.TRAINER:
        return "Trainer"
    if user.role == UserRole.ADMIN:
        return "Coordinator"
    return "Batch Leader" if is_lead else "Student"


async def _next_event_code(db: AsyncSession) -> str:
    """
    Next ACT-<year>-#### for this calendar year.

    Derived from the highest code already issued rather than a row count, so a
    deleted batch's cascade cannot make the sequence hand out a code twice.
    """
    year = datetime.utcnow().year
    prefix = f"ACT-{year}-"
    highest = (await db.execute(
        select(func.max(ActivityLog.event_code)).where(ActivityLog.event_code.like(f"{prefix}%"))
    )).scalar()
    seq = 1
    if highest:
        try:
            seq = int(highest.rsplit("-", 1)[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    return f"{prefix}{seq:04d}"


async def record(
    db: AsyncSession,
    *,
    batch_id,
    activity: str,
    module: str,
    actor: Optional[User] = None,
    actor_role: Optional[str] = None,
    details: Optional[str] = None,
    status_label: Optional[str] = None,
    severity: ActivitySeverity = ActivitySeverity.INFO,
    changed_field: Optional[str] = None,
    previous_value: Optional[str] = None,
    current_value: Optional[str] = None,
    source: str = "Web",
    commit: bool = False,
) -> ActivityLog:
    """
    Append one audit row.

    Does not commit by default: an audit entry belongs to the same transaction
    as the change it describes, so a failed write cannot leave a log claiming
    something happened.
    """
    row = ActivityLog(
        event_code=await _next_event_code(db),
        batch_id=batch_id,
        actor_id=(actor.id if actor else None),
        actor_name=(actor.full_name or actor.email.split("@")[0]) if actor else "System",
        actor_role=actor_role or actor_role_of(actor),
        activity=activity[:255],
        module=module,
        details=details,
        status_label=status_label,
        severity=severity,
        changed_field=changed_field,
        previous_value=_short(previous_value),
        current_value=_short(current_value),
        source=source,
        occurred_at=datetime.utcnow(),
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError:
        # Two writers took the same number. Roll the savepoint back far enough
        # to try once more rather than lose the caller's change.
        await db.rollback()
        raise
    if commit:
        await db.commit()
    return row


def _short(value: Optional[str], limit: int = 255) -> Optional[str]:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text[: limit - 1] + "\u2026" if len(text) > limit else text
