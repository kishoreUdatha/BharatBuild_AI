"""
Model resolution for the CLI.

The CLI does not own model IDs. The server does — see backend/app/core/models.py.

This module exists to make that explicit and to keep the CLI honest: it maps a
user-facing *tier* ("haiku", "sonnet", "opus") onto whatever the server
currently routes that tier to, by asking the server. Nothing here hardcodes a
provider model string.

Why: the CLI previously carried its own tier -> model maps in standalone.py and
agentic.py. Every ID in them was retired (claude-3-sonnet-20240229 retired
2025-07-21, claude-3-5-sonnet-20241022 retired 2025-10-28, claude-3-opus-20240229
retired 2026-01-05, claude-3-5-haiku-20241022 retired 2026-02-19,
claude-3-haiku-20240307 retired 2026-04-19). Nobody noticed because nothing
pointed at a single source of truth.

In server mode the CLI should not send a model at all — the Model Router picks
per stage. `resolve()` is only for standalone/direct mode.
"""
from __future__ import annotations

import os
from typing import Final, Optional

# User-facing tier names. These are stable; the models behind them are not.
TIERS: Final[tuple[str, ...]] = ("haiku", "sonnet", "opus")
DEFAULT_TIER: Final[str] = "sonnet"

# Consulted only if the server is unreachable AND the user is in standalone
# mode. Kept deliberately minimal — if you are editing this dict, you are
# probably solving the problem in the wrong place.
#
# Update alongside backend/app/core/models.py, never independently.
_OFFLINE_FALLBACK: Final[dict[str, str]] = {
    "haiku":  "claude-haiku-4-5",
    "sonnet": "claude-sonnet-5",
    "opus":   "claude-opus-5",
}

_cache: dict[str, str] = {}


async def fetch_from_server(api_client) -> dict[str, str]:
    """
    Ask the server which model each tier currently routes to.

    `api_client` is the CLI's authenticated httpx client. Returns {} on any
    failure — callers fall back to _OFFLINE_FALLBACK.
    """
    global _cache
    if _cache:
        return _cache
    try:
        resp = await api_client.get("/api/v1/models/tiers")
        if resp.status_code == 200:
            data = resp.json()
            mapping = data.get("tiers") if isinstance(data, dict) else None
            if isinstance(mapping, dict) and mapping:
                _cache = {k: str(v) for k, v in mapping.items()}
                return _cache
    except Exception:
        pass  # offline / older server / endpoint not deployed yet
    return {}


def resolve(tier: Optional[str] = None) -> str:
    """
    Resolve a tier to a concrete model ID for standalone mode.

    Prefers what the server reported (populate via fetch_from_server), then the
    offline fallback. Server mode should not call this — omit the model and let
    the Model Router decide.
    """
    key = (tier or os.getenv("BHARATBUILD_MODEL") or DEFAULT_TIER).strip().lower()
    if key not in TIERS:
        key = DEFAULT_TIER
    return _cache.get(key) or _OFFLINE_FALLBACK[key]


def is_tier(value: str) -> bool:
    return value.strip().lower() in TIERS


__all__ = ["TIERS", "DEFAULT_TIER", "fetch_from_server", "resolve", "is_tier"]
