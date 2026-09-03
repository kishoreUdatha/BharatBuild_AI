"""
Where each platform trainer teaches.

Trainers are BharatBuild's own staff, so who works at which college is the
platform operator's decision, not a customer's - a college should not be able
to grant itself somebody else's trainer, nor take one away.

An assignment is the *only* thing that gives a trainer reach: with none they
see an empty system. Everything here is therefore a permission change, and is
written to the log with who made it.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.college import College
from app.models.faculty import ProjectBatch
from app.models.trainer_assignment import TrainerAssignment
from app.models.user import User, UserRole
from app.modules.auth.dependencies import get_platform_staff

router = APIRouter(prefix="/trainer-assignments", tags=["Admin - Trainer Assignments"])


def _default_year() -> str:
    from datetime import date
    today = date.today()
    start = today.year if today.month >= 6 else today.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


class AssignmentIn(BaseModel):
    trainer_id: str
    college_id: str
    # Optional narrowing, rarely used: a trainer normally takes the whole
    # college, and naming each branch is data entry that goes stale when the
    # college adds one.
    department: Optional[str] = Field(None, max_length=100)
    section: Optional[str] = Field(None, max_length=10)
    academic_year: Optional[str] = None


@router.get("")
async def list_assignments(
    academic_year: Optional[str] = Query(None),
    trainer_id: Optional[str] = Query(None),
    current_user: User = Depends(get_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Every trainer and where they teach, with what each assignment reaches.

    The batch count is the point of the screen: an assignment to a section
    with no batches looks identical to a correct one until somebody notices
    the trainer has nothing to do.
    """
    year = academic_year or _default_year()

    trainers = (await db.execute(
        select(User).where(User.role == UserRole.TRAINER).order_by(User.full_name)
    )).scalars().all()
    if trainer_id:
        trainers = [t for t in trainers if str(t.id) == trainer_id]

    colleges = {str(c.id): c for c in (await db.execute(
        select(College)
        .where(College.is_active.is_(True))
        .where(College.is_self_serve.is_(False))
        .order_by(College.name)
    )).scalars().all()}

    rows = (await db.execute(
        select(TrainerAssignment)
        .where(TrainerAssignment.academic_year == year)
        .where(TrainerAssignment.is_active.is_(True))
        .order_by(TrainerAssignment.department, TrainerAssignment.section)
    )).scalars().all()

    # One grouped count rather than a query per assignment.
    counts = {
        (str(cid), dept, sec): n
        for cid, dept, sec, n in (await db.execute(
            select(ProjectBatch.college_id, ProjectBatch.department,
                   ProjectBatch.section, func.count())
            .where(ProjectBatch.academic_year == year)
            .group_by(ProjectBatch.college_id, ProjectBatch.department,
                      ProjectBatch.section)
        )).all()
    }

    def reach(a: TrainerAssignment) -> int:
        """How many batches this assignment actually reaches."""
        if not a.department:
            return sum(n for (cid, _, _), n in counts.items()
                       if cid == str(a.college_id))
        if a.section:
            return counts.get((str(a.college_id), a.department, a.section), 0)
        return sum(n for (cid, dept, _), n in counts.items()
                   if cid == str(a.college_id) and dept == a.department)

    by_trainer: dict = {}
    for a in rows:
        by_trainer.setdefault(str(a.trainer_id), []).append({
            "id": str(a.id),
            "college_id": str(a.college_id),
            "college": (colleges[str(a.college_id)].name
                        if str(a.college_id) in colleges else "Unknown college"),
            "department": a.department,
            "section": a.section,
            "label": ("Whole college" if not a.department
                      else f"{a.department}-{a.section}" if a.section
                      else f"{a.department} (whole branch)"),
            "batches": reach(a),
        })

    return {
        "academic_year": year,
        "trainers": [
            {
                "id": str(t.id),
                "name": t.full_name or t.email.split("@")[0],
                "email": t.email,
                "is_active": t.is_active,
                "assignments": by_trainer.get(str(t.id), []),
                "colleges": len({x["college_id"]
                                 for x in by_trainer.get(str(t.id), [])}),
                "batches": sum(x["batches"] for x in by_trainer.get(str(t.id), [])),
            }
            for t in trainers
        ],
        "colleges": [
            {"id": str(c.id), "name": c.name, "code": c.code}
            for c in colleges.values()
        ],
        # What each college actually runs, so the form offers branches and
        # sections that exist rather than a free-text box that quietly
        # produces an assignment reaching nothing.
        "structure": _structure(counts, colleges),
        "unassigned": [
            {"id": str(t.id), "name": t.full_name or t.email}
            for t in trainers if not by_trainer.get(str(t.id))
        ],
    }


