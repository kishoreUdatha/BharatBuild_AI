from typing import Dict, Any
from app.modules.agents.base_agent import BaseAgent, AgentContext


class CodeAgent(BaseAgent):
    """Agent for code generation"""

    SYSTEM_PROMPT = """You are an expert full-stack developer capable of generating production-ready code.

You can create complete applications with:
- Clean, well-structured code
- Best practices and design patterns
- Proper error handling
- Comprehensive comments
- Security considerations
- Performance optimizations

Support multiple frameworks and languages.
Generate complete, functional code that can be directly used."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="CodeAgent",
            role="Code Generation",
            capabilities=["code_generation", "full_stack_development", "best_practices"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Generate code based on requirements

        Args:
            context: AgentContext with user request and metadata

        Returns:
            Generated code and project structure
        """
        metadata = context.metadata or {}
        title = metadata.get("title", "")
        requirements = metadata.get("requirements", context.user_request)
        tech_stack = metadata.get("tech_stack", {})
        features = metadata.get("features", [])

        prompt = f"""
Generate complete, production-ready code for:

Project: {title}
Requirements: {requirements}
Technology Stack: {tech_stack}
Features: {', '.join(features) if isinstance(features, list) else features}

Provide:
1. Project structure
2. All necessary files with complete code
3. Configuration files
4. README with setup instructions
5. Key implementation details

Make the code clean, well-commented, and production-ready.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8192
        )

        return self.format_output(content=response)
