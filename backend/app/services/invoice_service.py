"""
Invoice Generation Service for BharatBuild AI
Generates professional PDF invoices for payments
"""

import io
from datetime import datetime
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import logging

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for generating professional PDF invoices"""

    def __init__(self):
        self.company_name = "BharatBuild AI"
        self.company_tagline = "AI-Powered Project Generation Platform"
        self.company_address_line1 = "Hyderabad, Telangana"
        self.company_address_line2 = "India - 500081"
        self.company_email = "support@bharatbuild.ai"
        self.company_website = "www.bharatbuild.ai"
        self.company_phone = "+91 9876543210"
        self.company_gstin = "36AABCU9603R1ZM"  # Update with actual GSTIN

    def generate_invoice_number(self, payment_id: str) -> str:
        """Generate a unique invoice number"""
        date_part = datetime.utcnow().strftime("%Y%m%d")
        unique_part = payment_id[-6:].upper() if payment_id else "000000"
        return f"BB-{date_part}-{unique_part}"

    def generate_invoice_pdf(
        self,
        invoice_number: str,
        customer_name: str,
        customer_email: str,
        customer_phone: Optional[str],
        plan_name: str,
        amount: int,  # in paise
        payment_id: str,
        payment_date: Optional[datetime] = None,
        customer_address: Optional[str] = None,
        customer_gstin: Optional[str] = None,
        college_name: Optional[str] = None
    ) -> bytes:
        """Generate a professional PDF invoice"""

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4  # 595.27, 841.89 points

        # Colors
        primary_color = colors.HexColor('#6366f1')  # Indigo
        secondary_color = colors.HexColor('#10b981')  # Green
        dark_color = colors.HexColor('#1f2937')
        gray_color = colors.HexColor('#6b7280')
        light_gray = colors.HexColor('#f3f4f6')
        border_color = colors.HexColor('#e5e7eb')

        payment_dt = payment_date or datetime.utcnow()

        # Calculate amounts
        amount_rupees = amount / 100
        base_amount = round(amount_rupees / 1.18, 2)
        gst_amount = round(amount_rupees - base_amount, 2)
        cgst = round(gst_amount / 2, 2)
        sgst = round(gst_amount / 2, 2)

        # ============ HEADER SECTION ============
        # Purple header bar
        c.setFillColor(primary_color)
        c.rect(0, height - 100, width, 100, fill=True, stroke=False)

        # Company name
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 28)
        c.drawString(40, height - 55, "BharatBuild AI")

        # Tagline
        c.setFont("Helvetica", 10)
        c.drawString(40, height - 72, self.company_tagline)

        # TAX INVOICE label
        c.setFont("Helvetica-Bold", 18)
        c.drawRightString(width - 40, height - 50, "TAX INVOICE")

        # Invoice number below
        c.setFont("Helvetica", 11)
        c.drawRightString(width - 40, height - 70, f"#{invoice_number}")

        # ============ INVOICE INFO BAR ============
        y_pos = height - 130

        # Light gray info bar
        c.setFillColor(light_gray)
        c.rect(30, y_pos - 35, width - 60, 40, fill=True, stroke=False)

        c.setFillColor(dark_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(45, y_pos - 12, "INVOICE DATE")
        c.drawString(200, y_pos - 12, "DUE DATE")
        c.drawString(355, y_pos - 12, "PAYMENT STATUS")

        c.setFont("Helvetica", 10)
        c.drawString(45, y_pos - 27, payment_dt.strftime('%d %B %Y'))
        c.drawString(200, y_pos - 27, "PAID")

        # Payment status badge
        c.setFillColor(secondary_color)
        c.roundRect(355, y_pos - 32, 50, 18, 3, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(367, y_pos - 26, "PAID")

        # ============ BILLING DETAILS ============
        y_pos = height - 200

        # FROM section
        c.setFillColor(gray_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y_pos, "FROM")

        c.setFillColor(dark_color)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y_pos - 18, self.company_name)

        c.setFont("Helvetica", 10)
        c.setFillColor(gray_color)
        c.drawString(40, y_pos - 33, self.company_address_line1)
        c.drawString(40, y_pos - 46, self.company_address_line2)
        c.drawString(40, y_pos - 59, f"Email: {self.company_email}")
        c.drawString(40, y_pos - 72, f"GSTIN: {self.company_gstin}")

        # BILL TO section
        c.setFillColor(gray_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(320, y_pos, "BILL TO")

        c.setFillColor(dark_color)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(320, y_pos - 18, customer_name or "Customer")

        c.setFont("Helvetica", 10)
        c.setFillColor(gray_color)
        bill_y = y_pos - 33

        if college_name:
            c.drawString(320, bill_y, college_name)
            bill_y -= 13
        if customer_address:
            c.drawString(320, bill_y, customer_address)
            bill_y -= 13
        c.drawString(320, bill_y, f"Email: {customer_email}")
        bill_y -= 13
        if customer_phone:
            c.drawString(320, bill_y, f"Phone: {customer_phone}")
            bill_y -= 13
        if customer_gstin:
            c.drawString(320, bill_y, f"GSTIN: {customer_gstin}")

        # ============ ITEMS TABLE ============
        y_pos = height - 320

        # Table header
        c.setFillColor(primary_color)
        c.rect(30, y_pos - 5, width - 60, 28, fill=True, stroke=False)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(45, y_pos + 5, "#")
        c.drawString(70, y_pos + 5, "DESCRIPTION")
        c.drawString(320, y_pos + 5, "HSN/SAC")
        c.drawString(400, y_pos + 5, "QTY")
        c.drawString(450, y_pos + 5, "RATE")
        c.drawRightString(width - 45, y_pos + 5, "AMOUNT")

        # Table row
        y_pos -= 35
        c.setFillColor(light_gray)
        c.rect(30, y_pos - 10, width - 60, 35, fill=True, stroke=False)

        c.setFillColor(dark_color)
        c.setFont("Helvetica", 10)
        c.drawString(45, y_pos + 5, "1")
        c.drawString(70, y_pos + 5, f"{plan_name} Subscription")
        c.setFont("Helvetica", 9)
        c.setFillColor(gray_color)
        c.drawString(70, y_pos - 8, "AI-Powered Project Generation Platform")

        c.setFillColor(dark_color)
        c.setFont("Helvetica", 10)
        c.drawString(320, y_pos + 5, "998314")
        c.drawString(405, y_pos + 5, "1")
        c.drawString(450, y_pos + 5, f"{base_amount:,.2f}")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width - 45, y_pos + 5, f"{base_amount:,.2f}")

        # ============ TOTALS SECTION ============
        y_pos -= 60

        # Subtotal
        c.setFillColor(gray_color)
        c.setFont("Helvetica", 10)
        c.drawString(380, y_pos, "Subtotal")
        c.setFillColor(dark_color)
        c.drawRightString(width - 45, y_pos, f"{base_amount:,.2f}")

        # CGST
        y_pos -= 18
        c.setFillColor(gray_color)
        c.drawString(380, y_pos, "CGST (9%)")
        c.setFillColor(dark_color)
        c.drawRightString(width - 45, y_pos, f"{cgst:,.2f}")

        # SGST
        y_pos -= 18
        c.setFillColor(gray_color)
        c.drawString(380, y_pos, "SGST (9%)")
        c.setFillColor(dark_color)
        c.drawRightString(width - 45, y_pos, f"{sgst:,.2f}")

        # Divider line
        y_pos -= 15
        c.setStrokeColor(border_color)
        c.setLineWidth(1)
        c.line(380, y_pos, width - 40, y_pos)

        # Total
        y_pos -= 25
        c.setFillColor(dark_color)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(380, y_pos, "Total (INR)")
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(width - 45, y_pos, f"₹ {amount_rupees:,.2f}")

        # ============ AMOUNT IN WORDS ============
        y_pos -= 50
        amount_words = self._amount_to_words(int(amount_rupees))

        c.setFillColor(light_gray)
        c.roundRect(30, y_pos - 15, width - 60, 35, 5, fill=True, stroke=False)

        c.setFillColor(gray_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(45, y_pos + 5, "AMOUNT IN WORDS")

        c.setFillColor(dark_color)
        c.setFont("Helvetica", 10)
        c.drawString(45, y_pos - 8, f"Indian Rupees {amount_words} Only")

        # ============ PAYMENT INFO ============
        y_pos -= 60

        c.setFillColor(gray_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y_pos, "PAYMENT INFORMATION")

        y_pos -= 18
        c.setFont("Helvetica", 10)
        c.setFillColor(dark_color)
        c.drawString(40, y_pos, f"Payment ID: {payment_id}")
        c.drawString(280, y_pos, f"Payment Method: Online (Razorpay)")

        y_pos -= 15
        c.drawString(40, y_pos, f"Transaction Date: {payment_dt.strftime('%d %B %Y, %I:%M %p')}")

        # ============ TERMS & NOTES ============
        y_pos -= 50

        c.setFillColor(gray_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y_pos, "TERMS & CONDITIONS")

        c.setFont("Helvetica", 8)
        terms = [
            "1. This is a computer-generated invoice and does not require a physical signature.",
            "2. Payment has been received. No further action required.",
            "3. For any queries regarding this invoice, please contact support@bharatbuild.ai",
            "4. Services are subject to our Terms of Service available at bharatbuild.ai/terms"
        ]

        y_pos -= 15
        for term in terms:
            c.drawString(40, y_pos, term)
            y_pos -= 12

        # ============ FOOTER ============
        # Footer bar
        c.setFillColor(primary_color)
        c.rect(0, 0, width, 50, fill=True, stroke=False)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width / 2, 30, "Thank you for choosing BharatBuild AI!")

        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2, 15, f"{self.company_website}  |  {self.company_email}  |  {self.company_phone}")

        # ============ WATERMARK (Paid stamp) ============
        c.saveState()
        c.setFillColor(colors.Color(0.1, 0.7, 0.5, alpha=0.15))
        c.setFont("Helvetica-Bold", 60)
        c.translate(width / 2, height / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, "PAID")
        c.restoreState()

        # Save PDF
        c.save()

        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(f"[Invoice] Generated invoice {invoice_number} for {customer_email}")

        return pdf_bytes

    def _amount_to_words(self, amount: int) -> str:
        """Convert amount to words (Indian numbering system)"""
        if amount == 0:
            return "Zero"

        ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
                'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
                'Seventeen', 'Eighteen', 'Nineteen']
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

        def two_digits(n):
            if n < 20:
                return ones[n]
            return tens[n // 10] + ('' if n % 10 == 0 else ' ' + ones[n % 10])

        def three_digits(n):
            if n < 100:
                return two_digits(n)
            return ones[n // 100] + ' Hundred' + ('' if n % 100 == 0 else ' and ' + two_digits(n % 100))

        if amount >= 10000000:  # Crore
            crore = amount // 10000000
            remainder = amount % 10000000
            result = three_digits(crore) + ' Crore'
            if remainder:
                result += ' ' + self._amount_to_words(remainder)
            return result

        if amount >= 100000:  # Lakh
            lakh = amount // 100000
            remainder = amount % 100000
            result = two_digits(lakh) + ' Lakh'
            if remainder:
                result += ' ' + self._amount_to_words(remainder)
            return result

        if amount >= 1000:  # Thousand
            thousand = amount // 1000
            remainder = amount % 1000
            result = two_digits(thousand) + ' Thousand'
            if remainder:
                result += ' ' + three_digits(remainder)
            return result

        return three_digits(amount)


# Global instance
invoice_service = InvoiceService()
