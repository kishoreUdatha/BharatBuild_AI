"""
Cross-tenant isolation test.

Written before the isolation exists, so it fails loudly and describes the
requirement precisely. Every phase of the migration is finished when this
turns green and stays green.

It builds a second college with its own faculty member, then asks - as that
person - for everything the portal will hand over. Nothing belonging to the
first college may come back.

Run inside the backend container:
    python tenant_isolation_test.py
"""
import os
import sys

# Run from anywhere: the backend package root is two directories up from
# tests/integration, and CI invokes this by absolute path, so sys.path[0] is
# this file's directory rather than the application root.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE", "http://localhost:8000/api/v1")

OUTSIDER_EMAIL = "isolation.probe@rivaltech.example"
OUTSIDER_PASSWORD = "Isolation@12345"
OUTSIDER_COLLEGE = "Rival Institute of Technology (isolation probe)"
STUDENT_EMAIL = "isolation.student@rivaltech.example"
ADMIN_EMAIL = "isolation.admin@rivaltech.example"
STUDENT_PASSWORD = "Isolation@12345"

# Real rows belonging to the home college. Asking for one of these by id
# is the test a list-only sweep cannot make: a list can be filtered and
# still leave every fetch-by-id wide open.
TARGETS = {}


async def load_targets():
    """
    Pick real rows belonging to the home college to ask for by id.

    Resolved from the database rather than a file so this runs anywhere -
    a developer's container, a CI job with a freshly seeded database - and
    always points at rows that actually exist.
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.batch_detail import BatchDocument
    from app.models.college import College
    from app.models.faculty import BasePaper, ProjectBatch, ProjectSubmission

    async with AsyncSessionLocal() as db:
        home = (await db.execute(
            select(College).where(College.code == "SGIT")
        )).scalar_one_or_none()
        if home is None:
            return {}
        batch = (await db.execute(
            select(ProjectBatch)
            .where(ProjectBatch.college_id == home.id)
            .order_by(ProjectBatch.batch_code)
        )).scalars().first()
        if batch is None:
            return {}
        doc = (await db.execute(select(BatchDocument)
               .where(BatchDocument.batch_id == batch.id))).scalars().first()
        sub = (await db.execute(select(ProjectSubmission)
               .where(ProjectSubmission.batch_id == batch.id))).scalars().first()
        bp = (await db.execute(select(BasePaper)
              .where(BasePaper.batch_id == batch.id))).scalars().first()
        return {
            "batch_code": batch.batch_code,
            "batch_id": str(batch.id),
            "document_id": str(doc.id) if doc else None,
            "submission_id": str(sub.id) if sub else None,
            "base_paper_id": str(bp.id) if bp else None,
        }

# What the home college's data looks like.
#
# The probe college now owns one batch and one student of its own, so "any
# record at all" no longer works as the oracle - its own rows would read as a
# leak. These markers identify rows belonging to the *other* college, which is
# the only thing that must never appear.
HOME_COLLEGE_HINTS = ("sgit.ac.in", "Sri Guru", "CSE-A-", "CSE-B-", "CSE-C-",
                      "22CS", "22IT")


# --------------------------------------------------------------------------
# tiny HTTP helper - no test framework, so this runs anywhere the app runs
# --------------------------------------------------------------------------
def call(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw)
            except ValueError:
                return r.status, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw.decode("utf-8", "replace")


def login(email, password, attempts=4):
    """
    Sign in, waiting out the login rate limiter if it trips.

    The suite signs in three times and may be run repeatedly, which is enough
    to hit slowapi's limit on /auth/login. That produced a 429 and, before the
    checks were made to fail loudly, a run that quietly skipped five
    assertions and still printed "passed".
    """
    import time

    delay = 5
    for attempt in range(attempts):
        status, body = call("POST", "/auth/login",
                            body={"email": email, "password": password})
        if status == 200 and isinstance(body, dict):
            return body.get("access_token")
        if status != 429:
            return None
        if attempt < attempts - 1:
            print(f"  ..  rate limited signing in as {email}, "
                  f"waiting {delay}s")
            time.sleep(delay)
            delay *= 3
    return None


# --------------------------------------------------------------------------
# the outsider
# --------------------------------------------------------------------------
async def ensure_outsider():
    """A faculty member at an unrelated college, in their own tenant."""
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole

    async with AsyncSessionLocal() as db:
        user = (await db.execute(
            select(User).where(User.email == OUTSIDER_EMAIL)
        )).scalar_one_or_none()
        if user is None:
            user = User(
                email=OUTSIDER_EMAIL,
                hashed_password=get_password_hash(OUTSIDER_PASSWORD),
                full_name="Isolation Probe",
                role=UserRole.FACULTY,
                department="CSE Department",
                college_name=OUTSIDER_COLLEGE,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()

        # Put them in their own tenant if tenancy exists yet. Before the
        # migration this attribute is simply absent, and the test still runs.
        if hasattr(user, "college_id"):
            from app.models.college import College
            college = (await db.execute(
                select(College).where(College.code == "ISOLATION-PROBE")
            )).scalar_one_or_none()
            if college is None:
                college = College(name=OUTSIDER_COLLEGE, code="ISOLATION-PROBE",
                                  is_active=True)
                db.add(college)
                await db.flush()
            if user.college_id != college.id:
                user.college_id = college.id
                await db.commit()


async def ensure_outsider_student():
    """A student at the probe college, for the fetch-by-id probes."""
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.college import College
    from app.models.user import User, UserRole

    async with AsyncSessionLocal() as db:
        college = (await db.execute(
            select(College).where(College.code == "ISOLATION-PROBE")
        )).scalar_one_or_none()
        user = (await db.execute(
            select(User).where(User.email == STUDENT_EMAIL)
        )).scalar_one_or_none()
        if user is None:
            user = User(
                email=STUDENT_EMAIL,
                hashed_password=get_password_hash(STUDENT_PASSWORD),
                full_name="Isolation Student",
                role=UserRole.STUDENT,
                department="CSE",
                college_name=OUTSIDER_COLLEGE,
                college_id=college.id if college else None,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()

        # Give them a batch of their own at the probe college.
        #
        # Without this the download endpoints refuse with "Join a batch
        # before setting up its project" - a real refusal, but the wrong one.
        # It would let the test pass while saying nothing about tenancy, since
        # the student never reaches the code that decides whose file this is.
        from app.models.faculty import (BatchRegistrationStatus, ProjectBatch,
                                        ProjectBatchMember, StudentEnrollment)
        if college is None:
            return
        batch = (await db.execute(
            select(ProjectBatch).where(ProjectBatch.batch_code == "PROBE-A-001")
        )).scalar_one_or_none()
        if batch is None:
            batch = ProjectBatch(
                college_id=college.id,
                batch_code="PROBE-A-001",
                join_code="PROBEJOIN001",
                title="Isolation probe batch",
                department="CSE",
                section="A",
                year="4th Year",
                semester="7",
                academic_year="2026-27",
                project_type="Major Project",
                registration_status=BatchRegistrationStatus.DRAFT,
                is_active=True,
            )
            db.add(batch)
            await db.flush()
        member = (await db.execute(
            select(ProjectBatchMember).where(
                ProjectBatchMember.batch_id == batch.id,
                ProjectBatchMember.student_id == user.id)
        )).scalar_one_or_none()
        if member is None:
            db.add(ProjectBatchMember(batch_id=batch.id, student_id=user.id,
                                      is_lead=True, is_active=True))
        enrol = (await db.execute(
            select(StudentEnrollment).where(StudentEnrollment.student_id == user.id)
        )).scalar_one_or_none()
        if enrol is None:
            db.add(StudentEnrollment(
                college_id=college.id, student_id=user.id, department="CSE",
                section="A", year="4th Year", semester="7",
                academic_year="2026-27", is_registered=True, is_active=True))
        await db.commit()


async def ensure_outsider_admin():
    """
    A college's own administrator at the probe college.

    Not a platform operator: no `is_superuser`. That is the line between
    somebody who runs one institution and somebody who runs the business, and
    this checks the first cannot read across it.
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.college import College
    from app.models.user import User, UserRole

    async with AsyncSessionLocal() as db:
        college = (await db.execute(
            select(College).where(College.code == "ISOLATION-PROBE")
        )).scalar_one_or_none()
        user = (await db.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )).scalar_one_or_none()
        if user is None:
            db.add(User(
                email=ADMIN_EMAIL,
                hashed_password=get_password_hash(STUDENT_PASSWORD),
                full_name="Isolation Admin",
                role=UserRole.ADMIN,
                college_name=OUTSIDER_COLLEGE,
                college_id=college.id if college else None,
                is_active=True,
                is_verified=True,
                is_superuser=False,
            ))
            await db.commit()


