from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, InitVar
from app.utils.claude_client import claude_client
from app.core.logging_config import logger
from app.core.config import settings


@dataclass
class AgentContext:
    """
    Context object passed between agents in the multi-agent workflow.
    Contains all necessary information for agents to process requests.
    """
    user_request: str
    project_id: str
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure metadata is never None - always use empty dict as fallback"""
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(
        self,
        name: str,
        role: str,
        capabilities: list,
        model: str = "haiku"
    ):
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.model = model
        self.claude = claude_client

    @abstractmethod
    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Process agent task with given context

        Args:
            context: AgentContext with user request and metadata

        Returns:
            Dict with agent output
        """
        pass

    def _optimize_system_prompt_for_plain_text(self, system_prompt: str) -> str:
        """
        Optimize system prompt to use Bolt.new-style XML tags instead of JSON (20% performance improvement)

        Args:
            system_prompt: Original system prompt

        Returns:
            Optimized system prompt for Bolt.new XML tag format
        """
        if not settings.USE_PLAIN_TEXT_RESPONSES:
            return system_prompt

        # Replace JSON instructions with Bolt.new XML tag format
        optimized = system_prompt.replace(
            "YOUR OUTPUT MUST BE VALID JSON:",
            "OUTPUT FORMAT: Use structured plain text with XML-like tags (Bolt.new format) for better performance and streaming. NO JSON."
        )
        optimized = optimized.replace(
            "Output valid JSON",
            "Output plain text with XML tags"
        )
        optimized = optimized.replace(
            "Return as JSON",
            "Return as plain text with XML tags"
        )

        # Add Bolt.new format instructions if not present
        if "<plan>" not in optimized and "<file" not in optimized:
            optimized += "\n\n🎯 BOLT.NEW FORMAT RULES:\n"
            optimized += "Use these XML-like tags for structured output:\n\n"
            optimized += "1. For project plans:\n"
            optimized += "   <plan>\n"
            optimized += "   Project Name: Todo App\n"
            optimized += "   Type: Full-stack\n"
            optimized += "   Features:\n"
            optimized += "   - User authentication\n"
            optimized += "   - CRUD operations\n"
            optimized += "   </plan>\n\n"
            optimized += "2. For file generation:\n"
            optimized += "   <file path=\"src/App.tsx\">\n"
            optimized += "   import React from 'react'\n"
            optimized += "   // code here\n"
            optimized += "   </file>\n\n"
            optimized += "3. For terminal commands:\n"
            optimized += "   <terminal>\n"
            optimized += "   npm install\n"
            optimized += "   npm run dev\n"
            optimized += "   </terminal>\n\n"
            optimized += "4. For errors/warnings:\n"
            optimized += "   <error>\n"
            optimized += "   Error description here\n"
            optimized += "   </error>\n\n"
            optimized += "5. For thinking/explanations:\n"
            optimized += "   <thinking>\n"
            optimized += "   Analyzing requirements...\n"
            optimized += "   </thinking>\n\n"
            optimized += "IMPORTANT:\n"
            optimized += "- Use XML tags, NOT JSON\n"
            optimized += "- Tags are case-sensitive\n"
            optimized += "- Close all tags properly\n"
            optimized += "- Content inside tags is plain text\n"

        logger.debug(f"[{self.name}] Optimized system prompt for Bolt.new XML format")
        return optimized

    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        Call Claude API with system and user prompts (optimized for plain text)

        Args:
            system_prompt: System prompt for the agent
            user_prompt: User's request/prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            Generated text response from Claude
        """
        try:
            # Optimize for plain text if enabled (20% performance boost!)
            optimized_system_prompt = self._optimize_system_prompt_for_plain_text(system_prompt)

            response = await self.claude.generate(
                prompt=user_prompt,
                system_prompt=optimized_system_prompt,
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.get("content", "")
        except Exception as e:
            logger.error(f"[{self.name}] Claude API error: {e}", exc_info=True)
            raise

    def format_output(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format agent output

        Args:
            content: Generated content
            metadata: Additional metadata

        Returns:
            Formatted output
        """
        output = {
            "content": content,
            "agent": self.__class__.__name__,
            "model": self.model
        }

        if metadata:
            output.update(metadata)

        return output
