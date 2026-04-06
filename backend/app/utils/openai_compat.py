"""
OpenAI-compatible wrapper that mimics the Anthropic SDK interface.

This module provides AsyncAnthropic and Anthropic classes that use
OpenAI-compatible API (LM Studio, Ollama, etc.) under the hood,
but expose the same interface as the Anthropic SDK.

This allows all existing code that does:
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=...)
    response = await client.messages.create(model=..., messages=..., system=...)

To work with LM Studio by simply changing the import to:
    from app.utils.openai_compat import AsyncAnthropic
"""

import os
import asyncio
from typing import Optional, Dict, List, Any, AsyncIterator
from dataclasses import dataclass
from openai import AsyncOpenAI, OpenAI

from app.core.config import settings
from app.core.logging_config import logger


# ── Response dataclasses that mimic Anthropic SDK response objects ──

@dataclass
class TextBlock:
    type: str
    text: str
    id: str = ""
    name: str = ""
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {}


@dataclass
class ToolUseBlock:
    type: str
    id: str
    name: str
    input: dict


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class AnthropicResponse:
    """Mimics anthropic.types.Message"""
    id: str
    content: list
    usage: Usage
    stop_reason: str
    model: str

    @property
    def type(self):
        return "message"


class StreamWrapper:
    """Mimics anthropic's stream context manager with text_stream"""

    def __init__(self, oai_stream, model: str):
        self._stream = oai_stream
        self._model = model
        self._collected_text = []
        self._final_message = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    @property
    def text_stream(self):
        return self._text_iterator()

    async def _text_iterator(self):
        async for chunk in self._stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                self._collected_text.append(text)
                yield text

    async def __aiter__(self):
        """Iterate over raw SSE events (for agentic.py streaming)"""
        async for chunk in self._stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                self._collected_text.append(text)
                yield _StreamEvent("content_block_delta", text)

    async def get_final_message(self):
        full_text = "".join(self._collected_text)
        return AnthropicResponse(
            id=f"lm-stream-{id(self)}",
            content=[TextBlock(type="text", text=full_text)],
            usage=Usage(
                input_tokens=0,  # LM Studio doesn't provide this in streaming
                output_tokens=len(full_text) // 4
            ),
            stop_reason="end_turn",
            model=self._model
        )


@dataclass
class _StreamEvent:
    type: str
    text: str = ""

    @property
    def content_block(self):
        return TextBlock(type="text", text=self.text)


# ── Messages API wrapper ──

class AsyncMessages:
    """Mimics anthropic.AsyncAnthropic().messages"""

    def __init__(self, client: AsyncOpenAI, default_model: str = "qwen3-4b-instruct-2507"):
        self._client = client
        self._default_model = default_model

    async def create(
        self,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str = "",
        messages: list = None,
        tools: list = None,
        tool_choice: dict = None,
        **kwargs
    ) -> AnthropicResponse:
        """Mimics client.messages.create() - converts Anthropic format to OpenAI format"""
        model = model or self._default_model

        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        if messages:
            for msg in messages:
                content = msg.get("content", "")
                role = msg.get("role", "user")

                # Handle Anthropic's tool_result format
                if isinstance(content, list):
                    # Flatten tool results into text
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "tool_result":
                                text_parts.append(f"Tool result ({item.get('tool_use_id', '')}): {item.get('content', '')}")
                            elif item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            else:
                                text_parts.append(str(item))
                        elif hasattr(item, 'text'):
                            text_parts.append(item.text)
                        else:
                            text_parts.append(str(item))
                    content = "\n".join(text_parts)

                oai_messages.append({"role": role, "content": str(content)})

        # Convert Anthropic tools to OpenAI function format if provided
        oai_tools = None
        if tools:
            oai_tools = []
            for tool in tools:
                oai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {})
                    }
                })

        create_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": oai_messages,
        }

        if oai_tools:
            create_kwargs["tools"] = oai_tools
            if tool_choice:
                tc_type = tool_choice.get("type", "auto")
                if tc_type == "any":
                    create_kwargs["tool_choice"] = "required"
                elif tc_type == "auto":
                    create_kwargs["tool_choice"] = "auto"
                else:
                    create_kwargs["tool_choice"] = "auto"

        try:
            response = await self._client.chat.completions.create(**create_kwargs)
        except Exception as e:
            logger.error(f"[OpenAI Compat] API error: {e}")
            raise

        # Convert OpenAI response to Anthropic format
        choice = response.choices[0] if response.choices else None
        content_blocks = []
        stop_reason = "end_turn"

        if choice:
            # Handle tool calls
            if choice.message.tool_calls:
                import json as _json
                for tc in choice.message.tool_calls:
                    try:
                        tool_input = _json.loads(tc.function.arguments)
                    except (ValueError, _json.JSONDecodeError):
                        tool_input = {"raw": tc.function.arguments}

                    content_blocks.append(ToolUseBlock(
                        type="tool_use",
                        id=tc.id or f"tool-{id(tc)}",
                        name=tc.function.name,
                        input=tool_input
                    ))
                stop_reason = "tool_use"

            # Handle text content
            if choice.message.content:
                content_blocks.append(TextBlock(
                    type="text",
                    text=choice.message.content
                ))

            if choice.finish_reason == "length":
                stop_reason = "max_tokens"
            elif choice.finish_reason == "tool_calls":
                stop_reason = "tool_use"

        if not content_blocks:
            content_blocks.append(TextBlock(type="text", text=""))

        usage = response.usage
        return AnthropicResponse(
            id=response.id or f"lm-{id(response)}",
            content=content_blocks,
            usage=Usage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0
            ),
            stop_reason=stop_reason,
            model=model
        )

    def stream(
        self,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str = "",
        messages: list = None,
        tools: list = None,
        **kwargs
    ) -> StreamWrapper:
        """Mimics client.messages.stream() context manager"""
        model = model or self._default_model

        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        if messages:
            for msg in messages:
                content = msg.get("content", "")
                role = msg.get("role", "user")
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            text_parts.append(item.get("text", item.get("content", str(item))))
                        else:
                            text_parts.append(str(item))
                    content = "\n".join(text_parts)
                oai_messages.append({"role": role, "content": str(content)})

        async def _create_stream():
            return await self._client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=oai_messages,
                stream=True
            )

        # Return a wrapper that creates the stream lazily
        return _LazyStreamWrapper(_create_stream, model)


