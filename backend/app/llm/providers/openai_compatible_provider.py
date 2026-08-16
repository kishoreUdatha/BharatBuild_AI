"""
OpenAI-Compatible Provider - Generic provider for any OpenAI-compatible API.

Supports:
- Qwen (Alibaba DashScope) - https://dashscope.aliyuncs.com/compatible-mode/v1
- MiniMax - https://api.minimax.chat/v1
- ZhiPu GLM - https://open.bigmodel.cn/api/paas/v4
- Together AI - https://api.together.xyz/v1
- Ollama (local) - http://localhost:11434/v1
- vLLM (self-hosted) - configurable
- Any other OpenAI-compatible endpoint
"""

import os
import time
import asyncio
import logging
from typing import AsyncGenerator, Optional, List, Dict

from app.llm.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

# Pre-configured provider registry
COMPATIBLE_PROVIDERS = {
    "qwen": {
        "key_env": "QWEN_API_KEY",
        "base_url_env": "QWEN_BASE_URL",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "alibaba": {
        "key_env": "QWEN_API_KEY",
        "base_url_env": "QWEN_BASE_URL",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "minimax": {
        "key_env": "MINIMAX_API_KEY",
        "base_url_env": "MINIMAX_BASE_URL",
        "default_base_url": "https://api.minimax.chat/v1",
    },
    "zhipu": {
        "key_env": "ZHIPU_API_KEY",
        "base_url_env": "ZHIPU_BASE_URL",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
    },
    "together": {
        "key_env": "TOGETHER_API_KEY",
        "base_url_env": "TOGETHER_BASE_URL",
        "default_base_url": "https://api.together.xyz/v1",
    },
    "ollama": {
        "key_env": "OLLAMA_API_KEY",
        "base_url_env": "OLLAMA_BASE_URL",
        "default_base_url": "http://localhost:11434/v1",
    },
    "vllm": {
        "key_env": "VLLM_API_KEY",
        "base_url_env": "VLLM_BASE_URL",
        "default_base_url": "http://localhost:8000/v1",
    },
}


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Generic OpenAI-compatible provider.
    Resolves API key and base URL from environment based on provider name.
    """

    def __init__(self, provider_name: str = "qwen"):
        self.provider_name = provider_name.lower()
        config = COMPATIBLE_PROVIDERS.get(self.provider_name, {})

        key_env = config.get("key_env", f"{provider_name.upper()}_API_KEY")
        base_url_env = config.get("base_url_env", f"{provider_name.upper()}_BASE_URL")
        default_base_url = config.get("default_base_url", "")

        self.api_key = os.getenv(key_env, "")
        self.base_url = os.getenv(base_url_env, default_base_url)
        self.max_retries = 3

    def is_available(self) -> bool:
        # Ollama and vLLM may not require API keys
        if self.provider_name in ("ollama", "vllm"):
            return bool(self.base_url)
        return bool(self.api_key)

    def _get_client(self):
        """Get AsyncOpenAI client with custom base_url."""
        from openai import AsyncOpenAI

        return AsyncOpenAI(
            api_key=self.api_key or "not-needed",
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
            return f"[ERROR] {self.provider_name} provider not configured. Check API key and base URL."

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
                    f"[{self.provider_name}] model={model_id} "
                    f"input_tokens={usage.prompt_tokens if usage else 0} "
                    f"output_tokens={usage.completion_tokens if usage else 0} "
                    f"latency={latency:.2f}s"
                )
                return output_text

            except Exception as e:
                wait_time = (2 ** attempt) + 0.5
                logger.warning(
                    f"[{self.provider_name}] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"[{self.provider_name}] All {self.max_retries} attempts failed for model={model_id}"
                    )
                    return f"[ERROR] {self.provider_name} API failed after {self.max_retries} attempts: {e}"

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield f"[ERROR] {self.provider_name} provider not configured. Check API key and base URL."
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
                    f"[{self.provider_name}/Stream] model={model_id} "
                    f"chunks={total_chunks} latency={latency:.2f}s"
                )
                return

            except Exception as e:
                wait_time = (2 ** attempt) + 0.5
                logger.warning(
                    f"[{self.provider_name}/Stream] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"[{self.provider_name}/Stream] All {self.max_retries} attempts failed for model={model_id}"
                    )
                    yield f"[ERROR] {self.provider_name} streaming failed after {self.max_retries} attempts: {e}"
