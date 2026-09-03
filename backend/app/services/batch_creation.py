"""
Forming a project batch.

Until now nothing in the application created one - only the seeder did. That
left the student portal unreachable in a real deployment, because its whole
flow starts with "enter your batch code" and no code could exist.

A batch is created empty and open: students join it themselves with the code,
which is what the student portal is built around. Faculty can still assign
someone directly from the Student Registrations tab.
"""

import re
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging_config import logger
from app.services.tenancy import acting_college, tenant_of
from app.models.academics import AcademicDepartment, AcademicSection
from app.models.college import College
from app.models.faculty import (
    BatchRegistrationStatus,
    ProjectBatch,
    StudentEnrollment,
)
from app.models.user import User, UserRole, COLLEGE_STAFF_ROLES

DEFAULT_TEAM_SIZE = 4
DEFAULT_FEE = 15000
MAX_TEAM_SIZE = 8
PROJECT_TYPES = ["Major Project", "Minor Project", "Capstone", "Research Project"]


class BatchCreationError(Exception):
    """A refusal the caller can show the user as-is."""


def _year_digit(year: Optional[str]) -> str:
    match = re.match(r"\s*(\d+)", year or "")
    return match.group(1) if match else "4"


class BatchCreationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----------------------------------------------------------- form options

    async def options(self, user: User, academic_year: str) -> dict:
        """
        What the form may offer: the departments and sections that exist, and
        the faculty who could guide. Driven by the academic structure so a batch
        cannot be created against a section nobody has defined.
        """
        departments = (await self.db.execute(
            select(AcademicDepartment)
            .where(AcademicDepartment.academic_year == academic_year)
            .where(AcademicDepartment.is_active.is_(True))
            .options(selectinload(AcademicDepartment.sections))
            .order_by(AcademicDepartment.display_order, AcademicDepartment.code)
        )).scalars().all()

        guides = (await self.db.execute(
            select(User).where(User.role.in_(COLLEGE_STAFF_ROLES)).order_by(User.full_name)
        )).scalars().all()

        return {
            "academic_year": academic_year,
            "departments": [
                {
                    "code": d.code,
                    "name": d.name,
                    "sections": sorted(
                        {(s.year, s.semester, s.name) for s in d.sections if s.is_active}
                    ) and [
                        {"year": s.year, "semester": s.semester, "name": s.name}
                        for s in sorted(
                            (s for s in d.sections if s.is_active),
                            key=lambda s: (s.year, s.semester, s.name),
                        )
                    ],
                }
                for d in departments
            ],
            "project_types": PROJECT_TYPES,
            "guides": [
                {"id": str(g.id), "name": g.full_name or g.email.split("@")[0]}
                for g in guides
            ],
            "defaults": {"team_size": DEFAULT_TEAM_SIZE, "project_fee": DEFAULT_FEE},
        }

    # ------------------------------------------------------------------ codes

    async def _next_codes(self, department: str, year: Optional[str],
                          section: Optional[str], academic_year: str,
                          college_id, college_code: Optional[str]) -> tuple:
        """
        Next free pair of codes for this cohort.

        Both are derived from the same sequence so a batch's faculty-facing code
        and the code a student types stay recognisably the same batch.

        Counted within one college. Shared across colleges, the sequence made a
        new institution's first CSE-A batch "CSE-A-017" because another college
        already had sixteen - a number that says nothing about their own cohort
        and quietly discloses the size of somebody else's.
        """
        existing = (await self.db.execute(
            select(ProjectBatch.batch_code)
            .where(ProjectBatch.academic_year == academic_year)
            .where(ProjectBatch.department == department)
            .where(ProjectBatch.section == section)
            .where(ProjectBatch.college_id == college_id)
        )).scalars().all()

        used = set()
        for code in existing:
            match = re.search(r"(\d+)\s*$", code or "")
            if match:
                used.add(int(match.group(1)))
        seq = 1
        while seq in used:
            seq += 1

        sec = section or "X"
        # The batch code is unique per college, so it needs no prefix. The join
        # code is unique across the platform - a student types it and it has to
        # mean one batch - so it carries the college. Numbering per college
        # without this made two institutions generate the same join code.
        stem = f"BB-{college_code}-" if college_code else "BB-"
        return (
            f"{department}-{sec}-{seq:03d}",
            f"{stem}{department}-{_year_digit(year)}{sec}-{seq:03d}",
        )

    # ----------------------------------------------------------------- create

    async def create(
        self,
        user: User,
        *,
        academic_year: str,
        department: str,
        year: str,
        semester: str,
        section: str,
        project_type: str = "Major Project",
        guide_id: Optional[str] = None,
        team_size: int = DEFAULT_TEAM_SIZE,
        project_fee: Optional[int] = None,
        count: int = 1,
        college_id: Optional[str] = None,
    ) -> dict:
        if not (1 <= count <= 20):
            raise BatchCreationError("Create between 1 and 20 batches at a time.")
        if not (2 <= team_size <= MAX_TEAM_SIZE):
            raise BatchCreationError(f"A team must have between 2 and {MAX_TEAM_SIZE} students.")
        if project_type not in PROJECT_TYPES:
            raise BatchCreationError(f"Project type must be one of {', '.join(PROJECT_TYPES)}.")

        # One college per batch. A trainer working across several says which;
        # everyone else has exactly one and need not.
        target = acting_college(user, college_id)
        college = (await self.db.execute(
            select(College).where(College.id == target)
        )).scalars().first()

        # The fee follows the project type unless one was given explicitly. A
        # minor project rarely costs what a major one does, and the college has
        # already said what each is worth - asking again on every batch is how
        # forty-five batches end up with forty-five chances to mistype it.
        if project_fee is None:
            project_fee = college.fee_for(project_type) if college else DEFAULT_FEE
        if project_fee < 0:
            raise BatchCreationError("The project fee cannot be negative.")

        # A college that has said which projects it runs should not be able to
        # create one it does not.
        offered = (college.project_types if college else None) or []
        if offered and project_type not in offered:
            raise BatchCreationError(
                f"{college.name} does not run {project_type}. It runs: "
                f"{', '.join(offered)}.")

        # The section has to exist in the academic structure. Without this a
        # typo would produce batches that no section screen can ever show.
        section_row = (await self.db.execute(
            select(AcademicSection)
            .join(AcademicDepartment, AcademicDepartment.id == AcademicSection.department_id)
            .where(AcademicDepartment.code == department)
            .where(AcademicDepartment.academic_year == academic_year)
            # In this college. Without it the check passed on any college's
            # structure, so a college with no departments at all could still
            # create batches - validated against a stranger's sections.
            .where(AcademicDepartment.college_id == target)
            .where(AcademicSection.year == year)
            .where(AcademicSection.semester == semester)
            .where(AcademicSection.name == section)
        )).scalars().first()
        if section_row is None:
            raise BatchCreationError(
                f"No section {section} for {department} {year} semester {semester} in "
                f"{academic_year}. Create the section first under Departments & Sections."
            )

        guide = None
        if guide_id:
            guide = (await self.db.execute(
                select(User).where(User.id == guide_id).where(User.role.in_(COLLEGE_STAFF_ROLES))
            )).scalar_one_or_none()
            if guide is None:
                raise BatchCreationError("That guide is not a faculty account.")

        created = []
        for _ in range(count):
            batch_code, join_code = await self._next_codes(
                department, year, section, academic_year, target,
                college.code if college else None)
            batch = ProjectBatch(
                # The batch belongs to the college of whoever created it.
                college_id=target,
                batch_code=batch_code,
                join_code=join_code,
                department=department,
                section=section,
                year=year,
                semester=semester,
                academic_year=academic_year,
                project_type=project_type,
                guide_id=guide.id if guide else None,
                team_size=team_size,
                project_fee=project_fee,
                # Empty and unclaimed: the title, abstract and objectives are the
                # team's to write once they have joined.
                registration_status=BatchRegistrationStatus.DRAFT,
                is_active=True,
            )
            self.db.add(batch)
            try:
                await self.db.flush()
            except IntegrityError:
                # Another coordinator took this number between the read and the
                # write. Roll back and let them retry rather than guess again.
                await self.db.rollback()
                raise BatchCreationError(
                    "Someone created a batch for this section at the same moment. "
                    "Try again and it will take the next number."
                )
            created.append({"id": str(batch.id), "batch_code": batch_code, "join_code": join_code})

        await self.db.commit()
        logger.info(f"[Faculty] {user.email} created {len(created)} batch(es) for "
                    f"{department} {year} sec {section}: {[c['batch_code'] for c in created]}")
        return {
            "created": created,
            "count": len(created),
            "guide": (guide.full_name if guide else None),
            "team_size": team_size,
            "project_fee": project_fee,
            "share": project_fee // max(1, team_size),
        }

    # ------------------------------------------------------------- capacity

    async def unassigned_students(self, department: str, year: str,
                                  section: str, academic_year: str) -> int:
        """
        How many students in this cohort are not yet in a batch.

        Shown next to the form so a coordinator can size the intake instead of
        guessing how many batches to open.
        """
        enrolled = (await self.db.execute(
            select(StudentEnrollment.student_id)
            .where(StudentEnrollment.academic_year == academic_year)
            .where(StudentEnrollment.department == department)
            .where(StudentEnrollment.year == year)
            .where(StudentEnrollment.section == section)
            .where(StudentEnrollment.is_active.is_(True))
        )).scalars().all()
        if not enrolled:
            return 0

        from app.models.faculty import ProjectBatchMember
        placed = (await self.db.execute(
            select(ProjectBatchMember.student_id)
            .where(ProjectBatchMember.student_id.in_(list(enrolled)))
            .where(ProjectBatchMember.is_active.is_(True))
        )).scalars().all()
        return len(set(str(e) for e in enrolled) - set(str(p) for p in placed))
