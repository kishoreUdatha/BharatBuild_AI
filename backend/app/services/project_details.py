"""
Entering a project's details.

The Project Details tab has always been able to *show* a title, abstract,
objectives, methodology, scope, technology stack and duration - the seeder put
them there. Nothing in the application could write them, so a batch created
through the app stayed permanently blank and the student journey stopped dead
at "Project Setup", whose gate is `batch.title`.

Both portals write through this module. The team proposes and submits; a guide
may correct. Keeping the rules here rather than in either endpoint is what
stops the two doors from drifting - the same reason `batch_actions` exists.

Authority is the caller's job: every function assumes the caller has already
established that this user may act on this batch.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_detail import (
    ActivitySeverity,
    ApprovalEvent,
    ApprovalEventKind,
    ItemStatus,
    ProjectMethodologyStep,
    ProjectObjective,
    ProjectScopeItem,
    ProjectTechnology,
    ScopeKind,
)
from app.models.faculty import BatchRegistrationStatus, ProjectBatch
from app.models.user import User
from app.services import activity_log

# How long a guide has to respond once a batch submits.
REVIEW_SLA_DAYS = 3

PROJECT_TYPES = ["Major Project", "Minor Project", "Capstone", "Research Project"]

# Offered as suggestions in the form; the column is free text because a stack
# is not something a project registration system should be able to veto.
SUGGESTED_LAYERS = [
    "Frontend", "Backend", "Database", "Machine Learning",
    "Infrastructure", "Hardware", "Tooling",
]

# Ceilings, not targets. They exist so a form post cannot write ten thousand
# rows, and sit well above what any real registration needs.
LIMITS = {
    "keywords": 12,
    "objectives": 12,
    "methodology": 12,
    "scope": 20,
    "technologies": 40,
}

MIN_OBJECTIVES = 3
MIN_ABSTRACT = 120

# Editing is refused in these states: an approved registration is a record of
# what was approved, and one sitting with a guide must not change underneath
# the person reading it.
_IN_REVIEW = ("This is with your guide for review. Wait for their response, or ask "
              "them to send it back.")
LOCKED_STATES = {
    BatchRegistrationStatus.APPROVED: "This registration is approved; its details are now fixed.",
    BatchRegistrationStatus.SUBMITTED: _IN_REVIEW,
    BatchRegistrationStatus.PENDING_APPROVAL: _IN_REVIEW,
}


class ProjectDetailsError(Exception):
    """A refusal the caller can show the user as-is."""

    def __init__(self, message: str, unmet: Optional[List[str]] = None):
        super().__init__(message)
        self.unmet = unmet or []


# ------------------------------------------------------------------ checklist

def completeness(batch: ProjectBatch) -> List[dict]:
    """
    The eight things a project registration must state.

    This is the single definition. The Project Details tab renders it and
    `submit` refuses on it, so the panel that says "6 of 8" and the button that
    refuses are reading the same eight answers rather than two lists that
    happen to agree today.
    """
    by_kind: Dict[str, List[str]] = {k.value: [] for k in ScopeKind}
    for item in batch.scope_items:
        by_kind[item.kind.value].append(item.text)

    return [
        {"key": "title", "label": "Title unique", "passed": bool(batch.title),
         "hint": "Give the project a title."},
        {"key": "problem", "label": "Problem statement clear",
         "passed": bool(batch.problem_statement),
         "hint": "State the problem the project addresses."},
        {"key": "abstract", "label": "Abstract complete",
         "passed": len((batch.abstract or "").strip()) >= MIN_ABSTRACT,
         "hint": "Write an abstract of at least %d characters." % MIN_ABSTRACT},
        {"key": "objectives", "label": "Objectives measurable",
         "passed": len(batch.objectives) >= MIN_OBJECTIVES,
         "hint": "List at least %d objectives." % MIN_OBJECTIVES},
        {"key": "methodology", "label": "Methodology provided",
         "passed": len(batch.methodology) > 0,
         "hint": "Add at least one methodology step."},
        {"key": "stack", "label": "Technology stack defined",
         "passed": len(batch.technologies) > 0,
         "hint": "Name at least one technology you will use."},
        {"key": "outcome", "label": "Expected outcome defined",
         "passed": bool(by_kind["outcome"]),
         "hint": "State at least one expected outcome."},
        {"key": "scope", "label": "Scope and deliverables listed",
         "passed": bool(by_kind["in_scope"] and by_kind["deliverable"]),
         "hint": "List what is in scope and what you will deliver."},
    ]


def editable(batch: ProjectBatch) -> Optional[str]:
    """The reason editing is refused, or None when it is allowed."""
    return LOCKED_STATES.get(batch.registration_status)


# ----------------------------------------------------------------------- read

def form(batch: ProjectBatch) -> dict:
    """The current values, shaped for a form rather than for display."""
    by_kind: Dict[str, List[str]] = {k.value: [] for k in ScopeKind}
    for item in sorted(batch.scope_items, key=lambda s: s.position):
        by_kind[item.kind.value].append(item.text)

    checks = completeness(batch)
    lock = editable(batch)

    return {
        "batch_code": batch.batch_code,
        "status": batch.registration_status.value,
        "locked": lock is not None,
        "locked_reason": lock,
        "title": batch.title,
        "domain": batch.domain,
        "project_type": batch.project_type,
        "keywords": [k.strip() for k in (batch.keywords or "").split(",") if k.strip()],
        "problem_statement": batch.problem_statement,
        "abstract": batch.abstract,
        "objectives": [
            {"text": o.text, "status": o.status.value}
            for o in sorted(batch.objectives, key=lambda o: o.position)
        ],
        "methodology": [
            {"title": s.title, "description": s.description}
            for s in sorted(batch.methodology, key=lambda s: s.position)
        ],
        "outcomes": by_kind["outcome"],
        "in_scope": by_kind["in_scope"],
        "out_of_scope": by_kind["out_of_scope"],
        "deliverables": by_kind["deliverable"],
        "technologies": [
            {"layer": t.layer, "name": t.name}
            for t in sorted(batch.technologies, key=lambda t: (t.layer, t.position))
        ],
        "start_date": batch.start_date,
        "target_completion": batch.target_completion,
        "weekly_effort_hours": batch.weekly_effort_hours,
        "checklist": checks,
        "checks_passed": sum(1 for c in checks if c["passed"]),
        "checks_total": len(checks),
        # Two different questions, and conflating them made a finished
        # registration report as incomplete the moment it was locked.
        # `complete` is about the eight answers; `can_submit` is about whether
        # this reader may act right now.
        "complete": all(c["passed"] for c in checks),
        "can_submit": all(c["passed"] for c in checks) and lock is None,
        "options": {
            "project_types": PROJECT_TYPES,
            "layers": SUGGESTED_LAYERS,
            "objective_statuses": [s.value for s in ItemStatus],
            "limits": LIMITS,
        },
    }


# ------------------------------------------------------------------- coercion

def _text(value: Any, limit: int, field: str) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if len(cleaned) > limit:
        raise ProjectDetailsError("%s is longer than %d characters." % (field, limit))
    return cleaned


def _lines(value: Any, cap: int, limit: int, field: str) -> List[str]:
    """Non-empty single-line entries, de-duplicated, order kept."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProjectDetailsError("%s must be a list." % field)
    out: List[str] = []
    seen = set()
    for raw in value:
        cleaned = _text(raw, limit, field)
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    if len(out) > cap:
        raise ProjectDetailsError("%s allows at most %d entries." % (field, cap))
    return out


