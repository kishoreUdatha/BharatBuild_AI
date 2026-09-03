"""
Who may see, and who may change, a given batch.

The faculty routes all sat behind a single role check: "is this account
faculty?". That is authentication, not authorisation - it let any faculty
member read and mutate any batch in any department, including changing its
leader and verifying its documents.

Authority here is derived from the academic structure that already records it:
a batch's own guide and reviewer, the coordinator of its section, and the
department's HOD and coordinators. Nothing new is invented, and nothing is
trusted just because an identifier was supplied in the URL.
"""

from typing import Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academics import (
    AcademicDepartment,
    AcademicSection,
    SectionFacultyAssignment,
)
from app.models.faculty import ProjectBatch
from app.models.trainer_assignment import TrainerAssignment
from app.models.user import User, UserRole

# Section roles that carry authority to change a batch, as opposed to merely
# being attached to the section.
MANAGING_SECTION_ROLES = {"Class Coordinator", "HOD"}


class FacultyAuthority:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _department_officers(self, code: str, academic_year: str) -> Set[str]:
        """HOD and coordinators of a department, who answer for every batch in it."""
        dept = (await self.db.execute(
            select(AcademicDepartment)
            .where(AcademicDepartment.code == code)
            .where(AcademicDepartment.academic_year == academic_year)
        )).scalar_one_or_none()
        if dept is None:
            return set()
        return {
            str(x) for x in (dept.hod_id, dept.dept_coordinator_id, dept.project_coordinator_id)
            if x is not None
        }

    async def _section_roles(self, user: User, batch: ProjectBatch) -> Set[str]:
        """The roles this user holds on the batch's own section."""
        rows = (await self.db.execute(
            select(SectionFacultyAssignment.role)
            .join(AcademicSection, AcademicSection.id == SectionFacultyAssignment.section_id)
            .join(AcademicDepartment, AcademicDepartment.id == AcademicSection.department_id)
            .where(SectionFacultyAssignment.faculty_id == user.id)
            .where(AcademicDepartment.code == batch.department)
            .where(AcademicDepartment.academic_year == batch.academic_year)
            .where(AcademicSection.year == batch.year)
            .where(AcademicSection.name == batch.section)
        )).scalars().all()
        return set(rows)

    async def _teaches_in_department(self, user: User, code: str, academic_year: str) -> bool:
        """Any role at all in the department, which is enough to look."""
        row = (await self.db.execute(
            select(SectionFacultyAssignment.id)
            .join(AcademicSection, AcademicSection.id == SectionFacultyAssignment.section_id)
            .join(AcademicDepartment, AcademicDepartment.id == AcademicSection.department_id)
            .where(SectionFacultyAssignment.faculty_id == user.id)
            .where(AcademicDepartment.code == code)
            .where(AcademicDepartment.academic_year == academic_year)
            .limit(1)
        )).scalars().first()
        return row is not None

    # ------------------------------------------------------------- decisions

    async def _assigned_to_batch(self, user: User, batch: ProjectBatch) -> bool:
        """
        Does a platform trainer's assignment cover this batch?

        The college must be the one they are currently working in, or a
        trainer scoped to Vignan could still edit Sri Guru's batches. A branch
        or section on the assignment narrows it further; usually there is
        none, and the whole college is theirs.
        """
        from app.services.tenancy import tenants_of

        active = {str(c) for c in tenants_of(user)}
        if str(batch.college_id) not in active:
            return False

        row = (await self.db.execute(
            select(TrainerAssignment.id)
            .where(TrainerAssignment.trainer_id == user.id)
            .where(TrainerAssignment.is_active.is_(True))
            .where(TrainerAssignment.college_id == batch.college_id)
            .where(TrainerAssignment.academic_year == batch.academic_year)
            # Null narrows nothing: no branch means the whole college, and no
            # section means the whole branch.
            .where((TrainerAssignment.department.is_(None))
                   | (TrainerAssignment.department == batch.department))
            .where((TrainerAssignment.section.is_(None))
                   | (TrainerAssignment.section == batch.section))
            .limit(1)
        )).scalars().first()
        return row is not None

    async def can_manage(self, user: User, batch: ProjectBatch) -> bool:
        """May this user change the batch - its team, documents or notes?"""
        if user.role == UserRole.ADMIN:
            return True
        # A platform trainer holds none of a college's own roles, so the checks
        # below would either grant them a whole department they are not part of
        # or refuse the sections they actually teach. Their assignment is the
        # only thing that decides.
        if user.role == UserRole.TRAINER:
            return await self._assigned_to_batch(user, batch)
        # A platform manager does a trainer's job across every college, so the
        # only question is whether the batch is in the college they are
        # currently working in. They hold no assignment and need none - that
        # is the difference between running the trainers and being one.
        if user.role == UserRole.MANAGER:
            from app.services.tenancy import tenants_of
            return str(batch.college_id) in {str(c) for c in tenants_of(user)}
        if batch.guide_id and str(batch.guide_id) == str(user.id):
            return True
        if batch.reviewer_id and str(batch.reviewer_id) == str(user.id):
            return True
        if await self._section_roles(user, batch) & MANAGING_SECTION_ROLES:
            return True
        return str(user.id) in await self._department_officers(
            batch.department, batch.academic_year
        )

    async def can_view(self, user: User, batch: ProjectBatch) -> bool:
        """
        May this user read the batch?

        Wider than management on purpose: a guide on a neighbouring section
        legitimately reviews and compares work across the department. It stops
        at the department boundary.
        """
        if await self.can_manage(user, batch):
            return True
        # For a trainer, reading is the same question as writing: they are not
        # a member of the department, so "a colleague on the next section" -
        # the reason viewing is wider than managing - does not apply.
        if user.role == UserRole.TRAINER:
            return False
        if await self._section_roles(user, batch):
            return True
        return await self._teaches_in_department(user, batch.department, batch.academic_year)

    async def can_act_for_department(self, user: User, code: str,
                                     academic_year: str) -> bool:
        """
        May this user act on a whole department - import a roster into it,
        create batches in it?

        For a college's own staff this is an office they hold: coordinator or
        head. Platform staff hold no office anywhere, so for them it is the
        college they are working in that decides - which is the whole point of
        assigning one. Without this a trainer given a college could not import
        the roster for it, and a manager could not import at all.
        """
        if user.role == UserRole.ADMIN:
            return True

        if user.role == UserRole.MANAGER:
            # They run every college; the picker decides which one.
            return bool(await self._colleges_with_department(user, code,
                                                             academic_year))

        if user.role == UserRole.TRAINER:
            # Only where an assignment covers this department, in the college
            # they are working in.
            from app.services.tenancy import tenants_of
            rows = (await self.db.execute(
                select(TrainerAssignment.id)
                .where(TrainerAssignment.trainer_id == user.id)
                .where(TrainerAssignment.is_active.is_(True))
                .where(TrainerAssignment.academic_year == academic_year)
                .where(TrainerAssignment.college_id.in_(tenants_of(user)))
                # A null department is the whole college, this one included.
                .where((TrainerAssignment.department.is_(None))
                       | (TrainerAssignment.department == code))
                .limit(1)
            )).scalars().first()
            return rows is not None

        if str(user.id) in await self._department_officers(code, academic_year):
            return True
        return await self._teaches_in_department(user, code, academic_year)

    async def _colleges_with_department(self, user: User, code: str,
                                        academic_year: str) -> Set[str]:
        """Which of the caller's colleges run this department at all."""
        from app.services.tenancy import tenants_of
        rows = (await self.db.execute(
            select(ProjectBatch.college_id)
            .where(ProjectBatch.academic_year == academic_year)
            .where(ProjectBatch.department == code)
            .where(ProjectBatch.college_id.in_(tenants_of(user)))
            .limit(1)
        )).scalars().all()
        return {str(r) for r in rows}

    async def managed_batch_ids(self, user: User, academic_year: str) -> Set[str]:
        """
        Every batch this user answers for, in one query set.

        The per-batch checks above decide one case at a time, which is right for
        a route guard but would mean a query per row when listing. This resolves
        the same four sources of authority in bulk: the batches they guide or
        review, the sections they coordinate, the departments they run, and -
        for a platform trainer, who belongs to no college at all - the sections
        they are assigned to teach.
        """
        if user.role == UserRole.ADMIN:
            rows = (await self.db.execute(
                select(ProjectBatch.id).where(ProjectBatch.academic_year == academic_year)
            )).scalars().all()
            return {str(r) for r in rows}

        # A platform trainer's reach is their assignments and nothing else.
        #
        # The other three sources are a college's own hierarchy - guide,
        # section coordinator, head of department - and a trainer holds none
        # of those legitimately. Letting them apply was not theoretical: a
        # trainer assigned to one section was recorded as an officer of the
        # whole department and reached all 45 batches in it, in a college they
        # are not a member of.
        if user.role == UserRole.TRAINER:
            return await self._assigned_batch_ids(user, academic_year)

        # A manager works every batch in the colleges they reach - which is all
        # of them, narrowed to one when they pick a college. Like a trainer
        # they hold none of a college's own roles, so without this the checks
        # below leave them with nothing at all.
        if user.role == UserRole.MANAGER:
            from app.services.tenancy import tenants_of
            colleges = tenants_of(user)
            # Focused on one trainer, the way the college picker focuses on one
            # college: every screen then shows that trainer's work and nothing
            # else. It is a view filter and not a loss of authority - what the
            # manager may *do* is decided by `can_manage`, which is untouched.
            focus = getattr(user, "_focus_trainer_id", None)
            if focus:
                return await self.batch_ids_for_trainer(
                    focus, colleges, academic_year)
            rows = (await self.db.execute(
                select(ProjectBatch.id)
                .where(ProjectBatch.academic_year == academic_year)
                .where(ProjectBatch.college_id.in_(colleges))
            )).scalars().all()
            return {str(r) for r in rows}

        owned = (await self.db.execute(
            select(ProjectBatch.id)
            .where(ProjectBatch.academic_year == academic_year)
            .where((ProjectBatch.guide_id == user.id) | (ProjectBatch.reviewer_id == user.id))
        )).scalars().all()
        ids = {str(r) for r in owned}

        # Sections this user manages, and the whole departments they run.
        managed_sections = (await self.db.execute(
            select(AcademicDepartment.code, AcademicSection.year, AcademicSection.name)
            .select_from(SectionFacultyAssignment)
            .join(AcademicSection, AcademicSection.id == SectionFacultyAssignment.section_id)
            .join(AcademicDepartment, AcademicDepartment.id == AcademicSection.department_id)
            .where(SectionFacultyAssignment.faculty_id == user.id)
            .where(SectionFacultyAssignment.role.in_(MANAGING_SECTION_ROLES))
            .where(AcademicDepartment.academic_year == academic_year)
        )).all()

        officer_depts = (await self.db.execute(
            select(AcademicDepartment.code)
            .where(AcademicDepartment.academic_year == academic_year)
            .where((AcademicDepartment.hod_id == user.id)
                   | (AcademicDepartment.dept_coordinator_id == user.id)
                   | (AcademicDepartment.project_coordinator_id == user.id))
        )).scalars().all()

        if officer_depts:
            rows = (await self.db.execute(
                select(ProjectBatch.id)
                .where(ProjectBatch.academic_year == academic_year)
                .where(ProjectBatch.department.in_(list(officer_depts)))
            )).scalars().all()
            ids.update(str(r) for r in rows)

        for code, year, name in managed_sections:
            rows = (await self.db.execute(
                select(ProjectBatch.id)
                .where(ProjectBatch.academic_year == academic_year)
                .where(ProjectBatch.department == code)
                .where(ProjectBatch.year == year)
                .where(ProjectBatch.section == name)
            )).scalars().all()
            ids.update(str(r) for r in rows)

        return ids

    async def batch_ids_for_trainer(self, trainer_id, colleges,
                                     academic_year: str) -> Set[str]:
        """
        The batches one trainer's assignments cover, inside `colleges`.

        Split out from `_assigned_batch_ids` so a manager can ask the same
        question about somebody else: "show me what this trainer works on".
        The college set is the caller's, never the trainer's, so focusing on a
        trainer can only ever narrow what the manager already reaches.
        """
        assignments = (await self.db.execute(
            select(TrainerAssignment.college_id, TrainerAssignment.department,
                   TrainerAssignment.section)
            .where(TrainerAssignment.trainer_id == trainer_id)
            .where(TrainerAssignment.is_active.is_(True))
            .where(TrainerAssignment.academic_year == academic_year)
            .where(TrainerAssignment.college_id.in_(colleges))
        )).all()

        ids: Set[str] = set()
        for college_id, department, section in assignments:
            query = (
                select(ProjectBatch.id)
                .where(ProjectBatch.academic_year == academic_year)
                .where(ProjectBatch.college_id == college_id)
            )
            # No branch means the whole college - the normal assignment. A
            # branch narrows it, and a section narrows it further.
            if department:
                query = query.where(ProjectBatch.department == department)
                if section:
                    query = query.where(ProjectBatch.section == section)
            rows = (await self.db.execute(query)).scalars().all()
            ids.update(str(r) for r in rows)
        return ids

    async def _assigned_batch_ids(self, user: User, academic_year: str) -> Set[str]:
        """
        The batches inside a platform trainer's assigned sections.

        Matched on college as well as branch and section: two colleges both
        have a CSE with a section A, and without the college in the predicate
        an assignment to one would hand over both.
        """
        # Narrowed to the college the trainer is currently working in, when
        # they have chosen one. `tenants_of` is the single place that decision
        # is recorded, so respecting it here means the switcher reaches every
        # screen without any of them knowing about it.
        from app.services.tenancy import tenants_of
        active = tenants_of(user)

        assignments = (await self.db.execute(
            select(TrainerAssignment.college_id, TrainerAssignment.department,
                   TrainerAssignment.section)
            .where(TrainerAssignment.trainer_id == user.id)
            .where(TrainerAssignment.is_active.is_(True))
            .where(TrainerAssignment.academic_year == academic_year)
            .where(TrainerAssignment.college_id.in_(active))
        )).all()

        ids: Set[str] = set()
        for college_id, department, section in assignments:
            query = (
                select(ProjectBatch.id)
                .where(ProjectBatch.academic_year == academic_year)
                .where(ProjectBatch.college_id == college_id)
            )
            # No branch means the whole college - the normal assignment. A
            # branch narrows it, and a section narrows it further.
            if department:
                query = query.where(ProjectBatch.department == department)
                if section:
                    query = query.where(ProjectBatch.section == section)
            rows = (await self.db.execute(query)).scalars().all()
            ids.update(str(r) for r in rows)
        return ids

    @staticmethod
    def denial(action: str) -> str:
        return (
            f"You do not have authority to {action} for this batch. "
            "Its guide, section coordinator or the department coordinator can."
        )
