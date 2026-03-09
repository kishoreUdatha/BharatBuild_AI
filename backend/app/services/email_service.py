"""
Email Service for BharatBuild AI
================================
Handles all email sending functionality including:
- Email verification on signup
- Password reset emails
- Purchase confirmations
- Notifications
- Bulk emails to students

Supports: Resend (recommended), SendGrid, and SMTP.
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict
from datetime import datetime
import secrets
import asyncio

from app.core.config import settings
from app.core.logging_config import logger
from app.services import email_templates

# Try to import Resend
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    logger.warning("[Email] Resend SDK not installed. Install with: pip install resend")

# Try to import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content, Personalization
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("[Email] SendGrid SDK not installed. Install with: pip install sendgrid")


class EmailService:
    """Async email service using Resend, SendGrid, or SMTP"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME
        self.frontend_url = settings.FRONTEND_URL

        # Email provider configuration
        self.email_provider = getattr(settings, 'EMAIL_PROVIDER', 'smtp').lower()
        self.resend_api_key = getattr(settings, 'RESEND_API_KEY', None)
        self.sendgrid_api_key = getattr(settings, 'SENDGRID_API_KEY', None)

        # Determine which provider to use
        self.use_resend = (
            self.email_provider == 'resend' and
            RESEND_AVAILABLE and
            bool(self.resend_api_key)
        )
        self.use_sendgrid = (
            not self.use_resend and
            self.email_provider == 'sendgrid' and
            SENDGRID_AVAILABLE and
            bool(self.sendgrid_api_key)
        )

        # Initialize Resend if configured
        if self.use_resend:
            resend.api_key = self.resend_api_key
            logger.info("[Email] Using Resend for email delivery")
        elif self.use_sendgrid:
            logger.info("[Email] Using SendGrid for email delivery")
        else:
            logger.info("[Email] Using SMTP for email delivery")

    @property
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        if self.use_resend:
            return bool(self.resend_api_key)
        if self.use_sendgrid:
            return bool(self.sendgrid_api_key)
        return bool(self.smtp_user and self.smtp_password)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """
        Send an email asynchronously.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
            attachments: List of attachments, each dict should have:
                - filename: Name of the file
                - content: Base64 encoded content OR bytes
                - content_type: MIME type (e.g., 'application/pdf')

        Returns True if successful, False otherwise.
        """
        if not self.is_configured:
            logger.warning("[Email] Email service not configured, skipping email send")
            return False

        if self.use_resend:
            return await self._send_via_resend(to_email, subject, html_content, text_content, attachments)
        elif self.use_sendgrid:
            return await self._send_via_sendgrid(to_email, subject, html_content, text_content, attachments)
        else:
            return await self._send_via_smtp(to_email, subject, html_content, text_content, attachments)

    async def _send_via_resend(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """Send email via Resend API"""
        try:
            import base64

            # Prepare email params
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            if text_content:
                params["text"] = text_content

            # Add attachments if provided
            if attachments:
                resend_attachments = []
                for att in attachments:
                    content = att.get("content")
                    # Convert bytes to base64 if needed
                    if isinstance(content, bytes):
                        content = base64.b64encode(content).decode('utf-8')

                    resend_attachments.append({
                        "filename": att.get("filename"),
                        "content": content,
                    })
                params["attachments"] = resend_attachments

            # Run synchronous Resend call in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: resend.Emails.send(params)
            )

            if response and response.get("id"):
                logger.info(f"[Email/Resend] Successfully sent email to {to_email}: {subject}")
                return True
            else:
                logger.error(f"[Email/Resend] Failed to send email: {response}")
                return False

        except Exception as e:
            logger.error(f"[Email/Resend] Failed to send email to {to_email}: {e}")
            return False

    async def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """Send email via SendGrid API"""
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            if text_content:
                message.add_content(Content("text/plain", text_content))

            sg = SendGridAPIClient(self.sendgrid_api_key)
            # Run synchronous SendGrid call in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, sg.send, message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"[Email/SendGrid] Successfully sent email to {to_email}: {subject}")
                return True
            else:
                logger.error(f"[Email/SendGrid] Failed with status {response.status_code}: {response.body}")
                return False

        except Exception as e:
            logger.error(f"[Email/SendGrid] Failed to send email to {to_email}: {e}")
            return False

    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject

            # Add plain text version (fallback)
            if text_content:
                message.attach(MIMEText(text_content, "plain"))

            # Add HTML version
            message.attach(MIMEText(html_content, "html"))

            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True
            )

            logger.info(f"[Email/SMTP] Successfully sent email to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"[Email/SMTP] Failed to send email to {to_email}: {e}")
            return False

    async def send_bulk_email(
        self,
        recipients: List[Dict[str, str]],  # [{"email": "...", "name": "..."}]
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Send bulk emails to multiple recipients.

        Args:
            recipients: List of dicts with 'email' and optional 'name' keys
            subject: Email subject
            html_content: HTML body (can use {{name}} placeholder)
            text_content: Plain text body (optional)

        Returns:
            Dict with 'success_count', 'failed_count', 'failed_emails'
        """
        success_count = 0
        failed_count = 0
        failed_emails = []

        for recipient in recipients:
            email = recipient.get("email")
            name = recipient.get("name", "Student")

            if not email:
                continue

            # Replace placeholders
            personalized_html = html_content.replace("{{name}}", name)
            personalized_text = text_content.replace("{{name}}", name) if text_content else None

            success = await self.send_email(email, subject, personalized_html, personalized_text)

            if success:
                success_count += 1
            else:
                failed_count += 1
                failed_emails.append(email)

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)

        logger.info(f"[Email] Bulk send complete: {success_count} success, {failed_count} failed")

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_emails": failed_emails
        }

    async def send_to_students(
        self,
        students: List[Dict[str, str]],
        subject: str,
        message: str,
        include_login_link: bool = True
    ) -> Dict[str, any]:
        """
        Send notification email to students.

        Args:
            students: List of student dicts with 'email', 'name' keys
            subject: Email subject
            message: Main message content
            include_login_link: Whether to include login button

        Returns:
            Result dict with success/failed counts
        """
        login_button = f'''
            <p style="text-align: center;">
                <a href="{self.frontend_url}/login" style="display: inline-block; background: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                    Login to BharatBuild AI
                </a>
            </p>
        ''' if include_login_link else ''

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>BharatBuild AI</h1>
                </div>
                <div class="content">
                    <p>Hi {{{{name}}}},</p>
                    <div style="margin: 20px 0;">
                        {message}
                    </div>
                    {login_button}
                </div>
                <div class="footer">
                    <p>&copy; {datetime.utcnow().year} BharatBuild AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Hi {{{{name}}}},

        {message}

        {'Login at: ' + self.frontend_url + '/login' if include_login_link else ''}

        - BharatBuild AI Team
        """

        return await self.send_bulk_email(students, subject, html_content, text_content)

    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_token: str
    ) -> bool:
        """Send email verification link to new user"""
        # URL-encode the token to handle special characters (+, /, =)
        from urllib.parse import quote
        encoded_token = quote(verification_token, safe='')
        verification_link = f"{self.frontend_url}/verify-email?token={encoded_token}"
        subject = "Verify your email - BharatBuild AI"

        html_content = email_templates.verification_email(
            user_name=user_name,
            verification_link=verification_link,
            frontend_url=self.frontend_url
        )

        text_content = f"""
Welcome to BharatBuild AI!

Hi {user_name or 'there'},

Thanks for signing up! Please verify your email address by clicking the link below:

{verification_link}

This link will expire in 24 hours.

If you didn't sign up for BharatBuild AI, please ignore this email.

- The BharatBuild AI Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_token: str
    ) -> bool:
        """Send password reset link"""
        # URL-encode the token to handle special characters (+, /, =)
        from urllib.parse import quote
        encoded_token = quote(reset_token, safe='')
        reset_link = f"{self.frontend_url}/forgot-password?token={encoded_token}"
        subject = "Reset your password - BharatBuild AI"

        html_content = email_templates.password_reset_email(
            user_name=user_name,
            reset_link=reset_link,
            frontend_url=self.frontend_url
        )

        text_content = f"""
Password Reset Request

Hi {user_name or 'there'},

We received a request to reset your password. Click the link below to create a new password:

{reset_link}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email.

- The BharatBuild AI Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_purchase_confirmation_email(
        self,
        to_email: str,
        user_name: str,
        plan_name: str,
        amount: int,  # in paise
        payment_id: str,
        customer_phone: Optional[str] = None,
        college_name: Optional[str] = None
    ) -> bool:
        """Send purchase confirmation email with invoice PDF attachment"""
        from app.services.invoice_service import invoice_service

        amount_display = f"₹{amount / 100:,.0f}"
        subject = f"Payment Confirmed - {plan_name} - BharatBuild AI"

        # Generate invoice
        invoice_number = invoice_service.generate_invoice_number(payment_id)

        try:
            invoice_pdf = invoice_service.generate_invoice_pdf(
                invoice_number=invoice_number,
                customer_name=user_name or "Customer",
                customer_email=to_email,
                customer_phone=customer_phone,
                plan_name=plan_name,
                amount=amount,
                payment_id=payment_id,
                college_name=college_name
            )

            # Create attachment
            attachments = [{
                "filename": f"Invoice_{invoice_number}.pdf",
                "content": invoice_pdf,
                "content_type": "application/pdf"
            }]
        except Exception as e:
            logger.error(f"[Email] Failed to generate invoice PDF: {e}")
            attachments = None

        html_content = email_templates.purchase_confirmation_email(
            user_name=user_name,
            plan_name=plan_name,
            amount_display=amount_display,
            payment_id=payment_id,
            frontend_url=self.frontend_url,
            invoice_number=invoice_number
        )

        text_content = f"""
Payment Successful!

Hi {user_name or 'there'},

Thank you for your purchase! Your payment has been confirmed.

Order Details:
- Invoice Number: {invoice_number}
- Plan: {plan_name}
- Amount Paid: {amount_display}
- Payment ID: {payment_id}
- Date: {datetime.utcnow().strftime('%B %d, %Y')}

Your invoice is attached to this email.

Start building at: {self.frontend_url}/build

- The BharatBuild AI Team
        """

        return await self.send_email(to_email, subject, html_content, text_content, attachments)

    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str
    ) -> bool:
        """Send welcome email after verification"""
        subject = "Welcome to BharatBuild AI - Let's build something amazing!"

        html_content = email_templates.welcome_email(
            user_name=user_name,
            frontend_url=self.frontend_url
        )

        text_content = f"""
Welcome to BharatBuild AI!

Hi {user_name or 'there'},

Your email has been verified and your account is ready to go!

Here's what you can do:
- Generate Complete Projects: Describe your idea and get a fully functional project
- AI-Powered Bug Fixing: Let AI detect and fix errors automatically
- Complete Documentation: Generate SRS, SDS, Reports, PPT, and Viva Q&A

Start building now: {self.frontend_url}/build

- The BharatBuild AI Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)


    async def send_new_user_alert(
        self,
        user_email: str,
        user_name: str,
        user_role: str,
        college_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> bool:
        """
        Send alert to admin when a new user registers.

        This helps track new signups in real-time.
        """
        # Admin email to receive alerts - can be configured in settings
        admin_email = getattr(settings, 'ADMIN_ALERT_EMAIL', None) or self.from_email

        subject = f"🎉 New User Signup - {user_name} ({user_role})"

        html_content = email_templates.new_user_alert_email(
            user_name=user_name,
            user_email=user_email,
            user_role=user_role,
            phone=phone,
            college_name=college_name,
            frontend_url=self.frontend_url
        )

        text_content = f"""
