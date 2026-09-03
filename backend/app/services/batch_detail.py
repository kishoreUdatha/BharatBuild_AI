"""
Batch Detail Service - the seven tabs of Batch Registration Details.

One loader fetches the batch with everything eager-loaded, then each tab is a
projection over it. Checklists are computed, never stored, so a tab can never
disagree with the underlying records.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch_detail import (
    ActivityLog,
    ApprovalEvent,
    BatchDocument,
    DOCUMENT_STATUS_LABELS,
    DocumentStatus,
    ScopeKind,
)
from app.models.faculty import (
    BasePaper,
    BasePaperStatus,
    BatchRegistrationStatus,
    ProjectBatch,
    ProjectBatchMember,
    ProjectReview,
    StudentEnrollment,
    StudentProfileStatus,
)
from app.models.user import User
from app.services.faculty_registrations import STATUS_LABELS, TEAM_SIZE
from app.services import batch_files, file_store, project_details

REVIEW_SLA_HOURS = 48


def _pct(part: int, whole: int) -> int:
    return int(round(part / whole * 100)) if whole else 0


class BatchDetailService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def load(self, identifier: str) -> Optional[ProjectBatch]:
        """Fetch by id or batch code, with every tab's relations eager-loaded."""
        stmt = (
            select(ProjectBatch)
            .options(
                selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
                selectinload(ProjectBatch.guide),
                selectinload(ProjectBatch.reviewer),
                # The paper's own relations are read by _paper_summary(full=True);
                # loading only base_paper leaves them lazy and blows up outside
                # the async context.
                selectinload(ProjectBatch.base_paper).selectinload(BasePaper.metrics),
                selectinload(ProjectBatch.base_paper).selectinload(BasePaper.key_methods),
                selectinload(ProjectBatch.base_paper).selectinload(BasePaper.uploaded_by),
                selectinload(ProjectBatch.base_paper).selectinload(BasePaper.file),
                selectinload(ProjectBatch.documents).selectinload(BatchDocument.file),
                selectinload(ProjectBatch.objectives),
                selectinload(ProjectBatch.methodology),
                selectinload(ProjectBatch.scope_items),
                selectinload(ProjectBatch.technologies),
                selectinload(ProjectBatch.supporting_papers),
                # Reviews and their reviewer: the review tab and the scheduling
                # routes both read these off the loaded batch, and a
                # relationship left lazy raises rather than loading here.
                selectinload(ProjectBatch.reviews).selectinload(ProjectReview.reviewer),
                selectinload(ProjectBatch.submissions),
                selectinload(ProjectBatch.contributions),
                selectinload(ProjectBatch.documents).selectinload(BatchDocument.uploaded_by),
                selectinload(ProjectBatch.approval_events).selectinload(ApprovalEvent.actor),
                selectinload(ProjectBatch.activities).selectinload(ActivityLog.actor),
            )
        )
        key = (identifier or "").strip()
        stmt = stmt.where(
            (ProjectBatch.id == key) | (ProjectBatch.batch_code == key.upper())
        )
        return (await self.db.execute(stmt)).scalars().unique().first()

    # ------------------------------------------------------------ shared head

    def header(self, batch: ProjectBatch) -> dict:
        checks = self.registration_checklist(batch)
        passed = sum(1 for c in checks if c["passed"])
        return {
            "id": str(batch.id),
            "batch_code": batch.batch_code,
            "title": batch.title,
            "project_type": batch.project_type,
            "department": batch.department,
            "year": batch.year,
            "semester": batch.semester,
            "section": batch.section,
            "academic_year": batch.academic_year,
            "guide": batch.guide.full_name if batch.guide else None,
            "status": STATUS_LABELS.get(batch.registration_status, "Draft"),
            "status_key": batch.registration_status.value,
            "registration_complete": passed == len(checks),
            "completeness": _pct(passed, len(checks)),
            "created_at": batch.created_at,
            "updated_at": batch.updated_at,
            "submitted_at": batch.submitted_at,
        }

    @staticmethod
    def registration_checklist(batch: ProjectBatch) -> List[dict]:
        """The eight gates shown on Overview. Derived, never stored."""
        active = [m for m in batch.members if m.is_active]
        bp = batch.base_paper
        objectives = list(batch.objectives)
        docs = list(batch.documents)
        declarations = [d for d in docs if d.category == "Student Declaration"
                        and d.status == DocumentStatus.VERIFIED]

        # Document gates. Without these the checklist reported everything
        # passed while a mandatory document was still missing, which would let
        # a registration be approved with no ethics approval on file.
        required = [d for d in docs if d.is_required]
        required_verified = [d for d in required if d.status == DocumentStatus.VERIFIED]
        ethics = next((d for d in docs if "ethic" in (d.name or "").lower()
                       or "ethic" in (d.category or "").lower()), None)
        cohort_ok = len({(m.student.section if m.student else None) for m in active}) <= 1

        rows = [
            ("members", "Four students verified", len(active) >= TEAM_SIZE and cohort_ok,
             "Passed" if len(active) >= TEAM_SIZE and cohort_ok
             else f"{len(active)}/{TEAM_SIZE}" if len(active) < TEAM_SIZE else "Mixed sections"),
            ("details", "Project details complete",
             bool(batch.title and batch.abstract and objectives),
             "Passed" if batch.title and batch.abstract and objectives else "Incomplete"),
            ("paper", "Primary base paper verified",
             bp is not None and bp.status == BasePaperStatus.VERIFIED,
             "Passed" if bp and bp.status == BasePaperStatus.VERIFIED
             else "Uploaded" if bp and bp.status == BasePaperStatus.PENDING else "Missing"),
            ("improvement", "Improvement statement accepted", bool(bp and bp.improvement_note),
             "Passed" if bp and bp.improvement_note else "Missing"),
            ("guide", "Guide assigned", batch.guide_id is not None,
             "Passed" if batch.guide_id else "Not assigned"),
            ("declarations", "Student declarations", len(declarations) > 0,
             "Passed" if declarations else "Missing"),
            ("documents", "Required documents verified",
             bool(required) and len(required_verified) == len(required),
             "Passed" if required and len(required_verified) == len(required)
             else f"{len(required_verified)}/{len(required)}" if required else "None required"),
            ("ethics", "Ethics approval",
             ethics is not None and ethics.status == DocumentStatus.VERIFIED,
             "Passed" if ethics and ethics.status == DocumentStatus.VERIFIED else "Pending"),
        ]
        return [{"key": k, "label": lbl, "passed": ok, "detail": detail} for k, lbl, ok, detail in rows]

    # ------------------------------------------------------------------ tabs

    async def overview(self, batch: ProjectBatch) -> dict:
        checks = self.registration_checklist(batch)
        docs = sorted(batch.documents, key=lambda d: d.uploaded_at)
        now = datetime.utcnow()
        sla = None
        if batch.review_due_at:
            hours = int((batch.review_due_at - now).total_seconds() // 3600)
            sla = f"{hours}h remaining" if hours >= 0 else f"Overdue {abs(hours) // 24 or 1}d"

        leader = next((m for m in batch.members if m.is_lead), None)
        return {
            "header": self.header(batch),
            "members": [self._member_row(m) for m in self._ordered_members(batch)],
            "cohort_note": " • ".join(filter(None, [
                f"All students belong to {batch.department}", batch.year,
                f"Semester {batch.semester}" if batch.semester else None,
                f"Section {batch.section}" if batch.section else None,
            ])),
            "project": {
                "title": batch.title,
                "domain": batch.domain,
                "problem_statement": batch.problem_statement,
                "abstract": batch.abstract,
                "objectives": [o.text for o in sorted(batch.objectives, key=lambda o: o.position)],
                "technologies": [t.name for t in sorted(batch.technologies, key=lambda t: (t.layer, t.position))],
                "expected_outcome": next(
                    (s.text for s in batch.scope_items if s.kind == ScopeKind.OUTCOME), None
                ),
            },
            "base_paper": self._paper_summary(batch),
            "checklist": checks,
            "checks_passed": sum(1 for c in checks if c["passed"]),
            "checks_total": len(checks),
            "approval": {
                "status": STATUS_LABELS.get(batch.registration_status, "Draft"),
                "submitted_by": (leader.student.full_name if leader and leader.student else None),
                "submitted_at": batch.submitted_at,
                "reviewer": batch.reviewer.full_name if batch.reviewer else (
                    batch.guide.full_name if batch.guide else None),
                "sla": sla,
            },
            "documents": [
                {"name": d.name, "status": DOCUMENT_STATUS_LABELS[d.status], "status_key": d.status.value}
                for d in docs[:5]
            ],
            "document_count": len(docs),
            "timeline": self._registration_timeline(batch),
        }

    async def team(self, batch: ProjectBatch) -> dict:
        members = self._ordered_members(batch)
        rows = [self._member_row(m, full=True) for m in members]
        verified = sum(1 for r in rows if r["profile_verified"])
        declared = sum(1 for r in rows if r["declaration_signed"])
        active = [m for m in members if m.is_active]

        checks = [
            ("joined", "Four students joined", len(active) >= TEAM_SIZE),
            ("department", "Same department",
             len({m.student.department for m in active if m.student}) <= 1),
            ("year", "Same academic year", True),
            ("semester", "Same semester", True),
            ("section", "Same section",
             len({m.student.section for m in active if m.student and m.student.section}) <= 1),
            ("rolls", "Unique roll numbers",
             len({m.student.roll_number for m in active if m.student}) == len(active)),
            ("contact", "Contact details verified", verified == len(rows) and bool(rows)),
            ("declarations", "Declarations signed", declared == len(rows) and bool(rows)),
        ]
        checklist = [{"key": k, "label": lbl, "passed": ok} for k, lbl, ok in checks]

        roles = Counter(r["responsibility"] or "Unassigned" for r in rows)
        return {
            "header": self.header(batch),
            "kpis": [
                {"id": "members", "value": f"{len(active)} / {TEAM_SIZE}", "label": "Team Members"},
                {"id": "verified", "value": str(verified), "label": "Verified Profiles"},
                {"id": "leader", "value": str(sum(1 for m in members if m.is_lead)), "label": "Batch Leader"},
                {"id": "declarations", "value": str(declared), "label": "Student Declarations"},
                {"id": "completion", "value": f"{_pct(verified, len(rows))}%", "label": "Team Completion"},
            ],
            "members": rows,
            "checklist": checklist,
            "checks_passed": sum(1 for c in checklist if c["passed"]),
            "checks_total": len(checklist),
            "roles": [{"role": role, "count": count} for role, count in roles.most_common()],
            "internal_note": batch.internal_note,
            "note_updated_by": batch.guide.full_name if batch.guide else None,
            "note_updated_at": batch.updated_at,
            "timeline": self._team_timeline(batch, members),
        }

    async def project(self, batch: ProjectBatch) -> dict:
        by_kind: Dict[str, List[str]] = defaultdict(list)
        for item in sorted(batch.scope_items, key=lambda s: s.position):
            by_kind[item.kind.value].append(item.text)

        layers: Dict[str, List[str]] = defaultdict(list)
        for tech in sorted(batch.technologies, key=lambda t: t.position):
            layers[tech.layer].append(tech.name)

        weeks = None
        if batch.start_date and batch.target_completion:
            weeks = max(1, (batch.target_completion - batch.start_date).days // 7)

        objectives = sorted(batch.objectives, key=lambda o: o.position)
        # One definition of "complete", shared with the entry form so the count
        # this panel shows and the gate that refuses a submission cannot drift.
        checklist = project_details.completeness(batch)

        return {
            "header": self.header(batch),
            "kpis": [
                {"id": "domain", "value": batch.domain or "—", "label": "Domain"},
                {"id": "type", "value": batch.project_type or "—", "label": "Project Type"},
                {"id": "objectives", "value": str(len(objectives)), "label": "Objectives"},
                {"id": "tech", "value": str(len(batch.technologies)), "label": "Technologies"},
                {"id": "duration", "value": f"{weeks} Weeks" if weeks else "—", "label": "Duration"},
            ],
            "overview": {
                "title": batch.title,
                "domain": batch.domain,
                "project_type": batch.project_type,
                "keywords": [k.strip() for k in (batch.keywords or "").split(",") if k.strip()],
                "problem_statement": batch.problem_statement,
                "abstract": batch.abstract,
            },
            "objectives": [
                {"position": o.position + 1, "text": o.text, "status": o.status.value.replace("_", " ").title()}
                for o in objectives
            ],
            "methodology": [
                {"position": s.position + 1, "title": s.title, "description": s.description}
                for s in sorted(batch.methodology, key=lambda s: s.position)
            ],
            "outcomes": by_kind.get("outcome", []),
            "in_scope": by_kind.get("in_scope", []),
            "out_of_scope": by_kind.get("out_of_scope", []),
            "deliverables": by_kind.get("deliverable", []),
            "technology_stack": [{"layer": layer, "items": items} for layer, items in layers.items()],
            "duration": {
                "start_date": batch.start_date,
                "target_completion": batch.target_completion,
                "weeks": weeks,
                "weekly_effort_hours": batch.weekly_effort_hours,
            },
            "checklist": checklist,
            "checks_passed": sum(1 for c in checklist if c["passed"]),
            "checks_total": len(checklist),
            "faculty_note": batch.faculty_note,
            "locked": project_details.editable(batch) is not None,
            "locked_reason": project_details.editable(batch),
            "history": self._module_activity(batch, {"Registration", "Team", "Approval"}),
        }

    @staticmethod
    def _quality_label(overall: Optional[int]) -> Optional[str]:
        if overall is None:
            return None
        if overall >= 90:
            return "Strong Base Paper"
        if overall >= 75:
            return "Solid Base Paper"
        if overall >= 60:
            return "Acceptable Base Paper"
        return "Weak Base Paper"

    def _paper_lifecycle(self, batch: ProjectBatch) -> List[dict]:
        """
        The six milestones a base paper passes through.

        Read off the paper itself rather than the audit log: the log only
        records what happened while someone was watching, whereas the paper's
        own fields say definitively whether metadata was extracted, the DOI
        recorded and the improvement statement written.
        """
        bp = batch.base_paper
        supporting = list(batch.supporting_papers)
        uploader = None
        if bp is not None and bp.uploaded_by is not None:
            uploader = bp.uploaded_by.full_name
        verifier = None
        if bp is not None and bp.verified_by_id is not None:
            verifier = batch.guide.full_name if batch.guide else "Faculty"

        steps = [
            ("Primary paper uploaded", bp is not None,
             bp.uploaded_at if bp else None, uploader),
            ("Metadata extracted", bool(bp and bp.publication and bp.year),
             bp.uploaded_at if bp else None, "System"),
            ("DOI validated", bool(bp and bp.doi),
             bp.uploaded_at if bp else None, "System"),
            ("Improvement statement added", bool(bp and bp.improvement_note),
             bp.updated_at if bp else None, uploader),
            ("Faculty verified", bool(bp and bp.status == BasePaperStatus.VERIFIED),
             bp.verified_at if bp else None, verifier),
            ("Supporting papers added", len(supporting) > 0,
             bp.updated_at if bp and supporting else None, uploader),
        ]
        return [
            {"step": label, "done": done, "occurred_at": when if done else None,
             "actor": actor if done else None}
            for label, done, when, actor in steps
        ]

    async def papers(self, batch: ProjectBatch) -> dict:
        bp = batch.base_paper
        supporting = sorted(batch.supporting_papers, key=lambda s: s.title)
        verified = 1 if bp and bp.status == BasePaperStatus.VERIFIED else 0
        pending = 1 if bp and bp.status == BasePaperStatus.PENDING else 0

        checks = [
            ("opens", "PDF opens correctly", bool(bp and bp.file_name)),
            ("metadata", "Title and metadata match", bool(bp and bp.title and bp.publication)),
            ("doi", "DOI resolves", bool(bp and bp.doi)),
            ("year", "Publication year valid", bool(bp and bp.year)),
            ("relevance", "Relevant to project domain", bool(bp and (bp.relevance_score or 0) >= 70)),
            ("primary", "Primary paper marked", bp is not None),
            ("improvement", "Improvement statement complete", bool(bp and bp.improvement_note)),
            ("similarity", "Plagiarism/similarity review",
             bp is not None and (bp.similarity_percent or 0) <= 20),
        ]
        checklist = [
            {"key": k, "label": lbl, "passed": ok,
             "detail": (f"{bp.similarity_percent:.0f}% similarity, passed"
                        if k == "similarity" and bp and bp.similarity_percent is not None
                        else "Passed" if ok else "Failed")}
            for k, lbl, ok in checks
        ]

        scores = [s for s in [bp.relevance_score, bp.methodology_score, bp.recency_score,
                              bp.credibility_score] if bp and s is not None] if bp else []
        overall = int(round(sum(scores) / len(scores))) if scores else None

        return {
            "header": self.header(batch),
            "kpis": [
                {"id": "uploaded", "value": str((1 if bp else 0) + len(supporting)), "label": "Papers Uploaded"},
                {"id": "primary", "value": "1" if bp else "0", "label": "Primary Paper"},
                {"id": "supporting", "value": str(len(supporting)), "label": "Supporting Papers"},
                {"id": "verified", "value": str(verified), "label": "Verified"},
                {"id": "pending", "value": str(pending + len(supporting)), "label": "Pending Verification"},
            ],
            "primary": self._paper_summary(batch, full=True),
            "improvement": {
                "current_limitation": bp.current_limitation if bp else None,
                "proposed": bp.improvement_note if bp else None,
                "contributions": [c.text for c in sorted(batch.contributions, key=lambda c: c.position)],
            },
            "supporting": [
                {
                    "id": str(s.id),
                    "title": s.title, "authors": s.authors, "source": s.source,
                    "year": s.year, "doi": s.doi, "purpose": s.purpose, "url": s.url,
                    "doi_label": "DOI available" if s.doi else "No DOI",
                }
                for s in supporting
            ],
            "checklist": checklist,
            "checks_passed": sum(1 for c in checklist if c["passed"]),
            "checks_total": len(checklist),
            "quality": {
                "relevance": bp.relevance_score if bp else None,
                "methodology": bp.methodology_score if bp else None,
                "recency": bp.recency_score if bp else None,
                "credibility": bp.credibility_score if bp else None,
                "overall": overall,
                "label": self._quality_label(overall),
            },
            "faculty_note": bp.faculty_note if bp else None,
            "verification_note": {
                "body": bp.faculty_note if bp else None,
                "actor": (batch.guide.full_name if batch.guide else None) if bp else None,
                "at": bp.verified_at if bp else None,
            },
            # Chips on the primary paper card.
            "primary_tags": [
                {"label": "Primary Paper", "tone": "indigo"},
                {"label": (bp.status.value.title() if bp else "Missing"),
                 "tone": "green" if bp and bp.status == BasePaperStatus.VERIFIED
                         else "amber" if bp else "red"},
                {"label": "DOI Valid" if bp and bp.doi else "No DOI",
                 "tone": "green" if bp and bp.doi else "amber"},
            ],
            "activity": self._paper_lifecycle(batch),
            "quick_actions": {
                "pending_papers": pending + len(supporting),
                "papers_total": (1 if bp else 0) + len(supporting),
                "has_doi": bool(bp and bp.doi),
                "similarity_percent": bp.similarity_percent if bp else None,
            },
        }

    async def documents(self, batch: ProjectBatch) -> dict:
        docs = sorted(batch.documents, key=lambda d: d.uploaded_at, reverse=True)
        counts = Counter(d.status for d in docs)
        storage = sum(d.file_size or 0 for d in docs)

        by_category: Dict[str, int] = defaultdict(int)
        for d in docs:
            by_category[d.category] += d.file_size or 0

        required = [d for d in docs if d.is_required]
        complete = sum(1 for d in required if d.status == DocumentStatus.VERIFIED)

        return {
            "header": self.header(batch),
            "kpis": [
                {"id": "total", "value": str(len(docs)), "label": "Total Documents"},
                {"id": "verified", "value": str(counts.get(DocumentStatus.VERIFIED, 0)), "label": "Verified"},
                {"id": "awaiting", "value": str(counts.get(DocumentStatus.AWAITING_VERIFICATION, 0)),
                 "label": "Awaiting Verification"},
                {"id": "changes", "value": str(counts.get(DocumentStatus.CHANGES_REQUESTED, 0)),
                 "label": "Changes Requested"},
                {"id": "missing", "value": str(counts.get(DocumentStatus.MISSING, 0)), "label": "Missing"},
                {"id": "storage", "value": f"{storage / 1024 / 1024:.1f} MB", "label": "Storage Used"},
            ],
            "rows": [self._document_row(d) for d in docs],
            "checklist": [
                {
                    "name": d.name.rsplit(".", 1)[0],
                    "status": DOCUMENT_STATUS_LABELS[d.status],
                    "status_key": d.status.value,
                    "passed": d.status == DocumentStatus.VERIFIED,
                }
                for d in sorted(required, key=lambda d: d.name)
            ],
            "checklist_complete": complete,
            "checklist_total": len(required),
            "queue": [
                self._document_row(d) for d in docs
                if d.status in {DocumentStatus.AWAITING_VERIFICATION, DocumentStatus.CHANGES_REQUESTED}
            ],
            "storage_by_category": [
                {"category": cat, "bytes": size} for cat, size in sorted(by_category.items(), key=lambda kv: -kv[1])
            ],
            "storage_used": storage,
            "categories": sorted({d.category for d in docs}),
            "can_manage": getattr(batch, "_can_manage", False),
            "upload": batch_files.options(),
            "missing_required": batch_files.outstanding(docs),
            "selected": self._document_row(
                next((d for d in docs if d.status == DocumentStatus.AWAITING_VERIFICATION), docs[0]), full=True
            ) if docs else None,
            "recent_activity": [
                {
                    "activity": a.activity,
                    "actor": a.actor_name,
                    "occurred_at": a.occurred_at,
                    "severity": a.severity.value,
                }
                for a in sorted(batch.activities, key=lambda a: a.occurred_at, reverse=True)
                if a.module in {"Documents", "Base Papers"}
            ][:5],
        }

    # The approval path a registration walks, in order. The journey strip
    # shows every stage - including the ones not reached yet - so a reader can
    # see what is still ahead, not only what has happened.
    JOURNEY_STAGES = [
        ("draft", "Draft Completed", None),
        ("submitted", "Submitted for Review", "submitted"),
        ("review_started", "Initial Review", "review_started"),
        ("changes_requested", "Changes Requested", "changes_requested"),
        ("resubmitted", "Resubmitted", "resubmitted"),
        ("documents_verified", "Document Verification", "documents_verified"),
        ("final_review", "Final Review", "final_review"),
        ("approved", "Approved", "approved"),
    ]

    # Which actions each history entry offers, matching what that kind of
    # event actually produced something to look at.
    EVENT_ACTIONS = {
        "submitted": ["view_submission"],
        "review_started": [],
        "changes_requested": ["view_remarks", "compare_changes"],
        "resubmitted": ["view_resubmission"],
        "documents_verified": ["view_documents"],
        "final_review": ["open_review", "add_note"],
        "approved": ["view_decision"],
        "rejected": ["view_decision"],
    }

    def _journey(self, batch: ProjectBatch, events: List) -> List[dict]:
        """
        Every stage with its state: done, current or pending.

        The current stage is the one the most recent event landed on, so a
        batch sent back for changes correctly reads as sitting at "Changes
        Requested" rather than at whatever stage comes next in the list.
        """
        last_by_kind = {}
        for e in events:
            last_by_kind[e.kind.value] = e

        latest = events[-1] if events else None
        rejected = batch.registration_status == BatchRegistrationStatus.REJECTED

        rows = []
        for key, label, kind in self.JOURNEY_STAGES:
            if kind is None:
                occurred, actor = batch.created_at, None
                state = "done"
            else:
                event = last_by_kind.get(kind)
                occurred = event.occurred_at if event else None
                actor = event.actor_role if event else None
                if event is None:
                    state = "pending"
                elif latest is not None and event.id == latest.id:
                    state = "current"
                else:
                    state = "done"

            if key == "approved" and rejected:
                label = "Rejected"

            rows.append({
                "key": key,
                "step": label,
                "kind": kind or "draft",
                "occurred_at": occurred,
                "actor": actor,
                "state": state,
                "done": state == "done",
            })
        return rows

    def _version_comparison(self, batch: ProjectBatch) -> List[dict]:
        """
        What changed between the original submission and the resubmission.

        Built from the audit log's recorded field changes plus any required
        document still outstanding, rather than from stored snapshots - there
        is no version store yet, and inventing one would be worse than
        reporting only what was actually recorded.
        """
        rows = []
        for a in sorted(batch.activities, key=lambda a: a.occurred_at):
            if not a.changed_field:
                continue
            rows.append({
                "field": a.changed_field,
                "original": a.previous_value or "Not recorded",
                "revised": a.current_value or "Not recorded",
                "resolved": True,
                "source": a.module,
            })

        for doc in batch.documents:
            if doc.status == DocumentStatus.MISSING and doc.is_required:
                rows.append({
                    "field": doc.name,
                    "original": "Not uploaded",
                    "revised": "Still outstanding",
                    "resolved": False,
                    "source": "Documents",
                })
            elif doc.status == DocumentStatus.CHANGES_REQUESTED:
                rows.append({
                    "field": doc.name,
                    "original": doc.version or "v1.0",
                    "revised": "Changes requested",
                    "resolved": False,
                    "source": "Documents",
                })
        return rows

    async def approvals(self, batch: ProjectBatch) -> dict:
        events = sorted([e for e in batch.approval_events if not e.is_private], key=lambda e: e.occurred_at)
        private = sorted([e for e in batch.approval_events if e.is_private], key=lambda e: e.occurred_at)
        cycles = len({e.cycle for e in events}) or 1
        changes = sum(1 for e in events if e.kind.value == "changes_requested")
        resubs = sum(1 for e in events if e.kind.value == "resubmitted")
        rejections = sum(1 for e in events if e.kind.value == "rejected")

        checks = self.registration_checklist(batch)
        passed = sum(1 for c in checks if c["passed"])
        blocking = next((c["label"] for c in checks if not c["passed"]), None)

        now = datetime.utcnow()
        total_hours = None
        if batch.submitted_at:
            total_hours = int((now - batch.submitted_at).total_seconds() // 3600)

        sla = None
        if batch.review_due_at:
            hours = int((batch.review_due_at - now).total_seconds() // 3600)
            sla = f"{hours}h remaining" if hours >= 0 else f"Overdue {abs(hours) // 24 or 1}d"

        leader = next((m for m in batch.members if m.is_lead), None)
        submitted_by = leader.student.full_name if leader and leader.student else None
        last_action = events[-1].occurred_at if events else batch.updated_at
        comparison = self._version_comparison(batch)
        participants = [
            {"name": batch.guide.full_name if batch.guide else None, "role": "Faculty Reviewer", "tag": "Reviewer"},
            {"name": leader.student.full_name if leader and leader.student else None,
             "role": "Batch Leader", "tag": "Submitter"},
        ]
        if batch.reviewer and batch.reviewer_id != batch.guide_id:
            participants.append({"name": batch.reviewer.full_name, "role": "Department Coordinator",
                                 "tag": "Coordinator"})

        return {
            "header": self.header(batch),
            "kpis": [
                {"id": "cycles", "value": str(cycles), "label": "Review Cycles"},
                {"id": "changes", "value": str(changes), "label": "Changes Requested"},
                {"id": "resubmissions", "value": str(resubs),
                 "label": "Resubmission" if resubs == 1 else "Resubmissions"},
                {"id": "rejections", "value": str(rejections), "label": "Rejections"},
            ],
            "current_status": STATUS_LABELS.get(batch.registration_status, "Draft"),
            "current_status_key": batch.registration_status.value,
            "total_review_time_hours": total_hours,
            "approval_status": {
                "status": STATUS_LABELS.get(batch.registration_status, "Draft"),
                "status_key": batch.registration_status.value,
                "checks_passed": passed,
                "checks_total": len(checks),
                "percent": int(round(passed / len(checks) * 100)) if checks else 0,
                "reviewer": batch.guide.full_name if batch.guide else None,
                "submitted_by": submitted_by,
                "last_action_at": last_action,
                "sla": sla,
                "blocking_item": blocking,
            },
            "journey": self._journey(batch, events),
            "history": [
                {
                    "id": str(e.id),
                    "kind": e.kind.value,
                    "title": e.title,
                    "body": e.body,
                    # The seeder writes multi-point remarks as newline or
                    # bullet separated text; splitting here keeps the list
                    # formatting out of the component.
                    "bullets": [
                        line.strip(" -\u2022\t")
                        for line in (e.body or "").splitlines()
                        if line.strip(" -\u2022\t")
                    ][1:],
                    "summary": ((e.body or "").splitlines() or [None])[0],
                    "status_label": e.status_label,
                    "actor": e.actor.full_name if e.actor else None,
                    "actor_role": e.actor_role,
                    "occurred_at": e.occurred_at,
                    "duration_minutes": e.duration_minutes,
                    "cycle": e.cycle,
                    "actions": self.EVENT_ACTIONS.get(e.kind.value, []),
                }
                for e in events
            ],
            "internal_notes": [
                {"id": str(e.id), "title": e.title, "body": e.body,
                 "actor": e.actor.full_name if e.actor else None, "occurred_at": e.occurred_at}
                for e in private
            ],
            "comparison": comparison,
            "comparison_resolved": sum(1 for c in comparison if c["resolved"]),
            "checklist": checks,
            "checks_passed": passed,
            "checks_total": len(checks),
            "blocking_item": blocking,
            "sla": sla,
            "participants": [p for p in participants if p["name"]],
            "decision_summary": {
                "approvals": sum(1 for e in events if e.kind.value == "approved"),
                "change_requests": changes,
                "resubmissions": resubs,
                "rejections": rejections,
                **self._turnaround(events),
            },
        }


    @staticmethod
    def _turnaround(events: List) -> dict:
        """
        Average student response = changes requested -> resubmitted.
        Average faculty review  = submitted/resubmitted -> the next faculty action.
        Measured off the event stream, so it stays true as cycles are added.
        """
        student_gaps, faculty_gaps = [], []
        pending_change = pending_submit = None

        for e in events:
            kind = e.kind.value
            if kind == "changes_requested":
                pending_change = e.occurred_at
            elif kind == "resubmitted":
                if pending_change:
                    student_gaps.append((e.occurred_at - pending_change).total_seconds() / 3600)
                    pending_change = None
                pending_submit = e.occurred_at
            elif kind == "submitted":
                pending_submit = e.occurred_at
            elif kind in {"review_started", "documents_verified", "final_review", "approved", "rejected"}:
                if pending_submit:
                    faculty_gaps.append((e.occurred_at - pending_submit).total_seconds() / 3600)
                    pending_submit = None

        def avg(values):
            return round(sum(values) / len(values), 1) if values else None

        return {
            "avg_student_response_hours": avg(student_gaps),
            "avg_faculty_review_hours": avg(faculty_gaps),
        }


    @staticmethod
    def _parse_day(value: Optional[str]) -> Optional[datetime]:
        """A bad date should narrow nothing rather than 500 the whole tab."""
        if not value:
            return None
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return None

    async def activity(
        self, batch: ProjectBatch, *, module: Optional[str] = None, severity: Optional[str] = None,
        actor: Optional[str] = None, search: Optional[str] = None,
        date_from: Optional[str] = None, date_to: Optional[str] = None,
        page: int = 1, per_page: int = 10,
    ) -> dict:
        rows = sorted(batch.activities, key=lambda a: a.occurred_at, reverse=True)
        # Date bounds arrive as YYYY-MM-DD from the picker; the "to" bound is
        # inclusive of that whole day, which is what a reader expects.
        start_at = self._parse_day(date_from)
        end_at = self._parse_day(date_to)
        if end_at:
            end_at += timedelta(days=1)

        def keep(a: ActivityLog) -> bool:
            if start_at and a.occurred_at < start_at:
                return False
            if end_at and a.occurred_at >= end_at:
                return False
            if module and a.module != module:
                return False
            if severity and a.severity.value != severity:
                return False
            if actor and (a.actor_name or "") != actor:
                return False
            if search:
                needle = search.lower()
                blob = " ".join(filter(None, [a.activity, a.details, a.actor_name, a.module])).lower()
                if needle not in blob:
                    return False
            return True

        scoped = [a for a in rows if keep(a)]
        by_module = Counter(a.module for a in rows)
        by_actor = Counter(a.actor_name or "System" for a in rows)
        by_role = Counter(a.actor_role or "System" for a in rows)

        total = len(scoped)
        pages = max(1, -(-total // per_page)) if total else 1
        current = min(max(page, 1), pages)
        start = (current - 1) * per_page
        window = scoped[start:start + per_page]

        return {
            "header": self.header(batch),
            "kpis": [
                {"id": "total", "value": str(len(rows)), "label": "Total Activities"},
                {"id": "student", "value": str(by_role.get("Student", 0) + by_role.get("Batch Leader", 0)),
                 "label": "Student Actions"},
                {"id": "documents", "value": str(by_module.get("Documents", 0)), "label": "Document Actions"},
                {"id": "faculty", "value": str(by_role.get("Faculty", 0)), "label": "Faculty Actions"},
                {"id": "system", "value": str(by_role.get("System", 0)), "label": "System Events"},
                {"id": "audit", "value": str(sum(1 for a in rows if a.severity.value in {"warning", "critical"})),
                 "label": "Audit Events"},
            ],
            "rows": [self._activity_row(a) for a in window],
            "page": current, "pages": pages, "per_page": per_page, "total": total,
            "showing_from": (start + 1) if total else 0,
            "showing_to": min(start + per_page, total),
            "summary": [{"module": m, "count": c} for m, c in by_module.most_common()],
            "participants": [{"name": n, "count": c} for n, c in by_actor.most_common()],
            "high_priority": [
                {"activity": a.activity, "severity": a.severity.value, "occurred_at": a.occurred_at}
                for a in rows if a.severity.value in {"warning", "critical"}
            ][:5],
            "modules": sorted(by_module),
            "actors": sorted(by_actor),
            "selected": self._activity_row(window[0]) if window else None,
            "last_integrity_check": rows[0].occurred_at if rows else None,
        }

    # ------------------------------------------------------------- fragments

    @staticmethod
    def _ordered_members(batch: ProjectBatch) -> List[ProjectBatchMember]:
        return sorted(batch.members, key=lambda m: (not m.is_lead, m.joined_at or m.created_at))

    async def _profile_state(self, student_ids: List[str]) -> Dict[str, StudentEnrollment]:
        if not student_ids:
            return {}
        rows = (await self.db.execute(
            select(StudentEnrollment).where(StudentEnrollment.student_id.in_(student_ids))
        )).scalars().all()
        return {str(r.student_id): r for r in rows}

    def _member_row(self, member: ProjectBatchMember, full: bool = False) -> dict:
        user: Optional[User] = member.student
        verified = bool(user and user.phone and user.email)
        row = {
            "id": str(member.id),
            "student_id": str(member.student_id),
            "name": user.full_name if user else None,
            "roll_number": user.roll_number if user else None,
            "role": "Batch Leader" if member.is_lead else "Member",
            "responsibility": member.responsibility,
            "mobile": user.phone if user else None,
            "email": user.email if user else None,
            "department": user.department if user else None,
            "section": user.section if user else None,
            "profile_verified": verified,
            "is_active": member.is_active,
        }
        if full:
            row.update({
                "joined_at": member.joined_at or member.created_at,
                "profile_completion": 100 if verified else 60,
                "declaration_signed": verified,
            })
        return row

    def _paper_summary(self, batch: ProjectBatch, full: bool = False) -> Optional[dict]:
        bp = batch.base_paper
        if bp is None:
            return None
        base = {
            "title": bp.title,
            "authors": bp.authors,
            "publication": bp.publication,
            "year": bp.year,
            "doi": bp.doi,
            "url": bp.url,
            "status": bp.status.value,
            "verified_by": bp.verified_by_id and (batch.guide.full_name if batch.guide else None),
            "verified_at": bp.verified_at,
            "improvement_note": bp.improvement_note,
            # Distinct from `url`, which is a link to where the paper was
            # published. This says whether we hold the PDF ourselves.
            "has_file": bp.file_id is not None,
        }
        if not full:
            return base
        base.update({
            "publisher": bp.publisher,
            "publication_type": bp.publication_type,
            "volume": bp.volume,
            "pages": bp.pages,
            "indexing": bp.indexing,
            "quartile": bp.quartile,
            "file_name": bp.file_name,
            "file_size": bp.file_size,
            "page_count": bp.page_count,
            "uploaded_by": bp.uploaded_by.full_name if bp.uploaded_by else None,
            "uploaded_at": bp.uploaded_at,
            "abstract_summary": bp.abstract_summary,
            "dataset": bp.dataset,
            "key_methods": [m.name for m in sorted(bp.key_methods, key=lambda m: m.position)],
            "metrics": [{"name": m.name, "value": m.value}
                        for m in sorted(bp.metrics, key=lambda m: m.position)],
        })
        return base

    @staticmethod
    def _document_row(doc: BatchDocument, full: bool = False) -> dict:
        row = {
            "id": str(doc.id),
            "name": doc.name,
            "category": doc.category,
            "version": doc.version if doc.status != DocumentStatus.MISSING else None,
            "uploaded_by": doc.uploaded_by.full_name if doc.uploaded_by else None,
            "uploaded_at": doc.uploaded_at if doc.status != DocumentStatus.MISSING else None,
            "file_size": doc.file_size,
            "status": DOCUMENT_STATUS_LABELS[doc.status],
            "status_key": doc.status.value,
            "similarity_percent": doc.similarity_percent,
            "is_required": doc.is_required,
            # Whether there are actually bytes behind this row. A download
            # button that appears when there is no file is a promise the
            # server cannot keep.
            "has_file": doc.file_id is not None,
            "superseded": doc.superseded_by_id is not None,
            "can_remove": (doc.status != DocumentStatus.VERIFIED
                           and doc.superseded_by_id is None
                           and doc.file_id is not None),
        }
        if full:
            row.update({
                "page_count": doc.page_count,
                "faculty_note": doc.faculty_note,
                "virus_scan_passed": doc.virus_scan_passed,
                "file": file_store.describe(doc.file),
            })
        return row

    @staticmethod
    def _activity_row(a: ActivityLog) -> dict:
        """
        Every row carries its full detail. The list used to ship a trimmed
        shape and give only the pre-selected row the audit fields, which left
        the detail panel blank for every row the reader actually clicked.
        """
        return {
            "id": str(a.id),
            "event_code": a.event_code,
            "occurred_at": a.occurred_at,
            "actor": a.actor_name,
            "actor_role": a.actor_role,
            "activity": a.activity,
            "module": a.module,
            "details": a.details,
            "status_label": a.status_label,
            "severity": a.severity.value,
            "ip_address": a.ip_address,
            "user_agent": a.user_agent,
            "source": a.source,
            "changed_field": a.changed_field,
            "previous_value": a.previous_value,
            "current_value": a.current_value,
        }


    def _module_activity(self, batch: ProjectBatch, modules: set, limit: int = 8) -> List[dict]:
        """Activity for one area of the batch, oldest first - drives the
        per-tab history strips. Derived from the audit log rather than a
        second, divergent source of truth."""
        rows = sorted(
            (a for a in batch.activities if a.module in modules),
            key=lambda a: a.occurred_at,
        )
        return [
            {
                "step": a.activity,
                "occurred_at": a.occurred_at,
                "actor": a.actor_name,
                "done": True,
            }
            for a in rows[:limit]
        ]

    def _registration_timeline(self, batch: ProjectBatch) -> List[dict]:
        members = self._ordered_members(batch)
        bp = batch.base_paper
        created = batch.created_at
        steps = [
            ("Batch Created", created, batch.guide.full_name if batch.guide else None),
            ("Members Joined", members[-1].joined_at if members else None,
             members[0].student.full_name if members and members[0].student else None),
            ("Project Details Added", created and (created.replace(microsecond=0)), None),
            ("Base Paper Uploaded", bp.uploaded_at if bp else None,
             bp.uploaded_by.full_name if bp and bp.uploaded_by else None),
            ("Guide Assigned", created, batch.guide.full_name if batch.guide else None),
            ("Submitted for Approval", batch.submitted_at, None),
        ]
        return [
            {"step": label, "occurred_at": when, "actor": actor, "done": when is not None}
            for label, when, actor in steps
        ]

    def _team_timeline(self, batch: ProjectBatch, members: List[ProjectBatchMember]) -> List[dict]:
        out = [{
            "step": "Batch created",
            "occurred_at": batch.created_at,
            "actor": members[0].student.full_name if members and members[0].student else None,
            "done": True,
        }]
        for member in members[1:]:
            name = member.student.full_name.split(" ")[0] if member.student and member.student.full_name else "Member"
            out.append({"step": f"{name} joined", "occurred_at": member.joined_at or member.created_at,
                        "actor": None, "done": True})
        out.append({"step": "All profiles verified",
                    "occurred_at": members[-1].joined_at if members else None,
                    "actor": None,
                    "done": all(m.student and m.student.phone for m in members)})
        out.append({"step": "Team submitted", "occurred_at": batch.submitted_at, "actor": None,
                    "done": batch.submitted_at is not None})
        return out
