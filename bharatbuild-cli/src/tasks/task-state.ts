/**
 * BharatBuild CLI - Task State
 *
 * Persisted status for the tasks in a spec's tasks.md.
 *
 * This used to be an in-memory Map, which meant a task list could not survive
 * a single CLI invocation - `spec run` would forget everything the moment the
 * process exited. State now lives in <projectDir>/.bharatbuild/tasks.json so
 * an interrupted run can be resumed.
 */
import fs from "fs";
import path from "path";

export type TaskStatus = "pending" | "in_progress" | "done" | "failed";

export interface TaskState {
  id: string;
  title: string;
  status: TaskStatus;
  /** Line index in tasks.md, so the checkbox can be ticked back. */
  line?: number;
  createdAt: string;
  updatedAt: string;
  error?: string;
}

interface TaskFile {
  version: 1;
  updatedAt: string;
  tasks: TaskState[];
}

const STATE_VERSION = 1;

export function taskStatePath(projectDir: string = process.cwd()): string {
  return path.join(projectDir, ".bharatbuild", "tasks.json");
}

export function loadTasks(projectDir: string = process.cwd()): TaskState[] {
  try {
    const p = taskStatePath(projectDir);
    if (!fs.existsSync(p)) return [];
    const parsed = JSON.parse(fs.readFileSync(p, "utf8")) as TaskFile;
    if (parsed.version !== STATE_VERSION || !Array.isArray(parsed.tasks)) return [];
    return parsed.tasks;
  } catch {
    return []; // corrupt state must not wedge the CLI
  }
}

export function saveTasks(tasks: TaskState[], projectDir: string = process.cwd()): void {
  const p = taskStatePath(projectDir);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const payload: TaskFile = { version: STATE_VERSION, updatedAt: new Date().toISOString(), tasks };
  fs.writeFileSync(p, JSON.stringify(payload, null, 2));
}

/**
 * Reconcile persisted state with the tasks currently in tasks.md.
 *
 * Tasks are keyed by position, so status survives re-reads of an unchanged
 * file. If the title at a position changed, the task is treated as new and its
 * status resets - carrying "done" over to different work would be a lie.
 */
export function syncTasks(
  parsed: Array<{ title: string; line: number }>,
  projectDir: string = process.cwd(),
): TaskState[] {
  const existing = loadTasks(projectDir);
  const now = new Date().toISOString();

  const merged: TaskState[] = parsed.map((p, i) => {
    const id = `task-${i + 1}`;
    const prior = existing.find((t) => t.id === id);
    if (prior && prior.title === p.title) {
      return { ...prior, line: p.line, updatedAt: prior.updatedAt };
    }
    return { id, title: p.title, status: "pending", line: p.line, createdAt: now, updatedAt: now };
  });

  saveTasks(merged, projectDir);
  return merged;
}

export function createTask(title: string, projectDir: string = process.cwd()): TaskState {
  const tasks = loadTasks(projectDir);
  const now = new Date().toISOString();
  const t: TaskState = {
    id: `task-${tasks.length + 1}`,
    title,
    status: "pending",
    createdAt: now,
    updatedAt: now,
  };
  saveTasks([...tasks, t], projectDir);
  return t;
}

export function updateTask(
  id: string,
  update: Partial<TaskState>,
  projectDir: string = process.cwd(),
): TaskState | undefined {
  const tasks = loadTasks(projectDir);
  const i = tasks.findIndex((t) => t.id === id);
  if (i === -1) return undefined;
  // Clear a stale error whenever a task leaves the failed state.
  const next: TaskState = { ...tasks[i]!, ...update, updatedAt: new Date().toISOString() };
  if (update.status && update.status !== "failed") delete next.error;
  tasks[i] = next;
  saveTasks(tasks, projectDir);
  return next;
}

export function getTask(id: string, projectDir: string = process.cwd()): TaskState | undefined {
  return loadTasks(projectDir).find((t) => t.id === id);
}

export function listTasks(projectDir: string = process.cwd()): TaskState[] {
  return loadTasks(projectDir);
}

export function resetTasks(projectDir: string = process.cwd()): void {
  saveTasks([], projectDir);
}
