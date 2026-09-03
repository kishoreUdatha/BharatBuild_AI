/**
 * Slash commands defined by the user, as .toml files.
 *
 * The registry was a fixed list compiled into the binary, so a project could
 * not add a command of its own — every team's repeated prompt ("review this
 * diff the way we review diffs", "write the release note") had to be retyped
 * or pasted from elsewhere. Custom agents already loaded from disk; commands
 * did not, which is an odd place to draw the line.
 *
 * Format, following gemini-cli's so files are portable between the two:
 *
 *     description = "Review the working tree"
 *     prompt = """
 *     Review these changes for {{args}}.
 *
 *     !{git diff}
 *     """
 *
 * `{{args}}` takes whatever followed the command name. `!{...}` runs a shell
 * command and substitutes its output, so a command can gather its own context
 * instead of describing where to find it.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { parse as parseToml } from "smol-toml";

export interface CustomCommand {
  /** Invoked as /name, or /dir:name for a file in a subdirectory. */
  name: string;
  description: string;
  /** Raw prompt text, placeholders not yet substituted. */
  prompt: string;
  /** Where it came from, for /help and for error messages. */
  source: string;
}

/** Directories searched, nearest last so a project overrides the user's. */
export function commandDirs(cwd: string = process.cwd()): string[] {
  const home = process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild");
  return [path.join(home, "commands"), path.join(cwd, ".bharatbuild", "commands")];
}

/** Every .toml under `dir`, recursively. */
function tomlFiles(dir: string, depth = 0): string[] {
  if (depth > 4) return [];
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];                     // absent directory is the normal case
  }
  const out: string[] = [];
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...tomlFiles(full, depth + 1));
    else if (e.isFile() && e.name.endsWith(".toml")) out.push(full);
  }
  return out;
}

/**
 * Command name from its path relative to the commands directory.
 *
 * A nested file becomes a namespaced command — commands/git/review.toml is
 * `/git:review` — so a project can group related prompts without them
 * colliding with anything else.
 */
export function commandName(file: string, root: string): string {
  const rel = path.relative(root, file).replace(/\.toml$/i, "");
  return rel.split(path.sep).join(":").toLowerCase();
}

export interface LoadResult {
  commands: CustomCommand[];
  /** Files that could not be used, with the reason. Never thrown. */
  errors: Array<{ file: string; reason: string }>;
}

/**
 * Load every custom command.
 *
 * A broken file is reported and skipped rather than thrown: one malformed
 * .toml must not stop the session from starting, and the user needs to be
 * told which file and why.
 */
export function loadCustomCommands(cwd: string = process.cwd()): LoadResult {
  const commands = new Map<string, CustomCommand>();
  const errors: LoadResult["errors"] = [];

  for (const dir of commandDirs(cwd)) {
    for (const file of tomlFiles(dir)) {
      const name = commandName(file, dir);
      try {
        const parsed = parseToml(fs.readFileSync(file, "utf8")) as Record<string, unknown>;
        const prompt = parsed["prompt"];
        if (typeof prompt !== "string" || !prompt.trim()) {
          errors.push({ file, reason: "needs a non-empty `prompt` string" });
          continue;
        }
        const description = typeof parsed["description"] === "string"
          ? parsed["description"]
          : `Custom command (${name})`;
        // Later directories win, so a project file shadows a personal one of
        // the same name rather than duplicating it in the palette.
        commands.set(name, { name, description, prompt, source: file });
      } catch (err) {
        errors.push({ file, reason: err instanceof Error ? err.message : String(err) });
      }
    }
  }

  return { commands: [...commands.values()].sort((a, b) => a.name.localeCompare(b.name)), errors };
}

/** Replace `{{args}}` with what the user typed after the command name. */
export function applyArgs(prompt: string, args: string): string {
  if (!prompt.includes("{{args}}")) {
    // No placeholder: append the arguments so they are not silently dropped.
    return args.trim() ? `${prompt}\n\n${args}` : prompt;
  }
  return prompt.split("{{args}}").join(args);
}

/** The `!{...}` shell injections in a prompt, in order. */
export function shellInjections(prompt: string): string[] {
  const out: string[] = [];
  const re = /!\{([^}]+)\}/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(prompt)) !== null) out.push(m[1]!.trim());
  return out;
}

/**
 * Substitute `!{cmd}` with the command's output.
 *
 * `run` is injected so the caller decides how commands execute — the TUI
 * routes them through the same shell tool as everything else, and tests pass
 * a stub rather than running anything.
 */
export async function expandShell(
  prompt: string,
  run: (cmd: string) => Promise<string>,
): Promise<string> {
  const injections = shellInjections(prompt);
  let out = prompt;
  for (const cmd of injections) {
    let result: string;
    try {
      result = await run(cmd);
    } catch (err) {
      // The prompt still goes through: the model can work with a note that
      // one piece of context is missing, and cannot work at all if the whole
      // command fails.
      result = `(command failed: ${err instanceof Error ? err.message : String(err)})`;
    }
    out = out.replace(`!{${cmd}}`, result);
  }
  return out;
}