def _as_date(value: Any, field: str) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ProjectDetailsError("%s must be a date like 2026-01-31." % field)


# ---------------------------------------------------------------------- write

async def save(
    db: AsyncSession,
    batch: ProjectBatch,
    payload: Dict[str, Any],
    actor: Optional[User],
    actor_role: Optional[str] = None,
    source: str = "Web",
) -> dict:
    """
    Write the whole form.

    Deliberately permissive: a team fills this in over several sittings, so a
    partial save is a normal act rather than an error. Completeness is enforced
    at `submit`, which is the moment the claim is actually made.
    """
    lock = editable(batch)
    if lock:
        raise ProjectDetailsError(lock)

    before = _snapshot(batch)

    # Only fields the caller actually sent are touched. A key that is absent is
    # left alone; a key sent as null or "" is a deliberate clear. Reading every
    # field with .get() instead would let a form that saves one card silently
    # erase the cards it did not include.
    def sent(field: str) -> bool:
        return field in payload

    if sent("title"):
        batch.title = _text(payload["title"], 255, "Title")
    if sent("domain"):
        batch.domain = _text(payload["domain"], 160, "Domain")

    if sent("project_type"):
        project_type = _text(payload["project_type"], 50, "Project type")
        if project_type is not None:
            if project_type not in PROJECT_TYPES:
                raise ProjectDetailsError(
                    "Project type must be one of %s." % ", ".join(PROJECT_TYPES))
            batch.project_type = project_type

    if sent("keywords"):
        keywords = _lines(payload["keywords"], LIMITS["keywords"], 40, "Keywords")
        joined = ", ".join(keywords)
        if len(joined) > 400:
            raise ProjectDetailsError("Those keywords are too long together; use shorter ones.")
        batch.keywords = joined or None

    if sent("problem_statement"):
        batch.problem_statement = _text(payload["problem_statement"], 4000, "Problem statement")
    if sent("abstract"):
        batch.abstract = _text(payload["abstract"], 6000, "Abstract")

    # Validated as a pair against whatever the batch will end up holding, so
    # moving only the start date cannot slip past the ordering rule.
    start = (_as_date(payload["start_date"], "Start date")
             if sent("start_date") else batch.start_date)
    target = (_as_date(payload["target_completion"], "Target completion")
              if sent("target_completion") else batch.target_completion)
    if start and target and target <= start:
        raise ProjectDetailsError("Target completion has to fall after the start date.")
    batch.start_date = start
    batch.target_completion = target

    if sent("weekly_effort_hours"):
        hours = payload["weekly_effort_hours"]
        if hours in (None, ""):
            batch.weekly_effort_hours = None
        else:
            try:
                hours = int(hours)
            except (TypeError, ValueError):
                raise ProjectDetailsError("Weekly effort must be a whole number of hours.")
            if not 1 <= hours <= 60:
                raise ProjectDetailsError(
                    "Weekly effort should be between 1 and 60 hours a student.")
            batch.weekly_effort_hours = hours

    await _replace_objectives(db, batch, payload.get("objectives"))
    await _replace_methodology(db, batch, payload.get("methodology"))
    await _replace_scope(db, batch, payload)
    await _replace_technologies(db, batch, payload.get("technologies"))

    batch.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(batch, ["objectives", "methodology", "scope_items", "technologies"])

    after = _snapshot(batch)
    changed = _changed_fields(before, after)
    if changed:
        single = changed[0] if len(changed) == 1 else None
        await activity_log.record(
            db,
            batch_id=batch.id,
            activity="Updated project details",
            module="Registration",
            actor=actor,
            actor_role=actor_role,
            details="Changed " + ", ".join(changed),
            status_label="Draft Saved",
            severity=ActivitySeverity.INFO,
            changed_field=single,
            previous_value=before.get(single) if single else None,
            current_value=after.get(single) if single else None,
            source=source,
        )

    await db.commit()
    await db.refresh(batch, ["objectives", "methodology", "scope_items", "technologies"])
    result = form(batch)
    result["changed_fields"] = changed
    return result


