/**
 * The approval prompt.
 *
 * It used to say `apply_patch needs approval` over a dump of the raw arguments
 * and answer on a single keypress. That asks the user to approve a function
 * call rather than an action, shows the change as JSON, and commits on a key
 * that could be a stray one. These cover what the prompt claims, what it
 * actually grants, and what the keys do.
 */
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs } from "../../src/ui/ink/glyphs.js";
import { setInkTheme } from "../../src/ui/ink/theme.js";
import { PermissionPrompt, type PermissionChoice } from "../../src/ui/ink/PermissionPrompt.js";
import { permissionCopy, programOf, alwaysAllowKey } from "../../src/ui/ink/permission-copy.js";

const ESC = String.fromCharCode(27);

/** Key sequences, spelled out — raw control bytes in source are invisible. */
const UP = `${ESC}[A`;
const DOWN = `${ESC}[B`;
const ENTER = "\r";
const ESCAPE = ESC;
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => { setGlyphs("unicode"); setInkTheme("dark"); });
afterEach(() => { unmount?.(); unmount = undefined; setGlyphs("ascii"); });

interface Harness {
  frame: () => string;
  press: (s: string) => Promise<void>;
  decisions: PermissionChoice[];
}

async function mount(toolName: string, input: Record<string, unknown>): Promise<Harness> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = 88; stdout.rows = 50;
  let last = "";
  stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });

  const decisions: PermissionChoice[] = [];
  const app = render(
    <PermissionPrompt pending={{ toolName, input }} onDecide={(c) => decisions.push(c)} />,
    { stdout, stdin, patchConsole: false },
  );
  unmount = () => app.unmount();
  await new Promise((r) => setTimeout(r, 60));

  return {
    frame: () => strip(last),
    press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 60)); },
    decisions,
  };
}

describe("what the prompt asks", () => {
  it("names the action, not the tool function", async () => {
    const h = await mount("execute_command", { command: "npm run build" });
    expect(h.frame()).toContain("Run command");
    expect(h.frame()).toContain("Do you want to run this command?");
    expect(h.frame()).not.toContain("execute_command");
  });

  it("shows an edit as a diff, not as two opaque strings", async () => {
    const h = await mount("edit_file", {
      file_path: "src/server.ts",
      old_string: "const port = 3000;",
      new_string: "const port = Number(process.env.PORT);",
    });
    const f = h.frame();
    expect(f).toContain("Edit file");
    expect(f).toContain("- const port = 3000;");
    expect(f).toContain("+ const port = Number(process.env.PORT);");
    expect(f).toContain("server.ts");
  });

  it("shows a new file as additions", async () => {
    const h = await mount("write_file", { file_path: "src/a.ts", content: "export const a = 1;" });
    expect(h.frame()).toContain("Create file");
    expect(h.frame()).toContain("+ export const a = 1;");
  });

  it("says out loud that publishing leaves the machine", async () => {
    const h = await mount("github_issue", { action: "create", repo: "acme/app", title: "Bug" });
    expect(h.frame()).toContain("This posts to GitHub.");
  });

  it("still asks about a tool it has no specific wording for", async () => {
    const copy = permissionCopy("some_new_tool", { thing: "value" });
    expect(copy.question).toContain("some_new_tool");
    expect(copy.preview.kind).toBe("lines");
  });
});

describe("what 'don't ask again' grants", () => {
  it("is scoped to the program the prompt showed", async () => {
    // The label says "allow npm". Keyed on the tool name it also allowed
    // `rm -rf`, since both arrive as execute_command.
    const npm = alwaysAllowKey("execute_command", { command: "npm test" });
    const rm = alwaysAllowKey("execute_command", { command: "rm -rf /" });
    expect(npm).not.toBe(rm);
  });

  it("grants the same key for the same program", () => {
    expect(alwaysAllowKey("execute_command", { command: "npm test" }))
      .toBe(alwaysAllowKey("execute_command", { command: "npm run build" }));
  });

  it("names that program in the label", () => {
    expect(permissionCopy("execute_command", { command: "npm test" }).alwaysLabel).toContain("npm");
  });

  it("does not grant a blanket allow when no program is identifiable", () => {
    expect(alwaysAllowKey("execute_command", {})).not.toBe(alwaysAllowKey("execute_command", { command: "ls" }));
  });

  it("reads through a path and leading environment assignments", () => {
    expect(programOf("/usr/bin/npm test")).toBe("npm");
    expect(programOf("NODE_ENV=test npm run build")).toBe("npm");
  });

  it("keeps other tools keyed on their own name", () => {
    expect(alwaysAllowKey("edit_file", { file_path: "a.ts" })).toBe("edit_file");
  });
});

describe("answering it", () => {
  it("starts on Yes without having chosen it", async () => {
    const h = await mount("execute_command", { command: "ls" });
    expect(h.frame()).toContain("❯ 1. Yes");
    expect(h.decisions, "nothing decided on mount").toHaveLength(0);
  });

  it("commits only on enter, so a stray key does not run the tool", async () => {
    const h = await mount("execute_command", { command: "ls" });
    await h.press(DOWN);
    expect(h.decisions).toHaveLength(0);
    await h.press(ENTER);
    expect(h.decisions).toEqual(["allow_always"]);
  });

  it("moves with the arrow keys and wraps", async () => {
    const h = await mount("execute_command", { command: "ls" });
    await h.press(UP);   // up from the first entry
    expect(h.frame()).toContain("❯ 3.");
  });

  it("takes a number as select-and-answer", async () => {
    const h = await mount("execute_command", { command: "ls" });
    await h.press("3");
    expect(h.decisions).toEqual(["deny"]);
  });

  it("denies on escape wherever the cursor is", async () => {
    const h = await mount("execute_command", { command: "ls" });
    await h.press(DOWN);   // sitting on "yes, always"
    await h.press(ESCAPE);
    expect(h.decisions).toEqual(["deny"]);
  });
});
