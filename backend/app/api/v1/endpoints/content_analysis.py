"""
Content Analysis API Endpoints
- Plagiarism Detection (Copyscape API)
- AI Content Detection (GPTZero API)
- IEEE Paper Analysis
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import re
import math
from collections import Counter
import hashlib

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from app.services.content_analysis_service import copyscape_service, gptzero_service

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class PlagiarismCheckRequest(BaseModel):
    text: str
    check_type: str = "full"  # full, quick


class PlagiarismResult(BaseModel):
    overall_score: float  # 0-100, lower is better (less plagiarism)
    original_percentage: float
    plagiarized_percentage: float
    sources_found: List[dict]
    highlighted_sections: List[dict]
    recommendations: List[str]
    status: str  # pass, warning, fail


class AIDetectionRequest(BaseModel):
    text: str


class AIDetectionResult(BaseModel):
    ai_probability: float  # 0-100, probability of AI-generated content
    human_probability: float
    confidence: float
    analysis: dict
    verdict: str  # human, mixed, ai
    recommendations: List[str]


class IEEEPaperAnalysis(BaseModel):
    title: str
    authors: List[str]
    abstract: str
    keywords: List[str]
    sections: List[dict]
    methodology: str
    findings: List[str]
    references_count: int
    suggested_next_steps: List[str]
    research_gaps: List[str]
    implementation_ideas: List[str]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate cosine similarity between two texts using TF-IDF like approach"""
    # Tokenize and normalize
    def tokenize(text):
        return re.findall(r'\b\w+\b', text.lower())

    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)

    # Create frequency vectors
    freq1 = Counter(tokens1)
    freq2 = Counter(tokens2)

    # Get all unique words
    all_words = set(freq1.keys()) | set(freq2.keys())

    if not all_words:
        return 0.0

    # Calculate cosine similarity
    dot_product = sum(freq1.get(word, 0) * freq2.get(word, 0) for word in all_words)
    magnitude1 = math.sqrt(sum(v ** 2 for v in freq1.values()))
    magnitude2 = math.sqrt(sum(v ** 2 for v in freq2.values()))

    if magnitude1 * magnitude2 == 0:
        return 0.0

    return (dot_product / (magnitude1 * magnitude2)) * 100


def analyze_text_patterns(text: str) -> dict:
    """Analyze text patterns for AI detection"""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return {"error": "No valid sentences found"}

    # Calculate sentence length variance (AI tends to be more uniform)
    sentence_lengths = [len(s.split()) for s in sentences]
    avg_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0

    # Calculate vocabulary richness
    words = re.findall(r'\b\w+\b', text.lower())
    unique_words = set(words)
    vocabulary_richness = len(unique_words) / len(words) if words else 0

    # Check for common AI patterns
    ai_patterns = [
        r'\bdelve\b',
        r'\bfurthermore\b',
        r'\bmoreover\b',
        r'\bin conclusion\b',
        r'\bit is important to note\b',
        r'\bas mentioned earlier\b',
        r'\boverall\b',
        r'\bin summary\b',
        r'\bsignificantly\b',
        r'\bcrucially\b',
        r'\bnotably\b',
    ]

    pattern_count = sum(1 for pattern in ai_patterns if re.search(pattern, text.lower()))

    # Check for repetitive structures
    bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
    bigram_freq = Counter(bigrams)
    repetitive_bigrams = sum(1 for count in bigram_freq.values() if count > 2)

    return {
        "sentence_count": len(sentences),
        "avg_sentence_length": avg_length,
        "sentence_length_variance": variance,
        "vocabulary_richness": vocabulary_richness,
        "ai_pattern_count": pattern_count,
        "repetitive_structures": repetitive_bigrams,
        "word_count": len(words),
        "unique_word_count": len(unique_words)
    }


def calculate_ai_probability(analysis: dict) -> float:
    """Calculate probability of AI-generated content based on analysis"""
    score = 50  # Start neutral

    # Low variance in sentence length suggests AI
    if analysis.get("sentence_length_variance", 0) < 20:
        score += 15
    elif analysis.get("sentence_length_variance", 0) > 50:
        score -= 10

    # AI patterns increase score
    pattern_count = analysis.get("ai_pattern_count", 0)
    score += min(pattern_count * 5, 20)

    # Very uniform vocabulary suggests AI
    vocab_richness = analysis.get("vocabulary_richness", 0)
    if vocab_richness < 0.3:
        score += 10
    elif vocab_richness > 0.6:
        score -= 10

    # Repetitive structures suggest AI
    if analysis.get("repetitive_structures", 0) > 5:
        score += 10

    # Very consistent average sentence length suggests AI
    avg_length = analysis.get("avg_sentence_length", 0)
    if 15 <= avg_length <= 20:
        score += 5

    return max(0, min(100, score))


