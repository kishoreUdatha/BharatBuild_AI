import fs from "fs"; import path from "path";
import { IgnoreManager } from "./ignore-manager.js"; import { detectStack } from "./stack-detector.js";
export interface RepoSummary { totalFiles:number; languages:Record<string,number>; topFiles:string[]; stack:ReturnType<typeof detectStack>; }
export function scanRepository(dir: string): RepoSummary {
  const ignore = new IgnoreManager(dir); const languages: Record<string,number> = {}; let totalFiles=0; const allFiles: string[]=[];
  function walk(d: string) { try { for (const e of fs.readdirSync(d,{withFileTypes:true})) { const full=path.join(d,e.name); if (ignore.isIgnored(e.name)) continue; if (e.isDirectory()) walk(full); else if (e.isFile()) { totalFiles++; allFiles.push(full); const ext=path.extname(e.name).slice(1); if (ext) languages[ext]=(languages[ext]??0)+1; } } } catch { /* skip */ } }
  walk(dir); return { totalFiles, languages, topFiles:allFiles.slice(0,20).map((f)=>path.relative(dir,f)), stack:detectStack(dir) };
}
