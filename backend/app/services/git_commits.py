"""
Turning a repository push into a trail against user stories.

The link is the commit message. A student writes

    git commit -m "US-101 parse the header row"

and the key is what ties the work to the story - the same convention every
issue tracker uses, because it asks nothing of the student beyond how they
already write commits.

Nothing here trusts the payload's own account fields to identify a person: the
name on a commit is whatever was configured locally. An author is only attached
to a batch member when the email matches one exactly.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime
from typing import Dict
from typing import List, Optional
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging_config import logger
from app.models.ai_planning import ProjectUserStory
from app.models.faculty import ProjectBatch, ProjectBatchMember
from app.models.project_tracking import (
    BatchIntegration, IntegrationKind, IntegrationState,
)
from app.models.story_commit import StoryCommit
from app.models.student_git_identity import StudentGitIdentity
from app.models.user import User

# "US-101", "us-101", "[US-101]" - anywhere in the message, and more than one
# key is allowed because a commit can genuinely finish two stories.
KEY_PATTERN = re.compile(r"\b([A-Z]{2,5}-\d{1,6})\b", re.IGNORECASE)

MAX_COMMITS_PER_PUSH = 200


class CommitError(Exception):
    """The push could not be accepted. The message is safe to return."""


def story_keys(message: str) -> List[str]:
    """Every story key named in a commit message, upper-cased, in order."""
    seen, keys = set(), []
    for match in KEY_PATTERN.findall(message or ""):
        key = match.upper()
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def signature_ok(secret: str, body: bytes, header: Optional[str]) -> bool:
    """
    Whether a GitHub-style HMAC header matches the body.

    Compared with `compare_digest`, so a wrong signature takes the same time as
    a right one and cannot be guessed a byte at a time.
    """
    if not header:
        return False
    sent = header.split("=", 1)[-1].strip()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent, expected)


def _parse_time(raw) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None)
    try:
        # GitHub sends ISO 8601; GitLab the same with a Z or an offset.
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


class GitCommitService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_push(self, batch: ProjectBatch, payload: dict,
                          provider: str = "github") -> dict:
        """
        Store the commits in a push and link the ones that name a story.

        Redelivery is a no-op rather than an error: webhooks retry, and a
        provider that gets a 500 for a duplicate will keep retrying forever.
        """
        commits = payload.get("commits") or []
        if not isinstance(commits, list):
            raise CommitError("The push carried no commit list.")
        if len(commits) > MAX_COMMITS_PER_PUSH:
            commits = commits[:MAX_COMMITS_PER_PUSH]

        # Only the refs/heads/ prefix comes off: a branch name legitimately
        # contains slashes, and splitting on all of them turns
        # feature/sensor-calibration into sensor-calibration.
        ref = (payload.get("ref") or "").strip()
        for prefix in ("refs/heads/", "refs/tags/"):
            if ref.startswith(prefix):
                ref = ref[len(prefix):]
                break
        branch = ref[:200] or None

        stories = (await self.db.execute(
            select(ProjectUserStory).where(ProjectUserStory.batch_id == batch.id)
        )).scalars().all()
        by_key = {s.key.upper(): s for s in stories}

        # Who a commit belongs to. The identities a student claimed come
        # first: git carries whatever email they configured locally, which is
        # hardly ever the college address, so matching on that alone would
        # leave most of a shared repository's commits credited to nobody.
        by_email, by_username, identities, mine = await self._authorship(batch)

        known = {
            sha for (sha,) in (await self.db.execute(
                select(StoryCommit.sha).where(StoryCommit.batch_id == batch.id)
            )).all()
        }

        stored, linked, skipped, unmatched_keys = 0, 0, 0, []
        for raw in commits:
            sha = (raw.get("id") or raw.get("sha") or "").strip()
            if not sha:
                continue
            if sha in known:
                skipped += 1
                continue
            known.add(sha)

            message = (raw.get("message") or "").strip()
            author = raw.get("author") or {}
            email = (author.get("email") or "").lower() or None
            handle = (author.get("username") or "").lower() or None

            # A verification code in the message proves the account is really
            # the student's, and binds the email it arrived from to them.
            claimed = self._claim_by_code(message, identities, email, by_email)
            owner_id = (str(claimed.student_id) if claimed
                        else by_email.get(email) or by_username.get(handle))

            story = None
            for key in story_keys(message):
                if key in by_key:
                    story = by_key[key]
                    break
                unmatched_keys.append(key)

            self.db.add(StoryCommit(
                batch_id=batch.id,
                story_id=story.id if story else None,
                sha=sha,
                message=message[:5000],
                url=raw.get("url"),
                branch=branch,
                author_name=author.get("name"),
                author_email=email,
                author_id=owner_id,
                provider=provider,
                committed_at=_parse_time(raw.get("timestamp") or raw.get("committed_date")),
            ))
            stored += 1
            if story is not None:
                linked += 1
            identity = mine.get(owner_id) if owner_id else None
            if identity is not None:
                when = _parse_time(raw.get("timestamp") or raw.get("committed_date"))
                if when and (identity.last_commit_at is None
                             or when > identity.last_commit_at):
                    identity.last_commit_at = when

        await self.db.commit()
        logger.info(
            f"[Git] {batch.batch_code}: {stored} commit(s) stored, {linked} linked, "
            f"{skipped} already seen"
        )
        return {
            "stored": stored,
            "linked": linked,
            "already_seen": skipped,
            "branch": branch,
            # Keys the team used that match no story here - almost always a
            # typo, and worth saying so rather than silently dropping.
            "unknown_keys": sorted(set(unmatched_keys)),
        }



    # ------------------------------------------------------------- identities

    async def _identities(self, batch: ProjectBatch) -> List[StudentGitIdentity]:
        return list((await self.db.execute(
            select(StudentGitIdentity).where(StudentGitIdentity.batch_id == batch.id)
        )).scalars().all())

    async def _authorship(self, batch: ProjectBatch):
        """
        Three ways to recognise the person behind a commit, in order of trust.

        A claimed address is the strong one - the student named it as theirs.
        The handle is a fallback for hosts that send it. Their college address
        is last and needs no claim at all: it is already known to be theirs,
        and it credits the student who simply has git configured with it.

        The maps point at student ids rather than identity rows, so a student
        who has never opened the screen is still credited for their own work.
        """
        identities = await self._identities(batch)
        mine: Dict[str, StudentGitIdentity] = {str(r.student_id): r for r in identities}
        by_email: Dict[str, str] = {}
        by_username: Dict[str, str] = {}
        for row in identities:
            for address in (row.emails or []):
                cleaned = (address or "").strip().lower()
                # First claim wins, so a later duplicate cannot take a
                # teammate's commits away from them.
                if cleaned:
                    by_email.setdefault(cleaned, str(row.student_id))
            if row.username:
                by_username.setdefault(row.username.strip().lower(), str(row.student_id))

        members = (await self.db.execute(
            select(User)
            .join(ProjectBatchMember, ProjectBatchMember.student_id == User.id)
            .where(ProjectBatchMember.batch_id == batch.id)
        )).scalars().all()
        for user in members:
            address = (user.email or "").strip().lower()
            if address:
                by_email.setdefault(address, str(user.id))
        return by_email, by_username, identities, mine

    @staticmethod
    def _claim_by_code(message: str, identities: List[StudentGitIdentity],
                       email: Optional[str], by_email: Dict[str, str]):
        """
        Bind an identity when its verification code turns up in a commit.

        Only the student who was given the code can have put it there, so the
        address it arrived from is theirs - which is the whole proof, and it
        costs them one commit rather than an OAuth round trip.
        """
        upper = (message or "").upper()
        for row in identities:
            if not row.verify_code or row.verify_code.upper() not in upper:
                continue
            if email and email not in by_email:
                row.emails = list(row.emails or []) + [email]
                by_email[email] = str(row.student_id)
            row.verify_code = None
            row.verified_at = datetime.utcnow()
            return row
        return None

    # ------------------------------------------------------------ connection

    async def _integration(self, batch: ProjectBatch,
                           create: bool = False) -> Optional[BatchIntegration]:
        row = (await self.db.execute(
            select(BatchIntegration)
            .where(BatchIntegration.batch_id == batch.id)
            .where(BatchIntegration.kind == IntegrationKind.REPOSITORY)
        )).scalars().first()
        if row is None and create:
            row = BatchIntegration(batch_id=batch.id, kind=IntegrationKind.REPOSITORY,
                                   state=IntegrationState.NOT_CONNECTED)
            self.db.add(row)
            await self.db.flush()
        return row

    @staticmethod
    def _public_base(request_base: str) -> str:
        """
        The origin a code host would have to post to.

        The request's own host is the last resort, and inside a container it is
        the service name - useless to GitHub - so a configured public URL wins.
        """
        from app.core.config import settings
        configured = (settings.WEBHOOK_PUBLIC_URL or "").strip()
        if configured:
            return configured.rstrip("/")
        api = (settings.NEXT_PUBLIC_API_URL or "").strip()
        if api:
            parts = urlsplit(api)
            if parts.scheme and parts.netloc:
                return f"{parts.scheme}://{parts.netloc}"
        return request_base.rstrip("/")

    @staticmethod
    def _reachable(base: str) -> bool:
        """Whether that origin is one a code host could actually resolve."""
        host = (urlsplit(base).hostname or "").lower()
        return not (
            host in {"localhost", "127.0.0.1", "0.0.0.0", "::1", "backend", "host.docker.internal"}
            or host.endswith(".local")
            or host.startswith("192.168.")
            or host.startswith("10.")
        )

    async def connection(self, batch: ProjectBatch, base_url: str) -> dict:
        """What the trainer needs to wire the repository up, and whether it has fired."""
        row = await self._integration(batch)
        total = (await self.db.execute(
            select(func.count(StoryCommit.id)).where(StoryCommit.batch_id == batch.id)
        )).scalar() or 0
        last = (await self.db.execute(
            select(StoryCommit.received_at)
            .where(StoryCommit.batch_id == batch.id)
            .order_by(StoryCommit.received_at.desc())
            .limit(1)
        )).scalar()
        public = self._public_base(base_url)
        # Who set it up, and in what capacity - a trainer opening this needs to
        # know the lead has already done it rather than doing it again.
        by = None
        if row is not None and row.connected_by:
            actor = (await self.db.execute(
                select(User).where(User.id == row.connected_by)
            )).scalars().first()
            if actor is not None:
                lead = (await self.db.execute(
                    select(ProjectBatchMember.is_lead)
                    .where(ProjectBatchMember.batch_id == batch.id)
                    .where(ProjectBatchMember.student_id == actor.id)
                )).scalar()
                by = {
                    "name": actor.full_name or actor.email,
                    "role": ("Batch leader" if lead
                             else "Team member" if lead is not None else "Trainer"),
                    "at": row.connected_at,
                }
        return {
            "batch_code": batch.batch_code,
            "webhook_url": f"{public}/api/v1/webhooks/git/{batch.batch_code}",
            # False on a local instance: the URL is right, but GitHub cannot
            # reach it without a tunnel, and the screen should say so rather
            # than let a trainer paste it and wonder why nothing arrives.
            "reachable": self._reachable(public),
            "repo_url": row.url if row else None,
            # Shown in full: it is a per-batch webhook secret, and a trainer who
            # cannot read it cannot paste it into GitHub.
            "secret": row.secret if row else None,
            "connected": bool(row and row.secret),
            "connected_by": by,
            "commits": total,
            "last_received_at": last,
            # Who on the team has linked an account. The repository is shared;
            # credit for what is in it is not.
            "team": await self.roster(batch),
            # The convention the students have to follow for a commit to land
            # on a story, spelled out where it is set up.
            "key_example": "US-101 parse the header row",
        }

    async def connect(self, batch: ProjectBatch, repo_url: Optional[str] = None,
                      rotate: bool = False, actor: Optional[User] = None) -> dict:
        """
        Record the repository and mint the secret its pushes must be signed with.

        Rotating is how a leaked secret is dealt with: the old one stops being
        accepted the moment the new one is written.
        """
        row = await self._integration(batch, create=True)
        if repo_url is not None:
            cleaned = repo_url.strip()[:500]
            if cleaned and not cleaned.lower().startswith(("http://", "https://")):
                raise CommitError("The repository link should start with http:// or https://.")
            row.url = cleaned or None
        if rotate or not row.secret:
            row.secret = secrets.token_urlsafe(24)
        if row.url:
            row.state = IntegrationState.CONNECTED
        row.detail = "Push webhook" if row.secret else None
        if actor is not None:
            row.connected_by = actor.id
            row.connected_at = datetime.utcnow()
        await self.db.commit()
        logger.info(f"[Git] {batch.batch_code}: repository connection updated"
                    f"{' (secret rotated)' if rotate else ''}")
        return {"secret": row.secret, "repo_url": row.url}


    # --------------------------------------------------- a student's identity

    VERIFY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no O/0, no I/1

    @classmethod
    def _new_code(cls) -> str:
        return "BB-" + "".join(secrets.choice(cls.VERIFY_ALPHABET) for _ in range(5))

    async def identity_of(self, batch: ProjectBatch, student: User) -> Optional[StudentGitIdentity]:
        return (await self.db.execute(
            select(StudentGitIdentity)
            .where(StudentGitIdentity.batch_id == batch.id)
            .where(StudentGitIdentity.student_id == student.id)
        )).scalars().first()

    async def my_connection(self, batch: ProjectBatch, student: User,
                            base_url: str) -> dict:
        """What one student sees: the team's repository, and their own link to it."""
        row = await self.identity_of(batch, student)
        repo = await self._integration(batch)
        mine = (await self.db.execute(
            select(func.count(StoryCommit.id))
            .where(StoryCommit.batch_id == batch.id)
            .where(StoryCommit.author_id == student.id)
        )).scalar() or 0
        # Commits nobody is credited with yet. Almost always somebody who has
        # not added the email they actually commit from.
        unclaimed = (await self.db.execute(
            select(func.count(StoryCommit.id))
            .where(StoryCommit.batch_id == batch.id)
            .where(StoryCommit.author_id.is_(None))
        )).scalar() or 0
        return {
            "batch_code": batch.batch_code,
            # The repository belongs to the team, and on a student project it is
            # the lead who created it on their own account - so it is the lead,
            # not the trainer, who can add a webhook to it.
            "repo_url": repo.url if repo else None,
            "repo_connected": bool(repo and repo.secret),
            "is_lead": bool(getattr(batch, "_is_lead", False)),
            "provider": row.provider if row else None,
            "username": row.username if row else None,
            "emails": list(row.emails or []) if row else [],
            "verified": bool(row and row.verified_at),
            "verify_code": row.verify_code if row else None,
            "my_commits": mine,
            "unclaimed_commits": unclaimed,
            "last_commit_at": row.last_commit_at if row else None,
            "key_example": "US-101 parse the header row",
        }

    async def claim_identity(self, batch: ProjectBatch, student: User,
                             username: Optional[str] = None,
                             emails: Optional[List[str]] = None,
                             provider: Optional[str] = None,
                             proven: bool = False) -> dict:
        """
        Record the git account and commit addresses this student works under.

        An address belongs to one student per batch. Letting two people claim
        the same one would not be a merge, it would be one of them quietly
        taking the other's work.
        """
        cleaned: List[str] = []
        for address in (emails or []):
            value = (address or "").strip().lower()
            if not value:
                continue
            if "@" not in value or len(value) > 200:
                raise CommitError(f"{address} does not look like an email address.")
            if value not in cleaned:
                cleaned.append(value)
        if len(cleaned) > 5:
            raise CommitError("Five commit addresses is the most one account needs.")

        taken = await self._identities(batch)
        for other in taken:
            if str(other.student_id) == str(student.id):
                continue
            clash = set(a.lower() for a in (other.emails or [])) & set(cleaned)
            if clash:
                raise CommitError(
                    f"{sorted(clash)[0]} is already claimed by another member of "
                    "this batch. Ask your trainer if that is wrong.")

        row = await self.identity_of(batch, student)
        if row is None:
            row = StudentGitIdentity(batch_id=batch.id, student_id=student.id, emails=[])
            self.db.add(row)
        # Read before the write: whether the set changed is what decides
        # whether an earlier proof still covers it.
        previous = set(a.lower() for a in (row.emails or []))
        row.username = (username or "").strip()[:120] or None
        row.provider = (provider or "").strip().lower()[:30] or None
        row.emails = cleaned
        if proven:
            # GitHub itself confirmed the account and the addresses, which is
            # stronger than a code in a commit - so there is nothing left to
            # prove and no code to chase.
            row.verified_at = datetime.utcnow()
            row.verify_code = None
        elif not row.verified_at or set(cleaned) != previous:
            # Anything not yet proven keeps a code outstanding, including an
            # address added after an earlier verification.
            row.verify_code = row.verify_code or self._new_code()

        # Anything already sitting in the repository under one of these
        # addresses was always theirs - it just had nobody to attach to.
        adopted = await self._adopt(batch, student, cleaned, row.username)
        await self.db.commit()
        logger.info(f"[Git] {batch.batch_code}: {student.email} claimed "
                    f"{len(cleaned)} address(es), adopting {adopted} commit(s)")
        return {"adopted": adopted}


    async def link_github(self, batch: ProjectBatch, student: User,
                          login: str, emails: List[str]) -> dict:
        """
        Record what GitHub says about this student, having just proved it.

        Only their verified GitHub addresses are taken. An unverified one on a
        GitHub account is not proof of anything, and this table decides who
        gets credit for work.

        Anything they had already entered by hand is kept: a laptop configured
        with an address that was never added to GitHub is exactly the case
        OAuth cannot see, and dropping it would lose them commits.
        """
        existing = await self.identity_of(batch, student)
        keep = list((existing.emails or []) if existing else [])
        merged = keep + [e for e in emails if e.lower() not in
                         {k.lower() for k in keep}]
        return await self.claim_identity(
            batch, student, username=login, emails=merged[:5],
            provider="github", proven=True)

    async def _adopt(self, batch: ProjectBatch, student: User,
                     emails: List[str], username: Optional[str]) -> int:
        """Credit the commits already stored that these addresses explain."""
        # Their college address needs no claim - it is already theirs, and a
        # student who has git configured with it has commits waiting too.
        addresses = list(emails)
        own = (student.email or "").strip().lower()
        if own and own not in addresses:
            addresses.append(own)
        if not addresses:
            return 0
        rows = (await self.db.execute(
            select(StoryCommit)
            .where(StoryCommit.batch_id == batch.id)
            .where(StoryCommit.author_id.is_(None))
            .where(func.lower(StoryCommit.author_email).in_(addresses))
        )).scalars().all()
        for row in rows:
            row.author_id = student.id
        return len(rows)

    async def roster(self, batch: ProjectBatch) -> List[dict]:
        """Who on the team has linked an account, for the trainer's screen."""
        members = (await self.db.execute(
            select(User)
            .join(ProjectBatchMember, ProjectBatchMember.student_id == User.id)
            .where(ProjectBatchMember.batch_id == batch.id)
            .order_by(User.full_name)
        )).scalars().all()
        identities = {str(r.student_id): r for r in await self._identities(batch)}
        counts = dict((str(sid), n) for sid, n in (await self.db.execute(
            select(StoryCommit.author_id, func.count(StoryCommit.id))
            .where(StoryCommit.batch_id == batch.id)
            .where(StoryCommit.author_id.isnot(None))
            .group_by(StoryCommit.author_id)
        )).all())
        out = []
        for user in members:
            row = identities.get(str(user.id))
            out.append({
                "student_id": str(user.id),
                "name": user.full_name or user.email,
                "username": row.username if row else None,
                "emails": list(row.emails or []) if row else [],
                "connected": row is not None,
                "verified": bool(row and row.verified_at),
                "commits": counts.get(str(user.id), 0),
                "last_commit_at": row.last_commit_at if row else None,
            })
        return out


    async def for_student(self, batch: ProjectBatch, student: User, *,
                          scope: str = "all", search: Optional[str] = None,
                          page: int = 1, per_page: int = 20) -> dict:
        """
        Everything this student has pushed to the batch repository.

        Commits that named no story are part of the answer rather than noise:
        a student looking for work they know they did needs to see the ones
        that landed nowhere, because a missing key is the usual reason a story
        looks emptier than the work behind it.
        """
        base = (
            select(StoryCommit)
            .where(StoryCommit.batch_id == batch.id)
            .where(StoryCommit.author_id == student.id)
        )
        if scope == "linked":
            base = base.where(StoryCommit.story_id.isnot(None))
        elif scope == "unlinked":
            base = base.where(StoryCommit.story_id.is_(None))
        if search:
            term = f"%{search.strip().lower()}%"
            base = base.where(func.lower(StoryCommit.message).like(term))

        total = (await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )).scalar() or 0

        rows = (await self.db.execute(
            base.options(selectinload(StoryCommit.story))
            .order_by(StoryCommit.committed_at.desc().nullslast(),
                      StoryCommit.received_at.desc())
            .offset((max(page, 1) - 1) * per_page)
            .limit(per_page)
        )).scalars().all()

        # The counters are of the whole set, not the filtered page, so the
        # tabs keep their numbers while one of them is selected.
        counts = dict((bool(linked), n) for linked, n in (await self.db.execute(
            select(StoryCommit.story_id.isnot(None), func.count(StoryCommit.id))
            .where(StoryCommit.batch_id == batch.id)
            .where(StoryCommit.author_id == student.id)
            .group_by(StoryCommit.story_id.isnot(None))
        )).all())

        return {
            "rows": [
                {
                    "sha": c.sha,
                    "short_sha": c.sha[:7],
                    "message": c.message.split("\n")[0][:200],
                    "url": c.url,
                    "branch": c.branch,
                    "committed_at": c.committed_at or c.received_at,
                    "story": ({
                        "id": str(c.story.id),
                        "key": c.story.key,
                        "title": c.story.title,
                    } if c.story else None),
                }
                for c in rows
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, -(-total // per_page)),
            "counts": {
                "all": counts.get(True, 0) + counts.get(False, 0),
                "linked": counts.get(True, 0),
                "unlinked": counts.get(False, 0),
            },
        }

    async def for_story(self, story_id: str, limit: int = 50) -> List[dict]:
        """The commits attached to one story, newest first."""
        rows = (await self.db.execute(
            select(StoryCommit)
            # The student behind the commit, where one has claimed the address.
            .options(selectinload(StoryCommit.author))
            .where(StoryCommit.story_id == story_id)
            .order_by(StoryCommit.committed_at.desc().nullslast(),
                      StoryCommit.received_at.desc())
            .limit(limit)
        )).scalars().all()
        return [
            {
                "sha": c.sha,
                "short_sha": c.sha[:7],
                "message": c.message.split("\n")[0][:200],
                "url": c.url,
                "branch": c.branch,
                # The portal's name for them once the account is linked, so
                # the trail reads as the team rather than as git configs.
                "author": ((c.author.full_name if c.author else None)
                           or c.author_name or c.author_email or "Unknown"),
                # False means nobody has claimed this address yet.
                "attributed": c.author_id is not None,
                "committed_at": c.committed_at or c.received_at,
            }
            for c in rows
        ]
