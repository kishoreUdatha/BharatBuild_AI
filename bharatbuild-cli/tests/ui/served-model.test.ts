/**
 * backend/.env deliberately routes sonnet and opus to haiku to keep local
 * development off paid tiers. The saving is intentional; the silence was not —
 * the status bar showed "sonnet" while haiku wrote the reply, so a weaker
 * answer looked like a Sonnet answer.
 */
import { describe, it, expect } from "vitest";
import { shortModelName, modelLabel, isSubstituted } from "../../src/ui/ink/served-model.js";

describe("shortening a model id", () => {
  it("drops the vendor prefix and writes the version the human way", () => {
    expect(shortModelName("claude-haiku-4-5")).toBe("haiku-4.5");
    expect(shortModelName("claude-sonnet-5")).toBe("sonnet-5");
    expect(shortModelName("claude-opus-4-6")).toBe("opus-4.6");
  });

  it("handles bedrock ids", () => {
    // These carry a region prefix and a version suffix.
    expect(shortModelName("us.anthropic.claude-haiku-4-5-20250714-v1:0")).toBe("haiku-4.5");
  });

  it("returns empty for empty input rather than throwing", () => {
    expect(shortModelName("")).toBe("");
  });
});

describe("what the status bar shows", () => {
  it("flags the substitution that prompted this", () => {
    // The exact case: ask for sonnet, get haiku.
    expect(modelLabel("sonnet", "claude-haiku-4-5")).toBe("sonnet→haiku-4.5");
    expect(modelLabel("opus", "claude-haiku-4-5")).toBe("opus→haiku-4.5");
  });

  it("names the winner when the user expressed no preference", () => {
    // "auto" is not a broken promise, so this is information not a warning.
    expect(modelLabel("auto", "claude-sonnet-5")).toBe("auto→sonnet-5");
  });

  it("stays quiet when the request was honoured", () => {
    expect(modelLabel("haiku", "claude-haiku-4-5")).toBe("haiku");
    expect(modelLabel("sonnet", "claude-sonnet-5")).toBe("sonnet");
  });

  it("does not treat a version suffix as a substitution", () => {
    // "sonnet" served by "sonnet-5" is the same model named loosely.
    expect(modelLabel("sonnet", "claude-sonnet-5")).not.toContain("→");
  });

  it("shows the plain request when the server said nothing", () => {
    // Direct API key, no proxy — there is no served model to report.
    expect(modelLabel("sonnet", null)).toBe("sonnet");
    expect(modelLabel("sonnet", undefined)).toBe("sonnet");
    expect(modelLabel("sonnet", "")).toBe("sonnet");
  });
});

describe("detecting a substitution", () => {
  it("is true only when the family actually changed", () => {
    expect(isSubstituted("sonnet", "claude-haiku-4-5")).toBe(true);
    expect(isSubstituted("haiku", "claude-haiku-4-5")).toBe(false);
    expect(isSubstituted("sonnet", "claude-sonnet-5")).toBe(false);
  });

  it("is false for auto, which promised nothing", () => {
    expect(isSubstituted("auto", "claude-haiku-4-5")).toBe(false);
  });

  it("is false when nothing was reported", () => {
    expect(isSubstituted("sonnet", null)).toBe(false);
  });
});
