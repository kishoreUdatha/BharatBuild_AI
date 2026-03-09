"""
Subscription Reminder Service for BharatBuild AI
Sends reminders to users who haven't subscribed after registration
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.billing import Subscription
from app.services.email_service import email_service
from app.services import email_templates
import logging

logger = logging.getLogger(__name__)


# Reminder schedule (in hours)
REMINDER_SCHEDULE = [
    {"hours": 2, "name": "2_hour", "label": "2 hours"},
    {"hours": 72, "name": "3_day", "label": "3 days"},      # 3 days
    {"hours": 168, "name": "7_day", "label": "7 days"},     # 7 days
]


class SubscriptionReminderService:
    """Service to send subscription reminders to unsubscribed users"""

    def __init__(self):
        self.is_running = False
        self.check_interval = 300  # Check every 5 minutes

    async def start(self):
        """Start the reminder service as a background task"""
        if self.is_running:
            logger.warning("[SubscriptionReminder] Service already running")
            return

        self.is_running = True
        logger.info("[SubscriptionReminder] Starting subscription reminder service")
        asyncio.create_task(self._reminder_loop())

    async def stop(self):
        """Stop the reminder service"""
        self.is_running = False
        logger.info("[SubscriptionReminder] Stopped subscription reminder service")

    async def _reminder_loop(self):
        """Main loop that checks for users needing reminders"""
        while self.is_running:
            try:
                await self._process_reminders()
            except Exception as e:
                logger.error(f"[SubscriptionReminder] Error in reminder loop: {e}")

            await asyncio.sleep(self.check_interval)

    async def _process_reminders(self):
        """Process all pending reminders"""
        async with AsyncSessionLocal() as db:
            for schedule in REMINDER_SCHEDULE:
                await self._send_reminders_for_schedule(db, schedule)

    async def _send_reminders_for_schedule(self, db: AsyncSession, schedule: dict):
        """Send reminders for a specific schedule (2hr, 3day, 7day)"""
        hours = schedule["hours"]
        reminder_name = schedule["name"]

        # Calculate time window
        # Users who registered between (now - hours - 1hr) and (now - hours)
        now = datetime.utcnow()
        window_end = now - timedelta(hours=hours)
        window_start = window_end - timedelta(hours=1)  # 1 hour window

        try:
            # Get users who:
            # 1. Registered within the time window
            # 2. Don't have an active subscription
            # 3. Haven't received this reminder yet

            # First, get users in the time window
            result = await db.execute(
                select(User).where(
                    and_(
                        User.created_at >= window_start,
                        User.created_at < window_end,
                        User.is_active == True
                    )
                )
            )
            users = result.scalars().all()

            for user in users:
                # Check if user has subscription
                has_subscription = await self._user_has_subscription(db, user.id)
                if has_subscription:
                    continue

                # Check if reminder already sent
                reminder_field = f"reminder_{reminder_name}_sent"
                if getattr(user, reminder_field, False):
                    continue

                # Send reminder
                await self._send_reminder(user, schedule)

                # Mark reminder as sent
                setattr(user, reminder_field, True)
                setattr(user, f"reminder_{reminder_name}_sent_at", now)
                await db.commit()

                logger.info(f"[SubscriptionReminder] Sent {reminder_name} reminder to {user.email}")

        except Exception as e:
            logger.error(f"[SubscriptionReminder] Error processing {reminder_name} reminders: {e}")

    async def _user_has_subscription(self, db: AsyncSession, user_id: str) -> bool:
        """Check if user has any subscription (active or past)"""
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()
        return subscription is not None

    async def _send_reminder(self, user: User, schedule: dict):
        """Send reminder via email and WhatsApp"""
        reminder_name = schedule["name"]
        reminder_label = schedule["label"]

        # Determine message based on reminder stage
        if reminder_name == "2_hour":
            subject = "Complete your BharatBuild AI setup - Special offer inside!"
            message_type = "first"
        elif reminder_name == "3_day":
            subject = "Don't miss out! Your project ideas are waiting"
            message_type = "second"
        else:  # 7_day
            subject = "Last chance: Unlock AI-powered project generation"
            message_type = "final"

        # Send email
        try:
            html_content = self._get_reminder_email(user, message_type)
            text_content = self._get_reminder_text(user, message_type)

            await email_service.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            logger.info(f"[SubscriptionReminder] Email sent to {user.email}")
        except Exception as e:
            logger.error(f"[SubscriptionReminder] Failed to send email to {user.email}: {e}")

        # Send WhatsApp
        if user.phone:
            try:
                whatsapp_message = self._get_whatsapp_message(user, message_type)
                await email_service.send_whatsapp_notification(
                    to_phone=user.phone,
                    message=whatsapp_message
                )
                logger.info(f"[SubscriptionReminder] WhatsApp sent to {user.phone}")
            except Exception as e:
                logger.error(f"[SubscriptionReminder] Failed to send WhatsApp to {user.phone}: {e}")

    def _get_reminder_email(self, user: User, message_type: str) -> str:
        """Get HTML email content for reminder"""
        user_name = user.full_name or "there"
        frontend_url = email_service.frontend_url

        if message_type == "first":
            return self._first_reminder_email(user_name, frontend_url)
        elif message_type == "second":
            return self._second_reminder_email(user_name, frontend_url)
        else:
            return self._final_reminder_email(user_name, frontend_url)

    def _get_reminder_text(self, user: User, message_type: str) -> str:
        """Get plain text content for reminder"""
        user_name = user.full_name or "there"
        frontend_url = email_service.frontend_url

        if message_type == "first":
            return f"""
