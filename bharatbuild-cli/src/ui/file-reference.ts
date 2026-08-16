import fs from "fs";
import path from "path";
import readline from "readline";
import chalk from "chalk";

export function parseFileReferences(input: string, cwd: string): string[] {
  const matches: string[] = [];
  const re = /@([\w./\\-]+)/g;
  let m;
  while ((m = re.exec(input)) !== null) {
    const ref = m[1] ?? "";
    const full = path.resolve(cwd, ref);
    if (fs.existsSync(full)) matches.push(full);
  }
  return matches;
}

export function expandFileReferences(input: string, cwd: string): string {
  return input.replace(/@([w./\\-]+)/g, (_match, ref: string) => {
    const full = path.resolve(cwd, ref);
    try {
      if (fs.existsSync(full)) {
        const stat = fs.statSync(full);
        if (stat.isFile() && stat.size < 100_000) {
          const content = fs.readFileSync(full, "utf8");
          return `\n\n[${ref}]:\n\`\`\`\n${content}\n\`\`\`\n`;
        }
      }
    } catch {}
    return _match;
  });
}

export async function tabCompleteFile(prefix: string, cwd: string): Promise<string[]> {
  const dir = path.resolve(cwd, path.dirname(prefix));
  const base = path.basename(prefix);
  try {
    return fs.readdirSync(dir)
      .filter((f) => f.startsWith(base))
      .slice(0, 10)
      .map((f) => {
        const full = path.join(path.dirname(prefix), f);
        const stat = fs.statSync(path.resolve(cwd, full));
        return stat.isDirectory() ? full + "/" : full;
      });
  } catch { return []; }
}
