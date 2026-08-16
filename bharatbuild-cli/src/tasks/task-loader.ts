import fs from "fs";
import path from "path";
export interface TaskDefinition { id: string; title: string; description: string; acceptanceCriteria?: string[]; }
export function loadTaskFile(filePath: string): TaskDefinition | null {
  try {
    const c = fs.readFileSync(filePath, "utf8");
    return {
      id: path.basename(filePath, path.extname(filePath)),
      title: c.match(/^#\s+(.+)$/m)?.[1]?.trim() ?? path.basename(filePath),
      description: c,
      acceptanceCriteria: c.match(/^##\s+Acceptance/m) ? c.split("\n").filter((l) => l.startsWith("- ")).map((l) => l.slice(2)) : undefined,
    };
  } catch { return null; }
}
export function loadTasksDir(dir: string): TaskDefinition[] {
  const td = path.join(dir, ".bharatbuild", "tasks");
  if (!fs.existsSync(td)) return [];
  return fs.readdirSync(td).filter((f) => f.endsWith(".md")).map((f) => loadTaskFile(path.join(td, f))).filter(Boolean) as TaskDefinition[];
}
