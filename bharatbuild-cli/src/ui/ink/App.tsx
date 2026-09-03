/**
 * App — Main ink TUI application component.
 *
 * Scrollback model
 * ----------------
 * This used to be a fixed-height full-screen app: the root Box was pinned to
 * `stdout.rows` and every frame repainted the same region. Anything older than
 * one screen was destroyed, so a long `/code` or `/help` wiped the
 * conversation and there was nothing to scroll back to.
 *
 * Now finished output goes through ink's <Static>, which prints each item once
 * and never repaints it. Those lines become ordinary terminal scrollback, so
 * the session history survives and the scrollbar works. Only the in-flight
 * assistant message, running tools, the status bar and the input are live.
 *
 * Layout (top to bottom):
 *   <Static>   committed messages + finished tool calls   ← real scrollback
 *   live:      streaming reply, running tools
 *   sticky:    StatusBar, InputPrompt (+ command palette)
 */

import React, { useState, useCallback, useEffect, useRef } from "react";
import { Box, Text, Static, useInput, useApp, useStdout } from "ink";
import { StatusBar, type Phase } from "./StatusBar.js";
import { MessageBubble, Welcome, type ChatMessage } from "./ChatMessages.js";
import { ToolOutput, ToolOutputList, type ToolCall, type ToolStatus } from "./ToolOutput.js";
import { InputPrompt } from "./InputPrompt.js";
import { runSlashCommand } from "./slash-actions.js";
import { PermissionPrompt, type PendingPermission, type PermissionChoice } from "./PermissionPrompt.js";
import { alwaysAllowKey } from "./permission-copy.js";
import { expandMentions } from "./file-mentions.js";
import { runUserCommand } from "../../tools/shell/index.js";
import { RewindPicker } from "./RewindPicker.js";
import { QuestionPrompt } from "./QuestionPrompt.js";
import { setQuestionAsker, type PendingQuestion } from "../../tools/agent/ask-user.js";
import { userTurns, keepBefore, type Turn } from "./rewind.js";
import { beginTurn, restoreSince, filesChangedSince } from "../../runtime/file-snapshots.js";

/**
 * How close two Esc presses have to be to count as a double-tap.
 *
 * Generous: this is a deliberate two-handed gesture on a keyboard, not a
 * mouse double-click, and a missed pair is more annoying than a rare
 * accidental one — the picker cancels on Esc anyway.
 */
const DOUBLE_ESC_MS = 600;
import { setPermissionAsker } from "../../permissions/permission-manager.js";
import {
  decideForMode, nextMode, normalizeMode, MODE_LABEL, type PermissionMode,
} from "./modes.js";
import { loadConfig } from "../../config/config.js";

/**
 * Honour the flags the user already reached for. `--trust-all-tools` and
 * BHARATBUILD_MODE=auto previously set config the TUI never consulted, so the
 * agent still stopped on every write.
 */
function initialPermissionMode(): PermissionMode {
  if (process.env["BHARATBUILD_TRUST_ALL_TOOLS"] === "1") return "auto";
  // Env beats the saved config, matching how the rest of the config layer
  // resolves precedence.
  const fromEnv = normalizeMode(process.env["BHARATBUILD_MODE"]);
  if (fromEnv) return fromEnv;
  try {
    return normalizeMode(loadConfig()?.permissionMode) ?? "ask";
  } catch {
    // A missing or malformed config must not stop the TUI from starting.
    return "ask";
  }
}
import { liveTail } from "./live-tail.js";
import { activityTip } from "./activity.js";
import { warmUp } from "./highlighter.js";
import { getGlyphs } from "./glyphs.js";
import { getInkTheme } from "./theme.js";

export interface AppProps {
  runtime: any;
  model: string;
  mode?: string;
  /**
   * Starting permission mode. Overrides config and env.
   *
   * Without this the mode came from the developer's own ~/.bharatbuild/
   * config.json, so the approval tests passed or failed depending on a file
   * outside the repo. Tests pin it; production omits it.
   */
  initialMode?: PermissionMode;
}

/** One committed thing in the scrollback. */
type HistoryEntry =
  | { kind: "message"; id: string; message: ChatMessage }
  | { kind: "tool"; id: string; tool: ToolCall }
  | { kind: "rollup"; id: string; text: string }
  // Blank rows printed once at startup to push the prompt to the bottom of
  // an empty screen. This lives in the transcript, not in the live region:
  // <Static> writes it once and never repaints it, so it adds nothing to the
  // height ink has to erase each frame.
  | { kind: "spacer"; id: string; lines: number }
  // The welcome panel. It used to render live and only while the transcript
  // was empty, so it vanished the moment the first message arrived. Printed
  // once into <Static> it stays at the top of the session, and scrolls away
  // naturally as the conversation grows past a screen.
  | { kind: "banner"; id: string };

