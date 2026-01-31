"""
BharatBuild AI - Professional College Brochure PDF Generator
Premium Design Version
"""

from fpdf import FPDF
import os

class BrochurePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=False, margin=0)

    def header(self):
        pass

    def footer(self):
        pass

    def draw_gradient(self, x, y, w, h, color1, color2, direction='vertical'):
        steps = 100
        if direction == 'vertical':
            step_h = h / steps
            for i in range(steps):
                r = int(color1[0] + (color2[0] - color1[0]) * i / steps)
                g = int(color1[1] + (color2[1] - color1[1]) * i / steps)
                b = int(color1[2] + (color2[2] - color1[2]) * i / steps)
                self.set_fill_color(r, g, b)
                self.rect(x, y + i * step_h, w, step_h + 0.5, 'F')
        else:
            step_w = w / steps
            for i in range(steps):
                r = int(color1[0] + (color2[0] - color1[0]) * i / steps)
                g = int(color1[1] + (color2[1] - color1[1]) * i / steps)
                b = int(color1[2] + (color2[2] - color1[2]) * i / steps)
                self.set_fill_color(r, g, b)
                self.rect(x + i * step_w, y, step_w + 0.5, h, 'F')

    def draw_rounded_rect(self, x, y, w, h, r, color):
        self.set_fill_color(*color)
        self.rect(x, y, w, h, 'F')


