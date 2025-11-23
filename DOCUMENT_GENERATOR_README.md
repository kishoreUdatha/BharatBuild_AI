# 📚 Academic Document Generator - User Guide

## Overview

This is **AGENT 5 - DOCSPACK AGENT**, an intelligent system that automatically generates complete academic documentation for student projects (B.Tech/MCA/M.Tech) by analyzing your codebase.

### What It Generates

✅ **8 Complete Documents:**

1. **Abstract** (3-4 pages) - Background, objectives, methodology, results
2. **SRS Document** (20+ pages) - IEEE 830-1998 compliant requirements specification
3. **UML Diagrams** - Class, Sequence, ER, Use Case diagrams in Mermaid format
4. **ER Diagram** - Detailed database schema with relationships
5. **Project Report** (30+ pages) - Complete 8-chapter academic report
6. **PPT Slides** (15-18 slides) - Presentation content
7. **Viva Questions** (25+ Q&A) - Comprehensive viva voce preparation
8. **Output Explanation** - Setup, run, and deployment guide

---

## How It Works

```
Your Project Codebase
         ↓
   ProjectAnalyzer
   (analyzes files, tech stack, structure)
         ↓
   DocsPackAgent
   (generates docs using Claude AI)
         ↓
   8 Markdown Files
   (ready for submission)
```

### The Agent System

**DocsPackAgent** uses Claude AI with a specialized prompt:

```xml
<documents>
  <abstract>...</abstract>
  <srs>...</srs>
  <uml>...</uml>
  <erd>...</erd>
  <report>...</report>
  <ppt_slides>...</ppt_slides>
  <viva>...</viva>
  <output_explanation>...</output_explanation>
</documents>
```

**Rules:**
- No code in documents
- Clean, academic-standard content
- All documents are consistent with each other
- Based on actual project analysis (not static templates)

---

## Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Anthropic API Key** (get from https://console.anthropic.com)
3. Your project codebase

### Setup

**Step 1: Set API Key**

Create `backend/.env` file:

```bash
ANTHROPIC_API_KEY=your_api_key_here
```

**Step 2: Install Dependencies**

```bash
cd backend
pip install -r requirements.txt
```

**Step 3: Run the Generator**

```bash
# From project root
python generate_academic_docs.py
```

### Output

Documents will be generated in `academic_documents/` folder:

```
academic_documents/
├── 01_ABSTRACT.md
├── 02_SRS_DOCUMENT.md
├── 03_UML_DIAGRAMS.md
├── 04_ER_DIAGRAM.md
├── 05_PROJECT_REPORT.md
├── 06_PPT_SLIDES.md
├── 07_VIVA_QUESTIONS.md
└── 08_OUTPUT_EXPLANATION.md
```

---

## Project Analysis

The **ProjectAnalyzer** automatically detects:

### 1. Project Name & Purpose
- From `README.md` first line and description
- Fallback to directory name

### 2. Domain Classification
- E-Commerce (keywords: shop, cart, product)
- Healthcare (keywords: patient, doctor, medical)
- Education (keywords: student, course, learning)
- AI/ML (keywords: agent, llm, ml)
- Finance (keywords: payment, transaction, banking)

### 3. Technology Stack

**Backend Detection:**
- `requirements.txt` → Python packages
  - FastAPI, Django, Flask
  - SQLAlchemy, Celery, Redis

**Frontend Detection:**
- `package.json` → Node packages
  - Next.js, React, Vue
  - Tailwind CSS

**Database Detection:**
- `.env.example` → Database URLs
  - PostgreSQL, MongoDB, MySQL
  - Redis

### 4. Architecture
- Microservices (frontend/ + backend/ + API structure)
- Client-Server (frontend/ + backend/)
- Monolithic

### 5. Modules
- From `backend/app/api/v1/endpoints/*.py`
- Or `backend/app/modules/*/`

### 6. Features
- From `README.md` Features section
- Or inferred from modules

### 7. Database Schema
- From `backend/app/models/*.py`
- Table names and relationships

---

## Customization

### Generate Specific Documents

Instead of all 8 documents, generate specific ones:

```python
from app.modules.agents.docspack_agent import DocsPackAgent
from app.modules.agents.project_analyzer import ProjectAnalyzer

# Analyze project
analyzer = ProjectAnalyzer("path/to/project")
analysis = analyzer.analyze()

# Initialize agent
agent = DocsPackAgent()

# Generate only Abstract (faster)
abstract = await agent.generate_abstract(analysis)

# Generate only SRS
srs = await agent.generate_srs(analysis)

# Generate only UML
uml = await agent.generate_uml(analysis)

# Generate only Viva Q&A
viva = await agent.generate_viva_qa(analysis)
```

