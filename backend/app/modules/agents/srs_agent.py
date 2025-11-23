from typing import Dict, Any
from app.modules.agents.base_agent import BaseAgent, AgentContext


class SRSAgent(BaseAgent):
    """Agent for generating Software Requirements Specification (SRS)"""

    SYSTEM_PROMPT = """You are an expert software requirements analyst specializing in creating comprehensive SRS documents.

Your SRS documents should follow IEEE 830 standards and include:
1. Introduction
   - Purpose
   - Scope
   - Definitions and acronyms
   - References
   - Overview

2. Overall Description
   - Product perspective
   - Product functions
   - User characteristics
   - Constraints
   - Assumptions and dependencies

3. Specific Requirements
   - Functional requirements
   - Non-functional requirements
   - Performance requirements
   - Security requirements
   - Database requirements

4. System Features
   - Detailed feature descriptions
   - User interactions
   - Data flow

5. External Interface Requirements
   - User interfaces
   - Hardware interfaces
   - Software interfaces
   - Communication interfaces

Be thorough, precise, and use professional technical writing."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="SRSAgent",
            role="Software Requirements Specification Generation",
            capabilities=["srs_generation", "requirements_analysis", "ieee_standards"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Generate SRS document

        Args:
            context: AgentContext with user request and metadata

        Returns:
            Complete SRS document
        """
        metadata = context.metadata or {}
        title = metadata.get("title", "")
        description = metadata.get("description", context.user_request)
        features = metadata.get("features", [])
        tech_stack = metadata.get("tech_stack", {})
        target_users = metadata.get("target_users", "")

        prompt = f"""
Generate a comprehensive Software Requirements Specification (SRS) document following IEEE 830 standards.

Project Title: {title}
Description: {description}
Key Features: {', '.join(features) if isinstance(features, list) else features}
Technology Stack: {tech_stack}
Target Users: {target_users}

Create a complete, professional SRS document with all sections mentioned in your system prompt.
Make it detailed and specific to this project.
Use proper formatting with sections, subsections, and numbering.
Include realistic requirements and specifications.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8192
        )

        return self.format_output(content=response)
