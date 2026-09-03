"""
Gemini-protocol compatibility layer for the BharatBuild backend.

Gemini CLI (and any other client that speaks the Google GenAI wire format)
talks to `{base_url}/v1beta/models/{model}:generateContent` and
`:streamGenerateContent`, sending Gemini-shaped bodies. This module exposes
those routes and translates them to the Anthropic Messages shape that
`claude_client` already speaks, so a client can point at this server with:

    GOOGLE_GEMINI_BASE_URL=http://localhost:8000

The translation is the whole job. Gemini and Anthropic differ in four places
that matter:

  1. Roles          - Gemini says "model", Anthropic says "assistant".
  2. Content        - Gemini nests everything in `parts`, Anthropic in typed
                      content blocks.
  3. Tool calls     - Gemini `functionCall`/`functionResponse` vs Anthropic
                      `tool_use`/`tool_result`.
  4. Tool call IDs  - Anthropic requires a `tool_use_id` to pair a result with
                      its call. Gemini's `functionResponse` carries only the
                      function *name*, so the id has to be reconstructed by
                      tracking calls as the history is walked. See
                      `_translate_contents`.

Mounted at the app root (not under /api/v1) because the Gemini path prefix is
fixed by the client SDK and cannot be configured.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any, Tuple
import asyncio
import json
import uuid

from jose import ExpiredSignatureError, JWTError, jwt

from app.utils.claude_client import claude_client
from app.core.config import settings
from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User

router = APIRouter(prefix="/v1beta", tags=["Gemini Compatibility"])


# =============================================================================
# Auth
# =============================================================================
#
# The Gemini client does not send `Authorization: Bearer`. It sends the
# credential as `x-goog-api-key`, or as a `?key=` query parameter. Both carry
# the same BharatBuild access token, so accept all three spellings and fall
# through to the normal token decode.


def _decode_credential(token: str) -> Dict[str, Any]:
    """
    Decode a credential, distinguishing expiry from every other failure.

    The shared `decode_token` collapses all JWT errors into one opaque
    "Could not validate credentials". That is fine for a browser session, where
    the frontend silently refreshes, but a CLI operator staring at a 401 has no
    way to tell a lapsed token from a wrong one. Expiry gets its own message and
    tells the caller what to do about it.
    """
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail=(
                "Credential expired. Access tokens last "
                f"{settings.ACCESS_TOKEN_EXPIRE_MINUTES // 60}h - use your refresh "
                f"token instead ({settings.REFRESH_TOKEN_EXPIRE_DAYS}d), or sign in "
                "again to mint a new one."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_gemini_user(
    db: AsyncSession = Depends(get_db),
    x_goog_api_key: Optional[str] = Header(default=None, alias="x-goog-api-key"),
    authorization: Optional[str] = Header(default=None),
    key: Optional[str] = Query(default=None),
) -> User:
    """
    Resolve the caller from a Gemini-style credential.

    Both access and refresh tokens are accepted here, which the interactive API
    deliberately does not do. The reason is that a CLI holds one static string
    for the whole session and has no way to rotate it: the Gemini client sends
    whatever is in GEMINI_API_KEY on every request and never reads a new token
    back. Accepting only access tokens would therefore break the CLI every 24
    hours. A refresh token is never exchanged for anything here — it is only
    proof of identity — so this widens the window from
    ACCESS_TOKEN_EXPIRE_MINUTES to REFRESH_TOKEN_EXPIRE_DAYS without granting
    any capability an access token would not already have.
    """
    token = x_goog_api_key or key
    if not token and authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = value

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing credential. Send the x-goog-api-key header.",
        )

    payload = _decode_credential(token)
    token_type = payload.get("type")
    if token_type not in ("access", "refresh"):
        raise HTTPException(
            status_code=401,
            detail=f"Unsupported token type: {token_type!r}",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token has no subject")
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Malformed subject in token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# =============================================================================
# Model mapping
# =============================================================================
#
# The client asks for Gemini model names. Route the small/fast tier to Haiku and
# everything else to Sonnet, matching what /agentic/chat already does.

def _resolve_model(model: str) -> str:
    name = (model or "").lower()
    if any(token in name for token in ("flash", "lite", "haiku", "small")):
        return claude_client.haiku_model
    return claude_client.sonnet_model


# =============================================================================
# Gemini -> Anthropic
# =============================================================================


def _translate_tools(gemini_tools: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Gemini: [{"functionDeclarations": [{name, description, parameters}]}]
    Anthropic: [{name, description, input_schema}]
    """
    if not gemini_tools:
        return []

    tools: List[Dict[str, Any]] = []
    for entry in gemini_tools:
        for decl in entry.get("functionDeclarations", []) or []:
            name = decl.get("name")
            if not name:
                continue
            tools.append({
                "name": name,
                "description": decl.get("description", ""),
                # An empty object schema is valid; a missing one is not.
                "input_schema": decl.get("parameters") or {
                    "type": "object", "properties": {},
                },
            })
    return tools