async def submit(
    db: AsyncSession,
    batch: ProjectBatch,
    actor: Optional[User],
    actor_role: str = "Batch Leader",
    note: Optional[str] = None,
    source: str = "Web",
) -> dict:
    """
    Send the registration to the guide.

    Refuses on the same eight checks the tab displays, and names the ones that
    are unmet - a button that only greys out leaves the team guessing which of
    eight things is missing.
    """
    if batch.registration_status == BatchRegistrationStatus.APPROVED:
        raise ProjectDetailsError("This registration is already approved.")
    if batch.registration_status in (BatchRegistrationStatus.SUBMITTED,
                                     BatchRegistrationStatus.PENDING_APPROVAL):
        raise ProjectDetailsError("This is already with your guide for review.")

    checks = completeness(batch)
    unmet = [c for c in checks if not c["passed"]]
    if unmet:
        raise ProjectDetailsError(
            "Finish these before submitting: " + "; ".join(c["hint"] for c in unmet),
            [c["key"] for c in unmet],
        )

    resubmission = batch.registration_status in (
        BatchRegistrationStatus.CHANGES_REQUESTED, BatchRegistrationStatus.REJECTED
    )
    highest = (await db.execute(
        select(func.max(ApprovalEvent.cycle)).where(ApprovalEvent.batch_id == batch.id)
    )).scalar() or 0
    cycle = highest + 1 if (resubmission or highest == 0) else highest

    now = datetime.utcnow()
    batch.registration_status = BatchRegistrationStatus.SUBMITTED
    batch.submitted_at = now
    batch.review_due_at = now + timedelta(days=REVIEW_SLA_DAYS)
    batch.resolved_at = None

    db.add(ApprovalEvent(
        batch_id=batch.id,
        cycle=cycle,
        kind=ApprovalEventKind.RESUBMITTED if resubmission else ApprovalEventKind.SUBMITTED,
        title="Registration resubmitted" if resubmission else "Registration submitted",
        body=note or ("Project details revised and sent back for review."
                      if resubmission else "Project details submitted for approval."),
        status_label="Submitted",
        actor_id=actor.id if actor else None,
        actor_role=actor_role,
        occurred_at=now,
    ))

    await activity_log.record(
        db,
        batch_id=batch.id,
        activity="Resubmitted registration" if resubmission else "Submitted registration",
        module="Registration",
        actor=actor,
        actor_role=actor_role,
        details=note or ("All %d project checks passed." % len(checks)),
        status_label="Submitted",
        severity=ActivitySeverity.SUCCESS,
        changed_field="registration_status",
        previous_value="Changes Requested" if resubmission else "Draft",
        current_value="Submitted",
        source=source,
    )

    await db.commit()
    await db.refresh(batch, ["objectives", "methodology", "scope_items", "technologies"])
    return {
        "status": batch.registration_status.value,
        "submitted_at": batch.submitted_at,
        "review_due_at": batch.review_due_at,
        "cycle": cycle,
        "resubmission": resubmission,
        "message": ("Resubmitted. Your guide has the revised registration."
                    if resubmission else
                    "Submitted. Your guide has three working days to review it."),
    }


