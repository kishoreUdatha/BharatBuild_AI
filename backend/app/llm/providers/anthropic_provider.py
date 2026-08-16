"""
Anthropic Provider - Supports both Direct API and AWS Bedrock.
"""

import os
import time
import asyncio
import logging
from typing import AsyncGenerator, Optional, List, Dict

from app.llm.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider supporting:
    - Direct Anthropic API (CLAUDE_PROVIDER=direct)
    - AWS Bedrock (CLAUDE_PROVIDER=bedrock)
    """

    def __init__(self):
        self.provider_type = os.getenv("CLAUDE_PROVIDER", "direct")
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.max_retries = 3

    def is_available(self) -> bool:
        if self.provider_type == "bedrock":
            return bool(self.aws_access_key and self.aws_secret_key)
        return bool(self.api_key)

    def _get_client(self):
        """Get the appropriate Anthropic client based on provider type."""
        import anthropic

        if self.provider_type == "bedrock":
            return anthropic.AsyncAnthropicBedrock(
                aws_access_key=self.aws_access_key,
                aws_secret_key=self.aws_secret_key,
                aws_region=self.aws_region,
            )
        return anthropic.AsyncAnthropic(api_key=self.api_key)

    def _build_messages(
        self,
        prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """Build messages list for the API call."""
        if messages:
            return messages
        return [{"role": "user", "content": prompt}]

    async def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if not self.is_available():
            return "[ERROR] Anthropic provider not configured. Set ANTHROPIC_API_KEY or AWS credentials."

        model_id = self._strip_prefix(model)
        client = self._get_client()
        built_messages = self._build_messages(prompt, messages)

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                kwargs = {
                    "model": model_id,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": built_messages,
                }
                if system_prompt:
                    kwargs["system"] = system_prompt

                response = await client.messages.create(**kwargs)

                latency = time.time() - start_time
                output_text = response.content[0].text if response.content else ""
                input_tokens = getattr(response.usage, "input_tokens", 0)
                output_tokens = getattr(response.usage, "output_tokens", 0)

                logger.info(
                    f"[Anthropic] model={model_id} "
                    f"input_tokens={input_tokens} output_tokens={output_tokens} "
                    f"latency={latency:.2f}s"
                )
                return output_text

            except Exception as e:
                wait_time = (2 ** attempt) + 0.5
                logger.warning(
                    f"[Anthropic] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Anthropic] All {self.max_retries} attempts failed for model={model_id}")
                    return f"[ERROR] Anthropic API failed after {self.max_retries} attempts: {e}"

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield "[ERROR] Anthropic provider not configured. Set ANTHROPIC_API_KEY or AWS credentials."
            return

        model_id = self._strip_prefix(model)
        client = self._get_client()

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                kwargs = {
                    "model": model_id,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if system_prompt:
                    kwargs["system"] = system_prompt

                total_tokens = 0
                async with client.messages.stream(**kwargs) as stream:
                    async for text in stream.text_stream:
                        total_tokens += 1
                        yield text

                latency = time.time() - start_time
                logger.info(
                    f"[Anthropic/Stream] model={model_id} "
                    f"chunks={total_tokens} latency={latency:.2f}s"
                )
                return

            except Exception as e:
                wait_time = (2 ** attempt) + 0.5
                logger.warning(
                    f"[Anthropic/Stream] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Anthropic/Stream] All {self.max_retries} attempts failed for model={model_id}")
                    yield f"[ERROR] Anthropic streaming failed after {self.max_retries} attempts: {e}"
