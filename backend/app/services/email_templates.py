"""
BharatBuild AI - Clean Email Templates
"""

from datetime import datetime
from typing import Optional


def verification_email(user_name: str, verification_link: str, frontend_url: str) -> str:
    """Email verification - clean and simple"""
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
                        <td style="background-color:#6366f1; padding:25px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:22px;">BharatBuild AI</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px;">
                            <h2 style="color:#333333; margin:0 0 15px 0; font-size:18px;">Verify Your Email</h2>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 20px 0;">
                                Hi {user_name or 'there'},
                            </p>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 25px 0;">
                                Thank you for signing up! Please click the button below to verify your email address and activate your account.
                            </p>

                            <!-- Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding:10px 0 25px 0;">
                                        <a href="{verification_link}" style="background-color:#6366f1; color:#ffffff; text-decoration:none; padding:12px 30px; border-radius:5px; font-size:14px; font-weight:bold; display:inline-block;">Verify Email</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="color:#888888; font-size:12px; line-height:18px; margin:0 0 15px 0;">
                                Or copy this link into your browser:
                            </p>
                            <p style="color:#6366f1; font-size:12px; word-break:break-all; margin:0 0 20px 0;">
                                {verification_link}
                            </p>

                            <p style="color:#888888; font-size:12px; margin:0;">
                                This link expires in 24 hours. If you didn't sign up, ignore this email.
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


def welcome_email(user_name: str, frontend_url: str) -> str:
    """Welcome email after verification"""
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
                        <td style="background-color:#6366f1; padding:25px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:22px;">Welcome to BharatBuild AI!</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px;">
                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 20px 0;">
                                Hi {user_name or 'there'},
                            </p>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 20px 0;">
                                Your account is now active! You're ready to start building amazing projects with AI.
                            </p>

                            <h3 style="color:#333333; font-size:15px; margin:25px 0 15px 0;">What you can do:</h3>

                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                                <tr>
                                    <td style="padding:12px; background-color:#f8f9fa; border-radius:5px; margin-bottom:10px;">
                                        <p style="color:#333333; font-size:14px; font-weight:bold; margin:0 0 5px 0;">Generate Projects</p>
                                        <p style="color:#666666; font-size:13px; margin:0;">Describe your idea and get complete working code</p>
                                    </td>
                                </tr>
                            </table>

                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                                <tr>
                                    <td style="padding:12px; background-color:#f8f9fa; border-radius:5px;">
                                        <p style="color:#333333; font-size:14px; font-weight:bold; margin:0 0 5px 0;">AI Bug Fixing</p>
                                        <p style="color:#666666; font-size:13px; margin:0;">Let AI detect and fix errors automatically</p>
                                    </td>
                                </tr>
                            </table>

                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:25px;">
                                <tr>
                                    <td style="padding:12px; background-color:#f8f9fa; border-radius:5px;">
                                        <p style="color:#333333; font-size:14px; font-weight:bold; margin:0 0 5px 0;">Documentation</p>
                                        <p style="color:#666666; font-size:13px; margin:0;">Generate SRS, reports, PPT and viva Q&A</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding:10px 0;">
                                        <a href="{frontend_url}/build" style="background-color:#6366f1; color:#ffffff; text-decoration:none; padding:12px 30px; border-radius:5px; font-size:14px; font-weight:bold; display:inline-block;">Start Building</a>
                                    </td>
                                </tr>
                            </table>
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


