import { gitDiff } from "../tools/git/index.js";
export async function checkRegressions(cwd?: string): Promise<{hasChanges:boolean;changedFiles:string[]}> {
  const diff=await gitDiff({staged:false,working_dir:cwd}); if (!diff.content||diff.isError) return {hasChanges:false,changedFiles:[]};
  const files=[...diff.content.matchAll(/^diff --git a\/.+ b\/(.+)$/gm)].map((m)=>m[1]??"");
  return {hasChanges:files.length>0,changedFiles:files};
}
