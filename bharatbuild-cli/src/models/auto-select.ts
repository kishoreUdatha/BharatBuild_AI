/**
 * BharatBuild CLI — Auto Model Selector
 *
 * Exact implementation of Kiro CLI's "Auto" routing logic:
 *
 *   1. Detect task complexity from prompt text + conversation length
 *   2. Score every available model by: quality fit × context adequacy ÷ cost
 *   3. Apply effort level override (low/medium/high/xhigh/max)
 *   4. Emit selected model + reason as a status event so TUI can display it
 *
 * Routing table mirrors kiro.dev/docs/models/ credit multipliers:
 *
 *   Qwen3 Coder Next   0.05x  — simple / high-freq
 *   MiniMax M2.1       0.15x  — moderate budget
 *   DeepSeek 3.2       0.25x  — moderate standard
 *   MiniMax M2.5       0.25x  — near-Opus budget
 *   Claude Haiku 4.5   0.4x   — fast iterations
 *   GLM-5              0.5x   — long-context budget
 *   Auto / Terra       1.0x   — everyday agentic baseline
 *   Claude Sonnet 5    1.3x   — complex / near-Opus
 *   Claude Opus 5      2.2x   — hardest tasks
 *   GPT-5.6 Sol        2.4x   — longest-horizon agentic
 */

import { MODEL_REGISTRY, type ModelInfo } from "./model-registry.js";
import { MODEL_TIERS } from "../config/constants.js";
import { availableProviders } from "../auth/provider-key.js";

export type TaskComplexity = "simple" | "moderate" | "complex" | "expert";
export type EffortLevel    = "low" | "medium" | "high" | "xhigh" | "max";

export interface AutoSelectOptions {
  effort?:        EffortLevel;
  preferCost?:    boolean;   // always pick cheapest capable model
  preferSpeed?:   boolean;   // pick fastest (lowest cost-in, usually smallest)
  requireTools?:  boolean;   // must support tool use
  contextLength?: number;    // minimum context window the session needs
  availableKeys?: string[];  // which providers have API keys
}

export interface AutoSelectResult {
  modelId:    string;
  modelName:  string;
  reason:     string;
  complexity: TaskComplexity;
  multiplier: number;        // Kiro credit multiplier of the selected model
}

// ── Complexity detection ──────────────────────────────────────────────────────
//
// Mirrors Kiro's server-side heuristics. Three signals:
//   a) prompt length                  — longer = more context needed
//   b) keyword patterns               — architectural / agentic keywords bump up
//   c) conversation depth             — deep sessions likely complex

export function detectComplexity(
  prompt: string,
  conversationTurns = 0,
): TaskComplexity {
  const p   = prompt.toLowerCase();
  const len = prompt.length;

  // Expert: architecture, security, full-stack refactors, long prompts
  if (
    len > 500 ||
    conversationTurns > 20 ||
    /refactor|architect|design pattern|migration|audit|multi[- ]?agent|orchestrat|scalab|concurrent|parallel agent|long.?horizon/i.test(p)
  ) return "expert";

  // Complex: implement features, debug hard issues, explain systems
  if (
    len > 200 ||
    conversationTurns > 8 ||
    /implement|create|build|generate|write (a|the)|explain|debug|why (is|does|did)|how (does|do|did)|test suite|integration test/i.test(p)
  ) return "complex";

  // Moderate: small edits, single-function tasks, quick questions
  if (
    len > 60 ||
    conversationTurns > 2 ||
    /fix|add|update|change|rename|move|convert|format|lint|typo|import|export/i.test(p)
  ) return "moderate";

  // Simple: one-liners, lookups, yes/no
  return "simple";
}

// ── Effort → complexity + model hint ─────────────────────────────────────────

interface EffortProfile {
  complexity:     TaskComplexity;
  /** Minimum credit multiplier the selected model must have */
  minMultiplier:  number;
  /** Maximum credit multiplier — keeps budget tasks cheap */
  maxMultiplier:  number;
}

const EFFORT_PROFILES: Record<EffortLevel, EffortProfile> = {
  low:   { complexity: "simple",   minMultiplier: 0,    maxMultiplier: 0.4  },
  medium:{ complexity: "moderate", minMultiplier: 0,    maxMultiplier: 0.5  },
  high:  { complexity: "complex",  minMultiplier: 0.4,  maxMultiplier: 1.3  },
  xhigh: { complexity: "expert",   minMultiplier: 1.0,  maxMultiplier: 2.2  },
  max:   { complexity: "expert",   minMultiplier: 2.0,  maxMultiplier: 99   },
};

// ── Provider key detection ────────────────────────────────────────────────────

export function detectAvailableProviders(): string[] {
  const p: string[] = [];
  // Through the shared resolver, so a key stored on disk counts. This read the
  // environment directly, so once keys could be stored the candidate list came
  // back empty and every task — "simple" or "expert" — hard-fell-back to the
  // cheapest model. The complexity was still computed, then discarded.
  const stored = availableProviders();
  if (stored.includes("anthropic"))                                   p.push("anthropic");
  if (stored.includes("openai"))                                      p.push("openai");
  // The registry calls Gemini's provider "google"; the key store calls it
  // "gemini". Same thing, two spellings.
  if (stored.includes("gemini"))                                      p.push("google");
  if (process.env["AWS_ACCESS_KEY_ID"])                               p.push("bedrock");
  if (process.env["DEEPSEEK_API_KEY"])                                p.push("deepseek");
  if (process.env["MINIMAX_API_KEY"])                                 p.push("minimax");
  if (process.env["ZHIPU_API_KEY"])                                   p.push("zhipu");
  if (process.env["QWEN_API_KEY"])                                    p.push("qwen");
  p.push("ollama"); // local — always potentially available
  return p;
}

