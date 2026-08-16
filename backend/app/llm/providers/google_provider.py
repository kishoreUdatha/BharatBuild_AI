"""
Google Gemini Provider - Uses httpx for direct API access.
Supports streaming via Server-Sent Events.
"""

import os
import time
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional, List, Dict

import httpx

from app.llm.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GoogleProvider(BaseLLMProvider):
    """
    Google Gemini provider using HTTP API directly via httpx.
    Models: gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash, gemini-2.5-pro, etc.
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY", "")
        self.base_url = os.getenv("GOOGLE_API_BASE_URL", GOOGLE_API_BASE)
        self.max_retries = 3

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_contents(
        self,
        prompt: str,
        system_prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> tuple:
        """Build contents and system_instruction for Gemini API."""
        system_instruction = None
        if system_prompt:
            system_instruction = {"parts": [{"text": system_prompt}]}

        if messages:
            contents = []
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}],
                })
            return contents, system_instruction

        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        return contents, system_instruction

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
            return "[ERROR] Google provider not configured. Set GOOGLE_API_KEY."

        model_id = self._strip_prefix(model)
        contents, system_instruction = self._build_contents(prompt, system_prompt, messages)

        url = f"{self.base_url}/models/{model_id}:generateContent"
        params = {"key": self.api_key}

        body: Dict = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_instruction:
            body["systemInstruction"] = system_instruction

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, params=params, json=body)
                    response.raise_for_status()
                    data = response.json()

                latency = time.time() - start_time

                # Extract text from response
                candidates = data.get("candidates", [])
                if not candidates:
                    return "[ERROR] Google API returned no candidates."

                parts = candidates[0].get("content", {}).get("parts", [])
                output_text = "".join(p.get("text", "") for p in parts)

                # Token usage
                usage_meta = data.get("usageMetadata", {})
                input_tokens = usage_meta.get("promptTokenCount", 0)
                output_tokens = usage_meta.get("candidatesTokenCount", 0)

                logger.info(
                    f"[Google] model={model_id} "
                    f"input_tokens={input_tokens} output_tokens={output_tokens} "
                    f"latency={latency:.2f}s"
                )
                return output_text

            except Exception as e:
                wait_time = (2 ** attempt) + 0.5
                logger.warning(
                    f"[Google] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Google] All {self.max_retries} attempts failed for model={model_id}")
                    return f"[ERROR] Google API failed after {self.max_retries} attempts: {e}"

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield "[ERROR] Google provider not configured. Set GOOGLE_API_KEY."
            return

        model_id = self._strip_prefix(model)
        contents, system_instruction = self._build_contents(prompt, system_prompt)

        url = f"{self.base_url}/models/{model_id}:streamGenerateContent"
        params = {"key": self.api_key, "alt": "sse"}

        body: Dict = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_instruction:
            body["systemInstruction"] = system_instruction

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                total_chunks = 0

                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream("POST", url, params=params, json=body) as response:
                        response.raise_for_status()
                        buffer = ""
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                json_str = line[6:]
                                if json_str.strip() == "[DONE]":
                                    break
                                try:
                                    chunk_data = json.loads(json_str)
                                    candidates = chunk_data.get("candidates", [])
                                    if candidates:
                                        parts = candidates[0].get("content", {}).get("parts", [])
                                        for part in parts:
                                            text = part.get("text", "")
                                            if text:
                                                total_chunks += 1
                                                yield text
                                except json.JSONDecodeError:
                                    continue

                latency = time.time() - start_time
                logger.info(
                    f"[Google/Stream] model={model_id} "
                    f"chunks={total_chunks} latency={latency:.2f}s"
                )
                return

            except Exception as e:
                wait_time = (2 ** attempt) + 0.5
                logger.warning(
                    f"[Google/Stream] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Google/Stream] All {self.max_retries} attempts failed for model={model_id}")
                    yield f"[ERROR] Google streaming failed after {self.max_retries} attempts: {e}"