# ---------------------------------------------------------- child replacement

async def _replace_objectives(db: AsyncSession, batch: ProjectBatch, raw: Any) -> None:
    if raw is None:
        return
    if not isinstance(raw, list):
        raise ProjectDetailsError("Objectives must be a list.")
    rows = []
    for entry in raw:
        if isinstance(entry, str):
            entry = {"text": entry}
        if not isinstance(entry, dict):
            raise ProjectDetailsError("Each objective must be text.")
        text = _text(entry.get("text"), 600, "Objective")
        if text is None:
            continue
        status = str(entry.get("status") or ItemStatus.PENDING.value).lower()
        try:
            status_enum = ItemStatus(status)
        except ValueError:
            raise ProjectDetailsError(
                "Objective status must be one of %s."
                % ", ".join(s.value for s in ItemStatus))
        rows.append((text, status_enum))
    if len(rows) > LIMITS["objectives"]:
        raise ProjectDetailsError("At most %d objectives." % LIMITS["objectives"])

    await db.execute(delete(ProjectObjective).where(ProjectObjective.batch_id == batch.id))
    for i, (text, status_enum) in enumerate(rows):
        db.add(ProjectObjective(batch_id=batch.id, position=i, text=text, status=status_enum))


async def _replace_methodology(db: AsyncSession, batch: ProjectBatch, raw: Any) -> None:
    if raw is None:
        return
    if not isinstance(raw, list):
        raise ProjectDetailsError("Methodology must be a list.")
    rows = []
    for entry in raw:
        if isinstance(entry, str):
            entry = {"title": entry}
        if not isinstance(entry, dict):
            raise ProjectDetailsError("Each methodology step needs a title.")
        title = _text(entry.get("title"), 120, "Methodology step")
        if title is None:
            continue
        rows.append((title, _text(entry.get("description"), 1000, "Methodology description")))
    if len(rows) > LIMITS["methodology"]:
        raise ProjectDetailsError("At most %d methodology steps." % LIMITS["methodology"])

    await db.execute(
        delete(ProjectMethodologyStep).where(ProjectMethodologyStep.batch_id == batch.id))
    for i, (title, description) in enumerate(rows):
        db.add(ProjectMethodologyStep(batch_id=batch.id, position=i,
                                      title=title, description=description))