### Manual Project Analysis

If automatic analysis doesn't work, provide manual analysis:

```python
project_analysis = {
    "project_name": "Hospital Management System",
    "project_purpose": "Digital platform for managing hospital operations",
    "domain": "Healthcare",
    "technology_stack": {
        "backend": {
            "framework": "FastAPI",
            "language": "Python 3.11",
            "database": "PostgreSQL 15"
        },
        "frontend": {
            "framework": "Next.js 14",
            "language": "TypeScript 5"
        }
    },
    "architecture": "Microservices with REST API",
    "database_schema": {
        "tables": ["patients", "doctors", "appointments", "prescriptions"],
        "relationships": {
            "patients_appointments": "1:N",
            "doctors_appointments": "1:N"
        }
    },
    "modules": [
        {"name": "Patient Management", "description": "Register, update patients"},
        {"name": "Appointment Booking", "description": "Schedule appointments"},
        {"name": "Prescription", "description": "Manage prescriptions"}
    ],
    "features": [
        "Patient registration and records",
        "Doctor profiles",
        "Appointment scheduling",
        "Electronic prescriptions",
        "Billing and payments"
    ],
    "file_structure": {}
}

# Generate documents
agent = DocsPackAgent()
documents = await agent.generate_documents(project_analysis)
```

---

## Usage Examples

### Example 1: E-Commerce Project

```bash
# Your project structure:
my-ecommerce/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           ├── products.py
│   │   │           ├── orders.py
│   │   │           └── users.py
│   │   └── models/
│   │       ├── user.py
│   │       ├── product.py
│   │       └── order.py
│   └── requirements.txt  # fastapi, sqlalchemy, redis
├── frontend/
│   ├── src/
│   └── package.json  # next, react, tailwindcss
└── README.md

# Run generator:
cd my-ecommerce
python generate_academic_docs.py

# Output:
# ✅ Detected: E-Commerce domain
# ✅ Tech Stack: FastAPI + Next.js + PostgreSQL
# ✅ Modules: Products, Orders, Users
# ✅ Features: Shopping cart, payment processing, etc.
# ✅ Generated 8 documents in academic_documents/
```

### Example 2: Custom Analysis

```python
# For projects without standard structure
import asyncio
from app.modules.agents.docspack_agent import DocsPackAgent

async def generate_for_custom_project():
    analysis = {
        "project_name": "AI Chatbot",
        "project_purpose": "Customer support chatbot using NLP",
        "domain": "Artificial Intelligence",
        "technology_stack": {
            "backend": {"framework": "Flask", "language": "Python 3.10"},
            "frontend": {"framework": "React", "language": "JavaScript"},
            "database": {"primary": "MongoDB"}
        },
        "architecture": "Microservices with message queue",
        "features": [
            "Natural language understanding",
            "Intent classification",
            "Multi-turn conversations",
            "Admin dashboard"
        ],
        "modules": [],
        "database_schema": {},
        "file_structure": {}
    }

    agent = DocsPackAgent()
    docs = await agent.generate_documents(analysis)

    # Save
    import os
    os.makedirs("academic_documents", exist_ok=True)

    with open("academic_documents/01_ABSTRACT.md", "w") as f:
        f.write(docs["abstract"])

    # ... save other docs

    print("✅ Documents generated!")

asyncio.run(generate_for_custom_project())
```

---

## Converting Documents

### Markdown to PDF

**Using Pandoc:**

```bash
# Install Pandoc: https://pandoc.org/installing.html

# Convert single file
pandoc 05_PROJECT_REPORT.md -o Project_Report.pdf

# With custom styling
pandoc 05_PROJECT_REPORT.md -o Project_Report.pdf \
  --pdf-engine=xelatex \
  --toc \
  --number-sections
```

### Markdown to DOCX

```bash
pandoc 02_SRS_DOCUMENT.md -o SRS.docx
```

### UML Diagrams to Images

1. Open https://mermaid.live
2. Copy diagram code from `03_UML_DIAGRAMS.md`
3. Export as PNG/SVG

### PPT Slides to PowerPoint

**Option 1: Manual**
- Copy content from `06_PPT_SLIDES.md`
- Paste into PowerPoint
- Add formatting and images

**Option 2: Marp (Markdown Presentations)**

```bash
# Install Marp CLI
npm install -g @marp-team/marp-cli

# Convert to PPT
marp 06_PPT_SLIDES.md --pptx
```

