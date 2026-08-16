/**
 * BharatBuild CLI — Credit Balance API Client
 *
 * Mirrors exactly how Kiro CLI manages credits server-side:
 *
 *   Kiro architecture:
 *     CLI → Kiro Backend → AWS Bedrock/OpenAI → response back
 *     Backend deducts credits, CLI displays balance from server
 *
 *   BharatBuild architecture (same):
 *     CLI → BharatBuild Backend → Model Provider → response back
 *     Backend deducts credits, CLI displays balance from server
 *
 * All credit state lives on the server. The CLI never trusts its own
 * local estimate as the source of truth — it always fetches from server.
 */

import { BharatBuildClient, APIError } from "./client.js";

// ── Types ─────────────────────────────────────────────────────────────────────

export type CreditTier = "free" | "pro" | "pro_plus" | "pro_max" | "power" | "enterprise";

export interface CreditBalance {
  tier:              CreditTier;
  creditsTotal:      number;   // total credits in plan (e.g. 1000 for Pro)
  creditsUsed:       number;   // credits consumed this billing cycle
  creditsRemaining:  number;   // creditsTotal - creditsUsed
  addOnCredits:      number;   // purchased add-on credits (on top of plan)
  resetAt:           number;   // unix ms — when credits reset (next billing cycle)
  /** Whether the user can currently make AI requests */
  canRequest:        boolean;
}

export interface CreditDeduction {
  /** Actual credits deducted by the server for this turn */
  creditsDeducted:   number;
  creditsRemaining:  number;
  model:             string;
  inputTokens:       number;
  outputTokens:      number;
  multiplier:        number;
}

export interface TierInfo {
  tier:         CreditTier;
  creditsLimit: number;
  addOnAvailable: boolean;
  models:       string[];    // model IDs available on this tier
}

// ── Tier credit limits — matches kiro.dev/docs/billing/ ──────────────────────

export const TIER_CREDITS: Record<CreditTier, number> = {
  free:       50,
  pro:        1_000,
  pro_plus:   2_000,
  pro_max:    5_000,
  power:      10_000,
  enterprise: 999_999,
};

// ── CreditClient ──────────────────────────────────────────────────────────────

export class CreditClient {
  constructor(private client: BharatBuildClient) {}

  /**
   * Fetch current credit balance from server.
   * Called on startup and after each turn to keep display accurate.
   */
  async getBalance(): Promise<CreditBalance> {
    try {
      const res = await this.client.get<{
        tier?:               string;
        credits_total?:      number;
        credits_used?:       number;
        credits_remaining?:  number;
        addon_credits?:      number;
        add_on_credits?:     number;
        reset_at?:           number;
        balance?:            number;
        tokens_remaining?:   number;
      }>("/api/v1/credits/balance");

      const remaining = res.credits_remaining ?? res.balance ?? res.tokens_remaining ?? 0;
      const used      = res.credits_used ?? 0;
      const total     = res.credits_total ?? (remaining + used);

      return {
        tier:             (res.tier ?? "free") as CreditTier,
        creditsTotal:     total,
        creditsUsed:      used,
        creditsRemaining: remaining,
        addOnCredits:     res.addon_credits ?? res.add_on_credits ?? 0,
        resetAt:          res.reset_at ?? (Date.now() + 30 * 24 * 60 * 60 * 1000),
        canRequest:       remaining > 0,
      };
    } catch (err) {
      if (err instanceof APIError && err.statusCode === 401) {
        throw err; // propagate auth errors
      }
      // Backend unreachable — return a "can't verify" state
      return {
        tier:             "free",
        creditsTotal:     0,
        creditsUsed:      0,
        creditsRemaining: -1,   // -1 = unknown
        addOnCredits:     0,
        resetAt:          0,
        canRequest:       true, // don't block — let the request fail naturally
      };
    }
  }

  /**
   * Report actual token usage to backend after a turn completes.
   * Server calculates exact credit deduction and returns new balance.
   * This is the server-authoritative credit deduction — same as Kiro.
   */
  async reportUsage(opts: {
    model:        string;
    inputTokens:  number;
    outputTokens: number;
    effort?:      string;
    sessionId?:   string;
  }): Promise<CreditDeduction | null> {
    try {
      const res = await this.client.post<{
        credits_deducted?:  number;
        credits_remaining?: number;
        model?:             string;
        input_tokens?:      number;
        output_tokens?:     number;
        multiplier?:        number;
      }>("/api/v1/credits/report", {
        model:         opts.model,
        input_tokens:  opts.inputTokens,
        output_tokens: opts.outputTokens,
        effort:        opts.effort ?? "medium",
        session_id:    opts.sessionId,
      });

      return {
        creditsDeducted:  res.credits_deducted  ?? 0,
        creditsRemaining: res.credits_remaining ?? 0,
        model:            res.model             ?? opts.model,
        inputTokens:      res.input_tokens      ?? opts.inputTokens,
        outputTokens:     res.output_tokens     ?? opts.outputTokens,
        multiplier:       res.multiplier        ?? 1.0,
      };
    } catch {
      // Backend unreachable — deduction failed silently
      // Local CostMeter estimate is shown as fallback
      return null;
    }
  }

  /**
   * Pre-flight check — can the user make a request with this model?
   * Called before each turn to gate access like Kiro does.
   */
  async canMakeRequest(model: string): Promise<{ allowed: boolean; reason?: string }> {
    try {
      const res = await this.client.post<{
        allowed: boolean;
        reason?: string;
      }>("/api/v1/credits/preflight", { model });
      return res;
    } catch {
      // If server is unreachable, allow — don't block the user
      return { allowed: true };
    }
  }

  /**
   * Formatted balance string for status bar display.
   * Matches Kiro's "X credits remaining" display.
   */
  static formatBalance(balance: CreditBalance): string {
    if (balance.creditsRemaining < 0) return "credits: ?";
    const r = balance.creditsRemaining;
    if (r === 0)    return "⚠ 0 credits";
    if (r < 10)     return `⚠ ${r.toFixed(1)} credits`;
    if (r < 100)    return `${r.toFixed(0)} credits`;
    return `${r.toFixed(0)}cr`;
  }

  /**
   * Warning level for credit balance display.
   */
  static warningLevel(balance: CreditBalance): "ok" | "low" | "critical" | "empty" {
    const r = balance.creditsRemaining;
    if (r < 0)  return "ok";      // unknown — don't warn
    if (r === 0) return "empty";
    const pct = r / Math.max(1, balance.creditsTotal + balance.addOnCredits);
    if (pct < 0.05) return "critical";
    if (pct < 0.15) return "low";
    return "ok";
  }
}
