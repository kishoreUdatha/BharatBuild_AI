/**
 * Native extended thinking.
 *
 * The CLI had a `thinking` *tool*: the model called it, wrote its reasoning
 * into the argument, and got an acknowledgement back — a whole extra
 * round-trip to record reasoning it had already done. The API does it inline,
 * and the reasoning is then available to the next turn instead of sitting in
 * the transcript as a tool result.
 *
 * Two things make this easy to get wrong, and both were hit while building it:
 * there are two request shapes depending on the model, and with tools in play
 * the thinking blocks must be sent back or the next request is a 400.
 */
import { describe, it, expect } from "vitest";
import {
  thinkingFor, effortFor, thinkingShape, supportsThinking, configuredLevel,
} from "../../src/models/thinking-config.js";
import { toWireMessages } from "../../src/models/wire-format.js";

describe("which shape a model takes", () => {
  it("gives Claude 4 an explicit token budget", () => {
    expect(thinkingShape("claude-sonnet-4-5-20250929")).toBe("budgeted");
    expect(thinkingFor("claude-sonnet-4-5-20250929", "low", 8000))
      .toEqual({ type: "enabled", budget_tokens: 2048 });
  });

  it("gives Claude 5 adaptive thinking instead", () => {
    // Sending a budget to Claude 5 is a hard 400: "thinking.type.enabled is
    // not supported for this model. Use thinking.type.adaptive and
    // output_config.effort".
    expect(thinkingShape("claude-sonnet-5")).toBe("adaptive");
    expect(thinkingFor("claude-sonnet-5", "low", 8000)).toEqual({ type: "adaptive" });
  });

  it("pairs adaptive with an effort level, and budgeted with none", () => {
    expect(effortFor("claude-sonnet-5", "high")).toEqual({ effort: "high" });
    expect(effortFor("claude-sonnet-4-5-20250929", "high")).toBeNull();
  });

  it("omits the parameter entirely for a model that has no thinking", () => {
    // Absent, not disabled: the API rejects the key outright on those models.
    expect(supportsThinking("gpt-4o")).toBe(false);
    expect(thinkingFor("gpt-4o", "high", 8000)).toBeNull();
    expect(effortFor("gpt-4o", "high")).toBeNull();
  });

  it("omits it when the level is off, whatever the model", () => {
    expect(thinkingFor("claude-sonnet-5", "off", 8000)).toBeNull();
    expect(thinkingFor("claude-sonnet-4-5-20250929", "off", 8000)).toBeNull();
  });
});

describe("the budget", () => {
  it("leaves room for the reply", () => {
    // budget_tokens is a floor on thinking, not a cap on the answer, so a
    // budget near max_tokens can starve the reply.
    const cfg = thinkingFor("claude-sonnet-4-5-20250929", "high", 3000);
    expect(cfg).not.toBeNull();
    expect((cfg as { budget_tokens: number }).budget_tokens).toBeLessThan(3000);
  });

  it("gives up rather than asking below the API floor", () => {
    // The minimum the API accepts is 1024; anything less is not worth a request.
    expect(thinkingFor("claude-sonnet-4-5-20250929", "low", 1200)).toBeNull();
  });

  it("scales with the level", () => {
    const b = (l: "low" | "medium" | "high") =>
      (thinkingFor("claude-sonnet-4-5-20250929", l, 60_000) as { budget_tokens: number }).budget_tokens;
    expect(b("low")).toBeLessThan(b("medium"));
    expect(b("medium")).toBeLessThan(b("high"));
  });
});

describe("switching it on", () => {
  it("is off unless asked for", () => {
    // Thinking is billed as output tokens; on by default would be a silent
    // price rise on every "what does this file do".
    expect(configuredLevel({})).toBe("off");
  });

  it("reads the level from the environment", () => {
    expect(configuredLevel({ BHARATBUILD_THINKING: "high" })).toBe("high");
    expect(configuredLevel({ BHARATBUILD_THINKING: "MEDIUM" })).toBe("medium");
  });

  it("ignores a value it does not recognise", () => {
    expect(configuredLevel({ BHARATBUILD_THINKING: "yes please" })).toBe("off");
  });
});

describe("sending the blocks back", () => {
  it("carries a thinking block through the wire format unchanged", () => {
    // With thinking and tools together the API requires the assistant turn's
    // thinking blocks back exactly as issued. A rewritten or dropped block is
    // rejected, so this cannot be lossy.
    const wire = toWireMessages([
      {
        role: "assistant",
        content: [
          { type: "thinking", thinking: "weighing two options", signature: "sig-abc" },
          { type: "text", text: "Here is the answer." },
        ],
      },
    ]) as Array<{ content: Array<Record<string, unknown>> }>;

    const blocks = wire[0]!.content;
    expect(blocks[0]).toEqual({
      type: "thinking",
      thinking: "weighing two options",
      signature: "sig-abc",
    });
    expect(blocks[1]).toEqual({ type: "text", text: "Here is the answer." });
  });

  it("keeps thinking ahead of the text, as the API produced it", () => {
    const wire = toWireMessages([
      {
        role: "assistant",
        content: [
          { type: "thinking", thinking: "t", signature: "s" },
          { type: "text", text: "answer" },
        ],
      },
    ]) as Array<{ content: Array<Record<string, unknown>> }>;
    expect(wire[0]!.content[0]!["type"]).toBe("thinking");
  });

  it("does not invent a thinking block on an ordinary turn", () => {
    const wire = toWireMessages([
      { role: "assistant", content: [{ type: "text", text: "plain" }] },
    ]) as Array<{ content: Array<Record<string, unknown>> }>;
    expect(wire[0]!.content).toHaveLength(1);
    expect(wire[0]!.content[0]!["type"]).toBe("text");
  });
});
