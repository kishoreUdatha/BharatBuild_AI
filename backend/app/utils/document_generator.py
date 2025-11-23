from typing import Optional, Dict, Any
from pathlib import Path
import io
import zipfile
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pptx import Presentation
from pptx.util import Inches as PptInches, Pt as PptPt
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from datetime import datetime

from app.core.config import settings
from app.core.logging_config import logger


class DocumentGenerator:
    """Generate various document formats (DOCX, PPTX, PDF)"""

    def __init__(self):
        self.temp_dir = settings.TEMP_DIR

    def generate_srs_docx(
        self,
        content: str,
        project_title: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate SRS document in DOCX format

        Args:
            content: SRS content
            project_title: Project title
            output_path: Output file path

        Returns:
            Path to generated document
        """
        if output_path is None:
            output_path = self.temp_dir / f"SRS_{project_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        doc = Document()

        # Title
        title = doc.add_heading(f'Software Requirements Specification', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Project Title
        subtitle = doc.add_heading(project_title, 1)
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Date
        date_para = doc.add_paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}")
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_page_break()

        # Parse and add content
        sections = content.split('\n\n')
        for section in sections:
            if section.strip():
                if section.startswith('#'):
                    # Heading
                    level = section.count('#', 0, 3)
                    text = section.lstrip('#').strip()
                    doc.add_heading(text, level)
                else:
                    # Paragraph
                    doc.add_paragraph(section.strip())

        doc.save(str(output_path))
        logger.info(f"Generated SRS DOCX: {output_path}")
        return str(output_path)

    def generate_report_docx(
        self,
        content: str,
        project_title: str,
        output_path: Optional[str] = None
    ) -> str:
        """Generate project report in DOCX format"""
        if output_path is None:
            output_path = self.temp_dir / f"Report_{project_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        doc = Document()

        # Title Page
        title = doc.add_heading('PROJECT REPORT', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        project_title_para = doc.add_heading(project_title, 1)
        project_title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph()

        submitted_by = doc.add_paragraph('Submitted By:')
        submitted_by.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        date_para = doc.add_paragraph(f"{datetime.now().strftime('%B %Y')}")
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_page_break()

        # Table of Contents placeholder
        doc.add_heading('Table of Contents', 1)
        doc.add_paragraph('(Auto-generated table of contents)')
        doc.add_page_break()

        # Content
        sections = content.split('\n\n')
        for section in sections:
            if section.strip():
                if section.startswith('#'):
                    level = min(section.count('#', 0, 3), 2)
                    text = section.lstrip('#').strip()
                    doc.add_heading(text, level)
                else:
                    doc.add_paragraph(section.strip())

        doc.save(str(output_path))
        logger.info(f"Generated Report DOCX: {output_path}")
        return str(output_path)

    def generate_ppt(
        self,
        slides_content: list,
        project_title: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate PowerPoint presentation

        Args:
            slides_content: List of dicts with 'title' and 'content'
            project_title: Project title
            output_path: Output file path

        Returns:
            Path to generated presentation
        """
        if output_path is None:
            output_path = self.temp_dir / f"Presentation_{project_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"

        prs = Presentation()
        prs.slide_width = PptInches(10)
        prs.slide_height = PptInches(7.5)

        # Title Slide
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        title.text = project_title
        subtitle.text = f"Generated on {datetime.now().strftime('%B %d, %Y')}"

        # Content Slides
        for slide_data in slides_content:
            bullet_slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(bullet_slide_layout)

            shapes = slide.shapes
            title_shape = shapes.title
            body_shape = shapes.placeholders[1]

            title_shape.text = slide_data.get('title', 'Untitled')

            tf = body_shape.text_frame
            content = slide_data.get('content', '')

            if isinstance(content, list):
                for item in content:
                    p = tf.add_paragraph()
                    p.text = str(item)
                    p.level = 0
            else:
                tf.text = str(content)

        prs.save(str(output_path))
        logger.info(f"Generated PPT: {output_path}")
        return str(output_path)

    def generate_pdf(
        self,
        content: str,
        project_title: str,
        output_path: Optional[str] = None
    ) -> str:
        """Generate PDF document"""
        if output_path is None:
            output_path = self.temp_dir / f"Document_{project_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=RGBColor(0, 0, 139),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        story.append(Paragraph(project_title, title_style))
        story.append(Spacer(1, 0.2*inch))

        # Content
        sections = content.split('\n\n')
        for section in sections:
            if section.strip():
                if section.startswith('#'):
                    text = section.lstrip('#').strip()
                    story.append(Paragraph(text, styles['Heading2']))
                else:
                    story.append(Paragraph(section.strip(), styles['BodyText']))
                story.append(Spacer(1, 0.1*inch))

        doc.build(story)
        logger.info(f"Generated PDF: {output_path}")
        return str(output_path)

    def create_project_zip(
        self,
        files: Dict[str, str],
        project_title: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create ZIP archive of project files

        Args:
            files: Dict of {filename: filepath}
            project_title: Project title
            output_path: Output ZIP path

        Returns:
            Path to generated ZIP file
        """
        if output_path is None:
            output_path = self.temp_dir / f"Project_{project_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, filepath in files.items():
                if Path(filepath).exists():
                    zipf.write(filepath, arcname=filename)
                    logger.info(f"Added to ZIP: {filename}")

        logger.info(f"Created ZIP archive: {output_path}")
        return str(output_path)

    def generate_viva_qa_docx(
        self,
        qa_content: list,
        project_title: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate Viva Q&A document

        Args:
            qa_content: List of dicts with 'question' and 'answer'
            project_title: Project title
            output_path: Output file path

        Returns:
            Path to generated document
        """
        if output_path is None:
            output_path = self.temp_dir / f"Viva_QA_{project_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        doc = Document()

        # Title
        title = doc.add_heading('Viva Voce Preparation', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        subtitle = doc.add_heading(project_title, 1)
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_page_break()

        # Q&A
        for i, qa in enumerate(qa_content, 1):
            # Question
            q_para = doc.add_paragraph()
            q_run = q_para.add_run(f"Q{i}: {qa.get('question', '')}")
            q_run.bold = True
            q_run.font.size = Pt(12)

            # Answer
            a_para = doc.add_paragraph()
            a_run = a_para.add_run(f"A: {qa.get('answer', '')}")
            a_run.font.size = Pt(11)

            doc.add_paragraph()  # Spacing

        doc.save(str(output_path))
        logger.info(f"Generated Viva Q&A DOCX: {output_path}")
        return str(output_path)


# Create singleton instance
document_generator = DocumentGenerator()
