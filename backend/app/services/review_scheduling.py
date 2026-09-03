"""
Scheduling reviews.

The portal could complete, move and cancel a review, but nothing could create
one - so every review on every screen came from the seeder, and a real
deployment would have had an empty calendar with no way to fill it.

Reviews are scheduled a round at a time. A coordinator does not book one batch;
they book "Progress Review for every CSE 4th-year Section A batch, Tuesday from
10:00, twenty minutes each". Doing that one batch at a time is what sends
people back to a spreadsheet, so the round is the primary operation here and
the single booking is the special case.

Times arrive as local wall clock and are stored as naive UTC, which is what the
rest of the codebase assumes. Nothing here compares a local time to a stored
one without converting first.
"""

from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.institution_time import (
    combine_local,
    humanise,
    local_today,
    parse_local_date,
    parse_local_time,
    to_utc,
    utc_now,
)
from app.core.logging_config import logger
from app.models.faculty import (
    ProjectBatch,
    ProjectReview,
    ReviewStatus,
)
from app.models.user import User, UserRole, COLLEGE_STAFF_ROLES

# The reviews a project passes through. Matches what the seeder has always
# used, so scheduled rounds and existing history share one vocabulary.
REVIEW_TYPES = [
    "Progress Review",
    "Design Review",
    "Testing Review",
    "Final Review",
]

DEFAULT_SLOT_MINUTES = 20
MIN_SLOT_MINUTES = 5
MAX_SLOT_MINUTES = 240
MAX_ROUND = 60

# How far ahead a round may be booked. Not a rule about academia - a guard so a
# typo in a year cannot fill the calendar for a decade.
MAX_AHEAD_DAYS = 365


class SchedulingError(Exception):
    """A refusal the caller can show the user as-is."""


def _clean_type(raw: Optional[str]) -> str:
    value = (raw or "").strip()
    if value not in REVIEW_TYPES:
        raise SchedulingError(
            "Review type must be one of " + ", ".join(REVIEW_TYPES) + ".")
    return value


def parse_when(day: str, at: str) -> datetime:
    """A local date and time, as the naive UTC that gets stored."""
    try:
        on = parse_local_date(day)
        start = parse_local_time(at)
    except ValueError as exc:
        raise SchedulingError(str(exc))

    when = combine_local(on, start)
    if when <= utc_now():
        raise SchedulingError("Pick a time in the future.")
    if (on - local_today()).days > MAX_AHEAD_DAYS:
        raise SchedulingError(f"That is more than {MAX_AHEAD_DAYS} days away.")
    return when


