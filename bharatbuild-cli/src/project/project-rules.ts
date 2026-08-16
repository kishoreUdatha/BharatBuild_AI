import fs from "fs";
import path from "path";
export function loadProjectRules(dir?: string): string {
  const files = [".bharatbuild/rules.md", "CLAUDE.md", ".cursorrules"];
  for (const f of files) {
    const full = path.join(dir ?? process.cwd(), f);
    try { if (fs.existsSync(full)) return fs.readFileSync(full, "utf8"); } catch {}
  }
  return "";
}
