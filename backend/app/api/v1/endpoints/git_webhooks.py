"""
Push webhooks from a batch's repository.

Unauthenticated by design - GitHub does not carry a session - so the batch is
named in the URL and the push is proved by an HMAC over the body using the
secret stored on that batch's repository integration. A batch with no secret
recorded accepts nothing: an open endpoint that writes to a student's project
trail is worse than no integration.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.faculty import ProjectBatch
from app.models.project_tracking import BatchIntegration, IntegrationKind
from app.services.git_commits import CommitError, GitCommitService, signature_ok

router = APIRouter(prefix="/webhooks/git", tags=["Git Webhooks"])

MAX_BODY_BYTES = 2 * 1024 * 1024


@router.post("/{batch_code}")
async def receive_push(
    batch_code: str,
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_gitlab_token: str = Header(None),
    x_github_event: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Record a push against this batch, linking commits that name a story.

    Set the URL as the repository's webhook, with the same secret recorded on
    the batch's repository integration:

        https://<host>/api/v1/webhooks/git/CSE-A-001
    """
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Push payload too large")

    batch = (await db.execute(
        select(ProjectBatch).where(ProjectBatch.batch_code == batch_code)
    )).scalars().first()
    # The same answer whether the batch is missing or unconfigured: a probe
    # should not be able to enumerate which batch codes exist.
    unknown = HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No repository is connected for that batch.")
    if batch is None:
        raise unknown

    integration = (await db.execute(
        select(BatchIntegration)
        .where(BatchIntegration.batch_id == batch.id)
        .where(BatchIntegration.kind == IntegrationKind.REPOSITORY)
    )).scalars().first()
    if integration is None or not integration.secret:
        logger.warning(f"[Git] Push for {batch_code} rejected: no secret recorded")
        raise unknown

    # GitHub signs the body; GitLab sends the secret back as a header. Either
    # proves the sender knows it, and neither is checked with ==.
    verified = signature_ok(integration.secret, body, x_hub_signature_256)
    if not verified and x_gitlab_token:
        import hmac as _hmac
        verified = _hmac.compare_digest(x_gitlab_token, integration.secret)
    if not verified:
        logger.warning(f"[Git] Push for {batch_code} failed signature check")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Signature did not match.")

    # A ping is how GitHub tests the hook; answering it is what makes the
    # green tick appear in their UI.
    if x_github_event == "ping":
        return {"ok": True, "pong": True, "batch": batch.batch_code}

    payload = await request.json()
    try:
        result = await GitCommitService(db).record_push(
            batch, payload, provider="gitlab" if x_gitlab_token else "github")
    except CommitError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {"ok": True, "batch": batch.batch_code, **result}
