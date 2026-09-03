"""
Colleges - the platform admin's onboarding surface.

Creating a college is the first step of onboarding one, and until now there was
no way to do it through the application at all: the only college in the system
was inserted by a seeder. Everything after this step - departments, rosters,
batches - already has a screen, so this is the piece that was missing.
"""

import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.college import College
from app.models.user import User
from app.modules.auth.dependencies import get_platform_staff

router = APIRouter(prefix="/colleges", tags=["Admin - Colleges"])

# A hostname, lowercase, no scheme and no "@". Deliberately strict: a typo here
# either hands a college nothing or - worse - hands it somebody else's students.
DOMAIN = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$")

# Domains no institution owns. Accepting one would put every Gmail signup into
# that college's tenant.
PUBLIC_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "outlook.com",
    "hotmail.com", "live.com", "icloud.com", "protonmail.com", "proton.me",
    "rediffmail.com", "aol.com", "zoho.com", "mail.com", "yandex.com",
}


def _clean_domains(raw: Optional[List[str]]) -> List[str]:
    """Normalise, validate and de-duplicate, preserving the order given."""
    out: List[str] = []
    for entry in raw or []:
        domain = (entry or "").strip().lower().lstrip("@")
        domain = re.sub(r"^https?://", "", domain).split("/")[0]
        if not domain:
            continue
        if not DOMAIN.match(domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{entry}' is not a valid domain. Use the bare "
                       f"hostname, e.g. sgit.ac.in")
        if domain in PUBLIC_DOMAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{domain} is a public mail provider. Adding it would "
                       f"put every {domain} signup into this college.")
        if domain not in out:
            out.append(domain)
    return out


# What a batch may be. A college picks the ones it actually runs; the list is
# the same one batch creation offers, so the two cannot drift apart.
from app.services.batch_creation import PROJECT_TYPES


class CollegeIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    email_domains: List[str] = Field(default_factory=list)
    default_project_fee: int = Field(15000, ge=0, le=1_000_000)
    project_types: List[str] = Field(default_factory=list)
    project_fees: dict = Field(default_factory=dict)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    # Where this college's project repositories are created. Optional: without
    # both, a team connects a repository by hand and nothing else changes.
    github_org: Optional[str] = Field(None, max_length=120)
    github_installation_id: Optional[str] = Field(None, max_length=40)
    is_active: bool = True

    @field_validator("github_org")
    @classmethod
    def _org(cls, value: Optional[str]) -> Optional[str]:
        if not value or not value.strip():
            return None
        name = value.strip().rstrip("/").split("/")[-1]
        if not re.match(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$", name):
            raise ValueError(
                "Use the organisation's GitHub name, e.g. sgit-projects")
        return name

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        # Upper case and no spaces: the code is typed by people and compared
        # exactly, so "sgit " and "SGIT" must not become two colleges.
        cleaned = re.sub(r"\s+", "-", value.strip().upper())
        if not re.match(r"^[A-Z0-9][A-Z0-9-]*$", cleaned):
            raise ValueError("Use letters, numbers and hyphens, e.g. SGIT")
        return cleaned


class CollegeUpdate(CollegeIn):
    """Same shape; every field is replaced on a PUT."""


def _clean_projects(types: List[str], fees: dict) -> tuple:
    """
    The project types a college runs, and a fee for each.

    A fee for a type the college does not run is dropped rather than kept: it
    would sit in the record looking authoritative while nothing could ever
    read it.
    """
    chosen: List[str] = []
    for entry in types or []:
        name = (entry or "").strip()
        if not name:
            continue
        if name not in PROJECT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{name}' is not a project type. Choose from: "
                       f"{', '.join(PROJECT_TYPES)}.")
        if name not in chosen:
            chosen.append(name)

    priced = {}
    for name in chosen:
        raw = (fees or {}).get(name)
        if raw in (None, ""):
            continue
        try:
            amount = int(raw)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The fee for {name} must be a whole number of rupees.")
        if amount < 0 or amount > 1_000_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The fee for {name} looks wrong: {amount}.")
        priced[name] = amount
    return chosen, priced


def _github_configured() -> bool:
    """Whether the deployment holds the App credentials at all."""
    from app.services.github_repos import configured
    return configured()


async def _get(db: AsyncSession, college_id: str) -> College:
    college = (await db.execute(
        select(College).where(College.id == college_id))).scalars().first()
    if college is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No such college.")
    return college


async def _row(db: AsyncSession, college: College) -> dict:
    students = (await db.execute(
        select(func.count()).select_from(User)
        .where(User.college_id == college.id))).scalar() or 0
    return {
        "id": str(college.id),
        "name": college.name,
        "code": college.code,
        "email_domains": college.email_domains or [],
        "default_project_fee": college.default_project_fee,
        "project_types": college.project_types or [],
        "project_fees": college.project_fees or {},
        "city": college.city,
        "state": college.state,
        "email": college.email,
        "phone": college.phone,
        "website": college.website,
        "github_org": college.github_org,
        "github_installation_id": college.github_installation_id,
        # Whether a repository can actually be created for this college's
        # batches: both halves recorded here, and the App's own credentials
        # present on the server.
        "github_ready": bool(college.github_org
                             and college.github_installation_id
                             and _github_configured()),
        "is_active": college.is_active,
        "is_self_serve": college.is_self_serve,
        "accounts": students,
        "created_at": college.created_at,
        # The self-serve tenant is where unmatched signups land. It is not a
        # customer, and editing or deleting it would strand those accounts.
        "editable": not college.is_self_serve,
    }


