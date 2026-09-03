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
import { toWireMessages } from "../models/wire-format.js";
import { loadCredentials } from "./auth.js";
import { loadConfig } from "../config/config.js";
import { resolveProviderKey } from "../auth/provider-key.js";

// ── Wire format for the proxy SSE stream ─────────────────────────────────────
//
// Backend streams newline-delimited JSON events matching the CLI's ModelChunk
// interface, plus a final "usage" event with credit deduction info.

interface ProxyToolCall {
  id?:    string;
  name?:  string;
  input?: Record<string, unknown>;
}

interface ProxyEvent {
  type:            string;
  text?:           string;
  /** Backend shape: {"type":"tool_use","tool":{id,name,input}} */
  tool?:           ProxyToolCall;
  /** Terminal event carries the full call list, stop reason and usage. */
  tool_calls?:     ProxyToolCall[];
  usage?:          { input_tokens?: number; output_tokens?: number; total_tokens?: number };
  // Flat aliases — older/alternate backend builds emit these instead.
  tool_use_id?:    string;
  tool_name?:      string;
  tool_input?:     Record<string, unknown>;
  input_tokens?:   number;
  output_tokens?:  number;
  stop_reason?:    string;
  /** Terminal failure reported inside a 200 response. */
  error?:             string;
  message?:           string;
  /** tool_use_start / tool_use_progress: the tool being composed. */
  name?:              string;
  bytes?:             number;
  // Credit metadata — only in final "complete" event
  credits_deducted?:  number;
  credits_remaining?: number;
  model_used?:        string;
  multiplier?:        number;
}

/**
 * Pull the human-readable part out of a provider error.
 *
 * These arrive as a stringified Python repr wrapped around JSON:
 *   Error code: 400 - {'type': 'error', 'error': {'message': 'Your credit
 *   balance is too low...'}}
 * The message is the only part worth showing; the rest is transport noise.
 */
