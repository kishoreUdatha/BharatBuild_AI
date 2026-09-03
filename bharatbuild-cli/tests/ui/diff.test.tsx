/**
 * File edits reported only "Written 8195 chars to 'index.html'", so a change
 * was invisible to both the user and the model. Tools now emit unified diffs
 * and the UI renders them with a line-number gutter, tinted rows and syntax
 * highlighting.
 */
import { describe, it, expect, afterEach } from "vitest";
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { buildUnifiedDiff, renderFileChange } from "../../src/tools/filesystem/diff.js";
import { DiffView, parseDiff, looksLikeDiff } from "../../src/ui/ink/Diff.js";
import { tokenize, detectLanguage } from "../../src/ui/ink/syntax.js";

const ESC = String.fromCharCode(27);
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
afterEach(() => { unmount?.(); unmount = undefined; });

async function draw(patch: string): Promise<{ plain: string; ansi: string }> {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = 100; stdout.rows = 40;
  let last = "";
  stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });
  const app = render(<DiffView patch={patch} />, { stdin, stdout, exitOnCtrlC: false, patchConsole: false });
  unmount = () => app.unmount();
  await new Promise((r) => setTimeout(r, 250));
  return { plain: strip(last).replace(/[ \t]+$/gm, ""), ansi: last };
}

describe("buildUnifiedDiff", () => {
  it("reports nothing when the content is identical", () => {
    const d = buildUnifiedDiff("a\nb\n", "a\nb\n", "f.ts");
    expect(d).toMatchObject({ added: 0, removed: 0, patch: "" });
  });

  it("counts a one-line replacement", () => {
    const d = buildUnifiedDiff("a\nold\nc\n", "a\nnew\nc\n", "f.ts");
    expect(d.added).toBe(1);
    expect(d.removed).toBe(1);
    expect(d.patch).toContain("-old");
    expect(d.patch).toContain("+new");
  });

  it("treats a new file as all additions", () => {
    const d = buildUnifiedDiff("", "x\ny\n", "f.ts");
    expect(d).toMatchObject({ added: 2, removed: 0 });
  });

  it("treats a deletion as all removals", () => {
    const d = buildUnifiedDiff("x\ny\n", "", "f.ts");
    expect(d).toMatchObject({ added: 0, removed: 2 });
  });

  it("emits a parseable hunk header with real line numbers", () => {
    const before = Array.from({ length: 20 }, (_, i) => `line${i + 1}`).join("\n");
    const after = before.replace("line15", "CHANGED");
    const d = buildUnifiedDiff(before, after, "f.ts");
    expect(d.patch).toMatch(/@@ -\d+,\d+ \+\d+,\d+ @@/);
    // Context only around the change, not the whole file.
    expect(d.patch).not.toContain("line2\n");
  });

  it("bounds the output so a huge edit cannot flood the context", () => {
    const before = Array.from({ length: 400 }, (_, i) => `a${i}`).join("\n");
    const after = Array.from({ length: 400 }, (_, i) => `b${i}`).join("\n");
    const d = buildUnifiedDiff(before, after, "f.ts", { maxLines: 20 });
    expect(d.patch.split("\n").length).toBeLessThan(40);
    expect(d.patch).toContain("truncated");
    // A bound that emits nothing is not a bound, it is a deletion. This
    // assertion was missing, so truncation dropping every content line passed
    // unnoticed — creating any file over the limit showed no diff at all.
    expect(d.patch).toContain("-a0");
  });

  it("shows what fits when a single hunk is larger than the budget", () => {
    // A newly created file is one hunk. The check was per-hunk and
    // all-or-nothing, so a 90-line create against an 80-line budget emitted a
    // header, a footer, and nothing in between — at which point the UI stopped
    // recognising it as a diff and rendered it as plain text.
    const created = Array.from({ length: 90 }, (_, i) => `line ${i + 1};`).join("\n");
    const d = buildUnifiedDiff("", created, "Big.java", { maxLines: 80 });

    expect(d.added).toBe(90);
    expect(d.patch).toContain("+line 1;");
    expect(d.patch).toContain("+line 80;");
    expect(d.patch).not.toContain("+line 81;");
    expect(d.patch).toContain("truncated");
    expect(looksLikeDiff(d.patch)).toBe(true);
  });

  it("handles CRLF without reporting every line as changed", () => {
    const d = buildUnifiedDiff("a\r\nb\r\n", "a\nb\n", "f.ts");
    expect(d).toMatchObject({ added: 0, removed: 0 });
  });
});

