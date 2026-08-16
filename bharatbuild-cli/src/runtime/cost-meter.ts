// BharatBuild CLI — Cost Meter
//
// Tracks token usage, USD cost, AND Kiro-style fractional credits.
//
// How Kiro calculates credits (from kiro.dev/docs/billing/):
//
//   credits = (tokens / BASELINE_TOKENS_PER_CREDIT) × model_multiplier
//
//   - BASELINE_TOKENS_PER_CREDIT: the token budget Auto (1.0x) spends per credit
//     Kiro doesn't publish the exact number, but from real usage patterns it's
//     approximately 1,000 combined tokens per credit on Auto.
//   - model_multiplier: per-model credit multiplier (0.05x for Qwen3 → 2.4x for Sol)
//   - Credits are fractional — 0.3 credits is a valid value
//   - Same model multiplier ≠ same credits: Opus 4.8 vs 4.6 have different
//     tokenizers so the same prompt costs different credits at the same 2.2x rate
//
// Per-turn credit formula:
//   turnCredits = ((inputTokens + outputTokens) / BASELINE_TOKENS_PER_CREDIT)
//                 × modelMultiplier
//                 × effortMultiplier   (higher effort = more internal thinking tokens)

import { MODEL_TIERS } from "../config/constants.js";
import { MODEL_REGISTRY } from "../models/model-registry.js";

// ── Constants ─────────────────────────────────────────────────────────────────

/**
 * Approximate combined tokens per 1 Kiro credit on the Auto (1.0x) baseline.
 * Derived from published credit allocations + typical task token counts.
 * Free tier: 50 credits. A typical "write a function" task ≈ 2,000 tokens → ~2 credits.
 * Therefore: 1,000 tokens ≈ 1 credit on Auto.
 */
const BASELINE_TOKENS_PER_CREDIT = 1_000;

/**
 * Effort level multipliers — higher effort means more internal reasoning tokens
 * which Kiro counts even though they aren't all visible in the output.
 */
const EFFORT_MULTIPLIERS: Record<string, number> = {
  low:   0.5,
  medium: 1.0,
  high:  1.5,
  xhigh: 2.0,
  max:   3.0,
};

// ── Pricing per 1M tokens (USD list price) ────────────────────────────────────

const MODEL_PRICING: Record<string, {
  input: number; output: number;
  cacheRead?: number; cacheWrite?: number;
}> = {
  // Claude — Anthropic list price
  [MODEL_TIERS.haiku]:    { input: 0.80,  output: 4.00,  cacheRead: 0.08,  cacheWrite: 1.00  },
  [MODEL_TIERS.sonnet]:   { input: 3.00,  output: 15.00, cacheRead: 0.30,  cacheWrite: 3.75  },
  [MODEL_TIERS.opus]:     { input: 15.00, output: 75.00, cacheRead: 1.50,  cacheWrite: 18.75 },
  [MODEL_TIERS.sonnet46]: { input: 3.00,  output: 15.00, cacheRead: 0.30,  cacheWrite: 3.75  },
  [MODEL_TIERS.sonnet45]: { input: 3.00,  output: 15.00, cacheRead: 0.30,  cacheWrite: 3.75  },
  [MODEL_TIERS.sonnet40]: { input: 3.00,  output: 15.00, cacheRead: 0.30,  cacheWrite: 3.75  },
  [MODEL_TIERS.opus48]:   { input: 15.00, output: 75.00, cacheRead: 1.50,  cacheWrite: 18.75 },
  [MODEL_TIERS.opus47]:   { input: 15.00, output: 75.00, cacheRead: 1.50,  cacheWrite: 18.75 },
  [MODEL_TIERS.opus46]:   { input: 15.00, output: 75.00, cacheRead: 1.50,  cacheWrite: 18.75 },
  [MODEL_TIERS.opus45]:   { input: 15.00, output: 75.00, cacheRead: 1.50,  cacheWrite: 18.75 },
  // GPT-5.6 — OpenAI list price
  [MODEL_TIERS.gpt56sol]:   { input: 12.00, output: 48.00 },
  [MODEL_TIERS.gpt56terra]: { input: 5.00,  output: 20.00 },
  [MODEL_TIERS.gpt56luna]:  { input: 0.50,  output: 2.00  },
  // Budget open-weight
  [MODEL_TIERS.deepseek]:   { input: 0.27,  output: 1.10  },
  [MODEL_TIERS.minimax25]:  { input: 0.27,  output: 1.10  },
  [MODEL_TIERS.minimax21]:  { input: 0.16,  output: 0.64  },
  [MODEL_TIERS.glm5]:       { input: 0.54,  output: 2.16  },
  [MODEL_TIERS.qwen3]:      { input: 0.054, output: 0.22  },
};

// ── Types ─────────────────────────────────────────────────────────────────────

export interface TokenUsage {
  inputTokens:      number;
  outputTokens:     number;
  cacheReadTokens:  number;
  cacheWriteTokens: number;
}

export interface TurnRecord {
  model:         string;
  inputTokens:   number;
  outputTokens:  number;
  credits:       number;
  costUsd:       number;
  durationMs:    number;
  effort:        string;
}

// ── CostMeter ─────────────────────────────────────────────────────────────────

export class CostMeter {
  private _model:     string;
  private _effort:    string;
  private _usage:     TokenUsage = { inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, cacheWriteTokens: 0 };
  private _turns:     number = 0;
  private _credits:   number = 0;   // Kiro-style fractional credits
  private _costUsd:   number = 0;   // USD
  private _startTime: number = Date.now();
  private _turnLog:   TurnRecord[] = [];

  constructor(model: string, effort = "medium") {
    this._model  = model;
    this._effort = effort;
  }

