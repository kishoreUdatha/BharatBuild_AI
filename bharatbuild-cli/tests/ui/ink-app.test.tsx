import { describe, it, expect, afterEach } from "vitest";
import { mountApp, makeRuntime, keys, type Harness } from "../helpers/ink-harness.js";
import { takeDenyReason } from "../../src/permissions/deny-reason.js";
import { checkPermission } from "../../src/permissions/permission-manager.js";
import { getGlyphs } from "../../src/ui/ink/glyphs.js";

let h: Harness | undefined;
afterEach(() => { h?.unmount(); h = undefined; });

describe("opening screen", () => {
  it("advertises the command palette instead of an empty pane", async () => {
    // An empty "Start typing…" screen is why /model got typed as a chat message.
    h = await mountApp({ runtime: makeRuntime() });
    // The welcome panel is printed into <Static> now, so it lives in the
    // scrollback rather than the repainted frame. It used to render live and
    // only while the transcript was empty, which meant it vanished the
    // moment the first message arrived.
    expect(h.output()).toContain("/ commands");
    expect(h.output()).toContain("Tab complete");
    // The working directory is shown so a session started in the wrong folder
    // is obvious before the agent writes anything.
    expect(h.output()).toContain(process.cwd());
  });

  it("shows model, agent and mode in the status bar", async () => {
    h = await mountApp({ runtime: makeRuntime(), model: "sonnet", mode: "developer" });
    // Model and agent are in the status bar, which stays live.
    expect(h.frame()).toContain("sonnet");
    expect(h.frame()).toContain("default");
    // The platform mode is shown in the welcome panel, which is now static.
    expect(h.output()).toContain("developer");
  });
});

describe("command palette", () => {
  it("opens on / and lists commands in two aligned columns", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/");
    const f = h.frame();
    expect(f).toContain("/help");
    expect(f).toContain("Show available commands");
    // Descriptions share a column, so their start offset is identical.
    const rows = f.split("\n").filter((l) => /^\s*\/\w[\w-]*\s{2,}\S/.test(l));
    expect(rows.length).toBeGreaterThan(2);
    const offsets = new Set(rows.map((l) => l.search(/\s{2,}\S/) + l.match(/\s{2,}/)![0].length));
    expect(offsets.size).toBe(1);
  });

  it("closes on Esc", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/");
    await h.press(keys.esc);
    expect(h.frame()).not.toContain("/ Commands");
  });

  it("narrows by fuzzy subsequence", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/ckp");
    expect(h.frame()).toContain("/checkpoint");
  });

  it("renders each row on one line without wrapping the name", async () => {
    // A hard-coded width once split "/checkpoint" into "/checkpoi" + "nt".
    h = await mountApp({ runtime: makeRuntime(), columns: 120 });
    await h.type("/ckp");
    expect(h.frame()).not.toMatch(/\/checkpoi\s*\n/);
  });

  it("completes on Tab", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/ckp");
    await h.press(keys.tab);
    expect(h.frame()).toContain("/checkpoint");
  });

  it("keeps the caret at the end after Tab completion", async () => {
    // ink-text-input does not move its caret when the value is set externally;
    // typing after Tab used to land mid-word ("/usageckpoint").
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/ckp");
    await h.press(keys.tab);
    await h.type("list");
    expect(h.frame()).toContain("/checkpoint list");
  });

  it("shows the signature hint once arguments are being typed", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/model ");
    expect(h.frame()).toContain("Show or set the active model");
  });
});

