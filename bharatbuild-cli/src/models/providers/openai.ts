/** BharatBuild CLI — OpenAI Provider */
import type { ModelChunk } from "../../runtime/agent-loop.js";
import { BaseModelProvider, type ModelProviderConfig } from "../model-provider.js";

export class OpenAIProvider extends BaseModelProvider {
  private baseUrl: string;
  constructor(config: ModelProviderConfig) {
    super(config);
    this.baseUrl = config.baseUrl ?? "https://api.openai.com/v1";
  }
  async *complete(params: { model: string; system: string; messages: unknown[]; tools: object[]; maxTokens: number; signal?: AbortSignal }): AsyncIterable<ModelChunk> {
    const apiKey = this.config.apiKey ?? process.env["OPENAI_API_KEY"];
    if (!apiKey) throw new Error("OPENAI_API_KEY not set");
    const messages = [{ role: "system", content: params.system }, ...params.messages as object[]];
    const res = await fetch(`${this.baseUrl}/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
      body: JSON.stringify({ model: params.model, messages, tools: params.tools.length ? params.tools : undefined, max_tokens: params.maxTokens, stream: true }),
      signal: params.signal,
    });
    if (!res.ok) { const e = await res.json() as { error?: { message?: string } }; throw new Error(e.error?.message ?? `HTTP ${res.status}`); }
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() ?? "";
      for (const part of parts) {
        const dataLine = part.split("\n").find((l) => l.startsWith("data: "))?.slice(6);
        if (!dataLine || dataLine === "[DONE]") { if (dataLine === "[DONE]") yield { type: "stop", stopReason: "end_turn" }; continue; }
        try {
          const ev = JSON.parse(dataLine) as Record<string, unknown>;
          const choice = (ev["choices"] as unknown[])?.[0] as Record<string, unknown> | undefined;
          const delta = choice?.["delta"] as Record<string, unknown> | undefined;
          if (delta?.["content"]) yield { type: "text_delta", text: String(delta["content"]) };
          if (choice?.["finish_reason"]) yield { type: "stop", stopReason: "end_turn" };
        } catch { /* skip */ }
      }
    }
  }
}
