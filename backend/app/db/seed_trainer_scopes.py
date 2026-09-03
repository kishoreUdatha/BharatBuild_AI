"""
Trainers with genuinely different reach, for testing the manager's filters.

Both existing trainers hold whole-college assignments, so filtering by one or
the other returns the same forty-five batches. The filter is correct and looks
broken. This builds a cohort where every trainer covers something different:
one section, one branch, one branch across two colleges, and a whole college.

It also gives Vignan its own academic structure. Vignan had batches but no
departments at all - they were created against Sri Guru's sections, back when
a department code was unique per platform rather than per college.

Idempotent: every row is looked up before it is created, so running it twice
changes nothing. Run it with

    docker exec -w /app bharatbuild_backend python -m app.db.seed_trainer_scopes
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.academics import AcademicDepartment, AcademicSection
from app.models.college import College
from app.models.faculty import ProjectBatch, ProjectBatchMember
from app.models.trainer_assignment import TrainerAssignment
from app.models.user import User, UserRole

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

YEAR = "2026-27"
STUDY_YEAR = "4th Year"
SEMESTER = "I"

# Dev only, and the same one the existing trainer accounts use so there is one
# password to remember while testing rather than five.
PASSWORD = "Trainer@123"

# Branches to stand up per college, with how many batches each section gets.
# Sri Guru already runs CSE A/B/C; these are the ones it does not yet use.
STRUCTURE = {
    "SGIT": {
        "ECE": {"name": "Electronics & Communication", "sections": {"A": 5, "B": 4}},
        "MECH": {"name": "Mechanical Engineering", "sections": {"A": 3}},
    },
    "VIT": {
        "CSE": {"name": "Computer Science & Engineering", "sections": {"A": 4}},
        "ECE": {"name": "Electronics & Communication", "sections": {"B": 3}},
    },
}

# Who works where. A null section means the whole branch; a null branch means
# the whole college. These are deliberately different shapes - the point of the
# fixture is that no two trainers see the same thing.
TRAINERS = [
    {
        "email": "anitha.rao@bharatbuild.ai",
        "name": "Anitha Rao",
        "scopes": [("SGIT", "CSE", "A")],
    },
    {
        "email": "suresh.babu@bharatbuild.ai",
        "name": "Suresh Babu",
        "scopes": [("SGIT", "CSE", None)],
    },
    {
        "email": "meera.krishnan@bharatbuild.ai",
        "name": "Meera Krishnan",
        "scopes": [("SGIT", "ECE", None), ("VIT", "ECE", None)],
    },
    {
        "email": "rahul.verma@bharatbuild.ai",
        "name": "Rahul Verma",
        "scopes": [("SGIT", "MECH", None), ("VIT", None, None)],
    },
]

# Names for the students who fill the new batches. Enough to avoid repeats
# within a section; they cycle across sections, which is fine and realistic.
FIRST = ["Aarav", "Diya", "Ishaan", "Kavya", "Rohan", "Sneha", "Vikram", "Ananya",
         "Karthik", "Meghana", "Nikhil", "Pooja", "Rahul", "Shreya", "Tarun",
         "Vaishnavi", "Yash", "Zoya", "Arjun", "Bhavya"]
LAST = ["Reddy", "Sharma", "Nair", "Iyer", "Menon", "Rao", "Gupta", "Bose",
        "Chowdary", "Pillai"]

TITLES = ["Smart Energy Meter", "Signal Noise Filter", "Antenna Array Design",
          "Gesture Controlled Arm", "Solar Tracker", "Vibration Analyser",
          "Thermal Flow Model", "Drone Payload Rig", "Campus Navigation App",
          "Attendance Vision", "Crop Yield Model", "Traffic Signal Optimiser"]


async def _college(db: AsyncSession, code: str) -> Optional[College]:
    return (await db.execute(
        select(College).where(College.code == code))).scalars().first()


async def _department(db: AsyncSession, college: College, code: str,
                      name: str) -> AcademicDepartment:
    row = (await db.execute(
        select(AcademicDepartment)
        .where(AcademicDepartment.code == code)
        .where(AcademicDepartment.academic_year == YEAR)
        .where(AcademicDepartment.college_id == college.id)
    )).scalars().first()
    if row:
        return row
    row = AcademicDepartment(
        school="School of Engineering", code=code, name=name,
        college_id=college.id, academic_year=YEAR, is_active=True)
    db.add(row)
    await db.flush()
    print(f"    + department {college.code}/{code}")
    return row


async def _section(db: AsyncSession, dept: AcademicDepartment,
                   name: str) -> AcademicSection:
    row = (await db.execute(
        select(AcademicSection)
        .where(AcademicSection.department_id == dept.id)
        .where(AcademicSection.year == STUDY_YEAR)
        .where(AcademicSection.semester == SEMESTER)
        .where(AcademicSection.name == name)
    )).scalars().first()
    if row:
        return row
    row = AcademicSection(department_id=dept.id, name=name, year=STUDY_YEAR,
                          semester=SEMESTER, is_active=True)
    db.add(row)
    await db.flush()
    return row


async def _student(db: AsyncSession, college: College, dept: str, section: str,
                   seq: int) -> User:
    """One student on the college's own domain, so tenancy resolves properly."""
    domain = (college.email_domains or ["example.edu"])[0]
    roll = f"22{dept[:2]}{section}{seq:03d}"
    email = f"{roll.lower()}@{domain}"
    row = (await db.execute(
        select(User).where(User.email == email))).scalars().first()
    if row:
        return row
    first = FIRST[(seq - 1) % len(FIRST)]
    last = LAST[(seq - 1) % len(LAST)]
    row = User(
        email=email,
        # Usernames are unique platform-wide but roll numbers are only unique
        # within a college - two colleges both issue a 22ECB001 - so the
        # college goes in the username and stays out of the roll number.
        username=f"{college.code.lower()}-{roll.lower()}",
        full_name=f"{first} {last}",
        hashed_password=pwd.hash(PASSWORD), role=UserRole.STUDENT,
        college_id=college.id, college_name=college.name,
        roll_number=roll, department=dept, section=section,
        is_active=True, is_verified=True,
    )
    db.add(row)
    await db.flush()
    return row