def _structure(counts: dict, colleges: dict) -> dict:
    out: dict = {}
    for (college_id, department, section), n in counts.items():
        if college_id not in colleges:
            continue
        dept = out.setdefault(college_id, {}).setdefault(department, [])
        if section and section not in dept:
            dept.append(section)
    return {cid: {d: sorted(s) for d, s in depts.items()}
            for cid, depts in out.items()}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_assignment(
    body: AssignmentIn,
    current_user: User = Depends(get_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Give a trainer a college.

    Everything in it follows - every branch, every section, and any added
    later. A branch or section may be named to narrow it, but that is the
    exception.
    """
    year = body.academic_year or _default_year()

    trainer = (await db.execute(
        select(User).where(User.id == body.trainer_id))).scalars().first()
    if trainer is None or trainer.role != UserRole.TRAINER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="That account is not a trainer.")

    college = (await db.execute(
        select(College).where(College.id == body.college_id))).scalars().first()
    if college is None or college.is_self_serve or not college.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Choose an active college.")

    section = (body.section or "").strip() or None
    department = (body.department or "").strip() or None

    existing = (await db.execute(
        select(TrainerAssignment)
        .where(TrainerAssignment.trainer_id == trainer.id)
        .where(TrainerAssignment.college_id == college.id)
        .where(TrainerAssignment.department.is_(None) if department is None
               else TrainerAssignment.department == department)
        .where(TrainerAssignment.section.is_(None) if section is None
               else TrainerAssignment.section == section)
        .where(TrainerAssignment.academic_year == year)
    )).scalars().first()
    if existing is not None:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{trainer.full_name} already teaches that here.")
        # Revoked before and being given back: reuse the row so the history
        # stays one thread rather than two.
        existing.is_active = True
        existing.assigned_by_id = current_user.id
        await db.commit()
        logger.info(f"[Assignments] {current_user.email} restored "
                    f"{trainer.email} -> {college.code} {department}-{section}")
        return {"id": str(existing.id), "restored": True}

    row = TrainerAssignment(
        trainer_id=trainer.id,
        college_id=college.id,
        department=department,
        section=section,
        academic_year=year,
        assigned_by_id=current_user.id,
    )
    db.add(row)
    await db.commit()
    logger.info(f"[Assignments] {current_user.email} assigned {trainer.email} "
                f"-> {college.code} "
                f"{department or 'whole college'}"
                f"{'-' + section if section else ''} {year}")
    return {"id": str(row.id), "restored": False}


@router.delete("/{assignment_id}")
async def revoke_assignment(
    assignment_id: str,
    current_user: User = Depends(get_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Stop a trainer teaching a section.

    Revoked, not deleted: the attendance they marked and the documents they
    verified stay explainable, and a row that vanished would leave those
    looking as though nobody was ever responsible.
    """
    row = (await db.execute(
        select(TrainerAssignment)
        .where(TrainerAssignment.id == assignment_id))).scalars().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No such assignment.")
    row.is_active = False
    await db.commit()
    logger.info(f"[Assignments] {current_user.email} revoked {assignment_id}")
    return {"revoked": True}
