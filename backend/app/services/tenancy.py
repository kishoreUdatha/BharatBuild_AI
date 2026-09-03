"""
Which college the caller belongs to, and how to keep queries inside it.

The portal was built for one institution, so its list queries filter on
academic year, department and section - never on the institution itself. That
was invisible while only one college existed and became a data breach the
moment a second account appeared: a faculty member at an unrelated college
could read every batch and download the full student roster.

The write paths were never affected, because they go through
`FacultyAuthority`, which asks *may this person act here*. Tenancy answers a
different question - *whose data is this* - and the two are kept apart on
purpose. Authority decides what a colleague may do; tenancy decides whether
they are a colleague at all.

Everything here fails closed. A portal user with no college gets an error, not
an unfiltered query.
"""
from __future__ import annotations

from typing import Optional, Set
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.college import College
from app.models.user import User, UserRole

SELF_SERVE_CODE = "SELF-SERVE"


class TenantMissing(HTTPException):
    """
    Raised when a portal request cannot be tied to a college.

    Deliberately a 403 rather than a 500: the request is well formed, the
    account simply has no business in the portal until someone places it in
    an institution.
    """

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This account is not attached to a college, so it cannot see "
                "portal data. An administrator needs to assign one."
            ),
        )


def tenant_of(user: User) -> UUID:
    """The caller's college, or refuse the request."""
    college_id = getattr(user, "college_id", None)
    if not college_id:
        raise TenantMissing()
    return college_id


def _is_platform_staff(user: User) -> bool:
    """The operator, or one of their operations managers."""
    return (bool(getattr(user, "is_superuser", False))
            or getattr(user, "role", None) == UserRole.MANAGER)


def tenants_of(user: User) -> Set[UUID]:
    """
    Every college this caller may act in.

    One for almost everybody: a student, a guide and a college administrator
    each belong to exactly one institution. A platform trainer belongs to none
    and is granted particular sections of particular colleges instead, so for
    them this is the set those assignments resolve to.

    An unassigned trainer gets an empty set, which makes every scoped query
    match nothing. That is deliberate: the failure mode of a missing
    assignment must be seeing no data, never seeing all of it.
    """
    if _is_platform_staff(user):
        # The platform operator and their managers, who work across every
        # tenant and belong to none. Resolved and cached the same way a
        # trainer's set is; without it, opening a customer's portal to look at
        # a problem refuses on the grounds that they have no college.
        cached = getattr(user, "_tenant_ids", None)
        if cached is None:
            raise TenantMissing()
        return set(cached)

    if getattr(user, "role", None) == UserRole.TRAINER:
        # Loaded by the caller and cached on the request; see
        # `load_trainer_tenants`. Absent means nothing has been loaded yet,
        # which is not the same as "assigned to nothing" and must not be
        # mistaken for it.
        cached = getattr(user, "_tenant_ids", None)
        if cached is None:
            raise TenantMissing()
        return set(cached)
    return {tenant_of(user)}


async def load_trainer_tenants(db: AsyncSession, user: User) -> Set[UUID]:
    """
    Resolve and cache a trainer's colleges for this request.

    Kept off `tenants_of` so the scoping helpers stay synchronous - they are
    called inside query builders, where an await is not available.
    """
    if _is_platform_staff(user):
        # Every tenant. Platform staff already reach all of them through the
        # platform screens; refusing here would only break the support path.
        rows = (await db.execute(select(College.id))).scalars().all()
        user._tenant_ids = {r for r in rows if r}
        return user._tenant_ids

    if getattr(user, "role", None) != UserRole.TRAINER:
        return {tenant_of(user)}

    from app.models.trainer_assignment import TrainerAssignment
    rows = (await db.execute(
        select(TrainerAssignment.college_id)
        .where(TrainerAssignment.trainer_id == user.id)
        .where(TrainerAssignment.is_active.is_(True))
    )).scalars().all()
    ids = {r for r in rows if r}
    # Cached on the object, not the class: two trainers in one process must
    # never see each other's set.
    user._tenant_ids = ids
    return ids


