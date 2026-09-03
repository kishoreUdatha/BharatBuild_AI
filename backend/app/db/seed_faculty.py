"""
Faculty Portal Seeder - demo data for the faculty dashboard.

    python -m app.db.seed_faculty

Idempotent: re-running deletes and rebuilds only the rows it created for the
target academic year, so it will not touch real data from other years.

The figures are chosen so the dashboard tells a story: Section B lags on
attendance and progress, a handful of batches are missing base papers, and a
few reviews are already overdue.
"""

import asyncio
import random
from datetime import date, datetime, time, timedelta

from passlib.context import CryptContext
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal, init_db
from app.core.institution_time import to_utc
from app.services.project_details import completeness
from app.models.batch_detail import (
    ProjectMethodologyStep,
    ProjectObjective,
    ProjectScopeItem,
    ProjectTechnology,
    ScopeKind,
)
from app.models.faculty import (
    AttendanceRecord,
    BasePaper,
    BasePaperStatus,
    BatchRegistrationStatus,
    BatchStageProgress,
    ProjectBatch,
    ProjectBatchMember,
    ProjectReview,
    ProjectSubmission,
    ReviewStatus,
    STAGE_ORDER,
    StudentEnrollment,
    StudentProfileStatus,
    SubmissionStatus,
)
from app.models.college import College
from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACADEMIC_YEAR = "2026-27"
DEPARTMENT = "CSE"
YEAR = "4th Year"
SEMESTER = "I"
PROJECT_TYPE = "Major Project"

# section -> (students, batches, unused, progress multiplier)
# The third slot was an attendance rate for seeded registers. Attendance is
# no longer invented, so nothing reads it.
SECTIONS = {
    "A": (64, 16, 0.88, 1.00),
    "B": (60, 15, 0.72, 0.82),
    "C": (56, 14, 0.91, 1.10),
}
UNASSIGNED_STUDENTS = 60

# Baseline percent per stage; each section scales this by its multiplier.
STAGE_BASELINE = [100, 96, 90, 78, 64, 42, 26, 10]

# Enough of a proposal to satisfy the eight checks a registration is judged
# on. Written out rather than generated so a seeded batch reads like something
# a team wrote, not like filler.
OBJECTIVE_TEMPLATES = [
    "Build a working prototype that handles the core case end to end.",
    "Measure accuracy against a labelled sample and report the figure.",
    "Keep the response under two seconds for a typical request.",
    "Document the setup so another team can run it unaided.",
]
METHODOLOGY_TEMPLATES = [
    ("Survey and requirements", "Read the recent work and agree what the system must do."),
    ("Design and data", "Settle the architecture and assemble the dataset."),
    ("Build and test", "Implement in increments, with tests written alongside."),
    ("Evaluate and document", "Measure against the objectives and write it up."),
]
TECHNOLOGY_TEMPLATES = [
    ("Frontend", "React"),
    ("Backend", "FastAPI"),
    ("Database", "PostgreSQL"),
    ("Machine Learning", "scikit-learn"),
]


def _proposal_rows(batch, title: str, rng):
    """The objectives, steps, technologies and scope a submitted batch needs."""
    subject = title.lower()
    batch.problem_statement = (
        f"Work on {subject} is still done by hand in most colleges, which is slow "
        "and inconsistent. This project automates the parts that can be checked "
        "mechanically so the people involved spend their time on the rest."
    )
    batch.objectives = [
        ProjectObjective(position=i, text=text)
        for i, text in enumerate(OBJECTIVE_TEMPLATES[:rng.randint(3, 4)])
    ]
    batch.methodology = [
        ProjectMethodologyStep(position=i, title=step, description=detail)
        for i, (step, detail) in enumerate(METHODOLOGY_TEMPLATES[:rng.randint(3, 4)])
    ]
    batch.technologies = [
        ProjectTechnology(position=i, layer=layer, name=name)
        for i, (layer, name) in enumerate(TECHNOLOGY_TEMPLATES[:rng.randint(3, 4)])
    ]
    batch.scope_items = [
        ProjectScopeItem(kind=ScopeKind.IN_SCOPE, position=0,
                         text=f"A prototype covering the main {subject} workflow."),
        ProjectScopeItem(kind=ScopeKind.OUT_OF_SCOPE, position=0,
                         text="Deployment to production infrastructure."),
        ProjectScopeItem(kind=ScopeKind.DELIVERABLE, position=0,
                         text="Source code, a report and a demonstration."),
        ProjectScopeItem(kind=ScopeKind.OUTCOME, position=0,
                         text="A measurable improvement over the manual process."),
    ]


