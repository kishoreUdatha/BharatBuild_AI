/**
 * BharatBuild CLI — Model Router
 * Selects the correct provider based on model ID.
 * Supports "auto" model ID for dynamic selection like Kiro CLI.
 */
import type { ModelClient, ModelChunk } from "../runtime/agent-loop.js";
import { AnthropicProvider } from "./providers/anthropic.js";
import { OpenAIProvider } from "./providers/openai.js";
import { GeminiProvider } from "./providers/gemini.js";
import { OllamaProvider } from "./providers/ollama.js";
import { BedrockProvider } from "./providers/bedrock.js";
import { autoSelectModel, isAutoModel, type AutoSelectOptions, type EffortLevel } from "./auto-select.js";

export { autoSelectModel, isAutoModel, type AutoSelectOptions, type EffortLevel };

/**
 * Create a model client for a specific model ID.
 */
export function createModelClient(modelId: string, overrideApiKey?: string): ModelClient {
  if (modelId.startsWith("claude-"))                                              return new AnthropicProvider({ model: modelId, apiKey: overrideApiKey });
  if (modelId.startsWith("gpt-") || modelId.startsWith("o1") || modelId.startsWith("o3")) return new OpenAIProvider({ model: modelId, apiKey: overrideApiKey });
  if (modelId.startsWith("gemini-"))                                              return new GeminiProvider({ model: modelId, apiKey: overrideApiKey });
  if (modelId.startsWith("ollama/"))                                              return new OllamaProvider({ model: modelId });
  if (modelId.startsWith("bedrock/") || modelId.startsWith("anthropic.claude"))  return new BedrockProvider({ model: modelId });
  // Budget open-weight models — all served via OpenAI-compatible APIs
  if (modelId.startsWith("deepseek-"))    return new OpenAIProvider({ model: modelId, apiKey: overrideApiKey ?? process.env["DEEPSEEK_API_KEY"], baseUrl: "https://api.deepseek.com/v1" });
  if (modelId.startsWith("minimax-"))     return new OpenAIProvider({ model: modelId, apiKey: overrideApiKey ?? process.env["MINIMAX_API_KEY"],  baseUrl: "https://api.minimax.chat/v1" });
  if (modelId.startsWith("glm-"))         return new OpenAIProvider({ model: modelId, apiKey: overrideApiKey ?? process.env["ZHIPU_API_KEY"],    baseUrl: "https://open.bigmodel.cn/api/paas/v4" });
  if (modelId.startsWith("qwen"))         return new OpenAIProvider({ model: modelId, apiKey: overrideApiKey ?? process.env["QWEN_API_KEY"],     baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1" });
  // Default fallback: Anthropic
  return new AnthropicProvider({ model: modelId, apiKey: overrideApiKey });
}

/**
 * Auto-selecting model client — picks the best model per request.
 * Mirrors Kiro CLI's "Auto" model mode exactly:
 *   - Scores every available model by quality-fit ÷ credit-multiplier
 *   - Passes conversation depth to complexity detection
 *   - Emits the selected model + reason as a status event before streaming
 */
export class AutoModelClient implements ModelClient {
  private opts: AutoSelectOptions;
  private lastResult: ReturnType<typeof autoSelectModel> | null = null;

  constructor(opts: AutoSelectOptions = {}) {
    this.opts = opts;
  }

  async *complete(params: {
    model: string;
    system: string;
    messages: unknown[];
    tools: object[];
    maxTokens: number;
    signal?: AbortSignal;
  }): AsyncIterable<ModelChunk> {
    const messages = params.messages as Array<{ role: string; content: unknown }>;

    // Derive prompt + conversation depth from message history
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    const prompt = typeof lastUser?.content === "string"
      ? lastUser.content
      : Array.isArray(lastUser?.content)
        ? (lastUser.content as Array<{ text?: string }>).map((c) => c.text ?? "").join(" ")
        : "";
    const conversationTurns = messages.filter((m) => m.role === "user").length;

    // Run auto-selection with conversation depth
    const result = autoSelectModel(prompt, this.opts, conversationTurns);
    this.lastResult = result;

    // Yield a status chunk so TUI shows which model was picked + why
    // This matches Kiro's "Using Claude Sonnet 5 (auto)" status line
    yield {
      type: "text_delta",
      text: `\x1b[2m  ✦ Auto → ${result.modelName}  (${result.complexity}, ${result.multiplier}x)\x1b[0m\n`,
    };

    // Delegate to the concrete provider
    const client = createModelClient(result.modelId);
    yield* client.complete({ ...params, model: result.modelId } as Parameters<typeof client.complete>[0]);
  }

  getLastResult() { return this.lastResult; }
}

/**
 * Create model client — supports "auto" keyword like Kiro CLI.
 *
 * Usage:
 *   createModelClientAuto("auto")             → auto-selects per request
 *   createModelClientAuto("auto", key, {effort:"max"}) → max effort
 *   createModelClientAuto("claude-3-5-haiku") → direct selection
 */
export function createModelClientAuto(
  modelId: string,
  overrideApiKey?: string,
  opts?: AutoSelectOptions
): ModelClient {
  if (isAutoModel(modelId)) {
    return new AutoModelClient(opts ?? {});
  }
  return createModelClient(modelId, overrideApiKey);
}