describe("slash dispatch", () => {
  it("runs a command locally without calling the model", async () => {
    // Every slash command used to be forwarded to the LLM as chat text.
    const runtime = makeRuntime();
    h = await mountApp({ runtime });
    await h.type("/usage");
    await h.press(keys.enter);
    await h.wait(400);
    expect(runtime.calls).toHaveLength(0);
    expect(h.output()).toContain("1,234 tokens");
  });

  it("submits exactly once per Enter", async () => {
    // The overlay and the text input both claimed Enter, doubling every command.
    const runtime = makeRuntime();
    h = await mountApp({ runtime });
    await h.type("/context");
    await h.press(keys.enter);
    await h.wait(400);
    const shown = (h.output().match(/Messages:/g) ?? []).length;
    expect(shown).toBe(1);
  });

  it("reports an unknown command rather than staying silent", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/definitelynotreal");
    await h.press(keys.enter);
    await h.wait(400);
    expect(h.output()).toContain("Unknown command");
  });

  it("clears the transcript on /clear", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/usage");
    await h.press(keys.enter);
    await h.wait(300);
    await h.clearInput();
    await h.type("/clear");
    await h.press(keys.enter);
    await h.wait(300);
    // The prompt survives the wipe; the banner is reprinted to scrollback.
    expect(h.frame()).toContain("Type a message");
  });

  it("updates the status bar when the model changes", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/model opus");
    await h.press(keys.enter);
    await h.wait(400);
    expect(h.frame()).toContain("opus");
  });

  it("shows PLAN in the status bar when plan mode is on", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("/plan");
    await h.press(keys.enter);
    await h.wait(400);
    expect(h.frame()).toContain("PLAN");
  });
});

describe("agent turns", () => {
  it("sends a plain prompt to the runtime exactly once", async () => {
    const runtime = makeRuntime();
    h = await mountApp({ runtime });
    await h.type("build a landing page");
    await h.press(keys.enter);
    await h.wait(900);
    expect(runtime.calls).toEqual(["build a landing page"]);
  });

  it("renders the streamed reply", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("build a landing page");
    await h.press(keys.enter);
    await h.wait(900);
    expect(h.output()).toContain("done building");
  });

  it("shows tool calls with their argument and duration", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    await h.type("build it");
    await h.press(keys.enter);
    await h.wait(900);
    // A finished tool call is committed to scrollback, not repainted.
    const f = h.output();
    expect(f).toContain("write_file");
    expect(f).toContain("src/app.tsx");
    expect(f).toContain("12ms");
  });

  it("registers exactly one runtime listener no matter how many turns run", async () => {
    // The subscription used to be created inside the submit handler, so turn N
    // replayed every chunk N times.
    const runtime = makeRuntime();
    h = await mountApp({ runtime });
    for (const p of ["one", "two", "three"]) {
      await h.clearInput();
      await h.type(p);
      await h.press(keys.enter);
      await h.wait(700);
    }
    expect(runtime.events.h["*"]).toHaveLength(1);
    expect(runtime.calls).toHaveLength(3);
  });

  it("does not accumulate the stream buffer across turns", async () => {
    const runtime = makeRuntime();
    h = await mountApp({ runtime });
    await h.type("first");
    await h.press(keys.enter);
    await h.wait(800);
    await h.clearInput();
    await h.type("second");
    await h.press(keys.enter);
    await h.wait(800);
    expect(h.output()).not.toContain("done buildingdone building");
  });

  it("surfaces runtime errors instead of dropping them", async () => {
    // `error` events were not handled, so a failed turn looked like silence.
    const runtime = makeRuntime({
      async run(this: any) {
        await runtime.events.emit({
          type: "error", message: "model refused", retryable: false, timestamp: 1,
        });
      },
    });
    h = await mountApp({ runtime });
    await h.type("do something");
    await h.press(keys.enter);
    await h.wait(700);
    expect(h.output()).toContain("model refused");
  });

  it("recovers to idle after a rejected run", async () => {
    const runtime = makeRuntime({ async run() { throw new Error("boom"); } });
    h = await mountApp({ runtime });
    await h.type("do something");
    await h.press(keys.enter);
    await h.wait(700);
    expect(h.output()).toContain("boom");
    expect(h.frame()).toContain("idle");
  });
});

