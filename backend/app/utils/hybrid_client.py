"""
Hybrid AI Client - Intelligent routing between Qwen (local, FREE) and Claude (API)

Routes simple code generation to local Qwen model (zero cost)
Routes complex tasks to Claude API (when needed)

Cost savings: 70-90% reduction by using local model for simple tasks
"""
import asyncio
from typing import Optional, Dict, List, Any, AsyncGenerator
import re

from app.core.config import settings
from app.core.logging_config import logger
from app.utils.claude_client import ClaudeClient, claude_client


class HybridClient:
    """
    Hybrid AI client that routes between local Qwen model and Claude API.

    Routing strategy:
    - Simple code generation (components, forms, styling) -> Qwen (FREE)
    - Complex tasks (architecture, debugging, analysis) -> Claude
    - Fallback to Claude if Qwen fails or is unavailable
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self._qwen_client = None
        self._claude_client = None  # Lazy load only if needed

        # Load config
        self.use_local_qwen = settings.USE_LOCAL_QWEN
        self.hybrid_routing = settings.HYBRID_ROUTING_ENABLED
        self.qwen_only_mode = getattr(settings, 'QWEN_ONLY_MODE', False)
        self.max_prompt_tokens = settings.QWEN_MAX_PROMPT_TOKENS

        # Simple task keywords (tasks suitable for local Qwen)
        keywords_str = getattr(settings, 'QWEN_SIMPLE_TASK_KEYWORDS', '')
        self.simple_task_keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]

        # Statistics tracking
        self.stats = {
            "qwen_requests": 0,
            "claude_requests": 0,
            "qwen_failures": 0,
            "total_cost_saved_usd": 0.0
        }

        logger.info(
            f"HybridClient initialized: use_local_qwen={self.use_local_qwen}, "
            f"hybrid_routing={self.hybrid_routing}, qwen_only_mode={self.qwen_only_mode}"
        )

    def _get_qwen_client(self):
        """Lazy-load Qwen client only when needed"""
        if self._qwen_client is None and (self.use_local_qwen or self.qwen_only_mode):
            try:
                from app.utils.qwen_client import qwen_client
                self._qwen_client = qwen_client
                logger.info("Qwen client loaded successfully")
            except ImportError as e:
                logger.warning(f"Qwen client not available: {e}")
                if not self.qwen_only_mode:
                    self.use_local_qwen = False
            except Exception as e:
                logger.error(f"Failed to load Qwen client: {e}")
                if not self.qwen_only_mode:
                    self.use_local_qwen = False
        return self._qwen_client

    def _get_claude_client(self):
        """Lazy-load Claude client only when needed (not in Qwen-only mode)"""
        if self._claude_client is None and not self.qwen_only_mode:
            try:
                self._claude_client = claude_client
                logger.info("Claude client loaded")
            except Exception as e:
                logger.error(f"Failed to load Claude client: {e}")
        return self._claude_client

    def _estimate_prompt_tokens(self, prompt: str, system_prompt: str = None) -> int:
        """Rough estimation of prompt tokens (4 chars ≈ 1 token)"""
        total_chars = len(prompt)
        if system_prompt:
            total_chars += len(system_prompt)
        return total_chars // 4

    def _is_simple_task(self, prompt: str, system_prompt: str = None) -> bool:
        """
        Determine if a task is simple enough for local Qwen model.

        Simple tasks:
        - UI component generation (React, Vue, etc.)
        - Basic CRUD operations
        - Styling and layout
        - Simple forms and inputs

        Complex tasks (use Claude):
        - Architecture design
        - Complex debugging
        - Multi-step reasoning
        - Large codebase analysis
        """
        prompt_lower = prompt.lower()

        # Check for complex task indicators (always use Claude)
        complex_indicators = [
            'architecture', 'design pattern', 'optimize', 'debug',
            'analyze', 'refactor', 'security', 'performance',
            'scalability', 'microservice', 'database schema',
            'algorithm', 'data structure', 'machine learning',
            'explain', 'why', 'how does', 'compare'
        ]

        for indicator in complex_indicators:
            if indicator in prompt_lower:
                return False

        # Check prompt size (large prompts need Claude's larger context)
        estimated_tokens = self._estimate_prompt_tokens(prompt, system_prompt)
        if estimated_tokens > self.max_prompt_tokens:
            return False

        # Check for simple task keywords
        simple_score = sum(1 for kw in self.simple_task_keywords if kw in prompt_lower)

        # If multiple simple keywords found, it's likely a simple task
        return simple_score >= 2

    def _select_backend(self, prompt: str, system_prompt: str = None, model: str = "haiku") -> str:
        """
        Select which backend to use for a request.

        Returns: "qwen" or "claude"
        """
        # Qwen-only mode: ALWAYS use Qwen (no Claude at all)
        if self.qwen_only_mode:
            return "qwen"

        # If hybrid routing is disabled, always use Claude
        if not self.hybrid_routing:
            return "claude"

        # If Qwen not available, use Claude
        if not self.use_local_qwen:
            return "claude"

        # Sonnet model requests always go to Claude (complex tasks)
        if model == "sonnet":
            return "claude"

        # Check if task is simple enough for Qwen
        if self._is_simple_task(prompt, system_prompt):
            return "qwen"

        return "claude"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None,
        messages: Optional[List[Dict[str, str]]] = None,
        force_backend: Optional[str] = None  # "qwen" or "claude" to override routing
    ) -> Dict[str, Any]:
        """
        Generate response using the best available backend.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: "haiku" or "sonnet" (sonnet always uses Claude)
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            messages: Optional conversation history
            force_backend: Force specific backend ("qwen" or "claude")

        Returns:
            Dict with response and metadata
        """
        # Determine backend
        if force_backend:
            backend = force_backend
        else:
            backend = self._select_backend(prompt, system_prompt, model)

        logger.info(f"HybridClient: routing to {backend} (model={model})")

        # Try Qwen if selected
        if backend == "qwen":
            qwen = self._get_qwen_client()
            if qwen:
                try:
                    result = await qwen.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=messages
                    )

                    # Track stats
                    self.stats["qwen_requests"] += 1

                    # Calculate saved cost (what Claude would have charged)
                    saved_cost = self._calculate_claude_cost(
                        result.get("input_tokens", 0),
                        result.get("output_tokens", 0),
                        model
                    )
                    self.stats["total_cost_saved_usd"] += saved_cost
                    result["cost_saved_usd"] = saved_cost
                    result["backend"] = "qwen"

                    logger.info(f"Qwen response: saved ${saved_cost:.4f}")
                    return result

                except Exception as e:
                    if self.qwen_only_mode:
                        # In Qwen-only mode, don't fall back to Claude
                        logger.error(f"Qwen generation failed (Qwen-only mode, no fallback): {e}")
                        raise RuntimeError(f"Qwen generation failed: {e}. Claude fallback disabled in QWEN_ONLY_MODE.")
                    logger.warning(f"Qwen generation failed, falling back to Claude: {e}")
                    self.stats["qwen_failures"] += 1
                    backend = "claude"
            elif self.qwen_only_mode:
                raise RuntimeError("Qwen client not available. Set USE_LOCAL_QWEN=True and ensure GPU is available.")

        # Use Claude (only if not in Qwen-only mode)
        if self.qwen_only_mode:
            raise RuntimeError("Claude fallback disabled in QWEN_ONLY_MODE. Ensure Qwen is properly configured.")

        claude = self._get_claude_client()
        if not claude:
            raise RuntimeError("Claude client not available and Qwen not configured.")

        result = await claude.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages
        )

        self.stats["claude_requests"] += 1
        result["backend"] = "claude"
        result["cost_saved_usd"] = 0.0

        return result

    def _calculate_claude_cost(self, input_tokens: int, output_tokens: int, model: str = "haiku") -> float:
        """Calculate what Claude would have charged (for cost savings tracking)"""
        # Claude pricing (Jan 2025)
        if model == "sonnet":
            input_cost = (input_tokens / 1_000_000) * 3.00
            output_cost = (output_tokens / 1_000_000) * 15.00
        else:  # haiku
            input_cost = (input_tokens / 1_000_000) * 0.80
            output_cost = (output_tokens / 1_000_000) * 4.00
        return input_cost + output_cost

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None,
        messages: Optional[List[Dict[str, str]]] = None,
        force_backend: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response using the best available backend.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: "haiku" or "sonnet"
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            messages: Optional conversation history
            force_backend: Force specific backend

        Yields:
            Chunks of text as they arrive
        """
        # Determine backend
        if force_backend:
            backend = force_backend
        else:
            backend = self._select_backend(prompt, system_prompt, model)

        logger.info(f"HybridClient streaming: routing to {backend} (model={model})")

        # Try Qwen if selected
        if backend == "qwen":
            qwen = self._get_qwen_client()
            if qwen:
                try:
                    async for chunk in qwen.generate_stream(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=messages
                    ):
                        yield chunk

                    self.stats["qwen_requests"] += 1
                    return

                except Exception as e:
                    if self.qwen_only_mode:
                        logger.error(f"Qwen streaming failed (Qwen-only mode, no fallback): {e}")
                        raise RuntimeError(f"Qwen streaming failed: {e}. Claude fallback disabled.")
                    logger.warning(f"Qwen streaming failed, falling back to Claude: {e}")
                    self.stats["qwen_failures"] += 1
                    backend = "claude"
            elif self.qwen_only_mode:
                raise RuntimeError("Qwen client not available in QWEN_ONLY_MODE.")

        # Use Claude (only if not in Qwen-only mode)
        if self.qwen_only_mode:
            raise RuntimeError("Claude fallback disabled in QWEN_ONLY_MODE.")

        claude = self._get_claude_client()
        if not claude:
            raise RuntimeError("Claude client not available and Qwen not configured.")

        async for chunk in claude.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages
        ):
            yield chunk

        self.stats["claude_requests"] += 1

    async def batch_generate(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None
    ) -> List[Dict[str, Any]]:
        """
        Generate responses for multiple prompts concurrently.
        Routes each prompt to the appropriate backend.
        """
        tasks = [
            self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            for prompt in prompts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch generate error for prompt {i}: {result}")
                processed_results.append({
                    "content": "",
                    "error": str(result),
                    "backend": "error"
                })
            else:
                processed_results.append(result)

        return processed_results

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "haiku",
        backend: str = "claude"
    ) -> float:
        """
        Calculate cost in USD based on token usage.
        Qwen is FREE, Claude has API costs.
        """
        if backend == "qwen":
            return 0.0  # Local model is FREE
        return self._calculate_claude_cost(input_tokens, output_tokens, model)

    def calculate_cost_in_paise(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "haiku",
        backend: str = "claude"
    ) -> int:
        """Calculate cost in Indian Paise. Qwen is FREE."""
        if backend == "qwen":
            return 0  # Local model is FREE
        usd_cost = self._calculate_claude_cost(input_tokens, output_tokens, model)
        return int(usd_cost * 83 * 100)  # USD to INR to paise

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        total_requests = self.stats["qwen_requests"] + self.stats["claude_requests"]
        qwen_percentage = (
            (self.stats["qwen_requests"] / total_requests * 100)
            if total_requests > 0 else 0
        )

        return {
            **self.stats,
            "total_requests": total_requests,
            "qwen_percentage": round(qwen_percentage, 2),
            "qwen_available": self.use_local_qwen,
            "hybrid_routing_enabled": self.hybrid_routing
        }

    def reset_stats(self):
        """Reset usage statistics"""
        self.stats = {
            "qwen_requests": 0,
            "claude_requests": 0,
            "qwen_failures": 0,
            "total_cost_saved_usd": 0.0
        }


# Create singleton instance
hybrid_client = HybridClient()

# Convenience: also export claude_client for direct access when needed
__all__ = ['hybrid_client', 'HybridClient', 'claude_client']
