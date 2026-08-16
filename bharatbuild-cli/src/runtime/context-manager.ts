// BharatBuild CLI - Context Manager
// Manages conversation history, compacts with model-based summarization.
//
// Gap 4 fix: _autoCompact() now calls the model to summarize old messages
// instead of blindly dropping them. Matches Kiro CLI's compaction behaviour.
// Falls back to trim-based compaction if the model call fails.

import { shouldCompact } from "../infra/compaction.js";

export interface Message {
  role:    "user" | "assistant" | "system";
  content: string | MessageContent[];
}

export interface MessageContent {
  type:       "text" | "tool_use" | "tool_result" | "image";
  text?:      string;
  id?:        string;
  name?:      string;
  input?:     unknown;
  content?:   string | Array<{ type: string; text?: string }>;
  isError?:   boolean;
  // Image fields
  imageBase64?: string;
  mimeType?:    string;
  imagePath?:   string;
}

export interface ContextStats {
  messageCount:    number;
  estimatedTokens: number;
  contextLimit:    number;
  usagePercent:    number;
  compacted:       boolean;
}

// rough token estimation: 1 token ~= 4 chars
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

function messageTokens(msg: Message): number {
  if (typeof msg.content === "string") {
    return estimateTokens(msg.content) + 4;
  }
  return msg.content.reduce((sum, c) => {
    if (c.type === "text" && c.text)      return sum + estimateTokens(c.text);
    if (c.type === "tool_use" && c.input) return sum + estimateTokens(JSON.stringify(c.input));
    if (c.type === "tool_result" && c.content) {
      const t = typeof c.content === "string" ? c.content : JSON.stringify(c.content);
      return sum + estimateTokens(t);
    }
    return sum + 10;
  }, 4);
}

/** Flatten a Message to a readable string for the summarization prompt. */
function messageToText(msg: Message): string {
  if (typeof msg.content === "string") return msg.content;
  return msg.content
    .filter((c): c is MessageContent & { text: string } => c.type === "text" && !!c.text)
    .map((c) => c.text)
    .join("");
}

export class ContextManager {
  private _messages:     Message[] = [];
  private _systemPrompt: string    = "";
  private _contextLimit: number;
  private _reserveTokens: number;
  private _compacted = false;
  /** Injected by AgentRuntime so compaction can call the model. */
  private _modelClient?: {
    complete(params: {
      model: string; system: string; messages: Message[];
      tools: object[]; maxTokens: number;
    }): AsyncIterable<{ type: string; text?: string }>;
  };
  private _modelId?: string;

  constructor(contextLimit = 200_000, reserveTokens = 8_000) {
    this._contextLimit   = contextLimit;
    this._reserveTokens  = reserveTokens;
  }

  /** Called by AgentRuntime so we can summarize with the same model. */
  setModelClient(
    client: ContextManager["_modelClient"],
    modelId: string,
  ): void {
    this._modelClient = client;
    this._modelId     = modelId;
  }

  setSystemPrompt(prompt: string): void {
    this._systemPrompt = prompt;
  }

  push(message: Message): void {
    this._messages.push(message);
    void this._autoCompact();
  }

  pushAll(messages: Message[]): void {
    this._messages.push(...messages);
    void this._autoCompact();
  }

  get messages(): Message[] {
    return [...this._messages];
  }

  get systemPrompt(): string {
    return this._systemPrompt;
  }

  clear(): void {
    this._messages = [];
    this._compacted = false;
  }

  stats(): ContextStats {
    const estimated = this._messages.reduce((sum, m) => sum + messageTokens(m), 0)
      + estimateTokens(this._systemPrompt);
    return {
      messageCount:    this._messages.length,
      estimatedTokens: estimated,
      contextLimit:    this._contextLimit,
      usagePercent:    Math.round((estimated / this._contextLimit) * 100),
      compacted:       this._compacted,
    };
  }

  /**
   * Auto-compact when approaching 80% of context limit.
   *
   * Strategy (Kiro-matching):
   *   1. Split messages into "old" (first 60%) and "recent" (last 40%).
   *   2. Ask the model to summarize the old messages into a compact paragraph.
   *   3. Replace old messages with a single assistant message containing the summary.
   *   4. If model call fails or isn't available → fall back to trim-based compaction.
   */
  private async _autoCompact(): Promise<void> {
    const flatMessages = this._messages.map((m) => ({
      role: (m.role === "system" ? "user" : m.role) as "user" | "assistant",
      content: messageToText(m),
    }));

    if (!shouldCompact(flatMessages, 0.8, this._contextLimit)) return;

    // Try model-based summarization first
    if (this._modelClient && this._modelId) {
      try {
        await this._summarizeWithModel();
        return;
      } catch {
        // Fall through to trim-based
      }
    }

    // Fallback: trim-based compaction
    this._trim();
  }

  private async _summarizeWithModel(): Promise<void> {
    const total = this._messages.length;
    if (total < 6) return; // not enough history to summarize

    // Keep the most recent 40% of messages intact
    const keepCount  = Math.max(2, Math.floor(total * 0.4));
    const oldMessages = this._messages.slice(0, total - keepCount);
    const newMessages = this._messages.slice(total - keepCount);

    // Build a plain-text transcript of the old messages
    const transcript = oldMessages
      .map((m) => `[${m.role}]: ${messageToText(m).slice(0, 1000)}`)
      .join("\n\n");

    const summaryPrompt =
      `The following is the early part of a conversation between a user and an AI assistant. ` +
      `Summarize it concisely, preserving: decisions made, files modified, commands run, ` +
      `errors encountered, and any context the assistant will need to continue the task.\n\n` +
      `--- Conversation ---\n${transcript}\n--- End ---\n\n` +
      `Write a compact summary (2-5 sentences) suitable for inclusion in an AI system prompt.`;

    let summary = "";
    const stream = this._modelClient!.complete({
      model:     this._modelId!,
      system:    "You are a precise summarizer. Distill conversations into dense, factual summaries.",
      messages:  [{ role: "user", content: summaryPrompt }],
      tools:     [],
      maxTokens: 512,
    });

    for await (const chunk of stream) {
      if (chunk.type === "text_delta" && chunk.text) summary += chunk.text;
    }

    if (!summary.trim()) return; // empty summary — bail to trim fallback

    // Replace old messages with the summary
    const summaryMessage: Message = {
      role:    "assistant",
      content: `[Earlier conversation summarized]\n\n${summary.trim()}`,
    };

    this._messages = [summaryMessage, ...newMessages];
    this._compacted = true;
  }

  private _trim(): void {
    const budget = this._contextLimit - this._reserveTokens
      - estimateTokens(this._systemPrompt);

    while (this._messages.length > 2) {
      const used = this._messages.reduce((sum, m) => sum + messageTokens(m), 0);
      if (used <= budget) break;
      this._messages.splice(1, 1);
    }
    this._compacted = true;
  }

  forRequest(): Message[] {
    return this.messages;
  }

  toJSON(): object {
    return {
      systemPrompt: this._systemPrompt,
      messages:     this._messages,
      contextLimit: this._contextLimit,
      compacted:    this._compacted,
    };
  }

  static fromJSON(data: any): ContextManager {
    const cm = new ContextManager(data.contextLimit);
    cm.setSystemPrompt(data.systemPrompt ?? "");
    cm.pushAll(data.messages ?? []);
    return cm;
  }
}
