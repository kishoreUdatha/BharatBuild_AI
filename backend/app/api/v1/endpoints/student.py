"""
Student Portal API - the student's own registration journey.

Mirrors what the faculty portal reads, from the other side of the same rows.
"""

from math import ceil
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query, Request,
                     status, UploadFile)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User, UserRole
from app.modules.auth.dependencies import get_current_user
from app.services import (
    attendance as attendance_service,
    batch_files,
    file_store,
    project_details,
    submissions,
)
from app.services.student_registration import (
    BatchCodeError,
    StudentRegistrationService,
)

router = APIRouter(prefix="/student", tags=["Student Portal"])


class PaymentConfirmBody(BaseModel):
    """What the gateway hands back to the browser after a successful payment."""
    razorpay_order_id: str = Field(..., max_length=120)
    razorpay_payment_id: str = Field(..., max_length=120)
    razorpay_signature: str = Field(..., max_length=256)


class GitOAuthBody(BaseModel):
    """The one-time code GitHub hands back after the student authorises."""
    code: str = Field(..., min_length=1, max_length=500)


class GitRepoBody(BaseModel):
    """Where the team's code lives, as the lead sets it."""
    repo_url: Optional[str] = Field(None, max_length=500)
    rotate_secret: bool = False


class GitIdentityBody(BaseModel):
    """The git account this student commits under, in their own words."""
    username: Optional[str] = Field(None, max_length=120,
                                    description="Their handle on GitHub or GitLab")
    emails: List[str] = Field(default_factory=list,
                              description="Every address they commit from")
    provider: Optional[str] = Field(None, max_length=30)


async def get_current_student(current_user: User = Depends(get_current_user)) -> User:
    """
    Students, and admins so support can look at a student's screen.

    Faculty are deliberately not allowed through: they have their own portal,
    and letting them load this would show a registration that is not theirs.
    """
    if current_user.role not in (UserRole.STUDENT, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This area is for student accounts.",
        )
    return current_user


class BatchCodeRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=40)


class ResendInviteRequest(BaseModel):
    member_id: str


