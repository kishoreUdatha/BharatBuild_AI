import { describe, it, expect } from "vitest";
import { fuzzyRank, commonPrefix } from "../../src/ui/ink/fuzzy.js";

const CMDS = [
  { name: "checkpoint", description: "Create and manage file restore points" },
  { name: "chat", description: "Switch between previous sessions" },
  { name: "clear", description: "Clear the conversation display" },
  { name: "compact", description: "Toggle compact message display" },
  { name: "context", description: "Inspect and edit the context window" },
  { name: "model", description: "Show or set the active model" },
];

describe("fuzzyRank", () => {
  it("returns everything for an empty query", () => {
    expect(fuzzyRank(CMDS, "")).toHaveLength(CMDS.length);
  });

  it("matches a scattered subsequence", () => {
    // Plain includes() found nothing for this — the reason it was added.
    expect(fuzzyRank(CMDS, "ckpt")[0]?.name).toBe("checkpoint");
  });

  it("ranks an exact prefix above a subsequence", () => {
    const names = fuzzyRank(CMDS, "cha").map((c) => c.name);
    expect(names[0]).toBe("chat");
  });

  it("ranks a name hit above a description-only hit", () => {
    const names = fuzzyRank(CMDS, "model").map((c) => c.name);
    expect(names[0]).toBe("model");
  });

  it("still finds commands by description", () => {
    expect(fuzzyRank(CMDS, "restore points").map((c) => c.name)).toContain("checkpoint");
  });

  it("returns nothing when there is no match", () => {
    expect(fuzzyRank(CMDS, "zzzzq")).toHaveLength(0);
  });

  it("is case insensitive", () => {
    expect(fuzzyRank(CMDS, "CHAT")[0]?.name).toBe("chat");
  });

  it("prefers the tighter span between two subsequence matches", () => {
    const items = [
      { name: "abcdefghixyz", description: "" },
      { name: "axyz", description: "" },
    ];
    expect(fuzzyRank(items, "axyz")[0]?.name).toBe("axyz");
  });
});

describe("commonPrefix", () => {
  it("returns the shared prefix", () => {
    expect(commonPrefix(["checkpoint", "chat"])).toBe("ch");
  });

  it("returns the whole name for a single candidate", () => {
    expect(commonPrefix(["checkpoint"])).toBe("checkpoint");
  });

  it("returns empty when nothing is shared", () => {
    expect(commonPrefix(["model", "chat"])).toBe("");
  });

  it("handles an empty list", () => {
    expect(commonPrefix([])).toBe("");
  });
});
