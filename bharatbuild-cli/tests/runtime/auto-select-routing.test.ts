/**
 * Auto-routing has to see a stored key.
 *
 * `detectAvailableProviders` read environment variables directly. Once a key
 * could also live in a file, that check found nothing, the candidate list came
 * back empty, and every task hit the hard fallback — the cheapest model, for
 * everything. The complexity was still computed and reported, then discarded,
 * so the banner honestly said "(expert, 0.4x)": graded expert, run on Haiku.
 *
 * The visible damage was not cost. Haiku ignores the scope instructions the
 * system prompt spends a paragraph on, so "write the program the string is
 * palindrum or not" produced nine files and roughly 3,000 lines of
 * documentation, in the user's home directory.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { autoSelectModel, detectAvailableProviders, detectComplexity } from "../../src/models/auto-select.js";
import { availableProviders } from "../../src/auth/provider-key.js";

let home: string;
const originalHome = process.env["BHARATBUILD_HOME"];

/** A home directory holding a stored key and nothing else. */
function withStoredKey(provider: string, key = "sk-test-value"): void {
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, "provider-keys.json"), JSON.stringify({ [provider]: key }));
}

beforeEach(() => {
  home = fs.mkdtempSync(path.join(os.tmpdir(), "bb-route-"));
  process.env["BHARATBUILD_HOME"] = home;
  // The suite runs with no provider keys; make that explicit so a developer
  // machine with one exported cannot make these pass for the wrong reason.
  delete process.env["ANTHROPIC_API_KEY"];
  delete process.env["OPENAI_API_KEY"];
});
afterEach(() => {
  if (originalHome === undefined) delete process.env["BHARATBUILD_HOME"];
  else process.env["BHARATBUILD_HOME"] = originalHome;
  try { fs.rmSync(home, { recursive: true, force: true }); } catch { /* windows lock */ }
});

describe("finding the keys", () => {
  it("counts a stored key, not just an exported one", () => {
    withStoredKey("anthropic");
    expect(availableProviders()).toContain("anthropic");
  });

  it("reports it to the model router", () => {
    withStoredKey("anthropic");
    expect(detectAvailableProviders()).toContain("anthropic");
  });

  it("still counts an exported key", () => {
    process.env["ANTHROPIC_API_KEY"] = "sk-ant-x";
    expect(detectAvailableProviders()).toContain("anthropic");
  });

  it("translates the key store's name to the registry's", () => {
    // The registry calls Gemini's provider "google"; the key store says
    // "gemini". A mismatch here silently drops the provider.
    withStoredKey("gemini");
    expect(detectAvailableProviders()).toContain("google");
  });
});

describe("picking a model for the work", () => {
  beforeEach(() => withStoredKey("anthropic"));

  it("sends a trivial prompt to the cheap model", () => {
    const r = autoSelectModel("hi", {}, 1);
    expect(r.complexity).toBe("simple");
    expect(r.multiplier).toBeLessThanOrEqual(0.5);
  });

  it("does not send a build request to the cheap model", () => {
    // The exact prompt behind the nine-file answer.
    const r = autoSelectModel("write the program the string is palindrum or not", {}, 1);
    expect(r.complexity).toBe("complex");
    expect(r.multiplier).toBeGreaterThan(0.5);
  });

  it("sends an expert task to the strongest model", () => {
    const r = autoSelectModel("refactor the orchestrator and audit every endpoint for auth gaps", {}, 1);
    expect(r.complexity).toBe("expert");
    expect(r.multiplier).toBeGreaterThanOrEqual(2);
  });

  it("never reports the no-keys fallback when a key is stored", () => {
    // The tell. This string appeared on every turn of a real session.
    for (const p of ["hi", "build a login page", "audit the architecture"]) {
      expect(autoSelectModel(p, {}, 1).reason, p).not.toMatch(/no provider API keys/i);
    }
  });

  it("scales the model with the task, not against it", () => {
    const simple = autoSelectModel("hi", {}, 1);
    const expert = autoSelectModel("refactor and audit the whole architecture", {}, 1);
    expect(expert.multiplier).toBeGreaterThan(simple.multiplier);
  });
});

describe("with no key anywhere", () => {
  it("still falls back rather than failing", () => {
    // The fallback is correct behaviour when it is actually true.
    const r = autoSelectModel("hi", {}, 1);
    expect(r.modelId).toBeTruthy();
    expect(r.reason).toMatch(/no provider API keys/i);
  });
});

describe("complexity grading itself", () => {
  it("treats a short greeting as simple", () => {
    expect(detectComplexity("hi", 0)).toBe("simple");
  });

  it("treats writing a program as complex", () => {
    expect(detectComplexity("write the program the string is palindrum or not", 0)).toBe("complex");
  });

  it("treats an audit as expert", () => {
    expect(detectComplexity("audit every endpoint for auth gaps", 0)).toBe("expert");
  });
});