async def remove_outsider():
    from sqlalchemy import delete, select

    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        from app.models.faculty import (ProjectBatch, ProjectBatchMember,
                                        StudentEnrollment)
        batch = (await db.execute(
            select(ProjectBatch).where(ProjectBatch.batch_code == "PROBE-A-001")
        )).scalar_one_or_none()
        if batch:
            await db.execute(delete(ProjectBatchMember).where(
                ProjectBatchMember.batch_id == batch.id))
            await db.execute(delete(ProjectBatch).where(ProjectBatch.id == batch.id))

        users = (await db.execute(
            select(User).where(User.email.in_(
                [OUTSIDER_EMAIL, STUDENT_EMAIL, ADMIN_EMAIL]))
        )).scalars().all()
        for user in users:
            await db.execute(delete(StudentEnrollment).where(
                StudentEnrollment.student_id == user.id))
            await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


# --------------------------------------------------------------------------
# what leaking looks like
# --------------------------------------------------------------------------
def leaked(payload, count):
    """
    How many pieces of the home college's data came back.

    Counts rows - JSON records or CSV lines - carrying one of the markers
    above. Two earlier versions of this got it wrong in opposite directions:
    one string-matched only the college name and passed 45 leaked batches that
    carry no name; the next counted every record and failed on the probe
    college's own rows once it had some. This counts foreign rows only.
    """
    blob = payload if isinstance(payload, str) else json.dumps(payload)
    if isinstance(payload, (dict, list)):
        rows = []
        if isinstance(payload, list):
            rows = payload
        else:
            for key in ("items", "rows", "students", "reviews", "results"):
                if isinstance(payload.get(key), list):
                    rows = payload[key]
                    break
        if rows:
            return sum(
                1 for row in rows
                if any(h in json.dumps(row) for h in HOME_COLLEGE_HINTS)
            )
    return sum(
        1 for line in blob.splitlines()
        if any(h in line for h in HOME_COLLEGE_HINTS)
    )


