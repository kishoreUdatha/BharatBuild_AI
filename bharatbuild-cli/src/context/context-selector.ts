import path from "path"; import { searchCode } from "../tools/search/index.js";
export async function selectRelevantFiles(task: string, projectDir: string, maxFiles=10): Promise<string[]> {
  const keywords=task.toLowerCase().split(/\s+/).filter((w)=>w.length>3); const allMatches=new Set<string>();
  for (const kw of keywords.slice(0,5)) { const r=await searchCode({pattern:kw,directory:projectDir,max_results:5}); r.content.split("\n").filter((l)=>!l.startsWith(" ")&&l.includes(path.sep)).forEach((f)=>allMatches.add(f.trim())); }
  return Array.from(allMatches).slice(0,maxFiles);
}
