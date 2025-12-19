from anthropic import AsyncAnthropic, Anthropic, APIStatusError, APIError, APIConnectionError, APITimeoutError
from typing import Optional, Dict, List, Any, AsyncGenerator
import asyncio
import json
import random
import httpx
from app.core.config import settings
from app.core.logging_config import logger

# Retry configuration - loaded from settings
MAX_RETRIES = settings.CLAUDE_MAX_RETRIES
BASE_DELAY = settings.CLAUDE_RETRY_BASE_DELAY
MAX_DELAY = settings.CLAUDE_RETRY_MAX_DELAY
REQUEST_TIMEOUT = float(settings.CLAUDE_REQUEST_TIMEOUT)
CONNECT_TIMEOUT = float(settings.CLAUDE_CONNECT_TIMEOUT)
RETRYABLE_ERRORS = ['overloaded_error', 'rate_limit_error', 'server_error']


class ClaudeClient:
    """Claude API client wrapper for both streaming and non-streaming requests"""

    def __init__(self):
        # Configure client - use mock server if base URL is provided
        client_kwargs = {"api_key": settings.ANTHROPIC_API_KEY}

        # Only set base_url if it's a non-empty string with actual content
        if settings.ANTHROPIC_BASE_URL and settings.ANTHROPIC_BASE_URL.strip():
            client_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL.strip()
            logger.info(f"Using custom Claude API base URL: {settings.ANTHROPIC_BASE_URL}")

        # Configure timeouts for production reliability
        client_kwargs["timeout"] = httpx.Timeout(
            connect=CONNECT_TIMEOUT,
            read=REQUEST_TIMEOUT,
            write=REQUEST_TIMEOUT,
            pool=REQUEST_TIMEOUT
        )

        if settings.USE_MOCK_CLAUDE:
            logger.info("Mock Claude API mode enabled")

        self.async_client = AsyncAnthropic(**client_kwargs)
        self.sync_client = Anthropic(**client_kwargs)
        self.haiku_model = settings.CLAUDE_HAIKU_MODEL
        self.sonnet_model = settings.CLAUDE_SONNET_MODEL

        logger.info(f"Claude client initialized: timeout={REQUEST_TIMEOUT}s, models=[{self.haiku_model}, {self.sonnet_model}]")

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable (overload, rate limit, network issues, etc.)"""
        error_str = str(error).lower()

        # Network/connection errors are always retryable
        if isinstance(error, (APIConnectionError, APITimeoutError)):
            logger.warning(f"Network error detected (retryable): {type(error).__name__}")
            return True

        # httpx network errors
        if isinstance(error, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)):
            logger.warning(f"HTTPX network error detected (retryable): {type(error).__name__}")
            return True

        if isinstance(error, (APIStatusError, APIError)):
            # Check error type from API response
            if hasattr(error, 'body') and isinstance(error.body, dict):
                error_type = error.body.get('error', {}).get('type', '')
                return error_type in RETRYABLE_ERRORS
            # Check status code for server errors
            if hasattr(error, 'status_code'):
                return error.status_code in [429, 500, 502, 503, 529]

        # Fallback: check error message for network-related issues
        network_errors = ['overload', 'rate_limit', '529', '503', 'capacity',
                         'connection', 'timeout', 'network', 'dns', 'socket']
        return any(err in error_str for err in network_errors)

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
        # Add jitter (0-25% of delay)
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
        """
        Generate response from Claude (non-streaming)

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: "haiku" or "sonnet"
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            messages: Optional list of previous messages for conversation

        Returns:
            Dict with response and metadata
        """
        # Select model
        model_name = self.sonnet_model if model == "sonnet" else self.haiku_model

        # Build messages
        if messages is None:
            messages = []

        messages.append({
            "role": "user",
            "content": prompt
        })

        # Set defaults
        if max_tokens is None:
            max_tokens = settings.CLAUDE_MAX_TOKENS
        if temperature is None:
            temperature = settings.CLAUDE_TEMPERATURE

        # Log request summary (detailed logging only in DEBUG mode)
        prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
        logger.info(f"Claude API: model={model_name}, max_tokens={max_tokens}, prompt_len={len(prompt)}")
        logger.debug(f"Claude request prompt: {prompt_preview}")

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # Make API call
                response = await self.async_client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt if system_prompt else "",
                    messages=messages
                )

                # Extract response
                content = response.content[0].text if response.content else ""

                result = {
                    "content": content,
                    "model": model_name,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                    "stop_reason": response.stop_reason,
                    "id": response.id
                }

                # Log response summary (saves 10-20ms per call)
                logger.info(f"Claude API response: id={response.id}, tokens={result['total_tokens']}, stop={response.stop_reason}")
                logger.debug(f"Claude response preview: {content[:200]}..." if len(content) > 200 else content)

                return result

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                if self._is_retryable_error(e) and attempt < MAX_RETRIES:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"Claude API error [{error_type}] (attempt {attempt + 1}/{MAX_RETRIES + 1}), retrying in {delay:.1f}s...",
                        extra={
                            "event_type": "claude_api_retry",
                            "error_type": error_type,
                            "attempt": attempt + 1,
                            "max_retries": MAX_RETRIES + 1,
                            "retry_delay": delay
                        }
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Claude API error (non-retryable or max retries exceeded): {error_type}: {e}",
                        extra={
                            "event_type": "claude_api_error",
                            "error_type": error_type,
                            "error_message": str(e),
                            "attempt": attempt + 1
                        }
                    )
                    raise

        # Should not reach here, but just in case
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
        """
        Generate streaming response from Claude

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: "haiku" or "sonnet"
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            messages: Optional list of previous messages for conversation

        Yields:
            Chunks of text as they arrive
        """
        # Select model
        model_name = self.sonnet_model if model == "sonnet" else self.haiku_model

        # Build messages
        if messages is None:
            messages = []

        messages.append({
            "role": "user",
            "content": prompt
        })

        # Set defaults
        if max_tokens is None:
            max_tokens = settings.CLAUDE_MAX_TOKENS
        if temperature is None:
            temperature = settings.CLAUDE_TEMPERATURE

        # Log streaming request summary
        prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
        logger.info(f"Claude Streaming: model={model_name}, max_tokens={max_tokens}, prompt_len={len(prompt)}")
        logger.debug(f"Claude streaming prompt: {prompt_preview}")

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # Make streaming API call
                collected_text = []
                has_yielded = False
                async with self.async_client.messages.stream(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt if system_prompt else "",
                    messages=messages
                ) as stream:
                    async for text in stream.text_stream:
                        has_yielded = True
                        collected_text.append(text)
                        yield text

                # Get final message with usage stats
                final_message = await stream.get_final_message()

                # Log streaming response summary
                total_tokens = final_message.usage.input_tokens + final_message.usage.output_tokens
                logger.info(f"Claude Streaming response: id={final_message.id}, tokens={total_tokens}, stop={final_message.stop_reason}")

                # Yield special token usage marker at end of stream
                # Format: __TOKEN_USAGE__:input:output:model
                yield f"__TOKEN_USAGE__:{final_message.usage.input_tokens}:{final_message.usage.output_tokens}:{model_name}"
                return  # Success, exit the retry loop

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                # Only retry if we haven't started yielding yet (can't recover mid-stream)
                if not has_yielded and self._is_retryable_error(e) and attempt < MAX_RETRIES:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"Claude Streaming API error [{error_type}] (attempt {attempt + 1}/{MAX_RETRIES + 1}), retrying in {delay:.1f}s...",
                        extra={
                            "event_type": "claude_stream_retry",
                            "error_type": error_type,
                            "attempt": attempt + 1,
                            "retry_delay": delay
                        }
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Claude Streaming API error (non-retryable): {error_type}: {e}",
                        extra={
                            "event_type": "claude_stream_error",
                            "error_type": error_type,
                            "error_message": str(e),
                            "has_yielded": has_yielded,
                            "attempt": attempt + 1
                        }
                    )
                    raise

        # Should not reach here, but just in case
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
        """
        Generate responses for multiple prompts concurrently

        Args:
            prompts: List of prompts
            system_prompt: System prompt
            model: "haiku" or "sonnet"
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            List of response dictionaries
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
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        return processed_results

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "haiku"
    ) -> float:
        """
        Calculate cost in USD based on token usage

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: "haiku" or "sonnet"

        Returns:
            Cost in USD
        """
        # Claude 3.5 Haiku pricing (as of Jan 2025)
        # Input: $0.80 / MTok, Output: $4.00 / MTok

        # Claude 3.5 Sonnet pricing (as of Jan 2025)
        # Input: $3.00 / MTok, Output: $15.00 / MTok

        if model == "sonnet":
            input_cost = (input_tokens / 1_000_000) * 3.00
            output_cost = (output_tokens / 1_000_000) * 15.00
        else:  # haiku
            input_cost = (input_tokens / 1_000_000) * 0.80
            output_cost = (output_tokens / 1_000_000) * 4.00

        return input_cost + output_cost

    def calculate_cost_in_paise(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "haiku"
    ) -> int:
        """
        Calculate cost in Indian Paise (for database storage)

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: "haiku" or "sonnet"

        Returns:
            Cost in paise (1 USD ≈ 83 INR = 8300 paise as of Jan 2025)
        """
        usd_cost = self.calculate_cost(input_tokens, output_tokens, model)
        # Convert to INR, then to paise
        return int(usd_cost * 83 * 100)


# Create singleton instance
claude_client = ClaudeClient()
