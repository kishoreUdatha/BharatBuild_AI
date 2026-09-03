/**
 * The credit system was calling three endpoints the backend does not serve —
 * /credits/balance, /credits/preflight, /credits/report — and every failure was
 * swallowed: preflight returned {allowed:true}, report returned null. Nothing
 * was checked, nothing deducted, and none of it was visible.
 *
 * Separately, the balance display read `tokens_remaining` while the API sends
 * `remaining_tokens` — the same two words reversed — so an account holding
 * 100,000 tokens showed "Token Balance: 0".
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { parseTokenBalance, formatTokenBalance, unknownBalance, TOKENS_BALANCE, BILLING_LIMITS } from "../../src/api/token-balance.js";
import { CreditClient } from "../../src/api/credits.js";
import { APIError } from "../../src/api/client.js";

const SRC = path.resolve(__dirname, "../../src");

/** Every .ts/.tsx file under a directory. */
function walk(dir: string): string[] {
  const out: string[] = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(full));
    else if (/\.tsx?$/.test(e.name)) out.push(full);
  }
  return out;
}
const read = (rel: string) => fs.readFileSync(path.join(SRC, rel), "utf8");

/** The exact body /api/v1/tokens/balance returns. */
const REAL_RESPONSE = {
  total_tokens: 100000, used_tokens: 0, remaining_tokens: 100000,
  monthly_allowance: 100000, monthly_used: 0, monthly_remaining: 100000,
  monthly_used_percentage: 0.0, premium_tokens: 0, premium_remaining: 0,
  rollover_tokens: 0, month_reset_date: "2026-09-01T00:00:00",
  total_requests: 0, requests_today: 0, last_request_at: null,
};

describe("reading the balance the server actually sends", () => {
  it("reads remaining_tokens, not tokens_remaining", () => {
    // The whole bug: this returned 0 for a 100,000-token account.
    expect(parseTokenBalance(REAL_RESPONSE).remaining).toBe(100000);
  });

  it("reads used and total from their real names", () => {
    const b = parseTokenBalance({ ...REAL_RESPONSE, used_tokens: 250 });
    expect(b.used).toBe(250);
    expect(b.total).toBe(100000);
  });

  it("parses the reset date, which arrives as a string not a number", () => {
    // The old code expected `reset_at` as a number and fell back to "30 days
    // from now"; the server sends `month_reset_date` as a string.
    //
    // Note the string carries no timezone ("2026-09-01T00:00:00"), so JS parses
    // it as local time — asserted in local terms here for that reason. Reading
    // it as UTC would be a guess about the server's clock, so the ambiguity is
    // left where it belongs rather than papered over.
    const d = new Date(parseTokenBalance(REAL_RESPONSE).resetAt);
    expect(d.getFullYear()).toBe(2026);
    expect(d.getMonth()).toBe(8); // September
    expect(d.getDate()).toBe(1);
  });

  it("falls back to a sensible reset when the field is missing", () => {
    expect(parseTokenBalance({ remaining_tokens: 5 }).resetAt).toBe(0);
  });

  it("still accepts the older aliases", () => {
    expect(parseTokenBalance({ tokens_remaining: 42 }).remaining).toBe(42);
    expect(parseTokenBalance({ credits_remaining: 43 }).remaining).toBe(43);
    expect(parseTokenBalance({ balance: 44 }).remaining).toBe(44);
  });

  it("prefers the canonical name when both are present", () => {
    expect(parseTokenBalance({ remaining_tokens: 1, balance: 999 }).remaining).toBe(1);
  });

  it("derives remaining from total and used when only those are given", () => {
    expect(parseTokenBalance({ total_tokens: 100, used_tokens: 30 }).remaining).toBe(70);
  });
});

describe("not confusing 'unknown' with 'empty'", () => {
  it("flags a response it could not read", () => {
    // Reporting 0 when the answer is "no idea" is how a funded account looks
    // broken — and how an empty one could look funded.
    expect(parseTokenBalance({ some: "other shape" }).unknown).toBe(true);
    expect(parseTokenBalance(REAL_RESPONSE).unknown).toBe(false);
  });

  it("treats a genuine zero as known", () => {
    const b = parseTokenBalance({ remaining_tokens: 0, total_tokens: 100, used_tokens: 100 });
    expect(b.unknown).toBe(false);
    expect(b.remaining).toBe(0);
  });

  it("says so rather than printing a number it does not have", () => {
    expect(formatTokenBalance(unknownBalance())).toBe("unknown");
    expect(formatTokenBalance(parseTokenBalance({ remaining_tokens: 0 }))).toBe("0");
  });
});

