import fs from "fs";
import path from "path";
export interface ProjectConfig { name: string; description?: string; mode: string; model: string; apiUrl: string; createdAt: string; }
export function loadProjectConfig(dir?: string): ProjectConfig | null {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild.json");
  try { if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as ProjectConfig; } catch {}
  return null;
}
export function saveProjectConfig(config: ProjectConfig, dir?: string) {
  fs.writeFileSync(path.join(dir ?? process.cwd(), ".bharatbuild.json"), JSON.stringify(config, null, 2));
}
