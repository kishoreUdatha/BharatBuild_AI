"""
BharatBuild AI - College Partnership Proposal PDF Generator
Creates a professional, well-formatted PDF proposal
"""

from fpdf import FPDF
from datetime import datetime

class ProposalPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.primary_color = (0, 82, 155)  # Blue
        self.secondary_color = (255, 107, 53)  # Orange
        self.text_color = (51, 51, 51)
        self.light_gray = (245, 245, 245)
        self.green_bg = (232, 245, 233)

    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', '', 9)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, 'BharatBuild AI - College Partnership Proposal', 0, 0, 'L')
            self.cell(0, 10, f'Page {self.page_no()}', 0, 1, 'R')
            self.set_draw_color(200, 200, 200)
            self.line(10, 15, 200, 15)
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, 'Confidential | BharatBuild AI Pvt. Ltd. | www.bharatbuild.ai', 0, 0, 'C')

    def section_title(self, title, number=None):
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(*self.primary_color)
        if number:
            self.cell(0, 12, f'{number}. {title}', 0, 1)
        else:
            self.cell(0, 12, title, 0, 1)
        # Orange underline
        self.set_fill_color(*self.secondary_color)
        self.rect(10, self.get_y(), 40, 3, 'F')
        self.ln(8)
        self.set_text_color(*self.text_color)

    def sub_section(self, title):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(*self.primary_color)
        self.cell(0, 10, title, 0, 1)
        self.set_text_color(*self.text_color)

    def body_text(self, text):
        self.set_font('Helvetica', '', 11)
        self.set_text_color(*self.text_color)
        self.multi_cell(0, 6, text)
        self.ln(3)

    def bullet_point(self, text, color=None):
        self.set_font('Helvetica', '', 11)
        if color:
            self.set_text_color(*color)
        else:
            self.set_text_color(*self.text_color)
        self.cell(8, 6, chr(149), 0, 0)  # Bullet character
        self.multi_cell(0, 6, text)

    def feature_box(self, title, description, bg_color=None):
        if bg_color is None:
            bg_color = self.light_gray

        start_y = self.get_y()
        self.set_fill_color(*bg_color)

        # Draw left border
        self.set_fill_color(*self.secondary_color)
        self.rect(10, start_y, 3, 20, 'F')

        # Draw background
        self.set_fill_color(*bg_color)
        self.rect(13, start_y, 184, 20, 'F')

        # Title
        self.set_xy(16, start_y + 3)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*self.secondary_color)
        self.cell(0, 6, title, 0, 1)

        # Description
        self.set_x(16)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(100, 100, 100)
        self.multi_cell(180, 5, description)

        self.set_y(start_y + 23)
        self.set_text_color(*self.text_color)

    def stat_box(self, number, label, x, y, width=45):
        self.set_xy(x, y)
        self.set_fill_color(*self.light_gray)
        self.rect(x, y, width, 25, 'F')

        self.set_xy(x, y + 3)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*self.primary_color)
        self.cell(width, 8, number, 0, 1, 'C')

        self.set_x(x)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(width, 6, label, 0, 1, 'C')

    def info_box(self, title, value, bg_color=None):
        if bg_color is None:
            bg_color = self.light_gray

        start_y = self.get_y()

        # Left accent bar
        self.set_fill_color(*self.primary_color)
        self.rect(10, start_y, 3, 18, 'F')

        # Background
        self.set_fill_color(*bg_color)
        self.rect(13, start_y, 184, 18, 'F')

        # Title
        self.set_xy(16, start_y + 3)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*self.secondary_color)
        self.cell(50, 6, title, 0, 0)

        # Value
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*self.text_color)
        self.cell(0, 6, value, 0, 1)

        self.set_y(start_y + 21)