def acting_college(user: User, requested: Optional[str] = None) -> UUID:
    """
    The single college a write belongs to.

    Reads may span every college a caller reaches, but a write cannot: an
    imported roster, a created batch and a marked register each land in one
    institution. For everybody except a platform trainer that is simply their
    own college. A trainer teaching three colleges has to say which - and if
    they do not, this refuses rather than picking one, because guessing would
    file a roster against the wrong institution.
    """
    allowed = tenants_of(user)
    if requested:
        try:
            wanted = UUID(str(requested))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Not found")
        if wanted not in allowed:
            # Same answer as a college that does not exist: confirming one is
            # real elsewhere is itself a small leak.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Not found")
        return wanted
    if len(allowed) == 1:
        return next(iter(allowed))
    if not allowed:
        raise TenantMissing()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="You work with more than one college. Choose which this is for.",
    )


def same_tenant(user: User, *rows) -> None:
    """
    Guard a row fetched by id.

    List endpoints are scoped by predicate, but anything loaded by a primary
    key or a code has already crossed the boundary by the time it is in hand -
    those callers check here. A missing row is left to the caller; this only
    speaks to ownership.
    """
    mine = tenants_of(user)
    for row in rows:
        if row is None:
            continue
        owner = getattr(row, "college_id", None)
        if owner is None:
            # A row that predates tenancy, or one reached through a parent.
            continue
        if owner not in mine:
            # Deliberately indistinguishable from "does not exist": confirming
            # that a batch code is real elsewhere is itself a small leak.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found",
            )


def scope(stmt, model, user: User):
    """
    Add the tenant predicate to a select.

    Use this rather than writing the filter by hand. The read paths were
    missed once already precisely because each endpoint was responsible for
    remembering, and one place to change beats forty-nine.
    """
    # `in_` rather than `==`: a platform trainer works across several
    # colleges, and an empty set matches nothing rather than everything.
    return stmt.where(model.college_id.in_(tenants_of(user)))


def scope_by_batch(stmt, model, batch_model, user: User):
    """
    Scope a table that reaches its college through `batch_id`.

    Fifteen tables hang off `project_batches` and carry no college of their
    own, so they are constrained through their parent instead of being given
    a redundant column to keep in step.
    """
    return stmt.join(batch_model, model.batch_id == batch_model.id).where(
        batch_model.college_id.in_(tenants_of(user))
    )


async def self_serve_tenant(db: AsyncSession) -> Optional[UUID]:
    """
    The college that individually signed-up students belong to.

    They need somewhere that is not a paying customer's tenant, or they turn
    up in that college's rosters and exports.
    """
    college = (await db.execute(
        select(College).where(College.code == SELF_SERVE_CODE)
    )).scalar_one_or_none()
    return college.id if college else None


async def resolve_for_signup(db: AsyncSession, email: Optional[str],
                             college_name: Optional[str] = None) -> Optional[UUID]:
    """
    Which tenant a new account joins.

    Decided by the email domain, never by what the person typed. The previous
    version matched a typed college name against the colleges table, so
    anybody could type a paying college's name and be placed inside its
    tenant - appearing in its rosters, batches and exports. A name is a claim;
    a mailbox on the college's own domain is evidence.

    `college_name` is still accepted and still recorded on the account as the
    student's own description of where they study, but it no longer decides
    anything. A student whose college uses gmail joins by roster or by batch
    code instead, and until then belongs to the self-serve tenant.
    """
    domain = (email or "").strip().lower().rpartition("@")[2]
    if domain:
        colleges = (await db.execute(
            select(College).where(College.is_active.is_(True))
        )).scalars().all()
        for college in colleges:
            if college.is_self_serve:
                continue
            owned = [d.strip().lower().lstrip("@")
                     for d in (college.email_domains or []) if d and d.strip()]
            # An exact domain, or a subdomain of one it owns: many colleges
            # issue students@sgit.ac.in from the same institution.
            if any(domain == d or domain.endswith("." + d) for d in owned):
                return college.id
    return await self_serve_tenant(db)
