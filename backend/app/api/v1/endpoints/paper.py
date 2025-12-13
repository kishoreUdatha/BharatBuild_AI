"""
IEEE Paper Upload API - Upload research papers for project generation
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import json
import io
import logging

# PDF parsing
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import pdfplumber
    PDFPLUMBER_SUPPORT = True
except ImportError:
    PDFPLUMBER_SUPPORT = False

from app.core.database import get_db
from app.core.logging_config import logger
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.modules.agents.paper_analyzer_agent import paper_analyzer_agent
from app.core.types import generate_uuid
router = APIRouter()

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF using available libraries"""

    text = ""

    # Try pdfplumber first (better quality)
    if PDFPLUMBER_SUPPORT:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using pdfplumber")
                return text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")

    # Fallback to PyPDF2
    if PDF_SUPPORT:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using PyPDF2")
                return text
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")

    raise ValueError("Could not extract text from PDF. Please ensure the PDF contains readable text (not scanned images).")


@router.post("/upload")
async def upload_paper(
    file: UploadFile = File(...),
    paper_title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an IEEE/research paper PDF for analysis.
    Returns paper analysis with extracted requirements.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read file
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    # Check PDF support
    if not PDF_SUPPORT and not PDFPLUMBER_SUPPORT:
        raise HTTPException(
            status_code=500,
            detail="PDF parsing not available. Install PyPDF2 or pdfplumber: pip install PyPDF2 pdfplumber"
        )

    try:
        # Extract text from PDF
        paper_text = extract_text_from_pdf(content)

        if len(paper_text) < 500:
            raise HTTPException(
                status_code=400,
                detail="Could not extract enough text from PDF. Please ensure it's a text-based PDF (not scanned)."
            )

        # Get paper title from filename if not provided
        if not paper_title:
            paper_title = file.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')

        return {
            "success": True,
            "paper_title": paper_title,
            "text_length": len(paper_text),
            "estimated_tokens": len(paper_text) // 4,
            "preview": paper_text[:1000] + "..." if len(paper_text) > 1000 else paper_text,
            "message": "Paper uploaded successfully. Use /analyze endpoint to get project requirements."
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Paper upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/analyze")
async def analyze_paper(
    file: UploadFile = File(...),
    paper_title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze an IEEE paper and stream the analysis results.
    Returns structured project requirements.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    try:
        paper_text = extract_text_from_pdf(content)

        if not paper_title:
            paper_title = file.filename.replace('.pdf', '').replace('_', ' ')

        async def stream_analysis():
            try:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing IEEE paper...'})}\n\n"
                yield f"data: {json.dumps({'type': 'info', 'paper_title': paper_title, 'text_length': len(paper_text)})}\n\n"

                async for chunk in paper_analyzer_agent.analyze_paper(paper_text, paper_title):
                    yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            stream_analysis(),
            media_type="text/event-stream"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate-project")
async def generate_project_from_paper(
    file: UploadFile = File(...),
    paper_title: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Full workflow: Upload paper → Analyze → Generate project prompt → Create project.
    This creates a project ready for the Bolt workflow.
    """
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    try:
        paper_text = extract_text_from_pdf(content)

        if not paper_title:
            paper_title = file.filename.replace('.pdf', '').replace('_', ' ')

        if not project_name:
            # Generate project name from paper title
            project_name = paper_title[:50].title().replace(' ', '')

        async def stream_generation():
            try:
                # Step 1: Analyze paper
                yield f"data: {json.dumps({'type': 'status', 'message': 'Step 1/3: Analyzing IEEE paper...', 'step': 1})}\n\n"

                analysis = await paper_analyzer_agent.analyze_paper_json(paper_text, paper_title)

                yield f"data: {json.dumps({'type': 'analysis', 'data': analysis})}\n\n"

                # Step 2: Generate project prompt
                yield f"data: {json.dumps({'type': 'status', 'message': 'Step 2/3: Generating project requirements...', 'step': 2})}\n\n"

                project_prompt = paper_analyzer_agent.generate_project_prompt(analysis)

                yield f"data: {json.dumps({'type': 'prompt', 'text': project_prompt})}\n\n"

                # Step 3: Create project record
                yield f"data: {json.dumps({'type': 'status', 'message': 'Step 3/3: Creating project...', 'step': 3})}\n\n"

                project_id = str(generate_uuid())
                project = Project(
                    id=project_id,
                    name=project_name,
                    description=f"IEEE Paper Implementation: {paper_title}",
                    user_id=current_user.id,
                    status="paper_analyzed",
                    project_type="academic"
                )
                db.add(project)
                await db.commit()

                yield f"data: {json.dumps({'type': 'project_created', 'project_id': project_id, 'project_name': project_name})}\n\n"

                # Final result
                yield f"data: {json.dumps({'type': 'done', 'project_id': project_id, 'prompt': project_prompt, 'analysis': analysis})}\n\n"

            except Exception as e:
                logger.error(f"Project generation error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            stream_generation(),
            media_type="text/event-stream"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/supported-formats")
async def get_supported_formats():
    """Get information about supported paper formats"""
    return {
        "supported_formats": ["PDF"],
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "pdf_support": {
            "pypdf2": PDF_SUPPORT,
            "pdfplumber": PDFPLUMBER_SUPPORT
        },
        "recommendations": [
            "Upload text-based PDFs (not scanned images)",
            "IEEE format papers work best",
            "Include abstract, methodology, and architecture sections",
            "Papers with clear system diagrams provide better results"
        ],
        "supported_domains": [
            "Machine Learning / Deep Learning",
            "Web Applications",
            "Mobile Applications",
            "IoT Systems",
            "Blockchain",
            "Computer Vision",
            "Natural Language Processing",
            "Data Analytics"
        ]
    }
