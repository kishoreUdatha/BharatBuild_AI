/**
 * Mounts the real ink App against synthetic TTY streams so tests can assert on
 * what the user would actually see. Ink refuses to render without a TTY, and
 * ink-text-input needs raw mode, so both streams are faked.
 */
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { App } from "../../src/ui/ink/App.js";

const ESC = String.fromCharCode(27);
const DEL = String.fromCharCode(127);

export interface Harness {
  /** The last repainted frame — status bar, input, in-flight output. */
  frame(): string;
  /**
   * Everything ever written to the terminal. Committed messages go through
   * ink's <Static>, which prints once and never repaints, so they live here
   * (this is the terminal's scrollback) and NOT in `frame()`.
   */
  output(): string;
  type(text: string): Promise<void>;
  press(key: string): Promise<void>;
  clearInput(): Promise<void>;
  wait(ms: number): Promise<void>;
  unmount(): void;
}

export const keys = { esc: ESC, del: DEL, enter: "\r", tab: "\t" };

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export async function mountApp(opts: {
  runtime: any;
  model?: string;
  mode?: string;
  columns?: number;
  rows?: number;
  /**
   * Permission mode to start in. Defaults to "ask" so tests never inherit the
   * developer's ~/.bharatbuild/config.json - three approval tests silently
   * depended on that file saying "ask", and flipping it to "auto" broke them
   * without a line of source changing.
   */
  initialMode?: "ask" | "auto" | "plan";
}): Promise<Harness> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true;
  stdin.setRawMode = () => stdin;
  stdin.ref = () => stdin;
  stdin.unref = () => stdin;

  const stdout: any = new PassThrough();
  stdout.isTTY = true;
  stdout.columns = opts.columns ?? 120;
  stdout.rows = opts.rows ?? 34;

  let last = "";
  let all = "";
  stdout.on("data", (c: Buffer) => {
    const s = c.toString();
    all += s;
    // Ink also emits bare cursor/erase sequences. Treating one of those as
    // "the current frame" makes assertions fail for no real reason, so only
    // writes that actually paint something count.
    if (s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "").trim().length > 0) {
      last = s;
    }
  });

  const instance = render(
    <App
      runtime={opts.runtime}
      model={opts.model ?? "auto"}
      mode={opts.mode ?? "developer"}
      initialMode={opts.initialMode ?? "ask"}
    />,
    { stdin, stdout, exitOnCtrlC: false, patchConsole: false },
  );

  await wait(250);

  const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

  return {
    frame: () => strip(last),
    output: () => strip(all),
    // Keystrokes must arrive as separate events; a bulk write is read as one key.
    async type(text: string) {
      for (const ch of text) { stdin.write(ch); await wait(5); }
      await wait(130);
    },
    async press(key: string) { stdin.write(key); await wait(150); },
    async clearInput() {
      for (let i = 0; i < 60; i++) { stdin.write(DEL); await wait(3); }
      await wait(140);
    },
    wait,
    unmount: () => instance.unmount(),
  };
}

/** Minimal runtime double with the surface the App and slash commands touch. */
export function makeRuntime(overrides: Record<string, any> = {}) {
  const calls: string[] = [];
  const rt: any = {
    calls,
    sessionId: "sess-test",
    serverCreditsRemaining: -1,
    cost: {
      summary: () => "1,234 tokens · 0.05 credits · 3s · 1 turn",
      breakdown: () => "",
      setModel() {},
      setEffort() {},
    },
    context: {
      messages: [] as any[],
      stats: () => ({
        messageCount: rt.context.messages.length,
        estimatedTokens: 900,
        contextLimit: 200_000,
        usagePercent: 0.45,
        compacted: false,
      }),
      clear() { rt.context.messages = []; },
      pushAll(m: any[]) { rt.context.messages = m; },
      push(m: any) { rt.context.messages.push(m); },
    },
    dispatcher: {
      renderBuiltInToolsList: () => "  read_file\n  write_file",
      resetBuiltInApprovals() {},
    },
    events: {
      h: {} as Record<string, Function[]>,
      on(t: string, fn: Function) { (this.h[t] ??= []).push(fn); return this; },
      off(t: string, fn: Function) {
        const l = this.h[t];
        if (l) l.splice(l.indexOf(fn), 1);
        return this;
      },
      async emit(e: any) {
        for (const fn of [...(this.h[e.type] ?? []), ...(this.h["*"] ?? [])]) await fn(e);
      },
    },
    async run(input: string) {
      calls.push(input);
      await rt.events.emit({ type: "status", message: "planning", phase: "planning", timestamp: 1 });
      await rt.events.emit({
        type: "tool_call", id: `t${calls.length}`, toolName: "write_file",
        input: { path: "src/app.tsx" }, timestamp: 2,
      });
      await rt.events.emit({
        type: "tool_result", id: `t${calls.length}`, toolName: "write_file",
        output: "@@ -1 +1 @@\n-old\n+new", isError: false, durationMs: 12, timestamp: 3,
      });
      await rt.events.emit({ type: "text", content: "done building", delta: true, timestamp: 4 });
      await rt.events.emit({
        type: "complete", totalTokens: 99, turns: 1, durationMs: 20,
        inputTokens: 50, outputTokens: 49, timestamp: 5,
      });
    },
    cancel() {},
    reset() { rt.context.clear(); },
    ...overrides,
  };
  return rt;
}