New User Registration Alert

A new user has signed up on BharatBuild AI:

Name: {user_name}
Email: {user_email}
Role: {user_role}
{f'Phone: {phone}' if phone else ''}
{f'College: {college_name}' if college_name else ''}
Time: {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}

View in Admin Portal: {self.frontend_url}/admin/users
        """

        return await self.send_email(admin_email, subject, html_content, text_content)

    async def send_webhook_notification(
        self,
        webhook_url: str,
        message: str,
        title: str = "BharatBuild AI Alert",
        color: int = 0x10b981  # Green color
    ) -> bool:
        """
        Send notification to Slack/Discord webhook.

        Works with both Slack and Discord webhook formats.
        """
        import httpx

        try:
            # Detect if it's Slack or Discord based on URL
            is_discord = "discord.com" in webhook_url

            if is_discord:
                # Discord webhook format
                payload = {
                    "embeds": [{
                        "title": title,
                        "description": message,
                        "color": color,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }
            else:
                # Slack webhook format
                payload = {
                    "text": f"*{title}*\n{message}"
                }

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                if response.status_code in [200, 204]:
                    logger.info(f"[Webhook] Successfully sent notification: {title}")
                    return True
                else:
                    logger.error(f"[Webhook] Failed with status {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"[Webhook] Failed to send notification: {e}")
            return False

    async def send_whatsapp_notification(
        self,
        to_phone: str,
        message: str
    ) -> bool:
        """
        Send WhatsApp notification using configured provider.

        Supports:
        - Exotel WhatsApp API (preferred for India)
        - Twilio WhatsApp API
        - Meta WhatsApp Cloud API

        Args:
            to_phone: Phone number with country code (e.g., +919876543210)
            message: Message text to send

        Returns:
            True if successful, False otherwise
        """
        import httpx

        # Try Exotel first (preferred for India)
        exotel_sid = getattr(settings, 'EXOTEL_SID', None)
        exotel_token = getattr(settings, 'EXOTEL_TOKEN', None)

        if exotel_sid and exotel_token:
            return await self._send_whatsapp_exotel(to_phone, message, exotel_sid, exotel_token)

        # Try Twilio
        twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        twilio_whatsapp = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)

        if twilio_sid and twilio_token and twilio_whatsapp:
            return await self._send_whatsapp_twilio(to_phone, message, twilio_sid, twilio_token, twilio_whatsapp)

        # Try Meta WhatsApp Cloud API
        meta_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        meta_phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)

        if meta_token and meta_phone_id:
            return await self._send_whatsapp_meta(to_phone, message, meta_token, meta_phone_id)

        logger.warning("[WhatsApp] No WhatsApp provider configured")
        return False

    async def _send_whatsapp_exotel(
        self,
        to_phone: str,
        message: str,
        exotel_sid: str,
        exotel_token: str
    ) -> bool:
        """Send WhatsApp message via Exotel API"""
        import httpx
        import base64

        try:
            # Exotel WhatsApp API endpoint
            exotel_subdomain = getattr(settings, 'EXOTEL_SUBDOMAIN', 'api.exotel.com')
            url = f"https://{exotel_subdomain}/v2/accounts/{exotel_sid}/messages"

            # Clean phone number (remove + and spaces)
            clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")

            # Get the Exotel WhatsApp number (sender)
            exotel_whatsapp_number = getattr(settings, 'EXOTEL_WHATSAPP_NUMBER', None)

            if not exotel_whatsapp_number:
                logger.error("[WhatsApp/Exotel] EXOTEL_WHATSAPP_NUMBER not configured")
                return False

            # Exotel API payload
            payload = {
                "from": exotel_whatsapp_number,
                "to": clean_phone,
                "body": message,
                "channel": "whatsapp"
            }

            # Basic auth
            auth_string = base64.b64encode(f"{exotel_sid}:{exotel_token}".encode()).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Basic {auth_string}",
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code in [200, 201, 202]:
                    logger.info(f"[WhatsApp/Exotel] Successfully sent message to {to_phone}")
                    return True
                else:
                    logger.error(f"[WhatsApp/Exotel] Failed with status {response.status_code}: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"[WhatsApp/Exotel] Failed to send message: {e}")
            return False

    async def _send_whatsapp_twilio(
        self,
        to_phone: str,
        message: str,
        account_sid: str,
        auth_token: str,
        from_number: str
    ) -> bool:
        """Send WhatsApp message via Twilio"""
        import httpx
        import base64

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

            # Ensure phone numbers have whatsapp: prefix
            from_whatsapp = f"whatsapp:{from_number}" if not from_number.startswith("whatsapp:") else from_number
            to_whatsapp = f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone

            data = {
                "From": from_whatsapp,
                "To": to_whatsapp,
                "Body": message
            }

            # Basic auth
            auth_string = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    headers={
                        "Authorization": f"Basic {auth_string}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                )

                if response.status_code in [200, 201]:
                    logger.info(f"[WhatsApp/Twilio] Successfully sent message to {to_phone}")
                    return True
                else:
                    logger.error(f"[WhatsApp/Twilio] Failed with status {response.status_code}: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"[WhatsApp/Twilio] Failed to send message: {e}")
            return False

    async def _send_whatsapp_meta(
        self,
        to_phone: str,
        message: str,
        access_token: str,
        phone_number_id: str
    ) -> bool:
        """Send WhatsApp message via Meta Cloud API"""
        import httpx

        try:
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"

            # Remove + from phone number if present
            clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")

            payload = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "text",
                "text": {
                    "body": message
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code in [200, 201]:
                    logger.info(f"[WhatsApp/Meta] Successfully sent message to {to_phone}")
                    return True
                else:
                    logger.error(f"[WhatsApp/Meta] Failed with status {response.status_code}: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"[WhatsApp/Meta] Failed to send message: {e}")
            return False

    async def send_whatsapp_new_user_alert(
        self,
        user_email: str,
        user_name: str,
        user_role: str,
        college_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> bool:
        """Send WhatsApp alert for new user registration"""
        admin_phone = getattr(settings, 'ADMIN_WHATSAPP_NUMBER', None)

        if not admin_phone:
            logger.warning("[WhatsApp] ADMIN_WHATSAPP_NUMBER not configured")
            return False

        message = f"""🎉 *New User Signup*

