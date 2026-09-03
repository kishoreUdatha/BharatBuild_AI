/**
 * Reading the token balance the backend actually sends.
 *
 * Three call sites each did their own `data.balance ?? data.tokens_remaining ?? 0`.
 * The field is `remaining_tokens` - the two words the other way round - so every
 * one of them fell through to 0. An account holding 100,000 tokens displayed as
 * "Token Balance: 0", which is why metering looked broken from the outside.
 *
 * The aliases below are kept because older builds of the API did send some of
 * them; the canonical names come first so a correct response always wins.
 */

import { AGENTIC_CHAT_STREAM } from "./endpoints.js";

/** GET /api/v1/tokens/balance */
export const TOKENS_BALANCE = "/api/v1/tokens/balance";

/** GET /api/v1/billing/limits — answers "may this request proceed?" */
export const BILLING_LIMITS = "/api/v1/billing/limits";

/** GET /api/v1/usage/session — per-session totals. */
export const USAGE_SESSION = "/api/v1/usage/session";

export interface TokenBalance {
  /** Tokens left to spend. -1 when the server could not be reached. */
  remaining: number;
  used: number;
  total: number;
  /** Allowance that resets monthly, when the plan has one. */
  monthlyRemaining: number;
  monthlyUsed: number;
  /** Tokens bought on top of the plan allowance. */
  premiumRemaining: number;
  rollover: number;
  resetAt: number;
  /** True when the balance is genuinely unknown, not genuinely zero. */
  unknown: boolean;
}

function num(...candidates: unknown[]): number | undefined {
  for (const c of candidates) {
    if (typeof c === "number" && Number.isFinite(c)) return c;
  }
  return undefined;
}

export function parseTokenBalance(raw: Record<string, unknown>): TokenBalance {
  // Canonical names first, then the aliases older builds used.
  const remaining = num(raw["remaining_tokens"], raw["tokens_remaining"], raw["credits_remaining"], raw["balance"], raw["available"]);
  const used = num(raw["used_tokens"], raw["tokens_used"], raw["credits_used"], raw["used"]);
  const total = num(raw["total_tokens"], raw["credits_total"], raw["total"]);

  const resolvedUsed = used ?? 0;
  const resolvedRemaining = remaining ?? (total !== undefined ? total - resolvedUsed : 0);

  const resetRaw = raw["month_reset_date"] ?? raw["reset_at"];
  let resetAt = 0;
  if (typeof resetRaw === "number") resetAt = resetRaw;
  else if (typeof resetRaw === "string") {
    const parsed = Date.parse(resetRaw);
    if (!Number.isNaN(parsed)) resetAt = parsed;
  }

  return {
    remaining: resolvedRemaining,
    used: resolvedUsed,
    total: total ?? resolvedRemaining + resolvedUsed,
    monthlyRemaining: num(raw["monthly_remaining"]) ?? resolvedRemaining,
    monthlyUsed: num(raw["monthly_used"]) ?? resolvedUsed,
    premiumRemaining: num(raw["premium_remaining"], raw["premium_tokens"]) ?? 0,
    rollover: num(raw["rollover_tokens"]) ?? 0,
    resetAt,
    // A response with no recognisable field is not a zero balance. Saying "0"
    // when the answer is "no idea" is how a working account looks broken.
    unknown: remaining === undefined && total === undefined,
  };
}

/** The balance when the server could not be asked at all. */
export function unknownBalance(): TokenBalance {
  return {
    remaining: -1, used: 0, total: 0,
    monthlyRemaining: -1, monthlyUsed: 0,
    premiumRemaining: 0, rollover: 0,
    resetAt: 0, unknown: true,
  };
}

/** Formatted for display; distinguishes "unknown" from "empty". */
export function formatTokenBalance(b: TokenBalance): string {
  if (b.unknown || b.remaining < 0) return "unknown";
  return b.remaining.toLocaleString("en-IN");
}

// Re-exported so callers touching the credit path have one import site.
export { AGENTIC_CHAT_STREAM };