  /** Call once per model response with the token counts from the API */
  add(usage: Partial<TokenUsage>, opts?: { durationMs?: number; model?: string }): void {
    const model      = opts?.model ?? this._model;
    const inputTok   = usage.inputTokens      ?? 0;
    const outputTok  = usage.outputTokens     ?? 0;
    const cacheRead  = usage.cacheReadTokens  ?? 0;
    const cacheWrite = usage.cacheWriteTokens ?? 0;

    this._usage.inputTokens      += inputTok;
    this._usage.outputTokens     += outputTok;
    this._usage.cacheReadTokens  += cacheRead;
    this._usage.cacheWriteTokens += cacheWrite;

    // ── USD cost ───────────────────────────────────────────────────────────
    const pricing = MODEL_PRICING[model];
    let turnCostUsd = 0;
    if (pricing) {
      const M = 1_000_000;
      turnCostUsd  = (inputTok   / M) * pricing.input;
      turnCostUsd += (outputTok  / M) * pricing.output;
      turnCostUsd += (cacheRead  / M) * (pricing.cacheRead  ?? 0);
      turnCostUsd += (cacheWrite / M) * (pricing.cacheWrite ?? 0);
    }
    this._costUsd += turnCostUsd;

    // ── Kiro credits ───────────────────────────────────────────────────────
    // credits = (totalTokens / BASELINE) × modelMultiplier × effortMultiplier
    const totalTok       = inputTok + outputTok;
    const modelMultiplier  = this._getModelMultiplier(model);
    const effortMultiplier = EFFORT_MULTIPLIERS[this._effort] ?? 1.0;
    const turnCredits      = (totalTok / BASELINE_TOKENS_PER_CREDIT)
                             * modelMultiplier
                             * effortMultiplier;
    this._credits += turnCredits;

    this._turns++;
    this._turnLog.push({
      model,
      inputTokens:  inputTok,
      outputTokens: outputTok,
      credits:      turnCredits,
      costUsd:      turnCostUsd,
      durationMs:   opts?.durationMs ?? 0,
      effort:       this._effort,
    });
  }

  /** Look up credit multiplier from registry, fallback to 1.0 */
  private _getModelMultiplier(modelId: string): number {
    const info = MODEL_REGISTRY.find((m) => m.id === modelId);
    return info?.creditMultiplier ?? 1.0;
  }

  // ── Getters ────────────────────────────────────────────────────────────────

  get totalTokens(): number { return this._usage.inputTokens + this._usage.outputTokens; }
  get usage():       TokenUsage { return { ...this._usage }; }
  get turns():       number { return this._turns; }
  get elapsedMs():   number { return Date.now() - this._startTime; }
  get credits():     number { return this._credits; }
  get turnLog():     TurnRecord[] { return [...this._turnLog]; }

  /** USD cost for the session */
  estimateCostUsd(): number { return this._costUsd; }

  /** One-line session summary — matches Kiro's status bar format */
  summary(): string {
    const secs = Math.round(this.elapsedMs / 1000);
    const creditsStr = this._credits >= 0.01
      ? `${this._credits.toFixed(2)} credits`
      : `<0.01 credits`;
    const costStr = this._costUsd > 0
      ? ` · $${this._costUsd.toFixed(4)}`
      : "";
    return (
      `${this.totalTokens.toLocaleString()} tokens · ${creditsStr}${costStr}` +
      ` · ${secs}s · ${this._turns} turn${this._turns !== 1 ? "s" : ""}`
    );
  }

  /** Breakdown per turn — for /logdump and /usage detail */
  breakdown(): string {
    if (this._turnLog.length === 0) return "  No turns recorded.";
    const lines: string[] = [];
    this._turnLog.forEach((t, i) => {
      lines.push(
        `  Turn ${i + 1}: ${t.model.split("-").slice(0, 3).join("-")}` +
        `  ${(t.inputTokens + t.outputTokens).toLocaleString()} tok` +
        `  ${t.credits.toFixed(3)} credits` +
        `  $${t.costUsd.toFixed(5)}` +
        (t.durationMs ? `  ${t.durationMs}ms` : "")
      );
    });
    return lines.join("\n");
  }

  /** Update active model mid-session (when Auto switches models) */
  setModel(model: string): void { this._model = model; }

  /** Update effort level */
  setEffort(effort: string): void { this._effort = effort; }

  /**
   * Report usage to the BharatBuild backend for server-authoritative
   * credit deduction. Same as Kiro's backend deducting after each turn.
   * Fire-and-forget — never blocks the UI.
   */
  async reportToServer(opts: {
    sessionId?: string;
    authToken?: string;
    apiBaseUrl?: string;
  } = {}): Promise<void> {
    const lastTurn = this._turnLog[this._turnLog.length - 1];
    if (!lastTurn || !opts.authToken) return;

    const baseUrl = opts.apiBaseUrl ?? process.env["BHARATBUILD_API_URL"] ?? "http://localhost:8000";
    try {
      await fetch(`${baseUrl}/api/v1/credits/report`, {
        method: "POST",
        headers: {
          "Content-Type":  "application/json",
          "Authorization": `Bearer ${opts.authToken}`,
        },
        body: JSON.stringify({
          model:         lastTurn.model,
          input_tokens:  lastTurn.inputTokens,
          output_tokens: lastTurn.outputTokens,
          effort:        lastTurn.effort,
          session_id:    opts.sessionId,
        }),
        signal: AbortSignal.timeout(5_000),
      });
    } catch {
      // Fire-and-forget — never throw, never block
    }
  }

  reset(): void {
    this._usage    = { inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, cacheWriteTokens: 0 };
    this._turns    = 0;
    this._credits  = 0;
    this._costUsd  = 0;
    this._startTime = Date.now();
    this._turnLog  = [];
  }
}
