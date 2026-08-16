import { spawn } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";

export async function openEditor(initialContent = ""): Promise<string | null> {
  const editor = process.env["EDITOR"] ?? process.env["VISUAL"] ?? (process.platform === "win32" ? "notepad" : "vi");
  const tmpFile = path.join(os.tmpdir(), `bharatbuild-input-${Date.now()}.md`);
  fs.writeFileSync(tmpFile, initialContent, "utf8");
  return new Promise((resolve) => {
    const child = spawn(editor, [tmpFile], { stdio: "inherit" });
    child.on("close", () => {
      try {
        const content = fs.readFileSync(tmpFile, "utf8").trim();
        fs.unlinkSync(tmpFile);
        resolve(content || null);
      } catch { resolve(null); }
    });
    child.on("error", () => { console.error(`Cannot open editor: ${editor}`); resolve(null); });
  });
}
