"""
Paper Analyzer Agent - Extracts implementation requirements from IEEE/research papers
"""

import json
import logging
import re
from typing import Dict, Any, AsyncGenerator, Optional
from pathlib import Path

from app.utils.claude_client import claude_client

logger = logging.getLogger(__name__)

# Token limits
MAX_PAPER_TOKENS = 30000  # ~120KB of text
CHARS_PER_TOKEN = 4


class PaperAnalyzerAgent:
    """Agent for analyzing IEEE papers and extracting project requirements"""

    def __init__(self):
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "paper_analyzer.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not load paper_analyzer.txt: {e}")
            return "Analyze the research paper and extract implementation requirements in JSON format."

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        return len(text) // CHARS_PER_TOKEN

    def _truncate_paper(self, content: str) -> str:
        """Truncate paper if too long, keeping important sections"""
        tokens = self._estimate_tokens(content)
        if tokens <= MAX_PAPER_TOKENS:
            return content

        # Keep abstract, introduction, methodology, and conclusion
        max_chars = MAX_PAPER_TOKENS * CHARS_PER_TOKEN

        # Try to find key sections
        sections = {
            'abstract': self._extract_section(content, ['abstract']),
            'introduction': self._extract_section(content, ['introduction', '1. introduction', 'i. introduction']),
            'methodology': self._extract_section(content, ['methodology', 'proposed method', 'approach', 'system design']),
            'architecture': self._extract_section(content, ['architecture', 'system architecture', 'design']),
            'conclusion': self._extract_section(content, ['conclusion', 'conclusions', 'summary'])
        }

        # Build truncated content
        truncated = ""
        for section_name, section_content in sections.items():
            if section_content:
                truncated += f"\n\n=== {section_name.upper()} ===\n{section_content}"

        # If sections not found, use beginning and end
        if len(truncated) < 1000:
            half = max_chars // 2
            truncated = content[:half] + "\n\n[... MIDDLE CONTENT TRUNCATED ...]\n\n" + content[-half:]

        return truncated[:max_chars]

    def _extract_section(self, content: str, keywords: list) -> Optional[str]:
        """Extract a section from paper based on keywords"""
        content_lower = content.lower()

        for keyword in keywords:
            # Find section start
            start_idx = content_lower.find(keyword)
            if start_idx == -1:
                continue

            # Find next section (look for common section markers)
            section_markers = ['\n1.', '\n2.', '\n3.', '\nii.', '\niii.', '\niv.',
                             '\nabstract', '\nintroduction', '\nconclusion',
                             '\nmethodology', '\nreferences', '\nacknowledgment']

            end_idx = len(content)
            for marker in section_markers:
                marker_idx = content_lower.find(marker, start_idx + len(keyword) + 100)
                if marker_idx != -1 and marker_idx < end_idx:
                    end_idx = marker_idx

            # Extract section (max 5000 chars per section)
            section = content[start_idx:min(end_idx, start_idx + 5000)]
            if len(section) > 200:
                return section

        return None

    def _clean_pdf_text(self, text: str) -> str:
        """Clean extracted PDF text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        # Remove page numbers and headers/footers
        text = re.sub(r'\n\d+\n', '\n', text)
        text = re.sub(r'Page \d+ of \d+', '', text)

        # Remove common PDF artifacts
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

        return text.strip()

    async def analyze_paper(
        self,
        paper_text: str,
        paper_title: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Analyze paper and stream structured analysis"""

        # Clean and truncate paper
        cleaned_text = self._clean_pdf_text(paper_text)
        truncated_text = self._truncate_paper(cleaned_text)

        tokens = self._estimate_tokens(truncated_text)
        logger.info(f"Analyzing paper: ~{tokens} tokens")

        prompt = f"""Analyze this IEEE/research paper and extract implementation requirements.

Paper Title: {paper_title or 'Unknown'}

Paper Content:
{truncated_text}

Provide a detailed JSON analysis following the format in your instructions.
After the JSON, provide a brief human-readable summary of what project should be built."""

        async for chunk in claude_client.generate_stream(
            prompt=prompt,
            system=self.system_prompt,
            model='sonnet',  # Use Sonnet for quality analysis
            max_tokens=8192,
            temperature=0.3
        ):
            yield chunk

    async def analyze_paper_json(
        self,
        paper_text: str,
        paper_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze paper and return structured JSON"""

        full_response = ""
        async for chunk in self.analyze_paper(paper_text, paper_title):
            full_response += chunk

        # Extract JSON from response
        try:
            # Find JSON block
            json_match = re.search(r'```json\s*(.*?)\s*```', full_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Try to find raw JSON
            json_start = full_response.find('{')
            json_end = full_response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = full_response[json_start:json_end]
                return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")

        # Return raw response if JSON parsing fails
        return {
            "raw_analysis": full_response,
            "parse_error": True
        }

    def generate_project_prompt(self, analysis: Dict[str, Any]) -> str:
        """Generate a project prompt from paper analysis"""

        if analysis.get('parse_error'):
            return analysis.get('raw_analysis', '')

        # Build project prompt from analysis
        paper_info = analysis.get('paper_info', {})
        problem = analysis.get('problem_statement', {})
        methodology = analysis.get('methodology', {})
        tech = analysis.get('technologies', {})
        impl = analysis.get('implementation_plan', {})

        prompt = f"""Build a project based on this IEEE paper:

**Paper:** {paper_info.get('title', 'Research Implementation')}
**Domain:** {paper_info.get('domain', 'Software Development')}

**Problem Statement:**
{problem.get('description', 'Implement the research paper')}

**Proposed Solution:**
{problem.get('proposed_solution', '')}

**Methodology:**
{methodology.get('approach', '')}
Steps: {', '.join(methodology.get('steps', []))}

**Tech Stack:**
- Languages: {', '.join(tech.get('programming_languages', ['Python', 'JavaScript']))}
- Frameworks: {', '.join(tech.get('frameworks', []))}
- Database: {', '.join(tech.get('databases', ['PostgreSQL']))}
- Algorithms: {', '.join(tech.get('algorithms', []))}

**Project Type:** {impl.get('project_type', 'web_app')}
**Academic Project:** Yes - Generate full documentation (SRS, SDS, UML, Reports, PPT)

**Core Features:**
"""
        for feature in impl.get('core_features', []):
            if isinstance(feature, dict):
                prompt += f"- {feature.get('feature', '')} [{feature.get('priority', 'medium')}]\n"
            else:
                prompt += f"- {feature}\n"

        return prompt


# Singleton
paper_analyzer_agent = PaperAnalyzerAgent()
