// BharatBuild CLI — Event Stream
// Typed SSE events flowing through the agent runtime

export type EventType =
  | "text"
  | "tool_call"
  | "tool_progress"
  | "tool_result"
  | "status"
  | "error"
  | "complete"
  | "usage"
  | "thinking"
  | "permission_request";

export interface BaseEvent {
  type: EventType;
  timestamp: number;
}

export interface TextEvent extends BaseEvent {
  type: "text";
  content: string;
  delta: boolean; // true = streaming chunk, false = complete message
}

export interface ToolCallEvent extends BaseEvent {
  type: "tool_call";
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  description?: string;
}

/**
 * A tool call is still being composed by the model.
 *
 * Emitted while the argument JSON streams in, so the UI can show that a write
 * is under way instead of nothing at all. Carries a byte count rather than the
 * content: the full input arrives once in ToolCallEvent, and echoing every
 * fragment would send a large file twice.
 */
export interface ToolProgressEvent extends BaseEvent {
  type: "tool_progress";
  id: string;
  toolName: string;
  bytes: number;
}

export interface ToolResultEvent extends BaseEvent {
  type: "tool_result";
  id: string;
  toolName: string;
  output: string;
  isError: boolean;
  durationMs: number;
}

export interface StatusEvent extends BaseEvent {
  type: "status";
  message: string;
  phase: "thinking" | "planning" | "coding" | "testing" | "fixing" | "done";
}

export interface ErrorEvent extends BaseEvent {
  type: "error";
  message: string;
  code?: string;
  retryable: boolean;
}

export interface CompleteEvent extends BaseEvent {
  type: "complete";
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  turns: number;
  durationMs: number;
  costUsd?: number;
}

export interface UsageEvent extends BaseEvent {
  type: "usage";
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens?: number;
  cacheWriteTokens?: number;
}

export interface ThinkingEvent extends BaseEvent {
  type: "thinking";
  content: string;
}

export interface PermissionRequestEvent extends BaseEvent {
  type: "permission_request";
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  riskLevel: "low" | "medium" | "high";
  description: string;
}

export type AgentEvent =
  | TextEvent
  | ToolCallEvent
  | ToolProgressEvent
  | ToolResultEvent
  | StatusEvent
  | ErrorEvent
  | CompleteEvent
  | UsageEvent
  | ThinkingEvent
  | PermissionRequestEvent;

// EventEmitter for the agent loop
export type EventHandler = (event: AgentEvent) => void | Promise<void>;

export class EventStream {
  private handlers: Map<EventType | "*", EventHandler[]> = new Map();

  on(type: EventType | "*", handler: EventHandler): this {
    const list = this.handlers.get(type) ?? [];
    list.push(handler);
    this.handlers.set(type, list);
    return this;
  }

  /** Detach a handler. Long-lived UIs need this to avoid replaying events. */
  off(type: EventType | "*", handler: EventHandler): this {
    const list = this.handlers.get(type);
    if (!list) return this;
    const idx = list.indexOf(handler);
    if (idx !== -1) list.splice(idx, 1);
    return this;
  }

  async emit(event: AgentEvent): Promise<void> {
    const specific = this.handlers.get(event.type) ?? [];
    const wildcard = this.handlers.get("*") ?? [];
    for (const h of [...specific, ...wildcard]) {
      await h(event);
    }
  }

  // factory helpers
  static text(content: string, delta = true): TextEvent {
    return { type: "text", content, delta, timestamp: Date.now() };
  }

  static status(message: string, phase: StatusEvent["phase"] = "thinking"): StatusEvent {
    return { type: "status", message, phase, timestamp: Date.now() };
  }

  static error(message: string, retryable = false, code?: string): ErrorEvent {
    return { type: "error", message, retryable, code, timestamp: Date.now() };
  }

  static toolCall(id: string, toolName: string, input: Record<string, unknown>, description?: string): ToolCallEvent {
    return { type: "tool_call", id, toolName, input, description, timestamp: Date.now() };
  }

  static toolResult(id: string, toolName: string, output: string, isError: boolean, durationMs: number): ToolResultEvent {
    return { type: "tool_result", id, toolName, output, isError, durationMs, timestamp: Date.now() };
  }

  static complete(stats: Omit<CompleteEvent, "type" | "timestamp">): CompleteEvent {
    return { type: "complete", ...stats, timestamp: Date.now() };
  }
}