SCOPE_FIELDS = {
    "in_scope": ScopeKind.IN_SCOPE,
    "out_of_scope": ScopeKind.OUT_OF_SCOPE,
    "deliverables": ScopeKind.DELIVERABLE,
    "outcomes": ScopeKind.OUTCOME,
}


async def _replace_scope(db: AsyncSession, batch: ProjectBatch, payload: Dict[str, Any]) -> None:
    """
    Only the kinds actually sent are replaced, so saving the scope card cannot
    silently wipe the expected-outcomes card that was not part of that form.
    """
    for field, kind in SCOPE_FIELDS.items():
        if payload.get(field) is None:
            continue
        items = _lines(payload[field], LIMITS["scope"], 400, field.replace("_", " "))
        await db.execute(
            delete(ProjectScopeItem)
            .where(ProjectScopeItem.batch_id == batch.id)
            .where(ProjectScopeItem.kind == kind)
        )
        for i, text in enumerate(items):
            db.add(ProjectScopeItem(batch_id=batch.id, kind=kind, position=i, text=text))


async def _replace_technologies(db: AsyncSession, batch: ProjectBatch, raw: Any) -> None:
    if raw is None:
        return
    if not isinstance(raw, list):
        raise ProjectDetailsError("Technologies must be a list.")
    rows = []
    seen = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ProjectDetailsError("Each technology needs a layer and a name.")
        name = _text(entry.get("name"), 80, "Technology")
        if name is None:
            continue
        layer = _text(entry.get("layer"), 60, "Layer") or "Other"
        key = (layer.lower(), name.lower())
        if key in seen:
            continue
        seen.add(key)
        rows.append((layer, name))
    if len(rows) > LIMITS["technologies"]:
        raise ProjectDetailsError("At most %d technologies." % LIMITS["technologies"])

    await db.execute(delete(ProjectTechnology).where(ProjectTechnology.batch_id == batch.id))
    counters: Dict[str, int] = {}
    for layer, name in rows:
        position = counters.get(layer, 0)
        counters[layer] = position + 1
        db.add(ProjectTechnology(batch_id=batch.id, layer=layer, name=name, position=position))


# -------------------------------------------------------------- change summary

def _snapshot(batch: ProjectBatch) -> Dict[str, Optional[str]]:
    """A flat before/after picture, used only to describe what changed."""
    by_kind: Dict[str, List[str]] = {k.value: [] for k in ScopeKind}
    for item in batch.scope_items:
        by_kind[item.kind.value].append(item.text)
    return {
        "title": batch.title,
        "domain": batch.domain,
        "project type": batch.project_type,
        "keywords": batch.keywords,
        "problem statement": batch.problem_statement,
        "abstract": batch.abstract,
        "start date": str(batch.start_date) if batch.start_date else None,
        "target completion": str(batch.target_completion) if batch.target_completion else None,
        "weekly effort": str(batch.weekly_effort_hours) if batch.weekly_effort_hours else None,
        "objectives": " | ".join(o.text for o in sorted(batch.objectives, key=lambda o: o.position)),
        "methodology": " | ".join(s.title for s in sorted(batch.methodology,
                                                         key=lambda s: s.position)),
        "in scope": " | ".join(by_kind["in_scope"]),
        "out of scope": " | ".join(by_kind["out_of_scope"]),
        "deliverables": " | ".join(by_kind["deliverable"]),
        "expected outcomes": " | ".join(by_kind["outcome"]),
        "technology stack": " | ".join("%s:%s" % (t.layer, t.name) for t in batch.technologies),
    }


def _changed_fields(before: Dict[str, Optional[str]],
                    after: Dict[str, Optional[str]]) -> List[str]:
    return [k for k in before if (before.get(k) or "") != (after.get(k) or "")]
