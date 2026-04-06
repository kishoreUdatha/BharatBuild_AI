"""
LLM Client - OpenAI-compatible API client (works with LM Studio, Ollama, etc.)

Replaces the previous Anthropic Claude client with an OpenAI-compatible client
that points to a local LM Studio server running Qwen model.

Usage:
    Set in .env:
        OPENAI_API_BASE=http://localhost:1234/v1
        OPENAI_API_KEY=lm-studio
        LLM_MODEL=qwen
"""
from openai import AsyncOpenAI, OpenAI
from typing import Optional, Dict, List, Any, AsyncGenerator
import asyncio
import json
import random
import httpx
from app.core.config import settings
from app.core.logging_config import logger
from app.utils.openai_compat import AsyncAnthropic as _AsyncAnthropicCompat

# Retry configuration - loaded from settings
MAX_RETRIES = settings.CLAUDE_MAX_RETRIES
BASE_DELAY = settings.CLAUDE_RETRY_BASE_DELAY
MAX_DELAY = settings.CLAUDE_RETRY_MAX_DELAY
REQUEST_TIMEOUT = float(settings.CLAUDE_REQUEST_TIMEOUT)
CONNECT_TIMEOUT = float(settings.CLAUDE_CONNECT_TIMEOUT)


class ClaudeClient:
    """OpenAI-compatible LLM client (drop-in replacement for Anthropic Claude client)"""

    def __init__(self):
        base_url = settings.OPENAI_API_BASE
        api_key = settings.OPENAI_API_KEY

        self._raw_async_client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT,
                read=REQUEST_TIMEOUT,
                write=REQUEST_TIMEOUT,
                pool=REQUEST_TIMEOUT
            )
        )
        self._raw_sync_client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT,
                read=REQUEST_TIMEOUT,
                write=REQUEST_TIMEOUT,
                pool=REQUEST_TIMEOUT
            )
        )

        # Provide Anthropic-compatible .async_client.messages interface
        # for code that accesses claude_client.async_client.messages.create()
        self.async_client = _AsyncAnthropicCompat()

        self.haiku_model = settings.CLAUDE_HAIKU_MODEL
        self.sonnet_model = settings.CLAUDE_SONNET_MODEL

        logger.info(f"LLM client initialized: base_url={base_url}, models=[{self.haiku_model}, {self.sonnet_model}]")

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable"""
        error_str = str(error).lower()
        if isinstance(error, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)):
            return True
        network_errors = ['overload', 'rate_limit', '529', '503', 'capacity',
                         'connection', 'timeout', 'network', 'dns', 'socket']
        return any(err in error_str for err in network_errors)

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
        jitter = delay * random.uniform(0, 0.25)
        return delay + jitter

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Generate response (non-streaming) - OpenAI chat completions format"""
        model_name = self.sonnet_model if model == "sonnet" else self.haiku_model

        # Build messages in OpenAI format
        oai_messages = []
        if system_prompt:
            oai_messages.append({"role": "system", "content": system_prompt})

        if messages:
            for msg in messages:
                oai_messages.append({"role": msg["role"], "content": msg["content"]})

        oai_messages.append({"role": "user", "content": prompt})

        if max_tokens is None:
            max_tokens = settings.CLAUDE_MAX_TOKENS
        if temperature is None:
            temperature = settings.CLAUDE_TEMPERATURE

        prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
        logger.info(f"LLM API: model={model_name}, max_tokens={max_tokens}, prompt_len={len(prompt)}")
        logger.debug(f"LLM request prompt: {prompt_preview}")

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await self._raw_async_client.chat.completions.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=oai_messages
                )

                content = response.choices[0].message.content if response.choices else ""
                usage = response.usage

                result = {
                    "content": content or "",
                    "model": model_name,
                    "input_tokens": usage.prompt_tokens if usage else 0,
                    "output_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                    "stop_reason": response.choices[0].finish_reason if response.choices else "unknown",
                    "id": response.id or f"lm-{id(response)}"
                }

                logger.info(f"LLM API response: id={result['id']}, tokens={result['total_tokens']}, stop={result['stop_reason']}")

                if result['stop_reason'] == "length":
                    logger.warning(
                        f"RESPONSE TRUNCATED: LLM hit max_tokens limit ({max_tokens}). "
                        f"Output may be incomplete!"
                    )
                    result["truncated"] = True

                return result

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                if self._is_retryable_error(e) and attempt < MAX_RETRIES:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(f"LLM API error [{error_type}] (attempt {attempt + 1}/{MAX_RETRIES + 1}), retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM API error (non-retryable): {error_type}: {e}")
                    raise

        raise last_error

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response - OpenAI chat completions format"""
        model_name = self.sonnet_model if model == "sonnet" else self.haiku_model

        oai_messages = []
        if system_prompt:
            oai_messages.append({"role": "system", "content": system_prompt})

        if messages:
            for msg in messages:
                oai_messages.append({"role": msg["role"], "content": msg["content"]})

        oai_messages.append({"role": "user", "content": prompt})

        if max_tokens is None:
            max_tokens = settings.CLAUDE_MAX_TOKENS
        if temperature is None:
            temperature = settings.CLAUDE_TEMPERATURE

        logger.info(f"LLM Streaming: model={model_name}, max_tokens={max_tokens}, prompt_len={len(prompt)}")

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                collected_text = []
                has_yielded = False

                stream = await self._raw_async_client.chat.completions.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=oai_messages,
                    stream=True
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        has_yielded = True
                        collected_text.append(text)
                        yield text

                # Estimate tokens (LM Studio may not return usage in streaming)
                full_text = "".join(collected_text)
                est_output_tokens = len(full_text) // 4  # rough estimate
                est_input_tokens = len(prompt) // 4

                logger.info(f"LLM Streaming response: ~{est_input_tokens + est_output_tokens} tokens")

                yield f"__TOKEN_USAGE__:{est_input_tokens}:{est_output_tokens}:{model_name}"
                return

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                if not has_yielded and self._is_retryable_error(e) and attempt < MAX_RETRIES:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(f"LLM Streaming error [{error_type}] (attempt {attempt + 1}/{MAX_RETRIES + 1}), retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM Streaming error: {error_type}: {e}")
                    raise

        if last_error:
            raise last_error

    async def batch_generate(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None
    ) -> List[Dict[str, Any]]:
        """Generate responses for multiple prompts concurrently"""
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

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch generate error for prompt {i}: {result}")
                processed_results.append({"content": "", "error": str(result)})
            else:
                processed_results.append(result)

        return processed_results

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str = "haiku") -> float:
        """Local model = FREE"""
        return 0.0

    def calculate_cost_in_paise(self, input_tokens: int, output_tokens: int, model: str = "haiku") -> int:
        """Local model = FREE"""
        return 0


# Create singleton instance
claude_client = ClaudeClient()
