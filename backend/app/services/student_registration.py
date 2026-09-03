"""
Student Team Registration - the student's own view of joining a batch.

The faculty portal reads this same data from the other side. Nothing here
duplicates it: the batch, its members and their payments are the rows faculty
already act on, so a seat confirmed here is confirmed there in the same breath.

Money is deliberately read-only. This service reports what a payment record
says and can render a receipt for one, but it never marks a share paid - that
belongs to the payment gateway, which is not wired up for registration fees.
"""

import io
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.faculty import (
    MemberInviteStatus,
    PaymentStatus,
    ProjectBatch,
    ProjectBatchMember,
    RegistrationPayment,
    StudentEnrollment,
    StudentProfileStatus,
)
from app.core.logging_config import logger
from app.models.college import College
from app.models.user import User
from app.services.tenancy import scope

# The five steps of the student registration journey, in order.
STEPS = [
    ("identity", "Identity Verified"),
    ("join", "Join Batch"),
    ("team", "Team Confirmation"),
    ("payment", "Individual Payment"),
    ("setup", "Project Setup"),
]


PAYMENT_BLOCKED_REASON = "The registration fee gateway is not connected yet."


def _display_name(user: Optional[User]) -> Optional[str]:
    if user is None:
        return None
    return user.full_name or user.email.split("@")[0]


class BatchCodeError(Exception):
    """A join code that cannot be used, with a reason the student can act on."""


class StudentRegistrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------- loading

    async def enrollment(self, user: User) -> Optional[StudentEnrollment]:
        return (await self.db.execute(
            select(StudentEnrollment)
            .where(StudentEnrollment.student_id == user.id)
            .where(StudentEnrollment.is_active.is_(True))
            .order_by(StudentEnrollment.academic_year.desc())
        )).scalars().first()

    async def membership(self, user: User) -> Optional[ProjectBatchMember]:
        return (await self.db.execute(
            select(ProjectBatchMember)
            .where(ProjectBatchMember.student_id == user.id)
            .where(ProjectBatchMember.is_active.is_(True))
            .options(
                selectinload(ProjectBatchMember.batch).selectinload(ProjectBatch.guide),
                selectinload(ProjectBatchMember.batch)
                .selectinload(ProjectBatch.members)
                .selectinload(ProjectBatchMember.student),
            )
        )).scalars().first()

    async def project_batch(self, user: User) -> ProjectBatch:
        """
        The batch whose project details this student may edit.

        Editing is the team's act, so any confirmed member may write - but only
        a member. The seat has to be taken, not merely allocated: a student who
        was put on a roster and never accepted has made no commitment to the
        project they would be describing.
        """
        membership = (await self.db.execute(
            select(ProjectBatchMember)
            .where(ProjectBatchMember.student_id == user.id)
            .where(ProjectBatchMember.is_active.is_(True))
        )).scalars().first()
        if membership is None:
            raise BatchCodeError("Join a batch before setting up its project.")
        if membership.invite_status != MemberInviteStatus.JOINED:
            raise BatchCodeError("Accept your seat in the batch first.")

        batch = (await self.db.execute(
            select(ProjectBatch)
            .where(ProjectBatch.id == membership.batch_id)
            .options(
                selectinload(ProjectBatch.objectives),
                selectinload(ProjectBatch.methodology),
                selectinload(ProjectBatch.scope_items),
                selectinload(ProjectBatch.technologies),
            )
        )).scalar_one_or_none()
        if batch is None:
            raise BatchCodeError("That batch no longer exists.")
        batch._is_lead = bool(membership.is_lead)
        return batch

    async def _payments(self, batch_id) -> dict:
        rows = (await self.db.execute(
            select(RegistrationPayment).where(RegistrationPayment.batch_id == batch_id)
        )).scalars().all()
        return {str(r.student_id): r for r in rows}

    async def _find_batch(self, code: str, user: User) -> Optional[ProjectBatch]:
        """
        Resolve a join code, within the caller's college only.

        Join codes are unique across the whole table rather than per college,
        so without the tenant predicate a code that leaked - read off a
        WhatsApp group, a screenshot, a shared sheet - would seat a student in
        another institution's batch. The department/section/year checks in
        `verify_batch` catch most of those by accident, but not a college that
        happens to run CSE-A in the same year.

        A foreign code returns None and so reports "no batch found", which is
        also the right answer to give: whether some other college uses that
        code is not this student's business.
        """
        cleaned = (code or "").strip().upper()
        if not cleaned:
            return None
        return (await self.db.execute(
            scope(select(ProjectBatch), ProjectBatch, user)
            # Either identifier. Everyone says "join CSE-A-001" because that is
            # the code on the notice board, but only BB-CSE-4A-001 used to
            # resolve - same batch, two names, and the obvious one failed.
            # The join code is derived from the batch code by a fixed rule, so
            # it was never the more secret of the two and accepting both gives
            # nothing away. Tenancy still scopes the query, so a code from
            # another college finds nothing.
            .where((ProjectBatch.join_code == cleaned)
                   | (func.upper(ProjectBatch.batch_code) == cleaned))
            .where(ProjectBatch.is_active.is_(True))
            .options(
                selectinload(ProjectBatch.guide),
                selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
            )
        )).scalar_one_or_none()

    # ------------------------------------------------------------- summary

    def _batch_summary(self, batch: ProjectBatch) -> dict:
        joined = sum(
            1 for m in batch.members
            if m.is_active and m.invite_status == MemberInviteStatus.JOINED
        )
        return {
            "id": str(batch.id),
            "batch_code": batch.batch_code,
            "join_code": batch.join_code,
            # "Batch 014" in the header - the trailing number of the join code
            # reads better than the full code once it is already on screen.
            "display_name": f"Batch {(batch.join_code or batch.batch_code).rsplit('-', 1)[-1]}",
            "department": batch.department,
            "year": batch.year,
            "section": batch.section,
            "project_type": batch.project_type,
            "guide": _display_name(batch.guide),
            "team_size": batch.team_size,
            "joined": joined,
            "title": batch.title,
            "project_fee": batch.project_fee,
            "share": batch.project_fee // max(1, batch.team_size),
        }

    def _team(self, batch: ProjectBatch, payments: dict, me: User) -> List[dict]:
        members = sorted(
            [m for m in batch.members if m.is_active],
            key=lambda m: (not m.is_lead, str(m.student_id)),
        )
        rows = []
        for i, m in enumerate(members, start=1):
            payment = payments.get(str(m.student_id))
            invited = m.invite_status != MemberInviteStatus.JOINED
            rows.append({
                "position": i,
                "member_id": str(m.id),
                "student_id": str(m.student_id),
                "name": _display_name(m.student),
                "roll_number": m.student.roll_number if m.student else None,
                "is_you": str(m.student_id) == str(me.id),
                "is_lead": bool(m.is_lead),
                "invite_status": m.invite_status.value,
                "chip": "You" if str(m.student_id) == str(me.id)
                        else "Joined" if not invited else "Invitation Pending",
                # An un-accepted seat has no identity, seat or payment state to
                # report yet; the screen shows a dash rather than a false "no".
                "identity_verified": None if invited else True,
                "seat_confirmed": None if invited else bool(m.seat_confirmed),
                "payment_status": None if invited
                                  else (payment.status.value if payment else "pending"),
                "can_remind": invited,
                "reminded_at": m.invite_reminded_at,
            })
        return rows

    # --------------------------------------------------------------- state

    async def state(self, user: User) -> dict:
        enrollment = await self.enrollment(user)
        membership = await self.membership(user)
        batch = membership.batch if membership else None

        payments = await self._payments(batch.id) if batch else {}
        my_payment = payments.get(str(user.id))
        team = self._team(batch, payments, user) if batch else []
        summary = self._batch_summary(batch) if batch else None

        identity_ok = bool(
            enrollment and enrollment.profile_status == StudentProfileStatus.VERIFIED
        )
        joined_ok = bool(membership and membership.invite_status == MemberInviteStatus.JOINED)
        team_ok = bool(
            batch and summary and summary["joined"] >= summary["team_size"]
            and all(r["seat_confirmed"] for r in team)
        )
        paid_ok = bool(my_payment and my_payment.status == PaymentStatus.PAID)
        everyone_paid = bool(
            batch and team
            and all(r["payment_status"] == "paid" for r in team)
        )
        # Writing the proposal is gated on the team being complete, not on the
        # fee. Money and planning are separate concerns, and while no gateway is
        # connected a payment gate would make every step after it unreachable -
        # a locked screen nobody could ever open.
        setup_ok = bool(team_ok and batch and batch.title)

        done = {"identity": identity_ok, "join": joined_ok, "team": team_ok,
                "payment": paid_ok, "setup": setup_ok}
        blocked = {"payment": PAYMENT_BLOCKED_REASON} if not paid_ok else {}
        current = next((k for k, _ in STEPS if not done[k] and k not in blocked), None)
        steps = [
            {
                "key": key,
                "label": label,
                "position": i,
                "state": "done" if done[key] else "current" if key == current else "pending",
                "blocked_reason": blocked.get(key),
            }
            for i, (key, label) in enumerate(STEPS, start=1)
        ]

        confirmed = sum(1 for r in team if r["seat_confirmed"])
        total = summary["team_size"] if summary else 0
        waiting = max(0, total - confirmed)

        return {
            "student": {
                "name": _display_name(user),
                "roll_number": user.roll_number,
                "email": user.email,
                "department": enrollment.department if enrollment else user.department,
                "section": enrollment.section if enrollment else user.section,
                "year": enrollment.year if enrollment else user.year_semester,
                "college": await self._college_label(user),
                "academic_year": enrollment.academic_year if enrollment else None,
            },
            "enrolled": enrollment is not None,
            "steps": steps,
            "current_step": current,
            "batch": summary,
            "team": team,
            "team_joined": confirmed,
            "team_size": total,
            "your_registration": {
                "confirmed": confirmed,
                "total": total,
                "percent": int(round(confirmed / total * 100)) if total else 0,
                "project_fee": summary["project_fee"] if summary else None,
                "team_members": total,
                "your_share": summary["share"] if summary else None,
                "payment": {
                    "status": my_payment.status.value if my_payment else None,
                    "amount": my_payment.amount if my_payment else (summary["share"] if summary else None),
                    "receipt_number": my_payment.receipt_number if my_payment else None,
                    "paid_at": my_payment.paid_at if my_payment else None,
                    "method": my_payment.method if my_payment else None,
                },
                "checklist": [
                    {"key": "identity", "label": "Identity verified", "done": identity_ok},
                    {"key": "join", "label": "Batch joined", "done": joined_ok},
                    {"key": "seat", "label": "Seat confirmed",
                     "done": bool(membership and membership.seat_confirmed)},
                    {"key": "payment", "label": "Payment completed", "done": paid_ok},
                ],
                "waiting_for": waiting,
                # Reported, not enforced: the team can see where the fees stand
                # without it blocking anyone from writing the proposal.
                "team_all_paid": everyone_paid,
                "next_action": self._next_action(done, waiting, paid_ok),
            },
            # One thing to paste. It carries the link for anyone who can click
            # it and the code for anyone reading it aloud, because a lead
            # shares this over WhatsApp as often as by email.
            "invite": {
                "code": summary["join_code"] or summary["batch_code"],
                "path": f"/student/registration?code="
                        f"{summary['join_code'] or summary['batch_code']}",
                "message": (
                    f"Join our BharatBuild project batch "
                    f"{summary['display_name']} - code "
                    f"{summary['join_code'] or summary['batch_code']}"
                ),
            } if summary else None,
            "eligibility_note": (
                f"Only verified students from {summary['department']}, {summary['year']}, "
                f"Section {summary['section']} can join this batch."
            ) if summary else None,
        }

    @staticmethod
    def _next_action(done: dict, waiting: int, paid_ok: bool) -> dict:
        """
        What the primary button says, and whether it can be pressed.

        The fee is reported but never blocks: it is the last thing offered, so
        an unconnected gateway leaves one button disabled rather than making
        the rest of the journey unreachable.
        """
        if not done["join"]:
            return {"label": "Join Your Batch", "enabled": False,
                    "reason": "Verify a batch code above to take your seat.",
                    "href": None}
        if waiting > 0:
            return {"label": f"Waiting for {waiting} Student{'s' if waiting != 1 else ''}",
                    "enabled": False,
                    "reason": "Project Setup unlocks once every seat is confirmed.",
                    "href": None}
        if not done["setup"]:
            return {"label": "Start Project Setup", "enabled": True, "reason": None,
                    "href": "/student/workspace"}
        if not paid_ok:
            return {"label": "Pay My Share", "enabled": False,
                    "reason": "The registration fee gateway is not connected yet.",
                    "href": None}
        return {"label": "Open Project Workspace", "enabled": True, "reason": None,
                "href": "/student/workspace"}

    # ------------------------------------------------------------- actions

    async def verify_batch(self, user: User, code: str) -> dict:
        """
        Resolve a join code and say whether this student may use it.

        The eligibility rules are enforced here rather than only on join, so a
        student finds out before committing rather than after.
        """
        batch = await self._find_batch(code, user)
        if batch is None:
            raise BatchCodeError("No batch found with that code. Check it with your coordinator.")

        enrollment = await self.enrollment(user)
        if enrollment is None:
            raise BatchCodeError("You are not enrolled for this academic year yet.")

        if enrollment.department != batch.department:
            raise BatchCodeError(
                f"This batch is for {batch.department}; you are enrolled in {enrollment.department}."
            )
        if batch.section and enrollment.section and enrollment.section != batch.section:
            raise BatchCodeError(
                f"This batch is for Section {batch.section}; you are in Section {enrollment.section}."
            )
        if batch.year and enrollment.year and enrollment.year != batch.year:
            raise BatchCodeError(
                f"This batch is for {batch.year}; you are in {enrollment.year}."
            )

        return {"batch": self._batch_summary(batch), "verified": True}

    async def _college_label(self, user: User) -> Optional[str]:
        """
        The institution to show this student.

        Two fields carry a college: `college_name` is free text typed at
        signup, and `college_id` is the institution the account actually
        belongs to. They disagree whenever somebody typed a name the system
        did not recognise - and the portal was showing the typed one, so a
        student enrolled at Sri Guru saw whatever they had once written.
        The link wins; the typed text is only a fallback for an account that
        has not been placed anywhere yet.
        """
        if user.college_id:
            college = (await self.db.execute(
                select(College).where(College.id == user.college_id)
            )).scalars().first()
            if college and not college.is_self_serve:
                return college.name
        return user.college_name

    async def _ensure_enrollment(self, user: User, batch: ProjectBatch) -> None:
        """
        Make sure a student in a batch is enrolled for its year.

        Enrolment is normally the college's act - a coordinator imports the
        roster - and everything on the registration screen is gated on it. A
        student who signed up and joined with a batch code had no enrolment at
        all, so the screen told them their college had not enrolled them while
        they were sitting in one of its batches.

        Only what the batch already states is written; nothing is invented.
        The profile stays unverified, because joining a batch is not the
        registration desk confirming who somebody is.
        """
        if not batch.college_id:
            return
        existing = (await self.db.execute(
            select(StudentEnrollment)
            .where(StudentEnrollment.student_id == user.id)
            .where(StudentEnrollment.academic_year == batch.academic_year)
        )).scalars().first()
        if existing is not None:
            if existing.is_active is False:
                existing.is_active = True
            return

        self.db.add(StudentEnrollment(
            college_id=batch.college_id,
            student_id=user.id,
            department=batch.department,
            section=batch.section,
            year=batch.year or "4th Year",
            semester=batch.semester,
            academic_year=batch.academic_year,
            is_registered=True,
            is_active=True,
        ))
        logger.info(f"[Registration] enrolled {user.email} in {batch.department} "
                    f"{batch.section or '-'} for {batch.academic_year} "
                    f"via {batch.batch_code}")

    async def join_batch(self, user: User, code: str) -> dict:
        verified = await self.verify_batch(user, code)
        batch = await self._find_batch(code, user)

        existing = await self.membership(user)
        if existing and str(existing.batch_id) != str(batch.id):
            raise BatchCodeError(
                f"You already belong to {existing.batch.batch_code}. "
                "Leaving a batch needs your coordinator."
            )

        member = next(
            (m for m in batch.members if str(m.student_id) == str(user.id) and m.is_active), None
        )
        if member is None:
            active = [m for m in batch.members if m.is_active]
            if len(active) >= batch.team_size:
                raise BatchCodeError(f"This batch is full ({batch.team_size} students).")
            # The first student to take a seat leads the batch. Someone has to:
            # submitting the registration is a leader's act, and a batch formed
            # through the app has nobody to appoint one otherwise. A coordinator
            # can hand the role to someone else from the Team tab.
            member = ProjectBatchMember(
                batch_id=batch.id,
                student_id=user.id,
                invited_at=datetime.utcnow(),
                is_lead=not any(m.is_lead and m.is_active for m in batch.members),
            )
            self.db.add(member)

        member.invite_status = MemberInviteStatus.JOINED
        member.seat_confirmed = True
        member.joined_at = member.joined_at or datetime.utcnow()
        member.is_active = True

        # Joining is the moment a student acquires an institution. Nothing had
        # been setting this: accounts created by signing up carried no college
        # at all, so every query scoped by tenancy skipped them, while the rows
        # written *for* them took the college from the batch and looked fine.
        # The batch is the authority here - it is what they just joined.
        if not user.college_id and batch.college_id:
            user.college_id = batch.college_id
            logger.info(f"[Registration] {user.email} placed in college "
                        f"{batch.college_id} by joining {batch.batch_code}")

        await self._ensure_enrollment(user, batch)

        # A seat carries a share; create the record so the amount owed is
        # visible immediately rather than appearing only after payment.
        payments = await self._payments(batch.id)
        if str(user.id) not in payments:
            self.db.add(RegistrationPayment(
                batch_id=batch.id,
                student_id=user.id,
                amount=batch.project_fee // max(1, batch.team_size),
                status=PaymentStatus.PENDING,
            ))

        await self.db.commit()
        return verified


    # -------------------------------------------------------------- payment

    async def _my_payment(self, user: User):
        membership = await self.membership(user)
        if membership is None:
            raise BatchCodeError("You are not in a batch yet.")
        batch = membership.batch
        payments = await self._payments(batch.id)
        payment = payments.get(str(user.id))
        if payment is None:
            # A seat carries a share; if the row is missing the student cannot
            # pay at all, so create it rather than refusing.
            payment = RegistrationPayment(
                batch_id=batch.id,
                student_id=user.id,
                amount=batch.project_fee // max(1, batch.team_size),
                status=PaymentStatus.PENDING,
            )
            self.db.add(payment)
            await self.db.flush()
        return batch, payment

    async def start_payment(self, user: User) -> dict:
        """
        Open an order with the gateway for this student's share.

        Only the order is created here. The card or UPI details are entered on
        the gateway's own checkout and never reach this application - which is
        the point of doing it this way rather than taking them in our form.
        """
        from app.core.config import settings

        batch, payment = await self._my_payment(user)
        if payment.status == PaymentStatus.PAID:
            raise BatchCodeError("Your share is already paid.")

        try:
            import razorpay
        except ImportError:
            raise BatchCodeError("Online payment is not available on this server.")
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            # One gateway account for the whole platform, not one per college:
            # the fee is collected by BharatBuild, so a college has nothing to
            # configure and should not be told it does.
            raise BatchCodeError(
                "Online payment is temporarily unavailable. Pay through your "
                "department and ask them to record it.")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID,
                                       settings.RAZORPAY_KEY_SECRET))
        try:
            order = client.order.create(data={
                # Paise, which is what the gateway counts in.
                "amount": int(payment.amount) * 100,
                "currency": "INR",
                "receipt": f"{batch.batch_code}-{str(user.id)[:8]}",
                # Carried into the gateway dashboard, so a payment landing in
                # the platform's account can be traced back to the college,
                # batch and student it was collected for.
                "notes": {
                    "college_id": str(batch.college_id) if batch.college_id else "",
                    "batch_code": batch.batch_code,
                    "student": user.email or "",
                    "roll_number": user.roll_number or "",
                    "purpose": "Project registration fee",
                },
            })
        except Exception as exc:
            logger.error(f"[Payment] order failed for {user.email}: {exc}")
            # A rejected key is a configuration problem, not a bad moment, and
            # telling a student to "try again" sends them round a loop that
            # cannot succeed.
            if "authentication" in str(exc).lower():
                raise BatchCodeError(
                    "Online payment is temporarily unavailable. Pay through your "
                    "department and ask them to record it.")
            raise BatchCodeError("The payment gateway did not open an order. Try again.")

        payment.reference = order["id"]
        await self.db.commit()
        logger.info(f"[Payment] {user.email} opened order {order['id']} "
                    f"for {batch.batch_code}")
        return {
            "order_id": order["id"],
            "amount": payment.amount,
            "amount_paise": int(payment.amount) * 100,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "batch_code": batch.batch_code,
            "student_name": user.full_name,
            "student_email": user.email,
            "description": f"Project registration fee - {batch.batch_code}",
        }

    async def confirm_payment(self, user: User, *, order_id: str,
                              payment_id: str, signature: str) -> dict:
        """
        Record a share as paid, once the gateway's signature checks out.

        The signature is what makes this safe to expose: a browser can post
        anything, so nothing is marked paid on the browser's word. Compared
        with `compare_digest`, so a wrong signature takes the same time as a
        right one.
        """
        import hashlib
        import hmac

        from app.core.config import settings

        batch, payment = await self._my_payment(user)
        if payment.status == PaymentStatus.PAID:
            return {"status": "paid", "message": "Your share was already recorded."}

        if not settings.RAZORPAY_KEY_SECRET:
            raise BatchCodeError("Online payment is not switched on.")
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature or ""):
            logger.warning(f"[Payment] bad signature from {user.email} on {order_id}")
            raise BatchCodeError("That payment could not be verified.")

        # The order this student actually opened, not one they were handed.
        if payment.reference and payment.reference != order_id:
            logger.warning(f"[Payment] {user.email} confirmed {order_id} against "
                           f"stored {payment.reference}")
            raise BatchCodeError("That payment belongs to a different order.")

        self._settle(payment, batch, payment_id=payment_id, method="Razorpay")
        await self.db.commit()
        logger.info(f"[Payment] {user.email} paid {payment.amount} for {batch.batch_code}")
        return {
            "status": "paid",
            "amount": payment.amount,
            "receipt_number": payment.receipt_number,
            "paid_at": payment.paid_at,
            "message": f"Paid. Receipt {payment.receipt_number}.",
        }


    @staticmethod
    def _txn_id(payment) -> str:
        """A short readable reference for one payment row: TXN<yymmdd><4 hex>."""
        when = payment.paid_at or payment.created_at or datetime.utcnow()
        return f"TXN{when:%y%m%d}{str(payment.id).replace('-', '')[:4].upper()}"

    @staticmethod
    def _settle(payment, batch, *, payment_id: str, method: str) -> None:
        """
        Mark a share paid. Shared by the browser callback and the webhook so the
        two cannot drift into recording the same payment differently.
        """
        payment.status = PaymentStatus.PAID
        payment.method = method
        payment.gateway_payment_id = payment_id
        # Clear any anomaly noted against an earlier attempt on this share -
        # once it is paid, "needs checking" is no longer true and would sit
        # there frightening the student.
        if payment.recorded_by_id is None:
            payment.note = None
        payment.paid_at = datetime.utcnow()
        payment.receipt_number = f"BB-{batch.batch_code}-{payment_id[-8:].upper()}"

    async def settle_from_webhook(self, event: str, entity: dict) -> str:
        """
        Settle a registration share from a gateway webhook.

        The browser callback is not a reliable place to record money: a student
        who closes the tab after paying never fires it, and their share stays
        outstanding while the money is gone. The webhook is the gateway
        telling the server directly, so it is what actually settles the row -
        the callback just makes the screen update while they watch.

        The caller has already checked the signature. Returns a short word for
        the log; unknown orders are ignored, because this endpoint also carries
        token purchases that have nothing to do with a registration fee.
        """
        order_id = entity.get("order_id") or entity.get("id")
        payment_id = entity.get("id") or ""
        if not order_id:
            return "no-order"

        payment = (await self.db.execute(
            select(RegistrationPayment)
            .options(selectinload(RegistrationPayment.batch))
            .where(RegistrationPayment.reference == order_id)
        )).scalars().first()
        if payment is None:
            return "not-a-registration"

        if payment.status == PaymentStatus.PAID:
            return "already-paid"

        if event == "payment.failed":
            payment.status = PaymentStatus.FAILED
            payment.note = (entity.get("error_description") or "")[:200] or None
            await self.db.commit()
            logger.info(f"[Payment] webhook: {order_id} failed")
            return "failed"

        # The amount the gateway actually took, in paise. A share is only
        # settled by the amount it is owed - anything else is an anomaly a
        # human has to look at, and quietly marking it paid would hide that.
        received = int(entity.get("amount") or 0)
        if received != int(payment.amount) * 100:
            payment.note = (f"Gateway took {received / 100:.0f} against a share of "
                            f"{payment.amount}. Needs checking.")[:200]
            await self.db.commit()
            logger.error(f"[Payment] webhook: {order_id} amount mismatch - "
                         f"{received} paise for a share of {payment.amount}")
            return "amount-mismatch"

        method = (entity.get("method") or "razorpay").title()
        self._settle(payment, payment.batch, payment_id=payment_id, method=method)
        await self.db.commit()
        logger.info(f"[Payment] webhook settled {payment.amount} for "
                    f"{payment.batch.batch_code} ({order_id})")
        return "paid"

    async def receipt_pdf(self, user: User) -> Optional[bytes]:
        """
        The payment receipt as an invoice PDF.

        A student forwards this to a parent or hands it to an office, so it has
        to read as a document rather than a text dump - and a PDF renders the
        same wherever it is opened.
        """
        membership = await self.membership(user)
        if membership is None:
            return None
        payments = await self._payments(membership.batch_id)
        payment = payments.get(str(user.id))
        if payment is None or payment.status != PaymentStatus.PAID:
            return None

        recorder = None
        if payment.recorded_by_id:
            recorder = (await self.db.execute(
                select(User).where(User.id == payment.recorded_by_id)
            )).scalars().first()

        return _draw_invoice(
            user=user,
            batch=membership.batch,
            payment=payment,
            college=await self._college_label(user),
            txn_id=self._txn_id(payment),
            recorded_by=recorder.full_name if recorder else ISSUER["name"],
        )

    async def payments_overview(self, user: User) -> dict:
        """
        The whole payments screen: this student, their team, and the trail.

        Built from the payment rows themselves rather than from a separate
        ledger - there is one share per student, and a transaction is simply a
        share that has been settled. Inventing a second table would let the two
        disagree about who has paid.
        """
        membership = await self.membership(user)
        if membership is None:
            raise BatchCodeError("You are not in a batch yet.")
        batch = membership.batch
        payments = await self._payments(batch.id)

        members = [m for m in batch.members if m.is_active and m.student]
        share = batch.project_fee // max(1, batch.team_size)

        rows, transactions = [], []
        paid_total = 0
        for index, member in enumerate(sorted(
                members, key=lambda m: (m.student.roll_number or "", m.student.full_name or "")), 1):
            student = member.student
            payment = payments.get(str(student.id))
            settled = payment is not None and payment.status == PaymentStatus.PAID
            amount = payment.amount if payment else share
            if settled:
                paid_total += amount

            recorder = None
            if payment is not None and payment.recorded_by_id:
                recorder = (await self.db.execute(
                    select(User).where(User.id == payment.recorded_by_id)
                )).scalars().first()

            rows.append({
                "position": index,
                "student_id": str(student.id),
                "name": student.full_name,
                "roll_number": student.roll_number,
                "is_me": str(student.id) == str(user.id),
                "is_lead": bool(member.is_lead),
                "share": amount,
                "paid": amount if settled else 0,
                "status": payment.status.value if payment else "pending",
                "paid_at": payment.paid_at if payment else None,
                "method": payment.method if payment else None,
                "receipt_number": payment.receipt_number if payment else None,
                # Online payments record themselves; a name here means somebody
                # entered it by hand.
                "recorded_by": (recorder.full_name if recorder
                                else ("Online" if settled else None)),
            })

            # Every share is a transaction, not just the settled ones. A student
            # looking for "where did my payment go" needs to see the attempt
            # that failed and the share still outstanding - a list of successes
            # only is the one list that cannot answer that question.
            if payment is not None:
                when = payment.paid_at or payment.created_at
                transactions.append({
                    "id": self._txn_id(payment),
                    "at": when,
                    "type": "Registration fee share",
                    "by": student.full_name,
                    "by_roll": student.roll_number,
                    "is_mine": str(student.id) == str(user.id),
                    "description": ("Refund for duplicate payment"
                                    if payment.status == PaymentStatus.REFUNDED
                                    else "Registration fee share"),
                    # Signed from the student's side: a fee leaves them, a
                    # refund comes back. The screen colours on this sign, so
                    # getting it wrong would paint a refund like a charge.
                    "amount": (amount if payment.status == PaymentStatus.REFUNDED
                               else -amount),
                    "status": payment.status.value,
                    "mode": payment.method or "-",
                    "receipt_number": payment.receipt_number,
                    "recorded_by": (recorder.full_name if recorder
                                    else ("Online" if settled else None)),
                    "note": payment.note,
                })

        transactions.sort(key=lambda t: t["at"] or datetime.min, reverse=True)
        mine = next((r for r in rows if r["is_me"]), None)
        total_fee = share * len(members)
        pending_total = total_fee - paid_total
        last = max((r["paid_at"] for r in rows if r["paid_at"]), default=None)

        schedule = self._schedule(batch, mine, share)
        return {
            "batch_code": batch.batch_code,
            "project_fee": batch.project_fee,
            "team_size": batch.team_size,
            "members": len(members),
            "your_share": mine["share"] if mine else share,
            "you_paid": mine["paid"] if mine else 0,
            "your_status": mine["status"] if mine else "pending",
            "your_receipt": mine["receipt_number"] if mine else None,
            "paid_at": mine["paid_at"] if mine else None,
            "team": rows,
            "totals": {
                # Over the members actually seated, not the nominal team size -
                # a batch of four in five seats owes four shares.
                "fee": total_fee,
                "paid": paid_total,
                "pending": pending_total,
                "completion": round(paid_total / total_fee * 100) if total_fee else 0,
                "paid_count": sum(1 for r in rows if r["status"] == "paid"),
            },
            "transactions": transactions,
            "last_updated": last,
            "schedule": schedule,
            "schedule_totals": {
                "count": len(schedule),
                "amount": sum(i["amount"] for i in schedule),
                "paid": sum(i["amount"] for i in schedule if i["status"] == "paid"),
                "pending": sum(i["amount"] for i in schedule if i["status"] != "paid"),
                "overdue": sum(i["amount"] for i in schedule if i["status"] == "overdue"),
            },
        }

    @staticmethod
    def _schedule(batch, mine: dict | None, share: int) -> list[dict]:
        """
        This student's instalments.

        One today, because the registration fee is collected as a single sum -
        so this returns a schedule of one rather than inventing a milestone
        plan the college never set. When a college defines real instalments,
        they come back as more rows and the screen already renders them.
        """
        today = date.today()
        rows = [{
            "number": 1,
            "label": "Instalment 1",
            "description": "Registration fee",
            "due": batch.start_date,
            "amount": mine["share"] if mine else share,
            "paid_at": mine["paid_at"] if mine else None,
            "mode": mine["method"] if mine else None,
            "receipt_number": mine["receipt_number"] if mine else None,
            "settled": bool(mine and mine["status"] == "paid"),
        }]

        for row in rows:
            due = row.pop("due")
            settled = row.pop("settled")
            # Overdue is a fact about the date, not a stored status - nothing
            # writes "overdue" anywhere, so it has to be worked out on read or
            # it silently goes stale the day after the due date.
            row["due"] = due
            row["status"] = ("paid" if settled
                             else "overdue" if due and due < today
                             else "upcoming")
            # Only the earliest unpaid instalment is payable; offering to pay a
            # later one first would leave the earlier one outstanding.
            row["payable"] = False

        nxt = next((r for r in rows if r["status"] != "paid"), None)
        if nxt is not None:
            nxt["payable"] = True
        return rows

    async def resend_invite(self, user: User, member_id: str) -> dict:
        membership = await self.membership(user)
        if membership is None:
            raise BatchCodeError("You are not in a batch yet.")

        target = next(
            (m for m in membership.batch.members if str(m.id) == member_id), None
        )
        if target is None:
            raise BatchCodeError("That member is not in your batch.")
        if target.invite_status == MemberInviteStatus.JOINED:
            raise BatchCodeError("That student has already joined.")

        target.invite_reminded_at = datetime.utcnow()
        await self.db.commit()
        return {
            "member_id": member_id,
            "reminded_at": target.invite_reminded_at,
            # Said plainly: the record is updated, but nothing was sent.
            "delivered": False,
            "detail": "Reminder recorded. Email delivery is not connected yet, "
                      "so share the batch code directly.",
        }

    async def receipt(self, user: User) -> Optional[str]:
        membership = await self.membership(user)
        if membership is None:
            return None
        payments = await self._payments(membership.batch_id)
        payment = payments.get(str(user.id))
        if payment is None or payment.status != PaymentStatus.PAID:
            return None

        batch = membership.batch
        lines = [
            "BharatBuild AI - Registration Fee Receipt",
            "=" * 44,
            f"Receipt number : {payment.receipt_number or '-'}",
            f"Student        : {_display_name(user)} ({user.roll_number or '-'})",
            f"Batch          : {batch.batch_code}"
            + (f" ({batch.join_code})" if batch.join_code else ""),
            f"Cohort         : {batch.department} / {batch.year} / Section {batch.section}",
            f"Project fee    : Rs {batch.project_fee:,} for {batch.team_size} students",
            f"Amount paid    : Rs {payment.amount:,}",
            f"Method         : {payment.method or '-'}",
            f"Payment ref    : {payment.gateway_payment_id or '-'}",
            f"Order ref      : {payment.reference or '-'}",
            f"Paid on        : {payment.paid_at.strftime('%d %b %Y, %I:%M %p') if payment.paid_at else '-'}",
            "",
            "Each student pays their own share separately from their own account.",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------- the invoice

# Whose name is on the invoice. The platform collects the fee, not the college,
# so this is deliberately the platform's own details.
ISSUER = {
    "name": "BharatBuild AI",
    "tagline": "Build Projects. Build Future.",
    "address": "Hyderabad, Telangana, India",
    "email": "support@bharatbuild.ai",
    "site": "www.bharatbuild.ai",
}

_ONES = ("", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
         "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
         "Sixteen", "Seventeen", "Eighteen", "Nineteen")
_TENS = ("", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
         "Eighty", "Ninety")


def _under_thousand(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()
    return (_ONES[n // 100] + " Hundred"
            + (" " + _under_thousand(n % 100) if n % 100 else ""))


def _in_words(amount: int) -> str:
    """
    An amount in words, grouped the Indian way - lakh and crore, not million.

    An invoice carries the words as well as the figure because that is what
    makes a tampered digit obvious.
    """
    if amount == 0:
        return "Zero Rupees Only"
    parts = []
    for divisor, label in ((10_000_000, "Crore"), (100_000, "Lakh"),
                           (1_000, "Thousand")):
        if amount >= divisor:
            parts.append(f"{_under_thousand(amount // divisor)} {label}")
            amount %= divisor
    if amount:
        parts.append(_under_thousand(amount))
    return " ".join(parts) + " Rupees Only"


def _draw_invoice(*, user, batch, payment, college, txn_id, recorded_by) -> bytes:
    """
    One A4 page, laid out on the template's own coordinates.

    The numbers are absolute points read from the template rather than a
    margin-and-flow reconstruction, because "close enough" on an invoice reads
    as a different document to whoever receives it.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas

    NAVY = colors.HexColor("#0B1F5B")
    INK = colors.HexColor("#101828")
    MUTED = colors.HexColor("#667085")
    GREEN = colors.HexColor("#079455")
    WHITE = colors.white
    TINT_BLUE = colors.HexColor("#EFF4FF")
    TINT_GREEN = colors.HexColor("#F0FDF4")
    TINT_GREY = colors.HexColor("#F8FAFC")
    RULE = colors.HexColor("#E4E7EC")
    RULE_BLUE = colors.HexColor("#1560EF")
    EDGE_BLUE = colors.HexColor("#B2CCFF")
    EDGE_GREEN = colors.HexColor("#ABEFC6")

    L, R = 42.51969, 552.7559          # the framed content
    TL, TR = 48.51969, 546.7559        # text inside it
    MID = 297.6378                     # centre, and the two-column divider

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)

    # A five-digit invoice number in the template's own format, derived from
    # the payment row so it never changes once issued.
    seq = int(str(payment.id).replace("-", "")[:6], 16) % 100000
    issued = payment.paid_at or datetime.utcnow()
    invoice_no = f"BBAI-INV-{issued:%Y}-{seq:05d}"
    c.setTitle(f"Invoice {invoice_no}")
    c.setAuthor(ISSUER["name"])
    c.setSubject("Major project registration payment")

    def line(y, x0, x1, colour, width):
        c.setStrokeColor(colour)
        c.setLineWidth(width)
        c.line(x0, y, x1, y)

    def box(x, y, w, h, fill, edge, width=0.5):
        if fill is not None:
            c.setFillColor(fill)
            c.rect(x, y, w, h, stroke=0, fill=1)
        c.setStrokeColor(edge)
        c.setLineWidth(width)
        c.rect(x, y, w, h, stroke=1, fill=0)

    # ---------------------------------------------------------------- header
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 19)
    c.drawString(TL, 785.5433, ISSUER["name"])
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(TL, 764.5433, ISSUER["tagline"])

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 17)
    c.drawRightString(R, 787.5433, "INVOICE")

    def labelled(y, label, value, value_colour=INK, bold_value=False):
        """A right-aligned `Label: value` pair, laid out from the right edge."""
        c.setFont("Helvetica-Bold" if bold_value else "Helvetica", 8.6)
        vw = c.stringWidth(value, "Helvetica-Bold" if bold_value else "Helvetica", 8.6)
        c.setFillColor(value_colour)
        c.drawRightString(R, y, value)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8.6)
        c.drawRightString(R - vw, y, label)

    labelled(776.3433, "Invoice No:", f" {invoice_no}")
    labelled(765.1433, "Invoice Date:", f" {issued:%d %b %Y}")
    labelled(753.9433, "Status:", " PAID", GREEN, bold_value=True)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.7)
    c.drawString(TL, 744.7913, f"{ISSUER['site']} | {ISSUER['email']}")
    line(735.322, TL, TR, RULE_BLUE, 1)

    # ------------------------------------------------- issued by / billed to
    box(L, 655.8181, R - L, 70, None, RULE, 0.5)
    c.setStrokeColor(RULE)
    c.setLineWidth(0.4)
    c.line(MID, 655.8181, MID, 725.8181)

    def party(x, rows):
        y = 710.2181
        c.setFillColor(INK)
        for i, text in enumerate(rows):
            c.setFont("Helvetica-Bold" if i < 2 else "Helvetica", 8.6)
            c.drawString(x, y, text)
            y -= 11.2

    cohort = " - ".join(p for p in (batch.department,
                                    f"{batch.year}" if batch.year else None)
                        if p) or "-"
    party(50.51969, ["ISSUED BY", ISSUER["name"], ISSUER["address"],
                     ISSUER["email"], ISSUER["site"]])
    party(305.6378, ["BILLED TO", _display_name(user),
                     f"Roll / Register No.: {user.roll_number or '-'}",
                     cohort, college or "-"])

    # -------------------------------------------------------- invoice details
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(TL, 637.3142, "Invoice Details")

    c.setFillColor(NAVY)
    c.rect(L, 608.1142, R - L, 24, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8.2)
    c.drawString(TL, 617.9142, "#")
    c.drawString(76.86615, 617.9142, "Description")
    c.drawString(337.65359, 617.9142, "Reference")
    c.drawRightString(TR, 617.9142, "Amount")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8.2)
    c.drawString(TL, 593.9142, "1")
    c.drawString(76.86615, 593.9142, "Major Project Registration Payment")
    c.drawString(337.65359, 593.9142, txn_id)
    c.drawRightString(TR, 593.9142, f"Rs. {payment.amount:,}")

    c.setStrokeColor(RULE)
    c.setLineWidth(0.45)
    c.rect(L, 584.1142, R - L, 48, stroke=1, fill=0)
    c.line(L, 608.1142, R, 608.1142)
    for x in (70.86615, 331.65359, 459.21259):
        c.line(x, 584.1142, x, 632.1142)

    # ----------------------------------------------------------- amount paid
    box(L, 529.2102, R - L, 46.4, TINT_BLUE, EDGE_BLUE, 0.6)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8.6)
    c.drawRightString(354.3307, 561.0102, "AMOUNT PAID")
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 17)
    c.drawRightString(TR, 552.6102, f"Rs. {payment.amount:,}")
    c.setFillColor(INK)
    c.setFont("Helvetica", 8.6)
    c.drawRightString(354.3307, 537.8102, "Amount in words")
    c.setFont("Helvetica-Bold", 8.6)
    c.drawRightString(TR, 537.8102, _in_words(payment.amount))

    # --------------------------------------------------- payment information
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(TL, 510.7063, "Payment Information")

    # A bank transfer really does carry a UTR; a card or UPI payment through
    # the gateway does not, and calling its id a UTR would be a false label on
    # a financial document.
    bank_like = (payment.method or "").lower() in ("bank transfer", "netbanking",
                                                   "net banking", "neft", "imps")
    rows = [
        ("Payment Status", payment.status.value.upper(), GREEN, True),
        ("Payment Mode", payment.method or "-", colors.black, False),
        ("Transaction ID", txn_id, colors.black, False),
        ("Bank / UTR Reference" if bank_like else "Gateway Reference",
         payment.gateway_payment_id or payment.reference or "-",
         colors.black, False),
        ("Payment Date",
         payment.paid_at.strftime("%d %b %Y, %I:%M %p") if payment.paid_at else "-",
         colors.black, False),
        ("Recorded By", recorded_by, colors.black, False),
        ("Receipt Number", payment.receipt_number or "-", colors.black, False),
    ]

    # The template was drawn with six rows; the block grows by one row height
    # per extra row and everything under it moves down by the same amount, so
    # adding a row never needs the coordinates below to be re-measured.
    ROW, TOP = 22, 505.5063
    depth = len(rows) * ROW
    bottom = TOP - depth
    drop = depth - 6 * ROW

    c.setFillColor(TINT_GREY)
    c.rect(L, bottom, 164.4094, depth, stroke=0, fill=1)

    y = TOP - 13.3
    for label, value, colour, bold in rows:
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 8.3)
        c.drawString(49.51969, y, label)
        c.setFillColor(colour)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 8.3)
        c.drawString(213.9291, y, str(value))
        y -= ROW

    c.setStrokeColor(RULE)
    c.setLineWidth(0.4)
    c.rect(L, bottom, R - L, depth, stroke=1, fill=0)
    for i in range(1, len(rows)):
        c.line(L, TOP - i * ROW, R, TOP - i * ROW)
    c.line(206.9291, bottom, 206.9291, TOP)

    # ---------------------------------------------------------------- closing
    box(L, 319.4024 - drop, R - L, 45.6, TINT_GREEN, EDGE_GREEN, 0.5)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8.6)
    c.drawString(50.51969, 350.4024 - drop, "Payment received successfully.")
    c.setFont("Helvetica", 8.6)
    c.drawString(50.51969, 339.2024 - drop,
                 f"This invoice is generated electronically by {ISSUER['name']}. "
                 "Please retain the Invoice No., Transaction ID and payment "
                 "reference for")
    c.drawString(50.51969, 328.0024 - drop, "your records.")

    line(306.4638 - drop, TL, TR, RULE, 0.6)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(MID, 289.7945 - drop, "Thank you for your payment.")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.7)
    c.drawCentredString(MID, 280.8945 - drop,
                        f"Computer-generated invoice from {ISSUER['name']}. "
                        f"No signature is required. | {ISSUER['email']}")

    c.showPage()
    c.save()
    return buf.getvalue()