describe("renderFileChange", () => {
  it("labels a creation", () => {
    const out = renderFileChange("Create", "src/a.ts", buildUnifiedDiff("", "x\n", "src/a.ts"));
    expect(out).toContain("Create(src/a.ts)");
    expect(out).toContain("Added 1 line");
  });

  it("labels an update with both counts", () => {
    const out = renderFileChange("Update", "src/a.ts", buildUnifiedDiff("a\nb\n", "a\nc\nd\n", "src/a.ts"));
    expect(out).toContain("Update(src/a.ts)");
    expect(out).toMatch(/Added \d+ lines?, removed \d+ lines?/);
  });

  it("labels a deletion", () => {
    const out = renderFileChange("Delete", "src/a.ts", buildUnifiedDiff("a\nb\n", "", "src/a.ts"));
    expect(out).toContain("Delete(src/a.ts)");
    expect(out).toContain("Removed 2 lines");
  });
});

describe("diff detection and parsing", () => {
  const patch = ["--- a/src/app.ts", "+++ b/src/app.ts", "@@ -10,3 +10,4 @@",
    " const keep = 1;", "-const old = 1;", "+const shiny = 2;", "+const extra = 3;"].join("\n");

  it("recognises a unified diff", () => {
    expect(looksLikeDiff(patch)).toBe(true);
    expect(looksLikeDiff("Written 8195 chars to 'index.html'")).toBe(false);
  });

  it("numbers lines from the hunk header, not from the diff index", () => {
    const { rows } = parseDiff(patch);
    const add = rows.filter((r) => r.kind === "add");
    expect(add[0]!.lineNo).toBe(11);
    expect(add[1]!.lineNo).toBe(12);
  });

  it("extracts the file path", () => {
    expect(parseDiff(patch).filePath).toBe("src/app.ts");
  });
});