export function readableModelError(detail: unknown): string {
  const text = typeof detail === "string" ? detail : JSON.stringify(detail ?? "");
  if (!text) return "The model backend failed without giving a reason.";

  // Both quoting styles, because this crosses a Python boundary.
  const message = text.match(/['"]message['"]\s*:\s*['"]([^'"]+)['"]/);
  if (message?.[1]) return attributeToServer(message[1]);

  return attributeToServer(text.length > 300 ? `${text.slice(0, 300)}…` : text);
}

/**
 * Say whose account the provider is complaining about.
 *
 * The provider's own wording is written for whoever holds the key — and on
 * this path that is the BharatBuild server, not the person reading the screen.
 * Relayed verbatim, "Your credit balance is too low… go to Plans & Billing"
 * sends the user to their own billing page to fix an account that is not the
 * one at fault. It cost a real debugging session: a working key was assumed
 * dead because the message said "your".
 */
function attributeToServer(message: string): string {
  // Only rewrite what is plainly about the key holder's account. Anything else
  // — a bad request, a context-length error — is about this request and reads
  // correctly as-is.
  const aboutTheAccount = /credit balance|billing|quota|rate limit|insufficient funds/i.test(message);
  if (!aboutTheAccount) return message;

  return (
    `The BharatBuild server's model account rejected the request: "${message}"\n` +
    `  This is the server's account, not yours. To use your own key instead, run:\n` +
    `      bharatbuild key set sk-ant-…\n` +
    `  That stores it once and applies in every terminal.`
  );
}

const VALID_STOP: ReadonlySet<string> = new Set(["end_turn", "tool_use", "max_tokens", "stop_sequence"]);

function normaliseStop(reason: string | undefined): ModelChunk["stopReason"] {
  return VALID_STOP.has(reason ?? "") ? (reason as ModelChunk["stopReason"]) : "end_turn";
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
          messages:   toWireMessages(params.messages),
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
    // Guards against emitting a call twice when it appears both as a streamed
    // "tool_use" event and again in the terminal "done" payload.
    const seenToolIds = new Set<string>();

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

            // The backend reports a failed generation as an event inside a
            // 200 response rather than as an HTTP error. There was no case
            // for it, so the stream simply ended with nothing in it and the
            // agent loop concluded "Model returned empty response
            // repeatedly" — discarding a precise, actionable message. The
            // real one, for the record, was that the server's own API key
            // had run out of credit.
            case "error": {
              throw new Error(readableModelError(ev.error ?? ev.message));
            }

            // The model has committed to a tool but is still writing its
            // arguments. Surfacing this is the difference between a visible
            // "writing app.py" and nine seconds of apparent hang.
            case "tool_use_start":
              if (ev.tool_use_id && ev.name) {
                yield { type: "tool_progress", toolUseId: ev.tool_use_id, toolName: ev.name, toolBytes: 0 };
              }
              break;

            case "tool_use_progress":
              if (ev.tool_use_id) {
                yield {
                  type: "tool_progress",
                  toolUseId: ev.tool_use_id,
                  toolName: ev.name ?? "",
                  toolBytes: ev.bytes ?? 0,
                };
              }
              break;

            // The backend nests the call under `tool`; this only checked the
            // flat aliases, so every tool call was silently dropped and the
            // agent stopped after announcing what it was about to do.
            case "tool_use": {
              const id    = ev.tool?.id   ?? ev.tool_use_id;
              const name  = ev.tool?.name ?? ev.tool_name;
              const input = ev.tool?.input ?? ev.tool_input ?? {};
              if (id && name) {
                seenToolIds.add(id);
                yield { type: "tool_use", toolUseId: id, toolName: name, toolInput: input };
              }
              break;
            }

            case "usage":
              yield {
                type:         "usage",
                inputTokens:  ev.usage?.input_tokens  ?? ev.input_tokens  ?? 0,
                outputTokens: ev.usage?.output_tokens ?? ev.output_tokens ?? 0,
              };
              break;

            case "stop":
              yield { type: "stop", stopReason: normaliseStop(ev.stop_reason) };
              break;

            // Terminal event. It was not handled at all, so no usage was ever
            // recorded (tokens: 0, turns: 0) and the loop never saw a
            // "tool_use" stop reason to continue on.
            case "done": {
              // Defensive: if a backend only reports calls in the final event,
              // emit the ones we have not already streamed.
              for (const call of ev.tool_calls ?? []) {
                if (call.id && call.name && !seenToolIds.has(call.id)) {
                  seenToolIds.add(call.id);
                  yield {
                    type: "tool_use",
                    toolUseId: call.id,
                    toolName: call.name,
                    toolInput: call.input ?? {},
                  };
                }
              }
              // Credits arrive on "done" — the agentic stream's terminal
              // event. These were only read from "complete", which this
              // backend never emits, so a server-authoritative balance would
              // have been discarded even once the server started sending one.
              if (ev.credits_deducted !== undefined || ev.credits_remaining !== undefined) {
                this.lastCreditsDeducted  = ev.credits_deducted  ?? 0;
                this.lastCreditsRemaining = ev.credits_remaining ?? -1;
                this.lastModelUsed        = ev.model_used ?? this.lastModelUsed;
              }
              const inTok  = ev.usage?.input_tokens  ?? ev.input_tokens  ?? 0;
              const outTok = ev.usage?.output_tokens ?? ev.output_tokens ?? 0;
              if (inTok || outTok) {
                yield { type: "usage", inputTokens: inTok, outputTokens: outTok };
              }
              yield { type: "stop", stopReason: normaliseStop(ev.stop_reason) };
              break;
            }

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
  // A direct key skips the proxy — lower latency, and the user's own account.
  // Checked through resolveProviderKey so a key stored on disk counts too: an
  // environment variable has to be set again in every new terminal, which is
  // how a user with a working key ended up hitting the server's exhausted one.
  if (resolveProviderKey()) return null;

  const creds = loadCredentials();
  if (!creds?.token) return null;

  const config  = loadConfig();
  const baseUrl = config.apiBaseUrl ?? process.env["BHARATBUILD_API_URL"] ?? "http://localhost:8000";

  return new ProxyModelClient(baseUrl, creds.token);
}
