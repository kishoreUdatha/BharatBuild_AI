"""
One user story, at one address, for everybody who is entitled to it.

The trainer portal, the faculty portal and the student portal all need to look
at the same story, so it lives outside all three rather than being copied into
each. `/stories/{id}` is a page a trainer can send to a student and have the
link work.

Who gets in, and what changes for them:

* Trainers, faculty and admins pass the same per-batch authority check the
  rest of the portal uses, and may edit.
* A student must be an active member of that batch, and the story must have
  reached the product backlog. AI Planning promises students cannot see a
  draft until a trainer has approved and moved it; this route is where that
  promise would otherwise leak.
* Anybody who can see the story can comment on it. A story nobody may discuss
  is not much use to a team.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.ai_planning import ProjectUserStory
from app.models.faculty import ProjectBatch, ProjectBatchMember
from app.models.user import User, UserRole
from app.modules.auth.dependencies import get_current_user
from app.services.faculty_authority import FacultyAuthority
from app.services.git_commits import GitCommitService
from app.services.project_tasks import TaskService
from app.services.user_stories import StoryError, UserStoryService

router = APIRouter(prefix="/stories", tags=["User Stories"])

STAFF = (UserRole.TRAINER, UserRole.FACULTY, UserRole.ADMIN)


class StoryPatchBody(BaseModel):
    """The fields the details panel can change. Absence means "leave it"."""
    title: Optional[str] = Field(None, min_length=3, max_length=240)
    narrative: Optional[str] = Field(None, max_length=2000)
    story_points: Optional[int] = Field(None, ge=0, le=100)
    priority: Optional[str] = None
    story_type: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    sprint_id: Optional[str] = None
    dependencies: Optional[str] = Field(None, max_length=300)
    trainer_comment: Optional[str] = Field(None, max_length=500)
    due_date: Optional[date] = None


class CommentBody(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class CriterionBody(BaseModel):
    text: str = Field(..., min_length=2, max_length=1000)
    kind: str = Field("acceptance", description="acceptance | definition_of_done")


class CriterionPatchBody(BaseModel):
    text: Optional[str] = Field(None, min_length=2, max_length=1000)
    met: Optional[bool] = None


class SubTaskBody(BaseModel):
    """A piece of work under this story. The story is implied by the URL."""
    title: str = Field(..., min_length=3, max_length=300)
    detail: Optional[str] = Field(None, max_length=2000)
    assignee_id: Optional[str] = None
    priority: str = Field("medium", description="high | medium | low")
    status: str = Field("open", description="open | in_progress | blocked | done")
    due_date: Optional[date] = None
    blocked_reason: Optional[str] = Field(None, max_length=300)


class SubTaskPatchBody(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    detail: Optional[str] = Field(None, max_length=2000)
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    blocked_reason: Optional[str] = Field(None, max_length=300)
    progress: Optional[int] = Field(None, ge=0, le=100)

# A student on the team edits a story with the same rights as their trainer.
# `_is_assignee` stays: the page still says whose story it is.
def _is_assignee(story, user: User) -> bool:
    """Whether this account is the one the story was handed to."""
    return story.assignee_id is not None and str(story.assignee_id) == str(user.id)


async def _story_and_batch(db: AsyncSession, story_id: str, user: User):
    """
    Load the story with the batch it belongs to, and decide what this user may
    do with it. Returns (service, story, batch, can_edit).
    """
    story = (await db.execute(
        select(ProjectUserStory).where(ProjectUserStory.id == story_id)
    )).scalars().first()
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    batch = (await db.execute(
        select(ProjectBatch)
        .where(ProjectBatch.id == story.batch_id)
        .options(
            selectinload(ProjectBatch.guide),
            selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
        )
    )).scalars().first()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    if user.role in STAFF:
        if not await FacultyAuthority(db).can_view(user, batch):
            logger.warning(f"[Stories] {user.email} denied {story.key} on {batch.batch_code}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This story belongs to a batch you are not attached to.",
            )
        return UserStoryService(db), story, batch, True

    on_the_team = any(
        m.is_active and str(m.student_id) == str(user.id) for m in batch.members
    )
    if not on_the_team:
        logger.warning(f"[Stories] {user.email} is not on {batch.batch_code}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="This story belongs to a batch you are not on.")
    if story.moved_to_backlog_at is None:
        # Deliberately a 404: telling a student a hidden draft exists is itself
        # a leak of the thing AI Planning is holding back.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    # A student on the team edits the story exactly as their trainer does. The
    # batch is still the boundary - membership is what got them this far, and a
    # story in someone else's batch is as invisible as it ever was.
    return UserStoryService(db), story, batch, True


@router.get("/{story_id}")
async def get_story(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Everything the single story page shows, and whether this user may edit it."""
    service, story, batch, can_edit = await _story_and_batch(db, story_id, current_user)
    try:
        # Reload through the service so the detail carries its epic, sprint,
        # assignee, criteria, tasks, comments and history in one shape - the
        # same one the trainer board's panel renders.
        detail = await service._detail(await service._story(batch, str(story.id)))
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"[Stories] {story_id} failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Could not load that story.")

    roster = [m for m in batch.members if m.is_active and m.student is not None]
    sprints = await service.sprints(batch.id)
    epics = await service._epics(batch.id)

    return {
        "story": detail,
        "batch": {
            "batch_id": str(batch.id),
            "batch_code": batch.batch_code,
            "project_title": batch.title,
            "department": batch.department,
            "section": batch.section,
            "guide": batch.guide.full_name if batch.guide else None,
            "members": len(roster),
        },
        # The commit trail for this story, newest first. Read-only everywhere:
        # it is written by the repository, not by a person.
        "commits": await GitCommitService(db).for_story(str(story.id)),
        "permissions": {
            "can_edit": can_edit,
            "can_comment": True,
            # The assignee gets a narrow slice of write access, so the page can
            # enable exactly those controls instead of showing a read-only view
            # to the person doing the work.
            "is_assignee": _is_assignee(story, current_user),
            "can_change_status": can_edit or _is_assignee(story, current_user),
            "can_update_progress": can_edit or _is_assignee(story, current_user),
            # What the viewer is here as, so the page can say so rather than
            # guessing from what happens to be editable.
            "role": current_user.role.value,
            # Which account is looking: the page uses it to decide whether a
            # given attachment is the viewer's own to remove.
            "user_id": str(current_user.id),
        },
        # Only staff get the option lists; a student cannot reassign anything,
        # and shipping the roster to a page that cannot use it is just leakage.
        "options": {
            "sprints": [
                {"id": str(s.id), "name": s.name, "window": None} for s in sprints
            ],
            "epics": [{"key": e.key, "title": e.title} for e in epics],
            "assignees": [
                {"id": str(m.student_id), "name": m.student.full_name,
                 "roll": m.student.roll_number}
                for m in roster
            ],
        } if can_edit else {"sprints": [], "epics": [], "assignees": []},
    }