def password_reset_email(user_name: str, reset_link: str, frontend_url: str) -> str:
    """Password reset email"""
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
                        <td style="background-color:#6366f1; padding:25px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:22px;">BharatBuild AI</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px;">
                            <h2 style="color:#333333; margin:0 0 15px 0; font-size:18px;">Reset Your Password</h2>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 20px 0;">
                                Hi {user_name or 'there'},
                            </p>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 25px 0;">
                                We received a request to reset your password. Click the button below to create a new password.
                            </p>

                            <!-- Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding:10px 0 25px 0;">
                                        <a href="{reset_link}" style="background-color:#6366f1; color:#ffffff; text-decoration:none; padding:12px 30px; border-radius:5px; font-size:14px; font-weight:bold; display:inline-block;">Reset Password</a>
                                    </td>
                                </tr>
                            </table>

                            <!-- Warning -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                                <tr>
                                    <td style="padding:12px; background-color:#fff8e6; border-left:3px solid #f59e0b; border-radius:3px;">
                                        <p style="color:#92400e; font-size:13px; margin:0;">
                                            <strong>Note:</strong> This link expires in 1 hour. If you didn't request this, please ignore this email.
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <p style="color:#888888; font-size:12px; line-height:18px; margin:0 0 10px 0;">
                                Or copy this link:
                            </p>
                            <p style="color:#6366f1; font-size:12px; word-break:break-all; margin:0;">
                                {reset_link}
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


def purchase_confirmation_email(
    user_name: str,
    plan_name: str,
    amount_display: str,
    payment_id: str,
    frontend_url: str,
    invoice_number: Optional[str] = None
) -> str:
    """Payment success email with invoice"""
    date = datetime.utcnow().strftime('%d %b %Y')

    invoice_row = f'''
                                            <tr>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                                                    <span style="color:#666666; font-size:13px;">Invoice No.</span>
                                                </td>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                                                    <span style="color:#6366f1; font-size:13px; font-weight:bold;">{invoice_number}</span>
                                                </td>
                                            </tr>''' if invoice_number else ''

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
                        <td style="background-color:#10b981; padding:25px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:22px;">Payment Successful!</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px;">
                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 20px 0;">
                                Hi {user_name or 'there'},
                            </p>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 25px 0;">
                                Thank you for your purchase! Your payment has been confirmed and your account has been upgraded.
                            </p>

                            <!-- Order Details -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8f9fa; border-radius:5px; margin-bottom:25px;">
                                <tr>
                                    <td style="padding:20px;">
                                        <h3 style="color:#333333; font-size:14px; margin:0 0 15px 0;">Order Details</h3>

                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            {invoice_row}
                                            <tr>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                                                    <span style="color:#666666; font-size:13px;">Plan</span>
                                                </td>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                                                    <span style="color:#333333; font-size:13px; font-weight:bold;">{plan_name}</span>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                                                    <span style="color:#666666; font-size:13px;">Amount</span>
                                                </td>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                                                    <span style="color:#10b981; font-size:13px; font-weight:bold;">{amount_display}</span>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                                                    <span style="color:#666666; font-size:13px;">Payment ID</span>
                                                </td>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                                                    <span style="color:#333333; font-size:12px;">{payment_id}</span>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding:8px 0;">
                                                    <span style="color:#666666; font-size:13px;">Date</span>
                                                </td>
                                                <td style="padding:8px 0; text-align:right;">
                                                    <span style="color:#333333; font-size:13px;">{date}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- Invoice Notice -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f9ff; border-radius:5px; margin-bottom:25px; border:1px solid #bfdbfe;">
                                <tr>
                                    <td style="padding:15px; text-align:center;">
                                        <p style="color:#1e40af; font-size:13px; margin:0;">
                                            Your tax invoice is attached to this email as a PDF.
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding:10px 0;">
                                        <a href="{frontend_url}/build" style="background-color:#10b981; color:#ffffff; text-decoration:none; padding:12px 30px; border-radius:5px; font-size:14px; font-weight:bold; display:inline-block;">Start Building</a>
                                    </td>
                                </tr>
                            </table>

                            <p style="color:#888888; font-size:12px; text-align:center; margin:20px 0 0 0;">
                                Questions? Email us at support@bharatbuild.ai
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


