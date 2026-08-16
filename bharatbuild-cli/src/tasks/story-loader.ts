import fs from "fs";
import path from "path";
export interface Story { id: string; title: string; description: string; }
export function loadStory(filePath: string): Story | null {
  try {
    const c = fs.readFileSync(filePath, "utf8");
    return { id: path.basename(filePath, ".md"), title: c.split("\n")[0]?.replace(/^#\s*/, "") ?? "Untitled", description: c };
  } catch { return null; }
}
