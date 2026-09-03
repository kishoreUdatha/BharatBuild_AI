"""
How far along a batch *ought* to be today.

The tracking screen used to call a batch "behind schedule" whenever its
progress sat under a fixed fifty percent. That is not a schedule - it takes
no account of where the cohort is in its own cycle. In the first month of a
six month project every batch is legitimately near zero and all of them would
be flagged; in the final month a batch at sixty percent is in real trouble and
would be reported as on track. On the current cohort the fixed line fired for
none of the forty-five batches, so the warning it promised was never delivered.

This derives the expectation from the batch's own dates instead, and both the
dashboard and the tracking screen read it from here so the two cannot drift
apart.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from app.core.institution_time import local_today

# How far a batch may sit under the line before anyone is told about it.
# Straight-line expectation is a model, not a timetable: work lands in bursts
# around review dates, so a batch a few points down is ordinary. Ten points is
# roughly a fortnight's drift on a six month cycle.
SCHEDULE_GRACE = 10.0

AHEAD = "ahead"
ON_TRACK = "on_track"
BEHIND = "behind"
UNKNOWN = "unknown"


def expected_progress(
    start_date: Optional[date],
    target_completion: Optional[date],
    today: Optional[date] = None,
) -> Optional[float]:
    """
    The percentage a batch should have reached by today, or None when its
    dates cannot say.

    Returning None matters: a batch with no schedule must not be accused of
    falling behind one. Callers treat None as "no opinion", not as zero.
    """
    if start_date is None or target_completion is None:
        return None
    if target_completion <= start_date:
        # Bad data - a cycle that ends before it begins tells us nothing.
        return None

    today = today or local_today()
    if today <= start_date:
        return 0.0
    if today >= target_completion:
        return 100.0

    elapsed = (today - start_date).days
    span = (target_completion - start_date).days
    return round(100.0 * elapsed / span, 2)


def schedule_state(actual: Optional[float], expected: Optional[float]) -> str:
    """Where a batch stands against its own timeline."""
    if expected is None:
        return UNKNOWN
    actual = actual or 0.0
    if actual < expected - SCHEDULE_GRACE:
        return BEHIND
    if actual > expected + SCHEDULE_GRACE:
        return AHEAD
    return ON_TRACK


def is_behind(actual: Optional[float], expected: Optional[float]) -> bool:
    """True only when the schedule is known and the batch is short of it."""
    return schedule_state(actual, expected) == BEHIND


def days_remaining(
    target_completion: Optional[date], today: Optional[date] = None
) -> Optional[int]:
    """Days left until the batch is due. Negative once the date has passed."""
    if target_completion is None:
        return None
    return (target_completion - (today or local_today())).days


def describe(actual: Optional[float], expected: Optional[float]) -> str:
    """A short phrase for a faculty-facing list."""
    state = schedule_state(actual, expected)
    if state == UNKNOWN:
        return "No schedule set"
    gap = round((actual or 0.0) - (expected or 0.0))
    if state == BEHIND:
        return f"{abs(gap)}% behind schedule"
    if state == AHEAD:
        return f"{gap}% ahead of schedule"
    return "On schedule"