async def _batches(db: AsyncSession, college: College, dept: str, section: str,
                   count: int) -> int:
    """Create `count` batches for this section, each with a small team."""
    made = 0
    for n in range(1, count + 1):
        code = f"{dept}-{section}-{n:03d}"
        existing = (await db.execute(
            select(ProjectBatch)
            .where(ProjectBatch.batch_code == code)
            .where(ProjectBatch.college_id == college.id)
            .where(ProjectBatch.academic_year == YEAR)
        )).scalars().first()
        if existing:
            continue

        offered = college.project_types or ["Major Project"]
        kind = offered[0]
        batch = ProjectBatch(
            college_id=college.id,
            batch_code=code,
            join_code=f"BB-{college.code}-{dept}-4{section}-{n:03d}",
            title=TITLES[(n - 1) % len(TITLES)],
            department=dept, section=section, year=STUDY_YEAR,
            semester=SEMESTER, academic_year=YEAR,
            project_type=kind,
            team_size=4,
            project_fee=college.fee_for(kind),
            overall_progress=0.0,
            is_active=True,
        )
        db.add(batch)
        await db.flush()

        for seat in range(4):
            student = await _student(db, college, dept, section,
                                     (n - 1) * 4 + seat + 1)
            db.add(ProjectBatchMember(batch_id=batch.id, student_id=student.id,
                                      is_lead=(seat == 0)))
        made += 1
    return made


async def _trainer(db: AsyncSession, email: str, name: str) -> User:
    row = (await db.execute(
        select(User).where(User.email == email))).scalars().first()
    if row:
        return row
    row = User(
        email=email, username=email.split("@")[0], full_name=name,
        hashed_password=pwd.hash(PASSWORD), role=UserRole.TRAINER,
        # Platform staff belong to no college; their reach is their
        # assignments and nothing else.
        college_id=None,
        is_active=True, is_verified=True,
    )
    db.add(row)
    await db.flush()
    print(f"  + trainer {name} <{email}>")
    return row


async def _assign(db: AsyncSession, trainer: User, college: College,
                  dept: Optional[str], section: Optional[str],
                  assigned_by: Optional[User]) -> None:
    existing = (await db.execute(
        select(TrainerAssignment)
        .where(TrainerAssignment.trainer_id == trainer.id)
        .where(TrainerAssignment.college_id == college.id)
        .where(TrainerAssignment.department.is_(None) if dept is None
               else TrainerAssignment.department == dept)
        .where(TrainerAssignment.section.is_(None) if section is None
               else TrainerAssignment.section == section)
        .where(TrainerAssignment.academic_year == YEAR)
    )).scalars().first()
    if existing:
        existing.is_active = True
        return
    db.add(TrainerAssignment(
        trainer_id=trainer.id, college_id=college.id,
        department=dept, section=section, academic_year=YEAR,
        is_active=True,
        assigned_by_id=assigned_by.id if assigned_by else None,
    ))
    where = college.code
    if dept:
        where += f"/{dept}" + (f"-{section}" if section else "")
    else:
        where += " (whole college)"
    print(f"      -> {where}")


async def seed(db: AsyncSession) -> None:
    print("Structure and batches")
    for college_code, branches in STRUCTURE.items():
        college = await _college(db, college_code)
        if college is None:
            print(f"  ! no college {college_code}; skipped")
            continue
        print(f"  {college.code}")
        for dept_code, spec in branches.items():
            dept = await _department(db, college, dept_code, spec["name"])
            for section, count in spec["sections"].items():
                await _section(db, dept, section)
                made = await _batches(db, college, dept_code, section, count)
                print(f"    {dept_code}-{section}: "
                      f"{made} new batches ({count} wanted)")

    await db.commit()

    print("\nTrainers")
    manager = (await db.execute(
        select(User).where(User.role == UserRole.MANAGER))).scalars().first()
    for spec in TRAINERS:
        trainer = await _trainer(db, spec["email"], spec["name"])
        for college_code, dept, section in spec["scopes"]:
            college = await _college(db, college_code)
            if college is None:
                continue
            await _assign(db, trainer, college, dept, section, manager)
    await db.commit()

    print(f"\nDone. Every account above signs in with: {PASSWORD}")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
