"""
Single source of truth for LLM routing: model IDs, pricing, per-stage
assignment, and the fix-loop escalation ladder.

Model IDs were previously hardcoded at ~20 call sites, which is how three
retired IDs stayed in production unnoticed. Nothing outside this module should
contain a literal model string.

All IDs are LiteLLM-resolvable, so a stage can be pointed at Anthropic, OpenAI,
or a self-hosted vLLM endpoint without touching caller code.
"""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Final, NamedTuple

# Ensure .env is loaded before os.getenv reads model IDs.
# This makes the module work standalone (tests, scripts) without requiring
# the caller to have loaded dotenv first.
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on system env vars


class Provider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI    = "openai"
    SELF      = "self_hosted"     # vLLM / Ollama behind an OpenAI-compatible API


class ModelSpec(NamedTuple):
    id: str                       # LiteLLM model string
    provider: Provider
    input_usd_mtok: float
    output_usd_mtok: float
    notes: str = ""


# ── stages ──────────────────────────────────────────────────────────────
class Stage(str, Enum):
    CLASSIFY     = "00_classify"
    REQUIREMENTS = "01_requirements"
    ARCHITECTURE = "02_architecture"
    PLANNING     = "03_planning"
    CONTRACT     = "04_contract"
    CODE         = "05_code"
    TEST         = "06_test"
    REVIEW       = "07_review"


# ── catalogue ───────────────────────────────────────────────────────────
# Self-hosted model string and rates are deployment-specific — override via env
# rather than editing this file.
_QWEN_ID: Final[str] = os.getenv(
    "BB_QWEN_MODEL", "hosted_vllm/Qwen/Qwen3-Coder-30B-A3B-Instruct"
)
# Self-hosted inference has no per-token invoice, but the budget gate needs a
# non-zero number or cheap-tier work looks free and never trips a cap. This is
# a nominal amortised rate; tune it to your GPU cost.
_QWEN_IN:  Final[float] = float(os.getenv("BB_QWEN_INPUT_USD_MTOK", "0.10"))
_QWEN_OUT: Final[float] = float(os.getenv("BB_QWEN_OUTPUT_USD_MTOK", "0.30"))

# These are populated from environment at import time.
# The env vars are the canonical source; the fallback is haiku (cheapest, always available).
_ENV_HAIKU:  Final[str] = os.getenv("CLAUDE_HAIKU_MODEL", "claude-haiku-4-5")
_ENV_SONNET: Final[str] = os.getenv("CLAUDE_SONNET_MODEL", "claude-haiku-4-5")
_ENV_OPUS:   Final[str] = os.getenv("CLAUDE_OPUS_MODEL", "claude-haiku-4-5")

HAIKU  = ModelSpec(f"anthropic/{_ENV_HAIKU}",  Provider.ANTHROPIC, 1.00,  5.00)
SONNET = ModelSpec(f"anthropic/{_ENV_SONNET}", Provider.ANTHROPIC, 3.00, 15.00,
                   "promo $2/$10 through 2026-08-31; billed at list to stay conservative")
OPUS   = ModelSpec(f"anthropic/{_ENV_OPUS}",   Provider.ANTHROPIC, 5.00, 25.00)
SOL    = ModelSpec("openai/gpt-5.6-sol",          Provider.OPENAI,    5.00, 30.00,
                   "GPT-5.6 frontier tier; 1M context")
QWEN   = ModelSpec(_QWEN_ID,                      Provider.SELF,   _QWEN_IN, _QWEN_OUT,
                   "self-hosted; rates are amortised, not invoiced")

CATALOGUE: Final[dict[str, ModelSpec]] = {
    m.id: m for m in (HAIKU, SONNET, OPUS, SOL, QWEN)
}


# ── per-stage routing ───────────────────────────────────────────────────
# Frontier spend is concentrated at 02 and 07: architecture decisions propagate
# into every later stage, and review is the last gate before delivery.
STAGE_MODEL: Final[dict[Stage, ModelSpec]] = {
    Stage.CLASSIFY:     HAIKU,
    Stage.REQUIREMENTS: SONNET,
    Stage.ARCHITECTURE: SOL,      # spend here
    Stage.PLANNING:     SONNET,
    Stage.CONTRACT:     SONNET,
    Stage.CODE:         QWEN,     # bulk generation; escalates on failure
    Stage.TEST:         QWEN,
    Stage.REVIEW:       SOL,      # OPUS is the configured fallback
}

# Fix-loop escalation. Attempt N uses LADDER[min(N-1, len-1)] — a failure that
# survives the cheap tier is, by definition, not a cheap failure.
FIX_LADDER: Final[tuple[ModelSpec, ...]] = (QWEN, SONNET, SOL)

# Used when a provider is unreachable or a stage's primary is rate-limited.
FALLBACK: Final[dict[str, ModelSpec]] = {
    SOL.id:  OPUS,
    QWEN.id: SONNET,
    OPUS.id: SOL,
}


