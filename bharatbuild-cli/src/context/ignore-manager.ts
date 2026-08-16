import fs from "fs"; import path from "path";
const DEFAULT_IGNORE = ["node_modules","dist","build",".git","__pycache__",".next","coverage",".venv","venv"];
export class IgnoreManager {
  private patterns: string[] = [...DEFAULT_IGNORE];
  constructor(projectDir: string) {
    const gp = path.join(projectDir,".gitignore");
    if (fs.existsSync(gp)) { const lines = fs.readFileSync(gp,"utf8").split("\n"); for (const l of lines) { const t=l.trim(); if (t&&!t.startsWith("#")) this.patterns.push(t); } }
  }
  isIgnored(filePath: string): boolean { const parts = filePath.replace(/\\/g,"/").split("/"); return this.patterns.some((p) => parts.some((part) => part===p||part.match(p.replace(/\*/g,".*")))); }
}
