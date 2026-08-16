import fs from "fs"; import path from "path";
export interface Symbol { name:string; kind:string; file:string; line:number; }
export function extractSymbols(filePath: string): Symbol[] {
  const symbols: Symbol[] = [];
  try {
    const content = fs.readFileSync(filePath,"utf8");
    const lines = content.split("\n");
    const patterns: Array<{re:RegExp; kind:string}> = [
      { re:/^export\s+(?:async\s+)?function\s+(\w+)/, kind:"function" },
      { re:/^export\s+class\s+(\w+)/, kind:"class" },
      { re:/^export\s+interface\s+(\w+)/, kind:"interface" },
      { re:/^export\s+type\s+(\w+)/, kind:"type" },
      { re:/^export\s+const\s+(\w+)/, kind:"const" },
      { re:/^def\s+(\w+)\s*\(/, kind:"function" },
      { re:/^class\s+(\w+)/, kind:"class" },
    ];
    lines.forEach((line, i) => {
      for (const { re, kind } of patterns) {
        const m = line.match(re);
        if (m) symbols.push({ name:m[1]??"", kind, file:filePath, line:i+1 });
      }
    });
  } catch { /* skip unreadable */ }
  return symbols;
}
