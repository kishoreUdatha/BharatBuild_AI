/**
 * What the model is told before it decides anything.
 *
 * The prompt was an inventory of capabilities — "you have tools for
 * reading/writing files… use them" — which says what the model *can* do and
 * nothing about what it *should* do. So it fell back on conversational
 * manners: announcing a plan and waiting, answering from a filename rather
 * than opening the file, calling a change done without running anything.
 *
 * None of that was a missing capability, so none of it is tested by checking
 * that a tool exists. These check the policy is actually stated, and that the
 * facts it is stated alongside are true.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { detectStack } from "../../src/context/stack-detector.js";
import { buildProjectContext, layoutSummary } from "../../src/context/project-context.js";

let dir: string;
const write = (rel: string, body: string) => {
  const full = path.join(dir, rel);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, body);
};
const pkg = (o: unknown) => write("package.json", JSON.stringify(o));

beforeEach(() => { dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-ctx-")); });
afterEach(() => {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

describe("what kind of project this is", () => {
  it("does not call an Ink CLI a react app", () => {
    // The bug this fixes: react is a dependency because Ink renders a terminal
    // UI with it, so a command-line tool was described to the model as a web
    // app — worse than saying nothing.
    pkg({ bin: { tool: "./cli.js" }, dependencies: { react: "^18", ink: "^5" } });
    expect(detectStack(dir).framework).toBe("cli (ink)");
  });

  it("still recognises a real react app", () => {
    // react-dom is the discriminator: it means a browser.
    pkg({ dependencies: { react: "^18", "react-dom": "^18" } });
    expect(detectStack(dir).framework).toBe("react");
  });

  it("prefers next.js over the react underneath it", () => {
    pkg({ dependencies: { next: "^14", react: "^18", "react-dom": "^18" } });
    expect(detectStack(dir).framework).toBe("next.js");
  });

  it("does not call a plain javascript project typescript", () => {
    // Every package.json was reported as typescript, so a JS project was told
    // to write types it has no compiler for.
    pkg({ dependencies: { express: "^4" } });
    expect(detectStack(dir).language).toBe("javascript");
  });

  it("calls it typescript when there is a tsconfig", () => {
    pkg({ dependencies: {} });
    write("tsconfig.json", "{}");
    expect(detectStack(dir).language).toBe("typescript");
  });

  it("reports how to run the tests", () => {
    // Otherwise "verify what you changed" is an instruction with no command.
    pkg({ devDependencies: { vitest: "^1" } });
    const stack = detectStack(dir);
    expect(stack.testFramework).toBe("vitest");
    expect(stack.packageManager).toBe("npm");
  });

  it("survives a malformed package.json", () => {
    write("package.json", "{ not json");
    expect(() => detectStack(dir)).not.toThrow();
  });
});

describe("what the repository looks like", () => {
  beforeEach(() => {
    pkg({ dependencies: {} });
    write("src/a.ts", "x");
    write("src/b.ts", "x");
    write("tests/a.test.ts", "x");
    write("node_modules/pkg/index.js", "x");
    write("dist/out.js", "x");
    write("README.md", "x");
  });

  it("names the directories instead of only counting files", () => {
    // "Total files: 337" tells the model a codebase exists but not what is in
    // it, so its cheapest opening move was to ask rather than to look.
    const layout = layoutSummary(dir);
    expect(layout).toContain("src/");
    expect(layout).toContain("tests/");
  });

  it("leaves out build output and dependencies", () => {
    const layout = layoutSummary(dir);
    expect(layout).not.toContain("node_modules");
    expect(layout).not.toContain("dist");
  });

  it("points at the files that say what the project is", () => {
    expect(layoutSummary(dir)).toContain("README.md");
  });

  it("puts the layout in the prompt addition", () => {
    const ctx = buildProjectContext(dir);
    expect(ctx.systemPromptAddition).toContain("src/");
    expect(ctx.systemPromptAddition).toContain("Working directory:");
  });

  it("does not throw on a directory it cannot read", () => {
    expect(() => layoutSummary(path.join(dir, "nope"))).not.toThrow();
    expect(layoutSummary(path.join(dir, "nope"))).toBe("");
  });
});

describe("the policy the prompt states", () => {
  // Read as source: composing a real runtime needs a model client and network
  // config, and what matters is that the text ships, not how it is assembled.
  const source = fs.readFileSync(
    path.join(process.cwd(), "src/runtime/agent-runtime.ts"), "utf8",
  );

  it("tells the agent to act rather than announce a plan and wait", () => {
    expect(source).toMatch(/do not stop to announce a plan/i);
  });

  it("tells it to read the file rather than answer from the name", () => {
    expect(source).toMatch(/Look before you answer/i);
    expect(source).toMatch(/open it and see/i);
  });

  it("tells it to follow the conventions already in the codebase", () => {
    expect(source).toMatch(/read a\s*\n?\s*neighbouring file/i);
    expect(source).toMatch(/confirming it is already a dependency/i);
  });

  it("tells it to verify before calling something done", () => {
    expect(source).toMatch(/"Done" means you checked/i);
  });

  it("tells it to finish the whole task and say what it left", () => {
    expect(source).toMatch(/Do what was asked, and all of it/i);
  });

  it("tells it to report failures rather than claim success", () => {
    expect(source).toMatch(/Never claim a result you did not observe/i);
  });

  it("keeps the background-server rule that already worked", () => {
    // The one instruction that was already shaped like a decision procedure.
    expect(source).toMatch(/prints "ready" and then fails/i);
  });
});