*Name:* {user_name}
*Email:* {user_email}
*Role:* {user_role}
{f'*Phone:* {phone}' if phone else ''}
{f'*College:* {college_name}' if college_name else ''}
*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Login to admin portal to view details."""

        return await self.send_whatsapp_notification(admin_phone, message)

    async def notify_new_user_registration(
        self,
        user_email: str,
        user_name: str,
        user_role: str,
        college_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> None:
        """
        Send all configured notifications for new user registration.

        This is the main method to call when a new user signs up.
        It will send email, webhook, and WhatsApp notifications based on configuration.
        """
        # Send email notification
        try:
            await self.send_new_user_alert(
                user_email=user_email,
                user_name=user_name,
                user_role=user_role,
                college_name=college_name,
                phone=phone
            )
        except Exception as e:
            logger.error(f"[Notification] Failed to send email alert: {e}")

        # Send webhook notification if configured
        webhook_url = getattr(settings, 'NEW_USER_WEBHOOK_URL', None)
        if webhook_url:
            try:
                message = f"""
**New User Registered**
- **Name:** {user_name}
- **Email:** {user_email}
- **Role:** {user_role}
{f'- **Phone:** {phone}' if phone else ''}
{f'- **College:** {college_name}' if college_name else ''}
- **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
                """.strip()

                await self.send_webhook_notification(
                    webhook_url=webhook_url,
                    message=message,
                    title="New User Signup"
                )
            except Exception as e:
                logger.error(f"[Notification] Failed to send webhook alert: {e}")

        # Send WhatsApp notification if configured
        admin_whatsapp = getattr(settings, 'ADMIN_WHATSAPP_NUMBER', None)
        if admin_whatsapp:
            try:
                await self.send_whatsapp_new_user_alert(
                    user_email=user_email,
                    user_name=user_name,
                    user_role=user_role,
                    college_name=college_name,
                    phone=phone
                )
            except Exception as e:
                logger.error(f"[Notification] Failed to send WhatsApp alert: {e}")


    async def get_notification_settings_from_db(self) -> dict:
        """
        Fetch notification settings from database.
        Falls back to .env settings if database is not available.
        """
        try:
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker
            from app.models import SystemSetting
            from app.core.config import settings as app_settings

            engine = create_async_engine(app_settings.DATABASE_URL)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                result = await session.execute(
                    select(SystemSetting).where(SystemSetting.category == "notifications")
                )
                db_settings = {}
                for setting in result.scalars().all():
                    key = setting.key.replace("notifications.", "")
                    db_settings[key] = setting.value

                await engine.dispose()
                return db_settings

        except Exception as e:
            logger.warning(f"[Notification] Could not fetch DB settings, using .env: {e}")
            return {}

    async def send_whatsapp_notification_with_settings(
        self,
        to_phone: str,
        message: str,
        settings_dict: dict
    ) -> bool:
        """Send WhatsApp notification using provided settings dict"""
        provider = settings_dict.get("whatsapp_provider", "exotel")

        if provider == "exotel":
            sid = settings_dict.get("exotel_sid")
            token = settings_dict.get("exotel_token")
            from_number = settings_dict.get("exotel_whatsapp_number")

            if sid and token and from_number:
                return await self._send_whatsapp_exotel(to_phone, message, sid, token)

        elif provider == "twilio":
            sid = settings_dict.get("twilio_sid")
            token = settings_dict.get("twilio_token")
            from_number = settings_dict.get("twilio_whatsapp_number")

            if sid and token and from_number:
                return await self._send_whatsapp_twilio(to_phone, message, sid, token, from_number)

        logger.warning(f"[WhatsApp] Provider '{provider}' not properly configured")
        return False

    async def notify_new_user_registration_v2(
        self,
        user_email: str,
        user_name: str,
        user_role: str,
        college_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> None:
        """
        Send notifications using database-configured settings.
        This is the enhanced version that reads from admin settings.
        """
        # Fetch settings from database
        db_settings = await self.get_notification_settings_from_db()

        # Check if email notifications are enabled
        if db_settings.get("email_enabled", False):
            admin_email = db_settings.get("admin_email")
            if admin_email:
                try:
                    # Send to DB-configured admin email
                    await self.send_new_user_alert(
                        user_email=user_email,
                        user_name=user_name,
                        user_role=user_role,
                        college_name=college_name,
                        phone=phone
                    )
                    logger.info(f"[Notification] Email alert sent to {admin_email}")
                except Exception as e:
                    logger.error(f"[Notification] Failed to send email alert: {e}")

        # Check if WhatsApp notifications are enabled
        if db_settings.get("whatsapp_enabled", False):
            admin_whatsapp = db_settings.get("admin_whatsapp")
            if admin_whatsapp:
                try:
                    message = f"""🎉 New User Signup!

