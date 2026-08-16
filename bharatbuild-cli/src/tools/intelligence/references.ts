import fs from "fs"; import path from "path";
export interface Reference { file:string; line:number; column:number; context:string; }
export function findReferences(symbolName: string, rootDir: string): Reference[] {
  const refs: Reference[] = [];
  const re = new RegExp(`\\b${symbolName}\\b`, "g");
  function walk(dir: string) {
    try {
      for (const e of fs.readdirSync(dir,{withFileTypes:true})) {
        const full = path.join(dir,e.name);
        if (e.isDirectory() && !["node_modules",".git","dist"].includes(e.name)) walk(full);
        else if (e.isFile() && /\.(ts|js|tsx|jsx|py|java|go)$/.test(e.name)) {
          try {
            const lines = fs.readFileSync(full,"utf8").split("\n");
            lines.forEach((line,i) => { const m = line.match(re); if (m) refs.push({file:full,line:i+1,column:line.indexOf(symbolName)+1,context:line.trim()}); });
          } catch { /* skip */ }
        }
      }
    } catch { /* skip */ }
  }
  walk(rootDir);
  return refs;
}
