"""
PDF Generator for Academic Documents
Converts SRS, SDS, Testing Plan, and Project Reports to professional PDF format
"""

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image as RLImage, ListFlowable, ListItem, KeepTogether
)
from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from datetime import datetime
from typing import Dict, List, Optional
import os
from io import BytesIO

from app.core.logging_config import logger


class AcademicPDFGenerator:
    """
    Generate professional academic PDF documents

    Features:
    - IEEE/ACM standard formatting
    - Table of contents
    - Headers and footers
    - Professional styling
    - Images and tables
    - Code snippets
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Create custom paragraph styles for academic documents"""

        # Title page styles
        self.styles.add(ParagraphStyle(
            name='DocTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='DocSubtitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=HexColor('#4a4a4a'),
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # Heading styles - Override existing styles by removing first
        if 'Heading1' in self.styles:
            del self.styles.byName['Heading1']
        self.styles.add(ParagraphStyle(
            name='Heading1',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            keepWithNext=True
        ))

        if 'Heading2' in self.styles:
            del self.styles.byName['Heading2']
        self.styles.add(ParagraphStyle(
            name='Heading2',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold',
            keepWithNext=True
        ))

        if 'Heading3' in self.styles:
            del self.styles.byName['Heading3']
        self.styles.add(ParagraphStyle(
            name='Heading3',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=HexColor('#455a64'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold',
            keepWithNext=True
        ))

        # Body text - Override existing style
        if 'BodyText' in self.styles:
            del self.styles.byName['BodyText']
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=HexColor('#333333'),
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))

        # Code style - Override existing style
        if 'Code' in self.styles:
            del self.styles.byName['Code']
        self.styles.add(ParagraphStyle(
            name='Code',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=HexColor('#d63384'),
            fontName='Courier',
            backColor=HexColor('#f5f5f5'),
            leftIndent=20,
            rightIndent=20,
            spaceAfter=6
        ))

        # Table cell style
        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=HexColor('#333333'),
            fontName='Helvetica'
        ))

    def _create_title_page(self, doc_info: Dict) -> List:
        """Create title page for academic document"""
        story = []

        # Add vertical space
        story.append(Spacer(1, 2*inch))

        # Document title
        title = Paragraph(doc_info.get('title', 'Project Document'), self.styles['DocTitle'])
        story.append(title)
        story.append(Spacer(1, 0.3*inch))

        # Subtitle (if any)
        if 'subtitle' in doc_info:
            subtitle = Paragraph(doc_info['subtitle'], self.styles['DocSubtitle'])
            story.append(subtitle)
            story.append(Spacer(1, 0.5*inch))

        # Project info
        if 'project_name' in doc_info:
            project_name = Paragraph(f"<b>Project:</b> {doc_info['project_name']}", self.styles['BodyText'])
            story.append(project_name)
            story.append(Spacer(1, 0.2*inch))

        # Version and date
        version_date = f"<b>Version:</b> {doc_info.get('version', '1.0')} | <b>Date:</b> {doc_info.get('date', datetime.utcnow().strftime('%B %d, %Y'))}"
        story.append(Paragraph(version_date, self.styles['BodyText']))
        story.append(Spacer(1, 1*inch))

        # Student/Author info (if any)
        if 'authors' in doc_info:
            story.append(Paragraph("<b>Prepared By:</b>", self.styles['Heading3']))
            for author in doc_info['authors']:
                story.append(Paragraph(author, self.styles['BodyText']))
            story.append(Spacer(1, 0.5*inch))

        # University/Organization (if any)
        if 'organization' in doc_info:
            org = Paragraph(doc_info['organization'], self.styles['BodyText'])
            story.append(org)

        # Powered by BharatBuild AI
        story.append(Spacer(1, 1*inch))
        footer = Paragraph(
            '<i>Generated by BharatBuild AI - AI-Powered Project Generator</i>',
            self.styles['BodyText']
        )
        story.append(footer)

        story.append(PageBreak())
        return story

    def _create_table_of_contents(self, sections: List[str]) -> List:
        """Create table of contents"""
        story = []

        story.append(Paragraph("Table of Contents", self.styles['Heading1']))
        story.append(Spacer(1, 0.3*inch))

        for i, section in enumerate(sections, 1):
            toc_entry = Paragraph(f"{i}. {section}", self.styles['BodyText'])
            story.append(toc_entry)
            story.append(Spacer(1, 0.1*inch))

        story.append(PageBreak())
        return story

    def _convert_to_flowables(self, content: Dict, section_title: str = None) -> List:
        """Convert content dictionary to ReportLab flowables"""
        story = []

        if section_title:
            story.append(Paragraph(section_title, self.styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))

        for key, value in content.items():
            # Section heading
            heading = key.replace('_', ' ').title()
            story.append(Paragraph(heading, self.styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))

            # Section content
            if isinstance(value, str):
                # Simple text
                para = Paragraph(value, self.styles['BodyText'])
                story.append(para)
                story.append(Spacer(1, 0.1*inch))

            elif isinstance(value, list):
                # List of items
                for item in value:
                    if isinstance(item, str):
                        bullet = Paragraph(f"• {item}", self.styles['BodyText'])
                        story.append(bullet)
                    elif isinstance(item, dict):
                        # Nested dictionary in list
                        for sub_key, sub_value in item.items():
                            sub_heading = Paragraph(f"<b>{sub_key}:</b>", self.styles['Heading3'])
                            story.append(sub_heading)
                            if isinstance(sub_value, str):
                                story.append(Paragraph(sub_value, self.styles['BodyText']))
                            elif isinstance(sub_value, list):
                                for sub_item in sub_value:
                                    bullet = Paragraph(f"  - {sub_item}", self.styles['BodyText'])
                                    story.append(bullet)
                story.append(Spacer(1, 0.1*inch))

            elif isinstance(value, dict):
                # Nested dictionary
                for sub_key, sub_value in value.items():
                    sub_heading = Paragraph(f"<b>{sub_key.replace('_', ' ').title()}:</b>", self.styles['Heading3'])
                    story.append(sub_heading)
                    if isinstance(sub_value, str):
                        story.append(Paragraph(sub_value, self.styles['BodyText']))
                    elif isinstance(sub_value, list):
                        for item in sub_value:
                            bullet = Paragraph(f"• {item}", self.styles['BodyText'])
                            story.append(bullet)
                    story.append(Spacer(1, 0.1*inch))

        story.append(Spacer(1, 0.2*inch))
        return story

    def generate_srs_pdf(
        self,
        srs_data: Dict,
        output_path: str,
        doc_info: Optional[Dict] = None
    ) -> bool:
        """
        Generate Software Requirements Specification PDF

        Args:
            srs_data: SRS content from Document Generator Agent
            output_path: Path to save PDF
            doc_info: Document metadata (title, version, authors, etc.)

        Returns:
            bool: True if successful
        """
        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            story = []

            # Title page
            if doc_info is None:
                doc_info = {
                    'title': 'Software Requirements Specification',
                    'subtitle': srs_data.get('title', 'Project SRS'),
                    'version': srs_data.get('version', '1.0'),
                    'date': srs_data.get('date', datetime.utcnow().strftime('%B %d, %Y'))
                }
            story.extend(self._create_title_page(doc_info))

            # Table of contents
            sections = [
                'Introduction',
                'Overall Description',
                'Functional Requirements',
                'Non-Functional Requirements',
                'System Features',
                'External Interface Requirements',
                'Other Requirements'
            ]
            story.extend(self._create_table_of_contents(sections))

            # SRS Content
            content = srs_data.get('content', {})

            # Introduction
            if 'introduction' in content:
                story.extend(self._convert_to_flowables(content['introduction'], '1. Introduction'))

            # Overall Description
            if 'overall_description' in content:
                story.extend(self._convert_to_flowables(content['overall_description'], '2. Overall Description'))

            # Functional Requirements
            if 'functional_requirements' in content:
                story.append(Paragraph('3. Functional Requirements', self.styles['Heading1']))
                story.append(Spacer(1, 0.2*inch))

                for req in content['functional_requirements']:
                    req_id = req.get('id', 'FR-X')
                    req_title = req.get('requirement', 'Requirement')
                    story.append(Paragraph(f"{req_id}: {req_title}", self.styles['Heading2']))

                    for key, value in req.items():
                        if key not in ['id', 'requirement']:
                            story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b>", self.styles['Heading3']))
                            if isinstance(value, list):
                                for item in value:
                                    story.append(Paragraph(f"• {item}", self.styles['BodyText']))
                            else:
                                story.append(Paragraph(str(value), self.styles['BodyText']))
                    story.append(Spacer(1, 0.2*inch))

            # Non-Functional Requirements
            if 'non_functional_requirements' in content:
                story.extend(self._convert_to_flowables(content['non_functional_requirements'], '4. Non-Functional Requirements'))

            # Build PDF
            doc.build(story)

            logger.info(f"Generated SRS PDF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating SRS PDF: {e}", exc_info=True)
            return False

    def generate_sds_pdf(
        self,
        sds_data: Dict,
        output_path: str,
        doc_info: Optional[Dict] = None
    ) -> bool:
        """Generate Software Design Specification PDF"""
        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            story = []

            # Title page
            if doc_info is None:
                doc_info = {
                    'title': 'Software Design Specification',
                    'subtitle': sds_data.get('title', 'Project SDS'),
                    'version': sds_data.get('version', '1.0'),
                    'date': sds_data.get('date', datetime.utcnow().strftime('%B %d, %Y'))
                }
            story.extend(self._create_title_page(doc_info))

            # SDS Content
            content = sds_data.get('content', {})

            for section_name, section_content in content.items():
                title = section_name.replace('_', ' ').title()
                story.extend(self._convert_to_flowables(section_content, title))

            doc.build(story)
            logger.info(f"Generated SDS PDF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating SDS PDF: {e}", exc_info=True)
            return False

    def generate_testing_plan_pdf(
        self,
        testing_data: Dict,
        output_path: str,
        doc_info: Optional[Dict] = None
    ) -> bool:
        """Generate Testing Plan PDF"""
        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            story = []

            # Title page
            if doc_info is None:
                doc_info = {
                    'title': 'Comprehensive Testing Plan',
                    'subtitle': testing_data.get('title', 'Project Testing Plan'),
                    'version': testing_data.get('version', '1.0'),
                    'date': testing_data.get('date', datetime.utcnow().strftime('%B %d, %Y'))
                }
            story.extend(self._create_title_page(doc_info))

            # Testing Content
            content = testing_data.get('content', {})

            for section_name, section_content in content.items():
                title = section_name.replace('_', ' ').title()
                story.extend(self._convert_to_flowables(section_content, title))

            doc.build(story)
            logger.info(f"Generated Testing Plan PDF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating Testing Plan PDF: {e}", exc_info=True)
            return False

    def _add_diagram_to_story(
        self,
        story: List,
        diagram_path: str,
        caption: str,
        width: float = 5*inch
    ):
        """Add a diagram/image to the PDF story"""
        try:
            if os.path.exists(diagram_path):
                img = RLImage(diagram_path, width=width, height=width*0.7)
                story.append(img)
                story.append(Spacer(1, 0.1*inch))

                # Caption
                caption_para = Paragraph(f"<i>Figure: {caption}</i>", self.styles['BodyText'])
                story.append(caption_para)
                story.append(Spacer(1, 0.2*inch))
        except Exception as e:
            logger.warning(f"Could not add diagram {diagram_path}: {e}")

    def generate_project_report_pdf(
        self,
        report_data: Dict,
        output_path: str,
        doc_info: Optional[Dict] = None,
        diagrams: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Generate Complete Project Report PDF (60-80 pages with UML diagrams)

        Args:
            report_data: Report content from Document Generator
            output_path: Path to save PDF
            doc_info: Document metadata
            diagrams: Dict of {diagram_type: image_path} for UML diagrams

        Returns:
            bool: Success status
        """
        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
            story = []

            # Title page
            if doc_info is None:
                doc_info = {
                    'title': report_data.get('title', 'Project Report'),
                    'subtitle': 'Complete Project Documentation',
                    'version': report_data.get('version', '1.0'),
                    'date': report_data.get('date', datetime.utcnow().strftime('%B %d, %Y'))
                }
            story.extend(self._create_title_page(doc_info))

            # Certificate page
            story.append(PageBreak())
            story.append(Spacer(1, 2*inch))
            story.append(Paragraph("CERTIFICATE", self.styles['DocTitle']))
            story.append(Spacer(1, 0.5*inch))
            cert_text = """
            This is to certify that the project entitled <b>"{title}"</b> is a bonafide work carried out by
            {author} in partial fulfillment of the requirements for the award of the degree.
            """.format(
                title=report_data.get('title', 'Project Title'),
                author=doc_info.get('authors', ['Student Name'])[0] if 'authors' in doc_info else 'Student Name'
            )
            story.append(Paragraph(cert_text, self.styles['BodyText']))
            story.append(Spacer(1, 2*inch))
            story.append(Paragraph("Guide's Signature: __________________", self.styles['BodyText']))
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("Date: __________________", self.styles['BodyText']))

            # Acknowledgement
            story.append(PageBreak())
            story.append(Paragraph("ACKNOWLEDGEMENT", self.styles['Heading1']))
            story.append(Spacer(1, 0.3*inch))
            ack_text = """
            I would like to express my sincere gratitude to my project guide for their invaluable guidance
            and support throughout this project. I am also thankful to the department faculty and my peers
            for their encouragement and assistance. This project would not have been possible without their
            continuous support.
            """
            story.append(Paragraph(ack_text, self.styles['BodyText']))

            # Table of Contents (generated from sections)
            story.append(PageBreak())
            sections = [
                'Abstract',
                'Introduction',
                'Literature Survey',
                'Problem Statement',
                'Objectives',
                'System Requirements',
                'System Analysis',
                'UML Diagrams',
                '  - Use Case Diagram',
                '  - Class Diagram',
                '  - Sequence Diagram',
                '  - Activity Diagram',
                '  - ER Diagram',
                'System Design & Architecture',
                'Database Design',
                'Implementation',
                'Modules',
                'Code Explanation',
                'Testing & Validation',
                'Results & Screenshots',
                'Conclusion',
                'Future Scope',
                'References',
                'Appendix'
            ]
            story.extend(self._create_table_of_contents(sections))

            # List of Figures
            story.append(PageBreak())
            story.append(Paragraph("LIST OF FIGURES", self.styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))
            figures = [
                'Use Case Diagram',
                'Class Diagram',
                'Sequence Diagram',
                'Activity Diagram',
                'ER Diagram',
                'System Architecture',
                'Database Schema',
                'Component Diagram',
                'Deployment Diagram',
                'User Interface Screenshots'
            ]
            for i, fig in enumerate(figures, 1):
                story.append(Paragraph(f"Figure {i}: {fig}", self.styles['BodyText']))
                story.append(Spacer(1, 0.05*inch))

            # Report Content
            content = report_data.get('content', {})

            # 1. ABSTRACT (1-2 pages)
            story.append(PageBreak())
            if 'abstract' in content:
                story.extend(self._convert_to_flowables(content['abstract'], '1. ABSTRACT'))

            # 2. INTRODUCTION (3-5 pages)
            story.append(PageBreak())
            if 'introduction' in content:
                story.extend(self._convert_to_flowables(content['introduction'], '2. INTRODUCTION'))

            # 3. LITERATURE SURVEY (5-8 pages)
            story.append(PageBreak())
            if 'literature_survey' in content:
                story.extend(self._convert_to_flowables(content['literature_survey'], '3. LITERATURE SURVEY'))

            # 4. PROBLEM STATEMENT & OBJECTIVES (2-3 pages)
            story.append(PageBreak())
            story.append(Paragraph('4. PROBLEM STATEMENT & OBJECTIVES', self.styles['Heading1']))
            if 'objectives' in content:
                story.extend(self._convert_to_flowables(content['objectives'], None))

            # 5. SYSTEM REQUIREMENTS (3-4 pages)
            story.append(PageBreak())
            if 'system_requirements' in content:
                story.extend(self._convert_to_flowables(content['system_requirements'], '5. SYSTEM REQUIREMENTS'))

            # 6. SYSTEM ANALYSIS (3-4 pages)
            story.append(PageBreak())
            story.append(Paragraph('6. SYSTEM ANALYSIS', self.styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))
            analysis_text = """
            The system analysis phase involves understanding the current system limitations and
            proposing solutions. This includes feasibility analysis (technical, economic, operational),
            requirement gathering, and identifying system constraints.
            """
            story.append(Paragraph(analysis_text, self.styles['BodyText']))

            # 7. UML DIAGRAMS (8-12 pages)
            story.append(PageBreak())
            story.append(Paragraph('7. UML DIAGRAMS', self.styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))

            # Add each diagram if available
            if diagrams:
                # Use Case Diagram
                story.append(Paragraph('7.1 Use Case Diagram', self.styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph('Use case diagrams capture the functional requirements of the system.',
                                     self.styles['BodyText']))
                if 'use_case' in diagrams:
                    self._add_diagram_to_story(story, diagrams['use_case'], 'Use Case Diagram')
                story.append(PageBreak())

                # Class Diagram
                story.append(Paragraph('7.2 Class Diagram', self.styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph('Class diagrams show the static structure of the system.',
                                     self.styles['BodyText']))
                if 'class' in diagrams:
                    self._add_diagram_to_story(story, diagrams['class'], 'Class Diagram')
                story.append(PageBreak())

                # Sequence Diagram
                story.append(Paragraph('7.3 Sequence Diagram', self.styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph('Sequence diagrams illustrate object interactions in time sequence.',
                                     self.styles['BodyText']))
                if 'sequence' in diagrams:
                    self._add_diagram_to_story(story, diagrams['sequence'], 'Sequence Diagram')
                story.append(PageBreak())

                # Activity Diagram
                story.append(Paragraph('7.4 Activity Diagram', self.styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph('Activity diagrams represent workflows and business processes.',
                                     self.styles['BodyText']))
                if 'activity' in diagrams:
                    self._add_diagram_to_story(story, diagrams['activity'], 'Activity Diagram')
                story.append(PageBreak())

                # ER Diagram
                story.append(Paragraph('7.5 ER Diagram', self.styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph('ER diagrams model the database structure and relationships.',
                                     self.styles['BodyText']))
                if 'er' in diagrams:
                    self._add_diagram_to_story(story, diagrams['er'], 'ER Diagram')

            # 8. SYSTEM DESIGN (5-7 pages)
            story.append(PageBreak())
            if 'system_design' in content:
                story.extend(self._convert_to_flowables(content['system_design'], '8. SYSTEM DESIGN & ARCHITECTURE'))

            # 9. DATABASE DESIGN (3-4 pages)
            story.append(PageBreak())
            story.append(Paragraph('9. DATABASE DESIGN', self.styles['Heading1']))
            if 'database_design' in content:
                story.extend(self._convert_to_flowables(content['database_design'], None))

            # 10. IMPLEMENTATION (8-10 pages)
            story.append(PageBreak())
            if 'implementation' in content:
                story.extend(self._convert_to_flowables(content['implementation'], '10. IMPLEMENTATION'))

            # 11. MODULES (5-8 pages)
            story.append(PageBreak())
            if 'modules' in content:
                story.extend(self._convert_to_flowables(content['modules'], '11. MODULES'))

            # 12. CODE EXPLANATION (5-7 pages)
            story.append(PageBreak())
            story.append(Paragraph('12. CODE EXPLANATION', self.styles['Heading1']))
            if 'code_explanation' in content:
                story.extend(self._convert_to_flowables(content['code_explanation'], None))

            # 13. TESTING (5-7 pages)
            story.append(PageBreak())
            if 'testing' in content:
                story.extend(self._convert_to_flowables(content['testing'], '13. TESTING & VALIDATION'))

            # 14. RESULTS & SCREENSHOTS (3-5 pages)
            story.append(PageBreak())
            if 'results' in content:
                story.extend(self._convert_to_flowables(content['results'], '14. RESULTS & SCREENSHOTS'))

            # 15. CONCLUSION (2-3 pages)
            story.append(PageBreak())
            if 'conclusion' in content:
                story.extend(self._convert_to_flowables(content['conclusion'], '15. CONCLUSION'))

            # 16. FUTURE SCOPE (2-3 pages)
            story.append(PageBreak())
            if 'future_scope' in content:
                story.extend(self._convert_to_flowables(content['future_scope'], '16. FUTURE SCOPE'))

            # 17. REFERENCES (1-2 pages)
            story.append(PageBreak())
            if 'references' in content:
                story.extend(self._convert_to_flowables(content['references'], '17. REFERENCES'))

            # 18. APPENDIX (2-3 pages)
            story.append(PageBreak())
            story.append(Paragraph('18. APPENDIX', self.styles['Heading1']))
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph('A. Source Code Listings', self.styles['Heading2']))
            story.append(Paragraph('B. Installation Guide', self.styles['Heading2']))
            story.append(Paragraph('C. User Manual', self.styles['Heading2']))

            doc.build(story)
            logger.info(f"Generated Project Report PDF (60-80 pages): {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating Project Report PDF: {e}", exc_info=True)
            return False


# Singleton instance
pdf_generator = AcademicPDFGenerator()
