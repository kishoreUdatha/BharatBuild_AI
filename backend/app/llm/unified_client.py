"""
Unified LLM Client - Single interface for all AI providers.

Routes requests to the correct provider based on model ID prefix:
- anthropic/xxx or claude-xxx → AnthropicProvider
- openai/xxx or gpt-xxx → OpenAIProvider
- deepseek/xxx → DeepseekProvider
- google/xxx or gemini-xxx → GoogleProvider
- qwen/xxx or alibaba/xxx → OpenAICompatibleProvider (Qwen)
- minimax/xxx → OpenAICompatibleProvider (MiniMax)
- zhipu/xxx or glm-xxx → OpenAICompatibleProvider (ZhiPu)
- together/xxx → OpenAICompatibleProvider (Together)
- ollama/xxx → OpenAICompatibleProvider (Ollama)
- No prefix → guess from model name
"""

import logging
from typing import AsyncGenerator, Optional, List, Dict

from app.llm.providers.anthropic_provider import AnthropicProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.deepseek_provider import DeepseekProvider
from app.llm.providers.google_provider import GoogleProvider
from app.llm.providers.openai_compatible_provider import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


# Model name patterns for auto-detection (no prefix)
MODEL_PATTERNS = {
    "claude": "anthropic",
    "gpt": "openai",
    "o1": "openai",
    "o3": "openai",
    "o4": "openai",
    "deepseek": "deepseek",
    "gemini": "google",
    "qwen": "qwen",
    "glm": "zhipu",
    "chatglm": "zhipu",
    "abab": "minimax",
    "llama": "together",
    "mixtral": "together",
    "mistral": "together",
}


class UnifiedLLMClient:
    """
    Unified multi-provider LLM client for BharatBuild AI.
    
    Usage:
        from app.llm import unified_llm_client
        
        # Simple generation
        result = await unified_llm_client.generate("claude-sonnet-5", "Hello!")
        
        # With explicit provider prefix
        result = await unified_llm_client.generate("openai/gpt-4o", "Hello!")
        
        # Streaming
        async for chunk in unified_llm_client.generate_stream("gemini-2.0-flash", "Write a poem"):
            print(chunk, end="")
    """

    def __init__(self):
        # Initialize all providers
        self._anthropic = AnthropicProvider()
        self._openai = OpenAIProvider()
        self._deepseek = DeepseekProvider()
        self._google = GoogleProvider()

        # OpenAI-compatible providers (lazy init by name)
        self._compatible_providers: Dict[str, OpenAICompatibleProvider] = {}

    def _get_compatible_provider(self, name: str) -> OpenAICompatibleProvider:
        """Get or create an OpenAI-compatible provider by name."""
        if name not in self._compatible_providers:
            self._compatible_providers[name] = OpenAICompatibleProvider(provider_name=name)
        return self._compatible_providers[name]

    def _resolve_provider(self, model: str):
        """
        Resolve which provider to use based on model string.
        
        Priority:
        1. Explicit prefix (e.g., "anthropic/claude-3-5-sonnet")
        2. Known model name pattern (e.g., "claude-3-5-sonnet" → Anthropic)
        3. Fallback to Anthropic
        """
        model_lower = model.lower()

        # Check explicit provider prefix
        if '/' in model:
            prefix = model.split('/')[0].lower()
            return self._provider_from_prefix(prefix)

        # Check model name patterns
        for pattern, provider_name in MODEL_PATTERNS.items():
            if model_lower.startswith(pattern):
                return self._provider_from_prefix(provider_name)

        # Fallback: try Anthropic (most common in this project)
        logger.warning(f"[UnifiedLLM] Could not determine provider for model '{model}'. Defaulting to Anthropic.")
        return self._anthropic

    def _provider_from_prefix(self, prefix: str):
        """Map a prefix string to a provider instance."""
        if prefix in ("anthropic", "claude"):
            return self._anthropic
        elif prefix in ("openai", "gpt"):
            return self._openai
        elif prefix == "deepseek":
            return self._deepseek
        elif prefix in ("google", "gemini"):
            return self._google
        elif prefix in ("qwen", "alibaba"):
            return self._get_compatible_provider("qwen")
        elif prefix == "minimax":
            return self._get_compatible_provider("minimax")
        elif prefix in ("zhipu", "glm"):
            return self._get_compatible_provider("zhipu")
        elif prefix == "together":
            return self._get_compatible_provider("together")
        elif prefix == "ollama":
            return self._get_compatible_provider("ollama")
        elif prefix == "vllm":
            return self._get_compatible_provider("vllm")
        else:
            # Try as a generic OpenAI-compatible provider
            return self._get_compatible_provider(prefix)

    async def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: str = '',
        max_tokens: int = 4096,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> str:
        """
        Generate a completion using the appropriate provider.
        Automatically tracks usage (tokens, cost, latency).
        """
        from app.llm.usage_tracker import usage_tracker
        
        provider = self._resolve_provider(model)

        if not provider.is_available():
            provider_name = type(provider).__name__
            return f"[ERROR] Provider {provider_name} is not available. Check API key configuration."

        # Track usage
        ctx = usage_tracker.start_call(
            model=model, user_id=user_id, project_id=project_id, agent_type=agent_type
        )

        response = await provider.generate(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        
        # Estimate tokens (approximate: 1 token ≈ 4 chars)
        input_tokens = (len(prompt) + len(system_prompt)) // 4
        output_tokens = len(response) // 4
        
        usage_tracker.end_call(ctx, input_tokens=input_tokens, output_tokens=output_tokens,
                              success=not response.startswith("[ERROR]"))
        
        return response

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system_prompt: str = '',
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming completion using the appropriate provider.

        Args:
            model: Model identifier
            prompt: The user prompt text
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            Text chunks as they are generated
        """
        provider = self._resolve_provider(model)

        if not provider.is_available():
            provider_name = type(provider).__name__
            yield f"[ERROR] Provider {provider_name} is not available. Check API key configuration."
            return

        async for chunk in provider.generate_stream(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield chunk

    def list_available_providers(self) -> Dict[str, bool]:
        """List all providers and their availability status."""
        providers = {
            "anthropic": self._anthropic.is_available(),
            "openai": self._openai.is_available(),
            "deepseek": self._deepseek.is_available(),
            "google": self._google.is_available(),
        }
        # Check compatible providers
        for name in ("qwen", "minimax", "zhipu", "together", "ollama", "vllm"):
            p = self._get_compatible_provider(name)
            providers[name] = p.is_available()
        return providers


# Singleton instance
unified_llm_client = UnifiedLLMClient()
