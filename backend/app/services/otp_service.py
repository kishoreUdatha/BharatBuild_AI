"""
One-time-code verification for email addresses and mobile numbers.

Used on the registration form: the visitor proves they own the address and the
number before an account is created. Registration then refuses to proceed
without that proof.

Two things are deliberate here:

* The code is hashed with a per-row salt, never stored in the clear. A dump of
  this table cannot be replayed.
* Nothing reports success unless a provider actually accepted the message. If
  no email or SMS provider is configured the request fails loudly rather than
  leaving the user waiting for a code that was never sent - except in local
  development, where the code is surfaced explicitly and labelled as such.
"""

import hashlib
import re
import secrets

from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import logger
from app.models.verification import (
    VerificationChannel,
    VerificationCode,
    VerificationPurpose,
)

CODE_LENGTH = 6
CODE_TTL_MINUTES = 10
# How long a completed verification stays usable for a registration.
PROOF_TTL_MINUTES = 30
RESEND_COOLDOWN_SECONDS = 60
MAX_SENDS_PER_WINDOW = 5
SEND_WINDOW_MINUTES = 60
MAX_VERIFY_ATTEMPTS = 5
# Claim marking a token as proof of contact ownership, so it cannot be
# confused with an access token signed by the same key.
PROOF_CLAIM = "contact_proof"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class OtpError(Exception):
    """A refusal the caller can show the user as-is."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


def normalise(channel: VerificationChannel, raw: str) -> str:
    """
    One canonical form per destination, so rate limits cannot be sidestepped by
    changing case or adding a country code.
    """
    value = (raw or "").strip()
    if channel == VerificationChannel.EMAIL:
        value = value.lower()
        if not EMAIL_RE.match(value):
            raise OtpError("Enter a valid email address.")
        return value

    digits = re.sub(r"\D", "", value)
    # Indian mobile numbers, with or without the 91 prefix.
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise OtpError("Enter a valid 10-digit Indian mobile number.")
    return digits


def _hash(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


class OtpService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --------------------------------------------------------------- lookup

    async def _live_code(
        self, channel: VerificationChannel, destination: str
    ) -> Optional[VerificationCode]:
        """The most recent unconsumed row for this destination."""
        return (await self.db.execute(
            select(VerificationCode)
            .where(VerificationCode.channel == channel)
            .where(VerificationCode.destination == destination)
            .where(VerificationCode.consumed_at.is_(None))
            .order_by(VerificationCode.created_at.desc())
        )).scalars().first()

    # -------------------------------------------------------------- request

    async def request(
        self,
        channel: VerificationChannel,
        raw_destination: str,
        *,
        purpose: VerificationPurpose = VerificationPurpose.SIGNUP,
        request_ip: Optional[str] = None,
        user_id=None,
    ) -> dict:
        destination = normalise(channel, raw_destination)
        now = datetime.utcnow()
        existing = await self._live_code(channel, destination)

        if existing is not None:
            since_last = (now - existing.last_sent_at).total_seconds()
            if since_last < RESEND_COOLDOWN_SECONDS:
                wait = int(RESEND_COOLDOWN_SECONDS - since_last)
                raise OtpError(f"Please wait {wait}s before requesting another code.", retry_after=wait)

            window_start = now - timedelta(minutes=SEND_WINDOW_MINUTES)
            if existing.created_at >= window_start and existing.send_count >= MAX_SENDS_PER_WINDOW:
                raise OtpError(
                    "Too many codes requested for this "
                    f"{'address' if channel == VerificationChannel.EMAIL else 'number'}. "
                    "Try again in an hour.",
                    retry_after=SEND_WINDOW_MINUTES * 60,
                )

        code = "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))
        salt = secrets.token_hex(8)

        if existing is not None and existing.created_at >= now - timedelta(minutes=SEND_WINDOW_MINUTES):
            # Reuse the row so send_count keeps counting across resends.
            record = existing
            record.send_count += 1
        else:
            record = VerificationCode(
                channel=channel,
                destination=destination,
                purpose=purpose,
                send_count=1,
                user_id=user_id,
            )
            self.db.add(record)

        record.code_hash = _hash(code, salt)
        record.salt = salt
        record.attempts = 0
        record.verified_at = None
        record.expires_at = now + timedelta(minutes=CODE_TTL_MINUTES)
        record.last_sent_at = now
        record.request_ip = request_ip

        delivered, channel_label, dev_code = await self._deliver(channel, destination, code)

        if not delivered and dev_code is None:
            # Nothing was sent and there is no fallback: do not leave a row
            # implying a code is in flight.
            await self.db.rollback()
            raise OtpError(
                f"Could not send the verification code by {channel_label}. "
                "The provider is not configured - contact support."
            )

        await self.db.commit()
        logger.info(f"[OTP] Code issued for {channel.value}:{self._mask(channel, destination)} "
                    f"(send #{record.send_count}, delivered={delivered})")

        return {
            "channel": channel.value,
            "destination": self._mask(channel, destination),
            "expires_in": CODE_TTL_MINUTES * 60,
            "resend_after": RESEND_COOLDOWN_SECONDS,
            "delivered": delivered,
            # Only ever populated outside production when no provider exists.
            "dev_code": dev_code,
            "dev_mode": dev_code is not None,
        }

    # --------------------------------------------------------------- verify

    async def verify(
        self, channel: VerificationChannel, raw_destination: str, code: str
    ) -> dict:
        destination = normalise(channel, raw_destination)
        record = await self._live_code(channel, destination)

        if record is None:
            raise OtpError("Request a code first.")
        # Note the code is checked even when the row is already verified. It
        # used to short-circuit here, which meant any wrong code submitted
        # afterwards was answered with "verified".
        already = record.verified_at is not None
        if record.is_expired and not already:
            raise OtpError("That code has expired. Request a new one.")
        if record.attempts >= MAX_VERIFY_ATTEMPTS:
            raise OtpError("Too many incorrect attempts. Request a new code.")

        supplied = re.sub(r"\D", "", code or "")
        # Constant-time compare so a wrong code cannot be narrowed by timing.
        if not secrets.compare_digest(_hash(supplied, record.salt), record.code_hash):
            record.attempts += 1
            await self.db.commit()
            left = MAX_VERIFY_ATTEMPTS - record.attempts
            raise OtpError(
                f"That code is not correct. {left} attempt{'s' if left != 1 else ''} left."
                if left > 0 else "Too many incorrect attempts. Request a new code."
            )

        if not already:
            record.verified_at = datetime.utcnow()
            await self.db.commit()
        logger.info(f"[OTP] Verified {channel.value}:{self._mask(channel, destination)}")
        return {
            "verified": True,
            "already": already,
            # Only the caller who supplied the correct code receives this, and
            # registration will not accept the destination without it.
            "verification_token": self._mint_token(channel, destination),
        }

    # ---------------------------------------------------------------- proof

    @staticmethod
    def _mint_token(channel: VerificationChannel, destination: str) -> str:
        return jwt.encode(
            {
                "typ": PROOF_CLAIM,
                "channel": channel.value,
                "destination": destination,
                "exp": datetime.utcnow() + timedelta(minutes=PROOF_TTL_MINUTES),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    async def check_proof(
        self, channel: VerificationChannel, raw_destination: str, token: Optional[str]
    ) -> bool:
        """
        Is this destination proven *by the holder of this token*?

        Binding to a token matters: keying proof off the destination alone let
        anyone who merely knew an address or number register with it during
        somebody else's verification window, without ever receiving the code.
        """
        if not token:
            return False
        try:
            destination = normalise(channel, raw_destination)
        except OtpError:
            return False

        try:
            claims = jwt.decode(token, settings.JWT_SECRET_KEY,
                                algorithms=[settings.JWT_ALGORITHM])
        except JWTError:
            return False

        if claims.get("typ") != PROOF_CLAIM:
            return False
        if claims.get("channel") != channel.value:
            return False
        if claims.get("destination") != destination:
            return False

        # The token proves who verified; the row proves it has not been spent.
        record = await self._live_code(channel, destination)
        if record is None or record.verified_at is None:
            return False
        return record.verified_at >= datetime.utcnow() - timedelta(minutes=PROOF_TTL_MINUTES)

    async def consume(self, channel: VerificationChannel, raw_destination: str, user_id=None) -> None:
        """
        Spend the proof so it cannot create a second account.

        Called after the user row is committed.
        """
        try:
            destination = normalise(channel, raw_destination)
        except OtpError:
            return
        record = await self._live_code(channel, destination)
        if record is None or record.verified_at is None:
            return
        record.consumed_at = datetime.utcnow()
        if user_id is not None:
            record.user_id = user_id
        await self.db.commit()

    # ------------------------------------------------------------- delivery

    async def _deliver(
        self, channel: VerificationChannel, destination: str, code: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Returns (delivered, channel_label, dev_code).

        dev_code is non-None only outside production when no provider is
        configured, so a developer can still complete the flow. The caller
        surfaces it flagged as dev mode rather than pretending it was sent.
        """
        if channel == VerificationChannel.EMAIL:
            delivered = await self._send_email(destination, code)
            label = "email"
        else:
            delivered = await self._send_sms(destination, code)
            label = "SMS"

        dev_code = None
        if not delivered and self._dev_fallback_allowed():
            dev_code = code
            logger.warning(
                f"[OTP] No {label} provider configured; returning the code in the response. "
                f"This only happens outside production. code={code} "
                f"destination={self._mask(channel, destination)}"
            )
        return delivered, label, dev_code

    @staticmethod
    def _dev_fallback_allowed() -> bool:
        env = str(getattr(settings, "ENVIRONMENT", "development")).lower()
        return env not in ("production", "prod")

    @staticmethod
    async def _send_email(destination: str, code: str) -> bool:
        from app.services.email_service import email_service

        subject = f"{code} is your BharatBuild verification code"
        text = (
            f"Your BharatBuild AI verification code is {code}.\n\n"
            f"It expires in {CODE_TTL_MINUTES} minutes. If you did not request it, ignore this email."
        )
        html = f"""
        <div style="font-family:Segoe UI,Arial,sans-serif;max-width:460px;margin:auto">
          <h2 style="color:#1B1B3A;margin-bottom:4px">Verify your email</h2>
          <p style="color:#5A5F7A;font-size:14px;margin-top:0">
            Use this code to finish creating your BharatBuild AI account.
          </p>
          <p style="font-size:30px;letter-spacing:8px;font-weight:700;color:#2563EB;margin:20px 0">
            {code}
          </p>
          <p style="color:#8A8FA8;font-size:12px">
            The code expires in {CODE_TTL_MINUTES} minutes. If you did not request it, ignore this email.
          </p>
        </div>
        """
        try:
            return bool(await email_service.send_email(
                to_email=destination, subject=subject, html_content=html, text_content=text
            ))
        except Exception as exc:
            logger.error(f"[OTP] Email send failed: {type(exc).__name__}: {exc}")
            return False

    @staticmethod
    async def _send_sms(destination: str, code: str) -> bool:
        """
        Send over whichever SMS provider is configured.

        MSG91 first because it is the usual choice for Indian numbers, then
        Twilio. Returns False when neither is set up - the caller decides what
        to do about it rather than this pretending.
        """
        import httpx

        message = (f"{code} is your BharatBuild AI verification code. "
                   f"Valid for {CODE_TTL_MINUTES} minutes. Do not share it.")

        msg91_key = getattr(settings, "MSG91_AUTH_KEY", None)
        if msg91_key:
            # MSG91's dedicated OTP endpoint. Note it takes query parameters
            # with an empty body, not JSON - posting a body here silently
            # returns a non-success type. `otp` passes our own code through so
            # this service stays the single source of truth for what is valid;
            # verification is done against our hash, never MSG91's.
            params = {
                "authkey": msg91_key,
                "mobile": f"91{destination}",
                "otp": code,
                "otp_length": CODE_LENGTH,
                "otp_expiry": CODE_TTL_MINUTES,
            }
            template_id = (getattr(settings, "MSG91_OTP_TEMPLATE_ID", None)
                           or getattr(settings, "MSG91_TEMPLATE_ID", None))
            if template_id:
                params["template_id"] = template_id

            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.post(
                        "https://api.msg91.com/api/v5/otp",
                        params=params,
                        headers={"Content-Type": "application/json"},
                    )
                payload = {}
                try:
                    payload = response.json()
                except Exception:
                    pass
                # A 200 does not mean sent - MSG91 reports failures in the body.
                if response.status_code < 300 and payload.get("type") == "success":
                    logger.info(f"[OTP] MSG91 accepted the send (request_id={payload.get('request_id')})")
                    return True
                logger.error(
                    f"[OTP] MSG91 did not send: HTTP {response.status_code} "
                    f"type={payload.get('type')} message={payload.get('message')}"
                )
            except Exception as exc:
                logger.error(f"[OTP] MSG91 send failed: {type(exc).__name__}: {exc}")

        sid = getattr(settings, "TWILIO_SID", None) or getattr(settings, "TWILIO_ACCOUNT_SID", None)
        token = getattr(settings, "TWILIO_TOKEN", None) or getattr(settings, "TWILIO_AUTH_TOKEN", None)
        sender = getattr(settings, "TWILIO_SMS_NUMBER", None)
        if sid and token and sender:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                        auth=(sid, token),
                        data={"To": f"+91{destination}", "From": sender, "Body": message},
                    )
                if response.status_code < 300:
                    return True
                logger.error(f"[OTP] Twilio rejected the send: {response.status_code} {response.text[:180]}")
            except Exception as exc:
                logger.error(f"[OTP] Twilio send failed: {type(exc).__name__}: {exc}")

        return False

    @staticmethod
    def _mask(channel: VerificationChannel, destination: str) -> str:
        """Never echo a full address or number back to the client."""
        if channel == VerificationChannel.EMAIL:
            name, _, domain = destination.partition("@")
            head = name[:2] if len(name) > 2 else name[:1]
            return f"{head}{'*' * max(1, len(name) - len(head))}@{domain}"
        return f"{'*' * 6}{destination[-4:]}"
