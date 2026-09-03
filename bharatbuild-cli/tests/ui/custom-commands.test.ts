/**
 * Slash commands defined by the user, as .toml files.
 *
 * The registry was a fixed list compiled into the binary, so a project could
 * not add a command of its own — every team's repeated prompt had to be
 * retyped or pasted from elsewhere. Custom *agents* already loaded from disk;
 * commands did not, which was an odd place to draw the line.
 *
 * The format follows gemini-cli's so files are portable between the two.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  loadCustomCommands, applyArgs, shellInjections, expandShell,
  commandName, commandDirs,
} from "../../src/ui/custom-commands.js";

let project: string;
let home: string;
const originalHome = process.env["BHARATBUILD_HOME"];

const write = (dir: string, rel: string, body: string) => {
  const full = path.join(dir, ".bharatbuild", "commands", rel);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, body);
};

beforeEach(() => {
  project = fs.mkdtempSync(path.join(os.tmpdir(), "bb-cmd-"));
  home = fs.mkdtempSync(path.join(os.tmpdir(), "bb-cmdhome-"));
  process.env["BHARATBUILD_HOME"] = home;
});
afterEach(() => {
  if (originalHome === undefined) delete process.env["BHARATBUILD_HOME"];
  else process.env["BHARATBUILD_HOME"] = originalHome;
  for (const d of [project, home]) {
    try { fs.rmSync(d, { recursive: true, force: true }); } catch { /* windows lock */ }
  }
});

describe("finding them", () => {
  it("loads a command from the project", () => {
    write(project, "review.toml", 'description = "Review"\nprompt = "Review this."');
    const { commands } = loadCustomCommands(project);
    expect(commands.map((c) => c.name)).toEqual(["review"]);
    expect(commands[0]!.description).toBe("Review");
  });

  it("namespaces a command in a subdirectory", () => {
    // So a project can group prompts without colliding with anything else.
    write(project, path.join("git", "log.toml"), 'prompt = "Summarise."');
    expect(loadCustomCommands(project).commands[0]!.name).toBe("git:log");
  });

  it("finds nothing when there is no commands directory", () => {
    // The overwhelmingly common case must be silent, not an error.
    const { commands, errors } = loadCustomCommands(project);
    expect(commands).toEqual([]);
    expect(errors).toEqual([]);
  });

  it("lets a project command shadow a personal one of the same name", () => {
    fs.mkdirSync(path.join(home, "commands"), { recursive: true });
    fs.writeFileSync(path.join(home, "commands", "review.toml"), 'prompt = "personal"');
    write(project, "review.toml", 'prompt = "project"');
    const { commands } = loadCustomCommands(project);
    expect(commands).toHaveLength(1);
    expect(commands[0]!.prompt).toBe("project");
  });

  it("searches the user directory as well as the project", () => {
    fs.mkdirSync(path.join(home, "commands"), { recursive: true });
    fs.writeFileSync(path.join(home, "commands", "mine.toml"), 'prompt = "p"');
    expect(loadCustomCommands(project).commands.map((c) => c.name)).toContain("mine");
    expect(commandDirs(project)).toHaveLength(2);
  });

  it("derives the name from the path, not the file contents", () => {
    expect(commandName(path.join("/root", "a", "b.toml"), "/root")).toBe("a:b");
  });
});

describe("a file that is wrong", () => {
  it("is reported and skipped rather than thrown", () => {
    // One malformed file must not stop the session from starting.
    write(project, "broken.toml", "this is not = valid toml [[[");
    write(project, "good.toml", 'prompt = "fine"');
    const { commands, errors } = loadCustomCommands(project);
    expect(commands.map((c) => c.name)).toEqual(["good"]);
    expect(errors).toHaveLength(1);
    expect(errors[0]!.file).toMatch(/broken\.toml$/);
  });

  it("says what was missing when there is no prompt", () => {
    write(project, "empty.toml", 'description = "no prompt here"');
    const { errors } = loadCustomCommands(project);
    expect(errors[0]!.reason).toMatch(/prompt/);
  });

  it("falls back to a description rather than showing none", () => {
    write(project, "bare.toml", 'prompt = "just a prompt"');
    expect(loadCustomCommands(project).commands[0]!.description).toContain("bare");
  });
});

describe("arguments", () => {
  it("substitutes {{args}}", () => {
    expect(applyArgs("Review for {{args}}.", "security")).toBe("Review for security.");
  });

  it("substitutes every occurrence", () => {
    expect(applyArgs("{{args}} and {{args}}", "x")).toBe("x and x");
  });

  it("appends arguments when the template has no placeholder", () => {
    // Silently dropping what the user typed is the worst option.
    expect(applyArgs("Do the thing.", "carefully")).toBe("Do the thing.\n\ncarefully");
  });

  it("leaves a template alone when no arguments were given", () => {
    expect(applyArgs("Do the thing.", "")).toBe("Do the thing.");
  });
});

describe("shell injection", () => {
  it("finds the commands to run", () => {
    expect(shellInjections("a !{git status} b !{ls} c")).toEqual(["git status", "ls"]);
  });

  it("substitutes their output", async () => {
    const out = await expandShell("Diff:\n!{git diff}", async () => "the diff");
    expect(out).toBe("Diff:\nthe diff");
  });

  it("sends the prompt anyway when a command fails", async () => {
    // A model can work with a note that one piece of context is missing; it
    // can do nothing at all if the whole command is abandoned.
    const out = await expandShell("Context: !{boom}", async () => { throw new Error("no such thing"); });
    expect(out).toContain("command failed");
    expect(out).toContain("no such thing");
  });

  it("leaves a prompt with no injections untouched", async () => {
    const out = await expandShell("plain prompt", async () => "should not run");
    expect(out).toBe("plain prompt");
  });
});
