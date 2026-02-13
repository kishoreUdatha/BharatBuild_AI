"""
Certificate Service - Generate learning certificates for students who complete checkpoints
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import io
import os

from app.core.logging_config import logger


class CertificateService:
    """Generate PDF learning certificates for completed projects"""

    CERTIFICATE_TEMPLATE = """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                              ║
    ║                         BHARATBUILD LEARNING CERTIFICATE                     ║
    ║                                                                              ║
    ║                        Certificate of Understanding                          ║
    ║                                                                              ║
    ╠══════════════════════════════════════════════════════════════════════════════╣
    ║                                                                              ║
    ║   This is to certify that                                                    ║
    ║                                                                              ║
    ║                           {student_name}                                     ║
    ║                                                                              ║
    ║   has successfully demonstrated understanding of the project:                ║
    ║                                                                              ║
    ║                           {project_title}                                    ║
    ║                                                                              ║
    ║   ───────────────────────────────────────────────────────────────────────    ║
    ║                                                                              ║
    ║   LEARNING ACHIEVEMENTS:                                                     ║
    ║                                                                              ║
    ║   ✓ Code Understanding          - {files_reviewed} files reviewed            ║
    ║   ✓ Concept Quiz Score          - {quiz_score}%                              ║
    ║   ✓ Viva Questions Reviewed     - {viva_reviewed} questions                  ║
    ║                                                                              ║
    ║   ───────────────────────────────────────────────────────────────────────    ║
    ║                                                                              ║
    ║   Technology Stack: {tech_stack}                                             ║
    ║   Domain: {domain}                                                           ║
    ║                                                                              ║
    ║   ───────────────────────────────────────────────────────────────────────    ║
    ║                                                                              ║
    ║   Certificate ID: {certificate_id}                                           ║
    ║   Issued On: {issue_date}                                                    ║
    ║                                                                              ║
    ║   Verify at: https://bharatbuild.ai/verify/{certificate_id}                  ║
    ║                                                                              ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """

    def __init__(self):
        pass

    def generate_certificate_id(self) -> str:
        """Generate a unique certificate ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_part = str(uuid.uuid4())[:8].upper()
        return f"BB-CERT-{timestamp}-{unique_part}"

    async def generate_certificate(
        self,
        student_name: str,
        student_email: str,
        project_title: str,
        project_domain: str,
        tech_stack: list,
        quiz_score: float,
        quiz_attempts: int,
        files_reviewed: int,
        viva_questions_reviewed: int,
        certificate_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a learning certificate.

        Args:
            student_name: Name of the student
            student_email: Email of the student
            project_title: Title of the project
            project_domain: Domain/category of the project
            tech_stack: List of technologies used
            quiz_score: Quiz score percentage
            quiz_attempts: Number of quiz attempts
            files_reviewed: Number of files reviewed
            viva_questions_reviewed: Number of viva Q&A reviewed

        Returns:
            Dict with certificate data and content
        """
        try:
            # Generate certificate ID if not provided
            if not certificate_id:
                certificate_id = self.generate_certificate_id()

            # Format tech stack
            tech_stack_str = ", ".join(tech_stack[:5]) if tech_stack else "Full Stack"
            if len(tech_stack) > 5:
                tech_stack_str += f" +{len(tech_stack) - 5} more"

            # Format issue date
            issue_date = datetime.utcnow().strftime("%B %d, %Y")

            # Generate text certificate
            text_content = self.CERTIFICATE_TEMPLATE.format(
                student_name=student_name.center(40),
                project_title=project_title[:50].center(40),
                files_reviewed=str(files_reviewed).rjust(3),
                quiz_score=f"{quiz_score:.1f}".rjust(5),
                viva_reviewed=str(viva_questions_reviewed).rjust(3),
                tech_stack=tech_stack_str[:60],
                domain=project_domain[:40] if project_domain else "Web Application",
                certificate_id=certificate_id,
                issue_date=issue_date
            )

            # Generate PDF if reportlab is available
            pdf_content = await self._generate_pdf_certificate(
                student_name=student_name,
                student_email=student_email,
                project_title=project_title,
                project_domain=project_domain,
                tech_stack=tech_stack,
                quiz_score=quiz_score,
                quiz_attempts=quiz_attempts,
                files_reviewed=files_reviewed,
                viva_questions_reviewed=viva_questions_reviewed,
                certificate_id=certificate_id,
                issue_date=issue_date
            )

            return {
                "success": True,
                "certificate_id": certificate_id,
                "text_content": text_content,
                "pdf_content": pdf_content,
                "metadata": {
                    "student_name": student_name,
                    "student_email": student_email,
                    "project_title": project_title,
                    "project_domain": project_domain,
                    "tech_stack": tech_stack,
                    "quiz_score": quiz_score,
                    "quiz_attempts": quiz_attempts,
                    "files_reviewed": files_reviewed,
                    "viva_questions_reviewed": viva_questions_reviewed,
                    "issued_at": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"[CertificateService] Error generating certificate: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_pdf_certificate(
        self,
        student_name: str,
        student_email: str,
        project_title: str,
        project_domain: str,
        tech_stack: list,
        quiz_score: float,
        quiz_attempts: int,
        files_reviewed: int,
        viva_questions_reviewed: int,
        certificate_id: str,
        issue_date: str
    ) -> Optional[bytes]:
        """Generate PDF certificate using reportlab"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib.enums import TA_CENTER, TA_LEFT

            # Create PDF buffer
            buffer = io.BytesIO()

            # Use landscape A4
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=1*cm,
                bottomMargin=1*cm
            )

            # Styles
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CertTitle',
                parent=styles['Heading1'],
                fontSize=28,
                textColor=colors.HexColor('#1a365d'),
                alignment=TA_CENTER,
                spaceAfter=10
            )

            subtitle_style = ParagraphStyle(
                'CertSubtitle',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#4a5568'),
                alignment=TA_CENTER,
                spaceAfter=20
            )

            name_style = ParagraphStyle(
                'StudentName',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2d3748'),
                alignment=TA_CENTER,
                spaceBefore=10,
                spaceAfter=10
            )

            project_style = ParagraphStyle(
                'ProjectTitle',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=colors.HexColor('#3182ce'),
                alignment=TA_CENTER,
                spaceBefore=10,
                spaceAfter=20
            )

            body_style = ParagraphStyle(
                'CertBody',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#4a5568'),
                alignment=TA_CENTER,
                spaceAfter=6
            )

            small_style = ParagraphStyle(
                'CertSmall',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#718096'),
                alignment=TA_CENTER,
                spaceAfter=4
            )

            # Build content
            content = []

            # Header
            content.append(Paragraph("BHARATBUILD", title_style))
            content.append(Paragraph("Certificate of Understanding", subtitle_style))
            content.append(Spacer(1, 20))

            # Certificate text
            content.append(Paragraph("This is to certify that", body_style))
            content.append(Spacer(1, 10))
            content.append(Paragraph(f"<b>{student_name}</b>", name_style))
            content.append(Spacer(1, 10))
            content.append(Paragraph("has successfully demonstrated understanding of the project:", body_style))
            content.append(Spacer(1, 10))
            content.append(Paragraph(f"<b>{project_title}</b>", project_style))
            content.append(Spacer(1, 20))

            # Learning Achievements Table
            achievements_data = [
                ['Learning Achievement', 'Result'],
                ['Code Understanding', f'{files_reviewed} files reviewed'],
                ['Concept Quiz Score', f'{quiz_score:.1f}%'],
                ['Quiz Attempts', f'{quiz_attempts} attempt(s)'],
                ['Viva Questions Reviewed', f'{viva_questions_reviewed} questions'],
            ]

            achievements_table = Table(achievements_data, colWidths=[3*inch, 2.5*inch])
            achievements_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#4a5568')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))

            content.append(achievements_table)
            content.append(Spacer(1, 20))

            # Tech Stack
            tech_str = ", ".join(tech_stack[:6]) if tech_stack else "Full Stack"
            content.append(Paragraph(f"<b>Technology Stack:</b> {tech_str}", body_style))
            content.append(Paragraph(f"<b>Domain:</b> {project_domain or 'Web Application'}", body_style))
            content.append(Spacer(1, 30))

            # Certificate ID and verification
            content.append(Paragraph(f"Certificate ID: <b>{certificate_id}</b>", small_style))
            content.append(Paragraph(f"Issued On: {issue_date}", small_style))
            content.append(Spacer(1, 10))
            content.append(Paragraph(
                f"Verify this certificate at: <font color='#3182ce'>https://bharatbuild.ai/verify/{certificate_id}</font>",
                small_style
            ))

            # Build PDF
            doc.build(content)

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            return pdf_bytes

        except ImportError:
            logger.warning("[CertificateService] reportlab not installed, skipping PDF generation")
            return None
        except Exception as e:
            logger.error(f"[CertificateService] Error generating PDF: {e}", exc_info=True)
            return None

    async def verify_certificate(self, certificate_id: str) -> Dict[str, Any]:
        """
        Verify a certificate by its ID.

        Args:
            certificate_id: The unique certificate ID

        Returns:
            Dict with verification status and certificate details
        """
        # In production, this would query the database
        # For now, return a structure that indicates what verification would look like
        return {
            "valid": True,  # Would be based on database lookup
            "certificate_id": certificate_id,
            "message": "Certificate verification requires database lookup"
        }

    def generate_certificate_filename(self, project_title: str, student_name: str) -> str:
        """Generate a safe filename for the certificate"""
        # Clean project title
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in project_title)
        safe_title = safe_title.replace(' ', '_')[:30]

        # Clean student name
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in student_name)
        safe_name = safe_name.replace(' ', '_')[:20]

        timestamp = datetime.utcnow().strftime("%Y%m%d")

        return f"LEARNING_CERTIFICATE_{safe_title}_{safe_name}_{timestamp}.pdf"


# Singleton instance
certificate_service = CertificateService()
