/**
 * `ask_user` — a question with real options.
 *
 * The agent could only ask in prose and hope the answer came back in a shape
 * it could act on. So it guessed — picking Python for "write a program" with
 * no language named, and learning three turns later that Java was wanted — or
 * it stopped and wrote a paragraph of alternatives that then had to be
 * answered in prose and re-interpreted.
 */
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import React from "react";
import { render } from "ink";
import { PassThrough } from "node:stream";
import { setGlyphs } from "../../src/ui/ink/glyphs.js";
import { setInkTheme } from "../../src/ui/ink/theme.js";
import { QuestionPrompt } from "../../src/ui/ink/QuestionPrompt.js";
import { askUser, setQuestionAsker } from "../../src/tools/agent/ask-user.js";

const ESC = String.fromCharCode(27);
const UP = `${ESC}[A`;
const DOWN = `${ESC}[B`;
const ENTER = "\r";
const SPACE = " ";
const strip = (s: string) => s.replace(new RegExp(`${ESC}\\[[0-9;?]*[A-Za-z]`, "g"), "");

let unmount: (() => void) | undefined;
beforeEach(() => { setGlyphs("unicode"); setInkTheme("dark"); });
afterEach(() => { unmount?.(); unmount = undefined; setQuestionAsker(null); setGlyphs("ascii"); });

const OPTIONS = [
  { label: "Python", description: "Shortest to write" },
  { label: "Java", description: "Matches this folder" },
  { label: "C++", description: "For a DSA assignment" },
];

async function mount(multiSelect = false) {
  const stdin: any = new PassThrough();
  stdin.isTTY = true; stdin.setRawMode = () => stdin; stdin.ref = () => stdin; stdin.unref = () => stdin;
  const stdout: any = new PassThrough();
  stdout.isTTY = true; stdout.columns = 78; stdout.rows = 24;
  let last = "";
  stdout.on("data", (c: Buffer) => { const s = c.toString(); if (strip(s).trim()) last = s; });

  const answers: Array<string[] | null> = [];
  const app = render(
    <QuestionPrompt
      question={{ header: "Language", question: "Which language?", options: OPTIONS, multiSelect }}
      onAnswer={(a) => answers.push(a)} />,
    { stdout, stdin, patchConsole: false },
  );
  unmount = () => app.unmount();
  await new Promise((r) => setTimeout(r, 60));
  return {
    frame: () => strip(last),
    press: async (s: string) => { stdin.write(s); await new Promise((r) => setTimeout(r, 60)); },
    answers,
  };
}

describe("what it shows", () => {
  it("asks the question with its header", async () => {
    const h = await mount();
    expect(h.frame()).toContain("Language");
    expect(h.frame()).toContain("Which language?");
  });

  it("explains what each option means", async () => {
    // The label alone rarely says why you would pick it.
    const h = await mount();
    expect(h.frame()).toContain("Shortest to write");
    expect(h.frame()).toContain("Matches this folder");
  });

  it("starts on the first option without having chosen it", async () => {
    const h = await mount();
    expect(h.frame()).toContain("❯ 1. Python");
    expect(h.answers).toHaveLength(0);
  });
});

describe("answering", () => {
  it("returns the option chosen with enter", async () => {
    const h = await mount();
    await h.press(DOWN);
    await h.press(ENTER);
    expect(h.answers).toEqual([["Java"]]);
  });

  it("takes a number as choose-and-answer", async () => {
    const h = await mount();
    await h.press("3");
    expect(h.answers).toEqual([["C++"]]);
  });

  it("wraps at the ends of the list", async () => {
    const h = await mount();
    await h.press(UP);
    expect(h.frame()).toContain("❯ 3. C++");
  });

  it("hands the decision back on escape rather than picking for you", async () => {
    // Dismissing is not the same as choosing option one.
    const h = await mount();
    await h.press(ESC);
    expect(h.answers).toEqual([null]);
  });
});

describe("choosing several", () => {
  it("toggles with space and confirms with enter", async () => {
    const h = await mount(true);
    await h.press(SPACE);
    await h.press(DOWN);
    await h.press(SPACE);
    await h.press(ENTER);
    expect(h.answers).toEqual([["Python", "Java"]]);
  });

  it("returns them in list order, not the order they were ticked", async () => {
    const h = await mount(true);
    await h.press(DOWN); await h.press(DOWN); await h.press(SPACE);   // C++
    await h.press(UP); await h.press(UP); await h.press(SPACE);       // Python
    await h.press(ENTER);
    expect(h.answers).toEqual([["Python", "C++"]]);
  });

  it("takes the row under the cursor when nothing was ticked", async () => {
    // Enter should do something sensible rather than nothing.
    const h = await mount(true);
    await h.press(DOWN);
    await h.press(ENTER);
    expect(h.answers).toEqual([["Java"]]);
  });
});

describe("the tool itself", () => {
  it("reports the chosen label back to the model", async () => {
    setQuestionAsker(async () => ["Java"]);
    const r = await askUser({ question: "Which?", options: OPTIONS });
    expect(r.content).toContain("Java");
    expect(r.isError).toBe(false);
  });

  it("refuses a question with fewer than two options", async () => {
    // With one answer there is no question to ask.
    const r = await askUser({ question: "Which?", options: [{ label: "only" }] });
    expect(r.isError).toBe(true);
    expect(r.content).toMatch(/two options/);
  });

  it("tells the model to decide when nobody can be asked", async () => {
    // Headless. Blocking forever, or silently returning the first option as
    // though it had been chosen, are both worse than saying so.
    setQuestionAsker(null);
    const r = await askUser({ question: "Which?", options: OPTIONS });
    expect(r.isError).toBe(false);
    expect(r.content).toMatch(/not interactive/i);
    expect(r.content).toMatch(/say which you chose/i);
  });

  it("tells the model to decide when the question is dismissed", async () => {
    setQuestionAsker(async () => null);
    const r = await askUser({ question: "Which?", options: OPTIONS });
    expect(r.isError).toBe(false);
    expect(r.content).toMatch(/best judgement/i);
  });

  it("reports several choices when more than one was picked", async () => {
    setQuestionAsker(async () => ["Python", "Java"]);
    const r = await askUser({ question: "Which?", options: OPTIONS, multiSelect: true });
    expect(r.content).toContain("Python, Java");
  });
});
