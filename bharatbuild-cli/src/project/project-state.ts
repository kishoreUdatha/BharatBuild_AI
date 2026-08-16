import fs from "fs";
import path from "path";
export interface ProjectState { lastTask?: string; lastModel?: string; sessionId?: string; updatedAt: string; }
export function loadState(dir?: string): ProjectState | null {
  try {
    const f = path.join(dir ?? process.cwd(), ".bharatbuild/state.json");
    if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as ProjectState;
  } catch {}
  return null;
}
export function saveState(state: Partial<ProjectState>, dir?: string) {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild/state.json");
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const existing = loadState(dir) ?? { updatedAt: "" };
  fs.writeFileSync(f, JSON.stringify({ ...existing, ...state, updatedAt: new Date().toISOString() }, null, 2));
}
