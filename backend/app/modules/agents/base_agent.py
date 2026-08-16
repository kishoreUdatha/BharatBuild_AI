from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, InitVar
from app.utils.claude_client import claude_client
from app.core.logging_config import logger
from app.core.config import settings
from app.utils.security import (
    INJECTION_DEFENSE_PREAMBLE,
    sanitize_user_input,
    wrap_user_input,
    sanitize_file_content_for_prompt,
    validate_file_path,
    sanitize_file_path,
)
from app.utils.token_budget import TokenBudget, estimate_tokens


@dataclass
class AgentContext:
    """
    Context object passed between agents in the multi-agent workflow.
    Contains all necessary information for agents to process requests.
    """
    user_request: str
    project_id: str
    user_id: Optional[str] = None  # User ID for isolation (diagrams, documents, etc.)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    # Token budget for this request (optional, set by orchestrator)
    token_budget: Optional[TokenBudget] = field(default=None, repr=False)
    # Dynamic model selection
    model_preference: str = "auto"  # "auto", "fast", "balanced", "smart", or model ID
    user_plan: str = "free"         # User's subscription plan

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
        self.model = model  # Default model (can be overridden by context)
        self.claude = claude_client
        # Token tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._call_count = 0

    def resolve_model(self, context: Optional['AgentContext'] = None) -> str:
        """
        Resolve which model to use for this agent call.
        
        Priority:
        1. User's explicit preference from context (if set)
        2. Agent's default model
        
        Args:
            context: Optional AgentContext with user preferences
            
        Returns:
            Model ID string ("haiku", "sonnet", etc.)
        """
        if context and context.model_preference != "auto":
            try:
                from app.config.model_registry import model_registry
                resolved = model_registry.resolve_model(
                    agent_type=self.role,
                    user_plan=context.user_plan,
                    user_preference=context.model_preference,
                )
                if resolved != self.model:
                    logger.info(f"[{self.name}] Model override: {self.model} -> {resolved} (user preference: {context.model_preference})")
                return resolved
            except ImportError:
                pass  # model_registry not available, use default
        
        return self.model

    def reset_token_tracking(self):
        """Reset token tracking counters"""
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._call_count = 0

    def get_token_usage(self) -> Dict[str, Any]:
        """Get accumulated token usage"""
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "call_count": self._call_count,
            "model": self.model
        }

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
        temperature: float = 0.7,
        token_budget: Optional[TokenBudget] = None,
        context: Optional['AgentContext'] = None
    ) -> str:
        """
        Call Claude API with system and user prompts (with injection defense and budget enforcement)

        Args:
            system_prompt: System prompt for the agent
            user_prompt: User's request/prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            token_budget: Optional token budget to enforce
            context: Optional AgentContext for dynamic model selection

        Returns:
            Generated text response from Claude
        """
        try:
            # Resolve model dynamically based on user preference
            active_model = self.resolve_model(context)

            # Check token budget before calling
            if token_budget:
                estimated_input = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
                if not token_budget.can_spend_input(estimated_input):
                    raise ValueError(
                        f"[{self.name}] Token budget exceeded: "
                        f"need ~{estimated_input} input tokens, "
                        f"only {token_budget.remaining_input} remaining"
                    )
                if not token_budget.can_make_call():
                    raise ValueError(
                        f"[{self.name}] Call budget exceeded: "
                        f"{token_budget.calls_made}/{token_budget.max_calls} calls used"
                    )
                # Respect budget for output tokens
                max_tokens = min(max_tokens, token_budget.get_recommended_max_tokens(max_tokens))

            # Add injection defense to system prompt
            secured_system_prompt = INJECTION_DEFENSE_PREAMBLE + "\n" + system_prompt

            # Optimize for plain text if enabled (20% performance boost!)
            optimized_system_prompt = self._optimize_system_prompt_for_plain_text(secured_system_prompt)

            response = await self.claude.generate(
                prompt=user_prompt,
                system_prompt=optimized_system_prompt,
                model=active_model,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Track token usage
            input_tokens = response.get("input_tokens", 0)
            output_tokens = response.get("output_tokens", 0)
            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens
            self._call_count += 1

            # Update budget if provided
            if token_budget:
                token_budget.record_call(input_tokens, output_tokens)

            logger.debug(f"[{self.name}] Token usage: +{input_tokens} in, +{output_tokens} out (call #{self._call_count}, model={active_model})")

            return response.get("content", "")
        except Exception as e:
            logger.error(f"[{self.name}] Claude API error: {e}", exc_info=True)
            raise

    @staticmethod
    def safe_user_input(text: str, max_length: int = 50000) -> str:
        """Wrap user input with injection-safe boundary tags."""
        return wrap_user_input(text, max_length)

    @staticmethod
    def safe_file_content(content: str, file_path: str, max_length: int = 10000) -> str:
        """Sanitize file content for safe inclusion in prompts."""
        return sanitize_file_content_for_prompt(content, file_path, max_length)

    @staticmethod
    def validate_output_path(path: str, base_dir: Optional[str] = None) -> Optional[str]:
        """
        Validate and sanitize a file path from LLM output.
        Returns sanitized path or None if invalid.
        """
        sanitized = sanitize_file_path(path)
        if sanitized and base_dir:
            is_valid, _ = validate_file_path(sanitized, base_dir=base_dir)
            if not is_valid:
                return None
        return sanitized

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
