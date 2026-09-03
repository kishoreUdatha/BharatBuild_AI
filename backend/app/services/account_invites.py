"""
Creating an account for somebody else.

Every account in this system arrived either from a seeder or from public
self-signup, which is fine for students and useless for onboarding: a college
needs its administrator created for it, and that administrator needs to create
their own guides and trainers.

The account is created with no usable password and an emailed link to set one.
Nobody - not the platform operator, not the college - ever handles another
person's credentials, and the link is the same password-reset token the rest of
the application already issues, so there is one mechanism to keep working
rather than two.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from jose import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import logger
from app.core.security import get_password_hash
from app.models.college import College
from app.models.user import User, UserRole
from app.services.email_service import email_service


class InviteError(Exception):
    """A refusal the caller can show the user as-is."""


# A college's own administrator creates their own guides. This is their
# business, not the vendor's - the platform operator should never be staffing
# a customer's departments for them.
#
# Not trainers: those are BharatBuild's staff, working across several colleges.
# A customer creating one would be creating an account they do not employ and
# cannot be given to anybody else.
COLLEGE_CREATABLE = [UserRole.FACULTY]

# The platform operator creates two kinds of account.
#
# ADMIN is the administrator a newly onboarded college is handed - the
# handover, after which everything belongs to the college. It carries
# UserRole.ADMIN with is_superuser left False, precisely the distinction
# `get_platform_admin` already draws: a college's administrator, not an
# administrator of the platform.
#
# TRAINER is BharatBuild's own teaching staff. They belong to no college at
# all, and are given colleges to work in through assignments afterwards.
#
# MANAGER is BharatBuild's operations staff, who run every college and the
# trainers across them. Only the operator may create one - a manager creating
# managers is how a support role quietly becomes an owner.
PLATFORM_CREATABLE = [UserRole.ADMIN, UserRole.TRAINER, UserRole.MANAGER]

ROLE_LABELS = {
    UserRole.MANAGER: "Platform manager",
    UserRole.ADMIN: "College administrator",
    UserRole.FACULTY: "Faculty",
    UserRole.TRAINER: "Trainer",
}


def _reset_token(user: User) -> str:
    """
    The same token `/forgot-password` issues.

    Longer-lived, because an invite may sit in a mailbox over a weekend and an
    hour is fine for a reset somebody just asked for but not for one they were
    not expecting.
    """
    return jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(days=7),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


class AccountInviteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _creatable(actor: User) -> List[UserRole]:
        """
        What this actor may create.

        Read by both the form and the create path. When these were two
        separate expressions they disagreed: the dropdown offered a manager
        "Faculty" while the server would have accepted an administrator or a
        trainer.
        """
        if actor.is_superuser:
            return PLATFORM_CREATABLE
        if actor.role == UserRole.MANAGER:
            # Colleges and trainers, which is their job - but not another
            # manager, which is how a support role quietly becomes an owner.
            return [UserRole.ADMIN, UserRole.TRAINER]
        return COLLEGE_CREATABLE

    async def options(self, actor: User) -> dict:
        """What this actor may create, and where."""
        platform = bool(actor.is_superuser) or actor.role == UserRole.MANAGER
        colleges = []
        if platform:
            rows = (await self.db.execute(
                select(College)
                .where(College.is_active.is_(True))
                .where(College.is_self_serve.is_(False))
                .order_by(College.name)
            )).scalars().all()
            colleges = [{"id": str(c.id), "name": c.name, "code": c.code}
                        for c in rows]
        return {
            "roles": [{"key": r.value, "label": ROLE_LABELS[r]}
                      for r in self._creatable(actor)],
            # A college admin creates only within their own college, so there
            # is nothing to choose.
            "colleges": colleges,
            "can_choose_college": platform,
        }

    async def create(
        self,
        actor: User,
        *,
        email: str,
        full_name: str,
        role: str,
        college_id: Optional[str] = None,
        department: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> dict:
        address = (email or "").strip().lower()
        if not address or "@" not in address:
            raise InviteError("That is not an email address.")

        name = (full_name or "").strip()
        if len(name) < 2:
            raise InviteError("Enter the person's name.")

        try:
            wanted = UserRole(role)
        except ValueError:
            raise InviteError("Unknown role.")

        allowed = self._creatable(actor)
        if wanted not in allowed:
            raise InviteError(
                f"You can create: {', '.join(ROLE_LABELS[r] for r in allowed)}.")

        # A platform trainer belongs to no college. Their reach comes from
        # assignments made afterwards, so there is nothing to attach here -
        # and attaching one would make them a member of a customer's tenant.
        # Neither belongs to a college: a trainer is given colleges through
        # assignments, and a manager runs all of them.
        if wanted in (UserRole.TRAINER, UserRole.MANAGER):
            return await self._create_platform_staff(
                actor, address, name, wanted, department, phone)

        # A college admin creates inside their own college and nowhere else.
        # Reading the target from the request for them would let one customer
        # put staff into another's tenant.
        target = college_id if actor.is_superuser else str(actor.college_id or "")
        if not target:
            raise InviteError("This account is not attached to a college, so it "
                              "cannot create staff for one.")
        college = (await self.db.execute(
            select(College).where(College.id == target))).scalars().first()
        if college is None or college.is_self_serve:
            raise InviteError("Choose a college.")
        if not college.is_active:
            raise InviteError(f"{college.name} is not active.")

        clash = (await self.db.execute(
            select(User).where(func.lower(User.email) == address))).scalars().first()
        if clash is not None:
            raise InviteError(f"{address} already has an account.")

        user = User(
            email=address,
            full_name=name,
            username=address.split("@")[0],
            # No password anybody can use. The hash is of a value nothing
            # knows, so the only way in is the link below - the account cannot
            # be signed into before its owner has claimed it.
            hashed_password=get_password_hash(jwt.encode(
                {"nonce": address, "at": datetime.utcnow().isoformat()},
                settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)),
            role=wanted,
            college_id=college.id,
            college_name=college.name,
            department=(department or "").strip() or None,
            phone=(phone or "").strip() or None,
            is_active=True,
            # Created by a person who already had to be trusted; the address
            # is confirmed by the fact they can follow the link sent to it.
            is_verified=True,
            # Never. A college's administrator administers their college; the
            # platform operator's own privileges are not something this form
            # can hand out, whoever is using it.
            is_superuser=False,
        )
        self.db.add(user)
        await self.db.flush()

        token = _reset_token(user)
        user.reset_token_hash = get_password_hash(token[:20])
        user.reset_token_expires = datetime.utcnow() + timedelta(days=7)
        await self.db.commit()

        sent = False
        try:
            sent = await email_service.send_password_reset_email(
                to_email=user.email, user_name=user.full_name, reset_token=token)
        except Exception as exc:                      # noqa: BLE001
            logger.error(f"[Invite] could not email {user.email}: {exc}")

        logger.info(f"[Invite] {actor.email} created {user.email} "
                    f"({wanted.value}) at {college.code}; emailed={sent}")
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": wanted.value,
            "college": college.name,
            "invite_sent": sent,
            # Said plainly rather than implied: an account nobody can sign into
            # and nobody was told about is worse than no account at all.
            "message": (
                f"{user.full_name} can now set a password from the link emailed "
                f"to {user.email}."
                if sent else
                f"{user.full_name}'s account was created, but the invite email "
                f"could not be sent. Ask them to use Forgot password on "
                f"{user.email} to set one."
            ),
        }

    async def _create_platform_staff(self, actor: User, address: str, name: str,
                                     wanted, department, phone) -> dict:
        """
        BharatBuild's own staff, attached to no college.

        A trainer sees nothing until they are given a college on the
        assignments screen, which is the correct default - an account that
        could see every tenant the moment it was created would be the
        opposite. A manager is that account by design, which is why only the
        operator may create one.
        """
        clash = (await self.db.execute(
            select(User).where(func.lower(User.email) == address))).scalars().first()
        if clash is not None:
            raise InviteError(f"{address} already has an account.")

        user = User(
            email=address,
            full_name=name,
            username=address.split("@")[0],
            hashed_password=get_password_hash(jwt.encode(
                {"nonce": address, "at": datetime.utcnow().isoformat()},
                settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)),
            role=wanted,
            college_id=None,
            department=(department or "").strip() or None,
            phone=(phone or "").strip() or None,
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        self.db.add(user)
        await self.db.flush()

        token = _reset_token(user)
        user.reset_token_hash = get_password_hash(token[:20])
        user.reset_token_expires = datetime.utcnow() + timedelta(days=7)
        await self.db.commit()

        sent = False
        try:
            sent = await email_service.send_password_reset_email(
                to_email=user.email, user_name=user.full_name, reset_token=token)
        except Exception as exc:                      # noqa: BLE001
            logger.error(f"[Invite] could not email {user.email}: {exc}")

        logger.info(f"[Invite] {actor.email} created {wanted.value} "
                    f"{user.email}; emailed={sent}")
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": wanted.value,
            "college": None,
            "invite_sent": sent,
            "message": (
                (f"{user.full_name} is created and runs every college"
                 if wanted == UserRole.MANAGER else
                 f"{user.full_name} is created. Assign them a college so they "
                 f"can see anything")
                + (f", and they can set a password from the link emailed to "
                   f"{user.email}." if sent else
                   f". The invite email could not be sent - ask them to use "
                   f"Forgot password on {user.email}.")
            ),
        }

    async def resend(self, actor: User, user_id: str) -> dict:
        """Send the set-a-password link again."""
        user = (await self.db.execute(
            select(User).where(User.id == user_id))).scalars().first()
        if user is None:
            raise InviteError("No such account.")
        if not actor.is_superuser and str(user.college_id) != str(actor.college_id):
            raise InviteError("That account belongs to another college.")

        token = _reset_token(user)
        user.reset_token_hash = get_password_hash(token[:20])
        user.reset_token_expires = datetime.utcnow() + timedelta(days=7)
        await self.db.commit()

        sent = False
        try:
            sent = await email_service.send_password_reset_email(
                to_email=user.email, user_name=user.full_name, reset_token=token)
        except Exception as exc:                      # noqa: BLE001
            logger.error(f"[Invite] resend to {user.email} failed: {exc}")

        return {
            "email": user.email,
            "invite_sent": sent,
            "message": (f"Sent again to {user.email}." if sent
                        else f"The email could not be sent to {user.email}."),
        }