@router.patch("/{story_id}")
async def patch_story(
    story_id: str,
    payload: StoryPatchBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change one story.

    Staff change anything. The assigned student changes its status - moving
    their own work along is the point of having a board - and nothing else.
    """
    service, story, batch, can_edit = await _story_and_batch(db, story_id, current_user)
    try:
        return await service.update(batch, str(story.id),
                                    payload.model_dump(exclude_unset=True), current_user)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{story_id}/branch")
async def story_branch(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    The branch this story's work belongs on, and whether we can make it.

    Answered for anyone who may see the story - the name is the same whoever
    asks, and a trainer telling a team what to call their branch is the point.
    """
    from app.services import github_repos
    from app.services.story_branches import branch_name, repo_url_for_batch

    _, story, batch, _ = await _story_and_batch(db, story_id, current_user)
    repo_url = await repo_url_for_batch(db, batch)
    parsed = github_repos.parse_repo(repo_url or "")

    # Why the button would not work, said before it is pressed rather than
    # after - a disabled button with no reason is its own small cruelty.
    blocked = None
    if not repo_url:
        blocked = "Your team has not connected a repository yet."
    elif parsed is None:
        blocked = "The team repository is not on GitHub, so it has to be made by hand."
    elif not github_repos.configured():
        blocked = "Branch creation is not switched on for this deployment yet."

    return {
        "story_key": story.key,
        "branch": branch_name(story.key, story.title),
        "repo_url": repo_url,
        "can_create": blocked is None,
        "reason": blocked,
    }


@router.post("/{story_id}/branch", status_code=status.HTTP_201_CREATED)
async def create_story_branch(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create the branch in the team's repository.

    Pressing it twice is not an error: the second person gets the branch the
    first one made, which is what they wanted.
    """
    from app.services.story_branches import BranchRefused, create_for_story

    _, story, batch, _ = await _story_and_batch(db, story_id, current_user)
    try:
        made = await create_for_story(db, batch, story)
    except BranchRefused as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(exc))
    except Exception as exc:
        logger.error(f"[Stories] Branch for {story.key} failed: "
                     f"{type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub could not be reached. Try again in a moment.")

    logger.info(f"[Stories] {current_user.email} "
                f"{'opened' if made['existed'] else 'created'} "
                f"{made['branch']} on {batch.batch_code}")
    return made


@router.post("/{story_id}/comments", status_code=status.HTTP_201_CREATED)
async def comment_on_story(
    story_id: str,
    payload: CommentBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leave a note. Anybody who can see the story can add one."""
    service, story, batch, _ = await _story_and_batch(db, story_id, current_user)
    try:
        return await service.comment(batch, str(story.id), payload.body, current_user)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ------------------------------------------------------------- attachments
#
# Anyone who can see the story can add a file: a screenshot of the bug and the
# sample output come from the team, not from the trainer. Removing one is for
# staff, or for whoever put it there.


@router.post("/{story_id}/attachments", status_code=status.HTTP_201_CREATED)
async def attach_file(
    story_id: str,
    file: UploadFile = File(..., description="The file to hang on this story"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Attach a file. Size and type rules are the file store's, not this route's."""
    service, story, batch, _ = await _story_and_batch(db, story_id, current_user)
    try:
        result = await service.attach(batch, str(story.id), file, current_user)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.info(f"[Stories] {current_user.email} attached {result['name']} to {story.key}")
    return result


@router.get("/{story_id}/attachments/{attachment_id}")
async def download_attachment(
    story_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send the file back, under the name it was uploaded with."""
    service, story, batch, _ = await _story_and_batch(db, story_id, current_user)
    try:
        content, headers = await service.read_attachment(
            batch, str(story.id), attachment_id)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return Response(content=content, headers=headers)


@router.delete("/{story_id}/attachments/{attachment_id}")
async def remove_attachment(
    story_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Detach a file.

    Staff, or the person who uploaded it - a student may take back their own
    screenshot without being able to clear the trainer's design document.
    """
    service, story, batch, can_edit = await _story_and_batch(db, story_id, current_user)
    try:
        attachment = await service._attachment(story.id, attachment_id)
        if not can_edit and str(attachment.uploaded_by_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only remove a file you uploaded.")
        return await service.detach(batch, str(story.id), attachment_id, current_user)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --------------------------------------------------------------- sub-tasks
#
# The tasks that break this story down. They are ordinary batch tasks with the
# story attached, so they show up on the Tasks screen too - a sub-task is not a
# second, parallel kind of work item.


@router.post("/{story_id}/tasks", status_code=status.HTTP_201_CREATED)
async def add_sub_task(
    story_id: str,
    payload: SubTaskBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Break this story into a piece of work. Staff, as with the story itself."""
    service, story, batch, can_edit = await _story_and_batch(db, story_id, current_user)
    if not can_edit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only a trainer can add a sub-task.")
    body = payload.model_dump()
    # The URL decides which story this belongs to, not the body.
    body["story_id"] = str(story.id)
    try:
        return await TaskService(db).create(batch, body, current_user)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{story_id}/tasks/{task_id}")
async def patch_sub_task(
    story_id: str,
    task_id: str,
    payload: SubTaskPatchBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tick one off, reassign it, or move its date.

    The assigned student may move a sub-task along and say what is blocking
    it; reassigning and re-dating stay with the trainer.
    """
    service, story, batch, can_edit = await _story_and_batch(db, story_id, current_user)
    if not can_edit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only a trainer can change a sub-task.")
    tasks = TaskService(db)
    try:
        task = await tasks._task(batch, task_id)
        if str(task.story_id) != str(story.id):
            raise StoryError("That task is not on this story.")
        return await tasks.update(batch, task_id, payload.model_dump(exclude_unset=True))
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ------------------------------------------------- acceptance criteria
#
# Rows of their own, not a text field: the met count is what the approval
# checklist on AI Planning reads, so ticking one here moves a figure there.


@router.post("/{story_id}/criteria", status_code=status.HTTP_201_CREATED)
async def add_criterion(
    story_id: str,
    payload: CriterionBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a criterion. It starts unmet - nothing is true because it was typed."""
    service, story, batch, can_edit = await _story_and_batch(db, story_id, current_user)
    if not can_edit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only a trainer can change the criteria.")
    try:
        return await service.add_criterion(batch, str(story.id), payload.text,
                                           payload.kind, current_user)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{story_id}/criteria/{criterion_id}")
async def patch_criterion(
    story_id: str,
    criterion_id: str,
    payload: CriterionPatchBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reword a criterion, or tick it off.

    Ticking is the assigned student's - they are the one who met it. The
    wording is the trainer's.
    """
    service, story, batch, can_edit = await _story_and_batch(db, story_id, current_user)
    try:
        return await service.update_criterion(
            batch, str(story.id), criterion_id,
            payload.model_dump(exclude_unset=True), current_user)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{story_id}/criteria/{criterion_id}")
async def remove_criterion(
    story_id: str,
    criterion_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Drop a criterion from the story."""
    service, story, batch, can_edit = await _story_and_batch(db, story_id, current_user)
    if not can_edit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only a trainer can change the criteria.")
    try:
        return await service.delete_criterion(batch, str(story.id), criterion_id,
                                              current_user)
    except StoryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