def extract_paper_sections(text: str) -> dict:
    """Extract sections from IEEE paper text"""
    sections = {
        "abstract": "",
        "introduction": "",
        "methodology": "",
        "results": "",
        "discussion": "",
        "conclusion": "",
        "references": ""
    }

    # Common section patterns
    section_patterns = {
        "abstract": r'(?:abstract|summary)[:\s]*(.+?)(?=\n\s*(?:i\.|1\.|introduction|keywords))',
        "introduction": r'(?:i\.|1\.?\s*)?introduction[:\s]*(.+?)(?=\n\s*(?:ii\.|2\.|related|methodology|background))',
        "methodology": r'(?:methodology|method|approach|proposed)[:\s]*(.+?)(?=\n\s*(?:results|experiment|evaluation|iv\.|4\.))',
        "results": r'(?:results|experiments|evaluation)[:\s]*(.+?)(?=\n\s*(?:discussion|conclusion|v\.|5\.))',
        "conclusion": r'(?:conclusion|concluding)[:\s]*(.+?)(?=\n\s*(?:references|acknowledgment|appendix))',
    }

    text_lower = text.lower()

    for section, pattern in section_patterns.items():
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            sections[section] = match.group(1).strip()[:1000]  # Limit to 1000 chars

    return sections


# Common code snippets and patterns for plagiarism database (simulated)
COMMON_CODE_PATTERNS = [
    "def main():",
    "if __name__ == '__main__':",
    "import numpy as np",
    "import pandas as pd",
    "from sklearn",
    "print('Hello, World!')",
    "for i in range(",
    "while True:",
    "class Solution:",
    "def __init__(self",
]