// ── Scoring ───────────────────────────────────────────────────────────────────
//
// Each model gets a score 0–100.  Higher = better fit for the task.
// Kiro's Auto maximises quality-per-credit, biased by complexity tier.

function scoreModel(model: ModelInfo, complexity: TaskComplexity): number {
  if (model.id === "auto") return -1; // never self-select

  const m = model.creditMultiplier;

  // Quality score: how well the model's tier matches the complexity
  let quality = 0;
  switch (complexity) {
    case "simple":
      // Best score at 0.05–0.4x; heavy models waste credits
      quality = m <= 0.4  ? 90 - (m * 50) :
                m <= 1.0  ? 60 - ((m - 0.4) * 40) :
                            20 - ((m - 1.0) * 10);
      break;
    case "moderate":
      // Sweet spot at 0.25–0.5x
      quality = m <= 0.25 ? 60 + (m * 100) :
                m <= 0.5  ? 85 :
                m <= 1.0  ? 80 - ((m - 0.5) * 30) :
                            50 - ((m - 1.0) * 10);
      break;
    case "complex":
      // Sweet spot at 1.0–1.3x (Sonnet / Terra tier)
      quality = m < 0.4   ? 30 :
                m < 1.0   ? 30 + ((m - 0.4) * 60) :
                m <= 1.3  ? 90 :
                            85 - ((m - 1.3) * 5);
      break;
    case "expert":
      // Best at 2.0–2.4x (Opus / Sol); Sonnet acceptable
      quality = m < 1.0   ? 20 :
                m < 1.3   ? 50 :
                m < 2.0   ? 60 + ((m - 1.3) * 30) :
                            90 + ((m - 2.0) * 10);
      break;
  }

  // Context window bonus — big windows are better for complex/expert
  const ctxBonus = complexity === "expert" || complexity === "complex"
    ? Math.min(10, model.contextWindow / 100000)
    : 0;

  // Cost penalty — prefer cheaper when quality is similar
  const costPenalty = m * 2;

  return Math.max(0, quality + ctxBonus - costPenalty);
}

// ── Main auto-select function ─────────────────────────────────────────────────

export function autoSelectModel(
  prompt: string,
  opts: AutoSelectOptions = {},
  conversationTurns = 0,
): AutoSelectResult {
  const available = opts.availableKeys ?? detectAvailableProviders();

  // Determine complexity
  const complexity = opts.effort
    ? EFFORT_PROFILES[opts.effort].complexity
    : detectComplexity(prompt, conversationTurns);

  const effortProfile = opts.effort ? EFFORT_PROFILES[opts.effort] : null;

  // Build candidate list — filter by availability, tool support, context need
  const candidates = MODEL_REGISTRY.filter((m) => {
    if (m.id === "auto")                                    return false;
    if (opts.requireTools && !m.supportsTools)              return false;
    if (opts.contextLength && m.contextWindow < opts.contextLength) return false;
    if (m.provider === "ollama")                            return true;
    if (!available.includes(m.provider))                   return false;
    // Effort bounds: clip to multiplier range
    if (effortProfile) {
      if (m.creditMultiplier < effortProfile.minMultiplier) return false;
      if (m.creditMultiplier > effortProfile.maxMultiplier) return false;
    }
    return true;
  });

  // Hard fallback — no keys at all, use Haiku
  if (candidates.length === 0) {
    const fallback = MODEL_REGISTRY.find((m) => m.id === MODEL_TIERS.haiku)!;
    return {
      modelId:    MODEL_TIERS.haiku,
      modelName:  fallback?.name ?? "Claude Haiku 4.5",
      reason:     "Fallback — no provider API keys detected",
      complexity,
      multiplier: 0.4,
    };
  }

  let selected: ModelInfo;
  let reason: string;

  if (opts.preferCost) {
    // Always cheapest capable
    selected = candidates.sort((a, b) => a.creditMultiplier - b.creditMultiplier)[0]!;
    reason   = `Cost-optimised — cheapest model for ${complexity} task`;
  } else if (opts.preferSpeed) {
    // Lowest input cost = usually fastest (smallest model)
    selected = candidates.sort((a, b) => a.costPer1kIn - b.costPer1kIn)[0]!;
    reason   = `Speed-optimised for ${complexity} task`;
  } else {
    // Score all candidates — pick highest
    const scored = candidates
      .map((m) => ({ model: m, score: scoreModel(m, complexity) }))
      .sort((a, b) => b.score - a.score);

    selected = scored[0]!.model;
    const score = scored[0]!.score.toFixed(0);
    reason = `Auto: ${complexity} task → ${selected.name} (score ${score}, ${selected.creditMultiplier}x)`;
  }

  return {
    modelId:    selected.id,
    modelName:  selected.name,
    reason,
    complexity,
    multiplier: selected.creditMultiplier,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

export const AUTO_MODEL_ID = "auto";

export function isAutoModel(modelId: string): boolean {
  return modelId.toLowerCase() === "auto" || modelId.toLowerCase() === "auto-select";
}
