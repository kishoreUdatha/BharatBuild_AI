import fs from "fs";
import path from "path";
import { minimatch } from "minimatch";

export function loadKiroIgnore(dir?: string): string[] {
  const root = dir ?? process.cwd();
  const files = [".bharatbuildignore", ".kiroignore", ".gitignore"];
  const patterns: string[] = ["node_modules/**", "dist/**", ".git/**", "*.log"];
  for (const f of files) {
    const full = path.join(root, f);
    try {
      if (fs.existsSync(full)) {
        const lines = fs.readFileSync(full, "utf8").split("\n")
          .map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
        patterns.push(...lines);
      }
    } catch {}
  }
  return [...new Set(patterns)];
}

export function isIgnored(filePath: string, patterns: string[]): boolean {
  const rel = path.relative(process.cwd(), filePath).replace(/\\/g, "/");
  return patterns.some((pat) => minimatch(rel, pat, { dot: true }));
}