Hi {user_name},

Welcome to BharatBuild AI! You're just one step away from generating complete projects with AI.

Start your first project now: {frontend_url}/pricing

What you'll get:
- Complete project generation in minutes
- Auto bug fixing with AI
- Full documentation (SRS, SDS, Reports)
- Presentation & Viva Q&A

Get started: {frontend_url}/pricing

- Team BharatBuild AI
"""
        elif message_type == "second":
            return f"""
Hi {user_name},

Your project ideas are waiting! You signed up for BharatBuild AI but haven't started building yet.

Here's what students are creating:
- E-commerce platforms
- Chat applications
- Portfolio websites
- Management systems

Don't let your ideas wait. Start building: {frontend_url}/pricing

- Team BharatBuild AI
"""
        else:
            return f"""
Hi {user_name},

This is your final reminder! Don't miss out on AI-powered project generation.

Limited time offer - Use code WELCOME20 for 20% off your first subscription.

Claim your offer: {frontend_url}/pricing

- Team BharatBuild AI
"""

    def _get_whatsapp_message(self, user: User, message_type: str) -> str:
        """Get WhatsApp message for reminder"""
        user_name = user.full_name or "there"
        frontend_url = email_service.frontend_url

        if message_type == "first":
            return f"""Hi {user_name}! 👋

Welcome to *BharatBuild AI*!

You're just one step away from generating complete projects with AI.

✨ *What you'll get:*
• Complete project in minutes
• Auto bug fixing
• Full documentation
• PPT & Viva Q&A

👉 Start now: {frontend_url}/pricing

Reply HELP for assistance."""

        elif message_type == "second":
            return f"""Hi {user_name}!

Your project ideas are waiting! 💡

You signed up for BharatBuild AI but haven't started building yet.

🚀 *Students are creating:*
• E-commerce apps
• Chat applications
• Portfolio sites
• Management systems

