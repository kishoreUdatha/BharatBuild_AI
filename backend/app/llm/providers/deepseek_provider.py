"""
Deepseek Provider - Uses OpenAI-compatible API with custom base URL.
"""

import os
import time
import asyncio
import logging
from typing import AsyncGenerator, Optional, List, Dict

from app.llm.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class DeepseekProvider(BaseLLMProvider):
    """
    Deepseek provider using OpenAI-compatible API.
    Models: deepseek-chat, deepseek-coder, deepseek-reasoner
    """

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", DEEPSEEK_BASE_URL)
        self.max_retries = 3

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        """Get AsyncOpenAI client pointed at Deepseek API."""
        from openai import AsyncOpenAI

        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _build_messages(
        self,
        prompt: str,
        system_prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """Build messages list for the API call."""
        if messages:
            return messages
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        result.append({"role": "user", "content": prompt})
        return result

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
            return "[ERROR] Deepseek provider not configured. Set DEEPSEEK_API_KEY."

        model_id = self._strip_prefix(model)
        client = self._get_client()
        built_messages = self._build_messages(prompt, system_prompt, messages)

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                response = await client.chat.completions.create(
                    model=model_id,
                    messages=built_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                latency = time.time() - start_time
                output_text = response.choices[0].message.content or ""
                usage = response.usage

                logger.info(
                    f"[Deepseek] model={model_id} "
                    f"input_tokens={usage.prompt_tokens if usage else 0} "
                    f"output_tokens={usage.completion_tokens if usage else 0} "
                    f"latency={latency:.2f}s"
                )
                return output_text

            except Exception as e:
                wait_time = (2 ** attempt) + 0.5
                logger.warning(
                    f"[Deepseek] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Deepseek] All {self.max_retries} attempts failed for model={model_id}")
                    return f"[ERROR] Deepseek API failed after {self.max_retries} attempts: {e}"

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield "[ERROR] Deepseek provider not configured. Set DEEPSEEK_API_KEY."
            return

        model_id = self._strip_prefix(model)
        client = self._get_client()
        built_messages = self._build_messages(prompt, system_prompt)

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                total_chunks = 0

                stream = await client.chat.completions.create(
                    model=model_id,
                    messages=built_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        total_chunks += 1
                        yield chunk.choices[0].delta.content

                latency = time.time() - start_time
                logger.info(
                    f"[Deepseek/Stream] model={model_id} "
                    f"chunks={total_chunks} latency={latency:.2f}s"
                )
                return

            except Exception as e:
                wait_time = (2 ** attempt) + 0.5
                logger.warning(
                    f"[Deepseek/Stream] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Deepseek/Stream] All {self.max_retries} attempts failed for model={model_id}")
                    yield f"[ERROR] Deepseek streaming failed after {self.max_retries} attempts: {e}"
