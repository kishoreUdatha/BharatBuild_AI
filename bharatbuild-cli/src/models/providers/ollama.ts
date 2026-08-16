/** BharatBuild CLI — Ollama Provider (local models) */
import type { ModelChunk } from "../../runtime/agent-loop.js";
import { BaseModelProvider, type ModelProviderConfig } from "../model-provider.js";

export class OllamaProvider extends BaseModelProvider {
  private baseUrl: string;
  constructor(config: ModelProviderConfig) {
    super(config);
    this.baseUrl = config.baseUrl ?? "http://localhost:11434";
  }
  async *complete(params: { model: string; system: string; messages: unknown[]; tools: object[]; maxTokens: number; signal?: AbortSignal }): AsyncIterable<ModelChunk> {
    const modelName = params.model.replace("ollama/", "");
    const messages = [{ role: "system", content: params.system }, ...params.messages as object[]];
    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: modelName, messages, stream: true, options: { num_predict: params.maxTokens } }),
      signal: params.signal,
    });
    if (!res.ok) throw new Error(`Ollama HTTP ${res.status} — is Ollama running at ${this.baseUrl}?`);
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const ev = JSON.parse(line) as Record<string, unknown>;
          const msg = ev["message"] as Record<string, unknown> | undefined;
          if (msg?.["content"]) yield { type: "text_delta", text: String(msg["content"]) };
          if (ev["done"]) yield { type: "stop", stopReason: "end_turn" };
        } catch { /* skip */ }
      }
    }
  }
}
