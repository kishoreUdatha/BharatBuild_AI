"""
Creating the branch for a story, the way Jira's "Create branch" does.

The convention is the same one `story_keys()` reads back: the story key leads
the branch name, so a commit naming that key attaches itself to the story
without anybody wiring anything up.

Creating the ref is a convenience over that convention, not a replacement for
it. If the branch cannot be created - no repository connected, the app not
installed on that account, a repository with no commits yet - the caller is
told plainly and the team can still make the branch themselves. The link is
the key in the message either way.
"""
from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_planning import ProjectUserStory
from app.models.faculty import ProjectBatch
from app.models.project_tracking import (BatchIntegration, IntegrationKind)

MAX = 60


def branch_name(key: str, title: str, max_len: int = MAX) -> str:
    """
    "US-201" + "Design solar PV system" -> "US-201-design-solar-pv-system".

    Trimmed on a hyphen so a long title never leaves the name cut mid-word,
    and never with a trailing hyphen - git allows it, but it reads as a slip.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    full = f"{key}-{slug}" if slug else key
    if len(full) <= max_len:
        return full
    return re.sub(r"-[^-]*$", "", full[:max_len]).rstrip("-")


async def repo_url_for_batch(db: AsyncSession, batch: ProjectBatch) -> Optional[str]:
    row = (await db.execute(
        select(BatchIntegration)
        .where(BatchIntegration.batch_id == batch.id)
        .where(BatchIntegration.kind == IntegrationKind.REPOSITORY)
    )).scalars().first()
    return (row.url or "").strip() or None if row else None


async def story_of(db: AsyncSession, story_id: str) -> Optional[ProjectUserStory]:
    return (await db.execute(
        select(ProjectUserStory).where(ProjectUserStory.id == story_id)
    )).scalars().first()


class BranchRefused(Exception):
    """Something the person who pressed the button should read."""


async def create_for_story(db: AsyncSession, batch: ProjectBatch,
                           story: ProjectUserStory) -> dict:
    """Create this story's branch in the team's repository."""
    from app.services import github_repos

    name = branch_name(story.key, story.title)
    repo_url = await repo_url_for_batch(db, batch)

    if not repo_url:
        raise BranchRefused(
            "Your team has not connected a repository yet, so there is nowhere "
            f"to create the branch. Connect one, or make it yourself with: "
            f"git checkout -b {name}")

    if not github_repos.configured():
        raise BranchRefused(
            f"Branch creation is not switched on here yet. Make it yourself "
            f"with: git checkout -b {name}")

    try:
        return await github_repos.create_branch(repo_url, name)
    except github_repos.RepoError as exc:
        raise BranchRefused(str(exc))
