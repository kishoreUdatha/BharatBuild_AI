"""
Turning a college signup into an enrolment the faculty portal can see.

Registration created a `User` and stopped. Every faculty screen reads
`StudentEnrollment`, so a student who signed up through the college form never
appeared anywhere - the roster import was the only route that actually enrolled
anyone. Two front doors, one of which led nowhere.

This closes that. A self-registered student is enrolled immediately but
**not** verified: they land in the faculty verification queue exactly as an
imported student does, because signing up is a claim about yourself, not a
confirmation by the institution.
"""

import re
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tenancy import self_serve_tenant
from app.core.logging_config import logger
from app.models.academics import AcademicDepartment
from app.models.faculty import StudentEnrollment, StudentProfileStatus
from app.models.user import User, UserRole


def default_academic_year(today: Optional[datetime] = None) -> str:
    """June starts a new academic year, matching the faculty portal."""
    now = today or datetime.utcnow()
    start = now.year if now.month >= 6 else now.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def parse_year_semester(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    "4th Year / 7th Semester" -> ("4th Year", "I").

    Semesters are stored as I or II because that is what a section is scoped by;
    the 7th/8th numbering is a property of the year, not a second dimension.
    Odd semester numbers are the first half of the year, even the second.
    """
    if not raw:
        return None, None
    year_match = re.search(r"(\d+)(?:st|nd|rd|th)\s*Year", raw, re.I)
    year = f"{year_match.group(1)}{_ordinal(int(year_match.group(1)))} Year" if year_match else None

    sem_match = re.search(r"(\d+)(?:st|nd|rd|th)\s*Sem", raw, re.I)
    semester = None
    if sem_match:
        semester = "I" if int(sem_match.group(1)) % 2 == 1 else "II"
    return year, semester


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


async def resolve_department_code(db: AsyncSession, raw: Optional[str],
                                  academic_year: str) -> Optional[str]:
    """
    Map whatever the signup form recorded onto the code enrolments use.

    Users store the full name ("Computer Science & Engineering"); enrolments
    and every faculty filter use the code ("CSE"). Copying the name across
    would produce rows that no screen can find, so the academic structure is
    the authority for the translation.
    """
    if not raw or not raw.strip():
        return None
    value = raw.strip()

    departments = (await db.execute(
        select(AcademicDepartment).where(AcademicDepartment.academic_year == academic_year)
    )).scalars().all()

    lowered = value.lower()
    for d in departments:
        if d.code.lower() == lowered or d.name.lower() == lowered:
            return d.code
    # "CSE Department", "Computer Science & Engineering (CSE)" and similar.
    for d in departments:
        if d.code.lower() in re.findall(r"[a-z]+", lowered):
            return d.code
        if d.name.lower() in lowered or lowered in d.name.lower():
            return d.code

    # No structure seeded for this year yet: keep an uppercase token rather
    # than inventing a department, so a coordinator can correct it later.
    token = re.sub(r"\s*department\s*$", "", value, flags=re.I).strip()
    return token.upper()[:100] if len(token) <= 12 else None


async def ensure_enrollment(
    db: AsyncSession, user: User, *, academic_year: Optional[str] = None, commit: bool = True,
) -> Optional[StudentEnrollment]:
    """
    Give a college student an enrolment for the current academic year.

    Returns the row, existing or new, or None when the account is not a college
    student. Safe to call more than once - the unique constraint on
    (student_id, academic_year) is respected by looking first.
    """
    if user.role != UserRole.STUDENT or not (user.roll_number or "").strip():
        return None

    year_key = academic_year or default_academic_year()
    existing = (await db.execute(
        select(StudentEnrollment)
        .where(StudentEnrollment.student_id == user.id)
        .where(StudentEnrollment.academic_year == year_key)
    )).scalar_one_or_none()
    if existing is not None:
        return existing

    code = await resolve_department_code(db, user.department, year_key)
    if code is None:
        logger.warning(f"[Enrolment] {user.email} has no usable department "
                       f"({user.department!r}); skipping enrolment")
        return None

    year, semester = parse_year_semester(user.year_semester)

    # The student joins their own account's college. An account with none -
    # somebody who signed up on their own rather than through an institution -
    # goes to the self-serve tenant, never into a paying college's roster.
    college_id = user.college_id or await self_serve_tenant(db)
    if college_id is None:
        logger.warning(f"[Enrolment] {user.email} has no college and no "
                       "self-serve tenant exists; skipping enrolment")
        return None

    enrollment = StudentEnrollment(
        college_id=college_id,
        student_id=user.id,
        department=code,
        section=(user.section or None),
        year=year or "1st Year",
        semester=semester,
        academic_year=year_key,
        is_registered=True,
        is_active=True,
        # Self-registration is a claim, not a confirmation. The student joins
        # the same verification queue an imported student does.
        profile_status=StudentProfileStatus.VERIFICATION_PENDING,
        # Email is proven by one-time code before an account can exist, and the
        # mobile too whenever one was given.
        contact_verified=bool(user.phone),
    )
    db.add(enrollment)
    if commit:
        await db.commit()
        await db.refresh(enrollment)
    logger.info(f"[Enrolment] {user.email} enrolled in {code} "
                f"{year or '?'} section {user.section or '-'} for {year_key}")
    return enrollment