Don't wait - Start building: {frontend_url}/pricing"""

        else:
            return f"""Hi {user_name}!

⏰ *Last chance!*

Don't miss AI-powered project generation.

🎁 *Special Offer:*
Use code *WELCOME20* for 20% off!

👉 Claim now: {frontend_url}/pricing

Offer expires soon!"""

    def _first_reminder_email(self, user_name: str, frontend_url: str) -> str:
        """First reminder email - 2 hours after registration"""
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f6f9fc; font-family:Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f6f9fc; padding:40px 20px;">
        <tr>
            <td align="center">
                <table width="500" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden;">

                    <!-- Header -->
                    <tr>
                        <td style="background-color:#6366f1; padding:30px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:24px;">Complete Your Setup! 🚀</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px;">
                            <p style="color:#333333; font-size:16px; line-height:24px; margin:0 0 20px 0;">
                                Hi {user_name},
                            </p>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 25px 0;">
                                Welcome to <strong>BharatBuild AI</strong>! You're just one step away from generating complete projects with AI.
                            </p>

                            <!-- Features -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0fdf4; border-radius:8px; margin-bottom:25px;">
                                <tr>
                                    <td style="padding:20px;">
                                        <p style="color:#166534; font-size:14px; font-weight:bold; margin:0 0 15px 0;">What you'll get:</p>
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding:5px 0; color:#166534; font-size:13px;">✓ Complete project generation in minutes</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:5px 0; color:#166534; font-size:13px;">✓ Auto bug fixing with AI</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:5px 0; color:#166534; font-size:13px;">✓ Full documentation (SRS, SDS, Reports)</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:5px 0; color:#166534; font-size:13px;">✓ Presentation & Viva Q&A preparation</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding:10px 0 25px 0;">
                                        <a href="{frontend_url}/pricing" style="background-color:#6366f1; color:#ffffff; text-decoration:none; padding:14px 35px; border-radius:6px; font-size:16px; font-weight:bold; display:inline-block;">Get Started Now →</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="color:#888888; font-size:12px; text-align:center; margin:0;">
                                Questions? Reply to this email or contact support@bharatbuild.ai
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8f9fa; padding:20px; text-align:center; border-top:1px solid #eeeeee;">
                            <p style="color:#888888; font-size:11px; margin:0;">
                                © {datetime.utcnow().year} BharatBuild AI. All rights reserved.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''

    def _second_reminder_email(self, user_name: str, frontend_url: str) -> str:
        """Second reminder email - 3 days after registration"""
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f6f9fc; font-family:Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f6f9fc; padding:40px 20px;">
        <tr>
            <td align="center">
                <table width="500" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden;">

                    <!-- Header -->
                    <tr>
                        <td style="background-color:#f59e0b; padding:30px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:24px;">Your Ideas Are Waiting! 💡</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px;">
                            <p style="color:#333333; font-size:16px; line-height:24px; margin:0 0 20px 0;">
                                Hi {user_name},
                            </p>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 25px 0;">
                                You signed up for BharatBuild AI but haven't started building yet. Don't let your project ideas wait!
                            </p>

                            <!-- Student Projects -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#fef3c7; border-radius:8px; margin-bottom:25px;">
                                <tr>
                                    <td style="padding:20px;">
                                        <p style="color:#92400e; font-size:14px; font-weight:bold; margin:0 0 15px 0;">Students are creating:</p>
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding:5px 0; color:#92400e; font-size:13px;">🛒 E-commerce platforms</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:5px 0; color:#92400e; font-size:13px;">💬 Chat applications</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:5px 0; color:#92400e; font-size:13px;">🎨 Portfolio websites</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:5px 0; color:#92400e; font-size:13px;">📊 Management systems</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding:10px 0 25px 0;">
                                        <a href="{frontend_url}/pricing" style="background-color:#f59e0b; color:#ffffff; text-decoration:none; padding:14px 35px; border-radius:6px; font-size:16px; font-weight:bold; display:inline-block;">Start Building Now →</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="color:#888888; font-size:12px; text-align:center; margin:0;">
                                Questions? Reply to this email or contact support@bharatbuild.ai
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8f9fa; padding:20px; text-align:center; border-top:1px solid #eeeeee;">
                            <p style="color:#888888; font-size:11px; margin:0;">
                                © {datetime.utcnow().year} BharatBuild AI. All rights reserved.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''

    def _final_reminder_email(self, user_name: str, frontend_url: str) -> str:
        """Final reminder email - 7 days after registration"""
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f6f9fc; font-family:Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f6f9fc; padding:40px 20px;">
        <tr>
            <td align="center">
                <table width="500" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden;">

                    <!-- Header -->
                    <tr>
                        <td style="background-color:#ef4444; padding:30px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:24px;">Last Chance! ⏰</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px;">
                            <p style="color:#333333; font-size:16px; line-height:24px; margin:0 0 20px 0;">
                                Hi {user_name},
                            </p>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 20px 0;">
                                This is your final reminder! Don't miss out on AI-powered project generation.
                            </p>

                            <!-- Special Offer -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#fef2f2; border:2px dashed #ef4444; border-radius:8px; margin-bottom:25px;">
                                <tr>
                                    <td style="padding:25px; text-align:center;">
                                        <p style="color:#dc2626; font-size:12px; font-weight:bold; margin:0 0 10px 0; text-transform:uppercase;">Limited Time Offer</p>
                                        <p style="color:#dc2626; font-size:28px; font-weight:bold; margin:0 0 10px 0;">20% OFF</p>
                                        <p style="color:#7f1d1d; font-size:14px; margin:0 0 5px 0;">Use code: <strong style="background:#dc2626; color:#fff; padding:3px 10px; border-radius:4px;">WELCOME20</strong></p>
                                        <p style="color:#888888; font-size:11px; margin:10px 0 0 0;">*Valid for first-time subscribers only</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding:10px 0 25px 0;">
                                        <a href="{frontend_url}/pricing" style="background-color:#ef4444; color:#ffffff; text-decoration:none; padding:14px 35px; border-radius:6px; font-size:16px; font-weight:bold; display:inline-block;">Claim Your Offer →</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="color:#888888; font-size:12px; text-align:center; margin:0;">
                                Questions? Reply to this email or contact support@bharatbuild.ai
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8f9fa; padding:20px; text-align:center; border-top:1px solid #eeeeee;">
                            <p style="color:#888888; font-size:11px; margin:0;">
                                © {datetime.utcnow().year} BharatBuild AI. All rights reserved.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''

    async def send_manual_reminder(self, user_id: str, reminder_type: str = "first") -> bool:
        """Manually send a reminder to a specific user"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"[SubscriptionReminder] User not found: {user_id}")
                return False

            schedule = {"name": reminder_type, "label": reminder_type}
            await self._send_reminder(user, schedule)
            return True


# Global instance
subscription_reminder_service = SubscriptionReminderService()
