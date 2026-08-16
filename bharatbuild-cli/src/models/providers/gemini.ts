/** BharatBuild CLI — Google Gemini Provider */
import type { ModelChunk } from "../../runtime/agent-loop.js";
import { BaseModelProvider, type ModelProviderConfig } from "../model-provider.js";

export class GeminiProvider extends BaseModelProvider {
  constructor(config: ModelProviderConfig) { super(config); }
  async *complete(params: { model: string; system: string; messages: unknown[]; tools: object[]; maxTokens: number; signal?: AbortSignal }): AsyncIterable<ModelChunk> {
    const apiKey = this.config.apiKey ?? process.env["GEMINI_API_KEY"] ?? process.env["GOOGLE_API_KEY"];
    if (!apiKey) throw new Error("GEMINI_API_KEY not set");
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${params.model}:streamGenerateContent?key=${apiKey}&alt=sse`;
    const contents = (params.messages as Array<{ role: string; content: string }>).map((m) => ({
      role: m.role === "assistant" ? "model" : "user",
      parts: [{ text: m.content }],
    }));
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ systemInstruction: { parts: [{ text: params.system }] }, contents, generationConfig: { maxOutputTokens: params.maxTokens } }),
      signal: params.signal,
    });
    if (!res.ok) throw new Error(`Gemini HTTP ${res.status}`);
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
        if (!dataLine) continue;
        try {
          const ev = JSON.parse(dataLine) as Record<string, unknown>;
          const candidate = ((ev["candidates"] as unknown[])?.[0]) as Record<string, unknown> | undefined;
          const parts2 = (candidate?.["content"] as Record<string, unknown>)?.["parts"] as Array<{ text?: string }> | undefined;
          for (const p of parts2 ?? []) { if (p.text) yield { type: "text_delta", text: p.text }; }
        } catch { /* skip */ }
      }
    }
    yield { type: "stop", stopReason: "end_turn" };
  }
}