---

## API Integration

Use the agent in your own FastAPI endpoints:

```python
from fastapi import APIRouter, BackgroundTasks
from app.modules.agents.project_analyzer import ProjectAnalyzer
from app.modules.agents.docspack_agent import DocsPackAgent

router = APIRouter()

@router.post("/generate-docs")
async def generate_academic_docs(
    project_id: str,
    background_tasks: BackgroundTasks
):
    """
    Generate academic documents for a project
    """

    # Get project from database
    project = get_project(project_id)

    # Analyze
    analyzer = ProjectAnalyzer(project.source_code_path)
    analysis = analyzer.analyze()

    # Generate in background
    background_tasks.add_task(
        generate_and_save_docs,
        project_id,
        analysis
    )

    return {"message": "Document generation started"}

async def generate_and_save_docs(project_id: str, analysis: dict):
    agent = DocsPackAgent()
    documents = await agent.generate_documents(analysis)

    # Upload to S3
    for doc_type, content in documents.items():
        upload_to_s3(
            f"projects/{project_id}/docs/{doc_type}.md",
            content
        )
```

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY not found"

**Solution:**
```bash
# Create backend/.env file
echo "ANTHROPIC_API_KEY=sk-ant-..." > backend/.env
```

### Issue: "Module not found: app.modules.agents"

**Solution:**
```bash
# Ensure you're running from project root
cd C:\Users\KishoreUdatha\IdeaProjects\BharatBuild_AI
python generate_academic_docs.py

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:./backend"
```

### Issue: "Analysis incomplete - missing modules"

**Solution:**
- Ensure your project has `backend/app/api/` or `backend/app/modules/`
- Or provide manual analysis (see Customization section)

### Issue: "Documents too generic"

**Solution:**
- Add detailed README.md with Features section
- Add comments in code explaining modules
- Provide manual analysis with specific details

---

## Cost Estimation

### Claude API Costs

- **Abstract:** ~2,000 tokens → $0.01
- **SRS:** ~8,000 tokens → $0.04
- **UML:** ~4,000 tokens → $0.02
- **ER Diagram:** ~3,000 tokens → $0.015
- **Report:** ~12,000 tokens → $0.06
- **PPT:** ~4,000 tokens → $0.02
- **Viva:** ~6,000 tokens → $0.03
- **Output Explanation:** ~3,000 tokens → $0.015

**Total per project:** ~$0.20 - $0.30

(Using Claude 3.5 Sonnet: $3/1M input tokens, $15/1M output tokens)

---

## Best Practices

### 1. Write Good README

```markdown
# Project Name

Brief description of what the project does.

## Features

- User authentication with JWT
- Product catalog with search
- Shopping cart and checkout
- Payment processing (Razorpay)
- Admin dashboard

## Tech Stack

- Backend: FastAPI, PostgreSQL
- Frontend: Next.js, Tailwind CSS
- Deployment: Docker
```

### 2. Organize Code Properly

```
project/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # Clear endpoint files
│   │   └── models/            # Database models
│   └── requirements.txt
├── frontend/
│   └── package.json
└── README.md
```

### 3. Use Descriptive Names

- ✅ `user_authentication.py`
- ✅ `product_catalog.py`
- ❌ `utils.py`
- ❌ `helpers.py`

### 4. Review & Customize

Generated documents are 90% ready. Always:
- Review for accuracy
- Add project-specific details
- Customize examples
- Add your college/university name
- Update guide names and dates

---

## FAQ

**Q: Can I use this for non-Python projects?**
A: Yes! Provide manual analysis with your tech stack. The agent works with any stack.

**Q: Will it read my actual code?**
A: No. It analyzes file structure, package.json, requirements.txt, README - not actual code logic.

**Q: Can I generate docs for existing projects?**
A: Yes! Point the analyzer to any project directory.

**Q: Is it suitable for commercial projects?**
A: It's designed for academic projects. For commercial, review and customize heavily.

**Q: How accurate are the documents?**
A: 85-90% accurate based on available information. Always review and customize.

**Q: Can I modify the agent's behavior?**
A: Yes! Edit `docspack_agent.py` system prompt and templates.

---

## Support

For issues or questions:
1. Check this README first
2. Review generated `academic_documents/` for examples
3. Check Claude API status: https://status.anthropic.com
4. Open issue on GitHub (if open source)

---

## License

This agent is part of BharatBuild AI platform.
Generated documents are yours to use for academic purposes.

---

**Happy Document Generating! 🎓📚**
