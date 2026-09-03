/**
 * Native extended thinking.
 *
 * The CLI had a `thinking` *tool*: the model called it, wrote its reasoning
 * into the argument, and got an acknowledgement back. That costs a full
 * round-trip — a request, a tool result, and another request — to record
 * reasoning the model had already done. The API does it inline for nothing
 * extra in latency, and the reasoning is available to the next turn rather
 * than being a tool result in the transcript.
 *
 * Two constraints from the API shape this:
 *
 *   - `budget_tokens` must be less than `max_tokens`, and is a floor on how
 *     much the model may spend thinking, not a cap on the reply.
 *   - When thinking is on and tools are in play, the thinking blocks have to
 *     be sent back with the assistant turn they belong to. Dropping them is a
 *     hard API error, not a degradation — see wire-format.
 */

/**
 * The two request shapes, because there are two.
 *
 * Claude 4-era models take an explicit token budget:
 *     thinking: { type: "enabled", budget_tokens: 2048 }
 *
 * Claude 5 rejects that outright — "thinking.type.enabled is not supported for
 * this model. Use thinking.type.adaptive and output_config.effort" — and
 * decides for itself how much to think, guided by an effort level. Sending the
 * wrong shape is a 400, not a fallback, so the model has to be classified
 * before the request is built.
 */
const BUDGETED = [/^claude-opus-4/, /^claude-sonnet-4/, /^claude-3-7-sonnet/, /^claude-haiku-4-5/];
const ADAPTIVE = [/^claude-opus-5/, /^claude-sonnet-5/, /^claude-haiku-5/];

export type ThinkingShape = "budgeted" | "adaptive" | "none";

export function thinkingShape(modelId: string): ThinkingShape {
  if (ADAPTIVE.some((re) => re.test(modelId))) return "adaptive";
  if (BUDGETED.some((re) => re.test(modelId))) return "budgeted";
  return "none";
}

export function supportsThinking(modelId: string): boolean {
  return thinkingShape(modelId) !== "none";
}

export type ThinkingLevel = "off" | "low" | "medium" | "high";

/**
 * Budget per level.
 *
 * The API floor is 1024. These are deliberately modest: thinking tokens are
 * billed as output, so a generous default would quietly multiply the cost of
 * every turn — and the tool this replaces was only ever used occasionally.
 */
const BUDGETS: Record<Exclude<ThinkingLevel, "off">, number> = {
  low: 2_048,
  medium: 6_144,
  high: 16_384,
};

export type ThinkingConfig =
  | { type: "enabled"; budget_tokens: number }
  | { type: "adaptive" };

/** Effort level that accompanies adaptive thinking, in output_config. */
const EFFORT: Record<Exclude<ThinkingLevel, "off">, string> = {
  low: "low",
  medium: "medium",
  high: "high",
};

/** The output_config for an adaptive model, or null when it does not apply. */
export function effortFor(modelId: string, level: ThinkingLevel): { effort: string } | null {
  if (level === "off") return null;
  if (thinkingShape(modelId) !== "adaptive") return null;
  return { effort: EFFORT[level] };
}

/**
 * The `thinking` parameter for a request, or null to omit it.
 *
 * Returns null rather than a disabled object: the API rejects the parameter
 * outright on models that do not support it, so it has to be absent, not off.
 */
export function thinkingFor(
  modelId: string,
  level: ThinkingLevel,
  maxTokens: number,
): ThinkingConfig | null {
  if (level === "off") return null;

  const shape = thinkingShape(modelId);
  if (shape === "none") return null;

  // Claude 5 sizes its own thinking; the level travels in output_config.effort.
  if (shape === "adaptive") return { type: "adaptive" };

  // budget_tokens must leave room for the reply itself. Two thirds keeps a
  // usable answer even when the model spends its whole allowance thinking.
  const ceiling = Math.floor(maxTokens * (2 / 3));
  const budget = Math.min(BUDGETS[level], ceiling);

  // Below the API's own floor there is no point asking.
  if (budget < 1024) return null;
  return { type: "enabled", budget_tokens: budget };
}

/**
 * The level to use, from the environment or a default.
 *
 * Off by default. Thinking is billed as output tokens, and turning it on for
 * every "what does this file do" would be a silent price rise; the levels are
 * there for work that earns them.
 */
export function configuredLevel(env: NodeJS.ProcessEnv = process.env): ThinkingLevel {
  const raw = (env["BHARATBUILD_THINKING"] ?? "").toLowerCase().trim();
  if (raw === "low" || raw === "medium" || raw === "high" || raw === "off") return raw;
  return "off";
}
