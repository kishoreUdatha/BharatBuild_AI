from typing import Dict, Any
from app.modules.agents.base_agent import BaseAgent, AgentContext


class PRDAgent(BaseAgent):
    """Agent for generating Product Requirements Document"""

    SYSTEM_PROMPT = """You are a senior product manager expert in creating comprehensive PRDs.

Your PRDs should include:
1. Executive Summary
2. Product Vision & Goals
3. Target Users & Personas
4. User Stories & Use Cases
5. Feature Requirements (Must-have, Should-have, Nice-to-have)
6. User Experience & Design Guidelines
7. Technical Considerations
8. Success Metrics & KPIs
9. Timeline & Milestones
10. Risk Assessment

Write clearly, be specific, and focus on user value."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="PRDAgent",
            role="Product Requirements Document Generation",
            capabilities=["prd_generation", "product_management", "user_stories"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Generate PRD

        Args:
            context: AgentContext with user request and metadata

        Returns:
            Complete Product Requirements Document
        """
        metadata = context.metadata or {}
        title = metadata.get("title", "")
        description = metadata.get("description", context.user_request)
        target_market = metadata.get("target_market", "")
        features = metadata.get("features", [])

        prompt = f"""
Create a comprehensive Product Requirements Document (PRD):

Product: {title}
Description: {description}
Target Market: {target_market}
Core Features: {features}

Generate a complete, professional PRD with all sections.
Be specific and actionable.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8192
        )

        return self.format_output(content=response)
