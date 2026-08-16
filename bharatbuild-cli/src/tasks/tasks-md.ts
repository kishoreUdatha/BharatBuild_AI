/**
 * BharatBuild CLI - tasks.md parser
 *
 * `spec new` / `spec quick` write a tasks.md full of checkbox items. Nothing
 * read it back, so the spec workflow stopped at "here are three markdown
 * files". This module turns that file into executable units and ticks the
 * checkboxes as they complete.
 */
import fs from "fs";
import path from "path";

export interface ParsedTask {
  /** Task text with the checkbox and bold markers stripped. */
  title: string;
  /** Indented sub-bullets (File:, Changes:, Depends on:, ...). */
  detail: string[];
  /** 0-based index of the checkbox line, used to tick it in place. */
  line: number;
  checked: boolean;
}

/** Only top-level "- [ ]" items count; sub-bullets are detail, not tasks. */
const CHECKBOX = /^(\s*)-\s*\[( |x|X)\]\s*(.+)$/;

/**
 * Headings whose checkboxes are exit criteria rather than work items. Running
 * "All tasks complete" as a task would be circular.
 */
const NON_TASK_SECTIONS = [/^#+\s*definition of done/i, /^#+\s*acceptance/i];

export function specTasksPath(projectDir: string = process.cwd()): string {
  return path.join(projectDir, ".bharatbuild", "specs", "tasks.md");
}

export function parseTasksMarkdown(content: string): ParsedTask[] {
  const lines = content.split("\n");
  const tasks: ParsedTask[] = [];
  let skipping = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]!;

    if (/^#+\s/.test(line)) {
      skipping = NON_TASK_SECTIONS.some((re) => re.test(line));
      continue;
    }
    if (skipping) continue;

    const m = CHECKBOX.exec(line);
    if (!m) continue;
    // Indented checkboxes belong to the task above them.
    if (m[1]!.length > 0) continue;

    const title = m[3]!
      .replace(/\*\*/g, "")
      .replace(/^Task\s*\d+\s*:\s*/i, "")
      .trim();
    if (!title) continue;

    const detail: string[] = [];
    for (let j = i + 1; j < lines.length; j++) {
      const next = lines[j]!;
      if (!next.trim()) continue;
      if (!/^\s+/.test(next)) break; // dedented - next task or new section
      detail.push(next.trim().replace(/^-\s*/, ""));
    }

    tasks.push({ title, detail, line: i, checked: m[2]!.toLowerCase() === "x" });
  }

  return tasks;
}

export function loadSpecTasks(projectDir: string = process.cwd()): ParsedTask[] {
  const p = specTasksPath(projectDir);
  if (!fs.existsSync(p)) return [];
  return parseTasksMarkdown(fs.readFileSync(p, "utf8"));
}

/** Tick (or untick) the checkbox on a given line, preserving everything else. */
export function setTaskChecked(
  line: number,
  checked: boolean,
  projectDir: string = process.cwd(),
): boolean {
  const p = specTasksPath(projectDir);
  if (!fs.existsSync(p)) return false;

  const lines = fs.readFileSync(p, "utf8").split("\n");
  const target = lines[line];
  if (target === undefined || !CHECKBOX.test(target)) return false;

  lines[line] = target.replace(/\[( |x|X)\]/, checked ? "[x]" : "[ ]");
  fs.writeFileSync(p, lines.join("\n"));
  return true;
}

/** Render a task as the instruction handed to the agent. */
export function taskToPrompt(task: ParsedTask): string {
  const parts = [`Implement this task from the project spec:\n\n${task.title}`];
  if (task.detail.length > 0) parts.push(`\nDetails:\n${task.detail.map((d) => `- ${d}`).join("\n")}`);
  parts.push(
    "\nRead the relevant files before editing. Make the change, then verify it " +
    "compiles or passes tests. Do not start work beyond this task.",
  );
  return parts.join("\n");
}
