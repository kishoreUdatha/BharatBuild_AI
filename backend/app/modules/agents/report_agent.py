from typing import Dict, Any
from app.modules.agents.base_agent import BaseAgent, AgentContext


class ReportAgent(BaseAgent):
    """Agent for generating comprehensive project reports"""

    SYSTEM_PROMPT = """You are an expert technical writer specializing in comprehensive project reports.

Your reports should include:
1. Executive Summary
2. Introduction
   - Background
   - Problem Statement
   - Objectives
3. Literature Review / Existing Systems
4. Proposed System
   - System Architecture
   - Design Approach
   - Technologies Used
5. Implementation Details
   - Modules Description
   - Key Features Implementation
   - Algorithms/Techniques
6. Testing & Validation
   - Test Cases
   - Results
   - Performance Analysis
7. Results & Discussion
   - Screenshots/Outputs
   - Analysis
   - Achievements
8. Limitations & Future Scope
9. Conclusion
10. References
11. Appendices (if needed)

Write in formal academic style with proper structure and technical depth."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="ReportAgent",
            role="Project Report Generation",
            capabilities=["report_generation", "technical_writing", "academic_documentation"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Generate comprehensive project report

        Args:
            context: AgentContext with user request and metadata

        Returns:
            Complete project report
        """
        metadata = context.metadata or {}
        title = metadata.get("title", "")
        srs_content = metadata.get("srs_content", "")
        code_summary = metadata.get("code_summary", "")
        tech_stack = metadata.get("tech_stack", {})
        features = metadata.get("features", [])

        prompt = f"""
Generate a comprehensive academic project report for:

Project Title: {title}
Technologies: {tech_stack}
Key Features: {', '.join(features) if isinstance(features, list) else features}

Requirements Summary:
{srs_content[:1000] if srs_content else 'Not provided'}

Code/Implementation Summary:
{code_summary[:1000] if code_summary else 'Not provided'}

Create a complete, well-structured project report following academic standards.
Include all sections mentioned in the system prompt.
Make it detailed (minimum 3000 words) with technical depth.
Use proper formatting with sections, subsections, and numbering.
Include realistic implementation details and analysis.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8192
        )

        return self.format_output(content=response)
