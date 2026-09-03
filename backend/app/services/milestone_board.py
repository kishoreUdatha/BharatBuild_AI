"""
The Milestones screen: tracker, details, approval queue, health and alerts.

The unit here is a milestone, which is why this is separate from the project
tracker and the task board. A coordinator on this screen is asking two things:
what is going to slip, and what is waiting on me to sign off.

Status is derived, not stored - the same argument as health in the tracker. A
milestone that is late is late because its date has passed and it is not done,
and a flag somebody has to remember to set would say otherwise within a week.
Approval is the exception: that *is* a decision a person made, so it is
recorded.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.institution_time import humanise, local_today
from app.models.batch_detail import ActivityLog
from app.models.faculty import ProjectBatch, ProjectStage
from app.models.milestones import (
    ApprovalState,
    EvidenceStatus,
    MilestoneChecklistItem,
    MilestoneDependency,
    MilestoneEvidence,
    MilestonePriority,
    MilestoneStatus,
    ProjectMilestone,
)
from app.services.project_tracker import STAGE_LABELS

# How close a planned date has to be before a milestone counts as upcoming
# rather than merely not started.
UPCOMING_DAYS = 7

HEALTH_ORDER = ["On Track", "At Risk", "Delayed", "Blocked", "Not Started"]


def _iso(d) -> Optional[str]:
    return d.isoformat() if d else None


def _short(d) -> Optional[str]:
    return d.strftime("%d %b") if d else None


class MilestoneBoard:
    """Reads for the Milestones screen, confined to one college."""

    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        self.college_id = college_id

    # ---------------------------------------------------------------- loading

    async def _batches(self, academic_year: str, **f) -> List[ProjectBatch]:
        stmt = (
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.guide))
            .where(ProjectBatch.academic_year == academic_year)
            .where(ProjectBatch.is_active.is_(True))
        )
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        for column, value in (
            (ProjectBatch.department, f.get("department")),
            (ProjectBatch.section, f.get("section")),
            (ProjectBatch.year, f.get("year")),
            (ProjectBatch.semester, f.get("semester")),
            (ProjectBatch.batch_code, f.get("batch_code")),
            (ProjectBatch.guide_id, f.get("guide_id")),
        ):
            if value:
                stmt = stmt.where(column == value)
        return list((await self.db.execute(stmt)).scalars().unique().all())

    async def _milestones(self, batch_ids) -> List[ProjectMilestone]:
        if not batch_ids:
            return []
        return list((await self.db.execute(
            select(ProjectMilestone)
            .options(selectinload(ProjectMilestone.owner),
                     selectinload(ProjectMilestone.reviewer))
            .where(ProjectMilestone.batch_id.in_(batch_ids))
            .order_by(ProjectMilestone.planned_date, ProjectMilestone.position)
        )).scalars().unique().all())

    async def _waiting_on(self, milestones) -> Dict[str, str]:
        """For each milestone, the unfinished thing it depends on."""
        if not milestones:
            return {}
        today = local_today()
        index = {str(m.id): m for m in milestones}
        links = (await self.db.execute(
            select(MilestoneDependency)
            .where(MilestoneDependency.milestone_id.in_([m.id for m in milestones]))
        )).scalars().all()

        out: Dict[str, str] = {}
        for link in links:
            target = index.get(str(link.depends_on_id))
            if target is None:
                continue
            done = self.derive_status(target, today) == MilestoneStatus.COMPLETE.value
            key = str(link.milestone_id)
            if done:
                # Only shown when nothing is outstanding, so a reader can tell
                # "cleared" from "never had a dependency".
                out.setdefault(key, f"{target.name} ✓")
            else:
                out[key] = target.name
        return out

    async def _counts(self, milestone_ids):
        """Evidence and dependency counts in two queries rather than 2N."""
        evidence = defaultdict(lambda: {"total": 0, "verified": 0})
        deps = defaultdict(int)
        if not milestone_ids:
            return evidence, deps

        rows = (await self.db.execute(
            select(MilestoneEvidence.milestone_id, MilestoneEvidence.status,
                   func.count())
            .where(MilestoneEvidence.milestone_id.in_(milestone_ids))
            .group_by(MilestoneEvidence.milestone_id, MilestoneEvidence.status)
        )).all()
        for mid, status, n in rows:
            evidence[str(mid)]["total"] += n
            if status == EvidenceStatus.VERIFIED:
                evidence[str(mid)]["verified"] += n

        rows = (await self.db.execute(
            select(MilestoneDependency.milestone_id, func.count())
            .where(MilestoneDependency.milestone_id.in_(milestone_ids))
            .group_by(MilestoneDependency.milestone_id)
        )).all()
        for mid, n in rows:
            deps[str(mid)] = n
        return evidence, deps

    # ------------------------------------------------------------- derivation

    @staticmethod
    def derive_status(m: ProjectMilestone, today: date) -> str:
        """
        What state this milestone is really in.

        Read from the dates and the work, not from a stored flag - a stored one
        is only as current as the last person who remembered to change it.
        """
        if m.progress >= 100 or m.completed_at:
            return MilestoneStatus.COMPLETE.value
        if m.status == MilestoneStatus.BLOCKED:
            # Blocked is the one a person asserts: nothing in the dates says
            # that a dependency is missing.
            return MilestoneStatus.BLOCKED.value
        due = m.forecast_date or m.planned_date
        if due and due < today:
            return MilestoneStatus.DELAYED.value
        if m.progress > 0:
            return MilestoneStatus.IN_PROGRESS.value
        if due and today <= due <= today + timedelta(days=UPCOMING_DAYS):
            return MilestoneStatus.UPCOMING.value
        return MilestoneStatus.NOT_STARTED.value

    @staticmethod
    def health_of(status: str, m: ProjectMilestone, today: date) -> str:
        if status == MilestoneStatus.COMPLETE.value:
            return "On Track"
        if status == MilestoneStatus.BLOCKED.value:
            return "Blocked"
        if status == MilestoneStatus.DELAYED.value:
            return "Delayed"
        if status == MilestoneStatus.NOT_STARTED.value:
            return "Not Started"
        # In progress or upcoming: at risk when the team's own forecast has
        # already slipped past the plan.
        if (m.forecast_date and m.planned_date
                and m.forecast_date > m.planned_date):
            return "At Risk"
        return "On Track"

    def _row(self, m: ProjectMilestone, batch: ProjectBatch,
             evidence, deps, today: date,
             waiting_on: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        status = self.derive_status(m, today)
        ev = evidence.get(str(m.id), {"total": 0, "verified": 0})
        stage = None
        if m.stage:
            try:
                stage = STAGE_LABELS[ProjectStage(str(m.stage).lower())]
            except (ValueError, KeyError):
                stage = str(m.stage).replace("_", " ").title()
        return {
            "id": str(m.id),
            "name": m.name,
            "batch_code": batch.batch_code,
            "project_title": batch.title,
            "guide_name": batch.guide.full_name if batch.guide else None,
            "stage": stage,
            "priority": m.priority.value,
            "status": status,
            "health": self.health_of(status, m, today),
            "approval": m.approval.value,
            "owner": m.owner.full_name if m.owner else None,
            "owner_id": str(m.owner_id) if m.owner_id else None,
            "reviewer": m.reviewer.full_name if m.reviewer else None,
            "planned_start": _iso(m.planned_start),
            "planned_date": _iso(m.planned_date),
            "planned_display": _short(m.planned_date),
            "forecast_date": _iso(m.forecast_date),
            "forecast_display": _short(m.forecast_date),
            "slipping": bool(m.forecast_date and m.planned_date
                             and m.forecast_date > m.planned_date),
            "progress": m.progress or 0,
            "evidence_verified": ev["verified"],
            "evidence_total": ev["total"],
            "dependencies": deps.get(str(m.id), 0),
            # What it is actually waiting on, named. A count tells a reader
            # there is a problem; the name tells them where to go.
            "waiting_on": (waiting_on or {}).get(str(m.id)),
        }

    # ------------------------------------------------------------------ board

    async def board(self, academic_year: str, page: int = 1,
                    per_page: int = 10, **f) -> Dict[str, Any]:
        """Counters, the tracker grouped by batch, and the details table."""
        today = local_today()
        batches = await self._batches(academic_year, **f)
        by_id = {str(b.id): b for b in batches}
        milestones = await self._milestones([b.id for b in batches])
        evidence, deps = await self._counts([m.id for m in milestones])
        waiting = await self._waiting_on(milestones)

        rows = [self._row(m, by_id[str(m.batch_id)], evidence, deps, today, waiting)
                for m in milestones if str(m.batch_id) in by_id]

        # Deltas are measured, not guessed: how many milestones were finished
        # or signed off in the last fortnight against the fortnight before.
        # Nothing stores a historical snapshot, but completion and approval
        # both carry a timestamp, which is enough to say honestly whether the
        # cohort is moving faster or slower.
        deltas = self._deltas(milestones, today)

        if f.get("status"):
            rows = [r for r in rows if r["status"] == str(f["status"]).lower()]
        if f.get("milestone"):
            rows = [r for r in rows if r["name"] == f["milestone"]]
        if f.get("approval"):
            rows = [r for r in rows if r["approval"] == str(f["approval"]).lower()]
        if f.get("due_from") or f.get("due_to"):
            lo, hi = f.get("due_from") or "0000", f.get("due_to") or "9999"
            rows = [r for r in rows
                    if r["planned_date"] and lo <= r["planned_date"] <= hi]

        # Worst first: delayed and blocked before anything comfortable.
        order = {"delayed": 0, "blocked": 1, "in_progress": 2,
                 "upcoming": 3, "not_started": 4, "complete": 5}
        rows.sort(key=lambda r: (order.get(r["status"], 9),
                                 r["planned_date"] or "9999"))

        total = len(rows)
        start = max(0, (page - 1) * per_page)

        # The tracker groups the same rows by batch, which is how the timeline
        # reads - one band per project, its milestones inside.
        grouped: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            g = grouped.setdefault(r["batch_code"], {
                "batch_code": r["batch_code"],
                "project_title": r["project_title"],
                "milestones": [],
            })
            g["milestones"].append(r)
        tracker = sorted(grouped.values(), key=lambda g: g["batch_code"])

        return {
            "kpis": self._kpis(rows, deltas),
            "options": self._options(batches, milestones),
            "tracker": tracker[:12],
            "rows": rows[start:start + per_page],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, -(-total // per_page)),
            "window": self._window(rows, today),
            "academic_year": academic_year,
        }

    @staticmethod
    def _window(rows, today: date) -> Dict[str, Any]:
        """The date span the timeline should draw, with today inside it."""
        dates = [r["planned_date"] for r in rows if r["planned_date"]]
        dates += [r["forecast_date"] for r in rows if r["forecast_date"]]
        if not dates:
            return {"start": today.isoformat(),
                    "end": (today + timedelta(days=14)).isoformat(),
                    "today": today.isoformat()}
        lo = min(min(dates), today.isoformat())
        hi = max(max(dates), today.isoformat())
        return {"start": lo, "end": hi, "today": today.isoformat()}

    def _deltas(self, milestones, today: date) -> Dict[str, int]:
        """
        Every counter's change over the last fortnight.

        Nothing stores a historical snapshot, but the counters can be
        *re-derived* for a past date from the data that is kept: a milestone
        was overdue a fortnight ago if its date had passed by then and its
        `completed_at` is later than then, or absent. Same for the rest.

        Only the counters the data can actually answer are returned. Progress
        and approval state are stored as they are *now* with no history, so
        "in progress a fortnight ago" and "awaiting approval a fortnight ago"
        are not knowable - and a card showing an arrow for them would be
        making a number up. Those two are left without one.
        """
        then = today - timedelta(days=14)
        cutoff = datetime.combine(then, datetime.max.time())

        def snapshot(as_of: date, stamp: datetime) -> Dict[str, int]:
            counts = Counter()
            for m in milestones:
                if m.created_at and m.created_at > stamp:
                    continue                       # did not exist yet
                counts["total"] += 1

                done = bool(m.completed_at and m.completed_at <= stamp)
                if done:
                    counts["complete"] += 1
                    continue

                due = m.forecast_date or m.planned_date
                if due and due < as_of:
                    counts["overdue"] += 1
                elif due and as_of <= due <= as_of + timedelta(days=UPCOMING_DAYS):
                    counts["upcoming"] += 1
            return counts

        # Only the past snapshot is returned. The present numbers are the ones
        # already on screen, and subtracting from a second, separately-computed
        # "now" let the two disagree - Upcoming once showed a change larger
        # than the value it was changing.
        return dict(snapshot(then, cutoff))

    @staticmethod
    def _kpis(rows, deltas: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        total = len(rows)
        by = Counter(r["status"] for r in rows)
        awaiting = sum(1 for r in rows
                       if r["approval"] in ("pending", "review_ready"))
        pending_evidence = sum(1 for r in rows
                               if r["evidence_verified"] < r["evidence_total"])
        done = by["complete"]
        rate = round(done / total * 100) if total else 0
        # Each delta is the number on screen minus the same count a fortnight
        # ago, so the two can never disagree.
        b = deltas or {}
        rate_then = round(b.get("complete", 0) / max(1, b.get("total", 1)) * 100)

        def d(key: str, current: int):
            if not b:
                return None
            return current - b.get(key, 0)

        return [
            {"id": "total", "value": total, "label": "Total Milestones",
             "delta": d("total", total)},
            {"id": "complete", "value": done, "label": "Completed", "tone": "ok",
             "delta": d("complete", done)},
            {"id": "progress", "value": by["in_progress"], "label": "In Progress",
             },
            {"id": "upcoming", "value": by["upcoming"], "label": "Upcoming",
             "delta": d("upcoming", by["upcoming"])},
            {"id": "delayed", "value": by["delayed"], "label": "Overdue",
             "tone": "danger" if by["delayed"] else "ok",
             # Fewer overdue is the improvement, so the arrow is inverted.
             "delta": d("overdue", by["delayed"]), "lower_is_better": True},
            {"id": "awaiting", "value": awaiting, "label": "Awaiting Approval",
             "tone": "warn" if awaiting else "ok",
             "lower_is_better": True},
            {"id": "evidence", "value": pending_evidence, "label": "Evidence Pending",
             "tone": "warn" if pending_evidence else "ok",
             "lower_is_better": True},
            {"id": "rate", "value": f"{rate}%", "label": "Completion Rate",
             "delta": (rate - rate_then) if b else None, "suffix": "%"},
        ]

    @staticmethod
    def _options(batches, milestones) -> Dict[str, Any]:
        """Dropdown values, from what exists rather than from every enum."""
        return {
            "batches": sorted({b.batch_code for b in batches}),
            "milestones": sorted({m.name for m in milestones}),
            "statuses": [s.value for s in MilestoneStatus],
            "approvals": [a.value for a in ApprovalState],
            "priorities": [p.value for p in MilestonePriority],
        }

    # ------------------------------------------------- queue, health, alerts

    async def queue(self, academic_year: str, **f) -> Dict[str, Any]:
        """
        Who is waiting on a signature, what falls due next, and what is stuck.

        The three right-hand panels answer one question between them - where
        should the next hour go - so they are built together from one read.
        """
        today = local_today()
        batches = await self._batches(academic_year, **f)
        by_id = {str(b.id): b for b in batches}
        milestones = await self._milestones([b.id for b in batches])
        evidence, deps = await self._counts([m.id for m in milestones])
        waiting = await self._waiting_on(milestones)
        rows = [self._row(m, by_id[str(m.batch_id)], evidence, deps, today, waiting)
                for m in milestones if str(m.batch_id) in by_id]

        approvals = [r for r in rows
                     if r["approval"] in ("pending", "review_ready", "changes_requested")]
        approvals.sort(key=lambda r: (r["approval"] != "review_ready",
                                      r["planned_date"] or "9999"))

        upcoming = [r for r in rows
                    if r["status"] not in ("complete",) and r["planned_date"]
                    and r["planned_date"] >= today.isoformat()]
        upcoming.sort(key=lambda r: r["planned_date"])

        health = Counter(r["health"] for r in rows)
        total = len(rows) or 1

        # What is holding what up: a dependency whose target is not complete.
        alerts = []
        if milestones:
            links = (await self.db.execute(
                select(MilestoneDependency)
                .where(MilestoneDependency.milestone_id.in_([m.id for m in milestones]))
            )).scalars().all()
            names = {str(m.id): m for m in milestones}
            for link in links:
                blocker = names.get(str(link.depends_on_id))
                waiter = names.get(str(link.milestone_id))
                if blocker is None or waiter is None:
                    continue
                if self.derive_status(blocker, today) == MilestoneStatus.COMPLETE.value:
                    continue
                batch = by_id.get(str(waiter.batch_id))
                alerts.append({
                    "blocker": blocker.name,
                    "waiting": waiter.name,
                    "batch_code": batch.batch_code if batch else "—",
                    "message": f"{blocker.name} blocks {waiter.name}",
                })
        alerts.sort(key=lambda a: a["batch_code"])

        return {
            "approvals": approvals[:8],
            "approval_total": len(approvals),
            "upcoming": upcoming[:6],
            "health": [{"label": k, "count": health.get(k, 0),
                        "percent": round(health.get(k, 0) / total * 100)}
                       for k in HEALTH_ORDER],
            "alerts": alerts[:6],
            "alert_total": len(alerts),
        }

    # ----------------------------------------------------------------- detail

    async def detail(self, milestone_id: str) -> Optional[Dict[str, Any]]:
        """One milestone in full: checklist, evidence, dependencies, activity."""
        m = (await self.db.execute(
            select(ProjectMilestone)
            .options(selectinload(ProjectMilestone.owner),
                     selectinload(ProjectMilestone.reviewer))
            .where(ProjectMilestone.id == milestone_id)
        )).scalars().unique().first()
        if m is None:
            return None

        stmt = select(ProjectBatch).where(ProjectBatch.id == m.batch_id)
        if self.college_id:
            stmt = stmt.where(ProjectBatch.college_id == self.college_id)
        batch = (await self.db.execute(
            stmt.options(selectinload(ProjectBatch.guide))
        )).scalars().unique().first()
        if batch is None:
            return None

        today = local_today()
        evidence, deps = await self._counts([m.id])
        waiting = await self._waiting_on([m])
        row = self._row(m, batch, evidence, deps, today, waiting)

        checklist = (await self.db.execute(
            select(MilestoneChecklistItem)
            .where(MilestoneChecklistItem.milestone_id == m.id)
            .order_by(MilestoneChecklistItem.position)
        )).scalars().all()

        files = (await self.db.execute(
            select(MilestoneEvidence)
            .where(MilestoneEvidence.milestone_id == m.id)
            .order_by(MilestoneEvidence.position)
        )).scalars().all()

        links = (await self.db.execute(
            select(MilestoneDependency)
            .where(MilestoneDependency.milestone_id == m.id)
        )).scalars().all()
        depends_on = []
        if links:
            others = (await self.db.execute(
                select(ProjectMilestone)
                .where(ProjectMilestone.id.in_([l.depends_on_id for l in links]))
            )).scalars().all()
            depends_on = [{
                "id": str(o.id), "name": o.name,
                "status": self.derive_status(o, today),
            } for o in others]

        activity = (await self.db.execute(
            select(ActivityLog)
            .where(ActivityLog.batch_id == batch.id)
            .order_by(ActivityLog.occurred_at.desc())
            .limit(6)
        )).scalars().all()

        return {
            **row,
            "detail": m.detail,
            "review_note": m.review_note,
            "checklist": [{"id": str(c.id), "label": c.label,
                           "done": bool(c.is_done)} for c in checklist],
            "evidence": [{"id": str(e.id), "label": e.label,
                          "status": e.status.value, "url": e.url} for e in files],
            "depends_on": depends_on,
            "activity": [{"code": a.event_code, "summary": a.activity,
                          "actor": a.actor_name, "at": humanise(a.occurred_at)}
                         for a in activity],
        }


    async def recovery_plan(self, academic_year: str, **f) -> Dict[str, Any]:
        """
        The order in which the slipping milestones should be cleared.

        Derived, not generated. A recovery plan is a topological question -
        what unblocks the most, soonest - and that is arithmetic on the
        dependency graph and the dates. A model would give a different answer
        each time it was asked and could not be checked against the data.

        Ranked by how many other milestones each one is holding up, then by
        how far past its date it already is.
        """
        today = local_today()
        batches = await self._batches(academic_year, **f)
        by_id = {str(b.id): b for b in batches}
        milestones = await self._milestones([b.id for b in batches])
        evidence, deps = await self._counts([m.id for m in milestones])
        waiting = await self._waiting_on(milestones)
        index = {str(m.id): m for m in milestones}

        blocking = Counter()
        if milestones:
            links = (await self.db.execute(
                select(MilestoneDependency)
                .where(MilestoneDependency.milestone_id.in_([m.id for m in milestones]))
            )).scalars().all()
            for link in links:
                blocking[str(link.depends_on_id)] += 1

        steps = []
        for m in milestones:
            batch = by_id.get(str(m.batch_id))
            if batch is None:
                continue
            row = self._row(m, batch, evidence, deps, today, waiting)
            if row["health"] not in ("At Risk", "Delayed", "Blocked"):
                continue
            due = m.forecast_date or m.planned_date
            overdue_by = (today - due).days if due and due < today else 0
            holds = blocking.get(str(m.id), 0)

            # Say what specifically is in the way, so the step is actionable
            # rather than a restatement of the problem.
            reasons = []
            if row["evidence_verified"] < row["evidence_total"]:
                reasons.append(
                    f"{row['evidence_total'] - row['evidence_verified']} piece(s) "
                    "of evidence to verify")
            if row["approval"] in ("pending", "review_ready"):
                reasons.append("waiting on approval")
            if row["approval"] == "changes_requested":
                reasons.append("changes were requested")
            unmet = [index[str(l)] for l in []]
            if row["dependencies"]:
                reasons.append(f"waits on {row['dependencies']} other milestone(s)")
            if not reasons:
                reasons.append("no evidence or approval outstanding - chase the owner")

            steps.append({
                **row,
                "blocks": holds,
                "overdue_days": overdue_by,
                "why": reasons,
            })

        steps.sort(key=lambda s: (-s["blocks"], -s["overdue_days"]))
        return {
            "steps": steps[:10],
            "total": len(steps),
            "headline": (
                f"{len(steps)} milestone(s) need recovering. "
                f"Clearing the top {min(3, len(steps))} unblocks "
                f"{sum(s['blocks'] for s in steps[:3])} others."
            ) if steps else "Nothing needs recovering.",
        }

    # ---------------------------------------------------------------- insight

    async def insight(self, academic_year: str) -> Dict[str, Any]:
        """Which milestones are likely to miss, and what to clear first."""
        today = local_today()
        batches = await self._batches(academic_year)
        by_id = {str(b.id): b for b in batches}
        milestones = await self._milestones([b.id for b in batches])
        evidence, deps = await self._counts([m.id for m in milestones])
        waiting = await self._waiting_on(milestones)
        rows = [self._row(m, by_id[str(m.batch_id)], evidence, deps, today, waiting)
                for m in milestones if str(m.batch_id) in by_id]

        at_risk = [r for r in rows if r["health"] in ("At Risk", "Delayed", "Blocked")]
        if not at_risk:
            return {"headline": "No milestone is currently at risk.",
                    "detail": "", "at_risk": 0, "codes": []}

        # What most of them are waiting on - the thing worth clearing first.
        causes = Counter()
        for r in at_risk:
            if r["dependencies"]:
                causes["unmet dependencies"] += 1
            if r["evidence_verified"] < r["evidence_total"]:
                causes["evidence not verified"] += 1
            if r["approval"] in ("pending", "review_ready"):
                causes["approval outstanding"] += 1
        top = [c for c, _ in causes.most_common(2)]

        return {
            "headline": (
                f"{len(at_risk)} milestone{'' if len(at_risk) == 1 else 's'} "
                f"{'is' if len(at_risk) == 1 else 'are'} likely to miss "
                "their planned dates."
            ),
            "detail": ("Most often because of " + " and ".join(top) + ".")
                      if top else "",
            "at_risk": len(at_risk),
            "codes": sorted({r["batch_code"] for r in at_risk})[:3],
        }