PROJECT_TITLES = [
    "Medical Image Classification", "Smart Irrigation", "Campus Safety Analytics",
    "Traffic Flow Prediction", "Crop Disease Detection", "Sign Language Translator",
    "Fraud Detection Engine", "Smart Attendance System", "Air Quality Forecasting",
    "Resume Screening Assistant", "Energy Usage Optimiser", "Landslide Early Warning",
    "Speech Emotion Recognition", "Waste Segregation Vision", "Personalised Tutor Bot",
    "Water Leakage Detection",
]

REVIEW_TYPES = ["Progress Review", "Testing Review", "Design Review", "Final Review"]

# A review round runs as a class does: a morning block, fixed-length slots, one
# batch after another. Laying reviews out this way rather than dropping each on
# a random hour is what keeps a reviewer from being booked in two rooms at once.
REVIEW_SLOT_MINUTES = 20
REVIEW_DAY_START = time(10, 0)
REVIEW_SLOTS_PER_DAY = 6

# Roughly this share of reviews sit in the past and were never completed, so
# the "overdue" panels have something real to show.
OVERDUE_SHARE = 0.2


def plan_review_slots(reviewers, batches, today, rng):
    """
    Give every batch a review slot, and no reviewer two slots at once.

    Batches are dealt round-robin to reviewers, then each reviewer's own list is
    laid into consecutive slots across consecutive days. Because a reviewer's
    slots are built as a strict sequence, the schedule cannot clash by
    construction - there is no collision check to get wrong.

    Times are institution-local and converted on the way out: writing 10:00 as
    a UTC timestamp is what made a morning review read as half past four in the
    afternoon.
    """
    dealt = {r.id: [] for r in reviewers}
    for index, batch in enumerate(batches):
        dealt[reviewers[index % len(reviewers)].id].append(batch)

    # Each reviewer's days are taken from a list of working days rather than
    # computed from an offset and then nudged off a weekend: nudging can push
    # two different offsets onto the same Monday, which is a collision the
    # sequence cannot express.
    # Long enough for the busiest reviewer's whole list, so no day is ever
    # reused for two of their blocks - which would put two reviews in one slot.
    blocks = max((len(v) for v in dealt.values()), default=0)
    needed = blocks // REVIEW_SLOTS_PER_DAY + 2
    past_days = _working_days(today - timedelta(days=1), -1, needed)
    future_days = _working_days(today + timedelta(days=1), 1, needed)

    overdue_cut = max(1, int(len(batches) * OVERDUE_SHARE))
    planned, seen = {}, 0

    for reviewer in reviewers:
        for position, batch in enumerate(dealt[reviewer.id]):
            block = position // REVIEW_SLOTS_PER_DAY
            slot = position % REVIEW_SLOTS_PER_DAY
            # The first few reviews dealt overall fall in the past, which is
            # what gives the overdue panels something real to show.
            days = past_days if seen < overdue_cut else future_days
            day = days[block]

            start = (datetime.combine(day, REVIEW_DAY_START)
                     + timedelta(minutes=REVIEW_SLOT_MINUTES * slot))
            planned[batch.id] = {
                "reviewer_id": reviewer.id,
                "scheduled_at": to_utc(start),
                "slot_minutes": REVIEW_SLOT_MINUTES,
            }
            seen += 1
    return planned


def _working_days(start, step, count):
    """`count` weekdays from `start`, walking forwards or backwards."""
    days, day = [], start
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=step)
    return days


