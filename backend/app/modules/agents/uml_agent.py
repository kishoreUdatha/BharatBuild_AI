from typing import Dict, Any
from app.modules.agents.base_agent import BaseAgent, AgentContext


class UMLAgent(BaseAgent):
    """Agent for generating UML diagrams (PlantUML format)"""

    SYSTEM_PROMPT = """You are an expert software architect specializing in UML diagrams.

Generate UML diagrams in PlantUML syntax for:
1. Use Case Diagram
2. Class Diagram
3. Sequence Diagram
4. Activity Diagram
5. Component Diagram
6. Deployment Diagram (if applicable)
7. ER Diagram (for database)

Return each diagram in valid PlantUML syntax that can be rendered.
Include proper relationships, multiplicities, and annotations.
Make diagrams comprehensive but clean and readable."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="UMLAgent",
            role="UML Diagram Generation",
            capabilities=["uml_generation", "plantuml_syntax", "software_architecture"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Generate UML diagrams

        Args:
            context: AgentContext with user request and metadata

        Returns:
            UML diagrams in PlantUML format
        """
        metadata = context.metadata or {}
        title = metadata.get("title", "")
        srs_content = metadata.get("srs_content", "")
        features = metadata.get("features", [])
        tech_stack = metadata.get("tech_stack", {})

        prompt = f"""
Generate comprehensive UML diagrams for:

Project: {title}
Technologies: {tech_stack}
Features: {', '.join(features) if isinstance(features, list) else features}

Requirements Summary:
{srs_content[:1000] if srs_content else ''}

Create the following diagrams in PlantUML syntax:

1. USE CASE DIAGRAM
2. CLASS DIAGRAM (main classes and relationships)
3. SEQUENCE DIAGRAM (key user interaction)
4. ACTIVITY DIAGRAM (main workflow)
5. ER DIAGRAM (database schema)

Separate each diagram with a clear header.
Use valid PlantUML syntax.
Make diagrams detailed and professional.
Include all important entities, actors, and relationships.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8192
        )

        return self.format_output(content=response)
