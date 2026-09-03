"""
Student Registrations Service - the Student Registrations tab.

Same shape as the batch view: one aggregate for the whole tab (KPIs, attention
list, profile-completion bars, paged rows) plus the mutations its toolbar runs.
"""

from collections import Counter
from dataclasses import dataclass
from math import ceil
from typing import Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.faculty import (
    ProjectBatch,
    ProjectBatchMember,
    StudentEnrollment,
    StudentProfileStatus,
)
from app.models.user import User

PROFILE_LABELS = {
    StudentProfileStatus.VERIFIED: "Verified",
    StudentProfileStatus.VERIFICATION_PENDING: "Verification Pending",
    StudentProfileStatus.PROFILE_INCOMPLETE: "Profile Incomplete",
}


@dataclass
class StudentFilters:
    academic_year: str
    department: Optional[str] = None
    section: Optional[str] = None
    year: Optional[str] = None
    semester: Optional[str] = None
    batch_status: Optional[str] = None   # in_batch | not_in_batch
    profile_status: Optional[str] = None
    search: Optional[str] = None


def _is_all(value: Optional[str]) -> bool:
    return value is None or not value.strip() or value.strip().lower().startswith("all")


class FacultyStudentsService:
    def __init__(self, db: AsyncSession, college_id=None):
        self.db = db
        # The caller's college. Every query this service builds is
        # confined to it - see app/services/tenancy.py.
        self.college_id = college_id

    async def _load(self, f: StudentFilters):
        """Enrollments with their user, plus a student_id -> (batch, role) map."""
        stmt = (
            select(StudentEnrollment, User)
            .join(User, StudentEnrollment.student_id == User.id)
            .where(StudentEnrollment.academic_year == f.academic_year)
            .where(StudentEnrollment.is_active.is_(True))
        )
        # The roster carries names, roll numbers, mobile numbers and email
        # addresses. It must never cross a college boundary.
        if self.college_id:
            stmt = stmt.where(StudentEnrollment.college_id == self.college_id)
        if not _is_all(f.department):
            stmt = stmt.where(StudentEnrollment.department == f.department)
        if not _is_all(f.section):
            stmt = stmt.where(StudentEnrollment.section == f.section)
        if not _is_all(f.year):
            stmt = stmt.where(StudentEnrollment.year == f.year)
        if not _is_all(f.semester):
            stmt = stmt.where(StudentEnrollment.semester == f.semester)
        if not _is_all(f.profile_status):
            stmt = stmt.where(
                StudentEnrollment.profile_status == StudentProfileStatus(f.profile_status)
            )
        rows = (await self.db.execute(stmt)).all()

        batch_stmt = (
            select(ProjectBatch)
            .options(selectinload(ProjectBatch.members))
            .where(ProjectBatch.academic_year == f.academic_year)
            .where(ProjectBatch.is_active.is_(True))
        )
        if self.college_id:
            batch_stmt = batch_stmt.where(ProjectBatch.college_id == self.college_id)
        batches = list((await self.db.execute(batch_stmt)).scalars().unique().all())

        membership: Dict[str, tuple] = {}
        for batch in batches:
            for member in batch.members:
                if member.is_active:
                    membership[str(member.student_id)] = (batch, member.is_lead)

        return rows, membership, batches

    @staticmethod
    def _row(enrollment: StudentEnrollment, user: User, membership: Dict[str, tuple]) -> dict:
        entry = membership.get(str(enrollment.student_id))
        batch, is_lead = entry if entry else (None, False)
        return {
            "id": str(enrollment.id),
            "student_id": str(user.id),
            "full_name": user.full_name,
            "roll_number": user.roll_number,
            "department": enrollment.department,
            "section": enrollment.section,
            "mobile": user.phone,
            "email": user.email,
            "batch_code": batch.batch_code if batch else None,
            "role": ("Batch Leader" if is_lead else "Member") if batch else None,
            "profile_status": PROFILE_LABELS[enrollment.profile_status],
            "profile_status_key": enrollment.profile_status.value,
        }

    async def build(self, f: StudentFilters, page: int, per_page: int) -> dict:
        rows, membership, _ = await self._load(f)

        # Batch-status filter needs membership, so it applies after the join.
        if f.batch_status == "in_batch":
            rows = [r for r in rows if str(r[0].student_id) in membership]
        elif f.batch_status == "not_in_batch":
            rows = [r for r in rows if str(r[0].student_id) not in membership]

        if f.search and f.search.strip():
            needle = f.search.strip().lower()

            def matches(enrollment, user) -> bool:
                entry = membership.get(str(enrollment.student_id))
                fields = [
                    user.full_name or "", user.roll_number or "",
                    user.email or "", user.phone or "",
                    entry[0].batch_code if entry else "",
                ]
                return any(needle in value.lower() for value in fields)

            rows = [r for r in rows if matches(r[0], r[1])]

        rows.sort(key=lambda r: (r[1].roll_number or ""))

        total = len(rows)
        in_batch = sum(1 for e, _ in rows if str(e.student_id) in membership)
        pending = sum(1 for e, _ in rows if e.profile_status == StudentProfileStatus.VERIFICATION_PENDING)
        complete = sum(1 for e, _ in rows if e.profile_status == StudentProfileStatus.VERIFIED)
        # Counted the same way verification decides, so the queue cannot show a
        # number that the verify button disagrees with.
        missing_contact = sum(1 for _, u in rows if not u.phone and not u.email)
        missing_mobile = sum(1 for _, u in rows if not u.phone)
        not_accepted = sum(1 for e, _ in rows if not e.invitation_accepted)

        # A roll number appearing on more than one student is a data-entry
        # duplicate the registration desk has to resolve.
        roll_counts = Counter((u.roll_number or "").strip().upper() for _, u in rows if u.roll_number)
        duplicates = sum(count for roll, count in roll_counts.items() if roll and count > 1)

        kpis = [
            {"id": "total", "value": str(total), "label": "Total Students"},
            {"id": "profiles", "value": str(complete), "label": "Profiles Complete"},
            {"id": "joined", "value": str(in_batch), "label": "Joined a Batch"},
            {"id": "unbatched", "value": str(total - in_batch), "label": "Not in Batch"},
            {"id": "pending", "value": str(pending), "label": "Verification Pending"},
            {"id": "duplicates", "value": str(duplicates), "label": "Duplicate Records"},
        ]

        attention = [
            {"id": "unbatched", "label": f"{total - in_batch} students not in any batch", "count": total - in_batch},
            {"id": "pending", "label": f"{pending} profiles awaiting verification", "count": pending},
            {"id": "contact", "label": f"{missing_contact} students with no mobile or email", "count": missing_contact},
            {"id": "mobile", "label": f"{missing_mobile} students without a mobile number", "count": missing_mobile},
            {"id": "duplicates", "label": f"{duplicates} possible duplicate roll numbers", "count": duplicates},
            {"id": "invites", "label": f"{not_accepted} invitations not accepted", "count": not_accepted},
        ]

        personal = sum(1 for _, u in rows if u.full_name and u.phone)
        academic = sum(1 for _, u in rows if u.roll_number and u.department and u.course)
        contact = sum(1 for e, _ in rows if e.contact_verified)
        declaration = sum(1 for e, _ in rows if e.declaration_signed)

        completion = [
            {"label": "Personal Details", "done": personal, "total": total},
            {"label": "Academic Details", "done": academic, "total": total},
            {"label": "Contact Verification", "done": contact, "total": total},
            {"label": "Batch Membership", "done": in_batch, "total": total},
            {"label": "Student Declaration", "done": declaration, "total": total},
        ]

        pages = max(1, ceil(total / per_page)) if total else 1
        current = min(max(page, 1), pages)
        start = (current - 1) * per_page
        window = rows[start:start + per_page]

        return {
            "kpis": kpis,
            "attention_items": attention,
            "completion": completion,
            "rows": [self._row(e, u, membership) for e, u in window],
            "page": current,
            "pages": pages,
            "per_page": per_page,
            "total": total,
            "showing_from": (start + 1) if total else 0,
            "showing_to": min(start + per_page, total),
            "profile_statuses": [
                {"key": s.value, "label": PROFILE_LABELS[s]} for s in StudentProfileStatus
            ],
        }

    # ------------------------------------------------------------- mutations

    async def verify(self, enrollment_ids: Sequence[str]) -> dict:
        stmt = (
            select(StudentEnrollment, User)
            .join(User, StudentEnrollment.student_id == User.id)
            .where(StudentEnrollment.id.in_(list(enrollment_ids)))
        )
        rows = (await self.db.execute(stmt)).all()

        verified, skipped = [], []
        for enrollment, user in rows:
            # Verifying a student nobody can reach would make the contact queue
            # meaningless, so one working channel is required - but only one.
            # Demanding both refused every student who signed up through the
            # college form, where the mobile number is optional and the email
            # has already been proven by one-time code. A profile that cannot
            # be verified is stuck for good: nothing downstream opens.
            if not user.phone and not user.email:
                skipped.append({"roll_number": user.roll_number,
                                "reason": "no mobile or email on record"})
                continue
            enrollment.profile_status = StudentProfileStatus.VERIFIED
            enrollment.contact_verified = True
            verified.append(user.roll_number)

        await self.db.commit()
        return {"verified": verified, "skipped": skipped}

    async def assign_to_batch(self, enrollment_ids: Sequence[str], batch_id: str) -> dict:
        batch = (
            await self.db.execute(
                select(ProjectBatch)
                .options(selectinload(ProjectBatch.members))
                .where(ProjectBatch.id == batch_id)
            )
        ).scalar_one_or_none()
        if batch is None:
            raise ValueError("Batch not found")

        enrollments = list(
            (await self.db.execute(
                select(StudentEnrollment).where(StudentEnrollment.id.in_(list(enrollment_ids)))
            )).scalars().all()
        )

        existing = {str(m.student_id) for m in batch.members}
        # Capacity is the batch's own team_size. Only the student-facing join
        # was enforcing it, so assigning from the faculty side could quietly
        # put six people in a batch of four - and every screen that says
        # "5 of 4 seats taken" is reading a batch somebody overfilled here.
        seats = batch.team_size or 0
        active = sum(1 for m in batch.members if m.is_active)
        added, skipped = [], []
        for enrollment in enrollments:
            student_id = str(enrollment.student_id)
            if student_id in existing:
                skipped.append({"student_id": student_id, "reason": "already in this batch"})
                continue
            if seats and active >= seats:
                skipped.append({
                    "student_id": student_id,
                    "reason": f"batch is full ({seats} seats)",
                })
                continue
            active += 1
            self.db.add(ProjectBatchMember(
                batch_id=batch.id,
                student_id=enrollment.student_id,
                is_lead=False,
                is_active=True,
            ))
            # Section follows the batch so the student stops showing as unassigned.
            if enrollment.section is None:
                enrollment.section = batch.section
            enrollment.invitation_accepted = True
            existing.add(student_id)
            added.append(student_id)

        await self.db.commit()
        return {"added": len(added), "skipped": skipped, "batch_code": batch.batch_code}
