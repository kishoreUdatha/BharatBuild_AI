from typing import Dict, Any
from app.modules.agents.base_agent import BaseAgent, AgentContext


class IdeaAgent(BaseAgent):
    """Agent for idea generation and refinement"""

    SYSTEM_PROMPT = """You are an expert idea generation and refinement specialist.
Your role is to help users brainstorm, refine, and validate project ideas.

For academic projects:
- Suggest innovative, feasible project ideas
- Consider current technology trends
- Ensure the scope is appropriate for the academic level
- Identify unique value propositions

For business ideas:
- Analyze market potential
- Identify target audience
- Suggest competitive advantages
- Outline key features

Provide structured, actionable output that can be used for further development.
Be creative, practical, and thorough in your analysis."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="IdeaAgent",
            role="Idea Generation and Refinement",
            capabilities=["idea_generation", "idea_refinement", "feasibility_analysis"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Generate and refine project idea

        Args:
            context: AgentContext with user request

        Returns:
            Refined idea with details
        """
        # Extract metadata if available
        metadata = context.metadata or {}
        domain = metadata.get("domain", "")
        constraints = metadata.get("constraints", "")
        mode = metadata.get("mode", "student")

        prompt = f"""
Please help refine and expand this project idea:

Initial Idea: {context.user_request}
Domain/Industry: {domain if domain else "General"}
Constraints: {constraints if constraints else "None specified"}
Mode: {mode}

Please provide:
1. Refined Project Title
2. Detailed Description
3. Key Features (list 5-7 core features)
4. Target Users/Audience
5. Unique Value Proposition
6. Technical Feasibility Analysis
7. Potential Challenges
8. Success Metrics

Format your response as structured JSON.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=4096,
            temperature=0.7
        )

        return self.format_output(content=response)
