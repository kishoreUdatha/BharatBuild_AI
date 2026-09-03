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
import { TOKENS_BALANCE, BILLING_LIMITS, parseTokenBalance } from "./token-balance.js";

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
  /**
   * Why the last credit check failed, if it did. The preflight used to
   * swallow a 404 on every turn and return {allowed:true}, so a completely
   * absent credit system was indistinguishable from a working one.
   */
  lastPreflightError: string | null = null;

  /** Why the last usage report failed, if it did. */
  lastReportError: string | null = null;

  /**
   * Set once the backend answers 404 for usage reporting. Deduction is then
   * server-side only, and any balance shown locally is an estimate.
   */
  usageReportingUnavailable = false;

  constructor(private client: BharatBuildClient) {}

  /**
   * Fetch current credit balance from server.
   * Called on startup and after each turn to keep display accurate.
   */
  async getBalance(): Promise<CreditBalance> {
    try {
      // /api/v1/credits/balance is not served - it 404d, this caught it, and
      // the caller was told the balance was unknown forever. The real route is
      // /api/v1/tokens/balance.
      const res = await this.client.get<Record<string, unknown>>(TOKENS_BALANCE);
      const b = parseTokenBalance(res);

      return {
        tier:             (typeof res["tier"] === "string" ? res["tier"] : "free") as CreditTier,
        creditsTotal:     b.total,
        creditsUsed:      b.used,
        creditsRemaining: b.unknown ? -1 : b.remaining,
        addOnCredits:     b.premiumRemaining,
        resetAt:          b.resetAt || Date.now() + 30 * 24 * 60 * 60 * 1000,
        // Only gate on a number the server actually gave us.
        canRequest:       b.unknown || b.remaining > 0,
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
    // Once the route has answered 404 there is no point paying a round trip
    // for it on every subsequent turn.
    if (this.usageReportingUnavailable) return null;
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
    } catch (err) {
      // /api/v1/credits/report is not served. This caught the 404 and returned
      // null on every turn, so nothing was ever deducted and the failure was
      // invisible — the CLI then showed a local estimate as though it were an
      // authoritative balance.
      //
      // Deduction belongs server-side during generation regardless: a client
      // that reports its own usage can simply decline to report it.
      const status = err instanceof APIError ? err.statusCode : 0;
      this.lastReportError = err instanceof Error ? err.message : String(err);
      if (status === 404) this.usageReportingUnavailable = true;
      return null;
    }
  }

  /**
   * Pre-flight check — can the user make a request with this model?
   * Called before each turn to gate access like Kiro does.
   */
  async canMakeRequest(model: string): Promise<{ allowed: boolean; reason?: string }> {
    try {
      // /api/v1/credits/preflight does not exist. /api/v1/billing/limits
      // answers the same question and is already served:
      //   {"success":true,"allowed":true,"reason":null,"current_usage":0,"limit":null}
      const res = await this.client.get<{
        allowed?: boolean;
        reason?:  string | null;
      }>(BILLING_LIMITS);
      return { allowed: res.allowed !== false, reason: res.reason ?? undefined };
    } catch (err) {
      // Still fail open - blocking a paying user because a check endpoint
      // blipped is worse than one unmetered turn - but no longer silently.
      // This swallowed a 404 on every single turn and nobody could tell.
      this.lastPreflightError = err instanceof Error ? err.message : String(err);
      return { allowed: true, reason: "credit check unavailable" };
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