def records(payload, spec):
    """
    How many records of another college's this response carries.

    `spec` names the places real data lives. Aggregate endpoints like the
    dashboard needed this: they return chart scaffolding that is always
    populated (eight stages, three series names) alongside genuine rows, so
    a blanket "any list is data" rule would report a leak on an empty tenant
    and a blanket "no lists" rule missed seventeen project rows.
    """
    if spec is None:                       # plain list endpoints
        if isinstance(payload, dict):
            for key in ("items", "rows", "students", "reviews", "results"):
                if isinstance(payload.get(key), list):
                    return len(payload[key])
        if isinstance(payload, list):
            return len(payload)
        return None

    total = 0
    for path in spec:
        # "attention_items[].count" sums that field across the list.
        field = None
        if "[]." in path:
            path, field = path.split("[].", 1)
        node = payload
        for step in path.split("."):
            if isinstance(node, dict):
                node = node.get(step)
            else:
                node = None
                break
        if isinstance(node, list) and node and isinstance(node[0], dict) and not field:
            # Attribute each row. The probe college has a batch of its own now,
            # so its rows legitimately appear here; only the other college's
            # may not.
            total += sum(
                1 for row in node
                if any(h in json.dumps(row) for h in HOME_COLLEGE_HINTS)
            )
        elif isinstance(node, list):
            if field:
                # A fixed set of summary cards is scaffolding, not data - the
                # dashboard always returns four of them. What matters is the
                # number on each, which must be zero for an empty tenant.
                total += sum(
                    row.get(field, 0) for row in node if isinstance(row, dict)
                )
            else:
                total += len(node)
        elif isinstance(node, dict):
            total += sum(v for v in node.values() if isinstance(v, (int, float)))
        elif isinstance(node, (int, float)):
            total += node
    return total


