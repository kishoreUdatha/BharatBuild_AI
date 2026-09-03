"""
Academic Structure Seeder - departments, sections, faculty roles and notices.

    python -m app.db.seed_academics

Idempotent: it deletes and rebuilds only the departments it owns for the
target academic year.

Only CSE 4th Year Semester I carries rich metadata (rooms, timetable,
subjects, faculty allocation) because that is the cohort the rest of the
faculty portal is seeded around. Other departments get their structure so the
tree is browsable, but no students - inventing enrolments for them would
change the totals every other faculty screen reports.
"""

import asyncio
import random
from datetime import datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal, init_db
from app.models.academics import (
    AcademicDepartment,
    AcademicSection,
    DepartmentNotice,
    NoticeSeverity,
    SectionFacultyAssignment,
    SectionStatus,
    SectionSubject,
    SectionUpdateRequest,
    SubjectKind,
)
from app.models.college import College
from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACADEMIC_YEAR = "2026-27"
SCHOOL = "School of Engineering"
# The demo institution these departments belong to. `college_id` became
# NOT NULL when academics went multi-tenant, so the structure needs a
# college to hang off - the same one the seeded staff emails imply.
COLLEGE_CODE = "SGIT"
COLLEGE_NAME = "Sri Guru Institute of Technology"
YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
SEMESTERS = ["I", "II"]
SECTION_NAMES = ["A", "B", "C"]

# code -> (name, display order)
DEPARTMENTS = [
    ("CSE", "Computer Science & Engineering", 1),
    ("ECE", "Electronics & Communication (ECE)", 2),
    ("EEE", "Electrical & Electronics (EEE)", 3),
    ("CIVIL", "Civil Engineering", 4),
    ("MECH", "Mechanical Engineering", 5),
]

# The staff the mock names, plus enough guides to make the allocation real.
FACULTY = [
    ("kavitha@sgit.ac.in", "Dr Kavitha"),
    ("ramesh@sgit.ac.in", "Dr Ramesh"),
    ("meena@sgit.ac.in", "Prof Meena"),
    ("suresh@sgit.ac.in", "Dr Suresh Kumar"),
    ("anitha@sgit.ac.in", "Dr Anitha"),
    ("vinod@sgit.ac.in", "Prof Vinod"),
    ("latha@sgit.ac.in", "Dr Latha"),
]

# CSE 4th Year Sem I - the cohort the portal is built around.
# section -> (capacity, room, coordinator, status, project guides)
FEATURED = {
    "A": (64, "CSE-401", "Dr Kavitha", SectionStatus.PUBLISHED,
          ["Dr Kavitha", "Prof Meena", "Dr Anitha", "Prof Vinod", "Dr Latha"]),
    "B": (64, "CSE-402", "Dr Ramesh", SectionStatus.PUBLISHED,
          ["Dr Ramesh", "Dr Anitha", "Prof Vinod", "Dr Latha"]),
    "C": (64, "CSE-403", "Prof Meena", SectionStatus.DRAFT,
          ["Prof Meena", "Dr Kavitha", "Dr Anitha", "Prof Vinod", "Dr Latha"]),
}

SUBJECTS = [
    ("CS401", "Machine Learning", SubjectKind.CORE, 4, "Dr Kavitha"),
    ("CS402", "Distributed Systems", SubjectKind.CORE, 4, "Dr Ramesh"),
    ("CS403", "Information Security", SubjectKind.CORE, 3, "Prof Meena"),
    ("CS404", "Software Architecture", SubjectKind.CORE, 3, "Dr Anitha"),
    ("CS451", "Machine Learning Lab", SubjectKind.LAB, 2, "Dr Kavitha"),
    ("CS452", "Project Work Lab", SubjectKind.LAB, 2, "Dr Ramesh"),
]

NOTICES = [
    ("Project Review Window", "Reviews for all 4th year batches run this week.",
     "22-26 Aug", 7, NoticeSeverity.INFO),
    ("Section B attendance intervention", "Section B is below the 75% attendance floor.",
     "due 20 Aug", 1, NoticeSeverity.WARNING),
    ("Faculty workload allocation", "Confirm guide allocation for the next semester.",
     "closes 21 Aug", 2, NoticeSeverity.INFO),
]


async def _faculty_users(db) -> dict:
    """Find or create the staff the structure references, keyed by name."""
    people = {}
    for email, name in FACULTY:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                hashed_password=pwd_context.hash("Faculty@123"),
                full_name=name,
                role=UserRole.FACULTY,
                department="CSE Department",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()
        people[name] = user
    return people


