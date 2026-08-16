import { executeCommand } from "../shell/index.js";
export interface Diagnostic { file:string; line:number; severity:"error"|"warning"|"info"; message:string; }
export async function getTypeScriptDiagnostics(cwd?: string): Promise<Diagnostic[]> {
  const r = await executeCommand({ command:"npx tsc --noEmit 2>&1", working_dir:cwd });
  const diags: Diagnostic[] = [];
  const re = /^(.+?)\((\d+),\d+\): (error|warning) TS\d+: (.+)$/gm; let m;
  while ((m = re.exec(r.content)) !== null) {
    diags.push({ file:m[1]??"", line:parseInt(m[2]??"0"), severity:(m[3]??"info") as "error"|"warning", message:m[4]??"" });
  }
  return diags;
}
export async function getESLintDiagnostics(cwd?: string): Promise<Diagnostic[]> {
  const r = await executeCommand({ command:"npx eslint . --format json 2>/dev/null", working_dir:cwd });
  try {
    const results = JSON.parse(r.content) as Array<{filePath:string; messages:Array<{line:number;severity:number;message:string}>}>;
    return results.flatMap((f) => f.messages.map((m) => ({ file:f.filePath, line:m.line, severity:m.severity===2?"error":"warning" as "error"|"warning", message:m.message })));
  } catch { return []; }
}
