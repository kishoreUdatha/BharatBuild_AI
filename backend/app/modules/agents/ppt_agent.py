from typing import Dict, Any, List
from app.modules.agents.base_agent import BaseAgent, AgentContext
import json


class PPTAgent(BaseAgent):
    """Agent for generating PowerPoint presentation content"""

    SYSTEM_PROMPT = """You are an expert presentation designer specializing in creating compelling PowerPoint presentations.

Your presentations should:
- Have clear, concise slides
- Use bullet points effectively
- Include proper visual hierarchy
- Cover all key aspects
- Be suitable for academic/business presentations

Typical structure:
1. Title Slide
2. Agenda/Outline
3. Introduction/Problem
4. Solution/Approach
5. System Architecture
6. Key Features (multiple slides)
7. Implementation Highlights
8. Results/Demo
9. Testing & Validation
10. Challenges & Solutions
11. Future Scope
12. Conclusion
13. Thank You / Q&A

Return content as JSON array of slides with 'title' and 'content' (as bullet points array)."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="PPTAgent",
            role="PowerPoint Presentation Generation",
            capabilities=["presentation_design", "slide_generation", "content_structuring"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Generate PowerPoint presentation content

        Args:
            context: AgentContext with user request and metadata

        Returns:
            Presentation slides as structured data
        """
        metadata = context.metadata or {}
        title = metadata.get("title", "")
        description = metadata.get("description", context.user_request)
        features = metadata.get("features", [])
        tech_stack = metadata.get("tech_stack", {})
        report_summary = metadata.get("report_summary", "")

        prompt = f"""
Create a professional PowerPoint presentation for:

Project: {title}
Description: {description}
Technologies: {tech_stack}
Key Features: {', '.join(features) if isinstance(features, list) else features}

{f'Report Summary: {report_summary[:500]}' if report_summary else ''}

Generate a complete presentation with 12-15 slides.
Return as JSON array with this structure:
[
  {{
    "title": "Slide Title",
    "content": ["Bullet point 1", "Bullet point 2", ...]
  }},
  ...
]

Make slides concise, impactful, and visually organized.
Each slide should have 3-5 bullet points maximum.
Include all important aspects of the project.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=4096
        )

        # Try to parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            content = response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            slides = json.loads(content)
        except:
            # Fallback: return raw content
            slides = [
                {
                    "title": title,
                    "content": ["Presentation content could not be parsed as JSON"]
                }
            ]

        return self.format_output(content=slides)