class _LazyStreamWrapper:
    """Wrapper that creates the stream on __aenter__"""

    def __init__(self, create_fn, model):
        self._create_fn = create_fn
        self._model = model
        self._wrapper = None

    async def __aenter__(self):
        stream = await self._create_fn()
        self._wrapper = StreamWrapper(stream, self._model)
        return self._wrapper

    async def __aexit__(self, *args):
        pass


class SyncMessages:
    """Mimics anthropic.Anthropic().messages (sync version)"""

    def __init__(self, client: OpenAI, default_model: str = "qwen3-4b-instruct-2507"):
        self._client = client
        self._default_model = default_model

    def create(
        self,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str = "",
        messages: list = None,
        **kwargs
    ) -> AnthropicResponse:
        model = model or self._default_model

        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        if messages:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            text_parts.append(item.get("text", item.get("content", str(item))))
                        else:
                            text_parts.append(str(item))
                    content = "\n".join(text_parts)
                oai_messages.append({"role": msg.get("role", "user"), "content": str(content)})

        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=oai_messages
        )

        choice = response.choices[0] if response.choices else None
        content_blocks = []

        if choice and choice.message.content:
            content_blocks.append(TextBlock(type="text", text=choice.message.content))
        else:
            content_blocks.append(TextBlock(type="text", text=""))

        usage = response.usage
        return AnthropicResponse(
            id=response.id or f"lm-{id(response)}",
            content=content_blocks,
            usage=Usage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0
            ),
            stop_reason="end_turn",
            model=model
        )


# ── Main wrapper classes ──

class AsyncAnthropic:
    """Drop-in replacement for anthropic.AsyncAnthropic using OpenAI-compatible API"""

    def __init__(self, api_key: str = None, **kwargs):
        base_url = settings.OPENAI_API_BASE
        api_key = api_key or settings.OPENAI_API_KEY
        model = settings.CLAUDE_HAIKU_MODEL

        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.messages = AsyncMessages(self._client, default_model=model)


class Anthropic:
    """Drop-in replacement for anthropic.Anthropic (sync) using OpenAI-compatible API"""

    def __init__(self, api_key: str = None, **kwargs):
        base_url = settings.OPENAI_API_BASE
        api_key = api_key or settings.OPENAI_API_KEY
        model = settings.CLAUDE_HAIKU_MODEL

        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self.messages = SyncMessages(self._client, default_model=model)


# Dummy exception classes for backward compatibility
class APIStatusError(Exception):
    pass

class APIError(Exception):
    pass

class APIConnectionError(Exception):
    pass

class APITimeoutError(Exception):
    pass