READS = [
    ("project batches",      "/faculty/batches?limit=200", None),
    ("student roster",       "/faculty/students?limit=300", None),
    ("faculty dashboard",    "/faculty/dashboard",
        # Bare totals are left out on purpose: a number cannot be attributed
        # to a college, and the probe's own batch makes them non-zero. The row
        # lists above carry batch codes, so they can be.
        ["project_rows", "upcoming_reviews", "section_rows"]),
    ("academic structure",   "/faculty/academics/structure", ["schools"]),
    ("structure CSV",        "/faculty/academics/structure.csv", None),
    ("registrations export", "/faculty/registrations/export?academic_year=2026-27", None),
    ("student CSV export",   "/faculty/registrations/students/export?academic_year=2026-27", None),
    # review scheduling, the approval queue, and the student's own portal -
    # the services these run through were never covered by the sweep above.
    ("review list",          "/faculty/reviews?limit=200", None),
    ("review schedule",      "/faculty/reviews/schedule", None),
    ("review options",       "/faculty/reviews/options", None),
    ("approval queue",       "/faculty/registrations/queue", None),
    # Project tracking. Added with the feature rather than after it, so the
    # tracker cannot become the next unscoped read path.
    ("tracker table",        "/faculty/tracking?per_page=100", ["rows"]),
    ("tracker alerts",       "/faculty/tracking/alerts", ["upcoming"]),
    ("task board",           "/faculty/tasks/board", ["rows"]),
    ("blocker queue",        "/faculty/tasks/blockers", ["queue"]),
    ("task workload",        "/faculty/tasks/workload", ["students"]),
    ("milestone board",      "/faculty/milestones/board", ["rows"]),
    ("milestone queue",      "/faculty/milestones/queue", ["approvals"]),
]

# The student portal, asked as a student of the probe college. Each of these
# answers "show me my own", so a leak here means the "my own" is not bounded
# by college.
STUDENT_READS = [
    ("student: registration", "/student/registration"),
    ("student: project",      "/student/project"),
    ("student: documents",    "/student/documents"),
    ("student: submissions",  "/student/submissions"),
    ("student: attendance",   "/student/attendance"),
]


# Rows belonging to the home college, asked for by their real id. Anything
# other than a refusal here is a leak, however well the list endpoints behave.
def by_id_probes():
    t = TARGETS
    code, bid = t.get("batch_code"), t.get("batch_id")
    doc, bp, sub = t.get("document_id"), t.get("base_paper_id"), t.get("submission_id")
    probes = []
    if code:
        probes += [
            ("faculty: tracker detail",   "faculty", f"/faculty/tracking/{code}"),
            ("faculty: batch detail",     "faculty", f"/faculty/batches/{code}"),
            ("faculty: activity log CSV", "faculty", f"/faculty/batches/{code}/activity-log.csv"),
            ("trainer: batch stories",    "faculty", f"/trainer/batches/{code}/stories"),
        ]
    if doc:
        probes += [
            ("faculty: document download", "faculty", f"/faculty/documents/{doc}/download"),
            ("student: document download", "student", f"/student/documents/{doc}/download"),
        ]
    if sub:
        probes.append(
            ("student: submission download", "student", f"/student/submissions/{sub}/download"))
    if bid:
        probes.append(
            ("student: base paper download", "student", f"/student/base-paper/download?batch_id={bid}"))
    return probes


async def home_college_has_data():
    """
    There must be something to leak.

    Run against an empty database - a fresh CI one, say - every endpoint
    returns nothing and every check passes while proving nothing at all. That
    is the most dangerous shape a security test can take, so the fixture is
    asserted before anything is measured.
    """
    from sqlalchemy import func, select

    from app.core.database import AsyncSessionLocal
    from app.models.college import College
    from app.models.faculty import ProjectBatch, StudentEnrollment

    async with AsyncSessionLocal() as db:
        home = (await db.execute(
            select(College).where(College.code == "SGIT")
        )).scalar_one_or_none()
        if home is None:
            return 0, 0
        batches = await db.scalar(select(func.count(ProjectBatch.id))
                                  .where(ProjectBatch.college_id == home.id))
        students = await db.scalar(select(func.count(StudentEnrollment.id))
                                   .where(StudentEnrollment.college_id == home.id))
        return batches or 0, students or 0


