/**
 * Which way the model calls go out.
 *
 * There was no signal. `Using direct API key` printed only when you were *not*
 * logged in, so being logged in and silently routed through the BharatBuild
 * server printed nothing at all — the first indication of which path you were
 * on was a turn failing. When the server's own model account ran out of
 * credit, the provider's "your credit balance is too low" read as though the
 * user's key was dead, and a working key was abandoned on that basis.
 */
import { describe, it, expect } from "vitest";
import { modelRoute, describeRoute } from "../../src/api/model-route.js";

/** An environment with nothing set, so a stray real key cannot leak in. */
const CLEAN: NodeJS.ProcessEnv = {};

describe("working out the route", () => {
  it("reports the server when proxied", () => {
    expect(modelRoute(true, CLEAN).via).toBe("server");
  });

  it("names the provider a direct key belongs to", () => {
    const r = modelRoute(false, { ANTHROPIC_API_KEY: "sk-ant-x" });
    expect(r.via).toBe("direct");
    expect(r.target).toBe("Anthropic");
  });

  it("names the variable responsible", () => {
    // A key left in a shell profile is invisible otherwise, and explains a
    // session that bypasses the server without being asked to.
    expect(modelRoute(false, { OPENAI_API_KEY: "sk-x" }).source).toBe("OPENAI_API_KEY");
  });

  it("prefers Anthropic when several keys are set", () => {
    // Matches createProxyClientIfLoggedIn, which checks Anthropic first.
    expect(modelRoute(false, { OPENAI_API_KEY: "a", ANTHROPIC_API_KEY: "b" }).target).toBe("Anthropic");
  });

  it("does not claim a provider when no key is set", () => {
    // Not proxied and no key means a local provider, or a config that will
    // fail on the first call — either way, not the server.
    const r = modelRoute(false, CLEAN);
    expect(r.via).toBe("direct");
    expect(r.source).toBeUndefined();
  });

  it("uses the configured host for the server", () => {
    expect(modelRoute(true, CLEAN, "https://api.bharatbuild.in").target)
      .toBe("https://api.bharatbuild.in");
  });
});

describe("the line it prints", () => {
  it("says direct, and which variable chose it", () => {
    const line = describeRoute(modelRoute(false, { ANTHROPIC_API_KEY: "x" }), "auto");
    expect(line).toContain("direct to Anthropic");
    expect(line).toContain("ANTHROPIC_API_KEY");
    expect(line).toContain("auto");
  });

  it("says the server, and who pays", () => {
    const line = describeRoute(modelRoute(true, CLEAN, "api.bharatbuild.in"), "sonnet");
    expect(line).toContain("via api.bharatbuild.in");
    expect(line).toContain("sonnet");
    expect(line).toMatch(/credits/i);
  });

  it("never prints the key itself", () => {
    // The variable name is useful; its value is a credential.
    const secret = "sk-ant-super-secret-value";
    const line = describeRoute(modelRoute(false, { ANTHROPIC_API_KEY: secret }), "auto");
    expect(line).not.toContain(secret);
  });

  it("distinguishes the two routes", () => {
    const direct = describeRoute(modelRoute(false, { ANTHROPIC_API_KEY: "x" }), "auto");
    const server = describeRoute(modelRoute(true, CLEAN), "auto");
    expect(direct).not.toBe(server);
  });
});
