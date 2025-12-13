"""
Email Service for BharatBuild AI
================================
Handles all email sending functionality including:
- Email verification on signup
- Password reset emails
- Purchase confirmations
- Notifications

Uses SMTP configuration from settings.
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime
import secrets

from app.core.config import settings
from app.core.logging_config import logger


class EmailService:
    """Async email service using SMTP"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME
        self.frontend_url = settings.FRONTEND_URL

    @property
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.smtp_user and self.smtp_password)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email asynchronously.

        Returns True if successful, False otherwise.
        """
        if not self.is_configured:
            logger.warning("[Email] SMTP not configured, skipping email send")
            return False

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

            logger.info(f"[Email] Successfully sent email to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"[Email] Failed to send email to {to_email}: {e}")
            return False

    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_token: str
    ) -> bool:
        """Send email verification link to new user"""
        verification_link = f"{self.frontend_url}/verify-email?token={verification_token}"

        subject = "Verify your email - BharatBuild AI"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .button:hover {{ background: #5a67d8; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to BharatBuild AI!</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name or 'there'},</p>
                    <p>Thanks for signing up for BharatBuild AI! Please verify your email address to get started.</p>
                    <p style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </p>
                    <p style="font-size: 14px; color: #6b7280;">
                        Or copy and paste this link in your browser:<br>
                        <code style="background: #e5e7eb; padding: 4px 8px; border-radius: 4px; word-break: break-all;">{verification_link}</code>
                    </p>
                    <p style="font-size: 14px; color: #6b7280;">This link will expire in 24 hours.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.utcnow().year} BharatBuild AI. All rights reserved.</p>
                    <p>If you didn't sign up for BharatBuild AI, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

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
        reset_link = f"{self.frontend_url}/reset-password?token={reset_token}"

        subject = "Reset your password - BharatBuild AI"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .warning {{ background: #fef3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name or 'there'},</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <div class="warning">
                        <strong>Security Notice:</strong> This link will expire in 1 hour. If you didn't request a password reset, please ignore this email and your password will remain unchanged.
                    </div>
                    <p style="font-size: 14px; color: #6b7280;">
                        Or copy and paste this link in your browser:<br>
                        <code style="background: #e5e7eb; padding: 4px 8px; border-radius: 4px; word-break: break-all;">{reset_link}</code>
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.utcnow().year} BharatBuild AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Password Reset Request

        Hi {user_name or 'there'},

        We received a request to reset your password. Click the link below to create a new password:

        {reset_link}

        This link will expire in 1 hour.

        If you didn't request a password reset, please ignore this email and your password will remain unchanged.

        - The BharatBuild AI Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_purchase_confirmation_email(
        self,
        to_email: str,
        user_name: str,
        plan_name: str,
        amount: int,  # in paise
        payment_id: str
    ) -> bool:
        """Send purchase confirmation email"""
        amount_display = f"₹{amount / 100:,.0f}"

        subject = f"Payment Confirmed - {plan_name} - BharatBuild AI"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .receipt {{ background: white; border: 1px solid #e5e7eb; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .receipt-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f3f4f6; }}
                .receipt-row:last-child {{ border-bottom: none; font-weight: 600; }}
                .button {{ display: inline-block; background: #10b981; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payment Successful!</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name or 'there'},</p>
                    <p>Thank you for your purchase! Your payment has been confirmed.</p>

                    <div class="receipt">
                        <h3 style="margin-top: 0;">Order Details</h3>
                        <div class="receipt-row">
                            <span>Plan</span>
                            <span>{plan_name}</span>
                        </div>
                        <div class="receipt-row">
                            <span>Amount Paid</span>
                            <span>{amount_display}</span>
                        </div>
                        <div class="receipt-row">
                            <span>Payment ID</span>
                            <span style="font-family: monospace;">{payment_id}</span>
                        </div>
                        <div class="receipt-row">
                            <span>Date</span>
                            <span>{datetime.utcnow().strftime('%B %d, %Y')}</span>
                        </div>
                    </div>

                    <p style="text-align: center;">
                        <a href="{self.frontend_url}/bolt" class="button">Start Building</a>
                    </p>

                    <p style="font-size: 14px; color: #6b7280;">
                        Need help? Reply to this email or visit our support page.
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.utcnow().year} BharatBuild AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Payment Successful!

        Hi {user_name or 'there'},

        Thank you for your purchase! Your payment has been confirmed.

        Order Details:
        - Plan: {plan_name}
        - Amount Paid: {amount_display}
        - Payment ID: {payment_id}
        - Date: {datetime.utcnow().strftime('%B %d, %Y')}

        Start building at: {self.frontend_url}/bolt

        - The BharatBuild AI Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str
    ) -> bool:
        """Send welcome email after verification"""
        subject = "Welcome to BharatBuild AI - Let's build something amazing!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .feature {{ background: white; border: 1px solid #e5e7eb; padding: 15px; border-radius: 8px; margin: 10px 0; }}
                .feature h4 {{ margin: 0 0 5px 0; color: #667eea; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to BharatBuild AI!</h1>
                    <p>Your AI-powered development partner</p>
                </div>
                <div class="content">
                    <p>Hi {user_name or 'there'},</p>
                    <p>Your email has been verified and your account is ready to go! Here's what you can do with BharatBuild AI:</p>

                    <div class="feature">
                        <h4>Generate Complete Projects</h4>
                        <p>Describe your idea and get a fully functional project with code, database schema, and APIs.</p>
                    </div>

                    <div class="feature">
                        <h4>AI-Powered Bug Fixing</h4>
                        <p>Let AI detect and fix errors in your code automatically.</p>
                    </div>

                    <div class="feature">
                        <h4>Complete Documentation</h4>
                        <p>Generate SRS, SDS, Project Reports, PPT, and Viva Q&A - perfect for students!</p>
                    </div>

                    <p style="text-align: center;">
                        <a href="{self.frontend_url}/bolt" class="button">Start Building Now</a>
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.utcnow().year} BharatBuild AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Welcome to BharatBuild AI!

        Hi {user_name or 'there'},

        Your email has been verified and your account is ready to go!

        Here's what you can do:
        - Generate Complete Projects: Describe your idea and get a fully functional project
        - AI-Powered Bug Fixing: Let AI detect and fix errors automatically
        - Complete Documentation: Generate SRS, SDS, Reports, PPT, and Viva Q&A

        Start building now: {self.frontend_url}/bolt

        - The BharatBuild AI Team
        """

        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()


def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)