def create_proposal():
    pdf = ProposalPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ==================== COVER PAGE ====================
    pdf.add_page()

    # Blue header bar
    pdf.set_fill_color(0, 82, 155)
    pdf.rect(0, 0, 210, 70, 'F')

    # Gradient effect
    pdf.set_fill_color(0, 60, 120)
    pdf.rect(0, 0, 210, 35, 'F')

    # Company name
    pdf.set_xy(0, 20)
    pdf.set_font('Helvetica', 'B', 32)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, 'BharatBuild AI', 0, 1, 'C')

    # Tagline
    pdf.set_font('Helvetica', 'I', 14)
    pdf.cell(0, 10, 'Smart Learning. Real Projects. Bright Futures.', 0, 1, 'C')

    # Main content area
    pdf.ln(30)

    # Partnership Proposal label
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(255, 107, 53)
    pdf.cell(0, 8, 'PARTNERSHIP PROPOSAL', 0, 1, 'L')
    pdf.ln(3)

    # Main title
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 12, 'AI-Powered Academic', 0, 1, 'L')
    pdf.cell(0, 12, 'Project Platform', 0, 1, 'L')

    # Orange accent bar
    pdf.set_fill_color(255, 107, 53)
    pdf.rect(10, pdf.get_y() + 5, 50, 4, 'F')
    pdf.ln(15)

    # Description
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 7, 'A comprehensive solution for academic project generation, documentation, and campus placement management.')

    pdf.ln(15)

    # Info boxes
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, pdf.get_y(), 190, 60, 'F')

    info_y = pdf.get_y() + 8

    # Prepared For
    pdf.set_xy(20, info_y)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 107, 53)
    pdf.cell(80, 6, 'PREPARED FOR:', 0, 0)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'PREPARED BY:', 0, 1)

    pdf.set_xy(20, info_y + 8)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(80, 6, '[College Name]', 0, 0)
    pdf.cell(0, 6, 'BharatBuild AI Pvt. Ltd.', 0, 1)

    pdf.set_xy(20, info_y + 15)
    pdf.cell(80, 6, '[City, State]', 0, 0)
    pdf.cell(0, 6, 'Bengaluru, Karnataka', 0, 1)

    pdf.set_xy(20, info_y + 28)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 107, 53)
    pdf.cell(80, 6, 'DATE:', 0, 1)

    pdf.set_xy(20, info_y + 35)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 6, datetime.now().strftime('%B %d, %Y'), 0, 1)

    # Footer contact section
    pdf.set_y(250)
    pdf.set_fill_color(0, 82, 155)
    pdf.rect(0, 250, 210, 47, 'F')

    pdf.set_xy(10, 255)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 6, 'Contact Us:', 0, 1)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(10)
    pdf.cell(95, 5, 'Email: colleges@bharatbuild.ai', 0, 0)
    pdf.cell(0, 5, 'WhatsApp: +91 9908787055', 0, 1)
    pdf.set_x(10)
    pdf.cell(95, 5, 'Phone: +91 9908787055', 0, 0)
    pdf.cell(0, 5, 'Website: www.bharatbuild.ai', 0, 1)

    # ==================== TABLE OF CONTENTS ====================
    pdf.add_page()
    pdf.section_title('Table of Contents')
    pdf.ln(5)

    toc_items = [
        ('1', 'Executive Summary', '3'),
        ('2', 'About BharatBuild AI', '4'),
        ('3', 'Problem Statement', '5'),
        ('4', 'Proposed Solution', '6'),
        ('5', 'Features & Benefits', '7'),
        ('6', 'Pricing & Packages', '9'),
        ('7', 'Implementation Plan', '10'),
        ('8', 'Why Choose BharatBuild', '11'),
        ('9', 'Terms & Conditions', '12'),
        ('10', 'Contact Information', '13'),
    ]

    for num, title, page in toc_items:
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(255, 107, 53)
        pdf.cell(10, 10, num + '.', 0, 0)
        pdf.set_font('Helvetica', '', 12)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(140, 10, title, 0, 0)
        pdf.cell(0, 10, page, 0, 1, 'R')
        # Dotted line
        pdf.set_draw_color(200, 200, 200)
        pdf.line(25, pdf.get_y() - 5, 175, pdf.get_y() - 5)

    # ==================== EXECUTIVE SUMMARY ====================
    pdf.add_page()
    pdf.section_title('Executive Summary', '1')

    pdf.body_text("BharatBuild AI is India's leading AI-powered academic project platform designed specifically for educational institutions. We help colleges deliver high-quality, industry-ready projects while reducing faculty workload and improving student outcomes.")
    pdf.ln(3)
    pdf.body_text("This proposal outlines how BharatBuild AI can transform your institution's academic project delivery, enhance learning outcomes, and streamline placement processes.")

    pdf.ln(8)

    # Key Highlights Box
    pdf.set_fill_color(232, 245, 233)
    start_y = pdf.get_y()
    pdf.rect(10, start_y, 190, 75, 'F')

    pdf.set_xy(15, start_y + 5)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(0, 82, 155)
    pdf.cell(0, 8, 'KEY HIGHLIGHTS', 0, 1)

    highlights = [
        'Complete project generation in minutes with AI assistance',
        'IEEE-compliant documentation (SRS, UML diagrams, reports)',
        '50+ page project reports ready for submission',
        'Built-in campus placement & assessment module',
        'Faculty dashboard for real-time monitoring',
        '70-85% cost savings compared to international tools'
    ]

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(51, 51, 51)
    for item in highlights:
        pdf.set_x(20)
        pdf.set_text_color(76, 175, 80)
        pdf.cell(8, 7, '+', 0, 0)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(0, 7, item, 0, 1)

    pdf.set_y(start_y + 85)

    # Investment Box
    pdf.set_fill_color(0, 82, 155)
    inv_y = pdf.get_y()
    pdf.rect(10, inv_y, 190, 35, 'F')

    pdf.set_xy(15, inv_y + 8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, 'INVESTMENT: Rs. 20,000 per project (4 students per team)', 0, 1)

    pdf.set_x(15)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, 'Only Rs. 5,000 per student | Includes complete project package with documentation', 0, 1)

    # ==================== ABOUT BHARATBUILD ====================
    pdf.add_page()
    pdf.section_title('About BharatBuild AI', '2')

    pdf.body_text("BharatBuild AI is an Indian technology company focused on revolutionizing academic project delivery through artificial intelligence. Founded with the mission to make quality education accessible and affordable, we serve students, developers, founders, and educational institutions across India.")

    pdf.ln(10)

    # Stats in a row
    stat_y = pdf.get_y()
    pdf.stat_box('10,000+', 'Projects Delivered', 10, stat_y)
    pdf.stat_box('100+', 'Partner Colleges', 60, stat_y)
    pdf.stat_box('50,000+', 'Students Served', 110, stat_y)
    pdf.stat_box('99.9%', 'Success Rate', 160, stat_y)

    pdf.set_y(stat_y + 35)

    # Mission
    pdf.sub_section('OUR MISSION')
    pdf.set_font('Helvetica', 'I', 11)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 6, '"To empower every Indian student with world-class AI tools for academic excellence, making quality project development accessible and affordable for all."')

    pdf.ln(8)

    # What We Offer
    pdf.sub_section('WHAT WE OFFER')

    offerings = [
        ('For Students:', 'Complete academic projects with documentation, diagrams, reports & viva preparation'),
        ('For Developers:', 'AI-powered code generation and rapid application development'),
        ('For Founders:', 'Quick MVP development and idea validation'),
        ('For Colleges:', 'Batch management, progress tracking & campus placement solutions'),
    ]

    for label, desc in offerings:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(255, 107, 53)
        pdf.cell(35, 7, label, 0, 0)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(0, 7, desc, 0, 1)

    # ==================== PROBLEM STATEMENT ====================
    pdf.add_page()
    pdf.section_title('Problem Statement', '3')

    pdf.body_text("Educational institutions across India face several challenges in delivering quality academic projects and managing placement processes:")

    pdf.ln(5)

    problems = [
        ('Poor Project Quality', 'Students struggle to create industry-standard projects due to lack of guidance and resources'),
        ('Time-Consuming Documentation', 'Creating IEEE-compliant SRS, UML diagrams, and reports takes weeks of effort'),
        ('Expensive International Tools', 'Tools like Bolt.new, Cursor cost $20+/month, unaffordable for most students'),
        ('No Indian Payment Options', "International platforms don't support UPI, Razorpay or Indian banking"),
        ('Manual Placement Process', 'Campus drives require significant manual effort for registration and assessment'),
        ('Limited Faculty Bandwidth', 'Faculty cannot individually guide large batches of students effectively'),
        ('Plagiarism Concerns', 'Difficulty in ensuring originality of student submissions'),
        ('Viva Preparation Gap', 'Students are often unprepared for project viva examinations'),
    ]

    for title, desc in problems:
        pdf.feature_box(title, desc, (255, 235, 238))

    # ==================== PROPOSED SOLUTION ====================
    pdf.add_page()
    pdf.section_title('Proposed Solution', '4')

    pdf.body_text("BharatBuild AI provides a comprehensive solution that addresses all the challenges faced by educational institutions:")

    pdf.ln(5)

    solutions = [
        ('AI-Powered Project Generation', 'Generate complete, production-ready projects in minutes with our advanced AI engine'),
        ('Automated Documentation', 'IEEE-compliant SRS, all UML diagrams, and 50+ page reports generated automatically'),
        ('Affordable Pricing', 'Rs. 20,000 per project (Rs. 5,000 per student) - 70-85% cheaper than alternatives'),
        ('Indian Payment Support', 'UPI, Razorpay, Net Banking, Credit/Debit cards - all Indian payment methods'),
        ('Campus Drive Module', 'Complete placement management with registration, quizzes, and instant results'),
        ('Faculty Dashboard', 'Real-time monitoring of student progress, batch management, and analytics'),
        ('Plagiarism Detection', 'AI-powered originality checker with detailed reports'),
        ('Viva Preparation', '50+ project-specific questions with detailed answers for each project'),
    ]

    for title, desc in solutions:
        pdf.feature_box(title, desc, (232, 245, 233))

    # ==================== FEATURES & BENEFITS ====================
    pdf.add_page()
    pdf.section_title('Features & Benefits', '5')

    pdf.sub_section('A. Student Project Module')
    pdf.ln(3)

    student_features = [
        ('Complete Source Code', 'Production-ready code in React, Node.js, Python, Java, and 30+ technologies'),
        ('IEEE-Format SRS', 'Software Requirements Specification following IEEE-830 standards'),
        ('UML Diagrams', 'Use Case, Class, Sequence, Activity, and ER diagrams auto-generated'),
        ('Project Report', '50+ page comprehensive report with all chapters for submission'),
        ('PPT Presentation', 'Professional slides with architecture diagrams and code snippets'),
        ('Viva Q&A', '50+ potential questions with detailed answers for examination'),
    ]

    for title, desc in student_features:
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(76, 175, 80)
        pdf.cell(8, 7, '+', 0, 0)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(45, 7, title, 0, 0)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, desc, 0, 1)

    pdf.ln(8)

    pdf.sub_section('B. Campus Drive Module')
    pdf.ln(3)

    campus_features = [
        ('Student Registration', 'Online registration with academic details, CGPA, department tracking'),
        ('Multi-Category Quiz', 'Logical Reasoning, Technical, AI/ML, English, Aptitude, Coding MCQs'),
        ('Auto-Save Progress', 'Quiz progress saves automatically, resume if disconnected'),
        ('Instant Results', 'Real-time scoring with section-wise breakdown and analysis'),
        ('Admin Dashboard', 'Monitor registrations, track progress, export reports to Excel'),
        ('Custom Branding', 'Your college logo, colors, and domain for professional look'),
    ]

    for title, desc in campus_features:
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(76, 175, 80)
        pdf.cell(8, 7, '+', 0, 0)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(45, 7, title, 0, 0)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, desc, 0, 1)

    # Page 2 of Features
    pdf.add_page()
    pdf.section_title('Features & Benefits (Continued)', '5')

    pdf.sub_section('C. Advanced Features for Institutions')
    pdf.ln(3)

    advanced_features = [
        ('Plagiarism Detection', 'AI-powered checker ensures 100% original code'),
        ('Faculty Dashboard', 'Real-time monitoring of student progress'),
        ('Batch Management', 'Organize by batch, department, year'),
        ('White-Label Solution', 'Custom branding with college logo'),
        ('LMS Integration', 'Moodle, Canvas integration via API'),
        ('Data Security', 'ISO 27001 compliant, data in India'),
        ('Multi-Department', 'CSE, IT, ECE, Mechanical templates'),
        ('24/7 Support', 'Dedicated account manager & training'),
    ]

    for title, desc in advanced_features:
        pdf.info_box(title, desc)

    pdf.ln(10)

    pdf.sub_section('D. Supported Technologies')
    pdf.ln(5)

    tech_stacks = [
        ('Frontend:', 'React, Next.js, Vue, Angular, TypeScript, Tailwind'),
        ('Backend:', 'Node.js, Python, Java, Django, Flask, Spring Boot'),
        ('Mobile:', 'React Native, Flutter, Android, iOS'),
        ('Database:', 'MongoDB, PostgreSQL, MySQL, Firebase'),
        ('AI/ML:', 'TensorFlow, PyTorch, OpenAI, LangChain'),
        ('Cloud:', 'AWS, Docker, Kubernetes, GitHub, Vercel'),
    ]

    for label, techs in tech_stacks:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(255, 107, 53)
        pdf.cell(25, 7, label, 0, 0)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(0, 7, techs, 0, 1)

    # ==================== PRICING ====================
    pdf.add_page()
    pdf.section_title('Pricing & Packages', '6')

    # Main pricing box
    pdf.set_fill_color(232, 245, 233)
    price_y = pdf.get_y()
    pdf.rect(10, price_y, 190, 100, 'F')

    # Border
    pdf.set_draw_color(76, 175, 80)
    pdf.rect(10, price_y, 190, 100, 'D')

    pdf.set_xy(15, price_y + 8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(0, 82, 155)
    pdf.cell(0, 8, 'COLLEGE PARTNERSHIP PACKAGE', 0, 1, 'C')

    pdf.set_font('Helvetica', 'B', 36)
    pdf.set_text_color(76, 175, 80)
    pdf.cell(0, 20, 'Rs. 20,000', 0, 1, 'C')

    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Per Complete Project | 4 Students per Team | Rs. 5,000 per Student', 0, 1, 'C')

    pdf.ln(5)
    pdf.set_x(15)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 8, "WHAT'S INCLUDED IN EACH PROJECT:", 0, 1)

    inclusions = [
        'Complete Source Code (any technology stack)',
        'IEEE-Format SRS Documentation',
        'All 5 UML Diagrams (Use Case, Class, Sequence, Activity, ER)',
        '50+ Page Project Report (ready for submission)',
        'Professional PPT Presentation',
        'Viva Q&A Preparation (50+ questions with answers)',
        'Plagiarism Report',
        '1 Month Support for Queries'
    ]

    for item in inclusions:
        pdf.set_x(20)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(76, 175, 80)
        pdf.cell(5, 5, '+', 0, 0)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(0, 5, item, 0, 1)

    pdf.set_y(price_y + 110)

    # Comparison table
    pdf.sub_section('COST COMPARISON:')
    pdf.ln(5)

    # Table header
    pdf.set_fill_color(0, 82, 155)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(70, 10, 'Platform', 1, 0, 'C', True)
    pdf.cell(60, 10, 'Cost per Student', 1, 0, 'C', True)
    pdf.cell(60, 10, 'vs BharatBuild', 1, 1, 'C', True)

    # Table rows
    comparisons = [
        ('BharatBuild AI', 'Rs. 5,000/student', '100%', True),
        ('Bolt.new', '$50+/student (~Rs. 4,200)', '800%+', False),
        ('Cursor', '$50+/student (~Rs. 4,200)', '800%+', False),
        ('Manual Development', 'Rs. 15,000-25,000/student', '300-500%', False),
    ]

    for platform, cost, vs, highlight in comparisons:
        if highlight:
            pdf.set_fill_color(232, 245, 233)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(76, 175, 80)
        else:
            pdf.set_fill_color(255, 255, 255)
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(51, 51, 51)

        pdf.cell(70, 9, platform, 1, 0, 'L', True)
        pdf.cell(60, 9, cost, 1, 0, 'C', True)
        pdf.cell(60, 9, vs, 1, 1, 'C', True)

    # ==================== IMPLEMENTATION PLAN ====================
    pdf.add_page()
    pdf.section_title('Implementation Plan', '7')

    pdf.body_text("Our streamlined implementation process ensures quick onboarding and minimal disruption:")

    pdf.ln(5)

    phases = [
        ('Phase 1: Onboarding', '1-2 Days', 'Agreement signing, account setup, branding configuration, platform walkthrough'),
        ('Phase 2: Training', '1 Day', 'Faculty training (2 hrs), student orientation, documentation, Q&A session'),
        ('Phase 3: Pilot', '1 Week', 'Pilot batch of 10-20 students, real project testing, feedback collection'),
        ('Phase 4: Full Rollout', 'Ongoing', 'Department-wise rollout, progress monitoring, dedicated support, quarterly reviews'),
    ]

    for phase, duration, desc in phases:
        start_y = pdf.get_y()

        # Left accent
        pdf.set_fill_color(0, 82, 155)
        pdf.rect(10, start_y, 3, 25, 'F')

        # Background
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(13, start_y, 184, 25, 'F')

        # Phase title
        pdf.set_xy(18, start_y + 3)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(0, 82, 155)
        pdf.cell(100, 7, phase, 0, 0)

        # Duration
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(255, 107, 53)
        pdf.cell(0, 7, duration, 0, 1, 'R')

        # Description
        pdf.set_x(18)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, desc, 0, 1)

        pdf.set_y(start_y + 30)

    # Timeline visual
    pdf.ln(10)
    pdf.sub_section('TYPICAL TIMELINE')
    pdf.ln(5)

    timeline_y = pdf.get_y()

    # Timeline bar
    pdf.set_fill_color(0, 82, 155)
    pdf.rect(20, timeline_y + 5, 170, 4, 'F')

    # Timeline points
    points = [('Day 1-2', 'Onboarding', 20), ('Day 3', 'Training', 75), ('Week 2', 'Pilot', 130), ('Week 3+', 'Rollout', 180)]

    for label, sublabel, x in points:
        # Circle
        pdf.set_fill_color(255, 107, 53)
        pdf.ellipse(x - 5, timeline_y + 2, 10, 10, 'F')

        # Label
        pdf.set_xy(x - 20, timeline_y + 15)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(40, 5, label, 0, 1, 'C')

        pdf.set_xy(x - 20, timeline_y + 20)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(40, 5, sublabel, 0, 1, 'C')

    # ==================== WHY CHOOSE BHARATBUILD ====================
    pdf.add_page()
    pdf.section_title('Why Choose BharatBuild', '8')

    reasons = [
        ('Indian Company, Indian Values', 'Built in India, for Indian students. We understand the unique needs of Indian educational institutions and academic requirements.'),
        ('Affordable & Transparent Pricing', "No hidden fees, no subscriptions. Simple project-based pricing that's 70-85% cheaper than international alternatives."),
        ('Complete Project Package', 'Not just code - complete documentation, diagrams, reports, presentations, and viva preparation included.'),
        ('Data Security & Compliance', "ISO 27001 compliant. All data stored in India. GDPR ready. Your institution's data is safe with us."),
        ('Dedicated Support', '24/7 support with dedicated account manager, phone support, and on-site training for faculty.'),
        ('Proven Track Record', '10,000+ projects delivered, 100+ partner colleges, 50,000+ students served with 99.9% success rate.'),
        ('Indian Payment Methods', 'UPI, Razorpay, Net Banking, and all Indian payment methods supported. No international transaction hassles.'),
        ('Continuous Innovation', 'Regular updates with latest technologies and features. We evolve with the industry needs.'),
    ]

    for title, desc in reasons:
        start_y = pdf.get_y()

        # Left accent
        pdf.set_fill_color(0, 82, 155)
        pdf.rect(10, start_y, 3, 22, 'F')

        # Background
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(13, start_y, 184, 22, 'F')

        # Title
        pdf.set_xy(18, start_y + 3)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(0, 6, title, 0, 1)

        # Description
        pdf.set_x(18)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(175, 5, desc)

        pdf.set_y(start_y + 26)

    # ==================== TERMS & CONDITIONS ====================
    pdf.add_page()
    pdf.section_title('Terms & Conditions', '9')

    terms = [
        ('Payment Terms', '50% advance at initiation, 50% on delivery. UPI/Bank Transfer/Razorpay accepted.'),
        ('Delivery Timeline', 'Standard projects: 7-10 working days. Complex projects may need more time.'),
        ('Revision Policy', '2 revision rounds included. Additional revisions: Rs. 2,000 per round.'),
        ('Intellectual Property', 'All code and documentation becomes property of institution/students.'),
        ('Confidentiality', 'All project details and student information kept strictly confidential.'),
        ('Support Period', '1 month post-delivery support included for queries and minor fixes.'),
        ('Cancellation', '100% refund before work starts. 50% refund after initiation.'),
        ('Validity', 'This proposal is valid for 30 days from the date of issue.'),
    ]

    for title, desc in terms:
        pdf.info_box(title, desc)

    pdf.ln(10)

    # Note box
    pdf.set_fill_color(255, 243, 224)
    note_y = pdf.get_y()
    pdf.rect(10, note_y, 190, 25, 'F')

    pdf.set_xy(15, note_y + 5)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 152, 0)
    pdf.cell(0, 6, 'Note: Terms may be customized based on institutional requirements.', 0, 1)

    pdf.set_x(15)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Please discuss any specific needs with our team.', 0, 1)

    # ==================== CONTACT INFORMATION ====================
    pdf.add_page()
    pdf.section_title('Contact Information', '10')

    pdf.body_text("We would be delighted to discuss this proposal further. Please reach out:")

    pdf.ln(10)

    # Contact cards
    contacts = [
        ('Email', 'colleges@bharatbuild.ai'),
        ('Phone', '+91 9908787055'),
        ('WhatsApp', '+91 9908787055'),
        ('Website', 'www.bharatbuild.ai'),
    ]

    card_width = 90
    x_positions = [10, 105]

    for i, (label, value) in enumerate(contacts):
        x = x_positions[i % 2]
        y = pdf.get_y() if i % 2 == 0 else y

        # Card background
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(x, y, card_width, 25, 'F')

        # Left accent
        pdf.set_fill_color(0, 82, 155)
        pdf.rect(x, y, 3, 25, 'F')

        # Label
        pdf.set_xy(x + 8, y + 4)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, label, 0, 1)

        # Value
        pdf.set_xy(x + 8, y + 12)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 82, 155)
        pdf.cell(0, 6, value, 0, 1)

        if i % 2 == 1:
            pdf.set_y(y + 30)

    pdf.ln(15)

    # Company info
    pdf.set_fill_color(245, 245, 245)
    info_y = pdf.get_y()
    pdf.rect(10, info_y, 190, 15, 'F')

    pdf.set_xy(15, info_y + 4)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 107, 53)
    pdf.cell(25, 6, 'Company:', 0, 0)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(70, 6, 'BharatBuild AI Pvt. Ltd.', 0, 0)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 107, 53)
    pdf.cell(25, 6, 'Location:', 0, 0)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 6, 'Bengaluru, Karnataka, India', 0, 1)

    pdf.ln(20)

    # CTA Box
    pdf.set_fill_color(0, 82, 155)
    cta_y = pdf.get_y()
    pdf.rect(10, cta_y, 190, 35, 'F')

    pdf.set_xy(15, cta_y + 8)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, 'Ready to Get Started?', 0, 1, 'C')

    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 6, "Schedule a free demo today and transform your institution's academic project delivery.", 0, 1, 'C')

    pdf.ln(15)

    # Thank you
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 12, 'Thank You', 0, 1, 'C')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Thank you for considering BharatBuild AI as your academic partner.', 0, 1, 'C')
    pdf.cell(0, 6, 'We look forward to empowering your students with the best AI tools.', 0, 1, 'C')

    # Save PDF
    output_path = 'BharatBuild_College_Proposal_New.pdf'
    pdf.output(output_path)
    print(f"PDF created successfully: {output_path}")
    return output_path


if __name__ == '__main__':
    create_proposal()