@router.get("")
async def list_colleges(
    search: Optional[str] = Query(None, max_length=100),
    include_inactive: bool = Query(True),
    current_user: User = Depends(get_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    """Every college on the platform, with how many accounts each holds."""
    query = select(College)
    if not include_inactive:
        query = query.where(College.is_active.is_(True))
    if search:
        needle = f"%{search.strip().lower()}%"
        query = query.where(func.lower(College.name).like(needle)
                            | func.lower(College.code).like(needle))
    colleges = (await db.execute(
        query.order_by(College.is_self_serve, College.name))).scalars().all()
    rows = [await _row(db, c) for c in colleges]
    return {
        "rows": rows,
        "totals": {
            "colleges": sum(1 for r in rows if not r["is_self_serve"]),
            "active": sum(1 for r in rows
                          if r["is_active"] and not r["is_self_serve"]),
            "accounts": sum(r["accounts"] for r in rows),
            # A college with no domains cannot take self-service signups, so
            # it is the number worth watching during onboarding.
            "without_domains": sum(1 for r in rows if not r["is_self_serve"]
                                   and not r["email_domains"]),
        },
        # Offered to the form, so the choices there are the same ones batch
        # creation accepts.
        "available_project_types": PROJECT_TYPES,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_college(
    body: CollegeIn,
    current_user: User = Depends(get_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    """Onboard a college."""
    domains = _clean_domains(body.email_domains)
    types, fees = _clean_projects(body.project_types, body.project_fees)
    await _refuse_clashes(db, body.code, domains, exclude=None)

    college = College(
        name=body.name.strip(),
        code=body.code,
        email_domains=domains,
        default_project_fee=body.default_project_fee,
        project_types=types,
        project_fees=fees,
        city=body.city, state=body.state, email=body.email,
        phone=body.phone, website=body.website,
        github_org=body.github_org,
        github_installation_id=(body.github_installation_id or "").strip() or None,
        is_active=body.is_active,
        is_self_serve=False,
    )
    db.add(college)
    await db.commit()
    logger.info(f"[Colleges] {current_user.email} onboarded {college.code} "
                f"with domains {domains}")
    return await _row(db, college)


@router.put("/{college_id}")
async def update_college(
    college_id: str,
    body: CollegeUpdate,
    current_user: User = Depends(get_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    college = await _get(db, college_id)
    if college.is_self_serve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The self-serve tenant cannot be edited. Unmatched signups "
                   "belong to it.")

    domains = _clean_domains(body.email_domains)
    types, fees = _clean_projects(body.project_types, body.project_fees)
    await _refuse_clashes(db, body.code, domains, exclude=str(college.id))

    college.name = body.name.strip()
    college.code = body.code
    college.email_domains = domains
    college.default_project_fee = body.default_project_fee
    college.project_types = types
    college.project_fees = fees
    college.city, college.state = body.city, body.state
    college.email, college.phone = body.email, body.phone
    college.website = body.website
    college.github_org = body.github_org
    college.github_installation_id = (
        (body.github_installation_id or "").strip() or None)
    college.is_active = body.is_active
    college.updated_at = datetime.utcnow()
    await db.commit()
    logger.info(f"[Colleges] {current_user.email} updated {college.code}")
    return await _row(db, college)


@router.post("/{college_id}/active")
async def set_active(
    college_id: str,
    active: bool = Query(...),
    current_user: User = Depends(get_platform_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Switch a college on or off.

    Deactivating rather than deleting: accounts, batches and attendance point
    at this row, and removing it would orphan a college's whole history. An
    inactive college stops taking new signups and keeps everything it has.
    """
    college = await _get(db, college_id)
    if college.is_self_serve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="The self-serve tenant cannot be switched off.")
    college.is_active = active
    college.updated_at = datetime.utcnow()
    await db.commit()
    logger.info(f"[Colleges] {current_user.email} set {college.code} "
                f"active={active}")
    return await _row(db, college)


async def _refuse_clashes(db: AsyncSession, code: str, domains: List[str],
                          *, exclude: Optional[str]) -> None:
    """
    A code or a domain may belong to one college only.

    A shared domain is the serious one: two colleges claiming sgit.ac.in means
    a student's tenant depends on which row happens to be read first.
    """
    others = (await db.execute(select(College))).scalars().all()
    for other in others:
        if exclude and str(other.id) == exclude:
            continue
        if (other.code or "").upper() == code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The code {code} is already used by {other.name}.")
        taken = {d.lower() for d in (other.email_domains or [])}
        clash = taken.intersection(domains)
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{', '.join(sorted(clash))} already belongs to "
                       f"{other.name}.")