async def _college_id(db):
    """
    The demo college these rows belong to.

    college_id became NOT NULL on enrolments, batches and attendance when the
    portal went multi-tenant; seed_academics creates SGIT, so reuse it rather
    than inventing a second institution the structure would not match.
    """
    college = (await db.execute(select(College).where(College.code == "SGIT"))).scalar_one_or_none()
    if college is None:
        raise SystemExit("No SGIT college found - run `python -m app.db.seed_academics` first.")
    return college.id


# Names for the demo roster. "Student 22CS001" made every initial-based avatar
# read the same two letters and every list look like placeholder data, which
# hides exactly the problems a demo is meant to surface. Drawn deterministically
# from the roll number so a re-seed does not shuffle who is who.
FIRST_NAMES = [
    "Aadhya", "Aarav", "Aditi", "Akhil", "Ananya", "Anirudh", "Anjali", "Arjun",
    "Bhavana", "Charan", "Deepika", "Dhruv", "Divya", "Farhan", "Gayatri",
    "Harini", "Harsha", "Ishaan", "Jahnavi", "Karthik", "Kavya", "Keerthi",
    "Lakshmi", "Manasa", "Meghana", "Naveen", "Nikhil", "Nithya", "Pallavi",
    "Pranav", "Praveen", "Priya", "Rahul", "Rakesh", "Ramya", "Rohith",
    "Sahithi", "Sandeep", "Sanjana", "Saketh", "Shreya", "Sindhuja", "Sneha",
    "Srihari", "Sruthi", "Sumanth", "Swathi", "Tejaswi", "Varun", "Vaishnavi",
    "Vamsi", "Vikram", "Vinay", "Yashwanth", "Yamini",
]

LAST_NAMES = [
    "Reddy", "Rao", "Sharma", "Naidu", "Chowdary", "Varma", "Iyer", "Menon",
    "Nair", "Pillai", "Kumar", "Prasad", "Bhat", "Desai", "Joshi", "Kulkarni",
    "Mehta", "Patel", "Shetty", "Gupta", "Agarwal", "Reddi", "Yadav", "Goud",
    "Mudiraj", "Vasu", "Sastry", "Acharya", "Rathod", "Bandari",
]


def student_name(roll: str) -> str:
    """
    A stable name for a roll number.

    Derived from the digits in the roll rather than random, so re-running the
    seeder leaves every student with the name they had.
    """
    digits = "".join(c for c in roll if c.isdigit()) or "0"
    n = int(digits)
    # Multiply before the modulo so neighbouring rolls do not land on the
    # same surname for seven students in a row.
    return f"{FIRST_NAMES[n % len(FIRST_NAMES)]} {LAST_NAMES[(n * 11) % len(LAST_NAMES)]}"