def create_brochure():
    pdf = BrochurePDF()
    pdf.set_margins(0, 0, 0)

    # Professional Color Palette
    PRIMARY = (0, 102, 204)       # Professional Blue
    PRIMARY_DARK = (0, 71, 143)   # Darker Blue
    ACCENT = (255, 107, 53)       # Orange accent
    DARK = (26, 32, 44)           # Almost Black
    WHITE = (255, 255, 255)
    LIGHT_BG = (245, 247, 250)    # Light gray-blue
    SUCCESS = (34, 197, 94)       # Green
    GRAY = (107, 114, 128)
    LIGHT_GRAY = (229, 231, 235)

    # ==================== PAGE 1: COVER ====================
    pdf.add_page()

    # Clean white background with accent strip
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, 210, 297, 'F')

    # Top accent bar
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(0, 0, 210, 8, 'F')

    # Left side color block
    pdf.draw_gradient(0, 0, 75, 297, PRIMARY_DARK, PRIMARY)

    # Company name on left strip
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(5, 30)
    pdf.cell(65, 10, 'BHARATBUILD', align='C')

    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(*ACCENT)
    pdf.set_xy(5, 42)
    pdf.cell(65, 12, 'AI', align='C')

    # Vertical text on left
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(200, 220, 255)
    pdf.set_xy(5, 70)
    pdf.cell(65, 6, 'INDIA\'S #1 AI PLATFORM', align='C')

    # Main content area - right side
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(80, 25)
    pdf.cell(125, 8, 'FOR EDUCATIONAL INSTITUTIONS', align='L')

    # Main headline
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(*DARK)
    pdf.set_xy(80, 40)
    pdf.cell(125, 12, 'Smart Learning.', align='L')
    pdf.set_xy(80, 54)
    pdf.cell(125, 12, 'Real Projects.', align='L')
    pdf.set_text_color(*ACCENT)
    pdf.set_xy(80, 68)
    pdf.cell(125, 12, 'Bright Futures.', align='L')

    # Orange underline
    pdf.set_fill_color(*ACCENT)
    pdf.rect(80, 84, 70, 3, 'F')

    # Description
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(80, 94)
    pdf.multi_cell(120, 5, 'AI-powered platform for complete project generation with IEEE documentation, UML diagrams, reports, presentations & viva preparation.')

    # Key metrics in a row
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*DARK)
    pdf.set_xy(80, 125)
    pdf.cell(125, 6, 'TRUSTED BY LEADING INSTITUTIONS', align='L')

    metrics = [
        ("10,000+", "Projects"),
        ("100+", "Colleges"),
        ("50,000+", "Students")
    ]

    met_x = 80
    for num, label in metrics:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(met_x, 135, 38, 28, 'F')

        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*PRIMARY)
        pdf.set_xy(met_x, 139)
        pdf.cell(38, 10, num, align='C')

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(met_x, 150)
        pdf.cell(38, 6, label, align='C')

        met_x += 42

    # Who it's for section
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*DARK)
    pdf.set_xy(80, 175)
    pdf.cell(125, 8, 'WHO USES BHARATBUILD', align='L')

    users = [
        ("Students", "Complete academic projects with documentation"),
        ("Developers", "Build production apps 10x faster"),
        ("Founders", "Validate ideas & create MVPs quickly"),
        ("Colleges", "Manage batches & placement drives")
    ]

    y = 188
    for title, desc in users:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(80, y, 120, 16, 'F')

        pdf.set_fill_color(*ACCENT)
        pdf.rect(80, y, 3, 16, 'F')

        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*DARK)
        pdf.set_xy(86, y + 2)
        pdf.cell(50, 6, title)

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(86, y + 8)
        pdf.cell(110, 6, desc)

        y += 19

    # Bottom contact section
    pdf.set_fill_color(*DARK)
    pdf.rect(75, 268, 135, 29, 'F')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(80, 273)
    pdf.cell(60, 6, 'www.bharatbuild.ai')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(80, 282)
    pdf.cell(125, 6, 'colleges@bharatbuild.ai  |  +91 9908787055')

    # Left strip bottom - decorative
    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 268, 75, 29, 'F')

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 278)
    pdf.cell(75, 8, 'Made in India', align='C')

    # ==================== PAGE 2: WHY BHARATBUILD ====================
    pdf.add_page()

    # White background
    pdf.set_fill_color(*WHITE)
    pdf.rect(0, 0, 210, 297, 'F')

    # Header bar
    pdf.draw_gradient(0, 0, 210, 50, PRIMARY, PRIMARY_DARK)

    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 15)
    pdf.cell(210, 12, 'Why Colleges Choose', align='C')

    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(255, 107, 53)
    pdf.set_xy(0, 28)
    pdf.cell(210, 12, 'BharatBuild AI', align='C')

    # Problem Section
    pdf.set_fill_color(254, 242, 242)
    pdf.rect(12, 58, 90, 125, 'F')

    # Red left border
    pdf.set_fill_color(239, 68, 68)
    pdf.rect(12, 58, 4, 125, 'F')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(185, 28, 28)
    pdf.set_xy(20, 63)
    pdf.cell(78, 8, 'Current Challenges')

    problems = [
        "Poor project quality",
        "International tools cost $200+",
        "No UPI payment options",
        "Documentation takes weeks",
        "No plagiarism detection",
        "No faculty dashboard",
        "Difficult viva preparation",
        "No batch management"
    ]

    pdf.set_font('Helvetica', '', 8)
    y = 76
    for problem in problems:
        pdf.set_text_color(239, 68, 68)
        pdf.set_xy(20, y)
        pdf.cell(6, 5, 'X')
        pdf.set_text_color(75, 85, 99)
        pdf.cell(70, 5, problem)
        y += 12

    # Solution Section
    pdf.set_fill_color(236, 253, 245)
    pdf.rect(108, 58, 90, 125, 'F')

    # Green left border
    pdf.set_fill_color(34, 197, 94)
    pdf.rect(108, 58, 4, 125, 'F')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(22, 101, 52)
    pdf.set_xy(116, 63)
    pdf.cell(78, 8, 'Our Solutions')

    solutions = [
        "AI generates in minutes",
        "Rs.20,000 per project",
        "UPI, Razorpay, Net Banking",
        "Auto IEEE documentation",
        "AI plagiarism detection",
        "Real-time faculty dashboard",
        "50+ viva questions included",
        "Complete batch management"
    ]

    pdf.set_font('Helvetica', '', 8)
    y = 76
    for solution in solutions:
        pdf.set_text_color(34, 197, 94)
        pdf.set_xy(116, y)
        pdf.cell(6, 5, '+')
        pdf.set_text_color(75, 85, 99)
        pdf.cell(70, 5, solution)
        y += 12

    # Key Benefits Section
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(0, 192)
    pdf.cell(210, 10, 'Key Benefits', align='C')

    benefits = [
        ("70-85%", "Cost Savings", "vs international tools"),
        ("5x", "Faster Delivery", "with AI assistance"),
        ("100%", "IEEE Compliant", "documentation"),
        ("24/7", "Support", "dedicated team")
    ]

    ben_x = 17
    for stat, title, desc in benefits:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(ben_x, 205, 42, 45, 'F')

        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(*ACCENT)
        pdf.set_xy(ben_x, 210)
        pdf.cell(42, 10, stat, align='C')

        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*DARK)
        pdf.set_xy(ben_x, 222)
        pdf.cell(42, 6, title, align='C')

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(ben_x, 230)
        pdf.cell(42, 6, desc, align='C')

        ben_x += 46

    # Bottom bar
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(0, 260, 210, 37, 'F')

    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 270)
    pdf.cell(210, 8, 'Join 100+ colleges already transforming their academic projects', align='C')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(0, 282)
    pdf.cell(210, 8, 'Schedule a demo: colleges@bharatbuild.ai', align='C')

    # ==================== PAGE 3: STUDENT MODE ====================
    pdf.add_page()

    pdf.set_fill_color(*WHITE)
    pdf.rect(0, 0, 210, 297, 'F')

    # Header
    pdf.draw_gradient(0, 0, 210, 55, ACCENT, (229, 90, 43))

    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 12)
    pdf.cell(210, 15, 'Student Mode', align='C')

    pdf.set_font('Helvetica', '', 12)
    pdf.set_xy(0, 32)
    pdf.cell(210, 10, 'Complete Academic Project Automation', align='C')

    # Features grid
    features = [
        ("Complete Source Code", "Production-ready code in React, Node.js, Python, Java & more frameworks", (59, 130, 246)),
        ("IEEE-Format SRS", "Auto-generated Software Requirements Specification following IEEE-830", (16, 185, 129)),
        ("UML Diagrams", "Use Case, Class, Sequence, Activity & ER diagrams auto-generated", (139, 92, 246)),
        ("50+ Page Report", "Complete project report with all chapters ready for submission", (245, 158, 11)),
        ("PPT Presentation", "Professional slides with architecture diagrams & code snippets", (236, 72, 153)),
        ("Viva Q&A Prep", "50+ potential questions with detailed answers for examination", (6, 182, 212))
    ]

    y = 65
    for i, (title, desc, color) in enumerate(features):
        x = 12 if i % 2 == 0 else 108
        if i > 0 and i % 2 == 0:
            y += 40

        # Card
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(x, y, 90, 38, 'F')

        # Color accent
        pdf.set_fill_color(*color)
        pdf.rect(x, y, 4, 38, 'F')

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*DARK)
        pdf.set_xy(x + 8, y + 5)
        pdf.cell(78, 6, title)

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(x + 8, y + 14)
        pdf.multi_cell(78, 4, desc)

    # Highlight box
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(12, 190, 186, 30, 'F')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(12, 196)
    pdf.cell(186, 8, 'Accepted by Leading Colleges Across India', align='C')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(12, 208)
    pdf.cell(186, 8, 'Code + Docs + Diagrams + Report + PPT + Viva = Complete Package', align='C')

    # Technologies Section
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*DARK)
    pdf.set_xy(0, 230)
    pdf.cell(210, 8, 'Supported Technologies', align='C')

    # Tech categories with colors
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(12, 242)
    pdf.cell(186, 5, 'Frontend: React | Next.js | Vue | Angular | TypeScript | HTML/CSS | Tailwind', align='C')

    pdf.set_text_color(*SUCCESS)
    pdf.set_xy(12, 250)
    pdf.cell(186, 5, 'Backend: Node.js | Python | Java | Django | Flask | FastAPI | Spring Boot | Express.js', align='C')

    pdf.set_text_color(139, 92, 246)
    pdf.set_xy(12, 258)
    pdf.cell(186, 5, 'Mobile & DB: React Native | Flutter | MongoDB | PostgreSQL | MySQL | Firebase', align='C')

    pdf.set_text_color(*ACCENT)
    pdf.set_xy(12, 266)
    pdf.cell(186, 5, 'AI/ML: TensorFlow | PyTorch | OpenAI | LangChain | Hugging Face | Scikit-learn | Pandas', align='C')

    pdf.set_text_color(*GRAY)
    pdf.set_xy(12, 274)
    pdf.cell(186, 5, 'Cloud & DevOps: AWS | Docker | Kubernetes | GitHub | CI/CD | Vercel | Netlify', align='C')

    # ==================== PAGE 4: CAMPUS DRIVE ====================
    pdf.add_page()

    # Dark background
    pdf.draw_gradient(0, 0, 210, 297, PRIMARY_DARK, DARK)

    # Header
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 20)
    pdf.cell(210, 12, 'Campus Drive Module', align='C')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(200, 210, 220)
    pdf.set_xy(0, 36)
    pdf.cell(210, 8, 'Complete Placement Management Solution', align='C')

    # Divider
    pdf.set_draw_color(255, 107, 53)
    pdf.set_line_width(0.8)
    pdf.line(80, 50, 130, 50)

    # Feature cards
    campus_features = [
        ("Student Registration", "Online registration with personal details, academic info, CGPA tracking", (59, 130, 246)),
        ("Multi-Category Quiz", "Logical, Technical, AI/ML, English, Aptitude & Coding MCQs", (16, 185, 129)),
        ("Auto-Save Progress", "Quiz saves automatically, students can resume if disconnected", (139, 92, 246)),
        ("Instant Results", "Real-time scoring with section-wise breakdown & analysis", (245, 158, 11)),
        ("Admin Dashboard", "Monitor registrations, track progress, export reports to Excel", (236, 72, 153)),
        ("Custom Branding", "Your college logo, colors & domain for professional look", (6, 182, 212))
    ]

    y = 60
    for i, (title, desc, color) in enumerate(campus_features):
        x = 12 if i % 2 == 0 else 108
        if i > 0 and i % 2 == 0:
            y += 42

        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x, y, 90, 40, 'F')

        # Color top bar
        pdf.set_fill_color(*color)
        pdf.rect(x, y, 90, 3, 'F')

        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*DARK)
        pdf.set_xy(x + 5, y + 8)
        pdf.cell(80, 6, title)

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(x + 5, y + 18)
        pdf.multi_cell(80, 4, desc)

    # Quiz categories highlight
    pdf.set_fill_color(*ACCENT)
    pdf.rect(12, 195, 186, 45, 'F')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(12, 202)
    pdf.cell(186, 8, 'Quiz Categories Available', align='C')

    categories = [
        ("Logical Reasoning", "Pattern & analytical"),
        ("Technical MCQs", "Core CS concepts"),
        ("AI/ML Questions", "Modern tech trends"),
        ("Coding MCQs", "Programming logic")
    ]

    cat_x = 22
    for cat, sub in categories:
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(cat_x, 215)
        pdf.cell(40, 6, cat, align='C')

        pdf.set_font('Helvetica', '', 6)
        pdf.set_text_color(255, 220, 200)
        pdf.set_xy(cat_x, 223)
        pdf.cell(40, 6, sub, align='C')

        cat_x += 44

    # Stats row
    pdf.set_fill_color(255, 255, 255)
    stats_data = [("500+", "Questions"), ("3", "Difficulty Levels"), ("Instant", "Results"), ("Excel", "Export")]

    stat_x = 22
    for stat_num, stat_label in stats_data:
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(stat_x, 250, 38, 30, 'F')

        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*PRIMARY)
        pdf.set_xy(stat_x, 255)
        pdf.cell(38, 10, stat_num, align='C')

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(stat_x, 267)
        pdf.cell(38, 6, stat_label, align='C')

        stat_x += 44

    # ==================== PAGE 5: PRICING ====================
    pdf.add_page()

    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(0, 0, 210, 297, 'F')

    # Header
    pdf.set_font('Helvetica', 'B', 26)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(0, 20)
    pdf.cell(210, 12, 'Simple Pricing', align='C')

    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(0, 36)
    pdf.cell(210, 8, 'Transparent project-based pricing for institutions', align='C')

    # Main pricing card
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(30, 55, 150, 110, 'F')

    # Blue top bar
    pdf.draw_gradient(30, 55, 150, 8, PRIMARY, PRIMARY_DARK)

    # Best value badge
    pdf.set_fill_color(*ACCENT)
    pdf.rect(75, 50, 60, 14, 'F')
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(75, 52)
    pdf.cell(60, 10, 'COLLEGE SPECIAL', align='C')

    # Price
    pdf.set_font('Helvetica', 'B', 42)
    pdf.set_text_color(*PRIMARY)
    pdf.set_xy(30, 72)
    pdf.cell(150, 20, 'Rs. 20,000', align='C')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*DARK)
    pdf.set_xy(30, 95)
    pdf.cell(150, 8, 'Per Complete Project', align='C')

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(30, 107)
    pdf.cell(150, 8, '4 Students per Project Team', align='C')

    # Per student highlight
    pdf.set_fill_color(236, 253, 245)
    pdf.rect(55, 120, 100, 18, 'F')
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(22, 101, 52)
    pdf.set_xy(55, 124)
    pdf.cell(100, 10, 'Only Rs. 5,000 per student!', align='C')

    # Per student calculation
    pdf.set_fill_color(*SUCCESS)
    pdf.rect(60, 145, 90, 14, 'F')
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(60, 148)
    pdf.cell(90, 8, '70% cheaper than competitors', align='C')

    # What's included
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*DARK)
    pdf.set_xy(0, 175)
    pdf.cell(210, 10, "What's Included", align='C')

    included = [
        ("Complete Source Code", "Any technology stack"),
        ("IEEE-Format SRS", "Professional documentation"),
        ("All UML Diagrams", "5 diagram types"),
        ("50+ Page Report", "Ready for submission"),
        ("PPT Presentation", "Professional slides"),
        ("Viva Q&A Prep", "50+ questions")
    ]

    y = 190
    for i, (title, desc) in enumerate(included):
        x = 20 if i % 2 == 0 else 110
        if i > 0 and i % 2 == 0:
            y += 22

        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x, y, 80, 20, 'F')

        pdf.set_text_color(*SUCCESS)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_xy(x + 3, y + 3)
        pdf.cell(6, 6, '+')

        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(*DARK)
        pdf.cell(65, 6, title)

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(x + 9, y + 11)
        pdf.cell(68, 6, desc)

    # Payment methods
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*DARK)
    pdf.set_xy(0, 260)
    pdf.cell(210, 8, 'Payment Methods', align='C')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(0, 270)
    pdf.cell(210, 8, 'UPI  |  Razorpay  |  Net Banking  |  Credit/Debit Cards  |  Bank Transfer', align='C')

    # ==================== PAGE 6: ADVANCED FEATURES ====================
    pdf.add_page()

    pdf.set_fill_color(*WHITE)
    pdf.rect(0, 0, 210, 297, 'F')

    # Header
    pdf.draw_gradient(0, 0, 210, 45, PRIMARY, PRIMARY_DARK)

    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 10)
    pdf.cell(210, 12, 'Advanced Features', align='C')

    pdf.set_font('Helvetica', '', 10)
    pdf.set_xy(0, 26)
    pdf.cell(210, 8, 'Enterprise-grade tools for academic institutions', align='C')

    # Features grid
    adv_features = [
        ("Plagiarism Detection", "AI-powered checker ensures 100% original code. Generate reports.", (239, 68, 68)),
        ("Faculty Dashboard", "Real-time monitoring of student progress & performance analytics.", (59, 130, 246)),
        ("Batch Management", "Organize by batch, department, year. Bulk project assignment.", (16, 185, 129)),
        ("White-Label Solution", "Custom branding with your college logo, colors & domain.", (139, 92, 246)),
        ("LMS Integration", "Seamless integration with Moodle, Canvas & other LMS via API.", (245, 158, 11)),
        ("Data Security", "ISO 27001 compliant. Data encrypted & stored in India.", (6, 182, 212)),
        ("Multi-Department", "Support for CSE, IT, ECE, Mechanical with domain templates.", (236, 72, 153)),
        ("24/7 Support", "Dedicated account manager, phone support & training.", (34, 197, 94)),
    ]

    y = 52
    for i, (title, desc, color) in enumerate(adv_features):
        x = 12 if i % 2 == 0 else 108
        if i > 0 and i % 2 == 0:
            y += 38

        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(x, y, 90, 36, 'F')

        pdf.set_fill_color(*color)
        pdf.rect(x, y, 4, 36, 'F')

        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*DARK)
        pdf.set_xy(x + 8, y + 4)
        pdf.cell(78, 6, title)

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(x + 8, y + 13)
        pdf.multi_cell(78, 4, desc)

    # Trust section
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(12, 210, 186, 35, 'F')

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(12, 216)
    pdf.cell(186, 8, 'Why Institutions Trust BharatBuild', align='C')

    trust_items = ["Indian Company", "Data in India", "UGC Compliant", "No Hidden Fees"]
    trust_x = 22
    for item in trust_items:
        pdf.set_font('Helvetica', '', 8)
        pdf.set_xy(trust_x, 228)
        pdf.cell(40, 8, item, align='C')
        trust_x += 44

    # Bottom stats
    stats_row = [
        ("10,000+", "Projects"),
        ("100+", "Colleges"),
        ("50,000+", "Students"),
        ("99.9%", "Uptime")
    ]

    stat_x = 22
    for num, label in stats_row:
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(stat_x, 255, 38, 28, 'F')

        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(*PRIMARY)
        pdf.set_xy(stat_x, 259)
        pdf.cell(38, 8, num, align='C')

        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(stat_x, 269)
        pdf.cell(38, 6, label, align='C')

        stat_x += 44

    # ==================== PAGE 7: CONTACT ====================
    pdf.add_page()

    # Clean white background
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, 210, 297, 'F')

    # Top accent bar
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(0, 0, 210, 8, 'F')

    # Left side color block (matching cover)
    pdf.draw_gradient(0, 0, 75, 297, PRIMARY_DARK, PRIMARY)

    # Left strip content
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(5, 40)
    pdf.cell(65, 10, 'BHARATBUILD', align='C')

    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(*ACCENT)
    pdf.set_xy(5, 52)
    pdf.cell(65, 12, 'AI', align='C')

    # Stats on left strip
    left_stats = [("10,000+", "Projects"), ("100+", "Colleges"), ("50,000+", "Students")]
    stat_y = 90
    for num, label in left_stats:
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(5, stat_y)
        pdf.cell(65, 10, num, align='C')

        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(200, 220, 255)
        pdf.set_xy(5, stat_y + 12)
        pdf.cell(65, 6, label, align='C')

        stat_y += 35

    # Main content - right side
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(85, 25)
    pdf.cell(115, 8, 'GET STARTED TODAY')

    pdf.set_font('Helvetica', 'B', 26)
    pdf.set_text_color(*DARK)
    pdf.set_xy(85, 38)
    pdf.cell(115, 14, 'Ready to Transform')
    pdf.set_xy(85, 54)
    pdf.cell(115, 14, 'Your Institution?')

    # Orange underline
    pdf.set_fill_color(*ACCENT)
    pdf.rect(85, 72, 50, 3, 'F')

    # Description
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*GRAY)
    pdf.set_xy(85, 82)
    pdf.multi_cell(115, 5, 'Join 100+ colleges already using BharatBuild AI to deliver quality academic projects.')

    # CTA Button
    pdf.set_fill_color(*ACCENT)
    pdf.rect(85, 105, 100, 20, 'F')
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(85, 110)
    pdf.cell(100, 10, 'Schedule Free Demo', align='C')

    # Contact Section
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*DARK)
    pdf.set_xy(85, 140)
    pdf.cell(115, 8, 'CONTACT US')

    # Contact details - clean list
    contact_items = [
        ("Email", "colleges@bharatbuild.ai"),
        ("Phone", "+91 9908787055"),
        ("WhatsApp", "+91 9908787055"),
        ("Website", "www.bharatbuild.ai")
    ]

    y = 155
    for label, value in contact_items:
        pdf.set_fill_color(*LIGHT_BG)
        pdf.rect(85, y, 115, 18, 'F')

        pdf.set_fill_color(*PRIMARY)
        pdf.rect(85, y, 3, 18, 'F')

        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(92, y + 3)
        pdf.cell(40, 5, label)

        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*DARK)
        pdf.set_xy(92, y + 9)
        pdf.cell(105, 6, value)

        y += 22

    # Bottom section - What we offer summary
    pdf.set_fill_color(*DARK)
    pdf.rect(75, 255, 135, 42, 'F')

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(80, 260)
    pdf.cell(125, 6, 'COMPLETE PROJECT PACKAGE INCLUDES:')

    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(200, 210, 220)
    pdf.set_xy(80, 270)
    pdf.cell(125, 5, 'Source Code | IEEE Documentation | UML Diagrams')
    pdf.set_xy(80, 278)
    pdf.cell(125, 5, '50+ Page Report | PPT Presentation | Viva Q&A Prep')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*ACCENT)
    pdf.set_xy(80, 287)
    pdf.cell(125, 6, 'Starting at Rs. 20,000 per project')

    # Left strip bottom
    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 255, 75, 42, 'F')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 268)
    pdf.cell(75, 8, 'Proudly', align='C')
    pdf.set_xy(0, 278)
    pdf.cell(75, 8, 'Made in India', align='C')

    # Save PDF
    output_path = os.path.join(os.path.dirname(__file__), 'docs', 'BharatBuild_College_Brochure_Professional.pdf')
    pdf.output(output_path)
    print(f"PDF created successfully: {output_path}")
    return output_path


if __name__ == "__main__":
    create_brochure()