async def _college(db) -> College:
    """The demo college, created once and reused on every re-run."""
    college = (await db.execute(
        select(College).where(College.code == COLLEGE_CODE)
    )).scalar_one_or_none()
    if college is None:
        college = College(name=COLLEGE_NAME, code=COLLEGE_CODE,
                          city="Coimbatore", state="Tamil Nadu", is_active=True)
        db.add(college)
        await db.flush()
    return college


async def seed(rng: random.Random) -> None:
    async with AsyncSessionLocal() as db:
        people = await _faculty_users(db)
        college = await _college(db)

        # Rebuild only this year's structure. The cascade clears sections,
        # subjects, faculty assignments, notices and requests with it.
        codes = [c for c, _, _ in DEPARTMENTS]
        await db.execute(
            delete(AcademicDepartment).where(
                AcademicDepartment.academic_year == ACADEMIC_YEAR,
                AcademicDepartment.code.in_(codes),
            )
        )
        await db.flush()

        now = datetime.utcnow()

        for code, name, order in DEPARTMENTS:
            department = AcademicDepartment(
                school=SCHOOL,
                code=code,
                name=name,
                college_id=college.id,
                academic_year=ACADEMIC_YEAR,
                hod_id=people["Dr Suresh Kumar"].id,
                dept_coordinator_id=people["Prof Meena"].id,
                project_coordinator_id=people["Dr Ramesh"].id,
                display_order=order,
                is_active=True,
            )
            db.add(department)
            await db.flush()

            featured_dept = code == "CSE"

            for year in YEARS:
                for semester in SEMESTERS:
                    featured = featured_dept and year == "4th Year" and semester == "I"
                    for section_name in SECTION_NAMES:
                        if featured:
                            capacity, room, coord, status, guides = FEATURED[section_name]
                        else:
                            capacity, room = 64, f"{code}-{year[0]}0{SECTION_NAMES.index(section_name) + 1}"
                            coord = FACULTY[SECTION_NAMES.index(section_name)][1]
                            status = SectionStatus.PUBLISHED if semester == "I" else SectionStatus.DRAFT
                            guides = []

                        section = AcademicSection(
                            department_id=department.id,
                            year=year,
                            semester=semester,
                            name=section_name,
                            capacity=capacity,
                            room=room,
                            schedule_days="Mon-Fri",
                            schedule_time="09:00 AM-04:00 PM",
                            coordinator_id=people[coord].id,
                            status=status,
                            timetable_published=status == SectionStatus.PUBLISHED,
                            is_active=True,
                        )
                        db.add(section)
                        await db.flush()

                        if not featured:
                            continue

                        assignments = [
                            (coord, "Class Coordinator", "Section ownership and attendance"),
                            ("Dr Ramesh", "Review Panel", "Chairs the review panel"),
                            ("Dr Suresh Kumar", "HOD", "Department head"),
                        ]
                        for order_index, guide_name in enumerate(guides):
                            assignments.append((guide_name, "Project Guide", "Guides project batches"))

                        seen = set()
                        for order_index, (person, role, responsibility) in enumerate(assignments):
                            key = (person, role)
                            if key in seen:
                                continue
                            seen.add(key)
                            db.add(SectionFacultyAssignment(
                                section_id=section.id,
                                faculty_id=people[person].id,
                                role=role,
                                responsibility=responsibility,
                                display_order=order_index,
                            ))

                        for order_index, (scode, title, kind, credits, teacher) in enumerate(SUBJECTS):
                            db.add(SectionSubject(
                                section_id=section.id,
                                code=scode,
                                title=title,
                                kind=kind,
                                credits=credits,
                                faculty_id=people[teacher].id,
                                display_order=order_index,
                            ))

            if featured_dept:
                for title, detail, window, days, severity in NOTICES:
                    db.add(DepartmentNotice(
                        department_id=department.id,
                        title=title,
                        detail=detail,
                        window_label=window,
                        due_at=now + timedelta(days=days),
                        severity=severity,
                        is_active=True,
                    ))

        await db.commit()

        total = (await db.execute(select(AcademicSection))).scalars().all()
        print(f"Seeded {len(DEPARTMENTS)} departments and {len(total)} sections "
              f"for {ACADEMIC_YEAR}.")


async def main() -> None:
    print("Seeding academic structure...")
    await init_db()
    await seed(random.Random(20260819))


if __name__ == "__main__":
    asyncio.run(main())
