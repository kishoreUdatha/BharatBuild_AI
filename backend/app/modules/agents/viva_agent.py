from typing import Dict, Any, List
from app.modules.agents.base_agent import BaseAgent, AgentContext
import json


class VivaAgent(BaseAgent):
    """Agent for generating Viva Voce (oral examination) Q&A preparation"""

    SYSTEM_PROMPT = """You are an expert academic examiner preparing students for Viva Voce examinations.

Generate comprehensive Q&A covering:
1. Project Overview & Objectives
2. Technical Concepts & Theory
3. Implementation Details
4. Design Decisions & Justifications
5. Challenges Faced & Solutions
6. Testing & Results
7. Comparative Analysis
8. Future Enhancements
9. Real-world Applications
10. Edge Cases & Limitations

Questions should be:
- Challenging but fair
- Cover both basic and advanced concepts
- Include "why" and "how" questions
- Test understanding, not just memorization
- Relevant to the project domain

Answers should be:
- Clear and concise
- Technically accurate
- Show deep understanding
- Include examples where appropriate
- Address the question directly

Return as JSON array of Q&A pairs."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="VivaAgent",
            role="Viva Voce Q&A Preparation",
            capabilities=["viva_preparation", "qa_generation", "academic_examination"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Generate Viva Q&A preparation material

        Args:
            context: AgentContext with user request and metadata

        Returns:
            Q&A pairs for viva preparation
        """
        metadata = context.metadata or {}
        title = metadata.get("title", "")
        domain = metadata.get("domain", "")
        tech_stack = metadata.get("tech_stack", {})
        features = metadata.get("features", [])
        srs_summary = metadata.get("srs_summary", "")
        report_summary = metadata.get("report_summary", "")

        prompt = f"""
Generate comprehensive Viva Voce Q&A preparation for:

Project: {title}
Domain: {domain}
Technologies: {tech_stack}
Key Features: {', '.join(features) if isinstance(features, list) else features}

{f'Requirements: {srs_summary[:300]}' if srs_summary else ''}
{f'Summary: {report_summary[:300]}' if report_summary else ''}

Create 25-30 important viva questions with detailed answers.
Cover all aspects: technical, theoretical, implementation, and practical.

Return as JSON array:
[
  {{
    "question": "Question text?",
    "answer": "Detailed answer with examples.",
    "category": "Technical/Theoretical/Implementation/Practical",
    "difficulty": "Basic/Intermediate/Advanced"
  }},
  ...
]

Make answers comprehensive (3-5 sentences) with technical depth.
Include questions that examiners commonly ask.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8192
        )

        # Try to parse JSON
        try:
            content = response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            qa_pairs = json.loads(content)
        except:
            # Fallback
            qa_pairs = [
                {
                    "question": "Q&A content could not be parsed",
                    "answer": "Please review the raw content",
                    "category": "General",
                    "difficulty": "Basic"
                }
            ]

        return self.format_output(content=qa_pairs)
