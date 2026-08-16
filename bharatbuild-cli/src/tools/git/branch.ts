import { executeCommand } from "../shell/index.js";
export async function createBranch(name: string, cwd?: string) {
  return { success: !(await executeCommand({ command: `git checkout -b ${name}`, working_dir: cwd })).isError };
}
export async function listBranches(cwd?: string): Promise<string[]> {
  const r = await executeCommand({ command: "git branch --format=%(refname:short)", working_dir: cwd });
  return r.isError ? [] : r.content.split("\n").filter(Boolean);
}
export async function switchBranch(name: string, cwd?: string) {
  return { success: !(await executeCommand({ command: `git checkout ${name}`, working_dir: cwd })).isError };
}