describe("tool approval", () => {
  // The App installs itself as the permission asker on mount, so the agent
  // loop's gate routes through the TUI instead of an invisible readline
  // prompt that ink paints over (which denied every call).
  const askFor = (name: string, input: Record<string, unknown>) =>
    checkPermission(name, input, { permissionMode: "ask", nonInteractive: true } as any);

  // The prompt answers on 1/2/3 (or arrows plus enter, or esc), the way
  // claude-code does. It used to answer on a bare y/a/n, which committed the
  // decision on a single keystroke that could easily be a stray one.
  const YES = "1";
  const ALWAYS = "2";
  const NO = "3";

  it("shows a prompt describing the pending call", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    const decision = askFor("write_file", { path: "src/app.tsx", content: "hello" });
    await h.wait(300);
    const f = h.frame();
    // It asks about the action, naming the file — not about the function.
    expect(f).toContain("Do you want to");
    expect(f).toContain("app.tsx");
    await h.press(NO);
    await decision;
  });

  it("allows the call when the user takes the first option", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    const decision = askFor("write_file", { path: "a.txt" });
    await h.wait(300);
    await h.press(YES);
    await expect(decision).resolves.toBe("allow");
  });

  it("denies the call when the user takes the last option", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    const decision = askFor("shell", { command: "rm -rf /" });
    await h.wait(300);
    await h.press(NO);
    await expect(decision).resolves.toBe("deny");
  });

  it("stops asking for a tool after 'always allow'", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    const first = askFor("write_file", { path: "a.txt" });
    await h.wait(300);
    await h.press(ALWAYS);
    await expect(first).resolves.toBe("allow");

    // Second call for the same tool must resolve without a prompt.
    await expect(askFor("write_file", { path: "b.txt" })).resolves.toBe("allow");
    await h.wait(200);
    expect(h.frame()).not.toContain("Do you want to");
  });

  it("does not carry a shell approval across to a different program", async () => {
    // The option says "allow npm for the rest of this session". Keyed on the
    // tool name it also allowed rm, because both arrive as the same tool.
    h = await mountApp({ runtime: makeRuntime() });
    const first = askFor("shell", { command: "npm test" });
    await h.wait(300);
    await h.press(ALWAYS);
    await expect(first).resolves.toBe("allow");

    // Same program: no prompt.
    await expect(askFor("shell", { command: "npm run build" })).resolves.toBe("allow");

    // Different program: must ask again.
    const other = askFor("shell", { command: "rm -rf /" });
    await h.wait(300);
    expect(h.frame()).toContain("Do you want to run this command?");
    await h.press(NO);
    await expect(other).resolves.toBe("deny");
  });

  it("previews the content a write would create", async () => {
    h = await mountApp({ runtime: makeRuntime() });
    const decision = askFor("write_file", { path: "a.txt", content: "line one\nline two" });
    await h.wait(300);
    expect(h.frame()).toContain("line one");
    await h.press(NO);
    await decision;
  });
});

describe("scrollback is preserved", () => {
  it("keeps earlier conversation after a screen-filling command", async () => {
    // Reported bug: running /code or /help wiped the chat above it, because
    // the whole app repainted one fixed-height region.
    h = await mountApp({ runtime: makeRuntime(), rows: 20, columns: 100 });
    await h.type("remember this first message");
    await h.press(keys.enter);
    await h.wait(800);

    await h.clearInput();
    await h.type("/help");
    await h.press(keys.enter);
    await h.wait(600);

    const out = h.output();
    expect(out).toContain("remember this first message");
    expect(out).toContain("done building");
    expect(out).toContain("/checkpoint");
  });

  it("keeps every turn of a multi-turn session", async () => {
    h = await mountApp({ runtime: makeRuntime(), rows: 16, columns: 90 });
    for (const p of ["alpha turn", "bravo turn", "charlie turn", "delta turn"]) {
      await h.clearInput();
      await h.type(p);
      await h.press(keys.enter);
      await h.wait(700);
    }
    const out = h.output();
    for (const p of ["alpha turn", "bravo turn", "charlie turn", "delta turn"]) {
      expect(out, `"${p}" fell out of scrollback`).toContain(p);
    }
  });

  it("does not reprint committed output on later frames", async () => {
    // <Static> must print history once. If it reprinted every frame the
    // scrollback would fill with duplicates and grow without bound.
    h = await mountApp({ runtime: makeRuntime(), rows: 20, columns: 100 });
    await h.type("unique marker phrase");
    await h.press(keys.enter);
    await h.wait(900);

    const count = () => (h!.output().match(/unique marker phrase/g) ?? []).length;
    const settled = count();

    // Force many repaints of the live region without mentioning the phrase.
    await h.type("zzz");
    await h.wait(300);
    await h.clearInput();
    await h.wait(300);

    expect(count()).toBe(settled);
  });
});

