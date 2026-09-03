import { describe, it, expect } from "vitest";
import { decodeJwt, jwtExpiresAt, jwtIsExpired } from "../../src/auth/jwt.js";

function makeJwt(payload: Record<string, unknown>): string {
  const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64(payload)}.signature`;
}

const inSeconds = (n: number) => Math.floor(Date.now() / 1000) + n;

describe("decodeJwt", () => {
  it("reads the payload without verifying the signature", () => {
    const t = makeJwt({ sub: "user-1", email: "a@b.c", exp: 123 });
    expect(decodeJwt(t)).toMatchObject({ sub: "user-1", email: "a@b.c", exp: 123 });
  });

  it.each([
    ["undefined", undefined],
    ["empty", ""],
    ["not a jwt", "hello"],
    ["wrong segment count", "a.b"],
    ["unparseable payload", "aaa.!!!notbase64json!!!.ccc"],
  ])("returns null for %s", (_label, input) => {
    expect(decodeJwt(input as string | undefined)).toBeNull();
  });
});

describe("jwtExpiresAt", () => {
  it("converts exp seconds to epoch milliseconds", () => {
    expect(jwtExpiresAt(makeJwt({ exp: 1_700_000_000 }))).toBe(1_700_000_000_000);
  });

  it("returns null when there is no exp claim", () => {
    expect(jwtExpiresAt(makeJwt({ sub: "x" }))).toBeNull();
  });
});

describe("jwtIsExpired", () => {
  it("is true for a token that has passed its exp", () => {
    expect(jwtIsExpired(makeJwt({ exp: inSeconds(-10) }))).toBe(true);
  });

  it("is false for a token with plenty of life left", () => {
    expect(jwtIsExpired(makeJwt({ exp: inSeconds(3600) }))).toBe(false);
  });

  it("treats a token inside the skew window as expired", () => {
    // 30s left, 60s skew — refresh before the server rejects it mid-request.
    expect(jwtIsExpired(makeJwt({ exp: inSeconds(30) }), 60_000)).toBe(true);
  });

  it("honours a zero skew", () => {
    expect(jwtIsExpired(makeJwt({ exp: inSeconds(30) }), 0)).toBe(false);
  });

  it("treats an unreadable token as not expired and lets the server decide", () => {
    expect(jwtIsExpired("garbage")).toBe(false);
    expect(jwtIsExpired(undefined)).toBe(false);
  });
});