/** Minimal stand-in for BharatBuildClient. */
function fakeClient(handlers: { get?: (p: string) => unknown; post?: (p: string) => unknown }) {
  return {
    async get(p: string) {
      if (!handlers.get) throw new APIError(404, "Not Found");
      return handlers.get(p);
    },
    async post(p: string) {
      if (!handlers.post) throw new APIError(404, "Not Found");
      return handlers.post(p);
    },
  } as any;
}

describe("the credit client talks to routes that exist", () => {
  it("fetches the balance from the tokens endpoint", async () => {
    let asked = "";
    const cc = new CreditClient(fakeClient({ get: (p) => { asked = p; return REAL_RESPONSE; } }));
    const b = await cc.getBalance();
    expect(asked).toBe(TOKENS_BALANCE);
    expect(b.creditsRemaining).toBe(100000);
    expect(b.canRequest).toBe(true);
  });

  it("checks limits through the billing endpoint", async () => {
    let asked = "";
    const cc = new CreditClient(fakeClient({
      get: (p) => { asked = p; return { success: true, allowed: true, reason: null }; },
    }));
    const r = await cc.canMakeRequest("auto");
    expect(asked).toBe(BILLING_LIMITS);
    expect(r.allowed).toBe(true);
    expect(cc.lastPreflightError).toBeNull();
  });

  it("passes a refusal through instead of allowing it anyway", async () => {
    const cc = new CreditClient(fakeClient({
      get: () => ({ allowed: false, reason: "monthly limit reached" }),
    }));
    await expect(cc.canMakeRequest("auto")).resolves.toMatchObject({
      allowed: false, reason: "monthly limit reached",
    });
  });
});

describe("a failing credit check is visible", () => {
  it("still fails open, but records why", async () => {
    // Blocking a paying user over a blipped check is worse than one unmetered
    // turn — but the old code left no trace at all.
    const cc = new CreditClient(fakeClient({}));
    const r = await cc.canMakeRequest("auto");
    expect(r.allowed).toBe(true);
    expect(cc.lastPreflightError).toMatch(/not found/i);
    expect(r.reason).toMatch(/unavailable/i);
  });

  it("marks usage reporting unavailable on 404 and stops retrying", async () => {
    let calls = 0;
    const cc = new CreditClient(fakeClient({ post: () => { calls++; throw new APIError(404, "Not Found"); } }));

    await cc.reportUsage({ model: "auto", inputTokens: 1, outputTokens: 1 });
    expect(cc.usageReportingUnavailable).toBe(true);
    expect(cc.lastReportError).toMatch(/not found/i);

    // A route that answered 404 should not cost a round trip every turn.
    await cc.reportUsage({ model: "auto", inputTokens: 1, outputTokens: 1 });
    expect(calls).toBe(1);
  });
});

describe("no dead credit routes remain", () => {
  it("nothing calls the endpoints the backend does not serve", () => {
    const dead = ["/api/v1/credits/balance", "/api/v1/credits/preflight"];
    const credits = read("api/credits.ts");
    for (const route of dead) {
      // Mentioning one in a comment is fine; calling it is not.
      expect(credits, route).not.toMatch(new RegExp(`["'\`]${route.replace(/\//g, "\\/")}["'\`]`));
    }
  });

  it("balance display goes through the shared parser", () => {
    // Several call sites each rolled their own field list, and all of them
    // were wrong in the same way.
    //
    // Discovered rather than listed: the list named ui/repl.ts, and when that
    // file was deleted the test failed on a missing file instead of on
    // anything about token balances. Anything that fetches the balance has to
    // parse it with the shared helper, whatever the file is called.
    const callers = walk(SRC).filter((f) => {
      const body = fs.readFileSync(f, "utf8");
      return body.includes("TOKENS_BALANCE")
        && !f.endsWith(`${path.sep}token-balance.ts`)   // the helper itself
        && !f.endsWith(`${path.sep}credits.ts`);        // the endpoint constant
    });

    expect(callers.length, "found some balance call sites").toBeGreaterThan(0);
    for (const file of callers) {
      const body = fs.readFileSync(file, "utf8");
      expect(body, file).toContain("parseTokenBalance");
      expect(body, file).not.toMatch(/data\.tokens_remaining/);
    }
  });
});