/** Tools whose repeated use is worth summarising rather than re-reading. */
const ROLLUP_LABELS: Record<string, string> = {
  execute_command: "shell command",
  shell: "shell command",
  read_file: "file read",
  read: "file read",
};

/**
 * Rows reserved for in-flight output: the streaming reply and any running
 * tool card. Fixed so the input box below it never moves.
 *
 * Kept small deliberately. Ink erases a frame by moving the cursor up by
 * that frame's height, so the live region has to stay well under the
 * viewport - the same constraint that governs everything else here.
 */
/**
 * Rows the interface costs before any padding or live output: the welcome
  * panel, the input box, the status line and the tip row.
 *
 * Measured by rendering into a 200-row terminal and counting, rather than
 * added up from the parts - the estimate was 23 and the truth is 28, and the
 * five-row shortfall pushed the banner off the top of every screen.
 */
const FIXED_ROWS = 15;

const LIVE_ROWS_MAX = 10;
const LIVE_ROWS_MIN = 3;

/**
 * Rows to reserve for in-flight output at this terminal height.
 *
 * A flat 10 did not fit a 20-row terminal alongside the banner, and pushed it
 * off the top - so this gives back what is left after the banner and the
 * sticky block, within bounds.
 */
function liveRowsFor(rows: number): number {
  // FIXED_ROWS is what everything else costs, so this is what is left over.
  return Math.max(LIVE_ROWS_MIN, Math.min(LIVE_ROWS_MAX, rows - FIXED_ROWS - 4));
}

let seq = 0;
const nextId = (kind: string) => `${kind}-${Date.now()}-${seq++}`;

