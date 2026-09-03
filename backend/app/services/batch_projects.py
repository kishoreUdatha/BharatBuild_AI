"""
The one project a batch shares.

Four students on a batch build one thing together, the way four developers
share a repository. This creates that project the first time somebody opens
it and hands back the same one to everybody afterwards.

Created on demand rather than with the batch. Batches are made empty and
filled later - the Create Batch dialog says so, and Vignan's ten still have no
members - so provisioning at creation would produce a project with no team and
no owner, and a roster import that makes forty-five batches would make
forty-five workspaces for teams that do not exist yet.

Who may then open it is decided in `get_user_project`, by membership of the
batch. Nothing here grants access.
"""
from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import logger
from app.models.faculty import ProjectBatch
from app.models.project import Project, ProjectMode, ProjectStatus
from app.models.user import User
from app.models.student_git_identity import StudentGitIdentity
from app.models.workspace import Workspace


async def project_for_batch(db: AsyncSession,
                            batch: ProjectBatch) -> Optional[Project]:
    """The batch's project, or None if nobody has opened one yet."""
    return (await db.execute(
        select(Project).where(Project.batch_id == batch.id)
    )).scalar_one_or_none()


async def _workspace_for_batch(db: AsyncSession,
                               batch: ProjectBatch) -> Workspace:
    """
    The batch's own workspace, created once.

    Not a member's. A workspace cascades to its projects, and a user cascades
    to their workspaces, so putting the team's project in a student's
    workspace would mean losing it when that student is removed.
    """
    existing = (await db.execute(
        select(Workspace).where(Workspace.batch_id == batch.id)
    )).scalar_one_or_none()
    if existing is not None:
        return existing

    workspace = Workspace(
        user_id=None,
        batch_id=batch.id,
        name=f"{batch.batch_code} — {batch.title or 'Project'}",
        description=f"Shared workspace for {batch.batch_code}",
        is_default=False,
        storage_path=f"workspaces/batch/{batch.id}",
        s3_prefix=f"workspaces/batch/{batch.id}",
    )
    db.add(workspace)
    await db.flush()
    return workspace


async def open_for_batch(db: AsyncSession, user: User,
                         batch: ProjectBatch) -> Tuple[Project, bool]:
    """
    The batch's project, created if this is the first time.

    Returns the project and whether it was just created, so the caller can say
    "opened" or "created" without asking again.
    """
    existing = await project_for_batch(db, batch)
    if existing is not None:
        return existing, False

    workspace = await _workspace_for_batch(db, batch)

    project = Project(
        # Who opened it, not who owns it. The team owns it through `batch_id`,
        # and this column is SET NULL precisely so their leaving does not take
        # the project with them.
        user_id=user.id,
        batch_id=batch.id,
        workspace_id=workspace.id,
        title=batch.title or batch.batch_code,
        description=batch.abstract or batch.problem_statement,
        mode=ProjectMode.COLLEGE,
        domain=batch.domain,
        requirements=batch.problem_statement,
        status=ProjectStatus.DRAFT,
        config={
            "batch_code": batch.batch_code,
            "department": batch.department,
            "section": batch.section,
            "academic_year": batch.academic_year,
        },
        # Keyed by batch, not by the student who opened it. Under a member's
        # id the team's files would sit in a folder named after whoever
        # clicked first, and move if that account went away.
        s3_path=f"workspaces/batch/{batch.id}",
    )
    db.add(project)
    try:
        await db.commit()
    except IntegrityError:
        # Two teammates opened the builder at the same moment. The unique
        # index on batch_id let one insert through; this is the other, and it
        # should get the project that won rather than an error.
        await db.rollback()
        winner = await project_for_batch(db, batch)
        if winner is None:
            raise
        logger.info(f"[BatchProject] Race on {batch.batch_code}; "
                    f"{user.email} joined the project that won")
        return winner, False

    await db.refresh(project)
    logger.info(f"[BatchProject] {user.email} opened the project for "
                f"{batch.batch_code}")
    return project, True