def new_user_alert_email(
    user_name: str,
    user_email: str,
    user_role: str,
    phone: Optional[str],
    college_name: Optional[str],
    frontend_url: str
) -> str:
    """Admin alert for new user signup"""
    timestamp = datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')

    phone_row = f'''
        <tr>
            <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                <span style="color:#666666; font-size:13px;">Phone</span>
            </td>
            <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                <span style="color:#333333; font-size:13px;">{phone}</span>
            </td>
        </tr>
    ''' if phone else ''

    college_row = f'''
        <tr>
            <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                <span style="color:#666666; font-size:13px;">College</span>
            </td>
            <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                <span style="color:#333333; font-size:13px;">{college_name}</span>
            </td>
        </tr>
    ''' if college_name else ''

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
                        <td style="background-color:#10b981; padding:25px; text-align:center;">
                            <p style="color:#ffffff; font-size:12px; margin:0 0 5px 0; text-transform:uppercase; letter-spacing:1px;">New User</p>
                            <h1 style="color:#ffffff; margin:0; font-size:20px;">Registration Alert</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px;">
                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 20px 0;">
                                A new user has signed up on BharatBuild AI.
                            </p>

                            <!-- User Details -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8f9fa; border-radius:5px; margin-bottom:25px;">
                                <tr>
                                    <td style="padding:20px;">
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                                                    <span style="color:#666666; font-size:13px;">Name</span>
                                                </td>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                                                    <span style="color:#333333; font-size:13px; font-weight:bold;">{user_name}</span>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                                                    <span style="color:#666666; font-size:13px;">Email</span>
                                                </td>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                                                    <span style="color:#333333; font-size:13px;">{user_email}</span>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee;">
                                                    <span style="color:#666666; font-size:13px;">Role</span>
                                                </td>
                                                <td style="padding:8px 0; border-bottom:1px solid #eeeeee; text-align:right;">
                                                    <span style="color:#333333; font-size:13px;">{user_role}</span>
                                                </td>
                                            </tr>
                                            {phone_row}
                                            {college_row}
                                            <tr>
                                                <td style="padding:8px 0;">
                                                    <span style="color:#666666; font-size:13px;">Time</span>
                                                </td>
                                                <td style="padding:8px 0; text-align:right;">
                                                    <span style="color:#333333; font-size:13px;">{timestamp}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center">
                                        <a href="{frontend_url}/admin/users" style="background-color:#6366f1; color:#ffffff; text-decoration:none; padding:12px 30px; border-radius:5px; font-size:14px; font-weight:bold; display:inline-block;">View in Admin</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8f9fa; padding:20px; text-align:center; border-top:1px solid #eeeeee;">
                            <p style="color:#888888; font-size:11px; margin:0;">
                                Automated notification from BharatBuild AI
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''


def test_notification_email(admin_email: str, timestamp: str) -> str:
    """Test notification email"""
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
                        <td style="background-color:#6366f1; padding:25px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:22px;">BharatBuild AI</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:30px; text-align:center;">
                            <div style="background-color:#d1fae5; color:#065f46; padding:10px 20px; border-radius:20px; display:inline-block; font-size:13px; font-weight:bold; margin-bottom:20px;">
                                Email Working
                            </div>

                            <h2 style="color:#333333; margin:0 0 15px 0; font-size:18px;">Test Successful!</h2>

                            <p style="color:#555555; font-size:14px; line-height:22px; margin:0 0 25px 0;">
                                Your email configuration is working correctly.
                            </p>

                            <!-- Details -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8f9fa; border-radius:5px; text-align:left;">
                                <tr>
                                    <td style="padding:15px;">
                                        <p style="color:#666666; font-size:13px; margin:0 0 8px 0;">
                                            <strong>To:</strong> {admin_email}
                                        </p>
                                        <p style="color:#666666; font-size:13px; margin:0 0 8px 0;">
                                            <strong>Time:</strong> {timestamp}
                                        </p>
                                        <p style="color:#666666; font-size:13px; margin:0;">
                                            <strong>Provider:</strong> Resend
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f8f9fa; padding:20px; text-align:center; border-top:1px solid #eeeeee;">
                            <p style="color:#888888; font-size:11px; margin:0;">
                                © {datetime.utcnow().year} BharatBuild AI
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''
