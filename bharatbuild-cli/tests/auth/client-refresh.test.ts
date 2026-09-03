/**
 * Regression tests for the failure that made every command print
 * "Could not validate credentials" 30 minutes after login: the client had no
 * 401 handling at all, so a recoverable session was never refreshed.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BharatBuildClient, APIError } from "../../src/api/client.js";

const realFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = realFetch; });

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("401 handling", () => {
  it("refreshes once and retries the request", async () => {
    const seen: string[] = [];
    globalThis.fetch = vi.fn(async (_url: any, init: any) => {
      const auth = init.headers["Authorization"];
      seen.push(auth);
      if (auth === "Bearer stale") return jsonResponse({ detail: "Could not validate credentials" }, 401);
      return jsonResponse({ email: "a@b.c" });
    }) as any;

    const client = new BharatBuildClient({
      apiBaseUrl: "http://x",
      authToken: "stale",
      onUnauthorized: async () => "fresh",
    });

    await expect(client.get("/api/v1/auth/me")).resolves.toEqual({ email: "a@b.c" });
    expect(seen).toEqual(["Bearer stale", "Bearer fresh"]);
  });

  it("does not retry more than once", async () => {
    let calls = 0;
    globalThis.fetch = vi.fn(async () => { calls++; return jsonResponse({ detail: "nope" }, 401); }) as any;

    const client = new BharatBuildClient({
      apiBaseUrl: "http://x",
      authToken: "stale",
      onUnauthorized: async () => "also-stale",
    });

    await expect(client.get("/x")).rejects.toBeInstanceOf(APIError);
    expect(calls).toBe(2);
  });

  it("shares one refresh across concurrent 401s", async () => {
    let refreshes = 0;
    globalThis.fetch = vi.fn(async (_u: any, init: any) =>
      init.headers["Authorization"] === "Bearer stale"
        ? jsonResponse({ detail: "no" }, 401)
        : jsonResponse({ ok: true }),
    ) as any;

    const client = new BharatBuildClient({
      apiBaseUrl: "http://x",
      authToken: "stale",
      onUnauthorized: async () => { refreshes++; await new Promise((r) => setTimeout(r, 20)); return "fresh"; },
    });

    await Promise.all([client.get("/a"), client.get("/b"), client.get("/c")]);
    expect(refreshes).toBe(1);
  });

  it("gives an actionable message when the session cannot be recovered", async () => {
    globalThis.fetch = vi.fn(async () => jsonResponse({ detail: "Could not validate credentials" }, 401)) as any;

    const client = new BharatBuildClient({
      apiBaseUrl: "http://x",
      authToken: "dead",
      onUnauthorized: async () => null,
    });

    // The backend's internal wording is not something a user can act on.
    await expect(client.get("/x")).rejects.toThrow(/bharatbuild login/);
  });

  it("leaves non-401 errors alone", async () => {
    globalThis.fetch = vi.fn(async () => jsonResponse({ detail: "Server exploded" }, 500)) as any;
    const client = new BharatBuildClient({
      apiBaseUrl: "http://x",
      authToken: "t",
      onUnauthorized: async () => "fresh",
    });
    await expect(client.get("/x")).rejects.toThrow("Server exploded");
  });

  it("does not attempt refresh when no handler is attached", async () => {
    let calls = 0;
    globalThis.fetch = vi.fn(async () => { calls++; return jsonResponse({ detail: "no" }, 401); }) as any;
    const client = new BharatBuildClient({ apiBaseUrl: "http://x", authToken: "t" });
    await expect(client.get("/x")).rejects.toBeInstanceOf(APIError);
    expect(calls).toBe(1);
  });
});

describe("credential expiry", () => {
  it("derives expiry from the token, not a hardcoded guess", async () => {
    const { isTokenExpired, canRefreshSession } = await import("../../src/api/auth.js");
    const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");
    const jwt = (exp: number, type = "access") =>
      `${b64({ alg: "HS256" })}.${b64({ exp, type })}.sig`;
    const past = Math.floor(Date.now() / 1000) - 60;
    const future = Math.floor(Date.now() / 1000) + 86_400;

    // Login used to stamp expiresAt 24h out while the backend issued 30-minute
    // tokens, so an expired token read as valid and every call 401'd.
    const creds: any = { token: jwt(past), refreshToken: jwt(future, "refresh"), expiresAt: Date.now() + 86_400_000 };
    expect(isTokenExpired(creds)).toBe(true);
    expect(canRefreshSession(creds)).toBe(true);
  });

  it("reports an unrecoverable session when the refresh token is dead too", async () => {
    const { isTokenExpired, canRefreshSession } = await import("../../src/api/auth.js");
    const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");
    const past = Math.floor(Date.now() / 1000) - 60;
    const jwt = (type: string) => `${b64({ alg: "HS256" })}.${b64({ exp: past, type })}.sig`;
    const creds: any = { token: jwt("access"), refreshToken: jwt("refresh") };
    expect(isTokenExpired(creds)).toBe(true);
    expect(canRefreshSession(creds)).toBe(false);
  });
});
