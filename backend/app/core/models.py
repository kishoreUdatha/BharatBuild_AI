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
# The env vars are the canonical source; each fallback is the CURRENT model of
# that tier.
#
# These previously all fell back to haiku. That turned a missing env var into a
# silent capability downgrade: every "escalate to Sonnet/Opus" path ran Haiku
# while still logging "Using Sonnet model", and SUPERSEDED_BY resolved a retired
# Sonnet ID to Haiku. A tier fallback must stay inside its own tier.
# Canonical current model per tier. Used both as the env fallback and as the
# replacement suggested when a configured ID turns out to be retired -- that
# hint must NOT be derived from the env var, or a retired ID ends up
# recommending itself.
CURRENT_HAIKU:  Final[str] = "claude-haiku-4-5"
CURRENT_SONNET: Final[str] = "claude-sonnet-5"
CURRENT_OPUS:   Final[str] = "claude-opus-5"

_ENV_HAIKU:  Final[str] = os.getenv("CLAUDE_HAIKU_MODEL", CURRENT_HAIKU)
_ENV_SONNET: Final[str] = os.getenv("CLAUDE_SONNET_MODEL", CURRENT_SONNET)
_ENV_OPUS:   Final[str] = os.getenv("CLAUDE_OPUS_MODEL", CURRENT_OPUS)

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

# Canonical list price per ACTUAL model, independent of which tier slot routed
# to it. This is the authority for billing.
#
# CATALOGUE is keyed by id, so when two tiers are pointed at the same model
# (e.g. a cost-saving profile with CLAUDE_SONNET_MODEL=claude-haiku-4-5) the
# entries collapse and the LAST spec wins -- which billed every Haiku call at
# Opus rates, a 5x overcharge. A call that ran on claude-haiku-4-5 costs Haiku
# money regardless of which tier asked for it, so price by model, not by tier.
LIST_PRICING: Final[dict[str, tuple[float, float]]] = {
    "claude-haiku-4-5":  (1.00,  5.00),
    "claude-sonnet-5":   (3.00, 15.00),   # $2/$10 intro through 2026-08-31
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-5":     (5.00, 25.00),
    "claude-opus-4-8":   (5.00, 25.00),
    "claude-opus-4-7":   (5.00, 25.00),
    "claude-fable-5":    (10.00, 50.00),
    "gpt-5.6-sol":       (5.00, 30.00),
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
    "claude-opus-4-20250514":     (15.00, 75.00),  # retired 2026-06-15
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
    "claude-opus-4-20250514",
})

SUPERSEDED_BY: Final[dict[str, str]] = {
    "claude-3-haiku-20240307":    HAIKU.id,
    "claude-3-5-haiku-20241022":  HAIKU.id,
    "claude-3-5-sonnet-20241022": SONNET.id,
    "claude-3-sonnet-20240229":   SONNET.id,
    "claude-sonnet-4-20250514":   SONNET.id,
    "claude-opus-4-20250514":     OPUS.id,
    "claude-3.5-sonnet":          SONNET.id,
}


# Model families that reject `temperature` / `top_p` / `top_k`. Sending any of
# them returns 400, so the sampling kwargs must be dropped per-model rather than
# passed unconditionally. Matched against the bare ID prefix so date-suffixed
# and future point releases of the same family are covered.
_NO_SAMPLING_PARAMS: Final[tuple[str, ...]] = (
    "claude-opus-5",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
)


def accepts_sampling_params(model_id: str) -> bool:
    """
    Whether `temperature`/`top_p`/`top_k` may be sent to this model.

    Opus 4.7+ and the 5-series removed them: a request carrying `temperature`
    returns 400 rather than ignoring it. Haiku 4.5 and older Sonnet still
    accept them.
    """
    bare = _bare(model_id)
    return not any(bare.startswith(prefix) for prefix in _NO_SAMPLING_PARAMS)


def sampling_kwargs(model_id: str, temperature: float | None) -> dict:
    """
    Sampling kwargs to splat into a messages.create() call.

    Always empty. anthropic 1.x dropped `temperature`/`top_p`/`top_k` from
    `messages.create()` for every model, so passing one raises TypeError
    client-side before a request is ever sent - a stricter rule than
    accepts_sampling_params(), which stays accurate about what the models
    themselves take but no longer decides what may be sent through the SDK.

    Kept as a function, and still called at each Anthropic call site, so the
    per-model rule can be restored here alone if the kwargs ever return.
    """
    return {}


def assert_not_retired() -> list[str]:
    """
    Names of configured models that are retired (and therefore 404 at the API).

    is_retired()/SUPERSEDED_BY were written as the safety net for exactly this
    and were never called from anywhere, so a retired ID in the environment
    reached production unnoticed. Called from the startup config validation.
    """
    problems = []
    for label, spec, replacement in (
        ("CLAUDE_HAIKU_MODEL",  HAIKU,  CURRENT_HAIKU),
        ("CLAUDE_SONNET_MODEL", SONNET, CURRENT_SONNET),
        ("CLAUDE_OPUS_MODEL",   OPUS,   CURRENT_OPUS),
    ):
        if is_retired(spec.id):
            problems.append(
                f"{label}={_bare(spec.id)} is retired and will 404 - use {replacement}"
            )
    return problems


def collapsed_tiers() -> list[str]:
    """
    Warnings for tier slots configured to the same underlying model.

    Legitimate as a cost-saving profile, but it has non-obvious consequences
    worth logging: "escalate to Sonnet" becomes a no-op, and CATALOGUE/FALLBACK
    are keyed by model id so the colliding entries overwrite each other.
    """
    warnings = []
    tiers = {"haiku": HAIKU.id, "sonnet": SONNET.id, "opus": OPUS.id}
    by_model: dict[str, list[str]] = {}
    for tier, model_id in tiers.items():
        by_model.setdefault(model_id, []).append(tier)

    for model_id, sharing in by_model.items():
        if len(sharing) > 1:
            warnings.append(
                f"tiers {'+'.join(sharing)} all point at {_bare(model_id)} - "
                "escalation between them is a no-op"
            )
    return warnings


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
    bare = _bare(model_id)

    # LIST_PRICING first: it is keyed by the actual model, so it stays correct
    # even when several tier slots collapse onto one model in CATALOGUE.
    priced = LIST_PRICING.get(bare)
    if priced is not None:
        inp, out = priced
    else:
        spec = CATALOGUE.get(model_id) or _CATALOGUE_BY_BARE.get(bare)
        if spec is not None:
            inp, out = spec.input_usd_mtok, spec.output_usd_mtok
        else:
            legacy = LEGACY_PRICING.get(bare)
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
    "is_retired", "current", "price_usd", "assert_not_retired",
    "accepts_sampling_params", "sampling_kwargs", "collapsed_tiers",
    "LIST_PRICING", "CURRENT_HAIKU", "CURRENT_SONNET", "CURRENT_OPUS",
    "ModelTier", "MODELS", "PRICING_USD_PER_MTOK", "model_for",
]