export function App({ runtime, model, mode, initialMode }: AppProps): React.ReactElement {
  const { exit } = useApp();
  const { stdout } = useStdout();

  // Append-only. <Static> requires this; it tracks how much it has printed.
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  // Bumped by /clear to remount <Static> after wiping the screen.
  const [staticKey, setStaticKey] = useState(0);

  const [streaming, setStreaming] = useState<ChatMessage | null>(null);
  const [activeTools, setActiveTools] = useState<ToolCall[]>([]);

  /**
   * Turns offered by the rewind picker, or null when it is closed.
   *
   * Captured when the picker opens rather than read on each render: the list
   * must not shift under the cursor if anything appends to the context while
   * it is open.
   */
  const [rewinding, setRewinding] = useState<Turn[] | null>(null);
  /** When Esc was last pressed on its own, for the double-tap. */
  const lastEscRef = useRef(0);

  /**
   * Image from /paste, waiting for the message it belongs to.
   *
   * Held rather than sent immediately because a screenshot is nearly always
   * evidence for a question — "why does this look wrong?" — and sending it
   * alone would spend a turn asking the model to guess what was being asked.
   */
  /** A question from ask_user, with the promise it is holding open. */
  const [question, setQuestion] = useState<
    (PendingQuestion & { resolve: (chosen: string[] | null) => void }) | null
  >(null);

  const [pendingImage, setPendingImage] = useState<{ imageBase64: string; mimeType: string } | null>(null);
  const pendingImageRef = useRef(pendingImage);
  pendingImageRef.current = pendingImage;

  const [phase, setPhase] = useState<Phase>("idle");
  const [agent, setAgent] = useState("default");
  const [activeModel, setActiveModel] = useState(model);
  // Which model actually answered, when the backend substituted one.
  const [servedModel, setServedModel] = useState<string | null>(null);
  const [tokenCount, setTokenCount] = useState(0);
  /**
   * Characters of reply streamed in this turn, for a live token estimate.
   * The exact count only arrives with the usage event when the turn ends, so
   * the status line had nothing to show while the model was writing - it read
   * as though nothing was happening.
   */
  const [streamedChars, setStreamedChars] = useState(0);
  const [creditBalance] = useState(0);
  const [compact, setCompact] = useState(false);
  // One source of truth for what the agent may do without being asked.
  // `planMode` is derived so the existing status badge and /plan command keep
  // working, but they now describe a mode that actually gates tools.
  const [permMode, setPermMode] = useState<PermissionMode>(
    () => initialMode ?? initialPermissionMode(),
  );
  const planMode = permMode === "plan";
  const setPlanMode = useCallback(
    (next: boolean | ((p: boolean) => boolean)) =>
      setPermMode((cur) => {
        const want = typeof next === "function" ? next(cur === "plan") : next;
        return want ? "plan" : "ask";
      }),
    [],
  );
  const modeRef = useRef<PermissionMode>(permMode);
  useEffect(() => { modeRef.current = permMode; }, [permMode]);
  const [tangentMode, setTangentMode] = useState(false);

  const [ctrlCCount, setCtrlCCount] = useState(0);
  const [prefill, setPrefill] = useState<string | undefined>(undefined);
  const [expandTools, setExpandTools] = useState(false);
  const [, setPaint] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [pending, setPending] = useState<(PendingPermission & { resolve: (c: PermissionChoice) => void }) | null>(null);
  // What is streaming right now, readable outside a state updater.
  const streamMsgRef = useRef<ChatMessage | null>(null);
  const alwaysAllow = useRef<Set<string>>(new Set());
  const turnStart = useRef<number | null>(null);
  // Messages typed while a turn is running, sent one per turn afterwards.
  const queueRef = useRef<string[]>([]);
  // Consecutive same-kind tool calls, summarised as "Ran N shell commands"
  // once the run ends — a wall of near-identical cards is hard to scan.
  const runRef = useRef<{ label: string; count: number } | null>(null);
  const [queued, setQueued] = useState<string[]>([]);
  const queuedCount = queued.length;
  const syncQueue = useCallback(() => setQueued([...queueRef.current]), []);
  // Esc must dismiss the palette when it is open and interrupt otherwise, so
  // the App needs to know which of the two is on screen.
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Height of the fixed live pane; also the number the startup padding has to
  // leave room for.
  const liveRows = liveRowsFor(stdout?.rows ?? 24);

  const busy = phase !== "idle";
  /**
   * Whether to reserve rows for live output at all.
   *
   * Not `busy` alone: phase reaches "idle" a frame before the streamed reply
   * is committed to <Static>, and collapsing the pane in that gap blinks the
   * last lines off the screen.
   */
  const liveActive = busy || streaming !== null || activeTools.length > 0;
  // handleSubmit is recreated on most renders; the queue check reads the
  // current phase through a ref so a stale closure cannot mis-route input.
  const phaseRef = useRef<Phase>(phase);
  phaseRef.current = phase;

  /**
   * A history entry minus its id, which commit assigns.
   *
   * Distributive on purpose: a plain `Omit<HistoryEntry, "id">` collapses the
   * union to the keys every variant shares — that is, to `kind` alone — so
   * every call had to be cast to get its own payload past the type.
   */
  type Uncommitted = HistoryEntry extends infer E
    ? E extends { id: string } ? Omit<E, "id"> : E
    : never;

  const commit = useCallback((entry: Uncommitted) => {
    setHistory((prev) => [...prev, { ...entry, id: nextId(entry.kind) } as HistoryEntry]);
  }, []);

  /** Emit "Ran N shell commands" when a run of same-kind tools ends. */
  const flushRun = useCallback(() => {
    const run = runRef.current;
    runRef.current = null;
    if (!run || run.count < 2) return;
    commit({
      kind: "rollup",
      text: `Ran ${run.count} ${run.label}${run.count === 1 ? "" : "s"}`,
    } as HistoryEntry);
  }, [commit]);

  const flushRunRef = useRef(flushRun);
  flushRunRef.current = flushRun;

  /**
   * Move the in-flight reply into the transcript.
   *
   * commit() used to be called from inside a setStreaming updater. Updaters
   * must be pure - React may invoke one more than once for a single update,
   * and every invocation appended the message again. The same mistake was
   * fixed for the shift+tab mode notice and left standing here, in three
   * separate places.
   */
  const resetTurnMetrics = useCallback(() => setStreamedChars(0), []);

  const flushStream = useCallback(() => {
    const pending = streamMsgRef.current;
    streamMsgRef.current = null;
    streamRef.current = "";
    if (pending) {
      commit({ kind: "message", message: { ...pending, isStreaming: false } } as HistoryEntry);
    }
    setStreaming(null);
  }, [commit]);

  const say = useCallback(
    (role: ChatMessage["role"], content: string) => {
      commit({
        kind: "message",
        message: { id: nextId(role), role, content, timestamp: new Date() },
      } as HistoryEntry);
    },
    [commit],
  );

  // Tick a visible timer while a turn is in flight, so a slow model still
  // looks alive.
  useEffect(() => {
    if (!busy) {
      turnStart.current = null;
      setElapsedSec(0);
      return;
    }
    if (turnStart.current === null) turnStart.current = Date.now();
    const id = setInterval(() => {
      if (turnStart.current !== null) {
        setElapsedSec(Math.floor((Date.now() - turnStart.current) / 1000));
      }
    }, 1000);
    return () => clearInterval(id);
  }, [busy]);

  const contextPercent = (() => {
    const pct = runtime?.context?.stats?.()?.usagePercent;
    return typeof pct === "number" ? pct : undefined;
  })();

  /**
   * Answer approval requests inside the TUI. Without this the loop fell back
   * to a readline prompt that ink painted over, so every tool was denied.
   */
  useEffect(() => {
    setPermissionAsker(async (toolName, input) => {
      // Read the mode through a ref: the asker is registered once, so a value
      // captured from state here would freeze at whatever it was on mount and
      // every later shift+tab would be ignored.
      const decided = decideForMode(modeRef.current, toolName);
      if (decided === "allow") return "allow";
      if (decided === "deny") return "deny";
      // Scoped to what the prompt actually offered. Keyed on the tool name,
      // approving `npm test` for the session also approved `rm -rf`, because
      // both arrive as the same tool.
      const grantKey = alwaysAllowKey(toolName, input);
      if (alwaysAllow.current.has(grantKey)) return "allow";
      return new Promise((resolve) => {
        setPending({
          toolName,
          input,
          resolve: (choice) => {
            if (choice === "allow_always") alwaysAllow.current.add(grantKey);
            setPending(null);
            resolve(choice === "deny" ? "deny" : "allow");
          },
        });
      });
    });
    return () => setPermissionAsker(null);
  }, []);

  // ask_user reaches the screen the same way the permission prompt does: the
  // tool cannot render, and readline would be painted over by ink.
  useEffect(() => {
    setQuestionAsker((q) => new Promise((resolve) => {
      setQuestion({ ...q, resolve: (chosen) => { setQuestion(null); resolve(chosen); } });
    }));
    return () => setQuestionAsker(null);
  }, []);

  useEffect(() => { warmUp(); }, []);

  /*
   * The prompt follows the conversation; it is not pinned to the viewport.
   *
   * It used to be pinned: blank spacers were printed at startup to push the
   * sticky block to the bottom of the terminal, and the live pane held a
   * constant height so nothing shifted. That kept the input perfectly still
   * and cost a permanent band of empty rows between a short reply and the
   * input — the reply ended mid-screen and the prompt sat ten rows below it.
   *
   * claude-code does not pin. Its prompt sits directly under the last line of
   * output and moves down as more arrives, letting the terminal scroll. So no
   * spacers, and the live pane is only as tall as a running turn needs. The
   * prompt still cannot drift *within* a turn, which was the original
   * complaint: the height is fixed for the turn's duration and changes only
   * at its boundaries, where the user has just pressed enter and expects it.
   */
  useEffect(() => {
    commit({ kind: "banner" } as HistoryEntry);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Text accumulated for the reply currently streaming in.
  const streamRef = useRef("");

  /**
   * Subscribe once. This used to live inside the submit handler, so prompt N
   * added the Nth listener and replayed every chunk N times.
   */
  useEffect(() => {
    if (!runtime?.events?.on) return;

    const onEvent = (event: any) => {
      switch (event.type) {
        case "text": {
          if (!event.content) return;
          streamRef.current += event.content;
          setStreamedChars((n) => n + event.content.length);
          const content = streamRef.current;
          setStreaming((prev) => {
            const next = prev
              ? { ...prev, content }
              : { id: nextId("assistant"), role: "assistant" as const, content, timestamp: new Date(), isStreaming: true };
            // Mirrored so flushStream can read it without an updater.
            streamMsgRef.current = next;
            return next;
          });
          setPhase("coding");
          return;
        }

        case "status":
          setPhase((prev) => (event.phase ?? prev) as Phase);
          return;

        // The model is still writing the call's arguments. Show the card now
        // rather than after — composing a large file took ~9s, during which
        // the UI had nothing to display and looked hung.
        case "tool_progress":
          setActiveTools((prev) => {
            const existing = prev.find((t) => t.id === event.id);
            if (existing) {
              return prev.map((t) =>
                t.id === event.id ? { ...t, pendingBytes: event.bytes } : t,
              );
            }
            return [
              ...prev,
              {
                id: event.id,
                name: event.toolName,
                status: "running" as ToolStatus,
                pendingBytes: event.bytes,
              },
            ];
          });
          setPhase("coding");
          return;

        case "tool_call":
          // Commit whatever the model has said so far BEFORE the tool card.
          // Text stayed live until the whole run finished, so every tool call
          // was committed ahead of the narration that introduced it — the
          // transcript came out with all the tool cards stacked at the top.
          // Flushing here also splits the reply into one entry per step
          // instead of gluing them into a single run-on paragraph.
          flushStream();
          streamRef.current = "";

          // tool_progress may already have created this card. Update it in
          // place — appending would leave two entries for one call, one of
          // them stuck "running" forever.
          setActiveTools((prev) => {
            const card = {
              id: event.id,
              name: event.toolName,
              input: event.input,
              status: "running" as ToolStatus,
            };
            return prev.some((t) => t.id === event.id)
              ? prev.map((t) => (t.id === event.id ? { ...t, ...card, pendingBytes: undefined } : t))
              : [...prev, card];
          });
          setPhase("coding");
          return;

        case "tool_result": {
          // Finished tools move into scrollback so they survive the session.
          setActiveTools((prev) => {
            const done = prev.find((t) => t.id === event.id);
            if (done) {
              const label = ROLLUP_LABELS[done.name];
              if (label) {
                if (runRef.current?.label === label) runRef.current.count += 1;
                else { flushRunRef.current(); runRef.current = { label, count: 1 }; }
              } else {
                flushRunRef.current();
              }
              commit({
                kind: "tool",
                tool: {
                  ...done,
                  status: (event.isError ? "error" : "success") as ToolStatus,
                  output: event.output,
                  durationMs: event.durationMs,
                },
              } as HistoryEntry);
            }
            return prev.filter((t) => t.id !== event.id);
          });
          return;
        }

        // Errors used to be dropped, so a failed turn looked like silence.
        case "error":
          setPhase("idle");
          say("system", `Error: ${event.message}`);
          return;

        case "usage":
          setTokenCount((n) => n + (event.inputTokens ?? 0) + (event.outputTokens ?? 0));
          return;

        case "complete":
          // The exact figure arrives with the usage event; the estimate has
          // done its job and must not carry into the next turn.
          resetTurnMetrics();
          flushRunRef.current();
          setPhase("idle");
          // The backend may serve a different model than the one requested —
          // its local profile routes sonnet and opus to haiku to save cost.
          // Read what actually answered so the status bar stops claiming the
          // model that was merely asked for.
          setServedModel(runtime?.servedModel ?? null);
          if (typeof event.totalTokens === "number") setTokenCount(event.totalTokens);
          flushStream();
          return;

        default:
          return;
      }
    };

    runtime.events.on("*", onEvent);
    return () => { runtime.events.off?.("*", onEvent); };
  }, [runtime, commit, say]);

  // Global shortcuts
  useInput((input, key) => {
    if (input === "c" && key.ctrl) {
      if (phase !== "idle") {
        runtime?.cancel?.();
        setPhase("idle");
        setCtrlCCount(0);
      } else {
        setCtrlCCount((prev) => {
          if (prev >= 1) { exit(); return 0; }
          setTimeout(() => setCtrlCCount(0), 2000);
          return prev + 1;
        });
      }
      return;
    }
    // Esc interrupts the turn. Ctrl+C already did this but nothing said so,
    // and Esc is what both reference CLIs bind.
    if (key.escape && busy && !paletteOpen && !pending) {
      runtime?.cancel?.();
      setPhase("idle");
      // Anything typed while the agent was working is dropped too. Esc means
      // stop; draining the queue straight afterwards started a brand new turn
      // out of a half-finished thought, which is the opposite of stopping.
      const dropped = queueRef.current.length;
      queueRef.current = [];
      syncQueue();
      say("system", dropped > 0
        ? `Interrupted. ${dropped} queued message${dropped === 1 ? "" : "s"} discarded.`
        : "Interrupted.");
      // Not a rewind candidate: this press meant "stop", and a second one a
      // moment later should not reopen the conversation as a list.
      lastEscRef.current = 0;
      return;
    }

    /*
     * Esc twice opens the rewind list.
     *
     * Only while idle. During a turn the first Esc means "stop", and the
     * handler above has already consumed it — pairing an interrupt with the
     * press that follows it would turn a double-tap-to-be-sure into a modal
     * nobody asked for.
     */
    if (key.escape && !busy && !paletteOpen && !pending && !rewinding) {
      const now = Date.now();
      if (now - lastEscRef.current < DOUBLE_ESC_MS) {
        lastEscRef.current = 0;
        const turns = userTurns(runtime?.context?.messages ?? []);
        if (turns.length === 0) {
          say("system", "Nothing to rewind to yet.");
          return;
        }
        setRewinding(turns);
        return;
      }
      lastEscRef.current = now;
      return;
    }
    if (input === "o" && key.ctrl) { setExpandTools((p) => !p); return; }
    // Cycle ask -> auto -> plan. This used to toggle plan mode alone, so the
    // "shift+tab modes" hint led straight to a read-only agent.
    if (key.tab && key.shift) {
      // Compute outside the updater: React may invoke an updater twice, which
      // would print the notice twice.
      const next = nextMode(modeRef.current);
      modeRef.current = next;
      setPermMode(next);
      // Announce it. A badge changing in the corner is easy to miss, and the
      // complaint was precisely not knowing why the agent kept stopping.
      say("system", `mode: ${MODE_LABEL[next]}`);
      return;
    }
  });

  const clearPrefill = useCallback(() => setPrefill(undefined), []);

  const wipeScreen = useCallback(() => {
    // <Static> output already lives in the terminal's scrollback, so clearing
    // has to clear the scrollback too (\x1b[3J) — otherwise /clear only pushes
    // the old text out of view.
    stdout?.write?.("\x1b[2J\x1b[3J\x1b[H");
    setHistory([]);
    setActiveTools([]);
    setStreaming(null);
    setStaticKey((k) => k + 1);
  }, [stdout]);

  // Draining goes straight to dispatch rather than back through the queue
  // guard. Re-entering the guard happens to work today — React flushes the
  // "idle" state in a microtask, which beats the setTimeout macrotask — but it
  // makes correctness depend on scheduler ordering for no reason. A drain is
  // by definition already past the guard.
  const dispatchRef = useRef<(input: string) => void>(() => {});

  /**
   * Run the next buffered message, if any. Called when a turn settles.
   * One at a time: each queued line becomes its own turn, which is what
   * "send after the turn ends" means.
   */
  const drainQueue = useCallback(() => {
    const next = queueRef.current.shift();
    syncQueue();
    // Straight to dispatch, never back through the guard.
    if (next !== undefined) setTimeout(() => dispatchRef.current(next), 0);
  }, [syncQueue]);

  /** Runs a prompt or command immediately, with no queue check. */
  const dispatch = useCallback(
    (input: string) => {

      const userMsg: ChatMessage = { id: nextId("user"), role: "user", content: input, timestamp: new Date() };
      commit({ kind: "message", message: userMsg } as HistoryEntry);

      /*
       * `!command` runs the shell directly, with no model turn.
       *
       * Checking something — the branch, whether the build passes, what a
       * directory holds — meant either leaving the session or spending a whole
       * turn asking the agent to run it. The result still joins the
       * conversation, so the next question can refer to it without repeating
       * anything.
       */
      if (input.startsWith("!")) {
        const command = input.slice(1).trim();
        if (!command) {
          say("system", "Type a command after ! — for example !npm test");
          return;
        }

        const id = nextId("bang");
        setPhase("tool");
        setActiveTools((prev) => [...prev, { id, name: "bash", status: "running", input: { command } }]);

        void (async () => {
          const began = Date.now();
          const result = await runUserCommand({ command, working_dir: process.cwd() });
          setActiveTools((prev) => prev.filter((t) => t.id !== id));
          commit({
            kind: "tool",
            tool: {
              id, name: "bash", input: { command },
              status: (result.isError ? "error" : "success") as ToolStatus,
              output: result.content,
              durationMs: Date.now() - began,
            },
          });

          // The model is told, so a follow-up question can build on it rather
          // than asking for the same command to be run again. Recorded as the
          // user's own turn because that is who ran it.
          try {
            runtime.context.push({
              role: "user",
              content: `I ran this command myself:\n\n$ ${command}\n\n${result.content}`,
            });
          } catch {
            /* a runtime without a context is still usable for running commands */
          }

          setPhase("idle");
          drainQueue();
        })();
        return;
      }

      // Slash commands are handled locally — they must never reach the model.
      if (input.startsWith("/")) {
        setPhase("thinking");
        void (async () => {
          const transcript = [
            ...history.flatMap((h) => (h.kind === "message" ? [h.message] : [])),
            userMsg,
          ].map((m) => ({ role: m.role, content: m.content, timestamp: m.timestamp }));

          try {
            const result = await runSlashCommand(input, {
              runtime, model: activeModel, agent, compact, planMode, tangentMode, transcript,
            });
            setPhase("idle");
            if (result.exit) { exit(); return; }
            // A user-defined .toml command expands to a prompt. Send it as a
            // turn rather than printing it: it is a template for something to
            // ask, not output to read.
            if (result.promptToSend !== undefined) {
              dispatchRef.current(result.promptToSend);
              return;
            }
            if (result.inputValue !== undefined) setPrefill(result.inputValue);
            if (result.attachImage) setPendingImage(result.attachImage);
            if (result.repaint) setPaint((p) => p + 1);
            if (result.patch?.model !== undefined) setActiveModel(result.patch.model);
            if (result.patch?.agent !== undefined) setAgent(result.patch.agent);
            if (result.patch?.compact !== undefined) setCompact(result.patch.compact);
            if (result.patch?.planMode !== undefined) setPlanMode(result.patch.planMode);
            if (result.patch?.tangentMode !== undefined) setTangentMode(result.patch.tangentMode);
            if (result.clear) { wipeScreen(); drainQueue(); return; }
            if (result.output) say("system", result.output);
          } catch (err) {
            setPhase("idle");
            say("system", `Command failed: ${(err as Error).message}`);
          }
          drainQueue();
        })();
        return;
      }

      if (!runtime || typeof runtime.run !== "function") {
        say("system", "No agent runtime is connected — cannot run prompts.");
        return;
      }

      streamRef.current = "";
      setPhase("thinking");

      // `@file` mentions are resolved here, not in the transcript above: the
      // user sees what they typed, and the model receives the file with it.
      // Without this the mention was just a path in a sentence, which the
      // model would as often answer from the name as read.
      // Open a snapshot turn so anything this prompt edits can be undone by
      // esc esc. Keyed to the message index the rewind picker uses, so the
      // two agree about what "back to here" means.
      beginTurn((runtime?.context?.messages ?? []).length);

      // The image rides with this message and is then spent. Passed as an
      // attachment rather than pushed separately: the loop always pushes the
      // user message itself, so pushing our own first produced the attachment
      // followed by a duplicate text-only turn.
      const attachments = pendingImageRef.current
        ? [{ type: "image" as const, imageBase64: pendingImageRef.current.imageBase64, mimeType: pendingImageRef.current.mimeType }]
        : undefined;
      if (attachments) setPendingImage(null);

      runtime
        .run(expandMentions(input), attachments ? { attachments } : undefined)
        .then(() => {
          setPhase("idle");
          flushStream();
          drainQueue();
        })
        .catch((err: Error) => {
          setPhase("idle");
          say("system", `Error: ${err.message}`);
          drainQueue();
        });
    },
    [runtime, exit, commit, say, wipeScreen, drainQueue, history, activeModel, agent, compact, planMode, tangentMode],
  );

  dispatchRef.current = dispatch;

  /**
   * The prompt stays usable while the agent works. Anything typed during a
   * turn is buffered rather than dropped — the input used to be replaced by
   * the word "waiting…", so a long turn meant a dead keyboard.
   */
  const handleSubmit = useCallback(
    (input: string) => {
      if (phaseRef.current !== "idle") {
        queueRef.current.push(input);
        syncQueue();
        return;
      }
      dispatch(input);
    },
    [dispatch, syncQueue],
  );

  // Spacers are layout, not content: counting them made the welcome panel
  // disappear the moment padding was printed.
  /*
   * The prompt sits at the bottom of an empty screen, and the two earlier
   * attempts at that had to be reverted.
   *
   * Ink erases a frame by moving the cursor up by that frame's height. Both
   * previous attempts - a computed spacer and a flexbox `height={rows}` - put
   * the padding in the live region, which made the live region as tall as the
   * viewport. Writing N lines into an N-row terminal scrolls it by one, the
   * top row is gone, and every subsequent erase is off by one: the interface
   * ends up on screen twice.
   *
   * The padding now goes through <Static>. Static content is written once and
   * never repainted, so it does not enter the erase height at all - the live
   * region stays at its natural dozen-or-so rows however much padding is
   * printed above it. The blanks simply become the top of the scrollback,
   * which is what a terminal does with anything scrolled off.
   */
  return (
    <Box flexDirection="column">
      {/* Committed output — printed once, becomes terminal scrollback. */}
      <Static key={staticKey} items={history}>
        {(entry) =>
          entry.kind === "banner" ? (
            <Box key={entry.id} flexDirection="column">
              <Welcome mode={mode} />
            </Box>
          ) : entry.kind === "spacer" ? (
            // Blank rows that push the prompt to the bottom on an empty screen.
            // A single space per row, because ink collapses a truly empty Text.
            <Box key={entry.id} flexDirection="column">
              {Array.from({ length: entry.lines }, (_, i) => (
                <Text key={i}> </Text>
              ))}
            </Box>
          ) : entry.kind === "rollup" ? (
            <Box key={entry.id} paddingX={1} marginBottom={1}>
              <Text color="gray" dimColor>{entry.text}</Text>
            </Box>
          ) : entry.kind === "message" ? (
            <Box key={entry.id} paddingX={1} flexDirection="column">
              <MessageBubble message={entry.message} compact={compact} />
            </Box>
          ) : (
            <Box key={entry.id} flexDirection="column">
              <ToolOutput tool={entry.tool} forceExpanded={expandTools || undefined} />
            </Box>
          )
        }
      </Static>

      {/* Live region: only what is still changing. */}
      {/* Only the tail. The live region is erased by cursor-up each frame, so
          letting it grow with the reply eventually outruns the erase and
          leaves a stale copy on screen. The full text is committed to
          <Static> when the turn ends. */}
      {/*
        * Fixed height, and this is the reason the prompt stays put.
        *
        * The input box renders below this pane, so its position was
        * whatever this happened to contain: 4 rows idle, ~19 mid-turn with
        * a reply streaming and a tool running. The prompt slid down as the
        * answer arrived and snapped back when it was committed.
        *
        * A Box with an explicit height reserves those rows whether or not
        * anything fills them, so the sum above the prompt is constant. The
        * content is capped to fit - LIVE_TAIL_LINES for the reply, leaving
        * the rest for a running tool card - because overflow here would
        * push the prompt down again.
        */}
      {/*
        * Bottom-anchored, so output grows upward the way a terminal does.
        *
        * A fixed-height column fills from the top, so a streaming reply
        * appeared at the top of the reserved block and crept down through six
        * blank rows toward the prompt — the opposite direction to every other
        * console. Anchoring to the end keeps the newest line adjacent to the
        * input and pushes older ones up, which is what the eye expects and
        * what claude-code does.
        */}
      <Box
        height={liveActive ? liveRows : 0}
        flexDirection="column"
        overflow="hidden"
        justifyContent="flex-end"
      >
        {streaming && (
          <Box paddingX={1} flexDirection="column">
            <MessageBubble
              message={{ ...streaming, content: liveTail(streaming.content) }}
              compact={compact}
            />
          </Box>
        )}
        {activeTools.length > 0 && (
          <ToolOutputList tools={activeTools} forceExpanded={expandTools || undefined} max={2} />
        )}
      </Box>

      {pending && (
        <PermissionPrompt pending={pending} onDecide={pending.resolve} />
      )}

      {question && (
        <QuestionPrompt question={question} onAnswer={question.resolve} />
      )}

      {rewinding && (
        <RewindPicker
          turns={rewinding}
          filesFor={(t) => filesChangedSince(t.index).length}
          onDecide={(turn) => {
            setRewinding(null);
            if (!turn) return;
            const all = runtime?.context?.messages ?? [];
            const kept = keepBefore(all, turn);
            runtime?.context?.clear?.();
            runtime?.context?.pushAll?.(kept);

            // Put the files back too. Rewinding the conversation alone left
            // the working tree exactly as the agent had left it, so "go back
            // to before I asked for that" restored the words and none of the
            // edits — the half that actually matters.
            const undo = restoreSince(turn.index);
            const changed = undo.restored.length + undo.deleted.length;
            const fileNote = changed === 0
              ? "No files were changed after that point."
              : `${undo.restored.length} file(s) restored` +
                (undo.deleted.length ? `, ${undo.deleted.length} created file(s) removed` : "") + ".";
            const failNote = undo.failed.length
              ? ` ${undo.failed.length} could not be written back: ${undo.failed.map((f) => f.reason).join("; ")}`
              : "";

            say("system", `Rewound — ${kept.length} message(s) kept. ${fileNote}${failNote} The message is back in the box to edit.`);
            // Handed back for editing, which is the point of going back: the
            // instruction was nearly right and wants changing, not retyping.
            setPrefill(turn.content);
          }}
        />
      )}

      {ctrlCCount > 0 && (
        <Box paddingX={1}>
          <Text color="yellow">Press Ctrl+C again to exit</Text>
        </Box>
      )}

      {/* An attached image is invisible otherwise — it is not in the box and
          not in the transcript, so nothing would say it is about to be sent. */}
      {pendingImage && (
        <Box paddingX={1}>
          <Text color={getInkTheme().accent}>
            {getGlyphs().clip} image attached {getGlyphs().sep}{" "}
            <Text color={getInkTheme().muted} dimColor>sent with your next message</Text>
          </Text>
        </Box>
      )}

      {/* What is waiting to be sent, so a queued message is not invisible. */}
      {queued.length > 0 && (
        <Box flexDirection="column" paddingX={1}>
          {queued.map((q, i) => (
            <Text key={i} dimColor>
              {"> "}{q.length > 70 ? `${q.slice(0, 67)}…` : q}
            </Text>
          ))}
        </Box>
      )}

      <InputPrompt
        onSubmit={handleSubmit}
        // Both of these own the keyboard while they are up; a live text input
        // underneath would swallow the arrow keys they navigate with.
        disabled={pending !== null || rewinding !== null || question !== null}
        onOverlayChange={setPaletteOpen}
        prefill={prefill}
        onPrefillConsumed={clearPrefill}
      />

      {/* Status sits BELOW the prompt, the way claude-code does it: the
          input stays at a fixed spot near the bottom instead of being pushed
          around by a bar that changes width as tokens tick up. */}
      <StatusBar
        model={activeModel}
        servedModel={servedModel}
        agent={agent}
        tokenCount={tokenCount}
        creditBalance={creditBalance}
        phase={phase}
        mode={mode}
        contextPercent={contextPercent}
        streamingTokens={Math.round(streamedChars / 4)}
        elapsedSec={elapsedSec}
        planMode={planMode}
        permMode={permMode}
        tangentMode={tangentMode}
        queuedCount={queuedCount}
      />

      {/* Hint under the status line, the way claude-code hangs one there. */}
      {/* Always one row, occupied or not. Appearing only while busy made the
          whole layout shift by a row at the start and end of every turn. */}
      <Box paddingX={1} height={1}>
        {busy ? (
          <Text color="gray" dimColor>
            {getGlyphs().elbowCont.trimEnd()} Tip: {activityTip(elapsedSec)}
          </Text>
        ) : (
          <Text> </Text>
        )}
      </Box>
    </Box>
  );
}