def main():
    batches, students = asyncio.run(home_college_has_data())
    if batches < 5 or students < 5:
        print("FAIL  the home college holds no data "
              f"({batches} batches, {students} students).")
        print("      Every check below would pass on an empty database while")
        print("      proving nothing. Seed the fixture before running this.")
        return 1
    print(f"fixture: home college holds {batches} batches, {students} students")

    global TARGETS
    TARGETS = asyncio.run(load_targets())

    asyncio.run(ensure_outsider())
    asyncio.run(ensure_outsider_student())
    asyncio.run(ensure_outsider_admin())
    token = login(OUTSIDER_EMAIL, OUTSIDER_PASSWORD)
    if not token:
        print("FAIL  the probe account could not sign in")
        return 1

    print(f"signed in as {OUTSIDER_EMAIL}")
    print("asserting no row belonging to the home college is returned")
    print()

    failures = 0
    for label, path, spec in READS:
        status, body = call("GET", path, token=token)

        # 403 or 404 is a perfectly good answer - the outsider has no business
        # here at all. What must not happen is a 200 carrying someone else's rows.
        if status in (401, 403, 404):
            print(f"  PASS  {label:24} refused ({status})")
            continue

        count = records(body, spec)
        hits = count if spec else leaked(body, count)
        shown = f"{count} records" if count is not None else f"{len(str(body))} bytes"
        if hits:
            print(f"  FAIL  {label:24} {status} leaked {hits} reference(s), {shown}")
            failures += 1
        else:
            print(f"  PASS  {label:24} {status} clean, {shown}")

    # --- the student's own portal -----------------------------------------
    student_token = login(STUDENT_EMAIL, STUDENT_PASSWORD)
    extra = 0
    if not student_token:
        print()
        print("  FAIL  student sign-in failed; its checks did not run")
        failures += 1
    if student_token:
        print()
        for label, path in STUDENT_READS:
            status, body = call("GET", path, token=student_token)
            extra += 1
            if status in (401, 403, 404, 409):
                print(f"  PASS  {label:30} refused ({status})")
                continue
            hits = leaked(body, None)
            if hits:
                print(f"  FAIL  {label:30} {status} leaked {hits} row(s)")
                failures += 1
            else:
                print(f"  PASS  {label:30} {status} clean")

    # --- a college's own administrator ------------------------------------
    admin_token = login(ADMIN_EMAIL, STUDENT_PASSWORD)
    if not admin_token:
        # Never skip quietly. A sign-in that fails - most often the login rate
        # limiter after repeated runs - would otherwise drop five checks and
        # still print "passed", which is exactly the false green this test
        # exists to prevent.
        print()
        print("  FAIL  admin sign-in failed; its checks did not run")
        failures += 1
    if admin_token:
        print()
        for label, path, platform in [
            ("admin: user directory", "/users/?page=1&page_size=50", False),
            ("admin: user stats",     "/users/stats", False),
            ("admin: platform revenue", "/admin/billing/revenue", True),
            ("admin: platform analytics", "/admin/analytics/overview", True),
            ("admin: pricing plans",  "/admin/plans", True),
        ]:
            status, body = call("GET", path, token=admin_token)
            extra += 1
            if platform:
                # The business's own figures. A customer's administrator has
                # no business here at all, so only a refusal will do.
                if status in (401, 403, 404):
                    print(f"  PASS  {label:30} refused ({status})")
                else:
                    print(f"  FAIL  {label:30} {status} readable by a college admin")
                    failures += 1
                continue
            hits = leaked(body, None)
            if hits:
                print(f"  FAIL  {label:30} {status} leaked {hits} row(s)")
                failures += 1
            else:
                print(f"  PASS  {label:30} {status} clean")

    # --- fetch by id, across the boundary ---------------------------------
    probes = by_id_probes()
    if probes:
        print()
        for label, who, path in probes:
            tok = token if who == "faculty" else student_token
            if not tok:
                print(f"  FAIL  {label:30} no {who} token, check did not run")
                failures += 1
                continue
            status, body = call("GET", path, token=tok)
            if status in (401, 403, 404, 409):
                print(f"  PASS  {label:30} refused ({status})")
            else:
                size = len(body) if isinstance(body, (str, bytes)) else len(str(body))
                print(f"  FAIL  {label:30} {status} returned {size} bytes")
                failures += 1
        checks = len(READS) + len(probes) + extra
    else:
        checks = len(READS) + extra

    asyncio.run(remove_outsider())

    print()
    if failures:
        print(f"{checks - failures} passed, {failures} FAILED "
              f"- another college's data is reachable")
    else:
        print(f"{checks} passed - no cross-tenant data returned")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