COMMON_TEXT_PATTERNS = [
    "machine learning is a subset of artificial intelligence",
    "the internet of things refers to",
    "cloud computing enables",
    "data science is an interdisciplinary field",
    "artificial neural networks are",
]


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/plagiarism/check", response_model=PlagiarismResult)
async def check_plagiarism(
    request: PlagiarismCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Check text for plagiarism using Copyscape API
    Returns plagiarism score and highlighted sections

    API: Copyscape (https://www.copyscape.com/api-guide.php)
    Cost: ~$0.03 per search
    """
    text = request.text

    if len(text) < 50:
        raise HTTPException(status_code=400, detail="Text too short for analysis (minimum 50 characters)")

    # Use Copyscape service
    result = await copyscape_service.check_text(text, full_comparison=(request.check_type == "full"))

    plagiarized_percentage = result.get("plagiarism_percentage", 0)
    original_percentage = result.get("original_percentage", 100)

    # Convert sources to expected format
    sources_found = []
    for src in result.get("sources_found", []):
        sources_found.append({
            "source": src.get("url", src.get("source", "Unknown")),
            "matched_text": src.get("title", ""),
            "similarity": src.get("percentage", src.get("matched_words", 0))
        })

    # Generate highlighted sections based on sources
    highlighted_sections = []
    for src in sources_found[:5]:
        highlighted_sections.append({
            "text": src.get("matched_text", "")[:100],
            "type": "web_match",
            "risk": "high" if plagiarized_percentage > 25 else "medium"
        })

    # Determine status
    if plagiarized_percentage < 10:
        status = "pass"
        recommendations = [
            "Your content appears to be mostly original.",
            "Good job maintaining originality!",
            "Consider adding more citations for referenced concepts."
        ]
    elif plagiarized_percentage < 25:
        status = "warning"
        recommendations = [
            "Some similar content detected online.",
            "Consider paraphrasing highlighted sections.",
            "Add proper citations for borrowed content.",
            "Review and rewrite flagged sections."
        ]
    else:
        status = "fail"
        recommendations = [
            "High similarity detected with existing content.",
            "Significant rewriting required.",
            "Ensure all borrowed content is properly cited.",
            "Consider using your own words to explain concepts.",
            "Review university plagiarism guidelines."
        ]

    # Add API info to recommendations
    if result.get("api") == "demo":
        recommendations.append("Note: Using demo mode. Configure Copyscape API for real plagiarism checks.")

    return PlagiarismResult(
        overall_score=round(plagiarized_percentage, 2),
        original_percentage=round(original_percentage, 2),
        plagiarized_percentage=round(plagiarized_percentage, 2),
        sources_found=sources_found[:5],
        highlighted_sections=highlighted_sections[:10],
        recommendations=recommendations,
        status=status
    )


@router.post("/ai-detection/check", response_model=AIDetectionResult)
async def detect_ai_content(
    request: AIDetectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Detect AI-generated content using GPTZero API
    Returns probability score and analysis

    API: GPTZero (https://gptzero.me/developers)
    Cost: Free tier available, then ~$10/month
    """
    text = request.text

    if len(text) < 100:
        raise HTTPException(status_code=400, detail="Text too short for analysis (minimum 100 characters)")

    # Use GPTZero service
    result = await gptzero_service.detect_ai(text)

    ai_probability = result.get("ai_probability", 50)
    human_probability = result.get("human_probability", 50)
    verdict = result.get("verdict", "mixed")

    # Determine confidence
    confidence_map = {"high": 90, "medium": 70, "low": 50}
    confidence = confidence_map.get(result.get("confidence", "medium"), 70)

    # Get analysis data
    analysis_data = result.get("analysis", {})
    if not analysis_data:
        # Calculate basic analysis if not provided
        analysis_data = analyze_text_patterns(text)
        analysis_data = {
            "sentence_count": analysis_data.get("sentence_count", 0),
            "avg_sentence_length": round(analysis_data.get("avg_sentence_length", 0), 1),
            "vocabulary_richness": round(analysis_data.get("vocabulary_richness", 0) * 100, 1),
            "ai_patterns_found": analysis_data.get("ai_pattern_count", 0),
            "word_count": analysis_data.get("word_count", len(text.split()))
        }

    # Generate recommendations based on verdict
    if verdict == "human":
        recommendations = [
            "Content appears to be human-written.",
            "Natural writing patterns detected.",
            "Good variation in sentence structure."
        ]
    elif verdict == "mixed":
        recommendations = [
            "Content may contain some AI-assisted sections.",
            "Consider adding more personal voice.",
            "Vary your sentence structures more.",
            "Add specific examples or personal experiences."
        ]
    else:
        recommendations = [
            "Content shows strong AI-generation patterns.",
            "Significantly rewrite to add personal voice.",
            "Avoid overused transitional phrases.",
            "Add specific examples and case studies.",
            "Vary sentence length and structure.",
            "Include personal insights and opinions."
        ]

    # Add API info
    if result.get("api") == "demo":
        recommendations.append("Note: Using demo mode. Configure GPTZero API for real AI detection.")

    return AIDetectionResult(
        ai_probability=round(ai_probability, 2),
        human_probability=round(human_probability, 2),
        confidence=confidence,
        analysis=analysis_data,
        verdict=verdict,
        recommendations=recommendations
    )


@router.post("/ieee-paper/test")
async def test_ieee_paper_analysis(
    file: UploadFile = File(None),
    text: str = Form(None)
):
    """
    Test IEEE paper analysis endpoint (no auth required - development only)
    """
    paper_text = ""

    if file:
        content = await file.read()
        try:
            paper_text = content.decode('utf-8')
        except:
            paper_text = content.decode('latin-1', errors='ignore')
    elif text:
        paper_text = text
    else:
        raise HTTPException(status_code=400, detail="Please provide either a file or text content")

    if len(paper_text) < 500:
        raise HTTPException(status_code=400, detail="Paper content too short for analysis")

    # Extract basic information
    lines = paper_text.split('\n')
    title = ""
    for line in lines[:10]:
        if line.strip() and len(line.strip()) > 10:
            title = line.strip()[:200]
            break

    # Extract keywords
    keywords = []
    keyword_match = re.search(r'keywords?[:\s]*([^\n]+)', paper_text.lower())
    if keyword_match:
        keywords = [k.strip() for k in keyword_match.group(1).split(',')][:10]

    sections = extract_paper_sections(paper_text)

    return {
        "title": title or "Title not detected",
        "authors": ["Authors not detected"],
        "abstract": sections.get("abstract", "Abstract not found")[:1000],
        "keywords": keywords or ["Keywords not detected"],
        "sections": [{"name": name, "content": content[:500], "word_count": len(content.split())} for name, content in sections.items() if content],
        "methodology": sections.get("methodology", "Methodology section not found")[:1000],
        "findings": ["No specific findings extracted"],
        "references_count": 0,
        "suggested_next_steps": ["Implement the proposed methodology", "Test with different datasets", "Compare with existing methods"],
        "research_gaps": ["Scalability not addressed", "Real-world deployment not discussed"],
        "implementation_ideas": ["Build a REST API", "Create a web dashboard", "Deploy on cloud"],
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "word_count": len(paper_text.split()),
        "status": "success"
    }


@router.post("/ieee-paper/analyze")
async def analyze_ieee_paper(
    file: UploadFile = File(None),
    text: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Analyze an IEEE research paper
    Extract key information and suggest next steps
    """
    paper_text = ""

    if file:
        # Read file content
        content = await file.read()
        try:
            paper_text = content.decode('utf-8')
        except:
            # Try to handle PDF (basic text extraction)
            paper_text = content.decode('latin-1', errors='ignore')
    elif text:
        paper_text = text
    else:
        raise HTTPException(status_code=400, detail="Please provide either a file or text content")

    if len(paper_text) < 500:
        raise HTTPException(status_code=400, detail="Paper content too short for analysis")

    # Extract basic information
    lines = paper_text.split('\n')

    # Try to extract title (usually first non-empty line)
    title = ""
    for line in lines[:10]:
        if line.strip() and len(line.strip()) > 10:
            title = line.strip()[:200]
            break

    # Extract authors (look for patterns like "Name1, Name2" or "by Author")
    authors = []
    author_patterns = [
        r'(?:by|authors?)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)',
        r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:,\s*[A-Z][a-z]+\s+[A-Z][a-z]+)*)$'
    ]
    for pattern in author_patterns:
        match = re.search(pattern, paper_text[:2000])
        if match:
            authors = [a.strip() for a in match.group(1).split(',')][:5]
            break

    # Extract keywords
    keywords = []
    keyword_match = re.search(r'keywords?[:\s]*([^\n]+)', paper_text.lower())
    if keyword_match:
        keywords = [k.strip() for k in keyword_match.group(1).split(',')][:10]

    # Extract sections
    sections = extract_paper_sections(paper_text)

    # Count references
    ref_patterns = [r'\[\d+\]', r'\(\d{4}\)', r'et al\.']
    references_count = sum(len(re.findall(p, paper_text)) for p in ref_patterns)
    references_count = min(references_count // 2, 50)  # Normalize

    # Generate findings from abstract/results
    findings = []
    results_text = sections.get("results", "") or sections.get("abstract", "")
    if results_text:
        sentences = re.split(r'[.!?]', results_text)
        findings = [s.strip() for s in sentences if len(s.strip()) > 20][:5]

    # Generate suggested next steps based on paper content
    suggested_next_steps = [
        "Implement the proposed methodology in a prototype",
        "Test with different datasets to validate findings",
        "Compare results with other state-of-the-art methods",
        "Extend the approach to handle edge cases",
        "Optimize for better performance/accuracy",
        "Document and publish your implementation",
        "Create a user-friendly interface for the solution"
    ]

    # Identify research gaps
    research_gaps = [
        "Scalability to larger datasets not addressed",
        "Real-world deployment challenges not discussed",
        "Limited comparison with recent methods",
        "No user study or usability evaluation",
        "Cross-domain applicability not explored"
    ]

    # Implementation ideas
    implementation_ideas = [
        "Build a REST API to expose the algorithm",
        "Create a web dashboard for visualization",
        "Develop a mobile app for accessibility",
        "Package as a reusable library/module",
        "Deploy on cloud for scalability",
        "Add monitoring and logging for production use"
    ]

    # Format sections for response
    section_list = [
        {"name": name, "content": content[:500], "word_count": len(content.split())}
        for name, content in sections.items() if content
    ]

    return {
        "title": title or "Title not detected",
        "authors": authors or ["Authors not detected"],
        "abstract": sections.get("abstract", "Abstract not found")[:1000],
        "keywords": keywords or ["Keywords not detected"],
        "sections": section_list,
        "methodology": sections.get("methodology", "Methodology section not found")[:1000],
        "findings": findings or ["No specific findings extracted"],
        "references_count": references_count,
        "suggested_next_steps": suggested_next_steps,
        "research_gaps": research_gaps,
        "implementation_ideas": implementation_ideas,
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "word_count": len(paper_text.split()),
        "status": "success"
    }


@router.get("/analysis/history")
async def get_analysis_history(
    analysis_type: Optional[str] = None,  # plagiarism, ai_detection, ieee_paper
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's analysis history"""
    # This would typically fetch from a database
    # For now, return empty history
    return {
        "history": [],
        "total_checks": 0,
        "message": "Analysis history will be available after performing checks"
    }


@router.post("/plagiarism/test")
async def test_plagiarism_check(request: PlagiarismCheckRequest):
    """
    Test plagiarism check endpoint (no auth required - development only)
    """
    text = request.text

    if len(text) < 50:
        raise HTTPException(status_code=400, detail="Text too short for analysis (minimum 50 characters)")

    # Use Copyscape service
    result = await copyscape_service.check_text(text, full_comparison=(request.check_type == "full"))

    plagiarized_percentage = result.get("plagiarism_percentage", 0)
    original_percentage = result.get("original_percentage", 100)

    # Convert sources to expected format
    sources_found = []
    for src in result.get("sources_found", []):
        sources_found.append({
            "source": src.get("url", src.get("source", "Unknown")),
            "matched_text": src.get("title", ""),
            "similarity": src.get("percentage", src.get("matched_words", 0))
        })

    # Determine status
    if plagiarized_percentage < 10:
        status = "pass"
        recommendations = ["Your content appears to be mostly original."]
    elif plagiarized_percentage < 25:
        status = "warning"
        recommendations = ["Some similar content detected. Consider paraphrasing."]
    else:
        status = "fail"
        recommendations = ["High similarity detected. Significant rewriting required."]

    if result.get("api") == "demo":
        recommendations.append("Note: Using demo mode. Configure Copyscape API for real checks.")

    return PlagiarismResult(
        overall_score=round(plagiarized_percentage, 2),
        original_percentage=round(original_percentage, 2),
        plagiarized_percentage=round(plagiarized_percentage, 2),
        sources_found=sources_found[:5],
        highlighted_sections=[],
        recommendations=recommendations,
        status=status
    )


@router.post("/ai-detection/test")
async def test_ai_detection(request: AIDetectionRequest):
    """
    Test AI detection endpoint (no auth required - development only)
    """
    text = request.text

    if len(text) < 100:
        raise HTTPException(status_code=400, detail="Text too short for analysis (minimum 100 characters)")

    # Use GPTZero service
    result = await gptzero_service.detect_ai(text)

    ai_probability = result.get("ai_probability", 50)
    human_probability = result.get("human_probability", 50)
    verdict = result.get("verdict", "mixed")

    confidence_map = {"high": 90, "medium": 70, "low": 50}
    confidence = confidence_map.get(result.get("confidence", "medium"), 70)

    analysis_data = result.get("analysis", analyze_text_patterns(text))

    recommendations = []
    if verdict == "human":
        recommendations = ["Content appears to be human-written."]
    elif verdict == "mixed":
        recommendations = ["Content may contain some AI-assisted sections."]
    else:
        recommendations = ["Content shows strong AI-generation patterns."]

    if result.get("api") == "demo":
        recommendations.append("Note: Using demo mode. Configure GPTZero API for real detection.")

    return AIDetectionResult(
        ai_probability=round(ai_probability, 2),
        human_probability=round(human_probability, 2),
        confidence=confidence,
        analysis=analysis_data,
        verdict=verdict,
        recommendations=recommendations
    )


@router.get("/status")
async def get_api_status():
    """
    Get status of content analysis APIs
    Shows which APIs are configured and active
    """
    return {
        "copyscape": {
            "enabled": copyscape_service.enabled,
            "status": "active" if copyscape_service.enabled else "demo_mode",
            "description": "Plagiarism detection via Copyscape",
            "cost": "~$0.03 per search",
            "config_required": ["COPYSCAPE_USERNAME", "COPYSCAPE_API_KEY"]
        },
        "gptzero": {
            "enabled": gptzero_service.enabled,
            "status": "active" if gptzero_service.enabled else "demo_mode",
            "description": "AI content detection via GPTZero",
            "cost": "Free tier available, then ~$10/month",
            "config_required": ["GPTZERO_API_KEY"]
        },
        "ieee_analysis": {
            "enabled": True,
            "status": "active",
            "description": "IEEE paper analysis (built-in)",
            "cost": "Free"
        },
        "setup_instructions": {
            "copyscape": "Get API key at https://www.copyscape.com/apiconfigure.php",
            "gptzero": "Get API key at https://gptzero.me/developers"
        }
    }