# ── legacy ──────────────────────────────────────────────────────────────
# Retired IDs kept so historical usage rows stay priceable. Never route here.
#
# Every ID below was sent by this backend at some point (confirmed against git
# history), so usage rows carrying it exist. A missing entry does not raise --
# price_usd() returns 0.0 -- so an omission shows up as revenue quietly going
# to zero rather than as an error.
LEGACY_PRICING: Final[dict[str, tuple[float, float]]] = {
    "claude-3-haiku-20240307":    (0.25,  1.25),   # retired 2026-04-19
    "claude-3-5-haiku-20241022":  (0.80,  4.00),   # retired 2026-02-19
    "claude-3-5-sonnet-20241022": (3.00, 15.00),   # retired 2025-10-28
    "claude-3-sonnet-20240229":   (3.00, 15.00),   # retired 2025-07-21
    "claude-sonnet-4-20250514":   (3.00, 15.00),   # retired 2026-06-15
    # Non-canonical alias that reached the DB by hand; priced as Sonnet 3.5 so
    # it does not fall through to 0.0. SUPERSEDED_BY already knows it.
    "claude-3.5-sonnet":          (3.00, 15.00),
}

RETIRED: Final[frozenset[str]] = frozenset({
    "claude-3-haiku-20240307",
    "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet-20241022",
    "claude-3-sonnet-20240229",
    "claude-sonnet-4-20250514",
})

SUPERSEDED_BY: Final[dict[str, str]] = {
    "claude-3-haiku-20240307":    HAIKU.id,
    "claude-3-5-haiku-20241022":  HAIKU.id,
    "claude-3-5-sonnet-20241022": SONNET.id,
    "claude-3-sonnet-20240229":   SONNET.id,
    "claude-sonnet-4-20250514":   SONNET.id,
    "claude-3.5-sonnet":          SONNET.id,
}


# ── accessors ───────────────────────────────────────────────────────────
def model_for_stage(stage: Stage | str) -> ModelSpec:
    """The model a pipeline stage runs on."""
    return STAGE_MODEL[Stage(stage)]


def model_for_attempt(attempt: int) -> ModelSpec:
    """Escalate the fix loop: attempt 1 cheap, 2 standard, 3+ frontier."""
    return FIX_LADDER[min(max(attempt, 1) - 1, len(FIX_LADDER) - 1)]


def fallback_for(model_id: str) -> ModelSpec | None:
    return FALLBACK.get(model_id)


def is_retired(model_id: str) -> bool:
    return _bare(model_id) in RETIRED


def current(model_id: str) -> str:
    """Map a possibly-stale ID to its current equivalent (identity if fine)."""
    return SUPERSEDED_BY.get(_bare(model_id), model_id)


def price_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """
    Actual cost from measured token counts.

    Returns 0.0 for an unknown model rather than raising — a pricing gap must
    never break a fix loop — but callers should log it.

    Accepts both the LiteLLM-prefixed form ("anthropic/claude-haiku-4-5") and
    the bare form ("claude-haiku-4-5"). The bare form is what model_for() and
    MODELS hand out, so keying only on the prefixed form silently priced every
    call through those accessors at zero.
    """
    spec = CATALOGUE.get(model_id) or _CATALOGUE_BY_BARE.get(_bare(model_id))
    if spec is not None:
        inp, out = spec.input_usd_mtok, spec.output_usd_mtok
    else:
        legacy = LEGACY_PRICING.get(_bare(model_id))
        if legacy is None:
            return 0.0
        inp, out = legacy
    return (input_tokens / 1_000_000) * inp + (output_tokens / 1_000_000) * out


def _bare(model_id: str) -> str:
    """Strip a LiteLLM provider prefix: 'anthropic/claude-x' -> 'claude-x'."""
    return model_id.split("/", 1)[-1] if "/" in model_id else model_id


# Bare-keyed view of the catalogue, so price_usd() resolves an ID in either
# form. Referenced by price_usd above; defined here because it needs _bare.
_CATALOGUE_BY_BARE: Final[dict[str, ModelSpec]] = {
    _bare(m.id): m for m in CATALOGUE.values()
}


# ── back-compat shims for existing settings/call sites ──────────────────
class ModelTier(str, Enum):
    CHEAP    = "cheap"
    STANDARD = "standard"
    FRONTIER = "frontier"


MODELS: Final[dict[ModelTier, str]] = {
    ModelTier.CHEAP:    _ENV_HAIKU,
    ModelTier.STANDARD: _ENV_SONNET,
    ModelTier.FRONTIER: _ENV_OPUS,
}

PRICING_USD_PER_MTOK: Final[dict[str, tuple[float, float]]] = {
    **{_bare(m.id): (m.input_usd_mtok, m.output_usd_mtok) for m in CATALOGUE.values()},
    **LEGACY_PRICING,
}


def model_for(tier: ModelTier | str) -> str:
    return MODELS[ModelTier(tier)]


__all__ = [
    "Provider", "ModelSpec", "Stage",
    "HAIKU", "SONNET", "OPUS", "SOL", "QWEN", "CATALOGUE",
    "STAGE_MODEL", "FIX_LADDER", "FALLBACK",
    "LEGACY_PRICING", "RETIRED", "SUPERSEDED_BY",
    "model_for_stage", "model_for_attempt", "fallback_for",
    "is_retired", "current", "price_usd",
    "ModelTier", "MODELS", "PRICING_USD_PER_MTOK", "model_for",
]