def _translate_contents(
    contents: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Translate Gemini `contents` into Anthropic `messages`.

    Gemini's functionResponse identifies its call by function *name* only, while
    Anthropic pairs by `tool_use_id`. So as the history is walked, the id minted
    for each tool_use is remembered under its name, and the matching
    functionResponse claims it. Names can repeat across turns, so the most
    recent unclaimed id for that name wins.
    """
    messages: List[Dict[str, Any]] = []
    pending_ids: Dict[str, List[str]] = {}
    call_counter = 0

    for content in contents or []:
        gemini_role = content.get("role", "user")
        role = "assistant" if gemini_role == "model" else "user"
        blocks: List[Dict[str, Any]] = []

        for part in content.get("parts", []) or []:
            if "text" in part and part.get("text") is not None:
                text = part["text"]
                # Anthropic rejects empty text blocks.
                if text != "":
                    blocks.append({"type": "text", "text": text})

            elif "functionCall" in part:
                call = part["functionCall"] or {}
                name = call.get("name", "")
                call_counter += 1
                tool_id = f"toolu_compat_{call_counter}"
                pending_ids.setdefault(name, []).append(tool_id)
                blocks.append({
                    "type": "tool_use",
                    "id": tool_id,
                    "name": name,
                    "input": call.get("args") or {},
                })

            elif "functionResponse" in part:
                resp = part["functionResponse"] or {}
                name = resp.get("name", "")
                queue = pending_ids.get(name)
                tool_id = queue.pop(0) if queue else f"toolu_compat_orphan_{name}"
                payload = resp.get("response")
                blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": payload if isinstance(payload, str)
                    else json.dumps(payload, ensure_ascii=False),
                })

            elif "inlineData" in part:
                inline = part["inlineData"] or {}
                mime = inline.get("mimeType", "")
                if mime.startswith("image/"):
                    blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": inline.get("data", ""),
                        },
                    })
                else:
                    # Non-image blobs have no Anthropic equivalent; naming the
                    # type beats dropping the part silently.
                    blocks.append({
                        "type": "text",
                        "text": f"[unsupported inline data: {mime or 'unknown'}]",
                    })

        if not blocks:
            continue

        # Anthropic rejects consecutive messages with the same role, which
        # Gemini histories do contain (e.g. a model turn split across parts).
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"].extend(blocks)
        else:
            messages.append({"role": role, "content": blocks})

    return messages


def _extract_system(body: Dict[str, Any]) -> Optional[str]:
    instruction = body.get("systemInstruction") or body.get("system_instruction")
    if not instruction:
        return None
    if isinstance(instruction, str):
        return instruction
    parts = instruction.get("parts", []) or []
    text = "".join(p.get("text", "") for p in parts)
    return text or None


def _build_anthropic_request(model: str, body: Dict[str, Any]) -> Dict[str, Any]:
    config = body.get("generationConfig") or {}
    messages = _translate_contents(body.get("contents") or [])
    if not messages:
        raise HTTPException(status_code=400, detail="No contents in request")

    system = _extract_system(body)

    # Gemini's JSON mode has no direct Anthropic equivalent. Steering via the
    # system prompt is the closest thing; without it the caller gets prose where
    # it expected parseable JSON. The CLI's model router depends on this.
    if config.get("responseMimeType") == "application/json":
        schema = config.get("responseJsonSchema") or config.get("responseSchema")
        directive = (
            "Respond with a single valid JSON object and nothing else. "
            "No markdown fences, no prose before or after."
        )
        if schema:
            directive += f"\nIt must conform to this JSON Schema:\n{json.dumps(schema)}"
        system = f"{system}\n\n{directive}" if system else directive

    request: Dict[str, Any] = {
        "model": _resolve_model(model),
        "max_tokens": config.get("maxOutputTokens") or 8192,
        "messages": messages,
    }
    if system:
        request["system"] = system

    tools = _translate_tools(body.get("tools"))
    if tools:
        request["tools"] = tools

    # `temperature` and `topP` are dropped, not translated. The Gemini client
    # sends both on every request, and anthropic 1.x removed both from
    # messages.create() for every model - forwarding either raises TypeError
    # on the call below, which splats this dict. Sampling stays at the model
    # default.
    if config.get("stopSequences"):
        request["stop_sequences"] = config["stopSequences"]

    return request


# =============================================================================
# Anthropic -> Gemini
# =============================================================================

_STOP_REASONS = {
    "end_turn": "STOP",
    "tool_use": "STOP",
    "stop_sequence": "STOP",
    "max_tokens": "MAX_TOKENS",
    "refusal": "SAFETY",
}


def _usage(input_tokens: int, output_tokens: int) -> Dict[str, int]:
    return {
        "promptTokenCount": input_tokens,
        "candidatesTokenCount": output_tokens,
        "totalTokenCount": input_tokens + output_tokens,
    }


def _gemini_response(
    parts: List[Dict[str, Any]],
    finish_reason: str,
    usage: Dict[str, int],
) -> Dict[str, Any]:
    return {
        "candidates": [{
            "content": {"role": "model", "parts": parts},
            "finishReason": finish_reason,
            "index": 0,
            "safetyRatings": [],
        }],
        "usageMetadata": usage,
    }


# =============================================================================
# Routes
# =============================================================================
#
# Path note: the ":generateContent" suffix is part of the literal path segment,
# not a path parameter. FastAPI matches it as `{model}:generateContent` because
# the colon has no special meaning in a path template.


@router.post("/models/{model}:generateContent")
async def generate_content(
    model: str,
    request: Request,
    current_user: User = Depends(get_gemini_user),
):
    """Non-streaming Gemini generateContent."""
    body = await request.json()
    anthropic_request = _build_anthropic_request(model, body)

    logger.info(
        f"[GeminiCompat] user={current_user.id} model={model} "
        f"-> {anthropic_request['model']} (generateContent)"
    )

    try:
        response = await claude_client.async_client.messages.create(**anthropic_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GeminiCompat] Upstream error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Upstream model error: {e}")

    parts: List[Dict[str, Any]] = []
    for block in response.content:
        if block.type == "text":
            parts.append({"text": block.text})
        elif block.type == "tool_use":
            parts.append({"functionCall": {"name": block.name, "args": block.input}})

    if not parts:
        parts = [{"text": ""}]

    return _gemini_response(
        parts,
        _STOP_REASONS.get(response.stop_reason, "STOP"),
        _usage(response.usage.input_tokens, response.usage.output_tokens),
    )


@router.post("/models/{model}:streamGenerateContent")
async def stream_generate_content(
    model: str,
    request: Request,
    current_user: User = Depends(get_gemini_user),
):
    """
    Streaming Gemini generateContent.

    The client requests `?alt=sse` and expects Server-Sent Events whose payloads
    are each a full GenerateContentResponse carrying only the new delta. Tool
    calls cannot stream incrementally in this format, so each one is emitted as
    a single chunk once its arguments have finished arriving.
    """
    body = await request.json()
    anthropic_request = _build_anthropic_request(model, body)

    logger.info(
        f"[GeminiCompat] user={current_user.id} model={model} "
        f"-> {anthropic_request['model']} (stream)"
    )

    async def event_generator():
        try:
            async with claude_client.async_client.messages.stream(
                **anthropic_request
            ) as stream:
                current_tool: Optional[Dict[str, Any]] = None

                async for event in stream:
                    if event.type == "content_block_start":
                        block = getattr(event, "content_block", None)
                        if block is not None and getattr(block, "type", None) == "tool_use":
                            current_tool = {"name": block.name, "input": ""}

                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            chunk = _gemini_response(
                                [{"text": delta.text}], None, _usage(0, 0)
                            )
                            # finishReason must be absent mid-stream, not null,
                            # or strict clients treat the turn as complete.
                            chunk["candidates"][0].pop("finishReason", None)
                            chunk.pop("usageMetadata", None)
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        elif hasattr(delta, "partial_json") and current_tool is not None:
                            current_tool["input"] += delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool is not None:
                            try:
                                args = json.loads(current_tool["input"] or "{}")
                            except (json.JSONDecodeError, TypeError) as e:
                                logger.debug(f"[GeminiCompat] Bad tool JSON: {e}")
                                args = {}
                            chunk = _gemini_response(
                                [{"functionCall": {
                                    "name": current_tool["name"], "args": args,
                                }}],
                                None,
                                _usage(0, 0),
                            )
                            chunk["candidates"][0].pop("finishReason", None)
                            chunk.pop("usageMetadata", None)
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                            current_tool = None

                    await asyncio.sleep(0)

                final = await stream.get_final_message()
                yield "data: " + json.dumps(
                    _gemini_response(
                        [],
                        _STOP_REASONS.get(final.stop_reason, "STOP"),
                        _usage(final.usage.input_tokens, final.usage.output_tokens),
                    ),
                    ensure_ascii=False,
                ) + "\n\n"

        except Exception as e:
            logger.error(f"[GeminiCompat] Stream error: {e}", exc_info=True)
            # There is no SSE error frame in the Gemini format; surfacing it as
            # a normal error envelope is what the client knows how to read.
            yield "data: " + json.dumps({
                "error": {"code": 500, "message": str(e), "status": "INTERNAL"}
            }) + "\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/models/{model}:countTokens")
async def count_tokens(
    model: str,
    request: Request,
    current_user: User = Depends(get_gemini_user),
):
    """
    Token counting.

    Clients call this to decide when to compress history, so a 404 here shows up
    as a context-management failure rather than an obvious missing route. Uses
    Anthropic's counter when available and falls back to a character estimate,
    since an approximate count is far better than an error.
    """
    body = await request.json()
    messages = _translate_contents(body.get("contents") or [])
    if not messages:
        return {"totalTokens": 0}

    payload: Dict[str, Any] = {"model": _resolve_model(model), "messages": messages}
    system = _extract_system(body)
    if system:
        payload["system"] = system

    try:
        result = await claude_client.async_client.messages.count_tokens(**payload)
        return {"totalTokens": result.input_tokens}
    except Exception as e:
        logger.warning(f"[GeminiCompat] count_tokens unavailable, estimating: {e}")
        chars = len(json.dumps(messages, ensure_ascii=False))
        return {"totalTokens": max(1, chars // 4)}


@router.get("/models")
async def list_models(current_user: User = Depends(get_gemini_user)):
    """Model listing, in the shape the Gemini client expects."""
    return {
        "models": [
            {
                "name": f"models/{name}",
                "displayName": display,
                "supportedGenerationMethods": [
                    "generateContent", "streamGenerateContent", "countTokens",
                ],
                "inputTokenLimit": 200000,
                "outputTokenLimit": 8192,
            }
            for name, display in (
                ("bharatbuild-pro", "BharatBuild Pro"),
                ("bharatbuild-flash", "BharatBuild Flash"),
            )
        ]
    }