async def seed(rng: random.Random) -> None:
    async with AsyncSessionLocal() as db:
        college_id = await _college_id(db)
        # --- faculty guide -------------------------------------------------
        guide_email = "kavitha@sgit.ac.in"
        guide = (await db.execute(select(User).where(User.email == guide_email))).scalar_one_or_none()
        if guide is None:
            guide = User(
                email=guide_email,
                hashed_password=pwd_context.hash("Faculty@123"),
                full_name="Dr Kavitha",
                role=UserRole.FACULTY,
                department="CSE Department",
                is_active=True,
                is_verified=True,
            )
            db.add(guide)
            await db.flush()
            print(f"  created guide {guide_email} (password: Faculty@123)")
        else:
            print(f"  reusing guide {guide_email}")

        # Batches are shared out across every faculty member, for the same
        # reason the reviews below are: one guide holding all forty-five is
        # not a workload, and it makes the guide column and the student-guide
        # ratio report meaningless. The primary guide stays first in the list
        # so the demo account still owns a full share.
        await db.flush()
        guides = (await db.execute(
            select(User).where(User.role == UserRole.FACULTY).order_by(User.email)
        )).scalars().all() or [guide]
        guides = [guide] + [g for g in guides if g.id != guide.id]

        # --- clear this academic year's previous seed ----------------------
        old_batches = (
            await db.execute(
                select(ProjectBatch.id).where(ProjectBatch.academic_year == ACADEMIC_YEAR)
            )
        ).scalars().all()
        if old_batches:
            # Children cascade at the DB level, but be explicit for SQLite too.
            for model in (ProjectSubmission, BasePaper, ProjectReview, BatchStageProgress, ProjectBatchMember):
                await db.execute(delete(model).where(model.batch_id.in_(old_batches)))
            await db.execute(delete(ProjectBatch).where(ProjectBatch.id.in_(old_batches)))

        old_enrollments = (
            await db.execute(
                select(StudentEnrollment.student_id).where(StudentEnrollment.academic_year == ACADEMIC_YEAR)
            )
        ).scalars().all()
        if old_enrollments:
            # Re-seeding replaces the students, so their attendance has to go
            # with them or it points at rows that no longer exist. Note what
            # that means now that none of it is seeded: running this against a
            # live college destroys registers people actually took.
            await db.execute(delete(AttendanceRecord).where(AttendanceRecord.academic_year == ACADEMIC_YEAR))
            await db.execute(delete(StudentEnrollment).where(StudentEnrollment.academic_year == ACADEMIC_YEAR))
        await db.flush()

        # --- students ------------------------------------------------------
        today = date.today()
        now = datetime.utcnow()
        roll_seq = 1
        students_by_section: dict[str | None, list[User]] = {}

        plan = [(sec, cfg[0]) for sec, cfg in SECTIONS.items()] + [(None, UNASSIGNED_STUDENTS)]

        for section, count in plan:
            bucket: list[User] = []
            for _ in range(count):
                roll = f"22CS{roll_seq:03d}"
                email = f"{roll.lower()}@sgit.ac.in"
                roll_seq += 1

                student = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
                if student is None:
                    student = User(
                        email=email,
                        hashed_password=pwd_context.hash("Student@123"),
                        full_name=student_name(roll),
                        role=UserRole.STUDENT,
                        roll_number=roll,
                        college_name="Sri Guru Institute of Technology",
                        department="Computer Science & Engineering",
                        course="B.Tech",
                        year_semester="4th Year / 7th Semester",
                        batch="2022-2026",
                        section=section,
                        is_active=True,
                    )
                    db.add(student)
                    await db.flush()

                # Set on every run, not just on create - re-seeding reuses
                # existing users, so a create-only assignment would leave older
                # rows without a mobile. Derived from the roll sequence so the
                # numbers stay unique and stable across runs; a few are left
                # blank on purpose to populate the "missing mobile" queue.
                student.phone = None if roll_seq % 60 == 0 else f"9{800000000 + roll_seq}"

                profile_status = rng.choices(
                    [
                        StudentProfileStatus.VERIFIED,
                        StudentProfileStatus.VERIFICATION_PENDING,
                        StudentProfileStatus.PROFILE_INCOMPLETE,
                    ],
                    weights=[88, 8, 4],
                )[0]
                db.add(StudentEnrollment(
                    college_id=college_id,
                    student_id=student.id,
                    department=DEPARTMENT,
                    section=section,
                    year=YEAR,
                    semester=SEMESTER,
                    academic_year=ACADEMIC_YEAR,
                    # A few in Section B have not completed registration.
                    is_registered=not (section == "B" and rng.random() < 0.07),
                    is_active=True,
                    profile_status=profile_status,
                    contact_verified=profile_status == StudentProfileStatus.VERIFIED,
                    declaration_signed=rng.random() < 0.95,
                    # Unassigned students have not accepted a batch invite yet.
                    invitation_accepted=section is not None and rng.random() < 0.97,
                ))
                bucket.append(student)
            students_by_section[section] = bucket
            print(f"  section {section or 'Unassigned'}: {count} students")

        await db.flush()

        # --- attendance ----------------------------------------------------
        # Deliberately not seeded. Attendance is a record of who was in a room
        # on a given morning; inventing it produced a month of plausible
        # history that no trainer had taken, which is the one kind of data a
        # register must never contain. The screens read an empty month
        # correctly - the trainer takes the first one.

        # --- batches -------------------------------------------------------
        total_batches = 0
        # Collected while the batches are built, then laid out in one pass so
        # the round is conflict-free by construction.
        scheduled_batches = []
        for section, cfg in SECTIONS.items():
            count, batch_count, _, multiplier = cfg
            members = list(students_by_section[section])
            rng.shuffle(members)

            for index in range(batch_count):
                code = f"{DEPARTMENT}-{section}-{index + 1:03d}"
                stage_percents = [
                    max(0, min(100, round(base * multiplier + rng.uniform(-6, 6))))
                    for base in STAGE_BASELINE
                ]
                overall = sum(stage_percents) / len(stage_percents)

                batch = ProjectBatch(
                    college_id=college_id,
                    registration_status=rng.choices(
                        [
                            BatchRegistrationStatus.APPROVED,
                            BatchRegistrationStatus.SUBMITTED,
                            BatchRegistrationStatus.PENDING_APPROVAL,
                            BatchRegistrationStatus.CHANGES_REQUESTED,
                            BatchRegistrationStatus.INCOMPLETE,
                            BatchRegistrationStatus.DRAFT,
                        ],
                        weights=[45, 20, 15, 6, 9, 5],
                    )[0],
                    batch_code=code,
                    # The code a student types to join. Derived from the same
                    # sequence as batch_code so the two stay recognisably the
                    # same batch - and without it the invite link is a URL with
                    # nothing after "code=".
                    join_code=f"BB-{DEPARTMENT}-{YEAR[0]}{section}-{index + 1:03d}",
                    title=PROJECT_TITLES[(index + len(section)) % len(PROJECT_TITLES)],
                    department=DEPARTMENT,
                    section=section,
                    year=YEAR,
                    semester=SEMESTER,
                    academic_year=ACADEMIC_YEAR,
                    project_type=PROJECT_TYPE,
                    guide_id=guides[(index + len(section)) % len(guides)].id,
                    overall_progress=overall,
                    is_active=True,
                    # ~1 in 6 batches is left without an abstract so the
                    # "project details incomplete" queue is not empty.
                    abstract=None if index % 6 == 5 else (
                        f"This project builds on recent work in {PROJECT_TITLES[(index + len(section)) % len(PROJECT_TITLES)].lower()}, "
                        "improving accuracy and reducing manual effort through automation."
                    ),
                )
                # Submission starts the review SLA; spread submissions over the
                # past few days so "Due Today" and "Overdue" are both populated.
                if batch.registration_status != BatchRegistrationStatus.DRAFT:
                    batch.submitted_at = now - timedelta(hours=rng.randint(4, 96))
                    batch.review_due_at = batch.submitted_at + timedelta(hours=48)
                # Resolution must follow submission, or the queue reports a
                # negative average resolution time.
                if batch.submitted_at and batch.registration_status in (
                    BatchRegistrationStatus.APPROVED,
                    BatchRegistrationStatus.SUBMITTED,
                ):
                    batch.resolved_at = batch.submitted_at + timedelta(hours=rng.randint(2, 40))

                # A status is a claim about what the team has written. Fill in
                # the proposal for any batch whose status implies one, then let
                # the application's own checklist decide whether the claim
                # stands - seeding SUBMITTED with an empty proposal produced
                # batches locked for review that said "2 of 8 complete", which
                # no team could ever have submitted.
                if batch.registration_status not in (
                    BatchRegistrationStatus.DRAFT,
                    BatchRegistrationStatus.INCOMPLETE,
                ):
                    _proposal_rows(batch, batch.title, rng)

                # `completeness` is the same function the tab renders and the
                # submit button refuses on, so the seeder cannot drift from it.
                if batch.registration_status not in (
                    BatchRegistrationStatus.DRAFT,
                    BatchRegistrationStatus.INCOMPLETE,
                ) and not all(c["passed"] for c in completeness(batch)):
                    batch.registration_status = BatchRegistrationStatus.INCOMPLETE
                    batch.submitted_at = None
                    batch.review_due_at = None
                    batch.resolved_at = None

                db.add(batch)
                await db.flush()
                total_batches += 1

                # 4 members each; one batch per section loses a member.
                chunk = members[index * 4:(index + 1) * 4]
                for position, student in enumerate(chunk):
                    db.add(ProjectBatchMember(
                        batch_id=batch.id,
                        student_id=student.id,
                        is_lead=(position == 0),
                        is_active=not (index == 2 and position == 3),
                    ))

                for stage, percent in zip(STAGE_ORDER, stage_percents):
                    db.add(BatchStageProgress(
                        batch_id=batch.id,
                        stage=stage,
                        percent=percent,
                        completed_at=now if percent >= 100 else None,
                    ))

                # Base papers: mostly verified, a few pending, a couple missing.
                draw = rng.random()
                if draw < 0.08:
                    status = BasePaperStatus.MISSING
                elif draw < 0.20:
                    status = BasePaperStatus.PENDING
                else:
                    status = BasePaperStatus.VERIFIED
                db.add(BasePaper(
                    batch_id=batch.id,
                    title=f"A Survey on {batch.title}",
                    publication="IEEE Access",
                    year=2025,
                    status=status,
                    verified_by_id=guide.id if status == BasePaperStatus.VERIFIED else None,
                    verified_at=now if status == BasePaperStatus.VERIFIED else None,
                ))

                # Keep the workflow state honest: a team that is short-handed or
                # has no base paper cannot sit in an approved/submitted state.
                if status == BasePaperStatus.MISSING or (index == 2):
                    if batch.registration_status in (
                        BatchRegistrationStatus.APPROVED,
                        BatchRegistrationStatus.SUBMITTED,
                    ):
                        batch.registration_status = BatchRegistrationStatus.INCOMPLETE

                # The review itself is booked after every batch exists, so the
                # whole round can be laid out without two landing on one
                # reviewer at the same moment.
                scheduled_batches.append((index, batch))

                # A pending submission on roughly a quarter of batches.
                if rng.random() < 0.27:
                    db.add(ProjectSubmission(
                        batch_id=batch.id,
                        document_type=rng.choice(["SRS", "Project Report", "PPT"]),
                        title=f"{batch.title} - draft",
                        status=SubmissionStatus.PENDING,
                        submitted_at=now - timedelta(days=rng.randint(0, 5)),
                    ))

        # --- reviews -------------------------------------------------------
        # Booked last, across every faculty member rather than all on the one
        # guide: a single reviewer taking sixty reviews is not a schedule, it
        # is a person double-booked sixty times.
        await db.flush()
        reviewers = (await db.execute(
            select(User).where(User.role == UserRole.FACULTY).order_by(User.email)
        )).scalars().all() or [guide]
        plan = plan_review_slots(
            reviewers, [b for _, b in scheduled_batches], now.date(), rng)
        for index, batch in scheduled_batches:
            slot = plan[batch.id]
            db.add(ProjectReview(
                batch_id=batch.id,
                review_type=REVIEW_TYPES[index % len(REVIEW_TYPES)],
                scheduled_at=slot["scheduled_at"],
                slot_minutes=slot["slot_minutes"],
                status=ReviewStatus.SCHEDULED,
                reviewer_id=slot["reviewer_id"],
            ))
        print(f"  {len(scheduled_batches)} reviews across {len(reviewers)} reviewers")

        print(f"  {total_batches} project batches")
        await db.commit()
        print("Faculty portal seed complete.")


async def main() -> None:
    print(f"Seeding faculty portal data for {ACADEMIC_YEAR}...")
    await init_db()
    # Fixed seed so re-running produces the same demo numbers.
    await seed(random.Random(20260819))


if __name__ == "__main__":
    asyncio.run(main())
