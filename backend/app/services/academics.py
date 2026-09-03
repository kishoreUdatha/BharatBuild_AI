"""
Departments & Sections - the academic structure browser.

Section metadata (capacity, room, timetable, coordinator, subjects) comes from
`app/models/academics.py`. Everything countable - assigned students, project
batches, attendance, progress, pending reviews - is derived from the
enrolment and batch tables, so this screen can never disagree with the
dashboard about how many students Section B has.

Health thresholds and the attendance-rate definition are imported from
`faculty_dashboard` rather than restated, for the same reason.
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academics import (
    AcademicDepartment,
    AcademicSection,
    DepartmentNotice,
    SectionFacultyAssignment,
    SectionStatus,
    SectionSubject,
    SectionUpdateRequest,
    SubjectKind,
)
from app.models.faculty import (
    BasePaperStatus,
    ProjectBatch,
    ReviewStatus,
    StudentEnrollment,
)
from app.models.user import User
from app.services.faculty_dashboard import (
    attendance_rates,
    ATTENDANCE_EXCELLENT,
    ATTENDANCE_FLOOR,
    ATTENDANCE_ON_TRACK,
    PROGRESS_EXCELLENT,
    PROGRESS_ON_TRACK,
)

# Roles that count towards a section's guide allocation, in display order.
ROLE_ORDER = ["Class Coordinator", "Project Guide", "Review Panel", "HOD"]
GUIDE_ROLE = "Project Guide"


def _pct(part: float, whole: float) -> Optional[int]:
    return int(round(part / whole * 100)) if whole else None


def _name(user: Optional[User]) -> Optional[str]:
    if user is None:
        return None
    return user.full_name or user.email.split("@")[0]


class AcademicsService:
    """Reads for the Departments & Sections screen."""

    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        # The caller's college. Every query this service builds is
        # confined to it - see app/services/tenancy.py.
        self.college_id = college_id

    # ------------------------------------------------------------- structure

    async def structure(self, academic_year: str) -> dict:
        """
        The left-hand tree: school -> department -> year -> semester -> sections.

        Student counts are per department and come from enrolments, so a
        department whose structure exists but which has no cohort loaded reads
        as zero rather than inventing a number.
        """
        departments = (await self.db.execute(
            select(AcademicDepartment)
            .where(AcademicDepartment.academic_year == academic_year)
            .where(AcademicDepartment.is_active.is_(True))
            .where(AcademicDepartment.college_id == self.college_id)
            .options(selectinload(AcademicDepartment.sections))
            .order_by(AcademicDepartment.display_order, AcademicDepartment.code)
        )).scalars().all()

        counts = dict((await self.db.execute(
            select(StudentEnrollment.department, func.count())
            .where(StudentEnrollment.academic_year == academic_year)
            .where(StudentEnrollment.is_active.is_(True))
            .where(StudentEnrollment.college_id == self.college_id)
            .group_by(StudentEnrollment.department)
        )).all())

        schools: Dict[str, List[dict]] = defaultdict(list)
        for dept in departments:
            years: Dict[str, Dict[str, List[AcademicSection]]] = defaultdict(lambda: defaultdict(list))
            for section in dept.sections:
                if section.is_active:
                    years[section.year][section.semester].append(section)

            schools[dept.school].append({
                "id": str(dept.id),
                "code": dept.code,
                "name": dept.name,
                "students": counts.get(dept.code, 0),
                "section_count": sum(len(s) for sems in years.values() for s in sems.values()),
                "years": [
                    {
                        "year": year,
                        "section_count": sum(len(s) for s in sems.values()),
                        "semesters": [
                            {
                                "semester": sem,
                                "sections": sorted(s.name for s in sections),
                                "section_count": len(sections),
                            }
                            for sem, sections in sorted(sems.items())
                        ],
                    }
                    for year, sems in sorted(years.items())
                ],
            })

        return {
            "academic_year": academic_year,
            "schools": [
                {"school": school, "departments": depts, "students": sum(d["students"] for d in depts)}
                for school, depts in sorted(schools.items())
            ],
        }

    # -------------------------------------------------------------- overview

    async def overview(
        self, academic_year: str, department_code: str, year: str, semester: str
    ) -> Optional[dict]:
        department = (await self.db.execute(
            select(AcademicDepartment)
            .where(AcademicDepartment.academic_year == academic_year)
            .where(AcademicDepartment.code == department_code)
            .options(
                selectinload(AcademicDepartment.hod),
                selectinload(AcademicDepartment.dept_coordinator),
                selectinload(AcademicDepartment.project_coordinator),
                selectinload(AcademicDepartment.notices),
            )
        )).scalar_one_or_none()
        if department is None:
            return None

        sections = (await self.db.execute(
            select(AcademicSection)
            .where(AcademicSection.department_id == department.id)
            .where(AcademicSection.year == year)
            .where(AcademicSection.semester == semester)
            .where(AcademicSection.is_active.is_(True))
            .options(
                selectinload(AcademicSection.coordinator),
                selectinload(AcademicSection.faculty).selectinload(SectionFacultyAssignment.faculty_member),
                selectinload(AcademicSection.subjects),
            )
            .order_by(AcademicSection.name)
        )).scalars().all()

        cohort = await self._cohort(academic_year, department_code, year, semester)

        cards, matrix = [], []
        for section in sections:
            metrics = self._section_metrics(section, cohort)
            guides = self._guides(section)
            cards.append({
                "id": str(section.id),
                "name": section.name,
                "students": metrics["students"],
                "batches": metrics["batches"],
                "coordinator": _name(section.coordinator),
                "guide_count": len(guides),
                "guides": [g["name"] for g in guides],
                "registration": metrics["registration"],
                "attendance": metrics["attendance"],
                "progress": metrics["progress"],
                "pending_reviews": metrics["pending_reviews"],
                "status": metrics["health"],
                "status_key": metrics["health"].lower().replace(" ", "_"),
            })
            matrix.append({
                "id": str(section.id),
                "section": section.name,
                "capacity": section.capacity,
                "assigned": metrics["students"],
                "unassigned": max(0, section.capacity - metrics["students"]),
                "over_capacity": max(0, metrics["students"] - section.capacity),
                "batches": metrics["batches"],
                "guides": len(guides),
                "ratio": f"{round(metrics['students'] / len(guides))}:1" if guides and metrics["students"] else "-",
                "coordinator": _name(section.coordinator),
                "room": section.room,
                "timetable": "Published" if section.timetable_published else "Draft",
                "status": section.status.value.title(),
                "status_key": section.status.value,
            })

        unmapped = sum(1 for e in cohort["enrollments"] if not e.section)

        return {
            "department": {
                "id": str(department.id),
                "code": department.code,
                "name": department.name,
                "school": department.school,
                "academic_year": department.academic_year,
                "hod": _name(department.hod),
                "dept_coordinator": _name(department.dept_coordinator),
                "project_coordinator": _name(department.project_coordinator),
            },
            "year": year,
            "semester": semester,
            "section_count": len(sections),
            "assigned_students": sum(c["students"] for c in cards),
            "batch_count": sum(c["batches"] for c in cards),
            "cards": cards,
            "matrix": matrix,
            "unmapped_students": unmapped,
            "notices": [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "detail": n.detail,
                    "window_label": n.window_label,
                    "due_at": n.due_at,
                    "severity": n.severity.value,
                }
                for n in sorted(
                    (n for n in department.notices if n.is_active),
                    key=lambda n: (n.due_at or datetime.max),
                )
            ],
        }

    # -------------------------------------------------------- section detail

    async def load_section(self, section_id: str) -> Optional[AcademicSection]:
        return (await self.db.execute(
            select(AcademicSection)
            .where(AcademicSection.id == section_id)
            .options(
                selectinload(AcademicSection.department),
                selectinload(AcademicSection.coordinator),
                selectinload(AcademicSection.faculty).selectinload(SectionFacultyAssignment.faculty_member),
                selectinload(AcademicSection.subjects).selectinload(SectionSubject.faculty_member),
            )
        )).scalar_one_or_none()

    def _header(self, section: AcademicSection) -> dict:
        dept = section.department
        return {
            "id": str(section.id),
            "name": section.name,
            "department": dept.code,
            "department_name": dept.name,
            "year": section.year,
            "semester": section.semester,
            "academic_year": dept.academic_year,
            "status": section.status.value.title(),
            "status_key": section.status.value,
            "coordinator": _name(section.coordinator),
            "room": section.room,
            "schedule_days": section.schedule_days,
            "schedule_time": section.schedule_time,
            "capacity": section.capacity,
        }

    async def section_overview(self, section: AcademicSection) -> dict:
        cohort = await self._cohort(
            section.department.academic_year, section.department.code,
            section.year, section.semester,
        )
        metrics = self._section_metrics(section, cohort)
        batches = [b for b in cohort["batches"] if b.section == section.name]

        core = sum(1 for s in section.subjects if s.kind == SubjectKind.CORE)
        labs = sum(1 for s in section.subjects if s.kind == SubjectKind.LAB)
        guides = self._guides(section)

        # Attention: the three things a coordinator is expected to act on.
        low_attendance = sum(
            1 for e in cohort["enrollments"]
            if e.section == section.name
            and cohort["rates"].get(str(e.student_id), 100.0) < ATTENDANCE_FLOOR
        )
        missing_paper = sum(
            1 for b in batches
            if b.base_paper is None or b.base_paper.status == BasePaperStatus.MISSING
        )
        attention = []
        over = metrics["students"] - section.capacity
        if over > 0:
            attention.append({"kind": "capacity", "severity": "warning",
                              "label": f"{over} student{'s' if over != 1 else ''} over capacity"})
        pending = metrics["pending_reviews"]
        if pending:
            attention.append({"kind": "reviews", "severity": "critical",
                              "label": f"{pending} review{'s' if pending != 1 else ''} pending"})
        if low_attendance:
            attention.append({"kind": "attendance", "severity": "warning",
                              "label": f"{low_attendance} student{'s' if low_attendance != 1 else ''} "
                                       f"below {int(ATTENDANCE_FLOOR)}% attendance"})
        if missing_paper:
            attention.append({"kind": "base_paper", "severity": "warning",
                              "label": f"{missing_paper} batch{'es' if missing_paper != 1 else ''} missing base paper"})

        distribution = Counter(b.domain or "Unassigned" for b in batches)
        peak = max(distribution.values()) if distribution else 0

        return {
            "header": self._header(section),
            "kpis": [
                {"id": "students", "value": f"{metrics['students']} / {section.capacity}",
                 "label": "Students Assigned",
                 "warn": metrics["students"] > section.capacity},
                {"id": "batches", "value": str(metrics["batches"]), "label": "Project Batches"},
                {"id": "guides", "value": str(len(guides)), "label": "Faculty Guides"},
                {"id": "core", "value": str(core), "label": "Core Subjects"},
                {"id": "labs", "value": str(labs), "label": "Labs"},
                {"id": "progress", "value": f"{metrics['progress'] or 0}%", "label": "Project Progress"},
                {"id": "attendance", "value": f"{metrics['attendance'] or 0}%", "label": "Attendance"},
            ],
            "faculty": self._faculty_summary(section),
            "distribution": [
                {"domain": domain, "count": count,
                 "share": int(round(count / peak * 100)) if peak else 0}
                for domain, count in distribution.most_common()
            ],
            "attention": attention,
            "metrics": metrics,
        }

    async def section_faculty(self, section: AcademicSection) -> dict:
        """Everyone attached to the section, and what each of them covers."""
        by_person = self._faculty_summary(section)
        subjects_by_faculty = defaultdict(list)
        for subject in section.subjects:
            if subject.faculty_id:
                subjects_by_faculty[str(subject.faculty_id)].append(subject.title)

        for person in by_person:
            person["subjects"] = subjects_by_faculty.get(person["id"], [])

        return {
            "header": self._header(section),
            "rows": by_person,
            "role_counts": [
                {"role": role, "count": sum(1 for a in section.faculty if a.role == role)}
                for role in ROLE_ORDER
                if any(a.role == role for a in section.faculty)
            ],
        }

    async def section_subjects(self, section: AcademicSection) -> dict:
        rows = sorted(section.subjects, key=lambda s: (s.display_order, s.title))
        return {
            "header": self._header(section),
            "rows": [
                {
                    "id": str(s.id),
                    "code": s.code,
                    "title": s.title,
                    "kind": s.kind.value.title(),
                    "kind_key": s.kind.value,
                    "credits": s.credits,
                    "faculty": _name(s.faculty_member),
                }
                for s in rows
            ],
            "total_credits": sum(s.credits or 0 for s in rows),
        }

    async def section_projects(self, section: AcademicSection) -> dict:
        cohort = await self._cohort(
            section.department.academic_year, section.department.code,
            section.year, section.semester,
        )
        batches = sorted(
            (b for b in cohort["batches"] if b.section == section.name),
            key=lambda b: b.batch_code,
        )
        return {
            "header": self._header(section),
            "rows": [
                {
                    "id": str(b.id),
                    "batch_code": b.batch_code,
                    "title": b.title,
                    "domain": b.domain,
                    "guide": _name(b.guide),
                    "members": sum(1 for m in b.members if m.is_active),
                    "progress": int(round(b.overall_progress or 0)),
                    "status": b.registration_status.value.replace("_", " ").title(),
                    "status_key": b.registration_status.value,
                    "base_paper": (b.base_paper.status.value if b.base_paper else "missing"),
                }
                for b in batches
            ],
        }

    # ------------------------------------------------------------- my access

    async def my_access(self, user: User, academic_year: str) -> dict:
        """
        What this faculty member can see, and why.

        Derived from their section assignments rather than their profile's
        department string, so the answer matches what the portal will actually
        let them open.
        """
        rows = (await self.db.execute(
            select(SectionFacultyAssignment)
            .where(SectionFacultyAssignment.faculty_id == user.id)
            .options(
                selectinload(SectionFacultyAssignment.section)
                .selectinload(AcademicSection.department)
            )
        )).scalars().all()

        scoped = [
            a for a in rows
            if a.section and a.section.department
            and a.section.department.academic_year == academic_year
        ]
        departments = sorted({a.section.department.code for a in scoped})
        sections = sorted({a.section.name for a in scoped})
        roles = sorted({a.role for a in scoped})

        return {
            "name": _name(user),
            "departments": departments,
            "department_label": ", ".join(f"{d} Department" for d in departments) or (user.department or "-"),
            "sections": sections,
            "section_label": (
                f"Sections {sections[0]}-{sections[-1]}" if len(sections) > 1
                else f"Section {sections[0]}" if sections else "No sections assigned"
            ),
            "roles": roles or ["Faculty"],
            "assignments": [
                {
                    "department": a.section.department.code,
                    "year": a.section.year,
                    "semester": a.section.semester,
                    "section": a.section.name,
                    "role": a.role,
                    "responsibility": a.responsibility,
                }
                for a in sorted(scoped, key=lambda a: (a.section.department.code, a.section.year,
                                                       a.section.semester, a.section.name, a.role))
            ],
        }

    # ------------------------------------------------------- update requests

    async def create_update_request(
        self, *, user: User, department: AcademicDepartment,
        section: Optional[AcademicSection], kind: str, note: str,
    ) -> SectionUpdateRequest:
        request = SectionUpdateRequest(
            section_id=section.id if section else None,
            department_id=department.id,
            requested_by_id=user.id,
            kind=kind,
            note=note.strip(),
        )
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def update_requests(self, department_id: str) -> List[dict]:
        rows = (await self.db.execute(
            select(SectionUpdateRequest)
            .where(SectionUpdateRequest.department_id == department_id)
            .options(
                selectinload(SectionUpdateRequest.section),
                selectinload(SectionUpdateRequest.requested_by),
            )
            .order_by(SectionUpdateRequest.created_at.desc())
            .limit(20)
        )).scalars().all()
        return [
            {
                "id": str(r.id),
                "section": r.section.name if r.section else None,
                "kind": r.kind,
                "note": r.note,
                "status": r.status.value.title(),
                "status_key": r.status.value,
                "requested_by": _name(r.requested_by),
                "created_at": r.created_at,
            }
            for r in rows
        ]

    # ------------------------------------------------------------- internals

    async def _cohort(
        self, academic_year: str, department_code: str, year: str, semester: str
    ) -> dict:
        """
        Everyone and everything in one department/year/semester, loaded once.

        The section cards, the allocation matrix and each section's detail all
        read from this, so they cannot drift apart.
        """
        enrollments = (await self.db.execute(
            select(StudentEnrollment)
            .where(StudentEnrollment.academic_year == academic_year)
            .where(StudentEnrollment.department == department_code)
            .where(StudentEnrollment.year == year)
            .where(StudentEnrollment.is_active.is_(True))
        )).scalars().all()

        batches = (await self.db.execute(
            select(ProjectBatch)
            .where(ProjectBatch.academic_year == academic_year)
            .where(ProjectBatch.department == department_code)
            .where(ProjectBatch.year == year)
            .where(ProjectBatch.is_active.is_(True))
            .options(
                selectinload(ProjectBatch.guide),
                selectinload(ProjectBatch.members),
                selectinload(ProjectBatch.reviews),
                selectinload(ProjectBatch.base_paper),
            )
        )).scalars().all()

        rates = await attendance_rates(
            self.db, [str(e.student_id) for e in enrollments], academic_year
        )
        return {"enrollments": enrollments, "batches": batches, "rates": rates}

    def _section_metrics(self, section: AcademicSection, cohort: dict) -> dict:
        enrollments = [e for e in cohort["enrollments"] if e.section == section.name]
        batches = [b for b in cohort["batches"] if b.section == section.name]

        registered = sum(1 for e in enrollments if e.is_registered)
        rates = [cohort["rates"][str(e.student_id)] for e in enrollments
                 if str(e.student_id) in cohort["rates"]]
        progresses = [b.overall_progress or 0.0 for b in batches]
        pending = sum(1 for b in batches for r in b.reviews if r.status == ReviewStatus.SCHEDULED)

        attendance = int(round(sum(rates) / len(rates))) if rates else None
        progress = int(round(sum(progresses) / len(progresses))) if progresses else None

        return {
            "students": len(enrollments),
            "batches": len(batches),
            "registration": _pct(registered, len(enrollments)),
            "attendance": attendance,
            "progress": progress,
            "pending_reviews": pending,
            "health": self._health(progress, attendance),
        }

    @staticmethod
    def _health(progress: Optional[int], attendance: Optional[int]) -> str:
        if progress is None or attendance is None:
            return "Not Assigned"
        if progress >= PROGRESS_EXCELLENT and attendance >= ATTENDANCE_EXCELLENT:
            return "Excellent"
        if progress >= PROGRESS_ON_TRACK and attendance >= ATTENDANCE_ON_TRACK:
            return "On Track"
        return "Needs Attention"

    @staticmethod
    def _guides(section: AcademicSection) -> List[dict]:
        return [
            {"id": str(a.faculty_id), "name": _name(a.faculty_member)}
            for a in sorted(section.faculty, key=lambda a: a.display_order)
            if a.role == GUIDE_ROLE
        ]

    @staticmethod
    def _faculty_summary(section: AcademicSection) -> List[dict]:
        """One entry per person, with every role they hold on this section."""
        by_person: Dict[str, dict] = {}
        for a in sorted(section.faculty,
                        key=lambda a: (ROLE_ORDER.index(a.role) if a.role in ROLE_ORDER else 99,
                                       a.display_order)):
            key = str(a.faculty_id)
            entry = by_person.setdefault(key, {
                "id": key,
                "name": _name(a.faculty_member),
                "roles": [],
                "responsibilities": [],
            })
            if a.role not in entry["roles"]:
                entry["roles"].append(a.role)
            if a.responsibility and a.responsibility not in entry["responsibilities"]:
                entry["responsibilities"].append(a.responsibility)

        rows = list(by_person.values())
        for row in rows:
            row["role_label"] = ", ".join(row["roles"])
        return rows