async def repo_of(db: AsyncSession, batch: ProjectBatch) -> dict:
    """
    The repository this batch already works in, if one has been connected.

    A team's code lives in git, not in the workspace - the workspace is where
    they build it. So opening the workspace should land them in the repo the
    batch already uses rather than starting a second place for the same work,
    and when there is none, say so plainly.
    """
    from app.models.project_tracking import (BatchIntegration, IntegrationKind,
                                             IntegrationState)
    row = (await db.execute(
        select(BatchIntegration)
        .where(BatchIntegration.batch_id == batch.id)
        .where(BatchIntegration.kind == IntegrationKind.REPOSITORY)
    )).scalars().first()

    url = (row.url or "").strip() if row is not None else ""
    return {
        "connected": bool(url),
        "url": url or None,
        # "octocat/smart-irrigation" - what a person calls the repository.
        "name": _repo_name(url),
        "state": (row.state.value if row is not None and row.state
                  else IntegrationState.NOT_CONNECTED.value),
        "connected_at": row.connected_at if row is not None else None,
    }


def _repo_name(url: str) -> Optional[str]:
    """owner/repo from a clone or browse URL, or None if it is neither."""
    if not url:
        return None
    trimmed = url.strip().rstrip("/")
    for suffix in (".git",):
        if trimmed.endswith(suffix):
            trimmed = trimmed[: -len(suffix)]
    # https://github.com/owner/repo, git@github.com:owner/repo
    tail = trimmed.split(":")[-1] if trimmed.startswith("git@") else trimmed
    parts = [p for p in tail.replace("//", "/").split("/") if p]
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return None


async def ensure_repo(db: AsyncSession, user: User, batch: ProjectBatch,
                      base_url: Optional[str] = None) -> dict:
    """
    Make sure the batch has somewhere for its code to go.

    Connected already: hand that back untouched - a team that has wired up
    their own repository must not have a second one created underneath them.

    Not connected, and the college has installed the GitHub App: create one in
    that college's organisation, add the team, and set the push webhook.

    Not connected and no App: say so and change nothing. Repository creation is
    a convenience, not a precondition - a college that has not set GitHub up,
    or a GitHub that is down, must still let a team open their workspace.
    """
    current = await repo_of(db, batch)
    if current["connected"]:
        return current

    from app.models.college import College
    from app.services import github_repos

    college = (await db.execute(
        select(College).where(College.id == batch.college_id)
    )).scalars().first()

    org = (getattr(college, "github_org", None) or "").strip() if college else ""
    installation = (getattr(college, "github_installation_id", None) or "").strip() if college else ""
    if not (org and installation and github_repos.configured()):
        current["reason"] = (
            "This college has not connected GitHub yet, so a repository has to "
            "be created and linked by hand.")
        return current

    # The secret first: the webhook is set at creation time, and it has to be
    # the same one this batch's pushes will be verified against.
    from app.services.git_commits import GitCommitService
    service = GitCommitService(db)
    wiring = await service.connection(batch, base_url or "")
    secret = wiring.get("secret")
    if not secret:
        minted = await service.connect(batch, actor=user)
        secret = minted.get("secret")
        wiring = await service.connection(batch, base_url or "")

    members = (await db.execute(
        select(StudentGitIdentity.username)
        .where(StudentGitIdentity.batch_id == batch.id)
        .where(StudentGitIdentity.username.isnot(None))
    )).scalars().all()

    try:
        made = await github_repos.create_for_batch(
            installation_id=installation,
            org=org,
            name=github_repos.repo_name(batch.batch_code, batch.title),
            description=(batch.title or batch.batch_code),
            collaborators=[m for m in members if m],
            webhook_url=wiring.get("webhook_url"),
            webhook_secret=secret,
        )
    except Exception as exc:
        # Logged, not raised. The workspace is already open by the time this
        # runs, and failing it now would take that away over something the
        # team can still do by hand.
        logger.warning(f"[BatchProject] Repository for {batch.batch_code} "
                       f"not created: {type(exc).__name__}: {exc}")
        current["reason"] = (
            "The repository could not be created automatically. Connect one by "
            "hand and everything else will work as normal.")
        return current

    await service.connect(batch, repo_url=made["url"], actor=user)
    logger.info(f"[BatchProject] {batch.batch_code} -> {made.get('full_name')}")
    result = await repo_of(db, batch)
    result["just_created"] = made.get("created", False)
    return result


def describe(project: Optional[Project]) -> dict:
    """What a batch screen needs to show "Open" or "Not started"."""
    if project is None:
        return {"exists": False, "project_id": None,
                "workspace_id": None, "status": None,
                "title": None, "progress": 0}
    return {
        "exists": True,
        "project_id": str(project.id),
        "workspace_id": str(project.workspace_id) if project.workspace_id else None,
        "title": project.title,
        "status": project.status.value if project.status else None,
        "progress": project.progress or 0,
        "updated_at": project.updated_at,
    }