@router.get("/registration")
async def get_registration(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Everything the Student Team Registration screen shows."""
    try:
        return await StudentRegistrationService(db).state(current_user)
    except Exception as exc:
        logger.error(f"[Student] Registration state failed for {current_user.email}: "
                     f"{type(exc).__name__}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Could not load your registration.")


@router.post("/registration/verify-batch")
async def verify_batch(
    payload: BatchCodeRequest,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Check a join code without taking the seat."""
    try:
        return await StudentRegistrationService(db).verify_batch(current_user, payload.code)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/registration/join")
async def join_batch(
    payload: BatchCodeRequest,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Take the seat, and record the share that comes with it."""
    try:
        result = await StudentRegistrationService(db).join_batch(current_user, payload.code)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.info(f"[Student] {current_user.email} joined batch {payload.code}")
    return result


@router.post("/registration/resend-invite")
async def resend_invite(
    payload: ResendInviteRequest,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Record a reminder for a team member who has not accepted their seat."""
    try:
        return await StudentRegistrationService(db).resend_invite(current_user, payload.member_id)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/registration/receipt.pdf")
async def download_receipt_pdf(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """The student's own payment receipt. Absent until the share is paid."""
    body = await StudentRegistrationService(db).receipt_pdf(current_user)
    if body is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No completed payment on record yet.")
    return StreamingResponse(
        iter([body]),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 'attachment; filename="registration-receipt.pdf"'},
    )


@router.get("/registration/receipt.txt")
async def download_receipt(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """The same receipt as plain text, for anything that cannot read a PDF."""
    body = await StudentRegistrationService(db).receipt(current_user)
    if body is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No completed payment on record yet.")
    return StreamingResponse(
        iter([body]),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="registration-receipt.txt"'},
    )


# ============================================
# Project Setup - the team's own project details
# ============================================


class ObjectiveBody(BaseModel):
    text: str
    status: Optional[str] = None


class StepBody(BaseModel):
    title: str
    description: Optional[str] = None


class TechnologyBody(BaseModel):
    layer: Optional[str] = None
    name: str


class ProjectSetupBody(BaseModel):
    """
    The Project Setup form.

    Every field is optional because a team fills this in over several sittings;
    a list that is sent replaces what was there, a list that is omitted is left
    alone.
    """
    title: Optional[str] = None
    domain: Optional[str] = None
    project_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    problem_statement: Optional[str] = None
    abstract: Optional[str] = None
    objectives: Optional[List[ObjectiveBody]] = None
    methodology: Optional[List[StepBody]] = None
    outcomes: Optional[List[str]] = None
    in_scope: Optional[List[str]] = None
    out_of_scope: Optional[List[str]] = None
    deliverables: Optional[List[str]] = None
    technologies: Optional[List[TechnologyBody]] = None
    start_date: Optional[str] = None
    target_completion: Optional[str] = None
    weekly_effort_hours: Optional[int] = None


class SubmitProjectBody(BaseModel):
    note: Optional[str] = Field(None, max_length=1000)


def _for_student(payload: dict, batch) -> dict:
    """
    Narrow the shared form payload to what THIS student may do.

    `complete` says the eight answers are all in; `can_submit` says this reader
    may act. A screen reads the second as "the button works", so a member who
    is not the leader must not see it true - they would press it and be
    refused.
    """
    is_lead = bool(getattr(batch, "_is_lead", False))
    payload["is_lead"] = is_lead
    if payload["can_submit"] and not is_lead:
        payload["can_submit"] = False
        payload["submit_blocked_reason"] = (
            "Your batch leader submits the registration once the team is happy with it.")
    else:
        payload["submit_blocked_reason"] = payload.get("locked_reason")
    return payload


@router.get("/project")
async def get_project(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """The team's project details, with what still has to be filled in."""
    try:
        batch = await StudentRegistrationService(db).project_batch(current_user)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _for_student(project_details.form(batch), batch)


@router.put("/project")
async def save_project(
    body: ProjectSetupBody,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Save the form. Partial saves are expected, so nothing is required here."""
    service = StudentRegistrationService(db)
    try:
        batch = await service.project_batch(current_user)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    try:
        result = await project_details.save(
            db, batch, body.model_dump(exclude_unset=True), current_user,
            actor_role="Batch Leader" if getattr(batch, "_is_lead", False) else "Student",
            source="Student Portal",
        )
    except project_details.ProjectDetailsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.info(f"[Student] {current_user.email} saved project details on "
                f"{batch.batch_code}: {result.get('changed_fields')}")
    return _for_student(result, batch)


@router.post("/project/submit")
async def submit_project(
    body: SubmitProjectBody,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Send the registration to the guide.

    Only the batch leader may do this. Any member can write the proposal, but
    submitting it is the team speaking with one voice, and a leader is who the
    approval trail records as having spoken.
    """
    service = StudentRegistrationService(db)
    try:
        batch = await service.project_batch(current_user)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if not getattr(batch, "_is_lead", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the batch leader can submit the registration for approval.",
        )
    try:
        result = await project_details.submit(
            db, batch, current_user, actor_role="Batch Leader",
            note=body.note, source="Student Portal",
        )
    except project_details.ProjectDetailsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            headers={"X-Unmet-Checks": ",".join(exc.unmet)} if exc.unmet else None,
        )
    logger.info(f"[Student] {current_user.email} submitted {batch.batch_code} for approval")
    return result


# ============================================
# Files - the team's own documents and paper
# ============================================


async def _my_batch(db: AsyncSession, user: User):
    """
    The batch this student may upload to.

    There is no batch id in any of these routes on purpose. A student acts on
    their own batch or on nothing, so there is no id for anyone to change.
    """
    try:
        return await StudentRegistrationService(db).project_batch(user)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _role_of(batch) -> str:
    return "Batch Leader" if getattr(batch, "_is_lead", False) else "Student"


@router.get("/builder")
async def get_team_builder(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    The build workspace this team shares, if they have opened one.

    Like every route on this router it takes no batch id: a student reaches
    their own batch or nothing, so there is no id for anyone to change to a
    teammate's - or another batch's.
    """
    from app.services.batch_projects import (describe, project_for_batch,
                                              repo_of)
    batch = await _my_batch(db, current_user)
    return {
        "batch_code": batch.batch_code,
        "workspace": describe(await project_for_batch(db, batch)),
        "repo": await repo_of(db, batch),
    }


@router.post("/builder")
async def open_team_builder(
    request: Request,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Open the team's workspace, creating it the first time.

    One project for the four of them, not one each. Whoever gets here first
    creates it and the rest join the same one.
    """
    from app.services.batch_projects import (describe, ensure_repo,
                                              open_for_batch)
    batch = await _my_batch(db, current_user)
    project, created = await open_for_batch(db, current_user, batch)
    # And somewhere to push. Connected already: untouched. Not connected, and
    # the college has installed the GitHub App: created in their organisation,
    # with the team added and the push webhook set.
    repo = await ensure_repo(db, current_user, batch, str(request.base_url))
    return {
        "batch_code": batch.batch_code,
        "created": created,
        "workspace": describe(project),
        "repo": repo,
    }


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Everything the team has uploaded, and what is still expected."""
    batch = await _my_batch(db, current_user)
    documents = await batch_files.load_batch_documents(db, batch.id)
    rows = [
        {
            "id": str(d.id),
            "name": d.name,
            "category": d.category,
            "version": d.version,
            "status": d.status.value,
            "is_required": d.is_required,
            "superseded": d.superseded_by_id is not None,
            "faculty_note": d.faculty_note,
            "uploaded_by": (d.uploaded_by.full_name if d.uploaded_by else None),
            "uploaded_at": d.uploaded_at,
            "file": file_store.describe(d.file),
            # A verified document is what an approval was granted against, and
            # a superseded one is history; neither may be taken back.
            "can_remove": d.status.value != "verified" and d.superseded_by_id is None,
        }
        for d in documents
    ]
    return {
        "batch_code": batch.batch_code,
        "rows": rows,
        "missing_required": batch_files.outstanding(documents),
        "is_lead": getattr(batch, "_is_lead", False),
        **batch_files.options(),
    }


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("Project Document"),
    name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Upload one of the team's registration documents."""
    batch = await _my_batch(db, current_user)
    try:
        return await batch_files.upload_document(
            db, batch, file, current_user, name=name, category=category,
            actor_role=_role_of(batch), source="Student Portal")
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Send a document belonging to this student's own batch."""
    batch = await _my_batch(db, current_user)
    try:
        document, content = await batch_files.document_for_download(db, batch, document_id)
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return StreamingResponse(
        iter([content]),
        media_type=document.file.mime_type,
        headers=file_store.download_headers(document.file, document.name),
    )


@router.delete("/documents/{document_id}")
async def remove_document(
    document_id: str,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Take back an upload a guide has not verified yet."""
    batch = await _my_batch(db, current_user)
    try:
        return await batch_files.delete_document(
            db, batch, document_id, current_user,
            actor_role=_role_of(batch), source="Student Portal")
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/base-paper", status_code=status.HTTP_201_CREATED)
async def upload_base_paper(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Upload the team's primary base paper as a PDF."""
    batch = await _my_batch(db, current_user)
    try:
        return await batch_files.upload_base_paper(
            db, batch, file, current_user, title=title,
            actor_role=_role_of(batch), source="Student Portal")
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/base-paper/download")
async def download_base_paper(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Send the team's base paper PDF."""
    batch = await _my_batch(db, current_user)
    try:
        paper, content = await batch_files.base_paper_for_download(db, batch)
    except batch_files.BatchFileError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return StreamingResponse(
        iter([content]),
        media_type=paper.file.mime_type,
        headers=file_store.download_headers(paper.file, paper.file_name),
    )


# ============================================
# Stage deliverables - the team's own work
# ============================================


@router.get("/submissions")
async def list_my_submissions(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """What the team has handed in, and the eight things expected of them."""
    batch = await _my_batch(db, current_user)
    rows = await submissions.load(db, batch.id)
    return {
        "batch_code": batch.batch_code,
        "rows": [submissions.row(s) for s in rows],
        "pending": sum(1 for s in rows
                       if s.status.value == "pending" and s.superseded_by_id is None),
        "overall_progress": int(round(batch.overall_progress or 0)),
        "is_lead": getattr(batch, "_is_lead", False),
        **submissions.options(rows),
    }


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def submit_work(
    document_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    link: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Hand in a deliverable.

    Any confirmed member may submit: the work belongs to the team, and making
    the leader the only one who can hand it in would stall a team whose leader
    is unavailable. Who submitted is recorded either way.
    """
    batch = await _my_batch(db, current_user)
    try:
        return await submissions.submit(
            db, batch, current_user, document_type=document_type, upload=file,
            link=link, title=title, actor_role=_role_of(batch), source="Student Portal")
    except submissions.SubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/submissions/{submission_id}")
async def withdraw_submission(
    submission_id: str,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Take back a submission the guide has not judged yet."""
    batch = await _my_batch(db, current_user)
    try:
        return await submissions.withdraw(
            db, batch, submission_id, current_user,
            actor_role=_role_of(batch), source="Student Portal")
    except submissions.SubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/submissions/{submission_id}/download")
async def download_my_submission(
    submission_id: str,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Send back a file this team submitted."""
    batch = await _my_batch(db, current_user)
    try:
        submission, content = await submissions.for_download(db, batch, submission_id)
    except submissions.SubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return StreamingResponse(
        iter([content]),
        media_type=submission.file.mime_type,
        headers=file_store.download_headers(submission.file),
    )


# ============================================
# Attendance - the student's own register
# ============================================


@router.get("/attendance")
async def my_attendance(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    This student's own attendance.

    Read-only from here, and scoped to the caller: a student can see the days
    their rate was built from, which is what makes a low rate arguable rather
    than just asserted.
    """
    service = StudentRegistrationService(db)
    enrollment = await service.enrollment(current_user)
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are not enrolled for an academic year yet.",
        )
    payload = await attendance_service.AttendanceService(db).for_student(
        current_user, enrollment.academic_year)
    payload["department"] = enrollment.department
    payload["section"] = enrollment.section
    return payload


@router.get("/attendance/month")
async def my_attendance_month(
    month: str = Query(None, pattern=r"^\d{4}-\d{2}$",
                       description="YYYY-MM; defaults to the latest with records"),
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    One month of this student's register, a row per day.

    Read-only: a student can see what was marked and argue with it, but the
    trainer is the only one who writes it.
    """
    service = StudentRegistrationService(db)
    enrollment = await service.enrollment(current_user)
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are not enrolled for an academic year yet.",
        )
    payload = await attendance_service.AttendanceService(db).month_for_student(
        current_user, enrollment.academic_year, month)
    payload["batch_label"] = " - ".join(p for p in (
        enrollment.department,
        f"{enrollment.academic_year}" if enrollment.academic_year else None,
        f"Section {enrollment.section}" if enrollment.section else None) if p)
    return payload


# ============================================
# My Stories
# ============================================
#
# A student sees only what is assigned to them - never the batch's whole
# backlog. Scoping on assignee_id rather than batch membership is what makes
# that true, and it is why no batch identifier is accepted here.


@router.get("/stories")
async def my_stories(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status",
                                         description="to_do | in_progress | in_review | done"),
    priority: Optional[str] = Query(None, description="high | medium | low"),
    sprint: Optional[str] = Query(None, description="Sprint name, or 'none'"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Every user story assigned to this student, with the tab counts."""
    from sqlalchemy import select as _select
    from sqlalchemy.orm import selectinload as _selectinload

    from app.models.ai_planning import ProjectUserStory, StoryWorkflowStatus
    from app.services.user_stories import WORKFLOW_LABELS

    stories = (await db.execute(
        _select(ProjectUserStory)
        .where(ProjectUserStory.assignee_id == current_user.id)
        .options(
            _selectinload(ProjectUserStory.epic),
            _selectinload(ProjectUserStory.sprint),
            _selectinload(ProjectUserStory.batch),
            # Loaded with the list so opening a story needs no second request:
            # a student's assigned set is small, and this is what View shows.
            _selectinload(ProjectUserStory.criteria),
        )
        .order_by(ProjectUserStory.due_date.is_(None), ProjectUserStory.due_date)
    )).scalars().all()

    rows = [
        {
            "id": str(t.id),
            "key": t.key,
            "title": t.title,
            "epic": t.epic.title if t.epic else "General",
            "priority": t.priority.value,
            "priority_label": t.priority.value.title(),
            "story_points": t.story_points or 0,
            "status": t.workflow_status.value,
            "status_label": WORKFLOW_LABELS[t.workflow_status],
            "sprint": t.sprint.name if t.sprint else None,
            "due_date": t.due_date,
            "batch_code": t.batch.batch_code if t.batch else None,
            "narrative": t.narrative,
            "acceptance_criteria": [
                {"text": c.text, "met": c.met}
                for c in sorted(t.criteria, key=lambda c: c.position or 0)
            ],
        }
        for t in stories
    ]

    # Counts come from everything assigned, not the filtered page: the tabs are
    # how you change the filter, so they cannot describe its result.
    def count(value: str) -> int:
        return sum(1 for r in rows if r["status"] == value)

    # Keyed off the enum so a new stage cannot be added to the workflow and
    # quietly go missing from the student's tabs.
    counts = {"total": len(rows)}
    counts.update({s.value: count(s.value) for s in StoryWorkflowStatus})

    def keep(r: dict) -> bool:
        if search:
            needle = search.lower()
            blob = " ".join(filter(None, [r["key"], r["title"], r["epic"]])).lower()
            if needle not in blob:
                return False
        if status_filter and r["status"] != status_filter:
            return False
        if priority and r["priority"] != priority:
            return False
        if sprint:
            if sprint == "none" and r["sprint"]:
                return False
            if sprint != "none" and r["sprint"] != sprint:
                return False
        return True

    matched = [r for r in rows if keep(r)]
    total = len(matched)
    pages = max(1, ceil(total / per_page))
    page = max(1, min(page, pages))

    return {
        "rows": matched[(page - 1) * per_page: page * per_page],
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "counts": counts,
        "filters": {
            "statuses": [{"value": k.value, "label": v} for k, v in WORKFLOW_LABELS.items()],
            "priorities": [{"value": p, "label": p.title()} for p in ("high", "medium", "low")],
            "sprints": sorted({r["sprint"] for r in rows if r["sprint"]}),
        },
    }


# ============================================
# Git - the student's own identity in the team repository
# ============================================


@router.get("/git")
async def my_git_identity(
    request: Request,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    The team's repository, and this student's own link to it.

    The repository is one per batch and the trainer connects it. What belongs
    to the student is which git account inside it is theirs.
    """
    from app.services.git_commits import GitCommitService

    batch = await _my_batch(db, current_user)
    return await GitCommitService(db).my_connection(
        batch, current_user, str(request.base_url))


@router.post("/git")
async def claim_git_identity(
    body: GitIdentityBody,
    request: Request,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Claim a git account and its commit addresses as this student's own."""
    from app.services.git_commits import CommitError, GitCommitService

    batch = await _my_batch(db, current_user)
    service = GitCommitService(db)
    try:
        await service.claim_identity(batch, current_user, username=body.username,
                                     emails=body.emails, provider=body.provider)
    except CommitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return await service.my_connection(batch, current_user, str(request.base_url))


@router.get("/commits")
async def my_commits(
    scope: str = Query("all", description="all | linked | unlinked"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Every commit credited to this student, newest first."""
    from app.services.git_commits import GitCommitService

    batch = await _my_batch(db, current_user)
    if scope not in {"all", "linked", "unlinked"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Scope must be all, linked or unlinked.")
    return await GitCommitService(db).for_student(
        batch, current_user, scope=scope, search=search,
        page=page, per_page=per_page)


def _require_lead(batch):
    """
    Only the team lead wires the repository up.

    On a student project the lead is the one who created the repo and added the
    others as collaborators, so they are the only member with the admin rights
    a webhook needs. A teammate seeing the secret would gain nothing and widen
    who can forge a push.
    """
    if not getattr(batch, "_is_lead", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the batch leader can connect the team repository.")


@router.get("/git/repo")
async def team_repo(
    request: Request,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """The webhook URL and secret for the team repository. Lead only."""
    from app.services.git_commits import GitCommitService

    batch = await _my_batch(db, current_user)
    _require_lead(batch)
    return await GitCommitService(db).connection(batch, str(request.base_url))


@router.post("/git/repo")
async def connect_team_repo(
    body: GitRepoBody,
    request: Request,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Record the team repository and mint (or rotate) its push secret."""
    from app.services.git_commits import CommitError, GitCommitService

    batch = await _my_batch(db, current_user)
    _require_lead(batch)
    service = GitCommitService(db)
    try:
        await service.connect(batch, repo_url=body.repo_url,
                              rotate=body.rotate_secret, actor=current_user)
    except CommitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return await service.connection(batch, str(request.base_url))


@router.get("/git/oauth/url")
async def git_oauth_url(
    current_user: User = Depends(get_current_student),
):
    """
    Where to send the student to authorise reading their GitHub identity.

    The same redirect URI as signing in, so a college registers one callback
    rather than two; what tells the two apart is what the browser does with
    the code afterwards.
    """
    import secrets as _secrets

    from app.core.config import settings
    from app.modules.oauth.github_provider import github_oauth

    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub linking is not switched on for this college yet. "
                   "Enter your details by hand instead.")
    state = _secrets.token_urlsafe(32)
    return {"authorization_url": github_oauth.get_authorization_url(state=state),
            "state": state}


@router.post("/git/oauth/link")
async def git_oauth_link(
    body: GitOAuthBody,
    request: Request,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Finish the link: ask GitHub who this is, and record it as proven.

    The code is exchanged server side, so the student's GitHub token never
    reaches the browser and is not kept once the addresses are read - the
    identity is what this feature needs, not standing access to their account.
    """
    from app.core.config import settings
    from app.modules.oauth.github_provider import github_oauth
    from app.services.git_commits import CommitError, GitCommitService

    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="GitHub linking is not switched on.")

    batch = await _my_batch(db, current_user)
    try:
        tokens = await github_oauth.exchange_code_for_tokens(body.code)
        token = (tokens or {}).get("access_token")
        if not token:
            raise ValueError("no access token")
        info = await github_oauth.get_user_info(token)
        rows = await github_oauth.get_user_emails(token)
    except Exception as exc:
        logger.warning(f"[Git] GitHub link failed for {current_user.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub did not confirm that sign-in. Please try again.")

    login = (info or {}).get("login")
    if not login:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="GitHub did not return an account name.")
    # Verified addresses only - an unverified one proves nothing, and this is
    # what decides who gets credit for a commit.
    emails = [r.get("email") for r in (rows or [])
              if r.get("email") and r.get("verified")]

    service = GitCommitService(db)
    try:
        await service.link_github(batch, current_user, login, emails)
    except CommitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return await service.my_connection(batch, current_user, str(request.base_url))


@router.post("/payments/order")
async def open_payment_order(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Open a gateway order for this student's share of the registration fee."""
    try:
        return await StudentRegistrationService(db).start_payment(current_user)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/payments/confirm")
async def confirm_payment(
    body: PaymentConfirmBody,
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Record the share as paid.

    Nothing is marked paid on the browser's word - the gateway's signature
    over the order and payment ids is checked first.
    """
    try:
        return await StudentRegistrationService(db).confirm_payment(
            current_user,
            order_id=body.razorpay_order_id,
            payment_id=body.razorpay_payment_id,
            signature=body.razorpay_signature)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/payments/overview")
async def payments_overview(
    current_user: User = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """This student's share, their team's, and every settled transaction."""
    try:
        return await StudentRegistrationService(db).payments_overview(current_user)
    except BatchCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