describe("DiffView rendering", () => {
  const patch = ["--- a/src/app.ts", "+++ b/src/app.ts", "@@ -10,3 +10,4 @@",
    " const keep = 1;", '-const old = "gone";', '+const shiny = "new";'].join("\n");

  it("shows a line-number gutter with +/- markers", async () => {
    const { plain } = await draw(patch);
    expect(plain).toMatch(/10\s+const keep/);
    expect(plain).toMatch(/11 - const old/);
    expect(plain).toMatch(/11 \+ const shiny/);
  });

  it("hides the hunk header once lines are numbered", async () => {
    const { plain } = await draw(patch);
    expect(plain).not.toContain("@@");
  });

  it("tints added and removed rows with distinct backgrounds", async () => {
    // Colour is the whole point of the request; assert the codes, not a look.
    const { ansi } = await draw(patch);
    const backgrounds = new Set(ansi.match(/\[48;2;\d+;\d+;\d+m/g) ?? []);
    expect(backgrounds.size).toBeGreaterThanOrEqual(2);
  });

  it("tints the whole row, not just the text", async () => {
    // The background only covers the cells a span occupies, so without padding
    // the green stopped at the last character of the code and the rest of the
    // row kept the terminal colour - the tint read as a ragged blob, not a band.
    // A mixed hunk: an all-addition patch is a file creation, and those are
    // left untinted on purpose, so one can no longer carry this assertion.
    const short = ["--- a/f.ts", "+++ b/f.ts", "@@ -1,3 +1,3 @@",
      "-const gone = 0;", "+const a = 1;", "+", "+const somewhat_longer_line = 2;"].join("\n");
    const { ansi } = await draw(short);

    const bgSpan = new RegExp(`${ESC}\\[48;2;\\d+;\\d+;\\d+m([\\s\\S]*?)(?:${ESC}\\[49m|$)`);
    const anyCode = new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g");
    const widths: number[] = [];
    for (const line of ansi.split("\n")) {
      const m = line.match(bgSpan);
      if (!m) continue;
      widths.push(m[1]!.replace(anyCode, "").length);
    }
    expect(widths.length).toBeGreaterThanOrEqual(3);
    // Every tinted row is the same width, including the blank one.
    expect(new Set(widths).size).toBe(1);
    expect(widths[0]).toBeGreaterThan(30);
  });

  it("keeps a long line on a single row", async () => {
    // A wrapped line would leave its overflow untinted below the band.
    // Mixed for the same reason: the tint is what a wrapped line would break,
    // so the case has to be one that is actually tinted.
    const long = ["--- a/f.ts", "+++ b/f.ts", "@@ -1,1 +1,1 @@",
      "-const x = 1;", "+const x = " + "y".repeat(400) + ";"].join("\n");
    const { plain } = await draw(long);
    const codeRows = plain.split("\n").filter((l) => /^\s*\d+\s+\+/.test(l));
    expect(codeRows).toHaveLength(1);
  });

  it("truncates a long diff rather than flooding the pane", async () => {
    const body = Array.from({ length: 80 }, (_, i) => `+line ${i}`).join("\n");
    const { plain } = await draw(["--- a/f.ts", "+++ b/f.ts", "@@ -1,0 +1,80 @@", body].join("\n"));
    expect(plain).toMatch(/more diff lines/);
  });
});

describe("syntax highlighting", () => {
  it("resolves Shiki language ids from a path", () => {
    expect(detectLanguage("src/a.tsx")).toBe("tsx");
    expect(detectLanguage("main.py")).toBe("python");
    expect(detectLanguage("data.json")).toBe("json");
    expect(detectLanguage("notes.txt")).toBe("plain");
  });

  it("covers languages beyond the pre-warmed set", () => {
    // Detection used to know six languages, so a Rust or Go file came back as
    // "plain" and the lazy-loading path was never exercised for it.
    const cases: Array<[string, string]> = [
      ["main.rs", "rust"], ["main.go", "go"], ["A.java", "java"],
      ["a.rb", "ruby"], ["a.php", "php"], ["a.cs", "csharp"],
      ["a.cpp", "cpp"], ["a.h", "c"], ["a.swift", "swift"],
      ["a.kt", "kotlin"], ["q.sql", "sql"], ["c.yml", "yaml"],
      ["README.md", "markdown"], ["Dockerfile", "docker"],
      ["main.tf", "terraform"], ["a.ex", "elixir"], ["a.hs", "haskell"],
    ];
    for (const [file, lang] of cases) {
      expect(detectLanguage(file), file).toBe(lang);
    }
  });

  it("accepts a bare fence hint", () => {
    expect(detectLanguage(undefined, "rust")).toBe("rust");
    expect(detectLanguage(undefined, "ts")).toBe("typescript");
    expect(detectLanguage(undefined, "nonsense")).toBe("plain");
  });

  it("marks keywords and strings separately", () => {
    const spans = tokenize('const name = "hello";', "typescript");
    expect(spans.find((s) => s.text === "const")?.kind).toBe("keyword");
    expect(spans.find((s) => s.text === '"hello"')?.kind).toBe("string");
  });

  it("treats a whole comment line as a comment", () => {
    expect(tokenize("// not a const keyword here", "typescript")).toEqual([
      { text: "// not a const keyword here", kind: "comment" },
    ]);
  });

  it("does not highlight keywords inside a string", () => {
    const spans = tokenize('const s = "import from";', "typescript");
    const inString = spans.find((s) => s.text === '"import from"');
    expect(inString?.kind).toBe("string");
  });

  it("leaves plain text alone", () => {
    expect(tokenize("just some words", "plain")).toEqual([{ text: "just some words", kind: "plain" }]);
  });
});

describe("a newly created file", () => {
  const created = ["--- a/new.ts", "+++ b/new.ts", "@@ -0,0 +1,3 @@",
    "+const a = 1;", "+const b = 2;", "+export { a, b };"].join("\n");

  it("is not tinted", async () => {
    // Every line is an addition, so tinting each row turns the block into a
    // solid green wall — the colour distinguishes nothing, because there is
    // nothing here that is not new.
    const { ansi } = await draw(created);
    expect(ansi.match(/\[48;2;\d+;\d+;\d+m/g) ?? []).toHaveLength(0);
  });

  it("still shows the + markers and line numbers", async () => {
    // Those carry the "this is all new" information the tint was carrying.
    const { plain } = await draw(created);
    expect(plain).toMatch(/1 \+ const a/);
    expect(plain).toMatch(/3 \+ export/);
  });

  it("leaves an edit tinted", async () => {
    // A mixed hunk is exactly where the colour earns its place.
    const edit = ["--- a/x.ts", "+++ b/x.ts", "@@ -1,2 +1,2 @@",
      " const keep = 1;", "-const old = 2;", "+const shiny = 3;"].join("\n");
    const { ansi } = await draw(edit);
    const backgrounds = new Set(ansi.match(/\[48;2;\d+;\d+;\d+m/g) ?? []);
    expect(backgrounds.size).toBeGreaterThanOrEqual(2);
  });

  it("tints a wholesale deletion", async () => {
    // All-removals is not the same case: red there is a warning, not decoration.
    const deleted = ["--- a/gone.ts", "+++ b/gone.ts", "@@ -1,2 +0,0 @@",
      "-const a = 1;", "-const b = 2;"].join("\n");
    const { ansi } = await draw(deleted);
    expect((ansi.match(/\[48;2;\d+;\d+;\d+m/g) ?? []).length).toBeGreaterThan(0);
  });
});
