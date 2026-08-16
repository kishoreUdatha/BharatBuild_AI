// BharatBuild CLI — Constants

export const CLI_NAME = "bharatbuild";
export const CLI_VERSION = "1.0.0";
export const CLI_DESCRIPTION = "BharatBuild AI — AI-powered code generation for India";

// API
// Published CLI talks to production by default. Local development overrides
// with BHARATBUILD_API_URL=http://localhost:8000 or --api-url.
export const DEFAULT_API_BASE_URL = "https://bharatbuild.ai";
export const DEFAULT_WS_URL       = "wss://bharatbuild.ai/ws";

/** Where the web login page lives — used by the browser login flow. */
export const LOGIN_PAGE_URL = "https://bharatbuild.ai/login";
export const DEFAULT_TIMEOUT_MS   = 300_000; // 5 minutes
export const DEFAULT_CONNECT_TIMEOUT_MS = 10_000;

// Models
//
// Single source of truth for model IDs. Nothing else in src/ should contain a
// literal provider model string - every ID here was previously duplicated
// across ~20 files, which is how three retired IDs stayed in place unnoticed
// (claude-3-5-sonnet-20241022 retired 2025-10-28, claude-3-5-haiku-20241022
// retired 2026-02-19). A retired ID returns HTTP 404 from the API.
//
// Callers should prefer a tier name ("haiku"/"sonnet"/"opus") and let
// resolveModel() map it, so the next model refresh touches only this block.
//
// Model IDs mirror exactly what Kiro CLI exposes (kiro.dev/docs/models/).
// All Claude models go through Anthropic's API directly.
// GPT-5.6 models go through OpenAI's API.
// Budget open-weight models (DeepSeek, MiniMax, GLM, Qwen) go through
// their respective provider APIs.
export const MODEL_TIERS = {
  // ── Anthropic Claude — primary tiers ──────────────────────────────────────
  haiku:        "claude-haiku-4-5",        // fast / cheap — free tier default
  sonnet:       "claude-sonnet-5",         // default working tier
  opus:         "claude-opus-5",           // hardest tasks, best quality

  // ── Anthropic Claude — previous Sonnet versions (Kiro free tier) ──────────
  sonnet46:     "claude-sonnet-4-6",       // 1M context
  sonnet45:     "claude-sonnet-4-5",       // 200K context
  sonnet40:     "claude-sonnet-4-0",       // 200K context

  // ── Anthropic Claude — previous Opus versions ─────────────────────────────
  opus48:       "claude-opus-4-8",         // updated tokenizer vs 4.6
  opus47:       "claude-opus-4-7",
  opus46:       "claude-opus-4-6",         // 1M context
  opus45:       "claude-opus-4-5",         // 200K context

  // ── OpenAI GPT-5.6 tiers ─────────────────────────────────────────────────
  gpt56sol:     "gpt-5.6-sol",             // hardest multi-step, 2.4x cost
  gpt56terra:   "gpt-5.6-terra",           // balanced agentic, 1.0x cost
  gpt56luna:    "gpt-5.6-luna",            // high-freq / cheapest GPT, 0.1x

  // ── Budget open-weight models ─────────────────────────────────────────────
  deepseek:     "deepseek-3.2",            // 128K, 0.25x cost
  minimax25:    "minimax-m2.5",            // 200K, near-Opus at 0.25x
  minimax21:    "minimax-m2.1",            // 200K, 0.15x
  glm5:         "glm-5",                   // 200K, repo-scale at 0.5x
  qwen3:        "qwen3-coder-next",        // 256K, cheapest at 0.05x
} as const;

export type ModelTier = keyof typeof MODEL_TIERS;

export const HAIKU_MODEL  = MODEL_TIERS.haiku;
export const SONNET_MODEL = MODEL_TIERS.sonnet;
export const OPUS_MODEL   = MODEL_TIERS.opus;

/** The tier used when a caller supplies nothing and auto-select is not in play. */
export const DEFAULT_TIER: ModelTier = "haiku";

/** Sentinel meaning "pick a model per request" - see models/auto-select.ts. */
export const DEFAULT_MODEL = "auto";

export function isModelTier(value: string): value is ModelTier {
  return value in MODEL_TIERS;
}

/**
 * Resolve whatever a caller has (tier name, concrete ID, "auto", or nothing)
 * into a concrete model ID.
 *
 * Passing "auto" through unchanged is deliberate: the model router treats it
 * as a sentinel and selects per request.
 */
export function resolveModel(value?: string | null): string {
  const v = (value ?? "").trim();
  if (!v) return MODEL_TIERS[DEFAULT_TIER];
  if (v === DEFAULT_MODEL) return DEFAULT_MODEL;
  if (isModelTier(v)) return MODEL_TIERS[v];
  return v; // already a concrete provider ID
}

// Agent loop
export const MAX_TURNS           = 50;
export const MAX_TOOL_RETRIES    = 3;
export const MAX_EMPTY_RETRIES   = 3;
export const CONTEXT_LIMIT_WARN  = 0.85; // warn at 85% context usage

// Retry
export const RETRY_BASE_DELAY_MS = 1_000;
export const RETRY_MAX_DELAY_MS  = 30_000;
export const RETRY_MAX_ATTEMPTS  = 4;

// Session
export const SESSION_DIR         = ".bharatbuild/sessions";
export const CHECKPOINT_DIR      = ".bharatbuild/checkpoints";
export const CONFIG_FILE         = ".bharatbuild/config.json";
export const CREDENTIALS_FILE    = ".bharatbuild/credentials.json";
export const HISTORY_FILE        = ".bharatbuild/history.json";

// Tools
export const MAX_FILE_READ_BYTES  = 1_000_000; // 1 MB
export const MAX_SHELL_OUTPUT     = 50_000;    // chars
export const SHELL_TIMEOUT_MS     = 120_000;   // 2 minutes
export const MAX_SEARCH_RESULTS   = 100;

// Permissions
export const DANGEROUS_COMMANDS = [
  "rm", "rmdir", "del", "format", "mkfs",
  "dd", "shred", "truncate",
  "chmod", "chown", "sudo", "su",
  "curl", "wget", "nc", "netcat",
  "git push --force", "git reset --hard",
  "DROP TABLE", "DROP DATABASE", "DELETE FROM",
];

export const ALWAYS_SAFE_TOOLS = [
  "read_file", "list_files", "search_code",
  "find_files", "git_status", "git_diff",
];

// UI
export const SPINNER_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"];
export const THINKING_MESSAGES = [
  "thinking…",
  "analyzing your codebase…",
  "planning the approach…",
  "writing code…",
  "reviewing changes…",
];
