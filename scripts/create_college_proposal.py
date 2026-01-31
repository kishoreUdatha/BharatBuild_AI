"""
BharatBuild AI - Professional College Proposal PDF Generator
"""

from fpdf import FPDF
import os
from datetime import datetime

class ProposalPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', '', 8)
            self.set_text_color(128, 128, 128)
            self.set_xy(10, 10)
            self.cell(0, 5, 'BharatBuild AI - College Partnership Proposal', align='L')
            self.cell(0, 5, f'Page {self.page_no()}', align='R')
            self.set_draw_color(200, 200, 200)
            self.line(10, 17, 200, 17)
            self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, 'Confidential | BharatBuild AI Pvt. Ltd. | www.bharatbuild.ai', align='C')

    def draw_gradient(self, x, y, w, h, color1, color2):
        steps = 100
        step_h = h / steps
        for i in range(steps):
            r = int(color1[0] + (color2[0] - color1[0]) * i / steps)
            g = int(color1[1] + (color2[1] - color1[1]) * i / steps)
            b = int(color1[2] + (color2[2] - color1[2]) * i / steps)
            self.set_fill_color(r, g, b)
            self.rect(x, y + i * step_h, w, step_h + 0.5, 'F')


def create_proposal():
    pdf = ProposalPDF()
    pdf.set_margins(15, 15, 15)

    # Colors
    PRIMARY = (0, 82, 165)
    PRIMARY_DARK = (0, 51, 102)
    ACCENT = (255, 107, 53)
    DARK = (33, 37, 41)
    GRAY = (108, 117, 125)
    LIGHT_BG = (248, 249, 250)
    SUCCESS = (40, 167, 69)
    WHITE = (255, 255, 255)

    current_date = datetime.now().strftime("%B %d, %Y")

    # ==================== COVER PAGE ====================
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    # Background
    pdf.set_fill_color(*WHITE)
    pdf.rect(0, 0, 210, 297, 'F')

    # Top bar
    pdf.draw_gradient(0, 0, 210, 60, PRIMARY_DARK, PRIMARY)

    # Company name
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 18)
    pdf.cell(210, 15, 'BharatBuild AI', align='C')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_xy(0, 38)
    pdf.cell(210, 8, 'Smart Learning. Real Projects. Bright Futures.', align='C')

    # Main Title Section
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(20, 80)
    pdf.cell(170, 8, 'PARTNERSHIP PROPOSAL', align='L')

    pdf.set_font('Helvetica', 'B', 32)
    pdf.set_text_color(*DARK)
    pdf.set_xy(20, 92)
    pdf.cell(170, 16, 'AI-Powered Academic', align='L')
    pdf.set_xy(20, 110)
    pdf.cell(170, 16, 'Project Platform', align='L')

    # Accent line
    pdf.set_fill_color(*ACCENT)
    pdf.rect(20, 130, 50, 4, 'F')

    # Subtitle
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(20, 145)
    pdf.multi_cell(170, 6, 'A comprehensive solution for academic project generation, documentation, and campus placement management.')

    # Proposal details box
    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(20, 175, 170, 50, 'F')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(25, 180)
    pdf.cell(80, 6, 'PREPARED FOR:')
    pdf.set_xy(110, 180)
    pdf.cell(80, 6, 'PREPARED BY:')

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*DARK)
    pdf.set_xy(25, 188)
    pdf.cell(80, 6, '[College Name]')
    pdf.set_xy(110, 188)
    pdf.cell(80, 6, 'BharatBuild AI Pvt. Ltd.')

    pdf.set_xy(25, 196)
    pdf.cell(80, 6, '[City, State]')
    pdf.set_xy(110, 196)
    pdf.cell(80, 6, 'Bengaluru, Karnataka')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(25, 210)
    pdf.cell(80, 6, 'DATE:')

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*DARK)
    pdf.set_xy(25, 218)
    pdf.cell(80, 6, current_date)

    # Contact info at bottom
    pdf.set_fill_color(*DARK)
    pdf.rect(0, 255, 210, 42, 'F')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 262)
    pdf.cell(85, 6, 'Contact Us:')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(20, 270)
    pdf.cell(85, 5, 'Email: colleges@bharatbuild.ai')
    pdf.set_xy(20, 277)
    pdf.cell(85, 5, 'Phone: +91 9908787055')
    pdf.set_xy(20, 284)
    pdf.cell(85, 5, 'Website: www.bharatbuild.ai')

    pdf.set_xy(120, 270)
    pdf.cell(70, 5, 'WhatsApp: +91 9908787055')

    # ==================== TABLE OF CONTENTS ====================
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 30)
    pdf.cell(180, 12, 'Table of Contents', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 44, 40, 3, 'F')

    toc_items = [
        ("1.", "Executive Summary", "3"),
        ("2.", "About BharatBuild AI", "4"),
        ("3.", "Problem Statement", "5"),
        ("4.", "Proposed Solution", "6"),
        ("5.", "Features & Benefits", "7"),
        ("6.", "Pricing & Packages", "9"),
        ("7.", "Implementation Plan", "10"),
        ("8.", "Why Choose BharatBuild", "11"),
        ("9.", "Terms & Conditions", "12"),
        ("10.", "Contact Information", "13"),
    ]

    y = 60
    for num, title, page in toc_items:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*PRIMARY)
        pdf.set_xy(20, y)
        pdf.cell(10, 8, num)

        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(*DARK)
        pdf.cell(130, 8, title)

        pdf.set_text_color(*GRAY)
        pdf.cell(20, 8, page, align='R')

        # Dotted line
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)
        for dot_x in range(50, 160, 3):
            pdf.line(dot_x, y + 6, dot_x + 1, y + 6)

        y += 14

    # ==================== EXECUTIVE SUMMARY ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '1. Executive Summary', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*DARK)
    pdf.set_xy(15, 50)
    pdf.multi_cell(180, 6, 'BharatBuild AI is India\'s leading AI-powered academic project platform designed specifically for educational institutions. We help colleges deliver high-quality, industry-ready projects while reducing faculty workload and improving student outcomes.')

    pdf.ln(5)
    pdf.multi_cell(180, 6, 'This proposal outlines how BharatBuild AI can transform your institution\'s academic project delivery, enhance learning outcomes, and streamline placement processes.')

    # Key highlights box
    pdf.ln(8)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(15, pdf.get_y(), 180, 70, 'F')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(20, pdf.get_y() + 5)
    pdf.cell(170, 8, 'KEY HIGHLIGHTS')

    highlights = [
        "Complete project generation in minutes with AI assistance",
        "IEEE-compliant documentation (SRS, UML diagrams, reports)",
        "50+ page project reports ready for submission",
        "Built-in campus placement & assessment module",
        "Faculty dashboard for real-time monitoring",
        "70-85% cost savings compared to international tools"
    ]

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*DARK)
    y = pdf.get_y() + 15
    for item in highlights:
        pdf.set_xy(25, y)
        pdf.set_text_color(*SUCCESS)
        pdf.cell(5, 5, '+')
        pdf.set_text_color(*DARK)
        pdf.cell(165, 5, item)
        y += 8

    # Value proposition
    pdf.ln(35)
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(15, pdf.get_y(), 180, 30, 'F')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, pdf.get_y() + 8)
    pdf.cell(170, 6, 'INVESTMENT: Rs. 20,000 per project (4 students per team)')

    pdf.set_font('Helvetica', '', 10)
    pdf.set_xy(20, pdf.get_y() + 16)
    pdf.cell(170, 6, 'Only Rs. 5,000 per student | Includes complete project package with documentation')

    # ==================== ABOUT BHARATBUILD ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '2. About BharatBuild AI', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*DARK)
    pdf.set_xy(15, 50)
    pdf.multi_cell(180, 6, 'BharatBuild AI is an Indian technology company focused on revolutionizing academic project delivery through artificial intelligence. Founded with the mission to make quality education accessible and affordable, we serve students, developers, founders, and educational institutions across India.')

    # Company stats
    pdf.ln(8)
    stats = [
        ("10,000+", "Projects Delivered"),
        ("100+", "Partner Colleges"),
        ("50,000+", "Students Served"),
        ("99.9%", "Success Rate")
    ]

    stat_x = 20
    for num, label in stats:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(stat_x, pdf.get_y(), 40, 30, 'F')

        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*PRIMARY)
        pdf.set_xy(stat_x, pdf.get_y() + 5)
        pdf.cell(40, 10, num, align='C')

        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(stat_x, pdf.get_y() + 17)
        pdf.cell(40, 6, label, align='C')

        stat_x += 44

    # Our mission
    pdf.ln(40)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(180, 8, 'OUR MISSION')

    pdf.ln(8)
    pdf.set_font('Helvetica', 'I', 11)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(180, 6, '"To empower every Indian student with world-class AI tools for academic excellence, making quality project development accessible and affordable for all."')

    # What we offer
    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(180, 8, 'WHAT WE OFFER')

    offers = [
        ("For Students", "Complete academic projects with documentation, diagrams, reports & viva preparation"),
        ("For Developers", "AI-powered code generation and rapid application development"),
        ("For Founders", "Quick MVP development and idea validation"),
        ("For Colleges", "Batch management, progress tracking & campus placement solutions")
    ]

    pdf.ln(5)
    for title, desc in offers:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*ACCENT)
        pdf.cell(35, 6, title + ":")
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*DARK)
        pdf.cell(145, 6, desc)
        pdf.ln(8)

    # ==================== PROBLEM STATEMENT ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '3. Problem Statement', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*DARK)
    pdf.set_xy(15, 50)
    pdf.multi_cell(180, 6, 'Educational institutions across India face several challenges in delivering quality academic projects and managing placement processes:')

    # Problems list
    problems = [
        ("Poor Project Quality", "Students struggle to create industry-standard projects due to lack of guidance and resources"),
        ("Time-Consuming Documentation", "Creating IEEE-compliant SRS, UML diagrams, and reports takes weeks of effort"),
        ("Expensive International Tools", "Tools like Bolt.new, Cursor cost $20+/month, unaffordable for most students"),
        ("No Indian Payment Options", "International platforms don't support UPI, Razorpay or Indian banking"),
        ("Manual Placement Process", "Campus drives require significant manual effort for registration and assessment"),
        ("Limited Faculty Bandwidth", "Faculty cannot individually guide large batches of students effectively"),
        ("Plagiarism Concerns", "Difficulty in ensuring originality of student submissions"),
        ("Viva Preparation Gap", "Students are often unprepared for project viva examinations")
    ]

    pdf.ln(8)
    for title, desc in problems:
        pdf.set_fill_color(254, 242, 242)
        pdf.rect(15, pdf.get_y(), 180, 16, 'F')
        pdf.set_fill_color(220, 53, 69)
        pdf.rect(15, pdf.get_y(), 3, 16, 'F')

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(220, 53, 69)
        pdf.set_xy(22, pdf.get_y() + 2)
        pdf.cell(170, 5, title)

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(22, pdf.get_y() + 7)
        pdf.cell(170, 5, desc)

        pdf.ln(19)

    # ==================== PROPOSED SOLUTION ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '4. Proposed Solution', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*DARK)
    pdf.set_xy(15, 50)
    pdf.multi_cell(180, 6, 'BharatBuild AI provides a comprehensive solution that addresses all the challenges faced by educational institutions:')

    # Solutions
    solutions = [
        ("AI-Powered Project Generation", "Generate complete, production-ready projects in minutes with our advanced AI engine"),
        ("Automated Documentation", "IEEE-compliant SRS, all UML diagrams, and 50+ page reports generated automatically"),
        ("Affordable Pricing", "Rs. 20,000 per project (Rs. 5,000 per student) - 70-85% cheaper than alternatives"),
        ("Indian Payment Support", "UPI, Razorpay, Net Banking, Credit/Debit cards - all Indian payment methods"),
        ("Campus Drive Module", "Complete placement management with registration, quizzes, and instant results"),
        ("Faculty Dashboard", "Real-time monitoring of student progress, batch management, and analytics"),
        ("Plagiarism Detection", "AI-powered originality checker with detailed reports"),
        ("Viva Preparation", "50+ project-specific questions with detailed answers for each project")
    ]

    pdf.ln(5)
    for title, desc in solutions:
        pdf.set_fill_color(212, 237, 218)
        pdf.rect(15, pdf.get_y(), 180, 16, 'F')
        pdf.set_fill_color(*SUCCESS)
        pdf.rect(15, pdf.get_y(), 3, 16, 'F')

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*SUCCESS)
        pdf.set_xy(22, pdf.get_y() + 2)
        pdf.cell(170, 5, title)

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(22, pdf.get_y() + 7)
        pdf.cell(170, 5, desc)

        pdf.ln(19)

    # ==================== FEATURES & BENEFITS ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '5. Features & Benefits', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    # Student Mode Features
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 50)
    pdf.cell(180, 8, 'A. Student Project Module')

    features_student = [
        ("Complete Source Code", "Production-ready code in React, Node.js, Python, Java, and 30+ technologies"),
        ("IEEE-Format SRS", "Software Requirements Specification following IEEE-830 standards"),
        ("UML Diagrams", "Use Case, Class, Sequence, Activity, and ER diagrams auto-generated"),
        ("Project Report", "50+ page comprehensive report with all chapters for submission"),
        ("PPT Presentation", "Professional slides with architecture diagrams and code snippets"),
        ("Viva Q&A", "50+ potential questions with detailed answers for examination")
    ]

    pdf.ln(5)
    for title, desc in features_student:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*DARK)
        pdf.set_xy(20, pdf.get_y() + 3)
        pdf.set_text_color(*SUCCESS)
        pdf.cell(5, 5, '+')
        pdf.set_text_color(*DARK)
        pdf.cell(50, 5, title)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(120, 5, desc)
        pdf.ln(8)

    # Campus Drive Features
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(180, 8, 'B. Campus Drive Module')

    features_campus = [
        ("Student Registration", "Online registration with academic details, CGPA, department tracking"),
        ("Multi-Category Quiz", "Logical Reasoning, Technical, AI/ML, English, Aptitude, Coding MCQs"),
        ("Auto-Save Progress", "Quiz progress saves automatically, resume if disconnected"),
        ("Instant Results", "Real-time scoring with section-wise breakdown and analysis"),
        ("Admin Dashboard", "Monitor registrations, track progress, export reports to Excel"),
        ("Custom Branding", "Your college logo, colors, and domain for professional look")
    ]

    pdf.ln(3)
    for title, desc in features_campus:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*DARK)
        pdf.set_xy(20, pdf.get_y() + 3)
        pdf.set_text_color(*SUCCESS)
        pdf.cell(5, 5, '+')
        pdf.set_text_color(*DARK)
        pdf.cell(50, 5, title)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(120, 5, desc)
        pdf.ln(8)

    # Page 2 of Features
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 10, '5. Features & Benefits (Continued)', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 37, 40, 3, 'F')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 48)
    pdf.cell(180, 8, 'C. Advanced Features for Institutions')

    features_advanced = [
        ("Plagiarism Detection", "AI-powered checker ensures 100% original code"),
        ("Faculty Dashboard", "Real-time monitoring of student progress"),
        ("Batch Management", "Organize by batch, department, year"),
        ("White-Label Solution", "Custom branding with college logo"),
        ("LMS Integration", "Moodle, Canvas integration via API"),
        ("Data Security", "ISO 27001 compliant, data in India"),
        ("Multi-Department", "CSE, IT, ECE, Mechanical templates"),
        ("24/7 Support", "Dedicated account manager & training")
    ]

    y = 60
    for title, desc in features_advanced:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(15, y, 180, 12, 'F')
        pdf.set_fill_color(*SUCCESS)
        pdf.rect(15, y, 3, 12, 'F')

        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*DARK)
        pdf.set_xy(22, y + 3)
        pdf.cell(50, 6, title)

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(120, 6, desc)

        y += 15

    # Supported Technologies
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 185)
    pdf.cell(180, 8, 'D. Supported Technologies')

    tech_categories = [
        ("Frontend", "React, Next.js, Vue, Angular, TypeScript, Tailwind"),
        ("Backend", "Node.js, Python, Java, Django, Flask, Spring Boot"),
        ("Mobile", "React Native, Flutter, Android, iOS"),
        ("Database", "MongoDB, PostgreSQL, MySQL, Firebase"),
        ("AI/ML", "TensorFlow, PyTorch, OpenAI, LangChain"),
        ("Cloud", "AWS, Docker, Kubernetes, GitHub, Vercel")
    ]

    y = 198
    for cat, techs in tech_categories:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*ACCENT)
        pdf.set_xy(20, y)
        pdf.cell(22, 6, cat + ":")
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*DARK)
        pdf.cell(155, 6, techs)
        y += 10

    # ==================== PRICING ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '6. Pricing & Packages', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    # Main pricing box
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(15, 50, 180, 60, 'F')

    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 58)
    pdf.cell(180, 8, 'COLLEGE PARTNERSHIP PACKAGE', align='C')

    pdf.set_font('Helvetica', 'B', 36)
    pdf.set_xy(15, 70)
    pdf.cell(180, 18, 'Rs. 20,000', align='C')

    pdf.set_font('Helvetica', '', 12)
    pdf.set_xy(15, 90)
    pdf.cell(180, 8, 'Per Complete Project | 4 Students per Team | Rs. 5,000 per Student', align='C')

    # What's included
    pdf.ln(25)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(180, 8, "WHAT'S INCLUDED IN EACH PROJECT:")

    included = [
        "Complete Source Code (any technology stack)",
        "IEEE-Format SRS Documentation",
        "All 5 UML Diagrams (Use Case, Class, Sequence, Activity, ER)",
        "50+ Page Project Report (ready for submission)",
        "Professional PPT Presentation",
        "Viva Q&A Preparation (50+ questions with answers)",
        "Plagiarism Report",
        "1 Month Support for Queries"
    ]

    pdf.ln(5)
    col = 0
    for i, item in enumerate(included):
        x = 20 if col == 0 else 110
        pdf.set_font('Helvetica', '', 10)
        pdf.set_xy(x, pdf.get_y() if col == 0 else pdf.get_y() - 7)
        pdf.set_text_color(*SUCCESS)
        pdf.cell(5, 7, '+')
        pdf.set_text_color(*DARK)
        pdf.cell(80, 7, item)
        col = 1 - col
        if col == 0:
            pdf.ln(7)

    # Comparison
    pdf.ln(15)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(180, 8, 'COST COMPARISON:')

    pdf.ln(8)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(15, pdf.get_y(), 180, 35, 'F')

    comparisons = [
        ("BharatBuild AI", "Rs. 5,000/student", "100%"),
        ("Bolt.new", "$50+/student (~Rs. 4,200)", "800%+"),
        ("Cursor", "$50+/student (~Rs. 4,200)", "800%+"),
        ("Manual Development", "Rs. 15,000-25,000/student", "300-500%")
    ]

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*DARK)
    pdf.set_xy(20, pdf.get_y() + 3)
    pdf.cell(70, 6, "Platform")
    pdf.cell(50, 6, "Cost per Student")
    pdf.cell(40, 6, "vs BharatBuild")

    pdf.ln(8)
    for platform, cost, comparison in comparisons:
        if platform == "BharatBuild AI":
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_text_color(*SUCCESS)
        else:
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(*DARK)

        pdf.set_xy(20, pdf.get_y())
        pdf.cell(70, 6, platform)
        pdf.cell(50, 6, cost)
        pdf.cell(40, 6, comparison)
        pdf.ln(6)

    # ==================== IMPLEMENTATION PLAN ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '7. Implementation Plan', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*DARK)
    pdf.set_xy(15, 48)
    pdf.multi_cell(180, 5, 'Our streamlined implementation process ensures quick onboarding and minimal disruption:')

    phases = [
        ("Phase 1: Onboarding", "1-2 Days", "Agreement signing, account setup, branding configuration, platform walkthrough"),
        ("Phase 2: Training", "1 Day", "Faculty training (2 hrs), student orientation, documentation, Q&A session"),
        ("Phase 3: Pilot", "1 Week", "Pilot batch of 10-20 students, real project testing, feedback collection"),
        ("Phase 4: Full Rollout", "Ongoing", "Department-wise rollout, progress monitoring, dedicated support, quarterly reviews")
    ]

    y = 68
    for phase, duration, desc in phases:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(15, y, 180, 28, 'F')
        pdf.set_fill_color(*PRIMARY)
        pdf.rect(15, y, 4, 28, 'F')

        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*PRIMARY)
        pdf.set_xy(22, y + 4)
        pdf.cell(100, 6, phase)

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*ACCENT)
        pdf.set_xy(150, y + 4)
        pdf.cell(40, 6, duration, align='R')

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*DARK)
        pdf.set_xy(22, y + 14)
        pdf.cell(165, 6, desc)

        y += 35

    # Timeline visual
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 215)
    pdf.cell(180, 8, 'TYPICAL TIMELINE')

    pdf.set_fill_color(*PRIMARY)
    pdf.rect(20, 230, 170, 4, 'F')

    timeline_points = [("Day 1-2", "Onboarding"), ("Day 3", "Training"), ("Week 2", "Pilot"), ("Week 3+", "Rollout")]
    tx = 20
    for day, label in timeline_points:
        pdf.set_fill_color(*ACCENT)
        pdf.ellipse(tx, 228, 8, 8, 'F')

        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*DARK)
        pdf.set_xy(tx - 10, 240)
        pdf.cell(28, 5, day, align='C')

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(tx - 10, 246)
        pdf.cell(28, 5, label, align='C')

        tx += 55

    # ==================== WHY CHOOSE BHARATBUILD ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '8. Why Choose BharatBuild', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    reasons = [
        ("Indian Company, Indian Values", "Built in India, for Indian students. We understand the unique needs of Indian educational institutions and academic requirements."),
        ("Affordable & Transparent Pricing", "No hidden fees, no subscriptions. Simple project-based pricing that's 70-85% cheaper than international alternatives."),
        ("Complete Project Package", "Not just code - complete documentation, diagrams, reports, presentations, and viva preparation included."),
        ("Data Security & Compliance", "ISO 27001 compliant. All data stored in India. GDPR ready. Your institution's data is safe with us."),
        ("Dedicated Support", "24/7 support with dedicated account manager, phone support, and on-site training for faculty."),
        ("Proven Track Record", "10,000+ projects delivered, 100+ partner colleges, 50,000+ students served with 99.9% success rate."),
        ("Indian Payment Methods", "UPI, Razorpay, Net Banking, and all Indian payment methods supported. No international transaction hassles."),
        ("Continuous Innovation", "Regular updates with latest technologies and features. We evolve with the industry needs.")
    ]

    pdf.ln(8)
    for title, desc in reasons:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(15, pdf.get_y(), 180, 22, 'F')
        pdf.set_fill_color(*SUCCESS)
        pdf.rect(15, pdf.get_y(), 4, 22, 'F')

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*DARK)
        pdf.set_xy(22, pdf.get_y() + 3)
        pdf.cell(170, 5, title)

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(22, pdf.get_y() + 9)
        pdf.multi_cell(165, 4, desc)

        pdf.ln(5)

    # ==================== TERMS & CONDITIONS ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '9. Terms & Conditions', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    terms = [
        ("Payment Terms", "50% advance at initiation, 50% on delivery. UPI/Bank Transfer/Razorpay accepted."),
        ("Delivery Timeline", "Standard projects: 7-10 working days. Complex projects may need more time."),
        ("Revision Policy", "2 revision rounds included. Additional revisions: Rs. 2,000 per round."),
        ("Intellectual Property", "All code and documentation becomes property of institution/students."),
        ("Confidentiality", "All project details and student information kept strictly confidential."),
        ("Support Period", "1 month post-delivery support included for queries and minor fixes."),
        ("Cancellation", "100% refund before work starts. 50% refund after initiation."),
        ("Validity", "This proposal is valid for 30 days from the date of issue.")
    ]

    y = 50
    for i, (title, desc) in enumerate(terms):
        pdf.set_fill_color(*LIGHT_BG) if i % 2 == 0 else pdf.set_fill_color(*WHITE)
        pdf.rect(15, y, 180, 18, 'F')

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*PRIMARY)
        pdf.set_xy(20, y + 3)
        pdf.cell(45, 6, title)

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*DARK)
        pdf.set_xy(68, y + 3)
        pdf.multi_cell(122, 5, desc)

        y += 22

    # Important note
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(15, 230, 180, 25, 'F')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 236)
    pdf.cell(170, 6, 'Note: Terms may be customized based on institutional requirements.')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(20, 245)
    pdf.cell(170, 6, 'Please discuss any specific needs with our team.')

    # ==================== CONTACT ====================
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(15, 25)
    pdf.cell(180, 12, '10. Contact Information', align='L')

    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, 39, 40, 3, 'F')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*DARK)
    pdf.set_xy(15, 48)
    pdf.cell(180, 6, 'We would be delighted to discuss this proposal further. Please reach out:')

    # Contact cards in grid
    contact_items = [
        ("Email", "colleges@bharatbuild.ai"),
        ("Phone", "+91 9908787055"),
        ("WhatsApp", "+91 9908787055"),
        ("Website", "www.bharatbuild.ai")
    ]

    y = 62
    for i, (label, value) in enumerate(contact_items):
        x = 15 if i % 2 == 0 else 105
        if i == 2:
            y = 100

        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(x, y, 85, 30, 'F')
        pdf.set_fill_color(*PRIMARY)
        pdf.rect(x, y, 4, 30, 'F')

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(x + 10, y + 6)
        pdf.cell(70, 6, label)

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*DARK)
        pdf.set_xy(x + 10, y + 16)
        pdf.cell(70, 6, value)

    # Company info
    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(15, 140, 180, 25, 'F')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(20, 146)
    pdf.cell(40, 6, 'Company:')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*DARK)
    pdf.cell(60, 6, 'BharatBuild AI Pvt. Ltd.')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(25, 6, 'Location:')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*DARK)
    pdf.cell(50, 6, 'Bengaluru, Karnataka, India')

    # Call to action box
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(15, 180, 180, 45, 'F')

    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 188)
    pdf.cell(180, 10, 'Ready to Get Started?', align='C')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_xy(15, 202)
    pdf.cell(180, 6, 'Schedule a free demo today and transform your', align='C')
    pdf.set_xy(15, 210)
    pdf.cell(180, 6, 'institution\'s academic project delivery.', align='C')

    # Thank you section
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*DARK)
    pdf.set_xy(15, 240)
    pdf.cell(180, 8, 'Thank You', align='C')

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(15, 252)
    pdf.cell(180, 6, 'Thank you for considering BharatBuild AI as your academic partner.', align='C')
    pdf.set_xy(15, 262)
    pdf.cell(180, 6, 'We look forward to empowering your students with the best AI tools.', align='C')

    # Save PDF
    output_path = os.path.join(os.path.dirname(__file__), 'docs', 'BharatBuild_College_Proposal.pdf')
    pdf.output(output_path)
    print(f"Proposal PDF created successfully: {output_path}")
    return output_path


if __name__ == "__main__":
    create_proposal()