describe("layout safety", () => {
  it("never paints more rows than the terminal has", async () => {
    // Overflow does not scroll — it corrupts the frame ("permissionsndow").
    const rows = 30;
    h = await mountApp({ runtime: makeRuntime(), rows, columns: 110 });
    await h.type("/help");
    await h.press(keys.enter);
    await h.wait(500);
    const lines = h.frame().replace(/\n+$/, "").split("\n");
    expect(lines.length).toBeLessThanOrEqual(rows);
  });

  it("keeps long output in full instead of truncating it", async () => {
    // The reported bug: output taller than the window used to be destroyed.
    // Committed output now goes to real scrollback, so all of it survives.
    h = await mountApp({ runtime: makeRuntime(), rows: 24, columns: 100 });
    await h.type("/help");
    await h.press(keys.enter);
    await h.wait(600);
    const out = h.output();
    expect(out).toContain("/checkpoint");
    expect(out).toContain("Shortcuts");
    expect(out).not.toMatch(/… \d+ more lines/);
  });

  it("keeps the prompt on its own row when the palette is open", async () => {
    h = await mountApp({ runtime: makeRuntime(), rows: 24, columns: 100 });
    await h.type("/");
    const f = h.frame();
    // A collapsed layout used to merge the prompt into a border row.
    expect(f).not.toMatch(/╰─>/);
    // The prompt sits inside its own framed row.
    expect(f).toMatch(/│\s*> \//);
    // And the frame is closed on both sides.
    expect(f).toMatch(/╭─+╮/);
    expect(f).toMatch(/╰─+╯/);
  });

  // "drawn once" lives in bottom-anchor.test.tsx, which replays the escape
  // codes through a virtual terminal. Counting occurrences in the raw stream
  // — which this test used to do — cannot tell a repaint from a duplicate.

  it("renders at a narrow width without wrapping the status bar into itself", async () => {
    h = await mountApp({ runtime: makeRuntime(), columns: 80, rows: 24 });
    expect(h.frame()).not.toMatch(/╰─⚡/);
  });
});

describe("transcript ordering", () => {
  it("commits narration before the tool call it introduces", async () => {
    // Text stayed live until the whole run ended, so every tool card was
    // committed ahead of the text that introduced it — the transcript came out
    // with all the tool cards stacked at the top and the prose below.
    const rt = makeRuntime({
      async run() {
        await rt.events.emit({ type: "text", content: "First I will write the HTML.", delta: true, timestamp: 1 });
        await rt.events.emit({ type: "tool_call", id: "t1", toolName: "write_file", input: { path: "index.html" }, timestamp: 2 });
        await rt.events.emit({ type: "tool_result", id: "t1", toolName: "write_file", output: "ok", isError: false, durationMs: 3, timestamp: 3 });
        await rt.events.emit({ type: "text", content: "Now the CSS.", delta: true, timestamp: 4 });
        await rt.events.emit({ type: "tool_call", id: "t2", toolName: "write_file", input: { path: "styles.css" }, timestamp: 5 });
        await rt.events.emit({ type: "tool_result", id: "t2", toolName: "write_file", output: "ok", isError: false, durationMs: 3, timestamp: 6 });
        await rt.events.emit({ type: "complete", totalTokens: 5, turns: 1, durationMs: 9, inputTokens: 3, outputTokens: 2, timestamp: 7 });
      },
    });
    h = await mountApp({ runtime: rt, columns: 100, rows: 30 });
    await h.type("build a page");
    await h.press(keys.enter);
    await h.wait(1200);

    const out = h.output();
    const posHtmlText = out.indexOf("First I will write the HTML");
    const posHtmlTool = out.indexOf("index.html");
    const posCssText = out.indexOf("Now the CSS");
    const posCssTool = out.indexOf("styles.css");

    expect(posHtmlText).toBeGreaterThan(-1);
    expect(posCssText).toBeGreaterThan(-1);
    expect(posHtmlText).toBeLessThan(posHtmlTool);
    expect(posHtmlTool).toBeLessThan(posCssText);
    expect(posCssText).toBeLessThan(posCssTool);
  });

  it("does not glue separate replies into one paragraph", async () => {
    const rt = makeRuntime({
      async run() {
        await rt.events.emit({ type: "text", content: "Creating the file.", delta: true, timestamp: 1 });
        await rt.events.emit({ type: "tool_call", id: "t1", toolName: "write_file", input: { path: "a" }, timestamp: 2 });
        await rt.events.emit({ type: "tool_result", id: "t1", toolName: "write_file", output: "ok", isError: false, durationMs: 1, timestamp: 3 });
        await rt.events.emit({ type: "text", content: "Done.", delta: true, timestamp: 4 });
        await rt.events.emit({ type: "complete", totalTokens: 1, turns: 1, durationMs: 1, inputTokens: 1, outputTokens: 0, timestamp: 5 });
      },
    });
    h = await mountApp({ runtime: rt, columns: 100, rows: 30 });
    await h.type("go");
    await h.press(keys.enter);
    await h.wait(1200);
    // "Creating the file.Done." was the reported symptom.
    expect(h.output()).not.toContain("Creating the file.Done.");
  });
});

describe("permission modes in the running app", () => {
  // The mode decides whether the agent stops on every write. These drive the
  // real App, so they cover the wiring the pure decideForMode tests cannot:
  // that the asker reads the *current* mode rather than one captured on mount.
  const askFor = (name: string, input: Record<string, unknown>) =>
    checkPermission(name, input, { permissionMode: "ask", nonInteractive: true } as any);

  it("auto-accept runs a write without showing a prompt", async () => {
    h = await mountApp({ runtime: makeRuntime(), initialMode: "auto" });
    await expect(askFor("write_file", { path: "a.txt" })).resolves.toBe("allow");
    expect(h.frame()).not.toContain("needs approval");
  });

  it("auto-accept runs a shell command without showing a prompt", async () => {
    h = await mountApp({ runtime: makeRuntime(), initialMode: "auto" });
    await expect(askFor("shell", { command: "npm test" })).resolves.toBe("allow");
    expect(h.frame()).not.toContain("needs approval");
  });

  it("plan mode refuses a write and says why", async () => {
    h = await mountApp({ runtime: makeRuntime(), initialMode: "plan" });
    await expect(askFor("write_file", { path: "a.txt" })).resolves.toBe("deny");
    // A bare denial reads as a transient failure and the model retries it.
    expect(takeDenyReason()).toMatch(/plan mode/i);
  });

  it("plan mode still allows reading, so it can investigate", async () => {
    h = await mountApp({ runtime: makeRuntime(), initialMode: "plan" });
    await expect(askFor("read_file", { path: "a.txt" })).resolves.toBe("allow");
  });

  it("shift+tab changes the mode the asker actually uses", async () => {
    // The asker is registered once on mount. Reading the mode from captured
    // state would freeze it at startup and every later shift+tab would be
    // ignored, which is the bug that made the cycle look like it did nothing.
    h = await mountApp({ runtime: makeRuntime(), initialMode: "ask" });
    await h.press("[Z");           // ask -> auto
    await h.wait(150);
    await expect(askFor("write_file", { path: "a.txt" })).resolves.toBe("allow");
    expect(h.frame()).not.toContain("needs approval");
  });

  it("shows the active mode in the status bar", async () => {
    h = await mountApp({ runtime: makeRuntime(), initialMode: "auto" });
    await h.wait(150);
    expect(h.frame()).toContain("auto-accept");
  });
});
