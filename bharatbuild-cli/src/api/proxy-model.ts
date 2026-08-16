/**
 * BharatBuild CLI — Server-Side Model Proxy
 *
 * This is the exact equivalent of how Kiro CLI works:
 *
 *   Kiro:        CLI → kiro.dev backend → AWS Bedrock → model → response
 *   BharatBuild: CLI → bharatbuild backend → model provider → response
 *
 * When a user is logged in (has auth token), ALL model calls go through
 * the BharatBuild backend. The backend:
 *   1. Validates the auth token
 *   2. Checks credit balance (pre-flight)
 *   3. Forwards the request to the model provider using server API keys
 *   4. Streams the response back to the CLI
 *   5. Deducts credits from the user's balance after completion
 *   6. Returns token usage + credit deduction in response metadata
 *
 * This means:
 *   - Users don't need their own API keys (like Kiro)
 *   - Server controls which models each tier can access (like Kiro)
 *   - Credit deduction is authoritative and server-side (like Kiro)
 *   - If not logged in, falls back to direct provider calls with user's own keys
 */

import type { ModelClient, ModelChunk } from "../runtime/agent-loop.js";
import { loadCredentials } from "./auth.js";
import { loadConfig } from "../config/config.js";

// ── Wire format for the proxy SSE stream ─────────────────────────────────────
//
// Backend streams newline-delimited JSON events matching the CLI's ModelChunk
// interface, plus a final "usage" event with credit deduction info.

interface ProxyEvent {
  type:            string;
  text?:           string;
  tool_use_id?:    string;
  tool_name?:      string;
  tool_input?:     Record<string, unknown>;
  input_tokens?:   number;
  output_tokens?:  number;
  stop_reason?:    string;
  // Credit metadata — only in final "complete" event
  credits_deducted?:  number;
  credits_remaining?: number;
  model_used?:        string;
  multiplier?:        number;
}

// ── ProxyModelClient ──────────────────────────────────────────────────────────

export class ProxyModelClient implements ModelClient {
  private baseUrl: string;
  private authToken: string;
  /** Credits deducted by the server for the last turn */
  lastCreditsDeducted  = 0;
  lastCreditsRemaining = -1;
  lastModelUsed        = "";

  constructor(baseUrl: string, authToken: string) {
    this.baseUrl   = baseUrl.replace(/\/$/, "");
    this.authToken = authToken;
  }

  async *complete(params: {
    model:     string;
    system:    string;
    messages:  unknown[];
    tools:     object[];
    maxTokens: number;
    signal?:   AbortSignal;
  }): AsyncIterable<ModelChunk> {
    // Router mounts agentic.router with prefix "/agentic" — "/agent" 404s.
    const url = `${this.baseUrl}/api/v1/agentic/chat/stream`;

    let res: Response;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type":  "application/json",
          "Accept":        "text/event-stream",
          "Authorization": `Bearer ${this.authToken}`,
        },
        body: JSON.stringify({
          model:      params.model,
          system:     params.system,
          messages:   params.messages,
          tools:      params.tools,
          max_tokens: params.maxTokens,
        }),
        signal: params.signal,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      throw new Error(`BharatBuild proxy: connection failed — ${msg}`);
    }

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const e = await res.json() as { detail?: string; message?: string; error?: string };
        detail = e.detail ?? e.message ?? e.error ?? detail;
      } catch { /* non-JSON body */ }

      if (res.status === 402) {
        throw new Error(`Insufficient credits. Top up at app.bharatbuild.in`);
      }
      if (res.status === 403) {
        throw new Error(`Model ${params.model} not available on your plan. Upgrade at app.bharatbuild.in`);
      }
      if (res.status === 401) {
        throw new Error(`Session expired. Run: bharatbuild login`);
      }
      throw new Error(`BharatBuild proxy error (${res.status}): ${detail}`);
    }

    if (!res.body) throw new Error("No response body from proxy");

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buf     = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";

        for (const part of parts) {
          const dataLine = part.split("\n")
            .find((l) => l.startsWith("data: "))
            ?.slice(6);
          if (!dataLine || dataLine === "[DONE]") continue;

          let ev: ProxyEvent;
          try { ev = JSON.parse(dataLine) as ProxyEvent; }
          catch { continue; }

          switch (ev.type) {
            case "text_delta":
              if (ev.text) yield { type: "text_delta", text: ev.text };
              break;

            case "tool_use":
              if (ev.tool_use_id && ev.tool_name) {
                yield {
                  type:      "tool_use",
                  toolUseId: ev.tool_use_id,
                  toolName:  ev.tool_name,
                  toolInput: ev.tool_input ?? {},
                };
              }
              break;

            case "usage":
              yield {
                type:         "usage",
                inputTokens:  ev.input_tokens  ?? 0,
                outputTokens: ev.output_tokens ?? 0,
              };
              break;

            case "stop":
              yield {
                type:       "stop",
                stopReason: (ev.stop_reason ?? "end_turn") as ModelChunk["stopReason"],
              };
              break;

            case "complete":
              // Server-authoritative credit deduction — store for status bar
              this.lastCreditsDeducted  = ev.credits_deducted  ?? 0;
              this.lastCreditsRemaining = ev.credits_remaining ?? -1;
              this.lastModelUsed        = ev.model_used        ?? params.model;
              // Also emit final usage if present
              if (ev.input_tokens || ev.output_tokens) {
                yield {
                  type:         "usage",
                  inputTokens:  ev.input_tokens  ?? 0,
                  outputTokens: ev.output_tokens ?? 0,
                };
              }
              yield { type: "stop", stopReason: "end_turn" };
              break;
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}

// ── Factory ───────────────────────────────────────────────────────────────────

/**
 * Returns a ProxyModelClient if the user is logged in, null otherwise.
 * The caller decides what to do when null (fall back to direct provider).
 */
export function createProxyClientIfLoggedIn(): ProxyModelClient | null {
  const creds = loadCredentials();
  if (!creds?.token) return null;

  const config  = loadConfig();
  const baseUrl = config.apiBaseUrl ?? process.env["BHARATBUILD_API_URL"] ?? "http://localhost:8000";

  return new ProxyModelClient(baseUrl, creds.token);
}
