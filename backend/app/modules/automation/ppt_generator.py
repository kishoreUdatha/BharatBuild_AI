"""
PowerPoint Presentation Generator for Academic Projects
Generates professional PPT presentations from project data
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from typing import Dict, List, Optional
from datetime import datetime

from app.core.logging_config import logger


class AcademicPPTGenerator:
    """
    Generate professional PowerPoint presentations for student projects

    Features:
    - Professional slide designs
    - Title slide, agenda, content, conclusion
    - Images and diagrams
    - Consistent branding
    - 15-18 slides
    """

    def __init__(self):
        # Professional color scheme
        self.primary_color = RGBColor(44, 62, 80)      # Dark blue-gray
        self.secondary_color = RGBColor(52, 73, 94)    # Medium blue-gray
        self.accent_color = RGBColor(41, 128, 185)     # Bright blue
        self.text_color = RGBColor(51, 51, 51)         # Dark gray
        self.light_gray = RGBColor(236, 240, 241)      # Light background

    def generate_project_presentation(
        self,
        ppt_data: Dict,
        output_path: str,
        project_info: Optional[Dict] = None
    ) -> bool:
        """
        Generate complete PowerPoint presentation

        Args:
            ppt_data: Presentation content from Document Generator Agent
            output_path: Path to save .pptx file
            project_info: Project metadata (title, authors, etc.)

        Returns:
            bool: True if successful
        """
        try:
            # Create presentation
            prs = Presentation()
            prs.slide_width = Inches(10)  # 16:9 aspect ratio
            prs.slide_height = Inches(5.625)

            # Get slide data
            slides_data = ppt_data.get('slides', [])
            project_title = ppt_data.get('project_title', 'Project Presentation')

            # Generate slides
            for slide_data in slides_data:
                slide_number = slide_data.get('slide_number', 0)
                title = slide_data.get('title', '')
                content = slide_data.get('content', {})
                content_type = content.get('type', 'bullets')

                if slide_number == 1:
                    # Title slide
                    self._create_title_slide(prs, title, content, project_info)
                elif content_type == 'agenda':
                    self._create_agenda_slide(prs, title, content)
                elif content_type == 'bullets':
                    self._create_bullet_slide(prs, title, content)
                elif content_type == 'two_column':
                    self._create_two_column_slide(prs, title, content)
                elif content_type == 'architecture':
                    self._create_architecture_slide(prs, title, content)
                elif content_type == 'features':
                    self._create_features_slide(prs, title, content)
                elif content_type == 'tech_stack':
                    self._create_tech_stack_slide(prs, title, content)
                elif content_type == 'database_schema':
                    self._create_database_slide(prs, title, content)
                elif content_type == 'testing_results':
                    self._create_testing_slide(prs, title, content)
                elif content_type == 'conclusion':
                    self._create_conclusion_slide(prs, title, content)
                elif content_type == 'future_enhancements':
                    self._create_future_scope_slide(prs, title, content)
                elif content_type == 'thank_you':
                    self._create_thank_you_slide(prs, title, content)
                else:
                    # Default bullet slide
                    self._create_bullet_slide(prs, title, content)

            # Save presentation
            prs.save(output_path)

            logger.info(f"Generated PowerPoint presentation: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating PowerPoint: {e}", exc_info=True)
            return False

    def _create_title_slide(self, prs: Presentation, title: str, content: Dict, project_info: Optional[Dict]):
        """Create title slide"""
        slide_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(slide_layout)

        # Background color
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.primary_color

        # Project title
        project_title = content.get('project_name', title)
        title_box = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(8), Inches(1.2))
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = project_title
        title_para.font.size = Pt(44)
        title_para.font.bold = True
        title_para.font.color.rgb = RGBColor(255, 255, 255)
        title_para.alignment = PP_ALIGN.CENTER

        # Subtitle
        subtitle = content.get('subtitle', 'AI-Powered Project Generation')
        subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(2.8), Inches(8), Inches(0.5))
        subtitle_frame = subtitle_box.text_frame
        subtitle_para = subtitle_frame.paragraphs[0]
        subtitle_para.text = subtitle
        subtitle_para.font.size = Pt(20)
        subtitle_para.font.color.rgb = self.light_gray
        subtitle_para.alignment = PP_ALIGN.CENTER

        # Student/Author info
        if project_info and 'authors' in project_info:
            authors_text = "\n".join(project_info['authors'])
        else:
            authors_text = content.get('presented_by', 'Student Name')

        author_box = slide.shapes.add_textbox(Inches(1), Inches(3.8), Inches(8), Inches(0.8))
        author_frame = author_box.text_frame
        author_para = author_frame.paragraphs[0]
        author_para.text = f"Presented By:\n{authors_text}"
        author_para.font.size = Pt(16)
        author_para.font.color.rgb = RGBColor(255, 255, 255)
        author_para.alignment = PP_ALIGN.CENTER

        # Date
        date_text = content.get('date', datetime.utcnow().strftime('%B %d, %Y'))
        date_box = slide.shapes.add_textbox(Inches(1), Inches(4.8), Inches(8), Inches(0.3))
        date_frame = date_box.text_frame
        date_para = date_frame.paragraphs[0]
        date_para.text = date_text
        date_para.font.size = Pt(14)
        date_para.font.color.rgb = self.light_gray
        date_para.alignment = PP_ALIGN.CENTER

    def _create_agenda_slide(self, prs: Presentation, title: str, content: Dict):
        """Create agenda/outline slide"""
        slide_layout = prs.slide_layouts[1]  # Title and content
        slide = prs.slides.add_slide(slide_layout)

        # Title
        title_shape = slide.shapes.title
        title_shape.text = title
        title_shape.text_frame.paragraphs[0].font.size = Pt(32)
        title_shape.text_frame.paragraphs[0].font.color.rgb = self.primary_color

        # Content
        items = content.get('items', [])

        left = Inches(1.5)
        top = Inches(2)
        width = Inches(7)
        height = Inches(3)

        textbox = slide.shapes.add_textbox(left, top, width, height)
        text_frame = textbox.text_frame
        text_frame.word_wrap = True

        for i, item in enumerate(items, 1):
            p = text_frame.add_paragraph() if i > 1 else text_frame.paragraphs[0]
            p.text = f"{i}. {item}"
            p.font.size = Pt(20)
            p.font.color.rgb = self.text_color
            p.space_before = Pt(10)
            p.level = 0

    def _create_bullet_slide(self, prs: Presentation, title: str, content: Dict):
        """Create standard bullet point slide"""
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)

        # Title
        title_shape = slide.shapes.title
        title_shape.text = title
        title_shape.text_frame.paragraphs[0].font.size = Pt(32)
        title_shape.text_frame.paragraphs[0].font.color.rgb = self.primary_color

        # Bullets
        points = content.get('points', [])

        left = Inches(1.5)
        top = Inches(2)
        width = Inches(7)
        height = Inches(3)

        textbox = slide.shapes.add_textbox(left, top, width, height)
        text_frame = textbox.text_frame
        text_frame.word_wrap = True

        for i, point in enumerate(points):
            p = text_frame.add_paragraph() if i > 0 else text_frame.paragraphs[0]
            # Remove emoji if present at start
            clean_point = point.lstrip('✅❌🎯📊💡🔧⚡🚀')
            p.text = f"• {clean_point.strip()}"
            p.font.size = Pt(18)
            p.font.color.rgb = self.text_color
            p.space_before = Pt(8)
            p.level = 0

    def _create_two_column_slide(self, prs: Presentation, title: str, content: Dict):
        """Create two-column slide"""
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)

        # Title
        title_shape = slide.shapes.title
        title_shape.text = title
        title_shape.text_frame.paragraphs[0].font.size = Pt(32)
        title_shape.text_frame.paragraphs[0].font.color.rgb = self.primary_color

        # Left column
        left_content = content.get('left', {})
        left_title = left_content.get('title', 'Left')
        left_points = left_content.get('points', [])

        left_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(4), Inches(3))
        left_frame = left_box.text_frame

        # Left title
        p = left_frame.paragraphs[0]
        p.text = left_title
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = self.accent_color

        # Left points
        for point in left_points:
            p = left_frame.add_paragraph()
            p.text = f"• {point}"
            p.font.size = Pt(16)
            p.font.color.rgb = self.text_color
            p.space_before = Pt(6)

        # Right column
        right_content = content.get('right', {})
        right_title = right_content.get('title', 'Right')
        right_points = right_content.get('points', [])

        right_box = slide.shapes.add_textbox(Inches(5.5), Inches(2), Inches(4), Inches(3))
        right_frame = right_box.text_frame

        # Right title
        p = right_frame.paragraphs[0]
        p.text = right_title
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = self.accent_color

        # Right points
        for point in right_points:
            p = right_frame.add_paragraph()
            p.text = f"• {point}"
            p.font.size = Pt(16)
            p.font.color.rgb = self.text_color
            p.space_before = Pt(6)

    def _create_architecture_slide(self, prs: Presentation, title: str, content: Dict):
        """Create system architecture slide"""
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)

        # Title
        title_shape = slide.shapes.title
        title_shape.text = title
        title_shape.text_frame.paragraphs[0].font.size = Pt(32)
        title_shape.text_frame.paragraphs[0].font.color.rgb = self.primary_color

        # Architecture layers
        layers = content.get('layers', [])

        left = Inches(2)
        top = Inches(2.2)
        width = Inches(6)
        layer_height = Inches(0.6)

        for i, layer in enumerate(layers):
            # Create colored box for each layer
            shape = slide.shapes.add_shape(
                1,  # Rectangle
                left,
                top + (i * (layer_height + Inches(0.1))),
                width,
                layer_height
            )

            # Layer color
            colors = [
                RGBColor(52, 152, 219),   # Blue
                RGBColor(46, 204, 113),   # Green
                RGBColor(155, 89, 182),   # Purple
                RGBColor(241, 196, 15),   # Yellow
            ]
            shape.fill.solid()
            shape.fill.fore_color.rgb = colors[i % len(colors)]

            # Layer text
            text_frame = shape.text_frame
            p = text_frame.paragraphs[0]
            p.text = layer
            p.font.size = Pt(16)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = PP_ALIGN.CENTER

    def _create_features_slide(self, prs: Presentation, title: str, content: Dict):
        """Create features slide"""
        self._create_bullet_slide(prs, title, content)

    def _create_tech_stack_slide(self, prs: Presentation, title: str, content: Dict):
        """Create technology stack slide"""
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)

        # Title
        title_shape = slide.shapes.title
        title_shape.text = title
        title_shape.text_frame.paragraphs[0].font.size = Pt(32)
        title_shape.text_frame.paragraphs[0].font.color.rgb = self.primary_color

        # Technologies by category
        categories = content.get('categories', {})

        left = Inches(1.5)
        top = Inches(2)
        width = Inches(7)

        textbox = slide.shapes.add_textbox(left, top, width, Inches(3))
        text_frame = textbox.text_frame

        for category, tech_list in categories.items():
            # Category header
            p = text_frame.add_paragraph() if text_frame.paragraphs[0].text else text_frame.paragraphs[0]
            p.text = f"{category}:"
            p.font.size = Pt(18)
            p.font.bold = True
            p.font.color.rgb = self.accent_color
            p.space_before = Pt(10)

            # Technologies
            if isinstance(tech_list, list):
                for tech in tech_list:
                    p = text_frame.add_paragraph()
                    p.text = f"  • {tech}"
                    p.font.size = Pt(16)
                    p.font.color.rgb = self.text_color
            else:
                p = text_frame.add_paragraph()
                p.text = f"  • {tech_list}"
                p.font.size = Pt(16)
                p.font.color.rgb = self.text_color

    def _create_database_slide(self, prs: Presentation, title: str, content: Dict):
        """Create database schema slide"""
        self._create_bullet_slide(prs, title, {'points': content.get('tables', [])})

    def _create_testing_slide(self, prs: Presentation, title: str, content: Dict):
        """Create testing results slide"""
        self._create_bullet_slide(prs, title, content)

    def _create_conclusion_slide(self, prs: Presentation, title: str, content: Dict):
        """Create conclusion slide"""
        self._create_bullet_slide(prs, title, content)

    def _create_future_scope_slide(self, prs: Presentation, title: str, content: Dict):
        """Create future scope slide"""
        enhancements = content.get('enhancements', [])
        self._create_bullet_slide(prs, title, {'points': enhancements})

    def _create_thank_you_slide(self, prs: Presentation, title: str, content: Dict):
        """Create thank you slide"""
        slide_layout = prs.slide_layouts[6]  # Blank
        slide = prs.slides.add_slide(slide_layout)

        # Background color
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.primary_color

        # Thank you text
        thank_you_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(0.8))
        thank_you_frame = thank_you_box.text_frame
        thank_you_para = thank_you_frame.paragraphs[0]
        thank_you_para.text = "Thank You!"
        thank_you_para.font.size = Pt(48)
        thank_you_para.font.bold = True
        thank_you_para.font.color.rgb = RGBColor(255, 255, 255)
        thank_you_para.alignment = PP_ALIGN.CENTER

        # Questions text
        message = content.get('message', 'Questions?')
        questions_box = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(8), Inches(0.5))
        questions_frame = questions_box.text_frame
        questions_para = questions_frame.paragraphs[0]
        questions_para.text = message
        questions_para.font.size = Pt(28)
        questions_para.font.color.rgb = self.light_gray
        questions_para.alignment = PP_ALIGN.CENTER

        # Contact info
        contact = content.get('contact', '')
        github = content.get('github', '')
        contact_text = []
        if contact:
            contact_text.append(f"📧 {contact}")
        if github:
            contact_text.append(f"💻 {github}")

        if contact_text:
            contact_box = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(8), Inches(0.8))
            contact_frame = contact_box.text_frame
            contact_para = contact_frame.paragraphs[0]
            contact_para.text = "\n".join(contact_text)
            contact_para.font.size = Pt(16)
            contact_para.font.color.rgb = RGBColor(255, 255, 255)
            contact_para.alignment = PP_ALIGN.CENTER

        # Powered by BharatBuild AI
        footer_box = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(8), Inches(0.3))
        footer_frame = footer_box.text_frame
        footer_para = footer_frame.paragraphs[0]
        footer_para.text = "Generated by BharatBuild AI"
        footer_para.font.size = Pt(12)
        footer_para.font.italic = True
        footer_para.font.color.rgb = self.light_gray
        footer_para.alignment = PP_ALIGN.CENTER


# Singleton instance
ppt_generator = AcademicPPTGenerator()
