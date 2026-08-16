import fs from "fs";
export function applyDeterministicFixes(filePath: string): boolean {
  try { let c=fs.readFileSync(filePath,"utf8"); const orig=c; c=c.split("\n").map((l)=>l.trimEnd()).join("\n"); if (!c.endsWith("\n")) c+="\n"; if (c!==orig){fs.writeFileSync(filePath,c,"utf8");return true;} return false; } catch { return false; }
}