Name: {user_name}
Email: {user_email}
Role: {user_role}
{f'Phone: {phone}' if phone else ''}
{f'College: {college_name}' if college_name else ''}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC

Login to admin portal to view details."""

                    success = await self.send_whatsapp_notification_with_settings(
                        to_phone=admin_whatsapp,
                        message=message,
                        settings_dict=db_settings
                    )
                    if success:
                        logger.info(f"[Notification] WhatsApp alert sent to {admin_whatsapp}")
                except Exception as e:
                    logger.error(f"[Notification] Failed to send WhatsApp alert: {e}")

        # Check Slack webhook
        slack_webhook = db_settings.get("slack_webhook")
        if slack_webhook:
            try:
                message = f"*New User Registered*\n• Name: {user_name}\n• Email: {user_email}\n• Role: {user_role}"
                if phone:
                    message += f"\n• Phone: {phone}"
                if college_name:
                    message += f"\n• College: {college_name}"

                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(slack_webhook, json={"text": message})
                    logger.info("[Notification] Slack notification sent")
            except Exception as e:
                logger.error(f"[Notification] Failed to send Slack alert: {e}")

        # Check Discord webhook
        discord_webhook = db_settings.get("discord_webhook")
        if discord_webhook:
            try:
                message = f"**New User Registered**\n• Name: {user_name}\n• Email: {user_email}\n• Role: {user_role}"
                if phone:
                    message += f"\n• Phone: {phone}"
                if college_name:
                    message += f"\n• College: {college_name}"

                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(discord_webhook, json={"content": message})
                    logger.info("[Notification] Discord notification sent")
            except Exception as e:
                logger.error(f"[Notification] Failed to send Discord alert: {e}")


# Singleton instance
email_service = EmailService()


def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)
