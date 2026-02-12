"""
Hybrid AI Client - Intelligent routing between Qwen (local, FREE) and Claude (API)

Features:
- Routes simple code generation to local Qwen model (zero cost)
- Routes complex tasks to Claude API (when needed)
- RAG (Retrieval-Augmented Generation) for enhanced context
- Cost savings: 70-90% reduction by using local model for simple tasks
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

        # RAG configuration
        self.use_rag = getattr(settings, 'USE_RAG', True)  # Enable by default
        self._rag_service = None

        # Statistics tracking
        self.stats = {
            "qwen_requests": 0,
            "claude_requests": 0,
            "qwen_failures": 0,
            "rag_retrievals": 0,
            "total_cost_saved_usd": 0.0
        }

        logger.info(
            f"HybridClient initialized: use_local_qwen={self.use_local_qwen}, "
            f"hybrid_routing={self.hybrid_routing}, qwen_only_mode={self.qwen_only_mode}, "
            f"use_rag={self.use_rag}"
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

    def _get_rag_service(self):
        """Lazy-load RAG service only when needed"""
        if self._rag_service is None and self.use_rag:
            try:
                from app.services.rag_service import rag_service
                if rag_service.is_available():
                    self._rag_service = rag_service
                    logger.info("RAG service loaded successfully")
                else:
                    logger.warning("RAG service not available (missing dependencies)")
                    self.use_rag = False
            except ImportError as e:
                logger.warning(f"RAG service not available: {e}")
                self.use_rag = False
            except Exception as e:
                logger.error(f"Failed to load RAG service: {e}")
                self.use_rag = False
        return self._rag_service

    def _get_rag_context(
        self,
        prompt: str,
        framework: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Retrieve relevant context from RAG for code generation.

        Args:
            prompt: The user's prompt
            framework: Target framework (react, fastapi, etc.)
            language: Programming language

        Returns:
            Context string to append to prompt, or empty string if RAG not available
        """
        if not self.use_rag:
            return ""

        rag = self._get_rag_service()
        if not rag:
            return ""

        try:
            # Detect framework from prompt if not provided
            if not framework:
                framework = self._detect_framework(prompt)

            context = rag.retrieve_for_code_generation(
                prompt=prompt,
                framework=framework,
                language=language,
                n_results=3
            )

            if context:
                self.stats["rag_retrievals"] += 1
                logger.info(f"RAG context retrieved for: {prompt[:50]}...")

            return context

        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return ""

    def _detect_framework(self, prompt: str) -> Optional[str]:
        """Detect target framework from prompt"""
        prompt_lower = prompt.lower()

        frameworks = {
            "react": ["react", "jsx", "tsx", "component", "hook", "usestate", "useeffect"],
            "nextjs": ["next.js", "nextjs", "next js", "getserverside", "getstaticprops"],
            "vue": ["vue", "vuejs", "vue.js", "nuxt"],
            "fastapi": ["fastapi", "fast api", "pydantic", "uvicorn"],
            "django": ["django", "drf", "django rest"],
            "express": ["express", "expressjs", "node.js api"],
            "flask": ["flask"],
            "spring": ["spring boot", "springboot", "java api"],
        }

        for framework, keywords in frameworks.items():
            if any(kw in prompt_lower for kw in keywords):
                return framework

        return None

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
        force_backend: Optional[str] = None,  # "qwen" or "claude" to override routing
        use_rag: Optional[bool] = None,  # Override RAG setting for this request
        framework: Optional[str] = None,  # Framework hint for RAG
        language: Optional[str] = None  # Language hint for RAG
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
            use_rag: Override RAG setting (True/False) for this request
            framework: Framework hint for RAG retrieval (react, fastapi, etc.)
            language: Language hint for RAG retrieval (typescript, python, etc.)

        Returns:
            Dict with response and metadata
        """
        # Determine backend
        if force_backend:
            backend = force_backend
        else:
            backend = self._select_backend(prompt, system_prompt, model)

        logger.info(f"HybridClient: routing to {backend} (model={model})")

        # Enhance prompt with RAG context if enabled
        enhanced_prompt = prompt
        rag_used = False
        should_use_rag = use_rag if use_rag is not None else self.use_rag

        if should_use_rag:
            rag_context = self._get_rag_context(prompt, framework, language)
            if rag_context:
                enhanced_prompt = f"{prompt}\n{rag_context}"
                rag_used = True
                logger.info(f"RAG context added ({len(rag_context)} chars)")

        # Try Qwen if selected
        if backend == "qwen":
            qwen = self._get_qwen_client()
            if qwen:
                try:
                    result = await qwen.generate(
                        prompt=enhanced_prompt,  # Use RAG-enhanced prompt
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
                    result["rag_used"] = rag_used

                    logger.info(f"Qwen response: saved ${saved_cost:.4f}, RAG={rag_used}")
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
            prompt=enhanced_prompt,  # Use RAG-enhanced prompt
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages
        )

        self.stats["claude_requests"] += 1
        result["backend"] = "claude"
        result["cost_saved_usd"] = 0.0
        result["rag_used"] = rag_used

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
        force_backend: Optional[str] = None,
        use_rag: Optional[bool] = None,  # Override RAG setting for this request
        framework: Optional[str] = None,  # Framework hint for RAG
        language: Optional[str] = None  # Language hint for RAG
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
            use_rag: Override RAG setting for this request
            framework: Framework hint for RAG retrieval
            language: Language hint for RAG retrieval

        Yields:
            Chunks of text as they arrive
        """
        # Determine backend
        if force_backend:
            backend = force_backend
        else:
            backend = self._select_backend(prompt, system_prompt, model)

        logger.info(f"HybridClient streaming: routing to {backend} (model={model})")

        # Enhance prompt with RAG context if enabled
        enhanced_prompt = prompt
        should_use_rag = use_rag if use_rag is not None else self.use_rag

        if should_use_rag:
            rag_context = self._get_rag_context(prompt, framework, language)
            if rag_context:
                enhanced_prompt = f"{prompt}\n{rag_context}"
                self.stats["rag_retrievals"] += 1
                logger.info(f"RAG context added to stream ({len(rag_context)} chars)")

        # Try Qwen if selected
        if backend == "qwen":
            qwen = self._get_qwen_client()
            if qwen:
                try:
                    async for chunk in qwen.generate_stream(
                        prompt=enhanced_prompt,  # Use RAG-enhanced prompt
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
            prompt=enhanced_prompt,  # Use RAG-enhanced prompt
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
            "hybrid_routing_enabled": self.hybrid_routing,
            "rag_enabled": self.use_rag,
            "qwen_only_mode": self.qwen_only_mode
        }

    def reset_stats(self):
        """Reset usage statistics"""
        self.stats = {
            "qwen_requests": 0,
            "claude_requests": 0,
            "qwen_failures": 0,
            "rag_retrievals": 0,
            "total_cost_saved_usd": 0.0
        }


# Create singleton instance
hybrid_client = HybridClient()

# Convenience: also export claude_client for direct access when needed
__all__ = ['hybrid_client', 'HybridClient', 'claude_client']
