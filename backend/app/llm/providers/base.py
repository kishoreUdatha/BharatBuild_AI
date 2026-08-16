"""
Base LLM Provider - Abstract interface for all providers.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List, Dict


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate a completion from the model."""
        ...

    @abstractmethod
    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming completion from the model."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        ...

    def _strip_prefix(self, model: str) -> str:
        """Remove provider prefix from model ID (e.g., 'openai/gpt-4' -> 'gpt-4')."""
        if '/' in model:
            return model.split('/', 1)[1]
        return model