class ReviewScheduler:
    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        # Reviews are reached through their batch, so this is applied to the
        # batch join rather than to the review row.
        self.college_id = college_id

    def _mine(self, stmt):
        """Confine a batch query to the caller's college."""
        if self.college_id:
            return stmt.where(ProjectBatch.college_id == self.college_id)
        return stmt

    # ------------------------------------------------------------- options

    async def options(self, academic_year: str) -> dict:
        """Review types, who can take one, and the defaults a form starts from."""
        reviewers = (await self.db.execute(
            select(User).where(User.role.in_(COLLEGE_STAFF_ROLES)).order_by(User.full_name)
        )).scalars().all()
        return {
            "review_types": REVIEW_TYPES,
            "reviewers": [
                {"id": str(r.id), "name": r.full_name or r.email.split("@")[0]}
                for r in reviewers
            ],
            "defaults": {
                "slot_minutes": DEFAULT_SLOT_MINUTES,
                "start_time": "10:00",
            },
            "limits": {
                "max_batches": MAX_ROUND,
                "min_slot_minutes": MIN_SLOT_MINUTES,
                "max_slot_minutes": MAX_SLOT_MINUTES,
                "max_days_ahead": MAX_AHEAD_DAYS,
            },
            "academic_year": academic_year,
        }

    # ------------------------------------------------------------ conflicts

    async def _reviewer_clashes(
        self, reviewer_id: Optional[str], slots: List[tuple], ignore: Optional[str] = None,
    ) -> Dict[datetime, str]:
        """
        Slots where this reviewer is already booked.

        Two reviews overlap when one starts before the other ends. A reviewer
        cannot be in two rooms, so this refuses rather than warns.
        """
        if not reviewer_id or not slots:
            return {}
        earliest = min(start for start, _ in slots)
        latest = max(start + timedelta(minutes=minutes) for start, minutes in slots)

        stmt = (
            select(ProjectReview, ProjectBatch)
            .join(ProjectBatch, ProjectReview.batch_id == ProjectBatch.id)
            .where(ProjectReview.reviewer_id == reviewer_id)
            .where(ProjectReview.status == ReviewStatus.SCHEDULED)
            .where(ProjectReview.scheduled_at >= earliest - timedelta(minutes=MAX_SLOT_MINUTES))
            .where(ProjectReview.scheduled_at <= latest)
        )
        if ignore:
            stmt = stmt.where(ProjectReview.id != ignore)

        booked = (await self.db.execute(stmt)).all()
        clashes: Dict[datetime, str] = {}
        for start, minutes in slots:
            finish = start + timedelta(minutes=minutes)
            for review, batch in booked:
                other_end = review.scheduled_at + timedelta(
                    minutes=review.slot_minutes or DEFAULT_SLOT_MINUTES)
                if review.scheduled_at < finish and start < other_end:
                    clashes[start] = batch.batch_code
                    break
        return clashes

    # ------------------------------------------------------------- one batch

    async def schedule(
        self,
        user: User,
        batch: ProjectBatch,
        *,
        review_type: str,
        day: str,
        at: str,
        reviewer_id: Optional[str] = None,
        slot_minutes: int = DEFAULT_SLOT_MINUTES,
    ) -> dict:
        """Book one review for one batch."""
        kind = _clean_type(review_type)
        when = parse_when(day, at)
        minutes = self._clean_minutes(slot_minutes)
        reviewer = await self._reviewer(reviewer_id, batch)

        await self._refuse_duplicate(batch, kind)
        clashes = await self._reviewer_clashes(
            str(reviewer.id) if reviewer else None, [(when, minutes)])
        if clashes:
            raise SchedulingError(
                f"{reviewer.full_name} is already reviewing "
                f"{clashes[when]} at that time.")

        review = ProjectReview(
            batch_id=batch.id,
            review_type=kind,
            scheduled_at=when,
            slot_minutes=minutes,
            status=ReviewStatus.SCHEDULED,
            reviewer_id=reviewer.id if reviewer else None,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)

        logger.info(f"[Reviews] {user.email} scheduled {kind} for "
                    f"{batch.batch_code} at {when} UTC")
        return {
            **self.row(review, batch.batch_code, reviewer),
            "message": f"{kind} booked for {batch.batch_code} on {humanise(when)}.",
        }

    # ----------------------------------------------------------------- round

    async def schedule_round(
        self,
        user: User,
        *,
        department: str,
        year: Optional[str],
        section: Optional[str],
        academic_year: str,
        review_type: str,
        day: str,
        start_time: str,
        slot_minutes: int = DEFAULT_SLOT_MINUTES,
        reviewer_id: Optional[str] = None,
        batch_codes: Optional[List[str]] = None,
    ) -> dict:
        """
        Book a review for every batch in a cohort, back to back.

        Batches that already have this review scheduled are skipped rather than
        double-booked, and reported so the coordinator knows the round did not
        silently cover fewer teams than they expected.
        """
        kind = _clean_type(review_type)
        first = parse_when(day, start_time)
        minutes = self._clean_minutes(slot_minutes)

        batches = await self._cohort(department, year, section, academic_year, batch_codes)
        if not batches:
            where = " ".join(filter(None, [
                department, year, (f"section {section}" if section else None)]))
            raise SchedulingError(f"No active batches in {where} for {academic_year}.")
        if len(batches) > MAX_ROUND:
            raise SchedulingError(
                f"That is {len(batches)} batches. Book at most {MAX_ROUND} in one round.")

        reviewer = await self._reviewer(reviewer_id, batches[0])

        already = {
            str(r.batch_id) for r in (await self.db.execute(
                select(ProjectReview)
                .where(ProjectReview.batch_id.in_([b.id for b in batches]))
                .where(ProjectReview.review_type == kind)
                .where(ProjectReview.status == ReviewStatus.SCHEDULED)
            )).scalars().all()
        }

        to_book = [b for b in batches if str(b.id) not in already]
        skipped = [b.batch_code for b in batches if str(b.id) in already]
        if not to_book:
            raise SchedulingError(
                f"Every batch in that cohort already has a {kind} scheduled.")

        slots = [(first + timedelta(minutes=minutes * i), minutes)
                 for i in range(len(to_book))]
        clashes = await self._reviewer_clashes(
            str(reviewer.id) if reviewer else None, slots)
        if clashes:
            when, other = sorted(clashes.items())[0]
            raise SchedulingError(
                f"{reviewer.full_name} is already reviewing {other} at "
                f"{humanise(when)}. Pick another time, slot length or reviewer.")

        created = []
        for batch, (when, _) in zip(to_book, slots):
            review = ProjectReview(
                batch_id=batch.id,
                review_type=kind,
                scheduled_at=when,
                slot_minutes=minutes,
                status=ReviewStatus.SCHEDULED,
                reviewer_id=reviewer.id if reviewer else None,
            )
            self.db.add(review)
            created.append((review, batch))
        await self.db.commit()

        logger.info(f"[Reviews] {user.email} scheduled a {kind} round: "
                    f"{len(created)} booked, {len(skipped)} skipped")
        last = slots[-1][0] + timedelta(minutes=minutes)
        return {
            "created": [
                self.row(review, batch.batch_code, reviewer) for review, batch in created
            ],
            "count": len(created),
            "skipped": skipped,
            "review_type": kind,
            "reviewer": reviewer.full_name if reviewer else None,
            "slot_minutes": minutes,
            "starts_at": first,
            "ends_at": last,
            "message": (
                f"{len(created)} {kind}s booked, {humanise(first)} to {humanise(last)}."
                + (f" {len(skipped)} skipped - already scheduled." if skipped else "")
            ),
        }

    # ------------------------------------------------------------- schedule

    async def agenda(
        self,
        *,
        academic_year: str,
        department: Optional[str] = None,
        section: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        day: Optional[str] = None,
        include_past: bool = False,
        limit: int = 200,
    ) -> dict:
        """The calendar, with what is booked and what has already slipped."""
        stmt = (
            select(ProjectReview, ProjectBatch)
            .join(ProjectBatch, ProjectReview.batch_id == ProjectBatch.id)
            .where(ProjectBatch.academic_year == academic_year)
            .where(
                ProjectBatch.college_id == self.college_id
                if self.college_id is not None
                else ProjectBatch.id.is_not(None)
            )
            .options(selectinload(ProjectReview.reviewer))
        )
        if department:
            stmt = stmt.where(ProjectBatch.department == department)
        if section:
            stmt = stmt.where(ProjectBatch.section == section)
        if reviewer_id:
            stmt = stmt.where(ProjectReview.reviewer_id == reviewer_id)
        if day:
            try:
                on = parse_local_date(day)
            except ValueError as exc:
                raise SchedulingError(str(exc))
            stmt = (stmt
                    .where(ProjectReview.scheduled_at >= combine_local(on, time(0, 0)))
                    .where(ProjectReview.scheduled_at
                           < combine_local(on + timedelta(days=1), time(0, 0))))
        elif not include_past:
            stmt = stmt.where(ProjectReview.scheduled_at >= utc_now())

        rows = (await self.db.execute(
            stmt.order_by(ProjectReview.scheduled_at).limit(limit)
        )).all()

        now = utc_now()
        items = [self.row(review, batch.batch_code, review.reviewer, now=now)
                 for review, batch in rows]
        self._flag_clashes(items)
        return {
            "items": items,
            "count": len(items),
            "overdue": sum(1 for i in items if i["overdue"]),
            "unassigned": sum(1 for i in items if not i["reviewer"]),
            "clashing": sum(1 for i in items if i["clashes_with"]),
            "academic_year": academic_year,
        }

    @staticmethod
    def _flag_clashes(items: List[dict]) -> None:
        """
        Mark reviews where one reviewer is booked twice at once.

        New bookings are refused when they clash, but a calendar inherited from
        before that rule - or built by an import - can still hold one, and a
        coordinator reading the schedule needs to see it rather than find out
        when nobody turns up.
        """
        by_reviewer: Dict[str, List[dict]] = {}
        for item in items:
            item["clashes_with"] = []
            if item["reviewer_id"] and item["status"] == ReviewStatus.SCHEDULED.value:
                by_reviewer.setdefault(item["reviewer_id"], []).append(item)

        for booked in by_reviewer.values():
            booked.sort(key=lambda i: i["scheduled_at"])
            for i, first in enumerate(booked):
                # Each review's own length, so consecutive slots in a round do
                # not read as overlapping each other.
                ends = first["scheduled_at"] + timedelta(minutes=first["slot_minutes"])
                for second in booked[i + 1:]:
                    if second["scheduled_at"] >= ends:
                        break
                    first["clashes_with"].append(second["batch_code"])
                    second["clashes_with"].append(first["batch_code"])

    # ------------------------------------------------------------ fragments

    @staticmethod
    def row(review: ProjectReview, batch_code: str,
            reviewer: Optional[User] = None, *, now: Optional[datetime] = None) -> dict:
        now = now or utc_now()
        return {
            "id": str(review.id),
            "batch_code": batch_code,
            "review_type": review.review_type,
            "scheduled_at": review.scheduled_at,
            "scheduled_label": humanise(review.scheduled_at),
            "slot_minutes": review.slot_minutes or DEFAULT_SLOT_MINUTES,
            "status": review.status.value,
            "status_label": review.status.value.title(),
            "reviewer": (reviewer.full_name if reviewer else None),
            "reviewer_id": str(review.reviewer_id) if review.reviewer_id else None,
            "score": review.score,
            "remarks": review.remarks,
            "completed_at": review.completed_at,
            # Scheduled and in the past. A completed or cancelled one cannot be
            # overdue, however long ago it was.
            "overdue": (review.status == ReviewStatus.SCHEDULED
                        and review.scheduled_at < now),
        }

    @staticmethod
    def _clean_minutes(raw: int) -> int:
        try:
            minutes = int(raw)
        except (TypeError, ValueError):
            raise SchedulingError("Slot length must be a whole number of minutes.")
        if not MIN_SLOT_MINUTES <= minutes <= MAX_SLOT_MINUTES:
            raise SchedulingError(
                f"A slot must be between {MIN_SLOT_MINUTES} and "
                f"{MAX_SLOT_MINUTES} minutes.")
        return minutes

    async def _reviewer(self, reviewer_id: Optional[str],
                        batch: ProjectBatch) -> Optional[User]:
        """
        Who takes the review.

        Falls back to the batch's guide, which is who would take it if nobody
        said otherwise - leaving it unassigned would put a slot on the calendar
        with nobody expected to turn up.
        """
        if reviewer_id:
            reviewer = (await self.db.execute(
                select(User).where(User.id == reviewer_id)
                .where(User.role.in_(COLLEGE_STAFF_ROLES))
            )).scalar_one_or_none()
            if reviewer is None:
                raise SchedulingError("That reviewer is not a faculty account.")
            return reviewer
        if batch.guide_id:
            return (await self.db.execute(
                select(User).where(User.id == batch.guide_id)
            )).scalar_one_or_none()
        return None

    async def _refuse_duplicate(self, batch: ProjectBatch, review_type: str) -> None:
        existing = (await self.db.execute(
            select(ProjectReview)
            .where(ProjectReview.batch_id == batch.id)
            .where(ProjectReview.review_type == review_type)
            .where(ProjectReview.status == ReviewStatus.SCHEDULED)
        )).scalars().first()
        if existing is not None:
            raise SchedulingError(
                f"{batch.batch_code} already has a {review_type} scheduled for "
                f"{humanise(existing.scheduled_at)}. Move that one instead.")

    async def _cohort(
        self, department: str, year: Optional[str], section: Optional[str],
        academic_year: str, batch_codes: Optional[List[str]],
    ) -> List[ProjectBatch]:
        stmt = (
            self._mine(select(ProjectBatch))
            .where(ProjectBatch.academic_year == academic_year)
            .where(ProjectBatch.department == department)
            .where(ProjectBatch.is_active.is_(True))
        )
        if year:
            stmt = stmt.where(ProjectBatch.year == year)
        if section:
            stmt = stmt.where(ProjectBatch.section == section)
        if batch_codes:
            stmt = stmt.where(ProjectBatch.batch_code.in_(batch_codes))
        return list((await self.db.execute(
            stmt.order_by(ProjectBatch.batch_code)
        )).scalars().all())

    async def cohort_preview(
        self, *, department: str, year: Optional[str], section: Optional[str],
        academic_year: str, review_type: str,
    ) -> dict:
        """
        Who a round would cover, before it is booked.

        Shown so a coordinator can see the batches and the ones already booked
        rather than discovering both from the result.
        """
        kind = _clean_type(review_type)
        batches = await self._cohort(department, year, section, academic_year, None)
        already = {
            str(r.batch_id) for r in (await self.db.execute(
                select(ProjectReview)
                .where(ProjectReview.batch_id.in_([b.id for b in batches] or [""]))
                .where(ProjectReview.review_type == kind)
                .where(ProjectReview.status == ReviewStatus.SCHEDULED)
            )).scalars().all()
        }
        return {
            "batches": [
                {
                    "batch_code": b.batch_code,
                    "title": b.title,
                    "section": b.section,
                    "already_scheduled": str(b.id) in already,
                }
                for b in batches
            ],
            "total": len(batches),
            "to_book": sum(1 for b in batches if str(b.id) not in already),
            "review_type": kind,
        }
